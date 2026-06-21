#!/usr/bin/env bash
# DeltaForge - build and start the full stack (backend + dashboard) in Docker.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

COMPOSE="infrastructure/docker/docker-compose.yml"
echo "[DeltaForge] Building and starting containers..."
docker compose -f "$COMPOSE" up --build "$@"
echo "Dashboard: http://localhost:8080   API docs: http://localhost:8000/docs"
