"""Anonimização determinística baseada nas partes cadastradas pelo usuário.

Substitui o anonimizador LLM antigo (``anonymizer_llm``): em vez de pedir pro
Gemini detectar PII, o usuário cadastra nome+aliases das partes no momento do
cadastro do processo e a substituição é feita por regex word-boundary,
case/accent-insensitive.

Mantém a anonimização regex base (CPF/CNPJ/OAB/email/telefone) do módulo
``hermes_api.anonymizer``.

Tokens canônicos: ``RECLAMANTE_1``, ``RECLAMADA_2`` etc. (sem ``<>`` pra
parecer natural no texto entregue ao LLM). Ministério Público é ignorado
(função processual irrelevante para anonimização).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from ..anonymizer import AnonymizationResult
from ..anonymizer import anonymize as regex_anonymize

VALID_ROLES = {"reclamante", "reclamada", "ministerio_publico"}
ROLE_TOKEN = {
    "reclamante": "RECLAMANTE",
    "reclamada": "RECLAMADA",
}


def _normalize_party(party: dict[str, Any]) -> dict[str, Any] | None:
    role = str(party.get("role", "")).strip().lower()
    if role not in VALID_ROLES:
        return None
    name = str(party.get("name", "")).strip()
    raw_aliases = party.get("aliases") or []
    aliases: list[str] = []
    if isinstance(raw_aliases, list):
        aliases = [str(a).strip() for a in raw_aliases if str(a).strip()]
    elif isinstance(raw_aliases, str):
        aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]
    ordinal = party.get("ordinal")
    try:
        ordinal_int = int(ordinal) if ordinal is not None else 1
    except (TypeError, ValueError):
        ordinal_int = 1
    return {
        "role": role,
        "ordinal": ordinal_int,
        "name": name,
        "aliases": aliases,
    }


def _strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _patterns_for(party: dict[str, Any]) -> list[re.Pattern[str]]:
    """Gera regexes para o nome e cada alias da parte.

    Word-boundary, case-insensitive. Para tolerar acentos divergentes
    (texto sem acento vs cadastro com acento), normaliza ambos e usa
    a string normalizada pra montar o padrão; o ``re.IGNORECASE`` cobre
    caixa.
    """
    candidates = [party["name"]] + party["aliases"]
    patterns: list[re.Pattern[str]] = []
    for cand in candidates:
        cand = cand.strip()
        if not cand:
            continue
        # versão sem acentos (escape) — substituições serão feitas em ambas
        normalized = _strip_accents(cand)
        for variant in {cand, normalized}:
            escaped = re.escape(variant)
            # word boundary nas extremidades
            patterns.append(re.compile(rf"(?<![\wÀ-ÿ]){escaped}(?![\wÀ-ÿ])", re.IGNORECASE))
    return patterns


def anonymize_with_parties(
    text: str,
    parties: list[dict[str, Any]] | None,
) -> AnonymizationResult:
    """Anonimiza ``text`` aplicando regex base + substituição por partes.

    Retorna ``AnonymizationResult`` com texto sanitizado e mapping
    ``{placeholder: original}`` consolidado.
    """
    base = regex_anonymize(text)
    out_text = base.text
    mapping: dict[str, str] = dict(base.mapping)

    if not parties:
        return AnonymizationResult(text=out_text, mapping=mapping)

    normalized: list[dict[str, Any]] = []
    for raw in parties:
        norm = _normalize_party(raw)
        if norm is None:
            continue
        if norm["role"] == "ministerio_publico":
            continue
        if not norm["name"]:
            continue
        normalized.append(norm)

    # Ordena por (role, ordinal) pra placeholder estável
    normalized.sort(key=lambda p: (p["role"], p["ordinal"]))

    for party in normalized:
        token_base = ROLE_TOKEN[party["role"]]
        placeholder = f"{token_base}_{party['ordinal']}"
        for pattern in _patterns_for(party):
            if pattern.search(out_text):
                out_text = pattern.sub(placeholder, out_text)
                mapping.setdefault(placeholder, party["name"])

    return AnonymizationResult(text=out_text, mapping=mapping)


def neutralize_party_placeholders(text: str) -> str:
    """Substitui placeholders ``RECLAMANTE_N`` por forma neutra de prosa.

    Usado como defensiva quando o LLM vaza placeholder em texto corrido
    (``[[CORPO]]``). Em ``[[TRANSCRICAO*]]``, prefira deanonymize literal.
    """
    def replace_reclamante(match: re.Match[str]) -> str:
        ordinal = int(match.group(1))
        if ordinal <= 1:
            return "a parte Reclamante"
        return f"a {_ordinal_pt(ordinal)} parte Reclamante"

    def replace_reclamada(match: re.Match[str]) -> str:
        ordinal = int(match.group(1))
        if ordinal <= 1:
            return "a parte Reclamada"
        return f"a {_ordinal_pt(ordinal)} parte Reclamada"

    out = re.sub(r"\bRECLAMANTE_(\d+)\b", replace_reclamante, text)
    out = re.sub(r"\bRECLAMADA_(\d+)\b", replace_reclamada, out)
    return out


_ORDINAIS = {
    2: "segunda",
    3: "terceira",
    4: "quarta",
    5: "quinta",
    6: "sexta",
    7: "sétima",
    8: "oitava",
    9: "nona",
    10: "décima",
}


def _ordinal_pt(n: int) -> str:
    return _ORDINAIS.get(n, f"{n}ª")


_TRANSCRICAO_MARKERS = ("[[TRANSCRICAO1]]", "[[TRANSCRICAO2]]", "[[TRANSCRICAO3]]")
_BODY_MARKERS = (
    "[[CORPO]]",
    "[[EMENTA]]",
    "[[NOTA]]",
    "[[ALERTA_VERMELHO]]",
)


def postprocess_minuta(text: str, anonymization_map: dict[str, str] | None) -> str:
    """Pós-processa a minuta antes da renderização DOCX.

    Para cada bloco entre marcadores:
    - ``[[TRANSCRICAO*]]``: deanonimiza placeholders (restaura nomes
      originais e PII regex), preservando a literalidade do trecho.
    - ``[[CORPO]]`` e demais blocos de prosa: neutraliza placeholders
      de partes que tenham escapado pra "a parte Reclamante/Reclamada".

    O mapping pode ser ``None`` ou vazio — nesse caso só a neutralização
    de placeholders de partes em CORPO acontece.
    """
    from ..anonymizer import deanonymize

    lines = text.splitlines()
    current_marker = "[[CORPO]]"
    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip().upper()
        if stripped in _TRANSCRICAO_MARKERS:
            current_marker = stripped
            out_lines.append(line)
            continue
        if stripped in _BODY_MARKERS:
            current_marker = stripped
            out_lines.append(line)
            continue
        if current_marker in _TRANSCRICAO_MARKERS:
            processed = deanonymize(line, anonymization_map or {})
        else:
            processed = neutralize_party_placeholders(line)
        out_lines.append(processed)
    return "\n".join(out_lines)


__all__ = [
    "VALID_ROLES",
    "anonymize_with_parties",
    "neutralize_party_placeholders",
    "postprocess_minuta",
]
