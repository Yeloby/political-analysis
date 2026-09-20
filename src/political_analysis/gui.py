import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .analysis import filter_since, summarize_series
from .providers.norway.ssb import municipality_population


class PoliticalAnalysisWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(
            application=app,
            title="Political Analysis",
        )

        self.set_default_size(760, 560)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        self.set_child(box)

        title = Gtk.Label()
        title.set_markup(
            "<span size='xx-large' weight='bold'>"
            "Political Analysis"
            "</span>"
        )
        title.set_xalign(0)
        box.append(title)

        subtitle = Gtk.Label(
            label="Analyser norske offentlige data"
        )
        subtitle.set_xalign(0)
        box.append(subtitle)

        form = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        box.append(form)

        self.place = Gtk.Entry()
        self.place.set_placeholder_text(
            "Kommune, f.eks. Trondheim"
        )
        self.place.set_hexpand(True)
        form.append(self.place)

        self.since = Gtk.Entry()
        self.since.set_placeholder_text("Fra år")
        self.since.set_width_chars(8)
        form.append(self.since)

        button = Gtk.Button(label="Analyser")
        button.connect("clicked", self.on_analyze)
        form.append(button)

        self.status = Gtk.Label()
        self.status.set_xalign(0)
        self.status.set_wrap(True)
        box.append(self.status)

        self.result = Gtk.Label()
        self.result.set_xalign(0)
        self.result.set_yalign(0)
        self.result.set_wrap(True)
        self.result.set_selectable(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.result)
        box.append(scroll)

        source = Gtk.Label(
            label=(
                "Kilde: Statistisk sentralbyrå · "
                "Tabell 07459"
            )
        )
        source.set_xalign(0)
        box.append(source)

    def on_analyze(self, button):
        place = self.place.get_text().strip()
        since_text = self.since.get_text().strip()

        if not place:
            self.status.set_text("Skriv inn en kommune.")
            return

        try:
            since = int(since_text) if since_text else None
        except ValueError:
            self.status.set_text("År må være et heltall.")
            return

        self.status.set_text("Henter data …")

        try:
            municipality, frame = municipality_population(place)
            frame = filter_since(frame, since)

            if frame.empty:
                raise ValueError("Ingen data for valgt periode.")

            summary = summarize_series(frame)

        except Exception as error:
            self.status.set_text(str(error))
            return

        first = f"{summary.first_value:,}".replace(",", " ")
        last = f"{summary.last_value:,}".replace(",", " ")
        change = f"{summary.change:+,}".replace(",", " ")
        percent = (
            f"{summary.percent_change:+.1f}"
            .replace(".", ",")
        )

        self.status.set_text(
            f"{municipality.name} · "
            f"{summary.first_year}–{summary.last_year}"
        )

        self.result.set_markup(
            f"<span size='x-large' weight='bold'>"
            f"{first} → {last}"
            f"</span>\n\n"
            f"Endring: {change} personer ({percent} %)\n\n"
            f"Metode: SSBs aggregerte kommuneserie for "
            f"sammenhengende historiske tall."
        )


class PoliticalAnalysisApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.Yeloby.PoliticalAnalysis"
        )

    def do_activate(self):
        window = PoliticalAnalysisWindow(self)
        window.present()


def main():
    app = PoliticalAnalysisApp()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
