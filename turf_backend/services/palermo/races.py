# pylint: disable=too-many-locals
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

import pdfplumber
from sqlmodel import Session, select

from turf_backend.models.turf import Horse, Race, RaceHorseLink
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
    inserted = 0

    for h in horses:
        stmt = select(Horse).where(
            Horse.nombre == h.nombre, Horse.numero == h.numero, Horse.page == h.page
        )
        existing = session.execute(stmt).scalar_one_or_none()

        if not existing:
            session.add(h)
            session.flush()  # obtener h.id sin commit
            horse_db = h
            inserted += 1
        else:
            horse_db = existing

        # Crear link a la race (si ya está linkeado no lo duplicamos)
        link_stmt = select(RaceHorseLink).where(
            RaceHorseLink.race_id == race_id, RaceHorseLink.horse_id == horse_db.id
        )
        link_exists = session.execute(link_stmt).scalar_one_or_none()

        if not link_exists:
            session.add(RaceHorseLink(race_id=race_id, horse_id=horse_db.id))  # type: ignore

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


def extract_race_information(
    pdf_path: str, horses_group: list[Horse]
) -> dict[str, Any] | None:
    horse = horses_group[0]

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[horse.page]  # type: ignore
        lines = (page.extract_text() or "").split("\n")

    # 1. Encontrar encabezado ("1ª Carrera", "2º Carrera", etc.)
    header_idx = None
    for idx in range(horse.line_index, -1, -1):  # type: ignore
        if RACE_HEADER_RE.search(lines[idx]):
            header_idx = idx
            break

    if header_idx is None:
        return None

    # 2. Tomar bloque de líneas alrededor del encabezado
    block = extract_race_block(lines, header_idx, radius=4)

    nombre, hora, distancia = extract_name_distance_hour(block)

    # Si no hay nombre, usar fallback
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


def insert_and_create_races(session, horses, pdf_path: str) -> int:
    races: dict[UUID, list[Horse]] = defaultdict(list)
    for horse in horses:
        races[horse.race_id].append(horse)

    inserted = 0

    for race_id, group in races.items():
        race = session.exec(select(Race).where(Race.race_id == race_id)).first()
        if not race:
            info = extract_race_information(pdf_path, group)
            race = Race(
                race_id=race_id,
                nombre=info["nombre"],
                distancia=info["distancia"],
                hour=info["hora"],
                hipodromo="Palermo",
                fecha=datetime.now().strftime("%d/%m/%Y"),
            )
            session.add(race)

        session.flush()
        inserted += assign_horses_to_race(session, race_id, group)

    return inserted
