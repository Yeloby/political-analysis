import pytest

from political_analysis.providers.norway.ssb import (
    Municipality,
    find_municipality,
    jsonstat_to_frame,
)


def test_jsonstat_to_frame():
    data = {
        "id": ["Region", "Tid"],
        "size": [1, 2],
        "dimension": {
            "Region": {
                "category": {
                    "index": {"K-5001": 0},
                    "label": {"K-5001": "Trondheim - Tråante"},
                }
            },
            "Tid": {
                "category": {
                    "index": {"2025": 0, "2026": 1},
                    "label": {"2025": "2025", "2026": "2026"},
                }
            },
        },
        "value": [216518, 218460],
    }

    frame = jsonstat_to_frame(data)

    assert len(frame) == 2
    assert frame.iloc[0]["Region"] == "Trondheim - Tråante"
    assert frame.iloc[0]["Tid"] == "2025"
    assert frame.iloc[0]["value"] == 216518
    assert frame.iloc[1]["value"] == 218460


def test_find_municipality_exact(monkeypatch):
    municipalities = [
        Municipality("K-5001", "Trondheim - Tråante"),
        Municipality("K-4601", "Bergen"),
    ]

    monkeypatch.setattr(
        "political_analysis.providers.norway.ssb.municipalities",
        lambda: municipalities,
    )

    result = find_municipality("Bergen")

    assert result.code == "K-4601"
    assert result.name == "Bergen"


def test_find_municipality_partial(monkeypatch):
    municipalities = [
        Municipality("K-5001", "Trondheim - Tråante"),
        Municipality("K-4601", "Bergen"),
    ]

    monkeypatch.setattr(
        "political_analysis.providers.norway.ssb.municipalities",
        lambda: municipalities,
    )

    result = find_municipality("Trondheim")

    assert result.code == "K-5001"


def test_find_municipality_missing(monkeypatch):
    monkeypatch.setattr(
        "political_analysis.providers.norway.ssb.municipalities",
        list,
    )

    with pytest.raises(ValueError, match="Fant ikke kommunen"):
        find_municipality("Andeby")
