# Hermes — Notas para Claude Code

## Contexto

Monorepo Next.js + FastAPI que porta a skill `hermes-tst`
(`/Users/fabioportela/.codex/skills/hermes-tst/`) para webapp privado. PRD
completa em `/Users/fabioportela/.claude/plans/analise-essa-skill-do-cryptic-wind.md`.

## Stack pinada

- Node 22, pnpm 11, TypeScript 5.7
- Next.js 15.1 (App Router, RSC), **Tailwind v3.4** (descemos da v4 por causa de fricção atual com shadcn — revisitar quando o ecossistema estabilizar), shadcn-style tokens
- Auth.js `5.0.0-beta.25` + Drizzle adapter, Resend provider (Mailhog em dev quando `AUTH_RESEND_KEY` ausente)
- Python 3.12, uv 0.11+
- FastAPI, SQLAlchemy 2 async, Alembic, Celery 5, asyncpg
- Postgres 16, Redis 7, MinIO

## Convenções

- Tabelas de **auth** em schema Postgres `auth`, manejadas por Drizzle (`apps/web/src/db`).
- Tabelas de **domínio** em schema `public`, manejadas por SQLAlchemy/Alembic (`apps/api`).
- Tipos compartilhados frontend↔backend são gerados via `pnpm gen:types` a partir do
  OpenAPI da API rodando em `localhost:8000`.
- Jobs longos vão para Celery; rotas FastAPI devem ser finas (validação + enfileiramento).
- Nada de chamadas LLM diretas do frontend — sempre via backend (gate de anonimização).

## Comandos frequentes

```bash
pnpm dev                 # roda web em :3000
pnpm --filter web build
pnpm --filter web lint
pnpm --filter web typecheck
uv run --package hermes-api pytest
uv run --package hermes-api alembic revision --autogenerate -m "msg"
uv run --package hermes-api alembic upgrade head
pnpm gen:types           # regenera packages/shared-types/src/api.ts
```

## Onde editar o quê

- Rotas API → `apps/api/src/hermes_api/routes/`
- Modelos do domínio → `apps/api/src/hermes_api/models/`
- Tarefas Celery → `apps/worker/src/hermes_worker/tasks/`
- Telas → `apps/web/src/app/(app)/`
- Componentes shadcn → `apps/web/src/components/ui/`
- Lógica de captura Bem-te-vi → `apps/playwright/src/hermes_playwright/`

## iCloud — atenção

O working dir vive em `~/Library/Mobile Documents/...`. Evite gerar arquivos
massivos (node_modules, .venv, .next) sem que o `.gitignore` os cubra. Se houver
lentidão, considere mover caches para fora:

```bash
pnpm config set store-dir ~/.pnpm-store
export UV_CACHE_DIR=~/.cache/uv
```

## Pós-conclusão — checklist obrigatório

Ao finalizar QUALQUER solicitação que altere código, apresente ao usuário
o conjunto completo de comandos pra rodar o app em dev sem dor de cabeça.
Não pular nenhum item, mesmo quando não estritamente necessário — é
diagnóstico preventivo.

Diretório do projeto local: `~/Code/Hermes`.

```bash
# 1. Puxar últimas mudanças
cd ~/Code/Hermes
git pull

# 2. Liberar portas que possam ter ficado presas
lsof -ti :3100 | xargs kill -9 2>/dev/null   # web
lsof -ti :8000 | xargs kill -9 2>/dev/null   # api

# 3. Limpar cache do Next (se mexeu em frontend ou tokens Tailwind)
rm -rf apps/web/.next

# 4. Subir Postgres/Redis/MinIO/API/worker via Docker
docker compose -f docker/docker-compose.yml up -d

# 5. Aplicar migrations novas, se houver
docker compose -f docker/docker-compose.yml run --rm migrate

# 6. Reiniciar API/worker quando o que mudou foi backend ou .env
docker compose -f docker/docker-compose.yml restart api worker

# 7. Rodar o web local com hot-reload (recomendado em dev)
docker compose -f docker/docker-compose.yml stop web
pnpm dev

# Alternativa: rodar web também no Docker (rebuild quando deps mudaram)
docker compose -f docker/docker-compose.yml up -d --build web
```

Indicar especificamente quais passos são necessários para a mudança em
questão (ex.: "só backend mudou — passos 1, 2, 6 bastam"), mas SEMPRE
listar o checklist completo pra o usuário escolher.

Se a mudança envolveu:
- Backend Python → reiniciar `api` e `worker`.
- Migrations Alembic → rodar o serviço `migrate` antes de reiniciar a API.
- `.env` → reiniciar containers afetados (`api`/`worker`/`web`).
- Frontend → `rm -rf apps/web/.next` antes do reload.
- Deps novas em `apps/web/package.json` → reinstalar (`pnpm install` ou
  rebuild da imagem `web`).
- Dependências Python novas em `pyproject.toml` → rebuild da imagem
  (`docker compose ... up -d --build api worker`).

## Skill de origem (referência)

Scripts Python originais em `/Users/fabioportela/.codex/skills/hermes-tst/scripts/`
e references em `/Users/fabioportela/.codex/skills/hermes-tst/references/`. Não
editar lá; portar para `apps/api` conforme as fases avançam.
