#!/usr/bin/env bash
# DeltaForge — run the web dashboard API (serves the built frontend if present)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

PORT="${DELTAFORGE_PORT:-8000}"
echo "[DeltaForge] Starting dashboard API on http://localhost:${PORT}"
PYTHONPATH=code python3 -m uvicorn backend.api.server:app --host 0.0.0.0 --port "$PORT" "$@"
