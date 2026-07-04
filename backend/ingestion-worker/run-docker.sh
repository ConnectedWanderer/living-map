#!/usr/bin/env bash
# Build ingestion-worker image and run it as a one-shot execution.
set -euo pipefail

cd "$(dirname "$0")"

IMAGE_TAG=${IMAGE_TAG:-living-map/ingestion-worker}
NETWORK=${NETWORK:-backend_default}
DATABASE_URL=${DATABASE_URL:-postgres://livingmap:livingmap@postgres:5432/livingmap?options=-c%20search_path=living_map,public}

echo "==> Building $IMAGE_TAG ..."
docker build -t "$IMAGE_TAG" .

echo "==> Running ingestion worker on network $NETWORK ..."
exec docker run --rm -i \
  --network "$NETWORK" \
  -e DATABASE_URL="$DATABASE_URL" \
  -e PGSSLMODE=disable \
  "$IMAGE_TAG"
