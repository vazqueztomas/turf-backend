from typing import Optional

from fastapi import APIRouter
from starlette.responses import FileResponse, JSONResponse

from controllers.pdf_file import PdfFileController
from models.turf import AvailableLocations

router = APIRouter(prefix="/files")


@router.get("/download")
def download_files_from_external_sources() -> JSONResponse:
    pdf_file_controller = PdfFileController()
    result = pdf_file_controller.download_files_from_external_sources()
    return JSONResponse(content={
        "message": result,
    })


@router.get("/list")
async def list_available_files(location: AvailableLocations) -> list[str]:
    pdf_file_controller = PdfFileController()

    return pdf_file_controller.list_available_files(location)


@router.get("/{location}/{filename}", response_model=None)
async def retrieve_file(location: AvailableLocations, filename: str) -> JSONResponse | FileResponse:
    pdf_file_controller = PdfFileController()

    file_location = pdf_file_controller.retrieve_file(location, filename)

    if not file_location:
        return JSONResponse(content={
            "message": "File not found",
        }, status_code=404)

    return FileResponse(file_location, media_type='application/pdf', filename=filename)
