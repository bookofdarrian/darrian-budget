import os
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import init_db, add_to_waitlist, get_waitlist_count, is_pro_user
from utils.auth import (
    require_login, inject_css, get_current_user,
    render_sidebar_brand, render_sidebar_user_widget,
    PEACH, PEACH_DARK, PEACH_GLOW, BG_CARD, BG_BORDER, TEXT_MUTED, TEXT_MAIN
)
from utils.stripe_utils import (
    create_checkout_session, create_billing_portal_session,
    STRIPE_ENABLED, is_sandbox_mode, stripe_enabled_for,
    poll_checkout_and_activate, get_latest_checkout_session_for_user,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(
    page_title="Pricing — Peach Savings",
    page_icon="🍑",
    layout="wide"
)
init_db()
inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()

months = []
for m in range(1, 13):
    months.append(datetime(2025, m, 1).strftime("%Y-%m"))
for m in range(1, 13):
    months.append(datetime(2026, m, 1).strftime("%Y-%m"))
current_month = datetime.now().strftime("%Y-%m")
default_idx = months.index(current_month) if current_month in months else 0
st.sidebar.selectbox("📅 Month", months, index=default_idx, key="pricing_month")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth",         icon="💎")
st.sidebar.page_link("pages/0_pricing.py",        label="Upgrade to Pro",    icon="⭐")

user = get_current_user()
if user:
    render_sidebar_user_widget()

# ── Handle checkout return ────────────────────────────────────────────────────
params = st.query_params
if params.get("checkout") == "success":
    _session_id = params.get("session_id", "")
    _user       = get_current_user() or {}
    _user_id    = _user.get("id", 0)
    _user_email = _user.get("email", "")

    # ── Polling: activate Pro immediately without a webhook server ────────────
    _activated = False
    if _session_id and _user_id and _user_email:
        _activated = poll_checkout_and_activate(_session_id, _user_id, _user_email)

    # Fallback: if session_id was missing, try to find the latest paid session
    if not _activated and _user_id and _user_email:
        _fallback_sid = get_latest_checkout_session_for_user(_user_email, _user_id)
        if _fallback_sid:
            _activated = poll_checkout_and_activate(_fallback_sid, _user_id, _user_email)

    # Refresh session state so the Pro badge and buttons update immediately
    if _activated and _user_id:
        from utils.db import get_user_by_id
        _fresh = get_user_by_id(_user_id)
        if _fresh:
            _fresh.pop("password_hash", None)
            _fresh.pop("salt", None)
            st.session_state["user"] = _fresh
            user = _fresh  # update local var so pricing cards render correctly

    st.balloons()
    if _activated:
        st.success("🎉 Welcome to Peach Savings Pro! Your subscription is now active.")
    else:
        st.success("🎉 Payment received! Your Pro plan will activate within a minute.")
        st.caption("If Pro features aren't visible yet, refresh the page in a moment.")
    st.query_params.clear()

elif params.get("checkout") == "cancelled":
    st.info("Checkout cancelled — no charge was made. You can upgrade anytime.")
    st.query_params.clear()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center; padding: 48px 0 36px 0;">
    <div style="font-size:0.85rem; color:{PEACH}; font-weight:600; letter-spacing:0.1em;
                text-transform:uppercase; margin-bottom:12px;">
        Simple, transparent pricing
    </div>
    <h1 style="font-size:2.8rem; font-weight:800; color:{TEXT_MAIN}; margin:0; line-height:1.1;">
        Start free.<br>Upgrade when you're ready.
    </h1>
    <p style="color:{TEXT_MUTED}; font-size:1.05rem; margin-top:16px;
              max-width:520px; margin-left:auto; margin-right:auto;">
        Peach Savings gives you a real-time view of your money — budgets, bank imports,
        AI insights, and net worth tracking. All in one place.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Pricing cards ─────────────────────────────────────────────────────────────
col_free, col_pro = st.columns(2, gap="large")

with col_free:
    st.markdown(f"""
    <div class="price-card">
        <div style="font-size:1.1rem; font-weight:700; color:{TEXT_MAIN}; margin-bottom:6px;">Free</div>
        <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:4px;">
            <span class="price-amount">$0</span>
        </div>
        <div class="price-period">Forever free · No credit card needed</div>
        <ul class="feature-list" style="margin-top:20px;">
            <li>Monthly budget tracking</li>
            <li>Expense &amp; income management</li>
            <li>Bank statement import (PDF)</li>
            <li>Financial goals</li>
            <li>Receipts &amp; HSA tracker</li>
            <li class="locked">AI Insights (Claude)</li>
            <li class="locked">Monthly Trends AI analysis</li>
            <li class="locked">Net Worth tracker</li>
            <li class="locked">Investment portfolio tracking</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if not user:
        if st.button("Get Started Free", use_container_width=True, key="free_cta"):
            st.switch_page("app.py")
    elif is_pro_user(user):
        st.button("Not your current plan", disabled=True, use_container_width=True)
    else:
        st.button("✓ Your Current Plan", disabled=True, use_container_width=True)

with col_pro:
    st.markdown(f"""
    <div class="price-card featured">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="font-size:1.1rem; font-weight:700; color:{TEXT_MAIN};">Pro</span>
            <span style="background:{PEACH}; color:#000; font-size:0.65rem; font-weight:700;
                         padding:2px 8px; border-radius:20px; letter-spacing:0.05em;">MOST POPULAR</span>
        </div>
        <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:4px;">
            <span class="price-amount">$7</span>
            <span class="price-period">/month</span>
        </div>
        <div class="price-period">Cancel anytime · Billed monthly</div>
        <ul class="feature-list" style="margin-top:20px;">
            <li>Everything in Free</li>
            <li>🤖 Claude AI monthly summaries</li>
            <li>🤖 Personalized budget recommendations</li>
            <li>🤖 Auto-categorize bank transactions</li>
            <li>🤖 Ask Claude anything about your money</li>
            <li>📈 Monthly Trends AI analysis</li>
            <li>💎 Net Worth tracker &amp; history</li>
            <li>📊 Investment portfolio tracking</li>
            <li>🎯 Savings projections</li>
            <li>⚡ Priority support</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if user and is_pro_user(user):
        st.success("✅ You're on Pro!")
        user_email = user.get("email", "")
        stripe_cid = user.get("stripe_customer_id", "")
        if stripe_cid and STRIPE_ENABLED:
            if st.button("Manage Subscription", use_container_width=True, key="manage_sub"):
                portal_url = create_billing_portal_session(stripe_cid, user_email)
                if portal_url:
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url={portal_url}">',
                        unsafe_allow_html=True
                    )
                    st.markdown(f"[Open billing portal]({portal_url})")
    elif user:
        user_email = user.get("email", "")
        sandbox = is_sandbox_mode(user_email)
        if sandbox:
            st.markdown(
                "<div style='background:#1a2a1a; border:1px solid #3a6b3a; border-radius:8px; "
                "padding:8px 12px; margin-bottom:10px; font-size:0.78rem; color:#7ec87e;'>"
                "🧪 <strong>Sandbox mode</strong> — Stripe test keys active. "
                "Use card <code>4242 4242 4242 4242</code>, any future date &amp; CVC.</div>",
                unsafe_allow_html=True
            )
        btn_label = "🧪 Test Checkout — $7/month" if sandbox else "🚀 Upgrade to Pro — $7/month"
        if st.button(btn_label, type="primary", use_container_width=True, key="pro_cta"):
            if stripe_enabled_for(user_email):
                url = create_checkout_session(user_email, user.get("id", 0))
                if url:
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url={url}">',
                        unsafe_allow_html=True
                    )
                    st.markdown(f"[Click here if not redirected]({url})")
                else:
                    st.error("Could not start checkout. Please try again.")
            else:
                if sandbox:
                    st.warning(
                        "⚙️ Test keys not configured. Add `STRIPE_TEST_SECRET_KEY` and "
                        "`STRIPE_TEST_PRICE_ID` to your Railway environment variables."
                    )
                else:
                    st.warning(
                        "⚙️ Stripe not configured yet. Add `STRIPE_SECRET_KEY` and "
                        "`STRIPE_PRICE_ID` to your Railway environment variables."
                    )
        footer = "🧪 Test mode — no real charge" if sandbox else "Secure payment via Stripe · Cancel anytime"
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.78rem; margin-top:6px;'>"
            f"{footer}</div>",
            unsafe_allow_html=True
        )
    else:
        if st.button("🚀 Get Pro — $7/month", type="primary",
                     use_container_width=True, key="pro_cta_anon"):
            st.switch_page("app.py")
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.78rem; margin-top:6px;'>"
            "Create a free account first, then upgrade</div>",
            unsafe_allow_html=True
        )

st.markdown("---")

# ── Feature comparison ────────────────────────────────────────────────────────
st.markdown("### What's included")
features = [
    ("Monthly budget tracking",              "✅", "✅"),
    ("Expense management",                   "✅", "✅"),
    ("Income tracking",                      "✅", "✅"),
    ("Bank PDF import (NFCU)",               "✅", "✅"),
    ("Financial goals",                      "✅", "✅"),
    ("Receipts & HSA tracker",               "✅", "✅"),
    ("Business Income Tracker (resale/side hustle)", "—", "✅"),
    ("AI Monthly Summary (Claude)",          "—",  "✅"),
    ("AI Budget Recommendations",            "—",  "✅"),
    ("AI Auto-Categorize Transactions",      "—",  "✅"),
    ("Ask Claude Anything",                  "—",  "✅"),
    ("Monthly Trends AI Analysis",           "—",  "✅"),
    ("Net Worth Tracker",                    "—",  "✅"),
    ("Investment Portfolio Tracking",        "—",  "✅"),
    ("Savings Projections",                  "—",  "✅"),
]
feat_df = pd.DataFrame(features, columns=["Feature", "Free", "Pro"])
st.dataframe(feat_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ── FAQ ───────────────────────────────────────────────────────────────────────
st.markdown("### Frequently Asked Questions")

with st.expander("Can I cancel anytime?"):
    st.write(
        "Yes. Cancel from your billing portal at any time. "
        "You keep Pro access until the end of your billing period."
    )
with st.expander("Is my financial data secure?"):
    st.write(
        "Your data is stored in a private PostgreSQL database. "
        "We never sell or share your data. Bank PDFs are parsed locally "
        "and the raw file is not stored."
    )
with st.expander("What bank does the import support?"):
    st.write(
        "Currently Navy Federal Credit Union (NFCU) PDF statements. "
        "More banks coming soon."
    )
with st.expander("Do I need my own Anthropic API key?"):
    st.write(
        "For the beta period, yes — you'll need a free Anthropic API key. "
        "We're working on bundling API costs into the Pro plan."
    )
with st.expander("What if Stripe isn't set up yet?"):
    st.write(
        "During the beta, join the waitlist below and get early access. "
        "We'll notify you when payments go live."
    )

st.markdown("---")

# ── Waitlist ──────────────────────────────────────────────────────────────────
st.markdown("### 📬 Join the Early Access List")
st.caption("Get notified when new features drop and lock in the beta price.")

wl_col1, wl_col2 = st.columns([3, 1])
with wl_col1:
    wl_email = st.text_input(
        "Email", placeholder="you@email.com", key="wl_email",
        label_visibility="collapsed"
    )
    wl_name = st.text_input(
        "Name (optional)", placeholder="First name", key="wl_name",
        label_visibility="collapsed"
    )
with wl_col2:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("Join Waitlist", type="primary", use_container_width=True, key="btn_waitlist"):
        if not wl_email or "@" not in wl_email:
            st.error("Please enter a valid email.")
        else:
            success = add_to_waitlist(wl_email, wl_name, source="pricing_page")
            if success:
                st.success("✅ You're on the list! We'll be in touch.")
            else:
                st.info("You're already on the list — we'll reach out soon!")

try:
    count = get_waitlist_count()
    if count > 0:
        st.caption(f"🔥 {count} people already on the waitlist")
except Exception:
    pass
