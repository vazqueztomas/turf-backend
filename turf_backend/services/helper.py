import re

REGEX_PDF_PALERMO = (
    r"^(Premio:|Récord|APUESTA|APUESTAS|Bono Especial|POZOS|^\d+ª Carrera|^Premio)"
)

PARENTS_RE = re.compile(
    r"(?P<sire>[\w\(\)\'\.\s]+?)-(?P<mother>[\w\(\)\'\.\s]+)", re.UNICODE
)
CODE_CLEAN_RE = re.compile(r"\b\d+\s*[A-Z]?\b")

RACE_HEADER_RE = re.compile(r"(?P<num>\d{1,2})\s*(?:ª|º)?\s*Carrera\b", re.IGNORECASE)
DISTANCE_RE = re.compile(r"\(?\b(\d{3,4})\s*m(?:etros)?\)?", re.IGNORECASE)
HOUR_RE = re.compile(r"\b(\d{1,2}:\d{2})\s*(?:Hs\.?|hs\.?)?", re.IGNORECASE)
PREMIO_RE = re.compile(r"Premio[:\s]+[\"“”']?([^\"“”'\-]+)", re.IGNORECASE)

MAIN_LINE_RE = re.compile(
    r"(?P<ultimas>(?:\d+[A-Z0-9]{0,2}\s+){1,6})\s*"
    r"(?P<num>\d{1,2})\s+"
    r"(?P<name>[A-ZÁÉÍÓÚÑ0-9\'\.\s\-]+?)\s+"
    r"(?P<peso>\d{1,2})",
    re.UNICODE,
)


def strip_unused_tokens_between_jockey_and_parents(text: str) -> str:
    tokens = text.split()
    clean = []
    for tk in tokens:
        if re.match(r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ\-]+$", tk):
            clean.append(tk)
        else:
            break
    return " ".join(clean)


def extract_header_idx(lines: list[str]) -> list[int]:
    headers = [
        i
        for i, ln in enumerate(lines)
        if re.search(r"Caballeriza.*5\s+Ultimas", ln, re.IGNORECASE)
    ]
    if not headers:
        headers = [
            i for i, ln in enumerate(lines) if "Caballeriza" in ln and "Ultimas" in ln
        ]
    return headers


def check_is_valid_race_header(lines: list[str], idx: int, joined: str) -> bool:
    window_text = joined
    max_ahead = 3
    for j in range(1, max_ahead + 1):
        if idx + j < len(lines):
            window_text += " " + lines[idx + j]

    if (
        DISTANCE_RE.search(window_text)
        or HOUR_RE.search(window_text)
        or PREMIO_RE.search(window_text)
    ):
        return True

    any(idx + j < len(lines) and "Caballeriza" in lines[idx + j] for j in range(6))

    return False


def clean_text(x: str) -> str:
    return re.sub(r"\s{2,}", " ", x).strip()


def extract_jockey_trainer_and_parents(rest) -> tuple[str, str, str]:
    nm = PARENTS_RE.search(rest)
    if nm:
        # madre puede llevar más tokens; tomamos el match
        sire = nm.group("sire").strip()
        mother = nm.group("mother").strip()
        jockey = strip_unused_tokens_between_jockey_and_parents(rest)
        padre_madre = (
            (f"{clean_text(sire)} - {clean_text(mother)}").replace(jockey, "").strip()
        )
        entrenador = rest.replace(jockey, "").replace(padre_madre, "").strip()
    else:
        jockey = ""
        padre_madre = ""
        entrenador = ""
    return jockey, padre_madre, entrenador  # type: ignore
