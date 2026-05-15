#!/usr/bin/env bash
# Roda o hermes-playwright no host (Mac), com display, para suportar o
# fluxo de login interativo do Bem-te-vi via /settings.
#
# Use este script no lugar do container playwright do docker-compose. Quando
# este serviço está rodando na porta 8001, o api/worker do compose o alcançam
# via host.docker.internal:8001 (configure PLAYWRIGHT_SERVICE_URL no .env).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export BEM_TE_VI_PROFILE_DIR="${BEM_TE_VI_PROFILE_DIR:-$ROOT/bem_te_vi_profile}"
export BEMTEVI_REAL_CAPTURE="${BEMTEVI_REAL_CAPTURE:-1}"
export BEMTEVI_HEADLESS="${BEMTEVI_HEADLESS:-1}"

echo "[hermes-playwright host] profile: $BEM_TE_VI_PROFILE_DIR"
echo "[hermes-playwright host] http://localhost:8001"

exec uv run --package hermes-playwright \
  uvicorn hermes_playwright.main:app \
  --host 0.0.0.0 --port 8001
