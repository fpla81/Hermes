"""Login interativo no Bem-te-vi para popular o profile persistente.

Rodar UMA vez no host (Mac/Linux com display), antes de ligar a captura real
em Docker:

    uv run --no-sync python apps/playwright/scripts/bootstrap_profile.py

Abre o chromium em modo headed, navega para o Bem-te-vi, espera você fazer
login e dar Enter no terminal. As cookies/storage ficam em
``./bem_te_vi_profile`` na raiz do repo (bind-mountado no container playwright).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROFILE_DIR = Path(os.environ.get("BEM_TE_VI_PROFILE_DIR", "./bem_te_vi_profile")).resolve()
LOGIN_URL = os.environ.get("BEMTEVI_LOGIN_URL", "https://bemtevi.tst.jus.br/")


async def main() -> None:
    from playwright.async_api import async_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[bootstrap] perfil em: {PROFILE_DIR}")
    print(f"[bootstrap] navegando para: {LOGIN_URL}")

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
        )
        page = await ctx.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        print("\n[bootstrap] faça login no browser. Quando terminar, volte aqui e tecle Enter.")
        await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        await ctx.close()
    print("[bootstrap] perfil salvo. Pode ligar BEMTEVI_REAL_CAPTURE=1 no .env.")


if __name__ == "__main__":
    asyncio.run(main())
