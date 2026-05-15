from __future__ import annotations

from hermes_playwright.extract import extract_pieces

SAMPLE_HTML = """
<html><body>
<table class="pecas">
  <thead><tr><th>Tipo</th><th>Data</th><th>Ações</th></tr></thead>
  <tbody>
    <tr>
      <td>Despacho de Admissibilidade do TRT</td>
      <td>15/03/2024</td>
      <td>
        <a href="/pecas/12345/html">ver</a>
        <a href="/pecas/12345/bin">baixar</a>
      </td>
    </tr>
    <tr>
      <td>Recurso de Revista</td>
      <td>10/01/2024</td>
      <td>
        <a href="/pecas/12300/visualizar">ver</a>
        <a href="/pecas/12300/download.pdf">pdf</a>
      </td>
    </tr>
    <tr>
      <td colspan="3">Linha sem peça — só separador</td>
    </tr>
  </tbody>
</table>
</body></html>
"""


def test_extract_pieces_from_table() -> None:
    pieces = extract_pieces(SAMPLE_HTML)
    assert len(pieces) == 2

    assert pieces[0]["tipo"] == "Despacho de Admissibilidade do TRT"
    assert pieces[0]["data"] == "15/03/2024"
    assert pieces[0]["id"] == "12345"
    assert pieces[0]["html_url"] == "/pecas/12345/html"
    assert pieces[0]["bin_url"] == "/pecas/12345/bin"

    assert pieces[1]["tipo"] == "Recurso de Revista"
    assert pieces[1]["id"] == "12300"
    assert pieces[1]["html_url"] == "/pecas/12300/visualizar"
    assert pieces[1]["bin_url"] == "/pecas/12300/download.pdf"


def test_extract_pieces_empty_when_no_table() -> None:
    assert extract_pieces("<html><body><p>nada</p></body></html>") == []
