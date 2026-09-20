from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SeriesSummary:
    first_year: str
    last_year: str
    first_value: int
    last_value: int
    change: int
    percent_change: float


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

    first_value = int(first["value"])
    last_value = int(last["value"])

    change = last_value - first_value
    percent_change = (change / first_value) * 100

    first_year = str(first.get("Tid", first.get("Tid_code", "")))
    last_year = str(last.get("Tid", last.get("Tid_code", "")))

    return SeriesSummary(
        first_year=first_year,
        last_year=last_year,
        first_value=first_value,
        last_value=last_value,
        change=change,
        percent_change=percent_change,
    )
