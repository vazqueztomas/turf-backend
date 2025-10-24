from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from turf_backend.database import get_connection
from turf_backend.models.turf import Horse

router = APIRouter()


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
    """
    Obtiene una lista de caballos almacenados en la base de datos.
    Se puede filtrar por nombre o jockey y paginar los resultados.
    """
    query = select(Horse)

    if nombre:
        query = query.where(Horse.nombre.ilike(f"%{nombre}%"))
    if jockey:
        query = query.where(Horse.jockey.ilike(f"%{jockey}%"))

    # Paginación
    offset = (page - 1) * limit
    return session.exec(query.offset(offset).limit(limit)).all()
