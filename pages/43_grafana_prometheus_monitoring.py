import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Grafana + Prometheus Monitoring", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_alerts (
                id SERIAL PRIMARY KEY,
                alert_name VARCHAR(255) NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) DEFAULT 'warning',
                threshold_value DECIMAL(10,2),
                current_value DECIMAL(10,2),
                service_name VARCHAR(255),
                container_name VARCHAR(255),
                message TEXT,
                status VARCHAR(20) DEFAULT 'firing',
                acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_by VARCHAR(255),
                acknowledged_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_targets (
                id SERIAL PRIMARY KEY,
                target_name VARCHAR(255) NOT NULL,
                target_url VARCHAR(500) NOT NULL,
                target_type VARCHAR(50) DEFAULT 'prometheus',
                scrape_interval INTEGER DEFAULT 15,
                is_active BOOLEAN DEFAULT TRUE,
                last_scrape TIMESTAMP,
                last_status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id SERIAL PRIMARY KEY,
                rule_name VARCHAR(255) NOT NULL,
                metric_name VARCHAR(255) NOT NULL,
                condition VARCHAR(20) NOT NULL,
                threshold DECIMAL(10,2) NOT NULL,
                duration_seconds INTEGER DEFAULT 60,
                severity VARCHAR(20) DEFAULT 'warning',
                is_active BOOLEAN DEFAULT TRUE,
                notification_channel VARCHAR(50) DEFAULT 'telegram',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT DEFAULT 'warning',
                threshold_value REAL,
                current_value REAL,
                service_name TEXT,
                container_name TEXT,
                message TEXT,
                status TEXT DEFAULT 'firing',
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_name TEXT NOT NULL,
                target_url TEXT NOT NULL,
                target_type TEXT DEFAULT 'prometheus',
                scrape_interval INTEGER DEFAULT 15,
                is_active INTEGER DEFAULT 1,
                last_scrape TEXT,
                last_status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                description TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                condition TEXT NOT NULL,
                threshold REAL NOT NULL,
                duration_seconds INTEGER DEFAULT 60,
                severity TEXT DEFAULT 'warning',
                is_active INTEGER DEFAULT 1,
                notification_channel TEXT DEFAULT 'telegram',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()

_ensure_tables()

# Sidebar
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🍑 Grafana + Prometheus Monitoring")

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🎯 Targets", "⚠️ Alerts", "⚙️ Settings"])

with tab1:
    st.header("Monitoring Dashboard")
    st.info("Connect to Prometheus and Grafana to view metrics.")

with tab2:
    st.header("Scrape Targets")
    st.markdown("**Add New Scrape Target**")
    
    with st.form("add_target_form"):
        target_name = st.text_input("Target Name")
        target_url = st.text_input("Target URL")
        target_type = st.selectbox("Target Type", ["prometheus", "node_exporter", "custom"])
        scrape_interval = st.number_input("Scrape Interval (seconds)", min_value=5, value=15)
        submitted = st.form_submit_button("Add Target")
        
        if submitted and target_name and target_url:
            conn = get_conn()
            cur = conn.cursor()
            if USE_POSTGRES:
                cur.execute(
                    "INSERT INTO monitoring_targets (target_name, target_url, target_type, scrape_interval) VALUES (%s, %s, %s, %s)",
                    (target_name, target_url, target_type, scrape_interval)
                )
            else:
                cur.execute(
                    "INSERT INTO monitoring_targets (target_name, target_url, target_type, scrape_interval) VALUES (?, ?, ?, ?)",
                    (target_name, target_url, target_type, scrape_interval)
                )
            conn.commit()
            st.success(f"Target '{target_name}' added successfully!")
            st.rerun()

with tab3:
    st.header("Alert Rules")
    st.markdown("**Configure Alert Rules**")
    
    with st.form("add_alert_rule_form"):
        rule_name = st.text_input("Rule Name")
        metric_name = st.text_input("Metric Name")
        condition = st.selectbox("Condition", [">", "<", ">=", "<=", "==", "!="])
        threshold = st.number_input("Threshold", value=0.0)
        severity = st.selectbox("Severity", ["info", "warning", "critical"])
        submitted = st.form_submit_button("Add Rule")
        
        if submitted and rule_name and metric_name:
            conn = get_conn()
            cur = conn.cursor()
            if USE_POSTGRES:
                cur.execute(
                    "INSERT INTO alert_rules (rule_name, metric_name, condition, threshold, severity) VALUES (%s, %s, %s, %s, %s)",
                    (rule_name, metric_name, condition, threshold, severity)
                )
            else:
                cur.execute(
                    "INSERT INTO alert_rules (rule_name, metric_name, condition, threshold, severity) VALUES (?, ?, ?, ?, ?)",
                    (rule_name, metric_name, condition, threshold, severity)
                )
            conn.commit()
            st.success(f"Alert rule '{rule_name}' added successfully!")
            st.rerun()

with tab4:
    st.header("Monitoring Settings")
    
    prometheus_url = st.text_input("Prometheus URL", value=get_setting("prometheus_url") or "http://localhost:9090")
    grafana_url = st.text_input("Grafana URL", value=get_setting("grafana_url") or "http://localhost:3000")
    
    if st.button("Save Settings"):
        set_setting("prometheus_url", prometheus_url)
        set_setting("grafana_url", grafana_url)
        st.success("Settings saved successfully!")