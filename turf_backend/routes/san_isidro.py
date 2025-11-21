# pylint: disable=too-many-locals, duplicate-code
import logging
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from turf_backend.database import get_connection
from turf_backend.models.turf import Horse, Race
from turf_backend.services.palermo_processing import extract_races_and_assign

logger = logging.getLogger("turf")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/san-isidro", tags=["San Isidro"])


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

    for race in races:
        q = select(Race).where(
            Race.numero == race["num"],
            Race.hipodromo == "Palermo",
        )
        race_obj = session.exec(q).first()

        if not race_obj:
            race_obj = Race(
                numero=race["num"],
                nombre=race.get("nombre"),
                distancia=race.get("distancia"),
                fecha=race.get("hora"),
                hipodromo="Palermo",
            )
            session.add(race_obj)
            session.commit()
            session.refresh(race_obj)
            inserted_races += 1

        for horse in race.horses:
            exists = session.exec(
                select(Horse).where(
                    Horse.nombre == horse.nombre,
                    Horse.numero == horse.num,
                    Horse.page == horse.page,
                )
            ).first()

            if exists:
                continue

            horse_obj = Horse(
                race_id=race_obj.id,
                numero=horse.num,
                nombre=horse.nombre,
                peso=horse.peso,
                jockey=horse.jockey,
                ultimas=horse.ultimas,
                padre_madre=horse.padre_madre,
                entrenador=horse.entrenador,
                raw_rest=horse.raw_rest,
                page=horse.page,
                line_index=horse.line_index,
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
