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

from ..llm import StubProvider, get_llm_provider, json_generation_config
from ..models.case import Case
from ..models.fundamento import Fundamento
from ..schemas.fundamento import FundamentoCreate

_EXTRACT_PROMPT = """Você é um assistente jurídico do TST. Recebe a MINUTA final
(em markdown com marcadores ``[[CORPO]]`` / ``[[TRANSCRICAO*]]`` / ``[[EMENTA]]``)
e o DOSSIÊ estruturado da análise. Extrai, por tema, a fundamentação
jurídica do gabinete pronta para reuso em casos análogos.

REGRA CRÍTICA — NÃO RESUMA. Você copia, não interpreta:

1. Para cada tema, localize na minuta o bloco completo dele (do cabeçalho
   "TEMA - ..." até pouco antes do próximo "TEMA - ..." ou do
   "DISPOSITIVO").
2. Dentro desse bloco, identifique onde TERMINA o RELATÓRIO DO RECURSO
   (relatório típico: parágrafo "O Eg. TRT decidiu/deu provimento...",
   bloco [[TRANSCRICAO1]] com trecho do acórdão regional, parágrafo das
   razões da parte recorrente, eventualmente bloco de embargos).
3. ``corpo_md`` = COPIE LITERAL, sem resumir, TUDO que vem após o
   relatório, EXCETO a frase final de conclusão decisória ("Conheço do
   Recurso de Revista e dou-lhe provimento, ...", "Não conheço do
   Recurso de Revista", "Nego provimento ao Agravo de Instrumento", etc).
   Inclua marcadores ``[[CORPO]]``, ``[[TRANSCRICAO*]]``, ``[[EMENTA]]``
   exatamente como aparecem. NUNCA parafrasear; NUNCA omitir parágrafos.
   Se a fundamentação tem 12 parágrafos, copie os 12.
4. Separe a CONCLUSÃO em DUAS hipóteses pré-prontas:
   - ``conclusao_provimento``: a versão "conheço e dou provimento" da
     conclusão decisória, aplicável quando, em caso futuro, o acórdão
     regional CONTRARIAR o entendimento da fundamentação acima. Use o
     dispositivo concreto compatível ("Conheço do Recurso de Revista,
     por contrariedade à Súmula nº ... do TST, e, no mérito, dou-lhe
     provimento para ..."). Pode ser inferida a partir da conclusão
     original da minuta, adaptando se necessário.
   - ``conclusao_nao_conhecimento``: a versão "não conheço" da conclusão,
     aplicável quando o acórdão regional do caso futuro ESTIVER EM
     CONFORMIDADE com o entendimento da fundamentação acima ("Não conheço
     do Recurso de Revista, porque o acórdão regional está em harmonia
     com a iterativa jurisprudência desta Corte / Súmula nº ... do
     TST.").
   Ambas devem ser frases curtas, no presente do indicativo, prontas pra
   colar; podem mencionar [[CORPO]] ao início.
5. ``titulo`` (≤ 80 chars), ``tags`` (3-8 strings) e ``resumo`` (1 frase
   de índice — esse SIM é sintético; NÃO copia o corpo).

Responda APENAS com JSON puro, sem ``` e sem texto adicional:
{
  "fundamentos": [
    {
      "tema": "...",
      "titulo": "...",
      "corpo_md": "...",
      "tags": ["..."],
      "resumo": "...",
      "conclusao_provimento": "...",
      "conclusao_nao_conhecimento": "..."
    }
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
        raw = provider.analyze(
            prompt,
            label="fundamentos",
            generation_config=json_generation_config(),
        )
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
            cp = item.get("conclusao_provimento")
            cp = str(cp).strip() if cp else None
            cn = item.get("conclusao_nao_conhecimento")
            cn = str(cn).strip() if cn else None
            out.append(
                FundamentoCreate(
                    tema=tema,
                    titulo=titulo,
                    corpo_md=corpo,
                    tags=tags,
                    resumo=resumo,
                    conclusao_provimento=cp,
                    conclusao_nao_conhecimento=cn,
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
