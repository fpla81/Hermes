from fastapi import Depends, Header, HTTPException, status

from .config import get_settings

Role = str  # "user" | "manager" | "admin"
MANAGER_ROLES = frozenset({"manager", "admin"})


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


async def current_user_role(
    x_hermes_user_role: str | None = Header(default=None),
) -> Role:
    """Role do usuário propagado pelo frontend (NextAuth → header).
    Sem header, default = "user". A confiança vem do secret (mesma checagem
    de ``current_user_id``); o frontend é a fonte da verdade.
    """
    role = (x_hermes_user_role or "user").strip().lower()
    if role not in {"user", "manager", "admin"}:
        return "user"
    return role


async def require_manager(role: Role = Depends(current_user_role)) -> Role:
    if role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acesso restrito a gerentes",
        )
    return role


async def require_admin(role: Role = Depends(current_user_role)) -> Role:
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acesso restrito a administradores",
        )
    return role

