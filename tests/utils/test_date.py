from turf_backend.utils.date import convert_to_date, extract_date_from_pdf


def test_extract_date_from_pdf(pdf_content: bytes) -> None:
    date = extract_date_from_pdf(pdf_content)
    assert date == "2024-06-01"


def test_convert_to_date(sample_date: str) -> None:
    date = convert_to_date(sample_date)
    assert date == "2024-11-29"
