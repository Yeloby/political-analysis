import pandas as pd
import pytest

from samfunnsdata.analysis import filter_since, summarize_series


def sample_frame():
    return pd.DataFrame(
        [
            {"Tid": "2000", "Tid_code": "2000", "value": 100},
            {"Tid": "2010", "Tid_code": "2010", "value": 120},
            {"Tid": "2020", "Tid_code": "2020", "value": 150},
        ]
    )


def test_filter_since():
    frame = filter_since(sample_frame(), 2010)

    assert list(frame["Tid_code"]) == ["2010", "2020"]


def test_filter_since_none():
    frame = sample_frame()

    result = filter_since(frame, None)

    assert len(result) == 3


def test_summarize_series():
    summary = summarize_series(sample_frame())

    assert summary.first_year == "2000"
    assert summary.last_year == "2020"
    assert summary.first_value == 100
    assert summary.last_value == 150
    assert summary.change == 50
    assert summary.percent_change == 50.0


def test_summarize_empty_series():
    with pytest.raises(ValueError, match="tom dataserie"):
        summarize_series(pd.DataFrame())
