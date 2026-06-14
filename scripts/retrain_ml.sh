#!/usr/bin/env bash
# DeltaForge — retrain ML model from saved trade history
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "[DeltaForge] Retraining ML model from trade history..."
PYTHONPATH=code python3 -m backend --retrain "$@"
