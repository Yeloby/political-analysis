from dataclasses import dataclass

import httpx
import pandas as pd

from ...cache import JsonCache


BASE_URL = "https://valgresultat.no/api"


@dataclass(frozen=True)
class ElectionArea:
    number: str
    name: str
    href: str


class ElectionClient:
    def __init__(self, timeout=30.0):
        self.timeout = timeout
        self.cache = JsonCache()

    def get(self, path: str):
        cache_key = {"path": path}
        cached = self.cache.get("valgresultat", cache_key)

        if cached is None:
            response = httpx.get(
                f"{BASE_URL}{path}",
                timeout=self.timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            cached = response.json()
            self.cache.set("valgresultat", cache_key, cached)

        return cached


def related_areas(data):
    return [
        ElectionArea(
            number=str(item.get("nr", "")),
            name=str(item.get("navn", "")),
            href=str(item.get("href", "")),
        )
        for item in data.get("_links", {}).get("related", [])
        if item.get("href")
    ]


def find_related_area(data, name: str):
    wanted = name.casefold().strip()

    areas = related_areas(data)

    exact = [
        area
        for area in areas
        if area.name.casefold() == wanted
    ]

    if exact:
        return exact[0]

    partial = [
        area
        for area in areas
        if wanted in area.name.casefold()
    ]

    if len(partial) == 1:
        return partial[0]

    if not partial:
        raise ValueError(f"Fant ikke området «{name}».")

    names = ", ".join(area.name for area in partial)
    raise ValueError(
        f"Områdenavnet «{name}» er tvetydig. Treffer: {names}"
    )


def parties_to_frame(data):
    election_id = data.get("id", {})
    rows = []

    for party in data.get("partier", []):
        party_id = party.get("id", {})
        result = party.get("stemmer", {}).get("resultat", {})
        counts = result.get("antall", {})

        rows.append(
            {
                "year": int(election_id.get("valgaar")),
                "election_type": election_id.get("valgtype"),
                "level": election_id.get("nivaa"),
                "area_number": election_id.get("nr"),
                "area_name": election_id.get("navn"),
                "party_code": party_id.get("partikode"),
                "party_name": party_id.get("navn"),
                "party_category": party_id.get("partikategori"),
                "votes": counts.get("total"),
                "percent": result.get("prosent"),
            }
        )

    return pd.DataFrame(rows)


def find_storting_municipality(
    year: int,
    municipality: str,
):
    client = ElectionClient()
    national = client.get(f"/{year}/st")

    wanted = municipality.casefold().strip()
    matches = []

    for district in related_areas(national):
        district_data = client.get(district.href)

        for area in related_areas(district_data):
            if area.name.casefold() == wanted:
                matches.append((district, area))

    if not matches:
        raise ValueError(
            f"Fant ikke kommunen «{municipality}» "
            f"i stortingsvalget {year}."
        )

    if len(matches) > 1:
        districts = ", ".join(
            district.name
            for district, _ in matches
        )
        raise ValueError(
            f"Kommunen «{municipality}» finnes i flere "
            f"valgdistrikter: {districts}"
        )

    return matches[0]


def storting_municipality_result(
    year: int,
    municipality: str,
):
    client = ElectionClient()

    _, municipality_area = find_storting_municipality(
        year,
        municipality,
    )

    municipality_data = client.get(
        municipality_area.href
    )

    return municipality_area, parties_to_frame(
        municipality_data
    )


STORTING_YEARS = (2009, 2013, 2017, 2021, 2025)


def storting_party_history(
    municipality: str,
    party_code: str,
    since: int | None = None,
):
    frames = []

    for year in STORTING_YEARS:
        if since is not None and year < since:
            continue

        area, frame = storting_municipality_result(
            year=year,
            municipality=municipality,
        )

        matches = frame[
            frame["party_code"].str.casefold()
            == party_code.casefold()
        ]

        if matches.empty:
            continue

        frames.append(matches)

    if not frames:
        raise ValueError(
            f"Fant ingen valgresultater for «{party_code}»."
        )

    return pd.concat(frames, ignore_index=True)
