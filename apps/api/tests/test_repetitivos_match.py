from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def fake_repetitivos():
    """Stub de TemaRepetitivo (sem precisar de DB)."""

    class _R:
        def __init__(self, numero, descricao, situacao, tese=None):
            self.numero = numero
            self.descricao = descricao
            self.situacao = situacao
            self.tese = tese

    return [
        _R(42, "Súmula 124 ao bancário com jornada 6h.", "suspenso"),
        _R(87, "Validade do divisor 220 em norma coletiva.", "decidido", "É válida..."),
        _R(99, "Outro tema sem aderência.", "outro"),
    ]


def _stage_responses(stage1: str, stage2: str):
    """Mock que devolve respostas distintas por chamada (stage1 primeiro)."""
    calls = {"n": 0}

    class FakeProvider:
        def analyze(self, prompt: str, **_kw) -> str:
            calls["n"] += 1
            return stage1 if calls["n"] == 1 else stage2

    return FakeProvider(), calls


def test_match_two_stage_confirma_subset(monkeypatch, fake_repetitivos) -> None:
    """Stage 1 devolve 3 candidatos; stage 2 confirma só o tema 42.
    O tema 87 é rejeitado (matéria diferente) e o 99 não passa o stage 1.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    from hermes_api.services.repetitivos_match import _format_tabela, _match_one_tema

    stage1 = """{
      "matches": [
        {"numero": 42, "confidence": 0.85, "justificativa": "matéria idêntica"},
        {"numero": 87, "confidence": 0.65, "justificativa": "possível"}
      ]
    }"""
    stage2 = """{
      "verificacoes": [
        {"numero": 42, "confirmado": true,  "razao": "mesma matéria e conflito", "confidence_final": 0.92},
        {"numero": 87, "confirmado": false, "razao": "matéria distinta",         "confidence_final": 0.2}
      ]
    }"""

    fake, calls = _stage_responses(stage1, stage2)
    tema = {
        "nome": "HORAS EXTRAS - DIVISOR",
        "fundamentos_argumentativos": ["jornada contratual de 6h"],
        "permissivos_invocados": ["Súmula 124 do TST"],
        "acordao_recorrido_resumo": "TRT aplicou divisor 220.",
    }
    tabela = _format_tabela(fake_repetitivos)
    with patch(
        "hermes_api.services.repetitivos_match.get_llm_provider",
        return_value=fake,
    ):
        out = _match_one_tema(tema, fake_repetitivos, tabela)

    assert calls["n"] == 2  # rodou stage 1 e stage 2
    assert [m["numero"] for m in out] == [42]
    item = out[0]
    assert item["kind"] == "alta"
    assert item["confidence"] == 0.92
    assert item["verificacao_razao"] == "mesma matéria e conflito"
    assert item["justificativa"] == "matéria idêntica"
    assert item["situacao"] == "suspenso"


def test_match_two_stage_rejeita_todos(monkeypatch, fake_repetitivos) -> None:
    """Stage 2 rejeita tudo → output vazio."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    from hermes_api.services.repetitivos_match import _format_tabela, _match_one_tema

    stage1 = """{"matches":[{"numero":42,"confidence":0.7,"justificativa":"x"}]}"""
    stage2 = """{"verificacoes":[{"numero":42,"confirmado":false,"razao":"não bate","confidence_final":0.1}]}"""
    fake, _ = _stage_responses(stage1, stage2)
    tema = {
        "nome": "X",
        "fundamentos_argumentativos": [],
        "permissivos_invocados": [],
        "acordao_recorrido_resumo": "",
    }
    with patch(
        "hermes_api.services.repetitivos_match.get_llm_provider", return_value=fake
    ):
        assert _match_one_tema(tema, fake_repetitivos, _format_tabela(fake_repetitivos)) == []


def test_match_two_stage_descartando_baixa_confidence_no_stage1(
    monkeypatch, fake_repetitivos
) -> None:
    """Stage 1 filtra candidatos com confidence < 0.6 antes do stage 2."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    from hermes_api.services.repetitivos_match import _format_tabela, _match_one_tema

    # único candidato com 0.5 → cai no stage 1, stage 2 não roda
    stage1 = """{"matches":[{"numero":42,"confidence":0.5,"justificativa":"x"}]}"""
    stage2 = "NUNCA CHAMADO"
    fake, calls = _stage_responses(stage1, stage2)
    tema = {
        "nome": "X",
        "fundamentos_argumentativos": [],
        "permissivos_invocados": [],
        "acordao_recorrido_resumo": "",
    }
    with patch(
        "hermes_api.services.repetitivos_match.get_llm_provider", return_value=fake
    ):
        assert _match_one_tema(tema, fake_repetitivos, _format_tabela(fake_repetitivos)) == []
    assert calls["n"] == 1  # stage 2 nem foi chamado


def test_match_stub_provider_returns_empty(monkeypatch, fake_repetitivos) -> None:
    """Sem GEMINI_API_KEY, o provider é stub e devolve [] silenciosamente."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from hermes_api.config import get_settings

    get_settings.cache_clear()
    from hermes_api.services.repetitivos_match import _format_tabela, _match_one_tema

    tema = {"nome": "X", "fundamentos_argumentativos": [], "permissivos_invocados": []}
    assert _match_one_tema(tema, fake_repetitivos, _format_tabela(fake_repetitivos)) == []


def test_format_tabela_trunca_descricao() -> None:
    from hermes_api.services.repetitivos_match import _format_tabela

    class _R:
        numero = 1
        descricao = "x" * 1000
        situacao = "suspenso"
        tese = None

    out = _format_tabela([_R()])
    assert "Tema 1 [suspenso]" in out
    # Trunca a descrição longa em ~220 chars + ellipsis.
    assert "…" in out


def test_stage2_below_confidence_threshold_is_filtered(monkeypatch, fake_repetitivos) -> None:
    """confirmado=true mas confidence_final abaixo de STAGE2_MIN_CONFIDENCE → descartado."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    from hermes_api.services.repetitivos_match import _format_tabela, _match_one_tema

    stage1 = """{"matches":[{"numero":42,"confidence":0.8,"justificativa":"x"}]}"""
    # confirmado=true mas confidence_final 0.5 (< 0.7) → cai
    stage2 = """{"verificacoes":[{"numero":42,"confirmado":true,"razao":"fraco","confidence_final":0.5}]}"""
    fake, _ = _stage_responses(stage1, stage2)
    tema = {
        "nome": "X",
        "fundamentos_argumentativos": [],
        "permissivos_invocados": [],
        "acordao_recorrido_resumo": "",
    }
    with patch(
        "hermes_api.services.repetitivos_match.get_llm_provider", return_value=fake
    ):
        out = _match_one_tema(tema, fake_repetitivos, _format_tabela(fake_repetitivos))
    assert out == []
