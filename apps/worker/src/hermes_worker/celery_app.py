from celery import Celery
from celery.schedules import crontab
from hermes_api.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hermes",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "refresh-tst-repetitivos": {
            "task": "hermes.refresh_repetitivos",
            # Segundas, 04:00 America/Sao_Paulo.
            "schedule": crontab(minute=0, hour=4, day_of_week=1),
        },
    },
)

celery_app.autodiscover_tasks(packages=["hermes_worker.tasks"])


@celery_app.task(name="hermes.ping")
def ping() -> str:
    return "pong"
