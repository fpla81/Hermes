"""Anonimizador via LLM (Gemini Flash).

Complementa o anonimizador regex (``hermes_api.anonymizer``) cobrindo o que
regex não pega: nomes próprios, endereços, nomes de empresas sem CNPJ
visível, datas que identificam pessoas (nascimento, admissão), matrículas
e RG.

Custo médio por caso (~50k tokens totais com Flash):
input $0,075/1M + output $0,30/1M ≈ $0,004 = R$ 0,02.

Stub-aware: sem ``GEMINI_API_KEY`` devolve o input intocado com um aviso
no mapping (chave ``_note``).
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from ..anonymizer import AnonymizationResult
from ..config import get_settings

PROMPT_TEMPLATE = """Você é um anonimizador de textos jurídicos trabalhistas.

Identifique no texto abaixo todas as informações pessoais identificáveis
(PII), EXCETO CPF, CNPJ, OAB, e-mails e telefones (já tratados antes).

Retorne APENAS JSON puro (sem markdown, sem ```), no formato:
{
  "entities": [
    {"type": "NAME", "original": "João da Silva Santos"},
    {"type": "ADDRESS", "original": "Rua das Flores, 123"},
    {"type": "COMPANY", "original": "Acme Indústria Têxtil LTDA"},
    {"type": "DATE", "original": "15/03/1985"},
    {"type": "MATRICULA", "original": "12345-6"}
  ]
}

Tipos válidos:
- NAME: nome completo ou parcial de pessoas físicas (partes, advogados, testemunhas, juízes não-canônicos).
- ADDRESS: endereço, CEP, bairro identificável.
- COMPANY: razão social de empresa que NÃO está em formato de CNPJ.
- DATE: data que identifica pessoa específica (nascimento, admissão, demissão); ignore datas processuais (autuação, sessão, despacho).
- MATRICULA: matrícula funcional, RG, identidade, prontuário.

Importante:
- Cada ocorrência única — se "João Silva" aparecer 5 vezes, liste UMA vez.
- ``original`` deve ser o trecho EXATO do texto, preservando capitalização/acentos.
- Ignore termos genéricos: "Reclamante", "Reclamada", "MM. Juiz", "Tribunal Regional".
- Se nada encontrar, retorne {"entities": []}.

Texto:
---
{text}
---
"""


class _GeminiAnonymizerProvider:
    """Cliente mínimo do Gemini para anonimização. Separado do llm.py
    pra permitir modelo diferente (Flash) sem mexer no provider de análise."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, model: str, timeout: float = 120.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def detect_pii(self, text: str) -> str:
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": PROMPT_TEMPLATE.replace("{text}", text)}]},
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


def _extract_entities(raw: str) -> list[dict[str, str]]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    entities = data.get("entities") if isinstance(data, dict) else None
    if not isinstance(entities, list):
        return []
    out: list[dict[str, str]] = []
    for item in entities:
        if not isinstance(item, dict):
            continue
        t = str(item.get("type", "")).strip().upper()
        o = str(item.get("original", "")).strip()
        if t and o:
            out.append({"type": t, "original": o})
    return out


def llm_anonymize(text: str) -> AnonymizationResult:
    """Anonimiza nomes/endereços/empresas/datas/matrículas via Gemini Flash.

    Devolve ``AnonymizationResult`` com texto substituído e mapping
    ``{placeholder: original}``. Se o LLM não estiver configurado ou falhar,
    devolve o input intocado e registra um aviso em ``mapping["_note"]``.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return AnonymizationResult(
            text=text,
            mapping={"_note": "GEMINI_API_KEY ausente — LLM anonymizer pulado"},
        )

    provider = _GeminiAnonymizerProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_anonymizer_model,
    )
    try:
        raw = provider.detect_pii(text)
    except Exception as exc:  # noqa: BLE001
        return AnonymizationResult(
            text=text,
            mapping={"_note": f"falha no LLM anonymizer: {exc}"},
        )

    entities = _extract_entities(raw)
    counters: dict[str, int] = {}
    mapping: dict[str, str] = {}
    out = text
    # ordena por tamanho decrescente — substitui o longo antes pra evitar
    # match parcial em strings que contêm outras
    for entity in sorted(entities, key=lambda e: len(e["original"]), reverse=True):
        original = entity["original"]
        if original not in out:
            continue
        label = entity["type"]
        counters[label] = counters.get(label, 0) + 1
        placeholder = f"<{label}_{counters[label]}>"
        mapping[placeholder] = original
        out = out.replace(original, placeholder)
    return AnonymizationResult(text=out, mapping=mapping)


def full_anonymize(text: str) -> AnonymizationResult:
    """Pipeline completo: regex (CPF/CNPJ/OAB/email/telefone) → LLM (resto).

    Retorna ``AnonymizationResult`` com o texto totalmente anonimizado e
    o mapping consolidado dos dois passos.
    """
    from ..anonymizer import anonymize

    regex_result = anonymize(text)
    llm_result = llm_anonymize(regex_result.text)
    combined_mapping = {**regex_result.mapping, **llm_result.mapping}
    return AnonymizationResult(text=llm_result.text, mapping=combined_mapping)


__all__ = ["llm_anonymize", "full_anonymize"]


def _normalize_entities(items: Any) -> list[dict[str, str]]:  # pragma: no cover - kept for typing
    return [i for i in items if isinstance(i, dict)]
