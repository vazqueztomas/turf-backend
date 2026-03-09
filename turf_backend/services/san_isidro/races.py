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
    PISTA_RE,
    RACE_HEADER_RE,
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


def _bulk_insert_races_and_horses(
    session: Session,
    races: list[Race],
    all_horses: list[Horse],
) -> int:
    """
    Inserta todas las carreras y caballos en un solo flush + commit.
    Mucho más eficiente que hacer commit por cada carrera/grupo.
    """
    session.add_all(races)
    session.flush()
    session.add_all(all_horses)
    session.commit()
    return len(all_horses)


def parse_race_header_from_page(lines: list[str]) -> dict[str, Any]:
    """
    Parse race metadata from a page's lines.

    Line 0 contains the race header:
      "1ª - Premio CORSA KIND 2011 - 13:45 hs."
    Lines 1-4 may contain distance and pista info.

    Returns a dict with keys: numero, nombre, hora, distancia, pista, hipodromo.
    """
    numero = None
    nombre = None
    hora = None
    distancia = None
    pista = None

    # Parse line 0 — the race header
    if lines:
        header_line = lines[0].strip()
        m = RACE_HEADER_RE.match(header_line)
        if m:
            numero = int(m.group(1))
            nombre = m.group(3).strip()
            hora = m.group(4)

        # If no hora from header, try HOUR_RE on line 0
        if hora is None:
            mh = HOUR_RE.search(header_line)
            if mh:
                hora = mh.group(1)

    # Scan lines 1-4 for distance and pista
    for i in range(1, min(5, len(lines))):
        candidate = lines[i]
        if distancia is None:
            md = DISTANCE_RE.search(candidate)
            if md:
                distancia = md.group(1)
        if pista is None:
            mp = PISTA_RE.search(candidate)
            if mp:
                pista = mp.group(1).strip()

    return {
        "numero": numero,
        "nombre": nombre or "Carrera",
        "hora": hora,
        "distancia": distancia,
        "pista": pista,
        "hipodromo": "San Isidro",
    }


# ---------------------------------------------------------------------------
# Legacy helpers kept for backward compatibility with existing tests.
# These functions implement the old line-scanning approach and are no longer
# used by the main parsing pipeline.
# ---------------------------------------------------------------------------

def find_race_number_and_line_above(
    lines: list[str], from_index: int
) -> tuple[int, int, str | None] | None:
    """Search upward from from_index for a line containing a bare race number."""
    import re
    _RACE_NUMBER_LINE_RE = re.compile(r"^\s*(\d{1,2})(?:\s+(.*\S))?\s*$")
    for idx in range(from_index, -1, -1):
        match = _RACE_NUMBER_LINE_RE.match(lines[idx])
        if match:
            number = int(match.group(1))
            inline_rest = match.group(2)
            return number, idx, inline_rest
    return None


def parse_race_at_line(lines: list[str], from_index: int) -> dict[str, Any] | None:
    """Legacy: search backward for race header, then extract hora/nombre/distancia."""
    import re
    _PREMIO_EXTRACT_RE = re.compile(
        r"(?i)^(?:premio|cl[aá]sico|gran premio|g\.?\s*p\.?)[:\s\-]*(.+)$"
    )
    _PREMIO_LINE_RE = re.compile(r"(?i)^(premio|cl[aá]sico|gran premio|g\.?\s*p\.?)\b")

    found = find_race_number_and_line_above(lines, from_index)
    if not found:
        return None
    race_number, race_line_index, inline_text = found

    # hora
    hora = None
    for offset in range(1, 4):
        idx = race_line_index + offset
        if idx >= len(lines):
            break
        mh = HOUR_RE.search(lines[idx])
        if mh:
            hora = mh.group(1)
            break

    # nombre
    nombre = None
    if inline_text:
        inline = inline_text.strip()
        mi = _PREMIO_EXTRACT_RE.match(inline)
        if mi and mi.group(1):
            nombre = mi.group(1).strip()
        elif inline.lower().startswith(("premio", "cl", "gran")):
            nombre = inline
    if nombre is None:
        for offset in range(1, 9):
            idx = race_line_index + offset
            if idx >= len(lines):
                break
            candidate = lines[idx].strip()
            if not candidate:
                continue
            if _PREMIO_LINE_RE.match(candidate):
                em = _PREMIO_EXTRACT_RE.match(candidate)
                if em and em.group(1):
                    nombre = em.group(1).strip()
                else:
                    nombre = candidate
                break

    # distancia
    distancia = None
    for offset in range(1, 21):
        idx = race_line_index + offset
        if idx >= len(lines):
            break
        dm = DISTANCE_RE.search(lines[idx])
        if dm:
            distancia = dm.group(1)
            break

    return {
        "numero": race_number,
        "nombre": nombre or f"Carrera {race_number}",
        "hora": hora,
        "distancia": distancia,
        "hipodromo": "San Isidro",
    }


def extract_all_races_from_lines(lines: list[str]) -> list[dict[str, Any]]:
    """Legacy: extract all races by scanning for bare race-number lines."""
    import re
    _RACE_NUMBER_LINE_RE = re.compile(r"^\s*(\d{1,2})(?:\s+(.*\S))?\s*$")
    races = []
    for idx, raw in enumerate(lines):
        if _RACE_NUMBER_LINE_RE.match(raw):
            parsed = parse_race_at_line(lines, idx)
            if parsed:
                races.append(parsed)
    return races


# ---------------------------------------------------------------------------

def insert_and_create_races(session: Session, horses: list[Horse], pdf_path: str) -> int:
    races_dict: dict[UUID, list[Horse]] = defaultdict(list)
    for h in horses:
        races_dict[h.race_id].append(h)

    all_races: list[Race] = []
    all_horses: list[Horse] = []
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")

    with pdfplumber.open(pdf_path) as pdf:
        for temporary_race_id, horses_group in races_dict.items():
            first_horse = horses_group[0]
            page_idx = first_horse.page

            page = pdf.pages[page_idx]
            lines = (page.extract_text() or "").splitlines()

            race_info = parse_race_header_from_page(lines)

            distancia_val = None
            if race_info["distancia"] is not None:
                try:
                    distancia_val = int(race_info["distancia"])
                except (ValueError, TypeError):
                    distancia_val = None

            all_races.append(Race(
                race_id=temporary_race_id,
                hipodromo="San Isidro",
                fecha=fecha_hoy,
                hour=race_info["hora"],
                nombre=race_info["nombre"],
                distancia=distancia_val,
                numero=race_info["numero"],
            ))

            for h in horses_group:
                h.race_id = temporary_race_id
                all_horses.append(h)

    return _bulk_insert_races_and_horses(session, all_races, all_horses)
