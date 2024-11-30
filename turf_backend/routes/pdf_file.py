from typing import Union

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from turf_backend.models.turf import AvailableLocations
from turf_backend.services.pdf_file import PdfFileService

router = APIRouter(prefix="/files")


@router.get("/download")
def download_files_from_external_sources() -> JSONResponse:
    pdf_file_service = PdfFileService()
    result = pdf_file_service.download_files_from_external_sources()
    return JSONResponse(
        content={
            "message": result,
        }
    )


@router.get("/list")
def list_available_files(location: AvailableLocations) -> list[str]:
    pdf_file_service = PdfFileService()

    return pdf_file_service.list_available_files(location)


@router.get("/{location}/{filename}", response_model=None)
def retrieve_file(
    location: AvailableLocations, filename: str
) -> Union[JSONResponse, FileResponse]:
    pdf_file_service = PdfFileService()

    file_location = pdf_file_service.retrieve_file(location, filename)

    if not file_location:
        return JSONResponse(
            content={
                "message": "File not found",
            },
            status_code=404,
        )

    return FileResponse(file_location, media_type="application/pdf", filename=filename)
