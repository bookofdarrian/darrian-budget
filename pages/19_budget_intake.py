"""
19_budget_intake.py
────────────────────
Monthly Budget Intake — two ways to enter your budget:
  1. Manual form  (income + expense rows)
  2. Excel upload (Microsoft Personal Monthly Budget template or generic)

After parsing, Claude can AI-categorise any unrecognised expense labels
before you confirm and save everything to the database.
"""

import os
import re
import io
from datetime import datetime

import streamlit as st
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.db import (
    get_conn, init_db, read_sql, execute as db_execute,
    seed_budget, seed_income, get_setting,
)
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.budget_importer import (
    parse_budget_excel,
    build_ai_categorise_prompt,
    parse_ai_categorise_response,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Budget Intake — Peach State Savings",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()

months = []
for m in range(1, 13):
    months.append(datetime(2025, m, 1).strftime("%Y-%m"))
for m in range(1, 13):
    months.append(datetime(2026, m, 1).strftime("%Y-%m"))

current_month = datetime.now().strftime("%Y-%m")
default_idx   = months.index(current_month) if current_month in months else 0
selected_month = st.sidebar.selectbox("📅 Month", months, index=default_idx)

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                      label="Overview",             icon="📊")
st.sidebar.page_link("pages/19_budget_intake.py",   label="Budget Intake",        icon="📥")
st.sidebar.page_link("pages/1_expenses.py",         label="Expenses",             icon="📋")
st.sidebar.page_link("pages/2_income.py",           label="Income",               icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py", label="Business Tracker 🔒",  icon="💼")
st.sidebar.page_link("pages/4_trends.py",           label="Monthly Trends",       icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",      label="Bank Import",          icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",         label="Receipts & HSA",       icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",      label="AI Insights 🔒",       icon="🤖")
st.sidebar.page_link("pages/8_goals.py",            label="Financial Goals",      icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",        label="Net Worth 🔒",         icon="💎")
st.sidebar.page_link("pages/15_bills.py",           label="Bill Calendar",        icon="📅")
st.sidebar.page_link("pages/16_paycheck.py",        label="Paycheck Allocator",   icon="💸")
st.sidebar.page_link("pages/0_pricing.py",          label="⭐ Upgrade to Pro",    icon="⭐")

render_sidebar_user_widget()

# ── Title ─────────────────────────────────────────────────────────────────────
month_label = datetime.strptime(selected_month, "%Y-%m").strftime("%B %Y")
st.title(f"📥 Budget Intake — {month_label}")
st.caption(
    "Enter your monthly budget manually **or** upload your Personal Monthly Budget Excel file. "
    "AI can help categorise any expenses it doesn't recognise."
)

# ── Helper: load existing categories from DB ──────────────────────────────────
@st.cache_data(ttl=60)
def _get_existing_categories() -> list[tuple[str, str]]:
    conn = get_conn()
    df = read_sql("SELECT DISTINCT category, subcategory FROM expenses ORDER BY category, subcategory", conn)
    conn.close()
    return list(zip(df["category"], df["subcategory"]))


# ── Helper: call Claude for AI categorisation ─────────────────────────────────
def _ai_categorise(unmatched: list[str], existing_cats: list[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Call Claude to categorise unmatched labels. Returns {label: (cat, sub)}."""
    api_key = st.session_state.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "") or get_setting("anthropic_api_key", "")
    if not api_key:
        return {}
    try:
        import anthropic
        client  = anthropic.Anthropic(api_key=api_key)
        prompt  = build_ai_categorise_prompt(unmatched, existing_cats)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        return parse_ai_categorise_response(raw, unmatched)
    except Exception as e:
        st.warning(f"AI categorisation failed: {e}")
        return {}


# ── Helper: save parsed data to DB ────────────────────────────────────────────
def _save_to_db(
    month: str,
    income_rows: list[dict],
    expense_rows: list[dict],
    overwrite: bool,
) -> tuple[int, int]:
    """
    Insert income + expense rows for the given month.
    If overwrite=True, delete existing rows first.
    Returns (income_count, expense_count).
    """
    conn = get_conn()

    if overwrite:
        db_execute(conn, "DELETE FROM income WHERE month = ?",   (month,))
        db_execute(conn, "DELETE FROM expenses WHERE month = ?", (month,))
        conn.commit()

    inc_count = 0
    for row in income_rows:
        source = row.get("source", "Imported Income")
        amount = float(row.get("amount", 0) or 0)
        notes  = row.get("notes", "Imported from Excel")
        if amount > 0:
            db_execute(conn,
                "INSERT INTO income (month, source, amount, notes) VALUES (?, ?, ?, ?)",
                (month, source, amount, notes),
            )
            inc_count += 1

    exp_count = 0
    for row in expense_rows:
        cat  = row.get("category", "Other")
        sub  = row.get("subcategory", "Other")
        proj = float(row.get("projected", 0) or 0)
        act  = float(row.get("actual",    0) or 0)
        db_execute(conn,
            "INSERT INTO expenses (month, category, subcategory, projected, actual) VALUES (?, ?, ?, ?, ?)",
            (month, cat, sub, proj, act),
        )
        exp_count += 1

    conn.commit()
    conn.close()
    return inc_count, exp_count


# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_upload, tab_manual = st.tabs(["📤 Upload Excel", "✏️ Manual Entry"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — EXCEL UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
with tab_upload:
    st.subheader("📤 Upload Your Monthly Budget Spreadsheet")
    st.markdown(
        "Upload the **Microsoft Personal Monthly Budget** template (`.xlsx`) "
        "or any flat Excel table with Description / Projected / Actual columns. "
        "The parser will auto-detect the layout."
    )

    with st.expander("ℹ️ Supported formats", expanded=False):
        st.markdown(
            """
**Format 1 — Microsoft Personal Monthly Budget template**
The exact template from Microsoft 365 (the one with Housing, Transportation,
Food, Entertainment, etc. sections side-by-side). Just upload it as-is.

**Format 2 — Generic flat table**
Any sheet with columns like:
| Description | Projected Cost | Actual Cost |
|---|---|---|
| Rent | 1200 | 1200 |
| Groceries | 400 | 380 |

Column names are flexible — the parser looks for keywords like
*projected*, *actual*, *description*, *item*, etc.
            """
        )

    uploaded_file = st.file_uploader(
        "Choose an Excel file (.xlsx or .xls)",
        type=["xlsx", "xls"],
        key="budget_upload",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()

        with st.spinner("Parsing spreadsheet…"):
            try:
                parsed = parse_budget_excel(file_bytes)
            except Exception as e:
                st.error(f"❌ Could not parse the file: {e}")
                st.stop()

        layout_badge = "🟢 Microsoft Template" if parsed["layout"] == "microsoft_template" else "🔵 Generic Table"
        st.success(
            f"✅ Parsed **{parsed['sheet']}** sheet  ·  Layout: {layout_badge}  ·  "
            f"{len(parsed['income'])} income row(s)  ·  {len(parsed['expenses'])} expense row(s)"
        )

        # ── AI categorisation for unmatched labels ────────────────────────────
        unmatched = parsed.get("unmatched", [])
        if unmatched:
            st.warning(
                f"⚠️ **{len(unmatched)} expense label(s)** couldn't be auto-categorised: "
                f"{', '.join(unmatched[:8])}{'…' if len(unmatched) > 8 else ''}"
            )
            col_ai1, col_ai2 = st.columns([2, 1])
            with col_ai1:
                st.markdown("Use **Claude AI** to suggest categories for these labels:")
            with col_ai2:
                run_ai = st.button("🤖 AI Categorise", type="primary", key="btn_ai_cat_upload")

            if run_ai:
                existing_cats = _get_existing_categories()
                with st.spinner("Claude is categorising your expenses…"):
                    ai_suggestions = _ai_categorise(unmatched, existing_cats)

                if ai_suggestions:
                    st.session_state["ai_suggestions_upload"] = ai_suggestions
                    st.success(f"✅ Claude suggested categories for {len(ai_suggestions)} label(s).")
                else:
                    st.info("No API key found — skipping AI categorisation. You can edit categories in the table below.")

            # Apply AI suggestions to parsed expenses
            ai_sugg = st.session_state.get("ai_suggestions_upload", {})
            if ai_sugg:
                for exp in parsed["expenses"]:
                    if exp["subcategory"] in ai_sugg:
                        exp["category"], exp["subcategory"] = ai_sugg[exp["subcategory"]]

        # ── Preview & edit income ─────────────────────────────────────────────
        st.markdown("---")
        st.subheader("💵 Income Preview")
        if parsed["income"]:
            inc_df = pd.DataFrame(parsed["income"])
            # Ensure columns exist
            for col in ["source", "amount", "notes"]:
                if col not in inc_df.columns:
                    inc_df[col] = "" if col != "amount" else 0.0

            edited_income = st.data_editor(
                inc_df[["source", "amount", "notes"]],
                column_config={
                    "source": st.column_config.TextColumn("Source"),
                    "amount": st.column_config.NumberColumn("Amount ($)", format="$%.2f", min_value=0),
                    "notes":  st.column_config.TextColumn("Notes"),
                },
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="edit_income_upload",
            )
        else:
            st.info("No income rows detected. You can add them manually on the Income page.")
            edited_income = pd.DataFrame(columns=["source", "amount", "notes"])

        # ── Preview & edit expenses ───────────────────────────────────────────
        st.markdown("---")
        st.subheader("📋 Expenses Preview")
        if parsed["expenses"]:
            exp_df = pd.DataFrame(parsed["expenses"])
            for col in ["category", "subcategory", "projected", "actual"]:
                if col not in exp_df.columns:
                    exp_df[col] = "" if col in ("category", "subcategory") else 0.0

            # Build category options for the dropdown
            all_cats = sorted(set(
                [c for c, _ in _get_existing_categories()] +
                exp_df["category"].tolist() +
                ["Housing", "Transportation", "Insurance", "Food", "Pets",
                 "Personal Care", "Entertainment", "Loans", "Taxes",
                 "Savings / Investments", "Gifts & Donations", "Legal", "Other"]
            ))

            edited_expenses = st.data_editor(
                exp_df[["category", "subcategory", "projected", "actual"]],
                column_config={
                    "category":    st.column_config.SelectboxColumn(
                        "Category", options=all_cats, required=True
                    ),
                    "subcategory": st.column_config.TextColumn("Subcategory"),
                    "projected":   st.column_config.NumberColumn("Projected ($)", format="$%.2f", min_value=0),
                    "actual":      st.column_config.NumberColumn("Actual ($)",    format="$%.2f", min_value=0),
                },
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="edit_expenses_upload",
            )
        else:
            st.info("No expense rows detected.")
            edited_expenses = pd.DataFrame(columns=["category", "subcategory", "projected", "actual"])

        # ── Summary totals ────────────────────────────────────────────────────
        if not edited_expenses.empty:
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            total_proj = edited_expenses["projected"].sum()
            total_act  = edited_expenses["actual"].sum()
            total_inc  = edited_income["amount"].sum() if not edited_income.empty else 0
            c1.metric("💵 Total Income",    f"${total_inc:,.2f}")
            c2.metric("📋 Total Projected", f"${total_proj:,.2f}")
            c3.metric("💳 Total Actual",    f"${total_act:,.2f}")

        # ── Save options ──────────────────────────────────────────────────────
        st.markdown("---")
        overwrite = st.checkbox(
            "🗑️ Replace existing data for this month (uncheck to merge / append)",
            value=True,
            key="overwrite_upload",
            help="If checked, all existing income and expense rows for the selected month are deleted before importing.",
        )

        if st.button("💾 Save to Budget", type="primary", key="btn_save_upload"):
            income_list  = edited_income.to_dict("records")  if not edited_income.empty  else []
            expense_list = edited_expenses.to_dict("records") if not edited_expenses.empty else []

            if not income_list and not expense_list:
                st.error("Nothing to save — the parsed data is empty.")
            else:
                inc_n, exp_n = _save_to_db(selected_month, income_list, expense_list, overwrite)
                st.success(
                    f"✅ Saved **{inc_n} income** and **{exp_n} expense** rows for {month_label}!"
                )
                st.balloons()
                # Clear AI suggestions cache
                st.session_state.pop("ai_suggestions_upload", None)
                _get_existing_categories.clear()
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — MANUAL ENTRY
# ─────────────────────────────────────────────────────────────────────────────
with tab_manual:
    st.subheader("✏️ Manual Budget Entry")
    st.caption(
        "Fill in your income and expenses directly. "
        "Use the **AI Suggest** button to let Claude fill in typical amounts based on your description."
    )

    # ── Income section ────────────────────────────────────────────────────────
    st.markdown("### 💵 Income")

    if "manual_income" not in st.session_state:
        st.session_state["manual_income"] = [
            {"source": "Salary — Paycheck 1 (Post-Tax)", "amount": 0.0, "notes": ""},
            {"source": "Salary — Paycheck 2 (Post-Tax)", "amount": 0.0, "notes": ""},
            {"source": "Extra Income",                   "amount": 0.0, "notes": ""},
        ]

    manual_inc_df = pd.DataFrame(st.session_state["manual_income"])
    edited_manual_income = st.data_editor(
        manual_inc_df,
        column_config={
            "source": st.column_config.TextColumn("Source",      width="large"),
            "amount": st.column_config.NumberColumn("Amount ($)", format="$%.2f", min_value=0),
            "notes":  st.column_config.TextColumn("Notes"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="manual_income_editor",
    )

    # ── Expense section ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Expenses")

    # Default expense template matching the app's seed categories
    _DEFAULT_EXPENSES = [
        {"category": "Housing",               "subcategory": "Mortgage / Rent",      "projected": 0.0, "actual": 0.0},
        {"category": "Housing",               "subcategory": "Phone",                "projected": 0.0, "actual": 0.0},
        {"category": "Housing",               "subcategory": "Electricity",          "projected": 0.0, "actual": 0.0},
        {"category": "Housing",               "subcategory": "Gas",                  "projected": 0.0, "actual": 0.0},
        {"category": "Housing",               "subcategory": "Water and Sewer",      "projected": 0.0, "actual": 0.0},
        {"category": "Housing",               "subcategory": "Cable / WiFi",         "projected": 0.0, "actual": 0.0},
        {"category": "Housing",               "subcategory": "Waste Removal",        "projected": 0.0, "actual": 0.0},
        {"category": "Housing",               "subcategory": "Maintenance / Repairs","projected": 0.0, "actual": 0.0},
        {"category": "Transportation",        "subcategory": "Vehicle Payment",      "projected": 0.0, "actual": 0.0},
        {"category": "Transportation",        "subcategory": "Insurance",            "projected": 0.0, "actual": 0.0},
        {"category": "Transportation",        "subcategory": "Fuel",                 "projected": 0.0, "actual": 0.0},
        {"category": "Transportation",        "subcategory": "Maintenance",          "projected": 0.0, "actual": 0.0},
        {"category": "Insurance",             "subcategory": "Renters",              "projected": 0.0, "actual": 0.0},
        {"category": "Insurance",             "subcategory": "Health",               "projected": 0.0, "actual": 0.0},
        {"category": "Food",                  "subcategory": "Groceries",            "projected": 0.0, "actual": 0.0},
        {"category": "Food",                  "subcategory": "Dining Out",           "projected": 0.0, "actual": 0.0},
        {"category": "Pets",                  "subcategory": "Food",                 "projected": 0.0, "actual": 0.0},
        {"category": "Pets",                  "subcategory": "Medical",              "projected": 0.0, "actual": 0.0},
        {"category": "Personal Care",         "subcategory": "Medical",              "projected": 0.0, "actual": 0.0},
        {"category": "Personal Care",         "subcategory": "Hair / Nails",         "projected": 0.0, "actual": 0.0},
        {"category": "Entertainment",         "subcategory": "Night Out",            "projected": 0.0, "actual": 0.0},
        {"category": "Entertainment",         "subcategory": "Subscriptions",        "projected": 0.0, "actual": 0.0},
        {"category": "Loans",                 "subcategory": "Credit Card",          "projected": 0.0, "actual": 0.0},
        {"category": "Savings / Investments", "subcategory": "Roth IRA",             "projected": 0.0, "actual": 0.0},
        {"category": "Savings / Investments", "subcategory": "Retirement Account",   "projected": 0.0, "actual": 0.0},
    ]

    if "manual_expenses" not in st.session_state:
        st.session_state["manual_expenses"] = _DEFAULT_EXPENSES.copy()

    all_cats_manual = sorted({
        "Housing", "Transportation", "Insurance", "Food", "Pets",
        "Personal Care", "Entertainment", "Loans", "Taxes",
        "Savings / Investments", "Gifts & Donations", "Legal", "Other",
    } | {c for c, _ in _get_existing_categories()})

    manual_exp_df = pd.DataFrame(st.session_state["manual_expenses"])
    edited_manual_expenses = st.data_editor(
        manual_exp_df,
        column_config={
            "category":    st.column_config.SelectboxColumn(
                "Category", options=all_cats_manual, required=True, width="medium"
            ),
            "subcategory": st.column_config.TextColumn("Subcategory", width="large"),
            "projected":   st.column_config.NumberColumn("Projected ($)", format="$%.2f", min_value=0),
            "actual":      st.column_config.NumberColumn("Actual ($)",    format="$%.2f", min_value=0),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="manual_expense_editor",
    )

    # ── AI Suggest for manual entry ───────────────────────────────────────────
    st.markdown("---")
    with st.expander("🤖 AI Budget Suggestions", expanded=False):
        st.markdown(
            "Describe your lifestyle and Claude will suggest realistic projected amounts "
            "for each expense category."
        )
        lifestyle_desc = st.text_area(
            "Describe your situation",
            placeholder=(
                "e.g. 'Single person in Atlanta, renting a 1BR apartment for $1,400/mo, "
                "drive a paid-off car, eat out 3x/week, gym membership, Netflix & Spotify'"
            ),
            height=100,
            key="lifestyle_desc",
        )
        if st.button("🤖 Get AI Budget Suggestions", type="primary", key="btn_ai_suggest_manual"):
            api_key = (
                st.session_state.get("api_key")
                or os.environ.get("ANTHROPIC_API_KEY", "")
                or get_setting("anthropic_api_key", "")
            )
            if not api_key:
                st.warning("No Anthropic API key found. Add one on the AI Insights page.")
            elif not lifestyle_desc.strip():
                st.warning("Please describe your situation first.")
            else:
                cat_list = "\n".join(
                    f"  - {r['category']} › {r['subcategory']}"
                    for r in edited_manual_expenses.to_dict("records")
                    if r.get("category") and r.get("subcategory")
                )
                prompt = (
                    f"I'm building a personal monthly budget. Here's my situation:\n{lifestyle_desc}\n\n"
                    f"My expense categories are:\n{cat_list}\n\n"
                    "For each category, suggest a realistic monthly projected amount in USD. "
                    "Reply in this exact format (one line per category):\n"
                    "CATEGORY: <category> › <subcategory> → AMOUNT: <number>\n"
                    "Only output those lines. Use 0 for categories that don't apply."
                )
                try:
                    import anthropic
                    client  = anthropic.Anthropic(api_key=api_key)
                    message = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=512,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = message.content[0].text
                    # Parse response
                    pattern = re.compile(
                        r"CATEGORY:\s*(.+?)\s*›\s*(.+?)\s*→\s*AMOUNT:\s*([\d,.]+)",
                        re.IGNORECASE,
                    )
                    suggestions: dict[tuple[str, str], float] = {}
                    for line in raw.strip().split("\n"):
                        m = pattern.match(line.strip())
                        if m:
                            cat = m.group(1).strip()
                            sub = m.group(2).strip()
                            amt = float(m.group(3).replace(",", ""))
                            suggestions[(cat, sub)] = amt

                    if suggestions:
                        # Apply to the expense table
                        updated = edited_manual_expenses.to_dict("records")
                        applied = 0
                        for row in updated:
                            key = (row.get("category", ""), row.get("subcategory", ""))
                            if key in suggestions:
                                row["projected"] = suggestions[key]
                                applied += 1
                        st.session_state["manual_expenses"] = updated
                        st.success(f"✅ Claude suggested amounts for {applied} categories!")
                        st.rerun()
                    else:
                        st.warning("Claude's response didn't match the expected format. Try rephrasing.")
                except Exception as e:
                    st.error(f"AI suggestion failed: {e}")

    # ── Summary ───────────────────────────────────────────────────────────────
    st.markdown("---")
    total_inc_m  = edited_manual_income["amount"].sum()  if not edited_manual_income.empty  else 0
    total_proj_m = edited_manual_expenses["projected"].sum() if not edited_manual_expenses.empty else 0
    total_act_m  = edited_manual_expenses["actual"].sum()    if not edited_manual_expenses.empty else 0
    balance_m    = total_inc_m - total_act_m

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Income",       f"${total_inc_m:,.2f}")
    c2.metric("📋 Projected",    f"${total_proj_m:,.2f}")
    c3.metric("💳 Actual Spent", f"${total_act_m:,.2f}")
    c4.metric("🏦 Remaining",    f"${balance_m:,.2f}")

    # ── Save ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    overwrite_manual = st.checkbox(
        "🗑️ Replace existing data for this month",
        value=False,
        key="overwrite_manual",
        help="If checked, existing income and expense rows for this month are deleted before saving.",
    )

    col_save, col_reset = st.columns([2, 1])
    with col_save:
        if st.button("💾 Save Budget", type="primary", key="btn_save_manual"):
            income_list  = [r for r in edited_manual_income.to_dict("records")  if float(r.get("amount", 0) or 0) > 0]
            expense_list = [r for r in edited_manual_expenses.to_dict("records") if r.get("category") and r.get("subcategory")]

            if not income_list and not expense_list:
                st.error("Nothing to save — all amounts are zero.")
            else:
                inc_n, exp_n = _save_to_db(selected_month, income_list, expense_list, overwrite_manual)
                st.success(f"✅ Saved **{inc_n} income** and **{exp_n} expense** rows for {month_label}!")
                st.balloons()
                # Reset form state
                st.session_state.pop("manual_income",   None)
                st.session_state.pop("manual_expenses", None)
                _get_existing_categories.clear()
                st.rerun()

    with col_reset:
        if st.button("🔄 Reset Form", key="btn_reset_manual"):
            st.session_state.pop("manual_income",   None)
            st.session_state.pop("manual_expenses", None)
            st.rerun()

# ── Footer: quick links ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "After saving, head to **[Expenses](pages/1_expenses.py)** to fine-tune individual rows, "
    "or **[AI Insights](pages/7_ai_insights.py)** for a full analysis of your month."
)
