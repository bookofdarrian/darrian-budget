#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/darrian-budget}"
LOG_FILE="${LOG_FILE:-/var/log/gym-autonomy-2h.log}"
RUNTIME_SECONDS="${RUNTIME_SECONDS:-7200}"

PRECHECK="${REPO_DIR}/scripts/autonomous_preflight.sh"
NIGHTLY="${REPO_DIR}/scripts/run_autonomous_nightly.sh"
TELEMETRY="${REPO_DIR}/scripts/nightly_telemetry_report.py"
SCHED_RUNNER="${REPO_DIR}/run_scheduled_agents.py"
VENV_PYTHON="${REPO_DIR}/venv/bin/python3"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
  echo "[$(date '+%F %T')] $1" | tee -a "$LOG_FILE"
}

if [ ! -x "$VENV_PYTHON" ]; then
  log "[ENV] Missing venv interpreter: $VENV_PYTHON"
  exit 1
fi

log "[START] 2-hour gym autonomy window starting"
log "[INFO] Repo: $REPO_DIR"

bash "$PRECHECK" | tee -a "$LOG_FILE"

set +e
bash "$NIGHTLY" | tee -a "$LOG_FILE"
NIGHTLY_RC=${PIPESTATUS[0]}
set -e

if [ $NIGHTLY_RC -ne 0 ]; then
  log "[WARN] Nightly wrapper exited non-zero ($NIGHTLY_RC); continuing to collect telemetry"
fi

set +e
"$VENV_PYTHON" "$SCHED_RUNNER" --dry-run --verbose | tee -a "$LOG_FILE"
SCHED_RC=${PIPESTATUS[0]}
set -e

if [ $SCHED_RC -ne 0 ]; then
  log "[WARN] Scheduled agent dry-run exited non-zero ($SCHED_RC)"
fi

END_TS=$(( $(date +%s) + RUNTIME_SECONDS ))
while [ "$(date +%s)" -lt "$END_TS" ]; do
  sleep 60
done

set +e
"$VENV_PYTHON" "$TELEMETRY" | tee -a "$LOG_FILE"
TELEM_RC=${PIPESTATUS[0]}
set -e

if [ $TELEM_RC -ne 0 ]; then
  log "[WARN] Telemetry report exited non-zero ($TELEM_RC)"
fi

log "[COMPLETE] 2-hour gym autonomy window finished"
log "[NEXT] Review PRs and approve human-gated production steps in GitHub Actions"
