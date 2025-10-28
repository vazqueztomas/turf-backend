import logging
import tempfile

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import select

from turf_backend.database import get_connection
from turf_backend.models.turf import Horse, Race
from turf_backend.routes.horses import extract_races_and_assign

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/turf", tags=["Turf Daily Update"])


class DailyPdfUpdater:
    BASE_URL = "https://www.palermo.com.ar/es/turf/programa-oficial"
    PDF_DOWNLOAD_TEXT = "Descargar VersiÃ³n PDF"

    def _make_request(self, url: str) -> str:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.text

    def _download_pdf(self, url: str) -> bytes:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    def _parse_anchor_tags(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        return soup.find_all("a", href=True)

    def fetch_latest_pdfs(self) -> list[bytes]:
        """
        Descarga todos los PDFs disponibles temporalmente desde Palermo.
        """
        try:
            response_text = self._make_request(self.BASE_URL)
            anchors = self._parse_anchor_tags(response_text)

            pdf_sources = [
                a["href"] for a in anchors if "programa-oficial-reunion" in a["href"]
            ]
            if not pdf_sources:
                logger.info("No se encontraron fuentes de PDFs.")
                return []

            pdf_urls = []
            for source in pdf_sources:
                html = self._make_request(source)
                anchors = self._parse_anchor_tags(html)
                pdf_urls.extend(
                    a["href"]
                    for a in anchors
                    if a["href"].endswith(".pdf")
                    and a.text.strip() == self.PDF_DOWNLOAD_TEXT
                )

            pdf_bytes = []
            for url in pdf_urls:
                logger.info(f"Descargando PDF: {url}")
                pdf_bytes.append(self._download_pdf(url))

            logger.info(f"Total PDFs descargados: {len(pdf_bytes)}")
            return pdf_bytes
        except Exception as e:
            logger.exception("Error descargando PDFs.")
            raise HTTPException(status_code=500, detail=f"Error descargando PDFs: {e}")


def process_pdfs_and_update_db():
    """
    Ejecuta el scraper + procesamiento y actualiza la base de datos.
    Se usa como background task.
    """
    logger.info("🔄 Iniciando actualización diaria de turf (background)...")
    updater = DailyPdfUpdater()

    # Creamos nuestra propia sesión independiente
    session_gen = get_connection()
    session = next(session_gen)

    try:
        pdfs = updater.fetch_latest_pdfs()
        if not pdfs:
            logger.info("No se encontraron PDFs nuevos.")
            return

        inserted_races = 0
        inserted_horses = 0
        total_horses_extracted = 0

        for pdf_content in pdfs:
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
                tmp.write(pdf_content)
                tmp.flush()
                extraction = extract_races_and_assign(tmp.name)

            total_horses_extracted += extraction["summary"]["horses"]
            races = extraction["races"]

            for r in races:
                # Buscar o crear carrera
                race = session.exec(
                    select(Race).where(
                        Race.numero == r["num"], Race.hipodromo == "Palermo"
                    )
                ).first()
                if not race:
                    race = Race(
                        numero=r["num"],
                        nombre=r.get("nombre"),
                        distancia=r.get("distancia"),
                        fecha=r.get("hora"),
                        hipodromo="Palermo",
                    )
                    session.add(race)
                    session.commit()
                    session.refresh(race)
                    inserted_races += 1

                for h in r.get("horses", []):
                    exists = session.exec(
                        select(Horse).where(
                            Horse.nombre == h.get("nombre"),
                            Horse.numero == h.get("num"),
                            Horse.page == h.get("page"),
                        )
                    ).first()
                    if exists:
                        continue

                    horse = Horse(
                        race_id=race.id,
                        numero=h.get("num"),
                        nombre=h.get("nombre"),
                        peso=h.get("peso"),
                        jockey=h.get("jockey"),
                        ultimas=h.get("ultimas"),
                        padre_madre=h.get("padre_madre"),
                        entrenador=h.get("entrenador"),
                        raw_rest=h.get("raw_rest"),
                        page=h.get("page"),
                        line_index=h.get("line_index"),
                    )
                    session.add(horse)
                    inserted_horses += 1

        session.commit()
        logger.info(
            f"✅ Actualización completada: {inserted_races} carreras nuevas, "
            f"{inserted_horses} caballos nuevos, {total_horses_extracted} extraídos en total."
        )
    except Exception as e:
        logger.exception(f"Error en background update: {e}")
        session.rollback()
    finally:
        try:
            session_gen.close()
        except Exception:
            pass


@router.post("/daily-update")
def trigger_daily_update(background_tasks: BackgroundTasks):
    """
    Endpoint que dispara el proceso de scraping y carga en background.
    Devuelve respuesta inmediata para evitar timeouts en Vercel.
    """
    try:
        background_tasks.add_task(process_pdfs_and_update_db)
        return {"message": "🚀 Daily update iniciado en background."}
    except Exception as e:
        logger.exception("Error iniciando actualización diaria")
        raise HTTPException(
            status_code=500, detail=f"No se pudo iniciar el proceso: {e}"
        )
