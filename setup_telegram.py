#!/usr/bin/env python3
"""
setup_telegram.py
=================
One-time Telegram bot setup for Peach State Savings.
Saves your bot token + chat ID to the app_settings DB table,
then sends a live test message to confirm it works.

STEP 1 — Get your bot token (2 min):
  1. Open Telegram → search @BotFather → tap START
  2. Send: /newbot
  3. Name it anything, e.g. "Darrian Dev Bot"
  4. Username must end in 'bot', e.g. "darrian_dev_bot"
  5. BotFather replies with your token — looks like:
     1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ

STEP 2 — Get your chat ID (1 min):
  1. Open Telegram → search your new bot → tap START or send any message
  2. Open this URL in your browser (replace YOUR_TOKEN):
     https://api.telegram.org/botYOUR_TOKEN/getUpdates
  3. Look for: "chat":{"id":123456789}  — that number is your chat ID

STEP 3 — Run this script:
  cd /Users/darrianbelcher/Downloads/darrian-budget
  source venv/bin/activate
  python3 setup_telegram.py --token "YOUR_TOKEN" --chat-id "YOUR_CHAT_ID"

  It will save to the DB and send a test message immediately.

STEP 4 — Also save to CT100 production DB (run from Mac):
  The script auto-saves to local SQLite. For CT100 production PostgreSQL,
  run the same command via SSH:

  ssh root@100.95.125.112 "cd /opt/darrian-budget && source venv/bin/activate && \
    python3 setup_telegram.py --token 'YOUR_TOKEN' --chat-id 'YOUR_CHAT_ID'"

Usage:
  python3 setup_telegram.py --token "1234567..." --chat-id "123456789"
  python3 setup_telegram.py --test          # test with existing saved credentials
  python3 setup_telegram.py --show          # show what's currently saved
"""

import sys
import argparse
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_setting, set_setting, init_db


def send_test_message(token: str, chat_id: str, message: str) -> bool:
    """Send a Telegram message. Returns True on success."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        if r.status_code == 200:
            return True
        print(f"  ❌ Telegram API error {r.status_code}: {r.text[:200]}")
        return False
    except requests.exceptions.ConnectionError:
        print("  ❌ No internet connection — check your network and try again")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Set up Telegram bot credentials for Peach State Savings",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--token",   help="Telegram bot token from @BotFather")
    parser.add_argument("--chat-id", dest="chat_id", help="Your Telegram chat ID")
    parser.add_argument("--test",    action="store_true", help="Send a test with saved credentials")
    parser.add_argument("--show",    action="store_true", help="Show what's currently saved")
    args = parser.parse_args()

    init_db()
    print("\n🤖 Peach State Savings — Telegram Setup\n" + "="*45)

    # ── Show current state ───────────────────────────────────
    if args.show:
        token   = get_setting("telegram_bot_token")
        chat_id = get_setting("telegram_chat_id")
        print(f"telegram_bot_token: {'SET (' + token[:20] + '...)' if token else 'NOT SET'}")
        print(f"telegram_chat_id:   {chat_id if chat_id else 'NOT SET'}")
        return 0

    # ── Test with existing credentials ──────────────────────
    if args.test:
        token   = get_setting("telegram_bot_token")
        chat_id = get_setting("telegram_chat_id")
        if not token or not chat_id:
            print("❌ Credentials not saved yet. Run: python3 setup_telegram.py --token '...' --chat-id '...'")
            return 1
        print(f"📤 Sending test message to chat {chat_id}...")
        msg = (
            "🍑 <b>Peach State Savings</b> — Test Message\n\n"
            "✅ Telegram is working!\n"
            "You'll receive overnight dev summaries and price alerts here."
        )
        if send_test_message(token, chat_id, msg):
            print("✅ Test message sent! Check your Telegram.")
            return 0
        return 1

    # ── Save new credentials ─────────────────────────────────
    if not args.token or not args.chat_id:
        parser.print_help()
        print("\n⚠️  Both --token and --chat-id are required.\n")
        return 1

    token   = args.token.strip()
    chat_id = args.chat_id.strip()

    # Validate token format
    if ":" not in token or len(token) < 30:
        print("❌ Token format looks wrong. Should be like: 1234567890:ABCdefGHIjklMNO...")
        return 1

    print(f"💾 Saving telegram_bot_token to app_settings DB...")
    set_setting("telegram_bot_token", token)

    print(f"💾 Saving telegram_chat_id ({chat_id}) to app_settings DB...")
    set_setting("telegram_chat_id", chat_id)

    print(f"\n📤 Sending test message to confirm it works...")
    msg = (
        "🍑 <b>Peach State Savings</b> — Telegram Connected!\n\n"
        "✅ Your credentials are saved. You'll now receive:\n"
        "  • 🌙 Overnight dev summaries (what was built)\n"
        "  • 👟 SoleOps price alerts\n"
        "  • 📊 Weekly financial digests\n"
        "  • 🚨 Uptime alerts\n\n"
        "You're all set, Darrian. 🎉"
    )
    if send_test_message(token, chat_id, msg):
        print("\n✅ Telegram is live! Check your phone — message should be there now.")
        print(f"\nTo also save on CT100 production DB, run:")
        print(f"  ssh root@100.95.125.112 \"cd /opt/darrian-budget && source venv/bin/activate && \\")
        print(f"    python3 setup_telegram.py --token '{token[:20]}...' --chat-id '{chat_id}'\"")
    else:
        print("\n⚠️  Credentials saved to DB but test message failed.")
        print("   Check token and chat ID — make sure you messaged the bot first.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
