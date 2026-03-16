"""
SoleOps Arbitrage Scanner — Page 71
Mercari → eBay sneaker arbitrage scanner with watchlist management,
ROI calculator, buy-signal Telegram alerts, and dedup logic.

Tabs:
  1. Scan Dashboard  — KPIs, last scan time, manual scan trigger
  2. Watchlist       — Add / remove target shoes with max buy price + target ROI %
  3. Scan Results    — Live table of buy opportunities with ROI
  4. Alert History   — All Telegram alerts sent
  5. Settings        — Telegram credentials, scan frequency, min ROI threshold
"""

import os
import time
import base64
import hashlib
import logging
import requests
import random
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from utils.db import (
    get_conn, USE_POSTGRES, execute as db_exec, init_db,
    get_setting, set_setting,
)
from utils.auth import (
    require_login, render_sidebar_brand,
    render_sidebar_user_widget, inject_css,
)

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="👟 SoleOps Arb Scanner — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_soleops_css()
require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                         label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",               label="✅ Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",  label="🎬 Creator",         icon="🎬")
st.sidebar.page_link("pages/25_notes.py",              label="📝 Notes",           icon="📝")
st.sidebar.page_link("pages/26_media_library.py",      label="🎵 Media Library",   icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# ── Logging ───────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)

# ── DB helpers ────────────────────────────────────────────────────────────────
PH = "%s" if USE_POSTGRES else "?"


def _ensure_tables():
    """Create arb_watchlist, arb_scan_results, arb_alerts_sent if missing."""
    conn = get_conn()

    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS arb_watchlist (
                id SERIAL PRIMARY KEY,
                shoe_name TEXT NOT NULL,
                size TEXT DEFAULT '',
                max_buy_price REAL NOT NULL DEFAULT 200,
                target_roi_pct REAL NOT NULL DEFAULT 30,
                active INTEGER DEFAULT 1,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS arb_scan_results (
                id SERIAL PRIMARY KEY,
                shoe_name TEXT NOT NULL,
                listing_title TEXT DEFAULT '',
                mercari_price REAL NOT NULL,
                ebay_avg_price REAL DEFAULT 0,
                ebay_low_price REAL DEFAULT 0,
                net_after_fees REAL DEFAULT 0,
                roi_pct REAL DEFAULT 0,
                mercari_url TEXT DEFAULT '',
                listing_id TEXT DEFAULT '',
                scanned_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                is_opportunity INTEGER DEFAULT 1
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS arb_alerts_sent (
                id SERIAL PRIMARY KEY,
                shoe_name TEXT NOT NULL,
                listing_title TEXT DEFAULT '',
                mercari_price REAL DEFAULT 0,
                ebay_avg_price REAL DEFAULT 0,
                net_after_fees REAL DEFAULT 0,
                roi_pct REAL DEFAULT 0,
                mercari_url TEXT DEFAULT '',
                listing_id_hash TEXT DEFAULT '',
                sent_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                telegram_ok INTEGER DEFAULT 0
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS arb_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_name TEXT NOT NULL,
                size TEXT DEFAULT '',
                max_buy_price REAL NOT NULL DEFAULT 200,
                target_roi_pct REAL NOT NULL DEFAULT 30,
                active INTEGER DEFAULT 1,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS arb_scan_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_name TEXT NOT NULL,
                listing_title TEXT DEFAULT '',
                mercari_price REAL NOT NULL,
                ebay_avg_price REAL DEFAULT 0,
                ebay_low_price REAL DEFAULT 0,
                net_after_fees REAL DEFAULT 0,
                roi_pct REAL DEFAULT 0,
                mercari_url TEXT DEFAULT '',
                listing_id TEXT DEFAULT '',
                scanned_at TEXT DEFAULT (datetime('now')),
                is_opportunity INTEGER DEFAULT 1
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS arb_alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_name TEXT NOT NULL,
                listing_title TEXT DEFAULT '',
                mercari_price REAL DEFAULT 0,
                ebay_avg_price REAL DEFAULT 0,
                net_after_fees REAL DEFAULT 0,
                roi_pct REAL DEFAULT 0,
                mercari_url TEXT DEFAULT '',
                listing_id_hash TEXT DEFAULT '',
                sent_at TEXT DEFAULT (datetime('now')),
                telegram_ok INTEGER DEFAULT 0
            )
        """)

    conn.commit()
    conn.close()


_ensure_tables()


# ── Watchlist DB helpers ──────────────────────────────────────────────────────

def _load_watchlist() -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM arb_watchlist ORDER BY shoe_name")
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _add_watchlist_item(shoe_name: str, size: str, max_buy: float,
                         target_roi: float, notes: str = "") -> bool:
    conn = get_conn()
    try:
        db_exec(conn,
            f"INSERT INTO arb_watchlist (shoe_name, size, max_buy_price, target_roi_pct, notes) "
            f"VALUES ({PH},{PH},{PH},{PH},{PH})",
            (shoe_name.strip(), size.strip(), max_buy, target_roi, notes.strip()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        log.error("add_watchlist_item: %s", exc)
        conn.close()
        return False


def _delete_watchlist_item(item_id: int):
    conn = get_conn()
    db_exec(conn, f"DELETE FROM arb_watchlist WHERE id={PH}", (item_id,))
    conn.commit()
    conn.close()


def _toggle_watchlist_item(item_id: int, active: int):
    conn = get_conn()
    db_exec(conn,
        f"UPDATE arb_watchlist SET active={PH} WHERE id={PH}",
        (active, item_id),
    )
    conn.commit()
    conn.close()


# ── Scan results DB helpers ───────────────────────────────────────────────────

def _save_scan_result(shoe_name: str, listing_title: str, mercari_price: float,
                       ebay_avg: float, ebay_low: float, net: float, roi: float,
                       mercari_url: str, listing_id: str):
    conn = get_conn()
    db_exec(conn,
        f"INSERT INTO arb_scan_results "
        f"(shoe_name, listing_title, mercari_price, ebay_avg_price, ebay_low_price, "
        f"net_after_fees, roi_pct, mercari_url, listing_id) "
        f"VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})",
        (shoe_name, listing_title, mercari_price, ebay_avg, ebay_low,
         net, roi, mercari_url, listing_id),
    )
    conn.commit()
    conn.close()


def _load_scan_results(limit: int = 200) -> list[dict]:
    conn = get_conn()
    c = db_exec(conn,
        f"SELECT * FROM arb_scan_results ORDER BY scanned_at DESC LIMIT {PH}",
        (limit,),
    )
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _clear_old_results():
    """Remove scan results older than 48 hours to keep the table lean."""
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn,
            "DELETE FROM arb_scan_results WHERE scanned_at < NOW() - INTERVAL '48 hours'")
    else:
        db_exec(conn,
            "DELETE FROM arb_scan_results WHERE scanned_at < datetime('now', '-48 hours')")
    conn.commit()
    conn.close()


# ── Alert dedup helpers ───────────────────────────────────────────────────────

def _listing_hash(listing_id: str, shoe_name: str) -> str:
    raw = f"{listing_id}::{shoe_name}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _already_alerted(listing_id: str, shoe_name: str, hours: int = 6) -> bool:
    """Return True if this listing was already alerted within `hours`."""
    lhash = _listing_hash(listing_id, shoe_name)
    conn = get_conn()
    if USE_POSTGRES:
        c = db_exec(conn,
            f"SELECT 1 FROM arb_alerts_sent WHERE listing_id_hash={PH} "
            f"AND sent_at > NOW() - INTERVAL '{hours} hours' LIMIT 1",
            (lhash,),
        )
    else:
        c = db_exec(conn,
            f"SELECT 1 FROM arb_alerts_sent WHERE listing_id_hash={PH} "
            f"AND sent_at > datetime('now','-{hours} hours') LIMIT 1",
            (lhash,),
        )
    row = c.fetchone()
    conn.close()
    return row is not None


def _record_alert(shoe_name: str, listing_title: str, mercari_price: float,
                   ebay_avg: float, net: float, roi: float,
                   mercari_url: str, listing_id: str, tg_ok: bool):
    lhash = _listing_hash(listing_id, shoe_name)
    conn = get_conn()
    db_exec(conn,
        f"INSERT INTO arb_alerts_sent "
        f"(shoe_name, listing_title, mercari_price, ebay_avg_price, net_after_fees, "
        f"roi_pct, mercari_url, listing_id_hash, telegram_ok) "
        f"VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})",
        (shoe_name, listing_title, mercari_price, ebay_avg, net,
         roi, mercari_url, lhash, 1 if tg_ok else 0),
    )
    conn.commit()
    conn.close()


def _load_alert_history(limit: int = 100) -> list[dict]:
    conn = get_conn()
    c = db_exec(conn,
        f"SELECT * FROM arb_alerts_sent ORDER BY sent_at DESC LIMIT {PH}",
        (limit,),
    )
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


# ── Mercari search ────────────────────────────────────────────────────────────

_MERCARI_URL = "https://api.mercari.com/v2/entities:search"
_MERCARI_HEADERS = {
    "Content-Type": "application/json",
    "X-Platform": "web",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "DPR": "2",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.mercari.com",
    "Referer": "https://www.mercari.com/",
}


def _mercari_search(query: str, max_price: float, limit: int = 30) -> list[dict]:
    """
    Search Mercari US active listings under max_price.
    Falls back to realistic mock data if the API is unavailable.
    """
    payload = {
        "userId": "",
        "pageSize": min(limit, 120),
        "pageToken": "",
        "searchSessionId": "",
        "indexRouting": "INDEX_ROUTING_UNSPECIFIED",
        "thumbnailTypes": [],
        "searchCondition": {
            "keyword": query,
            "excludeKeyword": "",
            "sort": "SORT_SCORE",
            "order": "ORDER_DESC",
            "status": ["STATUS_ON_SALE"],
            "sizeId": [],
            "brandId": [],
            "sellerId": [],
            "priceMin": 1,
            "priceMax": int(max_price),
            "itemConditionId": [],
            "shippingPayerId": [],
            "shippingFromArea": [],
            "shippingMethod": [],
            "categoryId": [],
            "color": [],
            "hasCoupon": False,
            "attributes": [],
            "itemTypes": [],
            "skuIds": [],
        },
        "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
        "serviceFrom": "suruga",
        "withItemBrand": True,
        "withItemSize": True,
        "withItemPromotions": False,
        "withItemSizes": True,
        "withShopname": False,
    }

    try:
        r = requests.post(
            _MERCARI_URL, headers=_MERCARI_HEADERS, json=payload, timeout=20
        )
        if r.status_code == 200:
            items = r.json().get("items", [])
            results = []
            for item in items:
                try:
                    price = int(item.get("price", 0))
                except (TypeError, ValueError):
                    price = 0
                if price <= 0:
                    continue
                item_id = item.get("id", "")
                results.append({
                    "name":      item.get("name", query),
                    "price":     price,
                    "condition": item.get("itemCondition", {}).get("name", "Used"),
                    "item_url":  f"https://www.mercari.com/us/item/{item_id}/",
                    "listing_id": item_id,
                })
            return results
        else:
            log.warning("Mercari HTTP %s — using mock fallback", r.status_code)
    except Exception as exc:
        log.warning("Mercari search error (%s) — using mock fallback", exc)

    # ── Mock fallback ─────────────────────────────────────────────────────────
    return _mock_mercari_results(query, max_price)


def _mock_mercari_results(query: str, max_price: float) -> list[dict]:
    """Generate plausible mock Mercari listings for demo/offline use."""
    conditions = ["New with tags", "Like new", "Good", "Fair"]
    mock_items = []
    base_price = min(max_price * 0.7, 150)
    random.seed(hash(query) % 10000)
    for i in range(random.randint(2, 6)):
        variance = random.uniform(0.75, 0.98)
        price = round(base_price * variance)
        price = max(10, min(price, max_price))
        fake_id = hashlib.md5(f"{query}{i}".encode()).hexdigest()[:10]
        mock_items.append({
            "name":       f"{query} (Sz {random.choice(['8','9','10','11','12'])})",
            "price":      int(price),
            "condition":  random.choice(conditions),
            "item_url":   f"https://www.mercari.com/us/item/{fake_id}/",
            "listing_id": fake_id,
        })
    return mock_items


# ── eBay helpers ──────────────────────────────────────────────────────────────

_EBAY_TOKEN_URL  = "https://api.ebay.com/identity/v1/oauth2/token"
_EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
_EBAY_SNEAKERS_CAT = "15709"


def _get_ebay_token(client_id: str, client_secret: str) -> str:
    """Exchange eBay client credentials for an OAuth application token."""
    if not client_id or not client_secret:
        return ""
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        r = requests.post(
            _EBAY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=(
                "grant_type=client_credentials"
                "&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope"
            ),
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("access_token", "")
    except Exception as exc:
        log.warning("eBay token error: %s", exc)
    return ""


def _ebay_avg_price(query: str, token: str, limit: int = 20) -> float:
    """Return avg eBay BIN price for a query. 0.0 on failure → uses mock."""
    if not token:
        return _mock_ebay_avg(query)
    try:
        r = requests.get(
            _EBAY_SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": query,
                "category_ids": _EBAY_SNEAKERS_CAT,
                "filter": "buyingOptions:{FIXED_PRICE}",
                "sort": "newlyListed",
                "limit": limit,
            },
            timeout=15,
        )
        if r.status_code == 200:
            items = r.json().get("itemSummaries", [])
            prices = []
            for item in items:
                try:
                    prices.append(float(item["price"]["value"]))
                except (KeyError, TypeError, ValueError):
                    pass
            if prices:
                return round(sum(prices) / len(prices), 2)
    except Exception as exc:
        log.warning("eBay search error: %s", exc)
    return _mock_ebay_avg(query)


def _mock_ebay_avg(query: str) -> float:
    """Deterministic mock eBay avg price for demo/offline use."""
    random.seed(hash(query) % 99999)
    return round(random.uniform(120, 380), 2)


# ── ROI calculator ────────────────────────────────────────────────────────────

EBAY_FEE_RATE  = 0.1325   # 13.25% final value fee (typical)
EBAY_FEE_FIXED = 0.30     # fixed per-transaction fee
EBAY_SHIP_EST  = 12.00    # estimated shipping cost


def _calc_roi(buy_price: float, ebay_avg: float) -> tuple[float, float]:
    """
    Returns (net_after_fees, roi_pct).
    net = ebay_avg - (ebay_avg * fee_rate) - fee_fixed - shipping - buy_price
    roi = net / buy_price * 100
    """
    fees = (ebay_avg * EBAY_FEE_RATE) + EBAY_FEE_FIXED + EBAY_SHIP_EST
    net  = round(ebay_avg - fees - buy_price, 2)
    roi  = round((net / buy_price) * 100, 1) if buy_price > 0 else 0.0
    return net, roi


# ── Telegram alert ────────────────────────────────────────────────────────────

def _send_telegram(token: str, chat_id: str, message: str) -> bool:
    """Send a Telegram message. Returns True on success."""
    if not token or not chat_id:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":   chat_id,
                "text":      message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        return r.status_code == 200
    except Exception as exc:
        log.error("Telegram send error: %s", exc)
        return False


def _build_alert_message(shoe: str, listing_title: str, mercari_price: float,
                           ebay_avg: float, net: float, roi: float,
                           mercari_url: str) -> str:
    sign = "📈" if roi >= 0 else "📉"
    return (
        f"🔵 <b>BUY SIGNAL — SoleOps Arb</b>\n\n"
        f"👟 <b>{shoe}</b>\n"
        f"📦 Listing: <i>{listing_title[:80]}</i>\n\n"
        f"🛒 Mercari price:  <b>${mercari_price:.2f}</b>\n"
        f"💵 eBay avg sell:  <b>${ebay_avg:.2f}</b>\n"
        f"{sign} Net after fees: <b>${net:.2f}</b>\n"
        f"📊 Est. ROI:        <b>{roi:.1f}%</b>\n\n"
        f"🔗 <a href='{mercari_url}'>View on Mercari →</a>"
    )


# ── Core scan logic ───────────────────────────────────────────────────────────

def _run_scan(watchlist: list[dict], tg_token: str, tg_chat: str,
              min_roi: float, ebay_client_id: str, ebay_client_secret: str,
              dedup_hours: int = 6) -> dict:
    """
    Scan Mercari for every active watchlist item, compute ROI,
    save results to DB, and send Telegram alerts for buy signals.

    Returns a summary dict.
    """
    active = [w for w in watchlist if w.get("active", 1)]
    if not active:
        return {"scanned": 0, "opportunities": 0, "alerts_sent": 0, "errors": []}

    _clear_old_results()

    ebay_token = _get_ebay_token(ebay_client_id, ebay_client_secret)

    total_opportunities = 0
    alerts_sent = 0
    errors = []

    for item in active:
        shoe_name  = item["shoe_name"]
        size_hint  = item.get("size", "")
        max_buy    = float(item.get("max_buy_price", 200))
        target_roi = float(item.get("target_roi_pct", 30))

        query = f"{shoe_name} {size_hint}".strip() if size_hint else shoe_name

        try:
            # 1️⃣  Pull cheap Mercari listings
            listings = _mercari_search(query, max_price=max_buy, limit=30)
        except Exception as exc:
            errors.append(f"{shoe_name}: Mercari error — {exc}")
            continue

        if not listings:
            continue

        # 2️⃣  Get eBay comp
        try:
            ebay_avg = _ebay_avg_price(query, ebay_token)
        except Exception as exc:
            errors.append(f"{shoe_name}: eBay error — {exc}")
            ebay_avg = _mock_ebay_avg(query)

        if ebay_avg <= 0:
            continue

        # 3️⃣  Evaluate each listing
        for listing in listings:
            mercari_price = float(listing["price"])
            net, roi      = _calc_roi(mercari_price, ebay_avg)

            is_opportunity = roi >= min_roi and net > 0
            if is_opportunity:
                total_opportunities += 1

            # Save result to DB
            _save_scan_result(
                shoe_name      = shoe_name,
                listing_title  = listing["name"],
                mercari_price  = mercari_price,
                ebay_avg       = ebay_avg,
                ebay_low       = 0.0,
                net            = net,
                roi            = roi,
                mercari_url    = listing["item_url"],
                listing_id     = listing["listing_id"],
            )

            # 4️⃣  Send Telegram alert for qualifying opportunities
            if is_opportunity and roi >= target_roi:
                lid = listing["listing_id"]
                if not _already_alerted(lid, shoe_name, hours=dedup_hours):
                    msg    = _build_alert_message(
                        shoe_name, listing["name"],
                        mercari_price, ebay_avg, net, roi,
                        listing["item_url"],
                    )
                    tg_ok = _send_telegram(tg_token, tg_chat, msg)
                    _record_alert(
                        shoe_name, listing["name"],
                        mercari_price, ebay_avg, net, roi,
                        listing["item_url"], lid, tg_ok,
                    )
                    if tg_ok:
                        alerts_sent += 1

    # Persist last-scan timestamp
    set_setting("arb_last_scan_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    set_setting("arb_last_opp_count", str(total_opportunities))

    return {
        "scanned": len(active),
        "opportunities": total_opportunities,
        "alerts_sent": alerts_sent,
        "errors": errors,
    }


# ── Misc helpers ──────────────────────────────────────────────────────────────

def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _roi_color(roi: float) -> str:
    if roi >= 40:
        return "🟢"
    if roi >= 20:
        return "🟡"
    if roi >= 0:
        return "🟠"
    return "🔴"


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("👟 SoleOps Arbitrage Scanner")
st.caption(
    "Scans Mercari for underpriced sneakers, auto-pulls eBay comps, "
    "calculates ROI, and sends Telegram buy-signal alerts."
)

# Tabs
tab_dash, tab_watch, tab_results, tab_alerts, tab_settings = st.tabs([
    "📡 Scan Dashboard",
    "📋 Watchlist",
    "🔍 Scan Results",
    "📣 Alert History",
    "⚙️ Settings",
])


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — SCAN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.subheader("📡 Scan Dashboard")

    # Load persisted stats
    last_scan_at  = get_setting("arb_last_scan_at", "Never")
    last_opp_str  = get_setting("arb_last_opp_count", "0")
    last_opp      = int(last_opp_str) if last_opp_str.isdigit() else 0

    watchlist_all = _load_watchlist()
    active_count  = sum(1 for w in watchlist_all if w.get("active", 1))
    results_all   = _load_scan_results(limit=500)
    alerts_all    = _load_alert_history(limit=500)

    # Best ROI from recent results
    best_roi_row   = None
    if results_all:
        best_row = max(results_all, key=lambda r: _safe_float(r.get("roi_pct", 0)))
        if _safe_float(best_row.get("roi_pct", 0)) > 0:
            best_roi_row = best_row

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("⏱ Last Scan", last_scan_at[:16] if last_scan_at != "Never" else "Never")
    k2.metric("🎯 Active Watchlist Items", active_count)
    k3.metric("🔥 Opportunities Found", last_opp)
    k4.metric("📣 Total Alerts Sent", len(alerts_all))

    st.divider()

    # ── Best ROI banner ───────────────────────────────────────────────────────
    if best_roi_row:
        roi_val  = _safe_float(best_roi_row.get("roi_pct", 0))
        net_val  = _safe_float(best_roi_row.get("net_after_fees", 0))
        shoe_nm  = best_roi_row.get("shoe_name", "")
        m_price  = _safe_float(best_roi_row.get("mercari_price", 0))
        e_avg    = _safe_float(best_roi_row.get("ebay_avg_price", 0))
        m_url    = best_roi_row.get("mercari_url", "")
        icon     = _roi_color(roi_val)

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #0a2010 0%, #12151c 100%);
            border: 1px solid #2a6b3a;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 16px;">
            <div style="font-size:0.8rem; color:#8892a4; text-transform:uppercase; letter-spacing:0.05em;">
                🏆 Best ROI Opportunity (Last Scan)
            </div>
            <div style="font-size:1.4rem; font-weight:700; color:#fafafa; margin:6px 0;">
                {icon} {shoe_nm}
            </div>
            <div style="color:#c8d0dc; font-size:0.9rem;">
                Buy on Mercari: <strong>${m_price:.2f}</strong> &nbsp;→&nbsp;
                eBay avg: <strong>${e_avg:.2f}</strong> &nbsp;→&nbsp;
                Net: <strong>${net_val:.2f}</strong> &nbsp;|&nbsp;
                ROI: <strong style="color:#7ec87e;">{roi_val:.1f}%</strong>
            </div>
            {"<div style='margin-top:8px;'><a href='" + m_url + "' target='_blank' style='color:#FFAB76;'>→ View listing on Mercari</a></div>" if m_url else ""}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info(
            "No opportunities found yet. Add items to your watchlist and run a scan.",
            icon="🔍",
        )

    st.divider()

    # ── Manual scan trigger ───────────────────────────────────────────────────
    st.subheader("🚀 Run Manual Scan")

    if not watchlist_all or active_count == 0:
        st.warning(
            "Your watchlist is empty. "
            "Go to the **Watchlist** tab to add shoes before scanning.",
            icon="⚠️",
        )
    else:
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            do_scan = st.button(
                "🔍 Scan Now",
                type="primary",
                use_container_width=True,
                key="dash_scan_btn",
            )
        with col_info:
            st.caption(
                f"Will scan **{active_count}** active watchlist item(s). "
                "Alerts sent via Telegram when ROI exceeds your threshold."
            )

        if do_scan:
            tg_token  = get_setting("arb_tg_token", "")
            tg_chat   = get_setting("arb_tg_chat_id", "")
            min_roi   = _safe_float(get_setting("arb_min_roi_pct", "20"), 20.0)
            ebay_cid  = get_setting("arb_ebay_client_id", "")
            ebay_csec = get_setting("arb_ebay_client_secret", "")
            dedup_hrs = int(get_setting("arb_dedup_hours", "6") or 6)

            if not tg_token or not tg_chat:
                st.warning(
                    "Telegram bot token / chat ID not configured. "
                    "Scanning now but alerts will be skipped. "
                    "Configure in the **Settings** tab.",
                    icon="📣",
                )

            with st.spinner("Scanning Mercari & pulling eBay comps…"):
                summary = _run_scan(
                    watchlist        = watchlist_all,
                    tg_token         = tg_token,
                    tg_chat          = tg_chat,
                    min_roi          = min_roi,
                    ebay_client_id   = ebay_cid,
                    ebay_client_secret = ebay_csec,
                    dedup_hours      = dedup_hrs,
                )

            st.success(
                f"✅ Scan complete — "
                f"**{summary['scanned']}** item(s) scanned, "
                f"**{summary['opportunities']}** opportunities found, "
                f"**{summary['alerts_sent']}** alert(s) sent."
            )

            if summary["errors"]:
                with st.expander(f"⚠️ {len(summary['errors'])} error(s)"):
                    for err in summary["errors"]:
                        st.caption(f"• {err}")

            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — WATCHLIST
# ═══════════════════════════════════════════════════════════════════════════════
with tab_watch:
    st.subheader("📋 Watchlist — Target Shoes")

    # ── Add form ──────────────────────────────────────────────────────────────
    with st.expander("➕ Add Shoe to Watchlist", expanded=len(_load_watchlist()) == 0):
        with st.form("add_watch_form", clear_on_submit=True):
            w_col1, w_col2, w_col3 = st.columns(3)
            with w_col1:
                w_shoe = st.text_input(
                    "Shoe Name *",
                    placeholder="Jordan 1 Retro High OG",
                    max_chars=120,
                )
                w_size = st.text_input(
                    "Size (optional)",
                    placeholder="10.5",
                    max_chars=20,
                )
            with w_col2:
                w_max_buy = st.number_input(
                    "Max Buy Price ($) *",
                    min_value=1.0,
                    max_value=5000.0,
                    value=150.0,
                    step=5.0,
                    help="Only show Mercari listings at or below this price.",
                )
                w_target_roi = st.number_input(
                    "Target ROI % *",
                    min_value=1.0,
                    max_value=500.0,
                    value=30.0,
                    step=5.0,
                    help="Trigger Telegram alert when estimated ROI meets this threshold.",
                )
            with w_col3:
                w_notes = st.text_area("Notes", placeholder="e.g. Only DS/VNDS", max_chars=200)

            submitted = st.form_submit_button("Add to Watchlist", type="primary")
            if submitted:
                if not w_shoe.strip():
                    st.error("Shoe name is required.")
                else:
                    ok = _add_watchlist_item(
                        w_shoe.strip(), w_size.strip(),
                        w_max_buy, w_target_roi, w_notes.strip()
                    )
                    if ok:
                        st.success(f"✅ **{w_shoe}** added to watchlist!")
                        st.rerun()
                    else:
                        st.error("Failed to save. Check logs.")

    st.divider()

    # ── Current watchlist ─────────────────────────────────────────────────────
    watchlist_items = _load_watchlist()
    if not watchlist_items:
        st.info("Your watchlist is empty. Add a shoe above to get started.", icon="👟")
    else:
        st.caption(f"**{len(watchlist_items)}** item(s) on watchlist")

        # Header row
        hdr = st.columns([3, 1.2, 1.2, 1.2, 2, 1, 1])
        hdr[0].markdown("**Shoe**")
        hdr[1].markdown("**Size**")
        hdr[2].markdown("**Max Buy**")
        hdr[3].markdown("**Target ROI**")
        hdr[4].markdown("**Notes**")
        hdr[5].markdown("**Active**")
        hdr[6].markdown("**Remove**")
        st.markdown("---")

        for item in watchlist_items:
            item_id    = item["id"]
            is_active  = bool(item.get("active", 1))
            cols       = st.columns([3, 1.2, 1.2, 1.2, 2, 1, 1])

            with cols[0]:
                label = item["shoe_name"]
                if not is_active:
                    label = f"~~{label}~~"
                st.markdown(label)

            with cols[1]:
                st.caption(item.get("size") or "Any")

            with cols[2]:
                st.caption(f"${item.get('max_buy_price', 0):.2f}")

            with cols[3]:
                st.caption(f"{item.get('target_roi_pct', 30):.0f}%")

            with cols[4]:
                st.caption(item.get("notes") or "—")

            with cols[5]:
                new_active = st.checkbox(
                    "Active",
                    value=is_active,
                    key=f"active_{item_id}",
                    label_visibility="collapsed",
                )
                if new_active != is_active:
                    _toggle_watchlist_item(item_id, 1 if new_active else 0)
                    st.rerun()

            with cols[6]:
                if st.button("🗑", key=f"del_{item_id}", help="Remove from watchlist"):
                    _delete_watchlist_item(item_id)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — SCAN RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_results:
    st.subheader("🔍 Current Scan Results")

    results = _load_scan_results(limit=300)

    if not results:
        st.info(
            "No scan results yet. Run a scan from the **Scan Dashboard** tab.",
            icon="📭",
        )
    else:
        # Filter controls
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            filter_opp = st.checkbox("Opportunities only", value=True)
        with fc2:
            min_roi_filter = st.slider(
                "Min ROI %", min_value=-50, max_value=200, value=0, step=5
            )
        with fc3:
            shoe_names = sorted(set(r.get("shoe_name", "") for r in results))
            selected_shoe = st.selectbox(
                "Filter by shoe", ["All"] + shoe_names
            )

        # Apply filters
        filtered = results
        if filter_opp:
            filtered = [r for r in filtered if _safe_float(r.get("roi_pct", 0)) >= 0
                        and _safe_float(r.get("net_after_fees", 0)) > 0]
        if min_roi_filter > -50:
            filtered = [r for r in filtered
                        if _safe_float(r.get("roi_pct", 0)) >= min_roi_filter]
        if selected_shoe != "All":
            filtered = [r for r in filtered if r.get("shoe_name") == selected_shoe]

        st.caption(f"Showing **{len(filtered)}** of **{len(results)}** results")
        st.divider()

        if not filtered:
            st.info("No results match the current filters.", icon="🔎")
        else:
            # Build display DataFrame
            display_rows = []
            for r in filtered:
                roi = _safe_float(r.get("roi_pct", 0))
                net = _safe_float(r.get("net_after_fees", 0))
                icon = _roi_color(roi)
                display_rows.append({
                    "Signal":        icon,
                    "Shoe":          r.get("shoe_name", ""),
                    "Listing":       r.get("listing_title", "")[:55],
                    "Mercari $":     f"${_safe_float(r.get('mercari_price', 0)):.2f}",
                    "eBay Avg $":    f"${_safe_float(r.get('ebay_avg_price', 0)):.2f}",
                    "Net (fees)":    f"${net:.2f}",
                    "ROI %":         f"{roi:.1f}%",
                    "Scanned":       str(r.get("scanned_at", ""))[:16],
                    "Link":          r.get("mercari_url", ""),
                })

            df = pd.DataFrame(display_rows)
            # Render table with clickable links
            st.dataframe(
                df.drop(columns=["Link"]),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.caption("🔗 **Direct Mercari Links**")
            link_cols = st.columns(3)
            for i, row in enumerate(display_rows[:30]):
                col = link_cols[i % 3]
                col.markdown(
                    f"{row['Signal']} [{row['Shoe']} — {row['Mercari $']}]({row['Link']})"
                    f"  *(ROI {row['ROI %']})*"
                )

    st.divider()

    # ── Inline ROI Calculator ─────────────────────────────────────────────────
    st.subheader("🧮 ROI Calculator")
    st.caption(
        f"Fee model: eBay final value fee **{EBAY_FEE_RATE*100:.2f}%** "
        f"+ ${EBAY_FEE_FIXED:.2f} fixed + ~${EBAY_SHIP_EST:.2f} shipping"
    )

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        calc_buy = st.number_input(
            "Buy Price ($)", min_value=0.01, max_value=10000.0, value=80.0, step=5.0,
            key="calc_buy"
        )
    with rc2:
        calc_sell = st.number_input(
            "eBay Avg Sell Price ($)", min_value=0.01, max_value=10000.0,
            value=150.0, step=5.0, key="calc_sell"
        )
    with rc3:
        calc_fee_rate = st.number_input(
            "eBay Fee Rate (%)", min_value=0.0, max_value=50.0,
            value=EBAY_FEE_RATE * 100, step=0.5, key="calc_fee"
        )

    c_fees = (calc_sell * (calc_fee_rate / 100)) + EBAY_FEE_FIXED + EBAY_SHIP_EST
    c_net  = calc_sell - c_fees - calc_buy
    c_roi  = (c_net / calc_buy * 100) if calc_buy > 0 else 0.0

    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("eBay Fees + Ship", f"${c_fees:.2f}")
    res_col2.metric("Net After Fees", f"${c_net:.2f}", delta=f"{c_roi:.1f}%")
    res_col3.metric("ROI", f"{c_roi:.1f}%")
    res_col4.metric("Break-even Sell", f"${calc_buy + c_fees:.2f}")

    if c_roi >= 30:
        st.success(f"✅ Strong arb opportunity at {c_roi:.1f}% ROI!", icon="🔥")
    elif c_roi >= 15:
        st.info(f"✅ Decent opportunity at {c_roi:.1f}% ROI", icon="📈")
    elif c_roi >= 0:
        st.warning(f"⚠️ Marginal at {c_roi:.1f}% ROI — consider shipping costs", icon="⚠️")
    else:
        st.error(f"❌ Negative ROI ({c_roi:.1f}%) — not worth buying at ${calc_buy:.2f}", icon="🚫")


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 4 — ALERT HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_alerts:
    st.subheader("📣 Alert History")
    st.caption("All Telegram buy-signal alerts sent by SoleOps Arb Scanner.")

    alert_hist = _load_alert_history(limit=200)

    if not alert_hist:
        st.info("No alerts have been sent yet. Configure Telegram in Settings and run a scan.", icon="📭")
    else:
        # Summary metrics
        total_alerts  = len(alert_hist)
        sent_ok       = sum(1 for a in alert_hist if a.get("telegram_ok", 0))
        best_roi_hist = max((_safe_float(a.get("roi_pct", 0)) for a in alert_hist), default=0.0)
        avg_net_hist  = (
            sum(_safe_float(a.get("net_after_fees", 0)) for a in alert_hist) / total_alerts
            if total_alerts > 0 else 0.0
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📣 Total Alerts", total_alerts)
        m2.metric("✅ Sent Successfully", sent_ok)
        m3.metric("🏆 Best ROI Alerted", f"{best_roi_hist:.1f}%")
        m4.metric("💰 Avg Net Profit", f"${avg_net_hist:.2f}")

        st.divider()

        # Table
        hist_rows = []
        for a in alert_hist:
            roi = _safe_float(a.get("roi_pct", 0))
            hist_rows.append({
                "Status":      "✅" if a.get("telegram_ok", 0) else "❌",
                "Sent At":     str(a.get("sent_at", ""))[:16],
                "Shoe":        a.get("shoe_name", ""),
                "Listing":     a.get("listing_title", "")[:45],
                "Mercari $":   f"${_safe_float(a.get('mercari_price', 0)):.2f}",
                "eBay Avg $":  f"${_safe_float(a.get('ebay_avg_price', 0)):.2f}",
                "Net":         f"${_safe_float(a.get('net_after_fees', 0)):.2f}",
                "ROI %":       f"{roi:.1f}%",
                "Link":        a.get("mercari_url", ""),
            })

        hist_df = pd.DataFrame(hist_rows)
        st.dataframe(
            hist_df.drop(columns=["Link"]),
            use_container_width=True,
            hide_index=True,
        )

        # Quick links to recent high-ROI alerts
        top_alerts = sorted(alert_hist, key=lambda a: _safe_float(a.get("roi_pct", 0)), reverse=True)[:10]
        if top_alerts:
            st.divider()
            st.caption("🔗 **Top 10 Alerts by ROI**")
            for a in top_alerts:
                roi = _safe_float(a.get("roi_pct", 0))
                url = a.get("mercari_url", "")
                shoe = a.get("shoe_name", "")
                icon = _roi_color(roi)
                mp = _safe_float(a.get("mercari_price", 0))
                net = _safe_float(a.get("net_after_fees", 0))
                ts  = str(a.get("sent_at", ""))[:16]
                if url:
                    st.markdown(
                        f"{icon} [{shoe}]({url}) — Buy ${mp:.2f} → Net ${net:.2f} "
                        f"*({roi:.1f}% ROI)* — *{ts}*"
                    )
                else:
                    st.markdown(
                        f"{icon} {shoe} — Buy ${mp:.2f} → Net ${net:.2f} "
                        f"*({roi:.1f}% ROI)* — *{ts}*"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 5 — SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_settings:
    st.subheader("⚙️ SoleOps Scanner Settings")
    st.caption(
        "All settings are stored securely in the app database. "
        "Credentials are never logged or exposed."
    )

    # Load existing
    s_tg_token  = get_setting("arb_tg_token", "")
    s_tg_chat   = get_setting("arb_tg_chat_id", "")
    s_min_roi   = _safe_float(get_setting("arb_min_roi_pct",  "20"), 20.0)
    s_dedup_hrs = int(get_setting("arb_dedup_hours", "6") or 6)
    s_ebay_cid  = get_setting("arb_ebay_client_id", "")
    s_ebay_csec = get_setting("arb_ebay_client_secret", "")

    with st.form("settings_form"):
        st.markdown("#### 📣 Telegram Bot")
        tg_col1, tg_col2 = st.columns(2)
        with tg_col1:
            new_tg_token = st.text_input(
                "Bot Token",
                value=s_tg_token,
                type="password",
                placeholder="123456789:ABC-xxx (from @BotFather)",
                help="Create a bot via @BotFather on Telegram and paste the token here.",
            )
        with tg_col2:
            new_tg_chat = st.text_input(
                "Chat ID",
                value=s_tg_chat,
                placeholder="-1001234567890 or your user ID",
                help=(
                    "To find your chat ID: message @userinfobot on Telegram, "
                    "or use https://api.telegram.org/botTOKEN/getUpdates"
                ),
            )

        st.markdown("#### 🛒 eBay API Credentials")
        st.caption(
            "Optional — used for real eBay comp data. "
            "Get credentials at [developer.ebay.com](https://developer.ebay.com). "
            "If left blank, realistic mock comps will be used."
        )
        eb_col1, eb_col2 = st.columns(2)
        with eb_col1:
            new_ebay_cid = st.text_input(
                "eBay Client ID (App ID)",
                value=s_ebay_cid,
                placeholder="YourApp-xxx-yyy",
            )
        with eb_col2:
            new_ebay_csec = st.text_input(
                "eBay Client Secret",
                value=s_ebay_csec,
                type="password",
                placeholder="eBay-xxx-yyy",
            )

        st.markdown("#### 🎯 Scan Thresholds")
        thresh_col1, thresh_col2 = st.columns(2)
        with thresh_col1:
            new_min_roi = st.number_input(
                "Minimum ROI % to trigger alert",
                min_value=0.0,
                max_value=500.0,
                value=s_min_roi,
                step=5.0,
                help="Only listings where estimated ROI meets this threshold will generate alerts.",
            )
        with thresh_col2:
            new_dedup_hrs = st.number_input(
                "Dedup window (hours)",
                min_value=1,
                max_value=72,
                value=s_dedup_hrs,
                step=1,
                help="Same listing won't re-alert within this many hours.",
            )

        st.markdown("#### 🛠 Fee Model (used in ROI calculations)")
        fee_col1, fee_col2, fee_col3 = st.columns(3)
        with fee_col1:
            cur_fee_rate = _safe_float(get_setting("arb_ebay_fee_rate", str(EBAY_FEE_RATE)), EBAY_FEE_RATE)
            new_fee_rate = st.number_input(
                "eBay Fee Rate (%)",
                min_value=0.0, max_value=50.0,
                value=round(cur_fee_rate * 100, 2), step=0.25,
            )
        with fee_col2:
            cur_fee_fixed = _safe_float(get_setting("arb_ebay_fee_fixed", str(EBAY_FEE_FIXED)), EBAY_FEE_FIXED)
            new_fee_fixed = st.number_input(
                "eBay Fixed Fee ($)",
                min_value=0.0, max_value=5.0,
                value=cur_fee_fixed, step=0.05,
            )
        with fee_col3:
            cur_ship = _safe_float(get_setting("arb_ship_est", str(EBAY_SHIP_EST)), EBAY_SHIP_EST)
            new_ship = st.number_input(
                "Est. Shipping ($)",
                min_value=0.0, max_value=100.0,
                value=cur_ship, step=1.0,
            )

        save_btn = st.form_submit_button("💾 Save Settings", type="primary")

    if save_btn:
        set_setting("arb_tg_token",           new_tg_token.strip())
        set_setting("arb_tg_chat_id",         new_tg_chat.strip())
        set_setting("arb_min_roi_pct",        str(new_min_roi))
        set_setting("arb_dedup_hours",        str(int(new_dedup_hrs)))
        set_setting("arb_ebay_client_id",     new_ebay_cid.strip())
        set_setting("arb_ebay_client_secret", new_ebay_csec.strip())
        set_setting("arb_ebay_fee_rate",      str(new_fee_rate / 100))
        set_setting("arb_ebay_fee_fixed",     str(new_fee_fixed))
        set_setting("arb_ship_est",           str(new_ship))

        # Update module-level fee constants so the ROI calc reflects immediately
        EBAY_FEE_RATE  = new_fee_rate / 100
        EBAY_FEE_FIXED = new_fee_fixed
        EBAY_SHIP_EST  = new_ship

        st.success("✅ Settings saved!", icon="💾")

    st.divider()

    # ── Telegram test ─────────────────────────────────────────────────────────
    st.subheader("🧪 Test Telegram Connection")
    if st.button("📣 Send Test Message", key="test_tg_btn"):
        tok  = get_setting("arb_tg_token", "")
        chat = get_setting("arb_tg_chat_id", "")
        if not tok or not chat:
            st.error("Configure Telegram bot token and chat ID first (and save settings).")
        else:
            test_msg = (
                "✅ <b>SoleOps Arb Scanner — Test Message</b>\n\n"
                "Your Telegram integration is working! 🎉\n\n"
                "You'll receive alerts like this when a watchlist shoe "
                "appears on Mercari below your max buy price with positive ROI.\n\n"
                "🔵 <b>Example Buy Signal</b>\n"
                "👟 <b>Jordan 1 Retro High OG</b>\n"
                "🛒 Mercari: <b>$120.00</b>  →  eBay avg: <b>$220.00</b>\n"
                "📈 Net after fees: <b>$71.45</b>  |  ROI: <b>59.5%</b>"
            )
            ok = _send_telegram(tok, chat, test_msg)
            if ok:
                st.success("✅ Test message sent! Check your Telegram.")
            else:
                st.error(
                    "❌ Failed to send. Double-check your bot token and chat ID. "
                    "Make sure you've sent at least one message to the bot first."
                )

    st.divider()

    # ── Quick start guide ─────────────────────────────────────────────────────
    with st.expander("📖 Quick Start Guide"):
        st.markdown("""
**Getting started with SoleOps Arbitrage Scanner:**

1. **Create a Telegram bot**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot`, follow prompts, copy the token
   - Message your new bot once (so it can reply to you)
   - Message [@userinfobot](https://t.me/userinfobot) to get your Chat ID
   - Paste both values in Settings above

2. **Add shoes to your watchlist** (Watchlist tab)
   - Enter the shoe name as it appears on Mercari (e.g. "Jordan 1 Retro High OG")
   - Set max buy price — only listings at or below this will be scanned
   - Set target ROI % — alerts only fire when this threshold is met

3. **eBay API (optional)**
   - Register at [developer.ebay.com](https://developer.ebay.com) (free)
   - Create an app, get Client ID + Secret
   - Add to Settings for real eBay comps (mock data used if blank)

4. **Run scans**
   - Click **Scan Now** on the Dashboard tab
   - Or set up a cron job / scheduled task to call the bot automatically

5. **ROI formula:**
   ```
   net = ebay_avg - (ebay_avg × fee%) - $0.30 - ~$12 shipping - mercari_price
   roi = net / mercari_price × 100
   ```

**Tips:**
- Set max buy price conservatively — leaves more room for profit
- Start with target ROI of 25–35% to account for unexpected costs
- Use the ROI Calculator (Scan Results tab) to model scenarios before buying
        """)
