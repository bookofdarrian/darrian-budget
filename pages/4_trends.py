import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_conn, init_db, read_sql
from utils.auth import require_password

st.set_page_config(page_title="Monthly Trends", page_icon="📈", layout="wide")
init_db()
require_password()

st.sidebar.title("💰 Budget Dashboard")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")

st.title("📈 Monthly Trends")
st.caption("Track your income, spending, and savings rate across every month you've recorded data.")

# ── DEBUG: show raw DB at top so it's always visible ─────────────────────────
with st.expander("🔍 Debug: Raw database contents", expanded=True):
    _conn = get_conn()
    _txn = read_sql("SELECT month, COUNT(*) as txns, SUM(amount) as total FROM bank_transactions GROUP BY month ORDER BY month", _conn)
    _inc = read_sql("SELECT month, SUM(amount) as income FROM income GROUP BY month ORDER BY month", _conn)
    _conn.close()
    st.write("**bank_transactions by month:**", _txn if not _txn.empty else "EMPTY")
    st.write("**income by month:**", _inc if not _inc.empty else "EMPTY")

conn = get_conn()
income_all  = read_sql("SELECT month, SUM(amount) AS income FROM income GROUP BY month", conn)
expense_all = read_sql("SELECT month, SUM(projected) AS projected, SUM(actual) AS actual FROM expenses GROUP BY month", conn)

# Pull actual spending from bank_transactions — sum by month (this is the primary source of actuals)
txn_all = read_sql("SELECT month, SUM(amount) AS txn_actual FROM bank_transactions GROUP BY month", conn)

# Pull category breakdown from bank_transactions for the category chart
txn_cat_all = read_sql(
    "SELECT month, category, SUM(amount) AS actual FROM bank_transactions "
    "WHERE category IS NOT NULL AND category != '' GROUP BY month, category", conn
)
conn.close()

if income_all.empty and expense_all.empty and txn_all.empty:
    st.info("No data yet — visit the Expenses and Income pages to enter some numbers first.")
    st.stop()

# Build a unified month list from ALL sources
all_months = set()
if not income_all.empty:
    all_months.update(income_all["month"].tolist())
if not expense_all.empty:
    all_months.update(expense_all["month"].tolist())
if not txn_all.empty:
    all_months.update(txn_all["month"].tolist())

month_base = pd.DataFrame(sorted(all_months), columns=["month"])

# Merge all sources onto the full month list using outer joins
trends = month_base.copy()
if not income_all.empty:
    trends = pd.merge(trends, income_all, on="month", how="left")
else:
    trends["income"] = 0.0

if not expense_all.empty:
    trends = pd.merge(trends, expense_all, on="month", how="left")
else:
    trends["projected"] = 0.0
    trends["actual"] = 0.0

trends = trends.fillna(0)

# Merge in bank transaction actuals — use txn total when available, fall back to expense actual
if not txn_all.empty:
    trends = pd.merge(trends, txn_all, on="month", how="left")
    trends["actual"] = trends.apply(
        lambda r: r["txn_actual"] if pd.notna(r.get("txn_actual")) and r["txn_actual"] > 0 else r["actual"],
        axis=1
    )
    trends.drop(columns=["txn_actual"], inplace=True)

trends = trends.sort_values("month").reset_index(drop=True)
trends["savings"]      = trends["income"] - trends["actual"]
trends["savings_rate"] = (trends["savings"] / trends["income"].replace(0, float("nan"))) * 100
trends["month_label"]  = trends["month"].apply(lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y"))

st.subheader("All-Time Summary")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Income",    f"${trends['income'].sum():,.2f}")
k2.metric("Total Spent",     f"${trends['actual'].sum():,.2f}")
k3.metric("Total Saved",     f"${trends['savings'].sum():,.2f}")
avg_sr = trends["savings_rate"].mean()
k4.metric("Avg Savings Rate", f"{avg_sr:.1f}%" if not pd.isna(avg_sr) else "—")

st.markdown("---")
st.subheader("Income vs. Actual Spending by Month")
chart_df = trends.set_index("month_label")[["income", "actual", "projected"]].copy()
chart_df.columns = ["Income", "Actual Spent", "Projected"]
st.bar_chart(chart_df, use_container_width=True)

st.markdown("---")
st.subheader("Monthly Savings (Income − Actual)")
savings_chart = trends.set_index("month_label")[["savings"]].copy()
savings_chart.columns = ["Savings"]
st.line_chart(savings_chart, use_container_width=True)

st.markdown("---")
st.subheader("Savings Rate % by Month")
sr_chart = trends.set_index("month_label")[["savings_rate"]].copy()
sr_chart.columns = ["Savings Rate (%)"]
st.line_chart(sr_chart, use_container_width=True)

st.markdown("---")
st.subheader("Spending by Category — All Months")
conn = get_conn()
cat_all = read_sql("SELECT month, category, SUM(actual) AS actual FROM expenses GROUP BY month, category", conn)
conn.close()

# Merge expense categories with bank transaction categories
if not txn_cat_all.empty:
    if not cat_all.empty:
        # Combine both sources — prefer txn data where it exists
        combined_cat = pd.concat([cat_all, txn_cat_all], ignore_index=True)
        combined_cat = combined_cat.groupby(["month", "category"])["actual"].sum().reset_index()
    else:
        combined_cat = txn_cat_all.rename(columns={"actual": "actual"})
else:
    combined_cat = cat_all

if not combined_cat.empty:
    cat_pivot = combined_cat.pivot_table(index="month", columns="category", values="actual", aggfunc="sum").fillna(0)
    cat_pivot.index = cat_pivot.index.map(lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y"))
    st.bar_chart(cat_pivot, use_container_width=True)
else:
    st.info("No category data yet.")

st.markdown("---")
with st.expander("🔍 Debug: What's in the database?", expanded=True):
    conn = get_conn()
    txn_months = read_sql("SELECT month, COUNT(*) as txn_count, SUM(amount) as total FROM bank_transactions GROUP BY month ORDER BY month", conn)
    inc_months = read_sql("SELECT month, SUM(amount) as income FROM income GROUP BY month ORDER BY month", conn)
    exp_months = read_sql("SELECT month, SUM(actual) as actual FROM expenses GROUP BY month ORDER BY month", conn)
    conn.close()
    st.markdown("**Bank Transactions by month:**")
    if txn_months.empty:
        st.warning("No bank transactions found at all!")
    else:
        st.dataframe(txn_months, use_container_width=True, hide_index=True)
    st.markdown("**Income by month:**")
    st.dataframe(inc_months, use_container_width=True, hide_index=True)
    st.markdown("**Expenses actual by month:**")
    st.dataframe(exp_months, use_container_width=True, hide_index=True)

st.markdown("---")
with st.expander("🗂️ View Raw Monthly Data"):
    display = trends[["month_label", "income", "projected", "actual", "savings", "savings_rate"]].copy()
    display.columns = ["Month", "Income", "Projected", "Actual Spent", "Savings", "Savings Rate (%)"]

    def color_savings(val):
        if isinstance(val, float) and not pd.isna(val):
            return "color: #21c354" if val >= 0 else "color: #ff4b4b"
        return ""

    styled = display.style\
        .format({"Income": "${:,.2f}", "Projected": "${:,.2f}", "Actual Spent": "${:,.2f}",
                 "Savings": "${:,.2f}", "Savings Rate (%)": "{:.1f}%"})\
        .map(color_savings, subset=["Savings", "Savings Rate (%)"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
