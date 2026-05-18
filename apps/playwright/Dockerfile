# Build context: repo root
FROM mcr.microsoft.com/playwright/python:v1.59.0-noble
ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.11.14
WORKDIR /app
COPY pyproject.toml ./
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/worker/pyproject.toml ./apps/worker/pyproject.toml
COPY apps/playwright/pyproject.toml ./apps/playwright/pyproject.toml
RUN uv sync --package hermes-playwright --no-dev || uv sync --package hermes-playwright
COPY apps/playwright ./apps/playwright
EXPOSE 8001
WORKDIR /app/apps/playwright
CMD ["uv", "run", "uvicorn", "hermes_playwright.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
