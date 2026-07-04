#!/usr/bin/env bash
# Trigger a remote les-job run on Scaleway, wait for completion,
# and print status and error details.
set -euo pipefail

JOB_NAME="les-job"
JOB_ID=""

for arg in "$@"; do
  case "$arg" in
  --help | -h)
    echo "Usage: $0 [<job-definition-id>]"
    echo ""
    echo "  <job-id>    Job definition ID (auto-discovered by name if omitted)"
    exit 0
    ;;
  *) JOB_ID="$arg" ;;
  esac
done

command -v scw >/dev/null 2>&1 || {
  echo "Fatal: 'scw' CLI not found. See https://github.com/scaleway/scaleway-cli"
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "==> Installing jq ..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y -qq jq
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm jq
  else
    echo "Fatal: 'jq' not found. Install it manually (https://jqlang.github.io/jq/download)"
    exit 1
  fi
}

if [ -z "$JOB_ID" ]; then
  echo "==> Looking up '$JOB_NAME' definition ..."
  JOB_ID=$(scw jobs definition list -o json | jq -r --arg N "$JOB_NAME" '.[] | select(.name == $N) | .id')
  if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
    echo "Error: No job definition named '$JOB_NAME' found."
    exit 1
  fi
  echo "    ID: $JOB_ID"
fi

echo "==> Starting run ..."
RUN_ID=$(scw jobs definition start "$JOB_ID" -o json | jq -r '.job_runs[0].id')
if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
  echo "Error: Could not start job run."
  exit 1
fi
echo "    Run ID: $RUN_ID"

echo "==> Waiting for run to complete (press Ctrl+C to stop) ..."

spinner="/-\|"
spin_i=0
while true; do
  spin_i=$(( (spin_i + 1) % 4 ))
  printf "\r    Status: %s " "${spinner:$spin_i:1}"

  status=$(scw jobs run get "$RUN_ID" -o json 2>/dev/null | jq -r '{s: .state, e: .exit_code, msg: .error_message}')
  state=$(echo "$status" | jq -r '.s')
  exit_code=$(echo "$status" | jq -r '.e')
  error_msg=$(echo "$status" | jq -r '.msg // empty')

  case "$state" in
  succeeded)
    printf "\r    Status: succeeded (exit code %s)\n" "$exit_code"
    echo ""
    echo "==> Logs: see https://console.scaleway.com/jobs/runs/$RUN_ID"
    exit 0
    ;;
  failed | error)
    printf "\r    Status: %s (exit code %s)\n" "$state" "$exit_code"
    echo ""
    if [ -n "$error_msg" ]; then
      echo "==> Error:"
      echo "$error_msg"
    fi
    echo "==> Full logs: https://console.scaleway.com/jobs/runs/$RUN_ID"
    exit 1
    ;;
  cancelled)
    printf "\r    Status: cancelled\n"
    exit 1
    ;;
  esac

  sleep 3
done
