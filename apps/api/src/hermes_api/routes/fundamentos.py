import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user_id, require_manager
from ..db import get_db
from ..models.fundamento import Fundamento
from ..schemas.fundamento import FundamentoCreate, FundamentoRead, FundamentoUpdate

router = APIRouter(prefix="/fundamentos", tags=["fundamentos"])


@router.post("/bulk", response_model=list[FundamentoRead])
async def bulk_create_fundamentos(
    payload: list[FundamentoCreate],
    user_id: str = Depends(current_user_id),
    _: str = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
) -> list[Fundamento]:
    """Salva em lote uma seleção de fundamentações extraídas via
    ``/cases/{id}/extract-fundamentos``."""
    created: list[Fundamento] = []
    for item in payload:
        tema = " ".join(item.tema.upper().split())
        f = Fundamento(
            user_id=user_id,
            tema=tema,
            titulo=item.titulo,
            corpo_md=item.corpo_md,
            tags=item.tags,
            resumo=item.resumo,
            conclusao_provimento=item.conclusao_provimento,
            conclusao_nao_conhecimento=item.conclusao_nao_conhecimento,
            source_case_id=item.source_case_id,
        )
        db.add(f)
        created.append(f)
    if created:
        await db.commit()
        for f in created:
            await db.refresh(f)
    return created


@router.get("", response_model=list[FundamentoRead])
async def list_fundamentos(
    q: str | None = Query(default=None),
    tema: str | None = Query(default=None),
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[Fundamento]:
    stmt = select(Fundamento).where(Fundamento.user_id == user_id)
    if tema:
        stmt = stmt.where(Fundamento.tema.ilike(f"%{tema.strip()}%"))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Fundamento.titulo.ilike(like),
                Fundamento.resumo.ilike(like),
                Fundamento.tema.ilike(like),
            )
        )
    stmt = stmt.order_by(Fundamento.created_at.desc()).limit(200)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{fundamento_id}", response_model=FundamentoRead)
async def get_fundamento(
    fundamento_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Fundamento:
    f = await db.get(Fundamento, fundamento_id)
    if f is None or f.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return f


@router.put("/{fundamento_id}", response_model=FundamentoRead)
async def update_fundamento(
    fundamento_id: uuid.UUID,
    payload: FundamentoUpdate,
    user_id: str = Depends(current_user_id),
    _: str = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
) -> Fundamento:
    f = await db.get(Fundamento, fundamento_id)
    if f is None or f.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = payload.model_dump(exclude_none=True)
    if "tema" in data:
        f.tema = " ".join(data["tema"].upper().split())
    if "titulo" in data:
        f.titulo = data["titulo"]
    if "corpo_md" in data:
        f.corpo_md = data["corpo_md"]
    if "tags" in data:
        f.tags = data["tags"]
    if "resumo" in data:
        f.resumo = data["resumo"]
    if "conclusao_provimento" in data:
        f.conclusao_provimento = data["conclusao_provimento"]
    if "conclusao_nao_conhecimento" in data:
        f.conclusao_nao_conhecimento = data["conclusao_nao_conhecimento"]
    await db.commit()
    await db.refresh(f)
    return f


@router.delete("/{fundamento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fundamento(
    fundamento_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    _: str = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    f = await db.get(Fundamento, fundamento_id)
    if f is None or f.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await db.delete(f)
    await db.commit()
