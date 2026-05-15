from __future__ import annotations

from unittest.mock import patch

from hermes_api.services.anonymizer_llm import full_anonymize, llm_anonymize


def test_llm_anonymize_no_api_key(monkeypatch) -> None:
    """Sem GEMINI_API_KEY, devolve o texto intocado com note no mapping."""
    from hermes_api.config import get_settings

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()

    result = llm_anonymize("João da Silva, mora na Rua das Flores, 123")
    assert result.text == "João da Silva, mora na Rua das Flores, 123"
    assert "GEMINI_API_KEY" in result.mapping["_note"]


def test_llm_anonymize_substitutes_entities(monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("HERMES_INTERNAL_SECRET", "x")
    get_settings.cache_clear()

    fake_response = """{
      "entities": [
        {"type": "NAME", "original": "João da Silva"},
        {"type": "ADDRESS", "original": "Rua das Flores, 123"},
        {"type": "COMPANY", "original": "Acme LTDA"}
      ]
    }"""

    with patch(
        "hermes_api.services.anonymizer_llm._GeminiAnonymizerProvider.detect_pii",
        return_value=fake_response,
    ):
        result = llm_anonymize(
            "O reclamante João da Silva trabalhou na Acme LTDA, na Rua das Flores, 123."
        )

    assert "João da Silva" not in result.text
    assert "Acme LTDA" not in result.text
    assert "Rua das Flores, 123" not in result.text
    assert "<NAME_1>" in result.text
    assert "<ADDRESS_1>" in result.text
    assert "<COMPANY_1>" in result.text
    assert result.mapping["<NAME_1>"] == "João da Silva"


def test_llm_anonymize_handles_bad_json(monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()

    with patch(
        "hermes_api.services.anonymizer_llm._GeminiAnonymizerProvider.detect_pii",
        return_value="isso não é JSON",
    ):
        result = llm_anonymize("texto qualquer")
    assert result.text == "texto qualquer"
    assert result.mapping == {}


def test_full_anonymize_combines_regex_and_llm(monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()

    text = "João da Silva (CPF 123.456.789-00) ajuizou ação contra Acme LTDA."
    fake_llm = '{"entities": [{"type": "NAME", "original": "João da Silva"}, {"type": "COMPANY", "original": "Acme LTDA"}]}'

    with patch(
        "hermes_api.services.anonymizer_llm._GeminiAnonymizerProvider.detect_pii",
        return_value=fake_llm,
    ):
        result = full_anonymize(text)

    # CPF veio do regex, NAME/COMPANY vieram do LLM
    assert "123.456.789-00" not in result.text
    assert "João da Silva" not in result.text
    assert "Acme LTDA" not in result.text
    assert "<CPF_1>" in result.mapping
    assert "<NAME_1>" in result.mapping
    assert "<COMPANY_1>" in result.mapping
