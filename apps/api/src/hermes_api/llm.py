"""Provedor LLM (Gemini) com stub de fallback.

A escolha é controlada por ``GEMINI_API_KEY``: ausente → ``StubProvider``
retorna um esqueleto previsível, útil em dev e CI. Presente →
``GeminiProvider`` chama a API REST do Google Generative Language.

Nenhum payload PII deve chegar aqui: o caller é responsável por aplicar
``hermes_api.anonymizer`` antes.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from .config import get_settings


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
    """REST minimal: POST ``models/{model}:generateContent``."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, model: str, timeout: float = 180.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def analyze(self, anonymized_text: str) -> str:
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": anonymized_text}]},
            ],
        }
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


def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.gemini_api_key:
        return GeminiProvider(api_key=s.gemini_api_key, model=s.gemini_model)
    return StubProvider()
