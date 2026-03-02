import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Stripe Revenue Dashboard", page_icon="🍑", layout="wide")
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


def _ensure_tables():
    """Create all required tables for Stripe metrics tracking."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_metrics (
                id SERIAL PRIMARY KEY,
                snapshot_date DATE NOT NULL UNIQUE,
                mrr DECIMAL(12, 2) NOT NULL DEFAULT 0,
                arr DECIMAL(12, 2) NOT NULL DEFAULT 0,
                active_subscriptions INTEGER NOT NULL DEFAULT 0,
                total_customers INTEGER NOT NULL DEFAULT 0,
                churned_customers INTEGER NOT NULL DEFAULT 0,
                new_customers INTEGER NOT NULL DEFAULT 0,
                arpu DECIMAL(10, 2) NOT NULL DEFAULT 0,
                ltv DECIMAL(12, 2) NOT NULL DEFAULT 0,
                churn_rate DECIMAL(5, 4) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_subscriptions (
                id SERIAL PRIMARY KEY,
                stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
                stripe_customer_id VARCHAR(255) NOT NULL,
                customer_email VARCHAR(255),
                plan_name VARCHAR(255),
                plan_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
                plan_interval VARCHAR(50),
                status VARCHAR(50) NOT NULL,
                start_date DATE NOT NULL,
                cancel_date DATE,
                current_period_start DATE,
                current_period_end DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices (
                id SERIAL PRIMARY KEY,
                stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
                stripe_customer_id VARCHAR(255) NOT NULL,
                stripe_subscription_id VARCHAR(255),
                amount_paid DECIMAL(10, 2) NOT NULL DEFAULT 0,
                amount_due DECIMAL(10, 2) NOT NULL DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'usd',
                status VARCHAR(50) NOT NULL,
                invoice_date DATE NOT NULL,
                paid_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers (
                id SERIAL PRIMARY KEY,
                stripe_customer_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255),
                name VARCHAR(255),
                created_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                total_spent DECIMAL(12, 2) NOT NULL DEFAULT 0,
                subscription_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_cohort_data (
                id SERIAL PRIMARY KEY,
                cohort_month DATE NOT NULL,
                months_since_start INTEGER NOT NULL,
                retained_customers INTEGER NOT NULL DEFAULT 0,
                total_cohort_customers INTEGER NOT NULL DEFAULT 0,
                retention_rate DECIMAL(5, 4) NOT NULL DEFAULT 0,
                revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cohort_month, months_since_start)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date DATE NOT NULL UNIQUE,
                mrr DECIMAL(12, 2) NOT NULL DEFAULT 0,
                arr DECIMAL(12, 2) NOT NULL DEFAULT 0,
                active_subscriptions INTEGER NOT NULL DEFAULT 0,
                total_customers INTEGER NOT NULL DEFAULT 0,
                churned_customers INTEGER NOT NULL DEFAULT 0,
                new_customers INTEGER NOT NULL DEFAULT 0,
                arpu DECIMAL(10, 2) NOT NULL DEFAULT 0,
                ltv DECIMAL(12, 2) NOT NULL DEFAULT 0,
                churn_rate DECIMAL(5, 4) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
                stripe_customer_id VARCHAR(255) NOT NULL,
                customer_email VARCHAR(255),
                plan_name VARCHAR(255),
                plan_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
                plan_interval VARCHAR(50),
                status VARCHAR(50) NOT NULL,
                start_date DATE NOT NULL,
                cancel_date DATE,
                current_period_start DATE,
                current_period_end DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
                stripe_customer_id VARCHAR(255) NOT NULL,
                stripe_subscription_id VARCHAR(255),
                amount_paid DECIMAL(10, 2) NOT NULL DEFAULT 0,
                amount_due DECIMAL(10, 2) NOT NULL DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'usd',
                status VARCHAR(50) NOT NULL,
                invoice_date DATE NOT NULL,
                paid_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_customer_id VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255),
                name VARCHAR(255),
                created_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                total_spent DECIMAL(12, 2) NOT NULL DEFAULT 0,
                subscription_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stripe_cohort_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_month DATE NOT NULL,
                months_since_start INTEGER NOT NULL,
                retained_customers INTEGER NOT NULL DEFAULT 0,
                total_cohort_customers INTEGER NOT NULL DEFAULT 0,
                retention_rate DECIMAL(5, 4) NOT NULL DEFAULT 0,
                revenue DECIMAL(12, 2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cohort_month, months_since_start)
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()


def get_metrics():
    """Retrieve the latest metrics from the database."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT snapshot_date, mrr, arr, active_subscriptions, total_customers,
               churned_customers, new_customers, arpu, ltv, churn_rate
        FROM stripe_metrics
        ORDER BY snapshot_date DESC
        LIMIT 30
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if rows:
        df = pd.DataFrame(rows, columns=[
            'snapshot_date', 'mrr', 'arr', 'active_subscriptions', 'total_customers',
            'churned_customers', 'new_customers', 'arpu', 'ltv', 'churn_rate'
        ])
        return df
    return pd.DataFrame()


def get_subscriptions():
    """Retrieve all subscriptions from the database."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT stripe_subscription_id, stripe_customer_id, customer_email,
               plan_name, plan_amount, plan_interval, status, start_date,
               cancel_date, current_period_start, current_period_end
        FROM stripe_subscriptions
        ORDER BY start_date DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if rows:
        df = pd.DataFrame(rows, columns=[
            'subscription_id', 'customer_id', 'email', 'plan_name', 'amount',
            'interval', 'status', 'start_date', 'cancel_date',
            'period_start', 'period_end'
        ])
        return df
    return pd.DataFrame()


def get_customers():
    """Retrieve all customers from the database."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT stripe_customer_id, email, name, created_date, is_active,
               total_spent, subscription_count
        FROM stripe_customers
        ORDER BY created_date DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if rows:
        df = pd.DataFrame(rows, columns=[
            'customer_id', 'email', 'name', 'created_date', 'is_active',
            'total_spent', 'subscription_count'
        ])
        return df
    return pd.DataFrame()


# Initialize tables
_ensure_tables()

# Main page content
st.title("💳 Stripe Revenue Dashboard")
st.markdown("Track your subscription metrics, MRR, churn, and customer analytics.")

# Metrics overview
metrics_df = get_metrics()

if not metrics_df.empty:
    latest = metrics_df.iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("MRR", f"${float(latest['mrr']):,.2f}")
    with col2:
        st.metric("ARR", f"${float(latest['arr']):,.2f}")
    with col3:
        st.metric("Active Subscriptions", int(latest['active_subscriptions']))
    with col4:
        st.metric("Total Customers", int(latest['total_customers']))
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("New Customers", int(latest['new_customers']))
    with col6:
        st.metric("Churned", int(latest['churned_customers']))
    with col7:
        st.metric("ARPU", f"${float(latest['arpu']):,.2f}")
    with col8:
        churn_pct = float(latest['churn_rate']) * 100
        st.metric("Churn Rate", f"{churn_pct:.2f}%")
    
    # MRR Chart
    st.subheader("📈 MRR Trend")
    if len(metrics_df) > 1:
        fig = px.line(
            metrics_df.sort_values('snapshot_date'),
            x='snapshot_date',
            y='mrr',
            title='Monthly Recurring Revenue'
        )
        fig.update_layout(xaxis_title="Date", yaxis_title="MRR ($)")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No metrics data available yet. Connect your Stripe account to start tracking.")

# Subscriptions section
st.subheader("📋 Subscriptions")
subs_df = get_subscriptions()

if not subs_df.empty:
    st.dataframe(subs_df, use_container_width=True)
else:
    st.info("No subscription data available.")

# Customers section
st.subheader("👥 Customers")
customers_df = get_customers()

if not customers_df.empty:
    st.dataframe(customers_df, use_container_width=True)
else:
    st.info("No customer data available.")

# Data management section
st.subheader("⚙️ Data Management")

with st.expander("Add Sample Data (for testing)"):
    if st.button("Generate Sample Metrics"):
        conn = get_conn()
        cur = conn.cursor()
        
        today = datetime.now().date()
        for i in range(30):
            snapshot_date = today - timedelta(days=i)
            mrr = 5000 + (30 - i) * 100 + np.random.randint(-200, 200)
            arr = mrr * 12
            active_subs = 50 + (30 - i) * 2 + np.random.randint(-5, 5)
            total_customers = active_subs + np.random.randint(10, 30)
            churned = np.random.randint(0, 5)
            new_customers = np.random.randint(1, 10)
            arpu = mrr / max(active_subs, 1)
            ltv = arpu * 12
            churn_rate = churned / max(total_customers, 1)
            
            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO stripe_metrics 
                    (snapshot_date, mrr, arr, active_subscriptions, total_customers,
                     churned_customers, new_customers, arpu, ltv, churn_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_date) DO UPDATE SET
                    mrr = EXCLUDED.mrr, arr = EXCLUDED.arr
                """, (snapshot_date, mrr, arr, active_subs, total_customers,
                      churned, new_customers, arpu, ltv, churn_rate))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO stripe_metrics 
                    (snapshot_date, mrr, arr, active_subscriptions, total_customers,
                     churned_customers, new_customers, arpu, ltv, churn_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (snapshot_date, mrr, arr, active_subs, total_customers,
                      churned, new_customers, arpu, ltv, churn_rate))
        
        conn.commit()
        cur.close()
        conn.close()
        st.success("Sample metrics generated!")
        st.rerun()