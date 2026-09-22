"""Shared GTK fixtures; ordinary non-GTK tests do not import GTK here."""
import pytest


@pytest.fixture(scope="session")
def app():
    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gio, Gtk

    app = Gtk.Application(application_id="io.github.Yeloby.Samfunnsdata.Test",
                          flags=Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    yield app
    app.quit()


@pytest.fixture
def window(app):
    from gi.repository import Gtk
    from test_gui_jobs import pump_until

    from samfunnsdata.gui import SamfunnsdataWindow

    window = SamfunnsdataWindow(app)
    yield window
    for child in list(Gtk.Window.list_toplevels()):
        child.destroy()
    pump_until(lambda: window.jobs.outstanding == 0)
