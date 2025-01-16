from pypdf import PdfReader


from typing import Union


def extract_text_from_pdf(pdf_path: str) -> Union[str, list[str]]:
    """
    Extract text from a specific page of a PDF file.

    Args:
        pdf_path (str): The path to the PDF file.
        page_number (int): The page number to extract text from (0-indexed).

    Returns:
        str: The extracted text from the specified page.
    """
    try:
        reader = PdfReader(pdf_path)
        return [page.extract_text() for page in reader.pages]
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
