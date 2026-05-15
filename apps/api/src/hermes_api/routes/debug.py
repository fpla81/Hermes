"""Endpoints utilitários pra debug em dev. Não usar em produção."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import current_user_id
from ..services.anonymizer_llm import full_anonymize

router = APIRouter(prefix="/debug", tags=["debug"])


class AnonymizePreviewIn(BaseModel):
    text: str


class AnonymizePreviewOut(BaseModel):
    anonymized: str
    mapping: dict[str, str]
    substitutions: int


@router.post("/anonymize", response_model=AnonymizePreviewOut)
def anonymize_preview(
    payload: AnonymizePreviewIn,
    _: str = Depends(current_user_id),
) -> AnonymizePreviewOut:
    """Roda regex + LLM anonymizer em texto cru e devolve o resultado.

    Útil pra calibrar prompt e ver o que cada passo cobre. Cobra Gemini
    Flash a cada chamada (~R$ 0,02 por kchar grande).
    """
    result = full_anonymize(payload.text)
    real_subs = sum(1 for k in result.mapping if not k.startswith("_"))
    return AnonymizePreviewOut(
        anonymized=result.text,
        mapping=result.mapping,
        substitutions=real_subs,
    )
