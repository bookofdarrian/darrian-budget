import streamlit as st
import json
from datetime import datetime
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="College List Builder | College Confused", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_colleges (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT,
                state TEXT,
                region TEXT,
                is_hbcu BOOLEAN DEFAULT FALSE,
                is_public BOOLEAN DEFAULT TRUE,
                acceptance_rate NUMERIC(5,2),
                avg_cost INTEGER,
                avg_net_cost INTEGER,
                enrollment INTEGER,
                graduation_rate NUMERIC(5,2),
                popular_majors JSONB DEFAULT '[]'::jsonb,
                website TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_user_college_lists (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                college_id INTEGER NOT NULL REFERENCES cc_colleges(id) ON DELETE CASCADE,
                notes TEXT,
                status TEXT DEFAULT 'Considering',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, college_id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_colleges_state ON cc_colleges(state)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_colleges_hbcu ON cc_colleges(is_hbcu)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_user_lists_user ON cc_user_college_lists(user_id)")
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_colleges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT,
                state TEXT,
                region TEXT,
                is_hbcu INTEGER DEFAULT 0,
                is_public INTEGER DEFAULT 1,
                acceptance_rate REAL,
                avg_cost INTEGER,
                avg_net_cost INTEGER,
                enrollment INTEGER,
                graduation_rate REAL,
                popular_majors TEXT DEFAULT '[]',
                website TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_user_college_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                college_id INTEGER NOT NULL,
                notes TEXT,
                status TEXT DEFAULT 'Considering',
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, college_id)
            )
        """)
    conn.commit()
    conn.close()

def _seed_colleges():
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute("SELECT COUNT(*) FROM cc_colleges")
    count = cur.fetchone()[0]
    if count > 0:
        conn.close()
        return
    colleges = [
        ("Harvard University", "Cambridge", "MA", "Northeast", False, False, 3.4, 57261, 18037, 31345, 97.5, '["Economics", "Computer Science", "Political Science", "Biology", "Mathematics"]', "https://www.harvard.edu"),
        ("Stanford University", "Stanford", "CA", "West", False, False, 3.7, 58416, 17271, 17680, 96.0, '["Computer Science", "Engineering", "Biology", "Economics", "Human Biology"]', "https://www.stanford.edu"),
        ("Massachusetts Institute of Technology", "Cambridge", "MA", "Northeast", False, False, 3.2, 58240, 24266, 11858, 96.0, '["Computer Science", "Engineering", "Mathematics", "Physics", "Biology"]', "https://www.mit.edu"),
        ("Yale University", "New Haven", "CT", "Northeast", False, False, 4.6, 62250, 17683, 14776, 97.0, '["Economics", "Political Science", "History", "Biology", "Psychology"]', "https://www.yale.edu"),
        ("Princeton University", "Princeton", "NJ", "Northeast", False, False, 4.0, 59710, 16562, 8623, 98.0, '["Computer Science", "Economics", "Public Policy", "Engineering", "History"]', "https://www.princeton.edu"),
        ("Columbia University", "New York", "NY", "Northeast", False, False, 3.9, 66139, 19854, 36649, 96.0, '["Economics", "Computer Science", "Political Science", "Psychology", "English"]', "https://www.columbia.edu"),
        ("University of Pennsylvania", "Philadelphia", "PA", "Northeast", False, False, 5.9, 63452, 24733, 28201, 96.0, '["Finance", "Economics", "Nursing", "Biology", "Computer Science"]', "https://www.upenn.edu"),
        ("Duke University", "Durham", "NC", "South", False, False, 6.0, 62688, 23513, 17620, 96.0, '["Computer Science", "Economics", "Public Policy", "Biology", "Engineering"]', "https://www.duke.edu"),
        ("University of Miami", "Coral Gables", "FL", "South", False, False, 19.0, 58636, 34000, 19096, 83.0, '["Business", "Biology", "Nursing", "Engineering", "Psychology"]', "https://www.miami.edu"),
    ]
    for college in colleges:
        cur.execute(f"""
            INSERT INTO cc_colleges (name, city, state, region, is_hbcu, is_public, acceptance_rate, avg_cost, avg_net_cost, enrollment, graduation_rate, popular_majors, website)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, college)
    conn.commit()
    conn.close()

_ensure_tables()
_seed_colleges()

st.title("🎓 College List Builder")
st.write("Build and manage your college list.")