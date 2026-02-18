import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_conn, init_db

st.set_page_config(page_title="Monthly Trends", page_icon="📈", layout="wide")
init_db()

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

# ── Pull all months that have data ───────────────────────────────────────────
conn = get_conn()

income_all  = pd.read_sql("SELECT month, SUM(amount) AS income  FROM income   GROUP BY month", conn)
expense_all = pd.read_sql(
    "SELECT month, SUM(projected) AS projected, SUM(actual) AS actual FROM expenses GROUP BY month", conn
)
conn.close()

if income_all.empty and expense_all.empty:
    st.info("No data yet — visit the Expenses and Income pages to enter some numbers first.")
    st.stop()

# Merge on month (outer so months with only one side still show)
trends = pd.merge(income_all, expense_all, on="month", how="outer").fillna(0)
trends = trends.sort_values("month").reset_index(drop=True)
trends["savings"]      = trends["income"] - trends["actual"]
trends["savings_rate"] = (trends["savings"] / trends["income"].replace(0, float("nan"))) * 100
trends["month_label"]  = trends["month"].apply(
    lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y")
)

# ── KPI summary row (all-time) ───────────────────────────────────────────────
st.subheader("All-Time Summary")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Income",    f"${trends['income'].sum():,.2f}")
k2.metric("Total Spent",     f"${trends['actual'].sum():,.2f}")
k3.metric("Total Saved",     f"${trends['savings'].sum():,.2f}")
avg_sr = trends["savings_rate"].mean()
k4.metric("Avg Savings Rate", f"{avg_sr:.1f}%" if not pd.isna(avg_sr) else "—")

st.markdown("---")

# ── Income vs Actual Spending chart ─────────────────────────────────────────
st.subheader("Income vs. Actual Spending by Month")

chart_df = trends.set_index("month_label")[["income", "actual", "projected"]].copy()
chart_df.columns = ["Income", "Actual Spent", "Projected"]
st.bar_chart(chart_df, use_container_width=True)

st.markdown("---")

# ── Savings over time ────────────────────────────────────────────────────────
st.subheader("Monthly Savings (Income − Actual)")

savings_chart = trends.set_index("month_label")[["savings"]].copy()
savings_chart.columns = ["Savings"]
st.line_chart(savings_chart, use_container_width=True)

st.markdown("---")

# ── Savings rate over time ───────────────────────────────────────────────────
st.subheader("Savings Rate % by Month")

sr_chart = trends.set_index("month_label")[["savings_rate"]].copy()
sr_chart.columns = ["Savings Rate (%)"]
st.line_chart(sr_chart, use_container_width=True)

st.markdown("---")

# ── Category breakdown over time ─────────────────────────────────────────────
st.subheader("Spending by Category — All Months")

conn = get_conn()
cat_all = pd.read_sql(
    "SELECT month, category, SUM(actual) AS actual FROM expenses GROUP BY month, category",
    conn
)
conn.close()

if not cat_all.empty:
    # Pivot: rows = month, cols = category
    cat_pivot = cat_all.pivot_table(index="month", columns="category", values="actual", aggfunc="sum").fillna(0)
    cat_pivot.index = cat_pivot.index.map(lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y"))
    st.bar_chart(cat_pivot, use_container_width=True)
else:
    st.info("No category data yet.")

st.markdown("---")

# ── Raw data table ───────────────────────────────────────────────────────────
with st.expander("🗂️ View Raw Monthly Data"):
    display = trends[["month_label", "income", "projected", "actual", "savings", "savings_rate"]].copy()
    display.columns = ["Month", "Income", "Projected", "Actual Spent", "Savings", "Savings Rate (%)"]

    def color_savings(val):
        if isinstance(val, float) and not pd.isna(val):
            return "color: #21c354" if val >= 0 else "color: #ff4b4b"
        return ""

    styled = display.style\
        .format({
            "Income":        "${:,.2f}",
            "Projected":     "${:,.2f}",
            "Actual Spent":  "${:,.2f}",
            "Savings":       "${:,.2f}",
            "Savings Rate (%)": "{:.1f}%",
        })\
        .map(color_savings, subset=["Savings", "Savings Rate (%)"])

    st.dataframe(styled, use_container_width=True, hide_index=True)
