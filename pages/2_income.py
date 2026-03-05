import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_conn, seed_income, init_db, read_sql, execute
from utils.auth import require_password, render_sidebar_brand, render_sidebar_nav, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Income", page_icon="🍑", layout="wide", initial_sidebar_state="auto")
init_db()
require_password()

# ── User isolation ─────────────────────────────────────────────────────────
_uid = st.session_state.get("user", {}).get("id", 0)

render_sidebar_brand()
months = []
for m in range(1, 13):
    months.append(datetime(2025, m, 1).strftime("%Y-%m"))
for m in range(1, 13):
    months.append(datetime(2026, m, 1).strftime("%Y-%m"))
current_month = datetime.now().strftime("%Y-%m")
default_idx = months.index(current_month) if current_month in months else 0
selected_month = st.sidebar.selectbox("📅 Month", months, index=default_idx)
seed_income(selected_month)

render_sidebar_nav()
render_sidebar_user_widget()

st.title(f"💵 Income — {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")

conn = get_conn()
income_df = read_sql("SELECT * FROM income WHERE month = ? AND user_id = ?", conn, params=(selected_month, _uid))
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
        execute(conn, "UPDATE income SET source = ?, amount = ?, notes = ? WHERE id = ? AND user_id = ?",
                (row['source'], row['amount'], row['notes'], row['id'], _uid))
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
            execute(conn, "INSERT INTO income (month, source, amount, notes, user_id) VALUES (?, ?, ?, ?, ?)",
                    (selected_month, src, amt, notes, _uid))
            conn.commit()
            conn.close()
            st.success("Added!")
            st.rerun()

st.markdown("---")
st.metric("Total Income This Month", f"${income_df['amount'].sum():,.2f}")
st.info("💡 Tip: Got an RSU vest or ESPP payout this month? Add it as a separate income source above so your monthly averages stay accurate.")
