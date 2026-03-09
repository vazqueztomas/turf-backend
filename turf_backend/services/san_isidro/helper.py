import re

# Matches the race header line, e.g.:
#   "1ª - Premio CORSA KIND 2011 - 13:45 hs."
#   "3ª - Clásico GRAN CRITERIUM (G1) - 15:00 hs."
RACE_HEADER_RE = re.compile(
    r"^(\d+)[ªº°]\s*-\s*(Premio|Cl[aá]sico|Gran\s+Premio|G\.?\s*P\.?)\s+(.+?)\s*-\s*(\d{1,2}:\d{2})\s*hs",
    re.IGNORECASE,
)

DISTANCE_RE = re.compile(
    r"\b(\d{3,4})\s*(?:m|mts|metros)\.?\b",
    re.IGNORECASE,
)

HOUR_RE = re.compile(r"\b(\d{1,2}:\d{2})\s*(?:hs\.?|Hs\.?)?", re.IGNORECASE)

PISTA_RE = re.compile(r"Pista\s+([A-Za-záéíóúÁÉÍÓÚÑñ\s]+)", re.IGNORECASE)

# Horse line must start with a 2-digit number, then uppercase name, then [HM], then peso anchor.
# We use this as a quick gate before full parsing.
HORSE_LINE_RE = re.compile(
    r"^\d{2}\s+[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9\s'\(\)\-\.]+[HM]\s.*\d{2,3}\.\d{2}",
    re.UNICODE,
)

# Pelo codes accepted
PELO_CODES = {
    "Z", "A", "T", "B", "R", "O", "P",
    "ZC", "ZD", "ZO", "AT", "ZA", "ZT", "TC", "AC", "RO", "TO",
}

# Race result letter codes used in ultimas (single letter only).
# S=placed, A=placed, L=Liquidado, V=Vendido, G=Ganó, N=No corrió, D=Distancia
_ULTIMA_LETTERS = "SALVGND"

# A single ultimas token: one or more \d+[letter] units, e.g. "0S", "3A", "0S3S4S"
ULTIMA_SEQ_TOKEN_RE = re.compile(rf"^(?:\d+[{_ULTIMA_LETTERS}])+$")

# Unit finder used internally by split_ultimas_cuida
_ULTIMA_UNIT_RE = re.compile(rf"\d+[{_ULTIMA_LETTERS}]")


def clean_text(x: str) -> str:
    return re.sub(r"\s{2,}", " ", x).strip()


def parse_weight(peso_str: str) -> float | int | None:
    try:
        w = float(peso_str)
        return int(w) if w.is_integer() else w
    except (ValueError, TypeError):
        return None


def split_ultimas_cuida(token: str) -> tuple[str, str]:
    """
    Split a token that may be concatenated ultimas+cuida, e.g. '2S1A1A1AHIPSI'.

    Strategy: find all ultima-unit end positions right-to-left; take the first
    split where the remaining cuida is >= 3 chars and starts with a letter.
    Returns (ultimas_part, cuida_part) or ('', token) if no valid split found.
    """
    if not token:
        return "", token

    # If the whole token is a pure ultimas sequence, there is no cuida.
    if ULTIMA_SEQ_TOKEN_RE.match(token):
        return "", token

    matches = list(_ULTIMA_UNIT_RE.finditer(token))
    if not matches:
        return "", token

    for i in range(len(matches) - 1, -1, -1):
        split_pos = matches[i].end()
        ul_candidate = token[:split_pos]
        cu_candidate = token[split_pos:]

        if len(cu_candidate) >= 3 and cu_candidate[0].isupper():
            if ULTIMA_SEQ_TOKEN_RE.match(ul_candidate):
                return ul_candidate, cu_candidate

    return "", token


def parse_pre_peso(pre_peso: str) -> tuple[str, str]:
    """
    Parse the portion before the peso on a horse line (after stripping numero and nombre+sexo).
    Format: [herraje_digit] [FF] STUD [(CODE)] JOCKEY...

    Returns (stud, jockey).
    """
    s = pre_peso.strip()

    # Strip leading single digit (herraje), e.g. "0 " or "0"
    s = re.sub(r"^\d\s*", "", s)

    # Strip leading "FF " handicap marker
    s = re.sub(r"^FF\s+", "", s)

    s = s.strip()
    if not s:
        return "", ""

    # If there's a parenthesized location code, e.g. "(CDU)" or "(LP)" or "(GGCHU)"
    # Everything up to and including the code is stud; rest is jockey.
    m = re.search(r"\([A-Z0-9]+\)", s)
    if m:
        stud = s[: m.end()].strip()
        jockey = s[m.end() :].strip()
        return stud, jockey

    # No parenthesized code: first token = stud, rest = jockey
    parts = s.split(None, 1)
    stud = parts[0] if parts else ""
    jockey = parts[1] if len(parts) > 1 else ""
    return stud, jockey


def parse_post_peso(post_peso: str) -> tuple[str, str, str, str, str, str]:
    """
    Parse the portion after the peso value on a horse line.
    Format: ENTRENADOR[PELO] EDAD PADRE-MADRE [ULTIMAS] [CUIDA]

    The parsing strategy works right-to-left:
      1. Last token: strip cuida (or split concatenated ultimas+cuida).
      2. Collect trailing ultimas sequence token(s).
      3. Find edad (leftmost single digit scanning from right).
      4. Tokens after edad = padre_madre; tokens before = entrenador + optional pelo.

    Returns (entrenador, pelo, edad, padre_madre, ultimas, cuida).
    """
    tokens = post_peso.split()
    if not tokens:
        return "", "", "", "", "", ""

    cuida = ""
    ultimas = ""
    edad = ""
    entrenador = ""
    pelo = ""
    padre_madre = ""

    # --- Step 1: Handle the last token ---
    # Could be: plain cuida, concatenated ultimas+cuida, or bare ultimas sequence (no cuida).
    last = tokens[-1]
    ul_part, cu_part = split_ultimas_cuida(last)
    if ul_part:
        # e.g. "2S1A1A1AHIPSI" -> ul_part="2S1A1A1A", cu_part="HIPSI"
        cuida = cu_part
        tokens = tokens[:-1]
        # Insert the separated ultimas sequence back for step 2 to collect
        tokens.append(ul_part)
    elif ULTIMA_SEQ_TOKEN_RE.match(last):
        # Bare ultimas sequence (no cuida), e.g. "0S3S4S" or "5S"
        cuida = ""
        # Leave in tokens list so step 2 picks it up
    else:
        # Plain cuida token, e.g. "HIPSI", "CDU", "L.P."
        cuida = last
        tokens = tokens[:-1]

    # --- Step 2: Collect trailing ultimas sequence token(s) ---
    # Ultimas can be a single concatenated token like "0S3S4S" or multiple
    # separate single-run tokens like "0S" "3S" "4S" (rare but handle it).
    ultimas_tokens = []
    while tokens and ULTIMA_SEQ_TOKEN_RE.match(tokens[-1]):
        ultimas_tokens.insert(0, tokens[-1])
        tokens = tokens[:-1]
    ultimas = "".join(ultimas_tokens)

    # --- Step 3: Find edad (single digit) scanning from right ---
    # edad is the LAST standalone single-digit token that comes before padre_madre.
    # padre_madre tokens contain hyphens (e.g. "FRAGOTERO-COMANDULERA") so we
    # skip hyphenated tokens when looking for edad.
    edad_idx = None
    for i in range(len(tokens) - 1, -1, -1):
        if re.match(r"^\d$", tokens[i]):
            edad_idx = i
            break

    if edad_idx is None:
        # No edad found — return what we have
        entrenador = " ".join(tokens)
        return entrenador, pelo, edad, padre_madre, ultimas, cuida

    edad = tokens[edad_idx]

    # --- Step 4: padre_madre = tokens after edad ---
    padre_madre = " ".join(tokens[edad_idx + 1:])

    # --- Step 5: tokens before edad = entrenador (with possible trailing pelo) ---
    pre_edad_tokens = tokens[:edad_idx]

    if not pre_edad_tokens:
        return entrenador, pelo, edad, padre_madre, ultimas, cuida

    last_pre = pre_edad_tokens[-1]

    # Check if the last pre-edad token is a standalone pelo code
    if last_pre in PELO_CODES:
        pelo = last_pre
        entrenador = " ".join(pre_edad_tokens[:-1])
    else:
        # Check if it ends with a pelo code (concatenated), e.g.:
        #   "ADRIANZC" -> root="ADRIAN", pelo="ZC"
        #   "DANIELA"  -> root="DANIEL", pelo="A"
        #   "GASTONA"  -> root="GASTON", pelo="A"
        matched_pelo = ""
        for code in sorted(PELO_CODES, key=len, reverse=True):  # longest first
            if last_pre.endswith(code) and len(last_pre) > len(code):
                candidate_root = last_pre[: -len(code)]
                # Root must look like part of a name (≥2 chars, all alpha)
                if len(candidate_root) >= 2 and re.match(r"^[A-ZÁÉÍÓÚÑ]+$", candidate_root, re.IGNORECASE):
                    matched_pelo = code
                    last_pre = candidate_root
                    break

        if matched_pelo:
            pelo = matched_pelo
            entrenador = " ".join(pre_edad_tokens[:-1] + [last_pre])
        else:
            pelo = ""
            entrenador = " ".join(pre_edad_tokens)

    return entrenador, pelo, edad, padre_madre, ultimas, cuida
