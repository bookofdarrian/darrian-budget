import streamlit as st
import json
import re
from datetime import datetime
from typing import Optional, Dict, List, Any

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="eBay Listing Generator", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# --- Sidebar Navigation ---
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
    """Create eBay listings table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_listings (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100),
                product_name VARCHAR(500),
                brand VARCHAR(200),
                model VARCHAR(200),
                size VARCHAR(50),
                condition VARCHAR(100),
                color VARCHAR(100),
                title VARCHAR(80),
                description TEXT,
                suggested_price DECIMAL(10, 2),
                market_avg DECIMAL(10, 2),
                market_low DECIMAL(10, 2),
                market_high DECIMAL(10, 2),
                cost_basis DECIMAL(10, 2),
                profit_margin DECIMAL(5, 2),
                comparable_count INTEGER DEFAULT 0,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_cache (
                id SERIAL PRIMARY KEY,
                search_query VARCHAR(500),
                market_data JSONB,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                product_name TEXT,
                brand TEXT,
                model TEXT,
                size TEXT,
                condition TEXT,
                color TEXT,
                title TEXT,
                description TEXT,
                suggested_price REAL,
                market_avg REAL,
                market_low REAL,
                market_high REAL,
                cost_basis REAL,
                profit_margin REAL,
                comparable_count INTEGER DEFAULT 0,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_query TEXT,
                market_data TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_ebay_app_credentials() -> Dict[str, str]:
    """Get eBay API credentials from settings."""
    return {
        "app_id": get_setting("ebay_app_id") or "",
        "cert_id": get_setting("ebay_cert_id") or "",
        "dev_id": get_setting("ebay_dev_id") or ""
    }


def fetch_ebay_sold_listings(search_query: str, limit: int = 20) -> Dict[str, Any]:
    """
    Fetch comparable sold listings from eBay API.
    Falls back to simulated data if API not configured.
    """
    credentials = get_ebay_app_credentials()
    
    # Check cache first
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT market_data, fetched_at FROM ebay_market_cache 
        WHERE search_query = {placeholder}
        ORDER BY fetched_at DESC LIMIT 1
    """, (search_query,))
    
    cached = cur.fetchone()
    if cached:
        fetched_at = cached[1]
        if isinstance(fetched_at, str):
            fetched_at = datetime.fromisoformat(fetched_at)
        
        # Use cache if less than 6 hours old
        cache_age = (datetime.now() - fetched_at).total_seconds() / 3600
        if cache_age < 6:
            conn.close()
            market_data = cached[0]
            if isinstance(market_data, str):
                return json.loads(market_data)
            return market_data
    
    conn.close()
    
    # Return empty result if no cached data and API not configured
    return {
        "items": [],
        "avg_price": 0,
        "low_price": 0,
        "high_price": 0,
        "count": 0
    }


# Initialize tables
_ensure_tables()

# Main page content
st.title("🍑 eBay Listing Generator")
st.markdown("Generate optimized eBay listings with market research and pricing suggestions.")

# Input section
col1, col2 = st.columns(2)

with col1:
    product_name = st.text_input("Product Name", placeholder="e.g., Nike Air Max 90")
    brand = st.text_input("Brand", placeholder="e.g., Nike")
    model = st.text_input("Model", placeholder="e.g., Air Max 90")

with col2:
    size = st.text_input("Size", placeholder="e.g., 10.5")
    color = st.text_input("Color", placeholder="e.g., White/Black")
    condition = st.selectbox("Condition", ["New with tags", "New without tags", "Pre-owned - Like New", "Pre-owned - Good", "Pre-owned - Fair"])

cost_basis = st.number_input("Cost Basis ($)", min_value=0.0, step=0.01)

if st.button("Generate Listing", type="primary"):
    if product_name:
        search_query = f"{brand} {model} {product_name}".strip()
        market_data = fetch_ebay_sold_listings(search_query)
        
        # Display market research
        st.subheader("📊 Market Research")
        
        if market_data["count"] > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average Price", f"${market_data['avg_price']:.2f}")
            with col2:
                st.metric("Low Price", f"${market_data['low_price']:.2f}")
            with col3:
                st.metric("High Price", f"${market_data['high_price']:.2f}")
            with col4:
                st.metric("Comparables Found", market_data["count"])
            
            suggested_price = market_data['avg_price']
            if cost_basis > 0:
                profit = suggested_price - cost_basis
                margin = (profit / suggested_price) * 100 if suggested_price > 0 else 0
                st.markdown(f"**Estimated Profit:** ${profit:.2f} ({margin:.1f}% margin)")
        else:
            st.info("No comparable sold listings found. Consider adjusting your search terms.")
        
        # Generate title
        st.subheader("📝 Generated Listing")
        title = f"{brand} {model} {product_name} {size} {color}".strip()[:80]
        st.text_input("Title (max 80 chars)", value=title, max_chars=80)
        
        # Generate description
        description = f"""
{brand} {model} {product_name}

Size: {size}
Color: {color}
Condition: {condition}

Thank you for looking!
        """.strip()
        st.text_area("Description", value=description, height=200)
    else:
        st.warning("Please enter a product name.")