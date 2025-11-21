import contextlib
import logging
import re
from datetime import datetime
from typing import Any

import pdfplumber

from turf_backend.models.turf import Horse, Race
from turf_backend.services.helper import (
    CODE_CLEAN_RE,
    DISTANCE_RE,
    HOUR_RE,
    MAIN_LINE_RE,
    PARENTS_RE,
    PREMIO_RE,
    RACE_HEADER_RE,
    REGEX_PDF_PALERMO,
    check_is_valid_race_header,
    clean_text,
    extract_header_idx,
    strip_unused_tokens_between_jockey_and_parents,
)

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)


def extract_horses_from_pdf(pdf_path: str) -> list[Horse]:
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")

            # buscamos headers de tabla en la página (varias formas)
            header_idxs = extract_header_idx(lines)

            for header_idx in header_idxs:
                # recorremos desde header_idx+1 hasta fin de sección
                for li in range(header_idx + 1, len(lines)):
                    ln = lines[li].rstrip()
                    if not ln.strip():
                        continue
                    # stop conditions: comienzo de otra sección
                    if re.match(
                        REGEX_PDF_PALERMO,
                        ln,
                    ):
                        break

                    main_line = MAIN_LINE_RE.search(ln)
                    if not main_line:
                        # si no encontramos, probablemente la info esté en varias líneas
                        # ; intentamos combinar 2 líneas y volver a probar
                        if li + 1 < len(lines):
                            combo = f"{ln} {lines[li + 1]}"
                            m2 = MAIN_LINE_RE.search(combo)
                            if m2:
                                main_line = m2
                                ln = combo
                            else:
                                continue
                        else:
                            continue

                    ultimas = clean_text(main_line.group("ultimas"))
                    num = main_line.group("num").strip()
                    nombre = clean_text(main_line.group("name"))
                    peso = main_line.group("peso").strip()

                    # resto del texto a la derecha del grupo 'peso'
                    rest = ln[main_line.end("peso") :].strip()

                    jockey = ""
                    padre_madre = ""
                    entrenador = ""

                    # 1) Si el resto contiene '-' interpretamos
                    # que hay padre-madre en la misma línea
                    nm = PARENTS_RE.search(rest)
                    if nm:
                        # madre puede llevar más tokens; tomamos el match
                        sire = nm.group("sire").strip()
                        mother = nm.group("mother").strip()
                        jockey = strip_unused_tokens_between_jockey_and_parents(rest)
                        padre_madre = (
                            (f"{clean_text(sire)} - {clean_text(mother)}")
                            .replace(jockey, "")
                            .strip()
                        )

                    else:
                        # 2) si no hay '-', el padre-madre
                        # puede estar en la siguiente línea
                        next_line = lines[li + 1] if li + 1 < len(lines) else ""
                        nm2 = PARENTS_RE.search(next_line)
                        if nm2:
                            sire = nm2.group("sire").strip()
                            mother = nm2.group("mother").strip()
                            padre_madre = f"{clean_text(sire)} - {clean_text(mother)}"
                            # jockey es lo que hay en rest (limpio códigos)
                            jockey = CODE_CLEAN_RE.sub("", rest).strip()
                            # trainer: lo que quede en next_line después del padre-madre
                            trainer_candidate = next_line[nm2.end() :].strip()
                            entrenador = CODE_CLEAN_RE.sub(
                                "", trainer_candidate
                            ).strip()
                        else:
                            jockey = ""
                            padre_madre = ""
                            entrenador = ""

                    results.append(
                        Horse(
                            page=page_idx,
                            line_index=li,
                            ultimas=ultimas,
                            numero=num,
                            nombre=nombre,
                            peso=int(peso) if peso.isdigit() else None,
                            jockey=jockey,
                            padre_madre=padre_madre,
                            entrenador=entrenador,
                            raw_rest=rest,
                        )
                    )
    return results


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
