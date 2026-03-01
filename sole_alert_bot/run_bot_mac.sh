#!/bin/bash
# run_bot_mac.sh — runs the eBay-only arb scanner from your Mac
# Mercari is skipped (blocked from Mac IPs) — works fully on CT100

cd /Users/darrianbelcher/Downloads/darrian-budget/sole_alert_bot
source /Users/darrianbelcher/Downloads/darrian-budget/venv/bin/activate

export DATABASE_URL="postgresql://postgres:jlYIqFpzBulCfWCxhZKoYrTWtscgAxRg@mainline.proxy.rlwy.net:51582/railway"
export TELEGRAM_BOT_TOKEN="8614943665:AAH-VgPnWqnPU7QJr3PXrtgHBQzPhv29qCU"
export TELEGRAM_CHAT_ID="6535912904"

echo "[$(date)] Running eBay arb scan..." >> /tmp/sole-alert-mac.log
python3 scan_arb.py >> /tmp/sole-alert-mac.log 2>&1
echo "[$(date)] Done." >> /tmp/sole-alert-mac.log
