import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import requests
import time
import base64

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Platform Sales Sync", page_icon="🍑", layout="wide")
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


def _ph(count: int = 1) -> str:
    """Return placeholder(s) for SQL queries based on database type."""
    if USE_POSTGRES:
        return ", ".join(["%s"] * count)
    return ", ".join(["?"] * count)


def _ensure_tables():
    """Create required tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Platform connections table for storing API credentials
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_platform_connections (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                credentials_encrypted TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                last_sync_at TIMESTAMP,
                sync_status VARCHAR(50) DEFAULT 'never_synced',
                sync_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform)
            )
        """)
        
        # Synced sales table for unified order records
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_synced_sales (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                platform_order_id VARCHAR(255) NOT NULL,
                item_title TEXT,
                item_sku VARCHAR(255),
                sale_price DECIMAL(10,2) NOT NULL,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                platform_fee DECIMAL(10,2) DEFAULT 0,
                payment_processing_fee DECIMAL(10,2) DEFAULT 0,
                other_fees DECIMAL(10,2) DEFAULT 0,
                total_fees DECIMAL(10,2) DEFAULT 0,
                net_revenue DECIMAL(10,2) DEFAULT 0,
                cost_of_goods DECIMAL(10,2) DEFAULT 0,
                net_profit DECIMAL(10,2) DEFAULT 0,
                buyer_username VARCHAR(255),
                buyer_location VARCHAR(255),
                sale_date TIMESTAMP,
                sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, platform_order_id)
            )
        """)
        
        # Sync logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sync_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                sync_type VARCHAR(50) DEFAULT 'manual',
                status VARCHAR(50) NOT NULL,
                orders_synced INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_details TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds INTEGER
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_platform_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                credentials_encrypted TEXT,
                is_active INTEGER DEFAULT 1,
                last_sync_at TIMESTAMP,
                sync_status VARCHAR(50) DEFAULT 'never_synced',
                sync_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_synced_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                platform_order_id VARCHAR(255) NOT NULL,
                item_title TEXT,
                item_sku VARCHAR(255),
                sale_price DECIMAL(10,2) NOT NULL,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                platform_fee DECIMAL(10,2) DEFAULT 0,
                payment_processing_fee DECIMAL(10,2) DEFAULT 0,
                other_fees DECIMAL(10,2) DEFAULT 0,
                total_fees DECIMAL(10,2) DEFAULT 0,
                net_revenue DECIMAL(10,2) DEFAULT 0,
                cost_of_goods DECIMAL(10,2) DEFAULT 0,
                net_profit DECIMAL(10,2) DEFAULT 0,
                buyer_username VARCHAR(255),
                buyer_location VARCHAR(255),
                sale_date TIMESTAMP,
                sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, platform_order_id)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                sync_type VARCHAR(50) DEFAULT 'manual',
                status VARCHAR(50) NOT NULL,
                orders_synced INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_details TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds INTEGER
            )
        """)
    
    conn.commit()


def get_context(data: str) -> str:
    """Generate context string."""
    context = f"""
Platform Sales Sync Data:
{data}
"""
    return context


# Initialize tables
_ensure_tables()

# Main page content
st.title("🍑 SoleOps Platform Sales Sync")
st.markdown("Connect and sync your sales data from various platforms.")

# Display sync status
st.subheader("Platform Connections")
st.info("Configure your platform API credentials to start syncing sales data.")