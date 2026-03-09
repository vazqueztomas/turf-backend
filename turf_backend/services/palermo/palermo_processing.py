import logging
import re
import uuid

import pdfplumber

from turf_backend.models.turf import Horse

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)

# Column x-boundaries (consistent across all Palermo PDFs)
_ULTIMAS_X_START = 110.0
_NUMERO_X = 165.0
_NOMBRE_X = 188.0
_JOCKEY_X = 297.0   # Jockey starts here
_PELO_X = 383.0     # P column
_EDAD_X = 394.0     # E column
_PM_X = 403.0       # Padre-Madre starts here
_ENTRENADOR_X = 496.0

# Approximate line height in pt for converting y -> approximate line_index
_LINE_HEIGHT_PT = 13.5


def parse_pdf_horses(pdf_path: str) -> list[Horse]:
    rows = extract_horses_from_pdf(pdf_path)
    seen: set[tuple] = set()
    unique: list[Horse] = []
    for r in rows:
        key = (r.nombre, r.numero, r.page)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def _group_by_row(words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
    if not words:
        return []
    sorted_w = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows: list[list[dict]] = []
    cur = [sorted_w[0]]
    for w in sorted_w[1:]:
        if abs(w["top"] - cur[0]["top"]) <= y_tol:
            cur.append(w)
        else:
            rows.append(sorted(cur, key=lambda w: w["x0"]))
            cur = [w]
    rows.append(sorted(cur, key=lambda w: w["x0"]))
    return rows


def _parse_horse_row(
    row: list[dict],
    race_id: uuid.UUID,
    page_idx: int,
    caballeriza: str | None,
) -> "Horse | None":
    if not row:
        return None

    # Horse rows start with ultimas codes (digit+letter) or DEBUTA at x ~ [110, 165)
    ultimas_words = [
        w for w in row
        if _ULTIMAS_X_START <= w["x0"] < _NUMERO_X
        and (re.match(r"^\d[A-Z]", w["text"]) or w["text"] == "DEBUTA")
    ]
    if not ultimas_words:
        return None
    ultimas = "DEBUTA" if ultimas_words[0]["text"] == "DEBUTA" else " ".join(w["text"] for w in ultimas_words)

    # Numero: token at x in [_NUMERO_X, _NOMBRE_X)
    num_words = [w for w in row if _NUMERO_X <= w["x0"] < _NOMBRE_X]
    if not num_words:
        return None
    try:
        numero = int(num_words[0]["text"])
    except ValueError:
        return None

    # Nombre: uppercase alpha tokens at x in [_NOMBRE_X, _JOCKEY_X), excluding numerics
    nombre_words = [
        w["text"] for w in row
        if _NOMBRE_X <= w["x0"] < _JOCKEY_X
        and re.match(r"^[A-ZÁÉÍÓÚÑ'\-]", w["text"])
        and not re.match(r"^\d", w["text"])
    ]
    nombre = " ".join(nombre_words)
    if not nombre:
        return None

    # Peso: first numeric token at x in [_NOMBRE_X, _JOCKEY_X)
    # Handicap races: "56.5" + "97" — we only take the actual weight (first token)
    peso_words = [
        w for w in row
        if _NOMBRE_X <= w["x0"] < _JOCKEY_X
        and re.match(r"^\d+\.?\d*$", w["text"])
    ]
    if not peso_words:
        return None
    try:
        peso = int(float(peso_words[0]["text"]))
    except ValueError:
        return None

    # Jockey (+ Desc codes): words at x in [_JOCKEY_X, _PELO_X)
    jockey_words = [w["text"] for w in row if _JOCKEY_X <= w["x0"] < _PELO_X]
    jockey = " ".join(jockey_words)

    # Padre-Madre: words at x in [_PM_X, _ENTRENADOR_X)
    pm_words = [w["text"] for w in row if _PM_X <= w["x0"] < _ENTRENADOR_X]
    padre_madre = " ".join(pm_words)

    # Entrenador: words at x >= _ENTRENADOR_X
    ent_words = [w["text"] for w in row if w["x0"] >= _ENTRENADOR_X]
    entrenador = " ".join(ent_words)

    # Approximate line_index from y position for race header lookup
    line_idx = int(row[0]["top"] / _LINE_HEIGHT_PT)

    return Horse(
        race_id=race_id,
        page=page_idx,
        line_index=line_idx,
        ultimas=ultimas,
        numero=str(numero),
        nombre=nombre,
        peso=peso,
        jockey=jockey,
        padre_madre=padre_madre,
        entrenador=entrenador,
        raw_rest="",
        caballeriza=caballeriza or "",
    )


def extract_horses_from_pdf(pdf_path: str) -> list[Horse]:
    results: list[Horse] = []
    caballeriza: str | None = None
    last_race_number = 0
    race_id = uuid.uuid4()

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            words = page.extract_words()
            if not words:
                continue

            rows = _group_by_row(words)

            for row in rows:
                # Caballeriza row: all words at x < 110, short (1-4 words)
                # Exclude race-metadata lines like "Peso 57 kilos." or "1400 mts."
                if row and all(w["x0"] < 110 for w in row) and len(row) <= 4:
                    combined = " ".join(w["text"] for w in row)
                    if not re.search(r"(?i)\b(kilos?|mts?|metros?|handicap)\b", combined):
                        caballeriza = combined
                    continue

                horse = _parse_horse_row(row, race_id, page_idx, caballeriza)
                if horse is None:
                    continue

                # New race when numero resets (horse numbers restart from 1)
                num = int(horse.numero)
                if num < last_race_number:
                    race_id = uuid.uuid4()
                    horse.race_id = race_id
                last_race_number = num

                results.append(horse)

    return results
