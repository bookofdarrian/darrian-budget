import streamlit as st
import requests
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Stripe Revenue Dashboard", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS stripe_customers (
                id SERIAL PRIMARY KEY,
                stripe_customer_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255),
                name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB,
                first_payment_date DATE,
                cohort_month VARCHAR(7),
                is_active BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_subscriptions (
                id SERIAL PRIMARY KEY,
                stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
                stripe_customer_id VARCHAR(255) NOT NULL,
                status VARCHAR(50),
                plan_id VARCHAR(255),
                plan_name VARCHAR(255),
                plan_amount INTEGER,
                plan_interval VARCHAR(20),
                plan_currency VARCHAR(10) DEFAULT 'usd',
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                cancel_at_period_end BOOLEAN DEFAULT FALSE,
                canceled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trial_start TIMESTAMP,
                trial_end TIMESTAMP,
                metadata JSONB
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices (
                id SERIAL PRIMARY KEY,
                stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
                stripe_customer_id VARCHAR(255) NOT NULL,
                stripe_subscription_id VARCHAR(255),
                status VARCHAR(50),
                amount_paid INTEGER,
                amount_due INTEGER,
                currency VARCHAR(10) DEFAULT 'usd',
                invoice_date TIMESTAMP,
                paid_at TIMESTAMP,
                period_start TIMESTAMP,
                period_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                id SERIAL PRIMARY KEY,
                stripe_event_id VARCHAR(255) UNIQUE NOT NULL,
                event_type VARCHAR(100),
                data JSONB,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_metrics_cache (
                id SERIAL PRIMARY KEY,
                metric_date DATE NOT NULL,
                metric_type VARCHAR(50) NOT NULL,
                metric_value DECIMAL(15, 2),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(metric_date, metric_type)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_customer_id TEXT UNIQUE NOT NULL,
                email TEXT,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                first_payment_date DATE,
                cohort_month TEXT,
                is_active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_subscription_id TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT NOT NULL,
                status TEXT,
                plan_id TEXT,
                plan_name TEXT,
                plan_amount INTEGER,
                plan_interval TEXT,
                plan_currency TEXT DEFAULT 'usd',
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                cancel_at_period_end INTEGER DEFAULT 0,
                canceled_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trial_start TIMESTAMP,
                trial_end TIMESTAMP,
                metadata TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_invoice_id TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT NOT NULL,
                stripe_subscription_id TEXT,
                status TEXT,
                amount_paid INTEGER,
                amount_due INTEGER,
                currency TEXT DEFAULT 'usd',
                invoice_date TIMESTAMP,
                paid_at TIMESTAMP,
                period_start TIMESTAMP,
                period_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_event_id TEXT UNIQUE NOT NULL,
                event_type TEXT,
                data TEXT,
                processed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_metrics_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_date DATE NOT NULL,
                metric_type TEXT NOT NULL,
                metric_value REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(metric_date, metric_type)
            )
        """)
    
    conn.commit()

_ensure_tables()

# Sidebar
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🍑 Stripe Revenue Dashboard")

# Get Stripe API key from settings
stripe_api_key = get_setting("stripe_api_key")

if not stripe_api_key:
    st.warning("Please configure your Stripe API key in Settings.")
    
    with st.form("stripe_api_key_form"):
        api_key = st.text_input("Stripe Secret Key", type="password")
        submitted = st.form_submit_button("Save API Key")
        
        if submitted and api_key:
            set_setting("stripe_api_key", api_key)
            st.success("API key saved!")
            st.rerun()
else:
    st.success("Stripe API key configured")
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Revenue", "$0.00", "0%")
    
    with col2:
        st.metric("Active Subscriptions", "0", "0")
    
    with col3:
        st.metric("MRR", "$0.00", "0%")
    
    with col4:
        st.metric("Churn Rate", "0%", "0%")
    
    st.subheader("Revenue Over Time")
    
    # Placeholder chart
    df = pd.DataFrame({
        'date': pd.date_range(start='2024-01-01', periods=12, freq='M'),
        'revenue': [0] * 12
    })
    
    fig = px.line(df, x='date', y='revenue', title='Monthly Revenue')
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Recent Invoices")
    st.info("No invoices found. Sync data from Stripe to see invoices.")
    
    if st.button("Sync Data from Stripe"):
        st.info("Sync functionality coming soon...")