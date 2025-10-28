import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from turf_backend.models.turf import AvailableLocations
from turf_backend.utils.date import extract_date

logger = logging.getLogger("extractor")
logger.setLevel(logging.DEBUG)


# TODO(Mati): Download PDFs from this other location
# https://hipodromosanisidro.com/programas/


# TODO (TOTO): Sacar esto, solo se utiliza dentro del
# router de los pdf ( no esta usandose actualmente)
class PdfFileController:
    def __init__(self) -> None:
        self.save_dir = Path("files")
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _make_request(self, url: str) -> str:
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def _download_pdf(self, url: str) -> bytes:
        response = requests.get(url)
        response.raise_for_status()
        return response.content

    def _parse_anchor_tags(self, text: str) -> list[BeautifulSoup | dict]:
        soup = BeautifulSoup(text, "html.parser")
        return soup.find_all("a", href=True)  # type: ignore

    def _save_file(self, file_path: Path, content: bytes) -> None:
        with file_path.open("wb") as file_:
            file_.write(content)

    # TODO(mati): Refactor this and try to make it more generic
    def download_files_from_external_sources(self) -> str:  # pylint: disable=too-many-locals
        url = "https://www.palermo.com.ar/es/turf/programa-oficial"

        response_text = self._make_request(url)
        anchor_tags = self._parse_anchor_tags(response_text)
        pdf_sources = [
            anchor["href"]
            for anchor in anchor_tags
            if "programa-oficial-reunion" in anchor["href"]
        ]

        if not pdf_sources:
            return "No PDFs sources found"

        pdf_urls = []
        for source in pdf_sources:
            response_text = self._make_request(source)  # type: ignore[arg-type]
            anchor_tags = self._parse_anchor_tags(response_text)
            pdf_urls.extend(
                anchor["href"]
                for anchor in anchor_tags
                if anchor["href"].endswith(".pdf")  # type: ignore
                and anchor.text.strip() == self.PDF_DOWNLOAD_TEXT  # type: ignore
            )

        for url in pdf_urls:
            pdf_content = self._download_pdf(url)
            pdf_filename = extract_date(pdf_content)
            location_dir_path = self.save_dir / Path(AvailableLocations.PALERMO.value)
            location_dir_path.mkdir(parents=True, exist_ok=True)
            file_path = location_dir_path / f"{pdf_filename}.pdf"
            self._save_file(file_path, pdf_content)

        return "PDFs downloaded successfully"

    def list_available_files(self, turf: AvailableLocations) -> list[str]:
        pdf_dir = Path(f"files/{turf.value}")
        pdf_files = list(pdf_dir.glob("*.pdf"))

        return [file.name for file in pdf_files]

    def retrieve_file(self, turf: AvailableLocations, filename: str) -> Path | None:
        pdf_dir = Path(f"files/{turf.value}/{filename}")
        if not pdf_dir.exists():
            return None

        return pdf_dir


# Heurística: buscamos la línea que contiene "
# "Caballeriza" + "5 Ultimas" y a partir de ahí
# interpretamos líneas que contienen: <ultimas> <num> <NOMBRE (MAYUS)> <peso> <resto...>
# luego intentamos sacar jockey / padre-madre / entrenador
# con varias reglas de fallback.
