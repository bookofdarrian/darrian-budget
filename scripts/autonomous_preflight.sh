#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/darrian-budget}"
VENV_PYTHON="${VENV_PYTHON:-$REPO_DIR/venv/bin/python3}"
REQ_FILE="${REQ_FILE:-$REPO_DIR/requirements.txt}"
REQ_DEV_FILE="${REQ_DEV_FILE:-$REPO_DIR/requirements-dev.txt}"

fail() {
  echo "[ENV] $1" >&2
  exit 1
}

echo "[ENV] Autonomous preflight starting..."

[ -d "$REPO_DIR" ] || fail "Repo directory not found: $REPO_DIR"
[ -x "$VENV_PYTHON" ] || fail "Expected venv python missing: $VENV_PYTHON"
[ -f "$REQ_FILE" ] || fail "Missing requirements.txt at $REQ_FILE"
[ -f "$REQ_DEV_FILE" ] || fail "Missing requirements-dev.txt at $REQ_DEV_FILE"

PY_VER="$($VENV_PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
$VENV_PYTHON - <<'PYCHK'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(1)
PYCHK
if [ $? -ne 0 ]; then
  fail "Python version must be >= 3.11 (found $PY_VER)"
fi

echo "[ENV] Python OK: $PY_VER"

"$VENV_PYTHON" -m pip --disable-pip-version-check check >/dev/null || fail "pip dependency health check failed"

"$VENV_PYTHON" -m pytest --version >/dev/null 2>&1 || fail "pytest unavailable in autonomous runtime"

if ! "$VENV_PYTHON" -m pip show pytest-asyncio >/dev/null 2>&1; then
  fail "pytest-asyncio missing"
fi
if ! "$VENV_PYTHON" -m pip show pytest-cov >/dev/null 2>&1; then
  fail "pytest-cov missing"
fi

echo "[ENV] Preflight PASS"
