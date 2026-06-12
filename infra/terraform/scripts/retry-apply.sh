#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# retry-apply.sh
# Retries terraform apply across availability domains until
# an OCI Always-Free ARM instance is successfully provisioned.
#
# Usage:
#   ./retry-apply.sh                          # default 5 min interval
#   RETRY_INTERVAL=600 ./retry-apply.sh       # custom 10 min interval
#
# Dependencies: terraform, OCI API key configured in tfvars
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TFVARS="${PROJECT_DIR}/terraform.tfvars"
RETRY_INTERVAL="${RETRY_INTERVAL:-60}"

# ─── Extract backend config from terraform.tfvars ───────────

if [ ! -f "$TFVARS" ]; then
  echo "[FATAL] ${TFVARS} not found."
  echo "  Run this script from infra/terraform/ or ensure terraform.tfvars exists."
  exit 1
fi

get_var() {
  grep "^[[:space:]]*$1" "$TFVARS" | head -1 | sed 's/.*=\s*//' | tr -d ' "' || true
}

REGION=$(get_var "region")
NAMESPACE=$(get_var "tenancy_namespace")
STATE_BUCKET=$(get_var "state_bucket_name")
STATE_BUCKET="${STATE_BUCKET:-living-map-terraform-state}"

if [ -z "$REGION" ] || [ -z "$NAMESPACE" ]; then
  echo "[FATAL] Could not extract 'region' or 'tenancy_namespace' from terraform.tfvars."
  exit 1
fi

# ─── Helpers ─────────────────────────────────────────────────

log()   { echo "[$(date +%Y-%m-%dT%H:%M:%S%z)] $*"; }
die()   { log "FATAL: $*"; exit 1; }

cleanup() {
  log "Received interrupt. Exiting."
  exit 130
}
trap cleanup SIGINT SIGTERM

init_terraform() {
  log "Initializing Terraform (backend: ${STATE_BUCKET}, region: ${REGION})..."
  if ! terraform init \
    -input=false \
    -reconfigure \
    -backend-config="bucket=${STATE_BUCKET}" \
    -backend-config="key=infra/terraform.tfstate" \
    -backend-config="region=${REGION}" \
    -backend-config="namespace=${NAMESPACE}" \
    2>&1; then
    die "terraform init failed. Does the state bucket '${STATE_BUCKET}' exist?"
  fi
  log "Terraform initialized."
}

try_apply() {
  local ad_number=$1
  log "Attempting apply with availability_domain_number = ${ad_number}..."

  local apply_output
  apply_output=$(terraform apply -auto-approve -input=false \
    -var "availability_domain_number=${ad_number}" \
    2>&1)
  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
    echo "$apply_output"
    return 0
  fi

  if echo "$apply_output" | grep -qi "out of\( host\)\? capacity\|InsufficientCapacity\|OutOfCapacity\|outofcapacity"; then
    echo "$apply_output" | grep -iA1 "Error:\|out of\( host\)\? capacity\|InsufficientCapacity\|OutOfCapacity" | head -6
    log "AD ${ad_number}: Out of capacity. Will try next AD."
    return 1
  fi

  echo "$apply_output" | grep -i "Error:" | head -5
  log "AD ${ad_number}: Apply failed (exit code ${exit_code}) with unexpected error."
  log "This may be a transient issue — will retry on next cycle."
  return 2
}

post_deploy() {
  log "=== Instance provisioned successfully! ==="

  local ip
  ip=$(terraform output -raw instance_public_ip 2>/dev/null || true)

  if [ -z "$ip" ]; then
    log "WARNING: Could not retrieve public IP from terraform output."
    log "Check the OCI console or run: terraform output"
    return
  fi

  log "Public IP: ${ip}"

  if [ -x "${SCRIPT_DIR}/configure-coolify.sh" ]; then
    log "Running configure-coolify.sh ${ip} ..."
    if bash "${SCRIPT_DIR}/configure-coolify.sh" "$ip"; then
      log "Coolify configuration complete!"
    else
      log "WARNING: configure-coolify.sh failed."
      log "Finish setup manually at http://${ip}:8000"
    fi
  else
    log "configure-coolify.sh not found — skipping post-deploy setup."
    log "SSH: ssh ubuntu@${ip}"
  fi
}

# ─── Main loop ──────────────────────────────────────────────

main() {
  cd "$PROJECT_DIR"
  log "=== OCI ARM Instance Retry Loop ==="
  log "  Region:            ${REGION}"
  log "  Availability ADs:  1, 2, 3"
  log "  Retry interval:    ${RETRY_INTERVAL}s"
  log "  State bucket:      ${STATE_BUCKET}"
  log "  Terraform dir:     ${PROJECT_DIR}"
  log ""

  init_terraform

  while true; do
    local deployed=false

    for ad in 1 2 3; do
      log "─────────────────────────────────────────"
      if try_apply "$ad"; then
        deployed=true
        post_deploy
        break
      fi
      sleep 2
    done

    if [ "$deployed" = true ]; then
      log "Done. Instance is ready."
      exit 0
    fi

    log "─────────────────────────────────────────"
    log "All 3 availability domains exhausted."
    log "Sleeping ${RETRY_INTERVAL}s before next cycle..."
    sleep "$RETRY_INTERVAL"
  done
}

main "$@"
