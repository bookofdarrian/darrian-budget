import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import requests
import base64
import urllib.parse

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Platform Sales Sync", page_icon="🍑", layout="wide")
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

PH = "%s" if USE_POSTGRES else "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    # Platform connections table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_platform_connections (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            credentials_encrypted TEXT NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            token_expiry TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            last_sync_at TIMESTAMP,
            sync_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, platform)
        )
    """)
    
    # Synced sales tracking table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_synced_sales (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            platform_order_id TEXT NOT NULL,
            dedup_key TEXT NOT NULL UNIQUE,
            sold_order_id INTEGER,
            item_title TEXT,
            sale_price REAL,
            platform_fees REAL,
            actual_fees REAL,
            shipping_cost REAL,
            net_amount REAL,
            buyer_username TEXT,
            sale_date TIMESTAMP,
            sync_status TEXT DEFAULT 'synced',
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fee_reconciled BOOLEAN DEFAULT FALSE,
            fee_difference REAL DEFAULT 0
        )
    """)
    
    # Sync history log
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_sync_logs (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            sync_type TEXT DEFAULT 'manual',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT DEFAULT 'running',
            orders_found INTEGER DEFAULT 0,
            orders_imported INTEGER DEFAULT 0,
            orders_skipped INTEGER DEFAULT 0,
            error_message TEXT,
            details TEXT
        )
    """)
    
    # Auto-sync schedule configuration
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_sync_schedules (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            is_enabled BOOLEAN DEFAULT FALSE,
            frequency_hours INTEGER DEFAULT 24,
            last_scheduled_run TIMESTAMP,
            next_scheduled_run TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, platform)
        )
    """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Platform fee structures
PLATFORM_FEES = {
    "ebay": {
        "final_value_fee": 0.1325,  # 13.25% for most categories
        "payment_processing": 0.029,  # 2.9%
        "payment_fixed": 0.30,  # $0.30 per order
        "international_fee": 0.015,  # 1.5% additional for international
    },
    "mercari": {
        "selling_fee": 0.10,  # 10% flat fee
        "payment_processing": 0.029,  # 2.9%
        "payment_fixed": 0.50,  # $0.50 per order
    },
    "depop": {
        "selling_fee": 0.10,  # 10% flat fee
        "payment_processing": 0.029,  # 2.9% (PayPal/Depop Payments)
        "payment_fixed": 0.30,  # $0.30 per order
    }
}

def calculate_platform_fees(platform: str, sale_price: float, shipping: float = 0, is_international: bool = False) -> Dict[str, float]:
    """Calculate expected platform fees based on sale price"""
    fees = PLATFORM_FEES.get(platform, {})
    result = {
        "selling_fee": 0.0,
        "payment_processing": 0.0,
        "payment_fixed": 0.0,
        "international_fee": 0.0,
        "total_fees": 0.0
    }
    
    if platform == "ebay":
        result["selling_fee"] = sale_price * fees.get("final_value_fee", 0)
        result["payment_processing"] = sale_price * fees.get("payment_processing", 0)
        result["payment_fixed"] = fees.get("payment_fixed", 0)
        if is_international:
            result["international_fee"] = sale_price * fees.get("international_fee", 0)
    elif platform == "mercari":
        result["selling_fee"] = sale_price * fees.get("selling_fee", 0)
        result["payment_processing"] = sale_price * fees.get("payment_processing", 0)
        result["payment_fixed"] = fees.get("payment_fixed", 0)
    elif platform == "depop":
        result["selling_fee"] = sale_price * fees.get("selling_fee", 0)
        result["payment_processing"] = sale_price * fees.get("payment_processing", 0)
        result["payment_fixed"] = fees.get("payment_fixed", 0)
    
    result["total_fees"] = sum([
        result["selling_fee"],
        result["payment_processing"],
        result["payment_fixed"],
        result["international_fee"]
    ])
    
    return result

def check_token_expiry(token_expiry: Optional[datetime]) -> bool:
    """Check if token is expired or about to expire"""
    if token_expiry and token_expiry < datetime.utcnow():
        return True
    return False

# Main page content
st.title("🍑 SoleOps Platform Sales Sync")
st.markdown("Connect your selling platforms and sync sales automatically.")

# Display platform connections
st.subheader("Platform Connections")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### eBay")
    st.info("Connect your eBay seller account to sync sales.")
    if st.button("Connect eBay", key="connect_ebay"):
        st.warning("eBay connection coming soon!")

with col2:
    st.markdown("### Mercari")
    st.info("Connect your Mercari account to sync sales.")
    if st.button("Connect Mercari", key="connect_mercari"):
        st.warning("Mercari connection coming soon!")

with col3:
    st.markdown("### Depop")
    st.info("Connect your Depop account to sync sales.")
    if st.button("Connect Depop", key="connect_depop"):
        st.warning("Depop connection coming soon!")

st.markdown("---")

# Sync history
st.subheader("Sync History")
st.info("No sync history yet. Connect a platform to get started!")