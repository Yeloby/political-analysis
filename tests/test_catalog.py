import pytest

from political_analysis.catalog import (
    datasets,
    find_datasets,
    get_dataset,
)


def test_catalog_contains_current_datasets():
    ids = {dataset.id for dataset in datasets()}

    assert "ssb-07459-population" in ids
    assert "valg-municipality-results" in ids
    assert "nav-registered-unemployed" in ids


def test_find_dataset_by_title():
    results = find_datasets("befolkning")

    assert [dataset.id for dataset in results] == [
        "ssb-07459-population"
    ]


def test_find_dataset_by_description():
    results = find_datasets("ledige")

    assert [dataset.id for dataset in results] == [
        "nav-registered-unemployed"
    ]


def test_get_dataset():
    dataset = get_dataset("nav-registered-unemployed")

    assert dataset.provider == "nav"
    assert dataset.time_resolution == "month"


def test_unknown_dataset():
    with pytest.raises(KeyError, match="Ukjent datasett"):
        get_dataset("andeby")


def test_dataset_metadata():
    dataset = get_dataset("nav-registered-unemployed")

    assert dataset.period == "1995–2025"
    assert dataset.measures == ("unemployed", "percent")
    assert dataset.limitations
