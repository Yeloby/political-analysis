import httpx
import pytest

from samfunnsdata import network


def test_cache_only_blocks_http_backend(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    network.set_mode(network.NetworkMode.CACHE_ONLY)
    try:
        with pytest.raises(network.CacheOnlyMiss):
            network.request("ssb", "table_data", "GET", "https://data.ssb.no/api")
        assert calls == []
    finally:
        network.set_mode(network.NetworkMode.ONLINE)


def test_redirect_without_follow_is_rejected_before_second_hop(monkeypatch):
    calls = []

    class RedirectResponse:
        is_redirect = True
        status_code = 302

        def __init__(self):
            self.headers = {"location": "https://data.ssb.no/next"}
            self.url = "https://data.ssb.no/api"

        def close(self):
            pass

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return RedirectResponse()
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    network.set_mode(network.NetworkMode.ONLINE)
    try:
        with pytest.raises(network.DestinationNotAllowed):
            network.request(
                "ssb",
                "table_data",
                "GET",
                "https://data.ssb.no/api",
                follow_redirects=False,
            )
        assert calls == ["https://data.ssb.no/api"]
    finally:
        network.set_mode(network.NetworkMode.ONLINE)
