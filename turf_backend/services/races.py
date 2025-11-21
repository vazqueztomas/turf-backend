# services/race_service.py
from uuid import UUID

from sqlmodel import Session

from turf_backend.models.turf import Horse, Race


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
