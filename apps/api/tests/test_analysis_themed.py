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
          "marco_legal_hint": "13.467/2017",
          "temas": [
            {
              "nome": "HORAS EXTRAS - INTERVALO INTRAJORNADA",
              "admissibilidade": "admitido",
              "acordao_recorrido_resumo": "O Eg. TRT negou provimento ao Recurso Ordinário da Reclamada...",
              "acordao_recorrido_transcricao": "trecho literal",
              "embargos_resumo": null,
              "embargos_transcricao": null,
              "fundamentos_argumentativos": ["A reforma trabalhista altera o regime"],
              "permissivos_invocados": ["art. 71, § 4º, da CLT"],
              "obices_aplicaveis": ["Súmula 126 do TST"],
              "jurisprudencia_citada": [],
              "conclusao_sugerida": "conhecer e dar provimento",
              "analise_juridica": "Conheço do Recurso..."
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
    tema = result["recursos"][0]["temas"][0]
    assert tema["nome"] == "HORAS EXTRAS - INTERVALO INTRAJORNADA"
    assert tema["acordao_recorrido_resumo"].startswith("O Eg. TRT")
    assert tema["acordao_recorrido_transcricao"] == "trecho literal"
    assert tema["analise_juridica"].startswith("Conheço")
    assert result["observacoes"] == "OK"
