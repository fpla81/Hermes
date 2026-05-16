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


PROMPT_TEMPLATE = """Você é assistente jurídico do TST. Receba o blueprint do despacho de admissibilidade (recursos esperados) e o texto rotulado das peças do processo. Produza um dossiê estruturado em JSON puro (sem markdown, sem ```) que vai alimentar a geração da minuta.

FORMATO OBRIGATÓRIO:

{
  "recursos": [
    {
      "tipo": "recurso_revista" | "agravo_instrumento" | "agravo_interno",
      "parte": "reclamante" | "reclamada" | "reclamantes" | "reclamadas" | "ministerio_publico" | "outro",
      "marco_legal_hint": "13.015/2014" | "13.467/2017" | null,   // só se conseguir inferir da data do acórdão regional
      "temas": [
        {
          "nome": "DESCRIÇÃO EM CAIXA ALTA - TERMOS SEPARADOS POR HÍFEN",  // ex.: "HORAS EXTRAS - DIVISOR APLICÁVEL"
          "admissibilidade": "admitido" | "denegado" | "parcialmente_admitido" | "prejudicado" | "nao_conhecido",  // SEGUIR o blueprint do despacho. Para AIRR, indicar a situação do RR que ele ataca.
          "acordao_recorrido_resumo": "...",        // 1 parágrafo seguindo a fórmula "O Eg. TRT [negou/deu] provimento ao Recurso Ordinário [da/do] [Reclamada/Reclamante], ao fundamento de que ... Eis as razões de decidir:"
          "acordao_recorrido_transcricao": "...",   // trecho LITERAL do acórdão regional no ponto, para citar
          "embargos_resumo": "..." | null,          // se houver Embargos de Declaração no ponto
          "embargos_transcricao": "..." | null,
          "fundamentos_argumentativos": ["..."],    // alegações jurídicas/factuais da parte, em texto direto SEM bullets, prontos pra colar; verbos: alega, aduz, sustenta, argumenta
          "permissivos_invocados": ["..."],         // arts/súmulas/OJs/precedentes invocados pela parte, AGRUPADOS POR DIPLOMA; ex.: "arts. 5º, II e LV, da Constituição; 832 da CLT"
          "obices_aplicaveis": ["..."],             // ex.: "Súmula 126 do TST", "art. 896, § 1º-A, da CLT"
          "jurisprudencia_citada": ["..."],         // precedentes vinculantes do STF/TST citados PELA PARTE (não os de fundamentação)
          "conclusao_sugerida": "conhecer e dar provimento" | "conhecer e negar provimento" | "não conhecer" | "nego seguimento" | "dou provimento ao Agravo de Instrumento" | "prejudicado",
          "analise_juridica": "..."                  // 1-2 parágrafos antecipando a análise para colar na minuta
        }
      ]
    }
  ],
  "observacoes": "..."
}

REGRAS ESTRITAS:

1. NÃO MISTURE fundamentos argumentativos com permissivos. Fundamentos = razões jurídicas/factuais. Permissivos = dispositivos/súmulas/OJs invocados.
2. Permissivos agrupados por diploma. Ex.: "arts. 5º, II e LV, e 7º, XXVI, da Constituição; 832 da CLT; 489, § 1º, do CPC".
3. Ignore permissivos que aparecem APENAS em ementas/jurisprudência citada (não invocados diretamente pela parte como base recursal).
4. Nomes processuais: "Eg. TRT", "TRT", "Corte Regional". NUNCA "Tribunal Regional" isolado.
5. "Constituição da República" / "Constituição". NUNCA "Constituição Federal" nem "CF". Idem "Código Civil" (nunca "CC").
6. Tema em caixa alta com " - " separando termos. NUNCA "TEMA Nº 1" ou ". ". Ex.: "DANO EXISTENCIAL - JORNADA EXTENUANTE".
7. Use os temas do blueprint como referência. Não invente recursos/temas inexistentes nas peças.
8. Se a data do acórdão regional não estiver clara, deixe marco_legal_hint=null.
9. Em `acordao_recorrido_transcricao` e `embargos_transcricao`, PRESERVE as quebras de parágrafo do texto original: separe parágrafos com `\\n\\n` (no JSON, isto é, a sequência literal de dois caracteres barra-invertida-n). NÃO colapse o trecho em um único bloco — a leitura da minuta depende dessa estrutura.

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
