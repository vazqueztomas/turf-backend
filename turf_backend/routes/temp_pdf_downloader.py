import logging
import tempfile

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from turf_backend.database import get_connection
from turf_backend.models.turf import Horse, Race
from turf_backend.routes.horses import (
    extract_races_and_assign,
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/turf", tags=["Turf Daily Update"])


class DailyPdfUpdater:
    BASE_URL = "https://www.palermo.com.ar/es/turf/programa-oficial"
    PDF_DOWNLOAD_TEXT = "Descargar VersiÃ³n PDF"

    def _make_request(self, url: str) -> str:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text

    def _download_pdf(self, url: str) -> bytes:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.content

    def _parse_anchor_tags(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        return soup.find_all("a", href=True)

    def download_pdfs_temporarily(self):
        """Descarga PDFs y devuelve la lista de bytes."""
        try:
            response_text = self._make_request(self.BASE_URL)
            anchor_tags = self._parse_anchor_tags(response_text)

            pdf_sources = [
                a["href"]
                for a in anchor_tags
                if "programa-oficial-reunion" in a["href"]
            ]
            if not pdf_sources:
                return []

            pdf_urls = []
            for source in pdf_sources:
                resp_text = self._make_request(source)
                anchor_tags = self._parse_anchor_tags(resp_text)
                pdf_urls.extend(
                    a["href"]
                    for a in anchor_tags
                    if a["href"].endswith(".pdf")
                    and a.text.strip() == self.PDF_DOWNLOAD_TEXT
                )
            pdf_bytes_list = [self._download_pdf(url) for url in pdf_urls]
            return pdf_bytes_list
        except Exception as e:
            logger.exception("Error descargando PDFs")
            raise HTTPException(status_code=500, detail=f"Error descargando PDFs: {e}")


@router.post("/daily-update")
def daily_update(session: Session = Depends(get_connection)):
    """
    Descarga los PDFs de Palermo, extrae carreras y caballos, y guarda únicamente los registros nuevos.
    Evita duplicados automáticamente.
    """
    updater = DailyPdfUpdater()
    pdfs = updater.download_pdfs_temporarily()
    if not pdfs:
        return {"message": "No se encontraron PDFs nuevos"}

    inserted_races = 0
    inserted_horses = 0
    total_horses_extracted = 0

    for pdf_content in pdfs:
        # Guardar PDF temporalmente
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
            tmp.write(pdf_content)
            tmp.flush()
            extraction = extract_races_and_assign(tmp.name)

        total_horses_extracted += extraction["summary"]["horses"]
        races = extraction["races"]

        for r in races:
            # Buscar o crear carrera única
            race_obj = session.exec(
                select(Race).where(Race.numero == r["num"], Race.hipodromo == "Palermo")
            ).first()
            if not race_obj:
                race_obj = Race(
                    numero=r["num"],
                    nombre=r.get("nombre"),
                    distancia=r.get("distancia"),
                    fecha=r.get("hora"),
                    hipodromo="Palermo",
                )
                session.add(race_obj)
                session.commit()
                session.refresh(race_obj)
                inserted_races += 1

            # Insertar caballos asociados
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

                horse_obj = Horse(
                    race_id=race_obj.id,
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
                session.add(horse_obj)
                inserted_horses += 1

    session.commit()

    return {
        "message": "✅ Daily update completado.",
        "races_inserted": inserted_races,
        "horses_inserted": inserted_horses,
        "total_horses_extracted": total_horses_extracted,
    }
