from __future__ import annotations

from unittest.mock import patch

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}


def test_debug_anonymize_regex_only(client, monkeypatch) -> None:
    """Sem GEMINI_API_KEY, regex roda e LLM step inclui _note."""
    from hermes_api.config import get_settings

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()

    resp = client.post(
        "/debug/anonymize",
        headers=HEADERS,
        json={"text": "CPF 123.456.789-00 e email teste@x.com"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "<CPF_1>" in body["anonymized"]
    assert "<EMAIL_1>" in body["anonymized"]
    assert body["substitutions"] == 2
    assert "_note" in body["mapping"]


def test_debug_anonymize_requires_auth(client) -> None:
    resp = client.post("/debug/anonymize", json={"text": "x"})
    assert resp.status_code in (401, 403)


def test_debug_anonymize_with_llm(client, monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()

    fake_response = '{"entities": [{"type": "NAME", "original": "João Silva"}]}'
    with patch(
        "hermes_api.services.anonymizer_llm._GeminiAnonymizerProvider.detect_pii",
        return_value=fake_response,
    ):
        resp = client.post(
            "/debug/anonymize",
            headers=HEADERS,
            json={"text": "Reclamante João Silva, CPF 111.222.333-44"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "<NAME_1>" in body["anonymized"]
    assert "<CPF_1>" in body["anonymized"]
    assert body["substitutions"] == 2
