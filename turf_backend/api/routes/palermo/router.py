# pylint: disable=too-many-locals
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from turf_backend.api.dependencies import DatabaseSession

from .dependencies import InjectedPalermoService

router = APIRouter(prefix="/palermo", tags=["Palermo"])


@router.get("/pdf/fetch")
def fetch_files(palermo_service: InjectedPalermoService) -> str:
    return palermo_service.download_palermo_files()


@router.get("/pdf/list")
def list_available_files(palermo_service: InjectedPalermoService) -> list[str]:
    return palermo_service.list_palermo_files()


@router.post("/pdf/upload")
async def upload_pdf(
    palermo_service: InjectedPalermoService,
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

    horses = palermo_service.parse_pdf_horses(tmp_path)

    if not horses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not horses found in the PDF.",
        )

    total_inserted = palermo_service.insert_and_create_races(session, horses, tmp_path)

    return JSONResponse(
        content={
            "horses_inserted": total_inserted,
        }
    )
