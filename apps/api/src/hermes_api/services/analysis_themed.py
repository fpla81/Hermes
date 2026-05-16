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
          "blueprint_tema": "..." | null,  // STRING EXATA do tema correspondente no blueprint do despacho (sem normalização). null SOMENTE se for matéria nova legítima ausente do blueprint (raro).
          "admissibilidade": "admitido" | "denegado" | "parcialmente_admitido" | "prejudicado" | "nao_conhecido",  // SEGUIR o blueprint do despacho. Para AIRR, indicar a situação do RR que ele ataca.
          "acordao_recorrido_resumo": "...",        // 1 parágrafo seguindo a fórmula "O Eg. TRT [negou/deu] provimento ao Recurso Ordinário [da/do] [Reclamada/Reclamante], ao fundamento de que ... Eis as razões de decidir:"
          "acordao_recorrido_transcricao": ["..."],  // ARRAY de strings — UMA ENTRADA POR PARÁGRAFO. Transcreva o CAPÍTULO INTEIRO do acórdão regional referente ao tema: do início (relatório das razões recursais / delimitação do que se discute) até o fim (decisão da questão), passando pela fundamentação completa. NÃO recorte só o trecho "mais relevante" — premissas fáticas e jurídicas precisam ficar todas presentes para o ministro avaliar.
          "embargos_resumo": "..." | null,          // se houver Embargos de Declaração no ponto
          "embargos_transcricao": ["..."] | null,   // ARRAY de parágrafos do CAPÍTULO INTEIRO dos EDs sobre o tema (do relatório dos embargos até a decisão deles); null se não houver EDs no ponto.
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
7. ALINHAMENTO 1:1 COM O DESPACHO (REGRA RÍGIDA):
   - Cada recurso/parte do dossiê deve corresponder a um recurso/parte do blueprint do despacho.
   - Para cada recurso do blueprint, o dossiê deve produzir EXATAMENTE UM tema por tema listado no blueprint, na MESMA ORDEM. NÃO subdivida um tema do despacho em vários temas do dossiê, mesmo que as peças tragam várias sub-questões dentro daquele guarda-chuva. Agrupe TODAS as sub-questões sob o nome do tema correspondente do blueprint, dentro de `fundamentos_argumentativos` e `analise_juridica`.
   - O `nome` do tema é a formatação canônica em CAIXA ALTA do tema do blueprint (ex.: blueprint "Horas extras - divisor" → dossiê "HORAS EXTRAS - DIVISOR"). NÃO crie qualificadores que o blueprint não tem.
   - Preencha `blueprint_tema` com o STRING ORIGINAL do blueprint que este tema referencia (idêntico, sem normalização) — serve para rastreabilidade.
   - Se as peças trazem matéria nova ausente do blueprint (raro), inclua o tema mesmo assim, mas marque `blueprint_tema: null` e cite o fato em `observacoes`.
   - Recursos/partes listados no blueprint sem peça correspondente nas peças anexadas: omitir do dossiê.
8. Se a data do acórdão regional não estiver clara, deixe marco_legal_hint=null.
9. `acordao_recorrido_transcricao` e `embargos_transcricao` são ARRAYS DE STRINGS, com UM ITEM POR PARÁGRAFO do trecho fonte. PRESERVE rigorosamente as quebras de parágrafo originais. NUNCA emita um único string longo com tudo concatenado — sempre array, mesmo se for um parágrafo só (`["único parágrafo"]`). A leitura da minuta depende dessa estrutura.
10. TRANSCRIÇÃO INTEGRAL DO CAPÍTULO (REGRA RÍGIDA): para cada tema, a transcrição NÃO pode ser um recorte editorial do trecho "mais relevante". Reproduza LITERAL e INTEGRALMENTE TODO o capítulo do acórdão regional que trata daquela matéria — do relatório das razões recursais (a delimitação do que está sendo discutido), passando pelos fundamentos (premissas fáticas, doutrina, jurisprudência invocada, raciocínio), até a parte final em que se decide a questão (dispositivo daquele capítulo). Idem para os Embargos de Declaração quando houver. Omitir parte do capítulo faz a minuta perder premissas e é um erro grave. Se o capítulo tem 30 parágrafos, devolva os 30. Se tem 3, devolva os 3. Não resuma, não interpole "(...)", não trunque.

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
        conc = r.get("conclusao", "")
        lines.append(f"- {tipo} ({parte}) — {conc}:")
        temas = r.get("temas") or []
        if temas:
            for idx, tema in enumerate(temas, start=1):
                lines.append(f"    {idx}. {tema}")
        else:
            lines.append("    (sem temas listados)")
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


def _split_paragraphs(value: Any) -> list[str] | None:
    """Normaliza transcricoes para lista de parágrafos.

    Aceita string (com `\\n\\n` ou `\\n` separadores), lista ou None.
    Em caso de string, divide em parágrafos preservando conteúdo.
    """
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # divide em parágrafos (1+ quebras de linha)
        paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
        return paragraphs or None
    return None


def _normalize_transcricoes(dossie: dict[str, Any]) -> dict[str, Any]:
    """Garante que campos de transcrição sejam listas de parágrafos."""
    for recurso in dossie.get("recursos") or []:
        for tema in recurso.get("temas") or []:
            for field in ("acordao_recorrido_transcricao", "embargos_transcricao"):
                normalized = _split_paragraphs(tema.get(field))
                tema[field] = normalized
    return dossie


def _blueprint_recurso_label(recurso: dict[str, Any]) -> str:
    tipo = TIPO_LABEL.get(recurso.get("tipo", ""), recurso.get("tipo", "") or "?")
    parte = PARTE_LABEL.get(recurso.get("parte", ""), recurso.get("parte", "") or "?")
    return f"{tipo} ({parte})"


def _validate_blueprint_alignment(
    dossie: dict[str, Any], blueprint: dict[str, Any] | None
) -> list[str]:
    """Devolve avisos quando o dossiê não respeita o 1:1 de temas do despacho."""
    if not blueprint or not blueprint.get("recursos"):
        return []
    blueprint_by_key: dict[tuple[str, str], list[str]] = {}
    for r in blueprint["recursos"]:
        key = (str(r.get("tipo", "")).lower(), str(r.get("parte", "")).lower())
        blueprint_by_key[key] = [str(t) for t in (r.get("temas") or [])]
    warnings: list[str] = []
    for recurso in dossie.get("recursos") or []:
        key = (str(recurso.get("tipo", "")).lower(), str(recurso.get("parte", "")).lower())
        blueprint_temas = blueprint_by_key.get(key)
        if blueprint_temas is None:
            continue
        temas = recurso.get("temas") or []
        label = _blueprint_recurso_label(recurso)
        if len(temas) > len(blueprint_temas):
            warnings.append(
                f"{label}: dossiê produziu {len(temas)} temas; despacho lista {len(blueprint_temas)} — possível subdivisão indevida."
            )
        blueprint_set = {t.strip().lower() for t in blueprint_temas if t.strip()}
        for tema in temas:
            ref = tema.get("blueprint_tema")
            if ref is None:
                continue
            if str(ref).strip().lower() not in blueprint_set:
                warnings.append(
                    f"{label}: tema '{tema.get('nome', '?')}' referencia blueprint_tema='{ref}' que não consta do despacho."
                )
    return warnings


def _append_observacoes(dossie: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    if not warnings:
        return dossie
    prefix = "Alinhamento com o despacho: " + " | ".join(warnings)
    existing = dossie.get("observacoes")
    if isinstance(existing, str) and existing.strip():
        dossie["observacoes"] = f"{prefix}\n\n{existing}"
    else:
        dossie["observacoes"] = prefix
    return dossie


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
    normalized = _normalize_transcricoes(parsed)
    warnings = _validate_blueprint_alignment(normalized, blueprint)
    return _append_observacoes(normalized, warnings)
