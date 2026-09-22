import json

import pytest

from samfunnsdata import catalog, network
from samfunnsdata.catalog import (
    SupportStatus,
    _dataset_from_record,
    find_datasets,
    load_discovered_ssb_snapshot,
    refresh_ssb_discovery_snapshot,
)


@pytest.fixture(autouse=True)
def reset_network_mode():
    previous_discovered = catalog.DISCOVERED_DATASETS
    previous_registry = catalog.DATASET_REGISTRY
    catalog.DISCOVERED_DATASETS = ()
    catalog.DATASET_REGISTRY = catalog.DatasetRegistry(curated=catalog.DATASETS, discovered=())
    network.set_mode(network.NetworkMode.ONLINE)
    yield
    catalog.DISCOVERED_DATASETS = previous_discovered
    catalog.DATASET_REGISTRY = previous_registry
    network.set_mode(network.NetworkMode.ONLINE)


def test_discovered_metadata_is_not_supported():
    with pytest.raises(TypeError):
        _dataset_from_record({"id": "07459", "title": "Befolkning", "support": "supported"})


def test_refresh_writes_snapshot_and_loads_it(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "ssb-discovery.json"
    records = [
        {
            "id": "12345",
            "title": "Ny SSB-tabell",
            "description": "Kort beskrivelse",
            "topic": "demography",
            "keywords": ["befolkning", "kommuner"],
            "support": "discovered",
            "dimensions": ["region", "year"],
            "period": "2020-2024",
            "source": "SSB",
        },
        {
            "id": "12345",
            "title": "Ny SSB-tabell",
            "support": "discovered",
        },
    ]
    monkeypatch.setattr(
        "samfunnsdata.catalog._fetch_ssb_metadata_records",
        lambda *args, **kwargs: tuple(records),
    )

    refreshed = refresh_ssb_discovery_snapshot(snapshot_path)

    assert snapshot_path.exists()
    assert [dataset.id for dataset in refreshed] == ["ssb-12345"]
    assert load_discovered_ssb_snapshot(snapshot_path)[0].support == SupportStatus.DISCOVERED
    assert find_datasets("befolkning")[0].id in {"ssb-12345", "ssb-07459-population"}


def test_failed_refresh_keeps_old_snapshot(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "ssb-discovery.json"
    old = {"schema_version": 1, "provider": "ssb", "tables": [{"id": "ssb-12345", "title": "Gammel tabell", "table_id": "12345", "support": "discovered", "provider": "ssb", "source": "SSB", "description": "", "topic": "demography", "dimensions": [], "period": "2020", "source_url": "https://example.com", "access_url": "https://example.com/data", "format": "json-stat2", "updated_at": None, "measures": [], "definition": "", "geography": [], "unit": "persons", "keywords": []}]}
    snapshot_path.write_text(json.dumps(old), encoding="utf-8")
    monkeypatch.setattr("samfunnsdata.catalog._fetch_ssb_metadata_records", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        refresh_ssb_discovery_snapshot(snapshot_path)

    assert json.loads(snapshot_path.read_text(encoding="utf-8")) == old


def test_cache_only_uses_existing_snapshot_and_zero_http(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "ssb-discovery.json"
    snapshot_path.write_text(json.dumps({"schema_version": 1, "provider": "ssb", "tables": [{"id": "ssb-98765", "title": "Cache-tabell", "table_id": "98765", "support": "discovered", "provider": "ssb", "source": "SSB", "description": "", "topic": "demography", "dimensions": ["year"], "period": "2024", "source_url": "https://example.com", "access_url": "https://example.com/data", "format": "json-stat2", "updated_at": None, "measures": [], "definition": "", "geography": [], "unit": "persons", "keywords": []}]}) , encoding="utf-8")
    network.set_mode(network.NetworkMode.CACHE_ONLY)
    called = False

    def fail(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("HTTP call should not occur")

    monkeypatch.setattr("samfunnsdata.catalog._fetch_ssb_metadata_records", fail)

    datasets_from_snapshot = refresh_ssb_discovery_snapshot(snapshot_path)
    assert datasets_from_snapshot[0].id == "ssb-98765"
    assert called is False

    missing_snapshot = tmp_path / "missing.json"
    with pytest.raises(network.CacheOnlyMiss):
        refresh_ssb_discovery_snapshot(missing_snapshot)


def test_unsupported_remote_metadata_is_ignored_in_registry_merge():
    dataset = _dataset_from_record({"id": "98765", "title": "Tabell", "support": "discovered"})
    assert dataset.support == SupportStatus.DISCOVERED
    assert dataset.queryable is False
    assert dataset.adapter is None
