import streamlit as st
import json
import time
import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import threading
import schedule
from bs4 import BeautifulSoup
import urllib.parse

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Sneaker Price Alert Bot", page_icon="🍑", layout="wide")
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
    """Create all required tables for sneaker price tracking."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sneaker_name VARCHAR(255) NOT NULL,
                brand VARCHAR(100),
                model VARCHAR(255),
                size VARCHAR(20),
                color VARCHAR(100),
                sku VARCHAR(100),
                buy_threshold DECIMAL(10, 2),
                sell_threshold DECIMAL(10, 2),
                retail_price DECIMAL(10, 2),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                source VARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                listing_url TEXT,
                listing_title TEXT,
                condition VARCHAR(50),
                seller VARCHAR(255),
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                alert_type VARCHAR(20) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                source VARCHAR(50) NOT NULL,
                listing_url TEXT,
                message TEXT,
                is_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                telegram_bot_token TEXT,
                telegram_chat_id TEXT,
                ebay_app_id TEXT,
                polling_interval_minutes INTEGER DEFAULT 30,
                alerts_enabled BOOLEAN DEFAULT TRUE,
                last_poll_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sneaker_name TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                size TEXT,
                color TEXT,
                sku TEXT,
                buy_threshold REAL,
                sell_threshold REAL,
                retail_price REAL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER,
                source TEXT NOT NULL,
                price REAL NOT NULL,
                listing_url TEXT,
                listing_title TEXT,
                condition TEXT,
                seller TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (watchlist_id) REFERENCES sneaker_watchlist(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER,
                alert_type TEXT NOT NULL,
                price REAL NOT NULL,
                source TEXT NOT NULL,
                listing_url TEXT,
                message TEXT,
                is_sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent_at TEXT,
                FOREIGN KEY (watchlist_id) REFERENCES sneaker_watchlist(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                telegram_bot_token TEXT,
                telegram_chat_id TEXT,
                ebay_app_id TEXT,
                polling_interval_minutes INTEGER DEFAULT 30,
                alerts_enabled INTEGER DEFAULT 1,
                last_poll_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


def poll_prices_for_sneaker(sneaker: Dict) -> List[Dict]:
    """Poll prices for a specific sneaker from various sources."""
    results = []
    # Implementation would go here
    return results


# Initialize tables
_ensure_tables()

# Main UI
st.title("👟 Sneaker Price Alert Bot")
st.write("Track sneaker prices and get alerts when they hit your buy/sell thresholds.")