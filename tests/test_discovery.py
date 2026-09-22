import json

import pytest

from samfunnsdata import catalog, network
from samfunnsdata.cache import JsonCache
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


def test_supported_support_is_not_upgraded_by_remote_discovery():
    local = catalog.Dataset(
        id="ssb-07459-population",
        provider="ssb",
        title="Befolkning",
        topic="demography",
        source="SSB",
        geography=("municipality",),
        time_resolution="year",
        dimensions=("geography", "year"),
        unit="persons",
        description="Lokalt støttet datasett.",
        period="1986–",
        measures=("population",),
        definition="Lokalt definert og støttet.",
        support=SupportStatus.SUPPORTED,
        adapter="samfunnsdata.providers.norway.ssb:municipality_population",
        interfaces=("python", "gui", "cli"),
        table_id="07459",
    )
    registry = catalog.DatasetRegistry(curated=(local,), discovered=())
    remote = _dataset_from_record({"id": "07459", "title": "Befolkning", "support": "discovered"}, provider="ssb")

    result = registry.register_discovered(remote)

    assert result is local
    assert result.support == SupportStatus.SUPPORTED


def test_planned_support_is_preserved_across_discovery_merge():
    local = catalog.Dataset(
        id="ssb-planned-table",
        provider="ssb",
        title="Planlagt tabell",
        topic="demography",
        source="SSB",
        geography=("municipality",),
        time_resolution="year",
        dimensions=("geography", "year"),
        unit="persons",
        description="Planlagt datasett.",
        period="2020–2024",
        measures=("population",),
        definition="Lokalt planlagt.",
        support=SupportStatus.PLANNED,
        table_id="98765",
    )
    registry = catalog.DatasetRegistry(curated=(local,), discovered=())
    remote = _dataset_from_record({"id": "98765", "title": "Planlagt tabell", "support": "discovered"}, provider="ssb")

    result = registry.register_discovered(remote)

    assert result is local
    assert result.support == SupportStatus.PLANNED


def test_remote_executor_fields_do_not_create_executable_metadata():
    dataset = _dataset_from_record(
        {
            "id": "bad-001",
            "title": "Skadelig tabell",
            "adapter": "evil.module.Class",
            "module": "subprocess",
            "class": "os.system",
            "support": "discovered",
        },
        provider="ssb",
    )

    assert dataset.support == SupportStatus.DISCOVERED
    assert dataset.adapter is None
    assert dataset.interfaces == ()


def test_snapshot_rejects_invalid_or_malformed_payloads(tmp_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not valid json}", encoding="utf-8")
    with pytest.raises(ValueError):
        catalog._load_ssb_snapshot(bad_json)

    wrong_version = tmp_path / "wrong-version.json"
    wrong_version.write_text(json.dumps({"schema_version": 2, "tables": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        catalog._load_ssb_snapshot(wrong_version)

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({"schema_version": 1, "tables": ["nope", {"id": "abc"}] }), encoding="utf-8")
    datasets = catalog._load_ssb_snapshot(malformed)
    assert datasets[0].id == "ssb-abc"


def test_ssb_search_traverses_pages_and_deduplicates(monkeypatch, tmp_path):
    calls = []
    pages = {
        1: {"page": 1, "pages": 2, "items": [{"id": "1", "label": "A"}, {"id": "2", "label": "B"}]},
        2: {"page": 2, "pages": 2, "items": [{"id": "2", "label": "B"}, {"id": "3", "label": "C"}]},
    }

    def fake_request(source, purpose, method, url, **kwargs):
        calls.append(kwargs.get("params", {}).copy())
        page = int(kwargs.get("params", {}).get("page", 1))
        payload = pages[page]
        return type("Resp", (), {"json": lambda self: payload, "raise_for_status": lambda self: None})()

    monkeypatch.setattr("samfunnsdata.network.request", fake_request)
    client = __import__("samfunnsdata.providers.norway.ssb", fromlist=["SsbClient"]).SsbClient()
    client.cache = JsonCache(root=tmp_path)

    tables = client.search("test")

    assert [table.id for table in tables] == ["1", "2", "3"]
    assert calls == [{"query": "test", "lang": "no", "pagesize": 100, "page": 1}, {"query": "test", "lang": "no", "pagesize": 100, "page": 2}]
