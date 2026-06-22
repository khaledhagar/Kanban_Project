#!/usr/bin/env bash
# Build and run the Project Management MVP container (Mac and Linux).
set -euo pipefail

IMAGE="pm-mvp"
CONTAINER="pm-mvp"
PORT="${PORT:-8000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker build -t "$IMAGE" "$ROOT"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

# Pass the OpenRouter key (and any other vars) from the root .env if present;
# it is intentionally excluded from the image. The app runs without it, but the
# AI features need it.
ENV_ARGS=()
[ -f "$ROOT/.env" ] && ENV_ARGS+=(--env-file "$ROOT/.env")
docker run -d --name "$CONTAINER" -p "${PORT}:8000" -v pm-data:/app/data \
  "${ENV_ARGS[@]}" "$IMAGE"

echo "Running at http://localhost:${PORT} (health: http://localhost:${PORT}/api/health)"
