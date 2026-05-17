"""Match dos temas do dossiê × tabela de Repetitivos do TST.

Depois do ``build_dossie``, este service pergunta ao LLM se cada tema do
caso tem aderência a algum repetitivo cadastrado. Os matches voltam no
dossiê (campo ``repetitivos_matches`` por tema) e o prompt do
``minuta_draft`` surfaceia como ``[[ALERTA_VERDE]]``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session as SyncSession

from ..llm import StubProvider, get_llm_provider
from ..models.tema_repetitivo import TemaRepetitivo

log = logging.getLogger(__name__)

CONF_HIGH = 0.7
CONF_MEDIUM = 0.4

_PROMPT = """Você é um assistente jurídico do TST. Analise se o tema
abaixo, extraído da análise de um caso concreto, tem aderência a algum
dos temas da tabela oficial de Recursos de Revista Repetitivos do TST.

TEMA DO CASO:
- nome: {nome}
- fundamentos argumentativos: {fundamentos}
- permissivos invocados: {permissivos}

TABELA DE REPETITIVOS (uma linha por tema, formato `Tema NNN [situacao]
descrição curta`):

{tabela}

Responda APENAS com JSON puro, sem ``` e sem texto adicional:

{
  "matches": [
    {"numero": 42, "confidence": 0.85, "justificativa": "..."}
  ]
}

Regras:
- "confidence" entre 0 e 1: 0.7+ = aderência clara; 0.4-0.7 = possível
  aderência (mesma matéria, mas com nuances); abaixo de 0.4, não inclua.
- "justificativa" curta (≤ 200 chars), apontando o ponto de aderência.
- Se nenhum repetitivo aderir, devolva ``{"matches": []}``.
- Ordene por confidence decrescente.
- Inclua no máximo 5 matches.
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _classify_kind(confidence: float) -> str | None:
    if confidence >= CONF_HIGH:
        return "alta"
    if confidence >= CONF_MEDIUM:
        return "media"
    return None


def _format_tabela(repetitivos: list[TemaRepetitivo]) -> str:
    parts: list[str] = []
    for r in repetitivos:
        # mantém compacto pro prompt: descrição truncada
        desc = (r.descricao or "").strip().replace("\n", " ")
        if len(desc) > 220:
            desc = desc[:217] + "…"
        parts.append(f"Tema {r.numero} [{r.situacao}] {desc}")
    return "\n".join(parts)


def _match_one_tema(
    tema: dict[str, Any],
    repetitivos: list[TemaRepetitivo],
    tabela_formatted: str,
) -> list[dict[str, Any]]:
    """Roda o LLM uma vez pro tema; devolve lista (vazia se nada bater)."""
    provider = get_llm_provider()
    if isinstance(provider, StubProvider) or not repetitivos:
        return []

    fundamentos = " | ".join(tema.get("fundamentos_argumentativos") or [])[:1500]
    permissivos = " | ".join(tema.get("permissivos_invocados") or [])[:1500]
    nome = str(tema.get("nome", "")).strip() or "(sem nome)"

    prompt = (
        _PROMPT.replace("{nome}", nome)
        .replace("{fundamentos}", fundamentos or "(nenhum)")
        .replace("{permissivos}", permissivos or "(nenhum)")
        .replace("{tabela}", tabela_formatted)
    )

    try:
        raw = provider.analyze(prompt)
    except Exception as exc:  # noqa: BLE001
        log.warning("repetitivos_match LLM call falhou: %s", exc)
        return []

    parsed = _extract_json(raw)
    if not parsed:
        return []
    raw_matches = parsed.get("matches") or []

    out: list[dict[str, Any]] = []
    by_numero = {r.numero: r for r in repetitivos}
    for m in raw_matches:
        try:
            numero = int(m.get("numero"))
        except (TypeError, ValueError):
            continue
        ref = by_numero.get(numero)
        if ref is None:
            continue
        try:
            confidence = float(m.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        kind = _classify_kind(confidence)
        if not kind:
            continue
        justificativa = str(m.get("justificativa", "")).strip()[:400] or None
        out.append(
            {
                "numero": ref.numero,
                "descricao": ref.descricao,
                "situacao": ref.situacao,
                "tese": ref.tese,
                "confidence": round(confidence, 2),
                "kind": kind,
                "justificativa": justificativa,
            }
        )

    # ordena por confidence desc e limita 5
    out.sort(key=lambda x: x["confidence"], reverse=True)
    return out[:5]


def attach_matches_to_dossie(
    db: SyncSession,
    dossie: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Anexa ``repetitivos_matches`` a cada tema do dossiê (in-place).

    Não levanta exceção em caso de falha: erros de LLM ou DB são logados
    e o dossiê volta sem matches (vazio). A análise é o produto principal
    e não pode quebrar por causa deste passo.
    """
    if not dossie:
        return dossie
    try:
        repetitivos = (
            db.query(TemaRepetitivo)
            .order_by(TemaRepetitivo.numero.asc())
            .all()
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("repetitivos_match: erro ao ler tabela: %s", exc)
        return dossie
    if not repetitivos:
        return dossie

    tabela = _format_tabela(repetitivos)

    for recurso in dossie.get("recursos") or []:
        for tema in recurso.get("temas") or []:
            try:
                tema["repetitivos_matches"] = _match_one_tema(
                    tema, repetitivos, tabela
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "repetitivos_match: falha no tema '%s': %s",
                    tema.get("nome"),
                    exc,
                )
                tema["repetitivos_matches"] = []
    return dossie
