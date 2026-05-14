from hermes_worker.celery_app import ping


def test_ping_runs_inline() -> None:
    assert ping() == "pong"
