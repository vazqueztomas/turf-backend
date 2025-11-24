"""
Pytest tests for san_isidro_parser.py
Fixtures:
- lines_from_pdf: extracts lines from the uploaded PDF and provides them to tests
- sample_lines: small crafted example to test edge cases
"""

from pathlib import Path

import pdfplumber
import pytest

HERE = Path("/Users/tomasvazquez/Develops/turf-backend/tests/services/san_isidro/files")
PDF_PATH = HERE / "SI_PROGRAMA_OFICIAL_01-11-2025_(MODIFICADO)_7098.pdf"


@pytest.fixture(scope="module")
def lines_from_pdf():
    assert PDF_PATH.exists(), f"PDF not found at {PDF_PATH}"
    with pdfplumber.open(str(PDF_PATH)) as pdf:
        text = []
        for page in pdf.pages:
            text.extend((page.extract_text() or "").splitlines())
    return text


@pytest.fixture
def sample_lines():
    return [
        "Some header",
        " 1",
        "13:00 hs.",
        "Premio PINBALL WIZARD 2020",
        "Condición: Todo Caballo 5 años y más edad",
        "1200 mts. - Pista Cesped Diagonal",
        "Wishbone (SI) 5S-0S-1S-3S  1  PASO NEVADO (*)    57.0 Banegas Kevin",
        "",
        " 2",
        "13:30 hs.",
        "Premio COOL DAY 2021",
        "1600 mts. - Pista Cesped Codo",
        "Pololo Y Pa (CDIA) 1A-0S-0A-0A  1  NIÑO OSCURO    57.0 Aguirre Ramon",
    ]
