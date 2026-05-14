from fastapi.testclient import TestClient
from hermes_playwright.main import app

client = TestClient(app)


def test_capture_stub_ok() -> None:
    r = client.post("/capture", json={"numero_processo": "0001234-56.2023.5.10.0001"})
    assert r.status_code == 200
    body = r.json()
    assert body["numero_processo"] == "0001234-56.2023.5.10.0001"
    assert "STUB" in body["html"]
    assert len(body["documentos"]) >= 1


def test_capture_invalid_numero() -> None:
    r = client.post("/capture", json={"numero_processo": "abc"})
    assert r.status_code == 422
