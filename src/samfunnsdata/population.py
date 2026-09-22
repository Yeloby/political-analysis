"""Thin application service around the unchanged SSB population provider."""

import json
from datetime import UTC, datetime

import pandas as pd

from . import network
from .analysis import filter_since, observation_value, summarize_series
from .catalog import get_dataset, get_source
from .help import application_version
from .providers.norway.ssb import municipality_population
from .questions import PopulationQuestion, parse_population_question
from .results import (
    AnalysisResult,
    DataReceipt,
    Measure,
    Observation,
    PopulationSeries,
    Provenance,
    Selection,
    Source,
    Transformation,
)

__all__ = [
    "PopulationQuestion",
    "analyze_population",
    "parse_population_question",
]


def _scalar(value):
    if value is None or pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def analyze_population(
    places, since=None, *, provider=None, checkpoint=lambda: None, used_at=None
):
    """Keep endpoint/order/status rules from milestone A, for any number of series.

    Filtering happens locally, after the provider requests all source years.
    No new metadata requests, cache reads, hashes, or inferred retrieval times.
    """
    provider = provider or municipality_population
    series, transformations = [], []
    for index, place in enumerate(places):
        checkpoint()
        with network.observe_requests() as requests:
            municipality, frame = provider(place)
        mode = network.get_mode().value
        access = frame.attrs.get("network_access") or {}
        checkpoint()
        returned_period = (
            (str(frame.iloc[0]["Tid_code"]), str(frame.iloc[-1]["Tid_code"]))
            if not frame.empty
            else None
        )
        frame = filter_since(frame, since)
        if frame.empty:
            raise ValueError(
                f"Ingen befolkningsdata for {municipality.name} fra {since}."
            )
        facts = summarize_series(frame)
        metadata = frame.attrs.get("jsonstat_metadata")
        metadata_json = (
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, allow_nan=False)
            if metadata is not None
            else None
        )
        observations = tuple(
            Observation(
                str(row["Tid_code"]),
                str(row.get("Tid", row["Tid_code"])),
                _scalar(row["value"]),
                _scalar(row.get("status")),
                _scalar(observation_value(row)),
            )
            for _, row in frame.iterrows()
        )
        warnings = []
        if any(o.status not in (None, "") for o in observations):
            warnings.append(
                "Statusmerkede kildeverdier er bevart, men brukes ikke i beregninger eller graf. Kodene er ikke tolket."
            )
        if any(o.source_value is None for o in observations):
            warnings.append(
                "Kilden har manglende observasjoner. Ingen verdier er erstattet."
            )
        if facts.change is None:
            warnings.append("Endring kan ikke beregnes fra de faktiske endepunktene.")
        elif facts.first_value == 0:
            warnings.append("Prosentvis endring fra null kan ikke beregnes.")
        identity = f"series-{index + 1}"
        selection = Selection(
            place,
            municipality.name,
            getattr(municipality, "code", None),
            since,
            "Personer1",
        )
        updated = metadata.get("updated") if metadata is not None else None
        series.append(
            PopulationSeries(
                identity,
                selection,
                returned_period,
                observations,
                facts,
                "status" in frame,
                metadata_json,
                Provenance(source_updated_at=updated,
                           cache_hit=access.get("cache_hit"), fetched_at=access.get("fetched_at"),
                           network_mode=mode, network_occurred=any(r.network_occurred for r in requests),
                           requests=tuple(requests)),
                tuple(warnings),
            )
        )
        for operation, description, inputs, outputs in (
            (
                "select_municipality",
                "SSBs aggregerte kommuneserie; kommunen velges hos kilden.",
                ("selection.municipality_code", "selection.geography_codelist"),
                ("source_observations",),
            ),
            (
                "restrict_period",
                "Behold kildeobservasjoner fra og med ønsket år, i kildens rekkefølge.",
                ("selection.since", "source_observations"),
                ("source_observations",),
            ),
            (
                "absolute_change",
                "Siste minus første endepunkt. Manglende eller statusmerket endepunkt gir ukjent resultat.",
                ("derived_facts.first_value", "derived_facts.last_value"),
                ("derived_facts.change",),
            ),
            (
                "percentage_change",
                "Absolutt endring delt på første verdi, ganger 100. Første verdi lik null gir ukjent resultat.",
                ("derived_facts.change", "derived_facts.first_value"),
                ("derived_facts.percent_change",),
            ),
        ):
            transformations.append(
                Transformation(operation, (identity,), description, inputs, outputs)
            )
    if not series:
        raise ValueError("Oppgi minst én kommune.")
    warnings = []
    if len(series) > 1:
        transformations.append(
            Transformation(
                "compare_series",
                tuple(s.id for s in series),
                "Vis kommuneseriene ved siden av hverandre med egne faktiske perioder. Ingen ny differanse eller tidsjustering beregnes.",
                ("source_observations", "derived_facts"),
                (),
            )
        )
        if (
            len(
                {
                    (s.derived_facts.first_year, s.derived_facts.last_year)
                    for s in series
                }
            )
            > 1
        ):
            warnings.append("Kommuneseriene har ulike faktiske perioder.")
    dataset = get_dataset("ssb-07459-population")
    source = get_source("ssb")
    receipt = DataReceipt(
        Source(
            source.id,
            source.authority,
            dataset.table_id,
            dataset.title,
            dataset.source_url,
            dataset.access_url,
        ),
        Measure("population", "Personer1", "Folkemengde", dataset.unit),
        tuple(series),
        tuple(transformations),
        used_at or datetime.now(UTC),
        application_version(),
        tuple(warnings),
    )
    checkpoint()
    title = (
        f"Befolkningsutvikling i {series[0].name}"
        if len(series) == 1
        else " og ".join(s.name for s in series)
    )
    return AnalysisResult(title, receipt)
