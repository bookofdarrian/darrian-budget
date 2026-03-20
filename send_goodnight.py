#!/usr/bin/env python3
"""Send a Telegram goodnight summary."""
import sys
sys.path.insert(0, "/Users/darrianbelcher/Downloads/darrian-budget")
from utils.db import get_setting, init_db
import requests
from datetime import datetime

init_db()
token   = get_setting("telegram_bot_token")
chat_id = get_setting("telegram_chat_id")

if not token or not chat_id:
    print("No Telegram credentials found.")
    sys.exit(1)

msg = (
    "🌙 <b>Goodnight, Darrian</b>\n\n"
    "✅ Tonight's fixes are live:\n"
    "  • <code>inject_soleops_css</code> ImportError → fixed (pages 68-70, 85-86)\n"
    "  • Test suite: 112/112 passing — 0 failures\n"
    "  • College Confused pages 87+88 deployed\n"
    "  • Commit <code>9c977c7</code> pushed to main\n\n"
    "🤖 Scheduled agent runner is armed — fires every 15 min on CT100.\n\n"
    f"⏰ {datetime.now().strftime('%a %b %d, %Y  %I:%M %p')}\n"
    "💤 Sleep well."
)

r = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
    timeout=10,
)
if r.status_code == 200:
    print("✅ Goodnight message sent!")
else:
    print(f"❌ {r.status_code}: {r.text[:200]}")
