import tempfile

import gi
import pandas as pd

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Gtk

from .analysis import (
    align_election_series,
    filter_since,
    format_number,
    observation_value,
    summarize_series,
)
from .charts import election_figure, population_figure
from .navigation import install_navigation
from .providers.norway.elections import (
    municipality_party_history,
    storting_party_history,
)
from .providers.norway.nav import municipality_unemployment_since
from .providers.norway.ssb import municipality_population
from .questions import (
    ElectionComparisonQuestion,
    ElectionQuestion,
    MunicipalElectionComparisonQuestion,
    MunicipalElectionQuestion,
    PopulationQuestion,
    UnemploymentQuestion,
    parse_question,
)


class SamfunnsdataWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(
            application=app,
            title="Samfunnsdata",
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
            "Samfunnsdata"
            "</span>"
        )
        title.set_xalign(0)
        box.append(title)

        subtitle = Gtk.Label(
            label="Offentlige data. Etterprøvbare svar."
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
        self.chart.set_size_request(-1, 360)
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
        self.source.set_text("")
        install_navigation(self, box, (advanced_label, form))

    def _display_chart(self, fig):
        import matplotlib.pyplot as plt

        try:
            with tempfile.NamedTemporaryFile(prefix="samfunnsdata-chart-", suffix=".png") as file:
                fig.savefig(file.name, dpi=180)
                # Pixbuf loads the pixels before the temporary file is removed.
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(file.name)
            self.chart.set_pixbuf(pixbuf)
            self.chart.set_visible(True)
        finally:
            plt.close(fig)

    def on_question(self, button):
        try:
            question = parse_question(
                self.question.get_text()
            )
        except ValueError as error:
            self.status.set_text(str(error))
            return

        if isinstance(question, UnemploymentQuestion):
            self.on_unemployment_question(question)
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

        if isinstance(
            question,
            MunicipalElectionComparisonQuestion,
        ):
            self.on_municipal_election_comparison(question)
            return

        if isinstance(question, MunicipalElectionQuestion):
            self.on_municipal_election_question(question)
            return

        if isinstance(question, ElectionQuestion):
            self.on_election_question(question)
            return

    def on_unemployment_question(self, question):
        import matplotlib.pyplot as plt

        self.status.set_text("Henter NAV-data …")

        since = question.since
        if since is None:
            since = 1995

        try:
            frame = municipality_unemployment_since(
                question.municipality,
                since,
            )
        except Exception as error:  # noqa: BLE001
            self.status.set_text(str(error))
            return

        first = frame.iloc[0]
        last = frame.iloc[-1]

        first_period = (
            f"{int(first['year'])}-{int(first['month']):02d}"
        )
        last_period = (
            f"{int(last['year'])}-{int(last['month']):02d}"
        )

        latest_unemployed = observation_value(last, "unemployed")
        latest_percent = last["percent"]

        if latest_percent is not None and not pd.isna(
            latest_percent
        ):
            percent_text = (
                f"{float(latest_percent):.1f}".replace(".", ",")
                + " %"
            )
        else:
            percent_text = "ikke oppgitt"

        self.status.set_text(
            f"Arbeidsledighet · {question.municipality} · "
            f"{first_period}–{last_period}"
        )

        latest_text = format_number(latest_unemployed, ",.0f")

        self.result.set_markup(
            f"<b>Registrerte helt ledige i "
            f"{question.municipality}</b>\n"
            f"<span size='x-large' weight='bold'>"
            f"{latest_text}</span>\n"
            f"Andel av arbeidsstyrken: {percent_text}\n\n"
            f"Siste observasjon: {last_period}\n"
            f"Metode: NAVs månedlige kommunestatistikk "
            f"for registrerte helt ledige."
        )

        self.current_series = [
            (question.municipality, frame)
        ]
        self.current_kind = "unemployment"

        self.raw_button.set_sensitive(True)
        self.export_button.set_sensitive(True)

        dates = pd.to_datetime(
            {
                "year": frame["year"].astype(int),
                "month": frame["month"].astype(int),
                "day": 1,
            }
        )

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(
            dates,
            frame["percent"],
        )
        ax.set_title(
            f"Registrerte helt ledige i "
            f"{question.municipality}"
        )
        ax.set_xlabel("Tid")
        ax.set_ylabel("Prosent av arbeidsstyrken")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()

        self._display_chart(fig)

        self.source.set_text(
            "Kilde: NAV · registrerte helt ledige"
        )

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
            first_comparison, second_comparison = align_election_series(first_frame, second_frame)
        except Exception as error:  # noqa: BLE001
            self.status.set_text(str(error))
            return

        first_name = str(
            first_comparison.iloc[-1]["party_name"]
        )
        second_name = str(
            second_comparison.iloc[-1]["party_name"]
        )

        first_start = float(
            first_comparison.iloc[0]["percent"]
        )
        first_end = float(
            first_comparison.iloc[-1]["percent"]
        )
        second_start = float(
            second_comparison.iloc[0]["percent"]
        )
        second_end = float(
            second_comparison.iloc[-1]["percent"]
        )

        first_change = first_end - first_start
        second_change = second_end - second_start
        latest_difference = first_end - second_end

        def pct(value):
            return f"{value:.2f}".replace(".", ",")

        def pp(value):
            return f"{value:+.2f}".replace(".", ",")

        first_year = min(
            int(first_comparison.iloc[0]["year"]),
            int(second_comparison.iloc[0]["year"]),
        )
        last_year = max(
            int(first_comparison.iloc[-1]["year"]),
            int(second_comparison.iloc[-1]["year"]),
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
            "Sammenligningen bruker felles valgår.\n"
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

        self._display_chart(fig)

        self.source.set_text(
            "Kilde: Valgdirektoratet · valgresultat.no"
        )

    def on_municipal_election_comparison(self, question):
        self.status.set_text("Henter kommunevalgdata …")

        try:
            first_frame = municipality_party_history(
                municipality=question.municipality,
                party_code=question.first_party_code,
                since=question.since,
            )
            second_frame = municipality_party_history(
                municipality=question.municipality,
                party_code=question.second_party_code,
                since=question.since,
            )
            first_comparison, second_comparison = align_election_series(first_frame, second_frame)
        except Exception as error:  # noqa: BLE001
            self.status.set_text(str(error))
            return

        first_name = str(first_comparison.iloc[-1]["party_name"])
        second_name = str(second_comparison.iloc[-1]["party_name"])

        first_start = float(first_comparison.iloc[0]["percent"])
        first_end = float(first_comparison.iloc[-1]["percent"])
        second_start = float(second_comparison.iloc[0]["percent"])
        second_end = float(second_comparison.iloc[-1]["percent"])

        first_change = first_end - first_start
        second_change = second_end - second_start
        latest_difference = first_end - second_end

        def pct(value):
            return f"{value:.2f}".replace(".", ",")

        def pp(value):
            return f"{value:+.2f}".replace(".", ",")

        first_year = min(
            int(first_comparison.iloc[0]["year"]),
            int(second_comparison.iloc[0]["year"]),
        )
        last_year = max(
            int(first_comparison.iloc[-1]["year"]),
            int(second_comparison.iloc[-1]["year"]),
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
            "Sammenligningen bruker felles valgår.\n"
            f"Forskjell i {last_year}: "
            f"{pct(abs(latest_difference))} prosentpoeng\n\n"
            f"Metode: Partienes stemmeandeler ved "
            f"kommunevalg i {question.municipality}."
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
            f"{question.municipality} – kommunevalg"
        )
        ax.set_xlabel("Valgår")
        ax.set_ylabel("Prosent")
        ax.legend()
        ax.grid(True, alpha=0.25)
        fig.tight_layout()

        self._display_chart(fig)

        self.source.set_text(
            "Kilde: Valgdirektoratet · valgresultat.no"
        )

    def on_municipal_election_question(self, question):
        self.status.set_text("Henter kommunevalgdata …")

        try:
            frame = municipality_party_history(
                municipality=question.municipality,
                party_code=question.party_code,
                since=question.since,
            )
        except (ValueError, KeyError) as error:
            self.status.set_text(str(error))
            return

        first = frame.iloc[0]
        last = frame.iloc[-1]

        party_name = str(last["party_name"])
        first_percent = observation_value(first, "percent")
        last_percent = observation_value(last, "percent")
        change = (last_percent - first_percent
                  if first_percent is not None and last_percent is not None else None)

        first_year = int(first["year"])
        last_year = int(last["year"])

        self.status.set_text(
            f"{party_name} · {question.municipality} · "
            f"{first_year}–{last_year}"
        )

        first_percent_text = (
            format_number(first_percent, ".2f")
        )
        last_percent_text = (
            format_number(last_percent, ".2f")
        )
        change_text = (
            format_number(change, "+.2f")
        )

        self.result.set_text(
            f"{party_name} · {question.municipality}\n"
            f"{first_year}: {first_percent_text} %\n"
            f"{last_year}: {last_percent_text} %\n"
            f"Endring: {change_text} prosentpoeng"
        )

        self.current_series = [
            (party_name, frame)
        ]
        self.current_kind = "election"
        self.raw_button.set_sensitive(True)
        self.export_button.set_sensitive(True)

        fig = election_figure(
            frame,
            f"{party_name} i {question.municipality}",
        )

        self._display_chart(fig)

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
        first_percent = observation_value(first, "percent")
        last_percent = observation_value(last, "percent")
        change = (last_percent - first_percent
                  if first_percent is not None and last_percent is not None else None)

        first_text = (
            format_number(first_percent, ".2f")
        )
        last_text = (
            format_number(last_percent, ".2f")
        )
        change_text = (
            format_number(change, "+.2f")
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

        self._display_chart(fig)

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

        first = format_number(summary.first_value, ",")
        last = format_number(summary.last_value, ",")
        change = format_number(summary.change, "+,")
        percent = (
            format_number(summary.percent_change, "+.1f")
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
                format_number(compare_summary.first_value, ",")
            )
            compare_last = (
                format_number(compare_summary.last_value, ",")
            )
            compare_change = (
                format_number(compare_summary.change, "+,")
            )
            compare_percent = (
                format_number(compare_summary.percent_change, "+.1f")
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

        self._display_chart(fig)
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
                    value_text = format_number(observation_value(row), ",.0f")
                    status = row.get("status")
                    if pd.notna(status) and status != "":
                        value_text += f" (status: {status}; kildeverdi: {row['value']})"
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
                    votes_text = format_number(observation_value(row, "votes"), ",.0f")
                    percent_text = format_number(observation_value(row, "percent"), ".2f")

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

        elif self.current_kind == "unemployment":
            for label, frame in self.current_series:
                lines.append(label)
                lines.append(
                    "År      Måned   Helt ledige   Andel"
                )
                lines.append(
                    "-----------------------------------"
                )

                for _, row in frame.iterrows():
                    year = int(row["year"])
                    month = int(row["month"])
                    unemployed = row["unemployed"]
                    percent = row["percent"]

                    if pd.isna(unemployed):
                        unemployed_text = "—"
                    else:
                        unemployed_text = (
                            f"{int(unemployed):,}"
                            .replace(",", " ")
                        )

                    if pd.isna(percent):
                        percent_text = "—"
                    else:
                        percent_text = (
                            f"{float(percent):.1f}"
                            .replace(".", ",")
                            + " %"
                        )

                    lines.append(
                        f"{year:<8}"
                        f"{month:<8}"
                        f"{unemployed_text:>11}"
                        f"{percent_text:>8}"
                    )

                lines.append("")

            source_text = (
                "Kilde: NAV · registrerte helt ledige"
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
        dialog.set_initial_name("samfunnsdata.csv")

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
                        "status",
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

        elif self.current_kind == "unemployment":
            for label, frame in self.current_series:
                export = frame.copy()
                export.insert(0, "Kommune", label)

                export = export.rename(
                    columns={
                        "year": "År",
                        "month": "Måned",
                        "unemployed": "Helt ledige",
                        "percent": "Andel av arbeidsstyrken",
                        "municipality_code": "Kommunenummer",
                    }
                )

                columns = [
                    column
                    for column in [
                        "Kommune",
                        "Kommunenummer",
                        "År",
                        "Måned",
                        "Helt ledige",
                        "Andel av arbeidsstyrken",
                    ]
                    if column in export.columns
                ]

                frames.append(export[columns])

        else:
            self.status.set_text(
                "Ingen data å eksportere."
            )
            return


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


class SamfunnsdataApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.Yeloby.Samfunnsdata"
        )

    def do_activate(self):
        window = SamfunnsdataWindow(self)
        window.present()


def main():
    app = SamfunnsdataApp()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
