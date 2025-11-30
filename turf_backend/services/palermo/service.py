# pylint: disable=too-many-locals
import re
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pdfplumber
from sqlmodel import Session

from turf_backend.models import Horse, Race
from turf_backend.services.file import FileService
from turf_backend.utils import (
    HTMLParser,
    LogLevel,
    Settings,
    extract_date,
    http_request,
    log,
)

from .helper import (
    DISTANCE_RE,
    HOUR_RE,
    MAIN_LINE_RE,
    NOMBRE_CON_DISTANCIA_RE,
    PREMIO_RE,
    RACE_HEADER_RE,
    extract_header_idx,
    extract_jockey_trainer_and_parents,
    extract_races_number_name_and_weight,
)


class PalermoService:
    @property
    def file_service(self) -> FileService:
        return FileService()

    @property
    def palermo_path(self) -> Path:
        path = self.file_service.save_dir / Path("palermo")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def download_palermo_files(self) -> str:
        response = http_request(Settings.PALERMO_URL)
        tags = HTMLParser.find_all(response.text, "a", href=True)
        pdf_sources = [
            tag.get("href")
            for tag in tags
            if "programa-oficial-reunion" in tag.get("href", "")
        ]

        if not pdf_sources:
            log("No PDFs sources found", LogLevel.WARNING)
            return "No PDFs sources found"

        pdf_urls: list[str] = []
        for source in pdf_sources:
            response = http_request(source)  # type: ignore[arg-type]
            tags = HTMLParser.find_all(response.text, "a", href=True)
            pdf_urls.extend(
                tag.get("href")
                for tag in tags
                if tag.get("href", "").endswith(".pdf")
                and tag.text.strip() == Settings.PALERMO_DOWNLOAD_TEXT  # type: ignore[attr-defined]
            )

        for url in pdf_urls:
            response = http_request(url)
            pdf_filename = extract_date(response.content)
            file_path = self.palermo_path / f"{pdf_filename}.pdf"
            self.file_service.save_file(file_path, response.content)

        return "PDFs downloaded successfully"

    def list_palermo_files(self) -> list[str]:
        return self.file_service.list_available_files(self.palermo_path)

    def parse_pdf_horses(self, pdf_path: str) -> list[Horse]:
        rows = self.extract_horses_from_pdf(pdf_path)

        seen = set()
        unique_rows = []

        for r in rows:
            key = (r.nombre, r.numero, r.page)
            if key not in seen:
                seen.add(key)
                unique_rows.append(r)

        return unique_rows

    def extract_horses_from_pdf(self, pdf_path: str) -> list[Horse]:
        results = []
        last_race_number = 0
        race_id = uuid.uuid4()

        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                lines = text.split("\n")

                # buscamos headers de tabla en la página
                header_idxs = extract_header_idx(lines)

                for header_idx in header_idxs:
                    # recorremos desde header_idx+1 hasta fin de sección
                    for li in range(header_idx + 1, len(lines)):
                        ln = lines[li].rstrip()
                        if not ln.strip():
                            continue

                        # detectamos caballeriza y la extraemos
                        if re.match(r"^[A-ZÁÉÍÓÚÑ0-9\s\(\)\.\º\-]+$", ln):
                            tokens = ln.split()
                            if len(tokens) <= 3:
                                caballeriza = ln.strip()
                                continue

                        main_line = MAIN_LINE_RE.search(ln)
                        if not main_line:
                            continue

                        ultimas, numero, nombre, peso = (
                            extract_races_number_name_and_weight(main_line)
                        )

                        if int(numero) < last_race_number:
                            race_id = uuid.uuid4()

                        last_race_number = int(numero)
                        rest = ln[main_line.end("peso") :].strip()

                        jockey, padre_madre, entrenador = (
                            extract_jockey_trainer_and_parents(rest)
                        )

                        results.append(
                            Horse(
                                race_id=race_id,
                                page=page_idx,
                                line_index=li,
                                ultimas=ultimas,
                                numero=str(numero),
                                nombre=nombre,
                                peso=int(peso) if peso.isdigit() else None,
                                jockey=jockey,
                                padre_madre=padre_madre,
                                entrenador=entrenador,
                                raw_rest=rest,
                                caballeriza=caballeriza,  # type: ignore
                            )
                        )
        return results

    def create_race(self, session: Session, **kwargs) -> Race:
        """
        Crea una carrera en la tabla Race.
        kwargs permite recibir numero, nombre, distancia, etc.
        """
        race = Race(**kwargs)
        session.add(race)
        session.commit()
        session.refresh(race)
        return race

    def assign_horses_to_race(
        self, session: Session, race_id: UUID, horses: list[Horse]
    ) -> int:
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

    # Encuentra la línea donde está la carrera
    def find_race_header(lines, start_index):
        for idx in range(start_index, -1, -1):
            if RACE_HEADER_RE.search(lines[idx]):
                return idx
        return None

    def extract_race_block(self, lines, header_index, radius=4):
        start = max(0, header_index - radius)
        end = min(len(lines), header_index + radius + 1)
        return lines[start:end]

    def extract_race_information(
        self, pdf_path: str, horses_group: list[Horse]
    ) -> dict[str, Any] | None:
        horse = horses_group[0]

        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[horse.page]  # type: ignore
            lines = (page.extract_text() or "").split("\n")

        # 1. Encontrar encabezado ("1ª Carrera", "2º Carrera", etc.)
        header_idx = None
        for idx in range(horse.line_index, -1, -1):  # type: ignore
            if RACE_HEADER_RE.search(lines[idx]):
                header_idx = idx
                break

        if header_idx is None:
            return None

        # 2. Tomar bloque de líneas alrededor del encabezado
        block = self.extract_race_block(lines, header_idx, radius=4)

        nombre, hora, distancia = self.extract_name_distance_hour(block)

        # Si no hay nombre, usar fallback
        if not nombre:
            header = RACE_HEADER_RE.search(lines[header_idx])
            numero = header.group("num")  # type: ignore[union-attr]
            nombre = f"Carrera {numero}"

        return {
            "nombre": nombre,
            "distancia": distancia,
            "hora": hora,
            "hipodromo": "Palermo",
        }

    def extract_name_distance_hour(self, block):
        nombre = None
        hora = None
        distancia = None

        for line in block:
            # ✔ Extraer nombre
            m = PREMIO_RE.match(line.strip())
            if m and not nombre:
                nombre = m.group(1).strip()

            m2 = NOMBRE_CON_DISTANCIA_RE.match(line.strip())
            if m2 and not nombre:
                nombre = m2.group("nombre").strip()
            # ✔ Extraer hora
            hm = HOUR_RE.search(line)
            if hm and not hora:
                hora = hm.group(1)

            # ✔ Extraer distancia
            dm = DISTANCE_RE.search(line)
            if dm and not distancia:
                distancia = int(dm.group(1))
        return nombre, hora, distancia

    def insert_and_create_races(
        self, session: Session, horses: list[Horse], pdf_path: str
    ) -> int:
        races_dict = defaultdict(list)
        for h in horses:
            races_dict[h.race_id].append(h)

        total_inserted = 0

        for rid, horses_group in races_dict.items():
            race_info = self.extract_race_information(pdf_path, horses_group)
            race = self.create_race(
                session,
                hipodromo="Palermo",
                fecha=datetime.now().strftime("%d/%m/%Y"),
                numero=None,
                nombre=race_info.get("nombre"),  # type: ignore[union-attr]
                distancia=race_info.get("distancia"),  # type: ignore[union-attr]
                hour=race_info.get("hora"),  # type: ignore[union-attr]
            )

            race.race_id = rid
            session.flush()

            total_inserted += self.assign_horses_to_race(session, rid, horses_group)
        return total_inserted
