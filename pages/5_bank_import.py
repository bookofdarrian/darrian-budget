import streamlit as st
import pandas as pd
import io
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, execute, fetchone
from utils.nfcu_parser import parse_nfcu_pdf
from utils.auth import require_password


# ── Auto-categorization rules ─────────────────────────────────────────────────
#
# TRANSFERS — account-to-account moves, NOT real expenses.
# NOTE: "Paid To -" lines (rent, utilities, gym) are real expenses — NOT listed here.
_TRANSFER_KEYWORDS = [
    'transfer to',           # "Transfer To Credit Card", "Transfer To Checking"
    'transfer from',         # "Transfer From Checking"
    'fidelity',
    'cashapp', 'cash app',
    'ach paid to darrian',   # ACH self-transfer (savings → checking)
    'zelle db darrian',
    'venmo',
    'nfo payment received',  # CC statement: payment received from checking
]

# MERCHANT RULES — checked in order, first match wins.
# Format: (keyword_in_description_lower, category, subcategory)
_AUTO_CAT_RULES: list[tuple[str, str, str]] = [
    # ── Transportation ──────────────────────────────────────────────────────
    ('chevron',           'Transportation', 'Fuel'),
    ('shell oil',         'Transportation', 'Fuel'),
    ('circle k',          'Transportation', 'Fuel'),
    ('qt ',               'Transportation', 'Fuel'),
    ('lyft',              'Transportation', 'Fuel'),
    ('uber',              'Transportation', 'Fuel'),
    ('mta*',              'Transportation', 'Fuel'),       # NYC subway/LIRR
    ('mta*lirr',          'Transportation', 'Fuel'),
    # ── Food / Dining ───────────────────────────────────────────────────────
    ('chipotle',          'Food', 'Dining Out'),
    ('chick-fil-a',       'Food', 'Dining Out'),
    ('zaxby',             'Food', 'Dining Out'),
    ('tst*',              'Food', 'Dining Out'),           # Toast POS restaurants
    ('sq *',              'Food', 'Dining Out'),           # Square POS restaurants
    ('nom ',              'Food', 'Dining Out'),
    ('pho ',              'Food', 'Dining Out'),
    ('deli',              'Food', 'Dining Out'),
    ('pizza',             'Food', 'Dining Out'),
    ('ramen',             'Food', 'Dining Out'),
    ('jerk',              'Food', 'Dining Out'),
    ('dunkin',            'Food', 'Dining Out'),
    ('wendys',            'Food', 'Dining Out'),
    ('american deli',     'Food', 'Dining Out'),
    ('kpot',              'Food', 'Dining Out'),
    ('peach cobbler',     'Food', 'Dining Out'),
    ('juicy joint',       'Food', 'Dining Out'),
    ('jamrock',           'Food', 'Dining Out'),
    ('cava',              'Food', 'Dining Out'),
    ('el super pan',      'Food', 'Dining Out'),
    ('gooey',             'Food', 'Dining Out'),
    ('jj fish',           'Food', 'Dining Out'),
    ('walmart',           'Food', 'Groceries'),
    ('wal-mart',          'Food', 'Groceries'),
    ('wm super',          'Food', 'Groceries'),
    ('walgreens',         'Personal Care', 'Medical'),
    # ── Entertainment ───────────────────────────────────────────────────────
    ('hulu',              'Entertainment', 'Subscriptions'),
    ('netflix',           'Entertainment', 'Subscriptions'),
    ('apple.com/bill',    'Entertainment', 'Subscriptions'),
    ('playstation',       'Entertainment', 'Subscriptions'),
    ('steamgames',        'Entertainment', 'Subscriptions'),
    ('amc ',              'Entertainment', 'Movies'),
    ('regal',             'Entertainment', 'Movies'),
    ('truist park',       'Entertainment', 'Night Out'),
    ('pf atlanta',        'Entertainment', 'Subscriptions'),  # Planet Fitness
    ('visaatlanta',       'Entertainment', 'Night Out'),
    ('redveil',           'Entertainment', 'Night Out'),      # concert ticket
    ('big city tourism',  'Entertainment', 'Night Out'),
    # ── Shopping / Amazon ───────────────────────────────────────────────────
    ('amazon',            'Entertainment', 'Subscriptions'),  # broad; user can remap
    ('bestbuy',           'Entertainment', 'Subscriptions'),
    ('ray-ban',           'Personal Care', 'Hair / Nails'),
    ('zenni optical',     'Personal Care', 'Medical'),
    ('tj maxx',           'Personal Care', 'Hair / Nails'),
    ('goodwill',          'Personal Care', 'Hair / Nails'),
    ('44th & 3rd',        'Entertainment', 'Subscriptions'),  # bookstore
    ('the darkroom',      'Entertainment', 'Subscriptions'),  # photography
    ('l train vintage',   'Personal Care', 'Hair / Nails'),
    ('luxer',             'Housing', 'Supplies'),             # package locker
    # ── Pets ────────────────────────────────────────────────────────────────
    ('fetch*',            'Pets', 'Medical'),
    ('petco',             'Pets', 'Food'),
    ('lifeline animal',   'Pets', 'Medical'),
    # ── Insurance / Services ────────────────────────────────────────────────
    ('allstate',          'Insurance', 'Renters'),
    ('aga service',       'Insurance', 'Renters'),            # Allianz travel insurance
    ('avalon home',       'Housing', 'Maintenance / Repairs'),# home inspection
    ('ga driver svcs',    'Transportation', 'Maintenance'),   # GA DMV
    ('aaa park',          'Transportation', 'Maintenance'),
    # ── Housing / Bills paid via ACH "Paid To -" ────────────────────────────
    ('the vivian',        'Housing', 'Mortgage / Rent'),
    ('gpc gpc',           'Housing', 'Electricity'),          # Georgia Power
    # ── Gardening income (Zelle payments received) ───────────────────────────
    ('zelle*joshua',      'Gardening', 'Gardening'),
    ('zelle*xavier',      'Gardening', 'Gardening'),
]

def _auto_category(description: str) -> tuple[str | None, str | None]:
    """Return (category, subcategory) based on description keywords, or (None, None)."""
    desc_lower = description.lower()
    # Transfers first — these are not real expenses
    if any(k in desc_lower for k in _TRANSFER_KEYWORDS):
        return ('Transfer', 'Transfer')
    # Merchant-specific rules
    for keyword, cat, sub in _AUTO_CAT_RULES:
        if keyword in desc_lower:
            return (cat, sub)
    return (None, None)


def _is_duplicate(conn, date: str, description: str, amount: float) -> bool:
    """Check if a transaction already exists by date + description + amount (any month)."""
    row = fetchone(
        conn,
        "SELECT id FROM bank_transactions WHERE date=? AND description=? AND amount=?",
        (date, description, amount)
    )
    return row is not None


st.set_page_config(page_title="Bank Import", page_icon="🏦", layout="wide")
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

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")

st.title("🏦 Bank Import")
st.caption("Upload your Navy Federal PDF statement or any bank CSV to pull in transactions. Then map each one to a budget category and apply to your actuals.")

conn = get_conn()
expense_df = read_sql("SELECT id, category, subcategory FROM expenses WHERE month = ?", conn, params=(selected_month,))
conn.close()

cat_options = ["— Uncategorized —"] + [
    f"{r['category']} › {r['subcategory']}" for _, r in expense_df.iterrows()
]

tab_nfcu, tab_csv, tab_manual, tab_review = st.tabs([
    "🏛️ Navy Federal PDF", "📂 Other Bank CSV", "✏️ Add Manually", "📋 Review & Apply"
])

# ── TAB 1 — Navy Federal PDF ──────────────────────────────────────────────────
with tab_nfcu:
    st.subheader("Import Navy Federal Statement (PDF)")
    with st.expander("ℹ️ How to download your NFCU statement", expanded=False):
        st.markdown("""
1. Log in at **navyfederal.org** or the Navy Federal app
2. Go to **Accounts** → select your checking account
3. Click **Statements** in the left menu
4. Choose the statement month and click **Download** (PDF)
5. Upload the PDF below — all accounts in the statement will be parsed automatically
        """)

    nfcu_file = st.file_uploader("Upload Navy Federal PDF statement", type=["pdf"], key="nfcu_pdf")

    if nfcu_file:
        try:
            with st.spinner("Parsing PDF..."):
                txns = parse_nfcu_pdf(io.BytesIO(nfcu_file.read()))
            if not txns:
                st.error("No transactions found.")
            else:
                debits  = [t for t in txns if t['is_debit']]
                credits = [t for t in txns if not t['is_debit']]
                st.success(f"Found **{len(debits)} expenses** and **{len(credits)} deposits/credits**.")

                preview_df = pd.DataFrame(txns)
                preview_df['type'] = preview_df['is_debit'].map({True: '💸 Expense', False: '💰 Deposit'})

                # ── Duplicate detection ──────────────────────────────────────
                conn = get_conn()
                preview_df['duplicate'] = preview_df.apply(
                    lambda r: _is_duplicate(conn, r['date'], r['description'], r['amount']),
                    axis=1
                )
                conn.close()

                new_count  = (~preview_df['duplicate']).sum()
                dup_count  = preview_df['duplicate'].sum()

                if dup_count > 0:
                    st.warning(
                        f"⚠️ **{dup_count} duplicate(s)** already in the database will be skipped. "
                        f"**{new_count} new** transaction(s) ready to import."
                    )
                    with st.expander(f"🔍 Show {dup_count} duplicate(s)", expanded=False):
                        dup_display = preview_df[preview_df['duplicate']][
                            ['date', 'description', 'amount', 'type', 'account']
                        ].rename(columns={
                            'date': 'Date', 'description': 'Description',
                            'amount': 'Amount ($)', 'type': 'Type', 'account': 'Account'
                        })
                        st.dataframe(dup_display, use_container_width=True, hide_index=True)
                else:
                    st.info(f"✅ No duplicates detected — all {new_count} transaction(s) are new.")

                # Show full preview with duplicate flag
                preview_display = preview_df[['date', 'description', 'amount', 'type', 'account', 'duplicate']].rename(
                    columns={
                        'date': 'Date', 'description': 'Description',
                        'amount': 'Amount ($)', 'type': 'Type',
                        'account': 'Account', 'duplicate': '⚠️ Duplicate'
                    }
                )
                st.dataframe(preview_display, use_container_width=True, hide_index=True)

                accounts = list(preview_df['account'].unique())
                selected_accounts = st.multiselect("Import from which accounts?", accounts, default=accounts)
                import_credits = st.checkbox("Also import deposits/credits", value=False)

                btn_label = f"✅ Import {new_count} New Transaction(s)" if new_count > 0 else "✅ Import (nothing new)"
                if st.button(btn_label, type="primary", disabled=(new_count == 0)):
                    conn = get_conn()
                    count = 0
                    for t in txns:
                        if t['account'] not in selected_accounts:
                            continue
                        if not t['is_debit'] and not import_credits:
                            continue
                        # Skip duplicates
                        if _is_duplicate(conn, t['date'], t['description'], t['amount']):
                            continue
                        # Month comes from the transaction date, not the sidebar selector
                        txn_month = t['date'][:7]
                        auto_cat, auto_sub = _auto_category(t['description'])
                        execute(conn,
                            "INSERT INTO bank_transactions "
                            "(month, date, description, amount, is_debit, category, subcategory, source) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (txn_month, t['date'], t['description'], t['amount'],
                             1 if t['is_debit'] else 0, auto_cat, auto_sub, 'nfcu_pdf'))
                        count += 1
                    conn.commit()
                    conn.close()
                    st.success(f"Imported {count} new transaction(s). Go to **Review & Apply** to categorize them.")
                    st.rerun()
        except Exception as e:
            st.error(f"Could not parse PDF: {e}")

# ── TAB 2 — CSV Import ────────────────────────────────────────────────────────
with tab_csv:
    st.subheader("Import Bank CSV")
    uploaded = st.file_uploader("Upload your bank CSV", type=["csv"], key="csv_upload")
    if uploaded:
        try:
            raw = pd.read_csv(uploaded)
            st.write("**Preview:**")
            st.dataframe(raw.head(10), use_container_width=True)
            col_options = ["— skip —"] + list(raw.columns)
            c1, c2, c3 = st.columns(3)
            with c1:
                date_col = st.selectbox("Date column", col_options, index=next((i+1 for i, c in enumerate(raw.columns) if "date" in c.lower()), 0))
            with c2:
                desc_col = st.selectbox("Description column", col_options, index=next((i+1 for i, c in enumerate(raw.columns) if any(k in c.lower() for k in ["desc", "merchant", "name", "memo"])), 0))
            with c3:
                amt_col = st.selectbox("Amount column", col_options, index=next((i+1 for i, c in enumerate(raw.columns) if "amount" in c.lower()), 0))

            if st.button("✅ Import Transactions", type="primary"):
                if "— skip —" in [date_col, desc_col, amt_col]:
                    st.error("Please map all three columns.")
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
                    count = skipped = 0
                    for _, row in expenses_only.iterrows():
                        date_str = str(row["date"])
                        desc_str = str(row["description"])
                        amt_val  = float(row["amount"])
                        # Month comes from the transaction date, not the sidebar selector
                        try:
                            txn_month = pd.to_datetime(date_str).strftime("%Y-%m")
                        except Exception:
                            txn_month = selected_month  # fallback if date can't be parsed

                        if _is_duplicate(conn, date_str, desc_str, amt_val):
                            skipped += 1
                            continue
                        execute(conn,
                            "INSERT INTO bank_transactions (month, date, description, amount, source) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (txn_month, date_str, desc_str, amt_val, "csv"))
                        count += 1
                    conn.commit()
                    conn.close()
                    msg = f"Imported {count} new transaction(s)."
                    if skipped:
                        msg += f" Skipped {skipped} duplicate(s)."
                    st.success(msg)
                    st.rerun()
        except Exception as e:
            st.error(f"Could not parse CSV: {e}")

# ── TAB 3 — Manual Entry ──────────────────────────────────────────────────────
with tab_manual:
    st.subheader("Add a Transaction Manually")
    c1, c2 = st.columns(2)
    with c1:
        t_date = st.date_input("Date", value=datetime.today())
        t_desc = st.text_input("Description / Merchant")
    with c2:
        t_amt  = st.number_input("Amount ($)", min_value=0.0, step=1.0)
        t_cat  = st.selectbox("Category (optional)", cat_options)
    t_notes = st.text_input("Notes")
    if st.button("➕ Add Transaction", type="primary"):
        if t_desc:
            cat_val = None if t_cat == "— Uncategorized —" else t_cat.split(" › ")[0]
            sub_val = None if t_cat == "— Uncategorized —" else t_cat.split(" › ")[1]
            # Month comes from the entered date
            txn_month = str(t_date)[:7]
            conn = get_conn()
            execute(conn,
                "INSERT INTO bank_transactions (month, date, description, amount, category, subcategory, source, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (txn_month, str(t_date), t_desc, t_amt, cat_val, sub_val, "manual", t_notes))
            conn.commit()
            conn.close()
            st.success("Transaction added!")
            st.rerun()
        else:
            st.error("Description is required.")

# ── TAB 4 — Review & Apply ────────────────────────────────────────────────────
with tab_review:
    st.subheader("Review & Apply Transactions")

    # Let user choose to view a specific month or all months
    review_filter = st.radio(
        "Show transactions for:",
        ["All months", f"Selected month ({datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')})"],
        horizontal=True,
        key="review_filter"
    )

    conn = get_conn()
    if review_filter.startswith("All"):
        txn_df = read_sql("SELECT * FROM bank_transactions ORDER BY date DESC", conn)
    else:
        txn_df = read_sql("SELECT * FROM bank_transactions WHERE month = ? ORDER BY date DESC", conn, params=(selected_month,))
    conn.close()

    if txn_df.empty:
        st.info("No transactions yet for this month.")
    else:
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
            use_container_width=True, hide_index=True, num_rows="fixed"
        )

        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("💾 Save Mappings", type="primary"):
                conn = get_conn()
                for _, row in edited_txn.iterrows():
                    if row['mapped_to'] != "— Uncategorized —" and " › " in str(row['mapped_to']):
                        parts = row['mapped_to'].split(" › ")
                        cat_v, sub_v = parts[0], parts[1]
                    else:
                        cat_v, sub_v = None, None
                    execute(conn, "UPDATE bank_transactions SET category=?, subcategory=?, notes=? WHERE id=?",
                            (cat_v, sub_v, row['notes'], row['id']))
                conn.commit()
                conn.close()
                st.success("Mappings saved!")
                st.rerun()

        with col_b:
            if st.button("⚡ Apply to Budget Actuals"):
                conn = get_conn()
                applied = skipped = 0
                for _, row in edited_txn.iterrows():
                    if row['mapped_to'] != "— Uncategorized —" and " › " in str(row['mapped_to']):
                        parts = row['mapped_to'].split(" › ")
                        cat_v, sub_v = parts[0], parts[1]
                        exp = fetchone(conn, "SELECT id, actual FROM expenses WHERE month=? AND category=? AND subcategory=?",
                                       (selected_month, cat_v, sub_v))
                        if exp:
                            orig = fetchone(conn, "SELECT amount FROM bank_transactions WHERE id=?", (row['id'],))
                            if orig:
                                new_actual = (exp[1] or 0) + orig[0]
                                execute(conn, "UPDATE expenses SET actual=? WHERE id=?", (new_actual, exp[0]))
                                execute(conn, "UPDATE bank_transactions SET matched_expense_id=? WHERE id=?", (exp[0], row['id']))
                                applied += 1
                        else:
                            skipped += 1
                conn.commit()
                conn.close()
                if applied:
                    st.success(f"✅ Applied {applied} transaction(s) to budget actuals!")
                if skipped:
                    st.warning(f"⚠️ {skipped} transaction(s) had no matching budget line.")
                st.rerun()

        st.markdown("---")
        with st.expander("🗑️ Delete a Transaction"):
            del_id = st.selectbox("Select transaction to delete", txn_df['id'].tolist(),
                format_func=lambda x: f"#{x} — {txn_df[txn_df['id']==x]['description'].values[0]} (${txn_df[txn_df['id']==x]['amount'].values[0]:,.2f})")
            if st.button("Delete", type="secondary"):
                conn = get_conn()
                execute(conn, "DELETE FROM bank_transactions WHERE id=?", (del_id,))
                conn.commit()
                conn.close()
                st.success("Deleted.")
                st.rerun()

        st.markdown("---")
        total_imported = txn_df['amount'].sum()
        categorized = txn_df[txn_df['category'].notna()]
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Transactions", len(txn_df))
        m2.metric("Total Spending", f"${total_imported:,.2f}")
        m3.metric("Categorized", f"{len(categorized)} / {len(txn_df)}")
