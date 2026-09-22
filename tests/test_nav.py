from pathlib import Path

import pandas as pd

from samfunnsdata.providers.norway.nav import (
    read_unemployment_csv,
)


def test_read_unemployment_csv(tmp_path: Path):
    path = tmp_path / "nav.csv"

    path.write_text(
        "Fylkesnr;Fylkenavn;Kommunenr;Kommunenavn;"
        "År;Månedsnummer;Beholdning;Andel av arbeidsstyrken\r\n"
        "50;Trøndelag;5001;Trondheim;2025;1;1234;2,8\r\n"
        "50;Trøndelag;5001;Trondheim;2025;2;1200;*\r\n",
        encoding="cp1252",
    )

    frame = read_unemployment_csv(path)

    assert len(frame) == 2
    assert frame.iloc[0]["municipality_code"] == "5001"
    assert frame.iloc[0]["municipality_name"] == "Trondheim"
    assert frame.iloc[0]["year"] == 2025
    assert frame.iloc[0]["month"] == 1
    assert frame.iloc[0]["unemployed"] == 1234
    assert frame.iloc[0]["percent"] == 2.8

    assert frame.iloc[1]["unemployed"] == 1200
    assert pd.isna(frame.iloc[1]["percent"])


def test_municipality_unemployment(tmp_path: Path):
    from samfunnsdata.providers.norway.nav import (
        municipality_unemployment,
    )

    path = tmp_path / "nav.csv"

    path.write_text(
        "Fylkesnr;Fylkenavn;Kommunenr;Kommunenavn;"
        "År;Månedsnummer;Beholdning;Andel av arbeidsstyrken\r\n"
        "50;Trøndelag;5001;Trondheim;2024;12;1500;2,5\r\n"
        "50;Trøndelag;5001;Trondheim;2025;1;1600;2,6\r\n"
        "46;Vestland;4601;Bergen;2025;1;2000;2,7\r\n",
        encoding="cp1252",
    )

    frame = read_unemployment_csv(path)
    result = municipality_unemployment(frame, "Trondheim")

    assert len(result) == 2
    assert list(result["year"]) == [2024, 2025]
    assert list(result["month"]) == [12, 1]
    assert list(result["unemployed"]) == [1500, 1600]
    assert list(result["percent"]) == [2.5, 2.6]


def test_municipality_unemployment_unknown(tmp_path: Path):
    from samfunnsdata.providers.norway.nav import (
        municipality_unemployment,
    )

    path = tmp_path / "nav.csv"

    path.write_text(
        "Fylkesnr;Fylkenavn;Kommunenr;Kommunenavn;"
        "År;Månedsnummer;Beholdning;Andel av arbeidsstyrken\r\n"
        "50;Trøndelag;5001;Trondheim;2025;1;1600;2,6\r\n",
        encoding="cp1252",
    )

    frame = read_unemployment_csv(path)

    try:
        municipality_unemployment(frame, "Andeby")
    except ValueError as error:
        assert "Fant ikke kommunen" in str(error)
    else:
        raise AssertionError("Forventet ValueError")


def test_municipality_unemployment_since(monkeypatch):
    import pandas as pd

    from samfunnsdata.providers.norway import nav

    source = pd.DataFrame(
        {
            "year": pd.Series([2014, 2015, 2015, 2016], dtype="Int64"),
            "month": pd.Series([12, 1, 2, 1], dtype="Int64"),
            "unemployed": [1000.0, 1100.0, 1050.0, 900.0],
            "percent": pd.Series(
                [2.0, 2.2, 2.1, 1.8],
                dtype="Float64",
            ),
        }
    )

    monkeypatch.setattr(
        nav,
        "municipality_unemployment_data",
        lambda municipality: source,
    )

    result = nav.municipality_unemployment_since(
        "Trondheim",
        2015,
    )

    assert len(result) == 3
    assert result.iloc[0]["year"] == 2015
    assert result.iloc[0]["month"] == 1
    assert result.iloc[-1]["year"] == 2016
