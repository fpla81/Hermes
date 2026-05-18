from __future__ import annotations

import httpx
import pytest

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}


def _patch_request(monkeypatch, status_code: int, body: dict) -> list[dict]:
    """Stub httpx.request capturando chamadas e devolvendo body fixo."""
    calls: list[dict] = []

    def fake_request(method: str, url: str, **kwargs: object) -> httpx.Response:
        calls.append({"method": method, "url": url, **kwargs})
        return httpx.Response(status_code=status_code, json=body)

    monkeypatch.setattr(httpx, "request", fake_request)
    return calls


def test_login_start_forwards_to_playwright(client, monkeypatch) -> None:
    calls = _patch_request(
        monkeypatch,
        200,
        {"session_id": "abc", "login_url": "https://x", "profile_dir": "/p", "reused": False},
    )
    resp = client.post("/bemtevi/login/start", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    assert resp.json()["session_id"] == "abc"
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/login/start")


def test_login_complete_includes_session_id(client, monkeypatch) -> None:
    calls = _patch_request(monkeypatch, 200, {"session_id": "abc", "saved_to": "/p"})
    resp = client.post(
        "/bemtevi/login/complete",
        headers=HEADERS,
        json={"session_id": "abc"},
    )
    assert resp.status_code == 200
    assert calls[0]["json"] == {"session_id": "abc"}


def test_login_503_when_playwright_unreachable(client, monkeypatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx, "request", boom)
    resp = client.post("/bemtevi/login/start", headers=HEADERS)
    assert resp.status_code == 503


def test_login_propagates_playwright_error(client, monkeypatch) -> None:
    _patch_request(monkeypatch, 503, {"detail": "no display"})
    resp = client.post("/bemtevi/login/start", headers=HEADERS)
    assert resp.status_code == 503
    assert "no display" in resp.text


@pytest.mark.parametrize("path", ["/bemtevi/login/start", "/bemtevi/login/status"])
def test_login_requires_auth(client, path) -> None:
    resp = client.post(path) if path.endswith("start") else client.get(path)
    assert resp.status_code in (401, 403)
