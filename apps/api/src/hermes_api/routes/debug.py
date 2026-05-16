"""Endpoints utilitários pra debug em dev. Não usar em produção."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import current_user_id
from ..schemas.case import PartyIn
from ..services.parties_anonymizer import anonymize_with_parties

router = APIRouter(prefix="/debug", tags=["debug"])


class AnonymizePreviewIn(BaseModel):
    text: str
    parties: list[PartyIn] | None = None


class AnonymizePreviewOut(BaseModel):
    anonymized: str
    mapping: dict[str, str]
    substitutions: int


@router.post("/anonymize", response_model=AnonymizePreviewOut)
def anonymize_preview(
    payload: AnonymizePreviewIn,
    _: str = Depends(current_user_id),
) -> AnonymizePreviewOut:
    """Roda regex + substituição determinística das partes em texto cru.

    Útil pra auditar o resultado da anonimização antes de mandar pro LLM.
    """
    parties = [p.model_dump() for p in (payload.parties or [])]
    result = anonymize_with_parties(payload.text, parties)
    return AnonymizePreviewOut(
        anonymized=result.text,
        mapping=result.mapping,
        substitutions=len(result.mapping),
    )
