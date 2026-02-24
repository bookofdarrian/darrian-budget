import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.db import get_conn, init_db, read_sql, execute, fetchone
from utils.auth import require_password

st.set_page_config(page_title="Financial Goals", page_icon="🎯", layout="wide", initial_sidebar_state="auto")
init_db()
require_password()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("💰 Budget Dashboard")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth",         icon="💎")

st.title("🎯 Financial Goals")
st.caption("Track your financial goals, savings targets, and action items — yearly, quarterly, and monthly.")

# ── Constants ─────────────────────────────────────────────────────────────────
GOAL_TYPES = ["savings", "investment", "debt", "spending_limit", "habit", "other"]
GOAL_TYPE_ICONS = {
    "savings":        "💰",
    "investment":     "📈",
    "debt":           "💳",
    "spending_limit": "🛑",
    "habit":          "✅",
    "other":          "🎯",
}
PERIODS = ["yearly", "quarterly", "monthly", "one-time"]
PERIOD_LABELS = {
    "yearly":    "📅 Yearly",
    "quarterly": "🗓️ Quarterly",
    "monthly":   "📆 Monthly",
    "one-time":  "⭐ One-Time",
}

# ── Helper functions ──────────────────────────────────────────────────────────
def load_goals() -> pd.DataFrame:
    conn = get_conn()
    df = read_sql("SELECT * FROM financial_goals WHERE status = 'active' ORDER BY sort_order, id", conn)
    conn.close()
    return df

def load_checklist(goal_id: int) -> pd.DataFrame:
    conn = get_conn()
    df = read_sql("SELECT * FROM goal_checklist WHERE goal_id = ? ORDER BY sort_order, id", conn, params=(goal_id,))
    conn.close()
    return df

def progress_pct(current: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return min(100.0, (current / target) * 100)

def months_remaining(target_date_str: str) -> str:
    if not target_date_str:
        return ""
    try:
        td = datetime.strptime(str(target_date_str), "%Y-%m-%d").date()
        today = date.today()
        if td < today:
            return "⚠️ Past due"
        months = (td.year - today.year) * 12 + (td.month - today.month)
        if months == 0:
            return "Due this month"
        return f"{months} month{'s' if months != 1 else ''} left"
    except Exception:
        return ""

def monthly_needed(current: float, target: float, target_date_str: str) -> str:
    if not target_date_str or target <= 0:
        return ""
    try:
        td = datetime.strptime(str(target_date_str), "%Y-%m-%d").date()
        today = date.today()
        months = (td.year - today.year) * 12 + (td.month - today.month)
        if months <= 0:
            return ""
        remaining = max(0, target - current)
        per_month = remaining / months
        return f"${per_month:,.2f}/mo needed"
    except Exception:
        return ""

def render_goal_card(goal, tab_prefix: str = "all"):
    """Render a single goal card with progress, checklist, and edit form."""
    icon = GOAL_TYPE_ICONS.get(str(goal.get("goal_type", "other")), "🎯")
    pct = progress_pct(float(goal.get("current_amount") or 0), float(goal.get("target_amount") or 0))
    time_left = months_remaining(str(goal.get("target_date") or ""))
    mo_needed = monthly_needed(
        float(goal.get("current_amount") or 0),
        float(goal.get("target_amount") or 0),
        str(goal.get("target_date") or "")
    )

    with st.container():
        col_title, col_meta = st.columns([3, 1])
        with col_title:
            st.markdown(f"### {icon} {goal['title']}")
            if goal.get("description"):
                st.caption(str(goal["description"]))
        with col_meta:
            period_label = PERIOD_LABELS.get(str(goal.get("period", "yearly")), str(goal.get("period", "")))
            st.markdown(f"**{period_label}**")
            if goal.get("category"):
                st.caption(f"📂 {goal['category']}")
            if time_left:
                st.caption(time_left)

        target_amt = float(goal.get("target_amount") or 0)
        current_amt = float(goal.get("current_amount") or 0)

        if target_amt > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Target",     f"${target_amt:,.2f}")
            c2.metric("Progress",   f"${current_amt:,.2f}")
            c3.metric("% Complete", f"{pct:.0f}%")
            st.progress(pct / 100)
            if mo_needed:
                st.caption(f"📊 {mo_needed}")
        elif str(goal.get("goal_type", "")) in ("habit", "other"):
            st.caption("✅ Action-based goal — track via checklist below")

        # Checklist
        checklist = load_checklist(int(goal["id"]))
        if not checklist.empty:
            st.markdown("**Action Items:**")
            conn = get_conn()
            for _, item in checklist.iterrows():
                checked = st.checkbox(
                    str(item["item"]),
                    value=bool(item["completed"]),
                    key=f"chk_{tab_prefix}_{item['id']}"
                )
                if checked != bool(item["completed"]):
                    execute(conn, "UPDATE goal_checklist SET completed=? WHERE id=?",
                            (1 if checked else 0, int(item["id"])))
                    conn.commit()
            conn.close()

        # Edit / Update progress — unique key per tab + goal ID
        with st.expander("✏️ Update Progress / Edit", expanded=False):
            with st.form(key=f"edit_goal_{tab_prefix}_{goal['id']}"):
                new_current = st.number_input(
                    "Current Amount ($)",
                    value=current_amt,
                    min_value=0.0, step=50.0,
                    key=f"cur_{tab_prefix}_{goal['id']}"
                )
                new_desc = st.text_area("Description", value=str(goal.get("description") or ""), key=f"desc_{tab_prefix}_{goal['id']}")
                new_date = st.text_input("Target Date (YYYY-MM-DD)", value=str(goal.get("target_date") or ""), key=f"date_{tab_prefix}_{goal['id']}")
                col_save, col_complete, col_delete = st.columns(3)
                save_btn     = col_save.form_submit_button("💾 Save", type="primary")
                complete_btn = col_complete.form_submit_button("✅ Mark Complete")
                delete_btn   = col_delete.form_submit_button("🗑️ Delete")

                if save_btn:
                    conn = get_conn()
                    execute(conn,
                        "UPDATE financial_goals SET current_amount=?, description=?, target_date=? WHERE id=?",
                        (new_current, new_desc, new_date or None, int(goal["id"])))
                    conn.commit()
                    conn.close()
                    st.success("Updated!")
                    st.rerun()
                if complete_btn:
                    conn = get_conn()
                    execute(conn, "UPDATE financial_goals SET status='completed' WHERE id=?", (int(goal["id"]),))
                    conn.commit()
                    conn.close()
                    st.success("Goal marked complete! 🎉")
                    st.rerun()
                if delete_btn:
                    conn = get_conn()
                    execute(conn, "DELETE FROM goal_checklist WHERE goal_id=?", (int(goal["id"]),))
                    execute(conn, "DELETE FROM financial_goals WHERE id=?", (int(goal["id"]),))
                    conn.commit()
                    conn.close()
                    st.rerun()

        st.markdown("---")

# ── Seed default goals if none exist ─────────────────────────────────────────
def seed_default_goals():
    conn = get_conn()
    row = fetchone(conn, "SELECT COUNT(*) FROM financial_goals")
    count = row[0] if row else 0
    conn.close()
    if count > 0:
        return

    conn = get_conn()
    defaults = [
        ("Max Roth IRA Contributions",
         "Contribute the full $7,000 annual limit to Roth IRA via Fidelity",
         "investment", 7000.0, 0.0, f"{date.today().year}-12-31", "yearly", "Retirement", 1),
        ("Increase ESPP to 7%",
         "Increase Employee Stock Purchase Plan contribution from current rate to 7%",
         "investment", 0.0, 0.0, f"{date.today().year}-06-30", "one-time", "Work Benefits", 2),
        ("Store Medical Receipts (No HSA Debit Card)",
         "Save all medical receipts and reimburse from HSA manually — do not use HSA debit card directly",
         "habit", 0.0, 0.0, None, "yearly", "HSA", 3),
        ("Home Maintenance Fund (2% of Income)",
         "Build a home maintenance reserve equal to 2% of annual income (~$1,200/yr)",
         "savings", 1200.0, 0.0, f"{date.today().year}-12-31", "yearly", "Housing", 4),
    ]
    for title, desc, gtype, target, current, tdate, period, cat, sort in defaults:
        execute(conn,
            "INSERT INTO financial_goals (title, description, goal_type, target_amount, current_amount, target_date, period, category, sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, desc, gtype, target, current, tdate, period, cat, sort))
    conn.commit()

    # Add checklist to the HSA habit goal
    habit_row = fetchone(conn, "SELECT id FROM financial_goals WHERE goal_type='habit' AND title LIKE '%Medical%'")
    if habit_row:
        habit_id = habit_row[0]
        checklist_items = [
            "Set up a dedicated folder (physical or digital) for medical receipts",
            "Stop using HSA debit card for direct purchases",
            "Log each medical expense in the Receipts & HSA page",
            "Reimburse yourself from HSA quarterly",
        ]
        for i, item in enumerate(checklist_items):
            execute(conn, "INSERT INTO goal_checklist (goal_id, item, sort_order) VALUES (?,?,?)", (habit_id, item, i))
    conn.commit()
    conn.close()

seed_default_goals()

# ── Load all goals ────────────────────────────────────────────────────────────
goals_df = load_goals()

# ── Summary KPIs ──────────────────────────────────────────────────────────────
if not goals_df.empty:
    goals_with_target = goals_df[goals_df["target_amount"] > 0]
    total_target  = float(goals_with_target["target_amount"].sum())
    total_current = float(goals_with_target["current_amount"].sum())
    overall_pct   = progress_pct(total_current, total_target)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Active Goals",    len(goals_df))
    k2.metric("Total Target",    f"${total_target:,.2f}"  if total_target  > 0 else "—")
    k3.metric("Total Progress",  f"${total_current:,.2f}" if total_current > 0 else "—")
    k4.metric("Overall Progress", f"{overall_pct:.0f}%"   if total_target  > 0 else "—")
    st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_all, tab_yearly, tab_quarterly, tab_monthly, tab_onetime, tab_add = st.tabs([
    "📋 All Goals", "📅 Yearly", "🗓️ Quarterly", "📆 Monthly", "⭐ One-Time", "➕ Add Goal"
])

with tab_all:
    if goals_df.empty:
        st.info("No goals yet. Add your first goal in the **Add Goal** tab.")
    else:
        for _, goal in goals_df.iterrows():
            render_goal_card(goal, tab_prefix="all")

for tab_widget, period_key in [
    (tab_yearly,    "yearly"),
    (tab_quarterly, "quarterly"),
    (tab_monthly,   "monthly"),
    (tab_onetime,   "onetime"),
]:
    with tab_widget:
        if goals_df.empty:
            filtered = pd.DataFrame()
        else:
            filtered = goals_df[goals_df["period"] == period_key.replace("onetime", "one-time")]
        if filtered.empty:
            st.info(f"No {period_key} goals yet. Add one in the **Add Goal** tab.")
        else:
            for _, goal in filtered.iterrows():
                render_goal_card(goal, tab_prefix=period_key)

# ── Add Goal Tab ──────────────────────────────────────────────────────────────
with tab_add:
    st.subheader("➕ Add a New Financial Goal")
    with st.form("add_goal_form"):
        c1, c2 = st.columns(2)
        with c1:
            title       = st.text_input("Goal Title *", placeholder="e.g. Japan Trip Fund, Camera Gear, Max Roth IRA")
            goal_type   = st.selectbox("Goal Type", GOAL_TYPES,
                              format_func=lambda x: f"{GOAL_TYPE_ICONS[x]} {x.replace('_', ' ').title()}")
            period      = st.selectbox("Period", PERIODS, format_func=lambda x: PERIOD_LABELS[x])
            category    = st.text_input("Category (optional)", placeholder="e.g. Travel, Camera Gear, Retirement")
        with c2:
            target_amount  = st.number_input("Target Amount ($)", min_value=0.0, step=100.0,
                                              help="Set to 0 for habit/action goals with no dollar target")
            current_amount = st.number_input("Current Amount ($)", min_value=0.0, step=50.0)
            target_date    = st.date_input("Target Date", value=date(date.today().year, 12, 31))
            description    = st.text_area("Description / Notes", height=80)

        st.markdown("**Checklist Items** (one per line, optional):")
        checklist_text = st.text_area(
            "Checklist",
            placeholder="e.g.\nOpen Fidelity account\nSet up auto-contribution\nVerify contribution limit",
            height=100, label_visibility="collapsed"
        )

        submitted = st.form_submit_button("➕ Add Goal", type="primary")
        if submitted:
            if not title.strip():
                st.error("Title is required.")
            else:
                conn = get_conn()
                cur = execute(conn,
                    "INSERT INTO financial_goals (title, description, goal_type, target_amount, current_amount, target_date, period, category) VALUES (?,?,?,?,?,?,?,?)",
                    (title.strip(), description.strip(), goal_type, target_amount, current_amount,
                     str(target_date), period, category.strip()))
                new_id = cur.lastrowid
                if not new_id:
                    row = fetchone(conn, "SELECT id FROM financial_goals ORDER BY id DESC LIMIT 1")
                    new_id = row[0] if row else None
                if new_id and checklist_text.strip():
                    items = [line.strip() for line in checklist_text.strip().split("\n") if line.strip()]
                    for i, item in enumerate(items):
                        execute(conn, "INSERT INTO goal_checklist (goal_id, item, sort_order) VALUES (?,?,?)",
                                (new_id, item, i))
                conn.commit()
                conn.close()
                st.success(f"Goal '{title}' added!")
                st.rerun()

# ── Completed Goals ───────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🏆 Completed Goals"):
    conn = get_conn()
    completed = read_sql("SELECT * FROM financial_goals WHERE status = 'completed' ORDER BY id DESC", conn)
    conn.close()
    if completed.empty:
        st.info("No completed goals yet — keep going!")
    else:
        for _, goal in completed.iterrows():
            icon = GOAL_TYPE_ICONS.get(str(goal.get("goal_type", "other")), "🎯")
            st.markdown(f"✅ **{icon} {goal['title']}** — {goal.get('description', '')}")
