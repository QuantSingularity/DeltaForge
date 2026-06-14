#!/usr/bin/env bash
# DeltaForge — build the dashboard for production into web-frontend/dist.
# Once built, the FastAPI server serves it directly at its root.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT/web-frontend"

command -v npm >/dev/null 2>&1 || { echo "ERROR: npm (Node 20+) required"; exit 1; }

echo "[DeltaForge] Installing frontend dependencies..."
npm install --silent
echo "[DeltaForge] Building dashboard..."
npm run build
echo "[DeltaForge] Build complete -> web-frontend/dist"
echo "Serve it with:  ./scripts/run_dashboard.sh"
