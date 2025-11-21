# pylint: disable=duplicate-code
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, text

from turf_backend.database import get_connection
from turf_backend.models.turf import Horse, Race

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/general", tags=["General"])


@router.get("/horses/", response_model=list[Horse])
def get_horses(
    session: Session = Depends(get_connection),
    nombre: str | None = Query(None, description="Buscar por nombre (parcial)"),
    jockey: str | None = Query(None, description="Buscar por jockey (parcial)"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(
        20, ge=1, le=100, description="Cantidad de resultados por página"
    ),
):
    query = select(Horse)

    if nombre:
        query = query.where(Horse.nombre.ilike(f"%{nombre}%"))  # type: ignore
    if jockey:
        query = query.where(Horse.jockey.ilike(f"%{jockey}%"))  # type: ignore

    offset = (page - 1) * limit
    return session.exec(query.offset(offset).limit(limit)).all()


@router.get("/races/")
def get_all_races(
    session: Session = Depends(get_connection),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    races = session.exec(select(Race).offset(offset).limit(limit)).all()
    return {"count": len(races), "results": races}


@router.get("/races/{race_id}")
def get_race_detail(race_id: UUID, session: Session = Depends(get_connection)):
    race = session.get(Race, race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")

    horses = session.exec(select(Horse).where(Horse.race_id == race_id)).all()
    return {"race": race, "horses": horses}


@router.delete("/reset/")
def reset_database(session: Session = Depends(get_connection)):
    """⚠️ SOLO para desarrollo: elimina todas las tablas de turf."""
    session.exec(text("DELETE FROM horses;"))  # type: ignore
    session.exec(text("DELETE FROM races;"))  # type: ignore
    session.commit()
    return {"message": "💣 Base de datos reseteada correctamente."}
