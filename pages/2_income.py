import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_conn, seed_income, init_db, read_sql, execute
from utils.auth import require_password

st.set_page_config(page_title="Income", page_icon="💵", layout="wide", initial_sidebar_state="auto")
init_db()
require_password()

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
seed_income(selected_month)

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth",         icon="💎")
st.sidebar.page_link("pages/15_bills.py",         label="Bill Calendar",     icon="📅")
st.sidebar.page_link("pages/16_paycheck.py",      label="Paycheck Allocator",icon="💸")

st.title(f"💵 Income — {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")

conn = get_conn()
income_df = read_sql("SELECT * FROM income WHERE month = ?", conn, params=(selected_month,))
conn.close()

st.subheader("Income Sources")
edited = st.data_editor(
    income_df[['id', 'source', 'amount', 'notes']],
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
        "source": st.column_config.TextColumn("Source"),
        "amount": st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
        "notes": st.column_config.TextColumn("Notes"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="fixed"
)

if st.button("💾 Save Changes", type="primary"):
    conn = get_conn()
    for _, row in edited.iterrows():
        execute(conn, "UPDATE income SET source = ?, amount = ?, notes = ? WHERE id = ?",
                (row['source'], row['amount'], row['notes'], row['id']))
    conn.commit()
    conn.close()
    st.success("Saved!")
    st.rerun()

st.markdown("---")
with st.expander("➕ Add Income Source"):
    src = st.text_input("Source (e.g. RSU Vest, Freelance)")
    amt = st.number_input("Amount ($)", min_value=0.0, step=50.0)
    notes = st.text_input("Notes")
    if st.button("Add"):
        if src:
            conn = get_conn()
            execute(conn, "INSERT INTO income (month, source, amount, notes) VALUES (?, ?, ?, ?)",
                    (selected_month, src, amt, notes))
            conn.commit()
            conn.close()
            st.success("Added!")
            st.rerun()

st.markdown("---")
st.metric("Total Income This Month", f"${income_df['amount'].sum():,.2f}")
st.info("💡 Tip: Got an RSU vest or ESPP payout this month? Add it as a separate income source above so your monthly averages stay accurate.")
