"""Ponta-a-ponta da Fase B: pieces → manifest → prepared → validate → packets → minuta → docx.

Celery não roda: a rota /packets e /docx só enfileiram. Os testes chamam as
funções das tasks diretamente para exercitar o lado worker contra o mesmo DB
in-memory.
"""

from __future__ import annotations

import io

import pytest
from docx import Document

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}


@pytest.fixture
def case_id(client) -> str:
    resp = client.post(
        "/cases",
        headers=HEADERS,
        json={"numero_processo": "0001234-56.2023.5.06.0020", "titulo": "Teste"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_pieces_and_manifest(client, case_id) -> None:
    pieces = {
        "pieces": [
            {"tipo": "Despacho de Admissibilidade do TRT", "data": "15/03/2024"},
            {"tipo": "Recurso de Revista", "data": "10/01/2024", "local_path": "rr.txt"},
            {"tipo": "Agravo de Instrumento em Recurso de Revista", "data": "01/04/2024", "local_path": "agravo.txt"},
        ]
    }
    resp = client.post(f"/cases/{case_id}/pieces", headers=HEADERS, json=pieces)
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/cases/{case_id}/manifest", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_manifest"] is True
    assert body["status"] == "preparing"


def test_manifest_requires_pieces(client, case_id) -> None:
    resp = client.post(f"/cases/{case_id}/manifest", headers=HEADERS)
    assert resp.status_code == 412


def test_prepared_upload_list_delete(client, case_id, fake_storage) -> None:
    # upload
    resp = client.post(
        f"/cases/{case_id}/prepared",
        headers=HEADERS,
        files={"file": ("recurso.txt", b"conteudo do recurso", "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"filenames": ["recurso.txt"]}
    assert fake_storage.objects[f"cases/{case_id}/prepared/recurso.txt"] == b"conteudo do recurso"

    # list
    resp = client.get(f"/cases/{case_id}/prepared", headers=HEADERS)
    assert resp.json() == {"filenames": ["recurso.txt"]}

    # delete
    resp = client.delete(f"/cases/{case_id}/prepared/recurso.txt", headers=HEADERS)
    assert resp.status_code == 204
    assert f"cases/{case_id}/prepared/recurso.txt" not in fake_storage.objects


def test_validate_resources_flow(client, case_id, fake_storage) -> None:
    long_text = ("Texto extenso do recurso de revista. " * 100).encode("utf-8")
    client.post(
        f"/cases/{case_id}/pieces",
        headers=HEADERS,
        json={"pieces": [
            {"tipo": "Recurso de Revista", "id": "9001", "local_path": "rr.txt"},
        ]},
    )
    client.post(f"/cases/{case_id}/manifest", headers=HEADERS)
    client.post(
        f"/cases/{case_id}/prepared",
        headers=HEADERS,
        files={"file": ("rr.txt", long_text, "text/plain")},
    )
    resp = client.post(f"/cases/{case_id}/validate-resources", headers=HEADERS)
    assert resp.status_code == 200, resp.text


def test_packets_service_renders_via_storage(client, case_id, fake_storage) -> None:
    """As tasks Celery usam SyncSessionLocal (Postgres). Aqui exercitamos os
    serviços que elas chamam — ``load_prepared_pieces`` + ``build_packets`` +
    ``render_docx`` — usando o FakeStorage, garantindo que o adapter S3 e a
    pipeline encadeada produzem packets e docx coerentes."""
    from hermes_api.services.analysis_packets import build_packets
    from hermes_api.services.docx import render_docx
    from hermes_api.services.manifest import build_manifest
    from hermes_api.services.prepared import load_prepared_pieces

    pieces_payload = [{"tipo": "Recurso de Revista", "id": "9001", "local_path": "rr.txt"}]
    long_text = ("Conteúdo do recurso de revista para gerar packets úteis. " * 200).encode("utf-8")
    client.post(f"/cases/{case_id}/pieces", headers=HEADERS, json={"pieces": pieces_payload})
    client.post(f"/cases/{case_id}/manifest", headers=HEADERS)
    client.post(
        f"/cases/{case_id}/prepared",
        headers=HEADERS,
        files={"file": ("rr.txt", long_text, "text/plain")},
    )

    manifest = build_manifest(pieces_payload, process_number="0001234-56.2023.5.06.0020")
    prepared = load_prepared_pieces(fake_storage, case_id, pieces_payload)
    packets, index = build_packets(manifest, prepared)
    assert len(packets) >= 1
    assert index["packet_count"] == len(packets)
    assert prepared[0].piece_id == "9001"

    minuta = "[[CORPO]]\nRECURSO DE REVISTA DA RECLAMADA\n\nConheço do recurso e dou provimento.\n"
    resp = client.post(f"/cases/{case_id}/minuta", headers=HEADERS, json={"text": minuta})
    assert resp.status_code == 200
    assert resp.json()["has_minuta"] is True

    blob = render_docx(minuta)
    doc = Document(io.BytesIO(blob))
    assert any("Conheço do recurso" in p.text for p in doc.paragraphs)


def test_docx_requires_minuta(client, case_id) -> None:
    resp = client.post(f"/cases/{case_id}/docx", headers=HEADERS)
    assert resp.status_code == 412


def test_packets_requires_manifest(client, case_id) -> None:
    resp = client.post(f"/cases/{case_id}/packets", headers=HEADERS)
    assert resp.status_code == 412


def test_get_docx_404_when_missing(client, case_id, fake_storage) -> None:
    resp = client.get(f"/cases/{case_id}/docx", headers=HEADERS)
    assert resp.status_code == 404
