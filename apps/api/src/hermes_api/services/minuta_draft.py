"""Gera rascunho de minuta em Markdown estruturado a partir do dossiê.

Saída usa os marcadores ``[[CORPO]]`` / ``[[TRANSCRICAO1]]`` / ``[[EMENTA]]``
esperados por ``services/docx.py``. O usuário ajusta no editor e gera o
DOCX final.

Sem ``GEMINI_API_KEY`` devolve um esqueleto previsível com TODOs.
"""

from __future__ import annotations

from typing import Any

from ..llm import StubProvider, get_llm_provider
from .analysis_themed import PARTE_LABEL, TIPO_LABEL

PROMPT_TEMPLATE = """Você é assistente jurídico do TST. Recebe o dossiê estruturado dos recursos analisados e deve produzir uma minuta de decisão em Markdown puro com os marcadores do padrão TST.

Estrutura obrigatória:

[[CORPO]]
PROCESSO Nº {numero}

Trata-se de {breve descrição}.

[[CORPO]]
RECURSO DE REVISTA DA RECLAMADA

TEMA - {NOME DO TEMA EM CAIXA ALTA}

Resumo dos fundamentos argumentativos e permissivos invocados pela parte.

[[TRANSCRICAO1]]
(opcional) trecho do acórdão regional relevante.

[[CORPO]]
Análise da admissibilidade e mérito, com conclusão.

Regras:
- Repita os blocos [[CORPO]]/[[TRANSCRICAO1]] conforme a estrutura.
- Para cada recurso e cada tema do dossiê, produza um bloco temático.
- Use linguagem formal de minuta TST. Conheça/Não conheço, Dou/Nego provimento.
- Não use texto fora dos marcadores.

Dossiê:
{dossie}
"""


def _stub_minuta(numero: str, pieces: list[dict[str, Any]]) -> str:
    chunks = ["[[CORPO]]", f"PROCESSO Nº {numero}", ""]
    chunks.append(
        "Trata-se de TODO (configurar GEMINI_API_KEY para gerar o rascunho real)."
    )
    for p in pieces:
        tipo = TIPO_LABEL.get(p.get("tipo", ""), p.get("tipo", ""))
        parte = PARTE_LABEL.get(p.get("parte", ""), p.get("parte"))
        header = f"{tipo}"
        if parte:
            header += f" — {parte}"
        chunks.append("")
        chunks.append("[[CORPO]]")
        chunks.append(header.upper())
        chunks.append("")
        chunks.append("TODO: análise.")
    return "\n".join(chunks)


def build_minuta_draft(
    numero_processo: str,
    pieces: list[dict[str, Any]],
    dossie: dict[str, Any] | None,
) -> str:
    provider = get_llm_provider()
    if isinstance(provider, StubProvider) or not dossie or not dossie.get("recursos"):
        return _stub_minuta(numero_processo, pieces)
    import json as _json

    prompt = PROMPT_TEMPLATE.replace(
        "{dossie}", _json.dumps(dossie, ensure_ascii=False, indent=2)
    ).replace("{numero}", numero_processo)
    try:
        return provider.analyze(prompt).strip()
    except Exception as exc:  # noqa: BLE001
        return f"[[CORPO]]\nTODO: falha ao gerar minuta ({exc}).\n"
