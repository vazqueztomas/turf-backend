# pylint: disable=duplicate-code
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from turf_backend.api.dependencies import DatabaseSession
from turf_backend.services.san_isidro.races import insert_and_create_races
from turf_backend.services.san_isidro.sanisidro_processing import parse_pdf_horses

router = APIRouter(prefix="/san-isidro", tags=["San Isidro"])


@router.post("/pdf/upload")
async def upload_pdf(
    session: DatabaseSession,
    file: UploadFile = File(...),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is no file in the request",
        )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    horses = parse_pdf_horses(tmp_path)
    if not horses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not horses found in the PDF.",
        )

    total_inserted = insert_and_create_races(session, horses, tmp_path)

    session.commit()

    return JSONResponse(
        content={
            "horses_inserted": total_inserted,
        }
    )
