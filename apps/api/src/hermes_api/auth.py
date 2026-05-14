from fastapi import Header, HTTPException, status

from .config import get_settings


async def current_user_id(
    x_hermes_secret: str | None = Header(default=None),
    x_hermes_user_id: str | None = Header(default=None),
) -> str:
    settings = get_settings()
    if not settings.internal_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HERMES_INTERNAL_SECRET não configurado",
        )
    if x_hermes_secret != settings.internal_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if not x_hermes_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Hermes-User-Id ausente",
        )
    return x_hermes_user_id
