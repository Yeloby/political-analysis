"""Medicine histories from FHI lmr/825; no aggregation across ATC categories."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from numbers import Real

import pandas as pd

from .fhi import BASE_URL, FhiClient

SOURCE = "lmr"
TABLE_ID = 825
MEASURES = ("AntallBrukere", "Brukere_Per1000_Innbyggere", "DDD", "Befolkning")
SEX_CODES = ("TOTALT", "1", "2")
DIMENSIONS = {
    "atc": "Atc_Verdi",
    "sex": "Kjonn_Verdi",
    "age": "Aldersgruppe_Verdi",
    "year": "Utlevering_Ar",
    "measure": "MEASURE_TYPE",
}


@dataclass(frozen=True)
class Category:
    code: str
    label: str


def _categories(dimensions: list[dict], code: str) -> tuple[Category, ...]:
    """Flatten FHI's category tree, retaining parent categories as candidates."""
    dimension = next((item for item in dimensions if item["code"] == code), None)
    if dimension is None:
        raise ValueError(f"FHI mangler dimensjonen {code}.")
    found = {}

    def visit(items: list[dict]) -> None:
        for item in items:
            category = Category(str(item["value"]), item.get("label") or str(item["value"]))
            if category.code in found and found[category.code] != category:
                raise ValueError(f"Motstridende FHI-etiketter for {category.code}.")
            found[category.code] = category
            visit(item.get("children") or [])

    visit(dimension["categories"])
    return tuple(found.values())


def atc_categories(*, client: FhiClient | None = None) -> tuple[Category, ...]:
    """Discover ATC codes and labels, including groups, from current FHI metadata."""
    client = client or FhiClient()
    return _categories(client.dimensions(SOURCE, TABLE_ID), DIMENSIONS["atc"])


def lookup_atc(code: str, *, client: FhiClient | None = None) -> Category:
    """Exact code lookup, ignoring surrounding whitespace and letter case."""
    wanted = code.strip().upper()
    for category in atc_categories(client=client):
        if category.code == wanted:
            return category
    raise ValueError(f"Ukjent ATC-kode: {code}")


def search_atc(text: str, *, client: FhiClient | None = None) -> list[Category]:
    """Return all literal, case-insensitive label matches; never pick a candidate."""
    wanted = text.strip().casefold()
    if not wanted:
        return []
    return [item for item in atc_categories(client=client) if wanted in item.label.casefold()]


def medicine_history(
    atc: str,
    sex: str = "TOTALT",
    age: str = "TOTALT",
    measure: str = "AntallBrukere",
    since: int | None = None,
    *,
    client: FhiClient | None = None,
) -> pd.DataFrame:
    """Return one ATC/sex/age/measure series, sorted by numeric year.

    Labels and valid selections come from current FHI dimensions. since is
    inclusive; an empty requested period raises ValueError. No observations are
    aggregated, imputed or dropped based on status. Raw JSON-stat metadata and
    structured FHI table metadata remain in DataFrame.attrs.
    """
    if since is not None and (isinstance(since, bool) or not isinstance(since, int)):
        raise TypeError("since må være et helt årstall.")
    client = client or FhiClient()
    dimensions = client.dimensions(SOURCE, TABLE_ID)
    selection = {"atc": atc.strip().upper(), "sex": sex, "age": age, "measure": measure}
    if sex not in SEX_CODES:
        raise ValueError(f"Ukjent kjønnskode: {sex}")
    if measure not in MEASURES:
        raise ValueError(f"Ukjent måltall: {measure}")
    for name, code in selection.items():
        available = {item.code for item in _categories(dimensions, DIMENSIONS[name])}
        if code not in available:
            raise ValueError(f"Ukjent {name}-kode: {code}")
    available_years = sorted(
        (item.code for item in _categories(dimensions, DIMENSIONS["year"])), key=int,
    )
    years = [year for year in available_years if since is None or int(year) >= since]
    if not years:
        raise ValueError("Ingen tilgjengelige år i den valgte perioden.")
    query = {DIMENSIONS[name]: [code] for name, code in selection.items()}
    query[DIMENSIONS["year"]] = years
    frame = client.data_frame(SOURCE, TABLE_ID, query)
    # Reject incomplete/expanded results instead of silently changing the series.
    for name, code in selection.items():
        if not frame[f"{DIMENSIONS[name]}_code"].eq(code).all():
            raise ValueError(f"FHI returnerte et annet utvalg for {name}.")
    returned_years = frame[f"{DIMENSIONS['year']}_code"]
    if returned_years.duplicated().any() or set(returned_years) != set(years):
        raise ValueError("FHI returnerte ikke nøyaktig én observasjon per valgt år.")
    rename = {}
    for name, dimension in DIMENSIONS.items():
        rename[dimension] = f"{name}_label"
        rename[f"{dimension}_code"] = f"{name}_code"
    attrs = deepcopy(frame.attrs)
    frame = frame.rename(columns=rename)
    frame["year"] = frame["year_code"].astype(int)
    columns = ["year"] + [
        column for name in DIMENSIONS for column in (f"{name}_code", f"{name}_label")
    ] + ["value", "status"]
    frame = frame.sort_values("year").reset_index(drop=True)[columns]
    frame.attrs = attrs
    table_metadata = client.metadata(SOURCE, TABLE_ID)
    frame.attrs["fhi_metadata"] = deepcopy(table_metadata)
    raw_metadata = attrs.get("jsonstat_metadata", {})
    frame.attrs["provenance"] = {
        "provider": "FHI", "source_id": SOURCE, "table_id": TABLE_ID,
        "table_title": raw_metadata.get("label") or table_metadata.get("name"),
        "url": f"{BASE_URL}/{SOURCE}/table/{TABLE_ID}",
        "selection": selection,
        "period": {"first_year": int(years[0]), "last_year": int(years[-1])},
        "available_years": [int(year) for year in available_years],
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
    return frame


def latest_medicine_observation(history: pd.DataFrame) -> pd.Series:
    """Return the latest YEAR, never fall back to an earlier numerical value.

    Valid means a finite real number and no status (None/NA/empty string).
    All nonempty statuses, including unknown flags, are conservatively invalid.
    The returned row retains coordinates/labels/attrs and adds raw_value and
    is_valid; value is None when invalid. The input history remains untouched.
    Empty or mixed/duplicate series are rejected.
    """
    if history.empty:
        raise ValueError("Kan ikke hente siste observasjon fra en tom historikk.")
    for name in ("atc", "sex", "age", "measure"):
        if history[f"{name}_code"].nunique(dropna=False) != 1:
            raise ValueError("Forventet én legemiddelserie.")
    if history["year"].duplicated().any():
        raise ValueError("Flere observasjoner for samme år.")
    row = history.sort_values("year").iloc[-1].copy()
    row.attrs = deepcopy(history.attrs)
    raw_value = row["value"]
    status = row["status"]
    valid = (
        isinstance(raw_value, Real) and not isinstance(raw_value, bool)
        and isfinite(raw_value) and (pd.isna(status) or status == "")
    )
    row["raw_value"] = raw_value
    row["is_valid"] = bool(valid)
    row["value"] = raw_value if valid else None
    return row
