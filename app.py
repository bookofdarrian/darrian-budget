import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from utils.db import init_db, seed_budget, seed_income, get_conn

# ── App config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Darrian's Budget",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# ── Sidebar: Month selector ─────────────────────────────────────────────────
st.sidebar.title("💰 Budget Dashboard")
st.sidebar.markdown("---")

months = []
for m in range(1, 13):
    months.append(datetime(2025, m, 1).strftime("%Y-%m"))
for m in range(1, 13):
    months.append(datetime(2026, m, 1).strftime("%Y-%m"))

current_month = datetime.now().strftime("%Y-%m")
default_idx = months.index(current_month) if current_month in months else 0
selected_month = st.sidebar.selectbox("📅 Month", months, index=default_idx)

# Seed the selected month if needed
seed_budget(selected_month)
seed_income(selected_month)

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")

# ── Main dashboard ──────────────────────────────────────────────────────────
st.title(f"📊 Overview — {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")

conn = get_conn()

# Income summary
income_df = pd.read_sql("SELECT * FROM income WHERE month = ?", conn, params=(selected_month,))
total_income = income_df['amount'].sum()

# Expense summary
expense_df = pd.read_sql("SELECT * FROM expenses WHERE month = ?", conn, params=(selected_month,))
total_projected = expense_df['projected'].sum()
total_actual = expense_df['actual'].sum()

conn.close()

# ── KPI Cards ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💵 Total Income", f"${total_income:,.2f}")

with col2:
    st.metric("📋 Projected Expenses", f"${total_projected:,.2f}")

with col3:
    actual_color = "normal"
    st.metric("💳 Actual Expenses", f"${total_actual:,.2f}", delta=f"${total_actual - total_projected:,.2f} vs projected", delta_color="inverse")

with col4:
    balance = total_income - total_actual
    st.metric("🏦 Remaining", f"${balance:,.2f}", delta_color="normal")

st.markdown("---")

# ── Spending by category ─────────────────────────────────────────────────────
st.subheader("Spending by Category")

if not expense_df.empty:
    cat_summary = expense_df.groupby("category")[["projected", "actual"]].sum().reset_index()
    cat_summary["difference"] = cat_summary["actual"] - cat_summary["projected"]
    cat_summary.columns = ["Category", "Projected", "Actual", "Difference"]

    def color_diff(val):
        if val > 0:
            return "color: #ff4b4b"
        elif val < 0:
            return "color: #21c354"
        return ""

    styled = cat_summary.style\
        .format({"Projected": "${:,.2f}", "Actual": "${:,.2f}", "Difference": "${:,.2f}"})\
        .map(color_diff, subset=["Difference"])

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Bar chart
    st.subheader("Projected vs Actual by Category")
    chart_data = cat_summary.set_index("Category")[["Projected", "Actual"]]
    st.bar_chart(chart_data)
else:
    st.info("No expense data yet for this month.")

# ── Budget health ────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Budget Health")

if total_income > 0:
    pct_spent = (total_actual / total_income) * 100
    st.progress(min(pct_spent / 100, 1.0), text=f"{pct_spent:.1f}% of income spent")

    col1, col2 = st.columns(2)
    with col1:
        savings_rate = ((total_income - total_actual) / total_income) * 100
        st.metric("Savings Rate", f"{savings_rate:.1f}%", help="% of income not yet spent this month")
    with col2:
        overage_cats = cat_summary[cat_summary["Difference"] > 0]["Category"].tolist()
        if overage_cats:
            st.warning(f"Over budget in: {', '.join(overage_cats)}")
        else:
            st.success("On track — no categories over budget!")
