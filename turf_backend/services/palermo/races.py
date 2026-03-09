# pylint: disable=too-many-locals
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

import pdfplumber
from sqlmodel import Session

from turf_backend.models.turf import Horse, Race
from turf_backend.services.palermo.helper import (
    DISTANCE_RE,
    HOUR_RE,
    NOMBRE_CON_DISTANCIA_RE,
    PREMIO_RE,
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


# Encuentra la línea donde está la carrera
def find_race_header(lines, start_index):
    for idx in range(start_index, -1, -1):
        if RACE_HEADER_RE.search(lines[idx]):
            return idx
    return None


def extract_race_block(lines, header_index, radius=4):
    start = max(0, header_index - radius)
    end = min(len(lines), header_index + radius + 1)
    return lines[start:end]


def _extract_race_info_from_lines(
    lines: list[str], line_index: int
) -> dict[str, Any] | None:
    """Extract race info from already-extracted page lines (no file I/O)."""
    header_idx = None
    for idx in range(line_index, -1, -1):
        if RACE_HEADER_RE.search(lines[idx]):
            header_idx = idx
            break

    if header_idx is None:
        return None

    block = extract_race_block(lines, header_idx, radius=4)
    nombre, hora, distancia = extract_name_distance_hour(block)

    if not nombre:
        header = RACE_HEADER_RE.search(lines[header_idx])
        numero = header.group("num")
        nombre = f"Carrera {numero}"

    return {
        "nombre": nombre,
        "distancia": distancia,
        "hora": hora,
        "hipodromo": "Palermo",
    }


def extract_race_information(
    pdf_path: str, horses_group: list[Horse]
) -> dict[str, Any] | None:
    horse = horses_group[0]

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[horse.page]  # type: ignore
        lines = (page.extract_text() or "").split("\n")

    return _extract_race_info_from_lines(lines, horse.line_index)  # type: ignore


def extract_name_distance_hour(block):
    nombre = None
    hora = None
    distancia = None

    for line in block:
        # ✔ Extraer nombre
        m = PREMIO_RE.match(line.strip())
        if m and not nombre:
            nombre = m.group(1).strip()

        m2 = NOMBRE_CON_DISTANCIA_RE.match(line.strip())
        if m2 and not nombre:
            nombre = m2.group("nombre").strip()
        # ✔ Extraer hora
        hm = HOUR_RE.search(line)
        if hm and not hora:
            hora = hm.group(1)

        # ✔ Extraer distancia
        dm = DISTANCE_RE.search(line)
        if dm and not distancia:
            distancia = int(dm.group(1))
    return nombre, hora, distancia


def insert_and_create_races(session, horses, pdf_path: str):
    races_dict = defaultdict(list)
    for h in horses:
        races_dict[h.race_id].append(h)

    all_races: list[Race] = []
    all_horses: list[Horse] = []
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")

    # Cache de líneas por página para no re-parsear el mismo texto
    page_lines_cache: dict[int, list[str]] = {}

    with pdfplumber.open(pdf_path) as pdf:
        for rid, horses_group in races_dict.items():
            horse = horses_group[0]
            page_idx = horse.page  # type: ignore

            if page_idx not in page_lines_cache:
                page_lines_cache[page_idx] = (
                    pdf.pages[page_idx].extract_text() or ""
                ).split("\n")

            lines = page_lines_cache[page_idx]
            race_info = _extract_race_info_from_lines(lines, horse.line_index)  # type: ignore

            if race_info is None:
                race_info = {"nombre": "Carrera", "distancia": None, "hora": None}

            all_races.append(Race(
                race_id=rid,
                hipodromo="Palermo",
                fecha=fecha_hoy,
                numero=None,
                nombre=race_info["nombre"],
                distancia=race_info["distancia"],
                hour=race_info["hora"],
            ))

            for h in horses_group:
                h.race_id = rid
                all_horses.append(h)

    session.add_all(all_races)
    session.flush()
    session.add_all(all_horses)
    session.commit()
    return len(all_horses)
