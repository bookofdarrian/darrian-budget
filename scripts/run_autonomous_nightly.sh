#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/darrian-budget}"
ORCH_FILE="${ORCH_FILE:-/opt/overnight-dev/orchestrator.py}"
VENV_PYTHON="${VENV_PYTHON:-$REPO_DIR/venv/bin/python3}"
LOG_FILE="${LOG_FILE:-/var/log/overnight-dev.log}"
PREFLIGHT_SCRIPT="${PREFLIGHT_SCRIPT:-$REPO_DIR/scripts/autonomous_preflight.sh}"
NOTIFY_LOCK_DIR="${NOTIFY_LOCK_DIR:-/tmp/overnight-dev-notify-locks}"
FAILURE_STATE_FILE="${FAILURE_STATE_FILE:-/tmp/overnight-dev-last-failure.state}"
FAILURE_COOLDOWN_SEC="${FAILURE_COOLDOWN_SEC:-21600}"
ORCH_MAX_ATTEMPTS="${ORCH_MAX_ATTEMPTS:-2}"
ORCH_RETRY_DELAY_SEC="${ORCH_RETRY_DELAY_SEC:-45}"

RUN_TS="$(date '+%F %T')"
RUN_ID="$(date '+%Y%m%d-%H%M%S')-$$"
RUN_HOST="$(hostname 2>/dev/null || echo 'unknown-host')"
FINAL_STATUS="unknown"
FINAL_CLASS="ENV"
FINAL_DETAIL=""
FINAL_ATTEMPT="1"
SUPPRESS_FINAL_FAIL_ALERT="0"

log_line() {
  echo "[$(date '+%F %T')] $1"
}

send_telegram() {
  local msg="$1"
  local dedupe_tag="${2:-}"  # optional, used to suppress duplicate sends

  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    if [ -n "$dedupe_tag" ]; then
      mkdir -p "$NOTIFY_LOCK_DIR"
      local lock_file="$NOTIFY_LOCK_DIR/${dedupe_tag}.lock"
      # If this lock exists, skip duplicate notification for this run/state.
      if [ -f "$lock_file" ]; then
        return 0
      fi
      date '+%F %T' > "$lock_file"
    fi

    curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -H 'Content-Type: application/json' \
      -d "{\"chat_id\":\"${TELEGRAM_CHAT_ID}\",\"text\":\"${msg}\"}" >/dev/null || true
  fi
}

should_suppress_failure_alert() {
  local fail_class="$1"
  local fail_detail="$2"
  local now_ts
  now_ts="$(date +%s)"
  local new_sig="${fail_class}|${fail_detail}"

  if [ -f "$FAILURE_STATE_FILE" ]; then
    local prev_ts=""
    local prev_sig=""
    prev_ts="$(cut -d'|' -f1 < "$FAILURE_STATE_FILE" 2>/dev/null || true)"
    prev_sig="$(cut -d'|' -f2- < "$FAILURE_STATE_FILE" 2>/dev/null || true)"

    if [ -n "$prev_ts" ] && [ -n "$prev_sig" ]; then
      local age=$((now_ts - prev_ts))
      if [ "$prev_sig" = "$new_sig" ] && [ "$age" -lt "$FAILURE_COOLDOWN_SEC" ]; then
        return 0
      fi
    fi
  fi

  mkdir -p "$(dirname "$FAILURE_STATE_FILE")"
  echo "${now_ts}|${new_sig}" > "$FAILURE_STATE_FILE"
  return 1
}

send_final_status() {
  # Always attempt one terminal notification (success/failure).
  # Uses dedupe key so EXIT trap + explicit failure paths can't spam.
  local rc=$?

  if [ "$FINAL_STATUS" = "success" ]; then
    send_telegram "✅ [${RUN_ID}] Nightly autonomous run completed on ${RUN_HOST}" "${RUN_ID}_done"
    return
  fi

  local fail_class="${FINAL_CLASS:-ENV}"
  local fail_detail="${FINAL_DETAIL:-unknown error}"

  if [ $rc -eq 0 ]; then
    send_telegram "✅ [${RUN_ID}] Nightly autonomous run completed on ${RUN_HOST} (attempt ${FINAL_ATTEMPT}/${ORCH_MAX_ATTEMPTS})" "${RUN_ID}_done"
  else
    if [ "$SUPPRESS_FINAL_FAIL_ALERT" = "1" ]; then
      return
    fi
    send_telegram "❌ [${RUN_ID}] [${fail_class}] Nightly autonomous run failed (exit=${rc}) on ${RUN_HOST} — ${fail_detail}" "${RUN_ID}_failed"
  fi
}

trap send_final_status EXIT

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
  echo "[$RUN_TS] [ENV] Nightly autonomous run started (run_id=${RUN_ID} host=${RUN_HOST})"

  PREFLIGHT_OK="0"
  for pre_attempt in 1 2; do
    if bash "$PREFLIGHT_SCRIPT"; then
      PREFLIGHT_OK="1"
      log_line "[ENV] Preflight passed on attempt ${pre_attempt}/2"
      break
    fi
    log_line "[ENV] Preflight failed on attempt ${pre_attempt}/2"
    [ "$pre_attempt" -lt 2 ] && sleep 10
  done

  if [ "$PREFLIGHT_OK" != "1" ]; then
    MSG="[$(date '+%F %T')] [ENV] Nightly preflight failed after retry (run_id=${RUN_ID})"
    echo "$MSG"
    FINAL_CLASS="ENV"
    FINAL_DETAIL="preflight failed after retry"
    if should_suppress_failure_alert "$FINAL_CLASS" "$FINAL_DETAIL"; then
      SUPPRESS_FINAL_FAIL_ALERT="1"
      log_line "[NOTIFY] Suppressed duplicate failure alert (${FINAL_CLASS}: ${FINAL_DETAIL})"
    fi
    exit 1
  fi

  if [ ! -f "$ORCH_FILE" ]; then
    MSG="[$(date '+%F %T')] [ENV] Missing orchestrator file: $ORCH_FILE (run_id=${RUN_ID})"
    echo "$MSG"
    FINAL_CLASS="ENV"
    FINAL_DETAIL="missing orchestrator file"
    if should_suppress_failure_alert "$FINAL_CLASS" "$FINAL_DETAIL"; then
      SUPPRESS_FINAL_FAIL_ALERT="1"
      log_line "[NOTIFY] Suppressed duplicate failure alert (${FINAL_CLASS}: ${FINAL_DETAIL})"
    fi
    exit 1
  fi

  RC=1
  ORCH_OUTPUT=""
  for attempt in $(seq 1 "$ORCH_MAX_ATTEMPTS"); do
    FINAL_ATTEMPT="$attempt"
    log_line "[ENV] Orchestrator attempt ${attempt}/${ORCH_MAX_ATTEMPTS}"

    set +e
    ORCH_OUTPUT="$($VENV_PYTHON "$ORCH_FILE" 2>&1)"
    RC=$?
    set -e

    if [ $RC -eq 0 ]; then
      break
    fi

    if [ "$attempt" -lt "$ORCH_MAX_ATTEMPTS" ]; then
      log_line "[ENV] Orchestrator failed on attempt ${attempt}/${ORCH_MAX_ATTEMPTS}; retrying in ${ORCH_RETRY_DELAY_SEC}s"
      sleep "$ORCH_RETRY_DELAY_SEC"
    fi
  done

  if [ $RC -ne 0 ]; then
    CLASS="$(classify_failure "$ORCH_OUTPUT")"
    MSG="[$(date '+%F %T')] [${CLASS}] Nightly run failed after ${FINAL_ATTEMPT}/${ORCH_MAX_ATTEMPTS} attempts (exit=$RC run_id=${RUN_ID})"
    echo "$MSG"
    echo "$ORCH_OUTPUT"
    FINAL_CLASS="$CLASS"
    FINAL_DETAIL="orchestrator error after retries"
    if should_suppress_failure_alert "$FINAL_CLASS" "$FINAL_DETAIL"; then
      SUPPRESS_FINAL_FAIL_ALERT="1"
      log_line "[NOTIFY] Suppressed duplicate failure alert (${FINAL_CLASS}: ${FINAL_DETAIL})"
    fi
    exit $RC
  fi

  MSG="[$(date '+%F %T')] [SUCCESS] Nightly autonomous run completed (run_id=${RUN_ID} attempt=${FINAL_ATTEMPT}/${ORCH_MAX_ATTEMPTS})"
  echo "$MSG"
  FINAL_STATUS="success"
} >> "$LOG_FILE" 2>&1
