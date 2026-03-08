# pylint: disable=too-many-locals, duplicate-code
import hashlib
import logging
import tempfile
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlmodel import Session, select

from turf_backend.database import get_connection
from turf_backend.models.turf import PdfImport
from turf_backend.services.san_isidro.races import insert_and_create_races
from turf_backend.services.san_isidro.sanisidro_processing import parse_pdf_horses
from turf_backend.services.san_isidro import scraper

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)


def compute_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()


router = APIRouter(prefix="/san-isidro", tags=["San Isidro"])


@router.post("/upload-and-save/")
async def upload_and_save(
    file: UploadFile = File(...),
    session: Session = Depends(get_connection),
):
    if not file:
        raise HTTPException(status_code=400, detail="Se requiere un archivo PDF válido")

    file_content = await file.read()
    file_hash = compute_file_hash(file_content)

    existing_import = session.exec(
        select(PdfImport).where(PdfImport.file_hash == file_hash)
    ).first()

    if existing_import:
        raise HTTPException(
            status_code=409,
            detail=f"Este PDF ya fue importado anteriormente el {existing_import.imported_at.strftime('%d/%m/%Y a las %H:%M')}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        horses = parse_pdf_horses(tmp_path)
    except Exception as e:
        logger.exception("Error extrayendo PDF")
        raise HTTPException(status_code=500, detail=f"Error extrayendo PDF: {e}")  # noqa: B904

    if not horses:
        pdf_import = PdfImport(
            file_hash=file_hash,
            filename=file.filename,
            hipodromo="san_isidro",
        )
        session.add(pdf_import)
        session.commit()
        return {
            "message": "No se encontró información de caballos en el PDF.",
            "inserted": 0,
        }

    total_inserted = insert_and_create_races(session, horses, tmp_path)

    pdf_import = PdfImport(
        file_hash=file_hash,
        filename=file.filename,
        hipodromo="san_isidro",
    )
    session.add(pdf_import)
    session.commit()

    return {f"Insertadas: {total_inserted}"}


@router.get("/calendar/orange-days")
def get_orange_days():
    """Get all orange days from San Isidro calendar."""
    try:
        days = scraper.get_orange_days()
        return {"days": [{"fecha": fecha, "calendario_id": cid} for fecha, cid in days]}
    except Exception as e:
        logger.exception("Error fetching orange days")
        raise HTTPException(status_code=500, detail=f"Error fetching calendar: {e}")


@router.get("/calendar/resultados")
def get_resultados_days(
    start: date = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    end: date = Query(..., description="Fecha fin (YYYY-MM-DD)"),
):
    """Get all resultados days for a date range."""
    try:
        days = scraper.get_resultados_days(start, end)
        return {"days": [{"fecha": fecha, "calendario_id": cid} for fecha, cid in days]}
    except Exception as e:
        logger.exception("Error fetching resultados days")
        raise HTTPException(status_code=500, detail=f"Error fetching calendar: {e}")


@router.get("/scrape/{calendario_id}")
def scrape_race_day(calendario_id: str):
    """Scrape races from a specific day by calendario_id."""
    try:
        races_data = scraper.scrape_race_day(calendario_id)
        return {
            "fecha": races_data.fecha,
            "calendario_id": races_data.calendario_id,
            "races": [
                {
                    "numero": r.numero,
                    "nombre": r.nombre,
                    "hora": r.hora,
                    "distancia": r.distancia,
                    "pista": r.pista,
                    "condicion": r.condicion,
                    "bolsa_total": r.bolsa_total,
                    "horses": [
                        {
                            "numero": h.numero,
                            "nombre": h.nombre,
                            "sexo": h.sexo,
                            "peso": h.peso,
                            "herraje": h.herraje,
                            "stud": h.stud,
                            "jockey": h.jockey,
                            "peso_jockey": h.peso_jockey,
                            "entrenador": h.entrenador,
                            "padre_madre": h.padre_madre,
                            "ultimas": h.ultimas,
                        }
                        for h in races_data.horses_by_race.get(r.numero, [])
                    ],
                }
                for r in races_data.races
            ],
        }
    except Exception as e:
        logger.exception("Error scraping race day")
        raise HTTPException(status_code=500, detail=f"Error scraping: {e}")


@router.get("/scrape/upcoming")
def scrape_upcoming():
    """Scrape races from the next upcoming orange day."""
    try:
        races_data = scraper.scrape_upcoming_races()
        if not races_data:
            raise HTTPException(status_code=404, detail="No upcoming race days found")
        return {
            "fecha": races_data.fecha,
            "calendario_id": races_data.calendario_id,
            "races": [
                {
                    "numero": r.numero,
                    "nombre": r.nombre,
                    "hora": r.hora,
                    "distancia": r.distancia,
                    "pista": r.pista,
                    "condicion": r.condicion,
                    "bolsa_total": r.bolsa_total,
                    "horses": [
                        {
                            "numero": h.numero,
                            "nombre": h.nombre,
                            "sexo": h.sexo,
                            "peso": h.peso,
                            "herraje": h.herraje,
                            "stud": h.stud,
                            "jockey": h.jockey,
                            "peso_jockey": h.peso_jockey,
                            "entrenador": h.entrenador,
                            "padre_madre": h.padre_madre,
                            "ultimas": h.ultimas,
                        }
                        for h in races_data.horses_by_race.get(r.numero, [])
                    ],
                }
                for r in races_data.races
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error scraping upcoming races")
        raise HTTPException(status_code=500, detail=f"Error scraping: {e}")


@router.get("/pdf-links/{calendario_id}")
def get_pdf_links(calendario_id: str):
    """Get PDF download links for a specific race day."""
    try:
        links = scraper.get_pdf_links(calendario_id)
        return {
            "calendario_id": calendario_id,
            "programa_oficial": links.programa_oficial,
            "inscriptos": links.inscriptos,
            "depurados": links.depurados,
        }
    except Exception as e:
        logger.exception("Error fetching PDF links")
        raise HTTPException(status_code=500, detail=f"Error fetching PDF links: {e}")


@router.get("/download-pdf/{calendario_id}")
def download_programa_oficial(calendario_id: str):
    """Download the PROGRAMA_OFICIAL PDF for a specific race day."""
    try:
        links = scraper.get_pdf_links(calendario_id)
        if not links.programa_oficial:
            raise HTTPException(status_code=404, detail="No se encontró el PDF del programa oficial")

        pdf_content = scraper.download_pdf(links.programa_oficial)
        filename = links.programa_oficial.split("/")[-1]

        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error downloading PDF")
        raise HTTPException(status_code=500, detail=f"Error downloading PDF: {e}")


@router.post("/auto-import/{calendario_id}")
def auto_import_pdf(calendario_id: str, session: Session = Depends(get_connection)):
    """Download PROGRAMA_OFICIAL PDF and import it automatically."""
    try:
        links = scraper.get_pdf_links(calendario_id)
        if not links.programa_oficial:
            raise HTTPException(status_code=404, detail="No se encontró el PDF del programa oficial")

        pdf_content = scraper.download_pdf(links.programa_oficial)
        file_hash = compute_file_hash(pdf_content)

        existing_import = session.exec(
            select(PdfImport).where(PdfImport.file_hash == file_hash)
        ).first()

        if existing_import:
            raise HTTPException(
                status_code=409,
                detail=f"Este PDF ya fue importado anteriormente el {existing_import.imported_at.strftime('%d/%m/%Y a las %H:%M')}",
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        try:
            horses = parse_pdf_horses(tmp_path)
        except Exception as e:
            logger.exception("Error extrayendo PDF")
            raise HTTPException(status_code=500, detail=f"Error extrayendo PDF: {e}")  # noqa: B904

        filename = links.programa_oficial.split("/")[-1]

        if not horses:
            pdf_import = PdfImport(file_hash=file_hash, filename=filename, hipodromo="san_isidro")
            session.add(pdf_import)
            session.commit()
            return {"message": "No se encontró información de caballos en el PDF.", "inserted": 0}

        total_inserted = insert_and_create_races(session, horses, tmp_path)

        pdf_import = PdfImport(file_hash=file_hash, filename=filename, hipodromo="san_isidro")
        session.add(pdf_import)
        session.commit()

        return {"message": "Importado correctamente", "inserted": total_inserted, "pdf": filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error auto-importing PDF")
        raise HTTPException(status_code=500, detail=f"Error auto-importing: {e}")


def _import_day(session: Session, fecha: str, calendario_id: str) -> dict:
    """Download and import the PROGRAMA_OFICIAL PDF for a single day. Returns a result dict."""
    try:
        links = scraper.get_pdf_links(calendario_id)
        if not links.programa_oficial:
            return {"fecha": fecha, "status": "skipped", "reason": "no PDF found"}

        pdf_content = scraper.download_pdf(links.programa_oficial)
        file_hash = compute_file_hash(pdf_content)

        existing = session.exec(select(PdfImport).where(PdfImport.file_hash == file_hash)).first()
        if existing:
            return {"fecha": fecha, "status": "skipped", "reason": "already imported"}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        horses = parse_pdf_horses(tmp_path)
        filename = links.programa_oficial.split("/")[-1]

        if not horses:
            session.add(PdfImport(file_hash=file_hash, filename=filename, hipodromo="san_isidro"))
            session.commit()
            return {"fecha": fecha, "status": "imported", "inserted": 0}

        total_inserted = insert_and_create_races(session, horses, tmp_path)
        session.add(PdfImport(file_hash=file_hash, filename=filename, hipodromo="san_isidro"))
        session.commit()
        return {"fecha": fecha, "status": "imported", "inserted": total_inserted}

    except Exception as e:
        logger.exception("Error syncing %s", fecha)
        return {"fecha": fecha, "status": "error", "reason": str(e)}


@router.post("/sync-all")
def sync_all_upcoming(session: Session = Depends(get_connection)):
    """Download and import PDFs for all upcoming orange days. Called by GitHub Actions cron."""
    try:
        orange_days = scraper.get_orange_days()
    except Exception as e:
        logger.exception("Error fetching orange days")
        raise HTTPException(status_code=500, detail=f"Error fetching calendar: {e}")

    results = [_import_day(session, fecha, cid) for fecha, cid in orange_days]
    return {"results": results}


@router.post("/sync-historical")
def sync_historical(
    session: Session = Depends(get_connection),
    start: date = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    end: date = Query(..., description="Fecha fin (YYYY-MM-DD)"),
):
    """Download and import PDFs for all past race days in a date range."""
    try:
        resultados_days = scraper.get_resultados_days(start, end)
    except Exception as e:
        logger.exception("Error fetching resultados days")
        raise HTTPException(status_code=500, detail=f"Error fetching calendar: {e}")

    if not resultados_days:
        return {"results": [], "message": "No se encontraron días de resultados en ese rango"}

    results = [_import_day(session, fecha, cid) for fecha, cid in resultados_days]
    return {"results": results}
