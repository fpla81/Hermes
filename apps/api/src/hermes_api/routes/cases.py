import uuid

import anyio
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user_id, require_manager
from ..config import get_settings
from ..db import get_db
from ..models.case import Case, CaseStatus
from ..models.fundamento import Fundamento
from ..schemas.case import (
    CaseCreate,
    CaseRead,
    MinutaUpload,
    PartiesUpdate,
    PiecesUpload,
    PreparedListing,
    StructuredPiece,
    StructuredPieceIn,
)
from ..services.despacho import parse_despacho
from ..services.fundamentos import (
    extract_from_minuta,
    increment_usage,
    search_for_theme,
)
from ..services.manifest import build_manifest
from ..services.minuta_draft import build_minuta_draft
from ..services.prepared import (
    list_prepared_filenames,
    load_prepared_pieces,
    prepared_key,
)
from ..services.resource_check import validate_resources
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


def _enqueue_packets(case_id: str) -> None:
    _get_celery().send_task("hermes.build_packets", args=[case_id])


def _enqueue_render_docx(case_id: str) -> None:
    _get_celery().send_task("hermes.render_docx", args=[case_id])


async def _get_owned_case(case_id: uuid.UUID, user_id: str, db: AsyncSession) -> Case:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return case


def _require_storage():
    storage = get_storage()
    if storage is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="storage S3 não configurado",
        )
    return storage


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
        parties=[p.model_dump() for p in payload.parties] or None,
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


@router.put("/{case_id}/parties", response_model=CaseRead)
async def update_parties(
    case_id: uuid.UUID,
    payload: PartiesUpdate,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await db.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    case.parties = [p.model_dump() for p in payload.parties] or None
    await db.commit()
    await db.refresh(case)
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
    if case.raw_html is None and case.artifact_key is None and not case.structured_pieces:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="adicione peças (ou capture o HTML) antes de analisar",
        )
    # permite re-trigger mesmo se status==analyzing (task anterior pode ter
    # crashado sem reverter o status). Worker idempotente sobrescreve resultado.
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


# ---------- Fase B: pipeline pós-captura ----------


@router.post("/{case_id}/pieces", response_model=CaseRead)
async def upload_pieces(
    case_id: uuid.UUID,
    payload: PiecesUpload,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await _get_owned_case(case_id, user_id, db)
    case.pieces_json = [p.model_dump(exclude_none=False) for p in payload.pieces]
    if case.status == CaseStatus.draft:
        case.status = CaseStatus.preparing
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/{case_id}/manifest", response_model=CaseRead)
async def build_case_manifest(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await _get_owned_case(case_id, user_id, db)
    if not case.pieces_json:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="envie pieces antes de gerar o manifest",
        )
    case.manifest = build_manifest(
        list(case.pieces_json),
        process_number=case.numero_processo or None,
    )
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/{case_id}/prepared", response_model=PreparedListing)
async def upload_prepared(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PreparedListing:
    case = await _get_owned_case(case_id, user_id, db)
    storage = _require_storage()
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="filename obrigatório")
    body = await file.read()
    key = prepared_key(str(case.id), file.filename)
    await anyio.to_thread.run_sync(
        storage.put_bytes, key, body, file.content_type or "application/octet-stream"
    )
    filenames = await anyio.to_thread.run_sync(list_prepared_filenames, storage, str(case.id))
    return PreparedListing(filenames=filenames)


@router.get("/{case_id}/prepared", response_model=PreparedListing)
async def get_prepared(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PreparedListing:
    case = await _get_owned_case(case_id, user_id, db)
    storage = _require_storage()
    filenames = await anyio.to_thread.run_sync(list_prepared_filenames, storage, str(case.id))
    return PreparedListing(filenames=filenames)


@router.delete("/{case_id}/prepared/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prepared(
    case_id: uuid.UUID,
    filename: str,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    case = await _get_owned_case(case_id, user_id, db)
    storage = _require_storage()
    await anyio.to_thread.run_sync(
        storage.delete_key, prepared_key(str(case.id), filename)
    )


@router.post("/{case_id}/validate-resources", response_model=CaseRead)
async def validate_case_resources(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await _get_owned_case(case_id, user_id, db)
    if not case.manifest:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="gere o manifest antes de validar recursos",
        )
    storage = _require_storage()
    prepared = await anyio.to_thread.run_sync(
        load_prepared_pieces, storage, str(case.id), case.pieces_json
    )
    case.resource_validation = validate_resources(dict(case.manifest), prepared)
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/{case_id}/packets", status_code=status.HTTP_202_ACCEPTED)
async def trigger_packets(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await _get_owned_case(case_id, user_id, db)
    if not case.manifest:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="gere o manifest antes de empacotar",
        )
    if case.status == CaseStatus.packaging:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="já está empacotando")
    case.status = CaseStatus.packaging
    case.last_error = None
    await db.commit()
    _enqueue_packets(str(case.id))
    return {"status": "enqueued", "case_id": str(case.id)}


@router.get("/{case_id}/packets")
async def get_packets(
    case_id: uuid.UUID,
    raw: int = 0,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    case = await _get_owned_case(case_id, user_id, db)
    if raw:
        if not case.packets_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="packets ainda não gerados")
        storage = _require_storage()
        body = await anyio.to_thread.run_sync(storage.get_bytes, case.packets_key)
        return Response(content=body, media_type="application/x-ndjson")
    if not case.packet_index:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="packets ainda não gerados")
    import json as _json

    return Response(
        content=_json.dumps(case.packet_index, ensure_ascii=False),
        media_type="application/json",
    )


@router.post("/{case_id}/minuta-draft")
async def generate_minuta_draft(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Gera um rascunho de minuta a partir do dossiê + peças estruturadas.

    Não salva — devolve o markdown no corpo da resposta para o usuário
    revisar e depois POSTar em /minuta.
    """
    case = await _get_owned_case(case_id, user_id, db)
    pieces = list(case.structured_pieces or [])
    if not pieces:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="adicione peças antes de gerar minuta",
        )
    acordao_data: str | None = None
    if case.despacho_blueprint and isinstance(case.despacho_blueprint, dict):
        acordao_data = case.despacho_blueprint.get("acordao_regional_data")

    # Recupera fundamentos do usuário aderentes a cada tema do dossiê
    # e os passa pro prompt da minuta. Incrementa usage_count.
    fundamentos_por_tema: dict[str, list[dict]] = {}
    used_ids: list[uuid.UUID] = []
    dossie = case.analysis_dossie or {}
    for recurso in dossie.get("recursos") or []:
        for tema in recurso.get("temas") or []:
            tema_nome = str(tema.get("nome", "")).strip()
            if not tema_nome:
                continue
            tags_hint = list(tema.get("permissivos_invocados") or [])[:5]
            matches = await search_for_theme(db, user_id, tema_nome, tags_hint, limit=3)
            if matches:
                fundamentos_por_tema[tema_nome] = [
                    {
                        "titulo": f.titulo,
                        "resumo": f.resumo,
                        "corpo_md": f.corpo_md,
                        "tags": f.tags or [],
                        "conclusao_provimento": f.conclusao_provimento,
                        "conclusao_nao_conhecimento": f.conclusao_nao_conhecimento,
                    }
                    for f in matches
                ]
                used_ids.extend(f.id for f in matches)
    if used_ids:
        await increment_usage(db, used_ids)
        await db.commit()

    draft = build_minuta_draft(
        case.numero_processo,
        pieces,
        case.analysis_dossie,
        acordao_regional_data=acordao_data,
        fundamentos_por_tema=fundamentos_por_tema or None,
    )
    return {"text": draft}


@router.post("/{case_id}/learn-fundamentos")
async def learn_fundamentos(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    _: str = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extrai fundamentações da minuta final e salva no banco do usuário."""
    case = await _get_owned_case(case_id, user_id, db)
    if not case.minuta_md:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="salve a minuta antes de aprender",
        )
    items = extract_from_minuta(case)
    created: list[Fundamento] = []
    for item in items:
        f = Fundamento(
            user_id=user_id,
            tema=item.tema,
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
    return {
        "learned": len(created),
        "fundamentos": [
            {
                "id": str(f.id),
                "tema": f.tema,
                "titulo": f.titulo,
                "resumo": f.resumo,
            }
            for f in created
        ],
    }


@router.post("/{case_id}/minuta", response_model=CaseRead)
async def upload_minuta(
    case_id: uuid.UUID,
    payload: MinutaUpload,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await _get_owned_case(case_id, user_id, db)
    case.minuta_md = payload.text
    await db.commit()
    await db.refresh(case)
    return case


@router.post("/{case_id}/docx", status_code=status.HTTP_202_ACCEPTED)
async def trigger_docx(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    case = await _get_owned_case(case_id, user_id, db)
    if not case.minuta_md:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="envie a minuta antes de gerar o docx",
        )
    if case.status == CaseStatus.rendering:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="já está renderizando")
    case.status = CaseStatus.rendering
    case.last_error = None
    await db.commit()
    _enqueue_render_docx(str(case.id))
    return {"status": "enqueued", "case_id": str(case.id)}


@router.get("/{case_id}/structured-pieces", response_model=list[StructuredPiece])
async def list_structured_pieces(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    case = await _get_owned_case(case_id, user_id, db)
    return case.structured_pieces or []


@router.post("/{case_id}/structured-pieces", response_model=StructuredPiece)
async def add_structured_piece(
    case_id: uuid.UUID,
    payload: StructuredPieceIn,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    case = await _get_owned_case(case_id, user_id, db)
    import uuid as _uuid
    from datetime import UTC, datetime

    piece = payload.model_dump()
    piece["id"] = str(_uuid.uuid4())
    piece["created_at"] = datetime.now(UTC).isoformat()
    piece["blueprint"] = None

    if piece["tipo"] == "despacho_admissibilidade":
        blueprint = parse_despacho(payload.text)
        piece["blueprint"] = blueprint
        case.despacho_blueprint = blueprint

    existing = list(case.structured_pieces or [])
    existing.append(piece)
    case.structured_pieces = existing
    await db.commit()
    return piece


@router.delete("/{case_id}/structured-pieces/{piece_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_structured_piece(
    case_id: uuid.UUID,
    piece_id: str,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    case = await _get_owned_case(case_id, user_id, db)
    existing = list(case.structured_pieces or [])
    remaining = [p for p in existing if p.get("id") != piece_id]
    if len(remaining) == len(existing):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="peça não encontrada")
    case.structured_pieces = remaining
    # se removeu o despacho, limpa o blueprint
    if not any(p.get("tipo") == "despacho_admissibilidade" for p in remaining):
        case.despacho_blueprint = None
    await db.commit()


@router.get("/{case_id}/docx")
async def get_docx(
    case_id: uuid.UUID,
    user_id: str = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    case = await _get_owned_case(case_id, user_id, db)
    if not case.docx_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="docx ainda não gerado")
    storage = _require_storage()
    body = await anyio.to_thread.run_sync(storage.get_bytes, case.docx_key)
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="minuta-{case.id}.docx"',
        },
    )
