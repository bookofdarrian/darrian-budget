#!/bin/bash
# ============================================================
# College Confused — Correct Deployment Script
# Updated: 2026-03-22 — reflects actual production setup
#
# ACTUAL ARCHITECTURE:
#   collegeconfused.org → Nginx Proxy Manager → port 8502
#   port 8502 → college-confused systemd service
#   systemd working dir: /opt/college-confused  (NOT a git repo)
#   git repo: /opt/darrian-budget
#
#   Files must be COPIED from /opt/darrian-budget to /opt/college-confused
#   git pull alone does NOT update what the service serves
#
# Usage:
#   bash deploy_college_confused.sh
#   OR: bash deploy_college_confused.sh pages/80_cc_home.py  (single file)
# ============================================================

set -e

CC_SOURCE="/opt/darrian-budget"
CC_SERVE="/opt/college-confused"
SERVICE="college-confused"
SERVER="root@100.95.125.112"

echo ""
echo "🎓 College Confused — Deploy Script"
echo "====================================="
echo "  Source (git): $CC_SOURCE"
echo "  Serving dir:  $CC_SERVE  (systemd, port 8502)"
echo ""

# ── 1. Pull latest code to git repo ────────────────────────
echo "📥 Step 1/4: Pulling latest code to git repo..."
ssh "$SERVER" "cd $CC_SOURCE && git pull origin main 2>&1 | tail -3"
echo "✅ Git repo updated."
echo ""

# ── 2. Copy updated files to serving directory ─────────────
echo "📁 Step 2/4: Copying pages to $CC_SERVE..."

if [ -n "$1" ]; then
    # Single file mode: bash deploy_college_confused.sh pages/80_cc_home.py
    FILE="$1"
    echo "  Copying single file: $FILE"
    ssh "$SERVER" "cp $CC_SOURCE/$FILE $CC_SERVE/$FILE"
    echo "✅ Copied $FILE"
else
    # Full sync: copy all pages, utils, static, and root-level CC files
    echo "  Syncing pages/ ..."
    ssh "$SERVER" "rsync -av --delete --exclude='__pycache__' $CC_SOURCE/pages/ $CC_SERVE/pages/ 2>&1 | tail -5"
    echo "  Syncing utils/ ..."
    ssh "$SERVER" "rsync -av --delete --exclude='__pycache__' $CC_SOURCE/utils/ $CC_SERVE/utils/ 2>&1 | tail -3"
    echo "  Syncing static/ (photos, CSS, assets) ..."
    ssh "$SERVER" "rsync -av --exclude='__pycache__' $CC_SOURCE/static/ $CC_SERVE/static/ 2>&1 | tail -5"
    echo "  Copying cc_app.py → app.py (entry point) ..."
    ssh "$SERVER" "cp $CC_SOURCE/cc_app.py $CC_SERVE/app.py"
    echo "  Copying cc_global_css.py ..."
    ssh "$SERVER" "cp $CC_SOURCE/cc_global_css.py $CC_SERVE/cc_global_css.py 2>/dev/null || true"
    echo "✅ Full sync complete."
fi
echo ""

# ── 3. Restart the service ──────────────────────────────────
echo "🔄 Step 3/4: Restarting college-confused service..."
ssh "$SERVER" "systemctl restart $SERVICE && sleep 4"
ssh "$SERVER" "systemctl status $SERVICE --no-pager | grep -E 'Active|PID'"
echo ""

# ── 4. Verify ──────────────────────────────────────────────
echo "🔍 Step 4/4: Verifying serving directory is correct..."
ssh "$SERVER" "grep -n '1\.5M\|10+' $CC_SERVE/pages/80_cc_home.py 2>/dev/null | head -5 || echo 'No 80_cc_home.py found'"
echo ""

echo "====================================="
echo "✅ Deployment complete!"
echo "   Live: https://collegeconfused.org/cc_home"
echo ""
echo "⚠️  If changes still don't show: the service was just restarted."
echo "    Wait 5–10 seconds for Streamlit to fully boot, then reload."
echo "====================================="
