from __future__ import annotations

from hermes_api.services.analysis_packets import build_packets
from hermes_api.services.resource_check import PreparedPiece


def test_short_text_yields_single_packet() -> None:
    manifest = {
        "rr_candidates_requires_legal_selection": [
            {"tipo": "Recurso de Revista", "id": "1"},
        ],
    }
    prepared = [PreparedPiece(filename="recurso_1.txt", content=b"texto curto.", piece_id="1")]
    packets, index = build_packets(manifest, prepared, max_chars=1000)
    assert len(packets) == 1
    assert index["packet_count"] == 1
    assert packets[0]["packet_id"] == "S001-P001"
    assert packets[0]["role"] == "recurso_de_revista"


def test_long_text_is_split_with_overlap() -> None:
    body = ". ".join(f"frase numero {i:03d}" for i in range(2000))
    manifest = {"rr_candidates_requires_legal_selection": [{"tipo": "Recurso de Revista", "id": "1"}]}
    prepared = [PreparedPiece(filename="recurso_1.txt", content=body.encode("utf-8"), piece_id="1")]
    packets, index = build_packets(manifest, prepared, max_chars=1000, overlap_chars=100)
    assert len(packets) > 1
    assert all(p["source_id"] == "S001" for p in packets)
    assert index["sources"][0]["packet_count"] == len(packets)


def test_include_all_prepared_adds_unmatched_pieces() -> None:
    manifest = {"rr_candidates_requires_legal_selection": []}
    prepared = [PreparedPiece(filename="extra.txt", content=b"conteudo apoio." * 20)]
    packets, index = build_packets(manifest, prepared, include_all_prepared=True)
    assert len(packets) == 1
    assert packets[0]["role"] == "apoio"
