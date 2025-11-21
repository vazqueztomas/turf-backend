import contextlib
import logging
import re
import uuid
from datetime import datetime
from typing import Any

import pdfplumber

from turf_backend.models.turf import Horse, Race
from turf_backend.services.helper import (
    DISTANCE_RE,
    HOUR_RE,
    MAIN_LINE_RE,
    PREMIO_RE,
    RACE_HEADER_RE,
    check_is_valid_race_header,
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

                    if detect_new_race(ln):
                        race_id = uuid.uuid4()
                        caballeriza = None
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

                    if detect_new_race(numero):
                        race_id = uuid.uuid4()

                    # resto del texto a la derecha del grupo 'peso'
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
                            numero=numero,
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


def detect_new_race(horse_number: str) -> bool:
    """
    Detecta si una línea marca el inicio de una nueva carrera.
    """
    return horse_number == 1


def extract_races_and_assign(pdf_path: str) -> dict[str, Any]:
    horses = extract_horses_from_pdf(pdf_path)
    logger.info(f"Caballos detectados: {len(horses)}")  # noqa: G004

    races = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):  # noqa
            text = page.extract_text() or ""
            lines = text.split("\n")

            for i, line in enumerate(lines):
                # unimos línea actual con la siguiente (casos donde está partida)
                line_joined = f"{line} {lines[i + 1]}" if i + 1 < len(lines) else line

                # detectar encabezado de carrera
                main_line = RACE_HEADER_RE.search(line_joined)
                if not main_line:
                    continue

                if not check_is_valid_race_header(lines, i, line_joined):
                    continue

                distance = None
                if dm := DISTANCE_RE.search(line_joined):
                    with contextlib.suppress(ValueError):
                        distance = int(dm.group(1))

                hour = None
                if hm := HOUR_RE.search(line_joined):
                    hour = hm.group(1)

                nombre = None
                if pm := PREMIO_RE.search(line_joined):
                    nombre = pm.group(1).strip()
                else:
                    lookahead_limit = 5
                    for j in range(1, lookahead_limit + 1):
                        if i + j >= len(lines):
                            break
                        candidate = lines[i + j]
                        if RACE_HEADER_RE.search(candidate):  # No cruzar otra carrera
                            break
                        if "Premio" in candidate or "premio" in candidate.lower():
                            nombre = re.sub(r"(?i)Premio[:\s]+", "", candidate).strip()
                            break
                        if not nombre and DISTANCE_RE.search(candidate):
                            before_dist = candidate.split(
                                str(DISTANCE_RE.search(candidate).group(1))  # type: ignore
                            )[0]
                            if before_dist.strip():
                                nombre = before_dist.strip().strip("-—:")
                                break

                    if not nombre and DISTANCE_RE.search(line_joined):
                        dist_match = DISTANCE_RE.search(line_joined)
                        before_dist = line_joined[: dist_match.start()].strip()  # type: ignore
                        # Evitar incluir "Carrera" o número
                        before_dist = re.sub(
                            r"(?i)\b\d{1,2}\s*(?:ª|º)?\s*Carrera\b", "", before_dist
                        ).strip()
                        if before_dist:
                            nombre = before_dist.strip("-—: ")

                    if not nombre:
                        quoted = re.search(r"[\"“](.*?)[\"”]", line_joined)
                        if quoted:
                            nombre = quoted.group(1).strip()

                races.append(
                    Race(
                        horses=[],
                        nombre=nombre,
                        distancia=distance,
                        hipodromo="Palermo",
                        fecha=datetime.now().strftime(
                            "%Y-%m-%d"
                        ),  # cambiar esto cuando haga extractor de fecha de pdf,
                        hour=hour,
                    )
                )

    # Ordenar por posición en el PDF
    races.sort(key=lambda race: (race.page, race.header_line_index))

    total_horses = sum(len(race["horses"]) for race in races)
    summary = {"races": len(races), "horses": total_horses}

    return {
        "races": races,
        "summary": summary,
    }
