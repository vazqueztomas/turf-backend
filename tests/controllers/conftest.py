from unittest.mock import MagicMock, patch

import pytest

from turf_backend.controllers.pdf_file import PdfFileController


@pytest.fixture()
def pdf_sources() -> list[str]:
    return ["https://www.palermo.com.ar/es/turf/programa-oficial"]


@pytest.fixture()
def pdf_file_controller() -> PdfFileController:
    return PdfFileController()


@pytest.fixture()
def mock_make_request() -> MagicMock:
    with patch(
        "turf_backend.controllers.pdf_file.PdfFileController._make_request"
    ) as mock:
        yield mock


@pytest.fixture()
def mock_parse_anchor_tags() -> MagicMock:
    with patch(
        "turf_backend.controllers.pdf_file.PdfFileController._parse_anchor_tags"
    ) as mock:
        yield mock


@pytest.fixture()
def link_pdf_1() -> str:
    return "https://www.palermo.com.ar/es/turf/programa-oficial-reunion-1.pdf"


@pytest.fixture()
def link_pdf_2() -> str:
    return "https://www.palermo.com.ar/es/turf/programa-oficial-reunion-2.pdf"


@pytest.fixture()
def link_pdf_3() -> str:
    return "https://www.palermo.com.ar/es/turf/programa-oficial-reunion-3.pdf"


@pytest.fixture()
def mock_pdf_urls() -> str:
    return ("https://www.palermo.com.ar/es/turf/programa-oficial-reunion-1.pdf",)


@pytest.fixture()
def download_pdf_text() -> str:
    return "Descargar VersiÃ³n PDF"


@pytest.fixture()
def mock_response_html(
    link_pdf_1: str, link_pdf_2: str, link_pdf_3: 3, download_pdf_text: str
) -> str:
    return f"""
    <html>
        <body>
            <a href={link_pdf_1}>{download_pdf_text}</a>
            <a href={link_pdf_2}>{download_pdf_text}</a>
            <a href={link_pdf_3}>Otro Link</a>
        </body>
    </html>
    """


@pytest.fixture()
def mock_anchor_tags(
    link_pdf_1: str, link_pdf_2: str, link_pdf_3: str, download_pdf_text: str
) -> list[dict]:
    return [
        {
            "href": link_pdf_1,
            "text": download_pdf_text,
        },
        {
            "href": link_pdf_2,
            "text": download_pdf_text,
        },
        {
            "href": link_pdf_3,
            "text": "Otro Link",
        },
    ]
