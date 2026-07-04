#!/usr/bin/env bash
# Build and run the ingestion-worker as a one-shot Docker batch job.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_TAG=${IMAGE_TAG:-living-map/ingestion-worker}
NETWORK=${NETWORK:-backend_default}
DATABASE_URL=${DATABASE_URL:-postgres://livingmap:livingmap@postgres:5432/livingmap?options=-c%20search_path=living_map,public}

echo "==> Building $IMAGE_TAG ..."
docker build -t "$IMAGE_TAG" "$SERVICE_ROOT"

echo "==> Running ingestion worker on network $NETWORK ..."
exec docker run --rm -i \
  --network "$NETWORK" \
  -e DATABASE_URL="$DATABASE_URL" \
  -e PGSSLMODE=disable \
  "$IMAGE_TAG"
