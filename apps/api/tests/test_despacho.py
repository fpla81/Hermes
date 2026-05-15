from __future__ import annotations

from unittest.mock import patch

from hermes_api.services.despacho import parse_despacho


def test_stub_returns_empty_blueprint_with_note() -> None:
    """Sem GEMINI_API_KEY o provider é StubProvider e devolve aviso."""
    result = parse_despacho("texto do despacho")
    assert result["recursos"] == []
    assert "GEMINI_API_KEY" in result["note"]


def test_normalizes_llm_response() -> None:
    fake_response = """{
      "recursos": [
        {"tipo": "Recurso_Revista", "parte": "Reclamada", "temas": ["Horas extras"], "conclusao": "ADMITIDO"},
        {"tipo": "agravo_instrumento", "parte": "reclamante", "temas": [], "conclusao": "denegado"}
      ]
    }"""

    class FakeProvider:
        def analyze(self, text: str) -> str:
            return fake_response

    with patch("hermes_api.services.despacho.get_llm_provider", return_value=FakeProvider()):
        result = parse_despacho("texto do despacho")

    assert len(result["recursos"]) == 2
    assert result["recursos"][0]["tipo"] == "recurso_revista"
    assert result["recursos"][0]["parte"] == "reclamada"
    assert result["recursos"][0]["temas"] == ["Horas extras"]
    assert result["recursos"][0]["conclusao"] == "admitido"


def test_handles_garbled_response() -> None:
    class FakeProvider:
        def analyze(self, text: str) -> str:
            return "isso não é JSON"

    with patch("hermes_api.services.despacho.get_llm_provider", return_value=FakeProvider()):
        result = parse_despacho("x")
    assert result["recursos"] == []
    assert "JSON" in result["note"]
