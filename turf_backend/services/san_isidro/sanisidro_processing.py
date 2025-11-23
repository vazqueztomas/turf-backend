import logging
import re
import uuid

import pdfplumber

from turf_backend.models.turf import Horse
from turf_backend.services.san_isidro.helper import (
    MAIN_LINE_RE,
    extract_header_idx,
    extract_jockey_trainer_and_parents,
    extract_races_number_name_and_weight,
)

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)


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


def extract_horses_from_pdf(pdf_path: str) -> list[Horse]:
    results = []
    last_race_number = 0
    race_id = uuid.uuid4()

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")

            # buscamos headers de tabla en la página
            header_idxs = extract_header_idx(lines)

            for header_idx in header_idxs:
                # recorremos desde header_idx+1 hasta fin de sección
                for li in range(header_idx + 1, len(lines)):
                    ln = lines[li].rstrip()
                    if not ln.strip():
                        continue

                    # detectamos caballeriza y la extraemos
                    if re.match(r"^[A-ZÁÉÍÓÚÑ0-9\s\(\)\.\º\-]+$", ln):
                        tokens = ln.split()
                        if len(tokens) <= 3:
                            caballeriza = ln.strip()
                            continue

                    main_line = MAIN_LINE_RE.search(ln)
                    if not main_line:
                        continue

                    ultimas, numero, nombre, peso = (
                        extract_races_number_name_and_weight(main_line)
                    )

                    if int(numero) < last_race_number:
                        race_id = uuid.uuid4()

                    last_race_number = int(numero)
                    rest = ln[main_line.end("peso") :].strip()

                    jockey, padre_madre, entrenador = (
                        extract_jockey_trainer_and_parents(rest)
                    )

                    results.append(
                        Horse(
                            race_id=race_id,
                            page=page_idx,
                            line_index=li,
                            ultimas=ultimas,
                            numero=str(numero),
                            nombre=nombre,
                            peso=int(peso) if peso.isdigit() else None,
                            jockey=jockey,
                            padre_madre=padre_madre,
                            entrenador=entrenador,
                            raw_rest=rest,
                            caballeriza=caballeriza,  # type: ignore
                        )
                    )
    return results
