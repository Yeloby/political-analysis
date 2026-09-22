import pandas as pd
import pytest

from samfunnsdata.providers.norway.elections import (
    ElectionArea,
    find_related_area,
    parties_to_frame,
)


@pytest.fixture(autouse=True)
def clear_municipality_index():
    from samfunnsdata.providers.norway import elections

    elections._MUNICIPALITY_INDEX.clear()
    elections._MUNICIPALITY_ELECTION_INDEX.clear()
    yield
    elections._MUNICIPALITY_INDEX.clear()
    elections._MUNICIPALITY_ELECTION_INDEX.clear()


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
    from samfunnsdata.providers.norway import elections

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
    from samfunnsdata.providers.norway import elections

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


def test_find_municipality_election_area(monkeypatch):
    from samfunnsdata.providers.norway import elections

    responses = {
        "/2023/ko": {
            "_links": {
                "related": [
                    {
                        "nr": "50",
                        "navn": "Trøndelag",
                        "href": "/2023/ko/50",
                    }
                ]
            }
        },
        "/2023/ko/50": {
            "_links": {
                "related": [
                    {
                        "nr": "5001",
                        "navn": "Trondheim",
                        "href": "/2023/ko/50/5001",
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

    county, municipality = elections.find_municipality_election_area(
        2023,
        "Trondheim",
    )

    assert county.name == "Trøndelag"
    assert municipality.number == "5001"
    assert municipality.name == "Trondheim"
    assert municipality.href == "/2023/ko/50/5001"


def test_find_municipality_election_area_missing(monkeypatch):
    from samfunnsdata.providers.norway import elections

    responses = {
        "/2023/ko": {
            "_links": {
                "related": [
                    {
                        "nr": "50",
                        "navn": "Trøndelag",
                        "href": "/2023/ko/50",
                    }
                ]
            }
        },
        "/2023/ko/50": {
            "_links": {"related": []}
        },
    }

    monkeypatch.setattr(
        elections.ElectionClient,
        "get",
        lambda self, path: responses[path],
    )

    with pytest.raises(
        ValueError,
        match="Fant ikke kommunen",
    ):
        elections.find_municipality_election_area(
            2023,
            "Andeby",
        )


def test_municipality_election_result(monkeypatch):
    from samfunnsdata.providers.norway import elections

    responses = {
        "/2023/ko": {
            "_links": {
                "related": [
                    {
                        "nr": "50",
                        "navn": "Trøndelag",
                        "href": "/2023/ko/50",
                    }
                ]
            }
        },
        "/2023/ko/50": {
            "_links": {
                "related": [
                    {
                        "nr": "5001",
                        "navn": "Trondheim",
                        "href": "/2023/ko/50/5001",
                    }
                ]
            }
        },
        "/2023/ko/50/5001": {
            "id": {
                "valgaar": "2023",
                "valgtype": "KO",
                "nivaa": "kommune",
                "nr": "5001",
                "navn": "Trondheim",
            },
            "partier": [
                {
                    "id": {
                        "partikategori": 1,
                        "partikode": "H",
                        "navn": "Høyre",
                    },
                    "stemmer": {
                        "resultat": {
                            "prosent": 29.21273,
                            "antall": {"total": 31945},
                        }
                    },
                }
            ],
        },
    }

    monkeypatch.setattr(
        elections.ElectionClient,
        "get",
        lambda self, path: responses[path],
    )

    area, frame = elections.municipality_election_result(
        2023,
        "Trondheim",
    )

    assert area.number == "5001"
    assert area.name == "Trondheim"

    row = frame.iloc[0]
    assert row["year"] == 2023
    assert row["election_type"] == "KO"
    assert row["area_number"] == "5001"
    assert row["party_code"] == "H"
    assert row["votes"] == 31945
    assert row["percent"] == pytest.approx(29.21273)


def test_municipality_party_history(monkeypatch):
    from samfunnsdata.providers.norway import elections

    def fake_result(year, municipality):
        assert municipality == "Trondheim"

        frame = pd.DataFrame(
            [
                {
                    "year": year,
                    "party_code": "H",
                    "party_name": "Høyre",
                    "votes": year,
                    "percent": 20.0,
                },
                {
                    "year": year,
                    "party_code": "A",
                    "party_name": "Arbeiderpartiet",
                    "votes": year + 1,
                    "percent": 25.0,
                },
            ]
        )

        return ElectionArea(
            number="5001",
            name="Trondheim",
            href=f"/{year}/ko/50/5001",
        ), frame

    monkeypatch.setattr(
        elections,
        "municipality_election_result",
        fake_result,
    )

    frame = elections.municipality_party_history(
        municipality="Trondheim",
        party_code="H",
        since=2015,
    )

    assert frame["year"].tolist() == [2015, 2019, 2023]
    assert frame["party_code"].tolist() == ["H", "H", "H"]
