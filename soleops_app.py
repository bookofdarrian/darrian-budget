"""
SoleOps — Standalone Streamlit Entry Point
Port: 8502 | Domain: soleops.io (or 404soleops.com)
Run: streamlit run soleops_app.py --server.port=8502 --server.address=0.0.0.0
"""

import streamlit as st
from utils.db import init_db, get_conn, execute as db_exec
from utils.auth import (
    require_login,
    inject_soleops_css,
    render_sidebar_brand,
    render_sidebar_user_widget,
    get_current_user,
)

st.set_page_config(
    page_title="SoleOps — Sneaker Reseller Platform",
    page_icon="👟",
    layout="wide",
)

init_db()
inject_soleops_css()
require_login()

# ── Sidebar ──────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("soleops_app.py",                          label="🏠 Dashboard",           icon="🏠")
st.sidebar.page_link("pages/65_sneaker_inventory_analyzer.py",  label="📦 Inventory Analyzer",  icon="📦")
st.sidebar.page_link("pages/68_soleops_price_monitor.py",       label="📈 Price Monitor",        icon="📈")
st.sidebar.page_link("pages/69_soleops_pnl_dashboard.py",       label="💰 P&L Dashboard",        icon="💰")
st.sidebar.page_link("pages/71_soleops_arb_scanner.py",         label="🔍 Arb Scanner",          icon="🔍")
st.sidebar.page_link("pages/72_resale_price_advisor.py",        label="🤖 AI Price Advisor",     icon="🤖")
st.sidebar.page_link("pages/84_soleops_stale_inventory.py",     label="⚠️ Stale Inventory",      icon="⚠️")
st.sidebar.page_link("pages/85_soleops_inventory_manager.py",   label="🗂️ Inventory Manager",    icon="🗂️")
st.sidebar.page_link("pages/86_soleops_listing_generator.py",   label="✍️ Listing Generator",    icon="✍️")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/70_soleops_stripe_paywall.py",      label="💳 Subscription",         icon="💳")
render_sidebar_user_widget()

# ── Main Dashboard ────────────────────────────────────────────────────────────
user = get_current_user()
uid = user.get("id", 0) if user else 0
username = user.get("username", "Reseller") if user else "Reseller"

st.title("👟 SoleOps")
st.markdown(f"Welcome back, **{username}** — your sneaker resale command center.")
st.markdown("---")

# ── Quick Stats (pulled from DB) ──────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

try:
    conn = get_conn()
    cursor = conn.cursor()

    # Active inventory count
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM sneaker_inventory WHERE user_id = ? AND status = 'active'",
            (uid,)
        )
        row = cursor.fetchone()
        inv_count = row[0] if row else 0
    except Exception:
        inv_count = None

    # Total net profit
    try:
        cursor.execute(
            "SELECT COALESCE(SUM(net_profit), 0) FROM sneaker_inventory WHERE user_id = ? AND status = 'sold'",
            (uid,)
        )
        row = cursor.fetchone()
        total_pnl = row[0] if row else 0
    except Exception:
        total_pnl = None

    # Stale pairs (>30 days unsold)
    try:
        cursor.execute(
            """SELECT COUNT(*) FROM sneaker_inventory
               WHERE user_id = ? AND status = 'active'
               AND date_listed IS NOT NULL
               AND julianday('now') - julianday(date_listed) > 30""",
            (uid,)
        )
        row = cursor.fetchone()
        stale_count = row[0] if row else 0
    except Exception:
        stale_count = None

    # Active price alerts
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_active = 1",
            (uid,)
        )
        row = cursor.fetchone()
        alerts_count = row[0] if row else 0
    except Exception:
        alerts_count = None

    conn.close()
except Exception:
    inv_count = total_pnl = stale_count = alerts_count = None

with col1:
    st.metric(
        "📦 Active Inventory",
        f"{inv_count}" if inv_count is not None else "—",
        help="Pairs currently listed or in hand"
    )
with col2:
    st.metric(
        "💰 Total Net Profit",
        f"${total_pnl:,.2f}" if total_pnl is not None else "—",
        help="Net profit across all sold pairs (fees deducted)"
    )
with col3:
    st.metric(
        "⚠️ Stale Pairs",
        f"{stale_count}" if stale_count is not None else "—",
        help="Pairs unsold for 30+ days — consider repricing",
        delta=f"-{stale_count} need action" if stale_count else None,
        delta_color="inverse" if stale_count else "off",
    )
with col4:
    st.metric(
        "🔔 Price Alerts",
        f"{alerts_count}" if alerts_count is not None else "—",
        help="Active eBay/Mercari price monitors"
    )

st.markdown("---")

# ── Feature Cards ─────────────────────────────────────────────────────────────
st.subheader("🚀 Your Tools")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 📈 Price Monitor")
    st.markdown("Real-time eBay + Mercari prices with Telegram alerts. Know exactly when to list and when to hold.")
    if st.button("Open Price Monitor →", key="btn_price"):
        st.switch_page("pages/68_soleops_price_monitor.py")

with c2:
    st.markdown("#### 💰 P&L Dashboard")
    st.markdown("Per-pair profit after fees. Platform breakdown. Monthly trends. Schedule C summary.")
    if st.button("Open P&L Dashboard →", key="btn_pnl"):
        st.switch_page("pages/69_soleops_pnl_dashboard.py")

with c3:
    st.markdown("#### ✍️ AI Listing Generator")
    st.markdown("Claude-powered eBay + Mercari titles and descriptions. Keyword-optimized, conversion-tested.")
    if st.button("Open Listing Generator →", key="btn_listing"):
        st.switch_page("pages/86_soleops_listing_generator.py")

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("#### 🔍 Arbitrage Scanner")
    st.markdown("Watchlist + buy thresholds. Alerts fire on Telegram the moment a target pair drops below buy price.")
    if st.button("Open Arb Scanner →", key="btn_arb"):
        st.switch_page("pages/71_soleops_arb_scanner.py")

with c5:
    st.markdown("#### ⚠️ Stale Inventory")
    st.markdown("Flag pairs sitting unsold. AI-generated markdown strategy per pair. Weekly digest email.")
    if st.button("Open Stale Inventory →", key="btn_stale"):
        st.switch_page("pages/84_soleops_stale_inventory.py")

with c6:
    st.markdown("#### 🤖 AI Price Advisor")
    st.markdown("Claude analyzes your pair vs current market comps and recommends the optimal list price.")
    if st.button("Open Price Advisor →", key="btn_advisor"):
        st.switch_page("pages/72_resale_price_advisor.py")

st.markdown("---")
st.caption("SoleOps — Built for serious sneaker resellers | Powered by Claude AI + Real-Time Market Data")
