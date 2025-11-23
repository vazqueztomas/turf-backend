import re

REGEX_PDF_SAN_ISIDRO = (
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
    """
    Extrae jockey, entrenador y padre-madre en formato:
    jockey: primeros tokens tipo Nombre Apellido
    entrenador: tokens entre jockey y sire/mother
    padre_madre: detectado por primer token padre terminando en (xxx)
    """
    tokens = rest.split()

    # 1) DETECTAR SIRE (primer token que parece un padre)
    sire_idx = None
    for i, tok in enumerate(tokens):
        if re.search(r"\((usa|arg|brz|chi|ury|mex|can)\)", tok.lower()):
            sire_idx = i
            break

    if sire_idx is None:
        return "", "", ""

    sire = tokens[sire_idx]
    mother = " ".join(tokens[sire_idx + 1 :]).strip()

    # 2) DETECTAR JOCKEY: primeros tokens tipo Nombre Apellido
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

    # 3) ENTRENADOR = tokens entre jockey y sire
    if jockey_tokens:
        j_end = len(jockey_tokens)
        entrenador_tokens = tokens[j_end:sire_idx]
    else:
        entrenador_tokens = tokens[:sire_idx]

    entrenador = " ".join(entrenador_tokens).strip()

    padre_madre = f"{sire} - {mother}"

    return jockey, padre_madre, entrenador


def extract_races_number_name_and_weight(main_line):
    raw_ultimas = main_line.group("ultimas")
    ultimas = "DEBUTA" if "DEBUTA" in raw_ultimas else clean_text(raw_ultimas)
    numero = int(main_line.group("num").strip())
    nombre = clean_text(main_line.group("name"))
    peso = main_line.group("peso").strip()
    return ultimas, numero, nombre, peso


def extract_race_name(lines, i: int, line: str):
    nombre = None
    if pm := PREMIO_RE.search(line):
        nombre = pm.group(1).strip()
    else:
        lookahead_limit = 5
        for j in range(1, lookahead_limit + 1):
            if i + j >= len(lines):
                break
            candidate = lines[i + j]
            if RACE_HEADER_RE.search(candidate):  # No cruzar otra carrera
                break
            if "Premio" in candidate or "premio" in candidate.lower():
                nombre = re.sub(r"(?i)Premio[:\s]+", "", candidate).strip()
                break
            if not nombre and DISTANCE_RE.search(candidate):
                before_dist = candidate.split(
                    str(DISTANCE_RE.search(candidate).group(1))  # type: ignore
                )[0]
                if before_dist.strip():
                    nombre = before_dist.strip().strip("-—:")
                    break
    return nombre


def parse_weight(peso_str: str) -> float | int | None:
    try:
        w = float(peso_str)
        # Si termina en .0 lo devolvemos como entero
        return int(w) if w.is_integer() else w
    except ValueError:
        return None
