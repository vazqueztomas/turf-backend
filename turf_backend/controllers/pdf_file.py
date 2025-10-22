import logging
import re
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

from turf_backend.models.turf import AvailableLocations
from turf_backend.utils.date import extract_date


# TODO(Mati): Download PDFs from this other location
# https://hipodromosanisidro.com/programas/
class PdfFileController:
    BASE_URL = "https://www.palermo.com.ar/es/turf/programa-oficial"
    PDF_DOWNLOAD_TEXT = "Descargar VersiÃ³n PDF"

    def __init__(self) -> None:
        self.save_dir = Path("files")
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _make_request(self, url: str) -> str:
        response = requests.get(url)
        response.raise_for_status()
        return response.text

    def _download_pdf(self, url: str) -> bytes:
        response = requests.get(url)
        response.raise_for_status()
        return response.content

    def _parse_anchor_tags(self, text: str) -> list[BeautifulSoup | dict]:
        soup = BeautifulSoup(text, "html.parser")
        return soup.find_all("a", href=True)

    def _save_file(self, file_path: Path, content: bytes) -> None:
        with file_path.open("wb") as file_:
            file_.write(content)

    # TODO(mati): Refactor this and try to make it more generic
    def download_files_from_external_sources(self) -> str:  # pylint: disable=too-many-locals
        url = "https://www.palermo.com.ar/es/turf/programa-oficial"

        response_text = self._make_request(url)
        anchor_tags = self._parse_anchor_tags(response_text)
        pdf_sources = [
            anchor["href"]
            for anchor in anchor_tags
            if "programa-oficial-reunion" in anchor["href"]
        ]

        if not pdf_sources:
            return "No PDFs sources found"

        pdf_urls = []
        for source in pdf_sources:
            response_text = self._make_request(source)  # type: ignore[arg-type]
            anchor_tags = self._parse_anchor_tags(response_text)
            pdf_urls.extend(
                anchor["href"]
                for anchor in anchor_tags
                if anchor["href"].endswith(".pdf")
                and anchor.text.strip() == self.PDF_DOWNLOAD_TEXT  # type: ignore
            )

        for url in pdf_urls:
            pdf_content = self._download_pdf(url)
            pdf_filename = extract_date(pdf_content)
            location_dir_path = self.save_dir / Path(AvailableLocations.PALERMO.value)
            location_dir_path.mkdir(parents=True, exist_ok=True)
            file_path = location_dir_path / f"{pdf_filename}.pdf"
            self._save_file(file_path, pdf_content)

        return "PDFs downloaded successfully"

    def list_available_files(self, turf: AvailableLocations) -> list[str]:
        pdf_dir = Path(f"files/{turf.value}")
        pdf_files = list(pdf_dir.glob("*.pdf"))

        return [file.name for file in pdf_files]

    def retrieve_file(self, turf: AvailableLocations, filename: str) -> Path | None:
        pdf_dir = Path(f"files/{turf.value}/{filename}")
        if not pdf_dir.exists():
            return None

        return pdf_dir


logger = logging.getLogger("extractor")
logger.setLevel(logging.DEBUG)

# Heurística: buscamos la línea que contiene "Caballeriza" + "5 Ultimas" y a partir de ahí
# interpretamos líneas que contienen: <ultimas> <num> <NOMBRE (MAYUS)> <peso> <resto...>
# luego intentamos sacar jockey / padre-madre / entrenador con varias reglas de fallback.

MAIN_LINE_RE = re.compile(
    r"(?P<ultimas>(?:\d+[A-Z0-9]{0,2}\s+){1,6})\s*"
    r"(?P<num>\d{1,2})\s+"
    r"(?P<name>[A-ZÁÉÍÓÚÑ0-9\'\.\s\-]+?)\s+"
    r"(?P<peso>\d{1,2})",
    re.UNICODE,
)

PARENTS_RE = re.compile(
    r"(?P<sire>[\w\(\)\'\.\s]+?)-(?P<mother>[\w\(\)\'\.\s]+)", re.UNICODE
)

CODE_CLEAN_RE = re.compile(
    r"\b\d+\s*[A-Z]?\b"
)  # tokens tipo "4 Z", "5", "11A" a eliminar cuando correspondan


def _clean_text(x: str) -> str:
    if not x:
        return ""
    return re.sub(r"\s{2,}", " ", x).strip()


def extract_horses_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extrae filas de caballo desde el PDF usando heurísticas.
    Devuelve lista de dicts con: page, line_index, ultimas, num, nombre, peso, jockey, padre_madre, entrenador, raw_rest
    """
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")

            # buscamos headers de tabla en la página (varias formas)
            header_idxs = [
                i
                for i, ln in enumerate(lines)
                if re.search(r"Caballeriza.*5\s+Ultimas", ln, re.IGNORECASE)
            ]
            if not header_idxs:
                # no siempre aparece; otra heurística: si línea contiene "Caballeriza" o "Caballeriza 5 Ultimas"
                header_idxs = [
                    i
                    for i, ln in enumerate(lines)
                    if "Caballeriza" in ln and "Ultimas" in ln
                ]

            for header_idx in header_idxs:
                # recorremos desde header_idx+1 hasta fin de sección
                for li in range(header_idx + 1, len(lines)):
                    ln = lines[li].rstrip()
                    if not ln.strip():
                        continue
                    # stop conditions: comienzo de otra sección
                    if re.match(
                        r"^(Premio:|Récord|APUESTA|APUESTAS|Bono Especial|POZOS|^\d+ª Carrera|^Premio)",
                        ln,
                    ):
                        break

                    m = MAIN_LINE_RE.search(ln)
                    if not m:
                        # si no encontramos, probablemente la info esté en varias líneas; intentamos combinar 2 líneas y volver a probar
                        if li + 1 < len(lines):
                            combo = f"{ln} {lines[li + 1]}"
                            m2 = MAIN_LINE_RE.search(combo)
                            if m2:
                                m = m2
                                ln = combo
                            else:
                                continue
                        else:
                            continue

                    ultimas = _clean_text(m.group("ultimas"))
                    num = m.group("num").strip()
                    nombre = _clean_text(m.group("name"))
                    peso = m.group("peso").strip()

                    # resto del texto a la derecha del grupo 'peso'
                    rest = ln[m.end("peso") :].strip()

                    jockey = ""
                    padre_madre = ""
                    entrenador = ""

                    # 1) Si el resto contiene '-' interpretamos que hay padre-madre en la misma línea
                    nm = PARENTS_RE.search(rest)
                    if nm:
                        # madre puede llevar más tokens; tomamos el match pero luego aplicamos heurísticas al resto
                        sire = nm.group("sire").strip()
                        mother = nm.group("mother").strip()
                        padre_madre = f"{_clean_text(sire)} - {_clean_text(mother)}"
                        # jockey: lo que hay antes de nm.start()
                        jockey_candidate = _clean_text(rest[: nm.start()])
                        jockey_candidate = CODE_CLEAN_RE.sub(
                            "", jockey_candidate
                        ).strip()
                        jockey = jockey_candidate
                        # trainer: texto posterior al match
                        trainer_candidate = rest[nm.end() :].strip()
                        trainer_candidate = CODE_CLEAN_RE.sub(
                            "", trainer_candidate
                        ).strip()
                        entrenador = _clean_text(trainer_candidate)
                    else:
                        # 2) si no hay '-', el padre-madre puede estar en la siguiente línea
                        next_line = lines[li + 1] if li + 1 < len(lines) else ""
                        nm2 = PARENTS_RE.search(next_line)
                        if nm2:
                            sire = nm2.group("sire").strip()
                            mother = nm2.group("mother").strip()
                            padre_madre = f"{_clean_text(sire)} - {_clean_text(mother)}"
                            # jockey es lo que hay en rest (limpio códigos)
                            jockey = CODE_CLEAN_RE.sub("", rest).strip()
                            # trainer: lo que quede en next_line después del padre-madre
                            trainer_candidate = next_line[nm2.end() :].strip()
                            entrenador = CODE_CLEAN_RE.sub(
                                "", trainer_candidate
                            ).strip()
                        else:
                            # 3) fallback: intentar detectar jockey name en rest (palabras con mayúscula inicial)
                            # quitamos códigos y números y tomamos las primeras 3-4 palabras como posible jockey
                            candidate = CODE_CLEAN_RE.sub("", rest).strip()
                            words = candidate.split()
                            if words:
                                # heurística: jockey suele ser 1-3 palabras. Tomamos hasta 3 palabras que empiecen con mayúsc.
                                jockey_parts = []
                                for w in words[:6]:
                                    if re.match(
                                        r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ\.]+$", w
                                    ) or re.match(
                                        r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ\.\-]+$", w
                                    ):
                                        jockey_parts.append(w)
                                    else:
                                        # si encontramos token tipo 'J' o 'R' también lo incorporamos
                                        if re.match(r"^[A-Z]\.?$", w):
                                            jockey_parts.append(w)
                                        else:
                                            # stop if we see something that is very unlikely a name (like '4', 'Z', '5')
                                            pass
                                    if len(jockey_parts) >= 3:
                                        break
                                jockey = " ".join(jockey_parts).strip()
                                padre_madre = ""  # desconocido
                                entrenador = ""
                            else:
                                jockey = ""
                                padre_madre = ""
                                entrenador = ""

                    results.append({
                        "page": page_idx,
                        "line_index": li,
                        "ultimas": ultimas,
                        "num": num,
                        "nombre": nombre,
                        "peso": int(peso) if peso.isdigit() else None,
                        "jockey": jockey,
                        "padre_madre": padre_madre,
                        "entrenador": entrenador,
                        "raw_rest": rest,
                    })

    return results
