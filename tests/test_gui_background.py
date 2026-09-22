"""Real window checks with synthetic providers; no network required."""

from threading import Event, get_ident
from types import SimpleNamespace

import pandas as pd
import pytest
from test_gui_jobs import pump_until

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from samfunnsdata import gui_work

pytestmark = pytest.mark.skipif(
    not Gtk.init_check(), reason="GTK display required (use xvfb-run)"
)


@pytest.mark.parametrize(
    "path",
    [
        "population",
        "population_compare",
        "nav",
        "parliament",
        "municipal",
        "parliament_compare",
        "municipal_compare",
    ],
)
def test_all_analysis_paths_work_off_main_thread(window, monkeypatch, path):
    owner = get_ident()
    provider_threads, render_threads, apply_threads = [], [], []
    population = pd.DataFrame(
        {"Tid_code": ["2021", "2025"], "value": [100, 110], "status": ["", ""]}
    )
    population.attrs["jsonstat_metadata"] = {"note": ["source note"]}
    election = pd.DataFrame(
        {
            "year": [2021, 2025],
            "party_name": ["Test", "Test"],
            "percent": [10.0, 15.0],
            "votes": [10, 15],
        }
    )
    nav = pd.DataFrame(
        {
            "year": [2024, 2025],
            "month": [1, 1],
            "unemployed": [10, 11],
            "percent": [1.0, 1.1],
        }
    )

    def record(frame):
        provider_threads.append(get_ident())
        return frame.copy(deep=True)

    monkeypatch.setattr(
        gui_work,
        "municipality_population",
        lambda place: (SimpleNamespace(name=place), record(population)),
    )
    monkeypatch.setattr(
        gui_work, "municipality_unemployment_since", lambda *_: record(nav)
    )
    monkeypatch.setattr(
        gui_work, "storting_party_history", lambda **_: record(election)
    )
    monkeypatch.setattr(
        gui_work, "municipality_party_history", lambda **_: record(election)
    )
    render = gui_work.render_chart

    def recorded_render(fig):
        render_threads.append(get_ident())
        return render(fig)

    monkeypatch.setattr(gui_work, "render_chart", recorded_render)
    apply = window._apply_analysis

    def recorded_apply(view):
        apply_threads.append(get_ident())
        apply(view)

    monkeypatch.setattr(window, "_apply_analysis", recorded_apply)
    question = SimpleNamespace(
        municipality="Test",
        party_code="A",
        first_party_code="A",
        second_party_code="B",
        since=None,
    )
    if path.startswith("population"):
        window.place.set_text("Test")
        window.compare_place.set_text("Other" if path.endswith("compare") else "")
        window.on_analyze(None)
    else:
        method = {
            "nav": "on_unemployment_question",
            "parliament": "on_election_question",
            "municipal": "on_municipal_election_question",
            "parliament_compare": "on_election_comparison",
            "municipal_compare": "on_municipal_election_comparison",
        }[path]
        getattr(window, method)(question)
    assert window.spinner.get_spinning()
    assert window.cancel_button.get_sensitive()
    pump_until(lambda: not window.jobs.active)
    assert provider_threads and all(thread != owner for thread in provider_threads)
    assert len(provider_threads) == (2 if path.endswith("compare") else 1)
    assert len(render_threads) == 1 and render_threads[0] != owner
    assert apply_threads == [owner]
    assert window.chart.get_paintable().get_width() > 0
    assert (
        not window.spinner.get_spinning() and not window.cancel_button.get_sensitive()
    )
    assert window.raw_button.get_sensitive() and window.export_button.get_sensitive()
    assert "2025" in window.status.get_text()
    assert "Metode:" in window.result.get_text() or path == "municipal"
    if path.startswith("population"):
        assert "100 → 110" in window.result.get_text()
        assert "(+10,0 %)" in window.result.get_text()
        assert window.current_series[0][1].attrs == population.attrs
        assert window.current_series[0][1]["status"].tolist() == ["", ""]
    if path.endswith("compare") and not path.startswith("population"):
        assert "Forskjell i 2025: 0,00" in window.result.get_text()


@pytest.mark.parametrize("old_error", [False, True])
def test_presented_window_repaints_and_keeps_newest_chart(
    window, monkeypatch, old_error
):
    started, release = Event(), Event()
    ticks, events = [], []
    owner = get_ident()
    with gui_work.chart_session(SimpleNamespace(checkpoint=lambda: None)):
        fig = gui_work.plt.figure(figsize=(1, 1))
        png = gui_work.render_chart(fig)

    def work(token, place, *_):
        assert get_ident() != owner
        if place == "A":
            started.set()
            assert release.wait(5)
            if old_error:
                raise ValueError("gammel feil")
        # Deliberately ignore cancellation, like a blocking external operation.
        return {
            "chart": png,
            "result": (False, place),
            "status": place,
            "source": place,
            "kind": "population",
            "series": [(place, pd.DataFrame())],
        }

    monkeypatch.setattr(gui_work, "population", work)
    window.present()
    tick = window.add_tick_callback(lambda *_: (ticks.append(get_ident()), True)[1])
    try:
        window.place.set_text("A")
        window.on_analyze(None)
        pump_until(started.is_set)
        assert window.spinner.get_spinning()
        GLib.idle_add(lambda: (events.append(get_ident()), GLib.SOURCE_REMOVE)[1])
        pump_until(lambda: ticks and events)
        assert ticks[0] == events[0] == owner
        window.place.set_text("B")
        window.on_analyze(None)
        pump_until(lambda: window.result.get_text() == "B")
        texture = window.chart.get_paintable()
        release.set()
        pump_until(lambda: window.jobs.outstanding == 0)
        assert (
            window.result.get_text()
            == window.source.get_text()
            == window.status.get_text()
            == "B"
        )
        assert window.chart.get_paintable() is texture
        assert not window.spinner.get_spinning()
    finally:
        release.set()
        window.remove_tick_callback(tick)


@pytest.mark.parametrize(
    "action", ["close", "destroy", "reset", "cancel", "invalid_input"]
)
def test_window_invalidates_running_analysis(window, monkeypatch, action):
    started, release = Event(), Event()
    calls = []
    frame = pd.DataFrame({"Tid_code": ["2025"], "value": [10]})

    def provider(place):
        calls.append(place)
        started.set()
        assert release.wait(5)
        return SimpleNamespace(name=place), frame

    monkeypatch.setattr(gui_work, "municipality_population", provider)
    monkeypatch.setattr(
        gui_work,
        "render_chart",
        lambda _: pytest.fail("Cancelled work rendered a chart"),
    )
    window.present()
    window.place.set_text("A")
    window.compare_place.set_text("B")
    try:
        window.on_analyze(None)
        pump_until(started.is_set)
        if action == "reset":
            window.lookup_action("new-analysis").activate(None)
        elif action == "cancel":
            window.cancel_button.emit("clicked")
        elif action == "invalid_input":
            window.place.set_text("")
            window.on_analyze(None)
        else:
            getattr(window, action)()
        assert not window.jobs.active
        release.set()
        pump_until(lambda: window.jobs.outstanding == 0)
        assert calls == ["A"]  # Checkpoint prevents the second provider call.
        assert window.current_series == []
        if action in {"close", "destroy"}:
            assert window.jobs.closed
        else:
            assert not window.spinner.get_spinning()
            assert window.result.get_text() == ""
    finally:
        release.set()


def test_raw_and_export_preparation_are_background_jobs(window, monkeypatch, tmp_path):
    from gi.repository import Gio

    owner = get_ident()
    threads = []
    window.current_kind = "population"
    window.current_series = [
        ("Test", pd.DataFrame({"Tid_code": ["2025"], "value": [0], "status": [""]}))
    ]
    raw, export = gui_work.raw_text, gui_work.export_csv

    def raw_work(*args):
        threads.append(get_ident())
        return raw(*args)

    def export_work(*args):
        threads.append(get_ident())
        return export(*args)

    monkeypatch.setattr(gui_work, "raw_text", raw_work)
    monkeypatch.setattr(gui_work, "export_csv", export_work)
    window.status.set_text("Original summary")
    window.on_show_raw(None)
    pump_until(lambda: not window.jobs.active)
    assert window.status.get_text() == "Original summary"
    path = tmp_path / "test.csv"
    dialog = SimpleNamespace(save_finish=lambda _: Gio.File.new_for_path(str(path)))
    window.on_export_finished(dialog, None)
    pump_until(lambda: not window.jobs.active)
    assert path.exists() and "Eksportert" in window.status.get_text()
    assert len(threads) == 2 and all(thread != owner for thread in threads)


def test_old_export_dialog_cannot_export_new_result(window, tmp_path):
    from gi.repository import Gio

    path = tmp_path / "stale.csv"
    generation = window.jobs.generation
    window.jobs.cancel()
    window.on_export_finished(
        SimpleNamespace(save_finish=lambda _: Gio.File.new_for_path(str(path))),
        None,
        ("population", []),
        generation,
    )
    assert not path.exists() and not window.jobs.active


def test_chart_sessions_serialize_creation_render_and_cleanup(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock

    from samfunnsdata.gui_jobs import JobToken

    first_inside, second_attempt, release = Event(), Event(), Event()
    lock = gui_work._chart_lock
    counter_lock = Lock()
    attempts, active, maximum = 0, 0, 0

    class ObservedLock:
        def __enter__(self):
            nonlocal attempts
            with counter_lock:
                attempts += 1
                if attempts == 2:
                    second_attempt.set()
            lock.acquire()

        def __exit__(self, *_args):
            lock.release()

    monkeypatch.setattr(gui_work, "_chart_lock", ObservedLock())
    previous = set(gui_work.plt.get_fignums())

    def render(number):
        nonlocal active, maximum
        with gui_work.chart_session(JobToken(number)):
            with counter_lock:
                active += 1
                maximum = max(maximum, active)
            try:
                fig = gui_work.plt.figure(figsize=(1, 1))
                if number == 1:
                    first_inside.set()
                    assert release.wait(5)
                return gui_work.render_chart(fig)
            finally:
                with counter_lock:
                    active -= 1

    with ThreadPoolExecutor(max_workers=2) as executor:
        a = executor.submit(render, 1)
        try:
            assert first_inside.wait(5)
            b = executor.submit(render, 2)
            assert second_attempt.wait(5)
            assert active == maximum == 1
        finally:
            release.set()
        assert a.result(timeout=5).startswith(b"\x89PNG")
        assert b.result(timeout=5).startswith(b"\x89PNG")
    assert maximum == 1 and active == 0
    assert set(gui_work.plt.get_fignums()) == previous


def test_gui_recovers_after_provider_and_render_failure(window, monkeypatch):
    frame = pd.DataFrame({"Tid_code": ["2025"], "value": [10]})
    def fail(*_args):
        raise ValueError("Lesbar kildefeil")
    monkeypatch.setattr(gui_work, "municipality_population", fail)
    window.place.set_text("Test")
    window.on_analyze(None)
    pump_until(lambda: not window.jobs.active)
    assert window.status.get_text() == "Lesbar kildefeil"
    assert not window.spinner.get_spinning()
    assert window.current_series == []
    monkeypatch.setattr(gui_work, "municipality_population", lambda place: (SimpleNamespace(name=place), frame))
    render = gui_work.render_chart
    monkeypatch.setattr(gui_work, "render_chart", fail)
    window.on_analyze(None)
    pump_until(lambda: not window.jobs.active)
    assert window.status.get_text() == "Lesbar kildefeil"
    assert not window.spinner.get_spinning()
    assert window.current_series == []
    monkeypatch.setattr(gui_work, "render_chart", render)
    window.on_analyze(None)
    pump_until(lambda: not window.jobs.active)
    assert window.status.get_text() == "Test · 2025–2025"
    assert window.raw_button.get_sensitive()


def test_nav_fetch_and_parse_serialized_for_existing_file_cache(window, monkeypatch):
    from samfunnsdata.gui_jobs import GuiJobs

    first_inside, second_attempt, release = Event(), Event(), Event()
    provider_calls = []
    original_lock = gui_work._nav_lock
    attempts = 0

    class ObservedLock:
        def __enter__(self):
            nonlocal attempts
            attempts += 1
            if attempts == 2:
                second_attempt.set()
            original_lock.acquire()

        def __exit__(self, *_args):
            original_lock.release()

    monkeypatch.setattr(gui_work, "_nav_lock", ObservedLock())
    frame = pd.DataFrame({"year": [2025], "month": [1], "unemployed": [10], "percent": [1.]})
    def provider(place, _since):
        provider_calls.append(place)
        if place == "A":
            first_inside.set()
            assert release.wait(5)
        return frame
    monkeypatch.setattr(gui_work, "municipality_unemployment_since", provider)
    applied = []
    # Independent controllers also share the NAV lock (e.g. two windows).
    other = GuiJobs(lambda _: None, pytest.fail)
    try:
        window.on_unemployment_question(SimpleNamespace(municipality="A", since=None))
        pump_until(first_inside.is_set)
        other.submit(lambda token: gui_work.unemployment_question(token, SimpleNamespace(municipality="B", since=None)), applied.append)
        pump_until(second_attempt.is_set)
        assert provider_calls == ["A"]
        release.set()
        pump_until(lambda: not window.jobs.active and not other.active)
        assert provider_calls == ["A", "B"]
        assert applied[0]["series"][0][0] == "B"
    finally:
        release.set()
        other.close()
        pump_until(lambda: other.outstanding == 0)
