"""
SoleOps Price Monitor Dashboard — Page 68
Live eBay + Mercari price tracking, profit calculator, watchlist, and Telegram alerts.
"""
import base64
import json
import random
import time
from datetime import datetime

import plotly.graph_objects as go
import requests
import streamlit as st

from utils.auth import inject_soleops_css, render_sidebar_brand, render_sidebar_user_widget, require_login
from utils.db import USE_POSTGRES, execute as db_exec, get_conn, get_setting, init_db, set_setting

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="👟 SoleOps Price Monitor — Peach State Savings",
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

# ── Constants ─────────────────────────────────────────────────────────────────
EBAY_TOKEN_URL   = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL  = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_CATEGORY    = "15709"   # Sneakers

EBAY_FEE_PCT     = 0.129    # 12.9%
EBAY_FEE_FLAT    = 0.30
MERCARI_FEE_PCT  = 0.10     # 10%
MERCARI_FEE_FLAT = 0.30

MERCARI_HEADERS = {
    "Content-Type":    "application/json",
    "X-Platform":      "web",
    "Accept":          "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "DPR":              "2",
    "X-Requested-With": "XMLHttpRequest",
    "Origin":           "https://www.mercari.com",
    "Referer":          "https://www.mercari.com/",
}

# ── DB table setup ────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_watchlist (
                id SERIAL PRIMARY KEY,
                sku TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                added_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_price_history (
                id SERIAL PRIMARY KEY,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                avg_price REAL DEFAULT 0,
                low_price REAL DEFAULT 0,
                listing_count INTEGER DEFAULT 0,
                checked_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_alerts (
                id SERIAL PRIMARY KEY,
                sku TEXT NOT NULL,
                platform TEXT DEFAULT 'both',
                condition TEXT DEFAULT 'below',
                threshold REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                last_triggered TEXT DEFAULT NULL,
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                avg_price REAL DEFAULT 0,
                low_price REAL DEFAULT 0,
                listing_count INTEGER DEFAULT 0,
                checked_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                platform TEXT DEFAULT 'both',
                condition TEXT DEFAULT 'below',
                threshold REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                last_triggered TEXT DEFAULT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()
    conn.close()


_ensure_tables()

# ── Fee helpers ───────────────────────────────────────────────────────────────

def ebay_net(price: float) -> float:
    """Net proceeds after eBay fees."""
    if price <= 0:
        return 0.0
    return round(price - (price * EBAY_FEE_PCT) - EBAY_FEE_FLAT, 2)


def mercari_net(price: float) -> float:
    """Net proceeds after Mercari fees."""
    if price <= 0:
        return 0.0
    return round(price - (price * MERCARI_FEE_PCT) - MERCARI_FEE_FLAT, 2)


def calc_profit(sale_price: float, cogs: float, platform: str) -> tuple[float, float]:
    """Return (net_after_fees, profit). platform = 'ebay' | 'mercari'"""
    net = ebay_net(sale_price) if platform == "ebay" else mercari_net(sale_price)
    profit = round(net - cogs, 2)
    return net, profit


# ── eBay API helpers ──────────────────────────────────────────────────────────

def _get_ebay_token() -> str | None:
    """Get eBay OAuth token from saved client ID + secret."""
    client_id     = get_setting("ebay_app_id", "")
    client_secret = get_setting("ebay_cert_id", "")
    if not client_id or not client_secret:
        return None
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        r = requests.post(
            EBAY_TOKEN_URL,
            headers={
                "Authorization":  f"Basic {credentials}",
                "Content-Type":   "application/x-www-form-urlencoded",
            },
            data=(
                "grant_type=client_credentials"
                "&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope"
            ),
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
        return None
    except Exception:
        return None


def ebay_search_listings(query: str, token: str, limit: int = 20) -> list[dict]:
    """Search eBay active Buy-It-Now listings in the sneakers category."""
    if not token:
        return []
    try:
        r = requests.get(
            EBAY_SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q":            query,
                "category_ids": EBAY_CATEGORY,
                "filter":       "buyingOptions:{FIXED_PRICE}",
                "sort":         "newlyListed",
                "limit":        limit,
                "fieldgroups":  "MATCHING_ITEMS",
            },
            timeout=15,
        )
        if r.status_code != 200:
            return []
        items = r.json().get("itemSummaries", [])
        results = []
        for item in items:
            try:
                price = float(item.get("price", {}).get("value", 0))
            except (TypeError, ValueError):
                price = 0.0
            results.append({
                "title":     item.get("title", ""),
                "price":     price,
                "condition": item.get("condition", ""),
                "item_url":  item.get("itemWebUrl", ""),
                "source":    "eBay",
            })
        return results
    except Exception:
        return []


def ebay_price_summary(query: str, token: str, limit: int = 20) -> dict:
    """Return {avg, low, count, listings} for an eBay query."""
    listings = ebay_search_listings(query, token, limit)
    prices = [r["price"] for r in listings if r["price"] > 0]
    return {
        "avg":      round(sum(prices) / len(prices), 2) if prices else 0.0,
        "low":      round(min(prices), 2) if prices else 0.0,
        "count":    len(prices),
        "listings": listings,
    }


# ── Mercari API helpers ───────────────────────────────────────────────────────

def mercari_search_listings(query: str, limit: int = 30) -> list[dict]:
    """Search Mercari active listings. Falls back to mock data on error."""
    payload = {
        "userId":          "",
        "pageSize":        min(limit, 120),
        "pageToken":       "",
        "searchSessionId": "",
        "indexRouting":    "INDEX_ROUTING_UNSPECIFIED",
        "thumbnailTypes":  [],
        "searchCondition": {
            "keyword":           query,
            "excludeKeyword":    "",
            "sort":              "SORT_SCORE",
            "order":             "ORDER_DESC",
            "status":            ["STATUS_ON_SALE"],
            "sizeId":            [],
            "brandId":           [],
            "sellerId":          [],
            "priceMin":          0,
            "priceMax":          0,
            "itemConditionId":   [],
            "shippingPayerId":   [],
            "shippingFromArea":  [],
            "shippingMethod":    [],
            "categoryId":        [],
            "color":             [],
            "hasCoupon":         False,
            "attributes":        [],
            "itemTypes":         [],
            "skuIds":            [],
        },
        "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
        "serviceFrom":     "suruga",
        "withItemBrand":   True,
        "withItemSize":    True,
        "withItemPromotions": False,
        "withItemSizes":   True,
        "withShopname":    False,
    }
    try:
        r = requests.post(
            "https://api.mercari.com/v2/entities:search",
            headers=MERCARI_HEADERS,
            json=payload,
            timeout=20,
        )
        if r.status_code != 200:
            return _mercari_mock(query)
        data = r.json()
        items = data.get("items", [])
        results = []
        for item in items:
            try:
                price = int(item.get("price", 0))
            except (TypeError, ValueError):
                price = 0
            item_id = item.get("id", "")
            results.append({
                "name":      item.get("name", ""),
                "price":     price,
                "condition": item.get("itemCondition", {}).get("name", ""),
                "item_url":  f"https://www.mercari.com/us/item/{item_id}/",
                "source":    "Mercari",
            })
        return results if results else _mercari_mock(query)
    except Exception:
        return _mercari_mock(query)


def _mercari_mock(query: str) -> list[dict]:
    """Mock Mercari results — used when the API is unavailable."""
    seed = sum(ord(c) for c in query)
    rng = random.Random(seed)
    base = rng.randint(80, 350)
    results = []
    for i in range(10):
        price = base + rng.randint(-30, 30)
        results.append({
            "name":      f"{query} (Mercari listing {i + 1})",
            "price":     price,
            "condition": rng.choice(["Like New", "Good", "Fair"]),
            "item_url":  "https://www.mercari.com",
            "source":    "Mercari (mock)",
        })
    return results


def mercari_price_summary(query: str, limit: int = 20) -> dict:
    """Return {avg, low, count, listings} for a Mercari query."""
    listings = mercari_search_listings(query, limit)
    prices = [r["price"] for r in listings if r["price"] > 0]
    return {
        "avg":      round(sum(prices) / len(prices), 2) if prices else 0.0,
        "low":      round(min(prices), 2) if prices else 0.0,
        "count":    len(prices),
        "listings": listings,
    }


# ── DB helpers ────────────────────────────────────────────────────────────────

def _load_watchlist() -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM soleops_watchlist ORDER BY id DESC")
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _add_watchlist(sku: str, display_name: str, notes: str):
    conn = get_conn()
    db_exec(
        conn,
        "INSERT INTO soleops_watchlist (sku, display_name, notes) VALUES (?, ?, ?)",
        (sku.strip(), display_name.strip(), notes.strip()),
    )
    conn.commit()
    conn.close()


def _remove_watchlist(item_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM soleops_watchlist WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def _save_price_history(sku: str, platform: str, avg: float, low: float, count: int):
    conn = get_conn()
    db_exec(
        conn,
        "INSERT INTO soleops_price_history (sku, platform, avg_price, low_price, listing_count) VALUES (?, ?, ?, ?, ?)",
        (sku, platform, avg, low, count),
    )
    conn.commit()
    conn.close()


def _load_price_history(sku: str) -> list[dict]:
    conn = get_conn()
    c = db_exec(
        conn,
        "SELECT * FROM soleops_price_history WHERE sku = ? ORDER BY checked_at ASC",
        (sku,),
    )
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _load_all_history_skus() -> list[str]:
    conn = get_conn()
    c = db_exec(conn, "SELECT DISTINCT sku FROM soleops_price_history ORDER BY sku")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def _load_alerts() -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM soleops_alerts ORDER BY id DESC")
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _add_alert(sku: str, platform: str, condition: str, threshold: float):
    conn = get_conn()
    db_exec(
        conn,
        "INSERT INTO soleops_alerts (sku, platform, condition, threshold) VALUES (?, ?, ?, ?)",
        (sku.strip(), platform, condition, threshold),
    )
    conn.commit()
    conn.close()


def _delete_alert(alert_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM soleops_alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


def _toggle_alert(alert_id: int, active: int):
    conn = get_conn()
    db_exec(conn, "UPDATE soleops_alerts SET active = ? WHERE id = ?", (active, alert_id))
    conn.commit()
    conn.close()


# ── Telegram helper ───────────────────────────────────────────────────────────

def _send_telegram(message: str) -> bool:
    """Send a Telegram message using saved bot token + chat ID."""
    bot_token = get_setting("telegram_bot_token", "")
    chat_id   = get_setting("telegram_chat_id", "")
    if not bot_token or not chat_id:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _check_alerts_against_price(sku: str, platform: str, avg_price: float):
    """Check active alerts for a SKU and fire Telegram if conditions are met."""
    alerts = _load_alerts()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for alert in alerts:
        if alert["sku"].lower() != sku.lower():
            continue
        if not alert["active"]:
            continue
        if alert["platform"] not in ("both", platform):
            continue
        threshold = float(alert["threshold"])
        condition = alert["condition"]
        triggered = False
        if condition == "below" and avg_price <= threshold:
            triggered = True
        elif condition == "above" and avg_price >= threshold:
            triggered = True
        if triggered:
            msg = (
                f"🚨 <b>SoleOps Price Alert</b>\n"
                f"SKU: <code>{sku}</code>\n"
                f"Platform: {platform.title()}\n"
                f"Avg Price: <b>${avg_price:.2f}</b> is {condition} ${threshold:.2f}\n"
                f"Time: {now_str}"
            )
            sent = _send_telegram(msg)
            conn = get_conn()
            db_exec(
                conn,
                "UPDATE soleops_alerts SET last_triggered = ? WHERE id = ?",
                (now_str, alert["id"]),
            )
            conn.commit()
            conn.close()
            if sent:
                st.toast(f"📲 Telegram alert sent for {sku} on {platform.title()}!", icon="📲")


# ── Search function that hits both platforms ──────────────────────────────────

def _search_both(query: str, save_to_db: bool = True) -> dict:
    """Search eBay and Mercari and return combined summary."""
    token     = _get_ebay_token()
    has_ebay  = bool(token)

    with st.spinner("🔍 Searching eBay…"):
        if has_ebay:
            ebay  = ebay_price_summary(query, token)
        else:
            # Mock eBay data when no API key
            seed = sum(ord(c) for c in query)
            rng = random.Random(seed + 1)
            base = rng.randint(100, 400)
            mock_listings = [
                {
                    "title":     f"{query} listing {i + 1}",
                    "price":     base + rng.randint(-40, 40),
                    "condition": rng.choice(["New", "Pre-owned"]),
                    "item_url":  "https://www.ebay.com",
                    "source":    "eBay (mock)",
                }
                for i in range(10)
            ]
            prices = [r["price"] for r in mock_listings]
            ebay = {
                "avg":      round(sum(prices) / len(prices), 2),
                "low":      round(min(prices), 2),
                "count":    len(prices),
                "listings": mock_listings,
            }

    with st.spinner("🔍 Searching Mercari…"):
        mercari = mercari_price_summary(query)

    if save_to_db and query.strip():
        _save_price_history(query, "ebay",    ebay["avg"],    ebay["low"],    ebay["count"])
        _save_price_history(query, "mercari", mercari["avg"], mercari["low"], mercari["count"])
        _check_alerts_against_price(query, "ebay",    ebay["avg"])
        _check_alerts_against_price(query, "mercari", mercari["avg"])

    return {
        "ebay":        ebay,
        "mercari":     mercari,
        "has_real_ebay": has_ebay,
        "checked_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Page title ────────────────────────────────────────────────────────────────
st.title("👟 SoleOps Price Monitor")
st.caption("Live eBay + Mercari pricing, profit-after-fees calculator, watchlist tracking, and Telegram alerts.")

tab_monitor, tab_watchlist, tab_history, tab_profit, tab_alerts = st.tabs([
    "🔍 Price Monitor",
    "📋 Watchlist",
    "📈 Price History",
    "💰 Profit Calculator",
    "🔔 Alerts",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRICE MONITOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_monitor:
    st.subheader("🔍 Search a Shoe by Name or SKU")

    col_q, col_btn = st.columns([4, 1])
    with col_q:
        search_query = st.text_input(
            "Shoe name or SKU",
            placeholder='e.g. "Jordan 1 Chicago size 10" or "DZ5485-612"',
            key="monitor_query",
            label_visibility="collapsed",
        )
    with col_btn:
        do_search = st.button("🔍 Search", type="primary", use_container_width=True)

    # Show API key status
    has_ebay_key = bool(get_setting("ebay_app_id") and get_setting("ebay_cert_id"))
    if not has_ebay_key:
        st.info(
            "ℹ️ No eBay API key configured — showing mock eBay data. "
            "Add your keys in the **🔔 Alerts** tab settings.",
            icon="ℹ️",
        )

    if do_search and search_query.strip():
        st.session_state["last_search_query"]  = search_query.strip()
        st.session_state["last_search_results"] = _search_both(search_query.strip())

    results = st.session_state.get("last_search_results")
    query   = st.session_state.get("last_search_query", "")

    if results and query:
        ebay    = results["ebay"]
        mercari = results["mercari"]
        ts      = results["checked_at"]
        mock_tag = "" if results["has_real_ebay"] else " (mock)"

        st.markdown(f"**Results for:** `{query}` — *checked {ts}*")
        st.divider()

        # ── Side-by-side price comparison ────────────────────────────────────
        col_e, col_m = st.columns(2)

        with col_e:
            st.markdown(
                '<div style="background:#12151c;border:1px solid #1e2330;border-radius:12px;padding:20px;">'
                f'<div style="font-size:1.1rem;font-weight:700;color:#FFAB76;">📦 eBay{mock_tag}</div>',
                unsafe_allow_html=True,
            )
            st.metric("Avg Listing Price",  f"${ebay['avg']:.2f}")
            st.metric("Lowest Listing",     f"${ebay['low']:.2f}")
            st.metric("Listings Found",     ebay["count"])
            ebay_net_avg = ebay_net(ebay["avg"])
            ebay_net_low = ebay_net(ebay["low"])
            st.markdown(
                f"<div style='background:#1a2a1a;border:1px solid #3a6b3a;border-radius:8px;padding:12px;margin-top:10px;'>"
                f"<div style='color:#7ec87e;font-weight:700;font-size:0.95rem;'>💵 If you sold today on eBay:</div>"
                f"<div style='font-size:1.3rem;font-weight:800;color:#fff;margin-top:4px;'>${ebay_net_avg:.2f} <span style='font-size:0.8rem;color:#8892a4;'>(net avg)</span></div>"
                f"<div style='font-size:0.85rem;color:#8892a4;margin-top:2px;'>Low listing net: ${ebay_net_low:.2f}</div>"
                f"<div style='font-size:0.75rem;color:#555;margin-top:6px;'>Fee: 12.9% + $0.30</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_m:
            is_mock = "Mercari (mock)" in (mercari["listings"][0]["source"] if mercari["listings"] else "Mercari (mock)")
            mock_m = " (mock)" if is_mock else ""
            st.markdown(
                '<div style="background:#12151c;border:1px solid #1e2330;border-radius:12px;padding:20px;">'
                f'<div style="font-size:1.1rem;font-weight:700;color:#FFAB76;">🏷️ Mercari{mock_m}</div>',
                unsafe_allow_html=True,
            )
            st.metric("Avg Listing Price",  f"${mercari['avg']:.2f}")
            st.metric("Lowest Listing",     f"${mercari['low']:.2f}")
            st.metric("Listings Found",     mercari["count"])
            merc_net_avg = mercari_net(mercari["avg"])
            merc_net_low = mercari_net(mercari["low"])
            st.markdown(
                f"<div style='background:#1a2a1a;border:1px solid #3a6b3a;border-radius:8px;padding:12px;margin-top:10px;'>"
                f"<div style='color:#7ec87e;font-weight:700;font-size:0.95rem;'>💵 If you sold today on Mercari:</div>"
                f"<div style='font-size:1.3rem;font-weight:800;color:#fff;margin-top:4px;'>${merc_net_avg:.2f} <span style='font-size:0.8rem;color:#8892a4;'>(net avg)</span></div>"
                f"<div style='font-size:0.85rem;color:#8892a4;margin-top:2px;'>Low listing net: ${merc_net_low:.2f}</div>"
                f"<div style='font-size:0.75rem;color:#555;margin-top:6px;'>Fee: 10% + $0.30</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Best platform recommendation ──────────────────────────────────────
        st.markdown("---")
        if ebay_net_avg > 0 and merc_net_avg > 0:
            if ebay_net_avg >= merc_net_avg:
                st.success(
                    f"✅ **eBay is better** for this shoe — you net **${ebay_net_avg:.2f}** vs **${merc_net_avg:.2f}** on Mercari "
                    f"(${ebay_net_avg - merc_net_avg:.2f} more per sale)"
                )
            else:
                st.success(
                    f"✅ **Mercari is better** for this shoe — you net **${merc_net_avg:.2f}** vs **${ebay_net_avg:.2f}** on eBay "
                    f"(${merc_net_avg - ebay_net_avg:.2f} more per sale)"
                )

        # ── Listings table ────────────────────────────────────────────────────
        st.markdown("---")
        col_el, col_ml = st.columns(2)

        with col_el:
            st.markdown("**📦 eBay Listings**")
            if ebay["listings"]:
                for item in ebay["listings"][:8]:
                    net = ebay_net(item["price"])
                    url = item.get("item_url", "")
                    title = item.get("title", item.get("name", ""))[:55]
                    link = f"[{title}]({url})" if url and url != "https://www.ebay.com" else title
                    st.markdown(
                        f"**${item['price']:.2f}** → net **${net:.2f}** — {link}  "
                        f"<span style='color:#8892a4;font-size:0.78rem;'>{item.get('condition','')}</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No eBay listings found.")

        with col_ml:
            st.markdown("**🏷️ Mercari Listings**")
            if mercari["listings"]:
                for item in mercari["listings"][:8]:
                    net = mercari_net(item["price"])
                    url = item.get("item_url", "")
                    title = item.get("name", item.get("title", ""))[:55]
                    link = f"[{title}]({url})" if url and url != "https://www.mercari.com" else title
                    st.markdown(
                        f"**${item['price']:.2f}** → net **${net:.2f}** — {link}  "
                        f"<span style='color:#8892a4;font-size:0.78rem;'>{item.get('condition','')}</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No Mercari listings found.")

        # ── Add to watchlist shortcut ─────────────────────────────────────────
        st.divider()
        with st.expander("➕ Add this shoe to Watchlist"):
            wl_name  = st.text_input("Display name", value=query, key="monitor_wl_name")
            wl_notes = st.text_input("Notes (optional)", key="monitor_wl_notes")
            if st.button("Add to Watchlist", key="monitor_add_wl"):
                _add_watchlist(query, wl_name, wl_notes)
                st.success(f"Added **{wl_name}** to watchlist!")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
with tab_watchlist:
    st.subheader("📋 Shoe Watchlist")

    # Add shoe form
    with st.expander("➕ Add Shoe to Watchlist", expanded=False):
        wc1, wc2 = st.columns(2)
        with wc1:
            new_sku  = st.text_input("SKU / Search term",    key="wl_sku",   placeholder='e.g. "Jordan 4 Red Thunder size 9"')
            new_name = st.text_input("Display name",         key="wl_name",  placeholder="Jordan 4 Red Thunder")
        with wc2:
            new_notes = st.text_input("Notes",               key="wl_notes", placeholder="Bought for $220")
        if st.button("Add to Watchlist", type="primary", key="wl_add_btn"):
            if new_sku.strip():
                _add_watchlist(new_sku.strip(), new_name.strip() or new_sku.strip(), new_notes.strip())
                st.success(f"Added **{new_name or new_sku}** to watchlist!")
                st.rerun()
            else:
                st.warning("Please enter a SKU or search term.")

    watchlist = _load_watchlist()

    if not watchlist:
        st.info("Your watchlist is empty. Search a shoe in the Price Monitor tab and add it, or add one above.")
    else:
        st.caption(f"**{len(watchlist)} shoes** on watchlist — click **Check Now** to get live prices.")

        for item in watchlist:
            sku      = item["sku"]
            name     = item.get("display_name") or sku
            notes    = item.get("notes", "")
            added_at = str(item.get("added_at", ""))[:10]
            item_id  = item["id"]

            # Load last known price from history
            history = _load_price_history(sku)
            ebay_last    = next((h for h in reversed(history) if h["platform"] == "ebay"),    None)
            mercari_last = next((h for h in reversed(history) if h["platform"] == "mercari"), None)

            with st.container():
                hdr, btn_col = st.columns([5, 1])
                with hdr:
                    st.markdown(f"#### 👟 {name}")
                    if notes:
                        st.caption(f"📝 {notes}")
                    st.caption(f"🔑 SKU: `{sku}` | Added: {added_at}")

                with btn_col:
                    if st.button("🔍 Check Now", key=f"wl_check_{item_id}"):
                        r = _search_both(sku, save_to_db=True)
                        st.session_state[f"wl_result_{item_id}"] = r

                # Price columns
                col_e, col_m = st.columns(2)
                wl_result = st.session_state.get(f"wl_result_{item_id}")

                with col_e:
                    if wl_result:
                        avg = wl_result["ebay"]["avg"]
                        low = wl_result["ebay"]["low"]
                        net = ebay_net(avg)
                        st.metric("eBay Avg",  f"${avg:.2f}", delta=f"net ${net:.2f}")
                        st.caption(f"Low: ${low:.2f}")
                    elif ebay_last:
                        avg = ebay_last["avg_price"]
                        net = ebay_net(avg)
                        ts  = str(ebay_last.get("checked_at", ""))[:16]
                        change = ""
                        older = [h for h in history if h["platform"] == "ebay"][:-1]
                        if older:
                            prev = older[-1]["avg_price"]
                            if prev > 0:
                                pct = round((avg - prev) / prev * 100, 1)
                                change = f"{'+' if pct >= 0 else ''}{pct}%"
                        st.metric("eBay Avg (last check)", f"${avg:.2f}", delta=change or None)
                        st.caption(f"Net: ${net:.2f} | Checked: {ts}")
                    else:
                        st.metric("eBay Avg", "—")
                        st.caption("Not checked yet")

                with col_m:
                    if wl_result:
                        avg = wl_result["mercari"]["avg"]
                        low = wl_result["mercari"]["low"]
                        net = mercari_net(avg)
                        st.metric("Mercari Avg", f"${avg:.2f}", delta=f"net ${net:.2f}")
                        st.caption(f"Low: ${low:.2f}")
                    elif mercari_last:
                        avg = mercari_last["avg_price"]
                        net = mercari_net(avg)
                        ts  = str(mercari_last.get("checked_at", ""))[:16]
                        change = ""
                        older = [h for h in history if h["platform"] == "mercari"][:-1]
                        if older:
                            prev = older[-1]["avg_price"]
                            if prev > 0:
                                pct = round((avg - prev) / prev * 100, 1)
                                change = f"{'+' if pct >= 0 else ''}{pct}%"
                        st.metric("Mercari Avg (last check)", f"${avg:.2f}", delta=change or None)
                        st.caption(f"Net: ${net:.2f} | Checked: {ts}")
                    else:
                        st.metric("Mercari Avg", "—")
                        st.caption("Not checked yet")

                if wl_result:
                    st.caption(f"✅ Live data — checked {wl_result['checked_at']}")

                col_del, _ = st.columns([1, 4])
                with col_del:
                    if st.button("🗑️ Remove", key=f"wl_del_{item_id}"):
                        _remove_watchlist(item_id)
                        st.session_state.pop(f"wl_result_{item_id}", None)
                        st.rerun()

                st.divider()

        # Bulk refresh button
        if st.button("🔄 Refresh All Prices", type="primary"):
            progress = st.progress(0, text="Refreshing watchlist…")
            for i, item in enumerate(watchlist):
                r = _search_both(item["sku"], save_to_db=True)
                st.session_state[f"wl_result_{item['id']}"] = r
                progress.progress((i + 1) / len(watchlist), text=f"Checked {item['sku']}")
            progress.empty()
            st.success("✅ All prices refreshed!")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRICE HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("📈 Historical Price Chart")

    all_skus = _load_all_history_skus()

    if not all_skus:
        st.info(
            "No price history yet. Use the Price Monitor or Watchlist tabs to "
            "search shoes — each search is saved to history."
        )
    else:
        selected_sku = st.selectbox("Select shoe (SKU / search term)", all_skus, key="hist_sku")

        if selected_sku:
            history = _load_price_history(selected_sku)

            # Split by platform
            ebay_h    = [h for h in history if h["platform"] == "ebay"]
            mercari_h = [h for h in history if h["platform"] == "mercari"]

            col_plat = st.columns(3)
            with col_plat[0]:
                platform_filter = st.selectbox(
                    "Platform", ["Both", "eBay", "Mercari"], key="hist_plat"
                )
            with col_plat[1]:
                price_type = st.selectbox("Price type", ["Average", "Low"], key="hist_ptype")

            price_key = "avg_price" if price_type == "Average" else "low_price"

            fig = go.Figure()

            if platform_filter in ("Both", "eBay") and ebay_h:
                ts_e = [str(h["checked_at"])[:16] for h in ebay_h]
                pr_e = [h[price_key] for h in ebay_h]
                fig.add_trace(go.Scatter(
                    x=ts_e, y=pr_e,
                    mode="lines+markers",
                    name="eBay",
                    line=dict(color="#FFAB76", width=2),
                    marker=dict(size=6),
                ))

            if platform_filter in ("Both", "Mercari") and mercari_h:
                ts_m = [str(h["checked_at"])[:16] for h in mercari_h]
                pr_m = [h[price_key] for h in mercari_h]
                fig.add_trace(go.Scatter(
                    x=ts_m, y=pr_m,
                    mode="lines+markers",
                    name="Mercari",
                    line=dict(color="#60a5fa", width=2),
                    marker=dict(size=6),
                ))

            fig.update_layout(
                title=f"{price_type} Listing Price — {selected_sku}",
                xaxis_title="Checked At",
                yaxis_title="Price ($)",
                hovermode="x unified",
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font=dict(color="#fafafa"),
                legend=dict(bgcolor="#12151c", bordercolor="#1e2330"),
                xaxis=dict(gridcolor="#1e2330"),
                yaxis=dict(gridcolor="#1e2330", tickprefix="$"),
            )

            st.plotly_chart(fig, use_container_width=True)

            # Summary stats
            st.divider()
            st.markdown("**📊 History Summary**")
            scol1, scol2, scol3, scol4 = st.columns(4)
            all_prices = [h[price_key] for h in history if h[price_key] > 0]
            if all_prices:
                scol1.metric("All-time High", f"${max(all_prices):.2f}")
                scol2.metric("All-time Low",  f"${min(all_prices):.2f}")
                scol3.metric("Overall Avg",   f"${sum(all_prices)/len(all_prices):.2f}")
                scol4.metric("Data Points",   len(all_prices))

            # Raw data
            with st.expander("🗃️ View Raw Data"):
                rows = []
                for h in history:
                    rows.append({
                        "Checked At":      str(h["checked_at"])[:19],
                        "Platform":        h["platform"].title(),
                        "Avg Price":       f"${h['avg_price']:.2f}",
                        "Low Price":       f"${h['low_price']:.2f}",
                        "Listings Found":  h["listing_count"],
                    })
                if rows:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PROFIT CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_profit:
    st.subheader("💰 Profit-After-Fees Calculator")
    st.caption("Enter your cost (COGS) and sale price to see real-time profit and ROI.")

    pc1, pc2 = st.columns(2)
    with pc1:
        cogs      = st.number_input("Cost of Goods (COGS) $", min_value=0.0, value=150.0, step=5.0, key="pc_cogs")
        sale_ebay = st.number_input("eBay Sale Price $",       min_value=0.0, value=200.0, step=5.0, key="pc_ebay")
        sale_merc = st.number_input("Mercari Sale Price $",    min_value=0.0, value=195.0, step=5.0, key="pc_merc")
        shipping  = st.number_input("Shipping cost (your cost) $", min_value=0.0, value=10.0, step=1.0, key="pc_ship")

    with pc2:
        # eBay calc
        ebay_fees    = round(sale_ebay * EBAY_FEE_PCT + EBAY_FEE_FLAT, 2)
        ebay_net_val = round(sale_ebay - ebay_fees - shipping, 2)
        ebay_profit  = round(ebay_net_val - cogs, 2)
        ebay_roi     = round((ebay_profit / cogs * 100), 1) if cogs > 0 else 0.0
        ebay_margin  = round((ebay_profit / sale_ebay * 100), 1) if sale_ebay > 0 else 0.0

        # Mercari calc
        merc_fees    = round(sale_merc * MERCARI_FEE_PCT + MERCARI_FEE_FLAT, 2)
        merc_net_val = round(sale_merc - merc_fees - shipping, 2)
        merc_profit  = round(merc_net_val - cogs, 2)
        merc_roi     = round((merc_profit / cogs * 100), 1) if cogs > 0 else 0.0
        merc_margin  = round((merc_profit / sale_merc * 100), 1) if sale_merc > 0 else 0.0

        st.markdown("**📦 eBay Breakdown**")
        st.markdown(
            f"<div style='background:#12151c;border:1px solid #1e2330;border-radius:10px;padding:16px;margin-bottom:12px;'>"
            f"<table style='width:100%;color:#fafafa;font-size:0.9rem;'>"
            f"<tr><td>Sale Price</td><td align='right'><b>${sale_ebay:.2f}</b></td></tr>"
            f"<tr><td>eBay Fees (12.9% + $0.30)</td><td align='right' style='color:#ff6b6b;'>−${ebay_fees:.2f}</td></tr>"
            f"<tr><td>Shipping Cost</td><td align='right' style='color:#ff6b6b;'>−${shipping:.2f}</td></tr>"
            f"<tr><td>COGS</td><td align='right' style='color:#ff6b6b;'>−${cogs:.2f}</td></tr>"
            f"<tr style='border-top:1px solid #1e2330;'><td><b>Net Profit</b></td>"
            f"<td align='right'><b style='color:{'#7ec87e' if ebay_profit >= 0 else '#ff6b6b'};font-size:1.2rem;'>${ebay_profit:.2f}</b></td></tr>"
            f"<tr><td>ROI</td><td align='right'>{ebay_roi:+.1f}%</td></tr>"
            f"<tr><td>Margin</td><td align='right'>{ebay_margin:.1f}%</td></tr>"
            f"</table></div>",
            unsafe_allow_html=True,
        )

        st.markdown("**🏷️ Mercari Breakdown**")
        st.markdown(
            f"<div style='background:#12151c;border:1px solid #1e2330;border-radius:10px;padding:16px;'>"
            f"<table style='width:100%;color:#fafafa;font-size:0.9rem;'>"
            f"<tr><td>Sale Price</td><td align='right'><b>${sale_merc:.2f}</b></td></tr>"
            f"<tr><td>Mercari Fees (10% + $0.30)</td><td align='right' style='color:#ff6b6b;'>−${merc_fees:.2f}</td></tr>"
            f"<tr><td>Shipping Cost</td><td align='right' style='color:#ff6b6b;'>−${shipping:.2f}</td></tr>"
            f"<tr><td>COGS</td><td align='right' style='color:#ff6b6b;'>−${cogs:.2f}</td></tr>"
            f"<tr style='border-top:1px solid #1e2330;'><td><b>Net Profit</b></td>"
            f"<td align='right'><b style='color:{'#7ec87e' if merc_profit >= 0 else '#ff6b6b'};font-size:1.2rem;'>${merc_profit:.2f}</b></td></tr>"
            f"<tr><td>ROI</td><td align='right'>{merc_roi:+.1f}%</td></tr>"
            f"<tr><td>Margin</td><td align='right'>{merc_margin:.1f}%</td></tr>"
            f"</table></div>",
            unsafe_allow_html=True,
        )

    # Best platform summary
    st.divider()
    best_profit = max(ebay_profit, merc_profit)
    best_plat   = "eBay" if ebay_profit >= merc_profit else "Mercari"
    diff        = abs(ebay_profit - merc_profit)

    if best_profit > 0:
        st.success(
            f"🏆 **{best_plat} wins** — ${best_profit:.2f} profit "
            f"(${diff:.2f} more than the other platform) | ROI: {ebay_roi if best_plat == 'eBay' else merc_roi:.1f}%"
        )
    elif best_profit < 0:
        st.error(
            f"❌ Unprofitable on both platforms at these prices. "
            f"Best case: {best_plat} at ${best_profit:.2f}. "
            f"You need to sell for at least ${cogs + shipping + (cogs * 0.15):.2f} to break even on eBay."
        )
    else:
        st.warning("⚠️ Break-even — no profit at these prices.")

    # Break-even analysis
    st.divider()
    st.markdown("**📐 Break-Even Analysis**")
    be1, be2 = st.columns(2)
    # Break-even price = (COGS + shipping + flat_fee) / (1 - fee_pct)
    ebay_breakeven  = round((cogs + shipping + EBAY_FEE_FLAT) / (1 - EBAY_FEE_PCT), 2)
    merc_breakeven  = round((cogs + shipping + MERCARI_FEE_FLAT) / (1 - MERCARI_FEE_PCT), 2)
    with be1:
        st.metric("eBay Break-Even Price",    f"${ebay_breakeven:.2f}")
    with be2:
        st.metric("Mercari Break-Even Price", f"${merc_breakeven:.2f}")

    # Volume projections
    st.divider()
    st.markdown("**📦 Volume Projections**")
    vol = st.slider("Units to sell", 1, 50, 5, key="pc_vol")
    vcol1, vcol2, vcol3, vcol4 = st.columns(4)
    vcol1.metric("eBay Total Revenue",  f"${sale_ebay * vol:,.2f}")
    vcol2.metric("eBay Total Profit",   f"${ebay_profit * vol:,.2f}")
    vcol3.metric("Mercari Total Revenue", f"${sale_merc * vol:,.2f}")
    vcol4.metric("Mercari Total Profit",  f"${merc_profit * vol:,.2f}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — ALERTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_alerts:
    st.subheader("🔔 Price Alerts & Settings")

    # ── API key settings ──────────────────────────────────────────────────────
    with st.expander("⚙️ API Key Settings", expanded=False):
        st.markdown("**eBay API Credentials** (for live data)")
        st.caption(
            "Get your keys from [developer.ebay.com](https://developer.ebay.com). "
            "You need Client ID (App ID) and Client Secret (Cert ID)."
        )
        ec1, ec2 = st.columns(2)
        with ec1:
            ebay_app  = st.text_input(
                "eBay App ID (Client ID)",
                value=get_setting("ebay_app_id", ""),
                type="password",
                key="cfg_ebay_app",
            )
        with ec2:
            ebay_cert = st.text_input(
                "eBay Cert ID (Client Secret)",
                value=get_setting("ebay_cert_id", ""),
                type="password",
                key="cfg_ebay_cert",
            )
        if st.button("💾 Save eBay Keys", key="save_ebay_keys"):
            if ebay_app.strip():
                set_setting("ebay_app_id",  ebay_app.strip())
            if ebay_cert.strip():
                set_setting("ebay_cert_id", ebay_cert.strip())
            st.success("eBay API keys saved!")
            # Quick token test
            tok = _get_ebay_token()
            if tok:
                st.success("✅ eBay token obtained successfully — keys are valid!")
            else:
                st.warning("⚠️ Could not get eBay token — double-check your keys.")

        st.divider()
        st.markdown("**Telegram Bot Settings** (for price alerts)")
        st.caption(
            "Create a bot via [@BotFather](https://t.me/BotFather) and get your chat ID "
            "from [@userinfobot](https://t.me/userinfobot)."
        )
        tc1, tc2 = st.columns(2)
        with tc1:
            tg_token = st.text_input(
                "Bot Token",
                value=get_setting("telegram_bot_token", ""),
                type="password",
                key="cfg_tg_token",
            )
        with tc2:
            tg_chat = st.text_input(
                "Chat ID",
                value=get_setting("telegram_chat_id", ""),
                key="cfg_tg_chat",
            )
        col_save_tg, col_test_tg = st.columns(2)
        with col_save_tg:
            if st.button("💾 Save Telegram Settings", key="save_tg"):
                if tg_token.strip():
                    set_setting("telegram_bot_token", tg_token.strip())
                if tg_chat.strip():
                    set_setting("telegram_chat_id",   tg_chat.strip())
                st.success("Telegram settings saved!")
        with col_test_tg:
            if st.button("📲 Send Test Message", key="test_tg"):
                ok = _send_telegram(
                    "🍑 <b>SoleOps Price Monitor</b>\n"
                    "✅ Telegram alerts are working! Your bot is connected."
                )
                if ok:
                    st.success("✅ Test message sent!")
                else:
                    st.error("❌ Failed — check your bot token and chat ID.")

    # ── Alert configuration ───────────────────────────────────────────────────
    st.divider()
    st.markdown("**➕ Create New Alert**")

    al1, al2, al3, al4 = st.columns(4)
    with al1:
        alert_sku       = st.text_input("Shoe (SKU / search term)", key="al_sku", placeholder='e.g. "Jordan 1 Chicago"')
    with al2:
        alert_platform  = st.selectbox("Platform", ["both", "ebay", "mercari"], key="al_plat")
    with al3:
        alert_condition = st.selectbox("Trigger when price is", ["below", "above"], key="al_cond")
    with al4:
        alert_threshold = st.number_input("Threshold $", min_value=0.0, value=200.0, step=5.0, key="al_thresh")

    if st.button("🔔 Create Alert", type="primary", key="al_create"):
        if alert_sku.strip():
            has_tg = bool(get_setting("telegram_bot_token") and get_setting("telegram_chat_id"))
            _add_alert(alert_sku.strip(), alert_platform, alert_condition, alert_threshold)
            if has_tg:
                st.success(
                    f"✅ Alert created — you'll get a Telegram message when "
                    f"**{alert_sku}** on **{alert_platform}** is **{alert_condition}** ${alert_threshold:.2f}"
                )
            else:
                st.warning(
                    "Alert created, but no Telegram bot configured — "
                    "add your bot token + chat ID above to receive notifications."
                )
            st.rerun()
        else:
            st.warning("Please enter a SKU or search term.")

    # ── Active alerts list ────────────────────────────────────────────────────
    st.divider()
    st.markdown("**📋 Active Alerts**")

    alerts = _load_alerts()
    if not alerts:
        st.info("No alerts yet. Create one above to get notified when a shoe hits your target price.")
    else:
        tg_configured = bool(get_setting("telegram_bot_token") and get_setting("telegram_chat_id"))
        if not tg_configured:
            st.warning("⚠️ Telegram not configured — alerts will fire when prices are checked but won't send messages.")

        for alert in alerts:
            alert_id       = alert["id"]
            a_sku          = alert["sku"]
            a_platform     = alert["platform"]
            a_condition    = alert["condition"]
            a_threshold    = float(alert["threshold"])
            a_active       = bool(alert["active"])
            a_last_trig    = str(alert.get("last_triggered") or "Never")[:16]

            status_icon = "🟢" if a_active else "🔴"
            with st.container():
                ac1, ac2, ac3, ac4, ac5 = st.columns([3, 1, 1, 1, 1])
                ac1.markdown(
                    f"{status_icon} **{a_sku}** — {a_platform.title()} price {a_condition} "
                    f"**${a_threshold:.2f}**"
                )
                ac2.caption(f"Last triggered: {a_last_trig}")

                with ac3:
                    toggle_label = "Pause" if a_active else "Enable"
                    if st.button(toggle_label, key=f"al_tog_{alert_id}"):
                        _toggle_alert(alert_id, 0 if a_active else 1)
                        st.rerun()

                with ac4:
                    if st.button("🔍 Check Now", key=f"al_check_{alert_id}"):
                        r = _search_both(a_sku, save_to_db=True)
                        if a_platform in ("both", "ebay"):
                            avg_e = r["ebay"]["avg"]
                            _check_alerts_against_price(a_sku, "ebay", avg_e)
                        if a_platform in ("both", "mercari"):
                            avg_m = r["mercari"]["avg"]
                            _check_alerts_against_price(a_sku, "mercari", avg_m)
                        st.toast(f"Checked {a_sku}!")

                with ac5:
                    if st.button("🗑️ Delete", key=f"al_del_{alert_id}"):
                        _delete_alert(alert_id)
                        st.rerun()

                st.divider()

    # ── How alerts work ───────────────────────────────────────────────────────
    with st.expander("ℹ️ How Alerts Work"):
        st.markdown("""
**SoleOps price alerts work like this:**

1. **Create an alert** with a SKU, platform (eBay, Mercari, or both), and threshold price.
2. **Alerts fire** whenever you:
   - Click "Check Now" in the Watchlist tab
   - Click "🔍 Search" in the Price Monitor tab
   - Click "🔄 Refresh All" in the Watchlist
   - Click "🔍 Check Now" next to any alert above
3. **Telegram message** is sent immediately when the condition is met.
4. Alerts are stored in the database and persist across sessions.

**Fee structure used:**
- eBay: **12.9%** + **$0.30** flat fee per sale
- Mercari: **10%** + **$0.30** flat fee per sale

**For automated background checks**, set up a cron job or use the Sole Alert Bot in `sole_alert_bot/`.
        """)
