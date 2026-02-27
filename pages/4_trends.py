

import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, get_setting, load_investment_context
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Monthly Trends — Peach State Savings", page_icon="📈", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("Monthly Trends")
inject_css()

# ── Load API key ──────────────────────────────────────────────────────────────
_env_key = os.environ.get("ANTHROPIC_API_KEY", "")
if "api_key" not in st.session_state:
    if _env_key:
        st.session_state["api_key"] = _env_key
    else:
        _db_key = get_setting("anthropic_api_key", "")
        if _db_key:
            st.session_state["api_key"] = _db_key

api_key = st.session_state.get("api_key", "")

# ── Load investment context from DB (always fresh — no session cache here) ───
_saved = load_investment_context()
_inv_401k      = float(_saved.get("bal_401k", 0) or 0)
_inv_401k_ytd  = float(_saved.get("contrib_401k_ytd", 0) or 0)
_inv_401k_match= float(_saved.get("match_401k_ytd", 0) or 0)
_inv_roth      = float(_saved.get("bal_roth", 0) or 0)
_inv_roth_ytd  = float(_saved.get("contrib_roth_ytd", 0) or 0)
_inv_hsa       = float(_saved.get("bal_hsa", 0) or 0)
_inv_hsa_ytd   = float(_saved.get("contrib_hsa_ytd", 0) or 0)
_inv_brokerage = float(_saved.get("bal_brokerage", 0) or 0)
_inv_notes     = _saved.get("notes", "") or ""
# Also keep session state in sync for AI context builder
st.session_state["inv_401k"]                = _inv_401k
st.session_state["inv_401k_contrib_ytd"]    = _inv_401k_ytd
st.session_state["inv_401k_employer_match"] = _inv_401k_match
st.session_state["inv_roth"]                = _inv_roth
st.session_state["inv_roth_contrib_ytd"]    = _inv_roth_ytd
st.session_state["inv_hsa"]                 = _inv_hsa
st.session_state["inv_hsa_contrib_ytd"]     = _inv_hsa_ytd
st.session_state["inv_brokerage"]           = _inv_brokerage
st.session_state["inv_notes"]               = _inv_notes
st.session_state["inv_loaded_from_db"]      = True

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/18_real_estate_bot.py", label="🏠 Real Estate Bot", icon="🏠")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends 🔒", icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights 🔒",    icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth 🔒",      icon="💎")
st.sidebar.page_link("pages/0_pricing.py",        label="⭐ Upgrade to Pro", icon="⭐")
render_sidebar_user_widget()

st.title("📈 Monthly Trends")
st.caption("Track your income, spending, and savings across every month — powered by your Navy Federal data.")
# v2

# ── Pull all data ─────────────────────────────────────────────────────────────
conn = get_conn()
income_all = read_sql("SELECT month, SUM(amount) AS income FROM income GROUP BY month", conn)

# Debits only, excluding transfers — is_debit=1 or NULL, category != 'Transfer'
txn_all = read_sql(
    """SELECT month, SUM(amount) AS spent FROM bank_transactions
       WHERE (is_debit = 1 OR is_debit IS NULL)
         AND (category IS NULL OR category != 'Transfer')
       GROUP BY month""",
    conn
)

# Credits (deposits) — is_debit=0
txn_credits_all = read_sql(
    "SELECT month, SUM(amount) AS deposited FROM bank_transactions WHERE is_debit = 0 GROUP BY month",
    conn
)

# Transfers — for separate display
txn_transfers_all = read_sql(
    """SELECT month, SUM(amount) AS transferred FROM bank_transactions
       WHERE category = 'Transfer'
       GROUP BY month""",
    conn
)

# Raw debit transactions (non-transfer) for merchant/spending analysis
txn_raw = read_sql(
    """SELECT month, date, description, amount, category, is_debit
       FROM bank_transactions
       WHERE (is_debit = 1 OR is_debit IS NULL)
         AND (category IS NULL OR category != 'Transfer')
       ORDER BY date DESC""",
    conn
)

# Category breakdown — debits only, no transfers
txn_cat_all = read_sql(
    """SELECT month, category, SUM(amount) AS spent
       FROM bank_transactions
       WHERE (is_debit = 1 OR is_debit IS NULL)
         AND category IS NOT NULL AND category != ''
         AND category != 'Transfer'
       GROUP BY month, category""",
    conn
)

# All transactions for AI context
txn_all_raw = read_sql(
    "SELECT month, date, description, amount, category, is_debit FROM bank_transactions ORDER BY date DESC",
    conn
)
conn.close()

# ── Guard: no data ────────────────────────────────────────────────────────────
if txn_all.empty and income_all.empty:
    st.info("📭 No data yet — import your Navy Federal PDF on the **Bank Import** page first.")
    st.stop()

# ── Build unified month table ─────────────────────────────────────────────────
all_months = set()
if not income_all.empty:
    all_months.update(income_all["month"].tolist())
if not txn_all.empty:
    all_months.update(txn_all["month"].tolist())

trends = pd.DataFrame(sorted(all_months), columns=["month"])

if not income_all.empty:
    trends = pd.merge(trends, income_all, on="month", how="left")
else:
    trends["income"] = 0.0

if not txn_all.empty:
    trends = pd.merge(trends, txn_all, on="month", how="left")
else:
    trends["spent"] = 0.0

if not txn_credits_all.empty:
    trends = pd.merge(trends, txn_credits_all, on="month", how="left")
else:
    trends["deposited"] = 0.0

if not txn_transfers_all.empty:
    trends = pd.merge(trends, txn_transfers_all, on="month", how="left")
else:
    trends["transferred"] = 0.0

trends = trends.fillna(0)
trends["savings"]      = trends["income"] - trends["spent"]
trends["savings_rate"] = (trends["savings"] / trends["income"].replace(0, float("nan"))) * 100
trends["month_label"]  = trends["month"].apply(lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y"))
trends = trends.sort_values("month").reset_index(drop=True)

# Compute totals via direct cursor queries to avoid pandas/psycopg2 compatibility issues.
from utils.db import execute as db_execute
_conn2 = get_conn()
_c = db_execute(_conn2, "SELECT SUM(amount) FROM income")
total_income_manual = float(_c.fetchone()[0] or 0)

_c = db_execute(_conn2, "SELECT SUM(amount) FROM bank_transactions WHERE is_debit = 0")
total_deposited = float(_c.fetchone()[0] or 0)

_c = db_execute(_conn2, "SELECT SUM(amount) FROM bank_transactions WHERE category = 'Transfer'")
total_transferred = float(_c.fetchone()[0] or 0)
_conn2.close()

# All-time income = manual income entries + bank deposit credits (payroll)
total_income_all     = total_income_manual + total_deposited
total_spent_all      = trends["spent"].sum()
total_saved_all      = total_income_all - total_spent_all
avg_sr = trends["savings_rate"].replace([float("inf"), float("-inf")], float("nan")).mean()

# ── All-Time KPIs ─────────────────────────────────────────────────────────────
st.subheader("📊 All-Time Summary")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Income",     f"${total_income_all:,.2f}",
          help="Manual income entries + all bank payroll/deposit credits")
k2.metric("Total Spent",      f"${total_spent_all:,.2f}")
k3.metric("Total Saved",      f"${total_saved_all:,.2f}")
k4.metric("Avg Savings Rate", f"{avg_sr:.1f}%" if not pd.isna(avg_sr) else "—")

notes = []
if total_income_manual > 0:
    notes.append(f"📋 Manual income entries: **${total_income_manual:,.2f}**")
if total_deposited > 0:
    notes.append(f"💰 Bank payroll/deposits: **${total_deposited:,.2f}**")
if total_transferred > 0:
    notes.append(f"🔄 Transfers excluded from spending: **${total_transferred:,.2f}**")
if notes:
    st.caption("  ·  ".join(notes))

# ── Investment Portfolio Snapshot ─────────────────────────────────────────────
# Use local vars loaded directly from DB above (not session state) to avoid
# cross-page session state timing issues.
_any_inv = any([_inv_401k, _inv_roth, _inv_hsa, _inv_brokerage])

if _any_inv:
    st.markdown("---")
    st.subheader("📈 Investment Portfolio")
    total_inv = _inv_401k + _inv_roth + _inv_hsa + _inv_brokerage
    i1, i2, i3, i4, i5 = st.columns(5)
    i1.metric("Total Portfolio",  f"${total_inv:,.2f}")
    i2.metric("401(k)",           f"${_inv_401k:,.2f}"      if _inv_401k      > 0 else "—")
    i3.metric("Roth IRA",         f"${_inv_roth:,.2f}"      if _inv_roth      > 0 else "—")
    i4.metric("HSA",              f"${_inv_hsa:,.2f}"       if _inv_hsa       > 0 else "—")
    i5.metric("Cash Mgmt / HY",   f"${_inv_brokerage:,.2f}" if _inv_brokerage > 0 else "—")

    # YTD contribution progress bars
    contrib_cols = st.columns(3)
    if _inv_roth_ytd > 0 or _inv_roth > 0:
        with contrib_cols[0]:
            roth_pct = min(_inv_roth_ytd / 7000, 1.0)
            st.caption(f"Roth IRA: ${_inv_roth_ytd:,.2f} / $7,000 limit")
            st.progress(roth_pct, text=f"{roth_pct*100:.0f}% of annual limit")
    if _inv_hsa_ytd > 0 or _inv_hsa > 0:
        with contrib_cols[1]:
            hsa_pct = min(_inv_hsa_ytd / 4300, 1.0)
            st.caption(f"HSA: ${_inv_hsa_ytd:,.2f} / $4,300 limit")
            st.progress(hsa_pct, text=f"{hsa_pct*100:.0f}% of annual limit")
    if _inv_401k_ytd > 0 or _inv_401k > 0:
        with contrib_cols[2]:
            k401_pct = min(_inv_401k_ytd / 23500, 1.0)
            st.caption(f"401(k): ${_inv_401k_ytd:,.2f} / $23,500 limit")
            st.progress(k401_pct, text=f"{k401_pct*100:.0f}% of annual limit")

    if _inv_notes.strip():
        st.caption(f"📝 {_inv_notes.strip()}")
    st.caption("💡 Update balances on the **AI Insights** page.")
else:
    st.markdown("---")
    st.info("📈 **Investment portfolio not set up** — add your 401k/Roth IRA/HSA balances on the **AI Insights** page to see them here.")

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
st.subheader("💵 Income vs. Spending by Month")
chart_df = trends.set_index("month_label")[["income", "spent"]].copy()
chart_df.columns = ["Income", "Spent"]
st.bar_chart(chart_df, use_container_width=True)

st.markdown("---")
st.subheader("💰 Monthly Savings")
st.line_chart(trends.set_index("month_label")[["savings"]].rename(columns={"savings": "Savings"}), use_container_width=True)

st.markdown("---")
st.subheader("📉 Savings Rate % by Month")
st.line_chart(trends.set_index("month_label")[["savings_rate"]].rename(columns={"savings_rate": "Savings Rate (%)"}), use_container_width=True)

# ── Category Breakdown ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏷️ Spending by Category")

if not txn_cat_all.empty:
    cat_pivot = txn_cat_all.pivot_table(index="month", columns="category", values="spent", aggfunc="sum").fillna(0)
    cat_pivot.index = cat_pivot.index.map(lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y"))
    st.bar_chart(cat_pivot, use_container_width=True)

    cat_totals = txn_cat_all.groupby("category")["spent"].sum().sort_values(ascending=False).reset_index()
    cat_totals.columns = ["Category", "Total Spent ($)"]
    cat_totals["Total Spent ($)"] = cat_totals["Total Spent ($)"].map("${:,.2f}".format)
    col_a, _ = st.columns([1, 1])
    with col_a:
        st.markdown("**All-Time Category Totals**")
        st.dataframe(cat_totals, use_container_width=True, hide_index=True)
else:
    st.info("No categorized transactions yet. Categorize your transactions on the **Bank Import** page.")

# ── Top Merchants ─────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏪 Top Merchants & Income (All Time)")

if not txn_raw.empty:
    # ── Merchant consolidation map ────────────────────────────────────────────
    # Groups similar merchants under one display name for cleaner reporting.
    _MERCHANT_GROUPS = [
        # (display_name, [keywords_to_match_in_description_lower])
        # ── Housing & Fixed Bills ────────────────────────────────────────────
        ("🏠 The Vivian (Rent)",        ["the vivian", "vivian 498", "vivian 4980", "paid to - the vivian"]),
        ("⚡ Georgia Power",            ["gpc gpc"]),
        ("🛡️ Allstate (Renters Ins.)", ["allstate"]),
        ("🏋️ Planet Fitness",          ["pf atlanta"]),
        # ── Transportation ───────────────────────────────────────────────────
        ("⛽ Fuel (All Stations)",      ["chevron", "shell oil", "circle k", "exxon", "sunoco", "qt ", "kwik save"]),
        ("🚗 Uber / Lyft",             ["uber", "lyft"]),
        ("🔧 Mavis (Auto)",            ["mavis"]),
        # ── Food & Dining ────────────────────────────────────────────────────
        ("🛒 Walmart / Grocery",        ["walmart", "wal-mart", "wm super"]),
        ("🌯 Chipotle",                 ["chipotle"]),
        ("🍗 Chick-fil-A",              ["chick-fil-a"]),
        ("🍗 Zaxby's",                  ["zaxby"]),
        ("🍔 Cook Out",                 ["cook out"]),
        ("🛵 DoorDash",                 ["doordash", "dd *doordash"]),
        # ── Shopping ─────────────────────────────────────────────────────────
        ("📦 Amazon",                   ["amazon"]),
        ("🛍️ eBay",                    ["ebay"]),
        ("👕 Goodwill / Thrift",        ["goodwill", "2w thrift", "l train vintage"]),
        # ── Travel ───────────────────────────────────────────────────────────
        ("✈️ Airbnb",                   ["airbnb"]),
        ("✈️ Expedia",                  ["expedia"]),
        # ── Subscriptions ────────────────────────────────────────────────────
        ("🍎 Apple (iTunes/iCloud)",    ["apple.com/bill", "apple.com"]),
        ("📺 Hulu",                     ["hulu"]),
        ("📺 Netflix",                  ["netflix"]),
        ("📺 Crunchyroll",              ["crunchyroll"]),
        ("🎮 PlayStation / Steam",      ["playstation", "steamgames"]),
        # ── Entertainment ────────────────────────────────────────────────────
        ("🎬 AMC Theatres",             ["amc "]),
        ("🎬 Regal Cinemas",            ["regal"]),
        ("🎟️ StubHub",                 ["stubhub"]),
        ("🎟️ Ticketmaster",            ["ticketmaster", "tm *ticketmaster"]),
        # ── Personal Care ────────────────────────────────────────────────────
        ("✂️ TheCut (Barber)",          ["thecut"]),
        ("💊 Walgreens",                ["walgreens"]),
        # ── Gardening (Zelle / Apple Pay sends to workers) ────────────────────────────
        ("🌿 Gardening (Labor/Supplies)",         ["zelle*joshua", "zelle*xavier", "zelle db travares",
                                         "apple cash sent mo", "apple cash sent to", "apple cash"]),
    ]

    def _consolidate_merchant(desc: str) -> str:
        d = desc.lower()
        for display, keywords in _MERCHANT_GROUPS:
            if any(k in d for k in keywords):
                return display
        return desc  # keep original if no match

    consolidated = txn_raw.copy()
    consolidated["merchant_group"] = consolidated["description"].apply(_consolidate_merchant)

    merchant_totals = (
        consolidated.groupby("merchant_group")["amount"]
        .agg(["sum", "count"]).reset_index()
        .rename(columns={"merchant_group": "Merchant", "sum": "Total Spent ($)", "count": "# Txns"})
        .sort_values("Total Spent ($)", ascending=False).head(25)
    )

    st.caption("Similar merchants are grouped together (e.g. all Amazon orders → one row, both Vivian rent payments → one row).")
    display_m = merchant_totals.copy()
    display_m["Total Spent ($)"] = display_m["Total Spent ($)"].map("${:,.2f}".format)
    st.dataframe(display_m, use_container_width=True, hide_index=True)

# ── Bank Deposits / Credits ───────────────────────────────────────────────────
if not txn_all_raw.empty and "is_debit" in txn_all_raw.columns and (txn_all_raw["is_debit"] == 0).any():
    st.markdown("---")
    st.subheader("💰 Bank Deposits & Credits")
    st.caption("Payroll deposits and other credits from your NFCU statement — not counted as income or spending.")
    credits_raw = txn_all_raw[txn_all_raw["is_debit"] == 0].copy()
    credits_display = credits_raw[["date", "description", "amount", "month"]].sort_values("date", ascending=False).copy()
    credits_display.columns = ["Date", "Description", "Amount ($)", "Month"]
    credits_display["Amount ($)"] = credits_display["Amount ($)"].map("${:,.2f}".format)
    st.dataframe(credits_display, use_container_width=True, hide_index=True)

# ── Month-by-Month Detail Table ───────────────────────────────────────────────
st.markdown("---")
with st.expander("🗂️ View Month-by-Month Detail"):
    display = trends[["month_label", "income", "spent", "savings", "savings_rate"]].copy()
    display.columns = ["Month", "Income", "Spent", "Savings", "Savings Rate (%)"]

    def color_savings(val):
        if isinstance(val, (int, float)) and not pd.isna(val):
            return "color: #21c354" if val >= 0 else "color: #ff4b4b"
        return ""

    styled = display.style.format({
        "Income": "${:,.2f}", "Spent": "${:,.2f}",
        "Savings": "${:,.2f}", "Savings Rate (%)": "{:.1f}%",
    }).map(color_savings, subset=["Savings", "Savings Rate (%)"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

# ── AI Spending Insights (Pro only) ──────────────────────────────────────────
st.markdown("---")
st.subheader("🤖 AI Spending Insights")
st.caption("Claude analyzes your Navy Federal transaction history and gives you real, actionable feedback on your spending habits.")

from utils.auth import current_user_is_pro
if not current_user_is_pro():
    from utils.auth import PEACH, BG_CARD, BG_BORDER, TEXT_MUTED
    st.markdown(f"""
    <div class="paywall-card">
        <h2>🔒 Pro Feature</h2>
        <p>
            AI Spending Insights are available on <strong>Peach State Savings Pro</strong>.<br>
            Upgrade for $7/month to unlock Claude AI analysis of your spending habits.
        </p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Upgrade to Pro — $7/month", type="primary",
                     use_container_width=True, key="trends_upgrade_btn"):
            st.switch_page("pages/0_pricing.py")
elif not api_key:
    st.warning("🔑 No API key found. Add your Anthropic key on the **AI Insights** page to unlock this feature.")
else:
    def build_investment_context_str() -> str:
        inv_401k               = st.session_state.get("inv_401k", 0)
        inv_401k_contrib_ytd   = st.session_state.get("inv_401k_contrib_ytd", 0)
        inv_401k_employer_match = st.session_state.get("inv_401k_employer_match", 0)
        inv_roth               = st.session_state.get("inv_roth", 0)
        inv_roth_contrib_ytd   = st.session_state.get("inv_roth_contrib_ytd", 0)
        inv_hsa                = st.session_state.get("inv_hsa", 0)
        inv_hsa_contrib_ytd    = st.session_state.get("inv_hsa_contrib_ytd", 0)
        inv_brokerage          = st.session_state.get("inv_brokerage", 0)
        inv_notes              = st.session_state.get("inv_notes", "")
        if not any([inv_401k, inv_roth, inv_hsa, inv_brokerage]):
            return ""
        total_inv = inv_401k + inv_roth + inv_hsa + inv_brokerage
        lines = [
            "",
            "=== INVESTMENT & RETIREMENT ACCOUNTS (Fidelity / external) ===",
            f"Total Investment Portfolio: ${total_inv:,.2f}",
        ]
        if inv_401k > 0:
            lines.append(f"  401(k) Balance: ${inv_401k:,.2f}")
            if inv_401k_contrib_ytd > 0:
                lines.append(f"    YTD Employee Contributions: ${inv_401k_contrib_ytd:,.2f} (2025 limit: $23,500)")
            if inv_401k_employer_match > 0:
                lines.append(f"    YTD Employer Match: ${inv_401k_employer_match:,.2f}")
        if inv_roth > 0:
            lines.append(f"  Roth IRA Balance: ${inv_roth:,.2f}")
            if inv_roth_contrib_ytd > 0:
                remaining = max(0, 7000 - inv_roth_contrib_ytd)
                lines.append(f"    YTD Contributions: ${inv_roth_contrib_ytd:,.2f} (limit $7,000 — ${remaining:,.2f} remaining)")
        if inv_hsa > 0:
            lines.append(f"  HSA Balance: ${inv_hsa:,.2f}")
            if inv_hsa_contrib_ytd > 0:
                remaining = max(0, 4300 - inv_hsa_contrib_ytd)
                lines.append(f"    YTD Contributions: ${inv_hsa_contrib_ytd:,.2f} (limit $4,300 — ${remaining:,.2f} remaining)")
        if inv_brokerage > 0:
            lines.append(f"  Cash Management / High Yield: ${inv_brokerage:,.2f}")
        if inv_notes.strip():
            lines.append(f"  Notes: {inv_notes.strip()}")
        return "\n".join(lines)

    def build_trends_context() -> str:
        lines = []
        lines.append("=== IMPORTANT CONTEXT ===")
        lines.append("- 'Visa Technology Payroll' deposits ARE the user's primary income (bi-weekly paycheck)")
        lines.append("- 'ACH Paid To Darrian Belcher' = transfers to user's own Fidelity/savings accounts, NOT payments to another person")
        lines.append("- 'Transfer To Credit Card' = credit card payments, NOT discretionary spending")
        lines.append("- Transfers have been excluded from the spending totals below")
        lines.append("- Zelle/Apple Pay sends to Joshua/Xavier are Gardening labor/supply expenses")
        lines.append("")

        lines.append("=== OVERALL FINANCIAL SUMMARY ===")
        lines.append(f"Months of data: {len(trends)}")
        lines.append(f"Total income (manual entries): ${trends['income'].sum():,.2f}")
        lines.append(f"Total spending (debits, transfers excluded): ${trends['spent'].sum():,.2f}")
        lines.append(f"Total saved: ${trends['savings'].sum():,.2f}")
        if not pd.isna(avg_sr):
            lines.append(f"Average monthly savings rate: {avg_sr:.1f}%")
        if total_deposited > 0:
            lines.append(f"Total payroll/bank deposits (NFCU credits, not in income table): ${total_deposited:,.2f}")
        if total_transferred > 0:
            lines.append(f"Total transfers (credit card payments, account transfers): ${total_transferred:,.2f}")
        lines.append("")

        lines.append("=== MONTH-BY-MONTH BREAKDOWN ===")
        for _, row in trends.iterrows():
            sr = f"{row['savings_rate']:.1f}%" if not pd.isna(row['savings_rate']) else "N/A"
            dep = f", Payroll Deposits=${row['deposited']:,.2f}" if row.get('deposited', 0) > 0 else ""
            xfr = f", Transfers=${row['transferred']:,.2f}" if row.get('transferred', 0) > 0 else ""
            lines.append(f"{row['month_label']}: Income=${row['income']:,.2f}, Spent=${row['spent']:,.2f}, Saved=${row['savings']:,.2f}, Rate={sr}{dep}{xfr}")
        lines.append("")

        if not txn_cat_all.empty:
            lines.append("=== SPENDING BY CATEGORY (ALL TIME, TRANSFERS EXCLUDED) ===")
            cat_summary = txn_cat_all.groupby("category")["spent"].sum().sort_values(ascending=False)
            for cat, total in cat_summary.items():
                lines.append(f"  {cat}: ${total:,.2f}")
            lines.append("")

        if not txn_raw.empty:
            lines.append("=== TOP 15 MERCHANTS BY TOTAL SPEND ===")
            top_merchants = txn_raw.groupby("description")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False).head(15)
            for merchant, row in top_merchants.iterrows():
                lines.append(f"  {merchant}: ${row['sum']:,.2f} ({int(row['count'])} transactions)")
            lines.append("")

            lines.append("=== RECENT EXPENSES (LAST 30, TRANSFERS EXCLUDED) ===")
            for _, row in txn_raw.head(30).iterrows():
                cat_label = f" [{row['category']}]" if pd.notna(row.get('category')) and row.get('category') else ""
                lines.append(f"  {row['date']} | {row['description']}{cat_label} | ${row['amount']:,.2f}")

        # Payroll deposits
        if not txn_all_raw.empty and "is_debit" in txn_all_raw.columns:
            credits_ctx = txn_all_raw[txn_all_raw["is_debit"] == 0]
            if not credits_ctx.empty:
                lines.append("")
                lines.append("=== PAYROLL / BANK DEPOSITS (NFCU credits) ===")
                for _, row in credits_ctx.iterrows():
                    lines.append(f"  {row['date']} | {row['description']} | ${row['amount']:,.2f}")

        # Investment context
        inv_str = build_investment_context_str()
        if inv_str:
            lines.append(inv_str)

        return "\n".join(lines)

    INPUT_COST_PER_M  = 3.00
    OUTPUT_COST_PER_M = 15.00

    def ask_claude_trends(prompt: str, context: str) -> tuple[str, dict]:
        client = anthropic.Anthropic(api_key=api_key)
        try:
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1500,
                messages=[{"role": "user", "content": (
                    "You are a sharp, no-nonsense personal finance advisor analyzing real bank transaction data "
                    "from a Navy Federal Credit Union account. Be specific, use real numbers from the data, "
                    "and give genuinely useful advice — not generic platitudes.\n\n"
                    f"Here is the complete financial data:\n\n{context}\n\n"
                    f"User request: {prompt}\n\n"
                    "FORMATTING RULES:\n"
                    "- Write dollar amounts as 'USD X.XX' or '$X.XX'\n"
                    "- Use plain dashes (-) for bullet points\n"
                    "- No markdown headers (no # or **bold**)\n"
                    "- Be specific with numbers from the actual data\n"
                    "- Keep it under 300 words unless the question requires more detail"
                )}]
            )
            usage = message.usage
            cost = (usage.input_tokens / 1_000_000 * INPUT_COST_PER_M) + (usage.output_tokens / 1_000_000 * OUTPUT_COST_PER_M)
            return message.content[0].text, {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "cost_usd": cost}
        except anthropic.AuthenticationError:
            return "❌ Invalid API key. Check your key on the AI Insights page.", {}
        except anthropic.RateLimitError:
            return "❌ Rate limit hit. Wait a moment and try again.", {}
        except Exception as e:
            return f"❌ Error: {e}", {}

    def render_ai_response(text: str):
        st.text(text.replace("$", "＄"))

    def show_usage(usage_info: dict):
        if not usage_info:
            return
        with st.expander(f"📊 Token usage — ${usage_info['cost_usd']:.4f}", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("Input tokens",  f"{usage_info['input_tokens']:,}")
            c2.metric("Output tokens", f"{usage_info['output_tokens']:,}")
            c3.metric("Cost",          f"${usage_info['cost_usd']:.4f}")

    # Show investment context status
    _any_inv = any([st.session_state.get("inv_401k", 0), st.session_state.get("inv_roth", 0),
                    st.session_state.get("inv_hsa", 0), st.session_state.get("inv_brokerage", 0)])
    if _any_inv:
        total_inv = sum([st.session_state.get(k, 0) for k in ["inv_401k", "inv_roth", "inv_hsa", "inv_brokerage"]])
        st.info(f"📈 Investment context active — **${total_inv:,.2f}** tracked across 401k/Roth/HSA/Cash. Claude will include this in all analyses. Update balances on the **AI Insights** page.")
    else:
        st.caption("💡 Add your 401k/Roth IRA/HSA balances on the **AI Insights** page to include them in Claude's analysis.")

    context = build_trends_context()

    st.markdown("**Quick Insights — click any to generate:**")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Analyze My Spending Habits", type="primary", use_container_width=True, key="btn_habits"):
            with st.spinner("Claude is analyzing your spending patterns..."):
                response, usage = ask_claude_trends(
                    "Analyze my overall spending habits across all months. What are my biggest spending categories? "
                    "Where am I spending the most money? Are there any concerning patterns or trends month-over-month? "
                    "What does my spending say about my financial priorities?", context)
            st.markdown("#### 🔍 Spending Habits Analysis")
            render_ai_response(response)
            show_usage(usage)

        if st.button("📉 Where Am I Overspending?", type="secondary", use_container_width=True, key="btn_over"):
            with st.spinner("Finding overspending patterns..."):
                response, usage = ask_claude_trends(
                    "Look at my spending data and identify where I'm likely overspending. "
                    "Call out specific merchants or categories that stand out. "
                    "Give me 3-5 specific, actionable things I could cut back on with estimated savings.", context)
            st.markdown("#### 📉 Overspending Analysis")
            render_ai_response(response)
            show_usage(usage)

        if st.button("🏪 Top Merchant Breakdown", type="secondary", use_container_width=True, key="btn_merchants"):
            with st.spinner("Analyzing merchant spending..."):
                response, usage = ask_claude_trends(
                    "Break down my top merchants by spending. Which merchants am I visiting most frequently "
                    "and spending the most at? Any subscriptions or recurring charges I should review?", context)
            st.markdown("#### 🏪 Merchant Analysis")
            render_ai_response(response)
            show_usage(usage)

    with col2:
        if st.button("📈 Month-Over-Month Trends", type="primary", use_container_width=True, key="btn_mom"):
            with st.spinner("Analyzing monthly trends..."):
                response, usage = ask_claude_trends(
                    "Compare my spending month-over-month. Which months were my best and worst financially? "
                    "Is my spending trending up or down? What's driving the changes? What's my savings trajectory?", context)
            st.markdown("#### 📈 Month-Over-Month Analysis")
            render_ai_response(response)
            show_usage(usage)

        if st.button("💡 Personalized Savings Tips", type="secondary", use_container_width=True, key="btn_tips"):
            with st.spinner("Generating personalized tips..."):
                response, usage = ask_claude_trends(
                    "Based on my actual spending data, give me 5 specific, personalized tips to improve my savings rate. "
                    "Reference real merchants and categories — not generic advice. "
                    "For each tip, estimate how much I could save per month.", context)
            st.markdown("#### 💡 Personalized Savings Tips")
            render_ai_response(response)
            show_usage(usage)

        if st.button("🎯 Financial Health Score", type="secondary", use_container_width=True, key="btn_score"):
            with st.spinner("Calculating your financial health..."):
                response, usage = ask_claude_trends(
                    "Give me an honest financial health assessment. Score me on: savings rate, spending discipline, "
                    "category balance, investment progress, and overall trajectory. "
                    "Be direct — what am I doing well and what needs immediate attention? "
                    "End with one concrete action I should take this week.", context)
            st.markdown("#### 🎯 Financial Health Assessment")
            render_ai_response(response)
            show_usage(usage)

    st.markdown("---")
    st.markdown("**Ask a custom question about your spending trends:**")
    custom_q = st.text_area(
        "Your question",
        placeholder="e.g. 'How much did I spend on food across all months?' or 'Am I on track with my Roth IRA contributions?'",
        height=80, label_visibility="collapsed"
    )
    if st.button("Ask Claude", type="primary", key="btn_custom_ask") and custom_q.strip():
        with st.spinner("Thinking..."):
            response, usage = ask_claude_trends(custom_q.strip(), context)
        st.markdown("#### Claude's Answer")
        render_ai_response(response)
        show_usage(usage)
