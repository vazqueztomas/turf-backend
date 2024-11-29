from typing import Optional

from fastapi import APIRouter
from starlette.responses import FileResponse

from controllers.pdf_file import PdfFileController
from models.turf import AvailableLocations

router = APIRouter(prefix="/files")


@router.get("/download")
def extract_premios():
    pdf_file_controller = PdfFileController()
    return pdf_file_controller.download_files()


        
@router.get("/list")
async def list_pdfs(location: AvailableLocations):
    pdf_file_controller = PdfFileController()

    return pdf_file_controller.list_all_pdfs(location)