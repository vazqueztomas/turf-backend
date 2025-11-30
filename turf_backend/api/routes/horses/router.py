from fastapi import APIRouter, Query
from sqlmodel import select

from turf_backend.api.dependencies import DatabaseSession
from turf_backend.models import Horse

router = APIRouter(prefix="/horses", tags=["Horses"])


@router.get("/", response_model=list[Horse])
def get_horses(
    session: DatabaseSession,
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
