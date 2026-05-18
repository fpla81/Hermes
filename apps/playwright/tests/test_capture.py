from datetime import UTC, datetime

from fastapi.testclient import TestClient
from hermes_playwright.capture import CapturedData
from hermes_playwright.main import app, get_capturer

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


def test_capture_with_overridden_capturer() -> None:
    class FakeCapturer:
        async def capture(self, numero_processo: str) -> CapturedData:
            return CapturedData(
                numero_processo=numero_processo,
                captured_at=datetime.now(UTC),
                html="<html>fake</html>",
                documentos=[],
            )

    app.dependency_overrides[get_capturer] = lambda: FakeCapturer()
    try:
        r = client.post(
            "/capture", json={"numero_processo": "0001234-56.2023.5.10.0001"}
        )
        assert r.status_code == 200
        assert r.json()["html"] == "<html>fake</html>"
    finally:
        app.dependency_overrides.clear()
