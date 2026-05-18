"""Cache local da tabela de Recursos de Revista Repetitivos do TST.

Faz scraping da página oficial e persiste em ``temas_repetitivos``.

A página é renderizada por Liferay com WAF agressivo (bloqueia user-agents
genéricos). Usamos httpx com headers de Chrome BR. Se vier 403 (caso o
endpoint pra escapar do WAF mude ou exija JS), retorna lista vazia + log.
Fallback via Playwright fica como TODO.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session as SyncSession

from ..models.tema_repetitivo import TemaRepetitivo
from ..schemas.tema_repetitivo import TemaRepetitivoIn

log = logging.getLogger(__name__)

# A página "tabela-de-recursos-de-revista-repetitivos" é só um índice;
# os temas reais vivem em /recursos-repetitivos/tabela-completa.
TST_URL = "https://www.tst.jus.br/nugep-sp/recursos-repetitivos/tabela-completa"

# Reaproveita headers realistas de um Chrome em PT-BR (passa WAF do Liferay
# em IP residencial brasileiro; em IP de datacenter pode levar 403).
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

_PROCESSO_RE = re.compile(r"(IRR|RR|IRDR)[\s-]+\d[\d.\-/]+", re.IGNORECASE)


def _classify_situacao(suspensao_cell: str, movimento_cell: str) -> str:
    """Mapeia colunas 'Há Decisão de Suspensão?' e 'Último Movimento' para
    o nosso enum lógico (``suspenso`` / ``decidido`` / ``julgado`` / ``outro``).
    """
    suspensao = suspensao_cell.lower()
    movimento = movimento_cell.lower()
    if "sim" in suspensao:
        return "suspenso"
    if "transitado em julgado" in movimento or "tese firmada" in movimento:
        return "decidido"
    if "julgad" in movimento or "acórdão" in movimento or "acordao" in movimento:
        return "decidido"
    if "publicad" in movimento:
        return "decidido"
    return "outro"


def parse_repetitivos_html(html: str) -> list[TemaRepetitivoIn]:
    """Parseia a /recursos-repetitivos/tabela-completa.

    Layout esperado (6 colunas):
      0: Tema (número, ex.: "1", "2")
      1: Representativo(s) da Controvérsia
      2: Tese/Questão Jurídica
      3: Último Movimento
      4: Há Decisão de Suspensão?
      5: Relator(a)

    Estratégia tolerante a rowspan/colspan: para cada <tr> com 6 ou mais
    células onde a primeira tem dígito puro, considera início de um tema.
    Linhas subsequentes (continuação) são ignoradas — a estrutura agrega
    multilinhas no mesmo <tr> em geral.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: dict[int, TemaRepetitivoIn] = {}

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 6:
                continue
            num_text = cells[0].get_text(" ", strip=True).strip()
            # primeira célula deve ser número puro do tema
            if not num_text.isdigit():
                continue
            try:
                numero = int(num_text)
            except ValueError:
                continue
            if numero in items:
                continue

            representativos = cells[1].get_text(" ", strip=True)
            tese_text = cells[2].get_text(" ", strip=True)
            movimento = cells[3].get_text(" ", strip=True) if len(cells) > 3 else ""
            suspensao = cells[4].get_text(" ", strip=True) if len(cells) > 4 else ""

            situacao = _classify_situacao(suspensao, movimento)
            descricao = tese_text or representativos or f"Tema {numero}"
            tese = tese_text if situacao == "decidido" and tese_text else None

            # link: primeiro <a href> da célula de representativos
            link = None
            for a in cells[1].find_all("a", href=True):
                href = a.get("href")
                if href and href.startswith(("http://", "https://")):
                    link = href
                    break

            try:
                items[numero] = TemaRepetitivoIn(
                    numero=numero,
                    descricao=descricao[:5000],
                    situacao=situacao,
                    tese=tese[:5000] if tese else None,
                    link=link,
                )
            except Exception:  # noqa: BLE001
                continue

    return list(items.values())


def fetch_repetitivos_table(timeout: float = 30.0) -> list[TemaRepetitivoIn]:
    """Baixa o HTML do TST e devolve a lista parseada.

    Estratégia em 2 tentativas:
      1) httpx direto com headers de Chrome BR — barato e rápido. Funciona
         quando a página é estática (o que NÃO é o caso atual do TST: a
         tabela é renderizada por React/Liferay client-side).
      2) Fallback via serviço Playwright (``PLAYWRIGHT_SERVICE_URL``), que
         abre Chromium headless e devolve o DOM pós-JS.

    Em qualquer falha, loga e devolve lista vazia.
    """
    # tenta httpx primeiro
    html = ""
    try:
        with httpx.Client(headers=_HEADERS, timeout=timeout, follow_redirects=True) as c:
            res = c.get(TST_URL)
        if res.status_code == 200:
            html = res.text
        else:
            log.warning(
                "fetch_repetitivos_table httpx: HTTP %s ao baixar %s",
                res.status_code,
                TST_URL,
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("fetch_repetitivos_table httpx falhou: %s", exc)

    items = parse_repetitivos_html(html) if html else []
    if items:
        return items

    # fallback Playwright se nenhum tema foi extraído
    pw_html = _fetch_via_playwright()
    if not pw_html:
        return []
    return parse_repetitivos_html(pw_html)


def _fetch_via_playwright() -> str:
    """Chama o microserviço hermes-playwright pra renderizar o JS."""
    from os import getenv

    base = getenv("PLAYWRIGHT_SERVICE_URL", "http://playwright:8001").rstrip("/")
    try:
        with httpx.Client(timeout=120.0) as c:
            r = c.post(
                f"{base}/render",
                json={"url": TST_URL, "wait_until": "networkidle", "timeout_ms": 60000},
            )
        if r.status_code != 200:
            log.warning(
                "fetch_repetitivos_table playwright: HTTP %s — body: %s",
                r.status_code,
                r.text[:300],
            )
            return ""
        data = r.json()
        return str(data.get("html") or "")
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "fetch_repetitivos_table playwright: erro ao chamar %s/render: %s",
            base,
            exc,
        )
        return ""


def upsert_repetitivos(db: SyncSession, items: list[TemaRepetitivoIn]) -> dict[str, int]:
    """Insere os novos / atualiza os existentes (por ``numero``).

    Não apaga itens que sumiram da fonte (estabilidade histórica).
    Devolve ``{"created": N, "updated": M}``.
    """
    created = 0
    updated = 0
    now = datetime.now(UTC)
    for item in items:
        row = (
            db.query(TemaRepetitivo)
            .filter(TemaRepetitivo.numero == item.numero)
            .one_or_none()
        )
        if row is None:
            row = TemaRepetitivo(
                numero=item.numero,
                descricao=item.descricao,
                situacao=item.situacao,
                tese=item.tese,
                link=item.link,
                fetched_at=now,
            )
            db.add(row)
            created += 1
        else:
            row.descricao = item.descricao
            row.situacao = item.situacao
            row.tese = item.tese
            row.link = item.link
            row.fetched_at = now
            updated += 1
    db.commit()
    return {"created": created, "updated": updated}


def refresh_now(db: SyncSession) -> dict[str, int]:
    items = fetch_repetitivos_table()
    if not items:
        return {"created": 0, "updated": 0, "fetched": 0}
    stats = upsert_repetitivos(db, items)
    stats["fetched"] = len(items)
    return stats
