import tempfile

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException

from turf_backend.controllers.pdf_file import extract_horses_from_pdf
from turf_backend.utils.date import extract_date


class TempPdfDownloader:
    BASE_URL = "https://www.palermo.com.ar/es/turf/programa-oficial"
    PDF_DOWNLOAD_TEXT = "Descargar VersiÃ³n PDF"

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
        return soup.find_all("a", href=True)

    def download_and_extract(self):
        """Descarga los PDFs de Palermo, los guarda temporalmente y extrae los datos."""
        try:
            response_text = self._make_request(self.BASE_URL)
            anchor_tags = self._parse_anchor_tags(response_text)

            pdf_sources = [
                anchor["href"]
                for anchor in anchor_tags
                if "programa-oficial-reunion" in anchor["href"]
            ]

            if not pdf_sources:
                return {"message": "No PDFs sources found", "results": []}

            pdf_urls = []
            for source in pdf_sources:
                response_text = self._make_request(source)  # type: ignore[arg-type]
                anchor_tags = self._parse_anchor_tags(response_text)
                pdf_urls.extend(
                    anchor["href"]
                    for anchor in anchor_tags
                    if anchor["href"].endswith(".pdf")
                    and anchor.text.strip() == self.PDF_DOWNLOAD_TEXT  # type: ignore
                )

            if not pdf_urls:
                return {"message": "No PDF URLs found", "results": []}

            all_results = []
            for url in pdf_urls:
                pdf_content = self._download_pdf(url)

                # Creamos un archivo temporal
                with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
                    tmp.write(pdf_content)
                    tmp.flush()

                    # Extraemos la fecha desde el contenido del PDF
                    pdf_filename = extract_date(pdf_content)

                    # Procesamos el PDF directamente desde el archivo temporal
                    horses_data = extract_horses_from_pdf(tmp.name)
                    all_results.extend(horses_data)

            return {
                "message": f"Se procesaron {len(pdf_urls)} PDFs correctamente.",
                "results": all_results,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error procesando PDFs: {e}")
