import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user_id
from ..db import get_db
from ..models.case import Case
from ..schemas.case import CaseCreate, CaseRead

router = APIRouter(prefix="/cases", tags=["cases"])


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
