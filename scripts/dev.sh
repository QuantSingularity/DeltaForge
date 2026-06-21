#!/usr/bin/env bash
# DeltaForge - full-stack development: starts the FastAPI server and the Vite
# dev server together with hot reload. Ctrl-C stops both.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

API_PORT="${DELTAFORGE_PORT:-8000}"

cleanup() {
    echo ""
    echo "[DeltaForge] Shutting down..."
    if [ -n "${API_PID:-}" ]; then
        kill "$API_PID" 2>/dev/null || true
    fi
    if [ -n "${UI_PID:-}" ]; then
        kill "$UI_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

echo "[DeltaForge] Starting API on http://localhost:${API_PORT}"
PYTHONPATH=code python3 -m uvicorn backend.api.server:app --reload --port "$API_PORT" &
API_PID=$!

if command -v npm >/dev/null 2>&1; then
    echo "[DeltaForge] Starting dashboard (Vite) - proxies /api and /ws to the API"
    (cd frontend && npm run dev) &
    UI_PID=$!
    echo "[DeltaForge] Dashboard: http://localhost:5173"
else
    echo "[DeltaForge] npm not found - API only. Open http://localhost:${API_PORT}"
fi

wait
