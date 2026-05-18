"""Cache layer para respostas do LLM e para nomes de Gemini Context Cache.

Best-effort: qualquer falha do Redis é silenciada e a chamada LLM original
acontece normalmente. Sem fallback in-memory — se o Redis cair, o sistema
volta a operar sem cache até o próximo restart resolvido.
"""

from __future__ import annotations

import hashlib
import logging

import redis

from .config import get_settings

log = logging.getLogger(__name__)

_RESPONSE_PREFIX = "llm:resp:"
_CONTEXT_CACHE_PREFIX = "gemini:ctxcache:"

_client: redis.Redis | None = None
_disabled = False


def _get_client() -> redis.Redis | None:
    global _client, _disabled
    if _disabled:
        return None
    if _client is not None:
        return _client
    s = get_settings()
    try:
        c = redis.Redis.from_url(
            s.redis_url,
            socket_connect_timeout=0.5,
            socket_timeout=1.0,
            decode_responses=True,
        )
        c.ping()
    except Exception as exc:  # noqa: BLE001
        log.info("cache: Redis indisponível (%s) — cache desativado neste processo", exc)
        _disabled = True
        return None
    _client = c
    return c


def _hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def response_get(model: str, prompt: str) -> str | None:
    s = get_settings()
    if not s.llm_response_cache_enabled:
        return None
    c = _get_client()
    if c is None:
        return None
    try:
        return c.get(_RESPONSE_PREFIX + _hash(model, prompt))
    except Exception as exc:  # noqa: BLE001
        log.debug("cache.response_get falhou: %s", exc)
        return None


def response_set(model: str, prompt: str, response: str) -> None:
    s = get_settings()
    if not s.llm_response_cache_enabled or not response:
        return
    c = _get_client()
    if c is None:
        return
    try:
        c.set(
            _RESPONSE_PREFIX + _hash(model, prompt),
            response,
            ex=s.llm_response_cache_ttl,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("cache.response_set falhou: %s", exc)


def context_cache_name_get(model: str, static_prefix: str) -> str | None:
    c = _get_client()
    if c is None:
        return None
    try:
        return c.get(_CONTEXT_CACHE_PREFIX + _hash(model, static_prefix))
    except Exception as exc:  # noqa: BLE001
        log.debug("cache.context_cache_name_get falhou: %s", exc)
        return None


def context_cache_name_set(
    model: str, static_prefix: str, name: str, ttl_seconds: int
) -> None:
    c = _get_client()
    if c is None:
        return
    # TTL local ligeiramente menor que o do Gemini pra evitar referenciar
    # um cache já expirado do lado deles.
    buffer = min(60, max(5, ttl_seconds // 20))
    try:
        c.set(
            _CONTEXT_CACHE_PREFIX + _hash(model, static_prefix),
            name,
            ex=max(1, ttl_seconds - buffer),
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("cache.context_cache_name_set falhou: %s", exc)


def context_cache_name_drop(model: str, static_prefix: str) -> None:
    c = _get_client()
    if c is None:
        return
    try:
        c.delete(_CONTEXT_CACHE_PREFIX + _hash(model, static_prefix))
    except Exception as exc:  # noqa: BLE001
        log.debug("cache.context_cache_name_drop falhou: %s", exc)
