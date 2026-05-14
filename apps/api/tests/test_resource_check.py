from __future__ import annotations

from hermes_api.services.resource_check import PreparedPiece, validate_resources


def _manifest_with_rr(piece_id: str = "12345") -> dict:
    return {
        "rr_candidates_requires_legal_selection": [
            {"tipo": "Recurso de Revista", "data": "10/01/2024", "id": piece_id}
        ],
        "later_agravos_candidates": [],
    }


def test_validate_ok_when_text_is_long_enough() -> None:
    long_text = ("Este é o teor do recurso de revista. " * 80).encode("utf-8")
    prepared = [PreparedPiece(filename="recurso_12345.txt", content=long_text, piece_id="12345")]
    result = validate_resources(_manifest_with_rr(), prepared)
    assert result["status"] == "ok"
    assert result["resources_checked"] == 1
    assert result["resources_failed"] == 0
    assert result["alert_text"] == ""


def test_validate_fails_when_file_missing() -> None:
    result = validate_resources(_manifest_with_rr(), [])
    assert result["status"] == "fail"
    assert result["resources_failed"] == 1
    assert "arquivo preparado não localizado" in result["resources"][0]["reasons"][0]
    assert "ALERTA" in result["alert_text"]


def test_validate_fails_on_sso_marker() -> None:
    content = ("Central Authentication Service " * 30).encode("utf-8")
    prepared = [PreparedPiece(filename="recurso_12345.txt", content=content, piece_id="12345")]
    result = validate_resources(_manifest_with_rr(), prepared)
    assert result["status"] == "fail"
    reasons = result["resources"][0]["reasons"]
    assert any("marcador" in r for r in reasons)


def test_match_by_tipo_when_no_id() -> None:
    long_text = ("Conteúdo do recurso. " * 80).encode("utf-8")
    manifest = {
        "rr_candidates_requires_legal_selection": [{"tipo": "Recurso de Revista"}],
        "later_agravos_candidates": [],
    }
    prepared = [PreparedPiece(filename="recurso-de-revista-reclamante.txt", content=long_text)]
    result = validate_resources(manifest, prepared)
    assert result["status"] == "ok"
