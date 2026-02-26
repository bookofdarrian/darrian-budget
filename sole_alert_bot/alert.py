#!/usr/bin/env python3
"""
alert.py — 404 Sole Archive Price Alert Bot
Checks eBay + Mercari every 30 min for your inventory.
Fires Telegram alerts when profit opportunity > MIN_PROFIT_THRESHOLD.

3 alert types:
  🟢 eBay Sell Signal   — "Jordan 1 Chicago Sz 10: eBay avg $285, cost $180, net profit $87 → list it now"
  🟢 Mercari Sell Signal — Same but Mercari (10% fees vs eBay's 13% = more profit per flip)
  🔵 Arb Opportunity    — "Nike Dunk Panda Sz 11 on Mercari $95, eBay avg $165 → buy + flip for $52 profit"

Usage:
    python alert.py              # normal run
    python alert.py --dry-run    # print alerts, don't send Telegram messages
    python alert.py --test       # send one test Telegram message and exit
    python alert.py --status     # print last 10 alerts + inventory count and exit

Cron (add via: crontab -e):
    */30 8-23 * * * /usr/bin/python3 /opt/sole-alert/alert.py >> /var/log/sole-alert.log 2>&1
"""

import os
import sys
import logging
import argparse
from datetime import datetime

import psycopg2
import requests

from ebay_search import get_ebay_token, ebay_avg_price, ebay_low_price
from mercari_search import mercari_avg_price, mercari_low_price

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config from environment ───────────────────────────────────────────────────
DATABASE_URL        = os.environ["DATABASE_URL"]           # postgres://...
TELEGRAM_TOKEN      = os.environ["TELEGRAM_BOT_TOKEN"]     # from @BotFather
TELEGRAM_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]       # your personal chat ID

# eBay credentials — read from env first, fall back to app_settings table
# (so you can set them once in the budget app UI and the bot picks them up)
EBAY_CLIENT_ID      = os.environ.get("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET  = os.environ.get("EBAY_CLIENT_SECRET", "")


def _get_db_setting(conn, key: str, default: str = "") -> str:
    """Read a value from the app_settings table (shared with the budget app)."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row and row[0] else default
    except Exception:
        return default


def _load_config_from_db(conn):
    """
    Pull eBay credentials + alert thresholds from the app_settings table.
    Environment variables take priority over DB values.
    """
    global EBAY_CLIENT_ID, EBAY_CLIENT_SECRET
    global MIN_PROFIT_THRESHOLD, EBAY_FEE_RATE, EBAY_FEE_FIXED
    global MERCARI_FEE_RATE, MERCARI_FEE_FIXED

    if not EBAY_CLIENT_ID:
        EBAY_CLIENT_ID = _get_db_setting(conn, "ebay_client_id", "")
    if not EBAY_CLIENT_SECRET:
        EBAY_CLIENT_SECRET = _get_db_setting(conn, "ebay_client_secret", "")

    # Alert thresholds — env var > DB setting > hardcoded default
    MIN_PROFIT_THRESHOLD = float(
        os.environ.get("MIN_PROFIT_THRESHOLD")
        or _get_db_setting(conn, "min_profit_threshold", "30")
    )
    EBAY_FEE_RATE = float(
        os.environ.get("EBAY_FEE_RATE")
        or _get_db_setting(conn, "ebay_fee_rate", "0.129")
    )
    EBAY_FEE_FIXED = float(os.environ.get("EBAY_FEE_FIXED", "0.30"))
    MERCARI_FEE_RATE = float(
        os.environ.get("MERCARI_FEE_RATE")
        or _get_db_setting(conn, "mercari_fee_rate", "0.10")
    )
    MERCARI_FEE_FIXED = float(os.environ.get("MERCARI_FEE_FIXED", "0.30"))


# Placeholders — overwritten by _load_config_from_db() at runtime
MIN_PROFIT_THRESHOLD = 30.0
EBAY_FEE_RATE        = 0.129
EBAY_FEE_FIXED       = 0.30
MERCARI_FEE_RATE     = 0.10
MERCARI_FEE_FIXED    = 0.30


# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(message: str, dry_run: bool = False) -> bool:
    """Send a Telegram message. Returns True on success."""
    if dry_run:
        print(f"\n[DRY RUN] Would send Telegram:\n{message}\n")
        return True
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return True
        log.warning("Telegram send failed: HTTP %s — %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        log.error("Telegram error: %s", e)
        return False


# ── Database ──────────────────────────────────────────────────────────────────
def get_inventory(conn) -> list[tuple]:
    """
    Load all items currently in inventory from sole_archive.
    Returns list of (item, size, buy_price, notes).
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT item, size, buy_price, notes
            FROM sole_archive
            WHERE status = 'inventory'
            ORDER BY item, size
        """)
        return cur.fetchall()


def log_price_check(conn, item: str, size: str,
                    ebay_avg: float, ebay_low: float,
                    mercari_avg: float, mercari_low: float):
    """Write a price snapshot to price_history for charting in the budget app."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO price_history
                (item, size, ebay_avg, ebay_low, mercari_avg, mercari_low, checked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (item, size, ebay_avg or None, ebay_low or None,
              mercari_avg or None, mercari_low or None, datetime.utcnow()))
    conn.commit()


def already_alerted_recently(conn, item: str, size: str,
                              platform: str, hours: int = 4) -> bool:
    """
    Prevent alert spam — don't re-alert for the same item+platform
    within the last `hours` hours.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM alert_log
            WHERE item = %s AND size = %s AND platform = %s
              AND alerted_at > NOW() - INTERVAL '%s hours'
            LIMIT 1
        """, (item, size, platform, hours))
        return cur.fetchone() is not None


def record_alert(conn, item: str, size: str, platform: str,
                 sell_price: float, profit: float):
    """Log that we sent an alert so we don't spam."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO alert_log (item, size, platform, sell_price, profit, alerted_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (item, size, platform, sell_price, profit, datetime.utcnow()))
    conn.commit()


# ── Profit calculation ────────────────────────────────────────────────────────
def calc_profit_ebay(sell_price: float, cost_basis: float) -> float:
    """Net profit after eBay fees."""
    fees = (sell_price * EBAY_FEE_RATE) + EBAY_FEE_FIXED
    return round(sell_price - fees - cost_basis, 2)


def calc_profit_mercari(sell_price: float, cost_basis: float) -> float:
    """Net profit after Mercari fees."""
    fees = (sell_price * MERCARI_FEE_RATE) + MERCARI_FEE_FIXED
    return round(sell_price - fees - cost_basis, 2)


# ── Status report ─────────────────────────────────────────────────────────────
def print_status(conn):
    """Print a quick status summary — inventory count + last 10 alerts."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sole_archive WHERE status = 'inventory'")
        inv_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM alert_log")
        total_alerts = cur.fetchone()[0]

        cur.execute("""
            SELECT alerted_at, platform, item, size, profit
            FROM alert_log
            ORDER BY alerted_at DESC
            LIMIT 10
        """)
        recent = cur.fetchall()

    print(f"\n{'='*60}")
    print(f"  404 Sole Archive Alert Bot — Status")
    print(f"{'='*60}")
    print(f"  Inventory items being monitored : {inv_count}")
    print(f"  Total alerts sent (all time)    : {total_alerts}")
    print(f"  Min profit threshold            : ${MIN_PROFIT_THRESHOLD:.0f}")
    print(f"  eBay fee rate                   : {EBAY_FEE_RATE*100:.1f}%")
    print(f"  Mercari fee rate                : {MERCARI_FEE_RATE*100:.1f}%")
    print(f"\n  Last 10 alerts:")
    if recent:
        for row in recent:
            ts, platform, item, size, profit = row
            platform_icon = {"ebay": "🟢", "mercari": "🟢", "arb": "🔵"}.get(platform, "•")
            print(f"    {platform_icon} {str(ts)[:16]}  {platform:<8}  {item} Sz {size}  profit=${profit:.0f}")
    else:
        print("    (no alerts sent yet)")
    print(f"{'='*60}\n")


# ── Main loop ─────────────────────────────────────────────────────────────────
def run(dry_run: bool = False):
    log.info("=== Sole Alert Bot starting (dry_run=%s) ===", dry_run)

    conn = psycopg2.connect(DATABASE_URL)

    # Load config from DB (eBay keys + thresholds set in the budget app UI)
    _load_config_from_db(conn)

    log.info(
        "Config: min_profit=$%.0f  ebay_fee=%.1f%%  mercari_fee=%.1f%%",
        MIN_PROFIT_THRESHOLD, EBAY_FEE_RATE * 100, MERCARI_FEE_RATE * 100
    )

    inventory = get_inventory(conn)

    if not inventory:
        log.info("No inventory items found — add shoes in the budget app → Business Tracker.")
        conn.close()
        return

    log.info("Loaded %d inventory items.", len(inventory))

    if not EBAY_CLIENT_ID or not EBAY_CLIENT_SECRET:
        log.warning(
            "eBay credentials not found in env or DB. "
            "Add them in the budget app → Business Tracker → eBay API Credentials."
        )

    # Get eBay token once (valid for 2 hours)
    ebay_token = get_ebay_token(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET) if EBAY_CLIENT_ID else None
    if not ebay_token:
        log.warning("Could not get eBay token — eBay checks will be skipped.")

    alerts_sent = 0

    for item, size, cost_basis, notes in inventory:
        query = f"{item} size {size}" if size else item
        log.info("Checking: %s", query)

        # ── eBay ──────────────────────────────────────────────────────────────
        e_avg = ebay_avg_price(query, ebay_token) if ebay_token else 0.0
        e_low = ebay_low_price(query, ebay_token) if ebay_token else 0.0

        # ── Mercari ───────────────────────────────────────────────────────────
        m_avg = mercari_avg_price(query)
        m_low = mercari_low_price(query)

        log.info(
            "  eBay avg=$%.0f low=$%.0f | Mercari avg=$%.0f low=$%.0f | Cost=$%.0f",
            e_avg, e_low, m_avg, m_low, cost_basis
        )

        # Log to Postgres for price history chart
        try:
            log_price_check(conn, item, size, e_avg, e_low, m_avg, m_low)
        except Exception as ex:
            log.warning("Could not log price check: %s", ex)
            conn.rollback()

        # ── 🟢 eBay sell signal (use avg price as realistic sell target) ──────
        if e_avg > 0:
            profit_ebay = calc_profit_ebay(e_avg, cost_basis)
            if profit_ebay >= MIN_PROFIT_THRESHOLD:
                if not already_alerted_recently(conn, item, size, "ebay"):
                    msg = (
                        f"🟢 <b>SELL SIGNAL — eBay</b>\n"
                        f"👟 <b>{item}</b> (Sz {size})\n"
                        f"💰 eBay avg: <b>${e_avg:.0f}</b> | Your cost: ${cost_basis:.0f}\n"
                        f"📈 Net profit: <b>${profit_ebay:.0f}</b> after {EBAY_FEE_RATE*100:.0f}% fees\n"
                        f"→ <b>List it now</b>\n"
                        f"🔗 <a href='https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}'>Search eBay</a>"
                    )
                    if send_telegram(msg, dry_run):
                        record_alert(conn, item, size, "ebay", e_avg, profit_ebay)
                        alerts_sent += 1
                        log.info("  ✅ eBay sell alert sent — profit $%.0f", profit_ebay)
                else:
                    log.info("  ⏭️  eBay alert suppressed (sent recently)")

        # ── 🟢 Mercari sell signal (use avg price) ────────────────────────────
        if m_avg > 0:
            profit_mercari = calc_profit_mercari(m_avg, cost_basis)
            if profit_mercari >= MIN_PROFIT_THRESHOLD:
                if not already_alerted_recently(conn, item, size, "mercari"):
                    msg = (
                        f"🟢 <b>SELL SIGNAL — Mercari</b>\n"
                        f"👟 <b>{item}</b> (Sz {size})\n"
                        f"💰 Mercari avg: <b>${m_avg:.0f}</b> | Your cost: ${cost_basis:.0f}\n"
                        f"📈 Net profit: <b>${profit_mercari:.0f}</b> after {MERCARI_FEE_RATE*100:.0f}% fees\n"
                        f"💡 Mercari = {(EBAY_FEE_RATE - MERCARI_FEE_RATE)*100:.0f}% less fees than eBay\n"
                        f"→ <b>List it now</b>\n"
                        f"🔗 <a href='https://www.mercari.com/search/?keyword={query.replace(' ', '+')}'>Search Mercari</a>"
                    )
                    if send_telegram(msg, dry_run):
                        record_alert(conn, item, size, "mercari", m_avg, profit_mercari)
                        alerts_sent += 1
                        log.info("  ✅ Mercari sell alert sent — profit $%.0f", profit_mercari)
                else:
                    log.info("  ⏭️  Mercari alert suppressed (sent recently)")

        # ── 🔵 Arb signal (Mercari low → flip on eBay) ───────────────────────
        # Higher bar: 1.5× threshold (you need to buy + ship + wait)
        if m_low > 0 and e_avg > 0:
            arb_profit = calc_profit_ebay(e_avg, m_low)
            if arb_profit >= MIN_PROFIT_THRESHOLD * 1.5:
                if not already_alerted_recently(conn, item, size, "arb"):
                    msg = (
                        f"🔵 <b>ARB OPPORTUNITY — Buy Mercari → Sell eBay</b>\n"
                        f"👟 <b>{item}</b> (Sz {size})\n"
                        f"🛒 Buy on Mercari: <b>${m_low:.0f}</b>\n"
                        f"💵 Sell on eBay avg: <b>${e_avg:.0f}</b>\n"
                        f"📈 Est. arb profit: <b>${arb_profit:.0f}</b> after eBay fees\n"
                        f"🔗 <a href='https://www.mercari.com/search/?keyword={query.replace(' ', '+')}'>Find on Mercari</a>"
                    )
                    if send_telegram(msg, dry_run):
                        record_alert(conn, item, size, "arb", m_low, arb_profit)
                        alerts_sent += 1
                        log.info("  ✅ Arb alert sent — profit $%.0f", arb_profit)
                else:
                    log.info("  ⏭️  Arb alert suppressed (sent recently)")

    conn.close()
    log.info("=== Done. %d alert(s) sent. ===", alerts_sent)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="404 Sole Archive Price Alert Bot")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print alerts without sending Telegram messages")
    parser.add_argument("--test", action="store_true",
                        help="Send a test Telegram message and exit")
    parser.add_argument("--status", action="store_true",
                        help="Print inventory count + last 10 alerts and exit")
    args = parser.parse_args()

    if args.test:
        ok = send_telegram(
            "✅ <b>404 Sole Archive Alert Bot — Test Message</b>\n\n"
            "Bot is connected and working! 🎉\n\n"
            "You'll receive 3 types of alerts here:\n"
            "🟢 <b>eBay Sell Signal</b> — when your inventory hits profitable eBay prices\n"
            "🟢 <b>Mercari Sell Signal</b> — same but Mercari (lower fees = more profit)\n"
            "🔵 <b>Arb Opportunity</b> — when a shoe is cheap on Mercari vs eBay avg\n\n"
            "Checks every 30 min, 8am–midnight. No spam — 4hr cooldown per item."
        )
        sys.exit(0 if ok else 1)

    conn = psycopg2.connect(DATABASE_URL)
    _load_config_from_db(conn)

    if args.status:
        print_status(conn)
        conn.close()
        sys.exit(0)

    conn.close()
    run(dry_run=args.dry_run)
