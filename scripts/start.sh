#!/usr/bin/env bash
# Build and run the Project Management MVP container (Mac and Linux).
set -euo pipefail

IMAGE="pm-mvp"
CONTAINER="pm-mvp"
PORT="${PORT:-8000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker build -t "$IMAGE" "$ROOT"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" -p "${PORT}:8000" "$IMAGE"

echo "Running at http://localhost:${PORT} (health: http://localhost:${PORT}/api/health)"
