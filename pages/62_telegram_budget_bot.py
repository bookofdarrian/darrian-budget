import streamlit as st
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import requests
import os

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Telegram Budget Bot", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

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

# Placeholder helper
def ph(count: int = 1) -> str:
    """Return correct placeholder(s) for current DB"""
    if count == 1:
        return "%s" if USE_POSTGRES else "?"
    return ", ".join(["%s" if USE_POSTGRES else "?" for _ in range(count)])


def _ensure_tables():
    """Create tables if they don't exist"""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id SERIAL PRIMARY KEY,
                message_id BIGINT,
                chat_id BIGINT,
                user_id BIGINT,
                username VARCHAR(255),
                raw_text TEXT,
                parsed_category VARCHAR(100),
                parsed_amount DECIMAL(10,2),
                parsed_description TEXT,
                parse_confidence DECIMAL(3,2),
                expense_id INTEGER,
                processed BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_config (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                chat_id BIGINT,
                is_active BOOLEAN DEFAULT TRUE,
                allowed_categories TEXT,
                default_category VARCHAR(100) DEFAULT 'Other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure expenses table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                category VARCHAR(100),
                amount DECIMAL(10,2),
                description TEXT,
                expense_date DATE,
                source VARCHAR(50) DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                user_id INTEGER,
                username TEXT,
                raw_text TEXT,
                parsed_category TEXT,
                parsed_amount REAL,
                parsed_description TEXT,
                parse_confidence REAL,
                expense_id INTEGER,
                processed INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                is_active INTEGER DEFAULT 1,
                allowed_categories TEXT,
                default_category TEXT DEFAULT 'Other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                amount REAL,
                description TEXT,
                expense_date DATE,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_ollama_endpoint() -> str:
    """Get Ollama endpoint from settings or environment"""
    endpoint = get_setting("ollama_endpoint")
    if not endpoint:
        endpoint = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
    return endpoint


# Initialize tables
_ensure_tables()

# Main page content
st.title("🍑 Telegram Budget Bot")
st.markdown("Configure and manage your Telegram budget bot integration.")

# Test input section
st.subheader("Test Message Parsing")
test_input = st.text_input(
    "Enter a test expense message",
    placeholder="e.g., Coffee $5.50 at Starbucks"
)

if test_input:
    st.info(f"You entered: {test_input}")