from unittest.mock import MagicMock

from turf_backend.controllers.pdf_file import PdfFileController


def test_extract_pdf_urls(  # pylint: disable=too-many-arguments, too-many-locals
    pdf_file_controller: PdfFileController,
    mock_make_request: MagicMock,
    mock_parse_anchor_tags: MagicMock,
    mock_response_html: str,
    mock_anchor_tags: MagicMock,
    pdf_sources: list[str],
    link_pdf_1: str,
    link_pdf_2: str,
) -> None:
    mock_make_request.return_value = mock_response_html

    mock_parse_anchor_tags.return_value = mock_anchor_tags

    pdf_urls = []
    for source in pdf_sources:
        response_text = pdf_file_controller._make_request(source)  # noqa: SLF001
        anchor_tags = pdf_file_controller._parse_anchor_tags(response_text)  # noqa: SLF001
        pdf_urls.extend(
            anchor["href"]
            for anchor in anchor_tags
            if anchor["href"].endswith(".pdf")
            and anchor["text"].strip() == "Descargar VersiÃ³n PDF"
        )

    assert pdf_urls == [
        link_pdf_1,
        link_pdf_2,
    ]
