"""Token assinado HMAC pra ingest via bookmarklet.

Sem JWT (zero deps novos). Formato: ``<base64url(user_id)>.<hmac_sha256_hex>``.
A assinatura usa ``HERMES_INTERNAL_SECRET``. Sem expiração: troque o secret
pra revogar todos os tokens emitidos.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from ..config import get_settings


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def make_token(user_id: str) -> str:
    settings = get_settings()
    if not settings.internal_secret:
        raise RuntimeError("HERMES_INTERNAL_SECRET não configurado")
    sig = hmac.new(
        settings.internal_secret.encode("utf-8"),
        user_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{_b64(user_id.encode('utf-8'))}.{sig}"


def verify_token(token: str) -> str | None:
    settings = get_settings()
    if not settings.internal_secret:
        return None
    try:
        encoded_user, sig = token.split(".", 1)
        user_id = _b64_decode(encoded_user).decode("utf-8")
        expected = hmac.new(
            settings.internal_secret.encode("utf-8"),
            user_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(expected, sig):
            return user_id
    except Exception:  # noqa: BLE001
        return None
    return None
