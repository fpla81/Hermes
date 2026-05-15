"""Parser do Despacho de Admissibilidade do TRT.

Recebe o texto do despacho e devolve um "blueprint" estruturado dos recursos
esperados: para cada recurso, identifica a parte recorrente, os temas
analisados e a conclusão (admitido / denegado / parcialmente admitido /
prejudicado / não conhecido) e o tipo de recurso (RR / Agravo).

Implementação: usa ``LLMProvider.analyze`` com prompt JSON estruturado. Em
modo stub (sem GEMINI_API_KEY), devolve um esqueleto vazio com aviso. Falha
graciosamente — qualquer erro de parse devolve ``{recursos: [], note: ...}``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..llm import StubProvider, get_llm_provider

PROMPT_TEMPLATE = """Você é um analista jurídico do TST. Leia o despacho de admissibilidade do TRT abaixo e extraia, em JSON puro (sem ```), a lista de recursos analisados.

Para cada recurso, devolva:
- tipo: "recurso_revista" | "agravo_instrumento" | "agravo_interno" | "outro"
- parte: "reclamante" | "reclamada" | "reclamantes" | "reclamadas" | "ministerio_publico" | "outro"
- temas: lista de strings com os temas analisados (substantivo, ex.: "Horas extras", "Dano moral")
- conclusao: "admitido" | "denegado" | "parcialmente_admitido" | "prejudicado" | "nao_conhecido"

Formato exato da resposta (apenas JSON, sem texto adicional):
{
  "recursos": [
    {"tipo": "...", "parte": "...", "temas": ["..."], "conclusao": "..."}
  ]
}

Despacho:
---
{text}
---
"""


def _normalize_blueprint(raw: dict[str, Any]) -> dict[str, Any]:
    recursos = raw.get("recursos", []) if isinstance(raw, dict) else []
    cleaned: list[dict[str, Any]] = []
    for item in recursos:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "tipo": str(item.get("tipo", "")).strip().lower() or "outro",
            "parte": str(item.get("parte", "")).strip().lower() or "outro",
            "temas": [str(t).strip() for t in (item.get("temas") or []) if str(t).strip()],
            "conclusao": str(item.get("conclusao", "")).strip().lower() or "",
        })
    return {"recursos": cleaned}


def _extract_json(text: str) -> dict[str, Any] | None:
    # tenta extrair o primeiro bloco JSON do texto (LLM pode prefixar/sufixar)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def parse_despacho(text: str) -> dict[str, Any]:
    provider = get_llm_provider()
    if isinstance(provider, StubProvider):
        return {
            "recursos": [],
            "note": "GEMINI_API_KEY ausente — adicione a chave para extrair o blueprint automaticamente.",
        }
    try:
        prompt = PROMPT_TEMPLATE.replace("{text}", text)
        response = provider.analyze(prompt)
    except Exception as exc:  # noqa: BLE001
        return {"recursos": [], "note": f"falha ao chamar LLM: {exc}"}
    parsed = _extract_json(response)
    if parsed is None:
        return {"recursos": [], "note": "resposta do LLM não veio em JSON válido"}
    return _normalize_blueprint(parsed)
