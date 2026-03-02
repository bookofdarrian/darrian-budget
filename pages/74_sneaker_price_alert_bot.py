import streamlit as st
import requests
import json
import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

st.set_page_config(page_title="Sneaker Price Alert Bot", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

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
    """Create required database tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL,
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(255) NOT NULL,
                size VARCHAR(20),
                target_buy_price DECIMAL(10, 2),
                target_sell_price DECIMAL(10, 2),
                active BOOLEAN DEFAULT TRUE,
                notify_telegram BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                condition VARCHAR(50),
                size VARCHAR(20),
                listing_url TEXT,
                listing_title TEXT,
                seller_name VARCHAR(255),
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL,
                alert_type VARCHAR(20) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                listing_url TEXT,
                message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_sku 
            ON sneaker_price_history(sku)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_scraped 
            ON sneaker_price_history(scraped_at)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_alerts_sku 
            ON sneaker_alerts(sku)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                size TEXT,
                target_buy_price REAL,
                target_sell_price REAL,
                active INTEGER DEFAULT 1,
                notify_telegram INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                price REAL NOT NULL,
                condition TEXT,
                size TEXT,
                listing_url TEXT,
                listing_title TEXT,
                seller_name TEXT,
                scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                platform TEXT NOT NULL,
                price REAL NOT NULL,
                listing_url TEXT,
                message TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_bot_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


def get_watchlist():
    """Get all items from watchlist."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sneaker_watchlist ORDER BY created_at DESC")
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def add_to_watchlist(sku: str, brand: str, model: str, size: str = None, 
                     target_buy_price: float = None, target_sell_price: float = None):
    """Add a sneaker to the watchlist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO sneaker_watchlist (sku, brand, model, size, target_buy_price, target_sell_price)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (sku, size) DO UPDATE SET
                brand = EXCLUDED.brand,
                model = EXCLUDED.model,
                target_buy_price = EXCLUDED.target_buy_price,
                target_sell_price = EXCLUDED.target_sell_price,
                updated_at = CURRENT_TIMESTAMP
        """, (sku, brand, model, size, target_buy_price, target_sell_price))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO sneaker_watchlist (sku, brand, model, size, target_buy_price, target_sell_price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sku, brand, model, size, target_buy_price, target_sell_price))
    
    conn.commit()


def remove_from_watchlist(item_id: int):
    """Remove an item from the watchlist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM sneaker_watchlist WHERE id = %s", (item_id,))
    else:
        cur.execute("DELETE FROM sneaker_watchlist WHERE id = ?", (item_id,))
    
    conn.commit()


def get_price_history(sku: str = None, days: int = 30):
    """Get price history for a SKU or all SKUs."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        if sku:
            cur.execute("""
                SELECT * FROM sneaker_price_history 
                WHERE sku = %s AND scraped_at > NOW() - INTERVAL '%s days'
                ORDER BY scraped_at DESC
            """, (sku, days))
        else:
            cur.execute("""
                SELECT * FROM sneaker_price_history 
                WHERE scraped_at > NOW() - INTERVAL '%s days'
                ORDER BY scraped_at DESC
            """, (days,))
    else:
        if sku:
            cur.execute("""
                SELECT * FROM sneaker_price_history 
                WHERE sku = ? AND scraped_at > datetime('now', '-' || ? || ' days')
                ORDER BY scraped_at DESC
            """, (sku, days))
        else:
            cur.execute("""
                SELECT * FROM sneaker_price_history 
                WHERE scraped_at > datetime('now', '-' || ? || ' days')
                ORDER BY scraped_at DESC
            """, (days,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def get_alerts(acknowledged: bool = None):
    """Get alerts, optionally filtered by acknowledged status."""
    conn = get_conn()
    cur = conn.cursor()
    
    if acknowledged is None:
        cur.execute("SELECT * FROM sneaker_alerts ORDER BY sent_at DESC")
    else:
        if USE_POSTGRES:
            cur.execute("SELECT * FROM sneaker_alerts WHERE acknowledged = %s ORDER BY sent_at DESC", (acknowledged,))
        else:
            cur.execute("SELECT * FROM sneaker_alerts WHERE acknowledged = ? ORDER BY sent_at DESC", (1 if acknowledged else 0,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def acknowledge_alert(alert_id: int):
    """Mark an alert as acknowledged."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("UPDATE sneaker_alerts SET acknowledged = TRUE WHERE id = %s", (alert_id,))
    else:
        cur.execute("UPDATE sneaker_alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    
    conn.commit()


# Initialize tables
_ensure_tables()

# Main UI
st.title("👟 Sneaker Price Alert Bot")
st.markdown("Track sneaker prices and get alerts when they hit your target!")

tab1, tab2, tab3, tab4 = st.tabs(["📋 Watchlist", "📊 Price History", "🔔 Alerts", "⚙️ Settings"])

with tab1:
    st.subheader("Add to Watchlist")
    
    col1, col2 = st.columns(2)
    with col1:
        new_sku = st.text_input("SKU", placeholder="e.g., DD1391-100")
        new_brand = st.text_input("Brand", placeholder="e.g., Nike")
        new_model = st.text_input("Model", placeholder="e.g., Air Jordan 1 Retro High OG")
    
    with col2:
        new_size = st.text_input("Size (optional)", placeholder="e.g., 10.5")
        new_buy_price = st.number_input("Target Buy Price ($)", min_value=0.0, step=5.0)
        new_sell_price = st.number_input("Target Sell Price ($)", min_value=0.0, step=5.0)
    
    if st.button("➕ Add to Watchlist"):
        if new_sku and new_brand and new_model:
            add_to_watchlist(
                new_sku, new_brand, new_model, 
                new_size if new_size else None,
                new_buy_price if new_buy_price > 0 else None,
                new_sell_price if new_sell_price > 0 else None
            )
            st.success(f"Added {new_model} to watchlist!")
            st.rerun()
        else:
            st.error("Please fill in SKU, Brand, and Model")
    
    st.markdown("---")
    st.subheader("Current Watchlist")
    
    watchlist = get_watchlist()
    if watchlist:
        for item in watchlist:
            with st.expander(f"**{item['model']}** ({item['sku']}) - Size: {item['size'] or 'All'}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**Brand:** {item['brand']}")
                    st.write(f"**Target Buy:** ${item['target_buy_price'] or 'Not set'}")
                with col2:
                    st.write(f"**SKU:** {item['sku']}")
                    st.write(f"**Target Sell:** ${item['target_sell_price'] or 'Not set'}")
                with col3:
                    if st.button("🗑️ Remove", key=f"remove_{item['id']}"):
                        remove_from_watchlist(item['id'])
                        st.rerun()
    else:
        st.info("No items in watchlist. Add some sneakers to track!")

with tab2:
    st.subheader("Price History")
    
    history = get_price_history(days=30)
    if history:
        df = pd.DataFrame(history)
        
        # Price chart
        fig = px.line(df, x='scraped_at', y='price', color='sku', 
                      title='Price Trends Over Time')
        st.plotly_chart(fig, use_container_width=True)
        
        # Data table
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No price history yet. Prices will be recorded as the bot runs.")

with tab3:
    st.subheader("Price Alerts")
    
    show_acknowledged = st.checkbox("Show acknowledged alerts")
    alerts = get_alerts(acknowledged=None if show_acknowledged else False)
    
    if alerts:
        for alert in alerts:
            alert_color = "🟢" if alert['alert_type'] == 'buy' else "🔴"
            with st.expander(f"{alert_color} {alert['sku']} - ${alert['price']} ({alert['platform']})"):
                st.write(alert['message'])
                if alert['listing_url']:
                    st.markdown(f"[View Listing]({alert['listing_url']})")
                if not alert['acknowledged']:
                    if st.button("✓ Acknowledge", key=f"ack_{alert['id']}"):
                        acknowledge_alert(alert['id'])
                        st.rerun()
    else:
        st.info("No alerts yet!")

with tab4:
    st.subheader("Bot Settings")
    
    st.markdown("### Telegram Notifications")
    telegram_token = st.text_input("Telegram Bot Token", type="password", 
                                   value=get_setting("telegram_bot_token") or "")
    telegram_chat_id = st.text_input("Telegram Chat ID", 
                                     value=get_setting("telegram_chat_id") or "")
    
    if st.button("💾 Save Telegram Settings"):
        set_setting("telegram_bot_token", telegram_token)
        set_setting("telegram_chat_id", telegram_chat_id)
        st.success("Telegram settings saved!")
    
    st.markdown("### Scan Interval")
    scan_interval = st.number_input("Scan interval (minutes)", min_value=5, max_value=1440, 
                                    value=int(get_setting("scan_interval") or 30))
    
    if st.button("💾 Save Scan Interval"):
        set_setting("scan_interval", str(scan_interval))
        st.success("Scan interval saved!")