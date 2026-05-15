"""Helpers para materializar peças preparadas a partir do S3.

A regra: cada arquivo em ``cases/{case_id}/prepared/`` vira um
``PreparedPiece``. Quando o ``pieces_json`` do caso tem entradas com
``local_path`` igual ao filename, copiamos ``tipo``/``data``/``id`` para a
peça preparada — assim o ``_match_prepared`` dos serviços encontra por id
em vez de heurística por nome.
"""

from __future__ import annotations

import re

from ..storage import S3Storage
from .resource_check import PreparedPiece

PREPARED_PREFIX = "cases/{case_id}/prepared/"


def prepared_prefix(case_id: str) -> str:
    return PREPARED_PREFIX.format(case_id=case_id)


def prepared_key(case_id: str, filename: str) -> str:
    return f"{prepared_prefix(case_id)}{filename}"


def list_prepared_filenames(storage: S3Storage, case_id: str) -> list[str]:
    prefix = prepared_prefix(case_id)
    return sorted(k[len(prefix):] for k in storage.list_keys(prefix) if k != prefix)


def _piece_id_of(piece: dict) -> str | None:
    for key in ("id", "peca_id", "piece_id"):
        value = piece.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    for key in ("html_url", "bin_url", "url"):
        match = re.search(r"/pecas/(\d+)/", str(piece.get(key, "")))
        if match:
            return match.group(1)
    return None


def load_prepared_pieces(
    storage: S3Storage,
    case_id: str,
    pieces_json: list[dict] | None,
) -> list[PreparedPiece]:
    """Baixa todo o conteúdo do prefixo ``prepared/`` e devolve PreparedPieces.

    Faz lookup no ``pieces_json`` por ``local_path`` igual ao filename
    para enriquecer com ``tipo``/``data``/``id`` quando disponível.
    """
    by_filename: dict[str, dict] = {}
    for piece in pieces_json or []:
        local = piece.get("local_path")
        if not local:
            continue
        # local_path pode vir como "prepared/foo.txt" ou só "foo.txt"
        filename = local.rsplit("/", 1)[-1]
        by_filename[filename] = piece

    out: list[PreparedPiece] = []
    for filename in list_prepared_filenames(storage, case_id):
        meta = by_filename.get(filename, {})
        content = storage.get_bytes(prepared_key(case_id, filename))
        out.append(
            PreparedPiece(
                filename=filename,
                content=content,
                tipo=meta.get("tipo"),
                data=meta.get("data"),
                piece_id=_piece_id_of(meta) if meta else None,
            )
        )
    return out
