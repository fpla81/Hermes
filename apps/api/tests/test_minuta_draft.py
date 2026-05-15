from __future__ import annotations

from unittest.mock import patch

from hermes_api.services.minuta_draft import build_minuta_draft


def test_stub_returns_skeleton() -> None:
    pieces = [
        {"tipo": "recurso_revista", "parte": "reclamada", "text": "x"},
    ]
    result = build_minuta_draft("0001234-56.2023.5.06.0020", pieces, None)
    assert "[[CORPO]]" in result
    assert "0001234-56.2023.5.06.0020" in result
    assert "TODO" in result


def test_uses_llm_when_dossie_present(monkeypatch) -> None:
    from hermes_api.config import get_settings

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    get_settings.cache_clear()

    fake_response = "[[CORPO]]\nMINUTA GERADA PELO LLM"

    class FakeProvider:
        def analyze(self, text: str) -> str:
            return fake_response

    with patch("hermes_api.services.minuta_draft.get_llm_provider", return_value=FakeProvider()):
        result = build_minuta_draft(
            "0001234-56.2023.5.06.0020",
            [{"tipo": "recurso_revista", "parte": "reclamada", "text": "x"}],
            {"recursos": [{"tipo": "recurso_revista", "parte": "reclamada", "temas": []}]},
        )

    assert "MINUTA GERADA PELO LLM" in result
