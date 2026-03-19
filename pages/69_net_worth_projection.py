import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from decimal import Decimal
import json
import io

st.set_page_config(page_title="Net Worth Projection", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS net_worth_projections (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                name VARCHAR(255) NOT NULL,
                current_net_worth DECIMAL(15,2) DEFAULT 0,
                annual_savings DECIMAL(15,2) DEFAULT 0,
                savings_rate DECIMAL(5,2) DEFAULT 20.0,
                expected_return DECIMAL(5,2) DEFAULT 7.0,
                inflation_rate DECIMAL(5,2) DEFAULT 3.0,
                projection_years INTEGER DEFAULT 20,
                scenario_type VARCHAR(50) DEFAULT 'base',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projection_scenarios (
                id SERIAL PRIMARY KEY,
                projection_id INTEGER REFERENCES net_worth_projections(id) ON DELETE CASCADE,
                scenario_name VARCHAR(100) NOT NULL,
                return_rate DECIMAL(5,2),
                savings_adjustment DECIMAL(5,2) DEFAULT 0,
                inflation_adjustment DECIMAL(5,2) DEFAULT 0,
                probability_weight DECIMAL(5,2) DEFAULT 33.33,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projection_snapshots (
                id SERIAL PRIMARY KEY,
                projection_id INTEGER REFERENCES net_worth_projections(id) ON DELETE CASCADE,
                year_number INTEGER NOT NULL,
                projected_value DECIMAL(15,2),
                inflation_adjusted_value DECIMAL(15,2),
                cumulative_contributions DECIMAL(15,2),
                cumulative_growth DECIMAL(15,2),
                scenario_type VARCHAR(50) DEFAULT 'base',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_projections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                name TEXT NOT NULL,
                current_net_worth REAL DEFAULT 0,
                annual_savings REAL DEFAULT 0,
                savings_rate REAL DEFAULT 20.0,
                expected_return REAL DEFAULT 7.0,
                inflation_rate REAL DEFAULT 3.0,
                projection_years INTEGER DEFAULT 20,
                scenario_type TEXT DEFAULT 'base',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projection_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projection_id INTEGER REFERENCES net_worth_projections(id) ON DELETE CASCADE,
                scenario_name TEXT NOT NULL,
                return_rate REAL,
                savings_adjustment REAL DEFAULT 0,
                inflation_adjustment REAL DEFAULT 0,
                probability_weight REAL DEFAULT 33.33,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projection_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projection_id INTEGER REFERENCES net_worth_projections(id) ON DELETE CASCADE,
                year_number INTEGER NOT NULL,
                projected_value REAL,
                inflation_adjusted_value REAL,
                cumulative_contributions REAL,
                cumulative_growth REAL,
                scenario_type TEXT DEFAULT 'base',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_current_net_worth():
    """Pull current net worth from existing net_worth table if available"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        ph = "%s" if USE_POSTGRES else "?"
        cur.execute("""
            SELECT total_assets - total_liabilities as net_worth 
            FROM net_worth 
            ORDER BY created_at DESC LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            return float(row[0]) if row[0] else 0.0
        return 0.0
    except Exception:
        return 0.0
    finally:
        conn.close()

st.title("🍑 Net Worth Projection")
st.write("Project your future net worth based on savings and investment assumptions.")