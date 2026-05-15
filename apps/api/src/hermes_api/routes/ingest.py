"""Ingest de HTML via bookmarklet.

O usuário clica um bookmarklet enquanto está logado no Bem-te-vi; ele coleta
o HTML da página de Peças e POSTa aqui com ``Authorization: Bearer <token>``.
Sem Playwright, sem Chrome controlado pelo servidor.
"""

from __future__ import annotations

from datetime import UTC, datetime

import anyio
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user_id
from ..db import get_db
from ..models.case import Case, CaseStatus
from ..schemas.case import PROCESSO_RE, CaseRead
from ..services.extract import extract_pieces
from ..services.tokens import make_token, verify_token
from ..storage import get_storage

router = APIRouter(tags=["ingest"])


class IngestPayload(BaseModel):
    numero_processo: str = Field(..., min_length=19, max_length=64)
    html: str = Field(..., min_length=1)
    url: str | None = None
    titulo: str | None = None


class IngestResult(BaseModel):
    case_id: str
    pieces_found: int
    created: bool


class TokenResult(BaseModel):
    token: str


def _normalize_numero(value: str) -> str:
    value = value.strip()
    match = PROCESSO_RE.match(value)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="numero_processo inválido (CNJ)",
        )
    seq, dv, ano, justica, tribunal, origem = match.groups()
    return f"{seq.zfill(7)}-{dv}.{ano}.{justica}.{tribunal}.{origem}"


def _resolve_user(
    authorization: str | None,
    x_hermes_secret: str | None,
    x_hermes_user_id: str | None,
) -> str:
    """Aceita Bearer token (bookmarklet/externo) OU sessão interna web→api."""
    from ..config import get_settings

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1].strip()
        user_id = verify_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token inválido",
            )
        return user_id

    settings = get_settings()
    if (
        settings.internal_secret
        and x_hermes_secret == settings.internal_secret
        and x_hermes_user_id
    ):
        return x_hermes_user_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Bearer token ou sessão interna obrigatório",
    )


@router.get("/me/ingest-token", response_model=TokenResult)
async def get_my_token(user_id: str = Depends(current_user_id)) -> TokenResult:
    return TokenResult(token=make_token(user_id))


@router.post("/cases/ingest", response_model=IngestResult)
async def ingest_case_html(
    payload: IngestPayload,
    authorization: str | None = Header(default=None),
    x_hermes_secret: str | None = Header(default=None),
    x_hermes_user_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    user_id = _resolve_user(authorization, x_hermes_secret, x_hermes_user_id)
    numero = _normalize_numero(payload.numero_processo)

    existing = await db.execute(
        select(Case).where(Case.user_id == user_id, Case.numero_processo == numero)
    )
    case = existing.scalar_one_or_none()
    created = False
    if case is None:
        case = Case(
            user_id=user_id,
            numero_processo=numero,
            titulo=payload.titulo,
        )
        db.add(case)
        created = True

    pieces = extract_pieces(payload.html)

    storage = get_storage()
    if storage is not None:
        key = f"cases/{user_id}/raw-pending-{numero}.html"
        await anyio.to_thread.run_sync(
            storage.put_bytes,
            key,
            payload.html.encode("utf-8"),
            "text/html; charset=utf-8",
        )
        case.artifact_key = key
        case.raw_html = None
    else:
        case.raw_html = payload.html

    if pieces:
        case.pieces_json = pieces
    case.captured_at = datetime.now(UTC)
    case.status = CaseStatus.captured
    case.last_error = None

    await db.commit()
    await db.refresh(case)

    # ajusta o storage key agora que temos o id do caso
    if storage is not None and case.artifact_key:
        new_key = f"cases/{case.id}/raw.html"
        await anyio.to_thread.run_sync(
            storage.put_bytes,
            new_key,
            payload.html.encode("utf-8"),
            "text/html; charset=utf-8",
        )
        case.artifact_key = new_key
        await db.commit()

    return IngestResult(case_id=str(case.id), pieces_found=len(pieces), created=created)


# Re-export para outras rotas que queiram inspecionar o CaseRead pós-ingest
__all__ = ["router", "CaseRead"]
