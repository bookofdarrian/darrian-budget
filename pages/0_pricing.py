"""
Peach State Savings — Three-Tier Pricing Page
Tiers:
  Free     "Panther Papers"  — always free, 18+, basic tools + cultural content
  Pro      $4.99/mo          — full AI-powered platform, Stripe checkout
  Sovereign 🔱               — invite-only, 25+, hand-selected by Darrian

Public build stats section shows proof-of-work (code stats only, no financials).
Sovereign admin panel visible only to owner email for granting/revoking access.
"""

import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import (
    init_db, add_to_waitlist, get_waitlist_count, is_pro_user,
    get_setting, set_setting, get_conn
)
from utils.auth import (
    require_login, inject_css, get_current_user,
    render_sidebar_brand, render_sidebar_user_widget,
    is_sovereign_user, current_user_is_sovereign,
    SOVEREIGN_OWNER_EMAIL,
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

# ── Sovereign tier colors ───────────────────────────────────────────────────
SOVEREIGN_GOLD   = "#FFD700"
SOVEREIGN_DARK   = "#B8860B"
SOVEREIGN_GLOW   = "#1a1400"
SOVEREIGN_BORDER = "#8B6914"

st.set_page_config(
    page_title="Pricing — Peach Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto"
)
init_db()
inject_css()

# ── Sovereign DB tables ──────────────────────────────────────────────────────
def _ensure_sovereign_tables():
    """Create sovereign_applications table if it doesn't exist."""
    try:
        conn = get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sovereign_applications (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT NOT NULL,
                name        TEXT,
                why_worthy  TEXT,
                age_confirm INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT DEFAULT (datetime('now')),
                reviewed_at TEXT,
                reviewed_by TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

_ensure_sovereign_tables()

# ── Build stats (public proof-of-work, no financials) ─────────────────────
BUILD_STATS = {
    "commits":   688,
    "pages":     154,
    "loc":       92519,
    "files":     522,
    "branches":  274,
    "since":     "2024",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",            label="Overview",      icon="📊")
st.sidebar.page_link("pages/22_todo.py",  label="Todo",          icon="✅")
st.sidebar.page_link("pages/0_pricing.py",label="Pricing",       icon="⭐")
render_sidebar_user_widget()

# ── Handle Stripe checkout return ────────────────────────────────────────────
params = st.query_params
if params.get("checkout") == "success":
    _session_id = params.get("session_id", "")
    _user       = get_current_user() or {}
    _user_id    = _user.get("id", 0)
    _user_email = _user.get("email", "")
    _activated  = False
    if _session_id and _user_id and _user_email:
        _activated = poll_checkout_and_activate(_session_id, _user_id, _user_email)
    if not _activated and _user_id and _user_email:
        _fallback_sid = get_latest_checkout_session_for_user(_user_email, _user_id)
        if _fallback_sid:
            _activated = poll_checkout_and_activate(_fallback_sid, _user_id, _user_email)
    if _activated and _user_id:
        from utils.db import get_user_by_id
        _fresh = get_user_by_id(_user_id)
        if _fresh:
            _fresh.pop("password_hash", None)
            _fresh.pop("salt", None)
            st.session_state["user"] = _fresh
    st.balloons()
    st.success("🎉 Welcome to Pro! Your subscription is now active." if _activated
               else "🎉 Payment received! Pro activates within a minute.")
    st.query_params.clear()
elif params.get("checkout") == "cancelled":
    st.info("Checkout cancelled — no charge was made.")
    st.query_params.clear()

user       = get_current_user()
is_pro     = is_pro_user(user) if user else False
is_sov     = is_sovereign_user(user) if user else False
is_owner   = (user or {}).get("email", "").lower() == SOVEREIGN_OWNER_EMAIL.lower()

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center; padding: 48px 0 36px 0;">
    <div style="font-size:0.85rem; color:{PEACH}; font-weight:600; letter-spacing:0.1em;
                text-transform:uppercase; margin-bottom:12px;">
        Three tiers. One mission.
    </div>
    <h1 style="font-size:2.8rem; font-weight:800; color:{TEXT_MAIN}; margin:0; line-height:1.1;">
        Build wealth.<br>On your own terms.
    </h1>
    <p style="color:{TEXT_MUTED}; font-size:1.05rem; margin-top:16px;
              max-width:560px; margin-left:auto; margin-right:auto;">
        Peach State Savings is AI-powered personal finance built for real people —
        budgets, bank imports, SoleOps reseller tools, and a tier so exclusive
        you have to be chosen for it.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Tier cards ───────────────────────────────────────────────────────────────
col_free, col_pro, col_sov = st.columns(3, gap="large")

# ── FREE — Panther Papers ────────────────────────────────────────────────────
with col_free:
    st.markdown(f"""
    <div class="price-card">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="font-size:1.1rem; font-weight:700; color:{TEXT_MAIN};">🐾 Panther Papers</span>
        </div>
        <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:4px;">
            <span class="price-amount">$0</span>
        </div>
        <div class="price-period">Forever free · No card needed</div>
        <ul class="feature-list" style="margin-top:20px;">
            <li>Monthly budget tracking</li>
            <li>Expense &amp; income management</li>
            <li>Bank statement import</li>
            <li>Financial goals</li>
            <li>Receipts &amp; HSA tracker</li>
            <li>Bill calendar</li>
            <li>Paycheck calculator</li>
            <li class="locked">AI Insights (Claude)</li>
            <li class="locked">Net Worth tracker</li>
            <li class="locked">Investment portfolio</li>
            <li class="locked">SoleOps full suite</li>
        </ul>
        <div style="margin-top:16px; padding:10px 12px;
                    background:rgba(0,78,137,0.15); border:1px solid #004E89;
                    border-radius:8px; font-size:0.78rem; color:#7ab3d4;">
            🐆 Named for the Panthers who laid the foundation.
            Free knowledge, free tools, forever.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if not user:
        if st.button("Get Started Free", use_container_width=True, key="free_cta"):
            st.switch_page("app.py")
    elif is_sov or is_pro:
        st.button("Not your current plan", disabled=True, use_container_width=True)
    else:
        st.button("✓ Your Current Plan", disabled=True, use_container_width=True)

# ── PRO — $4.99/mo ───────────────────────────────────────────────────────────
with col_pro:
    st.markdown(f"""
    <div class="price-card featured">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="font-size:1.1rem; font-weight:700; color:{TEXT_MAIN};">⭐ Pro</span>
            <span style="background:{PEACH}; color:#000; font-size:0.65rem; font-weight:700;
                         padding:2px 8px; border-radius:20px; letter-spacing:0.05em;">MOST POPULAR</span>
        </div>
        <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:4px;">
            <span class="price-amount">$4.99</span>
            <span class="price-period">/month</span>
        </div>
        <div class="price-period">Cancel anytime · Billed monthly</div>
        <ul class="feature-list" style="margin-top:20px;">
            <li>Everything in Panther Papers</li>
            <li>🤖 Claude AI monthly summaries</li>
            <li>🤖 Personalized budget recommendations</li>
            <li>🤖 Auto-categorize transactions</li>
            <li>🤖 Ask Claude anything about money</li>
            <li>📈 Monthly Trends AI analysis</li>
            <li>💎 Net Worth tracker &amp; history</li>
            <li>📊 Investment portfolio tracking</li>
            <li>🛒 SoleOps full reseller suite</li>
            <li>🎯 Savings projections</li>
            <li>⚡ Priority support</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if user and is_sov:
        st.info("🔱 Sovereign includes everything in Pro and more.")
    elif user and is_pro:
        st.success("✅ You're on Pro!")
        user_email  = user.get("email", "")
        stripe_cid  = user.get("stripe_customer_id", "")
        if stripe_cid and STRIPE_ENABLED:
            if st.button("Manage Subscription", use_container_width=True, key="manage_sub"):
                portal_url = create_billing_portal_session(stripe_cid, user_email)
                if portal_url:
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={portal_url}">', unsafe_allow_html=True)
                    st.markdown(f"[Open billing portal]({portal_url})")
    elif user:
        user_email = user.get("email", "")
        sandbox    = is_sandbox_mode(user_email)
        if sandbox:
            st.markdown(
                "<div style='background:#1a2a1a; border:1px solid #3a6b3a; border-radius:8px; "
                "padding:8px 12px; margin-bottom:10px; font-size:0.78rem; color:#7ec87e;'>"
                "🧪 <strong>Sandbox</strong> — Use card <code>4242 4242 4242 4242</code></div>",
                unsafe_allow_html=True
            )
        btn_label = "🧪 Test Checkout — $4.99/mo" if sandbox else "🚀 Upgrade to Pro — $4.99/mo"
        if st.button(btn_label, type="primary", use_container_width=True, key="pro_cta"):
            if stripe_enabled_for(user_email):
                url = create_checkout_session(user_email, user.get("id", 0))
                if url:
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
                    st.markdown(f"[Click here if not redirected]({url})")
                else:
                    st.error("Could not start checkout. Try again.")
            else:
                st.warning("⚙️ Stripe not configured on this server yet.")
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.78rem; margin-top:6px;'>"
            f"{'🧪 Test mode' if sandbox else 'Secure via Stripe · Cancel anytime'}</div>",
            unsafe_allow_html=True
        )
    else:
        if st.button("🚀 Get Pro — $4.99/mo", type="primary", use_container_width=True, key="pro_cta_anon"):
            st.switch_page("app.py")
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.78rem; margin-top:6px;'>"
            "Create a free account first, then upgrade</div>", unsafe_allow_html=True
        )

# ── SOVEREIGN — Invite Only ───────────────────────────────────────────────────
with col_sov:
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, {SOVEREIGN_GLOW} 0%, #0d0d00 100%);
                border:1px solid {SOVEREIGN_GOLD}; border-radius:14px;
                padding:28px; height:100%;
                box-shadow: 0 0 40px rgba(255,215,0,0.08);">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="font-size:1.1rem; font-weight:700; color:{SOVEREIGN_GOLD};">🔱 Sovereign</span>
            <span style="background:{SOVEREIGN_GOLD}; color:#000; font-size:0.65rem; font-weight:700;
                         padding:2px 8px; border-radius:20px; letter-spacing:0.05em;">INVITE ONLY</span>
        </div>
        <div style="display:flex; align-items:baseline; gap:4px; margin-bottom:4px;">
            <span style="font-size:2.5rem; font-weight:800; color:{SOVEREIGN_GOLD}; line-height:1;">Earned</span>
        </div>
        <div style="color:{SOVEREIGN_DARK}; font-size:0.85rem; margin-bottom:4px;">
            Not bought. Not applied for. Chosen.
        </div>
        <ul class="feature-list" style="margin-top:20px;">
            <li style="color:#e8d060;">Everything in Pro</li>
            <li style="color:#e8d060;">Direct line to Darrian</li>
            <li style="color:#e8d060;">Custom AI agents built for you</li>
            <li style="color:#e8d060;">Early access to every feature</li>
            <li style="color:#e8d060;">Private community access</li>
            <li style="color:#e8d060;">SoleOps white-glove onboarding</li>
            <li style="color:#e8d060;">Exclusive Panther content drops</li>
            <li style="color:#e8d060;">25+ only · Ubuntu values required</li>
            <li style="color:#e8d060;">Your feedback shapes the roadmap</li>
        </ul>
        <div style="margin-top:16px; padding:10px 12px;
                    background:rgba(255,215,0,0.06); border:1px solid {SOVEREIGN_BORDER};
                    border-radius:8px; font-size:0.78rem; color:{SOVEREIGN_GOLD};">
            🌍 <em>"I am because we are."</em> — Ubuntu<br>
            <span style="color:{TEXT_MUTED}; font-size:0.73rem;">
            Gullah Geechi · Panther · Sikh · VA · NC A&T built
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if user and is_sov:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{SOVEREIGN_GLOW},{BG_CARD}); "
            f"border:1px solid {SOVEREIGN_GOLD}; border-radius:10px; padding:14px; "
            f"text-align:center; color:{SOVEREIGN_GOLD}; font-weight:700;'>"
            "🔱 You are Sovereign.</div>",
            unsafe_allow_html=True
        )
    elif user and is_pro:
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.82rem; "
            f"padding:10px;'>You're on Pro — Sovereign is by invitation only.<br>"
            f"<span style='color:{SOVEREIGN_GOLD};'>Keep building. Darrian's watching.</span></div>",
            unsafe_allow_html=True
        )
    elif user:
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.82rem; padding:10px;'>"
            f"Sovereign access is granted by Darrian personally.<br>"
            f"<span style='color:{SOVEREIGN_GOLD};'>You can't buy your way in.</span></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.82rem; padding:10px;'>"
            "Create an account first. Then show what you're about.</div>",
            unsafe_allow_html=True
        )

st.markdown("---")

# ── Public Build Stats ────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center; padding:8px 0 20px 0;">
    <div style="font-size:0.8rem; color:{PEACH}; font-weight:600; letter-spacing:0.1em;
                text-transform:uppercase; margin-bottom:8px;">
        Built in public · Proof of work
    </div>
    <div style="color:{TEXT_MUTED}; font-size:0.9rem; max-width:480px;
                margin:0 auto 24px auto;">
        This platform is one person's work. No VC. No team.
        Just a Black engineer from Virginia building in the open.
    </div>
</div>
""", unsafe_allow_html=True)

s1, s2, s3, s4, s5 = st.columns(5)
stat_style = f"background:{BG_CARD}; border:1px solid {BG_BORDER}; border-radius:12px; padding:18px; text-align:center;"
num_style  = f"font-size:2rem; font-weight:800; color:{PEACH}; line-height:1;"
lbl_style  = f"font-size:0.75rem; color:{TEXT_MUTED}; margin-top:4px; text-transform:uppercase; letter-spacing:0.06em;"

with s1:
    st.markdown(f"<div style='{stat_style}'><div style='{num_style}'>688</div><div style='{lbl_style}'>Git Commits</div></div>", unsafe_allow_html=True)
with s2:
    st.markdown(f"<div style='{stat_style}'><div style='{num_style}'>154</div><div style='{lbl_style}'>Pages Built</div></div>", unsafe_allow_html=True)
with s3:
    st.markdown(f"<div style='{stat_style}'><div style='{num_style}'>92K</div><div style='{lbl_style}'>Lines of Code</div></div>", unsafe_allow_html=True)
with s4:
    st.markdown(f"<div style='{stat_style}'><div style='{num_style}'>522</div><div style='{lbl_style}'>Files</div></div>", unsafe_allow_html=True)
with s5:
    st.markdown(f"<div style='{stat_style}'><div style='{num_style}'>274</div><div style='{lbl_style}'>Branches</div></div>", unsafe_allow_html=True)

st.markdown(
    f"<div style='text-align:center; margin-top:12px;'>"
    f"<a href='https://github.com/bookofdarrian/darrian-budget' target='_blank' "
    f"style='color:{PEACH}; font-size:0.82rem; text-decoration:none;'>"
    "View on GitHub →</a></div>",
    unsafe_allow_html=True
)

st.markdown("---")

# ── Feature comparison table ──────────────────────────────────────────────────
st.markdown("### What's included in each tier")
features = [
    ("Budget tracking",                      "✅", "✅", "✅"),
    ("Expense & income management",          "✅", "✅", "✅"),
    ("Bank statement import",                "✅", "✅", "✅"),
    ("Financial goals",                      "✅", "✅", "✅"),
    ("Receipts & HSA tracker",               "✅", "✅", "✅"),
    ("Bill calendar",                        "✅", "✅", "✅"),
    ("Paycheck calculator",                  "✅", "✅", "✅"),
    ("AI Monthly Summary (Claude)",          "—",  "✅", "✅"),
    ("AI Budget Recommendations",            "—",  "✅", "✅"),
    ("Auto-Categorize Transactions",         "—",  "✅", "✅"),
    ("Ask Claude Anything",                  "—",  "✅", "✅"),
    ("Monthly Trends AI Analysis",           "—",  "✅", "✅"),
    ("Net Worth Tracker",                    "—",  "✅", "✅"),
    ("Investment Portfolio",                 "—",  "✅", "✅"),
    ("SoleOps Reseller Suite (40+ tools)",   "—",  "✅", "✅"),
    ("Savings Projections",                  "—",  "✅", "✅"),
    ("Direct line to Darrian",               "—",  "—",  "🔱"),
    ("Custom AI agents",                     "—",  "—",  "🔱"),
    ("Early feature access",                 "—",  "—",  "🔱"),
    ("Private community",                    "—",  "—",  "🔱"),
    ("Roadmap influence",                    "—",  "—",  "🔱"),
]
feat_df = pd.DataFrame(features, columns=["Feature", "🐾 Panther Papers", "⭐ Pro", "🔱 Sovereign"])
st.dataframe(feat_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Sovereign application (25+, logged in, not already sovereign) ─────────────
if user and not is_sov and not is_owner:
    with st.expander("🔱 Express interest in Sovereign access"):
        st.markdown(
            f"<div style='color:{TEXT_MUTED}; font-size:0.88rem; margin-bottom:12px;'>"
            "Sovereign is not applied for — it's granted. But you can let Darrian know "
            "who you are. If it's meant to happen, it will.<br><br>"
            "<strong style='color:gold;'>Must be 25 or older.</strong></div>",
            unsafe_allow_html=True
        )
        age_ok  = st.checkbox("✅ I confirm I am 25 years of age or older", key="sov_age_confirm")
        sov_name = st.text_input("Your name", key="sov_name", max_chars=100)
        sov_why  = st.text_area(
            "Why are you worthy? (Be real. No resume BS.)",
            key="sov_why", max_chars=1000, height=120
        )
        if st.button("Submit", key="sov_apply_btn"):
            if not age_ok:
                st.error("Must confirm you are 25+.")
            elif not sov_why.strip():
                st.error("Say something real.")
            else:
                try:
                    conn = get_conn()
                    # Check for duplicate
                    exists = conn.execute(
                        "SELECT id FROM sovereign_applications WHERE email=? AND status='pending'",
                        (user.get("email", ""),)
                    ).fetchone()
                    if exists:
                        st.info("Your expression of interest is already on file.")
                    else:
                        conn.execute(
                            "INSERT INTO sovereign_applications (email, name, why_worthy, age_confirm) VALUES (?,?,?,?)",
                            (user.get("email", ""), sov_name.strip(), sov_why.strip(), 1)
                        )
                        conn.commit()
                        st.success("🔱 Received. Darrian will reach out if the time is right.")
                    conn.close()
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")

# ── Waitlist ──────────────────────────────────────────────────────────────────
st.markdown("### 📬 Join the Early Access List")
st.caption("Get notified when new features drop and lock in the beta price.")
wl_col1, wl_col2 = st.columns([3, 1])
with wl_col1:
    wl_email = st.text_input("Email", placeholder="you@email.com", key="wl_email", label_visibility="collapsed")
    wl_name  = st.text_input("Name (optional)", placeholder="First name", key="wl_name", label_visibility="collapsed")
with wl_col2:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("Join Waitlist", type="primary", use_container_width=True, key="btn_waitlist"):
        if not wl_email or "@" not in wl_email:
            st.error("Please enter a valid email.")
        else:
            success = add_to_waitlist(wl_email, wl_name, source="pricing_page")
            if success:
                st.success("✅ You're on the list!")
            else:
                st.info("You're already on the list!")
try:
    count = get_waitlist_count()
    if count > 0:
        st.caption(f"🔥 {count} people already on the waitlist")
except Exception:
    pass

# ── FAQ ───────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Frequently Asked Questions")
with st.expander("Can I cancel Pro anytime?"):
    st.write("Yes. Cancel from your billing portal. You keep Pro access until the billing period ends.")
with st.expander("Is my financial data secure?"):
    st.markdown("""
**Yes — private, encrypted, never shared.**

- 🔐 Passwords hashed with **bcrypt** (one-way, salted)
- 🛡️ All traffic over **HTTPS / TLS 1.3**
- 🗄️ Each user's data is isolated in a **private PostgreSQL database**
- 📄 Bank PDFs parsed in memory and immediately discarded
- 🚫 We never sell or monetize your data
- 🤖 AI features send only what you request — nothing else
""")
with st.expander("How does Sovereign work?"):
    st.markdown(f"""
Sovereign is not a product tier you buy. It's something Darrian grants to people
he deems worthy — people building real things, living by real values,
25 and older.

If you're on the list above, he'll reach out. If not, keep building.

*Built on Ubuntu values: "I am because we are."*
""")
with st.expander("What banks does import support?"):
    st.write("Currently Navy Federal Credit Union (NFCU) PDF statements. More banks coming soon.")

# ── ADMIN: Sovereign Grant Panel (Owner Only) ─────────────────────────────────
if is_owner:
    st.markdown("---")
    st.markdown("### 🔱 Sovereign Admin Panel")
    st.caption("Only you can see this section.")

    try:
        conn = get_conn()
        apps = conn.execute(
            "SELECT id, email, name, why_worthy, age_confirm, status, created_at "
            "FROM sovereign_applications ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        conn.close()

        if apps:
            for app in apps:
                app_id, email, name, why, age_ok_val, status, created = app
                with st.expander(f"{email} — {status.upper()} — {created[:10]}"):
                    st.markdown(f"**Name:** {name or '(not given)'}")
                    st.markdown(f"**25+ confirmed:** {'Yes' if age_ok_val else 'No'}")
                    st.markdown(f"**Why worthy:**\n\n{why}")
                    if status == "pending":
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button(f"🔱 Grant Sovereign — {email}", key=f"grant_{app_id}"):
                                try:
                                    # Update user plan in auth DB
                                    from utils.db import get_conn as _auth_conn
                                    aconn = _auth_conn()
                                    aconn.execute(
                                        "UPDATE users SET plan='sovereign', subscription_status='active' WHERE email=?",
                                        (email,)
                                    )
                                    aconn.execute(
                                        "UPDATE sovereign_applications SET status='granted', reviewed_at=datetime('now'), reviewed_by=? WHERE id=?",
                                        (user.get("email"), app_id)
                                    )
                                    aconn.commit()
                                    aconn.close()
                                    st.success(f"✅ {email} is now Sovereign.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error granting: {e}")
                        with c2:
                            if st.button(f"❌ Deny — {email}", key=f"deny_{app_id}"):
                                try:
                                    dconn = get_conn()
                                    dconn.execute(
                                        "UPDATE sovereign_applications SET status='denied', reviewed_at=datetime('now'), reviewed_by=? WHERE id=?",
                                        (user.get("email"), app_id)
                                    )
                                    dconn.commit()
                                    dconn.close()
                                    st.info(f"Application from {email} denied.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
        else:
            st.info("No Sovereign applications yet.")

        # Manual grant by email (for people you choose directly)
        st.markdown("#### Grant Sovereign to anyone")
        col_grant, col_btn = st.columns([3, 1])
        with col_grant:
            direct_email = st.text_input("Email to grant Sovereign access", key="direct_sovereign_email")
        with col_btn:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🔱 Grant", key="direct_grant_btn", type="primary"):
                if direct_email and "@" in direct_email:
                    try:
                        gconn = get_conn()
                        updated = gconn.execute(
                            "UPDATE users SET plan='sovereign', subscription_status='active' WHERE LOWER(email)=LOWER(?)",
                            (direct_email.strip(),)
                        ).rowcount
                        gconn.commit()
                        gconn.close()
                        if updated > 0:
                            st.success(f"🔱 {direct_email} is now Sovereign.")
                        else:
                            st.error(f"No user found with email: {direct_email}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Enter a valid email.")

        # Revoke panel
        st.markdown("#### Revoke Sovereign access")
        revoke_email = st.text_input("Email to revoke", key="revoke_sovereign_email")
        if st.button("❌ Revoke", key="revoke_btn"):
            if revoke_email and "@" in revoke_email:
                try:
                    rconn = get_conn()
                    rconn.execute(
                        "UPDATE users SET plan='free', subscription_status='inactive' WHERE LOWER(email)=LOWER(?)",
                        (revoke_email.strip(),)
                    )
                    rconn.commit()
                    rconn.close()
                    st.success(f"Sovereign access revoked for {revoke_email}.")
                except Exception as e:
                    st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"Admin panel error: {e}")
