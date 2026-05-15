from __future__ import annotations

from unittest.mock import patch

from hermes_api.services.analysis_themed import build_dossie


def test_stub_returns_empty_with_note() -> None:
    result = build_dossie(pieces=[{"tipo": "recurso_revista", "text": "x"}], blueprint=None)
    assert result["recursos"] == []
    assert "GEMINI_API_KEY" in result["observacoes"]


def test_parses_llm_json(monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()

    fake_response = """{
      "recursos": [
        {
          "tipo": "recurso_revista",
          "parte": "reclamada",
          "temas": [
            {
              "nome": "Horas extras",
              "fundamentos_argumentativos": ["A"],
              "permissivos_invocados": ["art. 7º XIII"],
              "obices_aplicaveis": ["Súmula 126"],
              "jurisprudencia_citada": [],
              "conclusao_sugerida": "não conhecer"
            }
          ]
        }
      ],
      "observacoes": "OK"
    }"""

    class FakeProvider:
        def analyze(self, text: str) -> str:
            return fake_response

    with patch("hermes_api.services.analysis_themed.get_llm_provider", return_value=FakeProvider()):
        result = build_dossie(
            pieces=[{"tipo": "recurso_revista", "parte": "reclamada", "text": "..."}],
            blueprint={"recursos": []},
        )

    assert len(result["recursos"]) == 1
    assert result["recursos"][0]["temas"][0]["nome"] == "Horas extras"
    assert result["observacoes"] == "OK"
