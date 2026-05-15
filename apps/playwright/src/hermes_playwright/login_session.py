"""Sessão de login interativa para popular o profile persistente do Bem-te-vi.

A ideia: o usuário clica um botão no web app, o backend chama
``POST /login/start`` aqui; abrimos um Chromium **headed** com
``launch_persistent_context`` apontando para o mesmo ``profile_dir`` que a
captura usa. O usuário faz login no navegador que abre. Quando termina,
clica "Concluído" no web app, que chama ``POST /login/complete``.

Como ``launch_persistent_context`` salva cookies/storage no diretório do
profile ao fechar o contexto, basta fechar para persistir.

Requer um ambiente com display (Mac/Linux com tela). Em container headless,
o ``chromium.launch`` falha com erro claro de DISPLAY ausente; devolvemos
503 com mensagem útil.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .config import get_settings


@dataclass
class LoginSession:
    session_id: str
    started_at: datetime
    playwright: Any
    context: Any
    profile_dir: str


_SESSIONS: dict[str, LoginSession] = {}
_LOCK = asyncio.Lock()


async def start_login() -> dict[str, Any]:
    """Abre Chromium headed apontando para a URL de login. Não bloqueia.

    Devolve ``{session_id, login_url, profile_dir}``. O contexto fica aberto
    até ``complete_login`` ser chamado (ou expirar via cleanup futuro).
    """
    settings = get_settings()
    async with _LOCK:
        if _SESSIONS:
            existing = next(iter(_SESSIONS.values()))
            return {
                "session_id": existing.session_id,
                "login_url": settings.login_url,
                "profile_dir": existing.profile_dir,
                "reused": True,
            }

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - dependência sempre presente
        raise RuntimeError(f"playwright não instalado: {exc}") from exc

    pw = await async_playwright().start()
    try:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=settings.profile_dir,
            headless=False,
        )
    except Exception as exc:  # noqa: BLE001
        await pw.stop()
        raise RuntimeError(
            "não foi possível abrir o Chromium headed — verifique se há display "
            f"disponível na máquina onde o playwright service está rodando: {exc}"
        ) from exc

    page = context.pages[0] if context.pages else await context.new_page()
    try:
        await page.goto(settings.login_url, wait_until="domcontentloaded", timeout=settings.nav_timeout_ms)
    except Exception:
        # falhar a navegação não interrompe o fluxo — o usuário pode digitar a URL
        pass

    sid = secrets.token_urlsafe(16)
    session = LoginSession(
        session_id=sid,
        started_at=datetime.now(UTC),
        playwright=pw,
        context=context,
        profile_dir=settings.profile_dir,
    )
    async with _LOCK:
        _SESSIONS[sid] = session

    return {
        "session_id": sid,
        "login_url": settings.login_url,
        "profile_dir": settings.profile_dir,
        "reused": False,
    }


async def complete_login(session_id: str) -> dict[str, Any]:
    """Fecha o contexto persistente (auto-salva cookies) e descarta a sessão."""
    async with _LOCK:
        session = _SESSIONS.pop(session_id, None)
    if session is None:
        raise KeyError(session_id)
    try:
        await session.context.close()
    finally:
        await session.playwright.stop()
    return {"session_id": session_id, "saved_to": session.profile_dir}


async def cancel_login(session_id: str) -> None:
    """Fecha o contexto sem promessa de salvar (Chromium escreve no profile_dir igual)."""
    async with _LOCK:
        session = _SESSIONS.pop(session_id, None)
    if session is None:
        return
    try:
        await session.context.close()
    finally:
        await session.playwright.stop()


def list_sessions() -> list[dict[str, Any]]:
    return [
        {"session_id": s.session_id, "started_at": s.started_at.isoformat(), "profile_dir": s.profile_dir}
        for s in _SESSIONS.values()
    ]
