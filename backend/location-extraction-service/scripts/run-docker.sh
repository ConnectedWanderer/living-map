#!/usr/bin/env bash
# Build and run the location-extraction-service as a one-shot batch job.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_TAG=${IMAGE_TAG:-living-map/location-extraction-service}
NETWORK=${NETWORK:-backend_default}
DATABASE_URL=${DATABASE_URL:-postgres://livingmap:livingmap@postgres:5432/livingmap?options=-c%20search_path=living_map,public}
# psycopg2 doesn't support ?options= in connection URIs, so pass it via PGOPTIONS
CONTAINER_DB_URL=${DATABASE_URL%%\?options=*}

echo "==> Building $IMAGE_TAG ..."
docker build -t "$IMAGE_TAG" "$SERVICE_ROOT"

echo "==> Running location extraction on network $NETWORK ..."
exec docker run --rm -i \
  --network "$NETWORK" \
  -e DATABASE_URL="$CONTAINER_DB_URL" \
  -e PGOPTIONS="-c search_path=living_map,public" \
  -e SPACY_EN_MODEL=en_core_web_sm \
  -e SPACY_FR_MODEL=fr_core_news_sm \
  "$IMAGE_TAG"
