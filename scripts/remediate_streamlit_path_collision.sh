#!/bin/bash

set -euo pipefail

SERVER="${1:-root@100.95.125.112}"
APP_DIR="/opt/darrian-budget"
CC_DIR="/opt/college-confused"
CONTAINER="darrian-budget"
CC_SERVICE="college-confused"

echo "Checking SSH connectivity to ${SERVER}..."
ssh -o BatchMode=yes -o ConnectTimeout=8 "$SERVER" "echo connected >/dev/null"

echo "Updating ${APP_DIR} and pruning stale Streamlit page collisions..."
ssh "$SERVER" "cd ${APP_DIR} && git fetch origin && git reset --hard origin/main && git checkout main && git pull origin main && python3 scripts/prune_stale_streamlit_pages.py --repo-dir . --apply"

echo "Restarting ${CONTAINER} container..."
ssh "$SERVER" "docker restart ${CONTAINER} >/dev/null && sleep 8 && curl -sf http://localhost:8501/_stcore/health >/dev/null"

echo "Syncing College Confused serving tree with delete semantics..."
ssh "$SERVER" "rsync -a --delete --exclude='__pycache__' ${APP_DIR}/pages/ ${CC_DIR}/pages/ && rsync -a --delete --exclude='__pycache__' ${APP_DIR}/utils/ ${CC_DIR}/utils/ && systemctl restart ${CC_SERVICE} && sleep 5"

echo "Verifying no duplicate inferred page pathnames remain in ${APP_DIR}/pages..."
ssh "$SERVER" "cd ${APP_DIR} && dupes=\$(find pages -maxdepth 1 -name '*.py' -print | sed 's#^pages/##' | awk '{name=\$0; sub(/^[0-9]+_/, \"\", name); sub(/\\.py$/, \"\", name); print name}' | sort | uniq -d) && if [ -n \"\$dupes\" ]; then echo \"Duplicate pathnames still present:\" && echo \"\$dupes\" && exit 1; fi && echo 'No duplicate pathnames remain.'"

echo "Remediation complete."