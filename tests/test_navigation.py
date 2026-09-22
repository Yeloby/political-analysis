"""Offline GTK checks; run with xvfb-run on headless Linux."""
import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

from samfunnsdata.gui import SamfunnsdataWindow
from samfunnsdata.help import ATTRIBUTION
from samfunnsdata.navigation import about_window, catalog_window, help_window

pytestmark = pytest.mark.skipif(not Gtk.init_check(), reason="GTK display required (use xvfb-run)")


@pytest.fixture(scope="module")
def app():
    app = Gtk.Application(application_id="io.github.Yeloby.Samfunnsdata.Test",
                          flags=Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    yield app
    app.quit()


@pytest.fixture
def window(app):
    window = SamfunnsdataWindow(app)
    yield window
    for child in list(Gtk.Window.list_toplevels()):
        child.destroy()


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
    assert stack.get_pages().get_n_items() == 10
    catalog = catalog_window(window)
    view = next(x for x in children(catalog) if isinstance(x, Gtk.TextView))
    buffer = view.get_buffer()
    assert "Støttet: Python/API" in buffer.get_text(*buffer.get_bounds(), True)
    search = next(x for x in children(catalog) if isinstance(x, Gtk.SearchEntry))
    search.set_text("zzzz-no-match")
    search.emit("search-changed")
    assert "Ingen treff" in buffer.get_text(*buffer.get_bounds(), True)
