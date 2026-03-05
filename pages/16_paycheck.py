import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, execute, seed_budget, seed_income
from utils.auth import require_login, render_sidebar_brand, render_sidebar_nav, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="Paycheck Allocator — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto"
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
default_idx = months.index(current_month) if current_month in months else 0
selected_month = st.sidebar.selectbox("📅 Month", months, index=default_idx)
seed_budget(selected_month)
seed_income(selected_month)

render_sidebar_nav()

render_sidebar_user_widget()

# ── Page header ───────────────────────────────────────────────────────────────
month_label = datetime.strptime(selected_month, "%Y-%m").strftime("%B %Y")
st.title("💸 Paycheck Allocator")
st.caption(
    "Got paid? Enter your take-home and auto-distribute it across your budget categories. "
    "Supports 50/30/20, 70/20/10, or fully custom splits."
)

# ── Load current month data ───────────────────────────────────────────────────
conn = get_conn()
expense_df = read_sql(
    "SELECT * FROM expenses WHERE month = ? ORDER BY category, subcategory",
    conn, params=(selected_month,)
)
income_df = read_sql(
    "SELECT * FROM income WHERE month = ?",
    conn, params=(selected_month,)
)
conn.close()

# ── Current month income summary ──────────────────────────────────────────────
total_income_logged = float(income_df["amount"].sum())
total_projected     = float(expense_df["projected"].sum())
total_actual        = float(expense_df["actual"].sum())

k1, k2, k3 = st.columns(3)
k1.metric("💵 Income Logged This Month", f"${total_income_logged:,.2f}")
k2.metric("📋 Total Projected Expenses", f"${total_projected:,.2f}")
k3.metric(
    "💰 Unallocated",
    f"${max(0, total_income_logged - total_projected):,.2f}",
    help="Income logged minus total projected expenses"
)

st.markdown("---")

# ── Step 1: Enter paycheck ────────────────────────────────────────────────────
st.subheader("Step 1 — Enter Your Paycheck")

col_pay, col_src = st.columns([2, 2])
with col_pay:
    paycheck_amount = st.number_input(
        "Take-Home Amount ($)",
        min_value=0.0,
        value=st.session_state.get("pa_paycheck_amount", 0.0),
        step=50.0,
        format="%.2f",
        help="Your net (post-tax) paycheck amount",
        key="pa_paycheck_amount"
    )
with col_src:
    paycheck_source = st.text_input(
        "Paycheck Source / Label",
        value=st.session_state.get("pa_paycheck_source", "Salary — Paycheck (Post-Tax)"),
        placeholder="e.g. Visa Paycheck 1, Freelance, RSU Vest",
        key="pa_paycheck_source"
    )

log_income_col, _ = st.columns([2, 2])
with log_income_col:
    if st.button("📥 Log This Paycheck to Income", type="secondary", use_container_width=True):
        if paycheck_amount > 0 and paycheck_source.strip():
            conn = get_conn()
            execute(conn,
                "INSERT INTO income (month, source, amount, notes) VALUES (?, ?, ?, ?)",
                (selected_month, paycheck_source.strip(), paycheck_amount,
                 f"Logged via Paycheck Allocator on {datetime.now().strftime('%Y-%m-%d')}")
            )
            conn.commit()
            conn.close()
            st.success(f"✅ Logged ${paycheck_amount:,.2f} from '{paycheck_source}' to Income!")
            st.rerun()
        else:
            st.error("Enter an amount and source label first.")

st.markdown("---")

# ── Step 2: Choose allocation strategy ───────────────────────────────────────
st.subheader("Step 2 — Choose Your Allocation Strategy")

STRATEGIES = {
    "50/30/20 — Needs / Wants / Savings": {
        "description": "Classic rule: 50% to needs (housing, bills, food), 30% to wants (dining, entertainment), 20% to savings & debt payoff.",
        "buckets": [
            {"name": "Needs",   "pct": 50, "categories": ["Housing", "Transportation", "Insurance", "Food", "Pets", "Personal Care", "Loans"]},
            {"name": "Wants",   "pct": 30, "categories": ["Entertainment", "Dining Out"]},
            {"name": "Savings", "pct": 20, "categories": ["Savings / Investments"]},
        ]
    },
    "70/20/10 — Living / Savings / Giving": {
        "description": "70% for monthly living expenses, 20% for savings & investments, 10% for debt or giving.",
        "buckets": [
            {"name": "Living",  "pct": 70, "categories": ["Housing", "Transportation", "Insurance", "Food", "Pets", "Personal Care", "Entertainment"]},
            {"name": "Savings", "pct": 20, "categories": ["Savings / Investments"]},
            {"name": "Debt / Giving", "pct": 10, "categories": ["Loans"]},
        ]
    },
    "80/20 — Simple Savings": {
        "description": "Keep it simple: save 20% off the top, spend the rest however you like.",
        "buckets": [
            {"name": "Spending", "pct": 80, "categories": ["Housing", "Transportation", "Insurance", "Food", "Pets", "Personal Care", "Entertainment", "Loans"]},
            {"name": "Savings",  "pct": 20, "categories": ["Savings / Investments"]},
        ]
    },
    "Custom Split": {
        "description": "Define your own percentages across Needs, Wants, and Savings.",
        "buckets": []  # filled in below
    },
    "Match Budget Projections": {
        "description": "Distribute the paycheck proportionally to match your existing projected expense amounts.",
        "buckets": []  # computed dynamically
    },
}

strategy_name = st.selectbox(
    "Allocation Strategy",
    list(STRATEGIES.keys()),
    key="pa_strategy"
)
strategy = STRATEGIES[strategy_name]
st.caption(strategy["description"])

# ── Custom split inputs ───────────────────────────────────────────────────────
custom_buckets = []
if strategy_name == "Custom Split":
    st.markdown("**Define your custom split (must total 100%):**")
    c1, c2, c3 = st.columns(3)
    with c1:
        needs_pct = st.number_input("Needs %",   min_value=0, max_value=100, value=50, step=5, key="pa_needs_pct")
    with c2:
        wants_pct = st.number_input("Wants %",   min_value=0, max_value=100, value=30, step=5, key="pa_wants_pct")
    with c3:
        savings_pct = st.number_input("Savings %", min_value=0, max_value=100, value=20, step=5, key="pa_savings_pct")

    total_pct = needs_pct + wants_pct + savings_pct
    if total_pct != 100:
        st.warning(f"⚠️ Percentages total {total_pct}% — must equal 100% to proceed.")
    else:
        st.success("✅ Percentages total 100%")

    custom_buckets = [
        {"name": "Needs",   "pct": needs_pct,   "categories": ["Housing", "Transportation", "Insurance", "Food", "Pets", "Personal Care", "Loans"]},
        {"name": "Wants",   "pct": wants_pct,   "categories": ["Entertainment"]},
        {"name": "Savings", "pct": savings_pct, "categories": ["Savings / Investments"]},
    ]

st.markdown("---")

# ── Step 3: Preview allocation ────────────────────────────────────────────────
st.subheader("Step 3 — Preview Allocation")

if paycheck_amount <= 0:
    st.info("👆 Enter your paycheck amount in Step 1 to see the allocation preview.")
    st.stop()

# ── Compute allocations ───────────────────────────────────────────────────────
categories_in_budget = expense_df["category"].unique().tolist()

def compute_allocations(paycheck: float, strat_name: str, strat: dict, custom: list, expense_df: pd.DataFrame) -> list[dict]:
    """
    Returns a list of dicts:
      { category, subcategory, id, current_projected, allocated_amount, new_projected }
    """
    results = []

    if strat_name == "Match Budget Projections":
        # Distribute proportionally to existing projected amounts
        total_proj = float(expense_df["projected"].sum())
        if total_proj <= 0:
            # Fallback: equal split across categories
            n = len(expense_df)
            per_row = paycheck / n if n > 0 else 0
            for _, row in expense_df.iterrows():
                results.append({
                    "category":          row["category"],
                    "subcategory":       row["subcategory"],
                    "id":                int(row["id"]),
                    "current_projected": float(row["projected"]),
                    "allocated_amount":  round(per_row, 2),
                    "new_projected":     round(per_row, 2),
                })
        else:
            for _, row in expense_df.iterrows():
                share = float(row["projected"]) / total_proj
                alloc = round(paycheck * share, 2)
                results.append({
                    "category":          row["category"],
                    "subcategory":       row["subcategory"],
                    "id":                int(row["id"]),
                    "current_projected": float(row["projected"]),
                    "allocated_amount":  alloc,
                    "new_projected":     alloc,
                })
        return results

    # For bucket-based strategies
    buckets = custom if strat_name == "Custom Split" else strat["buckets"]

    # Map each expense row to a bucket
    cat_to_bucket: dict[str, dict] = {}
    for bucket in buckets:
        for cat in bucket["categories"]:
            cat_to_bucket[cat] = bucket

    # Compute bucket totals (sum of projected in each bucket)
    bucket_proj_totals: dict[str, float] = {b["name"]: 0.0 for b in buckets}
    for _, row in expense_df.iterrows():
        bucket = cat_to_bucket.get(row["category"])
        if bucket:
            bucket_proj_totals[bucket["name"]] += float(row["projected"])

    # Allocate paycheck to each row proportionally within its bucket
    for _, row in expense_df.iterrows():
        bucket = cat_to_bucket.get(row["category"])
        if bucket is None:
            # Unmatched category — allocate 0
            results.append({
                "category":          row["category"],
                "subcategory":       row["subcategory"],
                "id":                int(row["id"]),
                "current_projected": float(row["projected"]),
                "allocated_amount":  0.0,
                "new_projected":     float(row["projected"]),
            })
            continue

        bucket_alloc = paycheck * (bucket["pct"] / 100.0)
        bucket_total = bucket_proj_totals[bucket["name"]]

        if bucket_total > 0:
            # Proportional within bucket
            share = float(row["projected"]) / bucket_total
            alloc = round(bucket_alloc * share, 2)
        else:
            # No existing projections in this bucket — split equally
            rows_in_bucket = expense_df[expense_df["category"].isin(bucket["categories"])]
            n = len(rows_in_bucket)
            alloc = round(bucket_alloc / n, 2) if n > 0 else 0.0

        results.append({
            "category":          row["category"],
            "subcategory":       row["subcategory"],
            "id":                int(row["id"]),
            "current_projected": float(row["projected"]),
            "allocated_amount":  alloc,
            "new_projected":     alloc,
        })

    return results


# Guard: custom split must total 100
if strategy_name == "Custom Split":
    total_pct = (
        st.session_state.get("pa_needs_pct", 50) +
        st.session_state.get("pa_wants_pct", 30) +
        st.session_state.get("pa_savings_pct", 20)
    )
    if total_pct != 100:
        st.warning("Fix your custom percentages above before previewing.")
        st.stop()

allocations = compute_allocations(
    paycheck_amount, strategy_name, strategy, custom_buckets, expense_df
)

# ── Bucket summary cards ──────────────────────────────────────────────────────
if strategy_name not in ("Match Budget Projections",):
    buckets_to_show = custom_buckets if strategy_name == "Custom Split" else strategy["buckets"]
    bucket_cols = st.columns(len(buckets_to_show))
    for i, bucket in enumerate(buckets_to_show):
        bucket_total = sum(
            a["allocated_amount"] for a in allocations
            if any(a["category"] == cat for cat in bucket["categories"])
        )
        bucket_cols[i].metric(
            f"{bucket['name']} ({bucket['pct']}%)",
            f"${bucket_total:,.2f}",
            help=f"Categories: {', '.join(bucket['categories'])}"
        )
    st.markdown("")

# ── Allocation table ──────────────────────────────────────────────────────────
alloc_df = pd.DataFrame(allocations)

# Allow user to tweak individual allocations
st.markdown("**Review & adjust individual allocations:**")
st.caption("You can edit the 'New Projected ($)' column to fine-tune before applying.")

display_alloc = alloc_df[["id", "category", "subcategory", "current_projected", "allocated_amount", "new_projected"]].copy()
display_alloc.columns = ["id", "Category", "Subcategory", "Current Projected", "Auto-Allocated", "New Projected ($)"]

edited_alloc = st.data_editor(
    display_alloc,
    column_config={
        "id":               st.column_config.NumberColumn("ID",               disabled=True, width="small"),
        "Category":         st.column_config.TextColumn("Category",           disabled=True),
        "Subcategory":      st.column_config.TextColumn("Subcategory",        disabled=True),
        "Current Projected":st.column_config.NumberColumn("Current ($)",      disabled=True, format="$%.2f"),
        "Auto-Allocated":   st.column_config.NumberColumn("Auto-Allocated ($)",disabled=True, format="$%.2f"),
        "New Projected ($)":st.column_config.NumberColumn("New Projected ($)", format="$%.2f", min_value=0.0),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="pa_alloc_editor"
)

# Running totals
new_total = float(edited_alloc["New Projected ($)"].sum())
unallocated = paycheck_amount - new_total

t1, t2, t3 = st.columns(3)
t1.metric("💸 Paycheck",          f"${paycheck_amount:,.2f}")
t2.metric("📋 Total Allocated",   f"${new_total:,.2f}")
delta_color = "normal" if unallocated >= 0 else "inverse"
t3.metric(
    "💰 Remaining / Over",
    f"${unallocated:,.2f}",
    delta=f"${unallocated:,.2f}",
    delta_color=delta_color,
    help="Positive = unallocated funds. Negative = over-allocated."
)

if abs(unallocated) > 0.01:
    if unallocated > 0:
        st.info(
            f"💡 You have **${unallocated:,.2f}** unallocated. "
            "Consider adding it to Savings / Investments or an emergency fund."
        )
    else:
        st.warning(
            f"⚠️ You've allocated **${abs(unallocated):,.2f} more** than your paycheck. "
            "Reduce some line items before applying."
        )

st.markdown("---")

# ── Step 4: Apply allocations ─────────────────────────────────────────────────
st.subheader("Step 4 — Apply to Budget")

col_apply, col_info = st.columns([2, 3])
with col_info:
    st.markdown(
        "Clicking **Apply** will update the **Projected** amounts in your Expenses table "
        f"for **{month_label}** to match the values in the 'New Projected ($)' column above. "
        "Your actual spending is not changed."
    )

with col_apply:
    apply_btn = st.button(
        f"✅ Apply Allocation to {month_label}",
        type="primary",
        use_container_width=True,
        key="pa_apply_btn"
    )

if apply_btn:
    if unallocated < -0.01:
        st.error("⚠️ You're over-allocated. Reduce line items before applying.")
    else:
        conn = get_conn()
        updated = 0
        for _, row in edited_alloc.iterrows():
            execute(conn,
                "UPDATE expenses SET projected = ? WHERE id = ?",
                (float(row["New Projected ($)"]), int(row["id"]))
            )
            updated += 1
        conn.commit()
        conn.close()
        st.success(
            f"🎉 Applied! Updated projected amounts for {updated} expense line(s) in {month_label}. "
            "Head to **Expenses** to review."
        )
        st.balloons()

st.markdown("---")

# ── Allocation history / past paychecks ──────────────────────────────────────
st.subheader("📜 Income Logged This Month")
st.caption("All income entries for the selected month. Use the Income page to edit or delete entries.")

if income_df.empty:
    st.info("No income logged yet for this month.")
else:
    display_income = income_df[["source", "amount", "notes"]].copy()
    display_income.columns = ["Source", "Amount ($)", "Notes"]
    display_income["Amount ($)"] = display_income["Amount ($)"].apply(lambda x: f"${x:,.2f}")
    st.dataframe(display_income, use_container_width=True, hide_index=True)
    st.metric("Total Income This Month", f"${total_income_logged:,.2f}")

st.markdown("---")

# ── Strategy explainer ────────────────────────────────────────────────────────
with st.expander("📖 Strategy Guide — Which split is right for me?"):
    st.markdown("""
**50/30/20 — The Classic**
- Best for: Most people starting out with budgeting
- 50% Needs: Rent, utilities, groceries, insurance, minimum debt payments
- 30% Wants: Dining out, entertainment, subscriptions, hobbies
- 20% Savings: Emergency fund, retirement, extra debt payoff
- *Tip: If your needs exceed 50%, look at housing or transportation costs first.*

---

**70/20/10 — The Saver**
- Best for: People with lower incomes or high fixed costs
- 70% Living: All monthly expenses (needs + wants combined)
- 20% Savings: Retirement, investments, emergency fund
- 10% Debt / Giving: Extra debt payments or charitable giving
- *Tip: Great if you're just starting to save and 50/30/20 feels too tight.*

---

**80/20 — Keep It Simple**
- Best for: People who hate detailed budgeting
- Save 20% first (automate it), then spend the rest freely
- *Tip: Automate the 20% transfer on payday so you never see it.*

---

**Match Budget Projections**
- Best for: When you already have a detailed budget set up
- Distributes your paycheck proportionally to your existing projected amounts
- *Tip: Use this after your first month to keep your budget realistic.*

---

**Custom Split**
- Best for: Unique situations (high debt, aggressive saving, variable income)
- You define the exact percentages for Needs, Wants, and Savings
- *Tip: Start with 50/30/20 and adjust 5% at a time until it fits your life.*
    """)
