"""
Script para importar PDFs de Palermo automáticamente.
Corre en GitHub Actions conectándose directo a Neon, usando Vercel como proxy
para no ser bloqueado por palermo.com.ar.

Uso:
  python scripts/import_palermo.py
"""
import hashlib
import logging
import os
import sys
import tempfile

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setear vars antes de importar turf_backend
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

from sqlmodel import Session, SQLModel, create_engine, select  # noqa: E402

from turf_backend.models.turf import PdfImport  # noqa: E402
from turf_backend.services.palermo.palermo_processing import parse_pdf_horses  # noqa: E402
from turf_backend.services.palermo.races import insert_and_create_races  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("import_palermo")

BACKEND_URL = os.environ.get("BACKEND_URL", "https://turf-backend-theta.vercel.app")


def get_engine():
    url = _db_url.replace("postgres://", "postgresql://", 1)
    if "sslmode" not in url:
        url += "?sslmode=require"
    return create_engine(url)


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def get_available_pdfs() -> list[dict]:
    """Obtiene la lista de PDFs disponibles vía el backend (proxy a palermo.com.ar)."""
    resp = requests.get(f"{BACKEND_URL}/palermo/available-pdfs", timeout=30)
    resp.raise_for_status()
    return resp.json().get("pdfs", [])


def download_pdf_via_backend(pdf_url: str) -> bytes:
    """Descarga un PDF a través del backend como proxy."""
    resp = requests.get(
        f"{BACKEND_URL}/palermo/proxy-pdf",
        params={"url": pdf_url},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def import_pdf(engine, pdf_url: str, filename: str) -> dict:
    try:
        pdf_content = download_pdf_via_backend(pdf_url)
        file_hash = compute_hash(pdf_content)

        with Session(engine) as session:
            existing = session.exec(select(PdfImport).where(PdfImport.file_hash == file_hash)).first()
            if existing:
                logger.info("Ya importado: %s", filename)
                return {"filename": filename, "status": "skipped", "reason": "already imported"}

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name

            horses = parse_pdf_horses(tmp_path)

            if not horses:
                session.add(PdfImport(file_hash=file_hash, filename=filename, hipodromo="palermo"))
                session.commit()
                logger.info("Importado sin caballos: %s", filename)
                return {"filename": filename, "status": "imported", "inserted": 0}

            total = insert_and_create_races(session, horses, tmp_path)
            session.add(PdfImport(file_hash=file_hash, filename=filename, hipodromo="palermo"))
            session.commit()
            logger.info("Importado: %s — %d caballos", filename, total)
            return {"filename": filename, "status": "imported", "inserted": total}

    except Exception as e:
        logger.exception("Error procesando %s", filename)
        return {"filename": filename, "status": "error", "reason": str(e)}


def main():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    logger.info("Buscando PDFs disponibles en palermo.com.ar...")
    pdfs = get_available_pdfs()

    if not pdfs:
        logger.info("No se encontraron PDFs disponibles")
        return

    logger.info("PDFs a procesar: %d", len(pdfs))

    results = []
    for pdf in pdfs:
        result = import_pdf(engine, pdf["url"], pdf["filename"])
        results.append(result)

    imported = sum(1 for r in results if r["status"] == "imported")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    logger.info("Resumen — importados: %d, salteados: %d, errores: %d", imported, skipped, errors)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
