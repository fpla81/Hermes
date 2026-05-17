"""CLI: refresca a tabela de Repetitivos do TST agora (sem esperar o cron).

Uso:
    uv run --package hermes-api python -m hermes_api.scripts.refresh_repetitivos_now
"""

from __future__ import annotations

from hermes_api.db import SyncSessionLocal
from hermes_api.services.tst_repetitivos import refresh_now


def main() -> None:
    with SyncSessionLocal() as session:
        stats = refresh_now(session)
    print(
        f"Repetitivos atualizados — buscados: {stats.get('fetched', 0)} | "
        f"criados: {stats['created']} | atualizados: {stats['updated']}"
    )


if __name__ == "__main__":
    main()
