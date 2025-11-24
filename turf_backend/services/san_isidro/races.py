from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

import pdfplumber
from sqlmodel import Session

from turf_backend.models.turf import Horse, Race
from turf_backend.services.san_isidro.helper import (
    DISTANCE_RE,
    HOUR_RE,
    PREMIO_EXTRACT_RE,
    PREMIO_LINE_RE,
    RACE_NUMBER_LINE_RE,
)


def create_race(session: Session, **kwargs) -> Race:
    """
    Crea una carrera en la tabla Race.
    kwargs permite recibir numero, nombre, distancia, etc.
    """
    race = Race(**kwargs)
    session.add(race)
    session.commit()
    session.refresh(race)
    return race


def assign_horses_to_race(session: Session, race_id: UUID, horses: list[Horse]) -> int:
    """
    Asigna un race_id a todos los caballos extraídos del PDF.
    Inserta los caballos en la DB.
    Devuelve cuántos se insertaron.
    """
    inserted = 0
    for h in horses:
        h.race_id = race_id
        session.add(h)
        inserted += 1

    session.commit()
    return inserted


def find_race_number_and_line_above(
    lines: list[str], from_index: int
) -> tuple[int, int, str | None] | None:
    """
    Search upward from from_index to find a line that contains a race number.
    Returns tuple (race_number, line_index, inline_text) where inline_text is the rest of the line after the number (if any).
    """
    for idx in range(from_index, -1, -1):
        candidate = lines[idx]
        match = RACE_NUMBER_LINE_RE.match(candidate)
        if match:
            number = int(match.group(1))
            inline_rest = match.group(2)  # may be None
            return number, idx, inline_rest
    return None


def find_hour_below(
    lines: list[str], race_line_index: int, lookahead: int = 3
) -> str | None:
    for offset in range(1, lookahead + 1):
        idx = race_line_index + offset
        if idx >= len(lines):
            break
        candidate = lines[idx]
        m = HOUR_RE.search(candidate)
        if m:
            return m.group(1)
    return None


def find_name_below_or_inline(
    lines: list[str], race_line_index: int, inline_text: str | None, lookahead: int = 8
) -> str | None:
    """
    Find the race name. Preference:
      1) If inline_text is provided and looks like a Premio/... line, extract name from it.
      2) Otherwise scan lines below for Premio/Clásico/... lines.
      3) If none found, return None to allow fallback.
    """
    if inline_text:
        inline = inline_text.strip()
        m_inline = PREMIO_EXTRACT_RE.match(inline)
        if m_inline and m_inline.group(1):
            return m_inline.group(1).strip()
        if inline.lower().startswith(("premio", "cl", "gran")):
            return inline

    for offset in range(1, lookahead + 1):
        idx = race_line_index + offset
        if idx >= len(lines):
            break
        candidate = lines[idx].strip()
        if not candidate:
            continue
        if PREMIO_LINE_RE.match(candidate):
            em = PREMIO_EXTRACT_RE.match(candidate)
            if em and em.group(1):
                return em.group(1).strip()
            return candidate
    return None


def find_distance_below(
    lines: list[str], race_line_index: int, lookahead: int = 20
) -> str | None:
    for offset in range(1, lookahead + 1):
        idx = race_line_index + offset
        if idx >= len(lines):
            break
        candidate = lines[idx]
        dm = DISTANCE_RE.search(candidate)
        if dm:
            return dm.group(1)
    return None


def parse_race_at_line(lines, from_index: int) -> dict[str, Any] | None:
    found = find_race_number_and_line_above(lines, from_index)
    if not found:
        return None
    race_number, race_line_index, inline_text = found

    hora = find_hour_below(lines, race_line_index)
    nombre = (
        find_name_below_or_inline(lines, race_line_index, inline_text)
        or f"Carrera {race_number}"
    )
    distancia = find_distance_below(lines, race_line_index)

    return {
        "numero": race_number,
        "nombre": nombre,
        "hora": hora,
        "distancia": distancia,
        "hipodromo": "San Isidro",
    }


def extract_all_races_from_lines(lines: list[str]) -> list[dict[str, Any]]:
    races = []
    for idx, raw in enumerate(lines):
        if RACE_NUMBER_LINE_RE.match(raw):
            parsed = parse_race_at_line(lines, idx)
            if parsed:
                races.append(parsed)
    return races


def insert_and_create_races(session, horses, pdf_path: str):
    races_dict = defaultdict(list)
    for h in horses:
        races_dict[h.race_id].append(h)

    total_inserted = 0

    with pdfplumber.open(pdf_path) as pdf:
        for temporary_race_id, horses_group in races_dict.items():
            first_horse = horses_group[0]

            page = pdf.pages[first_horse.page]
            lines = (page.extract_text() or "").splitlines()

            race_info = parse_race_at_line(lines, first_horse.line_index)

            if not race_info:
                race_info = {
                    "nombre": "Carrera",
                    "distancia": None,
                    "hora": None,
                    "hipodromo": "San Isidro",
                }
            race = create_race(
                session,
                hipodromo="San Isidro",
                fecha=datetime.now().strftime("%d/%m/%Y"),
                hour=race_info["hora"],
                nombre=race_info["nombre"],
                distancia=race_info["distancia"],
            )

            race.race_id = temporary_race_id
            session.flush()

            total_inserted += assign_horses_to_race(
                session, temporary_race_id, horses_group
            )
    return total_inserted
