import logging
import tempfile

from sqlmodel import select

from turf_backend.controllers.temp_pdf_downloader import DailyPdfUpdater
from turf_backend.database import get_connection
from turf_backend.models.turf import Horse, Race
from turf_backend.routes.horses import extract_races_and_assign

logger = logging.getLogger("uvicorn.error")


def process_pdfs_and_update_db():
    logger.info("🔄 Iniciando actualización diaria de turf (background)...")
    updater = DailyPdfUpdater()

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
        msg_info = (
            f"✅ Actualización completada: {inserted_races} carreras nuevas, "
            f"{inserted_horses} caballos nuevos, {total_horses_extracted} extraídos en total."
        )
        logger.info(msg_info)
    except Exception as e:
        msg_error = f"Error en background update: {e}"
        logger.exception(msg_error)
        session.rollback()
    finally:
        try:
            session_gen.close()
        except Exception:
            pass
