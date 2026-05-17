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


def test_match_extrai_alta_e_media(monkeypatch, fake_repetitivos) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from hermes_api.config import get_settings

    get_settings.cache_clear()

    from hermes_api.services.repetitivos_match import _format_tabela, _match_one_tema

    fake_response = """{
      "matches": [
        {"numero": 42, "confidence": 0.85, "justificativa": "matéria idêntica"},
        {"numero": 87, "confidence": 0.5, "justificativa": "possível aderência"},
        {"numero": 99, "confidence": 0.1, "justificativa": "fraco"}
      ]
    }"""

    class FakeProvider:
        def analyze(self, prompt: str) -> str:
            return fake_response

    tema = {
        "nome": "HORAS EXTRAS - DIVISOR",
        "fundamentos_argumentativos": ["jornada contratual de 6h"],
        "permissivos_invocados": ["Súmula 124 do TST"],
    }
    tabela = _format_tabela(fake_repetitivos)
    with patch("hermes_api.services.repetitivos_match.get_llm_provider", return_value=FakeProvider()):
        out = _match_one_tema(tema, fake_repetitivos, tabela)

    kinds = {m["numero"]: m["kind"] for m in out}
    assert kinds == {42: "alta", 87: "media"}  # numero 99 abaixo do threshold
    assert out[0]["numero"] == 42
    assert out[0]["confidence"] == 0.85
    assert out[1]["confidence"] == 0.5
    assert out[0]["situacao"] == "suspenso"
    assert out[1]["tese"] == "É válida..."


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


def test_classify_kind_thresholds() -> None:
    from hermes_api.services.repetitivos_match import _classify_kind

    assert _classify_kind(0.9) == "alta"
    assert _classify_kind(0.7) == "alta"
    assert _classify_kind(0.69) == "media"
    assert _classify_kind(0.4) == "media"
    assert _classify_kind(0.39) is None
    assert _classify_kind(0.0) is None
