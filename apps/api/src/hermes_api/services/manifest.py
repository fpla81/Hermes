"""Construção do manifesto do caso (despacho-âncora, candidatos RR, agravos posteriores).

Portado de scripts/build_case_manifest.py. Não toca filesystem: recebe a lista
de peças (dicts) e devolve o manifest como dict.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

_PROCESS_RE = re.compile(r"\d{1,7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


def parse_br_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _norm(value: str | None) -> str:
    return _strip_accents(value or "").casefold()


def normalize_process_number(value: str) -> str:
    match = _PROCESS_RE.search(value)
    if not match:
        raise ValueError(f"Could not find a process number in: {value}")
    number = match.group(0)
    prefix, rest = number.split("-", 1)
    return f"{prefix.zfill(7)}-{rest}"


def slugify(value: str) -> str:
    value = _strip_accents(value).casefold()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "textos-fornecidos"


def _piece_text(piece: dict[str, Any]) -> str:
    keys = ("tipo", "html_url", "bin_url", "url", "local_path", "prepared_path", "file", "path", "filename")
    return " ".join(str(piece.get(key, "")) for key in keys)


def _is_dispatch(piece: dict[str, Any]) -> bool:
    normalized = _norm(_piece_text(piece))
    return (
        "despacho de admissibilidade" in normalized
        or "decisoes-admissao" in normalized
        or "admissibilidade trt" in normalized
    )


def _is_rr(piece: dict[str, Any]) -> bool:
    text = _norm(str(piece.get("tipo", "")))
    full_text = _norm(_piece_text(piece))
    if "agravo" in text or "contrarrazoes" in text or "contraminuta" in text:
        return False
    return "recurso de revista" in text or "recurso-de-revista" in full_text or "peticoesrr" in full_text


def _is_later_agravo(piece: dict[str, Any], dispatch_date: date | None) -> bool:
    text = _norm(str(piece.get("tipo", "")))
    full_text = _norm(_piece_text(piece))
    agravo = (
        "agravo de instrumento" in text
        or text.startswith("agravo")
        or "ag-airr" in text
        or "ag-rr" in text
        or "agravo-de-instrumento" in full_text
        or "agravos-tst" in full_text
    )
    if not agravo:
        return False
    piece_date = parse_br_date(str(piece.get("data", "")))
    return dispatch_date is None or piece_date is None or piece_date > dispatch_date


def _enrich_piece(piece: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(piece)
    parsed = parse_br_date(str(piece.get("data", "")))
    enriched["date_iso"] = parsed.isoformat() if parsed else None
    return enriched


def build_manifest(
    pieces: list[dict[str, Any]],
    *,
    process_number: str | None = None,
    case_slug: str | None = None,
) -> dict[str, Any]:
    """Monta o manifesto.

    ``pieces`` é a lista de objetos extraídos da tabela ``Peças`` do Bem-te-vi
    (`tipo`, `data`, `html_url`, `bin_url`, etc.) ou fornecidos manualmente no
    modo "textos fornecidos".
    """
    normalized_number = normalize_process_number(process_number) if process_number else None
    slug = normalized_number or slugify(case_slug or "textos-fornecidos")

    enriched = [_enrich_piece(p) for p in pieces]

    dispatch_candidates = [p for p in enriched if _is_dispatch(p)]
    dispatch_candidates.sort(
        key=lambda item: parse_br_date(str(item.get("data", ""))) or date.min,
        reverse=True,
    )
    anchor = dispatch_candidates[0] if dispatch_candidates else None
    anchor_date = parse_br_date(str(anchor.get("data", ""))) if anchor else None

    rr_candidates = [p for p in enriched if _is_rr(p)]
    later_agravos = [p for p in enriched if _is_later_agravo(p, anchor_date)]

    return {
        "process_number": normalized_number,
        "case_slug": slug,
        "dispatch_anchor": anchor,
        "dispatch_candidates": dispatch_candidates,
        "rr_candidates_requires_legal_selection": rr_candidates,
        "later_agravos_candidates": later_agravos,
        "selection_rule": (
            "Only RRs semantically referred to in the dispatch anchor are included; "
            "later agravos are candidates if dated after the anchor."
        ),
    }
