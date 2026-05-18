from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from .config import get_settings


@dataclass
class CapturedDocument:
    titulo: str
    data: str | None = None


@dataclass
class CapturedData:
    numero_processo: str
    captured_at: datetime
    html: str
    documentos: list[CapturedDocument]


class Capturer(Protocol):
    async def capture(self, numero_processo: str) -> CapturedData: ...


class StubCapturer:
    """Captura sintética usada quando BEMTEVI_REAL_CAPTURE não está ligado."""

    async def capture(self, numero_processo: str) -> CapturedData:
        html = (
            f"<html><body><h1>Processo {numero_processo}</h1>"
            "<p>STUB — captura real será portada do hermes-tst.</p>"
            "</body></html>"
        )
        return CapturedData(
            numero_processo=numero_processo,
            captured_at=datetime.now(UTC),
            html=html,
            documentos=[
                CapturedDocument(titulo="Petição inicial (stub)", data="2024-01-15"),
                CapturedDocument(titulo="Contestação (stub)", data="2024-02-10"),
            ],
        )


class PlaywrightCapturer:
    """Captura real: abre chromium com contexto persistente e baixa a página.

    A lógica TST-específica (login Bem-te-vi, navegação, extração de documentos)
    é portada do hermes-tst em uma fase futura. Aqui só fazemos o trabalho
    estrutural: abrir o browser, navegar para a URL de consulta e devolver o
    HTML renderizado.
    """

    def __init__(self, url_template: str, profile_dir: str, headless: bool, nav_timeout_ms: int):
        self.url_template = url_template
        self.profile_dir = profile_dir
        self.headless = headless
        self.nav_timeout_ms = nav_timeout_ms

    async def capture(self, numero_processo: str) -> CapturedData:
        from playwright.async_api import async_playwright

        url = self.url_template.format(numero_processo=numero_processo)
        async with async_playwright() as p:
            ctx = await p.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=self.headless,
            )
            try:
                page = await ctx.new_page()
                await page.goto(url, timeout=self.nav_timeout_ms, wait_until="domcontentloaded")
                html = await page.content()
            finally:
                await ctx.close()
        return CapturedData(
            numero_processo=numero_processo,
            captured_at=datetime.now(UTC),
            html=html,
            documentos=[],
        )


def build_capturer() -> Capturer:
    s = get_settings()
    if s.real_capture and s.lookup_url_template:
        return PlaywrightCapturer(
            url_template=s.lookup_url_template,
            profile_dir=s.profile_dir,
            headless=s.headless,
            nav_timeout_ms=s.nav_timeout_ms,
        )
    return StubCapturer()
