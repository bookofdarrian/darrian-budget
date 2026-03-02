import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import time

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Stripe Revenue Dashboard", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

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
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_metrics (
                id SERIAL PRIMARY KEY,
                snapshot_date DATE NOT NULL UNIQUE,
                mrr DECIMAL(12, 2) DEFAULT 0,
                arr DECIMAL(14, 2) DEFAULT 0,
                active_subscriptions INTEGER DEFAULT 0,
                total_customers INTEGER DEFAULT 0,
                churned_customers INTEGER DEFAULT 0,
                churn_rate DECIMAL(5, 4) DEFAULT 0,
                arpu DECIMAL(10, 2) DEFAULT 0,
                ltv DECIMAL(12, 2) DEFAULT 0,
                new_mrr DECIMAL(12, 2) DEFAULT 0,
                expansion_mrr DECIMAL(12, 2) DEFAULT 0,
                contraction_mrr DECIMAL(12, 2) DEFAULT 0,
                churned_mrr DECIMAL(12, 2) DEFAULT 0,
                raw_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_cohorts (
                id SERIAL PRIMARY KEY,
                cohort_month DATE NOT NULL,
                period_month DATE NOT NULL,
                starting_customers INTEGER DEFAULT 0,
                retained_customers INTEGER DEFAULT 0,
                retention_rate DECIMAL(5, 4) DEFAULT 0,
                cohort_mrr DECIMAL(12, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cohort_month, period_month)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers_cache (
                id SERIAL PRIMARY KEY,
                stripe_customer_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255),
                name VARCHAR(255),
                created_date DATE,
                subscription_status VARCHAR(50),
                current_mrr DECIMAL(10, 2) DEFAULT 0,
                lifetime_value DECIMAL(12, 2) DEFAULT 0,
                subscription_start DATE,
                subscription_end DATE,
                plan_name VARCHAR(255),
                plan_interval VARCHAR(50),
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices_cache (
                id SERIAL PRIMARY KEY,
                stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
                stripe_customer_id VARCHAR(255),
                amount_paid DECIMAL(10, 2) DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'usd',
                status VARCHAR(50),
                invoice_date DATE,
                period_start DATE,
                period_end DATE,
                subscription_id VARCHAR(255),
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL UNIQUE,
                mrr REAL DEFAULT 0,
                arr REAL DEFAULT 0,
                active_subscriptions INTEGER DEFAULT 0,
                total_customers INTEGER DEFAULT 0,
                churned_customers INTEGER DEFAULT 0,
                churn_rate REAL DEFAULT 0,
                arpu REAL DEFAULT 0,
                ltv REAL DEFAULT 0,
                new_mrr REAL DEFAULT 0,
                expansion_mrr REAL DEFAULT 0,
                contraction_mrr REAL DEFAULT 0,
                churned_mrr REAL DEFAULT 0,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_cohorts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_month DATE NOT NULL,
                period_month DATE NOT NULL,
                starting_customers INTEGER DEFAULT 0,
                retained_customers INTEGER DEFAULT 0,
                retention_rate REAL DEFAULT 0,
                cohort_mrr REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cohort_month, period_month)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_customer_id TEXT UNIQUE NOT NULL,
                email TEXT,
                name TEXT,
                created_date DATE,
                subscription_status TEXT,
                current_mrr REAL DEFAULT 0,
                lifetime_value REAL DEFAULT 0,
                subscription_start DATE,
                subscription_end DATE,
                plan_name TEXT,
                plan_interval TEXT,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_invoice_id TEXT UNIQUE NOT NULL,
                stripe_customer_id TEXT,
                amount_paid REAL DEFAULT 0,
                currency TEXT DEFAULT 'usd',
                status TEXT,
                invoice_date DATE,
                period_start DATE,
                period_end DATE,
                subscription_id TEXT,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


_ensure_tables()

st.title("💳 Stripe Revenue Dashboard")

# Main dashboard content
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 MRR Trends", "👥 Cohort Analysis", "⚙️ Settings"])

with tab1:
    st.subheader("Revenue Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="MRR", value="$0.00", delta="0%")
    
    with col2:
        st.metric(label="ARR", value="$0.00", delta="0%")
    
    with col3:
        st.metric(label="Active Subscriptions", value="0", delta="0")
    
    with col4:
        st.metric(label="LTV:CAC", value="0.0x", delta="0%")
    
    st.info("Connect your Stripe account in Settings to see live data.")

with tab2:
    st.subheader("MRR Trends")
    
    # Placeholder chart
    dates = pd.date_range(start=datetime.now() - timedelta(days=180), end=datetime.now(), freq='M')
    sample_data = pd.DataFrame({
        'date': dates,
        'mrr': np.random.randint(1000, 5000, len(dates))
    })
    
    fig = px.line(sample_data, x='date', y='mrr', title='Monthly Recurring Revenue')
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Cohort Retention Analysis")
    st.info("Cohort data will appear here once Stripe is connected and data is synced.")

with tab4:
    st.subheader("Stripe Settings")
    
    stripe_api_key = st.text_input("Stripe API Key (Secret)", type="password", 
                                    value=get_setting("stripe_api_key") or "")
    
    if st.button("Save Settings"):
        if stripe_api_key:
            set_setting("stripe_api_key", stripe_api_key)
            st.success("Settings saved!")
        else:
            st.warning("Please enter a valid API key.")
    
    if st.button("Sync Stripe Data"):
        st.info("Syncing... (This feature requires a valid Stripe API key)")