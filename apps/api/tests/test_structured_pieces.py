from __future__ import annotations

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}


def _create_case(client) -> str:
    resp = client.post(
        "/cases",
        headers=HEADERS,
        json={"numero_processo": "0001234-56.2023.5.06.0020", "titulo": "Teste"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_add_recurso_de_revista_piece(client) -> None:
    case_id = _create_case(client)
    resp = client.post(
        f"/cases/{case_id}/structured-pieces",
        headers=HEADERS,
        json={
            "tipo": "recurso_revista",
            "parte": "reclamada",
            "data": "10/01/2024",
            "text": "Texto integral do recurso.",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tipo"] == "recurso_revista"
    assert body["parte"] == "reclamada"
    assert body["blueprint"] is None  # blueprint só pro despacho


def test_add_despacho_runs_parser_stub_note(client) -> None:
    case_id = _create_case(client)
    resp = client.post(
        f"/cases/{case_id}/structured-pieces",
        headers=HEADERS,
        json={
            "tipo": "despacho_admissibilidade",
            "data": "15/03/2024",
            "text": "DESPACHO DE ADMISSIBILIDADE...",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["blueprint"] is not None
    # sem GEMINI_API_KEY, blueprint tem note de stub
    assert body["blueprint"]["recursos"] == []
    assert "GEMINI_API_KEY" in body["blueprint"].get("note", "")


def test_list_and_delete_pieces(client) -> None:
    case_id = _create_case(client)
    add = client.post(
        f"/cases/{case_id}/structured-pieces",
        headers=HEADERS,
        json={"tipo": "agravo_interno", "parte": "reclamante", "text": "x"},
    )
    piece_id = add.json()["id"]

    listing = client.get(f"/cases/{case_id}/structured-pieces", headers=HEADERS)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    delete = client.delete(
        f"/cases/{case_id}/structured-pieces/{piece_id}",
        headers=HEADERS,
    )
    assert delete.status_code == 204

    listing2 = client.get(f"/cases/{case_id}/structured-pieces", headers=HEADERS)
    assert listing2.json() == []


def test_delete_nonexistent_piece_returns_404(client) -> None:
    case_id = _create_case(client)
    resp = client.delete(
        f"/cases/{case_id}/structured-pieces/does-not-exist",
        headers=HEADERS,
    )
    assert resp.status_code == 404
