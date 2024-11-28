from fastapi import APIRouter

from controllers.pdf_file import PdfFileController

router = APIRouter(prefix="/files")


@router.get("/download")
def extract_premios():
    pdf_file_controller = PdfFileController()
    return pdf_file_controller.download_files()
