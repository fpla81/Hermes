# Build context: repo root
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.11.14
WORKDIR /app
COPY pyproject.toml ./
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/worker/pyproject.toml ./apps/worker/pyproject.toml
COPY apps/playwright/pyproject.toml ./apps/playwright/pyproject.toml
RUN uv sync --package hermes-api --no-dev || uv sync --package hermes-api
COPY apps/api ./apps/api
EXPOSE 8000
WORKDIR /app/apps/api
CMD ["uv", "run", "uvicorn", "hermes_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
