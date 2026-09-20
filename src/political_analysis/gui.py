import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk

from .analysis import filter_since, summarize_series
from .charts import population_figure
from .providers.norway.elections import storting_party_history
from .providers.norway.ssb import municipality_population
from .questions import (
    ElectionComparisonQuestion,
    ElectionQuestion,
    PopulationQuestion,
    parse_question,
)


class PoliticalAnalysisWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(
            application=app,
            title="Political Analysis",
        )

        self.set_default_size(1000, 760)

        self.current_series = []
        self.current_kind = None

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

        question_label = Gtk.Label(
            label="Hva vil du finne ut?"
        )
        question_label.set_xalign(0)
        box.append(question_label)

        question_form = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        box.append(question_form)

        self.question = Gtk.Entry()
        self.question.set_placeholder_text(
            "F.eks. Sammenlign Trondheim og Bergen siden 2000"
        )
        self.question.set_hexpand(True)
        self.question.connect(
            "activate",
            self.on_question,
        )
        question_form.append(self.question)

        question_button = Gtk.Button(
            label="Analyser spørsmål"
        )
        question_button.connect(
            "clicked",
            self.on_question,
        )
        question_form.append(question_button)

        advanced_label = Gtk.Label(
            label="Manuelle valg"
        )
        advanced_label.set_xalign(0)
        box.append(advanced_label)

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

        self.compare_place = Gtk.Entry()
        self.compare_place.set_placeholder_text(
            "Sammenlign med, f.eks. Bergen"
        )
        self.compare_place.set_hexpand(True)
        form.append(self.compare_place)

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

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
        )
        content.append(self.result)

        self.chart = Gtk.Picture()
        self.chart.set_can_shrink(True)
        self.chart.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.chart.set_size_request(-1, 440)
        self.chart.set_hexpand(True)
        self.chart.set_vexpand(True)
        self.chart.set_visible(False)
        content.append(self.chart)

        scroll.set_child(content)
        box.append(scroll)

        actions = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )
        box.append(actions)

        self.raw_button = Gtk.Button(label="Vis rådata")
        self.raw_button.set_sensitive(False)
        self.raw_button.connect("clicked", self.on_show_raw)
        actions.append(self.raw_button)

        self.export_button = Gtk.Button(label="Eksporter CSV")
        self.export_button.set_sensitive(False)
        self.export_button.connect("clicked", self.on_export)
        actions.append(self.export_button)

        self.source = Gtk.Label(
            label=(
                "Kilde: Statistisk sentralbyrå · "
                "Tabell 07459"
            )
        )
        self.source.set_xalign(0)
        box.append(self.source)

    def on_question(self, button):
        try:
            question = parse_question(
                self.question.get_text()
            )
        except ValueError as error:
            self.status.set_text(str(error))
            return

        if isinstance(question, PopulationQuestion):
            self.place.set_text(question.place)
            self.compare_place.set_text(
                question.compare_place or ""
            )
            self.since.set_text(
                str(question.since)
                if question.since is not None
                else ""
            )
            self.on_analyze(button)
            return

        if isinstance(question, ElectionComparisonQuestion):
            self.on_election_comparison(question)
            return

        if isinstance(question, ElectionQuestion):
            self.on_election_question(question)
            return

    def on_election_comparison(self, question):
        self.status.set_text("Henter valgdata …")

        try:
            first_frame = storting_party_history(
                municipality=question.municipality,
                party_code=question.first_party_code,
                since=question.since,
            )
            second_frame = storting_party_history(
                municipality=question.municipality,
                party_code=question.second_party_code,
                since=question.since,
            )
        except Exception as error:  # noqa: BLE001
            self.status.set_text(str(error))
            return

        first_name = str(
            first_frame.iloc[-1]["party_name"]
        )
        second_name = str(
            second_frame.iloc[-1]["party_name"]
        )

        first_start = float(
            first_frame.iloc[0]["percent"]
        )
        first_end = float(
            first_frame.iloc[-1]["percent"]
        )
        second_start = float(
            second_frame.iloc[0]["percent"]
        )
        second_end = float(
            second_frame.iloc[-1]["percent"]
        )

        first_change = first_end - first_start
        second_change = second_end - second_start
        latest_difference = first_end - second_end

        def pct(value):
            return f"{value:.2f}".replace(".", ",")

        def pp(value):
            return f"{value:+.2f}".replace(".", ",")

        first_year = min(
            int(first_frame.iloc[0]["year"]),
            int(second_frame.iloc[0]["year"]),
        )
        last_year = max(
            int(first_frame.iloc[-1]["year"]),
            int(second_frame.iloc[-1]["year"]),
        )

        self.status.set_text(
            f"{first_name} og {second_name} · "
            f"{question.municipality} · "
            f"{first_year}–{last_year}"
        )

        self.result.set_markup(
            f"<b>{first_name}</b>\n"
            f"<span size='x-large' weight='bold'>"
            f"{pct(first_start)} % → {pct(first_end)} %"
            f"</span>\n"
            f"Endring: {pp(first_change)} prosentpoeng\n\n"
            f"<b>{second_name}</b>\n"
            f"<span size='x-large' weight='bold'>"
            f"{pct(second_start)} % → {pct(second_end)} %"
            f"</span>\n"
            f"Endring: {pp(second_change)} prosentpoeng\n\n"
            f"Forskjell i {last_year}: "
            f"{pct(abs(latest_difference))} prosentpoeng\n\n"
            f"Metode: Partienes stemmeandeler ved "
            f"stortingsvalg i {question.municipality}."
        )

        self.current_series = [
            (first_name, first_frame),
            (second_name, second_frame),
        ]
        self.current_kind = "election"

        self.raw_button.set_sensitive(True)
        self.export_button.set_sensitive(True)

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(
            first_frame["year"],
            first_frame["percent"],
            marker="o",
            label=first_name,
        )
        ax.plot(
            second_frame["year"],
            second_frame["percent"],
            marker="o",
            label=second_name,
        )

        ax.set_title(
            f"{first_name} og {second_name} i "
            f"{question.municipality} – stortingsvalg"
        )
        ax.set_xlabel("Valgår")
        ax.set_ylabel("Prosent")
        ax.legend()
        ax.grid(True, alpha=0.25)
        fig.tight_layout()

        chart_path = "/tmp/political-analysis-chart.png"
        fig.savefig(chart_path, dpi=180)
        plt.close(fig)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(
            chart_path
        )
        self.chart.set_pixbuf(pixbuf)
        self.chart.set_visible(True)

        self.source.set_text(
            "Kilde: Valgdirektoratet · valgresultat.no"
        )

    def on_election_question(self, question):
        self.status.set_text("Henter valgdata …")

        try:
            frame = storting_party_history(
                municipality=question.municipality,
                party_code=question.party_code,
                since=question.since,
            )
        except Exception as error:  # noqa: BLE001
            self.status.set_text(str(error))
            return

        first = frame.iloc[0]
        last = frame.iloc[-1]

        party_name = str(last["party_name"])
        first_percent = float(first["percent"])
        last_percent = float(last["percent"])
        change = last_percent - first_percent

        first_text = (
            f"{first_percent:.2f}".replace(".", ",")
        )
        last_text = (
            f"{last_percent:.2f}".replace(".", ",")
        )
        change_text = (
            f"{change:+.2f}".replace(".", ",")
        )

        self.status.set_text(
            f"{party_name} · {question.municipality} · "
            f"{int(first['year'])}–{int(last['year'])}"
        )

        self.result.set_markup(
            f"<b>{party_name}</b>\n"
            f"<span size='x-large' weight='bold'>"
            f"{first_text} % → {last_text} %"
            f"</span>\n\n"
            f"Endring: {change_text} prosentpoeng\n\n"
            f"Metode: Partiets andel av godkjente stemmer "
            f"ved stortingsvalg i {question.municipality}."
        )

        self.current_series = [
            (party_name, frame)
        ]
        self.current_kind = "election"
        self.raw_button.set_sensitive(True)
        self.export_button.set_sensitive(True)

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(
            frame["year"],
            frame["percent"],
            marker="o",
        )
        ax.set_title(
            f"{party_name} i {question.municipality} – stortingsvalg"
        )
        ax.set_xlabel("Valgår")
        ax.set_ylabel("Prosent")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()

        chart_path = "/tmp/political-analysis-chart.png"
        fig.savefig(chart_path, dpi=180)
        plt.close(fig)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(chart_path)
        self.chart.set_pixbuf(pixbuf)
        self.chart.set_visible(True)

        self.source.set_text(
            "Kilde: Valgdirektoratet · valgresultat.no"
        )

    def on_analyze(self, button):
        place = self.place.get_text().strip()
        compare_place = self.compare_place.get_text().strip()
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

            comparison = None

            if compare_place:
                compare_municipality, compare_frame = (
                    municipality_population(compare_place)
                )
                compare_frame = filter_since(
                    compare_frame,
                    since,
                )

                if compare_frame.empty:
                    raise ValueError(
                        "Ingen data for sammenligningskommunen "
                        "i valgt periode."
                    )

                compare_summary = summarize_series(compare_frame)

                comparison = (
                    compare_municipality,
                    compare_frame,
                    compare_summary,
                )

        except Exception as error:  # noqa: BLE001
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

        self.source.set_text(
            "Kilde: Statistisk sentralbyrå · Tabell 07459"
        )

        if comparison:
            (
                compare_municipality,
                compare_frame,
                compare_summary,
            ) = comparison

            compare_first = (
                f"{compare_summary.first_value:,}"
                .replace(",", " ")
            )
            compare_last = (
                f"{compare_summary.last_value:,}"
                .replace(",", " ")
            )
            compare_change = (
                f"{compare_summary.change:+,}"
                .replace(",", " ")
            )
            compare_percent = (
                f"{compare_summary.percent_change:+.1f}"
                .replace(".", ",")
            )

            self.result.set_markup(
                f"<b>{municipality.name}</b>\n"
                f"<span size='x-large' weight='bold'>"
                f"{first} → {last}"
                f"</span>\n"
                f"Endring: {change} personer "
                f"({percent} %)\n\n"
                f"<b>{compare_municipality.name}</b>\n"
                f"<span size='x-large' weight='bold'>"
                f"{compare_first} → {compare_last}"
                f"</span>\n"
                f"Endring: {compare_change} personer "
                f"({compare_percent} %)\n\n"
                f"Metode: SSBs aggregerte kommuneserier for "
                f"sammenhengende historiske tall."
            )

            chart_series = [
                (municipality.name, frame),
                (compare_municipality.name, compare_frame),
            ]

            chart_title = (
                f"{municipality.name} og "
                f"{compare_municipality.name}"
            )

        else:
            self.result.set_markup(
                f"<span size='x-large' weight='bold'>"
                f"{first} → {last}"
                f"</span>\n\n"
                f"Endring: {change} personer "
                f"({percent} %)\n\n"
                f"Metode: SSBs aggregerte kommuneserie for "
                f"sammenhengende historiske tall."
            )

            chart_series = [
                (municipality.name, frame),
            ]

            chart_title = (
                f"Befolkningsutvikling i {municipality.name}"
            )

        self.current_series = chart_series
        self.current_kind = "population"
        self.raw_button.set_sensitive(True)
        self.export_button.set_sensitive(True)

        fig = population_figure(
            chart_series,
            chart_title,
        )

        chart_path = "/tmp/political-analysis-chart.png"
        fig.savefig(chart_path, dpi=180)

        import matplotlib.pyplot as plt
        plt.close(fig)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(chart_path)
        self.chart.set_pixbuf(pixbuf)
        self.chart.set_visible(True)
    def on_show_raw(self, button):
        if not self.current_series:
            return

        window = Gtk.Window(
            title="Rådata",
            transient_for=self,
            modal=False,
        )
        window.set_default_size(760, 600)

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        outer.set_margin_top(18)
        outer.set_margin_bottom(18)
        outer.set_margin_start(18)
        outer.set_margin_end(18)
        window.set_child(outer)

        title = Gtk.Label()
        title.set_markup(
            "<span size='x-large' weight='bold'>"
            "Rådata"
            "</span>"
        )
        title.set_xalign(0)
        outer.append(title)

        text = Gtk.TextView()
        text.set_editable(False)
        text.set_cursor_visible(False)
        text.set_monospace(True)

        lines = []

        if self.current_kind == "population":
            for label, frame in self.current_series:
                lines.append(label)
                lines.append("År      Innbyggere")
                lines.append("------------------")

                for _, row in frame.iterrows():
                    year = str(row["Tid_code"])
                    value = int(row["value"])
                    value_text = (
                        f"{value:,}".replace(",", " ")
                    )
                    lines.append(
                        f"{year:<8}{value_text:>10}"
                    )

                lines.append("")

            source_text = (
                "Kilde: Statistisk sentralbyrå · "
                "Tabell 07459"
            )

        elif self.current_kind == "election":
            for label, frame in self.current_series:
                lines.append(label)
                lines.append(
                    "Valgår   Stemmer      Prosent"
                )
                lines.append(
                    "-----------------------------"
                )

                for _, row in frame.iterrows():
                    year = int(row["year"])
                    votes = int(row["votes"])
                    percent = float(row["percent"])

                    votes_text = (
                        f"{votes:,}".replace(",", " ")
                    )
                    percent_text = (
                        f"{percent:.2f}"
                        .replace(".", ",")
                    )

                    lines.append(
                        f"{year:<8}"
                        f"{votes_text:>8}"
                        f"{percent_text:>12} %"
                    )

                lines.append("")

            source_text = (
                "Kilde: Valgdirektoratet · "
                "valgresultat.no"
            )

        else:
            lines.append("Ingen rådata tilgjengelig.")
            source_text = ""

        text.get_buffer().set_text(
            "\n".join(lines)
        )

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_child(text)
        outer.append(scroll)

        source = Gtk.Label(label=source_text)
        source.set_xalign(0)
        outer.append(source)

        window.present()

    def on_export(self, button):
        if not self.current_series:
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Eksporter CSV")
        dialog.set_initial_name("political-analysis.csv")

        dialog.save(
            self,
            None,
            self.on_export_finished,
        )

    def on_export_finished(self, dialog, result):
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            return

        if file is None:
            return

        path = file.get_path()

        if path is None:
            self.status.set_text(
                "Kan bare eksportere til en lokal fil."
            )
            return

        frames = []

        if self.current_kind == "population":
            for label, frame in self.current_series:
                export = frame.copy()
                export.insert(0, "Kommune", label)

                export = export.rename(
                    columns={
                        "Tid_code": "År",
                        "value": "Innbyggere",
                    }
                )

                columns = [
                    column
                    for column in [
                        "Kommune",
                        "År",
                        "Innbyggere",
                    ]
                    if column in export.columns
                ]

                frames.append(export[columns])

        elif self.current_kind == "election":
            for label, frame in self.current_series:
                export = frame.copy()

                export = export.rename(
                    columns={
                        "year": "Valgår",
                        "area_name": "Kommune",
                        "party_code": "Partikode",
                        "party_name": "Parti",
                        "votes": "Stemmer",
                        "percent": "Prosent",
                    }
                )

                columns = [
                    column
                    for column in [
                        "Valgår",
                        "Kommune",
                        "Partikode",
                        "Parti",
                        "Stemmer",
                        "Prosent",
                    ]
                    if column in export.columns
                ]

                frames.append(export[columns])

        else:
            self.status.set_text(
                "Ingen data å eksportere."
            )
            return

        import pandas as pd

        combined = pd.concat(
            frames,
            ignore_index=True,
        )

        combined.to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )

        self.status.set_text(
            f"Eksportert til {path}"
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
