import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils.db import get_conn, init_db
from utils.nfcu_parser import parse_nfcu_pdf

st.set_page_config(page_title="Bank Import", page_icon="🏦", layout="wide")
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

st.title("🏦 Bank Import")
st.caption(
    "Upload your Navy Federal PDF statement or any bank CSV to pull in transactions. "
    "Then map each one to a budget category and apply to your actuals."
)

# ── Helper: load categories for this month ────────────────────────────────────
conn = get_conn()
expense_df = pd.read_sql(
    "SELECT id, category, subcategory FROM expenses WHERE month = ?",
    conn, params=(selected_month,)
)
conn.close()

cat_options = ["— Uncategorized —"] + [
    f"{r['category']} › {r['subcategory']}" for _, r in expense_df.iterrows()
]

# ── Tab layout ────────────────────────────────────────────────────────────────
tab_nfcu, tab_csv, tab_manual, tab_review = st.tabs([
    "🏛️ Navy Federal PDF", "📂 Other Bank CSV", "✏️ Add Manually", "📋 Review & Apply"
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Navy Federal PDF Import
# ════════════════════════════════════════════════════════════════════════════
with tab_nfcu:
    st.subheader("Import Navy Federal Statement (PDF)")

    with st.expander("ℹ️ How to download your NFCU statement", expanded=False):
        st.markdown("""
1. Log in at **navyfederal.org** or the Navy Federal app
2. Go to **Accounts** → select your checking account
3. Click **Statements** in the left menu
4. Choose the statement month and click **Download** (PDF)
5. Upload the PDF below — all accounts in the statement will be parsed automatically

> 💡 The parser reads your Campus Checking, e-Checking, and Membership Savings transactions.
> Deposits (payroll, transfers in) are shown but not imported as expenses.
        """)

    nfcu_file = st.file_uploader(
        "Upload Navy Federal PDF statement",
        type=["pdf"],
        key="nfcu_pdf"
    )

    if nfcu_file:
        try:
            with st.spinner("Parsing PDF..."):
                pdf_bytes = nfcu_file.read()
                txns = parse_nfcu_pdf(io.BytesIO(pdf_bytes))

            if not txns:
                st.error("No transactions found. Make sure this is a Navy Federal statement PDF.")
            else:
                debits  = [t for t in txns if t['is_debit']]
                credits = [t for t in txns if not t['is_debit']]

                st.success(f"Found **{len(debits)} expenses** and **{len(credits)} deposits/credits** in this statement.")

                # Preview table
                preview_df = pd.DataFrame(txns)
                preview_df['type'] = preview_df['is_debit'].map({True: '💸 Expense', False: '💰 Deposit'})
                st.dataframe(
                    preview_df[['date', 'description', 'amount', 'type', 'account']].rename(columns={
                        'date': 'Date', 'description': 'Description',
                        'amount': 'Amount ($)', 'type': 'Type', 'account': 'Account'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                # Account filter
                accounts = list(preview_df['account'].unique())
                selected_accounts = st.multiselect(
                    "Import from which accounts?",
                    accounts, default=accounts
                )
                import_credits = st.checkbox("Also import deposits/credits (payroll, refunds)", value=False)

                if st.button("✅ Import to Bank Transactions", type="primary"):
                    conn = get_conn()
                    count = 0
                    for t in txns:
                        if t['account'] not in selected_accounts:
                            continue
                        if not t['is_debit'] and not import_credits:
                            continue
                        # Deduplicate
                        exists = conn.execute(
                            "SELECT id FROM bank_transactions WHERE month=? AND date=? AND description=? AND amount=?",
                            (selected_month, t['date'], t['description'], t['amount'])
                        ).fetchone()
                        if not exists:
                            conn.execute(
                                "INSERT INTO bank_transactions (month, date, description, amount, source) VALUES (?, ?, ?, ?, ?)",
                                (selected_month, t['date'], t['description'], t['amount'], 'nfcu_pdf')
                            )
                            count += 1
                    conn.commit()
                    conn.close()
                    st.success(f"Imported {count} new transaction(s). Go to **Review & Apply** to categorize them.")
                    st.rerun()

        except Exception as e:
            st.error(f"Could not parse PDF: {e}")
            st.caption("Make sure this is an unencrypted Navy Federal statement PDF.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Generic CSV Import
# ════════════════════════════════════════════════════════════════════════════
with tab_csv:
    st.subheader("Import Bank CSV")

    with st.expander("ℹ️ How to export from your bank", expanded=False):
        st.markdown("""
**Chase / Bank of America / Wells Fargo / Citi:**
1. Log in → Accounts → select your checking or credit card
2. Look for **Download** or **Export** (usually near the transaction list)
3. Choose **CSV** format and the date range for this month
4. Upload the file below

**Expected columns (any order):** `Date`, `Description` (or `Merchant`), `Amount`

> 💡 Negative amounts = money out (expenses). Positive = money in (credits/refunds).
        """)

    uploaded = st.file_uploader("Upload your bank CSV", type=["csv"], key="csv_upload")

    if uploaded:
        try:
            raw = pd.read_csv(uploaded)
            st.write("**Preview of uploaded file:**")
            st.dataframe(raw.head(10), use_container_width=True)

            st.markdown("**Map your CSV columns:**")
            col_options = ["— skip —"] + list(raw.columns)
            c1, c2, c3 = st.columns(3)
            with c1:
                date_col = st.selectbox("Date column", col_options,
                                        index=next((i+1 for i, c in enumerate(raw.columns)
                                                    if "date" in c.lower()), 0))
            with c2:
                desc_col = st.selectbox("Description column", col_options,
                                        index=next((i+1 for i, c in enumerate(raw.columns)
                                                    if any(k in c.lower() for k in ["desc", "merchant", "name", "memo"])), 0))
            with c3:
                amt_col  = st.selectbox("Amount column", col_options,
                                        index=next((i+1 for i, c in enumerate(raw.columns)
                                                    if "amount" in c.lower()), 0))

            if st.button("✅ Import Transactions", type="primary"):
                if date_col == "— skip —" or desc_col == "— skip —" or amt_col == "— skip —":
                    st.error("Please map all three columns before importing.")
                else:
                    imported = raw[[date_col, desc_col, amt_col]].copy()
                    imported.columns = ["date", "description", "amount"]
                    imported["amount"] = pd.to_numeric(
                        imported["amount"].astype(str).str.replace(r"[,$]", "", regex=True),
                        errors="coerce"
                    )
                    imported = imported.dropna(subset=["amount"])
                    expenses_only = imported[imported["amount"] < 0].copy()
                    expenses_only["amount"] = expenses_only["amount"].abs()

                    conn = get_conn()
                    count = 0
                    for _, row in expenses_only.iterrows():
                        exists = conn.execute(
                            "SELECT id FROM bank_transactions WHERE month=? AND date=? AND description=? AND amount=?",
                            (selected_month, str(row["date"]), str(row["description"]), float(row["amount"]))
                        ).fetchone()
                        if not exists:
                            conn.execute(
                                "INSERT INTO bank_transactions (month, date, description, amount, source) VALUES (?, ?, ?, ?, ?)",
                                (selected_month, str(row["date"]), str(row["description"]), float(row["amount"]), "csv")
                            )
                            count += 1
                    conn.commit()
                    conn.close()
                    st.success(f"Imported {count} new transaction(s). Head to **Review & Apply** to categorize them.")
                    st.rerun()
        except Exception as e:
            st.error(f"Could not parse CSV: {e}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Manual Entry
# ════════════════════════════════════════════════════════════════════════════
with tab_manual:
    st.subheader("Add a Transaction Manually")
    c1, c2 = st.columns(2)
    with c1:
        t_date  = st.date_input("Date", value=datetime.today())
        t_desc  = st.text_input("Description / Merchant")
    with c2:
        t_amt   = st.number_input("Amount ($)", min_value=0.0, step=1.0)
        t_cat   = st.selectbox("Category (optional)", cat_options)
    t_notes = st.text_input("Notes")

    if st.button("➕ Add Transaction", type="primary"):
        if t_desc:
            cat_val = None if t_cat == "— Uncategorized —" else t_cat.split(" › ")[0]
            sub_val = None if t_cat == "— Uncategorized —" else t_cat.split(" › ")[1]
            conn = get_conn()
            conn.execute(
                "INSERT INTO bank_transactions (month, date, description, amount, category, subcategory, source, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (selected_month, str(t_date), t_desc, t_amt, cat_val, sub_val, "manual", t_notes)
            )
            conn.commit()
            conn.close()
            st.success("Transaction added! Go to **Review & Apply** to push it to your budget.")
            st.rerun()
        else:
            st.error("Description is required.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — Review & Apply
# ════════════════════════════════════════════════════════════════════════════
with tab_review:
    st.subheader(f"Transactions for {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")

    conn = get_conn()
    txn_df = pd.read_sql(
        "SELECT * FROM bank_transactions WHERE month = ? ORDER BY date DESC",
        conn, params=(selected_month,)
    )
    conn.close()

    if txn_df.empty:
        st.info("No transactions yet for this month. Import a PDF/CSV or add one manually.")
    else:
        # Source badge helper
        source_labels = {'nfcu_pdf': '🏛️ NFCU PDF', 'csv': '📂 CSV', 'manual': '✏️ Manual'}

        def fmt_cat(row):
            if pd.notna(row['category']) and pd.notna(row['subcategory']):
                return f"{row['category']} › {row['subcategory']}"
            return "— Uncategorized —"

        txn_display = txn_df.copy()
        txn_display['mapped_to'] = txn_display.apply(fmt_cat, axis=1)
        txn_display['src'] = txn_display['source'].map(lambda s: source_labels.get(s, s))

        edited_txn = st.data_editor(
            txn_display[['id', 'date', 'description', 'amount', 'mapped_to', 'notes', 'src']],
            column_config={
                "id":          st.column_config.NumberColumn("ID",          disabled=True, width="small"),
                "date":        st.column_config.TextColumn("Date",          disabled=True),
                "description": st.column_config.TextColumn("Description",   disabled=True),
                "amount":      st.column_config.NumberColumn("Amount ($)",   format="$%.2f", disabled=True),
                "mapped_to":   st.column_config.SelectboxColumn("Map to Budget Line", options=cat_options),
                "notes":       st.column_config.TextColumn("Notes"),
                "src":         st.column_config.TextColumn("Source",        disabled=True, width="small"),
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed"
        )

        col_a, col_b = st.columns([1, 1])

        with col_a:
            if st.button("💾 Save Mappings", type="primary"):
                conn = get_conn()
                c = conn.cursor()
                for _, row in edited_txn.iterrows():
                    if row['mapped_to'] != "— Uncategorized —" and " › " in str(row['mapped_to']):
                        parts = row['mapped_to'].split(" › ")
                        cat_v, sub_v = parts[0], parts[1]
                    else:
                        cat_v, sub_v = None, None
                    c.execute(
                        "UPDATE bank_transactions SET category=?, subcategory=?, notes=? WHERE id=?",
                        (cat_v, sub_v, row['notes'], row['id'])
                    )
                conn.commit()
                conn.close()
                st.success("Mappings saved!")
                st.rerun()

        with col_b:
            if st.button("⚡ Apply to Budget Actuals"):
                conn = get_conn()
                c = conn.cursor()
                applied = 0
                skipped = 0
                for _, row in edited_txn.iterrows():
                    if row['mapped_to'] != "— Uncategorized —" and " › " in str(row['mapped_to']):
                        parts = row['mapped_to'].split(" › ")
                        cat_v, sub_v = parts[0], parts[1]
                        exp = c.execute(
                            "SELECT id, actual FROM expenses WHERE month=? AND category=? AND subcategory=?",
                            (selected_month, cat_v, sub_v)
                        ).fetchone()
                        if exp:
                            orig = c.execute(
                                "SELECT amount FROM bank_transactions WHERE id=?", (row['id'],)
                            ).fetchone()
                            if orig:
                                new_actual = (exp['actual'] or 0) + orig['amount']
                                c.execute("UPDATE expenses SET actual=? WHERE id=?", (new_actual, exp['id']))
                                c.execute(
                                    "UPDATE bank_transactions SET matched_expense_id=? WHERE id=?",
                                    (exp['id'], row['id'])
                                )
                                applied += 1
                        else:
                            skipped += 1
                conn.commit()
                conn.close()
                if applied:
                    st.success(f"✅ Applied {applied} transaction(s) to budget actuals!")
                if skipped:
                    st.warning(f"⚠️ {skipped} transaction(s) had no matching budget line — add the category first on the Expenses page.")
                st.rerun()

        st.markdown("---")

        # Delete individual transactions
        with st.expander("🗑️ Delete a Transaction"):
            del_id = st.selectbox(
                "Select transaction to delete",
                txn_df['id'].tolist(),
                format_func=lambda x: f"#{x} — {txn_df[txn_df['id']==x]['description'].values[0]} (${txn_df[txn_df['id']==x]['amount'].values[0]:,.2f})"
            )
            if st.button("Delete", type="secondary"):
                conn = get_conn()
                conn.execute("DELETE FROM bank_transactions WHERE id=?", (del_id,))
                conn.commit()
                conn.close()
                st.success("Deleted.")
                st.rerun()

        # Summary
        st.markdown("---")
        total_imported = txn_df['amount'].sum()
        categorized    = txn_df[txn_df['category'].notna()]
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Transactions", len(txn_df))
        m2.metric("Total Spending", f"${total_imported:,.2f}")
        m3.metric("Categorized", f"{len(categorized)} / {len(txn_df)}")
