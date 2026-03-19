import streamlit as st
import json
from datetime import datetime, date, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC: Test Score Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_test_scores (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                test_type VARCHAR(50) NOT NULL,
                test_date DATE NOT NULL,
                section_scores JSONB,
                composite_score INTEGER,
                target_score INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_study_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                test_type VARCHAR(50) NOT NULL,
                session_date DATE NOT NULL,
                duration_minutes INTEGER,
                topics_covered TEXT,
                practice_score INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_score_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                test_type VARCHAR(50) NOT NULL,
                target_score INTEGER NOT NULL,
                target_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_test_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                test_date TEXT NOT NULL,
                section_scores TEXT,
                composite_score INTEGER,
                target_score INTEGER,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                session_date TEXT NOT NULL,
                duration_minutes INTEGER,
                topics_covered TEXT,
                practice_score INTEGER,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_score_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                test_type TEXT NOT NULL,
                target_score INTEGER NOT NULL,
                target_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# College Command Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Command")
st.sidebar.page_link("pages/80_cc_home.py", label="CC Home", icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py", label="Timeline", icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py", label="Scholarships", icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py", label="Essays", icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py", label="Test Prep", icon="📚")
st.sidebar.page_link("pages/87_cc_college_list.py", label="College List", icon="🏫")

user_id = st.session_state.get("user_id", 1)

# Test type configurations
TEST_CONFIGS = {
    "SAT": {
        "sections": ["Evidence-Based Reading & Writing", "Math"],
        "max_section": 800,
        "max_composite": 1600,
        "min_score": 200,
        "percentiles": {1600: 99, 1550: 99, 1500: 98, 1450: 96, 1400: 94, 1350: 91, 1300: 87, 1250: 82, 1200: 76, 1150: 68, 1100: 59, 1050: 49, 1000: 40}
    },
    "ACT": {
        "sections": ["English", "Math", "Reading", "Science"],
        "max_section": 36,
        "max_composite": 36,
        "min_score": 1,
        "percentiles": {36: 99, 35: 99, 34: 99, 33: 98, 32: 97, 31: 95, 30: 93, 29: 90, 28: 87, 27: 83, 26: 79, 25: 74, 24: 68, 23: 62, 22: 55, 21: 48, 20: 41}
    },
    "AP": {
        "sections": ["Score"],
        "max_section": 5,
        "max_composite": 5,
        "min_score": 1,
        "percentiles": {5: 90, 4: 70, 3: 50, 2: 25, 1: 10}
    },
    "PSAT": {
        "sections": ["Evidence-Based Reading & Writing", "Math"],
        "max_section": 760,
        "max_composite": 1520,
        "min_score": 160,
        "percentiles": {1520: 99, 1450: 99, 1400: 97, 1350: 95, 1300: 91, 1250: 85, 1200: 78, 1150: 69, 1100: 58, 1050: 47, 1000: 36}
    }
}

AP_SUBJECTS = [
    "AP Biology", "AP Calculus AB", "AP Calculus BC", "AP Chemistry", "AP Computer Science A",
    "AP Computer Science Principles", "AP English Language", "AP English Literature",
    "AP Environmental Science", "AP European History", "AP Government", "AP Human Geography",
    "AP Macroeconomics", "AP Microeconomics", "AP Physics 1", "AP Physics 2", "AP Physics C: E&M",
    "AP Physics C: Mechanics", "AP Psychology", "AP Spanish Language", "AP Spanish Literature",
    "AP Statistics", "AP US History", "AP World History", "AP Art History", "AP Music Theory"
]

COLLEGE_SCORE_RANGES = {
    "Harvard": {"SAT": (1480, 1580), "ACT": (33, 36)},
    "MIT": {"SAT": (1510, 1580), "ACT": (34, 36)},
    "Stanford": {"SAT": (1470, 1570), "ACT": (33, 35)},
    "Yale": {"SAT": (1470, 1570), "ACT": (33, 35)},
    "Princeton": {"SAT": (1480, 1570), "ACT": (33, 35)},
    "Columbia": {"SAT": (1470, 1570), "ACT": (33, 35)},
    "UPenn": {"SAT": (1460, 1570), "ACT": (33, 35)},
    "Duke": {"SAT": (1450, 1570), "ACT": (33, 35)},
    "Northwestern": {"SAT": (1440, 1550), "ACT": (33, 35)},
    "Georgia Tech": {"SAT": (1370, 1530), "ACT": (31, 35)},
    "UGA": {"SAT": (1270, 1440), "ACT": (28, 32)},
    "Emory": {"SAT": (1410, 1530), "ACT": (32, 35)},
    "Spelman": {"SAT": (1100, 1280), "ACT": (22, 27)},
    "Morehouse": {"SAT": (1080, 1260), "ACT": (21, 26)},
    "Howard": {"SAT": (1130, 1320), "ACT": (23, 28)},
    "UCLA": {"SAT": (1360, 1530), "ACT": (30, 35)},
    "UC Berkeley": {"SAT": (1360, 1530), "ACT": (30, 35)},
    "NYU": {"SAT": (1370, 1530), "ACT": (31, 34)},
    "Boston University": {"SAT": (1340, 1500), "ACT": (30, 34)},
    "University of Michigan": {"SAT": (1360, 1530), "ACT": (31, 34)}
}

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def get_scores(user_id, test_type=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    if test_type:
        cur.execute(f"SELECT * FROM cc_test_scores WHERE user_id = {ph} AND test_type = {ph} ORDER BY test_date DESC", (user_id, test_type))
    else:
        cur.execute(f"SELECT * FROM cc_test_scores WHERE user_id = {ph} ORDER BY test_date DESC", (user_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_score(user_id, test_type, test_date, section_scores, composite_score, target_score, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    section_json = json.dumps(section_scores) if isinstance(section_scores, dict) else section_scores
    cur.execute(f"""
        INSERT INTO cc_test_scores (user_id, test_type, test_date, section_scores, composite_score, target_score, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, test_type, str(test_date), section_json, composite_score, target_score, notes))
    conn.commit()
    conn.close()

def delete_score(score_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM cc_test_scores WHERE id = {ph}", (score_id,))
    conn.commit()
    conn.close()

def get_study_sessions(user_id, test_type=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    if test_type:
        cur.execute(f"SELECT * FROM cc_study_sessions WHERE user_id = {ph} AND test_type = {ph} ORDER BY session_date DESC", (user_id, test_type))
    else:
        cur.execute(f"SELECT * FROM cc_study_sessions WHERE user_id = {ph} ORDER BY session_date DESC", (user_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_study_session(user_id, test_type, session_date, duration_minutes, topics_covered, practice_score, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO cc_study_sessions (user_id, test_type, session_date, duration_minutes, topics_covered, practice_score, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, test_type, str(session_date), duration_minutes, topics_covered, practice_score, notes))
    conn.commit()
    conn.close()

def delete_study_session(session_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM cc_study_sessions WHERE id = {ph}", (session_id,))
    conn.commit()
    conn.close()

def get_goals(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM cc_score_goals WHERE user_id = {ph} ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def add_goal(user_id, test_type, target_score, target_date, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO cc_score_goals (user_id, test_type, target_score, target_date, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, test_type, target_score, str(target_date) if target_date else None, notes))
    conn.commit()
    conn.close()

def delete_goal(goal_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM cc_score_goals WHERE id = {ph}", (goal_id,))
    conn.commit()
    conn.close()

def calculate_superscore(scores, test_type):
    if not scores or test_type not in ["SAT", "ACT", "PSAT"]:
        return None
    
    config = TEST_CONFIGS[test_type]
    best_sections = {}
    
    for score in scores:
        section_scores = score.get("section_scores")
        if isinstance(section_scores, str):
            try:
                section_scores = json.loads(section_scores)
            except:
                continue
        if not section_scores:
            continue
            
        for section, value in section_scores.items():
            if section not in best_sections or value > best_sections[section]:
                best_sections[section] = value
    
    if not best_sections:
        return None
    
    if test_type in ["SAT", "PSAT"]:
        return sum(best_sections.values())
    elif test_type == "ACT":
        return round(sum(best_sections.values()) / len(best_sections))
    return None

def get_percentile(score, test_type):
    if test_type not in TEST_CONFIGS:
        return None
    percentiles = TEST_CONFIGS[test_type]["percentiles"]
    for threshold in sorted(percentiles.keys(), reverse=True):
        if score >= threshold:
            return percentiles[threshold]
    return 1

def analyze_weaknesses(scores, test_type):
    if not scores:
        return []
    
    section_totals = {}
    section_counts = {}
    
    for score in scores:
        section_scores = score.get("section_scores")
        if isinstance(section_scores, str):
            try:
                section_scores = json.loads(section_scores)
            except:
                continue
        if not section_scores:
            continue
            
        for section, value in section_scores.items():
            section_totals[section] = section_totals.get(section, 0) + value
            section_counts[section] = section_counts.get(section, 0) + 1
    
    section_avgs = {}
    for section in section_totals:
        section_avgs[section] = section_totals[section] / section_counts[section]
    
    if not section_avgs:
        return []
    
    sorted_sections = sorted(section_avgs.items(), key=lambda x: x[1])
    return sorted_sections

def get_ai_recommendations(scores, study_sessions, goals, test_type):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Please configure your Anthropic API key in settings to get AI recommendations."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        scores_summary = []
        for s in scores[:5]:
            section_scores = s.get("section_scores")
            if isinstance(section_scores, str):
                try:
                    section_scores = json.loads(section_scores)
                except:
                    section_scores = {}
            scores_summary.append({
                "date": str(s.get("test_date")),
                "composite": s.get("composite_score"),
                "sections": section_scores
            })
        
        sessions_summary = []
        for sess in study_sessions[:10]:
            sessions_summary.append({
                "date": str(sess.get("session_date")),
                "duration": sess.get("duration_minutes"),
                "topics": sess.get("topics_covered"),
                "practice_score": sess.get("practice_score")
            })
        
        goals_summary = []
        for g in goals:
            if g.get("test_type") == test_type or test_type == "All":
                goals_summary.append({
                    "test_type": g.get("test_type"),
                    "target": g.get("target_score"),
                    "target_date": str(g.get("target_date"))
                })
        
        weaknesses = analyze_weaknesses(scores, test_type) if test_type != "All" else []
        superscore = calculate_superscore(scores, test_type) if test_type in ["SAT", "ACT", "PSAT"] else None
        
        prompt = f"""You are an expert college admissions test prep coach. Analyze this student's test scores and study habits, then provide specific, actionable recommendations.

Test Type Focus: {test_type}

Recent Scores:
{json.dumps(scores_summary, indent=2)}

Study Sessions (last 10):
{json.dumps(sessions_summary, indent=2)}

Goals:
{json.dumps(goals_summary, indent=2)}

Section Weaknesses (lowest to highest avg):
{weaknesses}

Superscore (if applicable): {superscore}

Please provide:
1. **Score Analysis**: What do the scores tell us about the student's progress?
2. **Weakness Diagnosis**: Which specific sections need the most work and why?
3. **Study Plan Recommendation**: A concrete weekly study plan with specific topics and time allocations
4. **Test Strategy Tips**: 3-5 specific strategies for the actual test day
5. **Timeline Advice**: Based on goals and current scores, is the target achievable? What milestones should they hit?
6. **Resource Recommendations**: Specific books, websites, or practice materials for their weak areas

Be specific and encouraging. Use data from their actual scores to personalize advice."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        return f"❌ Error getting AI recommendations: {str(e)}"

# Main UI
st.title("📝 Test Score Tracker")
st.markdown("Track SAT, ACT, AP, and PSAT scores with AI-powered study recommendations")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Score Log", "📚 Study Tracker", "🎯 Goals", "📈 Analytics", "🤖 AI Coach"])

with tab1:
    st.subheader("📊 Log Your Test Scores")
    
    with st.expander("➕ Add New Score", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            test_type = st.selectbox("Test Type", ["SAT", "ACT", "PSAT", "AP"])
            test_date = st.date_input("Test Date", value=date.today())
        
        with col2:
            if test_type == "AP":
                ap_subject = st.selectbox("AP Subject", AP_SUBJECTS)
                test_type_full = ap_subject
            else:
                test_type_full = test_type
            target_score = st.number_input("Target Score", min_value=TEST_CONFIGS[test_type]["min_score"], max_value=TEST_CONFIGS[test_type]["max_composite"], value=TEST_CONFIGS[test_type]["max_composite"])
        
        st.markdown("**Section Scores**")
        config = TEST_CONFIGS[test_type]
        section_scores = {}
        
        if test_type == "AP":
            section_scores["Score"] = st.slider("AP Score", 1, 5, 3)
            composite = section_scores["Score"]
        else:
            cols = st.columns(len(config["sections"]))
            for i, section in enumerate(config["sections"]):
                with cols[i]:
                    section_scores[section] = st.number_input(
                        section,
                        min_value=config["min_score"],
                        max_value=config["max_section"],
                        value=config["max_section"] // 2
                    )
            
            if test_type in ["SAT", "PSAT"]:
                composite = sum(section_scores.values())
            else:
                composite = round(sum(section_scores.values()) / len(section_scores))
        
        st.metric("Composite Score", composite)
        notes = st.text_area("Notes (optional)", placeholder="Any notes about this test...")
        
        if st.button("💾 Save Score", type="primary"):
            add_score(user_id, test_type_full if test_type == "AP" else test_type, test_date, section_scores, composite, target_score, notes)
            st.success("✅ Score saved!")
            st.rerun()
    
    st.markdown("---")
    st.subheader("📋 Your Scores")
    
    filter_type = st.selectbox("Filter by Test Type", ["All", "SAT", "ACT", "PSAT", "AP"])
    
    if filter_type == "All":
        scores = get_scores(user_id)
    elif filter_type == "AP":
        all_scores = get_scores(user_id)
        scores = [s for s in all_scores if s["test_type"].startswith("AP")]
    else:
        scores = get_scores(user_id, filter_type)
    
    if not scores:
        st.info("No scores logged yet. Add your first test score above!")
    else:
        for score in scores:
            section_scores = score.get("section_scores")
            if isinstance(section_scores, str):
                try:
                    section_scores = json.loads(section_scores)
                except:
                    section_scores = {}
            
            test_type_display = score["test_type"]
            base_type = "AP" if test_type_display.startswith("AP") else test_type_display
            percentile = get_percentile(score["composite_score"], base_type)
            
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{test_type_display}** - {score['test_date']}")
                with col2:
                    st.markdown(f"Score: **{score['composite_score']}** ({percentile}th percentile)")
                with col3:
                    if section_scores:
                        with st.expander("Sections"):
                            for section, val in section_scores.items():
                                st.write(f"{section}: {val}")
                with col4:
                    if st.button("🗑️", key=f"del_score_{score['id']}"):
                        delete_score(score["id"])
                        st.rerun()
                st.markdown("---")

with tab2:
    st.subheader("📚 Study Session Tracker")
    
    with st.expander("➕ Log Study Session", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            study_test_type = st.selectbox("Test Studying For", ["SAT", "ACT", "PSAT", "AP"], key="study_type")
            session_date = st.date_input("Session Date", value=date.today(), key="session_date")
            duration = st.number_input("Duration (minutes)", min_value=5, max_value=480, value=60)
        
        with col2:
            if study_test_type == "SAT" or study_test_type == "PSAT":
                topics = st.multiselect("Topics Covered", [
                    "Reading Comprehension", "Grammar/Writing", "Math - Algebra",
                    "Math - Problem Solving", "Math - Advanced Math", "Vocabulary",
                    "Data Analysis", "Essay Practice", "Full Practice Test"
                ])
            elif study_test_type == "ACT":
                topics = st.multiselect("Topics Covered", [
                    "English - Grammar", "English - Rhetoric", "Math - Pre-Algebra",
                    "Math - Algebra", "Math - Geometry", "Math - Trigonometry",
                    "Reading - Prose Fiction", "Reading - Social Science",
                    "Reading - Humanities", "Reading - Natural Science",
                    "Science - Data Representation", "Science - Research Summaries",
                    "Science - Conflicting Viewpoints", "Full Practice Test"
                ])
            else:
                topics = st.multiselect("Topics Covered", [
                    "Content Review", "Practice Problems", "Full Practice Test",
                    "FRQ Practice", "MCQ Practice", "Concept Review"
                ])
            
            practice_score = st.number_input("Practice Score (if applicable)", min_value=0, value=0)
        
        study_notes = st.text_area("Session Notes", placeholder="What did you learn? What was challenging?")
        
        if st.button("📝 Log Session", type="primary"):
            add_study_session(user_id, study_test_type, session_date, duration, ", ".join(topics), practice_score if practice_score > 0 else None, study_notes)
            st.success("✅ Study session logged!")
            st.rerun()
    
    st.markdown("---")
    st.subheader("📖 Recent Study Sessions")
    
    sessions = get_study_sessions(user_id)
    
    if not sessions:
        st.info("No study sessions logged yet. Start tracking your prep!")
    else:
        total_time = sum(s.get("duration_minutes", 0) for s in sessions)
        this_week = sum(s.get("duration_minutes", 0) for s in sessions 
                       if datetime.strptime(str(s["session_date"]), "%Y-%m-%d").date() >= date.today() - timedelta(days=7))
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Study Time", f"{total_time // 60}h {total_time % 60}m")
        col2.metric("This Week", f"{this_week // 60}h {this_week % 60}m")
        col3.metric("Sessions Logged", len(sessions))
        
        st.markdown("---")
        
        for session in sessions[:20]:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{session['test_type']}** - {session['session_date']}")
                with col2:
                    st.markdown(f"⏱️ {session['duration_minutes']} min | Topics: {session.get('topics_covered', 'N/A')}")
                with col3:
                    if session.get("practice_score"):
                        st.markdown(f"Score: {session['practice_score']}")
                with col4:
                    if st.button("🗑️", key=f"del_session_{session['id']}"):
                        delete_study_session(session["id"])
                        st.rerun()
                st.markdown("---")

with tab3:
    st.subheader("🎯 Score Goals")
    
    with st.expander("➕ Set New Goal", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            goal_test_type = st.selectbox("Test Type", ["SAT", "ACT", "PSAT"], key="goal_type")
            
            st.markdown("**College Score Ranges (for reference)**")
            selected_college = st.selectbox("Select College", list(COLLEGE_SCORE_RANGES.keys()))
            if selected_college in COLLEGE_SCORE_RANGES:
                ranges = COLLEGE_SCORE_RANGES[selected_college]
                if goal_test_type in ranges:
                    low, high = ranges[goal_test_type]
                    st.info(f"{selected_college} {goal_test_type} Range: {low} - {high}")
        
        with col2:
            config = TEST_CONFIGS[goal_test_type]
            goal_score = st.number_input("Target Score", min_value=config["min_score"], max_value=config["max_composite"], value=config["max_composite"] - 200)
            goal_date = st.date_input("Target Date", value=date.today() + timedelta(days=90), key="goal_date")
            goal_notes = st.text_area("Notes", placeholder="Why this goal? Which schools require this score?")
        
        if st.button("🎯 Set Goal", type="primary"):
            add_goal(user_id, goal_test_type, goal_score, goal_date, goal_notes)
            st.success("✅ Goal set!")
            st.rerun()
    
    st.markdown("---")
    st.subhe