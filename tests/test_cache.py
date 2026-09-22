from samfunnsdata.cache import JsonCache


def test_cache_roundtrip(tmp_path):
    cache = JsonCache(tmp_path)

    payload = {"query": "befolkning"}
    value = {"tables": [{"id": "07459"}]}

    assert cache.get("test", payload) is None
    cache.set("test", payload, value)
    assert cache.get("test", payload) == value
