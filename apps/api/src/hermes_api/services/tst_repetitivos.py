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

TST_URL = (
    "https://www.tst.jus.br/nugep-sp/tabela-de-recursos-de-revista-repetitivos"
)

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

_NUMERO_RE = re.compile(r"\bTema\s+(?:n[º°.]\s*)?(\d{1,4})\b", re.IGNORECASE)


def _classify_situacao(text: str) -> str:
    """Heurística simples: o texto adjacente ao tema sinaliza a situação."""
    lower = text.lower()
    if "suspens" in lower:
        return "suspenso"
    if "tese firmada" in lower or "tese fixada" in lower or "decidido" in lower:
        return "decidido"
    if "julgad" in lower:
        return "julgado"
    return "outro"


def _extract_tese(text: str) -> str | None:
    """Procura trecho após 'Tese firmada:' / 'Tese:' até ponto final/quebra."""
    for marker in ("Tese firmada:", "Tese fixada:", "Tese:"):
        idx = text.find(marker)
        if idx >= 0:
            after = text[idx + len(marker):].strip()
            # corta na primeira quebra dupla ou ~600 chars
            stop = after.find("\n\n")
            if stop < 0:
                stop = min(len(after), 800)
            tese = after[:stop].strip()
            if tese:
                return tese
    return None


def parse_repetitivos_html(html: str) -> list[TemaRepetitivoIn]:
    """Parser tolerante: varre blocos de texto procurando 'Tema NNN'.

    O DOM exato pode variar (Liferay). A estratégia é: pegar cada elemento
    textual que contenha 'Tema NNN' e tratar o conteúdo do bloco pai como
    a descrição + situação + tese.
    """
    soup = BeautifulSoup(html, "html.parser")
    items: dict[int, TemaRepetitivoIn] = {}

    # Itera por elementos com texto significativo (parágrafos, list-items,
    # cells, divs com pouco aninhamento). Para cada um, vê se cabeçalho
    # ou início traz "Tema NNN".
    for node in soup.select("p, li, td, div, h2, h3, h4"):
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        m = _NUMERO_RE.search(text)
        if not m:
            continue
        try:
            numero = int(m.group(1))
        except ValueError:
            continue
        if numero in items:
            continue  # primeira ocorrência ganha
        # Junta o contexto: o próprio nó + irmãos seguintes até o próximo
        # "Tema NNN" — pra capturar situação e tese que costumam vir
        # em parágrafos adjacentes.
        context_chunks = [text]
        sib = node.find_next_sibling()
        steps = 0
        while sib is not None and steps < 4:
            sib_text = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else ""
            if sib_text and _NUMERO_RE.search(sib_text):
                break
            if sib_text:
                context_chunks.append(sib_text)
            sib = sib.find_next_sibling()
            steps += 1
        context = " \n".join(context_chunks)

        # descrição = trecho após "Tema NNN" e antes de "Situação"/"Tese"
        desc_after = _NUMERO_RE.split(context, maxsplit=1)
        # split com grupo: [pre, numero, post]
        desc_raw = desc_after[-1] if len(desc_after) >= 2 else context
        # corta na palavra Situação/Tese se aparecer
        cut_at = min(
            (
                desc_raw.find(token)
                for token in ("Situação", "Status", "Tese firmada", "Tese fixada", "Tese:")
                if desc_raw.find(token) >= 0
            ),
            default=len(desc_raw),
        )
        descricao = desc_raw[:cut_at].strip(" -:–—\n\t")
        if not descricao:
            descricao = text  # fallback: linha inteira

        situacao = _classify_situacao(context)
        tese = _extract_tese(context) if situacao == "decidido" else None

        link = None
        a = node.find("a", href=True) if hasattr(node, "find") else None
        if a is not None:
            href = a.get("href")
            if href and href.startswith(("http://", "https://")):
                link = href

        try:
            items[numero] = TemaRepetitivoIn(
                numero=numero,
                descricao=descricao[:5000],
                situacao=situacao,
                tese=tese,
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
