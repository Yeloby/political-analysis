"""Receipt actions use the same generation/cancellation rules as analyses."""

import json
from threading import Event, get_ident
from types import SimpleNamespace

import pandas as pd
import pytest
from test_gui_jobs import pump_until

from samfunnsdata import gui, gui_work
from samfunnsdata.providers.norway.ssb import Municipality
from samfunnsdata.results import DataReceipt


def load(window, monkeypatch, compare=False):
    frame = pd.DataFrame(
        {"Tid_code": ["2020", "2021"], "value": [0, 10], "status": ["", ""]}
    )
    monkeypatch.setattr(
        gui_work,
        "municipality_population",
        lambda place: (Municipality(place, place), frame),
    )
    window.place.set_text("Ås")
    window.compare_place.set_text("Bergen" if compare else "")
    window.on_analyze(None)
    pump_until(lambda: not window.jobs.active)
    assert window.current_result is not None
    return window.current_result


@pytest.mark.parametrize("compare", [False, True])
def test_receipt_open_csv_and_json_export(window, monkeypatch, tmp_path, compare):
    result = load(window, monkeypatch, compare)
    assert window.receipt_button.get_sensitive()
    assert window.receipt_export_button.get_sensitive()
    assert "0 → 10" in window.result.get_text()
    windows = []
    original = gui.text_window

    def show(parent, title, text):
        windows.append((get_ident(), title, text))
        return original(parent, title, text)

    monkeypatch.setattr(gui, "text_window", show)
    window.on_show_receipt(None)
    assert not window.receipt_button.get_sensitive()
    pump_until(lambda: not window.jobs.active)
    assert windows[0][0] == get_ident()
    assert windows[0][1] == "Datakvittering"
    assert "Hentet fra kilden: Ukjent" in windows[0][2]
    assert "Prosentvis endring fra null" in windows[0][2]
    json_path = tmp_path / "population.receipt.json"
    dialog = SimpleNamespace(
        save_finish=lambda _: SimpleNamespace(get_path=lambda: str(json_path))
    )
    window.on_receipt_export_finished(
        dialog, None, result.receipt, window.jobs.generation
    )
    pump_until(lambda: not window.jobs.active)
    assert DataReceipt.from_json(json_path.read_text()) == result.receipt
    csv_path = tmp_path / "population.csv"
    dialog = SimpleNamespace(
        save_finish=lambda _: SimpleNamespace(get_path=lambda: str(csv_path))
    )
    window.on_export_finished(dialog, None)
    pump_until(lambda: not window.jobs.active)
    assert pd.read_csv(csv_path)["Innbyggere"].tolist() == (
        [0, 10] * (2 if compare else 1)
    )
    assert (
        json.loads(json_path.read_text())["series"][0]["provenance"]["fetched_at"]
        is None
    )
    window.lookup_action("new-analysis").activate(None)
    assert window.current_result is None
    assert not window.receipt_button.get_sensitive()
    assert not window.receipt_export_button.get_sensitive()


@pytest.mark.parametrize("action", ["cancel", "reset", "close"])
def test_receipt_preparation_stays_background_and_stale_view_is_dropped(
    window, monkeypatch, action
):
    load(window, monkeypatch)
    entered, release = Event(), Event()
    threads, shown = [], []
    original = gui_work.receipt_text

    def prepare(*args):
        threads.append(get_ident())
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(gui_work, "receipt_text", prepare)
    monkeypatch.setattr(gui, "text_window", lambda *args: shown.append(args))
    window.on_show_receipt(None)
    try:
        pump_until(entered.is_set)
        assert threads[0] != get_ident()
        # The owner thread still processes cancellation while preparation is blocked.
        if action == "cancel":
            window.on_cancel(None)
        elif action == "reset":
            window.lookup_action("new-analysis").activate(None)
        else:
            window.destroy()
    finally:
        release.set()
        pump_until(lambda: window.jobs.outstanding == 0)
    assert shown == []


def test_stale_receipt_dialog_cannot_export(window, monkeypatch, tmp_path):
    result = load(window, monkeypatch)
    generation = window.jobs.generation
    path = tmp_path / "old.receipt.json"
    window.jobs.cancel()
    dialog = SimpleNamespace(
        save_finish=lambda _: pytest.fail("Stale dialog must not finish")
    )
    window.on_receipt_export_finished(dialog, None, result.receipt, generation)
    assert not path.exists()


def test_nonpopulation_analysis_clears_receipt(window, monkeypatch):
    load(window, monkeypatch)
    frame = pd.DataFrame(
        {
            "year": [2021, 2025],
            "percent": [10, 20],
            "votes": [1, 2],
            "party_name": ["A", "A"],
        }
    )
    monkeypatch.setattr(gui_work, "storting_party_history", lambda **kwargs: frame)
    window.on_election_question(
        SimpleNamespace(municipality="Ås", party_code="A", since=None)
    )
    pump_until(lambda: not window.jobs.active)
    assert window.current_result is None
    assert not window.receipt_button.get_sensitive()
