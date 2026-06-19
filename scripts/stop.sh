#!/usr/bin/env bash
# Stop and remove the Project Management MVP container (Mac and Linux).
set -euo pipefail

CONTAINER="pm-mvp"

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
echo "Stopped and removed ${CONTAINER}"
