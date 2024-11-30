import re
from io import BytesIO

from pypdf import PdfReader

month_mapping = {
    "Enero": "01",
    "Febrero": "02",
    "Marzo": "03",
    "Abril": "04",
    "Mayo": "05",
    "Junio": "06",
    "Julio": "07",
    "Agosto": "08",
    "Septiembre": "09",
    "Octubre": "10",
    "Noviembre": "11",
    "Diciembre": "12",
}


def extract_date_from_pdf(pdf_content: bytes) -> str:  # pylint: disable=too-many-locals
    pdf_file = BytesIO(pdf_content)
    reader = PdfReader(pdf_file)

    text = reader.pages[0].extract_text()

    pattern = r"REUNION Nº\s*\d+\s*(?:◇\s*)?(.+?)\s*\."
    match = re.search(pattern, text)

    if match:
        date_str = match.group(1).strip()

        date_pattern = r"(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})"
        date_match = re.search(date_pattern, date_str)

        if date_match:
            day = date_match.group(1)
            month_name = date_match.group(2)
            year = date_match.group(3)

            month = month_mapping.get(month_name, "01")

            return f"{year}-{month}-{day.zfill(2)}"
        msg_error = "Date format not recognized in the PDF"
        raise ValueError(msg_error)
    msg_error = "No matching date pattern found in the PDF"
    raise ValueError(msg_error)


def convert_to_date(date_str: str) -> str:
    pattern = r"(\w+),\s*(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})"
    match = re.search(pattern, date_str)

    if match:
        day = match.group(2)
        month_name = match.group(3)
        year = match.group(4)

        # Default to January if not found
        month = month_mapping.get(month_name, "01")

        return f"{year}-{month}-{day.zfill(2)}"
    msg_error = "Invalid date format"
    raise ValueError(msg_error)
