from pathlib import Path
from typing import List, Optional, Union

import requests
from bs4 import BeautifulSoup

from models.turf import AvailableLocations
from utils.date import extract_date


# TODO: Download PDFs from this other location
# https://hipodromosanisidro.com/programas/
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

    def _parse_anchor_tags(self, text: str) -> List[Union[BeautifulSoup, dict]]:
        soup = BeautifulSoup(text, "html.parser")
        return soup.find_all("a", href=True)

    def _save_file(self, file_path: Path, content: bytes) -> None:
        with file_path.open("wb") as file_:
            file_.write(content)

    # TODO: Refactor this and try to make it more generic
    def download_files_from_external_sources(self) -> str:
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
            response_text = self._make_request(source) # type: ignore[arg-type] 
            anchor_tags = self._parse_anchor_tags(response_text)
            pdf_urls.extend(
                anchor["href"]
                for anchor in anchor_tags
                if anchor["href"].endswith(".pdf") # type: ignore[index]
                and anchor.text.strip() == "Descargar VersiÃ³n PDF" # type: ignore[index]
            )

        for url in pdf_urls:
            pdf_content = self._download_pdf(url)
            pdf_filename = extract_date(pdf_content)
            location_dir_path = self.save_dir / Path("palermo")
            location_dir_path.mkdir(parents=True,exist_ok=True)  
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
            return 
        
        return pdf_dir
