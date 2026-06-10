#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# configure-coolify.sh
# Post-provisioning: registers admin, creates project +
# environment, connects GitHub repo, sets env vars, deploys.
#
# Usage: ./configure-coolify.sh <vm-public-ip>
#   or:  ./configure-coolify.sh         # uses VM_IP from .env
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Config from .env ───────────────────────────────────────
if [ -f "${SCRIPT_DIR}/.env" ]; then
  set -a
  source "${SCRIPT_DIR}/.env"
  set +a
fi

VM_IP="${1:-${VM_IP:-}}"
: "${VM_IP:?Usage: configure-coolify.sh <vm-ip> or set VM_IP in .env}"
: "${COOLIFY_ADMIN_EMAIL:?Set COOLIFY_ADMIN_EMAIL in .env}"
: "${COOLIFY_ADMIN_PASSWORD:?Set COOLIFY_ADMIN_PASSWORD in .env}"
: "${GITHUB_REPO:?Set GITHUB_REPO in .env}"

COOLIFY_URL="http://${VM_IP}:8000"
API="${COOLIFY_URL}/api/v1"

# ─── Helpers ─────────────────────────────────────────────────
log()  { echo "  [ok] $*"; }
warn() { echo "  [!!] $*"; }
die()  { echo "  [fail] $*"; exit 1; }

api() {
  local method="$1" path="$2" data="${3:-}"
  local args=(-sS -X "$method" "${API}${path}")
  if [ -n "$TOKEN" ]; then
    args+=(-H "Authorization: Bearer $TOKEN")
  fi
  if [ -n "$data" ]; then
    args+=(-H "Content-Type: application/json" -d "$data")
  fi
  curl "${args[@]}"
}

# ─── Phases ──────────────────────────────────────────────────

wait_for_coolify() {
  echo "  Waiting for Coolify to be ready at ${COOLIFY_URL} ..."
  for i in $(seq 1 60); do
    if curl -sf "${API}/health" > /dev/null 2>&1; then
      log "Coolify is ready"
      return 0
    fi
    sleep 5
  done
  die "Coolify did not become ready within 5 minutes"
}

register_admin() {
  echo "  Registering admin user..."
  api POST /register "{
    \"name\": \"${COOLIFY_ADMIN_NAME:-Admin}\",
    \"email\": \"${COOLIFY_ADMIN_EMAIL}\",
    \"password\": \"${COOLIFY_ADMIN_PASSWORD}\"
  }" > /dev/null 2>&1 || true
  log "Admin registered (or already exists)"
}

login() {
  echo "  Logging in..."
  local resp
  resp=$(api POST /login "{
    \"email\": \"${COOLIFY_ADMIN_EMAIL}\",
    \"password\": \"${COOLIFY_ADMIN_PASSWORD}\"
  }")
  TOKEN=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('token') or d.get('access_token') or '')" 2>/dev/null || echo "")
  if [ -z "$TOKEN" ]; then
    die "Login failed. Response: $(echo "$resp" | head -c 200)"
  fi
  log "Logged in (token: ${TOKEN:0:16}...)"
}

create_project() {
  echo "  Creating project..."
  local resp
  resp=$(api POST /projects "{
    \"name\": \"living-map\",
    \"description\": \"Living Map - News event visualization\"
  }")
  PROJECT_UUID=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('uuid') or d.get('id') or '')" 2>/dev/null || echo "")
  if [ -z "$PROJECT_UUID" ]; then
    die "Project creation failed. Response: $(echo "$resp" | head -c 200)"
  fi
  log "Project created (UUID: ${PROJECT_UUID})"
}

create_environment() {
  echo "  Creating production environment..."
  local resp
  resp=$(api POST "/projects/${PROJECT_UUID}/environments" '{"name":"production"}')
  ENV_UUID=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('uuid') or d.get('id') or '')" 2>/dev/null || echo "")
  if [ -z "$ENV_UUID" ]; then
    die "Environment creation failed. Response: $(echo "$resp" | head -c 200)"
  fi
  log "Environment created (UUID: ${ENV_UUID})"
}

create_application() {
  echo "  Creating application from Git repository..."

  local resp
  resp=$(api POST /applications "{
    \"name\": \"living-map\",
    \"project_uuid\": \"${PROJECT_UUID}\",
    \"environment_name\": \"production\",
    \"repository\": \"${GITHUB_REPO}\",
    \"branch\": \"${GITHUB_BRANCH:-main}\",
    \"build_pack\": \"dockercompose\",
    \"docker_compose_location\": \"/backend/docker-compose.yml\",
    \"ports_exposes\": \"80,3002,8000\"
  }" 2>&1 || true)

  APP_UUID=$(echo "$resp" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get('uuid') or d.get('id') or '')
except: print('')
" 2>/dev/null || echo "")

  if [ -n "$APP_UUID" ]; then
    log "Application created (UUID: ${APP_UUID})"
  else
    warn "Application creation via API failed."
    warn "Create it manually in the Coolify UI: ${COOLIFY_URL}"
    warn "1. Open the 'living-map' project"
    warn "2. Click 'New Resource' -> 'From Docker Compose'"
    warn "3. Paste repo URL: ${GITHUB_REPO}"
    warn "4. Set compose file path: /backend/docker-compose.yml"
    APP_UUID=""
  fi
}

set_env_vars() {
  if [ -z "${APP_UUID:-}" ]; then
    warn "Skipping env vars (no application UUID)"
    return
  fi
  echo "  Setting environment variables..."

  local vars='[]'
  if [ -n "${DB_PASSWORD:-}" ]; then
    vars=$(echo "$vars" | python3 -c "
import sys,json
v=json.load(sys.stdin)
v.append({'key':'DATABASE_URL','value':'postgres://livingmap:${DB_PASSWORD}@postgres:5432/livingmap','is_build_time':false,'is_literal':true})
v.append({'key':'CORS_ORIGIN','value':'https://living-map.example.com','is_build_time':false,'is_literal':true})
v.append({'key':'LOCATION_EXTRACTION_URL','value':'http://location-extraction:8000','is_build_time':false,'is_literal':true})
v.append({'key':'LOG_LEVEL','value':'info','is_build_time':false,'is_literal':true})
v.append({'key':'SPACY_EN_MODEL','value':'en_core_web_sm','is_build_time':false,'is_literal':true})
v.append({'key':'SPACY_FR_MODEL','value':'fr_core_news_sm','is_build_time':false,'is_literal':true})
print(json.dumps(v))
")
    api PUT "/applications/${APP_UUID}/envs" "{\"environment_name\":\"production\",\"variables\":${vars}}" > /dev/null 2>&1 || true
    log "Environment variables set"
  else
    warn "DB_PASSWORD not set in .env — skipping env vars. Set them in Coolify UI."
  fi
}

deploy() {
  if [ -z "${APP_UUID:-}" ]; then
    warn "Skipping deploy (no application UUID)"
    return
  fi
  echo "  Triggering deployment..."
  api POST /deploy "{\"uuid\":\"${APP_UUID}\"}" > /dev/null 2>&1 || true
  log "Deployment triggered"
}

print_summary() {
  echo ""
  echo "  ──────────────────────────────────────────"
  echo "  Setup complete!"
  echo ""
  echo "  Coolify UI:    ${COOLIFY_URL}"
  echo "  SSH access:    ssh ubuntu@${VM_IP}"
  echo "  API token:     ${TOKEN:0:32}..."
  echo ""
  if [ -z "${APP_UUID:-}" ]; then
    echo "  Next: Finish setup in Coolify UI → ${COOLIFY_URL}"
    echo "  Login with:  ${COOLIFY_ADMIN_EMAIL}"
  else
    echo "  Deployment is in progress. Check status at ${COOLIFY_URL}"
  fi
  echo "  ──────────────────────────────────────────"
}

# ─── Main ───────────────────────────────────────────────────
main() {
  wait_for_coolify
  register_admin
  login
  create_project
  create_environment
  create_application
  set_env_vars
  deploy
  print_summary
}

main "$@"
