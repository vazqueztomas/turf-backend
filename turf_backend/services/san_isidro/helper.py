import re

RACE_HEADER_RE = re.compile(r"(?P<num>\d{1,2})\s*(?:ª|º)?\s*Carrera\b", re.IGNORECASE)

DISTANCE_RE = re.compile(r"\b(\d{3,4})\s*(?:m|metros)\b", re.IGNORECASE)
HOUR_RE = re.compile(r"\b(\d{1,2}:\d{2})\s*(?:hs\.?|Hs\.?)?", re.IGNORECASE)
PREMIO_RE = re.compile(r"Premio[:\s]+[\"“”']?([^\"“”']+)", re.IGNORECASE)
MAIN_LINE_RE = re.compile(
    r"(?P<ultimas>(?:\d+[A-Z0-9]{0,2}(?:[-\s])){1,6}|DEBUTA\s+)"
    r"(?P<num>\d{1,2})\s+"
    r"(?P<name>[A-Za-zÁÉÍÓÚÑ0-9\'\.\s\-]+?)\s+"
    r"(?P<peso>\d{1,3}(?:\.\d+)?)",
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


def extract_jockey_trainer_and_parents(rest: str) -> tuple[str, str, str]:
    tokens = rest.split()

    sire_idx = None
    for i, tok in enumerate(tokens):
        if re.search(r"\((usa|arg|brz|chi|ury|mex|can)\)", tok.lower()):
            sire_idx = i
            break

    if sire_idx is None:
        return "", "", ""

    sire = tokens[sire_idx]
    mother = " ".join(tokens[sire_idx + 1 :]).strip()

    jockey_tokens, jockey = detect_jockey(tokens)

    # 3) ENTRENADOR = tokens entre jockey y sire
    if jockey_tokens:
        j_end = len(jockey_tokens)
        entrenador_tokens = tokens[j_end:sire_idx]
    else:
        entrenador_tokens = tokens[:sire_idx]

    entrenador = " ".join(entrenador_tokens).strip()

    padre_madre = f"{sire} - {mother}"

    return jockey, padre_madre, entrenador


def detect_jockey(tokens):
    jockey_tokens = []
    for tok in tokens:
        if re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$", tok):  # token tipo "Flores"
            jockey_tokens.append(tok)
            # normalmente son nombre + apellido
            if len(jockey_tokens) == 2:
                break
        else:
            if jockey_tokens:
                break

    jockey = " ".join(jockey_tokens)
    return jockey_tokens, jockey


def extract_races_number_name_and_weight(main_line):
    raw_ultimas = main_line.group("ultimas")
    ultimas = "DEBUTA" if "DEBUTA" in raw_ultimas else clean_text(raw_ultimas)
    numero = int(main_line.group("num").strip())
    nombre = clean_text(main_line.group("name"))
    peso = main_line.group("peso").strip()
    return ultimas, numero, nombre, peso


def parse_weight(peso_str: str) -> float | int | None:
    w = float(peso_str)
    return int(w) if w.is_integer() else w
