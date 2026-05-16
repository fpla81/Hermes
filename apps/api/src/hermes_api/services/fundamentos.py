"""Aprendizado e recuperação de fundamentações jurídicas por tema.

Fluxo:

1. Após o usuário editar e salvar a minuta final, ``extract_from_minuta``
   pede ao LLM para extrair, por tema, ``{titulo, corpo_md, tags, resumo}``
   da fundamentação contida no markdown. Cada item vira uma linha em
   ``fundamentos`` (escopado pelo ``user_id``).

2. Na geração da próxima minuta, ``search_for_theme`` recupera os
   fundamentos mais aderentes a cada tema do dossiê — busca por
   correspondência exata em ``tema``, sobreposição em ``tags`` e
   ILIKE em ``resumo`` / ``titulo``. Os top-N entram no prompt.

Tudo SQL puro; nenhuma dependência de vector store por enquanto.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..llm import StubProvider, get_llm_provider
from ..models.case import Case
from ..models.fundamento import Fundamento
from ..schemas.fundamento import FundamentoCreate

_EXTRACT_PROMPT = """Você é um assistente jurídico do TST. Receba a MINUTA final
(em markdown com marcadores ``[[CORPO]]`` / ``[[TRANSCRICAO*]]`` / ``[[EMENTA]]``)
e o DOSSIÊ estruturado da análise, e extraia, para CADA tema, a
fundamentação jurídica do gabinete pronta para reuso em casos análogos.

Para cada tema do dossiê que apareça na minuta, devolva um objeto JSON com:
- ``tema``: nome canônico do tema, idêntico ao do dossiê (CAIXA ALTA).
- ``titulo``: título curto (≤ 80 chars) descrevendo a tese.
- ``corpo_md``: TRANSCRIÇÃO LITERAL do bloco de análise jurídica do tema
  na minuta (a parte que contém raciocínio + dispositivo do tema).
  Inclua os marcadores ``[[CORPO]]`` quando estiverem ali.
- ``tags``: array de 3 a 8 strings curtas — palavras-chave jurídicas (ex.:
  "horas extras", "divisor", "art 71 CLT", "súmula 437 TST").
- ``resumo``: 1 a 2 frases sintetizando a tese do gabinete sobre o tema,
  no presente do indicativo. Vai pro índice de busca. NÃO copie o corpo.

Responda APENAS com JSON puro, sem ``` e sem texto adicional:
{
  "fundamentos": [
    {"tema": "...", "titulo": "...", "corpo_md": "...", "tags": ["..."], "resumo": "..."}
  ]
}

Se um tema do dossiê NÃO tiver fundamentação na minuta (porque o tema
sumiu ou foi tratado só em transcrição), omita-o silenciosamente.

DOSSIÊ:
{dossie}

MINUTA:
{minuta}
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _normalize_tema(tema: str) -> str:
    return " ".join(tema.upper().split())


def extract_from_minuta(case: Case) -> list[FundamentoCreate]:
    """Pede ao LLM para extrair fundamentações da minuta final do caso.

    Retorna lista vazia se faltar minuta/dossiê ou se o LLM estiver em
    modo stub (sem GEMINI_API_KEY).
    """
    provider = get_llm_provider()
    if isinstance(provider, StubProvider):
        return []
    if not case.minuta_md or not case.analysis_dossie:
        return []
    prompt = (
        _EXTRACT_PROMPT.replace(
            "{dossie}", json.dumps(case.analysis_dossie, ensure_ascii=False, indent=2)
        )
        .replace("{minuta}", case.minuta_md)
    )
    try:
        raw = provider.analyze(prompt)
    except Exception:  # noqa: BLE001
        return []
    parsed = _extract_json(raw)
    if not parsed:
        return []
    items = parsed.get("fundamentos") or []
    out: list[FundamentoCreate] = []
    for item in items:
        try:
            tema = _normalize_tema(str(item.get("tema", "")).strip())
            titulo = str(item.get("titulo", "")).strip()
            corpo = str(item.get("corpo_md", "")).strip()
            if not tema or not titulo or not corpo:
                continue
            tags_raw = item.get("tags") or []
            tags = [str(t).strip() for t in tags_raw if str(t).strip()] if isinstance(tags_raw, list) else []
            resumo = item.get("resumo")
            resumo = str(resumo).strip() if resumo else None
            out.append(
                FundamentoCreate(
                    tema=tema,
                    titulo=titulo,
                    corpo_md=corpo,
                    tags=tags,
                    resumo=resumo,
                    source_case_id=case.id,
                )
            )
        except (TypeError, ValueError):
            continue
    return out


def _strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _score(fund: Fundamento, tema: str, tags_hint: list[str]) -> tuple[int, int, str]:
    """Score heurístico (maior = mais relevante). Tuple para ordenar
    (score, recency_proxy, created_at desc)."""
    tema_norm = _normalize_tema(tema)
    score = 0
    if _normalize_tema(fund.tema) == tema_norm:
        score += 100
    elif tema_norm in _normalize_tema(fund.tema) or _normalize_tema(fund.tema) in tema_norm:
        score += 60
    own_tags = [str(t).lower() for t in (fund.tags or [])]
    for h in tags_hint:
        if h.lower() in own_tags:
            score += 15
    tema_lower = _strip_accents(tema_norm).lower()
    if fund.resumo and tema_lower in _strip_accents(fund.resumo).lower():
        score += 8
    if tema_lower in _strip_accents(fund.titulo).lower():
        score += 5
    return (score, fund.usage_count, fund.created_at.isoformat())


async def search_for_theme(
    db: AsyncSession,
    user_id: str,
    tema: str,
    tags_hint: list[str] | None = None,
    limit: int = 3,
) -> list[Fundamento]:
    """Busca fundamentos do usuário aderentes ao tema dado.

    Primeira passada: SQL filtra candidatos (mesmo user_id; texto bate em
    qualquer um dos campos pesquisáveis ou tema idêntico). Em memória,
    ordena por score heurístico e retorna top-N.
    """
    tema_norm = _normalize_tema(tema)
    like = f"%{tema_norm}%"
    stmt = (
        select(Fundamento)
        .where(Fundamento.user_id == user_id)
        .where(
            or_(
                Fundamento.tema.ilike(like),
                Fundamento.titulo.ilike(like),
                Fundamento.resumo.ilike(like),
            )
        )
        .order_by(Fundamento.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)
    candidates = list(res.scalars().all())
    candidates.sort(key=lambda f: _score(f, tema_norm, tags_hint or []), reverse=True)
    return candidates[:limit]


async def increment_usage(
    db: AsyncSession,
    fundamento_ids: list[Any],
) -> None:
    """Soma 1 em ``usage_count`` para cada ``id`` da lista."""
    if not fundamento_ids:
        return
    stmt = select(Fundamento).where(Fundamento.id.in_(fundamento_ids))
    res = await db.execute(stmt)
    for f in res.scalars().all():
        f.usage_count = (f.usage_count or 0) + 1
    await db.flush()
