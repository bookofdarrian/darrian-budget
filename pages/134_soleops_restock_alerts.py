import streamlit as st
import json
import random
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# Page config must be first
st.set_page_config(page_title="SoleOps Restock Alerts", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

# Initialize
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

# Placeholder helper
def ph(count: int = 1) -> str:
    """Return correct placeholder syntax based on database type."""
    if USE_POSTGRES:
        return ", ".join(["%s"] * count) if count > 1 else "%s"
    return ", ".join(["?"] * count) if count > 1 else "?"

def _ensure_tables():
    """Create tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Restock watchlist table
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restock_watchlist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                product_name VARCHAR(255),
                retailer VARCHAR(100) NOT NULL,
                product_url TEXT,
                target_price DECIMAL(10,2),
                size VARCHAR(20),
                is_active BOOLEAN DEFAULT TRUE,
                last_checked TIMESTAMP,
                last_in_stock TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restock_alerts_log (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER REFERENCES restock_watchlist(id),
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                product_name VARCHAR(255),
                retailer VARCHAR(100) NOT NULL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price DECIMAL(10,2),
                sizes_available TEXT,
                notified BOOLEAN DEFAULT FALSE,
                notification_sent_at TIMESTAMP,
                product_url TEXT,
                estimated_margin DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restock_retailer_status (
                id SERIAL PRIMARY KEY,
                retailer VARCHAR(100) NOT NULL UNIQUE,
                is_online BOOLEAN DEFAULT TRUE,
                last_check TIMESTAMP,
                last_success TIMESTAMP,
                error_count INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restock_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                product_name TEXT,
                retailer TEXT NOT NULL,
                product_url TEXT,
                target_price REAL,
                size TEXT,
                is_active INTEGER DEFAULT 1,
                last_checked TEXT,
                last_in_stock TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restock_alerts_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                product_name TEXT,
                retailer TEXT NOT NULL,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                price REAL,
                sizes_available TEXT,
                notified INTEGER DEFAULT 0,
                notification_sent_at TEXT,
                product_url TEXT,
                estimated_margin REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (watchlist_id) REFERENCES restock_watchlist(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restock_retailer_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retailer TEXT NOT NULL UNIQUE,
                is_online INTEGER DEFAULT 1,
                last_check TEXT,
                last_success TEXT,
                error_count INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

# Initialize tables
_ensure_tables()

# Main page title
st.title("🔔 SoleOps Restock Alerts")

st.markdown("""
Monitor your favorite products and get notified when they restock!
""")

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["📋 Watchlist", "🚨 Recent Alerts", "⚙️ Settings"])

with tab1:
    st.subheader("Your Watchlist")
    
    # Add new item form
    with st.expander("➕ Add New Item to Watch"):
        col1, col2 = st.columns(2)
        with col1:
            new_sku = st.text_input("SKU", key="new_sku")
            new_product_name = st.text_input("Product Name", key="new_product_name")
            new_retailer = st.selectbox("Retailer", ["Nike", "Adidas", "Footlocker", "JD Sports", "Other"], key="new_retailer")
        with col2:
            new_url = st.text_input("Product URL", key="new_url")
            new_target_price = st.number_input("Target Price ($)", min_value=0.0, step=1.0, key="new_target_price")
            new_size = st.text_input("Size (optional)", key="new_size")
        
        if st.button("Add to Watchlist", type="primary"):
            if new_sku and new_retailer:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute(f"""
                    INSERT INTO restock_watchlist (user_id, sku, product_name, retailer, product_url, target_price, size)
                    VALUES ({ph(7)})
                """, (st.session_state.get("user_id", 1), new_sku, new_product_name, new_retailer, new_url, new_target_price if new_target_price > 0 else None, new_size if new_size else None))
                conn.commit()
                st.success("Item added to watchlist!")
                st.rerun()
            else:
                st.error("Please enter at least SKU and Retailer")
    
    # Display watchlist
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, sku, product_name, retailer, product_url, target_price, size, is_active, last_checked, last_in_stock
        FROM restock_watchlist
        WHERE user_id = %s
        ORDER BY created_at DESC
    """ if USE_POSTGRES else """
        SELECT id, sku, product_name, retailer, product_url, target_price, size, is_active, last_checked, last_in_stock
        FROM restock_watchlist
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (st.session_state.get("user_id", 1),))
    
    watchlist = cur.fetchall()
    
    if watchlist:
        for item in watchlist:
            item_id, sku, product_name, retailer, product_url, target_price, size, is_active, last_checked, last_in_stock = item
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    status_emoji = "✅" if is_active else "⏸️"
                    st.markdown(f"**{status_emoji} {product_name or sku}** ({retailer})")
                    st.caption(f"SKU: {sku} | Size: {size or 'Any'} | Target: ${target_price or 'N/A'}")
                with col2:
                    if last_in_stock:
                        st.caption(f"Last in stock: {last_in_stock}")
                with col3:
                    if st.button("🗑️", key=f"del_{item_id}"):
                        cur.execute(f"DELETE FROM restock_watchlist WHERE id = {ph()}", (item_id,))
                        conn.commit()
                        st.rerun()
                st.divider()
    else:
        st.info("Your watchlist is empty. Add items to start monitoring!")

with tab2:
    st.subheader("Recent Restock Alerts")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sku, product_name, retailer, detected_at, price, sizes_available, product_url, estimated_margin
        FROM restock_alerts_log
        WHERE user_id = %s
        ORDER BY detected_at DESC
        LIMIT 50
    """ if USE_POSTGRES else """
        SELECT sku, product_name, retailer, detected_at, price, sizes_available, product_url, estimated_margin
        FROM restock_alerts_log
        WHERE user_id = ?
        ORDER BY detected_at DESC
        LIMIT 50
    """, (st.session_state.get("user_id", 1),))
    
    alerts = cur.fetchall()
    
    if alerts:
        for alert in alerts:
            sku, product_name, retailer, detected_at, price, sizes_available, product_url, estimated_margin = alert
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**🚨 {product_name or sku}** - {retailer}")
                    st.caption(f"Detected: {detected_at} | Price: ${price or 'N/A'} | Sizes: {sizes_available or 'Unknown'}")
                with col2:
                    if product_url:
                        st.link_button("🔗 View", product_url)
                st.divider()
    else:
        st.info("No restock alerts yet. Keep monitoring!")

with tab3:
    st.subheader("Alert Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Notification Preferences**")
        email_alerts = st.checkbox("Email Alerts", value=True)
        push_alerts = st.checkbox("Push Notifications", value=False)
        
    with col2:
        st.markdown("**Check Frequency**")
        check_interval = st.selectbox("Check Interval", ["1 minute", "5 minutes", "15 minutes", "30 minutes", "1 hour"])
    
    if st.button("Save Settings", type="primary"):
        st.success("Settings saved!")