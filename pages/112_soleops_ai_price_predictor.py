"""
SoleOps AI Price Predictor - Claude-powered predictive pricing engine
Analyzes eBay/Mercari historical data, market trends, and inventory age
to recommend optimal listing prices and predict future price movements.
"""

import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
import statistics

# Database and auth imports
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps AI Price Predictor", page_icon="🍑", layout="wide")
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


def _ph(count=1):
    """Return placeholder string based on database type."""
    if USE_POSTGRES:
        return ", ".join(["%s"] * count)
    return ", ".join(["?"] * count)


def _ensure_tables():
    """Create all necessary tables for the AI Price Predictor."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Price predictions table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_price_predictions (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT NOT NULL,
            predicted_price REAL NOT NULL,
            confidence_score REAL NOT NULL,
            market_trend TEXT,
            optimal_platform TEXT,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actual_sale_price REAL,
            accuracy_score REAL,
            prediction_rationale TEXT,
            factors_json TEXT
        )
    """)
    
    # Market signals table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_market_signals (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            sku TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            magnitude REAL NOT NULL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_data TEXT,
            user_id INTEGER
        )
    """)
    
    # Historical comps cache table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_comps_cache (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            sku TEXT NOT NULL,
            platform TEXT NOT NULL,
            comp_data TEXT NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            avg_price REAL,
            min_price REAL,
            max_price REAL,
            sample_count INTEGER
        )
    """)
    
    # Price velocity tracking
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_price_velocity (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            sku TEXT NOT NULL,
            velocity_7d REAL,
            velocity_30d REAL,
            velocity_90d REAL,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            trend_direction TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def fetch_historical_comps(sku: str, platform: str = "all") -> dict:
    """
    Fetch historical comparable sales data for a SKU.
    In production, this would call eBay/Mercari APIs.
    Returns cached data or simulated data for demo.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    # Check cache first (valid for 24 hours)
    cache_cutoff = datetime.now() - timedelta(hours=24)
    if USE_POSTGRES:
        cur.execute("""
            SELECT comp_data, avg_price, min_price, max_price, sample_count, fetched_at
            FROM soleops_comps_cache
            WHERE sku = %s AND (platform = %s OR %s = 'all')
            AND fetched_at > %s
            ORDER BY fetched_at DESC LIMIT 1
        """, (sku, platform, platform, cache_cutoff))
    else:
        cur.execute("""
            SELECT comp_data, avg_price, min_price, max_price, sample_count, fetched_at
            FROM soleops_comps_cache
            WHERE sku = ? AND (platform = ? OR ? = 'all')
            AND fetched_at > ?
            ORDER BY fetched_at DESC LIMIT 1
        """, (sku, platform, platform, cache_cutoff.isoformat()))
    
    row = cur.fetchone()
    
    if row:
        conn.close()
        return {
            "comp_data": json.loads(row[0]) if row[0] else [],
            "avg_price": row[1],
            "min_price": row[2],
            "max_price": row[3],
            "sample_count": row[4],
            "fetched_at": row[5]
        }
    
    conn.close()
    return {
        "comp_data": [],
        "avg_price": None,
        "min_price": None,
        "max_price": None,
        "sample_count": 0,
        "fetched_at": None
    }


# Initialize tables
_ensure_tables()

# Main UI
st.title("🍑 SoleOps AI Price Predictor")
st.markdown("Analyze market data and get AI-powered pricing recommendations.")

# SKU input
sku_input = st.text_input("Enter SKU to analyze:", placeholder="e.g., NIKE-DUNK-LOW-001")

if sku_input:
    st.subheader(f"Analysis for: {sku_input}")
    
    # Fetch comps
    comps = fetch_historical_comps(sku_input)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Average Price", f"${comps['avg_price']:.2f}" if comps['avg_price'] else "N/A")
    
    with col2:
        st.metric("Min Price", f"${comps['min_price']:.2f}" if comps['min_price'] else "N/A")
    
    with col3:
        st.metric("Max Price", f"${comps['max_price']:.2f}" if comps['max_price'] else "N/A")
    
    if comps['sample_count'] == 0:
        st.info("No historical data found for this SKU. Try a different SKU or check back later.")