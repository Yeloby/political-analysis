from copy import deepcopy

import pandas as pd
import pytest

from samfunnsdata.catalog import find_datasets, get_dataset
from samfunnsdata.providers.norway.fhi import FhiClient
from samfunnsdata.providers.norway.medicines import (
    MEASURES,
    Category,
    atc_categories,
    latest_medicine_observation,
    lookup_atc,
    medicine_history,
    search_atc,
)


def category(code, label, children=None):
    return {"value": code, "label": label, "children": children}


@pytest.fixture
def fhi(monkeypatch):
    dimensions = [
        {"code": "Atc_Verdi", "categories": [category("A", "Group A", [
            category("A10", "Group A10", [
                category("A10BA02", "A10BA02 - metformin"),
                category("A10BD02", "A10BD02 - metformin and sulfonylureas"),
            ]),
        ])]},
        {"code": "Kjonn_Verdi", "categories": [category("TOTALT", "Begge kjønn", [
            category("1", "Mann"), category("2", "Kvinne"),
        ])]},
        {"code": "Aldersgruppe_Verdi", "categories": [category("TOTALT", "Alle aldre", [
            category("1", "0 - 4 år"),
        ])]},
        {"code": "Utlevering_Ar", "categories": [
            category("2027", "2027"), category("2004", "2004"), category("2025", "2025"),
        ]},
        {"code": "MEASURE_TYPE", "categories": [
            category(code, f"FHI label: {code}") for code in MEASURES
        ]},
    ]
    state = {"queries": [], "dimensions": dimensions,
             "values": {"2004": 0, "2025": None, "2027": None},
             "statuses": {"2004": "", "2025": "..", "2027": ":"}}

    def get_dimensions(self, source, table_id):
        assert (source, table_id) == ("lmr", 825)
        return deepcopy(dimensions)

    def metadata(self, source, table_id):
        assert (source, table_id) == ("lmr", 825)
        return {"name": "Per ATC-kode", "paragraphs": [{"text": "FHI methodology"}]}

    def data(self, source, table_id, selection, *, max_row_count):
        assert (source, table_id, max_row_count) == ("lmr", 825, 50000)
        state["queries"].append(deepcopy(selection))
        ids = ["Atc_Verdi", "Kjonn_Verdi", "Aldersgruppe_Verdi", "Utlevering_Ar", "MEASURE_TYPE"]
        years = list(reversed(selection["Utlevering_Ar"]))
        dims = {}
        for dim in ids:
            codes = years if dim == "Utlevering_Ar" else selection[dim]
            dims[dim] = {"category": {
                "index": codes, "label": {code: f"FHI label: {code}" for code in codes},
            }}
        return {
            "class": "dataset", "version": "2.0", "label": "Per ATC-kode. 2004-2027",
            "updated": "2028-01-01", "id": ids,
            "size": [len(dims[dim]["category"]["index"]) for dim in ids],
            "dimension": dims,
            "value": [state["values"][year] for year in years],
            "status": [state["statuses"][year] for year in years],
            "extension": {"flags": {"label": {":": "Skjult"}}},
        }

    monkeypatch.setattr(FhiClient, "dimensions", get_dimensions)
    monkeypatch.setattr(FhiClient, "metadata", metadata)
    monkeypatch.setattr(FhiClient, "data", data)
    return state


def test_exact_atc_lookup(fhi):
    assert lookup_atc(" a10ba02 ") == Category("A10BA02", "A10BA02 - metformin")
    with pytest.raises(ValueError, match="Ukjent ATC"):
        lookup_atc("A10BA")


def test_discovery_includes_nested_categories(fhi):
    assert [item.code for item in atc_categories()] == ["A", "A10", "A10BA02", "A10BD02"]


def test_atc_search_candidates(fhi):
    assert [item.code for item in search_atc(" METFORMIN ")] == ["A10BA02", "A10BD02"]
    assert [item.code for item in search_atc("sulfonylureas")] == ["A10BD02"]
    assert search_atc("unknown") == []
    assert search_atc(" ") == []


def test_history_request_chronology_values_and_metadata(fhi):
    frame = medicine_history("A10BA02")
    assert fhi["queries"] == [{
        "Atc_Verdi": ["A10BA02"], "Kjonn_Verdi": ["TOTALT"],
        "Aldersgruppe_Verdi": ["TOTALT"], "MEASURE_TYPE": ["AntallBrukere"],
        "Utlevering_Ar": ["2004", "2025", "2027"],
    }]
    assert list(frame.columns) == [
        "year", "atc_code", "atc_label", "sex_code", "sex_label", "age_code", "age_label",
        "year_code", "year_label", "measure_code", "measure_label", "value", "status",
    ]
    assert frame["year"].tolist() == [2004, 2025, 2027]
    assert frame["year_code"].tolist() == ["2004", "2025", "2027"]
    assert frame["atc_code"].tolist() == ["A10BA02"] * 3
    assert frame["atc_label"].tolist() == ["FHI label: A10BA02"] * 3
    assert frame["value"].iloc[0] == 0
    assert frame["value"].isna().tolist() == [False, True, True]
    assert frame["status"].tolist() == ["", "..", ":"]
    provenance = frame.attrs["provenance"]
    assert provenance["provider"] == "FHI"
    assert (provenance["source_id"], provenance["table_id"]) == ("lmr", 825)
    assert provenance["table_title"] == "Per ATC-kode. 2004-2027"
    assert provenance["selection"] == {
        "atc": "A10BA02", "sex": "TOTALT", "age": "TOTALT", "measure": "AntallBrukere",
    }
    assert provenance["period"] == {"first_year": 2004, "last_year": 2027}
    assert provenance["retrieved_at"]
    assert frame.attrs["jsonstat_metadata"]["updated"] == "2028-01-01"
    assert frame.attrs["jsonstat_metadata"]["extension"]["flags"]["label"][":"] == "Skjult"
    assert frame.attrs["fhi_metadata"]["paragraphs"] == [{"text": "FHI methodology"}]


def test_since_inclusive(fhi):
    frame = medicine_history("A10BA02", since=2025)
    assert frame["year"].tolist() == [2025, 2027]
    assert fhi["queries"][0]["Utlevering_Ar"] == ["2025", "2027"]
    assert frame.attrs["provenance"]["period"] == {"first_year": 2025, "last_year": 2027}
    assert frame.attrs["provenance"]["available_years"] == [2004, 2025, 2027]


@pytest.mark.parametrize("measure", MEASURES)
def test_selections_and_measure_identity(fhi, measure):
    frame = medicine_history("A10BA02", sex="2", age="1", measure=measure)
    assert fhi["queries"][0]["Kjonn_Verdi"] == ["2"]
    assert fhi["queries"][0]["Aldersgruppe_Verdi"] == ["1"]
    assert fhi["queries"][0]["MEASURE_TYPE"] == [measure]
    assert frame["measure_code"].tolist() == [measure] * 3
    assert frame["measure_label"].tolist() == [f"FHI label: {measure}"] * 3
    assert frame["sex_code"].tolist() == ["2"] * 3
    assert frame["age_code"].tolist() == ["1"] * 3


@pytest.mark.parametrize("kwargs", [
    {"sex": "3"}, {"age": "999"}, {"measure": "made_up"}, {"since": 2099},
])
def test_invalid_selection_does_not_post(fhi, kwargs):
    with pytest.raises(ValueError):
        medicine_history("A10BA02", **kwargs)
    assert not fhi["queries"]


def test_unknown_atc_does_not_post(fhi):
    with pytest.raises(ValueError, match="atc"):
        medicine_history("UNKNOWN")
    assert not fhi["queries"]


@pytest.mark.parametrize("value,status,valid", [
    (0, "", True), (1.25, None, True), (None, "", False),
    (None, "..", False), (None, ".", False), (None, ":", False),
    (123, ":", False), (123, "unknown", False), (float("inf"), "", False),
])
def test_latest_never_hides_status_or_falls_back(fhi, value, status, valid):
    fhi["values"]["2027"] = value
    fhi["statuses"]["2027"] = status
    frame = medicine_history("A10BA02")
    original = frame.copy(deep=True)
    latest = latest_medicine_observation(frame.iloc[::-1])
    assert latest["year"] == 2027
    assert latest["is_valid"] is valid
    assert latest["status"] == status
    if valid:
        assert latest["value"] == value
    else:
        assert latest["value"] is None
    if value is not None:
        assert latest["raw_value"] == value
    assert latest["measure_code"] == "AntallBrukere"
    assert latest.attrs == frame.attrs
    pd.testing.assert_frame_equal(frame, original)


def test_latest_rejects_empty_mixed_and_duplicate_series(fhi):
    frame = medicine_history("A10BA02")
    with pytest.raises(ValueError, match="tom"):
        latest_medicine_observation(frame.iloc[:0])
    with pytest.raises(ValueError, match="samme år"):
        latest_medicine_observation(pd.concat([frame, frame]))
    frame.loc[0, "measure_code"] = "DDD"
    with pytest.raises(ValueError, match="én legemiddelserie"):
        latest_medicine_observation(frame)


@pytest.mark.parametrize("fault", ["year", "selection"])
def test_unexpected_api_selection_rejected(fhi, monkeypatch, fault):
    original = FhiClient.data_frame

    def faulty(self, *args, **kwargs):
        frame = original(self, *args, **kwargs)
        if fault == "year":
            return frame.iloc[1:]
        frame.loc[0, "Atc_Verdi_code"] = "OTHER"
        return frame

    monkeypatch.setattr(FhiClient, "data_frame", faulty)
    with pytest.raises(ValueError, match="FHI returnerte"):
        medicine_history("A10BA02")


def test_medicines_catalog_capabilities():
    entry = get_dataset("fhi-lmr-825-medicines")
    assert entry.provider == "fhi"
    assert entry.geography == ()
    assert entry.dimensions == ("atc", "sex", "age", "year", "measure")
    assert entry.measures == ("users", "users_per_1000", "ddd", "population")
    assert entry.unit == "measure_dependent"
    assert entry in find_datasets("legemidler")
