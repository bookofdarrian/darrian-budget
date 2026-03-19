import streamlit as st
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
import json
import io

st.set_page_config(page_title="SoleOps Inventory Manager", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

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

# Condition grades and their value adjustments
CONDITION_GRADES = {
    "DS": {"label": "Deadstock (New)", "adjustment": 1.0, "description": "Brand new, never worn, with original box and tags"},
    "VNDS": {"label": "Very Near Deadstock", "adjustment": 0.90, "description": "Tried on once or twice, minimal signs of wear"},
    "PADS": {"label": "Pass As Deadstock", "adjustment": 0.80, "description": "Light wear, could pass as new to untrained eye"},
    "Used": {"label": "Used", "adjustment": 0.65, "description": "Visible wear, creasing, or sole wear"}
}

INVENTORY_STATUS = ["In Stock", "Listed", "Sold", "Shipped", "Returned", "Damaged"]

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                name VARCHAR(255) NOT NULL,
                brand VARCHAR(100),
                size VARCHAR(20),
                condition VARCHAR(20) DEFAULT 'DS',
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                storage_location VARCHAR(100),
                bin_number VARCHAR(50),
                shelf VARCHAR(50),
                platform_listed VARCHAR(100),
                list_price DECIMAL(10,2),
                market_value DECIMAL(10,2),
                status VARCHAR(50) DEFAULT 'In Stock',
                sold_price DECIMAL(10,2),
                sold_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_storage_locations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                location_name VARCHAR(100) NOT NULL,
                description TEXT,
                capacity INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                name TEXT NOT NULL,
                brand TEXT,
                size TEXT,
                condition TEXT DEFAULT 'DS',
                purchase_price REAL,
                purchase_date TEXT,
                storage_location TEXT,
                bin_number TEXT,
                shelf TEXT,
                platform_listed TEXT,
                list_price REAL,
                market_value REAL,
                status TEXT DEFAULT 'In Stock',
                sold_price REAL,
                sold_date TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_storage_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                location_name TEXT NOT NULL,
                description TEXT,
                capacity INTEGER DEFAULT 50,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_inventory(user_id, filters=None):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    query = f"SELECT * FROM soleops_inventory WHERE user_id = {ph}"
    params = [user_id]
    
    if filters:
        if filters.get("status"):
            query += f" AND status = {ph}"
            params.append(filters["status"])
        if filters.get("condition"):
            query += f" AND condition = {ph}"
            params.append(filters["condition"])
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_storage_locations(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM soleops_storage_locations WHERE user_id = {ph}", [user_id])
    rows = cur.fetchall()
    conn.close()
    return rows

# Main page content
st.title("🍑 SoleOps Inventory Manager")

user_id = get_user_id()

tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "➕ Add Item", "📍 Storage", "📊 Import/Export"])

with tab1:
    st.subheader("Current Inventory")
    inventory = get_inventory(user_id)
    if inventory:
        df = pd.DataFrame(inventory)
        st.dataframe(df)
    else:
        st.info("No inventory items found. Add your first item!")

with tab2:
    st.subheader("Add New Item")
    with st.form("add_item_form"):
        name = st.text_input("Item Name")
        sku = st.text_input("SKU")
        brand = st.text_input("Brand")
        size = st.text_input("Size")
        condition = st.selectbox("Condition", list(CONDITION_GRADES.keys()))
        purchase_price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
        submitted = st.form_submit_button("Add Item")
        if submitted and name:
            st.success(f"Added {name} to inventory!")

with tab3:
    st.subheader("Storage Locations")
    locations = get_storage_locations(user_id)
    if locations:
        for loc in locations:
            st.write(f"📍 {loc}")
    else:
        st.info("No storage locations configured.")

with tab4:
    st.subheader("Import/Export")
    
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        available_columns = df.columns.tolist()
        
        sku_index = available_columns.index("sku") if "sku" in available_columns else 0
        sku_col = st.selectbox("SKU Column", available_columns, index=sku_index)
        
        st.dataframe(df.head())
        
        if st.button("Import Data"):
            st.success("Data imported successfully!")