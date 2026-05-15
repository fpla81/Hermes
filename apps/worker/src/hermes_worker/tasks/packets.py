from __future__ import annotations

import json
import uuid

from hermes_api.db import SyncSessionLocal
from hermes_api.models.case import Case, CaseStatus
from hermes_api.services.analysis_packets import build_packets
from hermes_api.services.prepared import load_prepared_pieces
from hermes_api.storage import get_storage

from ..celery_app import celery_app

PACKETS_KEY_TEMPLATE = "cases/{case_id}/packets.jsonl"


@celery_app.task(name="hermes.build_packets", bind=True, max_retries=0)
def build_packets_task(self, case_id: str) -> dict[str, str]:  # noqa: ARG001
    cid = uuid.UUID(case_id)
    with SyncSessionLocal() as session:
        case = session.get(Case, cid)
        if case is None:
            return {"status": "not_found", "case_id": case_id}
        if not case.manifest:
            case.status = CaseStatus.error
            case.last_error = "manifest ausente"
            session.commit()
            return {"status": "error", "case_id": case_id, "error": "manifest ausente"}

        storage = get_storage()
        if storage is None:
            case.status = CaseStatus.error
            case.last_error = "storage S3 não configurado"
            session.commit()
            return {"status": "error", "case_id": case_id, "error": "no storage"}

        try:
            prepared = load_prepared_pieces(storage, case_id, case.pieces_json)
            packets, index = build_packets(dict(case.manifest), prepared)
            body = "\n".join(json.dumps(p, ensure_ascii=False) for p in packets).encode("utf-8")
            key = PACKETS_KEY_TEMPLATE.format(case_id=case_id)
            storage.put_bytes(key, body, "application/x-ndjson")
            case.packets_key = key
            case.packet_index = index
            case.status = CaseStatus.ready
            case.last_error = None
            session.commit()
            return {"status": "ready", "case_id": case_id, "packets": str(len(packets))}
        except Exception as exc:  # noqa: BLE001
            case.status = CaseStatus.error
            case.last_error = str(exc)[:500]
            session.commit()
            return {"status": "error", "case_id": case_id, "error": str(exc)}
