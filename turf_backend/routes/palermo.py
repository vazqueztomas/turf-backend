# type: ignore [circular]
# pylint: disable=too-many-locals
import hashlib
import logging
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session, select

from turf_backend.controllers.pdf_file import PdfFileController
from turf_backend.database import get_connection
from turf_backend.models.turf import AvailableLocations, PdfImport
from turf_backend.services.palermo.palermo_processing import (
    parse_pdf_horses,
)
from turf_backend.services.palermo.races import insert_and_create_races

logger = logging.getLogger("uvicorn.error")


def compute_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()


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
            hipodromo="palermo",
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
        hipodromo="palermo",
    )
    session.add(pdf_import)
    session.commit()

    return {f"Insertadas: {total_inserted}"}
