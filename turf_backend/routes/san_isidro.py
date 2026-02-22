# pylint: disable=too-many-locals, duplicate-code
import hashlib
import logging
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from turf_backend.database import get_connection
from turf_backend.models.turf import PdfImport
from turf_backend.services.san_isidro.races import insert_and_create_races
from turf_backend.services.san_isidro.sanisidro_processing import parse_pdf_horses

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
