import streamlit as st
import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading

st.set_page_config(page_title="Sneaker Price Alert Bot", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# Global scheduler instance
_scheduler = None
_scheduler_lock = threading.Lock()

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL,
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(255) NOT NULL,
                size VARCHAR(20),
                target_buy_price DECIMAL(10,2),
                target_sell_price DECIMAL(10,2),
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                listing_url TEXT,
                listing_title TEXT,
                condition VARCHAR(50),
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts_sent (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                alert_type VARCHAR(20) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                listing_url TEXT,
                message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sneaker_watchlist_sku ON sneaker_watchlist(sku)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sneaker_price_history_sku ON sneaker_price_history(sku)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sneaker_alerts_sent_sku ON sneaker_alerts_sent(sku)
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                price REAL NOT NULL,
                listing_url TEXT,
                listing_title TEXT,
                condition TEXT,
                scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                price REAL NOT NULL,
                listing_url TEXT,
                message TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

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

# Helper Functions
def get_watchlist(active_only=True):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if active_only:
        if USE_POSTGRES:
            cur.execute("SELECT * FROM sneaker_watchlist WHERE active = TRUE ORDER BY created_at DESC")
        else:
            cur.execute("SELECT * FROM sneaker_watchlist WHERE active = 1 ORDER BY created_at DESC")
    else:
        cur.execute("SELECT * FROM sneaker_watchlist ORDER BY created_at DESC")
    
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def add_to_watchlist(sku, brand, model, size=None, target_buy_price=None, target_sell_price=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        INSERT INTO sneaker_watchlist (sku, brand, model, size, target_buy_price, target_sell_price)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (sku, brand, model, size, target_buy_price, target_sell_price))
    
    conn.commit()
    conn.close()

def remove_from_watchlist(item_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"DELETE FROM sneaker_watchlist WHERE id = {ph}", (item_id,))
    conn.commit()
    conn.close()

def get_price_history(sku=None, days=30):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if sku:
        cur.execute(f"""
            SELECT * FROM sneaker_price_history 
            WHERE sku = {ph} 
            ORDER BY scraped_at DESC
        """, (sku,))
    else:
        cur.execute("SELECT * FROM sneaker_price_history ORDER BY scraped_at DESC LIMIT 100")
    
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def get_alerts_sent(limit=50):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT * FROM sneaker_alerts_sent ORDER BY sent_at DESC LIMIT {limit}")
    
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

# Main UI
st.title("👟 Sneaker Price Alert Bot")
st.markdown("Monitor sneaker prices across platforms and get alerts when prices hit your targets.")

tab1, tab2, tab3, tab4 = st.tabs(["📋 Watchlist", "➕ Add Sneaker", "📊 Price History", "🔔 Alerts"])

with tab1:
    st.subheader("Your Watchlist")
    
    watchlist = get_watchlist()
    
    if not watchlist:
        st.info("Your watchlist is empty. Add some sneakers to start tracking!")
    else:
        for item in watchlist:
            with st.expander(f"{item['brand']} {item['model']} - {item['sku']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Size:** {item['size'] or 'Any'}")
                with col2:
                    st.write(f"**Target Buy:** ${item['target_buy_price'] or 'N/A'}")
                with col3:
                    st.write(f"**Target Sell:** ${item['target_sell_price'] or 'N/A'}")
                
                if st.button("Remove", key=f"remove_{item['id']}"):
                    remove_from_watchlist(item['id'])
                    st.rerun()

with tab2:
    st.subheader("Add Sneaker to Watchlist")
    
    with st.form("add_sneaker_form"):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("SKU/Style Code", placeholder="e.g., DD1391-100")
            brand = st.selectbox("Brand", ["Nike", "Jordan", "Adidas", "New Balance", "Yeezy", "Other"])
        with col2:
            model = st.text_input("Model Name", placeholder="e.g., Air Jordan 1 Retro High OG")
            size = st.text_input("Size (optional)", placeholder="e.g., 10.5")
        
        col3, col4 = st.columns(2)
        with col3:
            target_buy = st.number_input("Target Buy Price ($)", min_value=0.0, step=5.0, value=0.0)
        with col4:
            target_sell = st.number_input("Target Sell Price ($)", min_value=0.0, step=5.0, value=0.0)
        
        submitted = st.form_submit_button("Add to Watchlist")
        
        if submitted:
            if sku and brand and model:
                add_to_watchlist(
                    sku, brand, model, 
                    size if size else None,
                    target_buy if target_buy > 0 else None,
                    target_sell if target_sell > 0 else None
                )
                st.success(f"Added {model} to watchlist!")
                st.rerun()
            else:
                st.error("Please fill in SKU, Brand, and Model")

with tab3:
    st.subheader("Price History")
    
    watchlist = get_watchlist(active_only=False)
    if watchlist:
        sku_options = ["All"] + [f"{item['sku']} - {item['model']}" for item in watchlist]
        selected = st.selectbox("Select Sneaker", sku_options)
        
        if selected != "All":
            sku = selected.split(" - ")[0]
            history = get_price_history(sku)
        else:
            history = get_price_history()
        
        if history:
            df = pd.DataFrame(history)
            st.dataframe(df)
            
            if len(df) > 1:
                fig = px.line(df, x='scraped_at', y='price', color='platform', 
                             title='Price History Over Time')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No price history available yet.")
    else:
        st.info("Add sneakers to your watchlist to see price history.")

with tab4:
    st.subheader("Recent Alerts")
    
    alerts = get_alerts_sent()
    
    if not alerts:
        st.info("No alerts have been sent yet.")
    else:
        for alert in alerts:
            alert_icon = "🟢" if alert['alert_type'] == 'buy' else "🔴"
            st.markdown(f"""
            {alert_icon} **{alert['sku']}** on {alert['platform']}  
            Price: ${alert['price']} | {alert['sent_at']}  
            {alert['message'] or ''}
            """)
            st.markdown("---")