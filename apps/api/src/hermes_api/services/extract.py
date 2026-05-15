"""Extração da tabela de peças do Bem-te-vi a partir do HTML capturado.

A página "Peças" do Bem-te-vi (rota interna ``/report/processo/{numero}``) usa
uma tabela HTML com linhas representando cada peça. Cada linha tem, em geral:
  - texto da coluna ``Tipo`` (e.g. "Despacho de Admissibilidade do TRT")
  - texto da coluna ``Data`` em ``dd/mm/yyyy``
  - um link visual com URL ``/pecas/{id}/html`` (ou similar)
  - um link de download com URL ``/pecas/{id}/bin``

Aqui parseamos heuristicamente, sem depender de seletor único: pegamos todas
as ``<tr>`` que tenham ao menos um link batendo em ``/pecas/<digits>/`` e
extraímos ``tipo`` (primeira célula com texto não-vazio que não seja data) +
``data`` (primeira célula em formato BR) + ``html_url`` + ``bin_url``.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

_DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_PIECE_URL_RE = re.compile(r"(/pecas/\d+/[^\"'\s]*)", re.IGNORECASE)
_PIECE_ID_RE = re.compile(r"/pecas/(\d+)/", re.IGNORECASE)


class _RowExtractor(HTMLParser):
    """Coleta linhas <tr> como (cell_texts, links).

    Ignora <thead> e <script>/<style>.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[list[str], list[str]]] = []
        self._in_row = False
        self._in_cell = False
        self._in_head = 0
        self._skip = 0
        self._current_cells: list[str] = []
        self._current_links: list[str] = []
        self._cell_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
            return
        if tag == "thead":
            self._in_head += 1
            return
        if tag == "tr" and not self._in_head:
            self._in_row = True
            self._current_cells = []
            self._current_links = []
            return
        if tag in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._cell_buf = []
            return
        if tag == "a" and self._in_row:
            href = next((v for k, v in attrs if k.lower() == "href" and v), None)
            if href:
                self._current_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
            return
        if tag == "thead" and self._in_head:
            self._in_head -= 1
            return
        if tag in {"td", "th"} and self._in_cell:
            text = " ".join("".join(self._cell_buf).split()).strip()
            self._current_cells.append(text)
            self._in_cell = False
            self._cell_buf = []
            return
        if tag == "tr" and self._in_row:
            self.rows.append((self._current_cells, self._current_links))
            self._in_row = False
            self._current_cells = []
            self._current_links = []

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_cell:
            self._cell_buf.append(data)


def extract_pieces(html: str) -> list[dict[str, Any]]:
    """Devolve a lista de peças extraídas da tabela.

    Cada item: ``{"tipo", "data", "id", "html_url", "bin_url"}``. Linhas sem
    link para ``/pecas/...`` são descartadas (header, rodapé, separadores).
    """
    parser = _RowExtractor()
    parser.feed(html)

    pieces: list[dict[str, Any]] = []
    for cells, links in parser.rows:
        piece_links = [h for h in links if _PIECE_ID_RE.search(h)]
        if not piece_links:
            continue
        piece_id = None
        html_url = None
        bin_url = None
        for href in piece_links:
            match = _PIECE_ID_RE.search(href)
            if match and piece_id is None:
                piece_id = match.group(1)
            lower = href.lower()
            if html_url is None and ("html" in lower or "view" in lower or "visualizar" in lower):
                html_url = href
            elif bin_url is None and ("bin" in lower or "download" in lower or "pdf" in lower):
                bin_url = href
        if html_url is None and piece_links:
            html_url = piece_links[0]

        data = None
        for cell in cells:
            m = _DATE_RE.search(cell)
            if m:
                data = m.group(1)
                break

        tipo = None
        for cell in cells:
            stripped = cell.strip()
            if not stripped or _DATE_RE.fullmatch(stripped) or _PIECE_ID_RE.search(stripped):
                continue
            # ignora células que são apenas labels curtos (botões "ver", "baixar")
            if len(stripped) < 3 or stripped.lower() in {"ver", "baixar", "abrir", "download"}:
                continue
            tipo = stripped
            break

        pieces.append({
            "tipo": tipo,
            "data": data,
            "id": piece_id,
            "html_url": html_url,
            "bin_url": bin_url,
        })

    return pieces
