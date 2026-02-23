import streamlit as st
import pandas as pd
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.db import init_db, seed_budget, seed_income, get_conn, read_sql, execute as db_execute
from utils.auth import (
    require_login, render_sidebar_brand, render_sidebar_user_widget,
    inject_css, get_current_user
)

# ── App config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()
inject_css()

# ── Handle Stripe checkout return ─────────────────────────────────────────────
# This runs AFTER require_login so we have a valid user session to upgrade.
require_login()

_params = st.query_params
if _params.get("checkout") == "success":
    _session_id = _params.get("session_id", "")
    _user       = st.session_state.get("user", {})
    _user_id    = _user.get("id", 0)
    _user_email = _user.get("email", "")

    # ── Polling: activate Pro immediately without a webhook server ────────────
    _activated = False
    if _session_id and _user_id and _user_email:
        from utils.stripe_utils import poll_checkout_and_activate
        _activated = poll_checkout_and_activate(_session_id, _user_id, _user_email)

    # Fallback: if session_id was missing, try to find the latest paid session
    if not _activated and _user_id and _user_email:
        from utils.stripe_utils import get_latest_checkout_session_for_user, poll_checkout_and_activate
        _fallback_sid = get_latest_checkout_session_for_user(_user_email, _user_id)
        if _fallback_sid:
            _activated = poll_checkout_and_activate(_fallback_sid, _user_id, _user_email)

    # Refresh the session state so the UI reflects Pro immediately
    if _activated:
        from utils.db import get_user_by_id
        _fresh = get_user_by_id(_user_id)
        if _fresh:
            _fresh.pop("password_hash", None)
            _fresh.pop("salt", None)
            st.session_state["user"] = _fresh

    st.balloons()
    if _activated:
        st.success("🎉 Welcome to Peach Savings Pro! Your subscription is now active.")
        st.markdown("### You're all set! 🍑")
        st.markdown(
            "Your Pro plan is **live right now** — AI Insights, Net Worth tracking, "
            "Monthly Trends, and all Pro features are unlocked. Use the sidebar to explore."
        )
    else:
        # Payment went through but polling couldn't confirm yet (rare edge case)
        st.success("🎉 Payment received! Your Pro plan will activate within a minute.")
        st.markdown(
            "If Pro features aren't visible yet, refresh the page in a moment. "
            "Your payment was successful."
        )
    st.query_params.clear()

elif _params.get("checkout") == "cancelled":
    st.info("Checkout cancelled — no charge was made. You can upgrade anytime.")
    st.query_params.clear()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()

months = []
for m in range(1, 13):
    months.append(datetime(2025, m, 1).strftime("%Y-%m"))
for m in range(1, 13):
    months.append(datetime(2026, m, 1).strftime("%Y-%m"))

current_month = datetime.now().strftime("%Y-%m")
default_idx = months.index(current_month) if current_month in months else 0
selected_month = st.sidebar.selectbox("📅 Month", months, index=default_idx)

seed_budget(selected_month)
seed_income(selected_month)

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights 🔒",    icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth 🔒",      icon="💎")
st.sidebar.page_link("pages/0_pricing.py",        label="⭐ Upgrade to Pro", icon="⭐")

render_sidebar_user_widget()

# ── Main dashboard ────────────────────────────────────────────────────────────
st.title(f"📊 Overview — {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")

conn = get_conn()

income_df      = read_sql("SELECT * FROM income WHERE month = ?", conn, params=(selected_month,))
total_income   = income_df['amount'].sum()

expense_df     = read_sql("SELECT * FROM expenses WHERE month = ?", conn, params=(selected_month,))
total_projected = expense_df['projected'].sum()
total_actual    = expense_df['actual'].sum()

_c = db_execute(conn, "SELECT SUM(amount) FROM income")
at_income_manual = float(_c.fetchone()[0] or 0)

_c = db_execute(conn, "SELECT SUM(amount) FROM bank_transactions WHERE is_debit = 0")
at_deposits = float(_c.fetchone()[0] or 0)

_c = db_execute(conn, """
    SELECT SUM(amount) FROM bank_transactions
    WHERE (is_debit = 1 OR is_debit IS NULL)
    AND (category IS NULL OR category != 'Transfer')
""")
at_spent = float(_c.fetchone()[0] or 0)
conn.close()

at_income_total = at_income_manual + at_deposits
at_saved        = at_income_total - at_spent

# ── Two-panel layout ──────────────────────────────────────────────────────────
left_col, right_col = st.columns(2, gap="large")

with left_col:
    st.markdown("#### 📅 This Month")
    m1, m2 = st.columns(2)
    m1.metric("💵 Income",    f"${total_income:,.2f}")
    m2.metric("📋 Projected", f"${total_projected:,.2f}")

    m3, m4 = st.columns(2)
    m3.metric(
        "💳 Actual Spent",
        f"${total_actual:,.2f}",
        delta=f"${total_actual - total_projected:,.2f} vs projected",
        delta_color="inverse"
    )
    balance = total_income - total_actual
    m4.metric("🏦 Remaining", f"${balance:,.2f}")

with right_col:
    st.markdown("#### 🗂️ All-Time")
    a1, a2 = st.columns(2)
    a1.metric("💵 Total Earned", f"${at_income_total:,.2f}",
              help="All manual income entries + bank deposit credits")
    a2.metric("💳 Total Spent",  f"${at_spent:,.2f}",
              help="All bank debits, transfers excluded")

    a3, a4 = st.columns(2)
    a3.metric("🏦 Net Saved", f"${at_saved:,.2f}")
    if at_income_total > 0:
        at_savings_pct = (at_saved / at_income_total) * 100
        a4.metric("📈 Savings Rate", f"{at_savings_pct:.1f}%",
                  help="All-time: % of total earned that was saved")
    else:
        a4.metric("📈 Savings Rate", "—")

st.markdown("---")

if total_income > 0:
    pct_spent = (total_actual / total_income) * 100
    st.progress(min(pct_spent / 100, 1.0),
                text=f"{pct_spent:.1f}% of this month's income spent")

st.markdown("---")

st.subheader("Spending by Category")

if not expense_df.empty:
    cat_summary = expense_df.groupby("category")[["projected", "actual"]].sum().reset_index()
    cat_summary["difference"] = cat_summary["actual"] - cat_summary["projected"]
    cat_summary.columns = ["Category", "Projected", "Actual", "Difference"]

    def color_diff(val):
        if val > 0:   return "color: #ff4b4b"
        elif val < 0: return "color: #21c354"
        return ""

    styled = cat_summary.style\
        .format({"Projected": "${:,.2f}", "Actual": "${:,.2f}", "Difference": "${:,.2f}"})\
        .map(color_diff, subset=["Difference"])

    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.subheader("Projected vs Actual by Category")
    chart_data = cat_summary.set_index("Category")[["Projected", "Actual"]]
    st.bar_chart(chart_data)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if total_income > 0:
            savings_rate = ((total_income - total_actual) / total_income) * 100
            st.metric("Monthly Savings Rate", f"{savings_rate:.1f}%",
                      help="% of this month's income not yet spent")
    with col2:
        overage_cats = cat_summary[cat_summary["Difference"] > 0]["Category"].tolist()
        if overage_cats:
            st.warning(f"Over budget in: {', '.join(overage_cats)}")
        else:
            st.success("On track — no categories over budget!")
else:
    st.info("No expense data yet for this month.")
