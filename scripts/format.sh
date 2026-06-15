#!/usr/bin/env bash
#
# Formats (or checks with --check) all files in the repository.
#
# One-time setup:
#   uv tool install pre-commit
#   pre-commit install
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# --- Dependency checks ---

command -v node >/dev/null 2>&1 || {
  echo "ERROR: Node.js is required for Prettier."
  exit 1
}

command -v uv >/dev/null 2>&1 || {
  echo "ERROR: uv is required for Python tooling."
  exit 1
}

# --- Mode ---

CHECK=
if [ "${1:-}" = "--check" ]; then
  CHECK=1
fi

# --- Format / Check ---

echo "--- Markdown ---"
PRETTIER_DIR=$(mktemp -d)
trap 'rm -rf "$PRETTIER_DIR"' EXIT
(
  cd "$PRETTIER_DIR"
  npm init -y > /dev/null 2>&1
  npm install --no-save --silent prettier@3.8
)
if [ "$CHECK" ]; then
  "$PRETTIER_DIR/node_modules/.bin/prettier" --check "**/*.md"
else
  "$PRETTIER_DIR/node_modules/.bin/prettier" --write "**/*.md"
fi

echo "--- Python ---"
(
  cd backend/location-extraction-service
  if [ "$CHECK" ]; then
    uv run ruff format --check .
    uv run ruff check .
  else
    uv run ruff format .
    uv run ruff check --fix .
  fi
)

echo "--- TypeScript ---"
(
  cd backend/ingestion-worker
  if [ "$CHECK" ]; then
    npm run lint:ci
  else
    npm run check
  fi
)

echo "--- Done ---"
