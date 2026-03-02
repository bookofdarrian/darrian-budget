import streamlit as st
import json
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal
import requests
import hashlib
import hmac

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


def _ensure_tables():
    """Create necessary tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        # Telegram messages table for logging
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id SERIAL PRIMARY KEY,
                message_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                user_id BIGINT,
                username VARCHAR(255),
                raw_text TEXT NOT NULL,
                parsed_category VARCHAR(100),
                parsed_amount DECIMAL(12, 2),
                parsed_description TEXT,
                parse_confidence DECIMAL(5, 2),
                parse_status VARCHAR(50) DEFAULT 'pending',
                expense_id INTEGER,
                manual_correction BOOLEAN DEFAULT FALSE,
                corrected_category VARCHAR(100),
                corrected_amount DECIMAL(12, 2),
                corrected_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                error_message TEXT,
                UNIQUE(message_id, chat_id)
            )
        """)
        
        # Telegram bot settings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_settings (
                id SERIAL PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Expense categories mapping for NLP
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expense_category_keywords (
                id SERIAL PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                keywords TEXT[],
                priority INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default category keywords if empty
        cur.execute("SELECT COUNT(*) FROM expense_category_keywords")
        if cur.fetchone()[0] == 0:
            default_categories = [
                ('Food & Dining', ['food', 'restaurant', 'lunch', 'dinner', 'breakfast', 'coffee', 'groceries', 'grocery', 'meal', 'eat', 'ate', 'chipotle', 'mcdonalds', 'starbucks', 'uber eats', 'doordash', 'grubhub'], 10),
                ('Transportation', ['gas', 'uber', 'lyft', 'taxi', 'parking', 'toll', 'marta', 'transit', 'car', 'fuel', 'metro'], 10),
                ('Shopping', ['amazon', 'target', 'walmart', 'clothes', 'shoes', 'sneakers', 'bought', 'purchase', 'shopping', 'store'], 8),
                ('Entertainment', ['netflix', 'spotify', 'movie', 'concert', 'game', 'gaming', 'subscription', 'hulu', 'disney'], 8),
                ('Bills & Utilities', ['electric', 'water', 'internet', 'phone', 'bill', 'rent', 'mortgage', 'insurance', 'utility'], 10),
                ('Health & Medical', ['doctor', 'pharmacy', 'medicine', 'gym', 'fitness', 'medical', 'dentist', 'health', 'hospital', 'prescription'], 9),
                ('Personal Care', ['haircut', 'barber', 'salon', 'spa', 'grooming'], 7),
                ('Education', ['book', 'course', 'class', 'tuition', 'udemy', 'coursera', 'training'], 7),
                ('Travel', ['flight', 'hotel', 'airbnb', 'vacation', 'trip', 'travel'], 8),
                ('Miscellaneous', ['misc', 'other', 'random'], 1),
            ]
            for cat, keywords, priority in default_categories:
                cur.execute("""
                    INSERT INTO expense_category_keywords (category, keywords, priority)
                    VALUES (%s, %s, %s)
                """, (cat, keywords, priority))
    else:
        # SQLite version
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                user_id BIGINT,
                username VARCHAR(255),
                raw_text TEXT NOT NULL,
                parsed_category VARCHAR(100),
                parsed_amount DECIMAL(12, 2),
                parsed_description TEXT,
                parse_confidence DECIMAL(5, 2),
                parse_status VARCHAR(50) DEFAULT 'pending',
                expense_id INTEGER,
                manual_correction BOOLEAN DEFAULT FALSE,
                corrected_category VARCHAR(100),
                corrected_amount DECIMAL(12, 2),
                corrected_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                error_message TEXT,
                UNIQUE(message_id, chat_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expense_category_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category VARCHAR(100) NOT NULL,
                keywords TEXT,
                priority INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


# Initialize tables
_ensure_tables()

# Main page content
st.title("🤖 Telegram Budget Bot")
st.markdown("Configure and manage your Telegram bot for tracking expenses.")

# Display message data placeholder
message_data = {
    "status": "ready",
    "message": "Bot configuration page loaded successfully"
}

st.json(message_data)