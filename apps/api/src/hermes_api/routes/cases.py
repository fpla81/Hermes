import uuid

import anyio
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user_id
from ..config import get_settings
from ..db import get_db
from ..models.case import Case, CaseStatus
from ..schemas.case import CaseCreate, CaseRead
from ..storage import get_storage

router = APIRouter(prefix="/cases", tags=["cases"])


def _get_celery():
    """Lazy singleton com broker/backend de Redis das nossas settings."""
    from celery import Celery

    settings = get_settings()
    if not hasattr(_get_celery, "_app"):
        _get_celery._app = Celery(
            "hermes",
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend,
        )
    return _get_celery._app


def _enqueue_capture(case_id: str) -> None:
    _get_celery().send_task("hermes.capture_case", args=[case_id])


def _enqueue_analyze(case_id: str) -> None:
    _get_celery().send_task("hermes.analyze_case", args=[case_id])


@router.get("", response_model=list[CaseRead])
async def list_cases(
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[Case]:
    result = await db.execute(
        select(Case).where(Case.user_id == user_id).order_by(Case.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = Case(
        user_id=user_id,
        numero_processo=payload.numero_processo,
        titulo=payload.titulo,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return case


@router.get("/{case_id}/html")
async def get_case_html(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if case.artifact_key:
        storage = get_storage()
        if storage is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="storage não configurado",
            )
        body = await anyio.to_thread.run_sync(storage.get_bytes, case.artifact_key)
        return Response(content=body, media_type="text/html; charset=utf-8")
    if case.raw_html is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="caso ainda não foi capturado"
        )
    return Response(content=case.raw_html, media_type="text/html; charset=utf-8")


@router.post("/{case_id}/capture", status_code=status.HTTP_202_ACCEPTED)
async def trigger_capture(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if case.status in (CaseStatus.capturing, CaseStatus.analyzing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"caso já está em {case.status}",
        )
    _enqueue_capture(str(case.id))
    return {"status": "enqueued", "case_id": str(case.id)}


@router.post("/{case_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def trigger_analyze(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if case.status in (CaseStatus.capturing, CaseStatus.analyzing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"caso já está em {case.status}",
        )
    if case.raw_html is None and case.artifact_key is None:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="capture primeiro antes de analisar",
        )
    _enqueue_analyze(str(case.id))
    return {"status": "enqueued", "case_id": str(case.id)}


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await db.delete(case)
    await db.commit()
