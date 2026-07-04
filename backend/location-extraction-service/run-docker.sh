#!/usr/bin/env bash
# Build and run the location-extraction-service as a one-shot batch job.
set -euo pipefail

cd "$(dirname "$0")"

IMAGE_TAG=${IMAGE_TAG:-living-map/location-extraction-service}
NETWORK=${NETWORK:-backend_default}
DATABASE_URL=${DATABASE_URL:-postgres://livingmap:livingmap@postgres:5432/livingmap?options=-c%20search_path=living_map,public}

echo "==> Building $IMAGE_TAG ..."
docker build -t "$IMAGE_TAG" .

echo "==> Running location extraction on network $NETWORK ..."
exec docker run --rm -i \
  --network "$NETWORK" \
  -e DATABASE_URL="$DATABASE_URL" \
  -e SPACY_EN_MODEL=en_core_web_sm \
  -e SPACY_FR_MODEL=fr_core_news_sm \
  "$IMAGE_TAG"
