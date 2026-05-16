from __future__ import annotations

from unittest.mock import patch

from hermes_api.services.analysis_themed import (
    _format_blueprint,
    _normalize_transcricoes,
    _split_paragraphs,
    _validate_blueprint_alignment,
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


def _fake_provider(response: str):
    class FakeProvider:
        def analyze(self, text: str) -> str:
            return response

    return FakeProvider()


def _run_build_dossie(monkeypatch, response: str, blueprint: dict) -> dict:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()
    with patch(
        "hermes_api.services.analysis_themed.get_llm_provider",
        return_value=_fake_provider(response),
    ):
        return build_dossie(
            pieces=[{"tipo": "recurso_revista", "parte": "reclamada", "text": "..."}],
            blueprint=blueprint,
        )


def test_blueprint_tema_field_carried_through(monkeypatch) -> None:
    response = """{
      "recursos": [
        {
          "tipo": "recurso_revista", "parte": "reclamada",
          "temas": [
            {"nome": "HORAS EXTRAS", "blueprint_tema": "Horas extras",
             "acordao_recorrido_transcricao": ["x"]}
          ]
        }
      ],
      "observacoes": ""
    }"""
    blueprint = {
        "recursos": [
            {"tipo": "recurso_revista", "parte": "reclamada", "temas": ["Horas extras"]}
        ]
    }
    result = _run_build_dossie(monkeypatch, response, blueprint)
    assert result["recursos"][0]["temas"][0]["blueprint_tema"] == "Horas extras"
    # nenhum aviso de alinhamento
    assert "Alinhamento com o despacho" not in (result.get("observacoes") or "")


def test_validation_warns_when_dossie_has_more_themes_than_blueprint(monkeypatch) -> None:
    response = """{
      "recursos": [
        {
          "tipo": "recurso_revista", "parte": "reclamada",
          "temas": [
            {"nome": "HORAS EXTRAS - DIVISOR", "blueprint_tema": "Horas extras",
             "acordao_recorrido_transcricao": ["x"]},
            {"nome": "HORAS EXTRAS - INTERVALO", "blueprint_tema": "Horas extras",
             "acordao_recorrido_transcricao": ["x"]},
            {"nome": "HORAS EXTRAS - ADICIONAL NOTURNO", "blueprint_tema": "Horas extras",
             "acordao_recorrido_transcricao": ["x"]}
          ]
        }
      ],
      "observacoes": "obs do LLM"
    }"""
    blueprint = {
        "recursos": [
            {"tipo": "recurso_revista", "parte": "reclamada", "temas": ["Horas extras"]}
        ]
    }
    result = _run_build_dossie(monkeypatch, response, blueprint)
    obs = result["observacoes"]
    assert "Alinhamento com o despacho" in obs
    assert "3 temas" in obs
    assert "despacho lista 1" in obs
    # observação original preservada
    assert "obs do LLM" in obs


def test_validation_warns_when_blueprint_tema_not_in_blueprint(monkeypatch) -> None:
    response = """{
      "recursos": [
        {
          "tipo": "recurso_revista", "parte": "reclamada",
          "temas": [
            {"nome": "FOO", "blueprint_tema": "Foo inexistente",
             "acordao_recorrido_transcricao": ["x"]}
          ]
        }
      ],
      "observacoes": ""
    }"""
    blueprint = {
        "recursos": [
            {"tipo": "recurso_revista", "parte": "reclamada", "temas": ["Horas extras"]}
        ]
    }
    result = _run_build_dossie(monkeypatch, response, blueprint)
    obs = result["observacoes"]
    assert "Foo inexistente" in obs
    assert "não consta do despacho" in obs


def test_validation_ignores_null_blueprint_tema(monkeypatch) -> None:
    """Tema marcado explicitamente como matéria nova (null) não gera aviso de mismatch."""
    response = """{
      "recursos": [
        {
          "tipo": "recurso_revista", "parte": "reclamada",
          "temas": [
            {"nome": "MATERIA NOVA", "blueprint_tema": null,
             "acordao_recorrido_transcricao": ["x"]}
          ]
        }
      ],
      "observacoes": ""
    }"""
    blueprint = {
        "recursos": [
            {"tipo": "recurso_revista", "parte": "reclamada", "temas": []}
        ]
    }
    result = _run_build_dossie(monkeypatch, response, blueprint)
    # 1 tema vs 0 do blueprint dispara aviso de contagem, mas não de mismatch por null
    obs = result.get("observacoes") or ""
    assert "não consta do despacho" not in obs


def test_format_blueprint_renders_numbered_list() -> None:
    blueprint = {
        "recursos": [
            {
                "tipo": "recurso_revista",
                "parte": "reclamada",
                "conclusao": "admitido",
                "temas": ["Horas extras", "Dano moral"],
            },
            {
                "tipo": "agravo_instrumento",
                "parte": "reclamante",
                "conclusao": "denegado",
                "temas": ["Insalubridade"],
            },
        ]
    }
    out = _format_blueprint(blueprint)
    assert "1. Horas extras" in out
    assert "2. Dano moral" in out
    assert "1. Insalubridade" in out
    # checa que o cabeçalho do recurso está presente
    assert "admitido:" in out
    assert "denegado:" in out


def test_validate_blueprint_alignment_no_blueprint_means_no_warnings() -> None:
    dossie = {"recursos": [{"tipo": "recurso_revista", "parte": "reclamada", "temas": [{}]}]}
    assert _validate_blueprint_alignment(dossie, None) == []
    assert _validate_blueprint_alignment(dossie, {"recursos": []}) == []
