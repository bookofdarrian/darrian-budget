import streamlit as st
import json
import time
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import requests
from bs4 import BeautifulSoup
import threading

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
            CREATE TABLE IF NOT EXISTS tracked_sneakers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL,
                brand VARCHAR(100),
                model VARCHAR(255),
                sku VARCHAR(100),
                size VARCHAR(20),
                condition VARCHAR(50) DEFAULT 'any',
                buy_threshold DECIMAL(10,2),
                sell_threshold DECIMAL(10,2),
                market_value DECIMAL(10,2),
                last_checked TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id SERIAL PRIMARY KEY,
                sneaker_id INTEGER REFERENCES tracked_sneakers(id) ON DELETE CASCADE,
                platform VARCHAR(50) NOT NULL,
                listing_title VARCHAR(500),
                listing_url TEXT,
                listing_price DECIMAL(10,2) NOT NULL,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                total_price DECIMAL(10,2) NOT NULL,
                condition VARCHAR(50),
                seller_name VARCHAR(255),
                seller_rating DECIMAL(3,2),
                alert_type VARCHAR(20) NOT NULL,
                signal_strength VARCHAR(20),
                price_diff DECIMAL(10,2),
                price_diff_pct DECIMAL(5,2),
                is_sent BOOLEAN DEFAULT FALSE,
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                alert_id INTEGER REFERENCES price_alerts(id) ON DELETE SET NULL,
                sneaker_id INTEGER REFERENCES tracked_sneakers(id) ON DELETE SET NULL,
                platform VARCHAR(50),
                alert_type VARCHAR(20),
                message TEXT,
                telegram_message_id VARCHAR(100),
                telegram_chat_id VARCHAR(100),
                delivery_status VARCHAR(20) DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id SERIAL PRIMARY KEY,
                sneaker_id INTEGER REFERENCES tracked_sneakers(id) ON DELETE CASCADE,
                platform VARCHAR(50) NOT NULL,
                avg_price DECIMAL(10,2),
                min_price DECIMAL(10,2),
                max_price DECIMAL(10,2),
                listing_count INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                telegram_bot_token TEXT,
                telegram_chat_id VARCHAR(100),
                ebay_app_id TEXT,
                polling_interval_minutes INTEGER DEFAULT 30,
                max_alerts_per_hour INTEGER DEFAULT 10,
                alert_cooldown_minutes INTEGER DEFAULT 60,
                is_bot_active BOOLEAN DEFAULT FALSE,
                last_poll_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tracked_sneakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                sku TEXT,
                size TEXT,
                condition TEXT DEFAULT 'any',
                buy_threshold REAL,
                sell_threshold REAL,
                market_value REAL,
                last_checked TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sneaker_id INTEGER REFERENCES tracked_sneakers(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                listing_title TEXT,
                listing_url TEXT,
                listing_price REAL NOT NULL,
                shipping_cost REAL DEFAULT 0,
                total_price REAL NOT NULL,
                condition TEXT,
                seller_name TEXT,
                seller_rating REAL,
                alert_type TEXT NOT NULL,
                signal_strength TEXT,
                price_diff REAL,
                price_diff_pct REAL,
                is_sent INTEGER DEFAULT 0,
                sent_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                alert_id INTEGER REFERENCES price_alerts(id) ON DELETE SET NULL,
                sneaker_id INTEGER REFERENCES tracked_sneakers(id) ON DELETE SET NULL,
                platform TEXT,
                alert_type TEXT,
                message TEXT,
                telegram_message_id TEXT,
                telegram_chat_id TEXT,
                delivery_status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sneaker_id INTEGER REFERENCES tracked_sneakers(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                avg_price REAL,
                min_price REAL,
                max_price REAL,
                listing_count INTEGER,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                max_alerts_per_hour INTEGER DEFAULT 10,
                alert_cooldown_minutes INTEGER DEFAULT 60,
                is_bot_active INTEGER DEFAULT 0,
                last_poll_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

# Sidebar
render_sidebar_brand()
render_sidebar_user_widget()

st.title("👟 Sneaker Price Alert Bot")
st.markdown("Track sneaker prices and get alerts when deals match your criteria.")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Add Sneaker", "⚙️ Settings", "📜 Alert History"])

with tab1:
    st.subheader("Tracked Sneakers")
    conn = get_conn()
    cur = conn.cursor()
    user_id = st.session_state.get("user_id", 1)
    cur.execute("SELECT * FROM tracked_sneakers WHERE user_id = ?", (user_id,)) if not USE_POSTGRES else cur.execute("SELECT * FROM tracked_sneakers WHERE user_id = %s", (user_id,))
    sneakers = cur.fetchall()
    
    if sneakers:
        for sneaker in sneakers:
            st.write(f"**{sneaker[2]}** - Size: {sneaker[6]} - Buy: ${sneaker[8]} - Sell: ${sneaker[9]}")
    else:
        st.info("No sneakers tracked yet. Add one to get started!")

with tab2:
    st.subheader("Add New Sneaker to Track")
    with st.form("add_sneaker_form"):
        name = st.text_input("Sneaker Name")
        brand = st.selectbox("Brand", ["Nike", "Adidas", "Jordan", "New Balance", "Yeezy", "Other"])
        model = st.text_input("Model")
        sku = st.text_input("SKU (optional)")
        size = st.text_input("Size")
        buy_threshold = st.number_input("Buy Alert Threshold ($)", min_value=0.0, step=10.0)
        sell_threshold = st.number_input("Sell Alert Threshold ($)", min_value=0.0, step=10.0)
        
        if st.form_submit_button("Add Sneaker"):
            if name and size:
                conn = get_conn()
                cur = conn.cursor()
                user_id = st.session_state.get("user_id", 1)
                if USE_POSTGRES:
                    cur.execute("""
                        INSERT INTO tracked_sneakers (user_id, name, brand, model, sku, size, buy_threshold, sell_threshold)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, name, brand, model, sku, size, buy_threshold, sell_threshold))
                else:
                    cur.execute("""
                        INSERT INTO tracked_sneakers (user_id, name, brand, model, sku, size, buy_threshold, sell_threshold)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, name, brand, model, sku, size, buy_threshold, sell_threshold))
                conn.commit()
                st.success("Sneaker added successfully!")
                st.rerun()
            else:
                st.error("Please fill in required fields (Name and Size)")

with tab3:
    st.subheader("Bot Settings")
    user_id = st.session_state.get("user_id", 1)
    
    telegram_token = st.text_input("Telegram Bot Token", type="password")
    telegram_chat_id = st.text_input("Telegram Chat ID")
    polling_interval = st.slider("Polling Interval (minutes)", 5, 120, 30)
    
    if st.button("Save Settings"):
        conn = get_conn()
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO sneaker_bot_settings (user_id, telegram_bot_token, telegram_chat_id, polling_interval_minutes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                telegram_bot_token = EXCLUDED.telegram_bot_token,
                telegram_chat_id = EXCLUDED.telegram_chat_id,
                polling_interval_minutes = EXCLUDED.polling_interval_minutes
            """, (user_id, telegram_token, telegram_chat_id, polling_interval))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO sneaker_bot_settings (user_id, telegram_bot_token, telegram_chat_id, polling_interval_minutes)
                VALUES (?, ?, ?, ?)
            """, (user_id, telegram_token, telegram_chat_id, polling_interval))
        conn.commit()
        st.success("Settings saved!")

with tab4:
    st.subheader("Alert History")
    conn = get_conn()
    cur = conn.cursor()
    user_id = st.session_state.get("user_id", 1)
    
    if USE_POSTGRES:
        cur.execute("SELECT * FROM alert_history WHERE user_id = %s ORDER BY created_at DESC LIMIT 50", (user_id,))
    else:
        cur.execute("SELECT * FROM alert_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", (user_id,))
    
    alerts = cur.fetchall()
    
    if alerts:
        for alert in alerts:
            st.write(f"**{alert[4]}** - {alert[5]} - {alert[6]}")
    else:
        st.info("No alerts yet. Alerts will appear here when price thresholds are met.")