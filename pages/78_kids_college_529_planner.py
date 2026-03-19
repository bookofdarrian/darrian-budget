import streamlit as st
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Kids College 529 Planner", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS children (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                birth_date DATE NOT NULL,
                target_college_age INTEGER DEFAULT 18,
                preferred_state VARCHAR(2),
                preferred_school_type VARCHAR(50) DEFAULT 'public_in_state',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS college_529_accounts (
                id SERIAL PRIMARY KEY,
                child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,
                account_name VARCHAR(255) NOT NULL,
                plan_state VARCHAR(2) NOT NULL,
                account_number VARCHAR(100),
                current_balance DECIMAL(12,2) DEFAULT 0,
                expected_return_rate DECIMAL(5,4) DEFAULT 0.07,
                beneficiary_name VARCHAR(255),
                custodian_name VARCHAR(255),
                opened_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contributions_529 (
                id SERIAL PRIMARY KEY,
                account_id INTEGER REFERENCES college_529_accounts(id) ON DELETE CASCADE,
                amount DECIMAL(12,2) NOT NULL,
                contribution_date DATE NOT NULL,
                contribution_type VARCHAR(50) DEFAULT 'one_time',
                source VARCHAR(100),
                is_recurring BOOLEAN DEFAULT FALSE,
                recurring_frequency VARCHAR(20),
                recurring_day INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS college_cost_estimates (
                id SERIAL PRIMARY KEY,
                state VARCHAR(2) NOT NULL,
                school_type VARCHAR(50) NOT NULL,
                year INTEGER NOT NULL,
                tuition_fees DECIMAL(12,2) NOT NULL,
                room_board DECIMAL(12,2) NOT NULL,
                books_supplies DECIMAL(12,2) DEFAULT 1200,
                other_expenses DECIMAL(12,2) DEFAULT 2500,
                inflation_rate DECIMAL(5,4) DEFAULT 0.05,
                source VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(state, school_type, year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS college_milestones (
                id SERIAL PRIMARY KEY,
                child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,
                milestone_name VARCHAR(255) NOT NULL,
                target_amount DECIMAL(12,2) NOT NULL,
                target_date DATE,
                achieved BOOLEAN DEFAULT FALSE,
                achieved_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_date DATE NOT NULL,
                target_college_age INTEGER DEFAULT 18,
                preferred_state TEXT,
                preferred_school_type TEXT DEFAULT 'public_in_state',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS college_529_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,
                account_name TEXT NOT NULL,
                plan_state TEXT NOT NULL,
                account_number TEXT,
                current_balance REAL DEFAULT 0,
                expected_return_rate REAL DEFAULT 0.07,
                beneficiary_name TEXT,
                custodian_name TEXT,
                opened_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contributions_529 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER REFERENCES college_529_accounts(id) ON DELETE CASCADE,
                amount REAL NOT NULL,
                contribution_date DATE NOT NULL,
                contribution_type TEXT DEFAULT 'one_time',
                source TEXT,
                is_recurring INTEGER DEFAULT 0,
                recurring_frequency TEXT,
                recurring_day INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS college_cost_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL,
                school_type TEXT NOT NULL,
                year INTEGER NOT NULL,
                tuition_fees REAL NOT NULL,
                room_board REAL NOT NULL,
                books_supplies REAL DEFAULT 1200,
                other_expenses REAL DEFAULT 2500,
                inflation_rate REAL DEFAULT 0.05,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(state, school_type, year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS college_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER REFERENCES children(id) ON DELETE CASCADE,
                milestone_name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                target_date DATE,
                achieved INTEGER DEFAULT 0,
                achieved_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

render_sidebar_brand()
render_sidebar_user_widget()

st.title("🎓 Kids College 529 Planner")
st.markdown("Plan and track 529 college savings for your children.")

# Main page content
tab1, tab2, tab3, tab4 = st.tabs(["Children", "529 Accounts", "Contributions", "Projections"])

with tab1:
    st.subheader("Manage Children")
    st.info("Add and manage children for college planning.")

with tab2:
    st.subheader("529 Accounts")
    st.info("Track your 529 college savings accounts.")

with tab3:
    st.subheader("Contributions")
    st.info("Record and track contributions to 529 accounts.")

with tab4:
    st.subheader("Projections")
    st.info("View college cost projections and savings goals.")