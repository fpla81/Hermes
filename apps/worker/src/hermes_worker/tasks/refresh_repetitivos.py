"""Refresh semanal da tabela TST de Recursos de Revista Repetitivos."""

from __future__ import annotations

import logging

from hermes_api.db import SyncSessionLocal
from hermes_api.services.tst_repetitivos import refresh_now

from ..celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="hermes.refresh_repetitivos")
def refresh_repetitivos() -> dict:
    """Baixa a página oficial, faz upsert dos temas no Postgres.

    Roda no Celery beat semanalmente. Pode ser disparada manualmente via
    ``celery -A hermes_worker call hermes.refresh_repetitivos``.
    """
    with SyncSessionLocal() as session:
        stats = refresh_now(session)
    log.info("refresh_repetitivos: %s", stats)
    return stats
