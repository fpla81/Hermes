from __future__ import annotations

import uuid

from hermes_api.db import SyncSessionLocal
from hermes_api.models.case import Case, CaseStatus
from hermes_api.services.docx import render_docx
from hermes_api.services.parties_anonymizer import postprocess_minuta
from hermes_api.storage import get_storage

from ..celery_app import celery_app

DOCX_KEY_TEMPLATE = "cases/{case_id}/minuta.docx"


@celery_app.task(name="hermes.render_docx", bind=True, max_retries=0)
def render_docx_task(self, case_id: str) -> dict[str, str]:  # noqa: ARG001
    cid = uuid.UUID(case_id)
    with SyncSessionLocal() as session:
        case = session.get(Case, cid)
        if case is None:
            return {"status": "not_found", "case_id": case_id}
        if not case.minuta_md:
            case.status = CaseStatus.error
            case.last_error = "minuta ausente"
            session.commit()
            return {"status": "error", "case_id": case_id, "error": "minuta ausente"}

        storage = get_storage()
        if storage is None:
            case.status = CaseStatus.error
            case.last_error = "storage S3 não configurado"
            session.commit()
            return {"status": "error", "case_id": case_id, "error": "no storage"}

        try:
            processed = postprocess_minuta(case.minuta_md, case.anonymization_map)
            blob = render_docx(processed)
            key = DOCX_KEY_TEMPLATE.format(case_id=case_id)
            storage.put_bytes(
                key,
                blob,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            case.docx_key = key
            case.status = CaseStatus.done
            case.last_error = None
            session.commit()
            return {"status": "done", "case_id": case_id}
        except Exception as exc:  # noqa: BLE001
            case.status = CaseStatus.error
            case.last_error = str(exc)[:500]
            session.commit()
            return {"status": "error", "case_id": case_id, "error": str(exc)}
