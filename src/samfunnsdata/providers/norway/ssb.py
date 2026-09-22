from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from math import prod

import pandas as pd

from ... import network
from ...cache import JsonCache

BASE_URL = "https://data.ssb.no/api/pxwebapi/v2"


@dataclass(frozen=True)
class SsbTable:
    id: str
    title: str


@dataclass(frozen=True)
class Municipality:
    code: str
    name: str


_LOCAL_MUNICIPALITY_LOOKUP = {
    "akershus": "0200",
    "alverstranda": "3024",
    "andebu": "3026",
    "asker": "3228",
    "askvoll": "1428",
    "aurskog-holand": "3218",
    "balsfjord": "5412",
    "bergen": "1201",
    "berlevåg": "5436",
    "bodo": "1804",
    "bremanger": "1438",
    "brønnøy": "1818",
    "buskerud": "0600",
    "dronninglund": "1825",
    "drammen": "3005",
    "færder": "3811",
    "fredrikstad": "3004",
    "gjesdal": "1122",
    "grimstad": "0904",
    "halden": "3001",
    "hamar": "3403",
    "harstad": "5406",
    "heim": "4631",
    "hjelmeland": "1134",
    "hodal": "3443",
    "karmøy": "1149",
    "kristiansand": "4204",
    "larvik": "3805",
    "lillestrøm": "3205",
    "lindesnes": "4202",
    "moss": "3002",
    "nordre follo": "3212",
    "nordkapp": "5435",
    "nordland": "1800",
    "oslo": "0301",
    "rauma": "1539",
    "sandefjord": "3804",
    "sandnes": "1108",
    "sarpsborg": "3003",
    "skien": "3807",
    "stavanger": "1103",
    "stor-Elvdal": "3439",
    "sveio": "1246",
    "sør-ovarheim": "4227",
    "tilsagn": "3020",
    "tønsberg": "3904",
    "trondheim": "5001",
    "tromsø": "5401",
    "ulstein": "1516",
    "vestby": "3211",
    "vestland": "4601",
    "vestvågøy": "1860",
    "volda": "1515",
    "ålesund": "1504",
}


def _normalize_municipality_name(name: str) -> str:
    normalized = str(name).casefold().strip()
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = " ".join(normalized.split())
    return normalized.strip()


def _municipality_search_terms(name: str) -> set[str]:
    normalized = _normalize_municipality_name(name)
    terms = {normalized}
    for separator in (" - ", "-", "–", "—"):
        if separator in normalized:
            left = normalized.split(separator, 1)[0].strip()
            if left:
                terms.add(left)
            compact = normalized.replace(separator, " ")
            if compact != normalized:
                terms.add(compact)
    return {term for term in terms if term}


def _k_prefixed_code(code: str) -> str:
    code = str(code).strip()
    return code if code.startswith("K-") else f"K-{code}"


def find_municipality_local(name: str) -> Municipality | None:
    wanted_terms = _municipality_search_terms(name)
    if not wanted_terms:
        return None

    exact = [
        Municipality(_k_prefixed_code(code), municipality_name)
        for municipality_name, code in _LOCAL_MUNICIPALITY_LOOKUP.items()
        if any(term in _municipality_search_terms(municipality_name) for term in wanted_terms)
    ]
    if exact:
        return exact[0]

    matches = [
        Municipality(_k_prefixed_code(code), municipality_name)
        for municipality_name, code in _LOCAL_MUNICIPALITY_LOOKUP.items()
        if any(
            term in alias
            for term in wanted_terms
            for alias in _municipality_search_terms(municipality_name)
        )
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        return None

    raise ValueError(
        f"Kommunenavnet «{name}» er tvetydig. Treffer: {', '.join(item.name for item in matches[:10])}"
    )


class SsbClient:
    def __init__(self, language="no", timeout=30.0):
        self.language = language
        self.timeout = timeout
        self.cache = JsonCache()
        self.last_data_access = None

    def search(self, query: str):
        params = {
            "query": query,
            "lang": self.language,
            "pagesize": 100,
            "page": 1,
        }
        seen_pages: set[int] = set()
        seen_ids: set[str] = set()
        results: list[SsbTable] = []

        while True:
            page = int(params["page"])
            if page in seen_pages:
                raise ValueError("SSB-tabellsøk returnerte samme side uten å gå fremover.")
            seen_pages.add(page)

            cached = self.cache.get("ssb-search", params)
            current = None
            if cached is None:
                response = network.request(
                    "ssb", "table_search", "GET", f"{BASE_URL}/tables",
                    free_text=True,
                    params=params,
                    timeout=self.timeout,
                    follow_redirects=True,
                )
                response.raise_for_status()
                current = response.json()
                self.cache.set("ssb-search", params, current)
            else:
                current = cached

            if isinstance(current, list):
                items = current
                total_pages = None
            elif isinstance(current, dict):
                items = (
                    current.get("items")
                    or current.get("tables")
                    or current.get("data")
                    or []
                )
                total_pages = (
                    current.get("pages")
                    or current.get("totalPages")
                    or current.get("pageCount")
                    or current.get("total_pages")
                    or None
                )
            else:
                items = []
                total_pages = None

            for item in items:
                if not isinstance(item, dict):
                    continue
                table_id = str(
                    item.get("id")
                    or item.get("tableId")
                    or item.get("code")
                    or ""
                )
                if not table_id or table_id in seen_ids:
                    continue
                title = str(
                    item.get("label")
                    or item.get("title")
                    or item.get("text")
                    or table_id
                )
                seen_ids.add(table_id)
                results.append(SsbTable(table_id, title))

            if total_pages is not None:
                total_pages = int(total_pages)
                if page >= total_pages:
                    break
            if not items:
                break
            if total_pages is None and len(items) < int(params["pagesize"]):
                break
            next_page = page + 1
            params["page"] = next_page
            if next_page > 20:
                break

        return results

    def get_codelist(self, codelist_id: str):
        params = {"lang": self.language}
        cache_key = {
            "codelist": codelist_id,
            **params,
        }

        cached = self.cache.get("ssb-codelist", cache_key)

        if cached is None:
            response = network.request(
                "ssb", "codelist", "GET", f"{BASE_URL}/codelists/{codelist_id}",
                params=params,
                timeout=self.timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            cached = response.json()
            self.cache.set("ssb-codelist", cache_key, cached)

        return cached

    def get_data(self, table_id: str, params: list[tuple[str, str]]):
        cache_payload = {
            "table": table_id,
            "params": params,
            "lang": self.language,
        }

        self.last_data_access = None
        cached = self.cache.get("ssb-data", cache_payload)
        hit = cached is not None
        fetched_at = None

        if cached is None:
            response = network.request(
                "ssb", "table_data", "GET", f"{BASE_URL}/tables/{table_id}/data",
                params=[("lang", self.language), *params],
                timeout=self.timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            cached = response.json()
            self.cache.set("ssb-data", cache_payload, cached)
            fetched_at = datetime.fromisoformat(response.extensions["samfunnsdata_request"].completed_at)

        self.last_data_access = {"cache_hit": hit, "fetched_at": fetched_at}

        return cached


def municipalities():
    client = SsbClient()
    data = client.get_codelist("agg_KommSummer")

    codes = data.get("codes") or data.get("code") or []
    labels = data.get("labels") or data.get("label") or []

    results = []

    if isinstance(codes, list) and isinstance(labels, list):
        for code, label in zip(codes, labels):
            if str(code).startswith("K-"):
                results.append(
                    Municipality(
                        code=str(code),
                        name=str(label),
                    )
                )

    if not results:
        values = (
            data.get("values")
            or data.get("items")
            or data.get("valueMap")
            or []
        )

        if isinstance(values, list):
            for item in values:
                if not isinstance(item, dict):
                    continue

                code = str(
                    item.get("code")
                    or item.get("id")
                    or item.get("value")
                    or ""
                )

                name = str(
                    item.get("label")
                    or item.get("text")
                    or item.get("name")
                    or ""
                )

                if code.startswith("K-") and name:
                    results.append(Municipality(code, name))

    return results


def find_municipality(name: str):
    candidate = str(name).strip()
    if not candidate:
        raise ValueError("Fant ikke kommunen «».")

    normalized = _normalize_municipality_name(candidate)
    candidates = municipalities()

    exact_matches = [
        municipality
        for municipality in candidates
        if _normalize_municipality_name(municipality.name) == normalized
        or _normalize_municipality_name(municipality.name).split(" - ", 1)[0] == normalized
        or _normalize_municipality_name(municipality.name).replace(" ", "") == normalized.replace(" ", "")
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(
            f"Kommunenavnet «{name}» er tvetydig. Treffer: {', '.join(item.name for item in exact_matches[:10])}"
        )

    partial_matches = [
        municipality
        for municipality in candidates
        if normalized in _normalize_municipality_name(municipality.name)
        or _normalize_municipality_name(municipality.name) in normalized
        or normalized.split(" - ", 1)[0] in _normalize_municipality_name(municipality.name)
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]
    if len(partial_matches) > 1:
        raise ValueError(
            f"Kommunenavnet «{name}» er tvetydig. Treffer: {', '.join(item.name for item in partial_matches[:10])}"
        )

    local_match = find_municipality_local(name)
    if local_match is not None:
        return local_match
    raise ValueError(f"Fant ikke kommunen «{name}».")


def jsonstat_to_frame(data):
    dimensions = data["id"]
    sizes = data["size"]
    values = data["value"]
    count = prod(sizes)
    status = data.get("status")
    if status is None or isinstance(status, str):
        statuses = [status] * count
    elif isinstance(status, list):
        if len(status) != count:
            raise ValueError("JSON-stat status length does not match dataset size")
        statuses = status
    elif isinstance(status, dict):
        if any(not key.isdigit() or str(int(key)) != key or int(key) >= count for key in status):
            raise ValueError("JSON-stat status index outside dataset size")
        statuses = [status.get(str(i)) for i in range(count)]
    else:
        raise TypeError("Unsupported JSON-stat status representation")

    codes = {}
    labels = {}

    for dimension in dimensions:
        category = data["dimension"][dimension]["category"]
        index = category["index"]

        if isinstance(index, dict):
            ordered = sorted(index.items(), key=lambda x: x[1])
            codes[dimension] = [code for code, _ in ordered]
        else:
            codes[dimension] = list(index)

        labels[dimension] = category.get("label", {})

    rows = []

    def walk(level, coordinates):
        if level == len(dimensions):
            flat_index = 0
            multiplier = 1

            for i in range(len(dimensions) - 1, -1, -1):
                flat_index += coordinates[i] * multiplier
                multiplier *= sizes[i]

            row = {}

            for dimension, position in zip(dimensions, coordinates):
                code = codes[dimension][position]
                row[dimension] = labels[dimension].get(code, code)
                row[f"{dimension}_code"] = code

            row["value"] = values.get(str(flat_index)) if isinstance(values, dict) else values[flat_index]
            rows.append(row)
            return

        for position in range(sizes[level]):
            walk(level + 1, coordinates + [position])

    walk(0, [])

    frame = pd.DataFrame(rows)
    frame["status"] = pd.Series(statuses, dtype=object)
    frame.attrs["jsonstat_metadata"] = deepcopy(
        {key: value for key, value in data.items() if key not in {"value", "status"}}
    )
    return frame


def municipality_population(name: str):
    municipality = find_municipality(name)
    client = SsbClient()

    params = [
        ("valueCodes[Region]", municipality.code),
        ("valueCodes[ContentsCode]", "Personer1"),
        ("valueCodes[Tid]", "*"),
        ("codelist[Region]", "agg_KommSummer"),
        ("outputValues[Region]", "aggregated"),
        ("outputFormat", "json-stat2"),
    ]

    raw = client.get_data("07459", params)
    frame = jsonstat_to_frame(raw)
    frame.attrs["network_access"] = client.last_data_access

    return municipality, frame

    params = [
        ("valueCodes[Region]", municipality.code),
        ("valueCodes[ContentsCode]", "Personer1"),
        ("valueCodes[Tid]", "*"),
        ("codelist[Region]", "agg_KommSummer"),
        ("outputValues[Region]", "aggregated"),
        ("outputFormat", "json-stat2"),
    ]

    raw = client.get_data("07459", params)
    frame = jsonstat_to_frame(raw)

    return municipality, frame
