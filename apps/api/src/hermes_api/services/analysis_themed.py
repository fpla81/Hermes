"""Análise temática estruturada: peças + blueprint → dossiê em JSON.

Usa o LLM (Gemini Pro recomendado pra qualidade jurídica) com prompt que
recebe (i) o blueprint do despacho âncora e (ii) o texto rotulado de cada
peça já anonimizada. Pede um dossiê JSON por recurso/tema com fundamentos,
permissivos, óbices e jurisprudência citada.

Sem ``GEMINI_API_KEY`` devolve um esqueleto vazio com note.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..llm import StubProvider, get_llm_provider

TIPO_LABEL = {
    "acordao_regional": "Acórdão Regional",
    "acordao_embargos_declaracao": "Acórdão de Embargos de Declaração",
    "despacho_admissibilidade": "Despacho de Admissibilidade",
    "recurso_revista": "Recurso de Revista",
    "agravo_instrumento": "Agravo de Instrumento",
    "agravo_interno": "Agravo Interno",
}

PARTE_LABEL = {
    "reclamante": "Reclamante",
    "reclamada": "Reclamada",
    "reclamantes": "Reclamantes",
    "reclamadas": "Reclamadas",
    "ministerio_publico": "Ministério Público",
    "outro": "Outro",
}


PROMPT_TEMPLATE = """Você é assistente jurídico do TST. Receba o blueprint do despacho de admissibilidade (recursos esperados) e o texto rotulado das peças do processo. Produza um dossiê estruturado em JSON puro (sem markdown, sem ```) com, para cada recurso recursal listado nas peças:

{
  "recursos": [
    {
      "tipo": "recurso_revista" | "agravo_instrumento" | "agravo_interno",
      "parte": "reclamante" | "reclamada" | ...,
      "temas": [
        {
          "nome": "...",                      // ex.: "Horas extras", "Dano moral"
          "fundamentos_argumentativos": ["..."],
          "permissivos_invocados": ["..."],
          "obices_aplicaveis": ["..."],       // Sumulas 126/296/297/333, art. 896 §1-A da CLT, etc.
          "jurisprudencia_citada": ["..."],
          "conclusao_sugerida": "conhecer e prover" | "conhecer e negar provimento" | "não conhecer" | "prejudicado" | "..."
        }
      ]
    }
  ],
  "observacoes": "..." // notas relevantes sobre divergências ou dúvidas
}

Importante:
- Use os temas listados no blueprint como referência mas não invente recursos que não estão nas peças.
- Cite literalmente trechos curtos como fundamento, sem inventar.
- Se a peça não trouxer informação suficiente para algum campo, devolva lista vazia.

Blueprint do despacho:
{blueprint}

Peças:
{pieces}
"""


def _format_blueprint(blueprint: dict[str, Any] | None) -> str:
    if not blueprint or not blueprint.get("recursos"):
        return "(blueprint indisponível)"
    lines: list[str] = []
    for r in blueprint["recursos"]:
        tipo = TIPO_LABEL.get(r.get("tipo", ""), r.get("tipo", ""))
        parte = PARTE_LABEL.get(r.get("parte", ""), r.get("parte", ""))
        temas = "; ".join(r.get("temas") or [])
        conc = r.get("conclusao", "")
        lines.append(f"- {tipo} ({parte}) — {conc}: {temas or '—'}")
    return "\n".join(lines)


def _format_pieces(pieces: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for p in pieces:
        tipo = TIPO_LABEL.get(p.get("tipo", ""), p.get("tipo", ""))
        parte = PARTE_LABEL.get(p.get("parte", ""), p.get("parte"))
        data = p.get("data")
        header = f"## {tipo}"
        if parte:
            header += f" — {parte}"
        if data:
            header += f" ({data})"
        parts.append(header)
        parts.append(str(p.get("text", "")))
        parts.append("")
    return "\n".join(parts).strip()


def _extract_json(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def build_dossie(
    pieces: list[dict[str, Any]],
    blueprint: dict[str, Any] | None,
) -> dict[str, Any]:
    provider = get_llm_provider()
    if isinstance(provider, StubProvider):
        return {
            "recursos": [],
            "observacoes": "GEMINI_API_KEY ausente — configure a chave para gerar o dossiê real.",
        }
    prompt = (
        PROMPT_TEMPLATE.replace("{blueprint}", _format_blueprint(blueprint))
        .replace("{pieces}", _format_pieces(pieces))
    )
    try:
        response = provider.analyze(prompt)
    except Exception as exc:  # noqa: BLE001
        return {"recursos": [], "observacoes": f"falha LLM: {exc}"}
    parsed = _extract_json(response)
    if parsed is None:
        return {"recursos": [], "observacoes": "resposta do LLM não veio em JSON válido"}
    return parsed
