from dataclasses import dataclass
from math import isfinite
from numbers import Real

import pandas as pd


@dataclass(frozen=True)
class SeriesSummary:
    first_year: str
    last_year: str
    first_value: int | None
    last_value: int | None
    change: int | None
    percent_change: float | None
    first_status: str | None = None
    last_status: str | None = None


def filter_since(frame: pd.DataFrame, since: int | None) -> pd.DataFrame:
    if since is None:
        return frame

    years = frame["Tid_code"].astype(int)
    return frame[years >= since]


def summarize_series(frame: pd.DataFrame) -> SeriesSummary:
    if frame.empty:
        raise ValueError("Kan ikke analysere en tom dataserie.")

    first = frame.iloc[0]
    last = frame.iloc[-1]

    first_value = observation_value(first)
    last_value = observation_value(last)
    first_value = int(first_value) if first_value is not None else None
    last_value = int(last_value) if last_value is not None else None

    change = (
        last_value - first_value
        if first_value is not None and last_value is not None else None
    )
    percent_change = (
        (change / first_value) * 100
        if change is not None and first_value != 0 else None
    )

    first_year = str(first.get("Tid", first.get("Tid_code", "")))
    last_year = str(last.get("Tid", last.get("Tid_code", "")))

    return SeriesSummary(
        first_year=first_year,
        last_year=last_year,
        first_value=first_value,
        last_value=last_value,
        change=change,
        percent_change=percent_change,
        first_status=observation_status(first),
        last_status=observation_status(last),
    )



def observation_status(row: pd.Series) -> str | None:
    status = row.get("status")
    return None if pd.isna(status) or status == "" else str(status)


def observation_value(row: pd.Series, column: str = "value") -> int | float | None:
    """Unflagged finite number, without changing source values or guessing flags.

    All nonempty source flags conservatively prevent an unqualified calculation;
    this does not interpret an unknown flag as suppression. Raw data stays intact.
    """
    value = row[column]
    if observation_status(row) is not None:
        return None
    if not isinstance(value, Real) or isinstance(value, bool) or not isfinite(value):
        return None
    return value


def format_number(value: float | None, spec: str = ",") -> str:
    if value is None or pd.isna(value):
        return "ikke beregnbart"
    text = format(value, spec)
    return text.replace(",", " ") if "," in spec else text.replace(".", ",")


def align_election_series(
    first: pd.DataFrame, second: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare endpoints of the common election-year intersection, never as-of.

    Missing/flagged endpoints in the common period reject comparison rather than
    searching backwards for a usable value. Returned frames retain source data.
    """
    message = "Resultatene kan ikke sammenlignes"
    for frame in (first, second):
        if frame.empty or frame["year"].isna().any() or frame["year"].duplicated().any():
            raise ValueError(f"{message}: manglende eller flertydig valgår.")
    years = sorted(set(first["year"]) & set(second["year"]))
    if not years:
        raise ValueError(f"{message}: ingen felles valgår.")
    aligned = tuple(
        frame.set_index("year", drop=False).loc[years].reset_index(drop=True)
        for frame in (first, second)
    )
    for column in ("election_type", "area_number", "level"):
        if column in first and column in second:
            if aligned[0][column].isna().any() or aligned[1][column].isna().any():
                raise ValueError(f"{message}: ukjent {column}.")
            if not aligned[0][column].eq(aligned[1][column]).all():
                raise ValueError(f"{message}: ulike {column}.")
    for frame in aligned:
        for position in (0, -1):
            row = frame.iloc[position]
            if observation_value(row, "percent") is None:
                raise ValueError(
                    f"{message}: verdi mangler eller er statusmerket i {int(row['year'])}."
                )
    return aligned
