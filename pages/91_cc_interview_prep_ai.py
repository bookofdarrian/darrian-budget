import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC Interview Prep AI", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# College Confused theme CSS
CC_CSS = """
<style>
    .cc-header {
        background: linear-gradient(135deg, #6B46C1 0%, #805AD5 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .cc-header h1 {
        margin: 0;
        font-size: 2rem;
    }
    .cc-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    .interview-card {
        background: #1E1E2E;
        border: 1px solid #6B46C1;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .question-card {
        background: #2D2D3D;
        border-left: 4px solid #805AD5;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }
    .tip-card {
        background: linear-gradient(135deg, #2D3748 0%, #1A202C 100%);
        border: 1px solid #4A5568;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .confidence-high { color: #48BB78; font-weight: bold; }
    .confidence-medium { color: #ECC94B; font-weight: bold; }
    .confidence-low { color: #F56565; font-weight: bold; }
    .metric-box {
        background: #2D2D3D;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #805AD5;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #A0AEC0;
    }
    .ai-response {
        background: #1A1A2E;
        border: 1px solid #6B46C1;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .feedback-positive { color: #48BB78; }
    .feedback-improvement { color: #ECC94B; }
    .session-history {
        border-left: 3px solid #6B46C1;
        padding-left: 1rem;
        margin: 0.5rem 0;
    }
</style>
"""
st.markdown(CC_CSS, unsafe_allow_html=True)

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Confused")
st.sidebar.page_link("pages/80_cc_home.py", label="CC Home", icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py", label="Timeline", icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py", label="Scholarships", icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py", label="Essay Station", icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py", label="Test Prep", icon="📝")
st.sidebar.page_link("pages/87_cc_college_list.py", label="College List", icon="🏫")
st.sidebar.page_link("pages/88_cc_fafsa_guide.py", label="FAFSA Guide", icon="📋")
st.sidebar.page_link("pages/91_cc_interview_prep_ai.py", label="Interview Prep AI", icon="🎤")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    """Create all required tables for interview prep."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        # Interview sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_sessions (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_type TEXT NOT NULL,
                college_name TEXT,
                duration_minutes INTEGER DEFAULT 0,
                questions_answered INTEGER DEFAULT 0,
                avg_confidence_score REAL DEFAULT 0,
                overall_feedback TEXT,
                strengths TEXT,
                improvements TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Question bank
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_questions (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                subcategory TEXT,
                question_text TEXT NOT NULL,
                difficulty TEXT DEFAULT 'medium',
                tips TEXT,
                sample_answer TEXT,
                follow_up_questions TEXT,
                college_specific TEXT,
                times_asked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User responses
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_responses (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id INTEGER REFERENCES cc_interview_sessions(id),
                question_id INTEGER REFERENCES cc_interview_questions(id),
                user_response TEXT,
                ai_feedback TEXT,
                confidence_score REAL,
                duration_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite versions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_type TEXT NOT NULL,
                college_name TEXT,
                duration_minutes INTEGER DEFAULT 0,
                questions_answered INTEGER DEFAULT 0,
                avg_confidence_score REAL DEFAULT 0,
                overall_feedback TEXT,
                strengths TEXT,
                improvements TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                subcategory TEXT,
                question_text TEXT NOT NULL,
                difficulty TEXT DEFAULT 'medium',
                tips TEXT,
                sample_answer TEXT,
                follow_up_questions TEXT,
                college_specific TEXT,
                times_asked INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_interview_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id INTEGER,
                question_id INTEGER,
                user_response TEXT,
                ai_feedback TEXT,
                confidence_score REAL,
                duration_seconds INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()


def _seed_questions():
    """Seed the question bank with common interview questions."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Check if questions already exist
    cur.execute("SELECT COUNT(*) FROM cc_interview_questions")
    count = cur.fetchone()[0]
    
    if count == 0:
        questions = [
            # Personal/Background
            ('personal', 'background', 'Tell me about yourself.', 'easy',
             'Focus on your academic interests, extracurriculars, and what drives you.',
             None, '["What are you most passionate about?"]', None),
            ('personal', 'background', 'Why are you interested in this college?', 'medium',
             'Research specific programs, professors, or opportunities unique to this school.',
             None, '["Have you visited campus?"]', None),
            ('personal', 'values', 'What is your greatest strength?', 'easy',
             'Choose a strength relevant to college success and provide a specific example.',
             None, '["Can you give me an example?"]', None),
            ('personal', 'values', 'What is your biggest weakness?', 'medium',
             'Be honest but show self-awareness and how you are working to improve.',
             None, '["How are you working on it?"]', None),
            
            # Academic
            ('academic', 'interests', 'What subject interests you the most and why?', 'easy',
             'Connect your academic interests to real-world applications or experiences.',
             None, '["What sparked this interest?"]', None),
            ('academic', 'goals', 'What do you plan to study in college?', 'medium',
             'Show genuine interest and some research into the field.',
             None, '["What career paths interest you?"]', None),
            ('academic', 'challenges', 'Describe a challenging academic experience.', 'medium',
             'Focus on what you learned and how you grew from the challenge.',
             None, '["What would you do differently?"]', None),
            
            # Extracurricular
            ('extracurricular', 'activities', 'What extracurricular activities are you involved in?', 'easy',
             'Highlight leadership, commitment, and impact rather than just listing activities.',
             None, '["Which is most meaningful to you?"]', None),
            ('extracurricular', 'leadership', 'Describe a leadership experience.', 'medium',
             'Focus on specific actions you took and their outcomes.',
             None, '["What did you learn from leading?"]', None),
            
            # Situational
            ('situational', 'conflict', 'Tell me about a time you faced a conflict.', 'hard',
             'Use the STAR method: Situation, Task, Action, Result.',
             None, '["What would you do differently?"]', None),
            ('situational', 'failure', 'Describe a time you failed at something.', 'hard',
             'Show resilience and what you learned from the experience.',
             None, '["How did it change your approach?"]', None),
            ('situational', 'problem-solving', 'Describe a problem you solved creatively.', 'hard',
             'Highlight your thought process and innovative approach.',
             None, '["What\'s your approach to solving it?"]', None),
            
            # Future Goals
            ('goals', 'career', 'Where do you see yourself in 10 years?', 'medium',
             'Show ambition but remain realistic and connected to your chosen field.',
             None, '["How will college help you get there?"]', None),
            ('goals', 'contribution', 'How do you plan to contribute to our campus community?', 'medium',
             'Reference specific clubs, organizations, or initiatives at the school.',
             None, '["What communities are you part of now?"]', None),
        ]
        
        for q in questions:
            cur.execute("""
                INSERT INTO cc_interview_questions 
                (category, subcategory, question_text, difficulty, tips, sample_answer, follow_up_questions, college_specific)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """ if not USE_POSTGRES else """
                INSERT INTO cc_interview_questions 
                (category, subcategory, question_text, difficulty, tips, sample_answer, follow_up_questions, college_specific)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, q)
        
        conn.commit()
    
    cur.close()
    conn.close()


def get_questions(category: Optional[str] = None, difficulty: Optional[str] = None) -> List[Dict]:
    """Get questions from the bank, optionally filtered."""
    conn = get_conn()
    cur = conn.cursor()
    
    query = "SELECT * FROM cc_interview_questions WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = %s" if USE_POSTGRES else " AND category = ?"
        params.append(category)
    
    if difficulty:
        query += " AND difficulty = %s" if USE_POSTGRES else " AND difficulty = ?"
        params.append(difficulty)
    
    cur.execute(query, params)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


def create_session(user_id: str, session_type: str, college_name: Optional[str] = None) -> int:
    """Create a new interview session."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO cc_interview_sessions (user_id, session_type, college_name)
            VALUES (%s, %s, %s) RETURNING id
        """, (user_id, session_type, college_name))
        session_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO cc_interview_sessions (user_id, session_type, college_name)
            VALUES (?, ?, ?)
        """, (user_id, session_type, college_name))
        session_id = cur.lastrowid
    
    conn.commit()
    cur.close()
    conn.close()
    
    return session_id


def save_response(user_id: str, session_id: int, question_id: int, 
                  response: str, feedback: str, confidence: float, duration: int):
    """Save a user's response to a question."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO cc_interview_responses 
        (user_id, session_id, question_id, user_response, ai_feedback, confidence_score, duration_seconds)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """ if USE_POSTGRES else """
        INSERT INTO cc_interview_responses 
        (user_id, session_id, question_id, user_response, ai_feedback, confidence_score, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, session_id, question_id, response, feedback, confidence, duration))
    
    conn.commit()
    cur.close()
    conn.close()


def get_session_history(user_id: str, limit: int = 10) -> List[Dict]:
    """Get recent interview sessions for a user."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM cc_interview_sessions 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
    """ if USE_POSTGRES else """
        SELECT * FROM cc_interview_sessions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]


# Initialize tables and seed data
_ensure_tables()
_seed_questions()

# Main page content
st.markdown("""
<div class="cc-header">
    <h1>🎤 Interview Prep AI</h1>
    <p>Practice your college interview skills with AI-powered feedback</p>
</div>
""", unsafe_allow_html=True)

# Get user ID
user_id = st.session_state.get("user_id", "default_user")

# Tabs for different features
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Practice", "📚 Question Bank", "📊 Progress", "💡 Tips"])

with tab1:
    st.markdown("### Start a Practice Session")
    
    col1, col2 = st.columns(2)
    
    with col1:
        session_type = st.selectbox(
            "Session Type",
            ["General Practice", "College-Specific", "Quick 5-Minute Drill", "Full Mock Interview"]
        )
    
    with col2:
        if session_type == "College-Specific":
            college_name = st.text_input("College Name", placeholder="e.g., Harvard University")
        else:
            college_name = None
    
    difficulty = st.select_slider(
        "Difficulty Level",
        options=["easy", "medium", "hard"],
        value="medium"
    )
    
    if st.button("🚀 Start Practice Session", type="primary"):
        # Create session
        session_id = create_session(user_id, session_type, college_name)
        st.session_state["current_session_id"] = session_id
        st.session_state["session_active"] = True
        st.session_state["current_question_idx"] = 0
        
        # Get questions for session
        questions = get_questions(difficulty=difficulty)
        if questions:
            import random
            random.shuffle(questions)
            st.session_state["session_questions"] = questions[:5]  # 5 questions per session
        
        st.rerun()
    
    # Active session
    if st.session_state.get("session_active"):
        questions = st.session_state.get("session_questions", [])
        current_idx = st.session_state.get("current_question_idx", 0)
        
        if current_idx < len(questions):
            question = questions[current_idx]
            
            st.markdown(f"""
            <div class="question-card">
                <h3>Question {current_idx + 1} of {len(questions)}</h3>
                <p style="font-size: 1.2rem;">{question['question_text']}</p>
                <small>Category: {question['category']} | Difficulty: {question['difficulty']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if question.get('tips'):
                with st.expander("💡 Tips for this question"):
                    st.write(question['tips'])
            
            response = st.text_area(
                "Your Response",
                height=200,
                placeholder="Type your answer here...",
                key=f"response_{current_idx}"
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("⏭️ Skip"):
                    st.session_state["current_question_idx"] += 1
                    st.rerun()
            
            with col2:
                confidence = st.slider("Confidence Level", 1, 10, 5)
            
            with col3:
                if st.button("✅ Submit Answer", type="primary"):
                    if response:
                        # Generate simple feedback (in production, use AI)
                        feedback = f"Good effort! Your response addressed the question. Consider adding more specific examples."
                        
                        save_response(
                            user_id=user_id,
                            session_id=st.session_state["current_session_id"],
                            question_id=question['id'],
                            response=response,
                            feedback=feedback,
                            confidence=confidence,
                            duration=60  # Placeholder
                        )
                        
                        st.markdown(f"""
                        <div class="ai-response">
                            <h4>📝 Feedback</h4>
                            <p>{feedback}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.session_state["current_question_idx"] += 1
                        st.success("Answer saved! Moving to next question...")
                        st.rerun()
                    else:
                        st.warning("Please enter a response before submitting.")
        else:
            st.success("🎉 Session Complete!")
            st.session_state["session_active"] = False
            st.balloons()

with tab2:
    st.markdown("### 📚 Question Bank")
    
    categories = ["All", "personal", "academic", "extracurricular", "situational", "goals"]
    selected_category = st.selectbox("Filter by Category", categories)
    
    questions = get_questions(
        category=selected_category if selected_category != "All" else None
    )
    
    for q in questions:
        with st.expander(f"**{q['question_text']}** ({q['difficulty']})"):
            st.write(f"**Category:** {q['category']}")
            if q.get('tips'):
                st.write(f"**Tips:** {q['tips']}")
            if q.get('follow_up_questions'):
                st.write(f"**Follow-up Questions:** {q['follow_up_questions']}")

with tab3:
    st.markdown("### 📊 Your Progress")
    
    sessions = get_session_history(user_id)
    
    if sessions:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="metric-box">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total Sessions</div>
            </div>
            """.format(len(sessions)), unsafe_allow_html=True)
        
        with col2:
            total_questions = sum(s.get('questions_answered', 0) for s in sessions)
            st.markdown("""
            <div class="metric-box">
                <div class="metric-value">{}</div>
                <div class="metric-label">Questions Answered</div>
            </div>
            """.format(total_questions), unsafe_allow_html=True)
        
        with col3:
            avg_confidence = sum(s.get('avg_confidence_score', 0) for s in sessions) / len(sessions) if sessions else 0
            st.markdown("""
            <div class="metric-box">
                <div class="metric-value">{:.1f}</div>
                <div class="metric-label">Avg Confidence</div>
            </div>
            """.format(avg_confidence), unsafe_allow_html=True)
        
        st.markdown("### Recent Sessions")
        for session in sessions[:5]:
            st.markdown(f"""
            <div class="session-history">
                <strong>{session['session_type']}</strong><br>
                <small>{session.get('created_at', 'N/A')}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No practice sessions yet. Start practicing to track your progress!")

with tab4:
    st.markdown("### 💡 Interview Tips")
    
    tips = [
        ("Before the Interview", [
            "Research the college thoroughly - know their mission, values, and unique programs",
            "Prepare specific examples from your experiences",
            "Practice with a friend or family member",
            "Prepare thoughtful questions to ask your interviewer"
        ]),
        ("During the Interview", [
            "Make eye contact and speak clearly",
            "Use the STAR method for behavioral questions",
            "Be authentic - don't try to be someone you're not",
            "Take a moment to think before answering complex questions"
        ]),
        ("Common Mistakes to Avoid", [
            "Don't memorize answers word-for-word",
            "Avoid negative comments about other schools",
            "Don't interrupt the interviewer",
            "Never lie or exaggerate your accomplishments"
        ])
    ]
    
    for category, tip_list in tips:
        st.markdown(f"""
        <div class="tip-card">
            <h4>{category}</h4>
            <ul>
                {''.join(f'<li>{tip}</li>' for tip in tip_list)}
            </ul>
        </div>
        """, unsafe_allow_html=True)