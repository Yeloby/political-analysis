import httpx
import pytest

from samfunnsdata.providers.norway.fhi import FhiClient, jsonstat_to_frame


def test_sources(monkeypatch):
    payload = [
        {
            "id": "lmr",
            "title": "Legemiddelregisteret (LMR)",
            "description": "Legemiddelstatistikk",
            "aboutUrl": "https://example.test/lmr",
            "publishedBy": "Folkehelseinstituttet",
        }
    ]

    def fake_get(url, timeout, **kwargs):
        return httpx.Response(
            200,
            json=payload,
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    source = FhiClient().sources()[0]

    assert source.id == "lmr"
    assert source.title == "Legemiddelregisteret (LMR)"
    assert source.published_by == "Folkehelseinstituttet"


def test_tables(monkeypatch):
    payload = [
        {
            "tableId": 825,
            "title": "Per ATC-kode. 2004-2025.",
            "publishedAt": "2026-03-03T08:00:00Z",
            "modifiedAt": "2026-02-26T11:20:35Z",
        }
    ]

    def fake_get(url, timeout, **kwargs):
        return httpx.Response(
            200,
            json=payload,
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    table = FhiClient().tables("lmr")[0]

    assert table.id == 825
    assert table.title == "Per ATC-kode. 2004-2025."


def test_table_metadata(monkeypatch):
    payload = {
        "name": "Per ATC-kode",
        "isOfficialStatistics": True,
        "paragraphs": [],
    }

    def fake_get(url, timeout, **kwargs):
        return httpx.Response(
            200,
            json=payload,
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    metadata = FhiClient().metadata("lmr", 825)

    assert metadata["isOfficialStatistics"] is True


def test_dimensions(monkeypatch):
    payload = {
        "dimensions": [
            {
                "code": "Kjonn_Verdi",
                "label": "Kjønn",
                "categories": [],
            },
            {
                "code": "Utlevering_Ar",
                "label": "År",
                "categories": [],
            },
        ]
    }

    def fake_get(url, timeout, **kwargs):
        return httpx.Response(
            200,
            json=payload,
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    dimensions = FhiClient().dimensions("lmr", 825)

    assert [item["code"] for item in dimensions] == [
        "Kjonn_Verdi",
        "Utlevering_Ar",
    ]


@pytest.mark.parametrize("limit", [None, 17])
def test_data_post(monkeypatch, limit):
    payload = {"id": ["x"], "value": [42]}
    dimensions = {"Atc_Verdi": ["A10BA02"], "Utlevering_Ar": ["2024", "2025"]}

    def fake_post(url, *, json, timeout, **kwargs):
        assert url == "https://statistikk-data.fhi.no/api/open/v1/lmr/Table/825/data"
        assert timeout == 7.5
        assert json == {
            "dimensions": [
                {"code": code, "filter": "item", "values": values}
                for code, values in dimensions.items()
            ],
            "response": {"format": "json-stat2", "maxRowCount": limit or 50000},
        }
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    kwargs = {} if limit is None else {"max_row_count": limit}
    assert FhiClient(timeout=7.5).data("lmr", 825, dimensions, **kwargs) == payload


def test_data_http_error(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(400, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(httpx.HTTPStatusError):
        FhiClient().data("other", 12, {"x": ["a"]})


def dataset():
    return {
        "version": "2.0", "class": "dataset",
        "id": ["A", "B"], "size": [2, 3],
        "dimension": {
            "B": {"category": {"index": ["b1", "b2", "b3"]}},
            "A": {"category": {
                "index": {"a2": 1, "a1": 0},
                "label": {"a2": "Second", "a1": "First"},
            }},
        },
        "value": [11, 12, 13, 21, 22, 23],
    }


def test_multidimensional_order_and_labels():
    frame = jsonstat_to_frame(dataset())
    assert list(frame.columns) == ["A", "A_code", "B", "B_code", "value", "status"]
    assert list(frame.itertuples(index=False, name=None)) == [
        ("First", "a1", "b1", "b1", 11, None),
        ("First", "a1", "b2", "b2", 12, None),
        ("First", "a1", "b3", "b3", 13, None),
        ("Second", "a2", "b1", "b1", 21, None),
        ("Second", "a2", "b2", "b2", 22, None),
        ("Second", "a2", "b3", "b3", 23, None),
    ]


@pytest.mark.parametrize("index", [{"A10BA02": 0}, ["A10BA02"], None])
def test_single_dimension(index):
    category = {"label": {"A10BA02": "A10BA02 - metformin"}}
    if index is not None:
        category["index"] = index
    frame = jsonstat_to_frame({
        "id": ["Atc_Verdi"], "size": [1],
        "dimension": {"Atc_Verdi": {"category": category}}, "value": [42],
    })
    assert frame.iloc[0].to_dict() == {
        "Atc_Verdi": "A10BA02 - metformin", "Atc_Verdi_code": "A10BA02",
        "value": 42, "status": None,
    }


@pytest.mark.parametrize("sparse", [False, True])
def test_missing_zero_and_status(sparse):
    data = dataset()
    data["value"] = {"0": 0, "4": 5} if sparse else [0, None, None, None, 5, None]
    data["status"] = (
        {"1": "..", "2": ".", "3": ":", "4": "unknown"} if sparse
        else [None, "..", ".", ":", "unknown", None]
    )
    data["extension"] = {"flags": {
        "index": ["..", ".", ":"],
        "label": {"..": "Manglende data", ".": "Lar seg ikke beregne",
                  ":": "Anonymisert eller skjult av andre årsaker"},
    }}
    frame = jsonstat_to_frame(data)
    assert frame["value"].iloc[0] == 0
    assert frame["value"].isna().tolist() == [False, True, True, True, False, True]
    assert frame["status"].tolist() == [None, "..", ".", ":", "unknown", None]
    assert frame.attrs["jsonstat_metadata"]["extension"] == data["extension"]
    frame.attrs["jsonstat_metadata"]["extension"]["flags"]["label"][":"] = "Changed"
    assert data["extension"]["flags"]["label"][":"] == "Anonymisert eller skjult av andre årsaker"


@pytest.mark.parametrize("status", ["", ":"])
def test_scalar_status(status):
    data = dataset()
    data["status"] = status
    assert jsonstat_to_frame(data)["status"].tolist() == [status] * 6


@pytest.mark.parametrize("field,value", [
    ("size", [2, 2]), ("size", [2]), ("value", [1]),
    ("value", {"6": 1}), ("status", [":"]),
])
def test_malformed_shape_rejected(field, value):
    data = dataset()
    data[field] = value
    with pytest.raises(ValueError):
        jsonstat_to_frame(data)


def test_invalid_category_positions():
    data = dataset()
    data["dimension"]["A"]["category"]["index"] = {"a1": 0, "a2": 2}
    with pytest.raises(ValueError, match="category positions"):
        jsonstat_to_frame(data)


def test_column_collision_rejected():
    data = {"id": ["value"], "size": [1]}
    with pytest.raises(ValueError, match="collide"):
        jsonstat_to_frame(data)


def test_data_frame(monkeypatch):
    def fake_data(self, source, table_id, dimensions, *, max_row_count):
        assert (source, table_id, dimensions, max_row_count) == (
            "other", 123, {"A": ["a1", "a2"]}, 99,
        )
        return dataset()

    monkeypatch.setattr(FhiClient, "data", fake_data)
    frame = FhiClient().data_frame("other", 123, {"A": ["a1", "a2"]}, max_row_count=99)
    assert frame["value"].tolist() == [11, 12, 13, 21, 22, 23]
