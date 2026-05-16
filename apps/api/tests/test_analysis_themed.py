from __future__ import annotations

from unittest.mock import patch

from hermes_api.services.analysis_themed import (
    _normalize_transcricoes,
    _split_paragraphs,
    build_dossie,
)


def test_split_paragraphs_from_string_with_double_newline() -> None:
    out = _split_paragraphs("Parágrafo 1.\n\nParágrafo 2.\n\nParágrafo 3.")
    assert out == ["Parágrafo 1.", "Parágrafo 2.", "Parágrafo 3."]


def test_split_paragraphs_from_string_with_single_newline() -> None:
    out = _split_paragraphs("Linha 1.\nLinha 2.")
    assert out == ["Linha 1.", "Linha 2."]


def test_split_paragraphs_keeps_list_intact() -> None:
    out = _split_paragraphs(["A", "B", "  ", "C"])
    assert out == ["A", "B", "C"]


def test_split_paragraphs_none_or_empty() -> None:
    assert _split_paragraphs(None) is None
    assert _split_paragraphs("") is None
    assert _split_paragraphs([]) is None
    assert _split_paragraphs("   ") is None


def test_normalize_transcricoes_converts_strings_to_lists() -> None:
    dossie = {
        "recursos": [
            {
                "temas": [
                    {
                        "acordao_recorrido_transcricao": "P1.\n\nP2.",
                        "embargos_transcricao": None,
                    }
                ]
            }
        ]
    }
    out = _normalize_transcricoes(dossie)
    tema = out["recursos"][0]["temas"][0]
    assert tema["acordao_recorrido_transcricao"] == ["P1.", "P2."]
    assert tema["embargos_transcricao"] is None


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
    assert tema["acordao_recorrido_transcricao"] == ["trecho literal"]
    assert tema["analise_juridica"].startswith("Conheço")
    assert result["observacoes"] == "OK"
