import logging
import re
import tempfile
from datetime import datetime
from typing import Any

import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select, text

from turf_backend.controllers.pdf_file import extract_horses_from_pdf
from turf_backend.database import get_connection
from turf_backend.models.turf import Horse, Race

logger = logging.getLogger("turf")
router = APIRouter(prefix="/turf", tags=["Turf"])


logger = logging.getLogger("extractor")
logger.setLevel(logging.INFO)

# ------------------------------
# Expresiones Regulares
# ------------------------------
RACE_HEADER_RE = re.compile(r"(?P<num>\d{1,2})\s*(?:ª|º)?\s*Carrera\b", re.IGNORECASE)
DISTANCE_RE = re.compile(r"\(?\b(\d{3,4})\s*m(?:etros)?\)?", re.IGNORECASE)
HOUR_RE = re.compile(r"\b(\d{1,2}:\d{2})\s*(?:Hs\.?|hs\.?)?", re.IGNORECASE)
PREMIO_RE = re.compile(r"Premio[:\s]+[\"“”']?(.*?)[\"”']?(?:\s|$)", re.IGNORECASE)
STOP_SECTION_RE = re.compile(
    r"^(Récord|APUESTA|APUESTAS|Bono Especial|POZOS|^Premio|^\d+ª Carrera|^POZOS)",
    re.IGNORECASE,
)


# ------------------------------
# Extracción de Carreras
# ------------------------------
def extract_races_and_assign(pdf_path: str) -> dict[str, Any]:
    """
    Extrae carreras y les asigna caballos desde el PDF del hipódromo Palermo.
    Devuelve un diccionario con las carreras, caballos asociados y resumen.
    """
    horses = extract_horses_from_pdf(pdf_path)
    logger.info(f"Caballos detectados: {len(horses)}")

    races: list[dict[str, Any]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")

            for i, line in enumerate(lines):
                # unimos línea actual con la siguiente (casos donde está partida)
                line_joined = f"{line} {lines[i + 1]}" if i + 1 < len(lines) else line

                # detectar encabezado de carrera
                m = RACE_HEADER_RE.search(line_joined)
                if not m:
                    continue

                num = int(m.group("num"))

                # distancia
                dist = None
                if dm := DISTANCE_RE.search(line_joined):
                    try:
                        dist = int(dm.group(1))
                    except ValueError:
                        pass

                # hora
                hour = None
                if hm := HOUR_RE.search(line_joined):
                    hour = hm.group(1)

                # nombre / premio
                nombre = None
                if pm := PREMIO_RE.search(line_joined):
                    nombre = pm.group(1).strip()
                else:
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    if "Premio" in next_line:
                        nombre = re.sub(r"(?i)Premio[:\s]+", "", next_line).strip()

                races.append({
                    "page": page_idx,
                    "header_line_index": i,
                    "num": num,
                    "distancia": dist,
                    "hora": hour,
                    "nombre": nombre,
                    "horses": [],
                    "assigned_set": set(),
                })

    # Ordenar por posición en el PDF
    races.sort(key=lambda r: (r["page"], r["header_line_index"]))

    # Asignar caballos a la carrera más cercana
    for h in horses:
        candidates = []
        for r in races:
            score = abs(r["page"] - h["page"]) * 1000 + abs(
                r["header_line_index"] - h["line_index"]
            )
            candidates.append((score, r))
        if not candidates:
            continue

        candidates.sort(key=lambda x: x[0])
        best_score, best_r = candidates[0]

        # ignorar asignaciones demasiado lejanas
        if best_score > 5000:
            continue

        key = ((h.get("nombre") or "").strip().upper(), str(h.get("num")))
        if key in best_r["assigned_set"]:
            continue

        best_r["assigned_set"].add(key)
        h_copy = dict(h)
        h_copy["assigned_race_num"] = best_r["num"]
        best_r["horses"].append(h_copy)

    # preparar salida final
    total_horses = sum(len(r["horses"]) for r in races)
    summary = {"races": len(races), "horses": total_horses}

    return {
        "generated_at": datetime.now(),
        "races": races,
        "summary": summary,
    }


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


# ------------------------------
# POST /upload-and-save/
# ------------------------------
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
        # Buscar o crear carrera (única por número e hipódromo)
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
                fecha=datetime.now(),
                hipodromo="Palermo",
            )
            session.add(race_obj)
            session.commit()
            session.refresh(race_obj)
            inserted_races += 1

        # Insertar caballos asociados
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
        "message": f"✅ Se cargaron {len(races)} carreras. Nuevas: {inserted_races}. Caballos insertados: {inserted_horses}",
        "summary": extraction["summary"],
    }


# ------------------------------
# GET /races/
# ------------------------------
@router.get("/races/")
def get_all_races(
    session: Session = Depends(get_connection),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    races = session.exec(select(Race).offset(offset).limit(limit)).all()
    return {"count": len(races), "results": races}


# ------------------------------
# GET /races/{race_id}
# ------------------------------
@router.get("/races/{race_id}")
def get_race_detail(race_id: int, session: Session = Depends(get_connection)):
    race = session.get(Race, race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")

    horses = session.exec(select(Horse).where(Horse.race_id == race_id)).all()
    return {"race": race, "horses": horses}


# ------------------------------
# DELETE /reset/
# ------------------------------
@router.delete("/reset/")
def reset_database(session: Session = Depends(get_connection)):
    """⚠️ SOLO para desarrollo: elimina todas las tablas de turf."""
    session.exec(text("DELETE FROM horses;"))
    session.exec(text("DELETE FROM races;"))
    session.commit()
    return {"message": "💣 Base de datos reseteada correctamente."}
