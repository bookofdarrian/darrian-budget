import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from decimal import Decimal
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Health Cost Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
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
            CREATE TABLE IF NOT EXISTS health_expenses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expense_date DATE NOT NULL,
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100),
                description TEXT,
                amount DECIMAL(10,2) NOT NULL,
                provider VARCHAR(200),
                is_hsa_eligible BOOLEAN DEFAULT FALSE,
                is_reimbursed BOOLEAN DEFAULT FALSE,
                reimbursed_date DATE,
                reimbursed_amount DECIMAL(10,2),
                receipt_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_contributions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                contribution_date DATE NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                source VARCHAR(50) NOT NULL,
                tax_year INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_withdrawals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                withdrawal_date DATE NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                expense_id INTEGER REFERENCES health_expenses(id),
                tax_year INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS health_recurring (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                frequency VARCHAR(20) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                is_hsa_eligible BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS health_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                expense_date DATE NOT NULL,
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(100),
                description TEXT,
                amount DECIMAL(10,2) NOT NULL,
                provider VARCHAR(200),
                is_hsa_eligible BOOLEAN DEFAULT 0,
                is_reimbursed BOOLEAN DEFAULT 0,
                reimbursed_date DATE,
                reimbursed_amount DECIMAL(10,2),
                receipt_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contribution_date DATE NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                source VARCHAR(50) NOT NULL,
                tax_year INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                withdrawal_date DATE NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                expense_id INTEGER,
                tax_year INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS health_recurring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                frequency VARCHAR(20) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                is_active BOOLEAN DEFAULT 1,
                is_hsa_eligible BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

def get_hsa_contributions(user_id, year=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if year:
        cur.execute(f"""
            SELECT id, contribution_date, amount, source, tax_year, notes
            FROM hsa_contributions
            WHERE user_id = {ph} AND tax_year = {ph}
            ORDER BY contribution_date DESC
        """, (user_id, year))
    else:
        cur.execute(f"""
            SELECT id, contribution_date, amount, source, tax_year, notes
            FROM hsa_contributions
            WHERE user_id = {ph}
            ORDER BY contribution_date DESC
        """, (user_id,))
    
    rows = cur.fetchall()
    contributions = []
    for row in rows:
        contributions.append({
            'id': row[0],
            'contribution_date': row[1],
            'amount': row[2],
            'source': row[3],
            'tax_year': row[4],
            'notes': row[5]
        })
    return contributions

def calculate_year_contributions(user_id, year):
    contributions = get_hsa_contributions(user_id, year)
    year_contributions = sum(float(c['amount']) for c in contributions)
    return year_contributions

# Initialize tables
_ensure_tables()

# Main page content
st.title("🏥 Health Cost Tracker")

user_id = st.session_state.get('user_id', 1)

tab1, tab2, tab3 = st.tabs(["Expenses", "HSA Tracker", "Reports"])

with tab1:
    st.subheader("Health Expenses")
    st.info("Track your medical expenses here.")

with tab2:
    st.subheader("HSA Contributions & Withdrawals")
    current_year = datetime.now().year
    year_contributions = calculate_year_contributions(user_id, current_year)
    st.metric("Year-to-Date Contributions", f"${year_contributions:,.2f}")

with tab3:
    st.subheader("Health Cost Reports")
    st.info("View reports and analytics here.")