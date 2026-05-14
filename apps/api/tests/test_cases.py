from __future__ import annotations

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}

VALID = "0001234-56.2023.5.10.0001"


def test_requires_auth(client) -> None:
    r = client.get("/cases")
    assert r.status_code == 401


def test_create_and_list(client) -> None:
    r = client.post("/cases", json={"numero_processo": VALID}, headers=HEADERS)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["numero_processo"] == VALID
    assert body["status"] == "draft"

    r = client.get("/cases", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_isolation_by_user(client) -> None:
    client.post("/cases", json={"numero_processo": VALID}, headers=HEADERS)
    other = {"X-Hermes-Secret": "test-secret", "X-Hermes-User-Id": "user-2"}
    r = client.get("/cases", headers=other)
    assert r.status_code == 200
    assert r.json() == []


def test_validacao_numero_invalido(client) -> None:
    r = client.post("/cases", json={"numero_processo": "abc"}, headers=HEADERS)
    assert r.status_code == 422


def test_capture_enqueues(client, mocker) -> None:
    spy = mocker.patch("hermes_api.routes.cases._enqueue_capture")
    created = client.post(
        "/cases", json={"numero_processo": VALID}, headers=HEADERS
    ).json()
    r = client.post(f"/cases/{created['id']}/capture", headers=HEADERS)
    assert r.status_code == 202
    spy.assert_called_once_with(created["id"])


def test_analyze_requires_capture_first(client, mocker) -> None:
    mocker.patch("hermes_api.routes.cases._enqueue_analyze")
    created = client.post(
        "/cases", json={"numero_processo": VALID}, headers=HEADERS
    ).json()
    r = client.post(f"/cases/{created['id']}/analyze", headers=HEADERS)
    assert r.status_code == 412


def test_get_and_delete(client) -> None:
    created = client.post(
        "/cases", json={"numero_processo": VALID}, headers=HEADERS
    ).json()
    cid = created["id"]
    r = client.get(f"/cases/{cid}", headers=HEADERS)
    assert r.status_code == 200

    r = client.delete(f"/cases/{cid}", headers=HEADERS)
    assert r.status_code == 204

    r = client.get(f"/cases/{cid}", headers=HEADERS)
    assert r.status_code == 404


def test_html_404_before_capture(client) -> None:
    created = client.post(
        "/cases", json={"numero_processo": VALID}, headers=HEADERS
    ).json()
    r = client.get(f"/cases/{created['id']}/html", headers=HEADERS)
    assert r.status_code == 404
