import streamlit as st
import json
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Paycheck Calculator v2", page_icon="🍑", layout="wide")
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

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paycheck_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                profile_name VARCHAR(255) NOT NULL,
                annual_salary DECIMAL(12,2) NOT NULL,
                pay_frequency VARCHAR(50) NOT NULL DEFAULT 'bi-weekly',
                filing_status VARCHAR(50) NOT NULL DEFAULT 'single',
                federal_allowances INTEGER DEFAULT 0,
                state_allowances INTEGER DEFAULT 0,
                pre_tax_401k DECIMAL(10,2) DEFAULT 0,
                pre_tax_hsa DECIMAL(10,2) DEFAULT 0,
                pre_tax_health DECIMAL(10,2) DEFAULT 0,
                pre_tax_fsa DECIMAL(10,2) DEFAULT 0,
                pre_tax_dental DECIMAL(10,2) DEFAULT 0,
                pre_tax_vision DECIMAL(10,2) DEFAULT 0,
                post_tax_roth_401k DECIMAL(10,2) DEFAULT 0,
                post_tax_other DECIMAL(10,2) DEFAULT 0,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_brackets_2024 (
                id SERIAL PRIMARY KEY,
                tax_type VARCHAR(50) NOT NULL,
                filing_status VARCHAR(50) NOT NULL,
                bracket_min DECIMAL(12,2) NOT NULL,
                bracket_max DECIMAL(12,2),
                rate DECIMAL(6,4) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_supplements (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                profile_id INTEGER REFERENCES paycheck_profiles(id),
                vest_date DATE NOT NULL,
                shares_vested INTEGER NOT NULL,
                price_per_share DECIMAL(10,2) NOT NULL,
                gross_value DECIMAL(12,2) NOT NULL,
                federal_withholding DECIMAL(10,2) NOT NULL,
                state_withholding DECIMAL(10,2) NOT NULL,
                fica_withholding DECIMAL(10,2) NOT NULL,
                net_value DECIMAL(12,2) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paycheck_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                profile_id INTEGER REFERENCES paycheck_profiles(id),
                pay_date DATE NOT NULL,
                gross_pay DECIMAL(12,2) NOT NULL,
                federal_tax DECIMAL(10,2) NOT NULL,
                state_tax DECIMAL(10,2) NOT NULL,
                social_security DECIMAL(10,2) NOT NULL,
                medicare DECIMAL(10,2) NOT NULL,
                pre_tax_deductions DECIMAL(10,2) NOT NULL,
                post_tax_deductions DECIMAL(10,2) NOT NULL,
                net_pay DECIMAL(12,2) NOT NULL,
                ytd_gross DECIMAL(12,2) DEFAULT 0,
                ytd_federal_tax DECIMAL(12,2) DEFAULT 0,
                ytd_state_tax DECIMAL(12,2) DEFAULT 0,
                ytd_social_security DECIMAL(12,2) DEFAULT 0,
                ytd_medicare DECIMAL(12,2) DEFAULT 0,
                is_rsu_supplement BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paycheck_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_name TEXT NOT NULL,
                annual_salary REAL NOT NULL,
                pay_frequency TEXT NOT NULL DEFAULT 'bi-weekly',
                filing_status TEXT NOT NULL DEFAULT 'single',
                federal_allowances INTEGER DEFAULT 0,
                state_allowances INTEGER DEFAULT 0,
                pre_tax_401k REAL DEFAULT 0,
                pre_tax_hsa REAL DEFAULT 0,
                pre_tax_health REAL DEFAULT 0,
                pre_tax_fsa REAL DEFAULT 0,
                pre_tax_dental REAL DEFAULT 0,
                pre_tax_vision REAL DEFAULT 0,
                post_tax_roth_401k REAL DEFAULT 0,
                post_tax_other REAL DEFAULT 0,
                is_default INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_brackets_2024 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tax_type TEXT NOT NULL,
                filing_status TEXT NOT NULL,
                bracket_min REAL NOT NULL,
                bracket_max REAL,
                rate REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_supplements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_id INTEGER REFERENCES paycheck_profiles(id),
                vest_date TEXT NOT NULL,
                shares_vested INTEGER NOT NULL,
                price_per_share REAL NOT NULL,
                gross_value REAL NOT NULL,
                federal_withholding REAL NOT NULL,
                state_withholding REAL NOT NULL,
                fica_withholding REAL NOT NULL,
                net_value REAL NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paycheck_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_id INTEGER REFERENCES paycheck_profiles(id),
                pay_date TEXT NOT NULL,
                gross_pay REAL NOT NULL,
                federal_tax REAL NOT NULL,
                state_tax REAL NOT NULL,
                social_security REAL NOT NULL,
                medicare REAL NOT NULL,
                pre_tax_deductions REAL NOT NULL,
                post_tax_deductions REAL NOT NULL,
                net_pay REAL NOT NULL,
                ytd_gross REAL DEFAULT 0,
                ytd_federal_tax REAL DEFAULT 0,
                ytd_state_tax REAL DEFAULT 0,
                ytd_social_security REAL DEFAULT 0,
                ytd_medicare REAL DEFAULT 0,
                is_rsu_supplement INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

def get_tax_optimization_tips(scenario_data):
    """Generate tax optimization tips based on paycheck scenario."""
    prompt = f"""As a tax optimization expert, analyze this paycheck scenario and provide 3-5 actionable tips:

Annual Salary: ${scenario_data.get('annual_salary', 0):,.2f}
Filing Status: {scenario_data.get('filing_status', 'single')}
Pre-tax 401k: ${scenario_data.get('pre_tax_401k', 0):,.2f}
Pre-tax HSA: ${scenario_data.get('pre_tax_hsa', 0):,.2f}
Federal Tax: ${scenario_data.get('federal_tax', 0):,.2f}
State Tax: ${scenario_data.get('state_tax', 0):,.2f}

Provide specific, actionable tax optimization strategies."""
    
    return prompt

st.title("💰 Paycheck Calculator v2")
st.write("Calculate your take-home pay with detailed tax breakdowns.")