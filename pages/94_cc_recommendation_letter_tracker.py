import streamlit as st
import datetime
import json
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC: Recommendation Letter Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ph(count=1):
    return ", ".join(["%s"] * count) if USE_POSTGRES else ", ".join(["?"] * count)

def _ensure_tables():
    conn = get_conn()
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS cc_recommenders (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            title TEXT,
            relationship TEXT,
            school TEXT,
            subject_taught TEXT,
            request_date DATE,
            deadline DATE,
            status TEXT DEFAULT 'pending',
            portal_submitted INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS cc_rec_letter_requests (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            recommender_id INTEGER NOT NULL,
            college_name TEXT NOT NULL,
            college_id INTEGER,
            status TEXT DEFAULT 'not_requested',
            request_sent_date DATE,
            reminder_sent_date DATE,
            submitted_date DATE,
            waived_ferpa INTEGER DEFAULT 1,
            deadline DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recommender_id) REFERENCES cc_recommenders(id)
        )
    """)
    conn.commit()
    conn.close()

_ensure_tables()

def get_recommenders(user_id):
    conn = get_conn()
    cur = db_exec(conn, f"SELECT * FROM cc_recommenders WHERE user_id = {_ph()} ORDER BY deadline ASC", (user_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_recommender(user_id, name, email, title, relationship, school, subject_taught, request_date, deadline, notes):
    conn = get_conn()
    db_exec(conn, f"""
        INSERT INTO cc_recommenders (user_id, name, email, title, relationship, school, subject_taught, request_date, deadline, notes)
        VALUES ({_ph(10)})
    """, (user_id, name, email, title, relationship, school, subject_taught, request_date, deadline, notes))
    conn.commit()
    conn.close()

def update_recommender(rec_id, name, email, title, relationship, school, subject_taught, request_date, deadline, status, portal_submitted, notes):
    conn = get_conn()
    db_exec(conn, f"""
        UPDATE cc_recommenders SET name={_ph()}, email={_ph()}, title={_ph()}, relationship={_ph()}, 
        school={_ph()}, subject_taught={_ph()}, request_date={_ph()}, deadline={_ph()}, 
        status={_ph()}, portal_submitted={_ph()}, notes={_ph()}
        WHERE id={_ph()}
    """, (name, email, title, relationship, school, subject_taught, request_date, deadline, status, portal_submitted, notes, rec_id))
    conn.commit()
    conn.close()

def delete_recommender(rec_id):
    conn = get_conn()
    db_exec(conn, f"DELETE FROM cc_rec_letter_requests WHERE recommender_id = {_ph()}", (rec_id,))
    db_exec(conn, f"DELETE FROM cc_recommenders WHERE id = {_ph()}", (rec_id,))
    conn.commit()
    conn.close()

def get_letter_requests(recommender_id=None, user_id=None):
    conn = get_conn()
    if recommender_id:
        cur = db_exec(conn, f"SELECT * FROM cc_rec_letter_requests WHERE recommender_id = {_ph()} ORDER BY deadline ASC", (recommender_id,))
    elif user_id:
        cur = db_exec(conn, f"""
            SELECT lr.*, r.name as recommender_name, r.email as recommender_email
            FROM cc_rec_letter_requests lr
            JOIN cc_recommenders r ON lr.recommender_id = r.id
            WHERE r.user_id = {_ph()}
            ORDER BY lr.deadline ASC
        """, (user_id,))
    else:
        cur = db_exec(conn, "SELECT * FROM cc_rec_letter_requests ORDER BY deadline ASC")
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_letter_request(recommender_id, college_name, college_id, deadline, waived_ferpa, notes):
    conn = get_conn()
    db_exec(conn, f"""
        INSERT INTO cc_rec_letter_requests (recommender_id, college_name, college_id, deadline, waived_ferpa, notes)
        VALUES ({_ph(6)})
    """, (recommender_id, college_name, college_id, deadline, waived_ferpa, notes))
    conn.commit()
    conn.close()

def update_letter_request(request_id, college_name, status, request_sent_date, reminder_sent_date, submitted_date, deadline, waived_ferpa, notes):
    conn = get_conn()
    db_exec(conn, f"""
        UPDATE cc_rec_letter_requests SET college_name={_ph()}, status={_ph()}, request_sent_date={_ph()}, 
        reminder_sent_date={_ph()}, submitted_date={_ph()}, deadline={_ph()}, waived_ferpa={_ph()}, notes={_ph()}
        WHERE id={_ph()}
    """, (college_name, status, request_sent_date, reminder_sent_date, submitted_date, deadline, waived_ferpa, notes, request_id))
    conn.commit()
    conn.close()

def delete_letter_request(request_id):
    conn = get_conn()
    db_exec(conn, f"DELETE FROM cc_rec_letter_requests WHERE id = {_ph()}", (request_id,))
    conn.commit()
    conn.close()

# Sidebar
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

# Main content
st.title("📝 Recommendation Letter Tracker")
st.markdown("Track your recommendation letter requests and their status.")

user_id = st.session_state.get("user_id", 1)

tab1, tab2, tab3 = st.tabs(["📋 Recommenders", "✉️ Letter Requests", "📊 Overview"])

with tab1:
    st.subheader("Your Recommenders")
    
    with st.expander("➕ Add New Recommender", expanded=False):
        with st.form("add_recommender_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name *")
                email = st.text_input("Email")
                title = st.text_input("Title (e.g., Teacher, Counselor)")
                relationship = st.text_input("Relationship (e.g., AP Chemistry Teacher)")
            with col2:
                school = st.text_input("School/Organization")
                subject_taught = st.text_input("Subject Taught")
                request_date = st.date_input("Request Date", value=datetime.date.today())
                deadline = st.date_input("Deadline")
            notes = st.text_area("Notes")
            
            if st.form_submit_button("Add Recommender"):
                if name:
                    add_recommender(user_id, name, email, title, relationship, school, subject_taught, request_date, deadline, notes)
                    st.success(f"Added {name} as a recommender!")
                    st.rerun()
                else:
                    st.error("Name is required.")
    
    recommenders = get_recommenders(user_id)
    
    if recommenders:
        for rec in recommenders:
            with st.expander(f"👤 {rec['name']} - {rec['status'].title()}", expanded=False):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**Email:** {rec['email'] or 'N/A'}")
                    st.write(f"**Title:** {rec['title'] or 'N/A'}")
                    st.write(f"**Relationship:** {rec['relationship'] or 'N/A'}")
                with col2:
                    st.write(f"**School:** {rec['school'] or 'N/A'}")
                    st.write(f"**Subject:** {rec['subject_taught'] or 'N/A'}")
                    st.write(f"**Deadline:** {rec['deadline'] or 'N/A'}")
                with col3:
                    status = st.selectbox("Status", ["pending", "requested", "confirmed", "submitted"], 
                                         index=["pending", "requested", "confirmed", "submitted"].index(rec['status']),
                                         key=f"status_{rec['id']}")
                    if status != rec['status']:
                        update_recommender(rec['id'], rec['name'], rec['email'], rec['title'], rec['relationship'],
                                          rec['school'], rec['subject_taught'], rec['request_date'], rec['deadline'],
                                          status, rec['portal_submitted'], rec['notes'])
                        st.rerun()
                
                if st.button("🗑️ Delete", key=f"del_rec_{rec['id']}"):
                    delete_recommender(rec['id'])
                    st.rerun()
    else:
        st.info("No recommenders added yet. Add your first recommender above!")

with tab2:
    st.subheader("Letter Requests by College")
    
    recommenders = get_recommenders(user_id)
    
    if recommenders:
        with st.expander("➕ Add New Letter Request", expanded=False):
            with st.form("add_letter_request_form"):
                rec_options = {rec['name']: rec['id'] for rec in recommenders}
                selected_rec = st.selectbox("Select Recommender", list(rec_options.keys()))
                college_name = st.text_input("College Name *")
                deadline = st.date_input("Deadline")
                waived_ferpa = st.checkbox("FERPA Waived", value=True)
                notes = st.text_area("Notes")
                
                if st.form_submit_button("Add Letter Request"):
                    if college_name:
                        add_letter_request(rec_options[selected_rec], college_name, None, deadline, 1 if waived_ferpa else 0, notes)
                        st.success(f"Added letter request for {college_name}!")
                        st.rerun()
                    else:
                        st.error("College name is required.")
        
        letter_requests = get_letter_requests(user_id=user_id)
        
        if letter_requests:
            for req in letter_requests:
                status_emoji = {"not_requested": "⚪", "requested": "🟡", "in_progress": "🟠", "submitted": "🟢"}.get(req['status'], "⚪")
                with st.expander(f"{status_emoji} {req['college_name']} - {req.get('recommender_name', 'Unknown')}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Recommender:** {req.get('recommender_name', 'Unknown')}")
                        st.write(f"**Deadline:** {req['deadline'] or 'N/A'}")
                        st.write(f"**FERPA Waived:** {'Yes' if req['waived_ferpa'] else 'No'}")
                    with col2:
                        new_status = st.selectbox("Status", ["not_requested", "requested", "in_progress", "submitted"],
                                                 index=["not_requested", "requested", "in_progress", "submitted"].index(req['status']),
                                                 key=f"req_status_{req['id']}")
                        if new_status != req['status']:
                            submitted_date = datetime.date.today() if new_status == "submitted" else req['submitted_date']
                            update_letter_request(req['id'], req['college_name'], new_status, req['request_sent_date'],
                                                 req['reminder_sent_date'], submitted_date, req['deadline'],
                                                 req['waived_ferpa'], req['notes'])
                            st.rerun()
                    
                    if st.button("🗑️ Delete Request", key=f"del_req_{req['id']}"):
                        delete_letter_request(req['id'])
                        st.rerun()
        else:
            st.info("No letter requests added yet.")
    else:
        st.warning("Please add recommenders first before creating letter requests.")

with tab3:
    st.subheader("Overview & Statistics")
    
    recommenders = get_recommenders(user_id)
    letter_requests = get_letter_requests(user_id=user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Recommenders", len(recommenders))
    with col2:
        st.metric("Total Requests", len(letter_requests))
    with col3:
        submitted = len([r for r in letter_requests if r['status'] == 'submitted'])
        st.metric("Submitted", submitted)
    with col4:
        pending = len([r for r in letter_requests if r['status'] != 'submitted'])
        st.metric("Pending", pending)
    
    if letter_requests:
        st.subheader("Upcoming Deadlines")
        upcoming = [r for r in letter_requests if r['deadline'] and r['status'] != 'submitted']
        upcoming.sort(key=lambda x: x['deadline'] if x['deadline'] else datetime.date.max)
        
        for req in upcoming[:5]:
            days_left = (req['deadline'] - datetime.date.today()).days if isinstance(req['deadline'], datetime.date) else None
            if days_left is not None:
                if days_left < 0:
                    st.error(f"⚠️ **OVERDUE** - {req['college_name']} ({req.get('recommender_name', 'Unknown')}): {abs(days_left)} days overdue")
                elif days_left <= 7:
                    st.warning(f"⏰ {req['college_name']} ({req.get('recommender_name', 'Unknown')}): {days_left} days left")
                else:
                    st.info(f"📅 {req['college_name']} ({req.get('recommender_name', 'Unknown')}): {days_left} days left")
