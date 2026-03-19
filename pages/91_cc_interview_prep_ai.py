import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC Interview Prep AI", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

CC_CSS = """
<style>
:root {
    --cc-primary: #6B46C1;
    --cc-secondary: #9F7AEA;
    --cc-accent: #E9D8FD;
    --cc-dark: #322659;
    --cc-light: #FAF5FF;
}
.cc-header {
    background: linear-gradient(135deg, var(--cc-primary), var(--cc-secondary));
    padding: 2rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 1.5rem;
}
.cc-card {
    background: var(--cc-light);
    border: 2px solid var(--cc-accent);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.cc-metric {
    background: white;
    border-left: 4px solid var(--cc-primary);
    padding: 1rem;
    border-radius: 0 8px 8px 0;
    margin-bottom: 0.5rem;
}
.cc-question {
    background: linear-gradient(135deg, #EDE9FE, #F3E8FF);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    border-left: 4px solid var(--cc-primary);
}
.cc-response {
    background: white;
    border: 1px solid var(--cc-accent);
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
}
.cc-feedback {
    background: #F0FDF4;
    border: 1px solid #86EFAC;
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1rem;
}
.cc-tip {
    background: #FEF3C7;
    border-left: 4px solid #F59E0B;
    padding: 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.5rem 0;
}
.confidence-high { color: #059669; font-weight: bold; }
.confidence-medium { color: #D97706; font-weight: bold; }
.confidence-low { color: #DC2626; font-weight: bold; }
.stButton > button {
    background: linear-gradient(135deg, var(--cc-primary), var(--cc-secondary)) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
}
</style>
"""
st.markdown(CC_CSS, unsafe_allow_html=True)

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Confused")
st.sidebar.page_link("pages/80_cc_home.py", label="CC Home", icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py", label="Timeline", icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py", label="Scholarships", icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py", label="Essay Station", icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py", label="Test Prep", icon="📚")
st.sidebar.page_link("pages/87_cc_college_list.py", label="College List", icon="🏫")
st.sidebar.page_link("pages/88_cc_fafsa_guide.py", label="FAFSA Guide", icon="📋")


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                college_name TEXT,
                session_type TEXT DEFAULT 'practice',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                total_questions INTEGER DEFAULT 0,
                avg_confidence_score REAL DEFAULT 0,
                notes TEXT,
                status TEXT DEFAULT 'in_progress'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_questions (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                tips TEXT,
                example_response TEXT,
                difficulty TEXT DEFAULT 'medium',
                college_specific TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_responses (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES cc_interview_sessions(id),
                question_id INTEGER REFERENCES cc_interview_questions(id),
                user_response TEXT,
                confidence_score REAL,
                ai_feedback TEXT,
                strengths TEXT,
                improvements TEXT,
                response_time_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                college_name TEXT,
                session_type TEXT DEFAULT 'practice',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                total_questions INTEGER DEFAULT 0,
                avg_confidence_score REAL DEFAULT 0,
                notes TEXT,
                status TEXT DEFAULT 'in_progress'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                tips TEXT,
                example_response TEXT,
                difficulty TEXT DEFAULT 'medium',
                college_specific TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                question_id INTEGER,
                user_response TEXT,
                confidence_score REAL,
                ai_feedback TEXT,
                strengths TEXT,
                improvements TEXT,
                response_time_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()


_ensure_tables()

st.markdown("""
<div class="cc-header">
    <h1>🎤 Interview Prep AI</h1>
    <p>Practice college interviews with AI-powered feedback</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cc-card">
    <h3>Welcome to Interview Prep!</h3>
    <p>Practice answering common college interview questions and receive feedback to improve your responses.</p>
</div>
""", unsafe_allow_html=True)