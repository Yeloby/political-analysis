from pathlib import Path

import pandas as pd

from ... import network
from ...cache import FileCache

NAV_UNEMPLOYMENT_URL = (
    "https://www.nav.no/_/attachment/download/"
    "ecea9530-b50e-4c19-be80-894f0f0fc2f7:"
    "7d8939bd2b25f1e716dc3f31bac9416d4ecff050/"
    "2025_HL110%20Antall%20ledige%20historisk.%20Kommune."
    "%20%C3%85r%20m%C3%A5ned.%20CSV.csv"
)


def unemployment_csv(
    *,
    timeout: float = 60.0,
    cache: FileCache | None = None,
) -> Path:
    cache = cache or FileCache()

    payload = {"url": NAV_UNEMPLOYMENT_URL}

    cached = cache.get(
        "nav-unemployment-municipality",
        payload,
        ".csv",
    )

    if cached is not None:
        return cached

    response = network.request("nav", "unemployment_csv", "GET",
        NAV_UNEMPLOYMENT_URL,
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()

    return cache.set(
        "nav-unemployment-municipality",
        payload,
        response.content,
        ".csv",
    )


def municipality_unemployment_data(
    municipality: str,
) -> pd.DataFrame:
    frame = read_unemployment_csv(unemployment_csv())
    return municipality_unemployment(frame, municipality)


def read_unemployment_csv(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        sep=";",
        encoding="cp1252",
        dtype={
            "Fylkesnr": "string",
            "Fylkenavn": "string",
            "Kommunenr": "string",
            "Kommunenavn": "string",
        },
    )

    frame = frame.rename(
        columns={
            "Fylkesnr": "county_code",
            "Fylkenavn": "county_name",
            "Kommunenr": "municipality_code",
            "Kommunenavn": "municipality_name",
            "År": "year",
            "Månedsnummer": "month",
            "Beholdning": "unemployed",
            "Andel av arbeidsstyrken": "percent",
        }
    )

    frame["unemployed"] = pd.to_numeric(
        frame["unemployed"],
        errors="coerce",
    )

    frame["percent"] = pd.to_numeric(
        frame["percent"].astype("string").str.replace(",", ".", regex=False),
        errors="coerce",
    )

    frame["year"] = pd.to_numeric(
        frame["year"],
        errors="coerce",
    ).astype("Int64")

    frame["month"] = pd.to_numeric(
        frame["month"],
        errors="coerce",
    ).astype("Int64")

    return frame



def municipality_unemployment(
    frame: pd.DataFrame,
    municipality: str,
) -> pd.DataFrame:
    wanted = municipality.casefold().strip()

    matches = frame[
        frame["municipality_name"].str.casefold().str.strip() == wanted
    ].copy()

    if matches.empty:
        raise ValueError(f"Fant ikke kommunen «{municipality}» i NAV-dataene.")

    matches = matches.drop_duplicates()

    selected = []

    for (_, _), group in matches.groupby(
        ["year", "month"],
        sort=True,
        dropna=False,
    ):
        if len(group) == 1:
            selected.append(group.iloc[0])
            continue

        usable = group[
            (group["unemployed"].fillna(0) > 0)
            | group["percent"].notna()
        ]

        if len(usable) == 1:
            selected.append(usable.iloc[0])
            continue

        if len(usable) > 1:
            distinct = usable.drop_duplicates(
                subset=["unemployed", "percent"]
            )

            if len(distinct) == 1:
                selected.append(usable.iloc[0])
                continue

        problem = group[
            [
                "year",
                "month",
                "municipality_code",
                "unemployed",
                "percent",
            ]
        ]

        raise ValueError(
            f"Flere ulike NAV-observasjoner finnes for «{municipality}» "
            "i samme måned:\n"
            f"{problem.to_string(index=False)}"
        )

    result = pd.DataFrame(selected)

    return (
        result.sort_values(["year", "month"])
        .reset_index(drop=True)
    )


def municipality_unemployment_since(
    municipality: str,
    since_year: int,
) -> pd.DataFrame:
    frame = municipality_unemployment_data(municipality)

    result = frame[
        frame["year"] >= since_year
    ].copy()

    if result.empty:
        raise ValueError(
            f"Ingen NAV-data for «{municipality}» "
            f"fra {since_year}."
        )

    return result.reset_index(drop=True)
