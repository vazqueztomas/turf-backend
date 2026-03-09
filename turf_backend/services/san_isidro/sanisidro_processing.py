import logging
import re
import uuid

import pdfplumber

from turf_backend.models.turf import Horse
from turf_backend.services.san_isidro.helper import (
    HORSE_LINE_RE,
    parse_pre_peso,
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


def parse_horse_line(line: str, page_idx: int, line_idx: int, race_id: uuid.UUID) -> Horse | None:
    """
    Parse a single horse line and return a Horse object, or None if parsing fails.

    Expected format (all on one line):
      NN NOMBRE [H|M] [herraje] [FF] [STUD (CODE)] JOCKEY PESO.XXENTRENADOR[PELO] EDAD PADRE-MADRE [ULTIMAS] [CUIDA]
    """
    line = line.strip()

    # Must start with 2-digit numero
    m_num = re.match(r"^(\d{2})\s+", line)
    if not m_num:
        return None
    numero_str = m_num.group(1)
    rest = line[m_num.end():]

    # Extract nombre + sexo: uppercase tokens until we hit [HM] as a standalone token
    # Nombre can contain: uppercase letters, digits, spaces, apostrophes, parentheses (e.g. ONE THING (BRZ))
    m_name_sex = re.match(
        r"^([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9\s'\(\)\-\.]*?)\s+([HM])\s+",
        rest,
        re.UNICODE,
    )
    if not m_name_sex:
        return None
    nombre = m_name_sex.group(1).strip()
    sexo = m_name_sex.group(2)
    rest = rest[m_name_sex.end():]

    # Find peso anchor: pattern \d{2,3}\.\d{2} (e.g. 56.00, 57.00, 54.00)
    m_peso = re.search(r"(\d{2,3}\.\d{2})", rest)
    if not m_peso:
        return None

    pre_peso = rest[: m_peso.start()]
    peso_str = m_peso.group(1)
    post_peso = rest[m_peso.end():]

    # Parse pre_peso to get stud and jockey
    stud, jockey = parse_pre_peso(pre_peso)

    # Parse post_peso to get entrenador, pelo, edad, padre_madre, ultimas, cuida
    entrenador, pelo, edad, padre_madre, ultimas, cuida = parse_post_peso(post_peso)

    peso = parse_weight(peso_str)

    return Horse(
        race_id=race_id,
        page=page_idx,
        line_index=line_idx,
        numero=numero_str,
        nombre=nombre,
        peso=peso,
        jockey=jockey.strip() if jockey else "",
        padre_madre=padre_madre.strip() if padre_madre else "",
        entrenador=entrenador.strip() if entrenador else "",
        ultimas=ultimas.strip() if ultimas else "",
        caballeriza=cuida.strip() if cuida else "",
        raw_rest=post_peso.strip() if post_peso else "",
    )


def extract_horses_from_pdf(pdf_path: str) -> list[Horse]:
    results = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            # Page 0 is the cover page — skip it
            if page_idx == 0:
                continue

            text = page.extract_text() or ""
            lines = text.split("\n")

            # Each page = one race: assign a fresh race_id per page
            race_id = uuid.uuid4()

            for line_idx, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    continue

                # Quick gate: does this line look like a horse line?
                if not HORSE_LINE_RE.match(stripped):
                    continue

                horse = parse_horse_line(stripped, page_idx, line_idx, race_id)
                if horse is not None:
                    results.append(horse)
                else:
                    logger.debug(
                        "Page %d line %d matched HORSE_LINE_RE but failed full parse: %r",
                        page_idx,
                        line_idx,
                        stripped[:80],
                    )

    return results
