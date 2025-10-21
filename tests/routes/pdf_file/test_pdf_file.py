from unittest.mock import patch

from fastapi.testclient import TestClient

from turf_backend.main import app

client = TestClient(app)


def test_retrieve_file_with_invalid_filename(
    location: str, invalid_pdf_filename: str
) -> None:
    response = client.get(f"/files/{location}/{invalid_pdf_filename}")
    assert response.status_code == 404


def test_list_available_files_no_files_found(location: str) -> None:
    response = client.get(f"/files/list?location={location}")
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_download_files_from_external_sources() -> None:
    with patch(
        "turf_backend.controllers.pdf_file.PdfFileController.download_files_from_external_sources",
        return_value="PDFs downloaded successfully",
    ):
        response = client.get("/files/download")

        assert response.status_code == 200
        assert response.json() == {"message": "PDFs downloaded successfully"}
