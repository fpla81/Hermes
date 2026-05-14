"""Geração de pacotes auditáveis para triagem extrativa.

Portado de scripts/build_analysis_packets.py. Recebe manifesto + peças
preparadas (bytes) e devolve ``(packets, index)`` como structs simples.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .resource_check import PreparedPiece
from .text_extract import SUPPORTED_SUFFIXES, extract_text

_RESOURCE_KEYS = (
    "dispatch_anchor",
    "dispatch_candidates",
    "rr_candidates_requires_legal_selection",
    "later_agravos_candidates",
)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _piece_id(piece: dict[str, Any]) -> str | None:
    for key in ("id", "peca_id", "piece_id"):
        value = piece.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    for key in ("html_url", "bin_url", "url"):
        m = re.search(r"/pecas/(\d+)/", str(piece.get(key, "")))
        if m:
            return m.group(1)
    return None


def _role_for_piece(piece: dict[str, Any]) -> str:
    text = _norm(" ".join(str(piece.get(k, "")) for k in ("tipo", "local_path", "prepared_path", "file", "path", "filename")))
    if "despacho de admissibilidade" in text or "admissibilidade" in text:
        return "dispatch"
    if "recurso de revista" in text:
        return "recurso_de_revista"
    if "agravo" in text:
        return "agravo"
    if "acordao" in text or "acórdão" in text:
        return "acordao"
    if "embargos" in text:
        return "embargos_declaracao"
    return "apoio"


def _manifest_pieces(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    pieces: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for key in _RESOURCE_KEYS:
        value = manifest.get(key)
        items = [value] if isinstance(value, dict) else (value if isinstance(value, list) else [])
        for item in items:
            if not isinstance(item, dict):
                continue
            uniq = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if uniq in seen_keys:
                continue
            seen_keys.add(uniq)
            pieces.append(item)
    return pieces


def _match_prepared(piece: dict[str, Any], prepared: list[PreparedPiece]) -> PreparedPiece | None:
    pid = _piece_id(piece)
    if pid:
        for p in prepared:
            if p.piece_id == pid:
                return p
        for p in prepared:
            stem = p.filename.rsplit(".", 1)[0]
            if stem.endswith(f"_{pid}"):
                return p
    tipo_slug = _norm(str(piece.get("tipo", ""))).replace(" ", "-")
    if tipo_slug:
        fuzzy = [
            p for p in prepared
            if _suffix(p.filename) in SUPPORTED_SUFFIXES and tipo_slug in _norm(p.filename)
        ]
        if len(fuzzy) == 1:
            return fuzzy[0]
    return None


def _suffix(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def _split_text(text: str, max_chars: int, overlap_chars: int) -> list[dict[str, Any]]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    effective_overlap = min(max(overlap_chars, 0), max_chars // 4)
    if len(text) <= max_chars:
        return [{"index": 1, "start": 0, "end": len(text), "text": text}]

    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(text):
        limit = min(start + max_chars, len(text))
        end = limit
        if limit < len(text):
            paragraph_break = text.rfind("\n\n", start, limit)
            sentence_break = max(text.rfind(". ", start, limit), text.rfind("; ", start, limit))
            candidate = paragraph_break if paragraph_break > start + max_chars // 2 else sentence_break
            if candidate > start + max_chars // 2:
                end = candidate + 1
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({"index": len(chunks) + 1, "start": start, "end": end, "text": chunk_text})
        if end >= len(text):
            break
        next_start = max(0, end - effective_overlap)
        start = next_start if next_start > start else end
    return chunks


def build_packets(
    manifest: dict[str, Any],
    prepared: list[PreparedPiece],
    *,
    max_chars: int = 12000,
    overlap_chars: int = 800,
    include_all_prepared: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Devolve ``(packets, index)``.

    Quando ``include_all_prepared`` é True, peças preparadas que não estão no
    manifesto entram como apoio.
    """
    packets: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    items: list[tuple[dict[str, Any], PreparedPiece]] = []
    used_prepared: set[str] = set()
    for piece in _manifest_pieces(manifest):
        match = _match_prepared(piece, prepared)
        if match is None:
            continue
        if match.filename in used_prepared:
            continue
        used_prepared.add(match.filename)
        items.append((piece, match))

    if include_all_prepared:
        for p in prepared:
            if p.filename in used_prepared:
                continue
            if _suffix(p.filename) not in SUPPORTED_SUFFIXES:
                continue
            used_prepared.add(p.filename)
            items.append(({"tipo": p.tipo or p.filename, "data": p.data, "local_path": p.filename}, p))

    for source_index, (piece, prep) in enumerate(items, start=1):
        extracted = extract_text(prep.content, prep.filename)
        text = extracted.text
        error = extracted.error
        chunks = _split_text(text, max_chars, overlap_chars) if text else []
        source_id = f"S{source_index:03d}"
        sources.append(
            {
                "source_id": source_id,
                "filename": prep.filename,
                "tipo": piece.get("tipo"),
                "data": piece.get("data"),
                "id": _piece_id(piece),
                "role": _role_for_piece(piece),
                "chars": len(text),
                "packet_count": len(chunks),
                "error": error,
            }
        )
        for chunk in chunks:
            packets.append(
                {
                    "packet_id": f"{source_id}-P{chunk['index']:03d}",
                    "source_id": source_id,
                    "filename": prep.filename,
                    "tipo": piece.get("tipo"),
                    "data": piece.get("data"),
                    "id": _piece_id(piece),
                    "role": _role_for_piece(piece),
                    "chunk_index": chunk["index"],
                    "chunk_total": len(chunks),
                    "char_start": chunk["start"],
                    "char_end": chunk["end"],
                    "text": chunk["text"],
                }
            )

    index = {
        "max_chars": max_chars,
        "overlap_chars": overlap_chars,
        "packet_count": len(packets),
        "sources": sources,
        "triage_instruction": (
            "Use each packet for extractive triage only: identify themes, party, resource class, "
            "argumentative grounds, legal permissives, and short evidence quotes with packet_id and offsets. "
            "Do not decide admissibility, case outcome, or foundation adherence in packet triage."
        ),
    }
    return packets, index
