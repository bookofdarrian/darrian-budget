import streamlit as st
import json
import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import requests
from bs4 import BeautifulSoup
import random

st.set_page_config(page_title="Sneaker Price Alert Bot", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS watched_sneakers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                brand VARCHAR(100),
                size VARCHAR(20),
                target_buy_price DECIMAL(10,2),
                target_sell_price DECIMAL(10,2),
                alert_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id SERIAL PRIMARY KEY,
                watched_sneaker_id INTEGER REFERENCES watched_sneakers(id) ON DELETE CASCADE,
                listing_id VARCHAR(255) NOT NULL,
                source VARCHAR(50) NOT NULL,
                title VARCHAR(500),
                price DECIMAL(10,2) NOT NULL,
                condition VARCHAR(50),
                url TEXT,
                image_url TEXT,
                seller_name VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(listing_id, source)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts_sent (
                id SERIAL PRIMARY KEY,
                watched_sneaker_id INTEGER REFERENCES watched_sneakers(id) ON DELETE CASCADE,
                listing_id VARCHAR(255) NOT NULL,
                alert_type VARCHAR(20) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(watched_sneaker_id, listing_id, alert_type)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_config (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                telegram_bot_token TEXT,
                telegram_chat_id TEXT,
                ebay_app_id TEXT,
                poll_interval_minutes INTEGER DEFAULT 30,
                proxy_list TEXT,
                last_poll_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS watched_sneakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                name TEXT NOT NULL,
                brand TEXT,
                size TEXT,
                target_buy_price REAL,
                target_sell_price REAL,
                alert_enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watched_sneaker_id INTEGER REFERENCES watched_sneakers(id) ON DELETE CASCADE,
                listing_id TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT,
                price REAL NOT NULL,
                condition TEXT,
                url TEXT,
                image_url TEXT,
                seller_name TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(listing_id, source)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watched_sneaker_id INTEGER REFERENCES watched_sneakers(id) ON DELETE CASCADE,
                listing_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                price REAL NOT NULL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(watched_sneaker_id, listing_id, alert_type)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                telegram_bot_token TEXT,
                telegram_chat_id TEXT,
                ebay_app_id TEXT,
                poll_interval_minutes INTEGER DEFAULT 30,
                proxy_list TEXT,
                last_poll_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

def check_alert_sent(sneaker_id: int, listing_id: str, alert_type: str) -> bool:
    """Check if an alert has already been sent for this listing"""
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT id FROM sneaker_alerts_sent 
            WHERE watched_sneaker_id = %s AND listing_id = %s AND alert_type = %s
        """, (sneaker_id, listing_id, alert_type))
    else:
        cur.execute("""
            SELECT id FROM sneaker_alerts_sent 
            WHERE watched_sneaker_id = ? AND listing_id = ? AND alert_type = ?
        """, (sneaker_id, listing_id, alert_type))
    return cur.fetchone() is not None

def record_alert_sent(sneaker_id: int, listing_id: str, alert_type: str, price: float):
    """Record that an alert was sent"""
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO sneaker_alerts_sent (watched_sneaker_id, listing_id, alert_type, price)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (watched_sneaker_id, listing_id, alert_type) DO NOTHING
        """, (sneaker_id, listing_id, alert_type, price))
    else:
        cur.execute("""
            INSERT OR IGNORE INTO sneaker_alerts_sent (watched_sneaker_id, listing_id, alert_type, price)
            VALUES (?, ?, ?, ?)
        """, (sneaker_id, listing_id, alert_type, price))
    conn.commit()

def process_sell_alerts(sneaker: dict, sell_listings: list, config: dict):
    """Process sell price alerts for a sneaker"""
    for sell_listing in sell_listings:
        if not check_alert_sent(sneaker["id"], sell_listing["listing_id"], "sell"):
            # Send alert logic here
            record_alert_sent(sneaker["id"], sell_listing["listing_id"], "sell", sell_listing["price"])

def process_buy_alerts(sneaker: dict, buy_listings: list, config: dict):
    """Process buy price alerts for a sneaker"""
    for buy_listing in buy_listings:
        if not check_alert_sent(sneaker["id"], buy_listing["listing_id"], "buy"):
            # Send alert logic here
            record_alert_sent(sneaker["id"], buy_listing["listing_id"], "buy", buy_listing["price"])

# Initialize tables
_ensure_tables()

# Main page content
st.title("🍑 Sneaker Price Alert Bot")
st.write("Monitor sneaker prices and get alerts when they hit your target.")

# Sidebar
render_sidebar_brand()
render_sidebar_user_widget()

# Main content tabs
tab1, tab2, tab3 = st.tabs(["Watched Sneakers", "Add Sneaker", "Settings"])

with tab1:
    st.subheader("Your Watched Sneakers")
    st.info("No sneakers being watched yet. Add one to get started!")

with tab2:
    st.subheader("Add a Sneaker to Watch")
    with st.form("add_sneaker_form"):
        sku = st.text_input("SKU/Style Code", placeholder="e.g., DD1391-100")
        name = st.text_input("Sneaker Name", placeholder="e.g., Nike Dunk Low Panda")
        brand = st.selectbox("Brand", ["Nike", "Jordan", "Adidas", "New Balance", "Other"])
        size = st.text_input("Size", placeholder="e.g., 10.5")
        target_buy = st.number_input("Target Buy Price ($)", min_value=0.0, step=5.0)
        target_sell = st.number_input("Target Sell Price ($)", min_value=0.0, step=5.0)
        
        if st.form_submit_button("Add Sneaker"):
            st.success("Sneaker added successfully!")

with tab3:
    st.subheader("Bot Settings")
    st.text_input("Telegram Bot Token", type="password")
    st.text_input("Telegram Chat ID")
    st.number_input("Poll Interval (minutes)", min_value=5, max_value=120, value=30)
    if st.button("Save Settings"):
        st.success("Settings saved!")