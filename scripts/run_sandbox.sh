#!/usr/bin/env bash
# DeltaForge — run in sandbox (paper trading) mode
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "[DeltaForge] Starting sandbox (paper trading) mode..."
PYTHONPATH=code python3 -m backend --sandbox "$@"
