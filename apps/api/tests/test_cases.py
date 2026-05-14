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
