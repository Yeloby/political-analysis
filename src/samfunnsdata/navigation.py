"""Desktop navigation around existing analyses; no data fetching or routing."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from . import network
from .catalog import (
    SOURCES,
    SupportStatus,
    _ssb_snapshot_path,
    find_datasets,
    get_source,
    load_discovered_ssb_snapshot,
    refresh_ssb_discovery_snapshot,
)
from .help import ATTRIBUTION, DESCRIPTION, TAGLINE, application_version, help_sections


def text_window(parent, title: str, text: str) -> Gtk.Window:
    window = Gtk.Window(title=title, transient_for=parent, destroy_with_parent=True)
    window.set_default_size(720, 520)
    view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
    view.set_left_margin(16)
    view.set_right_margin(16)
    view.set_top_margin(16)
    view.get_buffer().set_text(text)
    scroll = Gtk.ScrolledWindow()
    scroll.set_child(view)
    window.set_child(scroll)
    window.present()
    return window


def dataset_description(dataset) -> str:
    """Human-facing metadata; unknown values are explicit, never inferred."""
    source = get_source(dataset.provider)
    table_id = getattr(dataset, "table_id", None) or getattr(dataset, "id", "")
    access_url = getattr(dataset, "access_url", None) or "Ikke registrert"
    item_format = getattr(dataset, "format", None) or "Ikke registrert"
    source_url = getattr(dataset, "source_url", None) or source.url
    period = getattr(dataset, "period", "Ikke registrert")
    dimensions = getattr(dataset, "dimensions", None) or ()
    measures = getattr(dataset, "measures", None) or ()
    unit = getattr(dataset, "unit", "Ikke registrert")
    definition = getattr(dataset, "definition", "Ikke registrert")
    updated_at = getattr(dataset, "updated_at", None) or "Ikke registrert"
    official_statistics = getattr(dataset, "official_statistics", None)
    limitations = getattr(dataset, "limitations", None) or ()
    methodology = getattr(dataset, "methodology", None) or ()
    series_breaks = getattr(dataset, "series_breaks", None) or ()

    lines = [
        getattr(dataset, "title", "Uten tittel"),
        getattr(dataset, "support_label", "Uten støtte-status"),
        getattr(dataset, "description", "Beskrivelse mangler."),
        f"Kilde: {source.authority}",
        f"Datasett: {table_id}",
        f"Dataadresse: {access_url}",
        f"Format: {item_format}",
        f"Kildeinformasjon: {source_url}",
        f"Periode: {period}",
        f"Dimensjoner: {', '.join(dimensions)}",
        f"Måltall: {', '.join(measures)}",
        f"Enhet: {unit}",
        f"Definisjon: {definition}",
        f"Oppdatert hos kilden: {updated_at}",
        "Offisiell statistikk: " + (
            "Ikke registrert" if official_statistics is None
            else "Ja" if official_statistics else "Nei"
        ),
    ]
    lines.extend(f"Begrensning: {item}" for item in limitations)
    lines.extend(f"Metode: {item}" for item in methodology)
    lines.extend(f"Seriebrudd: {item}" for item in series_breaks)
    return "\n".join(lines)


def catalog_window(parent) -> Gtk.Window:
    window = Gtk.Window(title="Bla i datasett", transient_for=parent, destroy_with_parent=True)
    window.set_default_size(780, 600)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    for side in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{side}")(16)
    window.set_child(box)
    search = Gtk.SearchEntry(placeholder_text="Søk i den lokale katalogen")
    box.append(search)
    filters = Gtk.Box(spacing=10)
    source = Gtk.DropDown.new_from_strings(["Alle datakilder", *(x.authority for x in SOURCES)])
    status = Gtk.DropDown.new_from_strings(["Alle statuser", "Støttet", "Katalogisert", "Planlagt"])
    filters.append(source)
    filters.append(status)
    box.append(filters)

    split = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
    split.set_wide_handle(True)
    listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
    listbox.set_vexpand(True)
    listbox.set_size_request(300, -1)
    detail_scroll = Gtk.ScrolledWindow(vexpand=True)
    details = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
    detail_scroll.set_child(details)
    split.set_start_child(listbox)
    split.set_end_child(detail_scroll)
    box.append(split)
    window.catalog_listbox = listbox
    window.catalog_details = details
    window.catalog_matches = []

    def show_selected(*_args):
        row = listbox.get_selected_row()
        if row is None:
            details.get_buffer().set_text("Velg et datasett for å lese mer.")
            return
        dataset = getattr(row, "dataset", None)
        if dataset is None:
            details.get_buffer().set_text("Velg et datasett for å lese mer.")
            return
        details.get_buffer().set_text(dataset_description(dataset))

    listbox.connect("row-selected", show_selected)

    def refresh(*_args):
        provider = None if source.get_selected() == 0 else SOURCES[source.get_selected() - 1].id
        support = None if status.get_selected() == 0 else tuple(SupportStatus)[status.get_selected() - 1]
        matches = find_datasets(search.get_text(), provider=provider, support=support)
        window.catalog_matches = matches
        while True:
            child = listbox.get_first_child()
            if child is None:
                break
            listbox.remove(child)

        if not matches:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label="Ingen treff i den lokale katalogen. Andre data kan finnes hos kilden.")
            label.set_xalign(0)
            label.set_wrap(True)
            row.set_child(label)
            listbox.append(row)
            details.get_buffer().set_text("Ingen treff i den lokale katalogen. Andre data kan finnes hos kilden.")
            return

        for dataset in matches:
            row = Gtk.ListBoxRow()
            row.dataset = dataset
            content = Gtk.Box(spacing=12)
            content.set_margin_top(8)
            content.set_margin_bottom(8)
            content.set_margin_start(12)
            content.set_margin_end(12)
            title = Gtk.Label(label=dataset.title)
            title.set_xalign(0)
            title.set_hexpand(True)
            status_label = Gtk.Label(label=dataset.support_label)
            status_label.set_xalign(1)
            content.append(title)
            content.append(status_label)
            row.set_child(content)
            listbox.append(row)

        if matches:
            first = listbox.get_row_at_index(0)
            listbox.select_row(first)
            details.get_buffer().set_text(dataset_description(matches[0]))

    search.connect("search-changed", refresh)
    source.connect("notify::selected", refresh)
    status.connect("notify::selected", refresh)
    refresh()
    window.present()
    return window


def help_window(parent) -> Gtk.Window:
    window = Gtk.Window(title="Hjelp – Samfunnsdata", transient_for=parent, destroy_with_parent=True)
    window.set_default_size(850, 560)
    box = Gtk.Box(spacing=16)
    stack = Gtk.Stack(hexpand=True, vexpand=True)
    sidebar = Gtk.StackSidebar(stack=stack)
    box.append(sidebar)
    box.append(stack)
    for section in help_sections():
        view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.set_left_margin(12)
        view.set_right_margin(16)
        view.set_top_margin(16)
        view.get_buffer().set_text(section.text)
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(view)
        stack.add_titled(scroll, section.id, section.title)
    window.set_child(box)
    window.present()
    return window


def about_window(parent) -> Gtk.Window:
    # A small GTK about section keeps the requested attribution visibly at bottom.
    window = Gtk.Window(title="Om Samfunnsdata", transient_for=parent,
                        destroy_with_parent=True, modal=True)
    window.set_default_size(480, 340)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    for side in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{side}")(24)
    title = Gtk.Label(label="Samfunnsdata")
    title.add_css_class("title-1")
    box.append(title)
    for text in (TAGLINE, DESCRIPTION, f"Versjon {application_version()}", "Lisens: MIT"):
        box.append(Gtk.Label(label=text, wrap=True, selectable=True))
    box.append(Gtk.Box(vexpand=True))
    box.append(Gtk.Label(label=ATTRIBUTION, selectable=True))
    window.set_child(box)
    window.present()
    return window


def install_navigation(window, box, manual_widgets) -> None:
    def add(name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda *_: callback())
        window.add_action(action)
        return action

    def reset():
        window.jobs.cancel()
        window.current_series = []
        window.current_result = None
        window.receipt_button.set_sensitive(False)
        window.receipt_export_button.set_sensitive(False)
        window.current_kind = None
        for entry in (window.question, window.place, window.compare_place, window.since):
            entry.set_text("")
        for label in (window.status, window.result, window.source):
            label.set_text("")
        window.chart.set_visible(False)
        window.raw_button.set_sensitive(False)
        window.export_button.set_sensitive(False)
        window.question.grab_focus()

    add("new-analysis", reset)
    export = add("export-data", lambda: window.on_export(None))
    raw = add("raw-data", lambda: window.on_show_raw(None))
    source_info = add("source-info", lambda: text_window(
        window, "Kildeinformasjon for analysen", window.source.get_text()
        + "\n\nMetode og beregninger står i analyseresultatet. "
        "Full datakvittering er foreløpig ikke tilgjengelig for denne visningen.",
    ))
    # Existing handlers already update these buttons after successful analyses.
    # Mirror their state rather than adding a second analysis-state mechanism.
    for button, actions in ((window.export_button, (export,)),
                            (window.raw_button, (raw, source_info))):
        def sync(widget, _param=None, targets=actions):
            for action in targets:
                action.set_enabled(widget.get_sensitive())
        button.connect("notify::sensitive", sync)
        sync(button)
    def refresh_catalog():
        def work(token):
            if network.get_mode() == network.NetworkMode.CACHE_ONLY:
                path = _ssb_snapshot_path()
                if path.exists():
                    return load_discovered_ssb_snapshot(path)
                raise network.CacheOnlyMiss(
                    "Datakatalogen ligger bare i lokal cache og finnes ikke lokalt. "
                    "Skru av cache-only for å oppdatere katalogen."
                )
            return refresh_ssb_discovery_snapshot()

        def apply(_datasets):
            window.status.set_text("Datakatalog oppdatert. Nye SSB-tabeller ligger nå i den lokale katalogen.")

        if not window.jobs.active:
            window.jobs.submit(work, apply)

    add("quit", lambda: window.get_application().quit())
    add("refresh-datasets", refresh_catalog)
    add("datasets", lambda: catalog_window(window))
    add("sources", lambda: text_window(window, "Datakilder", "\n\n".join(
        f"{source.authority}\n{source.url}\n"
        + "\n".join(f"{item.title}: {item.support_label}" for item in find_datasets("", provider=source.id))
        for source in SOURCES
    ) + "\n\nOversikten gjelder registrerte datasett, ikke all statistikk hos myndighetene."))
    add("help", lambda: help_window(window))
    add("about", lambda: about_window(window))
    advanced = Gio.SimpleAction.new_stateful("manual", None, GLib.Variant.new_boolean(False))

    def toggle(action, _parameter):
        visible = not action.get_state().get_boolean()
        action.set_state(GLib.Variant.new_boolean(visible))
        for widget in manual_widgets:
            widget.set_visible(visible)
    advanced.connect("activate", toggle)
    window.add_action(advanced)
    for widget in manual_widgets:
        widget.set_visible(False)
    mode_action = Gio.SimpleAction.new_stateful(
        "cache-only", None, GLib.Variant.new_boolean(network.get_mode() == network.NetworkMode.CACHE_ONLY))
    window.network_label = Gtk.Label(xalign=0)
    box.append(window.network_label)

    def sync_mode():
        only = network.get_mode() == network.NetworkMode.CACHE_ONLY
        for target in window.get_application().get_windows():
            if hasattr(target, "network_label"):
                target.network_label.set_text("Nettverk: " + ("Kun lokal cache" if only else "Tillat nettilgang"))
                action = target.lookup_action("cache-only")
                if action is not None:
                    action.set_state(GLib.Variant.new_boolean(only))

    def toggle_network(_action, _parameter):
        only = network.get_mode() != network.NetworkMode.CACHE_ONLY
        network.set_mode(network.NetworkMode.CACHE_ONLY if only else network.NetworkMode.ONLINE)
        sync_mode()

    mode_action.connect("activate", toggle_network)
    window.add_action(mode_action)
    sync_mode()

    menus = (
        ("Fil", (("Ny analyse", "new-analysis"), ("Eksporter CSV", "export-data"), ("Avslutt", "quit"))),
        ("Data", (("Bla gjennom datakatalog", "datasets"), ("Oppdater datakatalog", "refresh-datasets"),
                  ("Datakilder", "sources"), ("Rådata", "raw-data"), ("Kildeinformasjon", "source-info"),
                  ("Kun lokal cache", "cache-only"))),
        ("Vis", (("Manuelle befolkningsvalg", "manual"),)),
        ("Hjelp", (("Brukerveiledning", "help"), ("Om Samfunnsdata", "about"))),
    )
    model = Gio.Menu()
    for title, items in menus:
        menu = Gio.Menu()
        for label, action in items:
            menu.append(label, f"win.{action}")
        model.append_submenu(title, menu)
    box.prepend(Gtk.PopoverMenuBar.new_from_model(model))
    window.get_application().set_accels_for_action("win.new-analysis", ["<Primary>n"])
    window.get_application().set_accels_for_action("win.help", ["F1"])
