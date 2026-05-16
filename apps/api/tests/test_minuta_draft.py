from __future__ import annotations

from unittest.mock import patch

from hermes_api.services.docx import STYLE_MARKERS
from hermes_api.services.minuta_draft import (
    PROMPT_TEMPLATE,
    VALID_MARKERS,
    _validate_minuta_structure,
    build_minuta_draft,
    compute_marco_legal,
)


def test_stub_returns_skeleton() -> None:
    pieces = [
        {"tipo": "recurso_revista", "parte": "reclamada", "text": "x"},
    ]
    result = build_minuta_draft("0001234-56.2023.5.06.0020", pieces, None)
    assert "[[CORPO]]" in result
    assert "0001234-56.2023.5.06.0020" in result
    assert "DISPOSITIVO" in result


def test_uses_llm_when_dossie_present(monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()

    fake_response = (
        "[[CORPO]]\n"
        "RECURSO DE REVISTA DA PARTE RECLAMADA INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017\n"
        "\n[[CORPO]]\nTEMA - HORAS EXTRAS\n\n"
        "[[CORPO]]\nDISPOSITIVO\nConheço e dou provimento."
    )

    class FakeProvider:
        def analyze(self, text: str) -> str:
            return fake_response

    with patch("hermes_api.services.minuta_draft.get_llm_provider", return_value=FakeProvider()):
        result = build_minuta_draft(
            "0001234-56.2023.5.06.0020",
            [{"tipo": "recurso_revista", "parte": "reclamada", "text": "x"}],
            {"recursos": [{"tipo": "recurso_revista", "parte": "reclamada", "temas": []}]},
            acordao_regional_data="15/06/2020",
        )

    assert "TEMA - HORAS EXTRAS" in result
    assert "DISPOSITIVO" in result
    # nenhum aviso de estrutura
    assert "<!-- AVISO" not in result


def test_prompt_lists_all_markers() -> None:
    """Prompt deve mencionar todos os marcadores válidos do renderizador DOCX."""
    for marker in STYLE_MARKERS:
        assert marker in PROMPT_TEMPLATE, f"marcador {marker} ausente do prompt"


def test_prompt_contains_agravo_interno_hierarchy() -> None:
    assert "HIERARQUIA QUANDO HÁ AGRAVO INTERNO" in PROMPT_TEMPLATE
    assert "Reitera as alegações no Agravo de Instrumento." in PROMPT_TEMPLATE


def test_prompt_contains_transcricao_formulas() -> None:
    """Prompt deve listar as 3 fórmulas de transição para a transcrição do acórdão regional."""
    assert "Eis o teor do acórdão regional:" in PROMPT_TEMPLATE
    assert "Eis os termos do acórdão regional:" in PROMPT_TEMPLATE
    assert "Esses, os termos do acórdão regional:" in PROMPT_TEMPLATE


def test_prompt_contains_tempos_verbais_section() -> None:
    """Prompt deve documentar a regra de tempos verbais por recurso em julgamento."""
    assert "TEMPOS VERBAIS POR RECURSO EM JULGAMENTO" in PROMPT_TEMPLATE
    assert "PRESENTE" in PROMPT_TEMPLATE
    assert "PASSADO" in PROMPT_TEMPLATE


def test_prompt_contains_compact_agravo_interno_formula() -> None:
    """Em sede de Agravo Interno reiterando, AIRR + AInterno colapsam em UMA frase."""
    assert (
        "No Agravo de Instrumento e no presente Agravo Interno, [a Reclamada/o Reclamante] reitera as alegações."
        in PROMPT_TEMPLATE
    )


def test_compute_marco_legal_lei_13015() -> None:
    assert compute_marco_legal("01/01/2013") == (
        "INTERPOSTO ANTERIORMENTE À VIGÊNCIA DA LEI Nº 13.015/2014"
    )


def test_compute_marco_legal_lei_13467() -> None:
    assert compute_marco_legal("15/06/2016") == (
        "INTERPOSTO ANTERIORMENTE À VIGÊNCIA DA LEI Nº 13.467/2017"
    )


def test_compute_marco_legal_pos_reforma() -> None:
    assert compute_marco_legal("01/03/2020") == (
        "INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017"
    )


def test_compute_marco_legal_iso() -> None:
    assert compute_marco_legal("2020-03-01") == (
        "INTERPOSTO NA VIGÊNCIA DA LEI Nº 13.467/2017"
    )


def test_compute_marco_legal_unknown() -> None:
    assert compute_marco_legal(None) is None
    assert compute_marco_legal("") is None
    assert compute_marco_legal("data inválida") is None


def test_validate_structure_ok() -> None:
    text = "[[CORPO]]\nTEMA - X\nDISPOSITIVO"
    assert _validate_minuta_structure(text) == []


def test_validate_structure_missing_dispositivo() -> None:
    text = "[[CORPO]]\nTEMA - X\nfim"
    problems = _validate_minuta_structure(text)
    assert any("DISPOSITIVO" in p for p in problems)


def test_validate_structure_missing_tema() -> None:
    text = "[[CORPO]]\ntexto\nDISPOSITIVO"
    problems = _validate_minuta_structure(text)
    assert any("TEMA" in p for p in problems)


def test_validate_structure_does_not_start_with_corpo() -> None:
    text = "TEMA - X\n[[CORPO]]\nDISPOSITIVO"
    problems = _validate_minuta_structure(text)
    assert any("[[CORPO]]" in p for p in problems)


def test_validate_structure_unknown_marker() -> None:
    text = "[[CORPO]]\n[[FOOBAR]]\nTEMA - X\nDISPOSITIVO"
    problems = _validate_minuta_structure(text)
    assert any("FOOBAR" in p for p in problems)


def test_build_minuta_warns_on_bad_output(monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()

    class FakeProvider:
        def analyze(self, text: str) -> str:
            return "minuta sem marcadores"

    with patch("hermes_api.services.minuta_draft.get_llm_provider", return_value=FakeProvider()):
        result = build_minuta_draft(
            "0001234-56.2023.5.06.0020",
            [{"tipo": "recurso_revista", "parte": "reclamada", "text": "x"}],
            {"recursos": [{"tipo": "recurso_revista", "parte": "reclamada", "temas": []}]},
        )

    assert result.startswith("<!-- AVISO")
    assert "minuta sem marcadores" in result


def test_valid_markers_match_style_markers() -> None:
    """A lista interna deve refletir exatamente o STYLE_MARKERS de docx.py."""
    assert set(VALID_MARKERS) == set(STYLE_MARKERS.keys())
