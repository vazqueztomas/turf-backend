from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_retrieve_file_with_invalid_filename(
    location: str, invalid_pdf_filename: str
) -> None:
    response = client.get(f"/files/{location}/{invalid_pdf_filename}")
    assert response.status_code == 404


def test_retrieve_file_with_valid_filename(
    location: str, valid_pdf_filename: str
) -> None:
    response = client.get(f"files/{location}/{valid_pdf_filename}")
    assert response.status_code == 200


def test_list_available_files(location: str) -> None:
    response = client.get(f"/files/list?location={location}")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_download_files_from_external_sources() -> None:
    response = client.get("/files/download")
    assert response.status_code == 200
    assert response.json() == {"message": "PDFs downloaded successfully"}
