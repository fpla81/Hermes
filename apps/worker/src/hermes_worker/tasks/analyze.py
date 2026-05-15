from __future__ import annotations

import uuid
from datetime import UTC, datetime

from hermes_api.anonymizer import anonymize
from hermes_api.db import SyncSessionLocal
from hermes_api.llm import get_llm_provider
from hermes_api.models.case import Case, CaseStatus
from hermes_api.storage import get_storage

from ..celery_app import celery_app


def _load_html(case: Case) -> str | None:
    if case.raw_html is not None:
        return case.raw_html
    if case.artifact_key:
        storage = get_storage()
        if storage is None:
            return None
        return storage.get_bytes(case.artifact_key).decode("utf-8", errors="replace")
    return None


TIPO_LABEL = {
    "acordao_regional": "Acórdão Regional",
    "acordao_embargos_declaracao": "Acórdão de Embargos de Declaração",
    "despacho_admissibilidade": "Despacho de Admissibilidade",
    "recurso_revista": "Recurso de Revista",
    "agravo_instrumento": "Agravo de Instrumento",
    "agravo_interno": "Agravo Interno",
}

PARTE_LABEL = {
    "reclamante": "Reclamante",
    "reclamada": "Reclamada",
    "reclamantes": "Reclamantes",
    "reclamadas": "Reclamadas",
    "ministerio_publico": "Ministério Público",
    "outro": "Outro",
}


def _structured_to_text(pieces: list[dict]) -> str:
    """Concatena structured_pieces em texto rotulado para o LLM."""
    parts: list[str] = []
    for p in pieces:
        tipo = TIPO_LABEL.get(str(p.get("tipo", "")), str(p.get("tipo", "")))
        parte = PARTE_LABEL.get(str(p.get("parte", "")), p.get("parte"))
        data = p.get("data")
        header = f"### {tipo}"
        if parte:
            header += f" — {parte}"
        if data:
            header += f" ({data})"
        parts.append(header)
        parts.append(str(p.get("text", "")))
        parts.append("")
    return "\n".join(parts).strip()


def _load_text(case: Case) -> str | None:
    """Prefere structured_pieces se houver; cai pra HTML capturado."""
    pieces = case.structured_pieces
    if pieces:
        return _structured_to_text(list(pieces))
    return _load_html(case)


@celery_app.task(name="hermes.analyze_case", bind=True, max_retries=0)
def analyze_case(self, case_id: str) -> dict[str, str]:  # noqa: ARG001
    cid = uuid.UUID(case_id)
    with SyncSessionLocal() as session:
        case = session.get(Case, cid)
        if case is None:
            return {"status": "not_found", "case_id": case_id}

        text = _load_text(case)
        if text is None:
            return {"status": "no_input", "case_id": case_id}

        case.status = CaseStatus.analyzing
        case.last_error = None
        session.commit()

        try:
            anon = anonymize(text)
            provider = get_llm_provider()
            result = provider.analyze(anon.text)
            case.analysis_result = result
            case.anonymization_map = anon.mapping
            case.analyzed_at = datetime.now(UTC)
            case.status = CaseStatus.ready
            session.commit()
            return {"status": "ready", "case_id": case_id}
        except Exception as exc:
            case.status = CaseStatus.error
            case.last_error = str(exc)[:500]
            session.commit()
            return {"status": "error", "case_id": case_id, "error": str(exc)}
