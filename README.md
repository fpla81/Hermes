# Hermes

Webapp privado para análise de processos do TST. Porta a skill `hermes-tst` para
Next.js 15 + FastAPI + Gemini 2.5 Flash.

> **Status:** Fase 0 (Fundação). Apenas esqueleto. Lógica de negócio (captura
> Bem-te-vi, anonimização, pipeline LLM, DOCX) entra nas Fases 1+.

## Stack

- **Frontend:** Next.js 15, TypeScript, Tailwind v4, shadcn/ui, Auth.js v5, Drizzle
- **Backend:** FastAPI (Python 3.12), SQLAlchemy 2, Alembic, Celery, Redis
- **Capture:** Playwright (Python) microservice
- **Infra:** Postgres 16, Redis 7, MinIO (S3), Mailhog (dev), Resend (prod)

## Monorepo

```
apps/
├── web/         Next.js
├── api/         FastAPI
├── worker/      Celery
└── playwright/  Bem-te-vi capture microservice
packages/
└── shared-types/  OpenAPI types for web
docker/
└── docker-compose.yml
```

## Pré-requisitos

- Node 22+ e `pnpm` 11+ (`npm i -g pnpm`)
- Python 3.12 e `uv` 0.11+ (`pip install --user uv` ou `brew install uv`)
- Docker Desktop (ou OrbStack) para o compose

## Setup

```bash
cp .env.example .env
pnpm install
uv sync
docker compose -f docker/docker-compose.yml up -d postgres redis minio mailhog
pnpm --filter web db:migrate     # tabelas de auth
uv run --package hermes-api alembic upgrade head   # tabelas do domínio
```

## Dev

```bash
# tudo em containers
docker compose -f docker/docker-compose.yml up

# ou serviços fora do compose, infra dentro
pnpm --filter web dev                   # http://localhost:3000
uv run --package hermes-api uvicorn hermes_api.main:app --reload --port 8000
uv run --package hermes-worker celery -A hermes_worker.celery_app worker --loglevel=info
uv run --package hermes-playwright uvicorn hermes_playwright.main:app --reload --port 8001
```

## Test

```bash
pnpm test
uv run pytest
```

## Próximas fases

Ver `/Users/fabioportela/.claude/plans/analise-essa-skill-do-cryptic-wind.md` (PRD completa).
