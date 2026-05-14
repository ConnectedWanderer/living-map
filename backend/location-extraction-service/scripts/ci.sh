#!/usr/bin/env bash
# CI entry point for location-extraction-service.
#
# Usage:
#   bash scripts/ci.sh                  # full suite (downloads models)
#   bash scripts/ci.sh --fast           # fast path: unit tests only
#   bash scripts/ci.sh --with-models    # full suite (explicit)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Install dependencies ==="
uv sync --frozen

if [[ "${1:-}" == "--fast" ]]; then
    echo "=== Fast path: skip model-dependent tests ==="
    uv run python -m pytest -m "not model_dependent" --cov=src --cov-report=term-missing
    uv run ruff check .
    uv run ruff format --check .
    exit 0
fi

echo "=== Download spaCy models ==="
uv run python -m spacy download en_core_web_sm fr_core_news_sm

echo "=== Download text2geo data (optional) ==="
uv run python -c "from text2geo import Geocoder; Geocoder(dataset='world')" || echo "Warning: text2geo data download failed (known upstream bug — see docs/decisions/ADR-005-text2geo-nan-bug.md). Geocoding tests mock the dependency, so this is non-critical."

echo "=== Run full test suite ==="
uv run python -m pytest --cov=src --cov-report=term-missing

echo "=== Lint ==="
uv run ruff check .

echo "=== Format check ==="
uv run ruff format --check .
