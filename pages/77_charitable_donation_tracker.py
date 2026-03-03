import streamlit as st
import json
import os
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64

st.set_page_config(page_title="Charitable Donation Tracker", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS charitable_donations (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                organization_name VARCHAR(255) NOT NULL,
                ein VARCHAR(20),
                amount DECIMAL(12,2) NOT NULL,
                payment_method VARCHAR(50),
                donation_type VARCHAR(50),
                receipt_url TEXT,
                receipt_data BYTEA,
                tax_deductible BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS donor_advised_funds (
                id SERIAL PRIMARY KEY,
                fund_name VARCHAR(255) NOT NULL,
                custodian VARCHAR(255),
                balance DECIMAL(12,2) DEFAULT 0,
                contributions_ytd DECIMAL(12,2) DEFAULT 0,
                grants_ytd DECIMAL(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS giving_goals (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                target_amount DECIMAL(12,2) NOT NULL,
                category VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daf_transactions (
                id SERIAL PRIMARY KEY,
                fund_id INTEGER REFERENCES donor_advised_funds(id),
                transaction_date DATE NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                recipient VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS charitable_donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                organization_name VARCHAR(255) NOT NULL,
                ein VARCHAR(20),
                amount DECIMAL(12,2) NOT NULL,
                payment_method VARCHAR(50),
                donation_type VARCHAR(50),
                receipt_url TEXT,
                receipt_data BLOB,
                tax_deductible BOOLEAN DEFAULT 1,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS donor_advised_funds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_name VARCHAR(255) NOT NULL,
                custodian VARCHAR(255),
                balance DECIMAL(12,2) DEFAULT 0,
                contributions_ytd DECIMAL(12,2) DEFAULT 0,
                grants_ytd DECIMAL(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS giving_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                target_amount DECIMAL(12,2) NOT NULL,
                category VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daf_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_id INTEGER REFERENCES donor_advised_funds(id),
                transaction_date DATE NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                recipient VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.markdown("---")
render_sidebar_user_widget()

st.title("🍑 Charitable Donation Tracker")

st.info("""
Track your charitable donations, manage donor-advised funds, and monitor your giving goals.
""")