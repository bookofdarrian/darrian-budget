"""
SoleOps — Standalone Streamlit Entry Point
Port: 8502 | Domain: getsoleops.com (backup: soleops.net)
Run: streamlit run soleops_app.py --server.port=8502 --server.address=0.0.0.0

Public landing page shown to unauthenticated visitors (Googlebot-indexable).
Authenticated users see the full dashboard with live inventory metrics.
"""

import streamlit as st
from utils.db import init_db, get_conn
from utils.auth import (
    inject_soleops_css,
    render_sidebar_brand,
    render_sidebar_user_widget,
    get_current_user,
)

st.set_page_config(
    page_title="SoleOps — Sneaker Reseller Operations Platform",
    page_icon="👟",
    layout="wide",
)

init_db()
inject_soleops_css()

user = get_current_user()

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC LANDING PAGE — shown to unauthenticated visitors + Googlebot
# ═══════════════════════════════════════════════════════════════════════════════
if not user:

    # Hide sidebar for the public landing page
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    .block-container { padding-top: 2rem; max-width: 980px; margin: 0 auto; }

    .so-hero {
        background: linear-gradient(135deg, #0A0A0F 0%, #0D0D1A 50%, #12082A 100%);
        border-radius: 16px;
        padding: 4rem 3rem;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #1A1A3A;
        position: relative;
        overflow: hidden;
    }
    .so-hero::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at center, rgba(0,212,255,0.05) 0%, transparent 60%);
        pointer-events: none;
    }
    .so-hero h1 {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00D4FF, #7B2FBE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
        line-height: 1.2;
    }
    .so-hero p {
        font-size: 1.2rem;
        color: #8A8AAA;
        max-width: 620px;
        margin: 0 auto 2rem;
        line-height: 1.6;
    }
    .so-badge {
        display: inline-block;
        background: rgba(0,212,255,0.1);
        border: 1px solid #00D4FF;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.85rem;
        color: #00D4FF;
        margin-bottom: 1.5rem;
        letter-spacing: 0.5px;
    }

    .so-feature-card {
        background: #0D0D1A;
        border: 1px solid #1A1A3A;
        border-radius: 12px;
        padding: 1.5rem;
        height: 100%;
        transition: border-color 0.2s;
    }
    .so-feature-card:hover { border-color: #00D4FF; }
    .so-feature-card h3 { color: #FFFFFF; font-size: 1.05rem; margin-bottom: 0.5rem; }
    .so-feature-card p { color: #6A6A8A; font-size: 0.92rem; line-height: 1.5; margin: 0; }
    .so-feature-card .tag {
        display: inline-block;
        background: rgba(123,47,190,0.2);
        color: #B06AFF;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.75rem;
        margin-bottom: 0.5rem;
    }

    .so-stat-row {
        background: #0D0D1A;
        border: 1px solid #1A1A3A;
        border-radius: 12px;
        padding: 1.5rem 1rem;
        text-align: center;
    }
    .so-stat-num {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00D4FF, #7B2FBE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .so-stat-label { font-size: 0.85rem; color: #6A6A8A; }

    .pricing-card {
        background: #0D0D1A;
        border: 1px solid #1A1A3A;
        border-radius: 12px;
        padding: 1.75rem;
        text-align: center;
    }
    .pricing-card.popular {
        border-color: #00D4FF;
        box-shadow: 0 0 20px rgba(0,212,255,0.1);
    }
    .pricing-card h3 { color: #FFFFFF; font-size: 1.1rem; margin-bottom: 0.25rem; }
    .pricing-card .price { font-size: 2rem; font-weight: 800; color: #00D4FF; }
    .pricing-card .price-sub { font-size: 0.85rem; color: #6A6A8A; margin-bottom: 1rem; }
    .pricing-card ul { list-style: none; padding: 0; margin: 0; text-align: left; }
    .pricing-card ul li { color: #8A8AAA; font-size: 0.9rem; padding: 4px 0; }
    .pricing-card ul li::before { content: "✓ "; color: #00D4FF; }

    .so-footer {
        text-align: center;
        padding: 2rem 0 1rem;
        color: #3A3A5A;
        font-size: 0.85rem;
        border-top: 1px solid #1A1A3A;
        margin-top: 3rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="so-hero">
        <div class="so-badge">👟 Built by a reseller, for resellers</div>
        <h1>Stop Leaving Money<br>on the Table.</h1>
        <p>SoleOps is the all-in-one operations platform for serious sneaker resellers.
        Real-time price alerts, AI-generated listings, P&amp;L tracking, and arbitrage
        scanning — all in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    cta1, cta2, cta3 = st.columns([2, 1, 2])
    with cta2:
        if st.button("👟 Start Free Trial", type="primary", use_container_width=True):
            st.switch_page("app.py")
    st.markdown("<div style='text-align:center; color:#3A3A5A; font-size:0.85rem; margin-top:-0.5rem;'>No credit card required · Free tier always available</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Stats ─────────────────────────────────────────────────────────────────
    st.subheader("The numbers that matter to resellers")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown('<div class="so-stat-row"><div class="so-stat-num">$0</div><div class="so-stat-label">to start</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown('<div class="so-stat-row"><div class="so-stat-num">Real-Time</div><div class="so-stat-label">eBay + Mercari prices</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown('<div class="so-stat-row"><div class="so-stat-num">AI</div><div class="so-stat-label">listing generation</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown('<div class="so-stat-row"><div class="so-stat-num">8</div><div class="so-stat-label">reseller tools</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Features ──────────────────────────────────────────────────────────────
    st.subheader("Every tool you need to run a tighter resale operation")

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""
        <div class="so-feature-card">
            <div class="tag">⚡ Real-Time</div>
            <h3>📈 Price Monitor</h3>
            <p>Live eBay and Mercari prices for every SKU in your inventory.
            Telegram alerts fire the moment a comp drops below your target sell price.</p>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="so-feature-card">
            <div class="tag">🤖 AI-Powered</div>
            <h3>✍️ AI Listing Generator</h3>
            <p>Claude AI writes keyword-optimized eBay titles and Mercari descriptions in seconds.
            Better copy = more views = faster sales.</p>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="so-feature-card">
            <div class="tag">📊 Analytics</div>
            <h3>💰 P&amp;L Dashboard</h3>
            <p>Per-pair profit after platform fees (eBay 13.25%, Mercari 10%).
            Monthly trends, best/worst performers, Schedule C tax summary.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    f4, f5, f6 = st.columns(3)
    with f4:
        st.markdown("""
        <div class="so-feature-card">
            <div class="tag">🔍 Scanner</div>
            <h3>🔍 Arbitrage Scanner</h3>
            <p>Set a watchlist with max buy prices. SoleOps scans Mercari and sends
            a Telegram alert the moment a target pair appears below your threshold.</p>
        </div>
        """, unsafe_allow_html=True)
    with f5:
        st.markdown("""
        <div class="so-feature-card">
            <div class="tag">⚠️ Alerts</div>
            <h3>⚠️ Stale Inventory Tracker</h3>
            <p>Flag pairs sitting unsold past 30/60/90 days. AI recommends exact
            price drops and cross-listing strategy. Stop holding dead inventory.</p>
        </div>
        """, unsafe_allow_html=True)
    with f6:
        st.markdown("""
        <div class="so-feature-card">
            <div class="tag">📦 Inventory</div>
            <h3>📦 Inventory Manager</h3>
            <p>Full CRUD inventory with SKU, size, COGS, condition, date purchased,
            and platform listed. Everything you need for tax time and profit tracking.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Pricing ───────────────────────────────────────────────────────────────
    st.subheader("Simple pricing. Cancel anytime.")

    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown("""
        <div class="pricing-card">
            <h3>Free</h3>
            <div class="price">$0</div>
            <div class="price-sub">forever</div>
            <ul>
                <li>5 inventory items</li>
                <li>Manual price lookup</li>
                <li>Basic P&L view</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with p2:
        st.markdown("""
        <div class="pricing-card">
            <h3>Starter</h3>
            <div class="price">$9.99</div>
            <div class="price-sub">per month</div>
            <ul>
                <li>50 inventory items</li>
                <li>Telegram alerts</li>
                <li>AI listing generator</li>
                <li>Full P&L dashboard</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with p3:
        st.markdown("""
        <div class="pricing-card popular">
            <h3>⭐ Pro</h3>
            <div class="price">$19.99</div>
            <div class="price-sub">per month</div>
            <ul>
                <li>Unlimited inventory</li>
                <li>Arb scanner</li>
                <li>Stale inventory AI</li>
                <li>Price advisor</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with p4:
        st.markdown("""
        <div class="pricing-card">
            <h3>Pro+</h3>
            <div class="price">$29.99</div>
            <div class="price-sub">per month</div>
            <ul>
                <li>Everything in Pro</li>
                <li>Direct API listing</li>
                <li>Multi-user access</li>
                <li>Priority support</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Final CTA ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="so-hero" style="padding: 3rem 2rem;">
        <h1 style="font-size:2rem;">Ready to run a tighter operation?</h1>
        <p>Start free. No credit card. Cancel anytime. Your 404 Sole Archive data stays yours.</p>
    </div>
    """, unsafe_allow_html=True)

    cta4, cta5, cta6 = st.columns([2, 1, 2])
    with cta5:
        if st.button("👟 Start Free Now", type="primary", use_container_width=True, key="cta_bottom"):
            st.switch_page("app.py")

    st.markdown("""
    <div class="so-footer">
        <strong>SoleOps</strong> · Sneaker Reseller Operations Platform<br>
        Built by resellers, for resellers · Real data from real inventory
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATED DASHBOARD — shown to logged-in users
# ═══════════════════════════════════════════════════════════════════════════════
uid = user.get("id", 0)
username = user.get("username", "Reseller")

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

st.title("👟 SoleOps")
st.markdown(f"Welcome back, **{username}** — your sneaker resale command center.")
st.markdown("---")

# ── Quick Stats ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

inv_count = total_pnl = stale_count = alerts_count = None
try:
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM sneaker_inventory WHERE user_id = ? AND status = 'active'", (uid,))
        row = cursor.fetchone()
        inv_count = row[0] if row else 0
    except Exception:
        pass
    try:
        cursor.execute("SELECT COALESCE(SUM(net_profit), 0) FROM sneaker_inventory WHERE user_id = ? AND status = 'sold'", (uid,))
        row = cursor.fetchone()
        total_pnl = row[0] if row else 0
    except Exception:
        pass
    try:
        cursor.execute("""SELECT COUNT(*) FROM sneaker_inventory WHERE user_id = ? AND status = 'active'
               AND date_listed IS NOT NULL AND julianday('now') - julianday(date_listed) > 30""", (uid,))
        row = cursor.fetchone()
        stale_count = row[0] if row else 0
    except Exception:
        pass
    try:
        cursor.execute("SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_active = 1", (uid,))
        row = cursor.fetchone()
        alerts_count = row[0] if row else 0
    except Exception:
        pass
    conn.close()
except Exception:
    pass

with col1:
    st.metric("📦 Active Inventory", f"{inv_count}" if inv_count is not None else "—", help="Pairs currently listed or in hand")
with col2:
    st.metric("💰 Total Net Profit", f"${total_pnl:,.2f}" if total_pnl is not None else "—", help="Net profit across all sold pairs")
with col3:
    st.metric("⚠️ Stale Pairs", f"{stale_count}" if stale_count is not None else "—",
              delta=f"-{stale_count} need action" if stale_count else None,
              delta_color="inverse" if stale_count else "off",
              help="Pairs unsold 30+ days")
with col4:
    st.metric("🔔 Price Alerts", f"{alerts_count}" if alerts_count is not None else "—", help="Active eBay/Mercari monitors")

st.markdown("---")
st.subheader("🚀 Your Tools")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 📈 Price Monitor")
    st.markdown("Real-time eBay + Mercari prices with Telegram alerts.")
    if st.button("Open Price Monitor →", key="btn_price"):
        st.switch_page("pages/68_soleops_price_monitor.py")
with c2:
    st.markdown("#### 💰 P&L Dashboard")
    st.markdown("Per-pair profit after fees. Monthly trends. Schedule C.")
    if st.button("Open P&L Dashboard →", key="btn_pnl"):
        st.switch_page("pages/69_soleops_pnl_dashboard.py")
with c3:
    st.markdown("#### ✍️ AI Listing Generator")
    st.markdown("Claude-powered eBay + Mercari titles and descriptions.")
    if st.button("Open Listing Generator →", key="btn_listing"):
        st.switch_page("pages/86_soleops_listing_generator.py")

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("#### 🔍 Arbitrage Scanner")
    st.markdown("Watchlist + Telegram alert when target pairs go below buy price.")
    if st.button("Open Arb Scanner →", key="btn_arb"):
        st.switch_page("pages/71_soleops_arb_scanner.py")
with c5:
    st.markdown("#### ⚠️ Stale Inventory")
    st.markdown("Flag aging pairs. AI markdown strategy per pair.")
    if st.button("Open Stale Inventory →", key="btn_stale"):
        st.switch_page("pages/84_soleops_stale_inventory.py")
with c6:
    st.markdown("#### 🤖 AI Price Advisor")
    st.markdown("Claude recommends optimal list price vs current comps.")
    if st.button("Open Price Advisor →", key="btn_advisor"):
        st.switch_page("pages/72_resale_price_advisor.py")

st.markdown("---")
st.caption("SoleOps — Built for serious sneaker resellers | Powered by Claude AI + Real-Time Market Data")
