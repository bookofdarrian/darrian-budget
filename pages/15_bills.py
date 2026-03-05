import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import re
from utils.db import get_conn, init_db, read_sql, execute, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_nav, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="Bill Calendar — Peach State Savings",
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

render_sidebar_nav()

render_sidebar_user_widget()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📅 Bill Calendar")
st.caption("See every recurring bill's due date, days remaining, and overdraft risk based on your NFCU balance.")

today = date.today()
sel_year  = int(selected_month[:4])
sel_month = int(selected_month[5:7])
_, days_in_month = calendar.monthrange(sel_year, sel_month)

# ── Load recurring templates ──────────────────────────────────────────────────
conn = get_conn()
templates_df = read_sql(
    "SELECT * FROM recurring_templates WHERE active = 1 ORDER BY due_day NULLS LAST, subcategory",
    conn
)
conn.close()

# ── NFCU Balance input (persisted in app_settings) ───────────────────────────
saved_balance_str = get_setting("nfcu_checking_balance", "0")
try:
    saved_balance = float(saved_balance_str)
except ValueError:
    saved_balance = 0.0

with st.expander("🏦 NFCU Checking Balance (for overdraft risk analysis)", expanded=True):
    col_bal, col_save = st.columns([3, 1])
    with col_bal:
        nfcu_balance = st.number_input(
            "Current NFCU Checking Balance ($)",
            min_value=0.0,
            value=saved_balance,
            step=50.0,
            format="%.2f",
            help="Enter your current NFCU checking balance. This is used to flag overdraft risk for upcoming bills.",
            key="nfcu_balance_input"
        )
    with col_save:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save Balance", type="primary"):
            set_setting("nfcu_checking_balance", str(nfcu_balance))
            st.success("Saved!")
            st.rerun()

st.markdown("---")

# ── Helper: compute due date for a bill in the selected month ─────────────────
def get_due_date(due_day: int | None, year: int, month: int) -> date | None:
    if due_day is None:
        return None
    # Clamp to last day of month (e.g. due_day=31 in February → Feb 28)
    last_day = calendar.monthrange(year, month)[1]
    clamped  = min(int(due_day), last_day)
    return date(year, month, clamped)


def days_until(due: date) -> int:
    return (due - today).days


def urgency_color(days: int) -> str:
    if days < 0:
        return "#888888"   # past
    elif days <= 3:
        return "#ff4b4b"   # red — urgent
    elif days <= 7:
        return "#ffa500"   # orange — soon
    elif days <= 14:
        return "#f0c040"   # yellow — upcoming
    else:
        return "#21c354"   # green — plenty of time


def urgency_emoji(days: int) -> str:
    if days < 0:
        return "✅"
    elif days <= 3:
        return "🔴"
    elif days <= 7:
        return "🟠"
    elif days <= 14:
        return "🟡"
    else:
        return "🟢"


# ── Build bill list with due dates ────────────────────────────────────────────
if templates_df.empty:
    st.info(
        "No recurring templates found. "
        "Go to **Expenses → Manage Recurring Expenses** to add your bills, "
        "then come back here to set their due dates."
    )
    st.stop()

# Enrich with due-date info
bills = []
for _, row in templates_df.iterrows():
    due_day = row.get("due_day")
    due_day = int(due_day) if pd.notna(due_day) and due_day is not None else None
    due_date = get_due_date(due_day, sel_year, sel_month)
    days_left = days_until(due_date) if due_date else None
    bills.append({
        "id":          int(row["id"]),
        "category":    row["category"],
        "subcategory": row["subcategory"],
        "amount":      float(row["projected"]),
        "due_day":     due_day,
        "due_date":    due_date,
        "days_left":   days_left,
    })

bills_with_due    = [b for b in bills if b["due_date"] is not None]
bills_without_due = [b for b in bills if b["due_date"] is None]

# Sort: upcoming first (by days_left), then past, then no-date
bills_with_due.sort(key=lambda b: b["days_left"] if b["days_left"] is not None else 9999)

# ── KPI strip ─────────────────────────────────────────────────────────────────
total_bills_amount = sum(b["amount"] for b in bills)
upcoming_7d        = [b for b in bills_with_due if b["days_left"] is not None and 0 <= b["days_left"] <= 7]
upcoming_7d_total  = sum(b["amount"] for b in upcoming_7d)
overdue            = [b for b in bills_with_due if b["days_left"] is not None and b["days_left"] < 0]

k1, k2, k3, k4 = st.columns(4)
k1.metric("📋 Total Recurring Bills", f"${total_bills_amount:,.2f}", help="Sum of all active recurring templates")
k2.metric("⚡ Due in Next 7 Days",    f"${upcoming_7d_total:,.2f}",  help="Bills due within the next 7 days")
k3.metric("🏦 NFCU Balance",          f"${nfcu_balance:,.2f}",       help="Your saved NFCU checking balance")

balance_after_7d = nfcu_balance - upcoming_7d_total
if nfcu_balance > 0:
    delta_color = "normal" if balance_after_7d >= 0 else "inverse"
    k4.metric(
        "💳 Balance After 7-Day Bills",
        f"${balance_after_7d:,.2f}",
        delta=f"${balance_after_7d - nfcu_balance:,.2f}",
        delta_color=delta_color
    )
else:
    k4.metric("💳 Balance After 7-Day Bills", "—", help="Enter your NFCU balance above")

st.markdown("---")

# ── Overdraft risk alert ──────────────────────────────────────────────────────
if nfcu_balance > 0 and bills_with_due:
    # Simulate running balance as bills come due (only future/today bills)
    future_bills = sorted(
        [b for b in bills_with_due if b["days_left"] is not None and b["days_left"] >= 0],
        key=lambda b: b["days_left"]
    )
    running = nfcu_balance
    risk_bills = []
    for b in future_bills:
        running -= b["amount"]
        if running < 0:
            risk_bills.append((b, running + b["amount"]))  # (bill, balance_before)

    if risk_bills:
        st.error(
            f"⚠️ **Overdraft Risk Detected!** Your NFCU balance of **${nfcu_balance:,.2f}** "
            f"may not cover all upcoming bills. You could go negative after paying "
            f"**{risk_bills[0][0]['subcategory']}** (${risk_bills[0][0]['amount']:,.2f}) "
            f"when your balance would be **${risk_bills[0][1]:,.2f}**."
        )
        with st.expander("📊 See full overdraft simulation"):
            running2 = nfcu_balance
            sim_rows = []
            for b in future_bills:
                running2 -= b["amount"]
                sim_rows.append({
                    "Bill":            b["subcategory"],
                    "Due":             b["due_date"].strftime("%-m/%-d") if b["due_date"] else "—",
                    "Amount":          f"${b['amount']:,.2f}",
                    "Balance After":   f"${running2:,.2f}",
                    "Status":          "🔴 NEGATIVE" if running2 < 0 else ("🟠 Low" if running2 < 200 else "✅ OK"),
                })
            st.dataframe(pd.DataFrame(sim_rows), use_container_width=True, hide_index=True)
    elif upcoming_7d_total > 0 and balance_after_7d < 200:
        st.warning(
            f"🟠 **Low Balance Warning** — After paying bills due in the next 7 days "
            f"(${upcoming_7d_total:,.2f}), your balance would drop to **${balance_after_7d:,.2f}**. "
            "Consider transferring funds before bills hit."
        )
    else:
        if nfcu_balance > 0:
            st.success(
                f"✅ **Balance looks healthy** — Your NFCU balance of **${nfcu_balance:,.2f}** "
                f"covers all upcoming bills with **${balance_after_7d:,.2f}** remaining after the next 7 days."
            )

st.markdown("---")

# ── Calendar grid view ────────────────────────────────────────────────────────
st.subheader(f"🗓️ {datetime(sel_year, sel_month, 1).strftime('%B %Y')} — Bill Calendar")

# Build a dict: day → list of bills
day_bills: dict[int, list] = {}
for b in bills_with_due:
    if b["due_date"] and b["due_date"].month == sel_month and b["due_date"].year == sel_year:
        d = b["due_date"].day
        day_bills.setdefault(d, []).append(b)

# Render a 7-column calendar grid using HTML
first_weekday = calendar.monthrange(sel_year, sel_month)[0]  # 0=Mon
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

cal_html = """
<style>
.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 16px;
}
.cal-header {
    background: #1e2330;
    color: #8892a4;
    text-align: center;
    padding: 6px 2px;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: 4px;
    letter-spacing: 0.05em;
}
.cal-day {
    background: #12151c;
    border: 1px solid #1e2330;
    border-radius: 6px;
    padding: 6px 4px;
    min-height: 72px;
    vertical-align: top;
    font-size: 0.78rem;
}
.cal-day.today {
    border-color: #FFAB76;
    background: #1a1208;
}
.cal-day.empty {
    background: transparent;
    border-color: transparent;
}
.cal-day-num {
    font-size: 0.72rem;
    color: #8892a4;
    margin-bottom: 3px;
    font-weight: 600;
}
.cal-day.today .cal-day-num {
    color: #FFAB76;
    font-weight: 800;
}
.cal-bill {
    display: block;
    border-radius: 3px;
    padding: 2px 4px;
    margin-bottom: 2px;
    font-size: 0.68rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #0e1117;
    font-weight: 600;
}
</style>
<div class="cal-grid">
"""

# Day-of-week headers
for dn in DAY_NAMES:
    cal_html += f'<div class="cal-header">{dn}</div>\n'

# Empty cells before first day
for _ in range(first_weekday):
    cal_html += '<div class="cal-day empty"></div>\n'

for day in range(1, days_in_month + 1):
    is_today = (today == date(sel_year, sel_month, day))
    today_cls = " today" if is_today else ""
    cal_html += f'<div class="cal-day{today_cls}"><div class="cal-day-num">{day}</div>\n'
    if day in day_bills:
        for b in day_bills[day]:
            dl = b["days_left"]
            color = urgency_color(dl if dl is not None else 99)
            name  = b["subcategory"][:16] + ("…" if len(b["subcategory"]) > 16 else "")
            cal_html += f'<span class="cal-bill" style="background:{color};" title="{b["subcategory"]} — ${b["amount"]:,.2f}">{name}</span>\n'
    cal_html += '</div>\n'

# Trailing empty cells
total_cells = first_weekday + days_in_month
remainder   = (7 - (total_cells % 7)) % 7
for _ in range(remainder):
    cal_html += '<div class="cal-day empty"></div>\n'

cal_html += "</div>"
st.markdown(cal_html, unsafe_allow_html=True)

# ── Color legend ──────────────────────────────────────────────────────────────
st.markdown(
    "🔴 Due ≤ 3 days &nbsp;&nbsp; 🟠 Due ≤ 7 days &nbsp;&nbsp; "
    "🟡 Due ≤ 14 days &nbsp;&nbsp; 🟢 Due > 14 days &nbsp;&nbsp; ✅ Already passed",
    unsafe_allow_html=True
)

st.markdown("---")

# ── Upcoming bills list ───────────────────────────────────────────────────────
st.subheader("⏰ Upcoming Bills — Countdown")

if not bills_with_due:
    st.info("No bills have due dates set yet. Use the editor below to add due days.")
else:
    for b in bills_with_due:
        dl = b["days_left"]
        emoji = urgency_emoji(dl)
        color = urgency_color(dl)

        if dl is None:
            label = "No due date"
        elif dl < 0:
            label = f"Due {abs(dl)} day{'s' if abs(dl) != 1 else ''} ago"
        elif dl == 0:
            label = "**Due TODAY**"
        elif dl == 1:
            label = "Due **tomorrow**"
        else:
            label = f"Due in **{dl} day{'s' if dl != 1 else ''}**"

        due_str = b["due_date"].strftime("%B %-d") if b["due_date"] else "—"

        col_emoji, col_name, col_date, col_label, col_amount = st.columns([0.5, 2.5, 1.5, 2, 1.5])
        col_emoji.markdown(f"<div style='font-size:1.3rem; padding-top:4px;'>{emoji}</div>", unsafe_allow_html=True)
        col_name.markdown(
            f"<div style='font-weight:600; color:#fafafa;'>{b['subcategory']}</div>"
            f"<div style='font-size:0.75rem; color:#8892a4;'>{b['category']}</div>",
            unsafe_allow_html=True
        )
        col_date.markdown(
            f"<div style='color:#8892a4; font-size:0.82rem; padding-top:4px;'>{due_str}</div>",
            unsafe_allow_html=True
        )
        col_label.markdown(
            f"<div style='color:{color}; font-size:0.85rem; padding-top:4px;'>{label}</div>",
            unsafe_allow_html=True
        )
        col_amount.markdown(
            f"<div style='font-weight:700; color:#fafafa; text-align:right; padding-top:4px;'>${b['amount']:,.2f}</div>",
            unsafe_allow_html=True
        )

if bills_without_due:
    with st.expander(f"⚠️ {len(bills_without_due)} bill(s) with no due date set"):
        for b in bills_without_due:
            st.markdown(f"- **{b['subcategory']}** ({b['category']}) — ${b['amount']:,.2f}")
        st.caption("Set due dates in the editor below.")

st.markdown("---")

# ── Due-date editor ───────────────────────────────────────────────────────────
st.subheader("✏️ Set Bill Due Dates")
st.caption(
    "Enter the day of the month each bill is due (1–31). "
    "Leave blank / 0 if the due date varies. Changes save immediately."
)

if templates_df.empty:
    st.info("No recurring templates found.")
else:
    # Build editable dataframe
    edit_rows = []
    for _, row in templates_df.iterrows():
        due_day_val = row.get("due_day")
        due_day_int = int(due_day_val) if pd.notna(due_day_val) and due_day_val is not None else 0
        edit_rows.append({
            "id":          int(row["id"]),
            "Category":    row["category"],
            "Bill":        row["subcategory"],
            "Amount ($)":  float(row["projected"]),
            "Due Day":     due_day_int,
        })

    edit_df = pd.DataFrame(edit_rows)

    edited = st.data_editor(
        edit_df[["id", "Category", "Bill", "Amount ($)", "Due Day"]],
        column_config={
            "id":         st.column_config.NumberColumn("ID",         disabled=True, width="small"),
            "Category":   st.column_config.TextColumn("Category",     disabled=True),
            "Bill":       st.column_config.TextColumn("Bill",         disabled=True),
            "Amount ($)": st.column_config.NumberColumn("Amount ($)", disabled=True, format="$%.2f"),
            "Due Day":    st.column_config.NumberColumn(
                "Due Day (1–31)",
                min_value=0,
                max_value=31,
                step=1,
                help="Day of month the bill is due. Set to 0 to clear.",
            ),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="due_day_editor"
    )

    if st.button("💾 Save Due Dates", type="primary"):
        conn = get_conn()
        saved_count = 0
        for _, row in edited.iterrows():
            due_val = int(row["Due Day"]) if row["Due Day"] and int(row["Due Day"]) > 0 else None
            execute(conn,
                "UPDATE recurring_templates SET due_day = ? WHERE id = ?",
                (due_val, int(row["id"]))
            )
            saved_count += 1
        conn.commit()
        conn.close()
        st.success(f"✅ Due dates saved for {saved_count} bill(s)!")
        st.rerun()

st.markdown("---")

# ── Smart Recurring Detection ─────────────────────────────────────────────────
st.subheader("🤖 Smart Recurring Detection")
st.caption(
    "Analyzes your imported bank transactions to find charges that appear in multiple months "
    "at a similar amount — and suggests adding them as recurring templates."
)

def _normalize_description(desc: str) -> str:
    """Strip trailing numbers/dates/IDs to group similar merchant names together."""
    d = desc.upper().strip()
    # Remove trailing reference numbers, dates, amounts
    d = re.sub(r'\s+\d{4,}$', '', d)          # trailing long numbers
    d = re.sub(r'\s+\d{1,2}/\d{1,2}$', '', d) # trailing dates like 02/25
    d = re.sub(r'\*\w+$', '', d)               # trailing *XXXXX codes
    d = re.sub(r'\s{2,}', ' ', d)              # collapse whitespace
    return d.strip()


def detect_recurring_candidates(min_months: int = 2, max_amount_variance_pct: float = 20.0) -> pd.DataFrame:
    """
    Scan bank_transactions for debits that appear in >= min_months distinct months
    with amount variance <= max_amount_variance_pct%.
    Returns a DataFrame of candidates with suggested category/amount/due_day.
    """
    conn = get_conn()
    txn_df = read_sql(
        "SELECT description, amount, month, date, category, subcategory "
        "FROM bank_transactions WHERE is_debit = 1 OR is_debit IS NULL",
        conn
    )
    conn.close()

    if txn_df.empty:
        return pd.DataFrame()

    # Normalize descriptions for grouping
    txn_df["norm_desc"] = txn_df["description"].apply(_normalize_description)

    # Group by normalized description
    candidates = []
    for norm_desc, group in txn_df.groupby("norm_desc"):
        months_seen = group["month"].nunique()
        if months_seen < min_months:
            continue

        amounts = group["amount"].dropna().astype(float)
        if amounts.empty:
            continue

        avg_amount = amounts.mean()
        min_amount = amounts.min()
        max_amount = amounts.max()

        # Skip if amount varies too wildly (likely not a fixed bill)
        if avg_amount > 0:
            variance_pct = ((max_amount - min_amount) / avg_amount) * 100
        else:
            continue

        if variance_pct > max_amount_variance_pct:
            continue

        # Skip very small amounts (< $1) — likely fees or rounding
        if avg_amount < 1.0:
            continue

        # Infer typical due day from the most common day-of-month
        try:
            days_of_month = group["date"].apply(
                lambda d: int(str(d)[8:10]) if len(str(d)) >= 10 else None
            ).dropna()
            typical_day = int(days_of_month.mode().iloc[0]) if not days_of_month.empty else None
        except Exception:
            typical_day = None

        # Use the most recent category if already categorized
        cat_vals = group["category"].dropna()
        sub_vals = group["subcategory"].dropna()
        suggested_cat = cat_vals.iloc[-1] if not cat_vals.empty else "Housing"
        suggested_sub = sub_vals.iloc[-1] if not sub_vals.empty else norm_desc.title()[:40]

        # Use the original (most recent) description as the label
        original_desc = group.sort_values("date", ascending=False)["description"].iloc[0]

        candidates.append({
            "description":     original_desc,
            "norm_desc":       norm_desc,
            "months_seen":     months_seen,
            "avg_amount":      round(avg_amount, 2),
            "variance_pct":    round(variance_pct, 1),
            "typical_due_day": typical_day,
            "suggested_cat":   suggested_cat,
            "suggested_sub":   suggested_sub,
        })

    if not candidates:
        return pd.DataFrame()

    df = pd.DataFrame(candidates).sort_values("avg_amount", ascending=False)
    return df


# Load existing template subcategories to filter out already-tracked bills
existing_subs = set(templates_df["subcategory"].str.upper().tolist()) if not templates_df.empty else set()

conn = get_conn()
txn_count_row = execute(conn, "SELECT COUNT(*) FROM bank_transactions WHERE is_debit = 1 OR is_debit IS NULL")
txn_count = txn_count_row.fetchone()[0]
conn.close()

if txn_count < 5:
    st.info(
        "📂 **Not enough transaction history yet.** Import at least 2 months of bank statements "
        "via **Bank Import** and this section will automatically detect recurring charges."
    )
else:
    col_thresh1, col_thresh2 = st.columns(2)
    with col_thresh1:
        min_months_filter = st.slider(
            "Minimum months seen", min_value=2, max_value=6, value=2,
            help="Only suggest bills that appear in at least this many months"
        )
    with col_thresh2:
        variance_filter = st.slider(
            "Max amount variance %", min_value=5, max_value=50, value=20,
            help="Higher = more lenient (catches bills with slight amount changes)"
        )

    candidates_df = detect_recurring_candidates(
        min_months=min_months_filter,
        max_amount_variance_pct=float(variance_filter)
    )

    if candidates_df.empty:
        st.success(
            "✅ No new recurring charges detected — either all your regular bills are already "
            "tracked as templates, or you need more transaction history."
        )
    else:
        # Filter out already-tracked bills (fuzzy match on normalized description)
        def _already_tracked(row) -> bool:
            norm = row["norm_desc"].upper()
            sub  = row["suggested_sub"].upper()
            # Check if any existing template subcategory is contained in the description or vice versa
            for existing in existing_subs:
                if existing in norm or norm in existing or existing in sub or sub in existing:
                    return True
            return False

        candidates_df["already_tracked"] = candidates_df.apply(_already_tracked, axis=1)
        new_candidates = candidates_df[~candidates_df["already_tracked"]].reset_index(drop=True)
        already_tracked = candidates_df[candidates_df["already_tracked"]]

        if not new_candidates.empty:
            st.markdown(
                f"**Found {len(new_candidates)} potential recurring charge(s)** not yet in your templates:"
            )

            # Build editable suggestion table
            suggest_rows = []
            for _, row in new_candidates.iterrows():
                suggest_rows.append({
                    "✓ Add":        False,
                    "Description":  row["description"][:50],
                    "Avg Amount":   row["avg_amount"],
                    "Months Seen":  int(row["months_seen"]),
                    "Variance %":   row["variance_pct"],
                    "Category":     row["suggested_cat"],
                    "Template Name":row["suggested_sub"][:40],
                    "Due Day":      int(row["typical_due_day"]) if row["typical_due_day"] else 0,
                    "_norm":        row["norm_desc"],
                })

            suggest_df = pd.DataFrame(suggest_rows)

            edited_suggestions = st.data_editor(
                suggest_df[[
                    "✓ Add", "Description", "Avg Amount", "Months Seen",
                    "Variance %", "Category", "Template Name", "Due Day"
                ]],
                column_config={
                    "✓ Add":         st.column_config.CheckboxColumn("Add?",          width="small"),
                    "Description":   st.column_config.TextColumn("Transaction",        disabled=True),
                    "Avg Amount":    st.column_config.NumberColumn("Avg ($)",          disabled=True, format="$%.2f"),
                    "Months Seen":   st.column_config.NumberColumn("Months",           disabled=True, width="small"),
                    "Variance %":    st.column_config.NumberColumn("Variance %",       disabled=True, format="%.1f%%"),
                    "Category":      st.column_config.TextColumn("Category",           help="Edit to change the budget category"),
                    "Template Name": st.column_config.TextColumn("Template Name",      help="Name for the recurring template"),
                    "Due Day":       st.column_config.NumberColumn(
                        "Due Day (1–31)",
                        min_value=0, max_value=31, step=1,
                        help="Inferred from typical transaction date. Set to 0 if variable."
                    ),
                },
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key="recurring_suggestions_editor"
            )

            selected_to_add = edited_suggestions[edited_suggestions["✓ Add"] == True]

            if not selected_to_add.empty:
                st.info(f"**{len(selected_to_add)} template(s) selected** — click below to add them.")

            if st.button(
                f"➕ Add {len(selected_to_add)} Selected as Recurring Templates",
                type="primary",
                disabled=selected_to_add.empty,
                key="btn_add_recurring"
            ):
                conn = get_conn()
                added = 0
                for _, row in selected_to_add.iterrows():
                    cat   = str(row["Category"]).strip() or "Housing"
                    sub   = str(row["Template Name"]).strip() or str(row["Description"])[:40]
                    amt   = float(row["Avg Amount"])
                    due_d = int(row["Due Day"]) if row["Due Day"] and int(row["Due Day"]) > 0 else None

                    # Check not already in templates
                    existing_check = execute(conn,
                        "SELECT id FROM recurring_templates WHERE subcategory = ?", (sub,)
                    ).fetchone()
                    if existing_check:
                        continue

                    execute(conn,
                        "INSERT INTO recurring_templates (category, subcategory, projected, active, due_day) "
                        "VALUES (?, ?, ?, 1, ?)",
                        (cat, sub, amt, due_d)
                    )
                    added += 1

                conn.commit()
                conn.close()
                st.success(
                    f"✅ Added {added} recurring template(s)! "
                    "They'll auto-fill into next month's expenses and appear in the calendar above."
                )
                st.rerun()

        else:
            st.success(
                "✅ All detected recurring charges are already tracked as templates. "
                "Your recurring expenses list looks complete!"
            )

        if not already_tracked.empty:
            with st.expander(f"ℹ️ {len(already_tracked)} charge(s) already tracked as templates"):
                for _, row in already_tracked.iterrows():
                    st.markdown(
                        f"- **{row['description'][:50]}** — "
                        f"${row['avg_amount']:,.2f}/mo · seen {row['months_seen']} months"
                    )

st.markdown("---")

# ── Monthly bill summary by category ─────────────────────────────────────────
st.subheader("📊 Bills by Category")
if not templates_df.empty:
    cat_summary = (
        templates_df.groupby("category")["projected"]
        .sum()
        .reset_index()
        .rename(columns={"category": "Category", "projected": "Monthly Total"})
        .sort_values("Monthly Total", ascending=False)
    )
    cat_summary["Monthly Total"] = cat_summary["Monthly Total"].apply(lambda x: f"${x:,.2f}")
    st.dataframe(cat_summary, use_container_width=True, hide_index=True)
