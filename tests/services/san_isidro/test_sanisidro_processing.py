from pathlib import Path

from turf_backend.services.san_isidro.races import (
    extract_all_races_from_lines,
    parse_race_at_line,
)
from turf_backend.services.san_isidro.races import (
    find_race_number_and_line_above as find_race_number_above,
)

HERE = Path("/mnt/data")
PDF_PATH = HERE / "SI_PROGRAMA_OFICIAL_01-11-2025_(MODIFICADO)_7098.pdf"


def test_find_race_number_above(sample_lines):
    from_index = 6
    race_number_above = find_race_number_above(sample_lines, from_index)
    assert race_number_above is not None
    num, idx, _ = race_number_above
    assert num == 1
    assert idx == 1


def test_parse_race_at_line_real_pdf(lines_from_pdf):
    race_index = None
    for i, line in enumerate(lines_from_pdf):
        s = line.strip()
        if s.isdigit() and 1 <= len(s) <= 2:
            race_index = i
            break
        if s and s.split()[0].isdigit() and 1 <= len(s.split()[0]) <= 2:
            race_index = i
            break

    assert race_index is not None, "No race index found in PDF text"
    from_index = min(race_index + 6, len(lines_from_pdf) - 1)
    race = parse_race_at_line(lines_from_pdf, from_index)
    assert race is not None
    assert isinstance(race.get("numero"), int)
    assert race["numero"] == int(lines_from_pdf[race_index].strip().split()[0])


def test_extract_all_races_from_lines(lines_from_pdf):
    races = extract_all_races_from_lines(lines_from_pdf)
    assert isinstance(races, list)
    assert len(races) > 0


def test_edge_cases_missing_name_or_distance(sample_lines):
    result = parse_race_at_line(sample_lines, len(sample_lines) - 1)
    assert result is not None
    assert result["numero"] == 2
    assert result["nombre"] == "COOL DAY 2021"
    assert result["distancia"] == 1600
