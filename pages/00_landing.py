"""
Peach State Savings — Public Landing Page
No login required. Shown to all visitors before they authenticate.
"""

import streamlit as st

st.set_page_config(
    page_title="Peach State Savings — AI-Powered Personal Finance",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
PEACH      = "#FFAB76"
PEACH_DARK = "#e8924f"
PEACH_GLOW = "#3d2010"
BG_MAIN    = "#0e1117"
BG_CARD    = "#12151c"
BG_BORDER  = "#1e2330"
TEXT_MUTED = "#8892a4"
TEXT_MAIN  = "#fafafa"

st.markdown(f"""
<style>
/* ── Base ── */
.main .block-container {{
    max-width: 1100px;
    padding: 0 2rem 4rem 2rem;
}}
body, .stApp {{
    background: {BG_MAIN};
    color: {TEXT_MAIN};
}}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stSidebarNav"] {{ display: none; }}

/* ── Hero ── */
.hero {{
    text-align: center;
    padding: 80px 20px 60px 20px;
}}
.hero-logo {{
    font-size: 3.2rem;
    font-weight: 900;
    color: {PEACH};
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin-bottom: 12px;
}}
.hero-sub {{
    font-size: 1.25rem;
    color: {TEXT_MUTED};
    margin-bottom: 32px;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.6;
}}
.hero-badge {{
    display: inline-block;
    background: {PEACH_GLOW};
    border: 1px solid {PEACH};
    color: {PEACH};
    font-size: 0.8rem;
    font-weight: 700;
    padding: 6px 16px;
    border-radius: 30px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 24px;
}}

/* ── Section headers ── */
.section-title {{
    font-size: 1.9rem;
    font-weight: 800;
    color: {TEXT_MAIN};
    text-align: center;
    margin-bottom: 8px;
    letter-spacing: -0.02em;
}}
.section-sub {{
    font-size: 1rem;
    color: {TEXT_MUTED};
    text-align: center;
    margin-bottom: 40px;
}}

/* ── Feature cards ── */
.feat-card {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 14px;
    padding: 24px;
    height: 100%;
    transition: border-color 0.2s;
}}
.feat-card:hover {{
    border-color: {PEACH};
}}
.feat-icon {{
    font-size: 2rem;
    margin-bottom: 10px;
}}
.feat-title {{
    font-size: 1rem;
    font-weight: 700;
    color: {TEXT_MAIN};
    margin-bottom: 6px;
}}
.feat-desc {{
    font-size: 0.85rem;
    color: {TEXT_MUTED};
    line-height: 1.6;
}}

/* ── Builder section ── */
.builder-card {{
    background: linear-gradient(135deg, {PEACH_GLOW} 0%, {BG_CARD} 100%);
    border: 1px solid {PEACH};
    border-radius: 18px;
    padding: 48px 40px;
    margin: 0 auto;
}}
.builder-name {{
    font-size: 1.4rem;
    font-weight: 800;
    color: {PEACH};
    margin-bottom: 4px;
}}
.builder-role {{
    font-size: 0.85rem;
    color: {TEXT_MUTED};
    margin-bottom: 20px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.builder-quote {{
    font-size: 1.05rem;
    color: {TEXT_MAIN};
    line-height: 1.8;
    font-style: italic;
    border-left: 3px solid {PEACH};
    padding-left: 20px;
    margin: 20px 0;
}}

/* ── Stat pills ── */
.stat-row {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    justify-content: center;
    margin: 32px 0;
}}
.stat-pill {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 40px;
    padding: 12px 28px;
    text-align: center;
}}
.stat-num {{
    font-size: 1.8rem;
    font-weight: 800;
    color: {PEACH};
    line-height: 1;
}}
.stat-label {{
    font-size: 0.75rem;
    color: {TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 4px;
}}

/* ── Pricing cards ── */
.price-card {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 14px;
    padding: 28px 24px;
    text-align: center;
}}
.price-card.featured {{
    border-color: {PEACH};
    background: linear-gradient(135deg, {PEACH_GLOW} 0%, {BG_CARD} 100%);
}}
.price-tag {{
    font-size: 2.2rem;
    font-weight: 900;
    color: {TEXT_MAIN};
    line-height: 1;
}}
.price-period {{
    font-size: 0.8rem;
    color: {TEXT_MUTED};
}}
.price-name {{
    font-size: 1rem;
    font-weight: 700;
    color: {PEACH};
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
.price-feat {{
    font-size: 0.85rem;
    color: #c8d0dc;
    text-align: left;
    margin: 6px 0;
}}
.price-feat::before {{
    content: "✓ ";
    color: {PEACH};
    font-weight: 700;
}}

/* ── CTA section ── */
.cta-section {{
    text-align: center;
    background: linear-gradient(135deg, {PEACH_GLOW} 0%, {BG_CARD} 100%);
    border: 1px solid {PEACH};
    border-radius: 20px;
    padding: 64px 40px;
    margin-top: 60px;
}}
.cta-title {{
    font-size: 2.2rem;
    font-weight: 900;
    color: {TEXT_MAIN};
    margin-bottom: 12px;
    letter-spacing: -0.02em;
}}
.cta-sub {{
    font-size: 1.05rem;
    color: {TEXT_MUTED};
    margin-bottom: 32px;
}}

/* ── Divider ── */
.section-divider {{
    border: none;
    border-top: 1px solid {BG_BORDER};
    margin: 60px 0;
}}

/* ── Buttons ── */
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {PEACH}, {PEACH_DARK}) !important;
    color: #000 !important;
    border: none !important;
    font-weight: 800 !important;
    font-size: 1rem !important;
    padding: 14px 32px !important;
    border-radius: 10px !important;
    min-height: 52px !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: {PEACH_DARK} !important;
}}

/* ── Mobile ── */
@media (max-width: 768px) {{
    .hero {{ padding: 48px 12px 36px 12px; }}
    .hero-logo {{ font-size: 2.2rem; }}
    .builder-card {{ padding: 28px 20px; }}
    .cta-section {{ padding: 40px 20px; }}
    .cta-title {{ font-size: 1.6rem; }}
    .section-title {{ font-size: 1.5rem; }}
    .main .block-container {{ padding: 0 1rem 3rem 1rem; }}
}}
</style>
""", unsafe_allow_html=True)


# ── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">🚀 Built by a TPM at Visa · Deployed on a self-hosted homelab</div>
    <div class="hero-logo">🍑 Peach State Savings</div>
    <div class="hero-sub">
        A full-stack, AI-powered personal finance platform built from scratch —
        covering budgeting, investing, net worth tracking, and more.
    </div>
</div>
""", unsafe_allow_html=True)

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    if st.button("🍑 Get Started Free — No Credit Card", type="primary", use_container_width=True):
        st.switch_page("app.py")
    st.markdown(
        f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.8rem; margin-top:10px;'>"
        "Free plan includes budgeting, expense tracking, bank import, and financial goals."
        "</div>",
        unsafe_allow_html=True
    )

# ── STATS ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="stat-row">
    <div class="stat-pill">
        <div class="stat-num">11+</div>
        <div class="stat-label">Finance Tools</div>
    </div>
    <div class="stat-pill">
        <div class="stat-num">AI</div>
        <div class="stat-label">Powered by Claude</div>
    </div>
    <div class="stat-pill">
        <div class="stat-num">100%</div>
        <div class="stat-label">Self-Hosted & Private</div>
    </div>
    <div class="stat-pill">
        <div class="stat-num">$0</div>
        <div class="stat-label">To Start</div>
    </div>
</div>
<hr class="section-divider">
""", unsafe_allow_html=True)


# ── FEATURES ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-title">Everything Your Finances Need</div>
<div class="section-sub">From day-to-day budgeting to long-term wealth tracking — all in one place.</div>
""", unsafe_allow_html=True)

features = [
    ("📊", "Budget Dashboard", "Track income vs spending in real time. See exactly where every dollar goes each month."),
    ("🤖", "AI Insights", "Claude-powered analysis of your spending patterns with personalized recommendations."),
    ("🏦", "Bank Import", "Paste your bank statement and watch it auto-categorize. NFCU, Chase, BofA, and more."),
    ("📈", "Portfolio & RSU Tracker", "Track your Visa RSUs, ESPP, investment portfolio, and dividend income in one view."),
    ("💎", "Net Worth Tracker", "Watch your net worth grow month over month with historical charts and projections."),
    ("🎯", "Financial Goals", "Set savings goals with deadlines. See progress bars and AI-powered milestone predictions."),
    ("🏠", "Rent vs Buy Calculator", "Model the real cost of buying vs renting in your market with full amortization breakdowns."),
    ("📋", "Bill Calendar", "Never miss a bill. Visual calendar with due-date alerts and monthly totals."),
    ("💸", "Paycheck Allocator", "Enter your gross salary — get an exact net paycheck breakdown including GA state taxes."),
    ("🧾", "HSA Receipt Vault", "Scan and categorize HSA receipts with AI for tax time."),
    ("📉", "Debt Payoff Planner", "Avalanche vs snowball — model your payoff date and total interest saved."),
]

rows = [features[i:i+3] for i in range(0, len(features), 3)]
for row in rows:
    cols = st.columns(len(row), gap="medium")
    for col, (icon, title, desc) in zip(cols, row):
        with col:
            st.markdown(f"""
            <div class="feat-card">
                <div class="feat-icon">{icon}</div>
                <div class="feat-title">{title}</div>
                <div class="feat-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)


# ── BUILDER STORY ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-title">Built by Someone Who Needed It</div>
<div class="section-sub">Not a startup. Not a VC-backed company. Just a builder who wanted better tools.</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="builder-card">
    <div class="builder-name">Darrian Belcher</div>
    <div class="builder-role">Technical Project Analyst @ Visa · Atlanta, GA</div>
    <div class="builder-quote">
        "I built Peach State Savings because every finance app I tried either did too little
        or cost too much — and none of them actually understood how I made money.
        Between my Visa salary, RSU vests, ESPP purchases, and sneaker resale income,
        I needed something custom. So I built it."
    </div>
    <div style="color: #c8d0dc; font-size: 0.9rem; line-height: 1.8; margin-top: 16px;">
        Every feature in this app was built from a real need. The bank import came from 
        spending 2 hours manually copying transactions into a spreadsheet. The RSU tracker 
        came from not understanding my Visa stock vests. The sneaker P&amp;L came from 
        losing track of what I actually made flipping shoes.<br><br>
        This runs 24/7 on a self-hosted homelab in my apartment — Proxmox, Docker, PostgreSQL,
        and an AI dev pipeline that ships new features overnight. It's production software
        I use every day to manage my own financial life.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)


# ── PRICING ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-title">Simple, Honest Pricing</div>
<div class="section-sub">Start free. Upgrade when you're ready.</div>
""", unsafe_allow_html=True)

pc_l, p1, p2, pc_r = st.columns([1, 2, 2, 1], gap="large")

with p1:
    st.markdown("""
    <div class="price-card">
        <div class="price-name">Free</div>
        <div class="price-tag">$0</div>
        <div class="price-period">forever</div>
        <div style="margin-top: 20px;">
            <div class="price-feat">Monthly budget dashboard</div>
            <div class="price-feat">Expense tracking</div>
            <div class="price-feat">Income logging</div>
            <div class="price-feat">Bank statement import</div>
            <div class="price-feat">Bill calendar</div>
            <div class="price-feat">Financial goals</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with p2:
    st.markdown("""
    <div class="price-card featured">
        <div class="price-name">Pro ⭐</div>
        <div class="price-tag">$4.99</div>
        <div class="price-period">/ month</div>
        <div style="margin-top: 20px;">
            <div class="price-feat">Everything in Free</div>
            <div class="price-feat">AI Spending Insights</div>
            <div class="price-feat">Net Worth Tracker</div>
            <div class="price-feat">Portfolio & RSU Tracker</div>
            <div class="price-feat">Monthly Trends Analysis</div>
            <div class="price-feat">Business Income Tracker</div>
            <div class="price-feat">Market News & Backtesting</div>
            <div class="price-feat">All Pro tools unlocked</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

# ── FINAL CTA ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cta-section">
    <div class="cta-title">Start managing your money better — today.</div>
    <div class="cta-sub">
        Free forever for core features. No credit card. No ads. No data selling.
        <br>Just tools that actually work, built by someone who uses them every day.
    </div>
</div>
""", unsafe_allow_html=True)

cta_l, cta_c, cta_r = st.columns([1, 2, 1])
with cta_c:
    st.markdown("<div style='margin-top: -32px;'></div>", unsafe_allow_html=True)
    if st.button("🍑 Create Free Account", type="primary", use_container_width=True, key="cta_bottom"):
        st.switch_page("app.py")
    st.markdown(
        f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.78rem; margin-top:8px; margin-bottom:10px; line-height:1.6;'>"
        "Creates a secure account with your email and password. "
        "Your data is stored privately on this server — no third-party sharing, no ads. "
        "Free plan is free forever, no credit card required."
        "</div>",
        unsafe_allow_html=True
    )
    if st.button("Sign In →", use_container_width=True, key="signin_bottom"):
        st.switch_page("app.py")

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<hr class="section-divider" style="margin-top: 60px;">
<div style="text-align: center; color: {TEXT_MUTED}; font-size: 0.8rem; padding-bottom: 40px;">
    🍑 Peach State Savings · Built &amp; self-hosted in Atlanta, GA ·
    <a href="https://www.linkedin.com/in/darrian-belcher/" style="color: {PEACH}; text-decoration: none;">
        Connect on LinkedIn
    </a>
</div>
""", unsafe_allow_html=True)
