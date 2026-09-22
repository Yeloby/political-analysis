from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from math import prod
from typing import Any

import pandas as pd

from ... import network

BASE_URL = "https://statistikk-data.fhi.no/api/open/v1"


@dataclass(frozen=True)
class FhiSource:
    id: str
    title: str
    description: str
    about_url: str
    published_by: str


@dataclass(frozen=True)
class FhiTable:
    id: int
    title: str
    published_at: str
    modified_at: str


class FhiClient:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def _get(self, path: str) -> Any:
        response = network.request("fhi", "metadata", "GET",
            f"{BASE_URL}/{path.lstrip('/')}",
            cache_relationship="uncached",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def sources(self) -> list[FhiSource]:
        payload = self._get("Common/source")

        return [
            FhiSource(
                id=item["id"],
                title=item["title"],
                description=item.get("description", ""),
                about_url=item.get("aboutUrl", ""),
                published_by=item.get("publishedBy", ""),
            )
            for item in payload
        ]

    def tables(self, source: str) -> list[FhiTable]:
        payload = self._get(f"{source}/table")

        return [
            FhiTable(
                id=item["tableId"],
                title=item["title"],
                published_at=item.get("publishedAt", ""),
                modified_at=item.get("modifiedAt", ""),
            )
            for item in payload
        ]

    def table(self, source: str, table_id: int) -> FhiTable:
        item = self._get(f"{source}/table/{table_id}")

        return FhiTable(
            id=item["tableId"],
            title=item["title"],
            published_at=item.get("publishedAt", ""),
            modified_at=item.get("modifiedAt", ""),
        )

    def metadata(self, source: str, table_id: int) -> dict:
        return self._get(f"{source}/table/{table_id}/metadata")

    def dimensions(self, source: str, table_id: int) -> list[dict]:
        payload = self._get(
            f"{source}/table/{table_id}/dimension"
        )
        return payload["dimensions"]

    def data(
        self,
        source: str,
        table_id: int,
        dimensions: dict[str, list[str]],
        *,
        max_row_count: int = 50_000,
    ) -> dict:
        query = {
            "dimensions": [
                {
                    "code": code,
                    "filter": "item",
                    "values": values,
                }
                for code, values in dimensions.items()
            ],
            "response": {
                "format": "json-stat2",
                "maxRowCount": max_row_count,
            },
        }

        response = network.request("fhi", "table_data", "POST",
            f"{BASE_URL}/{source}/Table/{table_id}/data",
            json=query,
            cache_relationship="uncached",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


    def data_frame(
        self,
        source: str,
        table_id: int,
        dimensions: dict[str, list[str]],
        *,
        max_row_count: int = 50_000,
    ) -> pd.DataFrame:
        """Query any FHI table and decode its observations, labels and statuses."""
        return jsonstat_to_frame(
            self.data(source, table_id, dimensions, max_row_count=max_row_count)
        )


def jsonstat_to_frame(data: dict[str, Any]) -> pd.DataFrame:
    """Decode an FHI JSON-stat2 dataset in declared dimension/category order.

    Like SSB, <dimension> holds labels (falling back to codes) and
    <dimension>_code holds category codes. value and status describe each cell.
    Missing values stay missing; status codes are never interpreted as numbers.
    Non-observation metadata is retained in attrs["jsonstat_metadata"], including
    any provider-specific status definitions in extension/category metadata.
    """
    dimensions = data["id"]
    sizes = data["size"]
    if len(dimensions) != len(sizes) or len(set(dimensions)) != len(dimensions):
        raise ValueError("JSON-stat id and size must describe distinct dimensions")
    if any(type(size) is not int or size < 1 for size in sizes):
        raise ValueError("JSON-stat dimension sizes must be positive integers")

    columns = [name for dim in dimensions for name in (dim, f"{dim}_code")]
    columns += ["value", "status"]
    if len(set(columns)) != len(columns):
        raise ValueError("Dimension names collide with generated DataFrame columns")

    codes = []
    labels = []
    for dim, size in zip(dimensions, sizes):
        category = data["dimension"][dim]["category"]
        index = category.get("index")
        if index is None and size == 1:
            index = list(category.get("label", {}))
        if isinstance(index, dict):
            if sorted(index.values()) != list(range(size)):
                raise ValueError(f"Invalid category positions for {dim}")
            ordered = sorted(index, key=index.__getitem__)
        elif isinstance(index, list):
            ordered = index
        else:
            raise TypeError(f"Missing or unsupported category index for {dim}")
        if len(ordered) != size or len(set(ordered)) != size:
            raise ValueError(f"Category count does not match size for {dim}")
        codes.append(ordered)
        labels.append(category.get("label", {}))

    count = prod(sizes)

    def observations(raw: Any, *, status: bool = False) -> list:
        if status and (raw is None or isinstance(raw, str)):
            return [raw] * count
        if isinstance(raw, list):
            if len(raw) != count:
                raise ValueError("Observation array length does not match dataset size")
            return raw
        if isinstance(raw, dict):
            if any(
                not isinstance(i, str) or not i.isdigit()
                or str(int(i)) != i or int(i) >= count
                for i in raw
            ):
                raise ValueError("Sparse observation index outside dataset size")
            return [raw.get(str(i)) for i in range(count)]
        raise ValueError("Unsupported observation representation")

    values = observations(data["value"])
    statuses = observations(data.get("status"), status=True)
    rows = []
    # product advances the last dimension fastest, as JSON-stat requires.
    for flat_index, coordinate in enumerate(product(*codes)):
        row = {}
        for dim, code, dimension_labels in zip(dimensions, coordinate, labels):
            row[dim] = dimension_labels.get(code, code)
            row[f"{dim}_code"] = code
        row["value"] = values[flat_index]
        row["status"] = statuses[flat_index]
        rows.append(row)
    frame = pd.DataFrame(rows, columns=columns)
    frame["status"] = pd.Series(statuses, dtype=object)
    frame.attrs["jsonstat_metadata"] = deepcopy(
        {key: value for key, value in data.items() if key not in {"value", "status"}}
    )
    return frame
