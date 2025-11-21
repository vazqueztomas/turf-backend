# type: ignore [circular]
# pylint: disable=too-many-locals
import logging
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session

from turf_backend.controllers.pdf_file import PdfFileController
from turf_backend.database import get_connection
from turf_backend.models.turf import AvailableLocations, Horse
from turf_backend.services.palermo_processing import extract_horses_from_pdf

logger = logging.getLogger("uvicorn.error")


router = APIRouter(prefix="/palermo", tags=["Palermo"])


@router.get("/download")
def download_files_from_external_sources() -> JSONResponse:
    pdf_file_controller = PdfFileController()
    result = pdf_file_controller.download_files_from_external_sources()
    return JSONResponse(
        content={
            "message": result,
        }
    )


@router.get("/list")
def list_available_files(location: AvailableLocations) -> list[str]:
    pdf_file_controller = PdfFileController()

    return pdf_file_controller.list_available_files(location)


@router.get("/{location}/{filename}", response_model=None)
def retrieve_file(
    location: AvailableLocations, filename: str
) -> JSONResponse | FileResponse:
    pdf_file_controller = PdfFileController()

    file_location = pdf_file_controller.retrieve_file(location, filename)

    if not file_location:
        return JSONResponse(
            content={
                "message": "File not found",
            },
            status_code=404,
        )

    return FileResponse(file_location, media_type="application/pdf", filename=filename)


@router.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...), session: Session = Depends(get_connection)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Se requiere un archivo PDF")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        rows = extract_horses_from_pdf(tmp_path)
    except Exception as e:
        logger.exception("Error extrayendo PDF")
        raise HTTPException(status_code=500, detail=f"Error extrayendo PDF: {e}")  # noqa: B904

    if not rows:
        return {
            "message": "No se encontró información de caballos en el PDF.",
            "inserted": 0,
        }

    seen = set()
    unique_rows = []

    for r in rows:
        # Definimos la clave única del caballo:
        key = (r.nombre, r.numero, r.page)
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)

    inserted = 0
    for r in unique_rows:
        try:
            h = Horse(
                numero=r.numero,
                nombre=r.nombre,
                peso=r.peso,
                jockey=r.jockey,
                ultimas=r.ultimas,
                padre_madre=r.padre_madre,
                entrenador=r.entrenador,
                page=r.page,
                line_index=r.line_index,
                raw_rest=r.raw_rest,
                caballeriza=r.caballeriza,
            )
            session.add(h)
            inserted += 1
        except Exception:
            logger.exception("Error guardando fila en DB")

    session.commit()

    return {
        "message": f"Se intentaron insertar {len(rows)} filas. "
        f"Filtradas: {len(unique_rows)} únicas. "
        f"Insertadas: {inserted}"
    }
