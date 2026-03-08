import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("turf")

BASE_URL = "https://hipodromosanisidro.com"
CALENDAR_URL = f"{BASE_URL}/programas/"
PROGRAM_API_URL = f"{BASE_URL}/wacP/public/programa-oficial/"
CALENDAR_API_URL = f"{BASE_URL}/wacP/public/calendario"


@dataclass
class RaceInfo:
    numero: int
    nombre: str
    hora: str
    distancia: int
    pista: str
    condicion: str
    bolsa_total: str
    premios: dict


@dataclass
class HorseInfo:
    numero: str
    nombre: str
    sexo: str
    peso: float
    herraje: str
    stud: str
    jockey: str
    peso_jockey: float
    entrenador: str
    padre_madre: str
    ultimas: str
    edad: str
    cuidado: str


@dataclass
class DayRaces:
    fecha: str
    calendario_id: str
    races: list[RaceInfo]
    horses_by_race: dict[int, list[HorseInfo]]


def fetch_page(url: str) -> BeautifulSoup:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


@dataclass
class CalendarEvent:
    fecha: str          # YYYY-MM-DD
    calendario_id: str
    tipo: str           # "resultados", "programa-oficial", "inscriptos"


def get_calendar_events(start: date, end: date) -> list[CalendarEvent]:
    """Fetch all calendar events for a date range from the official API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    params = {"start": start.isoformat(), "end": end.isoformat()}
    response = requests.get(CALENDAR_API_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    events = []
    for item in response.json():
        url = item.get("url", "")
        class_name = item.get("className", "")
        match = re.search(r"calendario_id=(\d+)", url)
        if not match:
            continue

        calendario_id = match.group(1)
        if "resultados" in class_name:
            tipo = "resultados"
        elif "programa-oficial" in class_name:
            tipo = "programa-oficial"
        elif "inscriptos" in class_name:
            tipo = "inscriptos"
        else:
            continue

        events.append(CalendarEvent(
            fecha=item.get("start", ""),
            calendario_id=calendario_id,
            tipo=tipo,
        ))

    return events


def get_orange_days() -> list[tuple[str, str]]:
    """Get upcoming programa-oficial days (next 60 days)."""
    today = date.today()
    events = get_calendar_events(today, today + timedelta(days=60))
    return [(e.fecha, e.calendario_id) for e in events if e.tipo == "programa-oficial"]


def get_resultados_days(start: date, end: date) -> list[tuple[str, str]]:
    """Get past race days (resultados) for a date range."""
    events = get_calendar_events(start, end)
    return [(e.fecha, e.calendario_id) for e in events if e.tipo == "resultados"]


def get_upcoming_orange_day() -> Optional[tuple[str, str]]:
    """Get the next upcoming orange day from calendar."""
    days = get_orange_days()
    if days:
        return days[0]
    return None


def scrape_race_day(calendario_id: str) -> DayRaces:
    """Scrape all races from a specific day using the API."""
    url = f"{PROGRAM_API_URL}{calendario_id}"
    soup = fetch_page(url)

    races = []
    horses_by_race = {}

    fecha_elem = soup.find("h4")
    fecha = ""
    if fecha_elem:
        fecha_text = fecha_elem.get_text(strip=True)
        fecha_match = re.search(r"\d{1,2}\s+de\s+\w+\s+de\s+\d{4}", fecha_text)
        if fecha_match:
            fecha = fecha_match.group(0)

    tables = soup.find_all("table")

    all_elements = soup.find_all(["div", "table"])

    race_divs = []
    for elem in all_elements:
        text = elem.get_text(strip=True)
        if re.search(r"\d+\s*ª\s*[-–]\s*Premio", text):
            race_divs.append(elem)

    current_race_info = None

    for i, div in enumerate(race_divs):
        div_text = div.get_text(strip=True)

        race_match = re.search(
            r"(\d+)\s*(?:ª|º)?\s*[-–]\s*Premio[:\s]+([^-]+?)(?:\s*-\s*(\d{1,2}:\d{2})\s*hs?)?",
            div_text,
            re.I,
        )
        if not race_match:
            continue

        numero = int(race_match.group(1))
        nombre = race_match.group(2).strip()
        hora = race_match.group(3) or ""

        distancia = 0
        pista = ""
        bolsa = ""

        for j in range(i, min(i + 10, len(all_elements))):
            if all_elements[j] == div:
                continue
            elem_text = all_elements[j].get_text(strip=True)

            dist_match = re.search(r"(\d{3,4})\s*mts?", elem_text, re.I)
            if dist_match and distancia == 0:
                distancia = int(dist_match.group(1))

            pista_match = re.search(
                r"Pista\s+(Arena|Tierra|Cemento|Grass)", elem_text, re.I
            )
            if pista_match:
                pista = pista_match.group(1)

            bolsa_match = re.search(r"Bolsa\s*Total[:\s]*\$?([\d\.]+)", elem_text, re.I)
            if bolsa_match:
                bolsa = bolsa_match.group(1)

        current_race_info = RaceInfo(
            numero=numero,
            nombre=nombre,
            hora=hora,
            distancia=distancia,
            pista=pista,
            condicion="",
            bolsa_total=bolsa,
            premios={},
        )
        races.append(current_race_info)
        horses_by_race[numero] = []

    table_idx = 0
    for race in races:
        while table_idx < len(tables):
            table = tables[table_idx]
            text = table.get_text(strip=True)

            if "EJEMP" not in text and "caballo" not in text.lower():
                table_idx += 1
                continue

            rows = table.find_all("tr")
            if len(rows) < 3:
                table_idx += 1
                continue

            horses = parse_horses_from_table(rows)
            horses_by_race[race.numero].extend(horses)
            table_idx += 1
            break

    return DayRaces(
        fecha=fecha,
        calendario_id=calendario_id,
        races=races,
        horses_by_race=horses_by_race,
    )


def parse_horses_from_table(rows) -> list[HorseInfo]:
    horses = []

    if len(rows) < 2:
        return horses

    header_row = rows[0]
    header_cells = header_row.find_all(["th", "td"])
    header_texts = [c.get_text(strip=True).lower() for c in header_cells]

    col_map = {}
    for i, h in enumerate(header_texts):
        if "ejemp" in h or "nro" in h:
            col_map["num"] = i
        elif "caballo" in h or "nombre" in h:
            col_map["nombre"] = i
        elif "sexo" in h:
            col_map["sexo"] = i
        elif "kg" in h and "peso" not in col_map:
            if "jockey" not in h.lower():
                col_map["peso"] = i
        elif "stud" in h:
            col_map["stud"] = i
        elif "jockey" in h:
            col_map["jockey"] = i
        elif "entrenador" in h:
            col_map["entrenador"] = i
        elif "padre" in h or "madre" in h:
            col_map["padre"] = i
        elif "últimas" in h or "ultimas" in h:
            col_map["ultimas"] = i
        elif "edad" in h:
            col_map["edad"] = i
        elif "cuida" in h:
            col_map["cuidado"] = i

    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        def get_text(c):
            return c.get_text(strip=True)

        numero = ""
        if "num" in col_map and col_map["num"] < len(cells):
            numero = get_text(cells[col_map["num"]])
            if not numero.isdigit():
                continue

        nombre = (
            get_text(cells[col_map["nombre"]])
            if "nombre" in col_map and col_map["nombre"] < len(cells)
            else ""
        )

        sexo = (
            get_text(cells[col_map["sexo"]])
            if "sexo" in col_map and col_map["sexo"] < len(cells)
            else ""
        )

        peso = 0.0
        if "peso" in col_map and col_map["peso"] < len(cells):
            peso_text = get_text(cells[col_map["peso"]])
            peso_match = re.search(r"([\d\.]+)", peso_text)
            if peso_match:
                peso = float(peso_match.group(1))

        stud = (
            get_text(cells[col_map["stud"]])
            if "stud" in col_map and col_map["stud"] < len(cells)
            else ""
        )

        jockey = ""
        peso_jockey = 0.0
        if "jockey" in col_map and col_map["jockey"] < len(cells):
            jtext = get_text(cells[col_map["jockey"]])
            jmatch = re.match(r"(.+?)\s*([\d\.]+)\s*$", jtext)
            if jmatch:
                jockey = jmatch.group(1).strip()
                peso_jockey = float(jmatch.group(2))
            else:
                jockey = jtext

        if "peso" not in col_map:
            for c in cells:
                ctext = get_text(c)
                if re.match(r"[\d\.]+\s*$", ctext):
                    try:
                        peso_jockey = float(ctext)
                    except:
                        pass

        entrenador = (
            get_text(cells[col_map["entrenador"]])
            if "entrenador" in col_map and col_map["entrenador"] < len(cells)
            else ""
        )

        padre_madre = (
            get_text(cells[col_map["padre"]])
            if "padre" in col_map and col_map["padre"] < len(cells)
            else ""
        )

        ultimas = (
            get_text(cells[col_map["ultimas"]])
            if "ultimas" in col_map and col_map["ultimas"] < len(cells)
            else ""
        )

        edad = (
            get_text(cells[col_map["edad"]])
            if "edad" in col_map and col_map["edad"] < len(cells)
            else ""
        )

        cuidado = (
            get_text(cells[col_map["cuidado"]])
            if "cuidado" in col_map and col_map["cuidado"] < len(cells)
            else ""
        )

        horses.append(
            HorseInfo(
                numero=numero,
                nombre=nombre,
                sexo=sexo,
                peso=peso,
                herraje="",
                stud=stud,
                jockey=jockey,
                peso_jockey=peso_jockey,
                entrenador=entrenador,
                padre_madre=padre_madre,
                ultimas=ultimas,
                edad=edad,
                cuidado=cuidado,
            )
        )

    return horses


def scrape_upcoming_races() -> Optional[DayRaces]:
    """Scrape races from the next upcoming orange day."""
    day = get_upcoming_orange_day()
    if day:
        fecha, calendario_id = day
        return scrape_race_day(calendario_id)
    return None


@dataclass
class PdfLinks:
    programa_oficial: Optional[str]
    inscriptos: Optional[str]
    depurados: Optional[str]


def get_pdf_links(calendario_id: str) -> PdfLinks:
    """Extract PDF download links from a program page."""
    url = f"{PROGRAM_API_URL}{calendario_id}"
    soup = fetch_page(url)

    programa_oficial = None
    inscriptos = None
    depurados = None

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.endswith(".pdf"):
            continue
        lower = href.lower()
        if "inscripto" in lower:
            inscriptos = href if href.startswith("http") else f"{BASE_URL}{href}"
        elif "depurado" in lower or "forfait" in lower:
            depurados = href if href.startswith("http") else f"{BASE_URL}{href}"
        elif "programa" in lower:
            programa_oficial = href if href.startswith("http") else f"{BASE_URL}{href}"

    return PdfLinks(
        programa_oficial=programa_oficial,
        inscriptos=inscriptos,
        depurados=depurados,
    )


def download_pdf(pdf_url: str) -> bytes:
    """Download a PDF from a URL and return its content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    response = requests.get(pdf_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.content
