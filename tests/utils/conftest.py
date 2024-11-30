from io import BytesIO

import pytest
from fpdf import FPDF


@pytest.fixture()
def valid_pdf_content() -> bytes:
    """
    Creates a valid PDF file containing the required text for testing.
    """
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="REUNION Nº1 Sabado, 1 de Junio de 2024.", ln=True, align="L")  # type: ignore[attr-defined]
    pdf_content = pdf.output(dest="S").encode("latin1")  # type: ignore[attr-defined]
    buffer.write(pdf_content)
    buffer.seek(0)

    return buffer.getvalue()


@pytest.fixture()
def invalid_pdf_content() -> bytes:
    """
    Creates an invalid PDF file containing the required text for testing.
    """
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="REUNION Nº1 Junio de 2024.", ln=True, align="L")  # type: ignore[attr-defined]
    pdf_content = pdf.output(dest="S").encode("latin1")  # type: ignore[attr-defined]
    buffer.write(pdf_content)
    buffer.seek(0)

    return buffer.getvalue()


@pytest.fixture()
def empty_pdf_content() -> bytes:
    """
    Creates an invalid PDF file containing the required text for testing.
    """
    buffer = BytesIO()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="", ln=True, align="L")  # type: ignore[attr-defined]
    pdf_content = pdf.output(dest="S").encode("latin1")  # type: ignore[attr-defined]
    buffer.write(pdf_content)
    buffer.seek(0)

    return buffer.getvalue()


@pytest.fixture()
def sample_date() -> str:
    """
    Returns a sample date string.
    """
    return "Viernes, 29 de Noviembre de 2024"
