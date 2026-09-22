import pytest

from samfunnsdata.catalog import (
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


def test_find_dataset_from_natural_language():
    results = find_datasets(
        "Hvordan har arbeidsledigheten i Trondheim utviklet seg?"
    )

    assert results
    assert results[0].id == "nav-registered-unemployed"


def test_find_dataset_from_population_question():
    results = find_datasets(
        "Vis befolkningen i Trondheim"
    )

    assert results
    assert results[0].id == "ssb-07459-population"


def test_catalog_search_returns_no_irrelevant_match():
    assert find_datasets("bananer romskip pingvin") == []


def test_parliament_catalog_matches_implemented_adapter():
    import importlib

    dataset = get_dataset("valg-parliament-results")
    assert dataset.queryable
    assert dataset.interfaces == ("python", "gui")
    module, name = dataset.adapter.split(":")
    assert callable(getattr(importlib.import_module(module), name))
    assert find_datasets("stortingsvalg")[0] == dataset
    assert dataset.provider == "elections"


def test_dataset_support_accepts_string_values():
    dataset = __import__("samfunnsdata.catalog", fromlist=["Dataset", "SupportStatus"]).Dataset(
        id="ssb-discovered-table",
        provider="ssb",
        title="Oppdaget SSB-tabell",
        topic="demography",
        source="SSB",
        geography=("municipality",),
        time_resolution="year",
        dimensions=("geography", "year"),
        unit="persons",
        description="En oppdaget tabell som ikke er semantisk støttet i applikasjonen.",
        period="2020–2024",
        measures=("population",),
        definition="Oppdaget fra SSB uten at applikasjonen implementerer analyseadapter.",
        support="discovered",
    )

    assert dataset.support == __import__("samfunnsdata.catalog", fromlist=["SupportStatus"]).SupportStatus.DISCOVERED
    assert dataset.queryable is False
    assert dataset.support_label == "Katalogisert – kan ikke hentes i Samfunnsdata"
