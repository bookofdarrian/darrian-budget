import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal

st.set_page_config(page_title="Weekly Spending Digest", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS digest_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                delivery_method VARCHAR(50) DEFAULT 'email',
                email_address VARCHAR(255),
                telegram_chat_id VARCHAR(100),
                delivery_day VARCHAR(20) DEFAULT 'sunday',
                delivery_time VARCHAR(10) DEFAULT '18:00',
                include_insights BOOLEAN DEFAULT TRUE,
                include_variance_alerts BOOLEAN DEFAULT TRUE,
                variance_threshold DECIMAL(5,2) DEFAULT 10.00,
                categories_to_include TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS digest_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                digest_date DATE NOT NULL,
                week_start DATE NOT NULL,
                week_end DATE NOT NULL,
                total_spent DECIMAL(12,2),
                category_breakdown JSONB,
                ai_insights TEXT,
                variance_alerts JSONB,
                delivery_status VARCHAR(50) DEFAULT 'pending',
                delivery_method VARCHAR(50),
                delivered_at TIMESTAMP,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_digest_history_user_date 
            ON digest_history(user_id, digest_date)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS digest_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                delivery_method TEXT DEFAULT 'email',
                email_address TEXT,
                telegram_chat_id TEXT,
                delivery_day TEXT DEFAULT 'sunday',
                delivery_time TEXT DEFAULT '18:00',
                include_insights INTEGER DEFAULT 1,
                include_variance_alerts INTEGER DEFAULT 1,
                variance_threshold REAL DEFAULT 10.00,
                categories_to_include TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS digest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                digest_date TEXT NOT NULL,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                total_spent REAL,
                category_breakdown TEXT,
                ai_insights TEXT,
                variance_alerts TEXT,
                delivery_status TEXT DEFAULT 'pending',
                delivery_method TEXT,
                delivered_at TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_digest_history_user_date 
            ON digest_history(user_id, digest_date)
        """)
    conn.commit()
    conn.close()

_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_week_bounds(reference_date=None):
    if reference_date is None:
        reference_date = datetime.now().date()
    days_since_monday = reference_date.weekday()
    week_start = reference_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

def get_previous_week_bounds(reference_date=None):
    if reference_date is None:
        reference_date = datetime.now().date()
    current_week_start, _ = get_week_bounds(reference_date)
    prev_week_end = current_week_start - timedelta(days=1)
    prev_week_start = prev_week_end - timedelta(days=6)
    return prev_week_start, prev_week_end

# Main page content
st.title("📊 Weekly Spending Digest")
st.markdown("Configure and view your weekly spending summaries.")

user_id = get_user_id()
week_start, week_end = get_week_bounds()

st.subheader(f"Current Week: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}")

# Placeholder for digest content
st.info("Weekly spending digest functionality is being set up.")