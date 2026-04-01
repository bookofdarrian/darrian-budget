"""
Page 92: CC Mentor Admin
Admin panel for Darrian to manage mentors, view system metrics, and configure alerts.

Darrian only. Restricted access.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json

st.set_page_config(
    page_title="Mentor Admin | College Confused",
    page_icon="🎓",
    layout="wide"
)

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.cc_speed_to_lead import _ensure_cc_stl_tables

init_db()
inject_css()
require_login()

# ─── Initialize Tables ──────────────────────────────────────────────────────

def _ensure_tables():
    """Ensure CC Speed to Lead tables exist."""
    conn = get_conn()
    _ensure_cc_stl_tables(conn)
    conn.close()

_ensure_tables()

# ─── Access Control ────────────────────────────────────────────────────────

DARRIAN_USER_ID = 1  # Darrian's hardcoded user ID

user_id = st.session_state.get("user_id")

if user_id != DARRIAN_USER_ID:
    st.error("🔒 Access Denied. This page is for Darrian only.")
    st.stop()

# ─── Sidebar ────────────────────────────────────────────────────────────────

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/80_cc_home.py", label="CC Home", icon="🎓")
st.sidebar.page_link("pages/81_cc_timeline.py", label="Timeline", icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py", label="Scholarships", icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py", label="Essay Station", icon="✍️")
st.sidebar.page_link("pages/84_cc_sat_act_prep.py", label="SAT/ACT Prep", icon="📝")
st.sidebar.page_link("pages/92_cc_mentor_admin.py", label="Mentor Admin", icon="🔧")
st.sidebar.markdown("---")
render_sidebar_user_widget()

# ─── Page Title ─────────────────────────────────────────────────────────────

st.title("🔧 Mentor & System Admin")
st.write("Manage mentors, view system metrics, and configure SLA alerts.")

# ─── Helper Functions ──────────────────────────────────────────────────────

def _load_mentors() -> list:
    """Load all mentors from database."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    rows = db_exec(conn, """
        SELECT id, name, email, timezone, bio, specialties, regions_covered, 
               max_students_per_month, current_month_load, active, created_at
        FROM cc_mentors
        ORDER BY current_month_load DESC
    """).fetchall()
    
    conn.close()
    
    mentors = []
    for row in rows:
        mentors.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "timezone": row[3],
            "bio": row[4],
            "specialties": json.loads(row[5] or "[]"),
            "regions_covered": json.loads(row[6] or "[]"),
            "max_students_per_month": row[7],
            "current_month_load": row[8],
            "active": row[9],
            "created_at": row[10]
        })
    
    return mentors

def _add_mentor(name: str, email: str, timezone: str, bio: str, max_load: int, 
                specialties: list, regions: list, active: bool = True):
    """Add a new mentor."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    try:
        db_exec(conn, f"""
            INSERT INTO cc_mentors (
                name, email, timezone, bio, specialties, regions_covered,
                max_students_per_month, active
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {1 if active else 0})
        """, (
            name, email, timezone, bio, json.dumps(specialties),
            json.dumps(regions), max_load
        ))
        conn.commit()
        conn.close()
        return True, "✅ Mentor added successfully!"
    except Exception as e:
        conn.close()
        return False, f"❌ Error adding mentor: {str(e)}"

def _update_mentor(mentor_id: int, **kwargs):
    """Update mentor fields."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    try:
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in ["name", "email", "timezone", "bio", "max_students_per_month", "active"]:
                if key == "specialties" or key == "regions_covered":
                    fields.append(f"{key} = {ph}")
                    values.append(json.dumps(value))
                else:
                    fields.append(f"{key} = {ph}")
                    values.append(value)
        
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(mentor_id)
            
            update_sql = f"UPDATE cc_mentors SET {', '.join(fields)} WHERE id = {ph}"
            db_exec(conn, update_sql, tuple(values))
            conn.commit()
        
        conn.close()
        return True, "✅ Mentor updated!"
    except Exception as e:
        conn.close()
        return False, f"❌ Error: {str(e)}"

def _reset_all_loads():
    """Reset current_month_load to 0 for all mentors."""
    conn = get_conn()
    
    try:
        db_exec(conn, """
            UPDATE cc_mentors SET current_month_load = 0, updated_at = CURRENT_TIMESTAMP
        """)
        conn.commit()
        conn.close()
        return True, "✅ All loads reset to 0!"
    except Exception as e:
        conn.close()
        return False, f"❌ Error: {str(e)}"

# ─── Section A: Manage Mentors ──────────────────────────────────────────────

st.subheader("Section A: Manage Mentors")

with st.expander("➕ Add New Mentor", expanded=False):
    with st.form("add_mentor_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            mentor_name = st.text_input("Mentor Name *", placeholder="e.g., Sarah Johnson")
            mentor_email = st.text_input("Email *", placeholder="sarah@collegeconfused.org")
            mentor_timezone = st.selectbox("Timezone", ["UTC", "EST", "CST", "MST", "PST"])
        
        with col2:
            max_load = st.number_input("Max Students/Month", min_value=1, max_value=50, value=10)
            mentor_active = st.checkbox("Active", value=True)
            mentor_bio = st.text_area("Bio (optional)", placeholder="Brief bio about mentor...")
        
        specialties = st.multiselect(
            "Specialties *",
            options=["college_list", "essays", "fafsa", "sat_act", "general"],
            default=[]
        )
        
        regions = st.multiselect(
            "Regions Covered *",
            options=["All States"] + [
                "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
                "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
                "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
                "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
                "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
                "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
                "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
                "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
                "Washington D.C.", "International"
            ],
            default=["All States"]
        )
        
        submitted = st.form_submit_button("💾 Save Mentor", type="primary")
        
        if submitted:
            if not mentor_name or not mentor_email or not specialties:
                st.error("❌ Please fill in all required fields.")
            else:
                success, message = _add_mentor(
                    name=mentor_name,
                    email=mentor_email,
                    timezone=mentor_timezone,
                    bio=mentor_bio,
                    max_load=max_load,
                    specialties=specialties,
                    regions=regions,
                    active=mentor_active
                )
                
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

# Mentor Roster Table
st.markdown("**Mentor Roster**")

mentors = _load_mentors()

if not mentors:
    st.info("📚 No mentors yet. Add one above!")
else:
    # Display as table + edit buttons
    df_data = []
    for m in mentors:
        status = "🟢 Active" if m['active'] else "🔴 Inactive"
        specialties_str = ", ".join(m['specialties']) if m['specialties'] else "None"
        regions_str = ", ".join(m['regions_covered'][:2]) + ("..." if len(m['regions_covered']) > 2 else "") if m['regions_covered'] else "None"
        
        df_data.append({
            "ID": m['id'],
            "Name": m['name'],
            "Email": m['email'],
            "Specialties": specialties_str,
            "Regions": regions_str,
            "Load": f"{m['current_month_load']}/{m['max_students_per_month']}",
            "Status": status
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Quick actions for each mentor
    st.write("**Quick Actions**")
    col1, col2 = st.columns(2)
    
    with col1:
        selected_mentor = st.selectbox(
            "Select mentor to edit/deactivate",
            options=[m['name'] for m in mentors],
            key="mentor_selector"
        )
        
        selected_m = next((m for m in mentors if m['name'] == selected_mentor), None)
        
        if selected_m:
            st.write(f"**{selected_m['name']}** (ID: {selected_m['id']})")
            st.write(f"Email: {selected_m['email']}")
            st.write(f"Current Load: {selected_m['current_month_load']}/{selected_m['max_students_per_month']}")
            
            if st.button(f"🔴 Deactivate {selected_m['name']}", type="secondary"):
                success, msg = _update_mentor(selected_m['id'], active=False)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    
    with col2:
        # Show all inquiries for this mentor
        if selected_m:
            ph = "%s" if USE_POSTGRES else "?"
            conn = get_conn()
            
            inq_rows = db_exec(conn, f"""
                SELECT COUNT(*) FROM cc_student_inquiries WHERE routed_to_mentor_id = {ph}
            """, (selected_m['id'],)).fetchone()
            
            conn.close()
            
            total_inquiries = inq_rows[0] if inq_rows else 0
            st.metric("Total Inquiries", total_inquiries)

# Load Reset
st.markdown("---")
st.subheader("Load Reset")

today = datetime.utcnow()
is_first_of_month = today.day == 1

if is_first_of_month:
    if st.button("🔄 Reset All Loads for New Month", type="primary"):
        st.warning("⚠️ Are you sure? This will reset current_month_load to 0 for ALL mentors.")
        if st.button("✅ Yes, reset now", type="secondary"):
            success, message = _reset_all_loads()
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
else:
    days_until = 32 - today.day
    st.info(f"📅 Load reset is available on the 1st of each month. {days_until} days until next reset.")

# ─── Section B: System Metrics ──────────────────────────────────────────────

st.markdown("---")
st.subheader("Section B: System Metrics")

conn = get_conn()
ph = "%s" if USE_POSTGRES else "?"

# Load KPIs
total_inquiries_row = db_exec(conn, "SELECT COUNT(*) FROM cc_student_inquiries").fetchone()
total_inquiries = total_inquiries_row[0]

qualified_row = db_exec(conn, """
    SELECT COUNT(*) FROM cc_student_inquiries WHERE qualification_status = 'qualified'
""").fetchone()
qualified_inquiries = qualified_row[0]

converted_row = db_exec(conn, """
    SELECT COUNT(*) FROM cc_student_inquiries WHERE student_booked_call = 1
""").fetchone()
converted = converted_row[0]

# Average response time
avg_response_row = db_exec(conn, """
    SELECT AVG(time_to_email_ms) FROM cc_inquiry_metrics WHERE time_to_email_ms IS NOT NULL
""").fetchone()
avg_response_ms = avg_response_row[0] if avg_response_row[0] else 0

conn.close()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Inquiries", total_inquiries)

with col2:
    qualified_rate = round((qualified_inquiries / total_inquiries * 100), 1) if total_inquiries > 0 else 0
    st.metric("Qualified Rate", f"{qualified_rate}%")

with col3:
    conversion_rate = round((converted / total_inquiries * 100), 1) if total_inquiries > 0 else 0
    st.metric("Conversion Rate", f"{conversion_rate}%")

with col4:
    avg_sec = round(avg_response_ms / 1000, 2)
    st.metric("Avg Response Time", f"{avg_sec}s", delta="<5min target")

st.markdown("---")

# Trend chart (last 30 days)
st.write("**Inquiry Trend (Last 30 Days)**")

conn = get_conn()

# Get daily inquiry counts for last 30 days
trend_rows = db_exec(conn, """
    SELECT DATE(created_at) as date, COUNT(*) as count
    FROM cc_student_inquiries
    WHERE created_at > datetime('now', '-30 days')
    GROUP BY DATE(created_at)
    ORDER BY DATE(created_at) ASC
""").fetchall()

conn.close()

if trend_rows:
    trend_df = pd.DataFrame(trend_rows, columns=["Date", "Inquiries"])
    
    fig = px.line(
        trend_df,
        x="Date",
        y="Inquiries",
        title="Daily Inquiries",
        markers=True,
        color_discrete_sequence=["#6C63FF"]
    )
    fig.update_layout(template="plotly_white", height=300)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📊 No data yet. Track will appear after first 30 days of inquiries.")

# ─── Section C: SLA Monitoring ──────────────────────────────────────────────

st.markdown("---")
st.subheader("Section C: SLA Monitoring")

with st.expander("⚙️ SLA Rules (Configure)", expanded=False):
    st.write("**Current SLA Rules:**")
    st.info("✅ Alert if response time > 5 minutes (300,000 ms)")
    st.info("✅ Alert if any inquiry unhandled for >24 hours")
    
    st.write("**Future:** Additional alert types coming soon (low mentor load, bounce rate, etc.)")

# Recent alerts
st.write("**Recent SLA Breaches (Last 7 Days)**")

conn = get_conn()
ph = "%s" if USE_POSTGRES else "?"

# Find inquiries with slow response
slow_response = db_exec(conn, """
    SELECT inq.id, inq.name, inq.email, m.time_to_email_ms, inq.created_at
    FROM cc_student_inquiries inq
    LEFT JOIN cc_inquiry_metrics m ON inq.id = m.inquiry_id
    WHERE m.time_to_email_ms > 300000
    AND inq.created_at > datetime('now', '-7 days')
    ORDER BY m.time_to_email_ms DESC
    LIMIT 10
""").fetchall()

# Find unhandled inquiries
unhandled = db_exec(conn, """
    SELECT id, name, email, created_at
    FROM cc_student_inquiries
    WHERE status = 'new'
    AND created_at < datetime('now', '-1 day')
    ORDER BY created_at ASC
    LIMIT 10
""").fetchall()

conn.close()

alerts = []

for row in slow_response:
    alerts.append({
        "Timestamp": row[4],
        "Student": row[1],
        "Issue": "Slow response time",
        "Details": f"{round(row[3]/1000, 1)}s",
        "Status": "Acknowledged"
    })

for row in unhandled:
    time_unhandled = (datetime.utcnow() - datetime.fromisoformat(row[3].replace('Z', '+00:00'))).total_seconds() / 3600
    alerts.append({
        "Timestamp": row[3],
        "Student": row[1],
        "Issue": "Unhandled >24h",
        "Details": f"{round(time_unhandled, 1)}h",
        "Status": "Pending"
    })

if not alerts:
    st.success("✅ No SLA breaches in the last 7 days!")
else:
    df_alerts = pd.DataFrame(alerts)
    st.dataframe(df_alerts, use_container_width=True, hide_index=True)

st.markdown("---")
st.write("💡 **Tip:** Use SLA monitoring to keep your mentor network performing at peak capacity!")
