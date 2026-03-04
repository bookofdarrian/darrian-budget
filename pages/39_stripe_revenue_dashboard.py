import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import os
import requests
from typing import Dict, List, Optional, Tuple
import numpy as np

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
            CREATE TABLE IF NOT EXISTS stripe_metrics (
                id SERIAL PRIMARY KEY,
                snapshot_date DATE NOT NULL,
                metric_type VARCHAR(50) NOT NULL,
                metric_value DECIMAL(15, 2) NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date, metric_type)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_subscriptions_cache (
                id SERIAL PRIMARY KEY,
                stripe_subscription_id VARCHAR(100) UNIQUE NOT NULL,
                customer_id VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                plan_amount DECIMAL(15, 2) NOT NULL,
                plan_interval VARCHAR(20) NOT NULL,
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                canceled_at TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers_cache (
                id SERIAL PRIMARY KEY,
                stripe_customer_id VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255),
                name VARCHAR(255),
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices_cache (
                id SERIAL PRIMARY KEY,
                stripe_invoice_id VARCHAR(100) UNIQUE NOT NULL,
                customer_id VARCHAR(100) NOT NULL,
                subscription_id VARCHAR(100),
                amount_paid DECIMAL(15, 2) NOT NULL,
                currency VARCHAR(10),
                status VARCHAR(50),
                paid_at TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_cohort_data (
                id SERIAL PRIMARY KEY,
                cohort_month DATE NOT NULL,
                period_month DATE NOT NULL,
                customers_count INTEGER NOT NULL,
                retention_rate DECIMAL(5, 2),
                revenue DECIMAL(15, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cohort_month, period_month)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL,
                metric_type VARCHAR(50) NOT NULL,
                metric_value DECIMAL(15, 2) NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(snapshot_date, metric_type)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_subscriptions_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_subscription_id VARCHAR(100) UNIQUE NOT NULL,
                customer_id VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                plan_amount DECIMAL(15, 2) NOT NULL,
                plan_interval VARCHAR(20) NOT NULL,
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                canceled_at TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_customer_id VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255),
                name VARCHAR(255),
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_invoice_id VARCHAR(100) UNIQUE NOT NULL,
                customer_id VARCHAR(100) NOT NULL,
                subscription_id VARCHAR(100),
                amount_paid DECIMAL(15, 2) NOT NULL,
                currency VARCHAR(10),
                status VARCHAR(50),
                paid_at TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_cohort_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_month DATE NOT NULL,
                period_month DATE NOT NULL,
                customers_count INTEGER NOT NULL,
                retention_rate DECIMAL(5, 2),
                revenue DECIMAL(15, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cohort_month, period_month)
            )
        """)
    conn.commit()

_ensure_tables()

# Render sidebar
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🍑 Stripe Revenue Dashboard")

# Main dashboard content
st.markdown("### Revenue Overview")

# Create sample data for demonstration
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("MRR", "$0", "0%")

with col2:
    st.metric("Active Subscriptions", "0", "0")

with col3:
    st.metric("Churn Rate", "0%", "0%")

with col4:
    st.metric("LTV", "$0", "0%")

# Sample chart
st.markdown("### Revenue Trend")

# Create empty figure with proper layout
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=[datetime.now() - timedelta(days=i) for i in range(30, 0, -1)],
    y=[0] * 30,
    mode='lines',
    name='MRR'
))
fig.update_layout(
    title="Monthly Recurring Revenue",
    xaxis_title="Date",
    yaxis_title="Revenue ($)",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

st.info("Connect your Stripe API key in settings to view real revenue data.")