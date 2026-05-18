from hermes_api.llm import GeminiProvider, StubProvider


def test_stub_returns_predictable_text() -> None:
    out = StubProvider().analyze("texto anonimizado")
    assert "stub" in out.lower()
    assert "tamanho do texto" in out.lower()


def test_gemini_provider_makes_request(mocker) -> None:
    fake = mocker.Mock(status_code=200)
    fake.raise_for_status = mocker.Mock()
    fake.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "análise"}, {"text": " continuada"}]}}
        ]
    }
    post = mocker.patch("hermes_api.llm.httpx.post", return_value=fake)

    out = GeminiProvider(api_key="k", model="gemini-2.5-flash").analyze("oi")
    assert out == "análise continuada"
    assert post.called
    args, kwargs = post.call_args
    assert "gemini-2.5-flash:generateContent" in args[0]
    assert kwargs["params"]["key"] == "k"


def test_gemini_provider_handles_empty_candidates(mocker) -> None:
    fake = mocker.Mock(status_code=200)
    fake.raise_for_status = mocker.Mock()
    fake.json.return_value = {"candidates": []}
    mocker.patch("hermes_api.llm.httpx.post", return_value=fake)

    out = GeminiProvider(api_key="k", model="gemini-2.5-flash").analyze("oi")
    assert out == ""
