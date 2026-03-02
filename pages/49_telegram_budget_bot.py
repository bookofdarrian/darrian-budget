import streamlit as st
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import threading
import queue
import re

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Telegram Budget Bot", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    """Create telegram_messages table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT,
                username VARCHAR(255),
                message_id BIGINT,
                message_text TEXT,
                parsed_amount DECIMAL(10, 2),
                parsed_category VARCHAR(100),
                parsed_merchant VARCHAR(255),
                parsed_date DATE,
                parse_confidence DECIMAL(3, 2),
                status VARCHAR(50) DEFAULT 'pending',
                expense_id INTEGER REFERENCES expenses(id),
                raw_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_messages_chat_id 
            ON telegram_messages(chat_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_messages_status 
            ON telegram_messages(status)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_messages_created 
            ON telegram_messages(created_at DESC)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER,
                username TEXT,
                message_id INTEGER,
                message_text TEXT,
                parsed_amount REAL,
                parsed_category TEXT,
                parsed_merchant TEXT,
                parsed_date TEXT,
                parse_confidence REAL,
                status TEXT DEFAULT 'pending',
                expense_id INTEGER,
                raw_response TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_bot_config(key: str) -> Optional[str]:
    """Get bot configuration value."""
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT config_value FROM telegram_bot_config WHERE config_key = {ph}", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_bot_config(key: str, value: str):
    """Set bot configuration value."""
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO telegram_bot_config (config_key, config_value, updated_at)
            VALUES ({ph}, {ph}, CURRENT_TIMESTAMP)
            ON CONFLICT (config_key) DO UPDATE SET 
                config_value = EXCLUDED.config_value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, value))
    else:
        cur.execute(f"""
            INSERT OR REPLACE INTO telegram_bot_config (config_key, config_value, updated_at)
            VALUES ({ph}, {ph}, CURRENT_TIMESTAMP)
        """, (key, value))
    
    conn.commit()
    conn.close()


# Initialize tables
_ensure_tables()

# Main page content
st.title("🍑 Telegram Budget Bot")
st.markdown("Configure and manage your Telegram bot for expense tracking.")

# Configuration section
st.header("Bot Configuration")

bot_token = get_bot_config("bot_token") or ""
new_token = st.text_input("Bot Token", value=bot_token, type="password", help="Enter your Telegram bot token from @BotFather")

if st.button("Save Configuration"):
    if new_token:
        set_bot_config("bot_token", new_token)
        st.success("Configuration saved!")
    else:
        st.error("Please enter a valid bot token")

# Status section
st.header("Bot Status")
st.info("NLP Backend: Configure your bot token above to get started.")

# Messages section
st.header("Recent Messages")
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT * FROM telegram_messages ORDER BY created_at DESC LIMIT 10")
messages = cur.fetchall()
conn.close()

if messages:
    for msg in messages:
        st.write(msg)
else:
    st.info("No messages yet. Start chatting with your bot!")