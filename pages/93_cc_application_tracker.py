import streamlit as st
import json
from datetime import datetime, date, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC: Application Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def _ph(count=1):
    """Return correct placeholder syntax based on database type."""
    if USE_POSTGRES:
        return ", ".join(["%s"] * count)
    return ", ".join(["?"] * count)

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    # CC Applications table
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_applications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                application_type TEXT DEFAULT 'Regular Decision',
                deadline DATE,
                submitted_at TIMESTAMP,
                decision_status TEXT DEFAULT 'Not Started',
                decision_date DATE,
                scholarship_amount DECIMAL(10, 2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_application_requirements (
                id SERIAL PRIMARY KEY,
                application_id INTEGER NOT NULL REFERENCES cc_applications(id) ON DELETE CASCADE,
                requirement_type TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN DEFAULT FALSE,
                due_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_common_app_checklist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                application_type TEXT DEFAULT 'Regular Decision',
                deadline DATE,
                submitted_at TIMESTAMP,
                decision_status TEXT DEFAULT 'Not Started',
                decision_date DATE,
                scholarship_amount REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_application_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                requirement_type TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN DEFAULT 0,
                due_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES cc_applications(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_common_app_checklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# CRUD Helper Functions
def get_applications(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM cc_applications WHERE user_id = {_ph()} ORDER BY deadline ASC NULLS LAST", (user_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def get_application_by_id(app_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM cc_applications WHERE id = {_ph()}", (app_id,))
    row = cur.fetchone()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return dict(zip(cols, row)) if row else None

def add_application(user_id, college_name, application_type, deadline, notes):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO cc_applications (user_id, college_name, application_type, deadline, notes)
        VALUES ({_ph(5)})
    """, (user_id, college_name, application_type, deadline, notes))
    conn.commit()
    app_id = cur.lastrowid if not USE_POSTGRES else None
    if USE_POSTGRES:
        cur.execute("SELECT lastval()")
        app_id = cur.fetchone()[0]
    conn.close()
    return app_id

def update_application(app_id, college_name, application_type, deadline, decision_status, decision_date, scholarship_amount, notes, submitted_at=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE cc_applications 
        SET college_name = {_ph()}, application_type = {_ph()}, deadline = {_ph()},
            decision_status = {_ph()}, decision_date = {_ph()}, scholarship_amount = {_ph()},
            notes = {_ph()}, submitted_at = {_ph()}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {_ph()}
    """, (college_name, application_type, deadline, decision_status, decision_date, scholarship_amount, notes, submitted_at, app_id))
    conn.commit()
    conn.close()

def delete_application(app_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM cc_applications WHERE id = {_ph()}", (app_id,))
    conn.commit()
    conn.close()

def get_requirements(app_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM cc_application_requirements WHERE application_id = {_ph()} ORDER BY due_date ASC NULLS LAST", (app_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_requirement(app_id, requirement_type, description, due_date):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO cc_application_requirements (application_id, requirement_type, description, due_date)
        VALUES ({_ph(4)})
    """, (app_id, requirement_type, description, due_date))
    conn.commit()
    conn.close()

def toggle_requirement(req_id, completed):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE cc_application_requirements SET completed = {_ph()} WHERE id = {_ph()}", (completed, req_id))
    conn.commit()
    conn.close()

def delete_requirement(req_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM cc_application_requirements WHERE id = {_ph()}", (req_id,))
    conn.commit()
    conn.close()

def get_checklist(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM cc_common_app_checklist WHERE user_id = {_ph()} ORDER BY category, item_name", (user_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_checklist_item(user_id, item_name, category, notes=""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO cc_common_app_checklist (user_id, item_name, category, notes)
        VALUES ({_ph(4)})
    """, (user_id, item_name, category, notes))
    conn.commit()
    conn.close()

def toggle_checklist_item(item_id, completed):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE cc_common_app_checklist SET completed = {_ph()} WHERE id = {_ph()}", (completed, item_id))
    conn.commit()
    conn.close()

def delete_checklist_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM cc_common_app_checklist WHERE id = {_ph()}", (item_id,))
    conn.commit()
    conn.close()

def initialize_default_checklist(user_id):
    """Initialize default Common App checklist items if none exist."""
    existing = get_checklist(user_id)
    if existing:
        return
    
    default_items = [
        # Profile Section
        ("Personal Information", "Profile", "Name, address, contact info, citizenship"),
        ("Family Information", "Profile", "Parents/guardians, siblings, household info"),
        ("Demographics", "Profile", "Race, ethnicity, language, first-gen status"),
        ("Geography", "Profile", "Where you've lived, schools attended"),
        
        # Education Section
        ("Current School Info", "Education", "GPA, class rank, course rigor"),
        ("Other Schools Attended", "Education", "Transfer history if applicable"),
        ("Grades & Courses", "Education", "Self-reported grades and courses"),
        ("Honors & Awards", "Education", "Academic recognitions (up to 5)"),
        
        # Testing Section
        ("SAT Scores", "Testing", "Self-report or send official scores"),
        ("ACT Scores", "Testing", "Self-report or send official scores"),
        ("AP/IB Scores", "Testing", "List all AP/IB exams taken"),
        
        # Activities Section
        ("Activity 1", "Activities", "Most important extracurricular"),
        ("Activity 2", "Activities", "Second most important"),
        ("Activity 3", "Activities", "Third most important"),
        ("Activity 4", "Activities", "Fourth activity"),
        ("Activity 5", "Activities", "Fifth activity"),
        ("Additional Activities", "Activities", "Activities 6-10"),
        
        # Writing Section
        ("Personal Essay", "Writing", "650-word main essay"),
        ("Additional Info", "Writing", "Explain circumstances if needed"),
        ("COVID-19 Impact", "Writing", "Optional pandemic impact statement"),
        
        # Recommendations
        ("Counselor Recommendation", "Recommendations", "Invite school counselor"),
        ("Teacher Rec #1", "Recommendations", "First teacher recommender"),
        ("Teacher Rec #2", "Recommendations", "Second teacher recommender"),
        ("FERPA Waiver", "Recommendations", "Sign recommendation waiver"),
    ]
    
    for item_name, category, notes in default_items:
        add_checklist_item(user_id, item_name, category, notes)

def get_ai_strategy_tips(applications, checklist):
    """Get AI-powered application strategy tips."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "Configure your Anthropic API key in settings to get AI strategy tips."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        # Build context
        app_summary = []
        for app in applications:
            status = app.get('decision_status', 'Not Started')
            deadline = app.get('deadline', 'No deadline')
            app_summary.append(f"- {app['college_name']}: {status}, Deadline: {deadline}")
        
        checklist_complete = sum(1 for item in checklist if item.get('completed'))
        checklist_total = len(checklist)
        
        prompt = f"""You are a college admissions counselor. Based on this student's application status, provide 3-5 specific, actionable strategy tips.

Applications ({len(applications)} schools):
{chr(10).join(app_summary) if app_summary else 'No applications added yet'}

Common App Progress: {checklist_complete}/{checklist_total} items complete

Provide personalized tips for:
1. Deadline management
2. Application strategy (early action/decision recommendations)
3. Essay/supplement priorities
4. Scholarship opportunities
5. Any red flags or concerns

Keep response under 300 words, focused and actionable."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"AI tips unavailable: {str(e)}"

# Get user info
user_id = st.session_state.get("user_id", 1)

# Initialize default checklist for new users
initialize_default_checklist(user_id)

# Page Title
st.title("🎓 College Application Tracker")
st.caption("Track applications, deadlines, requirements, and decisions in one place")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Applications", "➕ Add Application", "📝 Requirements", "✅ Common App Checklist", "📊 Decision Dashboard"
])

# Tab 1: Applications List
with tab1:
    applications = get_applications(user_id)
    
    if not applications:
        st.info("📚 No applications yet! Start by adding your first college application.")
    else:
        # Deadline Calendar View
        st.subheader("📅 Deadline Calendar")
        
        today = date.today()
        upcoming = []
        overdue = []
        submitted = []
        no_deadline = []
        
        for app in applications:
            if app.get('submitted_at'):
                submitted.append(app)
            elif app.get('deadline'):
                deadline_date = app['deadline'] if isinstance(app['deadline'], date) else datetime.strptime(str(app['deadline']), '%Y-%m-%d').date()
                if deadline_date < today:
                    overdue.append(app)
                else:
                    upcoming.append(app)
            else:
                no_deadline.append(app)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📤 Submitted", len(submitted))
        with col2:
            st.metric("⏰ Upcoming", len(upcoming))
        with col3:
            st.metric("🚨 Overdue", len(overdue))
        with col4:
            st.metric("📝 No Deadline", len(no_deadline))
        
        # Display applications by status
        if overdue:
            st.error("🚨 **Overdue Applications**")
            for app in overdue:
                with st.expander(f"❗ {app['college_name']} - Due: {app['deadline']}"):
                    st.write(f"**Type:** {app['application_type']}")
                    st.write(f"**Status:** {app['decision_status']}")
                    if app.get('notes'):
                        st.write(f"**Notes:** {app['notes']}")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✏️ Edit", key=f"edit_{app['id']}"):
                            st.session_state['editing_app'] = app['id']
                            st.rerun()
                    with col_b:
                        if st.button("🗑️ Delete", key=f"del_{app['id']}"):
                            delete_application(app['id'])
                            st.success("Application deleted!")
                            st.rerun()
        
        if upcoming:
            st.warning("⏰ **Upcoming Deadlines**")
            for app in sorted(upcoming, key=lambda x: x['deadline']):
                deadline_date = app['deadline'] if isinstance(app['deadline'], date) else datetime.strptime(str(app['deadline']), '%Y-%m-%d').date()
                days_left = (deadline_date - today).days
                
                status_color = "🟢" if days_left > 14 else "🟡" if days_left > 7 else "🔴"
                
                with st.expander(f"{status_color} {app['college_name']} - {days_left} days left"):
                    st.write(f"**Deadline:** {app['deadline']}")
                    st.write(f"**Type:** {app['application_type']}")
                    st.write(f"**Status:** {app['decision_status']}")
                    if app.get('notes'):
                        st.write(f"**Notes:** {app['notes']}")
                    
                    # Progress bar for requirements
                    reqs = get_requirements(app['id'])
                    if reqs:
                        completed = sum(1 for r in reqs if r.get('completed'))
                        st.progress(completed / len(reqs), text=f"Requirements: {completed}/{len(reqs)}")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("✏️ Edit", key=f"edit_up_{app['id']}"):
                            st.session_state['editing_app'] = app['id']
                            st.rerun()
                    with col_b:
                        if st.button("📤 Mark Submitted", key=f"submit_{app['id']}"):
                            update_application(
                                app['id'], app['college_name'], app['application_type'],
                                app['deadline'], app['decision_status'], app.get('decision_date'),
                                app.get('scholarship_amount', 0), app.get('notes', ''),
                                submitted_at=datetime.now()
                            )
                            st.success("Marked as submitted!")
                            st.rerun()
                    with col_c:
                        if st.button("🗑️ Delete", key=f"del_up_{app['id']}"):
                            delete_application(app['id'])
                            st.success("Application deleted!")
                            st.rerun()
        
        if submitted:
            st.success("📤 **Submitted Applications**")
            for app in submitted:
                with st.expander(f"✅ {app['college_name']} - {app['decision_status']}"):
                    st.write(f"**Submitted:** {app['submitted_at']}")
                    st.write(f"**Type:** {app['application_type']}")
                    st.write(f"**Decision Status:** {app['decision_status']}")
                    if app.get('decision_date'):
                        st.write(f"**Decision Date:** {app['decision_date']}")
                    if app.get('scholarship_amount') and float(app['scholarship_amount']) > 0:
                        st.write(f"**Scholarship:** ${float(app['scholarship_amount']):,.2f}")
                    if app.get('notes'):
                        st.write(f"**Notes:** {app['notes']}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✏️ Edit", key=f"edit_sub_{app['id']}"):
                            st.session_state['editing_app'] = app['id']
                            st.rerun()
                    with col_b:
                        if st.button("🗑️ Delete", key=f"del_sub_{app['id']}"):
                            delete_application(app['id'])
                            st.success("Application deleted!")
                            st.rerun()

# Tab 2: Add/Edit Application
with tab2:
    editing_id = st.session_state.get('editing_app')
    
    if editing_id:
        st.subheader("✏️ Edit Application")
        app = get_application_by_id(editing_id)
        if not app:
            st.error("Application not found!")
            st.session_state.pop('editing_app', None)
            st.rerun()
    else:
        st.subheader("➕ Add New Application")
        app = {}
    
    with st.form("application_form"):
        college_name = st.text_input("College Name *", value=app.get('college_name', ''))
        
        col1, col2 = st.columns(2)
        with col1:
            app_types = ['Early Decision', 'Early Decision II', 'Early Action', 'Restrictive Early Action', 'Regular Decision', 'Rolling']
            current_type = app.get('application_type', 'Regular Decision')
            type_index = app_types.index(current_type) if current_type in app_types else 4
            application_type = st.selectbox("Application Type", app_types, index=type_index)
        
        with col2:
            deadline_val = None
            if app.get('deadline'):
                if isinstance(app['deadline'], date):
                    deadline_val = app['deadline']
                else:
                    deadline_val = datetime.strptime(str(app['deadline']), '%Y-%m-%d').date()
            deadline = st.date_input("Deadline", value=deadline_val)
        
        if editing_id:
            col3, col4 = st.columns(2)
            with col3:
                decision_statuses = ['Not Started', 'In Progress', 'Submitted', 'Under Review', 'Accepted', 'Rejected', 'Waitlisted', 'Deferred', 'Withdrawn']
                current_status = app.get('decision_status', 'Not Started')
                status_index = decision_statuses.index(current_status) if current_status in decision_statuses else 0
                decision_status = st.selectbox("Decision Status", decision_statuses, index=status_index)
            
            with col4:
                decision_date_val = None
                if app.get('decision_date'):
                    if isinstance(app['decision_date'], date):
                        decision_date_val = app['decision_date']
                    else:
                        decision_date_val = datetime.strptime(str(app['decision_date']), '%Y-%m-%d').date()
                decision_date = st.date_input("Decision Date (if received)", value=decision_date_val)
            
            scholarship_amount = st.number_input(
                "Scholarship Amount ($)", 
                min_value=0.0, 
                value=float(app.get('scholarship_amount', 0) or 0),
                step=1000.0
            )
        else:
            decision_status = 'Not Started'
            decision_date = None
            scholarship_amount = 0.0
        
        notes = st.text_area("Notes", value=app.get('notes', '') or '')
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("💾 Save Application", type="primary")
        with col_btn2:
            if editing_id:
                cancel = st.form_submit_button("❌ Cancel")
                if cancel:
                    st.session_state.pop('editing_app', None)
                    st.rerun()
        
        if submitted:
            if not college_name:
                st.error("Please enter a college name!")
            else:
                if editing_id:
                    update_application(
                        editing_id, college_name, application_type, deadline,
                        decision_status, decision_date, scholarship_amount, notes,
                        submitted_at=app.get('submitted_at')
                    )
                    st.success(f"Updated {college_name}!")
                    st.session_state.pop('editing_app', None)
                else:
                    app_id = add_application(user_id, college_name, application_type, deadline, notes)
                    st.success(f"Added {college_name}!")
                    
                    # Add default requirements
                    default_reqs = [
                        ("Application Fee", "Submit application fee or fee waiver"),
                        ("Transcript", "Request official transcript"),
                        ("Test Scores", "Send SAT/ACT scores if required"),
                        ("Supplemental Essays", "Complete school-specific essays"),
                        ("Recommendations", "Ensure recommenders have submitted"),
                    ]
                    for req_type, desc in default_reqs:
                        add_requirement(app_id, req_type, desc, deadline)
                
                st.rerun()

# Tab 3: Requirements Tracker
with tab3:
    st.subheader("📝 Application Requirements")
    
    applications = get_applications(user_id)
    
    if not applications:
        st.info("Add some applications first to track their requirements!")
    else:
        selected_app = st.selectbox(
            "Select Application",
            options=applications,
            format_func=lambda x: f"{x['college_name']} ({x['application_type']})"
        )
        
        if selected_app:
            reqs = get_requirements(selected_app['id'])
            
            # Add new requirement
            with st.expander("➕ Add New Requirement"):
                with st.form("add_req_form"):
                    req_type = st.text_input("Requirement Type *")
                    req_desc = st.text_area("Description")
                    req_due = st.date_input("Due Date", value=selected_app.get('deadline'))
                    
                    if st.form_submit_button("Add Requirement"):
                        if req_type:
                            add_requirement(selected_app['id'], req_type, req_desc, req_due)
                            st.success("Requirement added!")
                            st.rerun()
                        else:
                            st.error("Please enter a requirement type!")
            
            # Display requirements
            if reqs:
                completed_count = sum(1 for r in reqs if r.get('completed'))
                st.progress(completed_count / len(reqs), text=f"Progress: {completed_count}/{len(reqs)} complete")
                
                for req in reqs:
                    col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
                    with col1:
                        completed = st.checkbox(
                            "Done",
                            value=bool(req.get('completed')),
                            key=f"req_check_{req['id']}",
                            label_visibility="collapsed"
                        )
                        if completed != bool(req.get('completed')):
                            toggle_requirement(req['id'], completed)
                            st.rerun()
                    
                    with col2:
                        status_icon = "✅" if req.get('completed') else "⬜"
                        st.write(f"{status_icon} **{req['requirement_type']}**")
                        if req.get('description'):
                            st.caption(req['description'])
                        if req.get('due_date'):
                            st.caption(f"Due: {req['due_date']}")
                    
                    with col3:
                        if st.button("🗑️", key=f"del_req_{req['id']}"):
                            delete_requirement(req['id'])
                            st.rerun()
            else:
                st.info("No requirements added yet for this application.")

# Tab 4: Common App Checklist
with tab4:
    st.subheader("✅ Common App Checklist")
    st.caption("Track your Common Application progress")
    
    checklist = get_checklist(user_id)
    
    # Add custom item
    with st.expander("➕ Add Custom Item"):
        with st.form("add_checklist_form"):
            item_name = st.text_input("Item Name *")
            category = st.selectbox("Category", ["Profile", "Education", "Testing", "Activities", "Writing", "Recommendations", "Other"])
            item_notes = st.text_area("Notes")
            
            if st.form_submit_button("Add Item"):
                if item_name:
                    add_checklist_item(user_id, item_name, category, item_notes)
                    st.success("Item added!")
                    st.rerun()
                else:
                    st.error("Please enter an item name!")
    
    # Group by category
    categories = {}
    for item in checklist:
        cat = item['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    # Overall progress
    total_complete = sum(1 for item in checklist if item.get('completed'))
    total_items = len(checklist)
    if total_items > 0:
        st.progress(total_complete / total_items, text=f"Overall Progress: {total_complete}/{total_items} ({int(total_complete/total_items*100)}%)")
    
    # Display by category
    for category, items in categories.items():
        completed_in_cat = sum(1 for item in items if item.get('completed'))
        
        with st.expander(f"📁 {category} ({completed_in_cat}/{len(items)} complete)"):
            for item in items:
                col1, col2, col3 = st.columns([0.1, 0.7, 0.2])
                
                with col1:
                    completed = st.checkbox(
                        "Done",
                        value=bool(item.get('completed')),
                        key=f"checklist_{item['id']}",
                        label_visibility="collapsed"
                    )
                    if completed != bool(item.get('completed')):
                        toggle_checklist_item(item['id'], completed)
                        st.rerun()
                
                with col2:
                    status_icon = "✅" if item.get('completed') else "⬜"
                    st.write