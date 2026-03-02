import streamlit as st
import json
import time
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
import base64
import re
from urllib.parse import quote_plus
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
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(255) NOT NULL,
                size VARCHAR(20),
                buy_threshold DECIMAL(10,2),
                sell_threshold DECIMAL(10,2),
                is_active BOOLEAN DEFAULT TRUE,
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                sku VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                condition VARCHAR(50),
                listing_url TEXT,
                listing_title TEXT,
                seller_name VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                alert_type VARCHAR(20) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                platform VARCHAR(50) NOT NULL,
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
                ebay_cert_id TEXT,
                ebay_oauth_token TEXT,
                ebay_token_expiry TIMESTAMP,
                polling_interval_minutes INTEGER DEFAULT 30,
                alerts_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sneaker_price_history_sku 
            ON sneaker_price_history(sku, timestamp DESC)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sneaker_watchlist_user 
            ON sneaker_watchlist(user_id, is_active)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                size TEXT,
                buy_threshold REAL,
                sell_threshold REAL,
                is_active INTEGER DEFAULT 1,
                last_checked TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                price REAL NOT NULL,
                condition TEXT,
                listing_url TEXT,
                listing_title TEXT,
                seller_name TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                alert_type TEXT NOT NULL,
                price REAL NOT NULL,
                platform TEXT NOT NULL,
                listing_url TEXT,
                message TEXT,
                is_sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent_at TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                telegram_bot_token TEXT,
                telegram_chat_id TEXT,
                ebay_app_id TEXT,
                ebay_cert_id TEXT,
                ebay_oauth_token TEXT,
                ebay_token_expiry TEXT,
                polling_interval_minutes INTEGER DEFAULT 30,
                alerts_enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

render_sidebar_brand()
render_sidebar_user_widget()

st.title("🍑 Sneaker Price Alert Bot")
st.markdown("Monitor sneaker prices and get alerts when they hit your target!")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 Watchlist", "📊 Price History", "🔔 Alerts", "⚙️ Settings"])

with tab1:
    st.subheader("Your Watchlist")
    
    with st.form("add_sneaker_form"):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("SKU", placeholder="e.g., DD1391-100")
            brand = st.text_input("Brand", placeholder="e.g., Nike")
            model = st.text_input("Model", placeholder="e.g., Air Jordan 1 Retro High OG")
        with col2:
            size = st.text_input("Size", placeholder="e.g., 10.5")
            buy_threshold = st.number_input("Buy Alert (under $)", min_value=0.0, step=10.0)
            sell_threshold = st.number_input("Sell Alert (over $)", min_value=0.0, step=10.0)
        
        submitted = st.form_submit_button("Add to Watchlist")
        if submitted and sku and brand and model:
            user_id = st.session_state.get("user_id", 1)
            conn = get_conn()
            cur = conn.cursor()
            try:
                if USE_POSTGRES:
                    cur.execute("""
                        INSERT INTO sneaker_watchlist (user_id, sku, brand, model, size, buy_threshold, sell_threshold)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, sku, size) DO UPDATE SET
                            brand = EXCLUDED.brand,
                            model = EXCLUDED.model,
                            buy_threshold = EXCLUDED.buy_threshold,
                            sell_threshold = EXCLUDED.sell_threshold,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, sku, brand, model, size, buy_threshold or None, sell_threshold or None))
                else:
                    cur.execute("""
                        INSERT OR REPLACE INTO sneaker_watchlist (user_id, sku, brand, model, size, buy_threshold, sell_threshold)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, sku, brand, model, size, buy_threshold or None, sell_threshold or None))
                conn.commit()
                st.success(f"Added {model} to watchlist!")
            except Exception as e:
                st.error(f"Error adding sneaker: {e}")
    
    # Display watchlist
    user_id = st.session_state.get("user_id", 1)
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("SELECT id, sku, brand, model, size, buy_threshold, sell_threshold, is_active FROM sneaker_watchlist WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    else:
        cur.execute("SELECT id, sku, brand, model, size, buy_threshold, sell_threshold, is_active FROM sneaker_watchlist WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    
    watchlist = cur.fetchall()
    if watchlist:
        for item in watchlist:
            with st.expander(f"{item[2]} {item[3]} - {item[1]} (Size: {item[4] or 'Any'})"):
                st.write(f"**Buy Alert:** ${item[5]}" if item[5] else "No buy alert set")
                st.write(f"**Sell Alert:** ${item[6]}" if item[6] else "No sell alert set")
                if st.button("Remove", key=f"remove_{item[0]}"):
                    if USE_POSTGRES:
                        cur.execute("DELETE FROM sneaker_watchlist WHERE id = %s", (item[0],))
                    else:
                        cur.execute("DELETE FROM sneaker_watchlist WHERE id = ?", (item[0],))
                    conn.commit()
                    st.rerun()
    else:
        st.info("Your watchlist is empty. Add some sneakers to monitor!")

with tab2:
    st.subheader("Price History")
    st.info("Price history will appear here once you start monitoring sneakers.")

with tab3:
    st.subheader("Recent Alerts")
    st.info("Alerts will appear here when prices hit your thresholds.")

with tab4:
    st.subheader("Bot Settings")
    
    with st.form("settings_form"):
        st.markdown("### Telegram Notifications")
        telegram_bot_token = st.text_input("Telegram Bot Token", type="password")
        telegram_chat_id = st.text_input("Telegram Chat ID")
        
        st.markdown("### eBay API")
        ebay_app_id = st.text_input("eBay App ID", type="password")
        ebay_cert_id = st.text_input("eBay Cert ID", type="password")
        
        st.markdown("### Polling Settings")
        polling_interval = st.slider("Check prices every (minutes)", 15, 120, 30)
        alerts_enabled = st.checkbox("Enable alerts", value=True)
        
        if st.form_submit_button("Save Settings"):
            st.success("Settings saved!")