from openai import OpenAI
from extract_text import extract_text_from_pdf


def get_race_details_from_text(text: str) -> str:
    """
    Get race details from the input text using OpenAI API.

    Args:
        text (str): The input text containing race details.

    Returns:
        str: The structured race details extracted from the text.
    """
    prompt = f"""
    Extract all the races and the horses with information that run in each race from the following text. 
    For each horse, include all relevant information such as name, number, jockey, trainer, last 5 races:

    {text}

    You must list ALL the races and the horses in text with their information in a following structured format:
    ´´´
    ### Race 2: HUMOR ACIDO - 1000 meters
        - **Horse: AIRE LIBRE**
        - Number: 1
        - Jockey: Barrueco Ramiro R
        - Trainer: Hildt German R
        - Desc.: LP
        - Weight: 56 kg
        - Pedigree: Hi Happy - Aneta
    ```
    """
    client = OpenAI()
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=1,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return e


def extract_race_details_from_pdf(pdf_path: str) -> str:
    """
    Extract race details from a specific page of a PDF file using OpenAI API.

    Args:
        pdf_path (str): The path to the PDF file.
        page_number (int): The page number to extract text from (0-indexed).
        openai_api_key (str): The OpenAI API key.

    Returns:
        str: The structured race details extracted from the PDF page.
    """

    text = extract_text_from_pdf(pdf_path)
    if text:
        return get_race_details_from_text(text)
    return ""


# Example usage
pdf_path = "/home/tomasvazquez/Develop/turf-backend/playground/example.pdf"

race_details = extract_race_details_from_pdf(pdf_path)
if race_details:
    print(race_details)
else:
    print("Failed to extract race details.")
