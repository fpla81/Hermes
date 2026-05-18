"""Provedor LLM (Gemini) com stub de fallback.

A escolha é controlada por ``GEMINI_API_KEY``: ausente → ``StubProvider``
retorna um esqueleto previsível, útil em dev e CI. Presente →
``GeminiProvider`` chama a API REST do Google Generative Language.

Caching:

- **Response cache** (Redis): toda chamada ``analyze`` consulta um cache
  chaveado por ``sha256(model + prompt)``. Hits evitam a chamada de rede
  inteira. Falha do Redis é silenciosa (fall-through).
- **Gemini Context Cache**: ``analyze_cached(static_prefix, dynamic)``
  cria (ou reusa) um ``cachedContents`` na API do Gemini com o prefixo
  estático. Tokens cacheados custam ~25% do normal. Útil para prompts
  com bloco fixo grande (tabela de Repetitivos).

Nenhum payload PII deve chegar aqui: o caller é responsável por aplicar
``hermes_api.anonymizer`` antes.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

import httpx

from . import cache
from .config import get_settings

log = logging.getLogger(__name__)


class LLMProvider(Protocol):
    def analyze(self, anonymized_text: str) -> str: ...


class StubProvider:
    def analyze(self, anonymized_text: str) -> str:
        return (
            "## Análise (stub)\n\n"
            "Configure GEMINI_API_KEY para gerar a análise real.\n\n"
            f"Tamanho do texto anonimizado: {len(anonymized_text)} caracteres."
        )

    def analyze_cached(self, static_prefix: str, dynamic: str) -> str:
        return self.analyze(static_prefix + "\n\n" + dynamic)


class GeminiProvider:
    """REST minimal: POST ``models/{model}:generateContent``.

    Timeout granular (connect / read separados) e retry exponencial em
    ``ReadTimeout`` — o Gemini Flash às vezes leva 4-6 min em prompts
    grandes (minuta com dossiê + tabela de Repetitivos).
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model: str,
        read_timeout: float = 600.0,
        connect_timeout: float = 15.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=connect_timeout,
            pool=connect_timeout,
        )
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------
    def analyze(self, anonymized_text: str) -> str:
        cached = cache.response_get(self.model, anonymized_text)
        if cached is not None:
            log.debug("llm: response cache hit (len=%d)", len(cached))
            return cached
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": anonymized_text}]},
            ],
        }
        out = self._post_generate(payload)
        cache.response_set(self.model, anonymized_text, out)
        return out

    def analyze_cached(self, static_prefix: str, dynamic: str) -> str:
        """Versão com Gemini Context Caching aplicado ao ``static_prefix``.

        ``static_prefix`` deve ser conteúdo grande e estável (ex.: tabela
        de Repetitivos + instruções fixas). ``dynamic`` é o input por
        request (ex.: tema do caso + formato de output).
        """
        settings = get_settings()
        full_prompt = static_prefix + "\n\n" + dynamic
        cached = cache.response_get(self.model, full_prompt)
        if cached is not None:
            log.debug("llm: response cache hit (cached path, len=%d)", len(cached))
            return cached

        if not settings.gemini_context_cache_enabled:
            return self.analyze(full_prompt)

        cache_name = self._get_or_create_context_cache(
            static_prefix, settings.gemini_context_cache_ttl
        )
        if not cache_name:
            # Falha ao criar context cache (ex.: prefix abaixo do mínimo
            # de tokens). Cai pra modo normal.
            return self.analyze(full_prompt)

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": dynamic}]},
            ],
            "cachedContent": cache_name,
        }
        try:
            out = self._post_generate(payload)
        except httpx.HTTPStatusError as exc:
            # 4xx (cache expirado/inválido): dropa o nome e tenta sem cache.
            if 400 <= exc.response.status_code < 500:
                log.warning(
                    "gemini context cache inválido (%s) — recriando e tentando sem cache",
                    exc.response.status_code,
                )
                cache.context_cache_name_drop(self.model, static_prefix)
                out = self.analyze(full_prompt)
            else:
                raise
        cache.response_set(self.model, full_prompt, out)
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _post_generate(self, payload: dict[str, Any]) -> str:
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = httpx.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                    timeout=self.timeout,
                )
                r.raise_for_status()
                data = r.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    return ""
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    backoff = 2 ** attempt
                    log.warning(
                        "Gemini timeout (tentativa %s/%s) — retry em %ss",
                        attempt + 1,
                        self.max_retries + 1,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                raise
        if last_exc:
            raise last_exc
        return ""

    def _get_or_create_context_cache(
        self, static_prefix: str, ttl_seconds: int
    ) -> str | None:
        name = cache.context_cache_name_get(self.model, static_prefix)
        if name:
            return name
        try:
            r = httpx.post(
                f"{self.BASE_URL}/cachedContents",
                params={"key": self.api_key},
                json={
                    "model": f"models/{self.model}",
                    "contents": [
                        {"role": "user", "parts": [{"text": static_prefix}]},
                    ],
                    "ttl": f"{ttl_seconds}s",
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
            name = data.get("name")
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300] if exc.response is not None else ""
            log.warning(
                "gemini context cache create falhou (%s): %s",
                exc.response.status_code if exc.response is not None else "?",
                body,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            log.warning("gemini context cache create erro: %s", exc)
            return None
        if not name:
            return None
        cache.context_cache_name_set(self.model, static_prefix, name, ttl_seconds)
        log.info("gemini context cache criado: %s (ttl=%ds)", name, ttl_seconds)
        return name


def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.gemini_api_key:
        return GeminiProvider(
            api_key=s.gemini_api_key,
            model=s.gemini_model,
            read_timeout=s.gemini_read_timeout,
            connect_timeout=s.gemini_connect_timeout,
            max_retries=s.gemini_max_retries,
        )
    return StubProvider()
