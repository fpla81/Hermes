"""Testes do cache layer (Redis response cache + Gemini context cache).

Sem Redis real: monkeypatcha ``hermes_api.cache._get_client`` pra um
``FakeRedis`` dict-based. Sem rede pro Gemini: monkeypatcha ``httpx.post``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.calls: list[tuple[str, ...]] = []

    def get(self, k: str) -> str | None:
        self.calls.append(("get", k))
        return self.store.get(k)

    def set(self, k: str, v: str, ex: int | None = None) -> None:
        self.calls.append(("set", k, str(ex)))
        self.store[k] = v

    def delete(self, k: str) -> None:
        self.calls.append(("delete", k))
        self.store.pop(k, None)

    def ping(self) -> bool:
        return True


@pytest.fixture
def fake_redis(monkeypatch):
    fr = FakeRedis()
    from hermes_api import cache as cache_mod

    monkeypatch.setattr(cache_mod, "_client", None)
    monkeypatch.setattr(cache_mod, "_disabled", False)
    monkeypatch.setattr(cache_mod, "_get_client", lambda: fr)
    return fr


@pytest.fixture
def settings_with_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    monkeypatch.setenv("LLM_RESPONSE_CACHE_ENABLED", "true")
    monkeypatch.setenv("GEMINI_CONTEXT_CACHE_ENABLED", "true")
    from hermes_api.config import get_settings

    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def _gen_response(text: str) -> Any:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json = MagicMock(
        return_value={
            "candidates": [{"content": {"parts": [{"text": text}]}}]
        }
    )
    return r


def _cache_create_response(name: str) -> Any:
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json = MagicMock(return_value={"name": name})
    return r


def test_analyze_response_cache_hit_skips_network(
    monkeypatch, fake_redis, settings_with_gemini
):
    from hermes_api.llm import GeminiProvider

    prov = GeminiProvider(api_key="fake", model="gemini-2.5-flash-lite")
    post_calls: list[dict] = []

    def fake_post(url, **kw):
        post_calls.append({"url": url, "json": kw.get("json")})
        return _gen_response("RESP")

    monkeypatch.setattr("hermes_api.llm.httpx.post", fake_post)

    out1 = prov.analyze("prompt-x")
    assert out1 == "RESP"
    assert len(post_calls) == 1

    # Segunda chamada: hit do cache, sem rede.
    out2 = prov.analyze("prompt-x")
    assert out2 == "RESP"
    assert len(post_calls) == 1  # não chamou de novo


def test_analyze_cached_creates_context_cache_then_reuses(
    monkeypatch, fake_redis, settings_with_gemini
):
    from hermes_api.llm import GeminiProvider

    prov = GeminiProvider(api_key="fake", model="gemini-2.5-flash-lite")
    post_calls: list[dict] = []

    def fake_post(url, **kw):
        post_calls.append({"url": url, "json": kw.get("json")})
        if url.endswith("/cachedContents"):
            return _cache_create_response("cachedContents/abc123")
        return _gen_response('{"matches":[]}')

    monkeypatch.setattr("hermes_api.llm.httpx.post", fake_post)

    static = "STATIC " * 100
    out1 = prov.analyze_cached(static, "dyn-1")
    out2 = prov.analyze_cached(static, "dyn-2")

    # Cria 1x o context cache (segundo call reusa nome via Redis).
    cache_creates = [c for c in post_calls if c["url"].endswith("/cachedContents")]
    assert len(cache_creates) == 1
    # generateContent rodou 2x e ambas referenciaram o cached name.
    generates = [c for c in post_calls if "generateContent" in c["url"]]
    assert len(generates) == 2
    for g in generates:
        assert g["json"]["cachedContent"] == "cachedContents/abc123"

    assert out1 == '{"matches":[]}'
    assert out2 == '{"matches":[]}'


def test_analyze_cached_response_hit_short_circuits_everything(
    monkeypatch, fake_redis, settings_with_gemini
):
    from hermes_api.llm import GeminiProvider

    prov = GeminiProvider(api_key="fake", model="gemini-2.5-flash-lite")
    post_calls: list[dict] = []

    def fake_post(url, **kw):
        post_calls.append({"url": url})
        if url.endswith("/cachedContents"):
            return _cache_create_response("cachedContents/abc")
        return _gen_response("RESP-Y")

    monkeypatch.setattr("hermes_api.llm.httpx.post", fake_post)

    out1 = prov.analyze_cached("S" * 50, "DYN")
    assert out1 == "RESP-Y"
    n_before = len(post_calls)

    out2 = prov.analyze_cached("S" * 50, "DYN")
    assert out2 == "RESP-Y"
    # Sem nenhuma chamada nova de rede.
    assert len(post_calls) == n_before


def test_analyze_cached_falls_back_when_context_cache_create_fails(
    monkeypatch, fake_redis, settings_with_gemini
):
    import httpx
    from hermes_api.llm import GeminiProvider

    prov = GeminiProvider(api_key="fake", model="gemini-2.5-flash-lite")
    post_calls: list[dict] = []

    def fake_post(url, **kw):
        post_calls.append({"url": url, "json": kw.get("json")})
        if url.endswith("/cachedContents"):
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.text = "minimum tokens not met"
            raise httpx.HTTPStatusError(
                "bad request", request=MagicMock(), response=mock_resp
            )
        return _gen_response("FALLBACK-OK")

    monkeypatch.setattr("hermes_api.llm.httpx.post", fake_post)

    out = prov.analyze_cached("S", "D")
    assert out == "FALLBACK-OK"
    # generateContent foi chamado sem cachedContent.
    generates = [c for c in post_calls if "generateContent" in c["url"]]
    assert len(generates) == 1
    assert "cachedContent" not in (generates[0]["json"] or {})


def test_response_cache_disabled_skips_redis(monkeypatch, fake_redis):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setenv("LLM_RESPONSE_CACHE_ENABLED", "false")
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    from hermes_api.llm import GeminiProvider

    prov = GeminiProvider(api_key="fake", model="gemini-2.5-flash-lite")
    post_calls = []

    def fake_post(url, **kw):
        post_calls.append(url)
        return _gen_response("X")

    monkeypatch.setattr("hermes_api.llm.httpx.post", fake_post)
    prov.analyze("p")
    prov.analyze("p")
    # Sem cache: rede 2x.
    assert len(post_calls) == 2
    get_settings.cache_clear()


def test_context_cache_400_on_generate_drops_name_and_retries_uncached(
    monkeypatch, fake_redis, settings_with_gemini
):
    """Se o cached name expirou no Gemini, generateContent retorna 4xx;
    o provider deve dropar o nome do Redis e cair pra analyze() sem cache.
    """
    import httpx
    from hermes_api import cache as cache_mod
    from hermes_api.llm import GeminiProvider

    # Pré-popula um cache name no Redis (simula cache previamente criado).
    cache_mod.context_cache_name_set(
        "gemini-2.5-flash-lite", "STATIC", "cachedContents/stale", 3600
    )

    prov = GeminiProvider(api_key="fake", model="gemini-2.5-flash-lite")
    seq: list[str] = []

    def fake_post(url, **kw):
        seq.append(url)
        if "generateContent" in url and kw.get("json", {}).get("cachedContent"):
            # 1ª chamada com cache → 404
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.text = "cache not found"
            raise httpx.HTTPStatusError(
                "expired", request=MagicMock(), response=mock_resp
            )
        return _gen_response("RECOVERED")

    monkeypatch.setattr("hermes_api.llm.httpx.post", fake_post)

    out = prov.analyze_cached("STATIC", "DYN")
    assert out == "RECOVERED"
    # Nome stale foi dropado.
    assert cache_mod.context_cache_name_get(
        "gemini-2.5-flash-lite", "STATIC"
    ) is None
