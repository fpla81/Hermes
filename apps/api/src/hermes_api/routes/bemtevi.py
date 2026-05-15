"""Proxy autenticado entre o web e o playwright service para o fluxo de login.

O web app não fala diretamente com o playwright service — vai sempre pela
API. Esses endpoints exigem ``current_user_id`` e repassam pra
``settings.playwright_service_url``.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import current_user_id
from ..config import get_settings

router = APIRouter(prefix="/bemtevi", tags=["bemtevi"])


class LoginCompletePayload(BaseModel):
    session_id: str


def _playwright_url() -> str:
    return get_settings().playwright_service_url.rstrip("/")


def _forward(method: str, path: str, json: dict | None = None) -> dict:
    url = f"{_playwright_url()}{path}"
    try:
        resp = httpx.request(method, url, json=json, timeout=30.0)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"playwright service indisponível em {url}: {exc}",
        ) from exc
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.post("/login/start")
def login_start(_: str = Depends(current_user_id)) -> dict:
    return _forward("POST", "/login/start")


@router.post("/login/complete")
def login_complete(
    payload: LoginCompletePayload,
    _: str = Depends(current_user_id),
) -> dict:
    return _forward("POST", "/login/complete", json={"session_id": payload.session_id})


@router.post("/login/cancel")
def login_cancel(
    payload: LoginCompletePayload,
    _: str = Depends(current_user_id),
) -> dict:
    return _forward("POST", "/login/cancel", json={"session_id": payload.session_id})


@router.get("/login/status")
def login_status(_: str = Depends(current_user_id)) -> dict:
    return _forward("GET", "/login/status")
