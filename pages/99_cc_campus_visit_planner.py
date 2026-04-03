import streamlit as st
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC: Campus Visit Planner", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

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

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_campus_visits (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                college_name VARCHAR(255) NOT NULL,
                visit_date DATE,
                visit_type VARCHAR(100),
                travel_mode VARCHAR(100),
                hotel_info TEXT,
                questions_to_ask TEXT,
                visit_notes TEXT,
                rating INTEGER,
                photos_url TEXT,
                status VARCHAR(50) DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_visit_agenda_items (
                id SERIAL PRIMARY KEY,
                visit_id INTEGER NOT NULL REFERENCES cc_campus_visits(id) ON DELETE CASCADE,
                time_slot VARCHAR(50),
                activity VARCHAR(255),
                location VARCHAR(255),
                notes TEXT,
                completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_campus_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                visit_date TEXT,
                visit_type TEXT,
                travel_mode TEXT,
                hotel_info TEXT,
                questions_to_ask TEXT,
                visit_notes TEXT,
                rating INTEGER,
                photos_url TEXT,
                status TEXT DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_visit_agenda_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_id INTEGER NOT NULL,
                time_slot TEXT,
                activity TEXT,
                location TEXT,
                notes TEXT,
                completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (visit_id) REFERENCES cc_campus_visits(id) ON DELETE CASCADE
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id() -> int:
    return st.session_state.get("user_id", 1)

# CRUD Operations for Visits
def create_visit(user_id: int, college_name: str, visit_date: Optional[date], visit_type: str,
                 travel_mode: str, hotel_info: str, questions_to_ask: str, status: str = "planned") -> int:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    visit_date_str = visit_date.isoformat() if visit_date else None
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO cc_campus_visits (user_id, college_name, visit_date, visit_type, travel_mode, 
                                          hotel_info, questions_to_ask, status)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            RETURNING id
        """, (user_id, college_name, visit_date_str, visit_type, travel_mode, hotel_info, questions_to_ask, status))
        visit_id = cur.fetchone()[0]
    else:
        cur.execute(f"""
            INSERT INTO cc_campus_visits (user_id, college_name, visit_date, visit_type, travel_mode,
                                          hotel_info, questions_to_ask, status)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id, college_name, visit_date_str, visit_type, travel_mode, hotel_info, questions_to_ask, status))
        visit_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return visit_id

def get_visits(user_id: int, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if status_filter:
        cur.execute(f"""
            SELECT id, college_name, visit_date, visit_type, travel_mode, hotel_info, 
                   questions_to_ask, visit_notes, rating, photos_url, status, created_at
            FROM cc_campus_visits
            WHERE user_id = {ph} AND status = {ph}
            ORDER BY visit_date ASC
        """, (user_id, status_filter))
    else:
        cur.execute(f"""
            SELECT id, college_name, visit_date, visit_type, travel_mode, hotel_info,
                   questions_to_ask, visit_notes, rating, photos_url, status, created_at
            FROM cc_campus_visits
            WHERE user_id = {ph}
            ORDER BY visit_date ASC
        """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    visits = []
    for row in rows:
        visits.append({
            "id": row[0],
            "college_name": row[1],
            "visit_date": row[2],
            "visit_type": row[3],
            "travel_mode": row[4],
            "hotel_info": row[5],
            "questions_to_ask": row[6],
            "visit_notes": row[7],
            "rating": row[8],
            "photos_url": row[9],
            "status": row[10],
            "created_at": row[11]
        })
    return visits

def update_visit(visit_id: int, **kwargs) -> None:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {ph}")
        if key == "visit_date" and value:
            values.append(value.isoformat() if isinstance(value, date) else value)
        else:
            values.append(value)
    
    values.append(visit_id)
    
    cur.execute(f"""
        UPDATE cc_campus_visits
        SET {", ".join(set_clauses)}
        WHERE id = {ph}
    """, values)
    
    conn.commit()
    conn.close()

def delete_visit(visit_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"DELETE FROM cc_campus_visits WHERE id = {ph}", (visit_id,))
    conn.commit()
    conn.close()

# CRUD Operations for Agenda Items
def create_agenda_item(visit_id: int, time_slot: str, activity: str, location: str, notes: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO cc_visit_agenda_items (visit_id, time_slot, activity, location, notes)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            RETURNING id
        """, (visit_id, time_slot, activity, location, notes))
        item_id = cur.fetchone()[0]
    else:
        cur.execute(f"""
            INSERT INTO cc_visit_agenda_items (visit_id, time_slot, activity, location, notes)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        """, (visit_id, time_slot, activity, location, notes))
        item_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return item_id

def get_agenda_items(visit_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, time_slot, activity, location, notes, completed
        FROM cc_visit_agenda_items
        WHERE visit_id = {ph}
        ORDER BY time_slot ASC
    """, (visit_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "time_slot": row[1],
            "activity": row[2],
            "location": row[3],
            "notes": row[4],
            "completed": bool(row[5])
        })
    return items

def update_agenda_item(item_id: int, **kwargs) -> None:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {ph}")
        values.append(value)
    
    values.append(item_id)
    
    cur.execute(f"""
        UPDATE cc_visit_agenda_items
        SET {", ".join(set_clauses)}
        WHERE id = {ph}
    """, values)
    
    conn.commit()
    conn.close()

def delete_agenda_item(item_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"DELETE FROM cc_visit_agenda_items WHERE id = {ph}", (item_id,))
    conn.commit()
    conn.close()

# Main UI
st.title("🏫 Campus Visit Planner")
st.markdown("Plan and track your college campus visits")

user_id = get_user_id()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📅 Upcoming Visits", "✅ Completed Visits", "➕ Add New Visit"])

with tab1:
    st.subheader("Upcoming Campus Visits")
    planned_visits = get_visits(user_id, "planned")
    
    if not planned_visits:
        st.info("No upcoming visits planned. Add a new visit to get started!")
    else:
        for visit in planned_visits:
            with st.expander(f"🏫 {visit['college_name']} - {visit['visit_date'] or 'Date TBD'}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Visit Type:** {visit['visit_type'] or 'N/A'}")
                    st.write(f"**Travel Mode:** {visit['travel_mode'] or 'N/A'}")
                    st.write(f"**Hotel:** {visit['hotel_info'] or 'N/A'}")
                with col2:
                    st.write(f"**Status:** {visit['status']}")
                    if visit['questions_to_ask']:
                        st.write(f"**Questions to Ask:**")
                        st.write(visit['questions_to_ask'])
                
                # Agenda Items
                st.markdown("---")
                st.write("**Agenda:**")
                agenda_items = get_agenda_items(visit['id'])
                
                for item in agenda_items:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.write(f"⏰ {item['time_slot']}")
                    with col2:
                        st.write(f"{item['activity']} @ {item['location']}")
                    with col3:
                        if st.checkbox("Done", value=item['completed'], key=f"agenda_{item['id']}"):
                            update_agenda_item(item['id'], completed=True)
                
                # Add agenda item
                with st.form(key=f"add_agenda_{visit['id']}"):
                    st.write("Add Agenda Item")
                    a_col1, a_col2 = st.columns(2)
                    with a_col1:
                        new_time = st.text_input("Time Slot", placeholder="9:00 AM", key=f"time_{visit['id']}")
                        new_activity = st.text_input("Activity", placeholder="Campus Tour", key=f"activity_{visit['id']}")
                    with a_col2:
                        new_location = st.text_input("Location", placeholder="Admissions Building", key=f"loc_{visit['id']}")
                        new_notes = st.text_input("Notes", key=f"notes_{visit['id']}")
                    
                    if st.form_submit_button("Add Item"):
                        if new_time and new_activity:
                            create_agenda_item(visit['id'], new_time, new_activity, new_location, new_notes)
                            st.rerun()
                
                # Actions
                st.markdown("---")
                action_col1, action_col2, action_col3 = st.columns(3)
                with action_col1:
                    if st.button("✅ Mark Complete", key=f"complete_{visit['id']}"):
                        update_visit(visit['id'], status="completed")
                        st.rerun()
                with action_col2:
                    if st.button("🗑️ Delete", key=f"delete_{visit['id']}"):
                        delete_visit(visit['id'])
                        st.rerun()

with tab2:
    st.subheader("Completed Visits")
    completed_visits = get_visits(user_id, "completed")
    
    if not completed_visits:
        st.info("No completed visits yet.")
    else:
        for visit in completed_visits:
            with st.expander(f"✅ {visit['college_name']} - {visit['visit_date'] or 'Date TBD'}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Visit Type:** {visit['visit_type'] or 'N/A'}")
                    st.write(f"**Rating:** {'⭐' * (visit['rating'] or 0)}")
                with col2:
                    if visit['visit_notes']:
                        st.write(f"**Notes:**")
                        st.write(visit['visit_notes'])
                
                # Add/Edit notes and rating
                with st.form(key=f"update_completed_{visit['id']}"):
                    new_rating = st.slider("Rating", 1, 5, visit['rating'] or 3, key=f"rating_{visit['id']}")
                    new_notes = st.text_area("Visit Notes", visit['visit_notes'] or "", key=f"vnotes_{visit['id']}")
                    
                    if st.form_submit_button("Update"):
                        update_visit(visit['id'], rating=new_rating, visit_notes=new_notes)
                        st.rerun()

with tab3:
    st.subheader("Plan a New Campus Visit")
    
    with st.form("new_visit_form"):
        college_name = st.text_input("College Name *", placeholder="Enter college name")
        
        col1, col2 = st.columns(2)
        with col1:
            visit_date = st.date_input("Visit Date", value=None)
            visit_type = st.selectbox("Visit Type", ["Campus Tour", "Information Session", "Open House", "Admitted Students Day", "Interview", "Other"])
        with col2:
            travel_mode = st.selectbox("Travel Mode", ["Car", "Plane", "Train", "Bus", "Other"])
            hotel_info = st.text_input("Hotel/Accommodation", placeholder="Hotel name and address")
        
        questions_to_ask = st.text_area("Questions to Ask", placeholder="List questions you want to ask during the visit")
        
        if st.form_submit_button("Create Visit"):
            if college_name:
                create_visit(user_id, college_name, visit_date, visit_type, travel_mode, hotel_info, questions_to_ask)
                st.success(f"Visit to {college_name} has been planned!")
                st.rerun()
            else:
                st.error("Please enter a college name")