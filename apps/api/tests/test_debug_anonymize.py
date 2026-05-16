from __future__ import annotations

HEADERS = {
    "X-Hermes-Secret": "test-secret",
    "X-Hermes-User-Id": "user-1",
}


def test_debug_anonymize_regex_only(client) -> None:
    """Sem partes cadastradas, só regex base roda (CPF/CNPJ/etc)."""
    resp = client.post(
        "/debug/anonymize",
        headers=HEADERS,
        json={"text": "CPF 123.456.789-00 e email teste@x.com"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "<CPF_1>" in body["anonymized"]
    assert "<EMAIL_1>" in body["anonymized"]
    assert body["substitutions"] == 2


def test_debug_anonymize_requires_auth(client) -> None:
    resp = client.post("/debug/anonymize", json={"text": "x"})
    assert resp.status_code in (401, 403)


def test_debug_anonymize_with_parties(client) -> None:
    """Substitui nome da parte por placeholder canônico."""
    resp = client.post(
        "/debug/anonymize",
        headers=HEADERS,
        json={
            "text": "O reclamante João Silva e a Empresa XYZ S/A",
            "parties": [
                {"role": "reclamante", "ordinal": 1, "name": "João Silva"},
                {"role": "reclamada", "ordinal": 1, "name": "Empresa XYZ S/A"},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "RECLAMANTE_1" in body["anonymized"]
    assert "RECLAMADA_1" in body["anonymized"]
    assert "João Silva" not in body["anonymized"]
    assert "Empresa XYZ" not in body["anonymized"]
