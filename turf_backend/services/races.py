from collections import defaultdict
from typing import Any
from uuid import UUID

import pdfplumber
from sqlmodel import Session

from turf_backend.models.turf import Horse, Race
from turf_backend.services.helper import (
    DISTANCE_RE,
    HOUR_RE,
    RACE_HEADER_RE,
    extract_race_name,
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


def extract_race_information(
    pdf_path: str, horses_group: list[Horse]
) -> dict[str, Any]:
    horses = horses_group[0]

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[horses.page]  # type: ignore
        lines = (page.extract_text() or "").split("\n")

        # Buscamos hacia arriba desde su line_index
        for i in range(horses.line_index - 1, -1, -1):  # pyright: ignore[reportOptionalOperand]
            line = lines[i]

            m = RACE_HEADER_RE.search(line)
            if not m:
                continue

            # ✔ Distancia
            dist = None
            if dm := DISTANCE_RE.search(line):
                dist = int(dm.group(1))

            # ✔ Hora
            hora = None
            if hm := HOUR_RE.search(line):
                hora = hm.group(1)

            nombre = extract_race_name(lines, i, line)

            return {
                "nombre": nombre,
                "distancia": dist,
                "hora": hora,
                "hipodromo": "Palermo",
            }
    return None


def insert_and_create_races(session, horses, pdf_path: str):
    races_dict = defaultdict(list)
    for h in horses:
        races_dict[h.race_id].append(h)

    total_inserted = 0

    for rid, horses_group in races_dict.items():
        race_info = extract_race_information(pdf_path, horses_group)
        race = create_race(
            session,
            hipodromo="Palermo",
            fecha=None,
            numero=None,
            nombre=race_info["nombre"],
            distancia=race_info["distancia"],
            hour=race_info["hora"],
        )

        race.race_id = rid
        session.flush()

        total_inserted += assign_horses_to_race(session, rid, horses_group)
    return total_inserted
