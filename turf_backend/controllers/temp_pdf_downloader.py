import logging

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException

logger = logging.getLogger()


class DailyPdfUpdater:
    BASE_URL = "https://www.palermo.com.ar/es/turf/programa-oficial"
    PDF_DOWNLOAD_TEXT = "Descargar VersiÃ³n PDF"

    def _make_request(self, url: str) -> str:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.text

    def _download_pdf(self, url: str) -> bytes:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content

    def _parse_anchor_tags(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        return soup.find_all("a", href=True)

    def fetch_latest_pdfs(self) -> list[bytes]:
        try:
            response_text = self._make_request(self.BASE_URL)
            anchors = self._parse_anchor_tags(response_text)

            pdf_sources = [
                a["href"] for a in anchors if "programa-oficial-reunion" in a["href"]
            ]
            if not pdf_sources:
                logger.info("No se encontraron fuentes de PDFs.")
                return []

            pdf_urls = []
            for source in pdf_sources:
                html = self._make_request(source)  # type: ignore
                anchors = self._parse_anchor_tags(html)
                pdf_urls.extend(
                    a["href"]
                    for a in anchors
                    if a["href"].endswith(".pdf")  # type: ignore
                    and a.text.strip() == self.PDF_DOWNLOAD_TEXT
                )

            pdf_bytes = []
            for url in pdf_urls:
                logger.info(f"Descargando PDF: {url}")  # noqa: G004
                pdf_bytes.append(self._download_pdf(url))

            logger.info(f"Total PDFs descargados: {len(pdf_bytes)}")  # noqa: G004
        except Exception as e:
            msg_error = f"Error descargando PDFs: {e}"
            logger.exception(msg_error)
            raise HTTPException(status_code=500, detail=msg_error)  # noqa: B904
        return pdf_bytes
