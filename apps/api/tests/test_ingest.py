from __future__ import annotations

from hermes_api.services.tokens import make_token

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}

SAMPLE_HTML = """
<html><body>
<table>
  <tr><th>Tipo</th><th>Data</th></tr>
  <tr>
    <td>Despacho de Admissibilidade do TRT</td>
    <td>15/03/2024</td>
    <td><a href="/pecas/100/html">ver</a></td>
  </tr>
</table>
</body></html>
"""


def test_token_endpoint_requires_session(client) -> None:
    resp = client.get("/me/ingest-token")
    assert resp.status_code in (401, 403)


def test_token_endpoint_returns_token(client) -> None:
    resp = client.get("/me/ingest-token", headers=HEADERS)
    assert resp.status_code == 200
    token = resp.json()["token"]
    assert "." in token  # formato user_id_b64.signature


def test_ingest_creates_case(client) -> None:
    token = make_token("user-1")
    resp = client.post(
        "/cases/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "numero_processo": "0001234-56.2023.5.06.0020",
            "html": SAMPLE_HTML,
            "url": "https://bemtevi.tst.jus.br/report/processo/0001234-56.2023.5.06.0020",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] is True
    assert body["pieces_found"] == 1
    case_id = body["case_id"]

    # confirma que o caso ficou no banco do usuário
    get = client.get(f"/cases/{case_id}", headers=HEADERS)
    assert get.status_code == 200
    assert get.json()["status"] == "captured"


def test_ingest_updates_existing_case(client) -> None:
    # cria o caso via API normal
    resp = client.post(
        "/cases",
        headers=HEADERS,
        json={"numero_processo": "0001234-56.2023.5.06.0020"},
    )
    assert resp.status_code == 201
    case_id = resp.json()["id"]

    token = make_token("user-1")
    resp = client.post(
        "/cases/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"numero_processo": "0001234-56.2023.5.06.0020", "html": SAMPLE_HTML},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] is False
    assert body["case_id"] == case_id


def test_ingest_rejects_missing_token(client) -> None:
    resp = client.post(
        "/cases/ingest",
        json={"numero_processo": "0001234-56.2023.5.06.0020", "html": "<p>x</p>"},
    )
    assert resp.status_code == 401


def test_ingest_rejects_invalid_token(client) -> None:
    resp = client.post(
        "/cases/ingest",
        headers={"Authorization": "Bearer garbage.signature"},
        json={"numero_processo": "0001234-56.2023.5.06.0020", "html": "<p>x</p>"},
    )
    assert resp.status_code == 401


def test_ingest_accepts_internal_session(client) -> None:
    """Web→api passa X-Hermes-Secret + X-Hermes-User-Id em vez de Bearer."""
    resp = client.post(
        "/cases/ingest",
        headers=HEADERS,
        json={"numero_processo": "0001234-56.2023.5.06.0020", "html": SAMPLE_HTML},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] is True


def test_ingest_rejects_bad_cnj(client) -> None:
    token = make_token("user-1")
    resp = client.post(
        "/cases/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"numero_processo": "12345", "html": "<p>x</p>"},
    )
    assert resp.status_code == 422
