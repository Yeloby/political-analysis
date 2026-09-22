from copy import deepcopy

import pandas as pd
import pytest

from samfunnsdata.analysis import summarize_series
from samfunnsdata.cache import JsonCache
from samfunnsdata.providers.norway.ssb import jsonstat_to_frame


@pytest.mark.parametrize("values,change,percent", [
    ([0, 5], 5, None), ([0, 0], 0, None),
    ([None, 5], None, None), ([5, None], None, None),
    ([5, None, 10], 5, 100.0),
])
def test_summary_zero_and_missing(values, change, percent):
    years = [str(2020 + i) for i in range(len(values))]
    frame = pd.DataFrame({"Tid_code": years, "value": values})
    original = frame.copy(deep=True)
    result = summarize_series(frame)
    assert result.first_year == years[0]
    assert result.last_year == years[-1]
    assert result.first_value == values[0]
    assert result.last_value == values[-1]
    assert result.change == change
    assert result.percent_change == percent
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("status", [":", "..", ".", "provisional", "unknown"])
def test_summary_flagged_latest_not_used_as_number(status):
    frame = pd.DataFrame({"Tid_code": ["2024", "2025"], "value": [10, 20], "status": ["", status]})
    result = summarize_series(frame)
    assert result.last_year == "2025"
    assert result.last_value is None
    assert result.change is None
    assert result.percent_change is None
    assert result.last_status == status
    assert frame["value"].tolist() == [10, 20]


@pytest.mark.parametrize("status,expected", [
    (["", ":", "p", "unknown"], ["", ":", "p", "unknown"]),
    ({"1": ":", "2": "p"}, [None, ":", "p", None]),
    ("p", ["p"] * 4),
])
def test_ssb_status_and_metadata(status, expected):
    raw = {
        "id": ["A", "Tid"], "size": [2, 2],
        "dimension": {
            "Tid": {"category": {"index": ["2024", "2025"]}},
            "A": {"category": {"index": {"b": 1, "a": 0}, "label": {"a": "Alpha", "b": "Beta"}}},
        },
        "value": [0, None, 3, 4], "status": status,
        "updated": "2026-01-01", "extension": {"status": {"p": "Provisional"}},
    }
    original = deepcopy(raw)
    frame = jsonstat_to_frame(raw)
    assert frame["status"].tolist() == expected
    assert frame["A_code"].tolist() == ["a", "a", "b", "b"]
    assert frame["A"].tolist() == ["Alpha", "Alpha", "Beta", "Beta"]
    assert frame["Tid_code"].tolist() == ["2024", "2025", "2024", "2025"]
    assert frame["value"].iloc[0] == 0
    assert pd.isna(frame["value"].iloc[1])
    assert frame["value"].iloc[2:].tolist() == [3, 4]
    assert frame.attrs["jsonstat_metadata"]["extension"] == raw["extension"]
    frame.attrs["jsonstat_metadata"]["extension"]["status"]["p"] = "Changed"
    assert raw == original


@pytest.mark.parametrize("bad", [b'not JSON', b'{"value":', b'\xff'])
def test_corrupt_cache_allows_replacement(tmp_path, bad):
    cache = JsonCache(tmp_path)
    path = cache.set("test", {"table": 1}, {"value": 3})
    path.write_bytes(bad)
    assert cache.get("test", {"table": 1}) is None
    cache.set("test", {"table": 1}, {"value": 7})
    assert cache.get("test", {"table": 1}) == {"value": 7}


def test_failed_cache_serialization_keeps_previous_entry(tmp_path):
    cache = JsonCache(tmp_path)
    cache.set("test", {}, {"value": 5})
    with pytest.raises(TypeError):
        cache.set("test", {}, object())
    assert cache.get("test", {}) == {"value": 5}


def test_atomic_cache_replacement_and_failed_publish(tmp_path, monkeypatch):
    import json

    from samfunnsdata import cache as cache_module

    cache = JsonCache(tmp_path)
    target = cache.set("test", {}, {"old": 1})
    replace = cache_module.os.replace

    def checked_replace(source, destination):
        assert json.loads(target.read_text()) == {"old": 1}
        assert json.loads(source.read_text()) == {"new": 2}
        assert source.parent == target.parent
        replace(source, destination)
    monkeypatch.setattr(cache_module.os, "replace", checked_replace)
    cache.set("test", {}, {"new": 2})
    assert cache.get("test", {}) == {"new": 2}

    def failed_replace(*_args):
        raise OSError("Synthetic disk failure")
    monkeypatch.setattr(cache_module.os, "replace", failed_replace)
    with pytest.raises(OSError):
        cache.set("test", {}, {"third": 3})
    assert cache.get("test", {}) == {"new": 2}
    assert list(tmp_path.iterdir()) == [target]


def test_corrupt_ssb_cache_refetches_once(tmp_path, monkeypatch):
    import httpx

    from samfunnsdata.providers.norway.ssb import SsbClient

    client = SsbClient()
    client.cache = JsonCache(tmp_path)
    params = {"lang": "no"}
    path = client.cache.set("ssb-codelist", {"codelist": "test", **params}, {})
    path.write_text("{")
    calls = []

    def get(url, **_kwargs):
        calls.append(url)
        return httpx.Response(200, json={"codes": ["a"]}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", get)
    assert client.get_codelist("test") == {"codes": ["a"]}
    assert client.get_codelist("test") == {"codes": ["a"]}
    assert len(calls) == 1


@pytest.mark.parametrize("command", ["population", "compare"])
@pytest.mark.parametrize("values,status", [([0, 5], ""), ([5, None], ""), ([5, 10], ":")])
def test_cli_missing_and_zero(monkeypatch, capsys, command, values, status):
    import sys
    from types import SimpleNamespace

    from samfunnsdata import cli

    frame = pd.DataFrame({"Tid_code": ["2024", "2025"], "value": values, "status": ["", status]})
    monkeypatch.setattr(cli, "municipality_population", lambda place: (SimpleNamespace(name=place, code="K-1"), frame))
    args = ["samfunnsdata", command, "Test"] + (["Other"] if command == "compare" else [])
    monkeypatch.setattr(sys, "argv", args)
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "ikke beregnbart" in output
    assert "2025" in output
    assert "nan" not in output.lower()
    if command == "population" and status:
        assert "status: :" in output


def test_election_alignment_preserves_raw_and_rejects_mismatched_area():
    from samfunnsdata.analysis import align_election_series

    first = pd.DataFrame({"year": [2025, 2017, 2021], "percent": [30, 10, None], "area_number": ["1"] * 3})
    first.attrs["source"] = {"title": "original"}
    second = pd.DataFrame({"year": [2017, 2021, 2025], "percent": [5, 6, 7], "area_number": ["1"] * 3})
    original = first.copy(deep=True)
    a, b = align_election_series(first, second)
    assert a["year"].tolist() == b["year"].tolist() == [2017, 2021, 2025]
    assert pd.isna(a.iloc[1]["percent"])
    assert a.attrs == first.attrs
    pd.testing.assert_frame_equal(first, original)
    second.loc[2, "area_number"] = "2"
    with pytest.raises(ValueError, match="ulike area_number"):
        align_election_series(first, second)


def test_election_flagged_common_year_does_not_fall_back():
    from samfunnsdata.analysis import align_election_series

    a = pd.DataFrame({"year": [2021, 2025], "percent": [10, 20]})
    b = pd.DataFrame({"year": [2021, 2025], "percent": [5, 15], "status": ["", ":"]})
    with pytest.raises(ValueError, match="2025"):
        align_election_series(a, b)


@pytest.mark.parametrize("status", [["p"], {"2": "p"}, 7])
def test_ssb_rejects_malformed_status(status):
    raw = {"id": ["Tid"], "size": [2], "dimension": {"Tid": {"category": {"index": ["2024", "2025"]}}},
           "value": [1, 2], "status": status}
    with pytest.raises((ValueError, TypeError)):
        jsonstat_to_frame(raw)


def test_ssb_sparse_values_remain_missing():
    raw = {"id": ["Tid"], "size": [2], "dimension": {"Tid": {"category": {"index": ["2024", "2025"]}}},
           "value": {"0": 0}, "status": {"1": ":"}}
    frame = jsonstat_to_frame(raw)
    assert frame.iloc[0]["value"] == 0
    assert pd.isna(frame.iloc[1]["value"])
    assert frame.iloc[1]["status"] == ":"


def test_population_chart_keeps_missing_and_flagged_gaps():
    import matplotlib.pyplot as plt

    from samfunnsdata.charts import population_figure

    frame = pd.DataFrame({"Tid_code": ["2023", "2024", "2025"], "value": [0, None, 42], "status": ["", "", ":"]})
    fig = population_figure([("Test", frame)], "Test")
    try:
        values = fig.axes[0].lines[0].get_ydata(orig=False)
        assert values[0] == 0
        assert pd.isna(values[1]) and pd.isna(values[2])
        assert frame.iloc[2]["value"] == 42
    finally:
        plt.close(fig)


def test_nav_duplicate_zero_characterization():
    """Documents existing selection, not evidence that zero is a placeholder."""
    from samfunnsdata.providers.norway.nav import municipality_unemployment

    frame = pd.DataFrame({"municipality_name": ["Test", "Test"], "municipality_code": ["1", "2"],
                          "year": [2025, 2025], "month": [1, 1], "unemployed": [0, 5], "percent": [None, None]})
    assert municipality_unemployment(frame, "Test")["unemployed"].tolist() == [5]
    assert municipality_unemployment(frame.iloc[:1], "Test")["unemployed"].tolist() == [0]
