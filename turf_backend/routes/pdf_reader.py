import re

from fastapi import APIRouter
from pypdf import PdfReader

router = APIRouter(prefix="/premios")


def add_unique_item(item, collection):
    if item not in collection:
        collection.append(item)


@router.get("/extract_premios")
def extract_premios():
    premios = []
    try:
        reader = PdfReader("example.pdf")
        for page in reader.pages:
            text = page.extract_text()
            premios_pattern = re.findall(r"Premio:.*", text)
            for premio in premios_pattern:
                add_unique_item(premio, premios)

    except Exception as exc:  # noqa: BLE001
        print(exc)  # noqa: T201

    return premios
