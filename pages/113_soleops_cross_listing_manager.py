import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Cross-Listing Manager", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_cross_listings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                platform_listing_id VARCHAR(255),
                listing_url TEXT,
                status VARCHAR(50) DEFAULT 'draft',
                listed_price DECIMAL(10,2),
                listed_at TIMESTAMP,
                synced_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_listing_templates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                template_name VARCHAR(255) NOT NULL,
                title_template TEXT,
                description_template TEXT,
                hashtags TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                brand VARCHAR(100),
                model VARCHAR(255),
                colorway VARCHAR(255),
                size VARCHAR(20),
                condition VARCHAR(50),
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                list_price DECIMAL(10,2),
                status VARCHAR(50) DEFAULT 'in_stock',
                location VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_cross_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                platform_listing_id TEXT,
                listing_url TEXT,
                status TEXT DEFAULT 'draft',
                listed_price REAL,
                listed_at TEXT,
                synced_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_listing_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                template_name TEXT NOT NULL,
                title_template TEXT,
                description_template TEXT,
                hashtags TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                condition TEXT,
                purchase_price REAL,
                purchase_date TEXT,
                list_price REAL,
                status TEXT DEFAULT 'in_stock',
                location TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# Get user_id from session
user_id = st.session_state.get("user_id", 1)

# Platform configurations
PLATFORMS = {
    "ebay": {"name": "eBay", "icon": "🏷️", "title_limit": 80},
    "stockx": {"name": "StockX", "icon": "📈", "title_limit": 100},
    "goat": {"name": "GOAT", "icon": "🐐", "title_limit": 100},
    "poshmark": {"name": "Poshmark", "icon": "👗", "title_limit": 80},
    "mercari": {"name": "Mercari", "icon": "🛒", "title_limit": 80},
    "depop": {"name": "Depop", "icon": "🌈", "title_limit": 80}
}

st.title("🍑 SoleOps Cross-Listing Manager")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "📋 Listings", "📝 Templates", "⚙️ Settings"])

with tab1:
    st.subheader("Inventory Management")
    
    # Add new inventory item
    with st.expander("➕ Add New Item"):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("SKU")
            brand = st.text_input("Brand")
            model = st.text_input("Model")
            colorway = st.text_input("Colorway")
        with col2:
            size = st.text_input("Size")
            condition = st.selectbox("Condition", ["New", "Like New", "Good", "Fair"])
            purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
            list_price = st.number_input("List Price ($)", min_value=0.0, step=0.01)
        
        if st.button("Add Item"):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO soleops_inventory (user_id, sku, brand, model, colorway, size, condition, purchase_price, list_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """ if not USE_POSTGRES else """
                INSERT INTO soleops_inventory (user_id, sku, brand, model, colorway, size, condition, purchase_price, list_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, sku, brand, model, colorway, size, condition, purchase_price, list_price))
            conn.commit()
            conn.close()
            st.success("Item added!")
            st.rerun()
    
    # Display inventory
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, sku, brand, model, colorway, size, condition, purchase_price, list_price, status
        FROM soleops_inventory WHERE user_id = ?
    """ if not USE_POSTGRES else """
        SELECT id, sku, brand, model, colorway, size, condition, purchase_price, list_price, status
        FROM soleops_inventory WHERE user_id = %s
    """, (user_id,))
    inventory = cur.fetchall()
    conn.close()
    
    if inventory:
        for item in inventory:
            with st.container():
                cols = st.columns([2, 2, 1, 1, 1])
                cols[0].write(f"**{item[2]} {item[3]}**")
                cols[1].write(f"{item[4]} - Size {item[5]}")
                cols[2].write(f"${item[8]:.2f}")
                cols[3].write(item[9])
    else:
        st.info("No inventory items yet. Add your first item above!")

with tab2:
    st.subheader("Cross-Listings")
    st.info("Select inventory items to create listings across multiple platforms.")

with tab3:
    st.subheader("Listing Templates")
    st.info("Create templates for different platforms to speed up listing creation.")

with tab4:
    st.subheader("Settings")
    
    # Platform fee calculator
    st.markdown("### 💰 Fee Calculator")
    test_price = st.number_input("Enter test sale price ($)", value=100.0, min_value=0.0, step=1.0)
    
    if test_price > 0:
        st.markdown("**Estimated fees by platform:**")
        fees = {
            "eBay": test_price * 0.1325,
            "StockX": test_price * 0.10,
            "GOAT": test_price * 0.095,
            "Poshmark": test_price * 0.20 if test_price > 15 else 2.95,
            "Mercari": test_price * 0.10,
            "Depop": test_price * 0.10
        }
        for platform, fee in fees.items():
            st.write(f"- {platform}: ${fee:.2f} (Net: ${test_price - fee:.2f})")