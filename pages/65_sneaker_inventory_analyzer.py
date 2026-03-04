import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sys
import os
import requests
import anthropic

st.set_page_config(page_title="SoleOps — Inventory Analyzer | Peach State Savings", page_icon="🍑", layout="wide")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# ── Constants ─────────────────────────────────────────────────────────────────
EBAY_FEE_RATE     = 0.129
EBAY_FEE_FIXED    = 0.30
MERCARI_FEE_RATE  = 0.10
MERCARI_FEE_FIXED = 0.30
STOCKX_FEE_RATE   = 0.115
GOAT_FEE_RATE     = 0.095
GOAT_FEE_FIXED    = 5.00

PLATFORMS  = ["eBay", "Mercari", "StockX", "GOAT", "Poshmark", "Facebook", "Other", "Unlisted"]
CONDITIONS = ["New with box", "New without box", "Like New", "Good", "Fair", "Poor"]

# (min_days, max_days, label, drop_pct, tier_idx)
AGING_TIERS = [
    (0,  7,  "🟢 Fresh",    0.00, 0),
    (7,  14, "🟡 Warm",     0.05, 1),
    (14, 21, "🟠 Aging",    0.10, 2),
    (21, 30, "🔴 Stale",    0.15, 3),
    (30, 999,"⚫ Critical", 0.20, 4),
]


# ── Database ──────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                shoe_name TEXT NOT NULL,
                brand TEXT DEFAULT '',
                colorway TEXT DEFAULT '',
                size TEXT NOT NULL,
                cost_basis REAL NOT NULL DEFAULT 0,
                condition TEXT DEFAULT 'New with box',
                listed_date DATE,
                listed_price REAL,
                listed_platform TEXT DEFAULT 'Unlisted',
                status TEXT DEFAULT 'inventory',
                sell_price REAL,
                sold_date DATE,
                sold_platform TEXT,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_suggestions (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES soleops_inventory(id) ON DELETE CASCADE,
                shoe_name TEXT,
                size TEXT,
                current_price REAL,
                suggested_price REAL,
                drop_pct REAL,
                reason TEXT,
                days_listed INTEGER,
                ebay_avg REAL DEFAULT 0,
                mercari_avg REAL DEFAULT 0,
                suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action_taken TEXT
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shoe_name TEXT NOT NULL,
                brand TEXT DEFAULT '',
                colorway TEXT DEFAULT '',
                size TEXT NOT NULL,
                cost_basis REAL NOT NULL DEFAULT 0,
                condition TEXT DEFAULT 'New with box',
                listed_date TEXT,
                listed_price REAL,
                listed_platform TEXT DEFAULT 'Unlisted',
                status TEXT DEFAULT 'inventory',
                sell_price REAL,
                sold_date TEXT,
                sold_platform TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                shoe_name TEXT,
                size TEXT,
                current_price REAL,
                suggested_price REAL,
                drop_pct REAL,
                reason TEXT,
                days_listed INTEGER,
                ebay_avg REAL DEFAULT 0,
                mercari_avg REAL DEFAULT 0,
                suggested_at TEXT DEFAULT (datetime('now')),
                action_taken TEXT,
                FOREIGN KEY (inventory_id) REFERENCES soleops_inventory(id) ON DELETE CASCADE
            )
        """)
    conn.commit()
    conn.close()


_ensure_tables()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
render_sidebar_user_widget()


# ── Business Logic ────────────────────────────────────────────────────────────
def _calc_profit(sell_price: float, cost_basis: float, platform: str) -> float:
    """Net profit after platform fees."""
    p = (platform or "").lower()
    if "ebay" in p:
        fees = (sell_price * EBAY_FEE_RATE) + EBAY_FEE_FIXED
    elif "mercari" in p:
        fees = (sell_price * MERCARI_FEE_RATE) + MERCARI_FEE_FIXED
    elif "stockx" in p:
        fees = sell_price * STOCKX_FEE_RATE
    elif "goat" in p:
        fees = (sell_price * GOAT_FEE_RATE) + GOAT_FEE_FIXED
    else:
        fees = sell_price * 0.10
    return round(sell_price - fees - cost_basis, 2)


def _get_aging_tier(days: int) -> dict:
    for lo, hi, label, drop_pct, tier_idx in AGING_TIERS:
        if lo <= days < hi:
            return {"label": label, "drop_pct": drop_pct, "tier": tier_idx, "days": days}
    return {"label": "⚫ Critical", "drop_pct": 0.20, "tier": 4, "days": days}


def _calc_days_listed(listed_date_val) -> int:
    if not listed_date_val:
        return 0
    try:
        if isinstance(listed_date_val, str):
            listed = datetime.strptime(listed_date_val[:10], "%Y-%m-%d").date()
        else:
            listed = listed_date_val
        return max(0, (date.today() - listed).days)
    except Exception:
        return 0


def _get_suggested_price(current_price: float, days_listed: int):
    tier = _get_aging_tier(days_listed)
    if tier["drop_pct"] == 0 or not current_price:
        return current_price, "Hold — still fresh"
    new_price = round(current_price * (1 - tier["drop_pct"]), 2)
    reason = f"{tier['label']} — {int(tier['drop_pct']*100)}% drop suggested"
    return new_price, reason


# ── CRUD ──────────────────────────────────────────────────────────────────────
def _load_inventory(user_id: int, status: str = "inventory") -> list[dict]:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    # SQLite-compatible ORDER BY (no NULLS LAST keyword)
    order = "ORDER BY CASE WHEN listed_date IS NULL THEN 1 ELSE 0 END, listed_date ASC, created_at DESC"
    cur.execute(f"""
        SELECT id, shoe_name, brand, colorway, size, cost_basis, condition,
               listed_date, listed_price, listed_platform, status,
               sell_price, sold_date, sold_platform, notes, created_at
        FROM soleops_inventory
        WHERE user_id = {ph} AND status = {ph}
        {order}
    """, (user_id, status))
    rows = cur.fetchall()
    conn.close()
    items = []
    for r in rows:
        days = _calc_days_listed(r[7])
        tier = _get_aging_tier(days)
        listed_price = float(r[8]) if r[8] else 0.0
        cost_basis = float(r[5]) if r[5] else 0.0
        sugg_price, sugg_reason = _get_suggested_price(listed_price, days) if listed_price > 0 else (0.0, "")
        pot_profit = _calc_profit(listed_price, cost_basis, r[9] or "ebay") if listed_price > 0 else 0.0
        items.append({
            "id": r[0], "shoe_name": r[1], "brand": r[2] or "",
            "colorway": r[3] or "", "size": r[4],
            "cost_basis": cost_basis, "condition": r[6] or "",
            "listed_date": r[7], "listed_price": listed_price,
            "listed_platform": r[9] or "Unlisted", "status": r[10],
            "sell_price": float(r[11]) if r[11] else 0.0,
            "sold_date": r[12], "sold_platform": r[13] or "",
            "notes": r[14] or "",
            "days_listed": days, "aging_tier": tier,
            "suggested_price": sugg_price, "suggestion_reason": sugg_reason,
            "potential_profit": pot_profit,
        })
    return items


def _load_sold(user_id: int) -> list[dict]:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, shoe_name, size, cost_basis, sell_price, sold_date, sold_platform, notes
        FROM soleops_inventory
        WHERE user_id = {ph} AND status = 'sold'
        ORDER BY sold_date DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{
        "id": r[0], "shoe_name": r[1], "size": r[2],
        "cost_basis": float(r[3]) if r[3] else 0.0,
        "sell_price": float(r[4]) if r[4] else 0.0,
        "sold_date": r[5], "sold_platform": r[6] or "",
        "net_profit": _calc_profit(float(r[4]) if r[4] else 0, float(r[3]) if r[3] else 0, r[6] or "ebay"),
        "notes": r[7] or "",
    } for r in rows]


def _create_item(user_id, shoe_name, brand, colorway, size, cost_basis,
                 condition, listed_date, listed_price, listed_platform, notes):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO soleops_inventory
        (user_id, shoe_name, brand, colorway, size, cost_basis, condition,
         listed_date, listed_price, listed_platform, status, notes)
        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},'inventory',{ph})
    """, (user_id, shoe_name, brand, colorway, size, cost_basis, condition,
          str(listed_date) if listed_date else None,
          listed_price if listed_price else None,
          listed_platform, notes))
    conn.commit()
    conn.close()


def _update_listing(item_id, listed_price, listed_platform, listed_date, notes):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE soleops_inventory
        SET listed_price={ph}, listed_platform={ph}, listed_date={ph}, notes={ph}
        WHERE id={ph}
    """, (listed_price if listed_price else None,
          listed_platform,
          str(listed_date) if listed_date else None,
          notes, item_id))
    conn.commit()
    conn.close()


def _mark_sold(item_id, sell_price, sold_platform, sold_date):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE soleops_inventory
        SET status='sold', sell_price={ph}, sold_platform={ph}, sold_date={ph}
        WHERE id={ph}
    """, (sell_price, sold_platform, str(sold_date) if sold_date else str(date.today()), item_id))
    conn.commit()
    conn.close()


def _delete_item(item_id):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"DELETE FROM soleops_inventory WHERE id = {ph}", (item_id,))
    conn.commit()
    conn.close()


# ── External APIs ─────────────────────────────────────────────────────────────
def _fetch_live_prices(query: str) -> dict:
    result = {"ebay_avg": 0.0, "ebay_low": 0.0, "mercari_avg": 0.0, "mercari_low": 0.0, "error": None}
    try:
        client_id = get_setting("ebay_app_id") or get_setting("ebay_client_id")
        client_secret = get_setting("ebay_cert_id") or get_setting("ebay_client_secret")
        if client_id and client_secret:
            from sole_alert_bot.ebay_search import get_ebay_token, ebay_avg_price, ebay_low_price
            token = get_ebay_token(client_id, client_secret)
            if token:
                result["ebay_avg"] = ebay_avg_price(query, token)
                result["ebay_low"] = ebay_low_price(query, token)
    except Exception as e:
        result["error"] = str(e)
    try:
        from sole_alert_bot.mercari_search import mercari_avg_price, mercari_low_price
        result["mercari_avg"] = mercari_avg_price(query)
        result["mercari_low"] = mercari_low_price(query)
    except Exception:
        pass
    return result


def _send_stale_telegram(item: dict) -> bool:
    token = get_setting("telegram_bot_token")
    chat_id = get_setting("telegram_chat_id")
    if not token or not chat_id:
        return False
    msg = (
        f"⏰ <b>STALE INVENTORY ALERT</b>\n"
        f"👟 <b>{item['shoe_name']}</b> (Sz {item['size']})\n"
        f"📅 Listed {item['days_listed']} days ago on {item['listed_platform']}\n"
        f"💰 Listed at: ${item['listed_price']:.0f} | Cost: ${item['cost_basis']:.0f}\n"
        f"💡 Suggested: <b>${item['suggested_price']:.0f}</b> ({item['suggestion_reason']})"
    )
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
        return r.status_code == 200
    except Exception:
        return False


def _get_ai_insights(inventory: list[dict]) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ AI insights unavailable — configure Anthropic API key in settings."
    if not inventory:
        return "No inventory to analyze."
    stale = [i for i in inventory if i["aging_tier"]["tier"] >= 2]
    total_cost = sum(i["cost_basis"] for i in inventory)
    total_value = sum(i["listed_price"] for i in inventory if i["listed_price"])
    stale_summary = ", ".join(i["shoe_name"] + " Sz" + i["size"] + " (" + str(i["days_listed"]) + "d)" for i in stale[:5])
    summary = (
        f"Inventory: {len(inventory)} pairs | Cost basis: ${total_cost:.0f} | "
        f"Listed value: ${total_value:.0f} | Stale (14d+): {len(stale)}\n"
        f"Stale pairs: {stale_summary}"
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content":
                f"You are a sneaker resale advisor. Give 3 specific, actionable recommendations "
                f"to maximize profit on this inventory. Use actual dollar amounts. Be direct.\n\n{summary}"}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"AI error: {str(e)}"


# ── Page Header ───────────────────────────────────────────────────────────────
st.title("👟 SoleOps — Sneaker Inventory Analyzer")
st.markdown("*Track aging, get price drop suggestions, and maximize your resale P&L.*")

user_id = st.session_state.get("user_id", 1)
inventory = _load_inventory(user_id, "inventory")

# ── KPI Cards ─────────────────────────────────────────────────────────────────
total_pairs = len(inventory)
total_cost = sum(i["cost_basis"] for i in inventory)
total_value = sum(i["listed_price"] for i in inventory if i["listed_price"])
stale_count = sum(1 for i in inventory if i["aging_tier"]["tier"] >= 2)
total_potential_profit = sum(i["potential_profit"] for i in inventory if i["potential_profit"] > 0)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("👟 Pairs in Inventory", total_pairs)
with k2:
    st.metric("💰 Total Cost Basis", f"${total_cost:,.0f}")
with k3:
    paper = total_value - total_cost
    st.metric("📈 Listed Value", f"${total_value:,.0f}",
              delta=f"+${paper:,.0f} paper" if paper > 0 else None)
with k4:
    st.metric("⏰ Stale Pairs (14d+)", stale_count,
              delta="Need attention" if stale_count > 0 else "All fresh",
              delta_color="inverse" if stale_count > 0 else "normal")
with k5:
    st.metric("💵 Est. Profit (if sold now)", f"${total_potential_profit:,.0f}")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Inventory",
    "⏰ Aging Alerts",
    "🔍 Price Lookup",
    "➕ Add / Edit",
    "📈 P&L Analytics",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1: INVENTORY OVERVIEW
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    if not inventory:
        st.info("👟 No inventory yet. Add your first pair in the **➕ Add / Edit** tab!")
    else:
        fc1, fc2 = st.columns([1, 3])
        with fc1:
            filter_platform = st.selectbox("Platform", ["All"] + PLATFORMS, key="fp")
        with fc2:
            filter_age = st.selectbox("Age filter", [
                "All", "🟢 Fresh (0-7d)", "🟡 Warm (7-14d)",
                "🟠 Aging (14-21d)", "🔴 Stale (21-30d)", "⚫ Critical (30d+)"
            ], key="fa")

        filtered = inventory
        if filter_platform != "All":
            filtered = [i for i in filtered if filter_platform.lower() in (i["listed_platform"] or "").lower()]
        tier_label_map = {"🟢 Fresh": 0, "🟡 Warm": 1, "🟠 Aging": 2, "🔴 Stale": 3, "⚫ Critical": 4}
        if filter_age != "All":
            target = next((v for k, v in tier_label_map.items() if k in filter_age), None)
            if target is not None:
                filtered = [i for i in filtered if i["aging_tier"]["tier"] == target]

        rows = []
        for item in filtered:
            tier = item["aging_tier"]
            rows.append({
                "ID": item["id"],
                "Shoe": item["shoe_name"],
                "Sz": item["size"],
                "Cost": f"${item['cost_basis']:.0f}",
                "Listed $": f"${item['listed_price']:.0f}" if item["listed_price"] else "—",
                "Platform": item["listed_platform"],
                "Days": item["days_listed"] if item.get("listed_date") else "—",
                "Age Status": tier["label"],
                "Suggested $": (f"${item['suggested_price']:.0f}" if item["aging_tier"]["tier"] > 0 and item["suggested_price"] else "Hold"),
                "Est. Profit": f"${item['potential_profit']:.0f}" if item["potential_profit"] else "—",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"ID": st.column_config.NumberColumn(width="small"),
                                    "Days": st.column_config.NumberColumn(width="small")})

        st.markdown("### ⚡ Quick Actions")
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            if st.button("🤖 AI Inventory Insights", use_container_width=True, type="primary"):
                with st.spinner("Claude is analyzing your inventory..."):
                    insights = _get_ai_insights(inventory)
                st.info(insights)
        with qc2:
            stale_items = [i for i in inventory if i["aging_tier"]["tier"] >= 2 and i["listed_price"]]
            if st.button(f"📱 Alert All Stale ({len(stale_items)} pairs)", use_container_width=True):
                sent = sum(1 for i in stale_items if _send_stale_telegram(i))
                if sent > 0:
                    st.success(f"✅ Sent {sent} Telegram alert(s)!")
                else:
                    st.warning("⚠️ Configure Telegram token in app settings first.")
        with qc3:
            if st.button("📤 Export CSV", use_container_width=True):
                csv = df.to_csv(index=False)
                st.download_button("⬇️ Download", csv, "soleops_inventory.csv", "text/csv")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2: AGING ALERTS
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("⏰ Aging Inventory — Price Drop Suggestions")

    # Legend
    lc1, lc2, lc3, lc4, lc5 = st.columns(5)
    with lc1: st.markdown("🟢 **Fresh** 0–7d → Hold")
    with lc2: st.markdown("🟡 **Warm** 7–14d → 5% drop")
    with lc3: st.markdown("🟠 **Aging** 14–21d → 10% drop")
    with lc4: st.markdown("🔴 **Stale** 21–30d → 15% drop")
    with lc5: st.markdown("⚫ **Critical** 30d+ → 20%+ or relist")
    st.markdown("---")

    aging = sorted([i for i in inventory if i["aging_tier"]["tier"] > 0 and i.get("listed_date")],
                   key=lambda x: x["days_listed"], reverse=True)

    if not aging:
        st.success("🎉 All inventory is fresh! Nothing needs repricing right now.")
    else:
        for item in aging:
            tier = item["aging_tier"]
            ca, cb, cc, cd, ce = st.columns([3, 1, 1, 1, 2])
            with ca:
                st.markdown(f"**{tier['label']}** &nbsp; 👟 **{item['shoe_name']}** (Sz {item['size']}) — {item['listed_platform']}")
            with cb:
                st.metric("Days", item["days_listed"])
            with cc:
                st.metric("Listed $", f"${item['listed_price']:.0f}" if item["listed_price"] else "—")
            with cd:
                drop = int(tier["drop_pct"] * 100)
                st.metric("Suggest $",
                          f"${item['suggested_price']:.0f}" if item["suggested_price"] else "—",
                          delta=f"-{drop}%" if drop else None, delta_color="inverse")
            with ce:
                if item["suggested_price"] and item["cost_basis"]:
                    profit_at_sugg = _calc_profit(item["suggested_price"], item["cost_basis"], item["listed_platform"])
                    profit_emoji = "💰" if profit_at_sugg > 0 else "📉"
                    st.markdown(f"{profit_emoji} **${profit_at_sugg:.0f}** profit at suggested price")

            if st.button(f"📱 Send Alert — {item['shoe_name'][:30]}", key=f"alert_{item['id']}"):
                ok = _send_stale_telegram(item)
                st.success("✅ Alert sent!") if ok else st.warning("⚠️ Configure Telegram in settings.")
            st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3: PRICE LOOKUP
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🔍 Live Price Lookup — eBay + Mercari")

    selected_item = None
    if inventory:
        options = ["— Custom search —"] + [f"{i['shoe_name']} Sz {i['size']}" for i in inventory]
        sel = st.selectbox("Quick-select from your inventory:", options, key="inv_sel")
        if sel != "— Custom search —":
            selected_item = next((i for i in inventory if f"{i['shoe_name']} Sz {i['size']}" == sel), None)
        default_q = f"{selected_item['shoe_name']} size {selected_item['size']}" if selected_item else ""
    else:
        default_q = ""

    sc1, sc2 = st.columns([4, 1])
    with sc1:
        search_q = st.text_input("Search query:", value=default_q,
                                  placeholder="Jordan 1 Retro High Chicago size 10", key="sq")
    with sc2:
        st.markdown("")
        st.markdown("")
        fetch_btn = st.button("🔍 Fetch Prices", type="primary", use_container_width=True)

    if fetch_btn and search_q:
        with st.spinner(f"Checking eBay + Mercari for: {search_q}..."):
            prices = _fetch_live_prices(search_q)

        if prices["ebay_avg"] == 0 and prices["mercari_avg"] == 0:
            st.warning("⚠️ No prices found. Check eBay API credentials in settings, or try a broader search term.")
        else:
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("eBay Avg", f"${prices['ebay_avg']:.0f}" if prices['ebay_avg'] else "N/A")
            with m2: st.metric("eBay Low", f"${prices['ebay_low']:.0f}" if prices['ebay_low'] else "N/A")
            with m3: st.metric("Mercari Avg", f"${prices['mercari_avg']:.0f}" if prices['mercari_avg'] else "N/A")
            with m4: st.metric("Mercari Low", f"${prices['mercari_low']:.0f}" if prices['mercari_low'] else "N/A")

            if selected_item:
                st.markdown("### 💰 Profit Analysis for Your Pair")
                eb_profit = _calc_profit(prices["ebay_avg"], selected_item["cost_basis"], "ebay") if prices["ebay_avg"] else 0
                mc_profit = _calc_profit(prices["mercari_avg"], selected_item["cost_basis"], "mercari") if prices["mercari_avg"] else 0
                best = "eBay" if eb_profit >= mc_profit else "Mercari"

                pa1, pa2, pa3 = st.columns(3)
                with pa1:
                    st.metric("eBay Profit", f"${eb_profit:.0f}",
                              delta=f"After {EBAY_FEE_RATE*100:.0f}% fees")
                with pa2:
                    st.metric("Mercari Profit", f"${mc_profit:.0f}",
                              delta=f"After {MERCARI_FEE_RATE*100:.0f}% fees")
                with pa3:
                    best_p = max(eb_profit, mc_profit)
                    st.metric(f"🏆 Best: {best}", f"${best_p:.0f}")

                st.info(f"💡 List on **{best}** → **${max(eb_profit, mc_profit):.0f} profit** after fees (cost basis: ${selected_item['cost_basis']:.0f})")

            # Bar chart
            cats = ["eBay Avg", "eBay Low", "Mercari Avg", "Mercari Low"]
            vals = [prices["ebay_avg"], prices["ebay_low"], prices["mercari_avg"], prices["mercari_low"]]
            colors = ["#0064d2", "#4d9de0", "#ff0211", "#ff6b6b"]
            fig = go.Figure()
            for cat, val, color in zip(cats, vals, colors):
                if val > 0:
                    fig.add_trace(go.Bar(name=cat, x=[cat], y=[val], marker_color=color,
                                         text=f"${val:.0f}", textposition="outside"))
            if selected_item and selected_item["listed_price"]:
                fig.add_hline(y=selected_item["listed_price"], line_dash="dash", line_color="green",
                              annotation_text=f"Your price: ${selected_item['listed_price']:.0f}")
            if selected_item:
                fig.add_hline(y=selected_item["cost_basis"], line_dash="dot", line_color="red",
                              annotation_text=f"Cost: ${selected_item['cost_basis']:.0f}")
            fig.update_layout(title=f"Market Prices: {search_q}", yaxis_title="Price ($)",
                              template="plotly_white", showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4: ADD / EDIT
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("➕ Add New Pair to Inventory")
    with st.form("add_form"):
        ac1, ac2 = st.columns(2)
        with ac1:
            shoe_name  = st.text_input("Shoe Name *", placeholder="Nike Air Jordan 1 Retro High OG Chicago")
            brand      = st.text_input("Brand", placeholder="Nike")
            size       = st.text_input("Size *", placeholder="10")
            cost_basis = st.number_input("Cost Basis ($) *", min_value=0.0, step=0.01)
            condition  = st.selectbox("Condition", CONDITIONS)
        with ac2:
            colorway         = st.text_input("Colorway", placeholder="Chicago / White Black Red")
            listed_platform  = st.selectbox("Platform", PLATFORMS, index=0)
            listed_price     = st.number_input("Listed Price ($)", min_value=0.0, step=0.01)
            listed_date      = st.date_input("Date Listed", value=None)
            notes            = st.text_area("Notes", placeholder="OG box, lightly worn, bought from StockX", height=68)

        if st.form_submit_button("💾 Add to Inventory", type="primary"):
            if not shoe_name.strip() or not size.strip() or cost_basis <= 0:
                st.error("❌ Shoe name, size, and cost basis are required.")
            else:
                _create_item(user_id, shoe_name.strip(), brand.strip(), colorway.strip(),
                             size.strip(), cost_basis, condition,
                             listed_date, listed_price if listed_price > 0 else None,
                             listed_platform, notes.strip())
                st.success(f"✅ Added **{shoe_name}** (Sz {size}) to inventory!")
                st.rerun()

    st.markdown("---")

    if inventory:
        st.subheader("✏️ Edit / Mark Sold / Delete")
        item_map = {i["id"]: f"[{i['id']}] {i['shoe_name']} Sz {i['size']}" for i in inventory}
        sel_edit_id = st.selectbox("Select item:", list(item_map.keys()),
                                   format_func=lambda x: item_map[x], key="edit_sel")
        edit_item = next((i for i in inventory if i["id"] == sel_edit_id), None)

        if edit_item:
            ec1, ec2 = st.columns(2)
            with ec1:
                st.markdown("**✏️ Update Listing**")
                with st.form("edit_form"):
                    new_price = st.number_input("Listed Price ($)",
                                                 min_value=0.0, step=0.01,
                                                 value=float(edit_item["listed_price"] or 0))
                    new_plat  = st.selectbox("Platform", PLATFORMS,
                                              index=PLATFORMS.index(edit_item["listed_platform"])
                                              if edit_item["listed_platform"] in PLATFORMS else 0)
                    new_date  = st.date_input("Listed Date",
                                               value=datetime.strptime(edit_item["listed_date"][:10], "%Y-%m-%d").date()
                                               if edit_item["listed_date"] else None)
                    new_notes = st.text_input("Notes", value=edit_item["notes"])
                    if st.form_submit_button("💾 Save", type="primary"):
                        _update_listing(edit_item["id"], new_price if new_price > 0 else None,
                                        new_plat, new_date, new_notes)
                        st.success("✅ Updated!")
                        st.rerun()

            with ec2:
                st.markdown("**✅ Mark as Sold**")
                with st.form("sell_form"):
                    sell_price  = st.number_input("Sale Price ($)", min_value=0.0, step=0.01)
                    sell_plat   = st.selectbox("Sold on", PLATFORMS, key="sp")
                    sell_date   = st.date_input("Sale Date", value=date.today())
                    if sell_price > 0:
                        preview = _calc_profit(sell_price, edit_item["cost_basis"], sell_plat)
                        color = "green" if preview > 0 else "red"
                        st.markdown(f"**Est. profit:** <span style='color:{color}'>${preview:.2f}</span> after fees",
                                    unsafe_allow_html=True)
                    if st.form_submit_button("💸 Mark Sold", type="primary"):
                        if sell_price <= 0:
                            st.error("Enter a sale price")
                        else:
                            _mark_sold(edit_item["id"], sell_price, sell_plat, sell_date)
                            p = _calc_profit(sell_price, edit_item["cost_basis"], sell_plat)
                            st.success(f"🎉 Sold! Net profit: ${p:.2f}")
                            st.rerun()

            with st.expander("⚠️ Danger Zone"):
                if st.button(f"🗑️ Delete {edit_item['shoe_name']} Sz {edit_item['size']}", type="secondary"):
                    _delete_item(edit_item["id"])
                    st.success("Deleted.")
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5: P&L ANALYTICS
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("📈 P&L Analytics — Sold History")
    sold = _load_sold(user_id)

    if not sold:
        st.info("📊 No sold items yet. Mark items as sold in **➕ Add / Edit** to see analytics.")
    else:
        total_sold   = len(sold)
        total_rev    = sum(i["sell_price"] for i in sold)
        total_cogs   = sum(i["cost_basis"] for i in sold)
        total_profit = sum(i["net_profit"] for i in sold)
        avg_profit   = total_profit / total_sold if total_sold else 0

        s1, s2, s3, s4 = st.columns(4)
        with s1: st.metric("Pairs Sold", total_sold)
        with s2: st.metric("Total Revenue", f"${total_rev:,.0f}")
        with s3: st.metric("Total COGS", f"${total_cogs:,.0f}")
        with s4: st.metric("Net Profit", f"${total_profit:,.0f}",
                           delta=f"${avg_profit:.0f} avg/pair")

        # Platform breakdown
        plat_data = {}
        for item in sold:
            p = item["sold_platform"] or "Unknown"
            if p not in plat_data:
                plat_data[p] = {"revenue": 0, "cogs": 0, "profit": 0, "pairs": 0}
            plat_data[p]["revenue"] += item["sell_price"]
            plat_data[p]["cogs"]    += item["cost_basis"]
            plat_data[p]["profit"]  += item["net_profit"]
            plat_data[p]["pairs"]   += 1

        if plat_data:
            pf_df = pd.DataFrame([
                {"Platform": k, "Pairs": v["pairs"], "Revenue": v["revenue"],
                 "Net Profit": v["profit"], "Avg $/Pair": round(v["profit"] / v["pairs"], 2)}
                for k, v in plat_data.items()
            ]).sort_values("Net Profit", ascending=False)

            ch1, ch2 = st.columns(2)
            with ch1:
                fig1 = px.bar(pf_df, x="Platform", y="Net Profit",
                              title="Net Profit by Platform", color="Platform",
                              color_discrete_sequence=["#0064d2", "#ff0211", "#00a550", "#ff6b00"])
                fig1.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)
            with ch2:
                fig2 = px.bar(pf_df, x="Platform", y="Avg $/Pair",
                              title="Avg Profit Per Pair by Platform", color="Platform",
                              color_discrete_sequence=["#0064d2", "#ff0211", "#00a550", "#ff6b00"])
                fig2.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

        # Sold history table
        st.subheader("📋 Sold History")
        sold_df = pd.DataFrame([{
            "Shoe": i["shoe_name"], "Sz": i["size"],
            "Date": i["sold_date"], "Platform": i["sold_platform"],
            "Cost": f"${i['cost_basis']:.0f}",
            "Sold For": f"${i['sell_price']:.0f}",
            "Net Profit": f"${i['net_profit']:.0f}",
        } for i in sold])
        st.dataframe(sold_df, use_container_width=True, hide_index=True)

        # Schedule C box
        with st.expander("🧾 Schedule C Tax Summary (404 Sole Archive)"):
            st.markdown(f"""
| Item | Amount |
|------|--------|
| Total Gross Revenue | ${total_rev:,.2f} |
| Total COGS | ${total_cogs:,.2f} |
| Gross Profit | ${total_rev - total_cogs:,.2f} |
| Est. Platform Fees (12% avg) | ${total_rev * 0.12:,.2f} |
| **Net Profit (est.)** | **${total_profit:,.2f}** |

*Actual fees vary by platform. Keep individual platform reports for accurate Schedule C filing.*
""")
