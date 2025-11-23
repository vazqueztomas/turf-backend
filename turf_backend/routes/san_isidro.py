# pylint: disable=too-many-locals, duplicate-code
import logging
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from turf_backend.database import get_connection
from turf_backend.services.san_isidro.races import insert_and_create_races
from turf_backend.services.san_isidro.sanisidro_processing import parse_pdf_horses

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/san-isidro", tags=["San Isidro"])


@router.post("/upload-and-save/")
async def upload_and_save(
    file: UploadFile = File(...),
    session: Session = Depends(get_connection),
):
    if not file:
        raise HTTPException(status_code=400, detail="Se requiere un archivo PDF válido")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        horses = parse_pdf_horses(tmp_path)
    except Exception as e:
        logger.exception("Error extrayendo PDF")
        raise HTTPException(status_code=500, detail=f"Error extrayendo PDF: {e}")  # noqa: B904

    if not horses:
        return {
            "message": "No se encontró información de caballos en el PDF.",
            "inserted": 0,
        }

    total_inserted = insert_and_create_races(session, horses, tmp_path)

    session.commit()

    return {f"Insertadas: {total_inserted}"}
