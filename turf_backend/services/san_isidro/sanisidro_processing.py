import logging
import re
import uuid

import pdfplumber

from turf_backend.models.turf import Horse
from turf_backend.services.san_isidro.helper import (
    parse_post_peso,
    parse_weight,
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


# ---------------------------------------------------------------------------
# Column-based word extraction
# ---------------------------------------------------------------------------

def _get_col_bounds(words: list[dict]) -> dict:
    """Derive column x-boundaries from the header row words."""
    bounds = {}
    for w in words:
        t = w["text"]
        x = w["x0"]
        if t == "JOCKEY":
            # Jockey content starts ~48px left of the header label
            bounds["jockey"] = x - 48
        elif t == "KG":
            # KG content starts ~5px left of the header label
            bounds["kg"] = x - 5
        elif t == "L.CUIDA":
            bounds["cuida"] = x

    bounds.setdefault("jockey", 315)
    bounds.setdefault("kg", 422)
    bounds.setdefault("cuida", 734)
    return bounds


def _group_by_row(words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
    """Group words into rows by their top (y) coordinate."""
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
    jockey_x: float,
    kg_x: float,
) -> Horse | None:
    """Parse a single horse from a row of words with x positions."""
    if not row:
        return None

    # Must start with a 2-digit horse numero
    if not re.match(r"^\d{2}$", row[0]["text"]):
        return None
    numero = row[0]["text"]

    # NOMBRE: words between x≈59 and SEXO column (x≈147)
    nombre_words = [
        w["text"] for w in row
        if 55 <= w["x0"] < 150
        and w["text"] not in ("H", "M")
        and not re.match(r"^\d+$", w["text"])
    ]
    nombre = " ".join(nombre_words)
    if not nombre:
        return None

    # STUD: words between herraje area and jockey column
    stud_words = [
        w["text"]
        for w in row
        if 162 <= w["x0"] < jockey_x
        and not (re.match(r"^\d$|^FF$", w["text"]) and w["x0"] < 250)
        and w["text"] not in ("H", "M")
    ]

    # JOCKEY + KG: find the peso pattern scanning words from jockey_x onwards
    # Handles both "56.00ALMADA" and concatenated "FRANCISCO55.00MAYANSKY"
    post_jockey = [w for w in row if w["x0"] >= jockey_x]
    jockey_parts: list[str] = []
    post_peso_parts: list[str] = []
    peso = None

    for i, w in enumerate(post_jockey):
        text = w["text"]
        pm = re.search(r"(\d{2,3}\.\d{2})", text)
        if pm:
            pre = text[: pm.start()]
            peso = parse_weight(pm.group(1))
            post = text[pm.end():]
            if pre:
                jockey_parts.append(pre)
            post_peso_parts = [post] + [ww["text"] for ww in post_jockey[i + 1:]]
            break
        jockey_parts.append(text)

    if peso is None:
        return None

    jockey = " ".join(jockey_parts)
    post_text = " ".join(post_peso_parts).strip()

    entrenador, _pelo, _edad, padre_madre, ultimas, cuida = parse_post_peso(post_text)

    line_idx = int(row[0]["top"])

    return Horse(
        race_id=race_id,
        page=page_idx,
        line_index=line_idx,
        numero=numero,
        nombre=nombre,
        peso=peso,
        jockey=jockey.strip(),
        padre_madre=padre_madre.strip(),
        entrenador=entrenador.strip(),
        ultimas=ultimas.strip(),
        caballeriza=cuida.strip(),
        raw_rest=post_text,
    )


def extract_horses_from_pdf(pdf_path: str) -> list[Horse]:
    results = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            # Page 0 is the cover — skip it
            if page_idx == 0:
                continue

            words = page.extract_words()
            if not words:
                continue

            col = _get_col_bounds(words)
            rows = _group_by_row(words)

            race_id = uuid.uuid4()

            for row in rows:
                horse = _parse_horse_row(
                    row,
                    race_id,
                    page_idx,
                    jockey_x=col["jockey"],
                    kg_x=col["kg"],
                )
                if horse is not None:
                    results.append(horse)

    return results
