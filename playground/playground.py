import pdfplumber


class Race:
    def __init__(self, name, hour, details):
        self.name = name
        self.hour = hour
        self.details = details

    def __repr__(self) -> str:
        return f"Carrera(nombre={self.name}, hora={self.hour}, detalles={self.details})"


def organize_races(data):
    races = []
    current_race = []
    name = ""
    time = ""

    for sublist in data:
        for item in sublist:
            if isinstance(item, list) and item and item[0] and "Carrera" in item[0]:
                if current_race:
                    # Remove redundant, empty, and None elements from the current race
                    current_race = [
                        [elem for elem in entry if elem is not None and elem != ""]
                        for entry in current_race
                        if any(entry)
                    ]
                    races.append(Race(name, time, current_race))
                name, time = item
                current_race = [item]
            elif any(isinstance(i, str) and "Caballeriza" in i for i in item) or any(
                isinstance(i, str) and i for i in item
            ):
                current_race.append(item)

    # Add the last race
    if current_race:
        current_race = [
            [elem for elem in entry if elem is not None and elem != ""]
            for entry in current_race
            if any(entry)
        ]
        races.append(Race(name, time, current_race))

    return races


def extract_data_from_pdf():
    with pdfplumber.open("example.pdf") as pdf:
        first_page = pdf.pages[1]
        tables = first_page.extract_tables()

        print(organize_races(tables)[0])  # noqa: T201


# Ejemplo de uso
pdf_path = "example.pdf"
example = extract_data_from_pdf(pdf_path)
