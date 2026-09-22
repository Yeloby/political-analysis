"""Desktop navigation around existing analyses; no data fetching or routing."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from .catalog import SOURCES, SupportStatus, find_datasets, get_source
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
    lines = [
        dataset.title, dataset.support_label, dataset.description,
        f"Kilde: {source.authority}",
        f"Datasett: {dataset.table_id or dataset.id}",
        f"Dataadresse: {dataset.access_url or 'Ikke registrert'}",
        f"Format: {dataset.format or 'Ikke registrert'}",
        f"Kildeinformasjon: {dataset.source_url or source.url}",
        f"Periode: {dataset.period}",
        f"Dimensjoner: {', '.join(dataset.dimensions)}",
        f"Måltall: {', '.join(dataset.measures)}",
        f"Enhet: {dataset.unit}",
        f"Definisjon: {dataset.definition}",
        f"Oppdatert hos kilden: {dataset.updated_at or 'Ikke registrert'}",
        "Offisiell statistikk: " + (
            "Ikke registrert" if dataset.official_statistics is None
            else "Ja" if dataset.official_statistics else "Nei"
        ),
    ]
    lines.extend(f"Begrensning: {item}" for item in dataset.limitations)
    lines.extend(f"Metode: {item}" for item in dataset.methodology)
    lines.extend(f"Seriebrudd: {item}" for item in dataset.series_breaks)
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
    view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
    scroll = Gtk.ScrolledWindow(vexpand=True)
    scroll.set_child(view)
    box.append(scroll)
    details = Gtk.TextView(editable=False, cursor_visible=False,
                           wrap_mode=Gtk.WrapMode.WORD_CHAR)
    details_scroll = Gtk.ScrolledWindow(min_content_height=180)
    details_scroll.set_child(details)
    expander = Gtk.Expander(label="Vis dimensjoner, måltall og metode for treffene")
    expander.set_child(details_scroll)
    box.append(expander)

    def refresh(*_args):
        provider = None if source.get_selected() == 0 else SOURCES[source.get_selected() - 1].id
        support = None if status.get_selected() == 0 else tuple(SupportStatus)[status.get_selected() - 1]
        matches = find_datasets(search.get_text(), provider=provider, support=support)
        details.get_buffer().set_text("\n\n────────────────────\n\n".join(
            dataset_description(x) for x in matches
        ))
        text = "\n\n".join(
            f"{x.title}\n{x.support_label}\n{x.description}\n"
            f"{get_source(x.provider).authority} · {x.period}" for x in matches
        )
        view.get_buffer().set_text(text or "Ingen treff i den lokale katalogen. Andre data kan finnes hos kilden.")

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
    add("quit", lambda: window.get_application().quit())
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
    menus = (
        ("Fil", (("Ny analyse", "new-analysis"), ("Eksporter CSV", "export-data"), ("Avslutt", "quit"))),
        ("Data", (("Bla i datasett", "datasets"), ("Datakilder", "sources"),
                  ("Rådata", "raw-data"), ("Kildeinformasjon", "source-info"))),
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
