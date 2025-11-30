import re
import uuid

import pdfplumber

from turf_backend.models import Horse
from turf_backend.services.san_isidro.helper import (
    MAIN_LINE_RE,
    extract_jockey_trainer_and_parents,
    extract_races_number_name_and_weight,
    parse_weight,
)


def parse_pdf_horses(pdf_path: str) -> list[Horse]:
    rows = extract_horses_from_pdf(pdf_path)

    seen = set()
    unique_rows = []

    for r in rows:
        key = (r.nombre, r.numero, r.page)
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)

    return unique_rows


def extract_caballeriza(line: str) -> str | None:
    if re.match(r"^[A-ZÁÉÍÓÚÑ0-9\s\(\)\.\º\-]+$", line):
        tokens = line.split()
        if len(tokens) <= 3:
            return line.strip()
    return None


def is_new_race(current_number: int, previous_number: int | None) -> bool:
    return False if previous_number is None else current_number < previous_number


def merge_broken_horse_lines(lines: list[str]) -> list[str]:
    """Une líneas de caballo que vienen divididas en el PDF."""
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Si esta línea contiene la info principal del caballo
        if MAIN_LINE_RE.search(line) and i + 1 < len(lines):
            # unir con la línea siguiente (padre/madre)
            next_line = lines[i + 1].strip()
            line = f"{line} {next_line}"
            i += 1

        merged.append(line)
        i += 1

    return merged


def extract_horses_from_pdf(pdf_path: str) -> list[Horse]:
    results = []
    race_id = uuid.uuid4()
    last_number: int | None = None
    caballeriza: str | None = None

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            raw_lines = text.split("\n")

            # 1) unir líneas rotas
            lines = merge_broken_horse_lines(raw_lines)

            for line_idx, line in enumerate(lines):
                # 2) detectar caballeriza
                detected = extract_caballeriza(line)
                if detected:
                    caballeriza = detected
                    continue

                # 3) detectar línea principal del caballo
                main = MAIN_LINE_RE.search(line)
                if not main:
                    continue

                ultimas, numero, nombre, peso = extract_races_number_name_and_weight(
                    main
                )
                numero_int = int(numero)

                # 4) detectar nueva carrera
                if is_new_race(numero_int, last_number):
                    race_id = uuid.uuid4()
                    caballeriza = None  # se resetea para la nueva carrera

                last_number = numero_int

                # 5) resto del texto
                rest = line[main.end("peso") :].strip()

                jockey, padre_madre, entrenador = extract_jockey_trainer_and_parents(
                    rest
                )

                # san isidro trae floats
                peso = parse_weight(peso)
                results.append(
                    Horse(
                        race_id=race_id,
                        page=page_idx,
                        line_index=line_idx,
                        ultimas=ultimas,
                        numero=str(numero_int),
                        nombre=nombre,
                        peso=peso,
                        jockey=jockey,
                        padre_madre=padre_madre,
                        entrenador=entrenador,
                        raw_rest=rest,
                        caballeriza=caballeriza,
                    )
                )

    return results
