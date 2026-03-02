import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
from decimal import Decimal
import json
import requests
from typing import Optional, Dict, Any, Tuple, List

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Rent vs Buy Calculator", page_icon="🍑", layout="wide")

init_db()
inject_css()
require_login()

# Atlanta-specific defaults
ATLANTA_DEFAULTS = {
    "property_tax_rate": 1.1,  # 1.1% of home value annually (Fulton County average)
    "homeowners_insurance_rate": 0.35,  # 0.35% of home value annually
    "hoa_monthly": 150,  # Average HOA in Atlanta metro
    "maintenance_rate": 1.0,  # 1% of home value annually for maintenance
    "closing_costs_rate": 3.0,  # 3% of purchase price
    "selling_costs_rate": 6.0,  # 6% of sale price (agent commissions)
    "home_appreciation_rate": 4.5,  # Atlanta historical average
    "rent_increase_rate": 3.5,  # Annual rent increase estimate
    "investment_return_rate": 7.0,  # S&P 500 average return
    "inflation_rate": 2.5,  # General inflation
    "pmi_rate": 0.5,  # PMI rate if down payment < 20%
    "pmi_threshold": 20.0,  # PMI drops off at 20% equity
}

# Atlanta neighborhood data (sample - would be populated from Zillow API)
ATLANTA_NEIGHBORHOODS = {
    "Buckhead": {"median_price": 650000, "median_rent": 2800, "appreciation": 5.0},
    "Midtown": {"median_price": 550000, "median_rent": 2500, "appreciation": 4.8},
    "Virginia Highland": {"median_price": 700000, "median_rent": 2600, "appreciation": 4.5},
    "Decatur": {"median_price": 480000, "median_rent": 2200, "appreciation": 5.2},
    "East Atlanta": {"median_price": 380000, "median_rent": 1800, "appreciation": 6.0},
    "Grant Park": {"median_price": 520000, "median_rent": 2100, "appreciation": 5.5},
    "Inman Park": {"median_price": 750000, "median_rent": 2700, "appreciation": 4.3},
    "Kirkwood": {"median_price": 420000, "median_rent": 1900, "appreciation": 5.8},
    "Old Fourth Ward": {"median_price": 480000, "median_rent": 2300, "appreciation": 5.0},
    "West Midtown": {"median_price": 520000, "median_rent": 2400, "appreciation": 5.5},
    "Sandy Springs": {"median_price": 550000, "median_rent": 2300, "appreciation": 4.2},
    "Marietta": {"median_price": 380000, "median_rent": 1700, "appreciation": 4.8},
    "Alpharetta": {"median_price": 520000, "median_rent": 2100, "appreciation": 4.5},
    "Smyrna": {"median_price": 420000, "median_rent": 1900, "appreciation": 5.0},
    "Custom": {"median_price": 400000, "median_rent": 2000, "appreciation": 4.5},
}


def _ensure_tables():
    """Create rent_vs_buy_scenarios table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rent_vs_buy_scenarios (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                scenario_name VARCHAR(255) NOT NULL,
                neighborhood VARCHAR(100),
                home_price DECIMAL(12, 2),
                down_payment_pct DECIMAL(5, 2),
                interest_rate DECIMAL(5, 3),
                loan_term_years INTEGER,
                monthly_rent DECIMAL(10, 2),
                property_tax_rate DECIMAL(5, 3),
                insurance_rate DECIMAL(5, 3),
                hoa_monthly DECIMAL(10, 2),
                maintenance_rate DECIMAL(5, 3),
                closing_costs_rate DECIMAL(5, 3),
                selling_costs_rate DECIMAL(5, 3),
                home_appreciation DECIMAL(5, 3),
                rent_increase DECIMAL(5, 3),
                investment_return DECIMAL(5, 3),
                analysis_years INTEGER,
                break_even_year DECIMAL(5, 2),
                buy_total_cost DECIMAL(14, 2),
                rent_total_cost DECIMAL(14, 2),
                recommendation VARCHAR(50),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zillow_market_cache (
                id SERIAL PRIMARY KEY,
                neighborhood VARCHAR(100) UNIQUE,
                median_price DECIMAL(12, 2),
                median_rent DECIMAL(10, 2),
                price_change_yoy DECIMAL(5, 2),
                rent_change_yoy DECIMAL(5, 2),
                days_on_market INTEGER,
                inventory_count INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rent_vs_buy_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                scenario_name TEXT NOT NULL,
                neighborhood TEXT,
                home_price REAL,
                down_payment_pct REAL,
                interest_rate REAL,
                loan_term_years INTEGER,
                monthly_rent REAL,
                property_tax_rate REAL,
                insurance_rate REAL,
                hoa_monthly REAL,
                maintenance_rate REAL,
                closing_costs_rate REAL,
                selling_costs_rate REAL,
                home_appreciation REAL,
                rent_increase REAL,
                investment_return REAL,
                analysis_years INTEGER,
                break_even_year REAL,
                buy_total_cost REAL,
                rent_total_cost REAL,
                recommendation TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zillow_market_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                neighborhood TEXT UNIQUE,
                median_price REAL,
                median_rent REAL,
                price_change_yoy REAL,
                rent_change_yoy REAL,
                days_on_market INTEGER,
                inventory_count INTEGER,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


_ensure_tables()

# Render sidebar
render_sidebar_brand()
render_sidebar_user_widget()

st.sidebar.markdown("---")
st.sidebar.page_link("pages/26_media_tracker.py", label="📺 Media Tracker")

st.title("🏠 Rent vs Buy Calculator")
st.markdown("**Atlanta-focused analysis to help you make the right housing decision**")