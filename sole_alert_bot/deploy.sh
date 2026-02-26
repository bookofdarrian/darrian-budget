#!/bin/bash
# deploy.sh — Copy the Sole Alert Bot to CT100 and set it up.
#
# Usage (from your Mac, Tailscale connected):
#   chmod +x deploy.sh
#   ./deploy.sh
#
# What it does:
#   1. Creates /opt/sole-alert/ on CT100
#   2. Copies all bot files
#   3. Installs Python dependencies
#   4. Creates the DB tables (requires DATABASE_URL to be set on CT100)
#   5. Adds the cron jobs (alert every 30 min + arb scan 3x/day)
#   6. Sends a test Telegram message to confirm everything works

set -e

CT100="root@100.95.125.112"   # CT100 Tailscale IP
REMOTE_DIR="/opt/sole-alert"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   404 Sole Archive Alert Bot — Deploy to CT100       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Source : $SCRIPT_DIR"
echo "  Target : $CT100:$REMOTE_DIR"
echo ""

# ── 1. Create remote directory ────────────────────────────────────────────────
echo "→ [1/6] Creating $REMOTE_DIR on CT100..."
ssh "$CT100" "mkdir -p $REMOTE_DIR"
echo "  ✅ Done"

# ── 2. Copy files ─────────────────────────────────────────────────────────────
echo "→ [2/6] Copying bot files..."
scp "$SCRIPT_DIR/alert.py"          "$CT100:$REMOTE_DIR/"
scp "$SCRIPT_DIR/scan_arb.py"       "$CT100:$REMOTE_DIR/"
scp "$SCRIPT_DIR/ebay_search.py"    "$CT100:$REMOTE_DIR/"
scp "$SCRIPT_DIR/mercari_search.py" "$CT100:$REMOTE_DIR/"
scp "$SCRIPT_DIR/setup_db.sql"      "$CT100:$REMOTE_DIR/"
scp "$SCRIPT_DIR/requirements.txt"  "$CT100:$REMOTE_DIR/"
echo "  ✅ Files copied"

# ── 3. Install dependencies ───────────────────────────────────────────────────
echo "→ [3/6] Installing Python dependencies on CT100..."
ssh "$CT100" "pip3 install -r $REMOTE_DIR/requirements.txt --quiet"
echo "  ✅ Dependencies installed"

# ── 4. Create DB tables ───────────────────────────────────────────────────────
echo "→ [4/6] Creating database tables..."
ssh "$CT100" "
  if [ -z \"\$DATABASE_URL\" ]; then
    echo '  ⚠️  DATABASE_URL not set on CT100 — skipping DB setup.'
    echo '  Set it in /etc/environment then run:'
    echo '    psql \$DATABASE_URL -f $REMOTE_DIR/setup_db.sql'
  else
    psql \"\$DATABASE_URL\" -f $REMOTE_DIR/setup_db.sql -q
    echo '  ✅ DB tables created (sole_archive, app_settings, price_history, alert_log)'
  fi
"

# ── 5. Add cron jobs ──────────────────────────────────────────────────────────
echo "→ [5/6] Setting up cron jobs..."
CRON_ALERT="*/30 8-23 * * * /usr/bin/python3 $REMOTE_DIR/alert.py >> /var/log/sole-alert.log 2>&1"
CRON_ARB="0 9,13,18 * * * /usr/bin/python3 $REMOTE_DIR/scan_arb.py >> /var/log/sole-alert.log 2>&1"

ssh "$CT100" "
  # Remove any existing sole-alert cron entries, then add fresh
  (crontab -l 2>/dev/null | grep -v 'sole-alert'; \
   echo '# 404 Sole Archive Alert Bot'; \
   echo '$CRON_ALERT'; \
   echo '$CRON_ARB') | crontab -
  echo '  ✅ Cron jobs installed:'
  crontab -l | grep -A1 'sole-alert'
"

# ── 6. Test Telegram connection ───────────────────────────────────────────────
echo "→ [6/6] Testing Telegram connection..."
ssh "$CT100" "
  if [ -z \"\$TELEGRAM_BOT_TOKEN\" ] || [ -z \"\$TELEGRAM_CHAT_ID\" ]; then
    echo ''
    echo '  ⚠️  TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set on CT100.'
    echo '  Complete setup by running:'
    echo ''
    echo '    nano /etc/environment'
    echo ''
    echo '  Add these lines (fill in your real values):'
    echo '    DATABASE_URL=postgres://user:password@host.railway.app:5432/railway'
    echo '    TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    echo '    TELEGRAM_CHAT_ID=123456789'
    echo '    EBAY_CLIENT_ID=DarrianB-404Sole-PRD-xxxxxxxxxxxx-xxxxxxxx'
    echo '    EBAY_CLIENT_SECRET=PRD-xxxxxxxxxxxxxxxxxxxx-xxxxxxxx-xxxx-xxxx'
    echo ''
    echo '  Then reload and test:'
    echo '    source /etc/environment'
    echo '    python3 $REMOTE_DIR/alert.py --test'
  else
    python3 $REMOTE_DIR/alert.py --test && echo '  ✅ Test message sent — check Telegram!'
  fi
"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Deploy complete!                                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Cron schedule:"
echo "    alert.py  — every 30 min, 8am–midnight (sell signals + inventory arb)"
echo "    scan_arb.py — 9am, 1pm, 6pm daily (proactive Mercari→eBay arb scan)"
echo ""
echo "  Useful commands on CT100:"
echo "    python3 $REMOTE_DIR/alert.py --test      # test Telegram"
echo "    python3 $REMOTE_DIR/alert.py --dry-run   # preview alerts"
echo "    python3 $REMOTE_DIR/alert.py --status    # inventory + last 10 alerts"
echo "    python3 $REMOTE_DIR/scan_arb.py --dry-run  # preview arb scan"
echo "    tail -f /var/log/sole-alert.log           # watch live logs"
echo ""
echo "  Budget app → Business Tracker → 🤖 Sole Alert Bot section"
echo "  shows live alert history + price charts."
echo ""
