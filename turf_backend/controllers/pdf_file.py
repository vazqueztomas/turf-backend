from pathlib import Path
from typing import List, Optional, Union

import requests
from bs4 import BeautifulSoup

from turf_backend.models.turf import AvailableLocations
from turf_backend.utils.date import extract_date


# TODO(Mati): Download PDFs from this other location
# https://hipodromosanisidro.com/programas/
class PdfFileController:
    BASE_URL: str = "https://www.palermo.com.ar/es/turf/programa-oficial"
    PDF_DOWNLOAD_TEXT: str = "Descargar VersiÃ³n PDF"

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

    def _parse_anchor_tags(self, text: str) -> List[Union[BeautifulSoup, dict]]:
        soup = BeautifulSoup(text, "html.parser")
        return soup.find_all("a", href=True)

    def _save_file(self, file_path: Path, content: bytes) -> None:
        with file_path.open("wb") as file_:
            file_.write(content)

    def _get_pdf_links(self, page_url: str, filter_text: str) -> list[str]:
        """Get PDF links from a given page URL, filtered by text."""
        response_text = self._make_request(page_url)
        anchor_tags = self._parse_anchor_tags(response_text)
        return [
            anchor["href"]
            for anchor in anchor_tags
            if anchor["href"].endswith(".pdf") and anchor.text.strip() == filter_text  # type: ignore[union-attr]
        ]

    def _get_program_links(self, base_url: str) -> List[str]:
        """Get the program links from the base URL."""
        response_text = self._make_request(base_url)
        anchor_tags = self._parse_anchor_tags(response_text)
        return [
            anchor["href"]
            for anchor in anchor_tags
            if "programa-oficial-reunion" in anchor["href"]  # type: ignore[union-attr]
        ]

    # TODO(Mati): Try to make it more generic
    def download_files_from_external_sources(self) -> str:
        """Download PDF files from external sources."""
        pdf_sources = self._get_program_links(self.BASE_URL)

        if not pdf_sources:
            return "No PDF sources found"

        pdf_urls = []
        for source in pdf_sources:
            pdf_urls.extend(self._get_pdf_links(source, self.PDF_DOWNLOAD_TEXT))

        if not pdf_urls:
            return "No PDFs found"

        for url in pdf_urls:
            pdf_content = self._download_pdf(url)
            pdf_filename = extract_date(pdf_content)
            location_dir_path = self.save_dir / Path(AvailableLocations.PALERMO.value)
            location_dir_path.mkdir(parents=True, exist_ok=True)
            file_path = location_dir_path / f"{pdf_filename}.pdf"
            self._save_file(file_path, pdf_content)

        return "PDFs downloaded successfully"

    def list_available_files(self, turf: AvailableLocations) -> List[str]:
        pdf_dir = Path(f"files/{turf.value}")
        pdf_files = list(pdf_dir.glob("*.pdf"))

        return [file.name for file in pdf_files]

    def retrieve_file(self, turf: AvailableLocations, filename: str) -> Optional[Path]:
        pdf_dir = Path(f"files/{turf.value}/{filename}")
        if not pdf_dir.exists():
            return None

        return pdf_dir
