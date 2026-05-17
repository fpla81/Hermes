"""Provedor LLM (Gemini) com stub de fallback.

A escolha é controlada por ``GEMINI_API_KEY``: ausente → ``StubProvider``
retorna um esqueleto previsível, útil em dev e CI. Presente →
``GeminiProvider`` chama a API REST do Google Generative Language.

Nenhum payload PII deve chegar aqui: o caller é responsável por aplicar
``hermes_api.anonymizer`` antes.
"""

from __future__ import annotations

import logging
import time
from typing import Protocol

import httpx

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

    def analyze(self, anonymized_text: str) -> str:
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": anonymized_text}]},
            ],
        }
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
