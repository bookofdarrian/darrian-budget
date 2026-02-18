import streamlit as st
import pandas as pd
import base64
import os
from datetime import datetime
from utils.db import get_conn, init_db

st.set_page_config(page_title="Receipts & HSA", page_icon="🧾", layout="wide")
init_db()

# ── Sidebar ──────────────────────────────────────────────────────────────────
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

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")

st.title("🧾 Receipts & HSA")

# ── Tabs: General Receipts vs HSA ─────────────────────────────────────────────
tab_expense, tab_hsa = st.tabs(["🧾 Expense Receipts", "🏥 HSA Medical Receipts"])


# ════════════════════════════════════════════════════════════════════════════
# Shared helper: render a receipt card
# ════════════════════════════════════════════════════════════════════════════
def render_receipt_card(row, receipt_type: str):
    """Render a single receipt as a card with image preview and delete button."""
    with st.container(border=True):
        c1, c2 = st.columns([2, 3])
        with c1:
            if row['image_data']:
                try:
                    img_bytes = bytes(row['image_data'])
                    b64 = base64.b64encode(img_bytes).decode()
                    # Detect format from filename
                    fname = (row['filename'] or "receipt.jpg").lower()
                    mime = "image/png" if fname.endswith(".png") else "image/jpeg"
                    st.markdown(
                        f'<img src="data:{mime};base64,{b64}" style="width:100%;border-radius:8px;"/>',
                        unsafe_allow_html=True
                    )
                except Exception:
                    st.caption("⚠️ Could not render image")
            else:
                st.markdown(
                    '<div style="background:#f0f0f0;border-radius:8px;padding:40px;text-align:center;color:#888;">📄 No image</div>',
                    unsafe_allow_html=True
                )
        with c2:
            st.markdown(f"**{row['merchant']}**")
            st.markdown(f"💰 **${row['amount']:,.2f}**")
            st.markdown(f"📅 {row['date']}  |  🗂️ {row['category']}")
            if row['notes']:
                st.caption(f"📝 {row['notes']}")
            st.caption(f"Added: {row['created_at'][:10] if row['created_at'] else '—'}")
            if st.button("🗑️ Delete", key=f"del_{receipt_type}_{row['id']}"):
                conn = get_conn()
                conn.execute("DELETE FROM receipts WHERE id=?", (row['id'],))
                conn.commit()
                conn.close()
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# Shared helper: upload form
# ════════════════════════════════════════════════════════════════════════════
def receipt_upload_form(receipt_type: str, category_default: str = ""):
    """Render the upload / snap form and return True if a receipt was saved."""
    st.subheader("📸 Add a Receipt")
    st.caption("Take a photo with your phone camera or upload an image/PDF from your device.")

    c1, c2 = st.columns(2)
    with c1:
        r_date     = st.date_input("Date", value=datetime.today(), key=f"date_{receipt_type}")
        r_merchant = st.text_input("Merchant / Provider", key=f"merchant_{receipt_type}")
    with c2:
        r_amount   = st.number_input("Amount ($)", min_value=0.0, step=0.01, key=f"amount_{receipt_type}")
        r_category = st.text_input("Category", value=category_default, key=f"cat_{receipt_type}")
    r_notes = st.text_input("Notes (optional)", key=f"notes_{receipt_type}")

    r_file = st.file_uploader(
        "📎 Attach receipt image (JPG, PNG) or PDF",
        type=["jpg", "jpeg", "png", "pdf"],
        key=f"file_{receipt_type}",
        help="On mobile, your browser will offer the camera as an option."
    )

    # Live preview
    if r_file and r_file.type.startswith("image/"):
        st.image(r_file, caption="Preview", use_container_width=True)

    if st.button("💾 Save Receipt", type="primary", key=f"save_{receipt_type}"):
        if not r_merchant:
            st.error("Merchant / Provider is required.")
            return False
        if not r_category:
            st.error("Category is required.")
            return False

        image_data = None
        filename   = None
        if r_file:
            image_data = r_file.read()
            filename   = r_file.name

        conn = get_conn()
        conn.execute(
            """INSERT INTO receipts
               (month, date, merchant, amount, category, receipt_type, filename, image_data, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (selected_month, str(r_date), r_merchant, r_amount,
             r_category, receipt_type, filename, image_data, r_notes)
        )
        conn.commit()
        conn.close()
        st.success("Receipt saved! ✅")
        st.rerun()
    return False


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — General Expense Receipts
# ════════════════════════════════════════════════════════════════════════════
with tab_expense:
    st.markdown(
        "Store receipts for any expense — groceries, dining, subscriptions, etc. "
        "Great for tracking and reconciling with your budget."
    )

    receipt_upload_form("expense")

    st.markdown("---")
    st.subheader(f"Saved Receipts — {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")

    # Filter controls
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        show_all_months_exp = st.checkbox("Show all months", key="all_months_exp")
    with fc2:
        search_exp = st.text_input("🔍 Search merchant", key="search_exp")

    conn = get_conn()
    if show_all_months_exp:
        receipts_exp = pd.read_sql(
            "SELECT * FROM receipts WHERE receipt_type='expense' ORDER BY date DESC", conn
        )
    else:
        receipts_exp = pd.read_sql(
            "SELECT * FROM receipts WHERE receipt_type='expense' AND month=? ORDER BY date DESC",
            conn, params=(selected_month,)
        )
    conn.close()

    if search_exp:
        receipts_exp = receipts_exp[
            receipts_exp['merchant'].str.contains(search_exp, case=False, na=False)
        ]

    if receipts_exp.empty:
        st.info("No expense receipts yet for this period. Add one above.")
    else:
        # Summary metrics
        m1, m2 = st.columns(2)
        m1.metric("Total Receipts", len(receipts_exp))
        m2.metric("Total Amount", f"${receipts_exp['amount'].sum():,.2f}")

        st.markdown("---")
        for _, row in receipts_exp.iterrows():
            render_receipt_card(row, "expense")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — HSA Medical Receipts
# ════════════════════════════════════════════════════════════════════════════
with tab_hsa:
    st.markdown("""
### 🏥 HSA Receipt Vault
Store medical receipts for HSA reimbursement. The IRS recommends keeping these for **at least 3 years**.
This vault keeps them organized by month and lets you track your total reimbursable expenses.
    """)

    with st.expander("ℹ️ What qualifies for HSA reimbursement?", expanded=False):
        st.markdown("""
**Common HSA-eligible expenses:**
- Doctor visits & co-pays
- Prescriptions & OTC medications (since 2020)
- Dental care (cleanings, fillings, orthodontia)
- Vision care (glasses, contacts, eye exams)
- Mental health therapy
- Lab tests & imaging
- Medical equipment (crutches, blood pressure monitors)
- Chiropractic care

> 💡 Always save the itemized receipt (not just the credit card slip) for IRS documentation.
        """)

    receipt_upload_form("hsa", category_default="Medical")

    st.markdown("---")
    st.subheader("HSA Receipt Vault")

    # Filter controls
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        show_all_months_hsa = st.checkbox("Show all months", key="all_months_hsa")
    with fc2:
        search_hsa = st.text_input("🔍 Search provider", key="search_hsa")

    conn = get_conn()
    if show_all_months_hsa:
        receipts_hsa = pd.read_sql(
            "SELECT * FROM receipts WHERE receipt_type='hsa' ORDER BY date DESC", conn
        )
    else:
        receipts_hsa = pd.read_sql(
            "SELECT * FROM receipts WHERE receipt_type='hsa' AND month=? ORDER BY date DESC",
            conn, params=(selected_month,)
        )
    conn.close()

    if search_hsa:
        receipts_hsa = receipts_hsa[
            receipts_hsa['merchant'].str.contains(search_hsa, case=False, na=False)
        ]

    if receipts_hsa.empty:
        st.info("No HSA receipts yet. Add your first medical receipt above.")
    else:
        # HSA summary metrics
        h1, h2, h3 = st.columns(3)
        h1.metric("Total Receipts", len(receipts_hsa))
        h2.metric("Total Reimbursable", f"${receipts_hsa['amount'].sum():,.2f}")

        # Year-to-date if showing all months
        if show_all_months_hsa:
            current_year = datetime.now().strftime("%Y")
            ytd = receipts_hsa[receipts_hsa['month'].str.startswith(current_year)]
            h3.metric(f"{current_year} YTD", f"${ytd['amount'].sum():,.2f}")
        else:
            h3.metric("This Month", f"${receipts_hsa['amount'].sum():,.2f}")

        st.markdown("---")

        # Category breakdown
        if len(receipts_hsa) > 1:
            with st.expander("📊 Breakdown by Category"):
                cat_breakdown = receipts_hsa.groupby("category")["amount"].sum().reset_index()
                cat_breakdown.columns = ["Category", "Total ($)"]
                cat_breakdown = cat_breakdown.sort_values("Total ($)", ascending=False)
                st.dataframe(
                    cat_breakdown.style.format({"Total ($)": "${:,.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )

        st.markdown("---")
        for _, row in receipts_hsa.iterrows():
            render_receipt_card(row, "hsa")

    # ── Export HSA receipts as CSV ────────────────────────────────────────────
    if not receipts_hsa.empty:
        st.markdown("---")
        with st.expander("📥 Export HSA Records"):
            export_df = receipts_hsa[['date', 'merchant', 'amount', 'category', 'notes', 'month']].copy()
            export_df.columns = ['Date', 'Provider', 'Amount', 'Category', 'Notes', 'Month']
            csv_bytes = export_df.to_csv(index=False).encode()
            st.download_button(
                label="⬇️ Download HSA Records as CSV",
                data=csv_bytes,
                file_name=f"hsa_receipts_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
