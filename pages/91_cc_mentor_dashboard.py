"""
Page 91: CC Mentor Dashboard
Internal dashboard for mentors to manage assigned inquiries and draft responses.

Requires login. Mentors see their assigned inquiries, draft/send emails, track conversions.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json

st.set_page_config(
    page_title="Mentor Dashboard | College Confused",
    page_icon="🎓",
    layout="wide"
)

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.cc_speed_to_lead import (
    _ensure_cc_stl_tables,
    get_mentor_inquiries,
    mentor_draft_response,
    send_email_to_student
)

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

# ─── Sidebar ────────────────────────────────────────────────────────────────

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("pages/80_cc_home.py",                      label="Home",               icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py",                  label="My Timeline",         icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",              label="Scholarships",        icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",             label="Essay Station",       icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",                 label="SAT/ACT Prep",        icon="📚")
st.sidebar.page_link("pages/87_cc_college_list.py",              label="College List",        icon="🏫")
st.sidebar.page_link("pages/88_cc_fafsa_guide.py",               label="FAFSA Guide",         icon="📋")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/93_cc_application_tracker.py",       label="Applications",        icon="📝")
st.sidebar.page_link("pages/97_cc_admissions_decision_tracker.py", label="Decisions",          icon="📬")
st.sidebar.page_link("pages/94_cc_recommendation_letter_tracker.py", label="Rec Letters",      icon="📨")
st.sidebar.page_link("pages/95_cc_interview_prep_ai.py",         label="Interview Prep",      icon="🎤")
st.sidebar.page_link("pages/96_cc_financial_aid_appeal_generator.py", label="Aid Appeals",     icon="💸")
st.sidebar.page_link("pages/98_cc_test_score_tracker.py",        label="Score Tracker",       icon="📊")
st.sidebar.page_link("pages/99_cc_campus_visit_planner.py",      label="Campus Visits",       icon="🗺️")
st.sidebar.page_link("pages/89_cc_student_inquiry_form.py",      label="Get Help",            icon="🙋")
render_sidebar_user_widget()

# ─── Helper Functions ──────────────────────────────────────────────────────

def _get_mentor_id() -> int:
    """Get current mentor ID from session state."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    # Assume mentor ID is stored in user_id from auth
    user_id = st.session_state.get("user_id")
    
    # TODO: Once CC mentors are linked to auth users, uncomment:
    # mentor_row = db_exec(conn, f"SELECT id FROM cc_mentors WHERE user_id = {ph}", (user_id,)).fetchone()
    # mentor_id = mentor_row[0] if mentor_row else None
    
    # For now, check if there's a current mentor context
    mentor_id = st.session_state.get("mentor_id")
    conn.close()
    
    return mentor_id

def _load_mentor_kpis(mentor_id: int) -> dict:
    """Load KPI data for mentor dashboard."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    # Total inquiries this month
    total_row = db_exec(conn, f"""
        SELECT COUNT(*) FROM cc_student_inquiries
        WHERE routed_to_mentor_id = {ph}
        AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
    """, (mentor_id,)).fetchone()
    total_this_month = total_row[0] if total_row else 0
    
    # Max students per month
    max_row = db_exec(conn, f"""
        SELECT max_students_per_month FROM cc_mentors WHERE id = {ph}
    """, (mentor_id,)).fetchone()
    max_load = max_row[0] if max_row else 10
    
    # Pending responses (new inquiries not yet responded to)
    pending_row = db_exec(conn, f"""
        SELECT COUNT(*) FROM cc_student_inquiries
        WHERE routed_to_mentor_id = {ph} AND status = 'new'
    """, (mentor_id,)).fetchone()
    pending = pending_row[0] if pending_row else 0
    
    # Conversion rate (booked calls / total inquiries)
    conversions_row = db_exec(conn, f"""
        SELECT COUNT(*) FROM cc_student_inquiries
        WHERE routed_to_mentor_id = {ph} AND student_booked_call = 1
    """, (mentor_id,)).fetchone()
    conversions = conversions_row[0] if conversions_row else 0
    
    all_inquiries_row = db_exec(conn, f"""
        SELECT COUNT(*) FROM cc_student_inquiries
        WHERE routed_to_mentor_id = {ph}
    """, (mentor_id,)).fetchone()
    all_inquiries = all_inquiries_row[0] if all_inquiries_row else 1
    
    conversion_rate = round((conversions / all_inquiries) * 100, 1) if all_inquiries > 0 else 0
    
    conn.close()
    
    return {
        "total_this_month": total_this_month,
        "max_load": max_load,
        "pending": pending,
        "conversion_rate": conversion_rate
    }

def _format_time_since(created_at: str) -> str:
    """Format time since inquiry was created (e.g., '5 min ago')."""
    try:
        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        now = datetime.utcnow()
        delta = now - created_dt
        
        minutes = delta.total_seconds() / 60
        if minutes < 1:
            return "just now"
        elif minutes < 60:
            return f"{int(minutes)} min ago"
        elif minutes < 1440:
            hours = int(minutes / 60)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(minutes / 1440)
            return f"{days} day{'s' if days != 1 else ''} ago"
    except:
        return "recently"

# ─── Page Title & KPIs ──────────────────────────────────────────────────────

st.title("📋 Your Mentor Dashboard")

mentor_id = _get_mentor_id()

if not mentor_id:
    st.warning("⚠️ Please contact Darrian to set up your mentor account.")
    st.stop()

# Fetch mentor name
conn = get_conn()
ph = "%s" if USE_POSTGRES else "?"
mentor_row = db_exec(conn, f"SELECT name FROM cc_mentors WHERE id = {ph}", (mentor_id,)).fetchone()
mentor_name = mentor_row[0] if mentor_row else "Mentor"
conn.close()

st.write(f"Welcome back, **{mentor_name}**! 👋")

# Load KPIs
kpis = _load_mentor_kpis(mentor_id)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total This Month",
        f"{kpis['total_this_month']}/{kpis['max_load']}",
        delta=f"{kpis['max_load'] - kpis['total_this_month']} remaining"
    )

with col2:
    pending_color = "🔴" if kpis['pending'] > 3 else "🟢"
    st.metric(
        "Pending Responses",
        f"{pending_color} {kpis['pending']}",
        delta="Action needed" if kpis['pending'] > 3 else "On track"
    )

with col3:
    st.metric(
        "Conversion Rate",
        f"{kpis['conversion_rate']}%",
        delta="All time" if kpis['conversion_rate'] > 0 else "0 conversions yet"
    )

st.markdown("---")

# ─── Tabs ───────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📬 Inbox", "✅ Converted", "📊 Stats"])

# ─── Tab 1: Inbox (Active Inquiries) ────────────────────────────────────────

with tab1:
    st.subheader("New Inquiries")
    
    # Load inquiries
    inquiries = get_mentor_inquiries(mentor_id, st.session_state.get("db_conn") or get_conn(), status="new")
    
    if not inquiries:
        st.info("✅ No pending inquiries! You're all caught up.")
    else:
        # Display as expandable cards
        for inq in inquiries:
            with st.expander(f"📩 {inq['name']} — {inq['goal']} ({inq['time_since_inquiry_min']} min ago)", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Grade Level:** {inq['grade_level']}")
                    st.write(f"**Goal:** {inq['goal']}")
                    st.write(f"**Region:** {inq['region']}")
                    if inq.get('major_interest'):
                        st.write(f"**Major/Interest:** {inq['major_interest']}")
                    st.write(f"**Email:** {inq['email']}")
                    st.write(f"**Submitted:** {_format_time_since(inq['created_at'])}")
                
                with col2:
                    if st.button(f"✉️ Draft Email", key=f"draft_{inq['id']}"):
                        st.session_state[f"show_email_modal_{inq['id']}"] = True
        
        st.markdown("---")

# ─── Email Drafting Modal ───────────────────────────────────────────────────

for inq in inquiries:
    if st.session_state.get(f"show_email_modal_{inq['id']}", False):
        st.subheader(f"✉️ Draft Response to {inq['name']}")
        
        # Fetch draft from backend
        conn = get_conn()
        draft = mentor_draft_response(inq['id'], mentor_id, conn)
        conn.close()
        
        if draft.get('error'):
            st.error(f"❌ {draft['error']}")
        elif not draft.get('ready_to_send'):
            st.error(f"❌ Could not generate draft. Error: {draft.get('email_subject', 'Unknown')}")
        else:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Student:** {draft['student_name']}")
                st.write(f"**Goal:** {draft['goal']}")
                if draft.get('major_interest'):
                    st.write(f"**Major:** {draft['major_interest']}")
            
            with col2:
                st.write(f"**Grade:** {draft['grade_level']}")
                if draft.get('region'):
                    st.write(f"**Region:** {draft['region']}")
            
            # Email form
            with st.form(f"email_form_{inq['id']}", clear_on_submit=True):
                subject = st.text_input("Subject", value=draft.get('email_subject', ''))
                body = st.text_area("Email Body", value=draft.get('email_body_html', ''), height=250)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    send_button = st.form_submit_button("📧 Send Email", type="primary")
                
                with col2:
                    cancel_button = st.form_submit_button("Cancel")
                
                if send_button:
                    # Send email
                    conn = get_conn()
                    success = send_email_to_student(
                        inquiry_id=inq['id'],
                        mentor_id=mentor_id,
                        email_subject=subject,
                        email_body=body,
                        conn=conn
                    )
                    conn.close()
                    
                    if success:
                        st.success(f"✅ Email sent to {inq['name']}! You'll see a reply in your email.")
                        st.session_state[f"show_email_modal_{inq['id']}"] = False
                        st.rerun()
                    else:
                        st.error("❌ Failed to send email. Please try again.")
                
                if cancel_button:
                    st.session_state[f"show_email_modal_{inq['id']}"] = False
                    st.rerun()

# ─── Tab 2: Converted Inquiries ─────────────────────────────────────────────

with tab2:
    st.subheader("Inquiries That Converted to Calls")
    
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    converted_rows = db_exec(conn, f"""
        SELECT id, name, email, goal, created_at, mentor_response_sent_at
        FROM cc_student_inquiries
        WHERE routed_to_mentor_id = {ph} AND student_booked_call = 1
        ORDER BY mentor_response_sent_at DESC
    """, (mentor_id,)).fetchall()
    
    conn.close()
    
    if not converted_rows:
        st.info("📚 Once students book calls with you, they'll show up here!")
    else:
        df = pd.DataFrame(converted_rows, columns=["ID", "Name", "Email", "Goal", "Submitted", "Email Sent"])
        st.dataframe(df, use_container_width=True, hide_index=True)

# ─── Tab 3: Stats ──────────────────────────────────────────────────────────

with tab3:
    st.subheader("Month-to-Date Summary")
    
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    # Response time stats
    stats_row = db_exec(conn, f"""
        SELECT 
            COUNT(*),
            AVG(time_to_email_ms),
            SUM(CASE WHEN student_first_reply_at IS NOT NULL THEN 1 ELSE 0 END)
        FROM cc_inquiry_metrics
        WHERE inquiry_id IN (
            SELECT id FROM cc_student_inquiries WHERE routed_to_mentor_id = {ph}
        )
    """, (mentor_id,)).fetchone()
    
    total_handled = stats_row[0] if stats_row else 0
    avg_response_ms = stats_row[1] if stats_row else 0
    replies = stats_row[2] if stats_row else 0
    
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Inquiries Handled", total_handled)
    
    with col2:
        avg_sec = round((avg_response_ms or 0) / 1000, 1)
        st.metric("Avg Response Time", f"{avg_sec}s")
    
    with col3:
        reply_rate = round((replies / total_handled * 100), 1) if total_handled > 0 else 0
        st.metric("Reply Rate", f"{reply_rate}%")
    
    st.markdown("---")
    st.write("📈 Coming soon: Detailed charts and trends!")
