#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Start Agent Dashboard (Dash — no Streamlit)
# Usage:
#   Local:    bash start_agent_dashboard.sh
#   Homelab:  bash start_agent_dashboard.sh --server
# ──────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$REPO_DIR/venv"
APP_FILE="$REPO_DIR/agent_dashboard/app.py"
PORT="${DASHBOARD_PORT:-8502}"
LOG_FILE="/var/log/overnight-dev.log"

# ── Colour helpers ────────────────────────────────────────────
green()  { echo -e "\033[0;32m$*\033[0m"; }
yellow() { echo -e "\033[0;33m$*\033[0m"; }
red()    { echo -e "\033[0;31m$*\033[0m"; }

green "🤖  Agent Dashboard Launcher"
echo   "  Repo:  $REPO_DIR"
echo   "  App:   $APP_FILE"
echo   "  Port:  $PORT"
echo

# ── Activate venv ─────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    green "  ✅  venv activated: $VENV_DIR"
else
    yellow "  ⚠️  No venv found at $VENV_DIR — using system Python"
fi

# ── Install / upgrade dash if missing ────────────────────────
if ! python3 -c "import dash" 2>/dev/null; then
    yellow "  📦  Installing dash + dash-bootstrap-components..."
    pip install -q dash>=2.16.0 dash-bootstrap-components>=1.5.0
fi

# ── Kill any existing dashboard process ──────────────────────
if lsof -ti:"$PORT" >/dev/null 2>&1; then
    yellow "  ⚠️  Port $PORT in use — killing old process..."
    lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# ── Launch ───────────────────────────────────────────────────
green "  🚀  Starting dashboard on http://0.0.0.0:$PORT ..."
echo

export DASHBOARD_PORT="$PORT"
export AGENT_LOG_FILE="$LOG_FILE"

# Run in foreground so the terminal shows output; press Ctrl+C to stop.
exec python3 "$APP_FILE"
