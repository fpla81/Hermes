from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from hermes_api.config import get_settings
from hermes_api.db import SyncSessionLocal
from hermes_api.models.case import Case, CaseStatus
from hermes_api.storage import get_storage

from ..celery_app import celery_app


@celery_app.task(name="hermes.capture_case", bind=True, max_retries=0)
def capture_case(self, case_id: str) -> dict[str, str]:  # noqa: ARG001
    settings = get_settings()
    cid = uuid.UUID(case_id)
    with SyncSessionLocal() as session:
        case = session.get(Case, cid)
        if case is None:
            return {"status": "not_found", "case_id": case_id}

        case.status = CaseStatus.capturing
        case.last_error = None
        session.commit()

        try:
            r = httpx.post(
                f"{settings.playwright_service_url}/capture",
                json={"numero_processo": case.numero_processo},
                timeout=60.0,
            )
            r.raise_for_status()
            data = r.json()
            html: str = data["html"]
            pieces = data.get("pieces") or []
            storage = get_storage()
            if storage is not None:
                key = f"cases/{case_id}/raw.html"
                storage.put_bytes(
                    key, html.encode("utf-8"), content_type="text/html; charset=utf-8"
                )
                case.artifact_key = key
                case.raw_html = None
            else:
                case.raw_html = html
            if pieces:
                case.pieces_json = pieces
            case.captured_at = datetime.now(UTC)
            case.status = CaseStatus.captured
            session.commit()
            return {"status": "captured", "case_id": case_id}
        except Exception as exc:
            case.status = CaseStatus.error
            case.last_error = str(exc)[:500]
            session.commit()
            return {"status": "error", "case_id": case_id, "error": str(exc)}
