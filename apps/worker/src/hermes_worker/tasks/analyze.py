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


@celery_app.task(name="hermes.analyze_case", bind=True, max_retries=0)
def analyze_case(self, case_id: str) -> dict[str, str]:  # noqa: ARG001
    cid = uuid.UUID(case_id)
    with SyncSessionLocal() as session:
        case = session.get(Case, cid)
        if case is None:
            return {"status": "not_found", "case_id": case_id}

        html = _load_html(case)
        if html is None:
            return {"status": "no_capture", "case_id": case_id}

        case.status = CaseStatus.analyzing
        case.last_error = None
        session.commit()

        try:
            anon = anonymize(html)
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
