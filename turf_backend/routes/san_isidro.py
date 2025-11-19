# pylint: disable=too-many-locals, duplicate-code
import logging
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select, text

from turf_backend.database import get_connection
from turf_backend.models.turf import Horse, Race
from turf_backend.services.pdf_processing import extract_races_and_assign

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/san-isidro", tags=["San Isidro"])


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


@router.post("/upload-and-save/")
async def upload_and_save(
    file: UploadFile = File(...),
    session: Session = Depends(get_connection),
):
    if not file:
        raise HTTPException(status_code=400, detail="Se requiere un archivo PDF válido")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    extraction = extract_races_and_assign(tmp_path)
    races = extraction["races"]

    inserted_races = 0
    inserted_horses = 0

    for r in races:
        q = select(Race).where(
            Race.numero == r["num"],
            Race.hipodromo == "Palermo",
        )
        race_obj = session.exec(q).first()

        if not race_obj:
            race_obj = Race(
                numero=r["num"],
                nombre=r.get("nombre"),
                distancia=r.get("distancia"),
                fecha=r.get("hora"),
                hipodromo="Palermo",
            )
            session.add(race_obj)
            session.commit()
            session.refresh(race_obj)
            inserted_races += 1

        for h in r.get("horses", []):
            exists = session.exec(
                select(Horse).where(
                    Horse.nombre == h.get("nombre"),
                    Horse.numero == h.get("num"),
                    Horse.page == h.get("page"),
                )
            ).first()

            if exists:
                continue

            horse_obj = Horse(
                race_id=race_obj.id,
                numero=h.get("num"),
                nombre=h.get("nombre"),
                peso=h.get("peso"),
                jockey=h.get("jockey"),
                ultimas=h.get("ultimas"),
                padre_madre=h.get("padre_madre"),
                entrenador=h.get("entrenador"),
                raw_rest=h.get("raw_rest"),
                page=h.get("page"),
                line_index=h.get("line_index"),
            )

            session.add(horse_obj)
            inserted_horses += 1

    session.commit()

    return {
        "message": f"✅ Se cargaron {len(races)} carreras. "
        f"Nuevas: {inserted_races}. "
        f"Caballos insertados: {inserted_horses} ",
        "summary": extraction["summary"],
    }


@router.get("/races/")
def get_all_races(
    session: Session = Depends(get_connection),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    races = session.exec(select(Race).offset(offset).limit(limit)).all()
    return {"count": len(races), "results": races}


@router.get("/races/{race_id}")
def get_race_detail(race_id: int, session: Session = Depends(get_connection)):
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
