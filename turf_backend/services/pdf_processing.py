import contextlib
import logging
import re
from datetime import datetime
from typing import Any

import pdfplumber

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)

REGEX_PDF_PALERMO = (
    r"^(Premio:|Récord|APUESTA|APUESTAS|Bono Especial|POZOS|^\d+ª Carrera|^Premio)"
)

PARENTS_RE = re.compile(
    r"(?P<sire>[\w\(\)\'\.\s]+?)-(?P<mother>[\w\(\)\'\.\s]+)", re.UNICODE
)
CODE_CLEAN_RE = re.compile(r"\b\d+\s*[A-Z]?\b")

RACE_HEADER_RE = re.compile(r"(?P<num>\d{1,2})\s*(?:ª|º)?\s*Carrera\b", re.IGNORECASE)
DISTANCE_RE = re.compile(r"\(?\b(\d{3,4})\s*m(?:etros)?\)?", re.IGNORECASE)
HOUR_RE = re.compile(r"\b(\d{1,2}:\d{2})\s*(?:Hs\.?|hs\.?)?", re.IGNORECASE)
PREMIO_RE = re.compile(r"Premio[:\s]+[\"“”']?([^\"“”'\-]+)", re.IGNORECASE)

MAIN_LINE_RE = re.compile(
    r"(?P<ultimas>(?:\d+[A-Z0-9]{0,2}\s+){1,6})\s*"
    r"(?P<num>\d{1,2})\s+"
    r"(?P<name>[A-ZÁÉÍÓÚÑ0-9\'\.\s\-]+?)\s+"
    r"(?P<peso>\d{1,2})",
    re.UNICODE,
)

BASE_URL = "https://www.palermo.com.ar/es/turf/programa-oficial"
PDF_DOWNLOAD_TEXT = "Descargar VersiÃ³n PDF"


def _clean_text(x: str) -> str:
    if not x:
        return ""
    return re.sub(r"\s{2,}", " ", x).strip()


def extract_horses_from_pdf(pdf_path: str):
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")

            # buscamos headers de tabla en la página (varias formas)
            header_idxs = [
                i
                for i, ln in enumerate(lines)
                if re.search(r"Caballeriza.*5\s+Ultimas", ln, re.IGNORECASE)
            ]
            if not header_idxs:
                # no siempre aparece; otra heurística: si línea
                # contiene "Caballeriza" o "Caballeriza 5 Ultimas"
                header_idxs = [
                    i
                    for i, ln in enumerate(lines)
                    if "Caballeriza" in ln and "Ultimas" in ln
                ]

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

                    m = MAIN_LINE_RE.search(ln)
                    if not m:
                        # si no encontramos, probablemente la info esté en varias líneas
                        # ; intentamos combinar 2 líneas y volver a probar
                        if li + 1 < len(lines):
                            combo = f"{ln} {lines[li + 1]}"
                            m2 = MAIN_LINE_RE.search(combo)
                            if m2:
                                m = m2
                                ln = combo
                            else:
                                continue
                        else:
                            continue

                    ultimas = _clean_text(m.group("ultimas"))
                    num = m.group("num").strip()
                    nombre = _clean_text(m.group("name"))
                    peso = m.group("peso").strip()

                    # resto del texto a la derecha del grupo 'peso'
                    rest = ln[m.end("peso") :].strip()

                    jockey = ""
                    padre_madre = ""
                    entrenador = ""

                    # 1) Si el resto contiene '-' interpretamos
                    # que hay padre-madre en la misma línea
                    nm = PARENTS_RE.search(rest)
                    if nm:
                        # madre puede llevar más tokens; tomamos el match
                        # pero luego aplicamos heurísticas al resto
                        sire = nm.group("sire").strip()
                        mother = nm.group("mother").strip()
                        padre_madre = f"{_clean_text(sire)} - {_clean_text(mother)}"
                        # jockey: lo que hay antes de nm.start()
                        jockey_candidate = _clean_text(rest[: nm.start()])
                        jockey_candidate = CODE_CLEAN_RE.sub(
                            "", jockey_candidate
                        ).strip()
                        jockey = jockey_candidate
                        # trainer: texto posterior al match
                        trainer_candidate = rest[nm.end() :].strip()
                        trainer_candidate = CODE_CLEAN_RE.sub(
                            "", trainer_candidate
                        ).strip()
                        entrenador = _clean_text(trainer_candidate)
                    else:
                        # 2) si no hay '-', el padre-madre
                        # puede estar en la siguiente línea
                        next_line = lines[li + 1] if li + 1 < len(lines) else ""
                        nm2 = PARENTS_RE.search(next_line)
                        if nm2:
                            sire = nm2.group("sire").strip()
                            mother = nm2.group("mother").strip()
                            padre_madre = f"{_clean_text(sire)} - {_clean_text(mother)}"
                            # jockey es lo que hay en rest (limpio códigos)
                            jockey = CODE_CLEAN_RE.sub("", rest).strip()
                            # trainer: lo que quede en next_line después del padre-madre
                            trainer_candidate = next_line[nm2.end() :].strip()
                            entrenador = CODE_CLEAN_RE.sub(
                                "", trainer_candidate
                            ).strip()
                        else:
                            # 3) fallback: intentar detectar jockey
                            # name en rest (palabras con mayúscula inicial)
                            # quitamos códigos y números y tomamos
                            # las primeras 3-4 palabras como posible jockey
                            candidate = CODE_CLEAN_RE.sub("", rest).strip()
                            words = candidate.split()
                            if words:
                                # heurística: jockey suele ser 1-3 palabras.
                                # Tomamos hasta 3 palabras que empiecen con mayúsc.
                                jockey_parts = []
                                for w in words[:6]:
                                    if re.match(
                                        r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ\.]+$", w
                                    ) or re.match(
                                        r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ\.\-]+$", w
                                    ):
                                        jockey_parts.append(w)
                                    else:
                                        # si encontramos token tipo
                                        # 'J' o 'R' también lo incorporamos
                                        if re.match(r"^[A-Z]\.?$", w):
                                            jockey_parts.append(w)
                                        else:
                                            # stop if we see something that is
                                            # very unlikely a name (like '4', 'Z', '5')
                                            pass
                                    if len(jockey_parts) >= 3:
                                        break
                                jockey = " ".join(jockey_parts).strip()
                                padre_madre = ""  # desconocido
                                entrenador = ""
                            else:
                                jockey = ""
                                padre_madre = ""
                                entrenador = ""

                    results.append({
                        "page": page_idx,
                        "line_index": li,
                        "ultimas": ultimas,
                        "num": num,
                        "nombre": nombre,
                        "peso": int(peso) if peso.isdigit() else None,
                        "jockey": jockey,
                        "padre_madre": padre_madre,
                        "entrenador": entrenador,
                        "raw_rest": rest,
                    })
    return results


def extract_races_and_assign(pdf_path: str) -> dict[str, Any]:
    """
    Extrae carreras y les asigna caballos desde el PDF del hipódromo Palermo.
    Devuelve un diccionario con las carreras, caballos asociados y resumen.
    """
    horses = extract_horses_from_pdf(pdf_path)
    logger.info(f"Caballos detectados: {len(horses)}")  # noqa: G004

    races: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")

            for i, line in enumerate(lines):
                # unimos línea actual con la siguiente (casos donde está partida)
                line_joined = f"{line} {lines[i + 1]}" if i + 1 < len(lines) else line

                # detectar encabezado de carrera
                m = RACE_HEADER_RE.search(line_joined)
                if not m:
                    continue

                if not check_is_valid_race_header(lines, i, line_joined):
                    continue

                num = int(m.group("num"))

                dist = None
                if dm := DISTANCE_RE.search(line_joined):
                    with contextlib.suppress(ValueError):
                        dist = int(dm.group(1))

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
                                str(DISTANCE_RE.search(candidate).group(1))
                            )[0]
                            if before_dist.strip():
                                nombre = before_dist.strip().strip("-—:")
                                break

                    if not nombre and DISTANCE_RE.search(line_joined):
                        dist_match = DISTANCE_RE.search(line_joined)
                        before_dist = line_joined[: dist_match.start()].strip()
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

                races.append({
                    "page": page_idx,
                    "header_line_index": i,
                    "num": num,
                    "distancia": dist,
                    "hora": hour,
                    "nombre": nombre,
                    "horses": [],
                    "assigned_set": set(),
                })

    # Ordenar por posición en el PDF
    races.sort(key=lambda r: (r["page"], r["header_line_index"]))  # noqa: FURB118

    # Asignar caballos a la carrera más cercana
    for h in horses:
        candidates = []
        for r in races:
            score = abs(r["page"] - h["page"]) * 1000 + abs(
                r["header_line_index"] - h["line_index"]
            )
            candidates.append((score, r))
        if not candidates:
            continue

        candidates.sort(key=lambda x: x[0])  # noqa: FURB118
        best_score, best_r = candidates[0]

        # ignorar asignaciones demasiado lejanas
        if best_score > 5000:
            continue

        key = ((h.get("nombre") or "").strip().upper(), str(h.get("num")))
        if key in best_r["assigned_set"]:
            continue

        best_r["assigned_set"].add(key)
        h_copy = dict(h)
        h_copy["assigned_race_num"] = best_r["num"]
        best_r["horses"].append(h_copy)

    total_horses = sum(len(r["horses"]) for r in races)
    summary = {"races": len(races), "horses": total_horses}

    return {
        "generated_at": datetime.now(),
        "races": races,
        "summary": summary,
    }


def check_is_valid_race_header(lines: list[str], idx: int, joined: str) -> bool:
    window_text = joined
    max_ahead = 3
    for j in range(1, max_ahead + 1):
        if idx + j < len(lines):
            window_text += " " + lines[idx + j]

    if (
        DISTANCE_RE.search(window_text)
        or HOUR_RE.search(window_text)
        or PREMIO_RE.search(window_text)
    ):
        return True

    for j in range(6):
        if idx + j < len(lines) and "Caballeriza" in lines[idx + j]:
            return True

    return False
