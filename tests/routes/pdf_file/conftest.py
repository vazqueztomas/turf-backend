import pytest

from turf_backend.models.turf import AvailableLocations


@pytest.fixture()
def valid_pdf_filename() -> str:
    return "2024-12-02.pdf"


@pytest.fixture()
def invalid_pdf_filename() -> str:
    return "invalid_filename.pdf"


@pytest.fixture()
def location() -> str:
    return AvailableLocations.PALERMO.value
