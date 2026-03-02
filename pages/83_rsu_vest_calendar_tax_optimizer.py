import streamlit as st
import datetime
import calendar
import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List, Tuple
import pandas as pd

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="RSU Vest Calendar + Tax Optimizer", page_icon="🍑", layout="wide")
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
    """Create RSU vest tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                company VARCHAR(255) NOT NULL,
                vest_date DATE NOT NULL,
                shares DECIMAL(12, 4) NOT NULL,
                price_at_vest DECIMAL(12, 2),
                withholding_rate DECIMAL(5, 4) DEFAULT 0.22,
                shares_withheld DECIMAL(12, 4) DEFAULT 0,
                actual_withholding DECIMAL(12, 2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                filing_status VARCHAR(50) DEFAULT 'single',
                state VARCHAR(2) DEFAULT 'GA',
                annual_income_estimate DECIMAL(14, 2) DEFAULT 0,
                other_withholding DECIMAL(14, 2) DEFAULT 0,
                prior_year_tax DECIMAL(14, 2) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                alert_message TEXT NOT NULL,
                quarter INTEGER,
                year INTEGER,
                is_resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company TEXT NOT NULL,
                vest_date DATE NOT NULL,
                shares REAL NOT NULL,
                price_at_vest REAL,
                withholding_rate REAL DEFAULT 0.22,
                shares_withheld REAL DEFAULT 0,
                actual_withholding REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                filing_status TEXT DEFAULT 'single',
                state TEXT DEFAULT 'GA',
                annual_income_estimate REAL DEFAULT 0,
                other_withholding REAL DEFAULT 0,
                prior_year_tax REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                alert_message TEXT NOT NULL,
                quarter INTEGER,
                year INTEGER,
                is_resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


# 2024 Federal Tax Brackets
FEDERAL_TAX_BRACKETS_2024 = {
    'single': [
        (11600, 0.10),
        (47150, 0.12),
        (100525, 0.22),
        (191950, 0.24),
        (243725, 0.32),
        (609350, 0.35),
        (float('inf'), 0.37)
    ],
    'married_filing_jointly': [
        (23200, 0.10),
        (94300, 0.12),
        (201050, 0.22),
        (383900, 0.24),
        (487450, 0.32),
        (731200, 0.35),
        (float('inf'), 0.37)
    ]
}

# Initialize tables
_ensure_tables()

st.title("🍑 RSU Vest Calendar + Tax Optimizer")
st.markdown("Track your RSU vests and optimize tax withholding")