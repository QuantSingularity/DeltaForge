#!/usr/bin/env bash
# DeltaForge — run live trading bot
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

EXCHANGE="${DELTAFORGE_EXCHANGE:-}"
EXCHANGE_ARG=""
if [ -n "$EXCHANGE" ]; then
    EXCHANGE_ARG="--exchange $EXCHANGE"
fi

echo "[DeltaForge] Starting live trading bot..."
PYTHONPATH=code python3 -m backend $EXCHANGE_ARG "$@"
