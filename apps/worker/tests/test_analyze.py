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
    import hermes_worker.tasks.analyze as a

    monkeypatch.setattr(a, "SyncSessionLocal", session_local)
    return session_local


def _seed_with_html(session_local, html: str) -> str:
    with session_local() as s:
        c = Case(
            id=uuid.uuid4(),
            user_id="u1",
            numero_processo="0001234-56.2023.5.10.0001",
            status=CaseStatus.captured,
            raw_html=html,
        )
        s.add(c)
        s.commit()
        return str(c.id)


def test_analyze_anonymiza_e_chama_llm(sync_session, mocker) -> None:
    from hermes_worker.tasks.analyze import analyze_case

    case_id = _seed_with_html(sync_session, "CPF 123.456.789-09 reclamante")

    fake = mocker.Mock()
    fake.analyze.return_value = "resultado da análise"
    mocker.patch("hermes_worker.tasks.analyze.get_llm_provider", return_value=fake)

    result = analyze_case.run(case_id)
    assert result["status"] == "ready"

    # LLM recebeu texto anonimizado, não o CPF original
    sent_text = fake.analyze.call_args[0][0]
    assert "123.456.789-09" not in sent_text
    assert "<CPF_1>" in sent_text

    with sync_session() as s:
        c = s.get(Case, uuid.UUID(case_id))
        assert c.status == CaseStatus.ready
        assert c.analysis_result == "resultado da análise"
        assert c.analyzed_at is not None
        assert c.anonymization_map == {"<CPF_1>": "123.456.789-09"}


def test_analyze_sem_captura_retorna_no_capture(sync_session) -> None:
    from hermes_worker.tasks.analyze import analyze_case

    with sync_session() as s:
        c = Case(
            id=uuid.uuid4(),
            user_id="u1",
            numero_processo="0001234-56.2023.5.10.0001",
            status=CaseStatus.draft,
        )
        s.add(c)
        s.commit()
        cid = str(c.id)

    result = analyze_case.run(cid)
    assert result["status"] == "no_capture"


def test_analyze_llm_erro_marca_caso_como_error(sync_session, mocker) -> None:
    from hermes_worker.tasks.analyze import analyze_case

    case_id = _seed_with_html(sync_session, "texto")
    fake = mocker.Mock()
    fake.analyze.side_effect = RuntimeError("api down")
    mocker.patch("hermes_worker.tasks.analyze.get_llm_provider", return_value=fake)

    result = analyze_case.run(case_id)
    assert result["status"] == "error"

    with sync_session() as s:
        c = s.get(Case, uuid.UUID(case_id))
        assert c.status == CaseStatus.error
        assert c.last_error == "api down"
