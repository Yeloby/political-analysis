from dataclasses import replace
from importlib import import_module

import pytest

from samfunnsdata import catalog
from samfunnsdata.catalog import (
    SupportStatus,
    datasets,
    find_datasets,
    get_dataset,
    get_source,
)
from samfunnsdata.help import ATTRIBUTION, application_version, help_sections


def test_registered_adapters_exist():
    for item in datasets():
        assert item.queryable
        assert item.support == SupportStatus.SUPPORTED
        module, name = item.adapter.split(":")
        assert callable(getattr(import_module(module), name))
        assert get_source(item.provider).authority


def test_fhi_is_not_advertised_as_gui():
    item = get_dataset("fhi-lmr-825-medicines")
    assert item.interfaces == ("python",)
    assert item.support_label == "Støttet: Python/API"
    assert item.official_statistics is None


@pytest.mark.parametrize("status", [SupportStatus.DISCOVERED, SupportStatus.PLANNED])
def test_unimplemented_datasets_remain_searchable_but_not_queryable(monkeypatch, status):
    item = replace(datasets()[0], id="test-unimplemented", support=status, adapter=None, interfaces=())
    monkeypatch.setattr(catalog, "DATASETS", (item,))
    assert find_datasets("legemidler", support=status) == [item]
    assert find_datasets("", support=SupportStatus.SUPPORTED) == []
    assert not item.queryable
    assert "Støttet:" not in item.support_label


@pytest.mark.parametrize("changes", [
    {"adapter": None}, {"interfaces": ()},
    {"support": SupportStatus.DISCOVERED}, {"support": SupportStatus.PLANNED},
])
def test_inconsistent_support_rejected(changes):
    with pytest.raises(ValueError):
        replace(datasets()[0], **changes)


def test_invalid_status_rejected():
    with pytest.raises(TypeError):
        replace(datasets()[0], support="supported")


def test_registry_filters_and_authority_search():
    assert [x.provider for x in find_datasets("", provider="fhi")] == ["fhi"]
    assert [x.provider for x in find_datasets("Folkehelseinstituttet")] == ["fhi"]
    assert find_datasets("", provider="unknown") == []
    assert find_datasets("", support=SupportStatus.DISCOVERED) == []
    with pytest.raises(KeyError):
        get_source("unknown")


def test_help_resource_sections_and_scope():
    sections = help_sections()
    assert {x.id for x in sections} == {
        "start", "capabilities", "questions", "browse", "concepts", "missing",
        "methods", "export", "limits", "troubleshooting",
    }
    assert len({x.id for x in sections}) == len(sections)
    assert all(x.title and x.text for x in sections)
    text = "\n".join(x.text for x in sections)
    assert "ikke som spørsmål eller analyser i GUI-en" in text
    assert "Manglende data er ikke null" in text
    assert "ikke en full datakvittering" in text
    assert ATTRIBUTION == "Laget av Johan Slåttavik"


def test_version_fallback(monkeypatch):
    import samfunnsdata.help as help_module
    from samfunnsdata import __version__

    def absent(_name):
        raise help_module.PackageNotFoundError
    monkeypatch.setattr(help_module, "version", absent)
    assert application_version() == __version__
    monkeypatch.setattr(help_module, "version", lambda _name: "9.8.7")
    assert application_version() == "9.8.7"
