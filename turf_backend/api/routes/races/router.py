# pylint: disable=duplicate-code
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from turf_backend.api.dependencies import DatabaseSession
from turf_backend.models.turf import Horse, Race

router = APIRouter(prefix="/races", tags=["Races"])


@router.get("/")
def get_all_races(
    session: DatabaseSession,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    races = session.exec(select(Race).offset(offset).limit(limit)).all()
    return {"count": len(races), "results": races}


@router.get("/{race_id}")
def get_race_detail(race_id: UUID, session: DatabaseSession):
    race = session.get(Race, race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")

    horses = session.exec(select(Horse).where(Horse.race_id == race_id)).all()
    return {"race": race, "horses": horses}
