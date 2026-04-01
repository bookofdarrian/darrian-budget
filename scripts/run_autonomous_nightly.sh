#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/darrian-budget}"
ORCH_FILE="${ORCH_FILE:-/opt/overnight-dev/orchestrator.py}"
VENV_PYTHON="${VENV_PYTHON:-$REPO_DIR/venv/bin/python3}"
LOG_FILE="${LOG_FILE:-/var/log/overnight-dev.log}"
PREFLIGHT_SCRIPT="${PREFLIGHT_SCRIPT:-$REPO_DIR/scripts/autonomous_preflight.sh}"

send_telegram() {
  local msg="$1"
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -H 'Content-Type: application/json' \
      -d "{\"chat_id\":\"${TELEGRAM_CHAT_ID}\",\"text\":\"${msg}\"}" >/dev/null || true
  fi
}

classify_failure() {
  local text="$1"
  local upper
  upper="$(printf '%s' "$text" | tr '[:lower:]' '[:upper:]')"
  if [[ "$upper" == *"PYTEST"* ]] || [[ "$upper" == *"TEST"* ]]; then
    echo "TEST"
  elif [[ "$upper" == *"GIT"* ]] || [[ "$upper" == *"MERGE"* ]] || [[ "$upper" == *"PUSH"* ]]; then
    echo "GIT"
  elif [[ "$upper" == *"DEPLOY"* ]] || [[ "$upper" == *"HEALTH CHECK"* ]] || [[ "$upper" == *"DOCKER"* ]]; then
    echo "DEPLOY"
  else
    echo "ENV"
  fi
}

mkdir -p "$(dirname "$LOG_FILE")"

{
  echo "[$(date '+%F %T')] [ENV] Nightly autonomous run started"

  if ! bash "$PREFLIGHT_SCRIPT"; then
    MSG="[$(date '+%F %T')] [ENV] Nightly preflight failed"
    echo "$MSG"
    send_telegram "$MSG"
    exit 1
  fi

  if [ ! -f "$ORCH_FILE" ]; then
    MSG="[$(date '+%F %T')] [ENV] Missing orchestrator file: $ORCH_FILE"
    echo "$MSG"
    send_telegram "$MSG"
    exit 1
  fi

  set +e
  ORCH_OUTPUT="$($VENV_PYTHON "$ORCH_FILE" 2>&1)"
  RC=$?
  set -e

  if [ $RC -ne 0 ]; then
    CLASS="$(classify_failure "$ORCH_OUTPUT")"
    MSG="[$(date '+%F %T')] [${CLASS}] Nightly run failed (exit=$RC)"
    echo "$MSG"
    echo "$ORCH_OUTPUT"
    send_telegram "$MSG"
    exit $RC
  fi

  MSG="[$(date '+%F %T')] [SUCCESS] Nightly autonomous run completed"
  echo "$MSG"
  send_telegram "$MSG"
} >> "$LOG_FILE" 2>&1
