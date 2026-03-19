import streamlit as st
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Customer CRM", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ph(count: int = 1) -> str:
    """Return correct placeholder(s) for SQL queries."""
    placeholder = "%s" if USE_POSTGRES else "?"
    return ", ".join([placeholder] * count)

def _ensure_tables():
    """Create all required tables for Customer CRM."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                buyer_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                name TEXT,
                email TEXT,
                notes TEXT,
                vip_status BOOLEAN DEFAULT FALSE,
                banned BOOLEAN DEFAULT FALSE,
                ban_reason TEXT,
                total_orders INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                first_order_date DATE,
                last_order_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, buyer_id, platform)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_feedback (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                feedback_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_communications (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES soleops_customers(id) ON DELETE CASCADE,
                direction TEXT CHECK (direction IN ('inbound', 'outbound')),
                channel TEXT,
                subject TEXT,
                message TEXT,
                comm_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_orders (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                item_name TEXT,
                sale_price REAL,
                order_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                buyer_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                name TEXT,
                email TEXT,
                notes TEXT,
                vip_status INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                total_orders INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                first_order_date TEXT,
                last_order_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, buyer_id, platform)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                feedback_date TEXT DEFAULT CURRENT_DATE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER REFERENCES soleops_customers(id) ON DELETE CASCADE,
                direction TEXT CHECK (direction IN ('inbound', 'outbound')),
                channel TEXT,
                subject TEXT,
                message TEXT,
                comm_date TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                item_name TEXT,
                sale_price REAL,
                order_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

# Sidebar
with st.sidebar:
    render_sidebar_brand()
    render_sidebar_user_widget()

st.title("🍑 SoleOps Customer CRM")
st.markdown("Manage your customer relationships, track feedback, and communications.")