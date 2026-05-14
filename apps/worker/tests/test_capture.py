from __future__ import annotations

import uuid

import pytest
from hermes_api.db import Base
from hermes_api.models.case import Case, CaseStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sync_session(monkeypatch):
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    session_local = sessionmaker(eng, expire_on_commit=False)
    import hermes_worker.tasks.capture as cap

    monkeypatch.setattr(cap, "SyncSessionLocal", session_local)
    return session_local


def _seed(session_local) -> str:
    with session_local() as s:
        c = Case(
            id=uuid.uuid4(),
            user_id="u1",
            numero_processo="0001234-56.2023.5.10.0001",
            status=CaseStatus.draft,
        )
        s.add(c)
        s.commit()
        return str(c.id)


def test_capture_success(sync_session, mocker) -> None:
    from hermes_worker.tasks.capture import capture_case

    case_id = _seed(sync_session)
    fake = mocker.Mock(status_code=200)
    fake.raise_for_status = mocker.Mock()
    fake.json.return_value = {"html": "<html>ok</html>", "documentos": []}
    mocker.patch("hermes_worker.tasks.capture.httpx.post", return_value=fake)

    result = capture_case.run(case_id)
    assert result["status"] == "captured"

    with sync_session() as s:
        c = s.get(Case, uuid.UUID(case_id))
        assert c.status == CaseStatus.captured
        assert c.raw_html == "<html>ok</html>"
        assert c.captured_at is not None
        assert c.last_error is None


def test_capture_http_error_marks_case_error(sync_session, mocker) -> None:
    from hermes_worker.tasks.capture import capture_case

    case_id = _seed(sync_session)
    mocker.patch(
        "hermes_worker.tasks.capture.httpx.post",
        side_effect=RuntimeError("boom"),
    )

    result = capture_case.run(case_id)
    assert result["status"] == "error"

    with sync_session() as s:
        c = s.get(Case, uuid.UUID(case_id))
        assert c.status == CaseStatus.error
        assert c.last_error == "boom"


def test_capture_unknown_case(sync_session) -> None:
    from hermes_worker.tasks.capture import capture_case

    result = capture_case.run(str(uuid.uuid4()))
    assert result["status"] == "not_found"
