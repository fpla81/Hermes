# Build context: repo root
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.11.14
WORKDIR /app
COPY pyproject.toml ./
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/worker/pyproject.toml ./apps/worker/pyproject.toml
COPY apps/playwright/pyproject.toml ./apps/playwright/pyproject.toml
RUN uv sync --package hermes-worker --no-dev || uv sync --package hermes-worker
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
WORKDIR /app/apps/worker
CMD ["uv", "run", "celery", "-A", "hermes_worker.celery_app", "worker", "--loglevel=info"]
