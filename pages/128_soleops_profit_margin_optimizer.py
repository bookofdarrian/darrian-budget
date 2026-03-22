import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps: Profit Margin Optimizer", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar navigation
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
    """Create necessary tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_margin_analysis (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER,
                sku TEXT,
                item_name TEXT NOT NULL,
                cogs REAL NOT NULL DEFAULT 0,
                current_price REAL,
                recommended_price_ebay REAL,
                recommended_price_mercari REAL,
                recommended_price_depop REAL,
                market_average_price REAL,
                target_margin_pct REAL DEFAULT 30,
                shipping_cost REAL DEFAULT 0,
                ebay_margin_pct REAL,
                mercari_margin_pct REAL,
                depop_margin_pct REAL,
                ai_recommendation TEXT,
                competitive_alert TEXT,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if soleops_inventory exists, create if not
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku TEXT,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                condition TEXT DEFAULT 'New',
                purchase_price REAL DEFAULT 0,
                purchase_date DATE,
                platform TEXT,
                status TEXT DEFAULT 'In Stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_margin_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER,
                sku TEXT,
                item_name TEXT NOT NULL,
                cogs REAL NOT NULL DEFAULT 0,
                current_price REAL,
                recommended_price_ebay REAL,
                recommended_price_mercari REAL,
                recommended_price_depop REAL,
                market_average_price REAL,
                target_margin_pct REAL DEFAULT 30,
                shipping_cost REAL DEFAULT 0,
                ebay_margin_pct REAL,
                mercari_margin_pct REAL,
                depop_margin_pct REAL,
                ai_recommendation TEXT,
                competitive_alert TEXT,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                condition TEXT DEFAULT 'New',
                purchase_price REAL DEFAULT 0,
                purchase_date DATE,
                platform TEXT,
                status TEXT DEFAULT 'In Stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


# Platform fee structures
PLATFORM_FEES = {
    "ebay": {
        "name": "eBay",
        "seller_fee_pct": 13.25,
        "payment_processing_pct": 0,  # Included in 13.25%
        "fixed_fee": 0.30,
        "description": "13.25% final value fee (includes payment processing)"
    },
    "mercari": {
        "name": "Mercari",
        "seller_fee_pct": 10.0,
        "payment_processing_pct": 2.9,
        "fixed_fee": 0.50,
        "description": "10% seller fee + 2.9% + $0.50 payment processing"
    },
    "depop": {
        "name": "Depop",
        "seller_fee_pct": 10.0,
        "payment_processing_pct": 3.3,
        "fixed_fee": 0.45,
        "description": "10% seller fee + 3.3% + $0.45 payment processing"
    }
}


def calculate_platform_fees(sale_price, platform_key):
    """Calculate total fees for a given platform and sale price."""
    if platform_key not in PLATFORM_FEES:
        return 0
    
    platform = PLATFORM_FEES[platform_key]
    seller_fee = sale_price * (platform["seller_fee_pct"] / 100)
    processing_fee = sale_price * (platform["payment_processing_pct"] / 100) + platform["fixed_fee"]
    return seller_fee + processing_fee


def calculate_profit_margin(sale_price, cogs, shipping_cost, platform_key):
    """Calculate profit margin for a given sale."""
    fees = calculate_platform_fees(sale_price, platform_key)
    profit = sale_price - cogs - shipping_cost - fees
    margin_pct = (profit / sale_price * 100) if sale_price > 0 else 0
    return profit, margin_pct


def calculate_recommended_price(cogs, shipping_cost, target_margin_pct, platform_key):
    """Calculate recommended price to achieve target margin."""
    if platform_key not in PLATFORM_FEES:
        return cogs + shipping_cost
    
    platform = PLATFORM_FEES[platform_key]
    total_fee_pct = (platform["seller_fee_pct"] + platform["payment_processing_pct"]) / 100
    fixed_fee = platform["fixed_fee"]
    
    # Price = (COGS + Shipping + Fixed Fee + Target Profit) / (1 - Fee%)
    # Target Profit = Price * Target Margin%
    # Solving for Price: Price = (COGS + Shipping + Fixed Fee) / (1 - Fee% - Target Margin%)
    
    denominator = 1 - total_fee_pct - (target_margin_pct / 100)
    if denominator <= 0:
        return None  # Target margin not achievable
    
    recommended_price = (cogs + shipping_cost + fixed_fee) / denominator
    return round(recommended_price, 2)


# Initialize tables
_ensure_tables()

# Main page content
st.title("🍑 SoleOps: Profit Margin Optimizer")
st.markdown("Optimize your pricing strategy across platforms to maximize profit margins.")

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["📊 Margin Calculator", "📦 Inventory Analysis", "📈 Reports"])

with tab1:
    st.subheader("Quick Margin Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        item_name = st.text_input("Item Name", placeholder="Nike Air Jordan 1 Retro High OG")
        cogs = st.number_input("Cost of Goods (COGS)", min_value=0.0, value=100.0, step=5.0)
        shipping_cost = st.number_input("Shipping Cost", min_value=0.0, value=15.0, step=1.0)
        target_margin = st.slider("Target Margin %", min_value=5, max_value=60, value=30)
    
    with col2:
        st.markdown("### Recommended Prices by Platform")
        
        for platform_key, platform_info in PLATFORM_FEES.items():
            recommended = calculate_recommended_price(cogs, shipping_cost, target_margin, platform_key)
            if recommended:
                profit, margin = calculate_profit_margin(recommended, cogs, shipping_cost, platform_key)
                st.metric(
                    label=f"{platform_info['name']} Price",
                    value=f"${recommended:.2f}",
                    delta=f"${profit:.2f} profit ({margin:.1f}%)"
                )
            else:
                st.warning(f"{platform_info['name']}: Target margin not achievable")

with tab2:
    st.subheader("Inventory Margin Analysis")
    st.info("Connect your inventory to analyze margins across all items.")

with tab3:
    st.subheader("Margin Reports")
    st.info("View historical margin analysis and trends.")