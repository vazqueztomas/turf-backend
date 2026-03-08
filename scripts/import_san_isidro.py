"""
Script para importar PDFs históricos y próximos de San Isidro.
Corre directamente en GitHub Actions, conectándose a Neon sin pasar por Vercel.

Uso:
  python scripts/import_san_isidro.py --start 2026-01-01 --end 2026-02-28 --tipo resultados
  python scripts/import_san_isidro.py --tipo upcoming
"""
import argparse
import hashlib
import logging
import os
import sys
import tempfile
from datetime import date, timedelta

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Parsear POSTGRES_URL y setear las vars individuales que requiere settings.py
# Esto debe hacerse ANTES de importar cualquier módulo de turf_backend
_db_url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL", "")
if not _db_url:
    print("ERROR: Falta la variable de entorno POSTGRES_URL o DATABASE_URL")
    sys.exit(1)

from urllib.parse import urlparse as _urlparse  # noqa: E402
_parsed = _urlparse(_db_url)
os.environ.setdefault("ENVIRONMENT", "PRODUCTION")
os.environ.setdefault("POSTGRES_USER", _parsed.username or "")
os.environ.setdefault("POSTGRES_PASSWORD", _parsed.password or "")
os.environ.setdefault("POSTGRES_HOST", _parsed.hostname or "")
os.environ.setdefault("POSTGRES_DATABASE", _parsed.path.lstrip("/"))
os.environ.setdefault("POSTGRES_URL", _db_url)
os.environ.setdefault("OPENAI_API_KEY", "dummy")

from sqlmodel import Session, SQLModel, create_engine, select

from turf_backend.models.turf import PdfImport
from turf_backend.services.san_isidro import scraper
from turf_backend.services.san_isidro.races import insert_and_create_races
from turf_backend.services.san_isidro.sanisidro_processing import parse_pdf_horses

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("import_san_isidro")


def get_engine():
    url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta la variable de entorno POSTGRES_URL o DATABASE_URL")
    # Neon usa postgres:// pero SQLAlchemy necesita postgresql://
    url = url.replace("postgres://", "postgresql://", 1)
    # Neon requiere SSL
    if "sslmode" not in url:
        url += "?sslmode=require"
    return create_engine(url)


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def import_day(engine, fecha: str, calendario_id: str) -> dict:
    """Cada día usa su propia sesión para que un fallo no contamine los siguientes."""
    try:
        links = scraper.get_pdf_links(calendario_id)
        if not links.programa_oficial:
            logger.info("Sin PDF: %s (%s)", fecha, calendario_id)
            return {"fecha": fecha, "status": "skipped", "reason": "no PDF"}

        pdf_content = scraper.download_pdf(links.programa_oficial)
        file_hash = compute_hash(pdf_content)

        with Session(engine) as session:
            existing = session.exec(select(PdfImport).where(PdfImport.file_hash == file_hash)).first()
            if existing:
                logger.info("Ya importado: %s", fecha)
                return {"fecha": fecha, "status": "skipped", "reason": "already imported"}

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name

            horses = parse_pdf_horses(tmp_path)
            filename = links.programa_oficial.split("/")[-1]

            if not horses:
                session.add(PdfImport(file_hash=file_hash, filename=filename, hipodromo="san_isidro"))
                session.commit()
                logger.info("Importado sin caballos: %s", fecha)
                return {"fecha": fecha, "status": "imported", "inserted": 0}

            total = insert_and_create_races(session, horses, tmp_path)
            session.add(PdfImport(file_hash=file_hash, filename=filename, hipodromo="san_isidro"))
            session.commit()
            logger.info("Importado: %s — %d caballos", fecha, total)
            return {"fecha": fecha, "status": "imported", "inserted": total}

    except Exception as e:
        logger.exception("Error procesando %s (%s)", fecha, calendario_id)
        return {"fecha": fecha, "status": "error", "reason": str(e)}


def get_days_via_backend(tipo: str, start: str = "", end: str = "") -> list[tuple[str, str]]:
    """
    Obtiene los días del calendario usando el backend como proxy,
    para evitar que GitHub Actions sea bloqueado por hipodromosanisidro.com.
    """
    backend_url = os.environ.get("BACKEND_URL", "https://turf-backend-theta.vercel.app")
    if tipo == "upcoming":
        url = f"{backend_url}/san-isidro/calendar/orange-days"
        response = requests.get(url, timeout=30)
    else:
        url = f"{backend_url}/san-isidro/calendar/resultados"
        response = requests.get(url, params={"start": start, "end": end}, timeout=30)

    response.raise_for_status()
    data = response.json()
    return [(d["fecha"], d["calendario_id"]) for d in data["days"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tipo", choices=["resultados", "upcoming"], required=True)
    parser.add_argument("--start", help="Fecha inicio YYYY-MM-DD (solo para resultados)")
    parser.add_argument("--end", help="Fecha fin YYYY-MM-DD (solo para resultados)")
    args = parser.parse_args()

    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    if args.tipo == "upcoming":
        days = get_days_via_backend("upcoming")
    else:
        if not args.start or not args.end:
            parser.error("--start y --end son requeridos para --tipo resultados")
        days = get_days_via_backend("resultados", args.start, args.end)

    logger.info("Días a procesar: %d", len(days))

    results = []
    for fecha, calendario_id in days:
        result = import_day(engine, fecha, calendario_id)
        results.append(result)

    imported = sum(1 for r in results if r["status"] == "imported")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    logger.info("Resumen — importados: %d, salteados: %d, errores: %d", imported, skipped, errors)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
