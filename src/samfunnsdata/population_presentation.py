"""Population renderers: structured facts in, user text/files out."""

from html import escape
from pathlib import Path

import pandas as pd

from .analysis import format_number


def summary_text(series):
    facts = series.derived_facts
    return (
        f"{format_number(facts.first_value)} → {format_number(facts.last_value)}",
        (
            f"Endring: {format_number(facts.change, '+,')} personer "
            f"({format_number(facts.percent_change, '+.1f')} %)"
        ),
    )


def gui_summary(result):
    blocks = []
    comparison = len(result.series) > 1
    for series in result.series:
        values, change = summary_text(series)
        heading = f"<b>{escape(series.name)}</b>\n" if comparison else ""
        blocks.append(
            heading
            + f"<span size='x-large' weight='bold'>{values}</span>\n"
            + ("" if comparison else "\n")
            + change
        )
    method = (
        "SSBs aggregerte kommuneserier"
        if comparison
        else "SSBs aggregerte kommuneserie"
    )
    return (
        "\n\n".join(blocks)
        + f"\n\nMetode: {method} for sammenhengende historiske tall."
    )


def observation_text(observation):
    text = format_number(observation.usable_value, ",.0f")
    if observation.status not in (None, ""):
        raw = observation.source_value
        text += f" (status: {observation.status}; kildeverdi: {raw})"
    return text


def raw_text(result_series):
    lines = []
    for _, series in result_series:
        lines.extend((series.name, "År      Innbyggere", "------------------"))
        lines.extend(
            f"{o.period:<8}{observation_text(o):>10}"
            for o in series.source_observations
        )
        lines.append("")
    return "\n".join(lines), "Kilde: Statistisk sentralbyrå · Tabell 07459"


def export_csv(result_series, path, *, checkpoint=lambda: None):
    frames = []
    for _, series in result_series:
        checkpoint()
        rows = []
        for o in series.source_observations:
            row = {"Kommune": series.name, "År": o.period, "Innbyggere": o.source_value}
            if series.status_available:
                row["status"] = o.status
            rows.append(row)
        frames.append(pd.DataFrame(rows))
    combined = pd.concat(frames, ignore_index=True)
    checkpoint()
    combined.to_csv(path, index=False, encoding="utf-8-sig")
    return f"Eksportert til {path}"


def export_receipt(receipt, path, *, checkpoint=lambda: None):
    encoded = receipt.to_json()
    checkpoint()
    Path(path).write_text(encoded, encoding="utf-8")
    return f"Datakvittering eksportert til {path}"


def receipt_text(receipt):
    unknown = "Ukjent / ikke registrert"
    source = receipt.source
    lines = [
        "Kilde",
        f"{source.authority} · Tabell {source.dataset_id}",
        source.dataset_title or unknown,
        source.source_url or unknown,
        f"Lisens: {source.license or unknown}",
        "",
        "Måltall",
        f"{receipt.measure.label} ({receipt.measure.unit})",
        "",
        "Henting/cache",
        f"Brukt i denne analysen: {receipt.used_at.isoformat()}",
        "Brukstidspunktet er ikke tidspunktet da data ble hentet fra SSB.",
    ]
    for s in receipt.series:
        p, f = s.provenance, s.derived_facts
        cache = unknown if p.cache_hit is None else ("Ja" if p.cache_hit else "Nei")
        lines.extend(
            (
                "",
                f"Utvalg – {s.name}",
                f"Kommunekode: {s.selection.municipality_code or unknown}",
                f"Ønsket fra år: {s.selection.since if s.selection.since is not None else 'Alle tilgjengelige år'}",
                "Periode",
                f"Returnert av kilden: {s.source_returned_period[0]}–{s.source_returned_period[1]}",
                f"Faktisk brukt etter periodevalg: {f.first_year}–{f.last_year}",
                f"Hentet fra kilden: {p.fetched_at.isoformat() if p.fetched_at else unknown}",
                f"Cachetreff for befolkningsdata: {cache}",
                f"Nettverksmodus ved bruk: {p.network_mode or unknown}",
                f"Kildekontakt i operasjonen: {unknown if p.network_occurred is None else ('Ja' if p.network_occurred else 'Nei')}",
                f"Kildeoppdatering: {p.source_updated_at or unknown}",
                "Kildeobservasjoner (SSB):",
            )
        )
        lines.extend(
            f"  {o.period_label}: {o.source_value if o.source_value is not None else 'Mangler'}; "
            f"status: {o.status if o.status not in (None, '') else ('Ingen markering' if s.status_available else unknown)}"
            for o in s.source_observations
        )
        lines.extend(("Beregninger (Samfunnsdata):", summary_text(s)[1]))
        lines.extend(
            t.description for t in receipt.transformations if s.id in t.series_ids
        )
        lines.append("Advarsler")
        lines.extend(s.warnings or ("Ingen påviste advarsler for denne serien.",))
    lines.extend(("", "Advarsler for analysen"))
    lines.extend(receipt.warnings or ("Ingen påviste advarsler.",))
    lines.extend(
        (
            "",
            "Tekniske detaljer",
            "JSON viser utvalg, status, beregninger og kildemetadata.",
            "Ukjente proveniensfelt er null. Cachefilnavn er ikke innholdshash. Nettverksadresser viser bare opprinnelsesvert, uten sti eller søketekst.",
            receipt.to_json(),
        )
    )
    return "\n".join(lines)


def source_activity(result):
    provenance = [s.provenance for s in result.series]
    if all(p.cache_hit is True for p in provenance):
        return "Data: hentet fra cache"
    if all(p.cache_hit is False and p.fetched_at is not None for p in provenance):
        return "Data: hentet fra kilden nå"
    if all(p.cache_hit is not None for p in provenance):
        return "Data: delvis cache, delvis hentet fra kilden nå"
    return "Data: hentemåte ukjent"
