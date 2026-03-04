import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import time

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Uptime Kuma Status Page", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_monitors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                url VARCHAR(512),
                monitor_type VARCHAR(50) DEFAULT 'http',
                uptime_kuma_id INTEGER,
                check_interval INTEGER DEFAULT 60,
                expected_status INTEGER DEFAULT 200,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_heartbeats (
                id SERIAL PRIMARY KEY,
                monitor_id INTEGER REFERENCES uptime_monitors(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL,
                response_time INTEGER,
                status_code INTEGER,
                message TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_incidents (
                id SERIAL PRIMARY KEY,
                monitor_id INTEGER REFERENCES uptime_monitors(id) ON DELETE CASCADE,
                incident_type VARCHAR(50) NOT NULL,
                started_at TIMESTAMP NOT NULL,
                resolved_at TIMESTAMP,
                duration_seconds INTEGER,
                alert_sent BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_alert_config (
                id SERIAL PRIMARY KEY,
                alert_type VARCHAR(50) NOT NULL,
                is_enabled BOOLEAN DEFAULT FALSE,
                config_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_monitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT,
                monitor_type TEXT DEFAULT 'http',
                uptime_kuma_id INTEGER,
                check_interval INTEGER DEFAULT 60,
                expected_status INTEGER DEFAULT 200,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_id INTEGER,
                status TEXT NOT NULL,
                response_time INTEGER,
                status_code INTEGER,
                message TEXT,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (monitor_id) REFERENCES uptime_monitors(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_id INTEGER,
                incident_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                resolved_at TEXT,
                duration_seconds INTEGER,
                alert_sent INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (monitor_id) REFERENCES uptime_monitors(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS uptime_alert_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                is_enabled INTEGER DEFAULT 0,
                config_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Sidebar Navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
render_sidebar_user_widget()

# Main Page Content
st.title("🍑 Uptime Kuma Status Page")
st.markdown("Monitor the status of your services and infrastructure.")

# Display monitors
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT id, name, url, monitor_type, is_active FROM uptime_monitors ORDER BY name")
monitors = cur.fetchall()
conn.close()

if monitors:
    for monitor in monitors:
        monitor_id, name, url, monitor_type, is_active = monitor
        status_icon = "🟢" if is_active else "🔴"
        st.markdown(f"{status_icon} **{name}** - {url or 'N/A'} ({monitor_type})")
else:
    st.info("No monitors configured yet. Add monitors to start tracking uptime.")

# Add new monitor section
st.markdown("---")
st.subheader("Add New Monitor")

with st.form("add_monitor_form"):
    col1, col2 = st.columns(2)
    with col1:
        monitor_name = st.text_input("Monitor Name")
        monitor_url = st.text_input("URL")
    with col2:
        monitor_type = st.selectbox("Type", ["http", "https", "ping", "tcp"])
        check_interval = st.number_input("Check Interval (seconds)", min_value=30, value=60)
    
    submitted = st.form_submit_button("Add Monitor")
    if submitted and monitor_name:
        conn = get_conn()
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO uptime_monitors (name, url, monitor_type, check_interval) VALUES (%s, %s, %s, %s)",
                (monitor_name, monitor_url, monitor_type, check_interval)
            )
        else:
            cur.execute(
                "INSERT INTO uptime_monitors (name, url, monitor_type, check_interval) VALUES (?, ?, ?, ?)",
                (monitor_name, monitor_url, monitor_type, check_interval)
            )
        conn.commit()
        conn.close()
        st.success(f"Monitor '{monitor_name}' added successfully!")
        st.rerun()