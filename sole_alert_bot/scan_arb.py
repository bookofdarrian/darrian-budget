#!/usr/bin/env python3
"""
scan_arb.py — Proactive Mercari→eBay Arbitrage Scanner
Searches Mercari for cheap sneakers (NOT in your inventory) and checks
if they can be flipped on eBay for profit.

This runs separately from alert.py — add it to cron to run a few times a day:
    0 9,13,18 * * * /usr/bin/python3 /opt/sole-alert/scan_arb.py >> /var/log/sole-alert.log 2>&1

Usage:
    python scan_arb.py              # scan and send Telegram alerts
    python scan_arb.py --dry-run    # print results, don't send Telegram
    python scan_arb.py --queries "Jordan 1,Yeezy 350,Dunk Low"  # custom search terms
"""

import os
import sys
import logging
import argparse
from datetime import datetime

import psycopg2
import requests

from ebay_search import get_ebay_token, ebay_avg_price
from mercari_search import mercari_search

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config (with DB fallback for Telegram) ────────────────────────────────────
DATABASE_URL     = os.environ.get("DATABASE_URL", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
EBAY_CLIENT_ID   = os.environ.get("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET", "")

# Sneaker search terms to scan on Mercari
# These are the most flippable categories — edit to match your expertise
DEFAULT_QUERIES = [
    "Jordan 1 Retro High",
    "Jordan 1 Low",
    "Jordan 4 Retro",
    "Nike Dunk Low",
    "Nike Dunk High",
    "Yeezy 350 V2",
    "Yeezy 700",
    "New Balance 550",
    "New Balance 2002R",
    "Air Force 1",
    "Travis Scott",
    "Off White Nike",
]

# Only alert on listings under this price (avoid expensive grails)
MAX_BUY_PRICE = float(os.environ.get("ARB_MAX_BUY_PRICE", "300"))

# Minimum arb profit to alert on
MIN_ARB_PROFIT = float(os.environ.get("ARB_MIN_PROFIT", "45"))

# eBay fee defaults (overridden by DB settings if available)
EBAY_FEE_RATE  = float(os.environ.get("EBAY_FEE_RATE", "0.129"))
EBAY_FEE_FIXED = float(os.environ.get("EBAY_FEE_FIXED", "0.30"))


def _get_db_setting(conn, key: str, default: str = "") -> str:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row and row[0] else default
    except Exception:
        return default


def _load_config_from_db(conn):
    global EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_FEE_RATE, MIN_ARB_PROFIT
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

    # Telegram — fall back to DB if env vars not set
    if not TELEGRAM_TOKEN:
        TELEGRAM_TOKEN = _get_db_setting(conn, "telegram_bot_token", "")
    if not TELEGRAM_CHAT_ID:
        TELEGRAM_CHAT_ID = _get_db_setting(conn, "telegram_chat_id", "")

    if not EBAY_CLIENT_ID:
        EBAY_CLIENT_ID = _get_db_setting(conn, "ebay_client_id", "")
    if not EBAY_CLIENT_SECRET:
        EBAY_CLIENT_SECRET = _get_db_setting(conn, "ebay_client_secret", "")
    EBAY_FEE_RATE = float(
        os.environ.get("EBAY_FEE_RATE")
        or _get_db_setting(conn, "ebay_fee_rate", "0.129")
    )
    # Use 1.5× the standard threshold for arb (higher bar since you need to buy first)
    base_thresh = float(
        os.environ.get("MIN_PROFIT_THRESHOLD")
        or _get_db_setting(conn, "min_profit_threshold", "30")
    )
    MIN_ARB_PROFIT = base_thresh * 1.5


def send_telegram(message: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"\n[DRY RUN] Would send:\n{message}\n")
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
        return r.status_code == 200
    except Exception as e:
        log.error("Telegram error: %s", e)
        return False


def already_alerted_recently(conn, item: str, size: str, platform: str, hours: int = 6) -> bool:
    """Arb scanner uses 6hr cooldown (longer than sell signals)."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM alert_log
                WHERE item = %s AND size = %s AND platform = %s
                  AND alerted_at > NOW() - INTERVAL '%s hours'
                LIMIT 1
            """, (item, size, platform, hours))
            return cur.fetchone() is not None
    except Exception:
        return False


def record_alert(conn, item: str, size: str, platform: str,
                 sell_price: float, profit: float):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alert_log (item, size, platform, sell_price, profit, alerted_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (item, size, platform, sell_price, profit, datetime.utcnow()))
        conn.commit()
    except Exception as e:
        log.warning("Could not record alert: %s", e)
        conn.rollback()


def calc_profit_ebay(sell_price: float, cost_basis: float) -> float:
    fees = (sell_price * EBAY_FEE_RATE) + EBAY_FEE_FIXED
    return round(sell_price - fees - cost_basis, 2)


def scan(queries: list[str], dry_run: bool = False):
    log.info("=== Arb Scanner starting — %d queries ===", len(queries))

    conn = psycopg2.connect(DATABASE_URL)
    _load_config_from_db(conn)

    log.info("Config: min_arb_profit=$%.0f  max_buy=$%.0f  ebay_fee=%.1f%%",
             MIN_ARB_PROFIT, MAX_BUY_PRICE, EBAY_FEE_RATE * 100)

    if not EBAY_CLIENT_ID:
        log.error("No eBay credentials — set them in the budget app or env vars. Exiting.")
        conn.close()
        return

    ebay_token = get_ebay_token(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET)
    if not ebay_token:
        log.error("Could not get eBay token. Exiting.")
        conn.close()
        return

    alerts_sent = 0

    for query in queries:
        log.info("Scanning Mercari for: %s", query)

        # Get cheap Mercari listings
        mercari_results = mercari_search(query, limit=30, status="on_sale")
        if not mercari_results:
            log.info("  No Mercari results for '%s'", query)
            continue

        # Filter to listings under MAX_BUY_PRICE
        cheap = [r for r in mercari_results if 0 < r["price"] <= MAX_BUY_PRICE]
        if not cheap:
            log.info("  No listings under $%.0f for '%s'", MAX_BUY_PRICE, query)
            continue

        log.info("  Found %d listings under $%.0f", len(cheap), MAX_BUY_PRICE)

        # Get eBay avg for this query
        e_avg = ebay_avg_price(query, ebay_token, limit=20)
        if e_avg <= 0:
            log.info("  No eBay data for '%s' — skipping", query)
            continue

        log.info("  eBay avg: $%.0f", e_avg)

        # Check each cheap Mercari listing for arb potential
        for listing in cheap:
            mercari_price = listing["price"]
            arb_profit = calc_profit_ebay(e_avg, mercari_price)

            if arb_profit < MIN_ARB_PROFIT:
                continue

            # Use listing name as item identifier for dedup
            item_name = listing["name"][:60]
            size_str = ""  # Mercari doesn't always expose size in search results

            if already_alerted_recently(conn, item_name, size_str, "arb"):
                log.info("  ⏭️  Arb alert suppressed for: %s", item_name)
                continue

            log.info("  🔵 ARB FOUND: Buy $%.0f → Sell $%.0f → Profit $%.0f | %s",
                     mercari_price, e_avg, arb_profit, item_name[:50])

            msg = (
                f"🔵 <b>ARB OPPORTUNITY</b>\n"
                f"👟 <b>{item_name}</b>\n"
                f"🛒 Listed on Mercari: <b>${mercari_price:.0f}</b>\n"
                f"💵 eBay avg for <i>{query}</i>: <b>${e_avg:.0f}</b>\n"
                f"📈 Est. profit after eBay fees: <b>${arb_profit:.0f}</b>\n"
                f"🔗 <a href='{listing['item_url']}'>View on Mercari</a>"
            )

            if send_telegram(msg, dry_run):
                record_alert(conn, item_name, size_str, "arb", e_avg, arb_profit)
                alerts_sent += 1

            # Max 3 arb alerts per query to avoid flooding
            if alerts_sent >= 3:
                break

        if alerts_sent >= 10:
            log.info("Reached 10 alerts — stopping to avoid spam.")
            break

    conn.close()
    log.info("=== Arb scan done. %d alert(s) sent. ===", alerts_sent)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mercari→eBay Arb Scanner")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print results without sending Telegram")
    parser.add_argument("--queries", type=str, default="",
                        help="Comma-separated search terms (overrides defaults)")
    args = parser.parse_args()

    queries = (
        [q.strip() for q in args.queries.split(",") if q.strip()]
        if args.queries
        else DEFAULT_QUERIES
    )

    scan(queries, dry_run=args.dry_run)
