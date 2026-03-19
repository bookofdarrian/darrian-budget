import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC: Interview Prep AI", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ph(n=1):
    return ", ".join(["%s"] * n) if USE_POSTGRES else ", ".join(["?"] * n)

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cc_interview_questions (
            id {"SERIAL" if USE_POSTGRES else "INTEGER"} PRIMARY KEY {"" if USE_POSTGRES else "AUTOINCREMENT"},
            category TEXT NOT NULL,
            question TEXT NOT NULL,
            tips TEXT,
            college_type TEXT DEFAULT 'general',
            difficulty TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cc_interview_sessions (
            id {"SERIAL" if USE_POSTGRES else "INTEGER"} PRIMARY KEY {"" if USE_POSTGRES else "AUTOINCREMENT"},
            user_id INTEGER NOT NULL,
            college_name TEXT,
            college_type TEXT,
            session_type TEXT DEFAULT 'practice',
            total_questions INTEGER DEFAULT 0,
            avg_score REAL DEFAULT 0,
            confidence_score REAL DEFAULT 0,
            duration_minutes INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cc_interview_responses (
            id {"SERIAL" if USE_POSTGRES else "INTEGER"} PRIMARY KEY {"" if USE_POSTGRES else "AUTOINCREMENT"},
            session_id INTEGER NOT NULL,
            question_id INTEGER,
            question_text TEXT NOT NULL,
            response_text TEXT,
            clarity_score REAL DEFAULT 0,
            depth_score REAL DEFAULT 0,
            authenticity_score REAL DEFAULT 0,
            specificity_score REAL DEFAULT 0,
            overall_score REAL DEFAULT 0,
            feedback TEXT,
            improvement_suggestions TEXT,
            response_time_seconds INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES cc_interview_sessions(id)
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS cc_college_interview_tips (
            id {"SERIAL" if USE_POSTGRES else "INTEGER"} PRIMARY KEY {"" if USE_POSTGRES else "AUTOINCREMENT"},
            college_type TEXT NOT NULL,
            tip_category TEXT NOT NULL,
            tip_text TEXT NOT NULL,
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    
    cur.execute("SELECT COUNT(*) FROM cc_interview_questions")
    if cur.fetchone()[0] == 0:
        _seed_questions(cur, conn)
    
    cur.execute("SELECT COUNT(*) FROM cc_college_interview_tips")
    if cur.fetchone()[0] == 0:
        _seed_tips(cur, conn)
    
    conn.close()

def _seed_questions(cur, conn):
    questions = [
        ("about_yourself", "Tell me about yourself.", "Keep it 2-3 minutes. Focus on academics, interests, and why you're excited about college.", "general", "easy"),
        ("about_yourself", "What's something not on your application that you'd like us to know?", "Share a meaningful story or perspective that reveals your character.", "general", "medium"),
        ("about_yourself", "How would your friends describe you?", "Be authentic and give specific examples.", "general", "easy"),
        
        ("why_school", "Why do you want to attend our university?", "Research specific programs, professors, opportunities. Be genuine and specific.", "general", "medium"),
        ("why_school", "What will you contribute to our campus community?", "Connect your unique experiences and skills to campus life.", "general", "medium"),
        ("why_school", "Have you visited campus? What stood out to you?", "If you visited, share genuine impressions. If not, mention virtual tours or conversations with students.", "general", "easy"),
        
        ("academics", "What's your favorite subject and why?", "Show intellectual curiosity beyond just getting good grades.", "general", "easy"),
        ("academics", "Tell me about a book you've read recently that impacted you.", "Discuss what you learned and how it changed your thinking.", "general", "medium"),
        ("academics", "Describe a challenging academic experience and how you handled it.", "Show resilience, problem-solving, and growth mindset.", "general", "medium"),
        ("academics", "What do you want to study and why?", "Connect your interests to experiences and future goals.", "general", "medium"),
        
        ("leadership", "Tell me about a leadership experience.", "Focus on impact, what you learned, and how you grew.", "general", "medium"),
    ]
    
    for q in questions:
        cur.execute(f"INSERT INTO cc_interview_questions (category, question, tips, college_type, difficulty) VALUES ({_ph(5)})", q)
    
    conn.commit()

def _seed_tips(cur, conn):
    tips = [
        ("general", "preparation", "Research the school thoroughly before your interview.", 1),
        ("general", "presentation", "Dress professionally and arrive early.", 2),
        ("general", "communication", "Speak clearly and maintain eye contact.", 3),
    ]
    
    for t in tips:
        cur.execute(f"INSERT INTO cc_college_interview_tips (college_type, tip_category, tip_text, priority) VALUES ({_ph(4)})", t)
    
    conn.commit()

_ensure_tables()

st.markdown("# 🎤 Interview Prep AI")
st.markdown("Practice your college interview skills with AI-powered feedback.")