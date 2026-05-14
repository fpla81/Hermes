from __future__ import annotations

from hermes_api.services.manifest import build_manifest, normalize_process_number, slugify


def test_normalize_process_number_pads_to_seven_digits() -> None:
    assert normalize_process_number("1234-56.2023.5.06.0020") == "0001234-56.2023.5.06.0020"
    assert normalize_process_number("0001234-56.2023.5.06.0020") == "0001234-56.2023.5.06.0020"


def test_slugify_ascii() -> None:
    assert slugify("Texto Fornecido") == "texto-fornecido"
    assert slugify("") == "textos-fornecidos"


def test_build_manifest_picks_latest_dispatch_and_later_agravo() -> None:
    pieces = [
        {"tipo": "Despacho de Admissibilidade do TRT", "data": "01/02/2024"},
        {"tipo": "Despacho de Admissibilidade do TRT", "data": "15/03/2024"},
        {"tipo": "Recurso de Revista", "data": "10/01/2024"},
        {"tipo": "Agravo de Instrumento em Recurso de Revista", "data": "01/04/2024"},
        {"tipo": "Agravo de Instrumento em Recurso de Revista", "data": "01/01/2024"},
        {"tipo": "Petição", "data": "05/05/2024"},
    ]
    manifest = build_manifest(pieces, process_number="0001234-56.2023.5.06.0020")

    assert manifest["process_number"] == "0001234-56.2023.5.06.0020"
    assert manifest["dispatch_anchor"]["data"] == "15/03/2024"
    assert len(manifest["rr_candidates_requires_legal_selection"]) == 1
    # later_agravo só posterior ao âncora (15/03/2024)
    laters = manifest["later_agravos_candidates"]
    assert len(laters) == 1
    assert laters[0]["data"] == "01/04/2024"


def test_build_manifest_without_dispatch_keeps_all_agravos() -> None:
    pieces = [
        {"tipo": "Recurso de Revista"},
        {"tipo": "Agravo de Instrumento"},
    ]
    manifest = build_manifest(pieces, case_slug="textos-fornecidos")
    assert manifest["dispatch_anchor"] is None
    assert manifest["case_slug"] == "textos-fornecidos"
    assert len(manifest["later_agravos_candidates"]) == 1
