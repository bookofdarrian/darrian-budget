import streamlit as st
import json
import time
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import re
from bs4 import BeautifulSoup
import schedule
import threading

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Sneaker Price Alert Bot", page_icon="🍑", layout="wide")
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
    """Create all necessary tables for sneaker price tracking."""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            # Tracked sneakers watchlist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    sneaker_name VARCHAR(255) NOT NULL,
                    brand VARCHAR(100),
                    style_code VARCHAR(50),
                    size VARCHAR(20),
                    buy_threshold DECIMAL(10, 2),
                    sell_threshold DECIMAL(10, 2),
                    target_condition VARCHAR(50) DEFAULT 'any',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Price history from polling
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sneaker_price_history (
                    id SERIAL PRIMARY KEY,
                    watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                    source VARCHAR(50) NOT NULL,
                    listing_id VARCHAR(255),
                    title VARCHAR(500),
                    price DECIMAL(10, 2) NOT NULL,
                    shipping_cost DECIMAL(10, 2) DEFAULT 0,
                    condition VARCHAR(50),
                    seller_name VARCHAR(255),
                    listing_url TEXT,
                    image_url TEXT,
                    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alerts sent
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sneaker_alerts (
                    id SERIAL PRIMARY KEY,
                    watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                    price_history_id INTEGER REFERENCES sneaker_price_history(id) ON DELETE CASCADE,
                    alert_type VARCHAR(20) NOT NULL,
                    message TEXT,
                    telegram_sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Poll log for tracking last poll times
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sneaker_poll_log (
                    id SERIAL PRIMARY KEY,
                    watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                    source VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    listings_found INTEGER DEFAULT 0,
                    error_message TEXT,
                    polled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # SQLite versions
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    sneaker_name TEXT NOT NULL,
                    brand TEXT,
                    style_code TEXT,
                    size TEXT,
                    buy_threshold REAL,
                    sell_threshold REAL,
                    target_condition TEXT DEFAULT 'any',
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
                    listing_id TEXT,
                    title TEXT,
                    price REAL NOT NULL,
                    shipping_cost REAL DEFAULT 0,
                    condition TEXT,
                    seller_name TEXT,
                    listing_url TEXT,
                    image_url TEXT,
                    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (watchlist_id) REFERENCES sneaker_watchlist(id) ON DELETE CASCADE
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sneaker_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watchlist_id INTEGER,
                    price_history_id INTEGER,
                    alert_type TEXT NOT NULL,
                    message TEXT,
                    telegram_sent INTEGER DEFAULT 0,
                    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (watchlist_id) REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                    FOREIGN KEY (price_history_id) REFERENCES sneaker_price_history(id) ON DELETE CASCADE
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sneaker_poll_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watchlist_id INTEGER,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    listings_found INTEGER DEFAULT 0,
                    error_message TEXT,
                    polled_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (watchlist_id) REFERENCES sneaker_watchlist(id) ON DELETE CASCADE
                )
            """)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()


def save_price_history(watchlist_id: int, source: str, listing_id: str, title: str, 
                       price: float, shipping_cost: float, condition: str, 
                       seller_name: str, listing_url: str, image_url: str) -> int:
    """Save a price history record."""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO sneaker_price_history 
                (watchlist_id, source, listing_id, title, price, shipping_cost, condition, seller_name, listing_url, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (watchlist_id, source, listing_id, title, price, shipping_cost, condition, seller_name, listing_url, image_url))
            result = cur.fetchone()
            price_id = result[0] if result else None
        else:
            cur.execute("""
                INSERT INTO sneaker_price_history 
                (watchlist_id, source, listing_id, title, price, shipping_cost, condition, seller_name, listing_url, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (watchlist_id, source, listing_id, title, price, shipping_cost, condition, seller_name, listing_url, image_url))
            price_id = cur.lastrowid
        
        conn.commit()
        return price_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()


# Initialize tables
_ensure_tables()

# Main page content
st.title("👟 Sneaker Price Alert Bot")
st.markdown("Track sneaker prices and get alerts when they hit your target!")

# Placeholder for main functionality
st.info("This feature is under development. Add sneakers to your watchlist and set price alerts.")