from pathlib import Path
from typing import List, Union

import requests
from bs4 import BeautifulSoup


class PdfFileController:
    def __init__(self) -> None:
        self.save_dir = Path("files")
        self.save_dir.mkdir(
            parents=True, exist_ok=True
        ) 

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

    def download_files(self) -> str:
        url = "https://www.palermo.com.ar/es/turf/programa-oficial"

        response_text = self._make_request(url)
        anchor_tags = self._parse_anchor_tags(response_text)
        pdf_sources = [
            anchor["href"]
            for anchor in anchor_tags
            if "programa-oficial-reunion" in anchor["href"]
        ] 

        pdf_urls = []
        for source in pdf_sources:
            response_text = self._make_request(source)
            anchor_tags = self._parse_anchor_tags(response_text)
            pdf_urls.extend(
                anchor["href"]
                for anchor in anchor_tags
                if anchor["href"].endswith(".pdf")
                and anchor.text.strip()
                == "Descargar VersiÃ³n PDF"
            )

        for url in pdf_urls:
            pdf_content = self._download_pdf(url)
            pdf_filename = Path(url).name  
            file_path = self.save_dir / pdf_filename  
            self._save_file(file_path, pdf_content)

        return "PDFs downloaded successfully"
