import streamlit as st
import datetime
from decimal import Decimal
import json

st.set_page_config(page_title="Subscription Tracker", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL,
                cost DECIMAL(10,2) NOT NULL,
                billing_cycle VARCHAR(50) NOT NULL,
                next_renewal DATE NOT NULL,
                category VARCHAR(100),
                status VARCHAR(50) DEFAULT 'active',
                notes TEXT,
                price_history JSONB DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_next_renewal ON subscriptions(next_renewal)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cost REAL NOT NULL,
                billing_cycle TEXT NOT NULL,
                next_renewal DATE NOT NULL,
                category TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT,
                price_history TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    cur.close()
    conn.close()

_ensure_tables()

BILLING_CYCLES = ["monthly", "yearly", "weekly", "quarterly", "bi-monthly", "bi-yearly"]
CATEGORIES = ["Entertainment", "Productivity", "Health & Fitness", "News & Media", "Cloud Storage", 
              "Music", "Gaming", "Education", "Finance", "Software", "Utilities", "Other"]
STATUSES = ["active", "paused", "cancelled", "trial"]

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_subscriptions(user_id, status_filter=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if status_filter and status_filter != "all":
        query = f"SELECT * FROM subscriptions WHERE user_id = {ph} AND status = {ph} ORDER BY next_renewal ASC"
        cur.execute(query, (user_id, status_filter))
    else:
        query = f"SELECT * FROM subscriptions WHERE user_id = {ph} ORDER BY next_renewal ASC"
        cur.execute(query, (user_id,))
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_subscription_by_id(sub_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM subscriptions WHERE id = {ph}", (sub_id,))
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return dict(zip(columns, row))
    return None

def add_subscription(user_id, name, cost, billing_cycle, next_renewal, category, status, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    price_history = json.dumps([{"date": str(datetime.date.today()), "cost": float(cost)}])
    cur.execute(f"""
        INSERT INTO subscriptions (user_id, name, cost, billing_cycle, next_renewal, category, status, notes, price_history)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, name, cost, billing_cycle, next_renewal, category, status, notes, price_history))
    conn.commit()
    cur.close()
    conn.close()

def update_subscription(sub_id, name, cost, billing_cycle, next_renewal, category, status, notes, old_cost=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if old_cost and float(old_cost) != float(cost):
        cur.execute(f"SELECT price_history FROM subscriptions WHERE id = {ph}", (sub_id,))
        row = cur.fetchone()
        if row:
            try:
                history = json.loads(row[0]) if row[0] else []
            except:
                history = []
            history.append({"date": str(datetime.date.today()), "cost": float(cost)})
            price_history = json.dumps(history)
            cur.execute(f"""
                UPDATE subscriptions 
                SET name = {ph}, cost = {ph}, billing_cycle = {ph}, next_renewal = {ph}, 
                    category = {ph}, status = {ph}, notes = {ph}, price_history = {ph},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = {ph}
            """, (name, cost, billing_cycle, next_renewal, category, status, notes, price_history, sub_id))
    else:
        cur.execute(f"""
            UPDATE subscriptions 
            SET name = {ph}, cost = {ph}, billing_cycle = {ph}, next_renewal = {ph}, 
                category = {ph}, status = {ph}, notes = {ph}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {ph}
        """, (name, cost, billing_cycle, next_renewal, category, status, notes, sub_id))
    
    conn.commit()
    cur.close()
    conn.close()

def delete_subscription(sub_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM subscriptions WHERE id = {ph}", (sub_id,))
    conn.commit()
    cur.close()
    conn.close()

def calculate_next_renewal(current_date, billing_cycle):
    if billing_cycle == "weekly":
        return current_date + datetime.timedelta(weeks=1)
    elif billing_cycle == "bi-monthly":
        return current_date + datetime.timedelta(days=60)
    elif billing_cycle == "monthly":
        month = current_date.month + 1
        year = current_date.year
        if month > 12:
            month = 1
            year += 1
        day = min(current_date.day, 28)
        return datetime.date(year, month, day)
    elif billing_cycle == "quarterly":
        month = current_date.month + 3
        year = current_date.year
        while month > 12:
            month -= 12
            year += 1
        day = min(current_date.day, 28)
        return datetime.date(year, month, day)
    elif billing_cycle == "bi-yearly":
        month = current_date.month + 6
        year = current_date.year
        while month > 12:
            month -= 12
            year += 1
        day = min(current_date.day, 28)
        return datetime.date(year, month, day)
    elif billing_cycle == "yearly":
        return datetime.date(current_date.year + 1, current_date.month, min(current_date.day, 28))
    return current_date + datetime.timedelta(days=30)

def get_monthly_cost(cost, billing_cycle):
    cost = float(cost)
    if billing_cycle == "weekly":
        return cost * 4.33
    elif billing_cycle == "bi-monthly":
        return cost / 2
    elif billing_cycle == "monthly":
        return cost
    elif billing_cycle == "quarterly":
        return cost / 3
    elif billing_cycle == "bi-yearly":
        return cost / 6
    elif billing_cycle == "yearly":
        return cost / 12
    return cost

def get_annual_cost(cost, billing_cycle):
    return get_monthly_cost(cost, billing_cycle) * 12

def days_until_renewal(next_renewal):
    if isinstance(next_renewal, str):
        next_renewal = datetime.datetime.strptime(next_renewal, "%Y-%m-%d").date()
    today = datetime.date.today()
    return (next_renewal - today).days

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("📺 Subscription Tracker")
st.markdown("Track all your recurring subscriptions, monitor spending, and get renewal alerts.")

user_id = get_user_id()

if "edit_subscription_id" not in st.session_state:
    st.session_state.edit_subscription_id = None
if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False

subscriptions = get_subscriptions(user_id)
active_subs = [s for s in subscriptions if s["status"] == "active"]

total_monthly = sum(get_monthly_cost(s["cost"], s["billing_cycle"]) for s in active_subs)
total_annual = total_monthly * 12
upcoming_renewals = [s for s in active_subs if days_until_renewal(s["next_renewal"]) <= 7]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Monthly Cost", f"${total_monthly:.2f}")
with col2:
    st.metric("Annual Cost", f"${total_annual:.2f}")
with col3:
    st.metric("Active Subscriptions", len(active_subs))
with col4:
    st.metric("Renewals This Week", len(upcoming_renewals))

if upcoming_renewals:
    st.warning("⚠️ **Upcoming Renewals**")
    for sub in upcoming_renewals:
        days = days_until_renewal(sub["next_renewal"])
        if days <= 0:
            st.error(f"🔴 **{sub['name']}** - ${float(sub['cost']):.2f} - Due today or overdue!")
        elif days <= 3:
            st.warning(f"🟠 **{sub['name']}** - ${float(sub['cost']):.2f} - Renews in {days} day(s)")
        else:
            st.info(f"🟡 **{sub['name']}** - ${float(sub['cost']):.2f} - Renews in {days} day(s)")

st.markdown("---")

col_left, col_right = st.columns([2, 1])

with col_right:
    st.subheader("➕ Add Subscription")
    
    with st.form("add_subscription_form", clear_on_submit=True):
        new_name = st.text_input("Subscription Name*", placeholder="Netflix, Spotify, etc.")
        new_cost = st.number_input("Cost*", min_value=0.0, step=0.01, format="%.2f")
        new_billing = st.selectbox("Billing Cycle*", BILLING_CYCLES)
        new_renewal = st.date_input("Next Renewal Date*", value=datetime.date.today())
        new_category = st.selectbox("Category", CATEGORIES)
        new_status = st.selectbox("Status", STATUSES, index=0)
        new_notes = st.text_area("Notes", placeholder="Optional notes...")
        
        submitted = st.form_submit_button("Add Subscription", use_container_width=True)
        
        if submitted:
            if not new_name:
                st.error("Subscription name is required!")
            elif new_cost <= 0:
                st.error("Cost must be greater than 0!")
            else:
                add_subscription(user_id, new_name, new_cost, new_billing, new_renewal, 
                               new_category, new_status, new_notes)
                st.success(f"✅ Added {new_name}!")
                st.rerun()

with col_left:
    st.subheader("📋 Your Subscriptions")
    
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.selectbox("Filter by Status", ["all", "active", "paused", "cancelled", "trial"])
    with filter_col2:
        category_filter = st.selectbox("Filter by Category", ["all"] + CATEGORIES)
    
    filtered_subs = get_subscriptions(user_id, status_filter if status_filter != "all" else None)
    if category_filter != "all":
        filtered_subs = [s for s in filtered_subs if s.get("category") == category_filter]
    
    if not filtered_subs:
        st.info("No subscriptions found. Add your first subscription above!")
    else:
        for sub in filtered_subs:
            days = days_until_renewal(sub["next_renewal"])
            monthly = get_monthly_cost(sub["cost"], sub["billing_cycle"])
            
            status_emoji = {"active": "🟢", "paused": "⏸️", "cancelled": "🔴", "trial": "🆓"}.get(sub["status"], "❓")
            
            with st.expander(f"{status_emoji} **{sub['name']}** - ${float(sub['cost']):.2f}/{sub['billing_cycle']} ({sub.get('category', 'Uncategorized')})"):
                info_col1, info_col2, info_col3 = st.columns(3)
                with info_col1:
                    st.write(f"**Monthly Cost:** ${monthly:.2f}")
                    st.write(f"**Annual Cost:** ${monthly * 12:.2f}")
                with info_col2:
                    st.write(f"**Next Renewal:** {sub['next_renewal']}")
                    if days <= 0:
                        st.write("**Days Until:** ⚠️ Due!")
                    else:
                        st.write(f"**Days Until:** {days}")
                with info_col3:
                    st.write(f"**Status:** {sub['status'].title()}")
                    st.write(f"**Billing:** {sub['billing_cycle'].title()}")
                
                if sub.get("notes"):
                    st.write(f"**Notes:** {sub['notes']}")
                
                try:
                    history = json.loads(sub.get("price_history", "[]")) if sub.get("price_history") else []
                    if len(history) > 1:
                        st.write("**Price History:**")
                        for entry in history[-5:]:
                            st.write(f"  • {entry['date']}: ${entry['cost']:.2f}")
                except:
                    pass
                
                edit_col1, edit_col2, edit_col3 = st.columns(3)
                with edit_col1:
                    if st.button("✏️ Edit", key=f"edit_{sub['id']}"):
                        st.session_state.edit_subscription_id = sub["id"]
                with edit_col2:
                    if st.button("🔄 Mark Renewed", key=f"renew_{sub['id']}"):
                        new_date = calculate_next_renewal(datetime.date.today(), sub["billing_cycle"])
                        update_subscription(sub["id"], sub["name"], sub["cost"], sub["billing_cycle"],
                                          new_date, sub.get("category"), sub["status"], sub.get("notes"))
                        st.success(f"Renewed! Next date: {new_date}")
                        st.rerun()
                with edit_col3:
                    if st.button("🗑️ Delete", key=f"delete_{sub['id']}"):
                        delete_subscription(sub["id"])
                        st.success(f"Deleted {sub['name']}")
                        st.rerun()

if st.session_state.edit_subscription_id:
    sub = get_subscription_by_id(st.session_state.edit_subscription_id)
    if sub:
        st.markdown("---")
        st.subheader(f"✏️ Edit: {sub['name']}")
        
        with st.form("edit_subscription_form"):
            edit_name = st.text_input("Subscription Name*", value=sub["name"])
            edit_cost = st.number_input("Cost*", min_value=0.0, step=0.01, format="%.2f", value=float(sub["cost"]))
            edit_billing = st.selectbox("Billing Cycle*", BILLING_CYCLES, 
                                       index=BILLING_CYCLES.index(sub["billing_cycle"]) if sub["billing_cycle"] in BILLING_CYCLES else 0)
            
            renewal_date = sub["next_renewal"]
            if isinstance(renewal_date, str):
                renewal_date = datetime.datetime.strptime(renewal_date, "%Y-%m-%d").date()
            edit_renewal = st.date_input("Next Renewal Date*", value=renewal_date)
            
            edit_category = st.selectbox("Category", CATEGORIES,
                                        index=CATEGORIES.index(sub.get("category", "Other")) if sub.get("category") in CATEGORIES else len(CATEGORIES)-1)
            edit_status = st.selectbox("Status", STATUSES,
                                      index=STATUSES.index(sub["status"]) if sub["status"] in STATUSES else 0)
            edit_notes = st.text_area("Notes", value=sub.get("notes", "") or "")
            
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    update_subscription(sub["id"], edit_name, edit_cost, edit_billing, edit_renewal,
                                      edit_category, edit_status, edit_notes, old_cost=sub["cost"])
                    st.success("Updated!")
                    st.session_state.edit_subscription_id = None
                    st.rerun()
            with col_cancel:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.edit_subscription_id = None
                    st.rerun()

st.markdown("---")
st.subheader("📊 Spending Analytics")

if active_subs:
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.write("**Cost by Category**")
        category_costs = {}
        for sub in active_subs:
            cat = sub.get("category", "Other") or "Other"
            monthly = get_monthly_cost(sub["cost"], sub["billing_cycle"])
            category_costs[cat] = category_costs.get(cat, 0) + monthly
        
        if category_costs:
            import pandas as pd
            cat_df = pd.DataFrame([
                {"Category": k, "Monthly Cost": v} 
                for k, v in sorted(category_costs.items(), key=lambda x: -x[1])
            ])
            st.bar_chart(cat_df.set_index("Category"))
    
    with chart_col2:
        st.write("**Top Subscriptions by Cost**")
        sorted_subs = sorted(active_subs, key=lambda x: get_monthly_cost(x["cost"], x["billing_cycle"]), reverse=True)[:10]
        if sorted_subs:
            import pandas as pd
            sub_df = pd.DataFrame([
                {"Subscription": s["name"], "Monthly": get_monthly_cost(s["cost"], s["billing_cycle"])}
                for s in sorted_subs
            ])
            st.bar_chart(sub_df.set_index("Subscription"))
    
    st.write("**Monthly Breakdown**")
    breakdown_data = []
    for sub in active_subs:
        monthly = get_monthly_cost(sub["cost"], sub["billing_cycle"])
        breakdown_data.append({
            "Name": sub["name"],
            "Monthly Cost": f"${monthly:.2f}",
            "Annual Cost": f"${monthly * 12:.2f}",
            "Billing": sub["billing_cycle"].title(),
            "Category": sub.get("category", "Other"),
            "Next Renewal": str(sub["next_renewal"]),
            "Days Until": days_until_renewal(sub["next_renewal"])
        })
    
    if breakdown_data:
        import pandas as pd
        st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True, hide_index=True)
else:
    st.info("Add some subscriptions to see spending analytics!")

st.markdown("---")
st.caption("💡 Tip: Mark subscriptions as 'paused' or 'cancelled' to track them without including in cost calculations.")