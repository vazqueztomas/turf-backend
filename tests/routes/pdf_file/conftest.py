import pytest


@pytest.fixture()
def valid_pdf_filename() -> str:
    return "1212__a6e4f41397df62b45b5037d1f96df65c.pdf"


@pytest.fixture()
def invalid_pdf_filename() -> str:
    return "invalid_filename.pdf"


@pytest.fixture()
def location() -> str:
    return "palermo"
