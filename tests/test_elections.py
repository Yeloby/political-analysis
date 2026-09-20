import pandas as pd
import pytest

from political_analysis.providers.norway.elections import (
    ElectionArea,
    find_related_area,
    parties_to_frame,
)


def test_find_related_area_exact():
    data = {
        "_links": {
            "related": [
                {
                    "nr": "16",
                    "navn": "Sør-Trøndelag",
                    "href": "/2025/st/16",
                },
                {
                    "nr": "17",
                    "navn": "Nord-Trøndelag",
                    "href": "/2025/st/17",
                },
            ]
        }
    }

    result = find_related_area(data, "Sør-Trøndelag")

    assert result == ElectionArea(
        number="16",
        name="Sør-Trøndelag",
        href="/2025/st/16",
    )


def test_find_related_area_missing():
    data = {"_links": {"related": []}}

    with pytest.raises(ValueError, match="Fant ikke området"):
        find_related_area(data, "Andeby")


def test_parties_to_frame():
    data = {
        "id": {
            "valgaar": "2025",
            "valgtype": "ST",
            "nivaa": "kommune",
            "nr": "5001",
            "navn": "Trondheim",
        },
        "partier": [
            {
                "id": {
                    "partikode": "FRP",
                    "navn": "Fremskrittspartiet",
                    "partikategori": "STORTINGSPARTI",
                },
                "stemmer": {
                    "resultat": {
                        "antall": {"total": 22730},
                        "prosent": 17.31585,
                    }
                },
            }
        ],
    }

    frame = parties_to_frame(data)

    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 1

    row = frame.iloc[0]

    assert row["year"] == 2025
    assert row["area_number"] == "5001"
    assert row["area_name"] == "Trondheim"
    assert row["party_code"] == "FRP"
    assert row["party_name"] == "Fremskrittspartiet"
    assert row["votes"] == 22730
    assert row["percent"] == pytest.approx(17.31585)
