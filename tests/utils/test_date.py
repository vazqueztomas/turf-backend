import pytest

from turf_backend.utils.date import convert_to_date, extract_date_from_pdf


def test_extract_date_from_pdf(valid_pdf_content: bytes) -> None:
    date = extract_date_from_pdf(valid_pdf_content)
    assert date == "2024-06-01"


def test_extract_date_from_pdf_invalid(invalid_pdf_content: bytes) -> None:
    with pytest.raises(ValueError, match="Date format not recognized in the PDF"):
        extract_date_from_pdf(invalid_pdf_content)


def test_extract_date_from_pdf_empty(empty_pdf_content: bytes) -> None:
    with pytest.raises(ValueError, match="No matching date pattern found in the PDF"):
        extract_date_from_pdf(empty_pdf_content)


def test_convert_to_date(sample_date: str) -> None:
    date = convert_to_date(sample_date)
    assert date == "2024-11-29"


def test_convert_to_date_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid date format"):
        convert_to_date("Invalid date string")
