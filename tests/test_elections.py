import pandas as pd
import pytest

from political_analysis.providers.norway.elections import (
    ElectionArea,
    find_related_area,
    parties_to_frame,
)


@pytest.fixture(autouse=True)
def clear_municipality_index():
    from political_analysis.providers.norway import elections

    elections._MUNICIPALITY_INDEX.clear()
    yield
    elections._MUNICIPALITY_INDEX.clear()


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


def test_find_storting_municipality(monkeypatch):
    from political_analysis.providers.norway import elections

    responses = {
        "/2025/st": {
            "_links": {
                "related": [
                    {
                        "nr": "16",
                        "navn": "Sør-Trøndelag",
                        "href": "/2025/st/16",
                    },
                    {
                        "nr": "12",
                        "navn": "Hordaland",
                        "href": "/2025/st/12",
                    },
                ]
            }
        },
        "/2025/st/16": {
            "_links": {
                "related": [
                    {
                        "nr": "5001",
                        "navn": "Trondheim",
                        "href": "/2025/st/16/5001",
                    }
                ]
            }
        },
        "/2025/st/12": {
            "_links": {
                "related": [
                    {
                        "nr": "4601",
                        "navn": "Bergen",
                        "href": "/2025/st/12/4601",
                    }
                ]
            }
        },
    }

    monkeypatch.setattr(
        elections.ElectionClient,
        "get",
        lambda self, path: responses[path],
    )

    district, municipality = (
        elections.find_storting_municipality(
            2025,
            "Bergen",
        )
    )

    assert district.name == "Hordaland"
    assert municipality.name == "Bergen"
    assert municipality.number == "4601"


def test_find_storting_municipality_missing(monkeypatch):
    from political_analysis.providers.norway import elections

    responses = {
        "/2025/st": {
            "_links": {
                "related": [
                    {
                        "nr": "16",
                        "navn": "Sør-Trøndelag",
                        "href": "/2025/st/16",
                    }
                ]
            }
        },
        "/2025/st/16": {
            "_links": {
                "related": [
                    {
                        "nr": "5001",
                        "navn": "Trondheim",
                        "href": "/2025/st/16/5001",
                    }
                ]
            }
        },
    }

    monkeypatch.setattr(
        elections.ElectionClient,
        "get",
        lambda self, path: responses[path],
    )

    import pytest

    with pytest.raises(
        ValueError,
        match="Fant ikke kommunen",
    ):
        elections.find_storting_municipality(
            2025,
            "Atlantis",
        )
