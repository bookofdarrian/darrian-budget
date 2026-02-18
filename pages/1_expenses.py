import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_conn, seed_budget, init_db, read_sql, execute
from utils.auth import require_password

st.set_page_config(page_title="Expenses", page_icon="📋", layout="wide")
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
seed_budget(selected_month)

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")

st.title(f"📋 Expenses — {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")

# ── Auto-fill recurring expenses ─────────────────────────────────────────────
conn = get_conn()
templates_df = read_sql("SELECT * FROM recurring_templates WHERE active = 1", conn)
conn.close()

if not templates_df.empty:
    conn = get_conn()
    existing = read_sql("SELECT subcategory FROM expenses WHERE month = ?", conn, params=(selected_month,))
    conn.close()
    existing_subs = existing['subcategory'].tolist()
    new_recurring = templates_df[~templates_df['subcategory'].isin(existing_subs)]
    if not new_recurring.empty:
        conn = get_conn()
        for _, row in new_recurring.iterrows():
            execute(conn,
                "INSERT INTO expenses (month, category, subcategory, projected, actual) VALUES (?, ?, ?, ?, 0)",
                (selected_month, row['category'], row['subcategory'], row['projected'])
            )
        conn.commit()
        conn.close()
        st.toast(f"✅ Auto-filled {len(new_recurring)} recurring expense(s) for this month.")

# ── Load expenses ─────────────────────────────────────────────────────────────
conn = get_conn()
expense_df = read_sql(
    "SELECT * FROM expenses WHERE month = ? ORDER BY category, subcategory",
    conn, params=(selected_month,)
)
conn.close()

categories = expense_df['category'].unique().tolist()
selected_cat = st.selectbox("Filter by Category", ["All"] + categories)

filtered = expense_df[expense_df['category'] == selected_cat] if selected_cat != "All" else expense_df

# ── Editable table ────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Budget Table")
st.caption("Edit **Projected** to update your budget plan, or **Actual** to log spending. Hit Save when done.")

edit_cols = ['id', 'category', 'subcategory', 'projected', 'actual', 'notes']
display_df = filtered[edit_cols].copy()

edited = st.data_editor(
    display_df,
    column_config={
        "id":          st.column_config.NumberColumn("ID",           disabled=True, width="small"),
        "category":    st.column_config.TextColumn("Category",       disabled=True),
        "subcategory": st.column_config.TextColumn("Subcategory",    disabled=True),
        "projected":   st.column_config.NumberColumn("Projected ($)", format="$%.2f", min_value=0),
        "actual":      st.column_config.NumberColumn("Actual ($)",    format="$%.2f", min_value=0),
        "notes":       st.column_config.TextColumn("Notes"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="fixed"
)

if st.button("💾 Save Changes", type="primary"):
    conn = get_conn()
    for _, row in edited.iterrows():
        execute(conn,
            "UPDATE expenses SET projected = ?, actual = ?, notes = ? WHERE id = ?",
            (row['projected'], row['actual'], row['notes'], row['id'])
        )
    conn.commit()
    conn.close()
    st.success("Saved!")
    st.rerun()

st.markdown("---")

# ── Add a new custom expense row ─────────────────────────────────────────────
with st.expander("➕ Add Custom Expense"):
    col1, col2 = st.columns(2)
    with col1:
        new_cat = st.text_input("Category")
        new_sub = st.text_input("Subcategory")
    with col2:
        new_proj   = st.number_input("Projected ($)", min_value=0.0, step=10.0)
        new_actual = st.number_input("Actual ($)",    min_value=0.0, step=10.0)
    new_notes = st.text_input("Notes")
    save_as_recurring = st.checkbox("💾 Also save as a recurring template (auto-fills future months)")

    if st.button("Add Row"):
        if new_cat and new_sub:
            conn = get_conn()
            execute(conn,
                "INSERT INTO expenses (month, category, subcategory, projected, actual, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (selected_month, new_cat, new_sub, new_proj, new_actual, new_notes)
            )
            if save_as_recurring:
                existing_t = read_sql("SELECT id FROM recurring_templates WHERE subcategory = ?", conn, params=(new_sub,))
                if existing_t.empty:
                    execute(conn,
                        "INSERT INTO recurring_templates (category, subcategory, projected) VALUES (?, ?, ?)",
                        (new_cat, new_sub, new_proj)
                    )
            conn.commit()
            conn.close()
            st.success("Added!" + (" (saved as recurring)" if save_as_recurring else ""))
            st.rerun()
        else:
            st.error("Category and Subcategory are required.")

# ── Recurring templates manager ───────────────────────────────────────────────
with st.expander("🔁 Manage Recurring Expenses"):
    st.caption("These auto-fill into every new month. Toggle active/inactive or delete rows.")
    conn = get_conn()
    tmpl_df = read_sql("SELECT * FROM recurring_templates ORDER BY category, subcategory", conn)
    conn.close()

    if tmpl_df.empty:
        st.info("No recurring templates yet. Add one above by checking 'Save as recurring template'.")
    else:
        tmpl_edit = st.data_editor(
            tmpl_df[['id', 'category', 'subcategory', 'projected', 'active']],
            column_config={
                "id":          st.column_config.NumberColumn("ID",           disabled=True, width="small"),
                "category":    st.column_config.TextColumn("Category"),
                "subcategory": st.column_config.TextColumn("Subcategory"),
                "projected":   st.column_config.NumberColumn("Projected ($)", format="$%.2f", min_value=0),
                "active":      st.column_config.CheckboxColumn("Active"),
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )
        if st.button("💾 Save Recurring Templates"):
            conn = get_conn()
            for _, row in tmpl_edit.iterrows():
                execute(conn,
                    "UPDATE recurring_templates SET category=?, subcategory=?, projected=?, active=? WHERE id=?",
                    (row['category'], row['subcategory'], row['projected'], int(row['active']), row['id'])
                )
            conn.commit()
            conn.close()
            st.success("Recurring templates saved!")
            st.rerun()

# ── Summary footer ────────────────────────────────────────────────────────────
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Projected Total", f"${filtered['projected'].sum():,.2f}")
with col2:
    st.metric("Actual Total", f"${filtered['actual'].sum():,.2f}")
with col3:
    diff = filtered['actual'].sum() - filtered['projected'].sum()
    st.metric("Difference", f"${diff:,.2f}", delta_color="inverse")
