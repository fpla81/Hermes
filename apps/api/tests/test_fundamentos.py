from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from hermes_api.models.case import Case
from hermes_api.models.fundamento import Fundamento
from hermes_api.services.fundamentos import (
    extract_from_minuta,
    increment_usage,
    search_for_theme,
)

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}


@pytest.mark.asyncio
async def test_search_ranks_exact_tema_first(session_factory) -> None:
    async with session_factory() as db:
        db.add_all(
            [
                Fundamento(
                    user_id="u1",
                    tema="DANO MORAL - QUANTUM",
                    titulo="Tese base",
                    corpo_md="x",
                    tags=["dano moral"],
                    resumo="Critérios de proporcionalidade.",
                ),
                Fundamento(
                    user_id="u1",
                    tema="HORAS EXTRAS",
                    titulo="Outro tema",
                    corpo_md="y",
                    tags=["horas extras"],
                    resumo="bla",
                ),
            ]
        )
        await db.commit()
        out = await search_for_theme(db, "u1", "DANO MORAL - QUANTUM")
        assert len(out) >= 1
        assert out[0].tema == "DANO MORAL - QUANTUM"


@pytest.mark.asyncio
async def test_search_isolates_by_user(session_factory) -> None:
    async with session_factory() as db:
        db.add_all(
            [
                Fundamento(
                    user_id="u1",
                    tema="DANO MORAL",
                    titulo="A",
                    corpo_md="x",
                    tags=[],
                    resumo="Tese sobre dano moral.",
                ),
                Fundamento(
                    user_id="u2",
                    tema="DANO MORAL",
                    titulo="B",
                    corpo_md="x",
                    tags=[],
                    resumo="Tese sobre dano moral.",
                ),
            ]
        )
        await db.commit()
        out_u1 = await search_for_theme(db, "u1", "DANO MORAL")
        assert len(out_u1) == 1
        assert out_u1[0].titulo == "A"


@pytest.mark.asyncio
async def test_search_uses_tags_overlap(session_factory) -> None:
    async with session_factory() as db:
        db.add_all(
            [
                Fundamento(
                    user_id="u1",
                    tema="OUTRA COISA",
                    titulo="match por tag",
                    corpo_md="x",
                    tags=["dano moral", "quantum"],
                    resumo="referência sobre dano moral",
                ),
                Fundamento(
                    user_id="u1",
                    tema="OUTRA COISA",
                    titulo="sem aderência",
                    corpo_md="x",
                    tags=["totalmente diferente"],
                    resumo="referência sobre dano moral",
                ),
            ]
        )
        await db.commit()
        out = await search_for_theme(
            db, "u1", "DANO MORAL", tags_hint=["dano moral", "quantum"]
        )
        assert out[0].titulo == "match por tag"


@pytest.mark.asyncio
async def test_increment_usage(session_factory) -> None:
    async with session_factory() as db:
        f = Fundamento(
            user_id="u1",
            tema="X",
            titulo="t",
            corpo_md="c",
            tags=[],
            resumo=None,
            usage_count=2,
        )
        db.add(f)
        await db.commit()
        await db.refresh(f)
        await increment_usage(db, [f.id])
        await db.commit()
        await db.refresh(f)
        assert f.usage_count == 3


def test_extract_from_minuta_parses_llm_output(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    fake = """{
      "fundamentos": [
        {
          "tema": "DANO MORAL - QUANTUM",
          "titulo": "Critérios de proporcionalidade",
          "corpo_md": "[[CORPO]]\\nConheço do RR...",
          "tags": ["dano moral", "quantum", "art 944 CC"],
          "resumo": "Quantum deve observar proporcionalidade e razoabilidade."
        }
      ]
    }"""

    class FakeProvider:
        def analyze(self, text: str) -> str:
            return fake

    case = Case(
        id=uuid.uuid4(),
        user_id="u1",
        numero_processo="0001234-56.2023.5.06.0020",
        minuta_md="[[CORPO]]\nConheço do RR.",
        analysis_dossie={"recursos": [{"temas": [{"nome": "DANO MORAL - QUANTUM"}]}]},
    )
    with patch(
        "hermes_api.services.fundamentos.get_llm_provider", return_value=FakeProvider()
    ):
        out = extract_from_minuta(case)
    assert len(out) == 1
    assert out[0].tema == "DANO MORAL - QUANTUM"
    assert out[0].tags == ["dano moral", "quantum", "art 944 CC"]
    assert out[0].resumo and "proporcionalidade" in out[0].resumo


def test_extract_returns_empty_in_stub_mode(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from hermes_api.config import get_settings

    get_settings.cache_clear()
    case = Case(
        id=uuid.uuid4(),
        user_id="u1",
        numero_processo="0001234-56.2023.5.06.0020",
        minuta_md="x",
        analysis_dossie={"recursos": []},
    )
    assert extract_from_minuta(case) == []


def test_list_fundamentos_endpoint_filters_by_user(client) -> None:
    from hermes_api.config import get_settings
    from hermes_api.db import get_db
    from hermes_api.main import app

    # Reusa session do client; cria 2 fundamentos via DB direto.
    session_dep = app.dependency_overrides[get_db]

    async def insert() -> list[Fundamento]:
        async for db in session_dep():
            db.add_all(
                [
                    Fundamento(
                        user_id="user-1",
                        tema="DANO MORAL",
                        titulo="meu",
                        corpo_md="x",
                        tags=[],
                        resumo="t",
                    ),
                    Fundamento(
                        user_id="alheio",
                        tema="DANO MORAL",
                        titulo="alheio",
                        corpo_md="x",
                        tags=[],
                        resumo="t",
                    ),
                ]
            )
            await db.commit()
            return []

    import asyncio

    asyncio.get_event_loop().run_until_complete(insert())
    get_settings.cache_clear()

    res = client.get("/fundamentos", headers=HEADERS)
    assert res.status_code == 200, res.text
    body = res.json()
    titles = {f["titulo"] for f in body}
    assert "meu" in titles
    assert "alheio" not in titles
