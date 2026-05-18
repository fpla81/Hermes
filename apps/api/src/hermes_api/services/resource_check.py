"""Validação de texto útil em peças recursais.

Portado de scripts/check_resource_texts.py. Recebe o manifesto e uma lista de
``PreparedPiece`` (bytes em memória) e devolve um dict de auditoria. Sem I/O.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .text_extract import SUPPORTED_SUFFIXES, extract_text

_RESOURCE_TYPES = (
    "recurso de revista",
    "agravo de instrumento",
    "agravo",
    "ag-airr",
    "ag-rr",
)
_BAD_TEXT_MARKERS = (
    "nada a fazer",
    "single sign-on",
    "login único",
    "login unico",
    "serviço de autenticação",
    "servico de autenticacao",
    "central authentication service",
    "não foi possível",
    "nao foi possivel",
    "erro ao carregar",
)


@dataclass
class PreparedPiece:
    """Peça anonimizada já carregada em memória (vinda do S3 ou upload)."""

    filename: str
    content: bytes
    tipo: str | None = None
    data: str | None = None
    piece_id: str | None = None


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _piece_id(piece: dict[str, Any]) -> str | None:
    for key in ("id", "peca_id", "piece_id"):
        value = piece.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    for key in ("html_url", "bin_url", "url"):
        match = re.search(r"/pecas/(\d+)/", str(piece.get(key, "")))
        if match:
            return match.group(1)
    return None


def _is_resource_piece(piece: dict[str, Any]) -> bool:
    text = _norm_text(str(piece.get("tipo", "")))
    return any(kind in text for kind in _RESOURCE_TYPES)


def _resource_pieces(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for key in ("rr_candidates_requires_legal_selection", "later_agravos_candidates"):
        for item in manifest.get(key, []) or []:
            if not isinstance(item, dict) or not _is_resource_piece(item):
                continue
            pid = _piece_id(item) or json.dumps(item, sort_keys=True, ensure_ascii=False)
            if pid in seen:
                continue
            seen.add(pid)
            out.append(item)
    return out


def _match_prepared(piece: dict[str, Any], prepared: list[PreparedPiece]) -> PreparedPiece | None:
    """Casa uma peça do manifesto com um arquivo preparado.

    Estratégias, em ordem:
      1) ``piece_id`` igual ao da peça
      2) sufixo ``_{pid}.<ext>`` no filename
      3) ``tipo`` normalizado contido no filename (match único)
    """
    pid = _piece_id(piece)
    if pid:
        for p in prepared:
            if p.piece_id == pid:
                return p
        for p in prepared:
            stem = p.filename.rsplit(".", 1)[0]
            if stem.endswith(f"_{pid}"):
                return p

    tipo_slug = _norm_text(str(piece.get("tipo", ""))).replace(" ", "-")
    if tipo_slug:
        fuzzy = [
            p for p in prepared
            if _suffix(p.filename) in SUPPORTED_SUFFIXES and tipo_slug in _norm_text(p.filename)
        ]
        if len(fuzzy) == 1:
            return fuzzy[0]
    return None


def _suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def _validate_one(
    piece: dict[str, Any],
    match: PreparedPiece | None,
    min_chars: int,
    min_words: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    if match is None:
        metrics = {"chars": 0, "words": 0, "bad_marker": None, "extraction_error": None, "sample": "", "filename": None}
        reasons.append("arquivo preparado não localizado")
    else:
        extracted = extract_text(match.content, match.filename)
        clean = re.sub(r"\s+", " ", extracted.text).strip()
        bad_marker = next((m for m in _BAD_TEXT_MARKERS if m in _norm_text(clean)), None)
        metrics = {
            "chars": len(clean),
            "words": len(re.findall(r"\w+", clean)),
            "bad_marker": bad_marker,
            "extraction_error": extracted.error,
            "sample": clean[:240],
            "filename": match.filename,
        }
        if metrics["chars"] < min_chars:
            reasons.append(f"texto insuficiente: {metrics['chars']} caracteres, mínimo {min_chars}")
        if metrics["words"] < min_words:
            reasons.append(f"texto insuficiente: {metrics['words']} palavras, mínimo {min_words}")
        if bad_marker:
            reasons.append(f"marcador de erro/SSO encontrado: {bad_marker}")
        if extracted.error:
            reasons.append(str(extracted.error))

    return {
        "tipo": piece.get("tipo"),
        "data": piece.get("data"),
        "id": _piece_id(piece),
        "html_url": piece.get("html_url"),
        "bin_url": piece.get("bin_url"),
        **metrics,
        "has_usable_text": not reasons,
        "reasons": reasons,
    }


def _alert_text(resources: list[dict[str, Any]]) -> str:
    failed = [r for r in resources if not r["has_usable_text"]]
    if not failed:
        return ""
    parts = [
        "ALERTA: não foi possível elaborar o resumo dos recursos, porque há peça recursal "
        "sem texto útil nos arquivos previamente anonimizados."
    ]
    for item in failed:
        label = " - ".join(
            part for part in (str(item.get("tipo") or ""), str(item.get("data") or ""), str(item.get("id") or ""))
            if part
        )
        parts.append(f"{label}: {'; '.join(item['reasons'])}.")
    parts.append(
        "Transcreva o texto integral dos recursos pertinentes para que o resumo "
        "seja reelaborado e inserido na minuta em .docx."
    )
    return " ".join(parts)


def validate_resources(
    manifest: dict[str, Any],
    prepared: list[PreparedPiece],
    *,
    min_chars: int = 400,
    min_words: int = 80,
) -> dict[str, Any]:
    resources = [
        _validate_one(piece, _match_prepared(piece, prepared), min_chars, min_words)
        for piece in _resource_pieces(manifest)
    ]
    status = "ok" if all(r["has_usable_text"] for r in resources) else "fail"
    return {
        "status": status,
        "min_chars": min_chars,
        "min_words": min_words,
        "resources_checked": len(resources),
        "resources_failed": sum(1 for r in resources if not r["has_usable_text"]),
        "resources": resources,
        "alert_text": _alert_text(resources),
    }
