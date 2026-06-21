#!/usr/bin/env bash
# DeltaForge - stop and remove the Docker stack.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

docker compose -f infrastructure/docker/docker-compose.yml down "$@"
echo "[DeltaForge] Stack stopped."
