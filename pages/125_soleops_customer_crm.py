import streamlit as st
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Customer CRM", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                buyer_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                email TEXT,
                vip_status BOOLEAN DEFAULT FALSE,
                banned BOOLEAN DEFAULT FALSE,
                ban_reason TEXT,
                notes TEXT,
                first_purchase TIMESTAMP,
                total_orders INTEGER DEFAULT 0,
                total_revenue DECIMAL(10,2) DEFAULT 0,
                avg_order_value DECIMAL(10,2) DEFAULT 0,
                last_order_date TIMESTAMP,
                linked_customer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, buyer_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_feedback (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                platform TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_communications (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES soleops_customers(id) ON DELETE CASCADE,
                direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
                message TEXT NOT NULL,
                channel TEXT NOT NULL,
                subject TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_orders (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                item_title TEXT,
                sale_price DECIMAL(10,2),
                order_date TIMESTAMP,
                status TEXT DEFAULT 'completed',
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
                username TEXT NOT NULL,
                email TEXT,
                vip_status INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                notes TEXT,
                first_purchase TEXT,
                total_orders INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0,
                avg_order_value REAL DEFAULT 0,
                last_order_date TEXT,
                linked_customer_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, buyer_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                feedback_text TEXT,
                feedback_date TEXT DEFAULT CURRENT_TIMESTAMP,
                platform TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES soleops_customers(id) ON DELETE CASCADE,
                direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
                message TEXT NOT NULL,
                channel TEXT NOT NULL,
                subject TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_customer_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES soleops_customers(id) ON DELETE CASCADE,
                order_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                item_title TEXT,
                sale_price REAL,
                order_date TEXT,
                status TEXT DEFAULT 'completed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

def get_ai_customer_insights(customer_data: Dict[str, Any]) -> str:
    """Generate AI insights for a customer."""
    prompt = f"""Analyze this resale customer and provide brief, actionable insights:

Customer: {customer_data.get('username', 'Unknown')}
Platform: {customer_data.get('platform', 'Unknown')}
Total Orders: {customer_data.get('total_orders', 0)}
Total Revenue: ${customer_data.get('total_revenue', 0):.2f}
Average Order Value: ${customer_data.get('avg_order_value', 0):.2f}
VIP Status: {'Yes' if customer_data.get('vip_status') else 'No'}

Provide 2-3 brief insights about this customer and suggestions for engagement."""
    
    return prompt

# Main page content
st.title("🍑 SoleOps Customer CRM")
st.markdown("Manage your resale customer relationships")

# Display customer list or management interface
tab1, tab2, tab3 = st.tabs(["Customers", "Add Customer", "Analytics"])

with tab1:
    st.subheader("Customer List")
    conn = get_conn()
    cur = conn.cursor()
    user_id = st.session_state.get("user_id", 1)
    ph = get_placeholder()
    
    cur.execute(f"SELECT * FROM soleops_customers WHERE user_id = {ph} ORDER BY updated_at DESC", (user_id,))
    customers = cur.fetchall()
    
    if customers:
        for customer in customers:
            with st.expander(f"{customer[4]} ({customer[3]})"):
                st.write(f"**Buyer ID:** {customer[2]}")
                st.write(f"**Email:** {customer[5] or 'N/A'}")
                st.write(f"**Total Orders:** {customer[11]}")
                st.write(f"**Total Revenue:** ${customer[12]:.2f}" if customer[12] else "**Total Revenue:** $0.00")
                st.write(f"**VIP:** {'Yes' if customer[6] else 'No'}")
                st.write(f"**Banned:** {'Yes' if customer[7] else 'No'}")
    else:
        st.info("No customers found. Add your first customer!")

with tab2:
    st.subheader("Add New Customer")
    with st.form("add_customer"):
        platform = st.selectbox("Platform", ["eBay", "Mercari", "Poshmark", "Depop", "Other"])
        buyer_id = st.text_input("Buyer ID")
        username = st.text_input("Username")
        email = st.text_input("Email (optional)")
        notes = st.text_area("Notes (optional)")
        
        if st.form_submit_button("Add Customer"):
            if buyer_id and username:
                conn = get_conn()
                cur = conn.cursor()
                user_id = st.session_state.get("user_id", 1)
                ph = get_placeholder()
                
                try:
                    cur.execute(f"""
                        INSERT INTO soleops_customers (user_id, buyer_id, platform, username, email, notes)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """, (user_id, buyer_id, platform, username, email or None, notes or None))
                    conn.commit()
                    st.success("Customer added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding customer: {e}")
            else:
                st.warning("Please fill in Buyer ID and Username")

with tab3:
    st.subheader("Customer Analytics")
    conn = get_conn()
    cur = conn.cursor()
    user_id = st.session_state.get("user_id", 1)
    ph = get_placeholder()
    
    cur.execute(f"SELECT COUNT(*), SUM(total_revenue), AVG(avg_order_value) FROM soleops_customers WHERE user_id = {ph}", (user_id,))
    stats = cur.fetchone()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Customers", stats[0] or 0)
    with col2:
        st.metric("Total Revenue", f"${stats[1] or 0:.2f}")
    with col3:
        st.metric("Avg Order Value", f"${stats[2] or 0:.2f}")