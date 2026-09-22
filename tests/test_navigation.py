"""Offline GTK checks; run with xvfb-run on headless Linux."""
import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from test_gui_jobs import pump_until

from samfunnsdata.help import ATTRIBUTION
from samfunnsdata.navigation import about_window, catalog_window, help_window

pytestmark = pytest.mark.skipif(not Gtk.init_check(), reason="GTK display required (use xvfb-run)")


def children(widget):
    yield widget
    child = widget.get_first_child()
    while child:
        yield from children(child)
        child = child.get_next_sibling()


def test_result_actions_and_reset(window, monkeypatch):
    assert not window.lookup_action("export-data").get_enabled()
    assert not window.lookup_action("raw-data").get_enabled()
    assert not window.lookup_action("source-info").get_enabled()
    called = []
    monkeypatch.setattr(window, "on_export", lambda _: called.append("export"))
    window.current_series = [("test", object())]
    window.current_kind = "population"
    window.question.set_text("test")
    window.result.set_text("result")
    window.source.set_text("source")
    window.raw_button.set_sensitive(True)
    window.export_button.set_sensitive(True)
    assert window.lookup_action("source-info").get_enabled()
    window.lookup_action("export-data").activate(None)
    assert called == ["export"]
    window.lookup_action("new-analysis").activate(None)
    assert window.current_series == []
    assert window.current_kind is None
    assert window.result.get_text() == window.source.get_text() == window.question.get_text() == ""
    assert not window.lookup_action("export-data").get_enabled()
    assert not window.lookup_action("raw-data").get_enabled()


def test_manual_toggle_and_menus(window):
    action = window.lookup_action("manual")
    assert not action.get_state().get_boolean()
    assert not window.place.get_parent().get_visible()
    action.activate(None)
    assert window.place.get_parent().get_visible()
    action.activate(None)
    assert not window.place.get_parent().get_visible()
    bar = window.get_child().get_first_child()
    model = bar.get_menu_model()
    assert [model.get_item_attribute_value(i, "label", None).get_string()
            for i in range(model.get_n_items())] == ["Fil", "Data", "Vis", "Hjelp"]
    for i in range(model.get_n_items()):
        menu = model.get_item_link(i, "submenu")
        for j in range(menu.get_n_items()):
            name = menu.get_item_attribute_value(j, "action", None).get_string()
            assert window.lookup_action(name.removeprefix("win.")) is not None


def test_help_about_catalog_render(window):
    about = about_window(window)
    labels = [x.get_text() for x in children(about.get_child()) if isinstance(x, Gtk.Label)]
    assert "Samfunnsdata" in labels
    assert ATTRIBUTION == labels[-1]
    assert "Lisens: MIT" in labels
    help_view = help_window(window)
    stack = next(x for x in children(help_view) if isinstance(x, Gtk.Stack))
    assert stack.get_pages().get_n_items() == 11
    catalog = catalog_window(window)
    view = next(x for x in children(catalog) if isinstance(x, Gtk.TextView))
    buffer = view.get_buffer()
    assert "Støttet: Python/API" in buffer.get_text(*buffer.get_bounds(), True)
    search = next(x for x in children(catalog) if isinstance(x, Gtk.SearchEntry))
    search.set_text("zzzz-no-match")
    search.emit("search-changed")
    assert "Ingen treff" in buffer.get_text(*buffer.get_bounds(), True)


@pytest.mark.parametrize("provider,handler,years", [
    ("storting_party_history", "on_election_comparison", [2017, 2021, 2025]),
    ("municipality_party_history", "on_municipal_election_comparison", [2015, 2019, 2023]),
])
@pytest.mark.parametrize("case", ["same", "different", "missing", "no_common"])
def test_election_comparison_periods(window, monkeypatch, provider, handler, years, case):
    from types import SimpleNamespace

    import pandas as pd

    from samfunnsdata import gui_work

    first = pd.DataFrame({"party_name": ["A"] * 3, "year": years, "percent": [10, 20, 30]})
    second_years = years[:-1] if case == "different" else years
    if case == "no_common":
        second_years = [years[0] - 4]
    second = pd.DataFrame({"party_name": ["B"] * len(second_years), "year": second_years,
                           "percent": [5] * len(second_years)})
    if case == "missing":
        second.loc[len(second) - 1, "percent"] = float("nan")
    monkeypatch.setattr(gui_work, provider, lambda **kw: first if kw["party_code"] == "A" else second)
    question = SimpleNamespace(municipality="Test", first_party_code="A", second_party_code="B", since=None)
    getattr(window, handler)(question)
    pump_until(lambda: not window.jobs.active)
    if case in {"missing", "no_common"}:
        assert "kan ikke sammenlignes" in window.status.get_text().lower()
        assert "Forskjell i" not in window.result.get_text()
    else:
        expected_year = years[-2] if case == "different" else years[-1]
        expected_difference = "15,00" if case == "different" else "25,00"
        assert f"Forskjell i {expected_year}: {expected_difference}" in window.result.get_text()
        assert "felles valgår" in window.result.get_text().lower()


@pytest.mark.parametrize("values", [[0, 5], [0, 0], [None, 5], [5, None]])
def test_population_gui_missing_endpoints(window, monkeypatch, values):
    from types import SimpleNamespace

    import pandas as pd

    from samfunnsdata import gui_work

    frame = pd.DataFrame({"Tid_code": ["2024", "2025"], "value": values})
    monkeypatch.setattr(gui_work, "municipality_population", lambda _: (SimpleNamespace(name="Test"), frame))
    window.place.set_text("Test")
    window.on_analyze(None)
    pump_until(lambda: not window.jobs.active)
    assert "2025" in window.status.get_text()
    assert "ikke beregnbart" in window.result.get_text()
    window.on_show_raw(None)
    pump_until(lambda: not window.jobs.active)


def test_chart_temp_files_unique_cleaned_and_pixels_loaded(window, monkeypatch):
    from pathlib import Path

    import matplotlib.pyplot as plt

    from samfunnsdata import gui_work
    from samfunnsdata.gui_jobs import JobToken

    seen = []
    for i in range(3):
        with gui_work.chart_session(JobToken(i)):
            fig, ax = plt.subplots(figsize=(1, 1))
            ax.plot([0, 1])
            save = fig.savefig

            def capture(path, save=save, **kwargs):
                seen.append(Path(path))
                assert Path(path).is_file()
                save(path, **kwargs)
            monkeypatch.setattr(fig, "savefig", capture)
            png = gui_work.render_chart(fig)
        window._apply_analysis({"chart": png, "result": (False, "test"),
                                "status": "done", "source": "test", "series": [], "kind": "population"})
        assert window.chart.get_paintable() is not None
        assert not seen[-1].exists()
        assert not plt.fignum_exists(fig.number)
    assert len(set(seen)) == 3

    def fail(path, **_kwargs):
        seen.append(Path(path))
        raise OSError("Synthetic render failure")
    with pytest.raises(OSError), gui_work.chart_session(JobToken(4)):
        fig = plt.figure()
        monkeypatch.setattr(fig, "savefig", fail)
        gui_work.render_chart(fig)
    assert not seen[-1].exists()
    assert not plt.fignum_exists(fig.number)


def test_population_export_preserves_status_and_null(window, tmp_path):
    import pandas as pd
    from gi.repository import Gio

    raw = pd.DataFrame({"Tid_code": ["2024", "2025"], "value": [0, None], "status": ["", ":"]})
    window.current_kind = "population"
    window.current_series = [("Test", raw)]
    path = tmp_path / "export.csv"

    class Dialog:
        def save_finish(self, _result):
            return Gio.File.new_for_path(str(path))
    window.on_export_finished(Dialog(), None)
    pump_until(lambda: not window.jobs.active)
    output = pd.read_csv(path)
    assert output["Innbyggere"].iloc[0] == 0
    assert pd.isna(output["Innbyggere"].iloc[1])
    assert output["status"].iloc[1] == ":"
