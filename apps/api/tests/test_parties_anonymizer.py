from __future__ import annotations

from hermes_api.services.parties_anonymizer import (
    anonymize_with_parties,
    neutralize_party_placeholders,
    postprocess_minuta,
)


def _party(role: str, name: str, ordinal: int = 1, aliases: list[str] | None = None) -> dict:
    return {"role": role, "ordinal": ordinal, "name": name, "aliases": aliases or []}


def test_anonymizes_party_name() -> None:
    text = "O reclamante Maria Silva ajuizou ação contra Empresa XYZ S/A."
    parties = [
        _party("reclamante", "Maria Silva"),
        _party("reclamada", "Empresa XYZ S/A"),
    ]
    result = anonymize_with_parties(text, parties)
    assert "Maria Silva" not in result.text
    assert "Empresa XYZ" not in result.text
    assert "RECLAMANTE_1" in result.text
    assert "RECLAMADA_1" in result.text
    assert result.mapping["RECLAMANTE_1"] == "Maria Silva"


def test_case_insensitive_match() -> None:
    text = "MARIA SILVA também aparece em caixa alta e maria silva minúscula."
    parties = [_party("reclamante", "Maria Silva")]
    result = anonymize_with_parties(text, parties)
    assert "Maria Silva" not in result.text
    assert "MARIA SILVA" not in result.text
    assert "maria silva" not in result.text
    assert result.text.count("RECLAMANTE_1") == 2


def test_accent_insensitive_match() -> None:
    text = "Joao Pereira (sem acento) e João Pereira (com)."
    parties = [_party("reclamante", "João Pereira")]
    result = anonymize_with_parties(text, parties)
    assert "João Pereira" not in result.text
    assert "Joao Pereira" not in result.text
    assert result.text.count("RECLAMANTE_1") == 2


def test_word_boundary_does_not_clobber_substring() -> None:
    """Parte 'Silva' não deve substituir 'Silvana' nem 'Silva.Costa'."""
    text = "Maria Silvana trabalha. Silva Costa também. Silva sozinha sim."
    parties = [_party("reclamante", "Silva")]
    result = anonymize_with_parties(text, parties)
    # 'Silvana' não pode ser tocado
    assert "Silvana" in result.text
    # 'Silva sozinha' deve virar placeholder
    assert "RECLAMANTE_1 sozinha" in result.text


def test_aliases_also_replaced() -> None:
    text = "Porto do Recife S/A é o réu. Porto do Recife continua. PORTO chamou também."
    parties = [
        _party(
            "reclamada",
            "Porto do Recife S/A",
            aliases=["Porto do Recife", "PORTO"],
        )
    ]
    result = anonymize_with_parties(text, parties)
    assert "Porto do Recife" not in result.text
    assert result.text.count("RECLAMADA_1") == 3


def test_multiple_reclamantes_get_ordinals() -> None:
    text = "Maria Silva e João Souza ajuizaram ação."
    parties = [
        _party("reclamante", "Maria Silva", ordinal=1),
        _party("reclamante", "João Souza", ordinal=2),
    ]
    result = anonymize_with_parties(text, parties)
    assert "RECLAMANTE_1" in result.text
    assert "RECLAMANTE_2" in result.text


def test_mpt_is_skipped() -> None:
    text = "O Ministério Público do Trabalho ajuizou ACP contra Empresa XYZ S/A."
    parties = [
        _party("ministerio_publico", "Ministério Público do Trabalho"),
        _party("reclamada", "Empresa XYZ S/A"),
    ]
    result = anonymize_with_parties(text, parties)
    assert "Ministério Público" in result.text  # não substituído
    assert "Empresa XYZ" not in result.text


def test_keeps_regex_anonymization() -> None:
    text = "Maria Silva, CPF 123.456.789-00, e-mail maria@x.com"
    parties = [_party("reclamante", "Maria Silva")]
    result = anonymize_with_parties(text, parties)
    assert "RECLAMANTE_1" in result.text
    assert "<CPF_1>" in result.text
    assert "<EMAIL_1>" in result.text


def test_no_parties_returns_regex_only() -> None:
    text = "CPF 123.456.789-00 sem partes cadastradas."
    result = anonymize_with_parties(text, None)
    assert "<CPF_1>" in result.text


def test_neutralize_placeholders_single_party() -> None:
    out = neutralize_party_placeholders("RECLAMANTE_1 alega. RECLAMADA_1 contesta.")
    assert "a parte Reclamante" in out
    assert "a parte Reclamada" in out
    assert "RECLAMANTE_1" not in out


def test_neutralize_placeholders_multiple_parties() -> None:
    out = neutralize_party_placeholders("RECLAMANTE_2 e RECLAMADA_3 discutem.")
    assert "a segunda parte Reclamante" in out
    assert "a terceira parte Reclamada" in out


def test_postprocess_minuta_deanonymizes_transcricao() -> None:
    minuta = """[[CORPO]]
RECLAMANTE_1 sustenta que tem razão.

[[TRANSCRICAO1]]
O Tribunal entendeu que RECLAMANTE_1 não comprovou os fatos.

[[CORPO]]
Conheço do Recurso de Revista da parte Reclamante."""
    mapping = {"RECLAMANTE_1": "Maria Silva"}
    out = postprocess_minuta(minuta, mapping)
    # CORPO: neutralizado
    assert "a parte Reclamante sustenta" in out
    # TRANSCRICAO: deanonimizado literal
    assert "Maria Silva não comprovou" in out


def test_postprocess_minuta_handles_no_mapping() -> None:
    minuta = "[[CORPO]]\nRECLAMANTE_1 ajuizou."
    out = postprocess_minuta(minuta, None)
    assert "a parte Reclamante" in out
