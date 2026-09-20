from dataclasses import dataclass

import httpx

from ...cache import JsonCache

BASE_URL = "https://data.ssb.no/api/pxwebapi/v2"


@dataclass(frozen=True)
class SsbTable:
    id: str
    title: str


class SsbClient:
    def __init__(self, language="no", timeout=30.0):
        self.language = language
        self.timeout = timeout
        self.cache = JsonCache()

    def search(self, query: str):
        params = {
            "query": query,
            "lang": self.language,
            "pagesize": 100,
        }

        cached = self.cache.get("ssb-search", params)

        if cached is None:
            response = httpx.get(
                f"{BASE_URL}/tables",
                params=params,
                timeout=self.timeout,
                follow_redirects=True,
            )
            response.raise_for_status()

            cached = response.json()
            self.cache.set("ssb-search", params, cached)

        if isinstance(cached, list):
            items = cached
        else:
            items = (
                cached.get("tables")
                or cached.get("items")
                or cached.get("data")
                or []
            )

        results = []

        for item in items:
            table_id = str(
                item.get("id")
                or item.get("tableId")
                or item.get("code")
                or ""
            )

            title = str(
                item.get("label")
                or item.get("title")
                or item.get("text")
                or table_id
            )

            if table_id:
                results.append(
                    SsbTable(
                        id=table_id,
                        title=title,
                    )
                )

        return results
