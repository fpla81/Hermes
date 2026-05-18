"""Match dos temas do dossiê × tabela de Repetitivos do TST (two-stage).

Stage 1 — triagem: para cada tema do dossiê, envia tabela completa
(formato compacto) ao LLM e recolhe até 5 candidatos com confidence ≥ 0.6.
Critérios duros + exemplos negativos no prompt pra reduzir falso positivo
de cara.

Stage 2 — verificação crítica: pra cada tema (batch dos candidatos), novo
prompt confronta o tema do caso (com acórdão recorrido) com a descrição
COMPLETA + tese firmada de cada candidato. LLM devolve confirmado=true/false
+ razão. Só os confirmados viram match final no dossiê.

Resultado: campo ``repetitivos_matches`` por tema, sempre com ``kind="alta"``
(nível "media" foi descontinuado — falso positivo demais).
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

# Confidence mínimo pra um candidato sair do stage 1.
STAGE1_MIN_CONFIDENCE = 0.6
# Stage 2 só aceita confirmado=true; confidence_final volta como métrica
# informativa (não-bloqueante a partir deste ponto).
STAGE2_MIN_CONFIDENCE = 0.7

# Prefixo ESTÁTICO do stage 1 — instruções fixas + tabela. Este bloco é
# o alvo do Gemini Context Cache (~50KB de tabela). Importante: NADA
# variável por request aqui (qualquer mudança invalida o cache).
_STAGE1_STATIC = """Você é um assistente jurídico do TST. Sua tarefa: para
um tema extraído da análise de um caso concreto, identificar aderência a
algum tema da tabela oficial de Recursos de Revista Repetitivos do TST.

CRITÉRIOS DE ADERÊNCIA (regra rígida — todos devem ser satisfeitos):

1. **Mesma matéria jurídica nuclear.** Não basta toque tangencial nem
   compartilhar área (trabalhista, processual). Tem que ser a mesma
   controvérsia jurídica de fundo.
2. **Mesmo conflito de tese.** Não basta "ambos falam de horas extras".
   Tem que ser o mesmo ponto controvertido (ex.: divisor aplicável ao
   bancário com jornada 6h — não vale pra "incidência de horas extras
   sobre adicional noturno").
3. **Mesmo dispositivo legal / súmula em disputa**, quando o repetitivo
   gira em torno de um dispositivo específico.

EXEMPLOS NEGATIVOS (estes NÃO são aderência — não inclua):

- Caso discute "intervalo intrajornada do art. 71 da CLT" e Tema NNN
  trata de "intervalo interjornada do art. 66 da CLT". Mesma área, mesmo
  diploma, mas conflitos distintos.
- Caso invoca "Súmula 85 do TST" sobre compensação de jornada, e Tema
  NNN também invoca a Súmula 85, mas pra discutir banco de horas em
  norma coletiva. Mesmo permissivo, conflito distinto.
- Caso é "preliminar de nulidade por negativa de prestação jurisdicional"
  e Tema NNN trata de mérito de horas extras. Sem ligação meritória.

DIRETRIZ DE CALIBRAÇÃO: **prefira FALSO NEGATIVO a FALSO POSITIVO.** Em
dúvida razoável, NÃO inclua. Vai existir uma segunda etapa de verificação
crítica; aqui você está fazendo triagem.

TABELA DE REPETITIVOS (uma linha por tema, formato `Tema NNN [situacao]
descrição curta`):

{tabela}
"""


# Sufixo DINÂMICO do stage 1 — varia por request. Não cacheável.
_STAGE1_DYNAMIC = """TEMA DO CASO:
- nome: {nome}
- fundamentos argumentativos: {fundamentos}
- permissivos invocados: {permissivos}

Responda APENAS com JSON puro, sem ``` e sem texto adicional:

{
  "matches": [
    {"numero": 42, "confidence": 0.85, "justificativa": "..."}
  ]
}

Regras formais:
- "confidence" entre 0 e 1. Use ≥ 0.6 apenas pra aderência que satisfaça
  os 3 critérios acima. Abaixo de 0.6, NÃO inclua.
- "justificativa" curta (≤ 200 chars), apontando o ponto de aderência.
- Se nenhum repetitivo aderir, devolva ``{"matches": []}``.
- Ordene por confidence decrescente.
- Inclua no MÁXIMO 5 matches (preferindo qualidade a quantidade).
"""


_STAGE2_PROMPT = """Você é um assistente jurídico do TST. Vai fazer a
**verificação crítica** de candidatos a aderência entre o tema do caso
abaixo e a lista de Temas de Recursos de Revista Repetitivos pré-selecionados
por uma primeira triagem.

Sua tarefa: para CADA candidato, decidir se realmente há aderência (mesma
matéria nuclear + mesmo conflito de tese), olhando agora a descrição
**completa** do repetitivo e a tese firmada quando houver.

TEMA DO CASO:
- nome: {nome}
- fundamentos argumentativos: {fundamentos}
- permissivos invocados: {permissivos}
- acórdão recorrido (resumo): {acordao_resumo}

CANDIDATOS A VERIFICAR:

{candidatos_block}

REGRA: confirmado=true APENAS se a mesma matéria nuclear E o mesmo
conflito de tese. Diferença de conflito (ex.: ambos falam de horas
extras, mas um discute divisor e o outro adicional noturno) = false.
Diferença de matéria (intervalo intrajornada vs interjornada) = false.
Em dúvida razoável, retorne false. Prefira FALSO NEGATIVO.

Responda APENAS com JSON puro, sem ``` e sem texto adicional:

{
  "verificacoes": [
    {
      "numero": 42,
      "confirmado": true,
      "razao": "...",
      "confidence_final": 0.9
    }
  ]
}

Regras formais:
- Devolva UMA entrada por candidato (mesmos ``numero`` recebidos).
- "razao" curta (≤ 200 chars).
- "confidence_final" 0..1, refletindo o grau de aderência depois da
  verificação. Ignorada se confirmado=false.
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
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


def _format_candidatos(
    candidatos: list[dict[str, Any]],
    by_numero: dict[int, TemaRepetitivo],
) -> str:
    parts: list[str] = []
    for c in candidatos:
        numero = int(c["numero"])
        ref = by_numero.get(numero)
        if not ref:
            continue
        desc = (ref.descricao or "").strip()
        tese = (ref.tese or "").strip()
        parts.append(f"### Tema {numero} [{ref.situacao}]")
        parts.append(f"**Descrição completa:**\n{desc}")
        if tese:
            parts.append(f"**Tese firmada:**\n{tese}")
        primeira = c.get("justificativa")
        if primeira:
            parts.append(f"_(triagem: {primeira})_")
        parts.append("")
    return "\n".join(parts).strip()


def _stage1_triagem(
    tema: dict[str, Any],
    tabela_formatted: str,
) -> list[dict[str, Any]]:
    """Devolve até 5 candidatos com confidence ≥ STAGE1_MIN_CONFIDENCE."""
    provider = get_llm_provider()
    if isinstance(provider, StubProvider):
        return []

    fundamentos = " | ".join(tema.get("fundamentos_argumentativos") or [])[:1500]
    permissivos = " | ".join(tema.get("permissivos_invocados") or [])[:1500]
    nome = str(tema.get("nome", "")).strip() or "(sem nome)"

    static_prefix = _STAGE1_STATIC.replace("{tabela}", tabela_formatted)
    dynamic = (
        _STAGE1_DYNAMIC.replace("{nome}", nome)
        .replace("{fundamentos}", fundamentos or "(nenhum)")
        .replace("{permissivos}", permissivos or "(nenhum)")
    )
    try:
        if hasattr(provider, "analyze_cached"):
            raw = provider.analyze_cached(static_prefix, dynamic)
        else:
            raw = provider.analyze(static_prefix + "\n\n" + dynamic)
    except Exception as exc:  # noqa: BLE001
        log.warning("repetitivos_match stage1 LLM falhou: %s", exc)
        return []

    parsed = _extract_json(raw)
    if not parsed:
        return []
    candidatos: list[dict[str, Any]] = []
    for m in parsed.get("matches") or []:
        try:
            numero = int(m.get("numero"))
            confidence = float(m.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if confidence < STAGE1_MIN_CONFIDENCE:
            continue
        candidatos.append(
            {
                "numero": numero,
                "confidence": confidence,
                "justificativa": str(m.get("justificativa", "")).strip()[:400] or None,
            }
        )
    candidatos.sort(key=lambda x: x["confidence"], reverse=True)
    return candidatos[:5]


def _stage2_verificar(
    tema: dict[str, Any],
    candidatos: list[dict[str, Any]],
    by_numero: dict[int, TemaRepetitivo],
) -> list[dict[str, Any]]:
    """Confronta cada candidato com a descrição completa + tese e devolve
    a lista de verificações ({numero, confirmado, razao, confidence_final}).
    """
    if not candidatos:
        return []
    provider = get_llm_provider()
    if isinstance(provider, StubProvider):
        return []

    fundamentos = " | ".join(tema.get("fundamentos_argumentativos") or [])[:1500]
    permissivos = " | ".join(tema.get("permissivos_invocados") or [])[:1500]
    nome = str(tema.get("nome", "")).strip() or "(sem nome)"
    acordao = str(tema.get("acordao_recorrido_resumo", "")).strip() or "(não disponível)"
    candidatos_block = _format_candidatos(candidatos, by_numero)

    prompt = (
        _STAGE2_PROMPT.replace("{nome}", nome)
        .replace("{fundamentos}", fundamentos or "(nenhum)")
        .replace("{permissivos}", permissivos or "(nenhum)")
        .replace("{acordao_resumo}", acordao)
        .replace("{candidatos_block}", candidatos_block)
    )
    try:
        raw = provider.analyze(prompt)
    except Exception as exc:  # noqa: BLE001
        log.warning("repetitivos_match stage2 LLM falhou: %s", exc)
        return []

    parsed = _extract_json(raw)
    if not parsed:
        return []

    out: list[dict[str, Any]] = []
    for v in parsed.get("verificacoes") or []:
        try:
            numero = int(v.get("numero"))
        except (TypeError, ValueError):
            continue
        confirmado = bool(v.get("confirmado"))
        razao = str(v.get("razao", "")).strip()[:400] or None
        try:
            conf_final = float(v.get("confidence_final", 0.0))
        except (TypeError, ValueError):
            conf_final = 0.0
        out.append(
            {
                "numero": numero,
                "confirmado": confirmado,
                "razao": razao,
                "confidence_final": conf_final,
            }
        )
    return out


def _match_one_tema(
    tema: dict[str, Any],
    repetitivos: list[TemaRepetitivo],
    tabela_formatted: str,
) -> list[dict[str, Any]]:
    """Pipeline two-stage. Devolve só os candidatos confirmados na verificação."""
    if not repetitivos:
        return []

    candidatos = _stage1_triagem(tema, tabela_formatted)
    if not candidatos:
        log.debug("repetitivos_match: stage1 sem candidatos pro tema %s", tema.get("nome"))
        return []

    by_numero = {r.numero: r for r in repetitivos}
    verificacoes = _stage2_verificar(tema, candidatos, by_numero)
    if not verificacoes:
        log.debug(
            "repetitivos_match: stage2 sem resposta pro tema %s — descartando %d candidatos",
            tema.get("nome"),
            len(candidatos),
        )
        return []

    by_cand = {c["numero"]: c for c in candidatos}
    verif_by_numero = {v["numero"]: v for v in verificacoes}

    out: list[dict[str, Any]] = []
    for numero, v in verif_by_numero.items():
        if not v["confirmado"]:
            log.debug(
                "repetitivos_match: tema %s rejeitou Tema %d na verificação — %s",
                tema.get("nome"),
                numero,
                v.get("razao"),
            )
            continue
        if v["confidence_final"] < STAGE2_MIN_CONFIDENCE:
            log.debug(
                "repetitivos_match: tema %s confirmou Tema %d mas confidence final %.2f abaixo do limiar",
                tema.get("nome"),
                numero,
                v["confidence_final"],
            )
            continue
        ref = by_numero.get(numero)
        if not ref:
            continue
        cand_meta = by_cand.get(numero, {})
        out.append(
            {
                "numero": ref.numero,
                "descricao": ref.descricao,
                "situacao": ref.situacao,
                "tese": ref.tese,
                "confidence": round(v["confidence_final"], 2),
                "kind": "alta",
                "justificativa": cand_meta.get("justificativa"),
                "verificacao_razao": v.get("razao"),
            }
        )

    out.sort(key=lambda x: x["confidence"], reverse=True)
    return out


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
