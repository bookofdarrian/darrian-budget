import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
import json
import io
import csv

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Inventory Manager", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(255) NOT NULL,
                colorway VARCHAR(255),
                size VARCHAR(20) NOT NULL,
                condition VARCHAR(50) DEFAULT 'New',
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                purchase_source VARCHAR(255),
                quantity INTEGER DEFAULT 1,
                storage_location VARCHAR(255),
                notes TEXT,
                status VARCHAR(50) DEFAULT 'in_stock',
                sold_price DECIMAL(10,2),
                sold_date DATE,
                sold_platform VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_listings (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES soleops_inventory(id) ON DELETE CASCADE,
                platform VARCHAR(50) NOT NULL,
                listing_id VARCHAR(255),
                list_price DECIMAL(10,2),
                listed_date DATE,
                listing_url VARCHAR(500),
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_photos (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES soleops_inventory(id) ON DELETE CASCADE,
                photo_url VARCHAR(500) NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_data (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100),
                brand VARCHAR(100),
                model VARCHAR(255),
                size VARCHAR(20),
                platform VARCHAR(50),
                avg_price DECIMAL(10,2),
                last_sale_price DECIMAL(10,2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                colorway TEXT,
                size TEXT NOT NULL,
                condition TEXT DEFAULT 'New',
                purchase_price REAL,
                purchase_date TEXT,
                purchase_source TEXT,
                quantity INTEGER DEFAULT 1,
                storage_location TEXT,
                notes TEXT,
                status TEXT DEFAULT 'in_stock',
                sold_price REAL,
                sold_date TEXT,
                sold_platform TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER REFERENCES soleops_inventory(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                listing_id TEXT,
                list_price REAL,
                listed_date TEXT,
                listing_url TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER REFERENCES soleops_inventory(id) ON DELETE CASCADE,
                photo_url TEXT NOT NULL,
                is_primary INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                brand TEXT,
                model TEXT,
                size TEXT,
                platform TEXT,
                avg_price REAL,
                last_sale_price REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

def get_inventory(user_id, status_filter=None):
    conn = get_conn()
    cur = conn.cursor()
    
    if status_filter:
        cur.execute("""
            SELECT * FROM soleops_inventory 
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC
        """.replace("?", "%s") if USE_POSTGRES else """
            SELECT * FROM soleops_inventory 
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC
        """, (user_id, status_filter))
    else:
        cur.execute("""
            SELECT * FROM soleops_inventory 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """.replace("?", "%s") if USE_POSTGRES else """
            SELECT * FROM soleops_inventory 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]

def add_inventory_item(user_id, data):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO soleops_inventory 
        (user_id, sku, brand, model, colorway, size, condition, purchase_price, 
         purchase_date, purchase_source, quantity, storage_location, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """.replace("?", "%s") if USE_POSTGRES else """
        INSERT INTO soleops_inventory 
        (user_id, sku, brand, model, colorway, size, condition, purchase_price, 
         purchase_date, purchase_source, quantity, storage_location, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, data.get('sku'), data['brand'], data['model'], data.get('colorway'),
        data['size'], data.get('condition', 'New'), data.get('purchase_price'),
        data.get('purchase_date'), data.get('purchase_source'), data.get('quantity', 1),
        data.get('storage_location'), data.get('notes'), data.get('status', 'in_stock')
    ))
    
    conn.commit()
    return cur.lastrowid

def update_inventory_item(item_id, data):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE soleops_inventory 
        SET sku = ?, brand = ?, model = ?, colorway = ?, size = ?, condition = ?,
            purchase_price = ?, purchase_date = ?, purchase_source = ?, quantity = ?,
            storage_location = ?, notes = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """.replace("?", "%s") if USE_POSTGRES else """
        UPDATE soleops_inventory 
        SET sku = ?, brand = ?, model = ?, colorway = ?, size = ?, condition = ?,
            purchase_price = ?, purchase_date = ?, purchase_source = ?, quantity = ?,
            storage_location = ?, notes = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.get('sku'), data['brand'], data['model'], data.get('colorway'),
        data['size'], data.get('condition', 'New'), data.get('purchase_price'),
        data.get('purchase_date'), data.get('purchase_source'), data.get('quantity', 1),
        data.get('storage_location'), data.get('notes'), data.get('status', 'in_stock'),
        item_id
    ))
    
    conn.commit()

def delete_inventory_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM soleops_inventory WHERE id = ?".replace("?", "%s") if USE_POSTGRES else "DELETE FROM soleops_inventory WHERE id = ?", (item_id,))
    conn.commit()

def mark_as_sold(item_id, sold_price, sold_date, sold_platform):
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE soleops_inventory 
        SET status = 'sold', sold_price = ?, sold_date = ?, sold_platform = ?, 
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """.replace("?", "%s") if USE_POSTGRES else """
        UPDATE soleops_inventory 
        SET status = 'sold', sold_price = ?, sold_date = ?, sold_platform = ?, 
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (sold_price, sold_date, sold_platform, item_id))
    
    conn.commit()

# Main UI
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🍑 SoleOps Comprehensive Inventory Manager")

user_id = st.session_state.get("user_id", 1)

tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "➕ Add Item", "📊 Analytics", "⚙️ Settings"])

with tab1:
    st.subheader("Inventory List")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "in_stock", "listed", "sold"])
    
    filter_val = None if status_filter == "All" else status_filter
    inventory = get_inventory(user_id, filter_val)
    
    if inventory:
        for item in inventory:
            with st.expander(f"{item['brand']} {item['model']} - Size {item['size']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**SKU:** {item.get('sku', 'N/A')}")
                    st.write(f"**Colorway:** {item.get('colorway', 'N/A')}")
                    st.write(f"**Condition:** {item.get('condition', 'New')}")
                with col2:
                    st.write(f"**Purchase Price:** ${item.get('purchase_price', 0):.2f}")
                    st.write(f"**Purchase Date:** {item.get('purchase_date', 'N/A')}")
                    st.write(f"**Source:** {item.get('purchase_source', 'N/A')}")
                with col3:
                    st.write(f"**Status:** {item.get('status', 'in_stock')}")
                    st.write(f"**Location:** {item.get('storage_location', 'N/A')}")
                    st.write(f"**Quantity:** {item.get('quantity', 1)}")
                
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("✏️ Edit", key=f"edit_{item['id']}"):
                        st.session_state['edit_item_id'] = item['id']
                with btn_col2:
                    if st.button("💰 Mark Sold", key=f"sell_{item['id']}"):
                        st.session_state['sell_item_id'] = item['id']
                with btn_col3:
                    if st.button("🗑️ Delete", key=f"delete_{item['id']}"):
                        delete_inventory_item(item['id'])
                        st.rerun()
    else:
        st.info("No inventory items found. Add some items to get started!")

with tab2:
    st.subheader("Add New Inventory Item")
    
    with st.form("add_item_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            brand = st.text_input("Brand *", placeholder="Nike, Adidas, etc.")
            model = st.text_input("Model *", placeholder="Air Jordan 1, Yeezy 350, etc.")
            colorway = st.text_input("Colorway", placeholder="Bred, Zebra, etc.")
            size = st.text_input("Size *", placeholder="10, 10.5, etc.")
            sku = st.text_input("SKU", placeholder="DQ4914-600")
        
        with col2:
            condition = st.selectbox("Condition", ["New", "Used - Like New", "Used - Good", "Used - Fair"])
            purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
            purchase_date = st.date_input("Purchase Date", value=datetime.now())
            purchase_source = st.text_input("Purchase Source", placeholder="StockX, SNKRS, etc.")
            quantity = st.number_input("Quantity", min_value=1, value=1)
        
        storage_location = st.text_input("Storage Location", placeholder="Shelf A, Box 1, etc.")
        notes = st.text_area("Notes", placeholder="Any additional notes...")
        
        submitted = st.form_submit_button("Add Item")
        
        if submitted:
            if brand and model and size:
                item_data = {
                    'sku': sku,
                    'brand': brand,
                    'model': model,
                    'colorway': colorway,
                    'size': size,
                    'condition': condition,
                    'purchase_price': purchase_price,
                    'purchase_date': str(purchase_date),
                    'purchase_source': purchase_source,
                    'quantity': quantity,
                    'storage_location': storage_location,
                    'notes': notes,
                    'status': 'in_stock'
                }
                add_inventory_item(user_id, item_data)
                st.success("Item added successfully!")
                st.rerun()
            else:
                st.error("Please fill in all required fields (Brand, Model, Size)")

with tab3:
    st.subheader("Inventory Analytics")
    
    all_inventory = get_inventory(user_id)
    
    if all_inventory:
        df = pd.DataFrame(all_inventory)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_items = len(df)
            st.metric("Total Items", total_items)
        
        with col2:
            in_stock = len(df[df['status'] == 'in_stock'])
            st.metric("In Stock", in_stock)
        
        with col3:
            total_invested = df['purchase_price'].sum() if 'purchase_price' in df.columns else 0
            st.metric("Total Invested", f"${total_invested:,.2f}")
        
        with col4:
            sold_items = df[df['status'] == 'sold']
            if len(sold_items) > 0 and 'sold_price' in sold_items.columns:
                total_revenue = sold_items['sold_price'].sum()
                st.metric("Total Revenue", f"${total_revenue:,.2f}")
            else:
                st.metric("Total Revenue", "$0.00")
    else:
        st.info("No data available for analytics.")

with tab4:
    st.subheader("Settings")
    st.info("Settings coming soon!")