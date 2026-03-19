import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
import io

st.set_page_config(page_title="SoleOps Inventory Manager", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(200) NOT NULL,
                colorway VARCHAR(200),
                size VARCHAR(20) NOT NULL,
                condition VARCHAR(50) DEFAULT 'New',
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                purchase_source VARCHAR(200),
                listed_platforms JSONB DEFAULT '[]',
                list_prices JSONB DEFAULT '{}',
                status VARCHAR(50) DEFAULT 'in_stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_cache (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100),
                brand VARCHAR(100),
                model VARCHAR(200),
                size VARCHAR(20),
                platform VARCHAR(50),
                avg_price DECIMAL(10,2),
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
                listed_platforms TEXT DEFAULT '[]',
                list_prices TEXT DEFAULT '{}',
                status TEXT DEFAULT 'in_stock',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                brand TEXT,
                model TEXT,
                size TEXT,
                platform TEXT,
                avg_price REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()


_ensure_tables()


def ph(count=1):
    return ", ".join(["%s"] * count) if USE_POSTGRES else ", ".join(["?"] * count)


def get_inventory(user_id, filters=None):
    conn = get_conn()
    cur = conn.cursor()
    
    query = f"""
        SELECT id, sku, brand, model, colorway, size, condition, 
               purchase_price, purchase_date, purchase_source,
               listed_platforms, list_prices, status, notes, created_at, updated_at
        FROM soleops_inventory
        WHERE user_id = {ph()}
    """
    params = [user_id]
    
    if filters:
        if filters.get("brand"):
            query += f" AND LOWER(brand) LIKE LOWER({ph()})"
            params.append(f"%{filters['brand']}%")
        if filters.get("status"):
            query += f" AND status = {ph()}"
            params.append(filters["status"])
        if filters.get("size"):
            query += f" AND size = {ph()}"
            params.append(filters["size"])
        if filters.get("platform"):
            if USE_POSTGRES:
                query += f" AND listed_platforms::text LIKE {ph()}"
            else:
                query += f" AND listed_platforms LIKE {ph()}"
            params.append(f'%"{filters["platform"]}"%')
        if filters.get("date_from"):
            query += f" AND purchase_date >= {ph()}"
            params.append(filters["date_from"])
        if filters.get("date_to"):
            query += f" AND purchase_date <= {ph()}"
            params.append(filters["date_to"])
    
    query += " ORDER BY created_at DESC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    inventory = []
    for row in rows:
        listed_platforms = row[10]
        list_prices = row[11]
        
        if isinstance(listed_platforms, str):
            try:
                listed_platforms = json.loads(listed_platforms)
            except:
                listed_platforms = []
        
        if isinstance(list_prices, str):
            try:
                list_prices = json.loads(list_prices)
            except:
                list_prices = {}
        
        inventory.append({
            "id": row[0],
            "sku": row[1],
            "brand": row[2],
            "model": row[3],
            "colorway": row[4],
            "size": row[5],
            "condition": row[6],
            "purchase_price": float(row[7]) if row[7] else None,
            "purchase_date": row[8],
            "purchase_source": row[9],
            "listed_platforms": listed_platforms,
            "list_prices": list_prices,
            "status": row[12],
            "notes": row[13],
            "created_at": row[14],
            "updated_at": row[15]
        })
    
    return inventory


def add_inventory_item(user_id, item_data):
    conn = get_conn()
    cur = conn.cursor()
    
    listed_platforms = json.dumps(item_data.get("listed_platforms", []))
    list_prices = json.dumps(item_data.get("list_prices", {}))
    
    cur.execute(f"""
        INSERT INTO soleops_inventory 
        (user_id, sku, brand, model, colorway, size, condition, 
         purchase_price, purchase_date, purchase_source, listed_platforms, 
         list_prices, status, notes)
        VALUES ({ph(14)})
    """, (
        user_id,
        item_data.get("sku"),
        item_data["brand"],
        item_data["model"],
        item_data.get("colorway"),
        item_data["size"],
        item_data.get("condition", "New"),
        item_data.get("purchase_price"),
        item_data.get("purchase_date"),
        item_data.get("purchase_source"),
        listed_platforms,
        list_prices,
        item_data.get("status", "in_stock"),
        item_data.get("notes")
    ))
    
    conn.commit()
    cur.close()
    conn.close()


def update_inventory_item(item_id, item_data):
    conn = get_conn()
    cur = conn.cursor()
    
    listed_platforms = json.dumps(item_data.get("listed_platforms", []))
    list_prices = json.dumps(item_data.get("list_prices", {}))
    
    cur.execute(f"""
        UPDATE soleops_inventory SET
        sku = {ph()}, brand = {ph()}, model = {ph()}, colorway = {ph()},
        size = {ph()}, condition = {ph()}, purchase_price = {ph()},
        purchase_date = {ph()}, purchase_source = {ph()}, 
        listed_platforms = {ph()}, list_prices = {ph()},
        status = {ph()}, notes = {ph()}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph()}
    """, (
        item_data.get("sku"),
        item_data["brand"],
        item_data["model"],
        item_data.get("colorway"),
        item_data["size"],
        item_data.get("condition", "New"),
        item_data.get("purchase_price"),
        item_data.get("purchase_date"),
        item_data.get("purchase_source"),
        listed_platforms,
        list_prices,
        item_data.get("status", "in_stock"),
        item_data.get("notes"),
        item_id
    ))
    
    conn.commit()
    cur.close()
    conn.close()


def delete_inventory_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM soleops_inventory WHERE id = {ph()}", (item_id,))
    conn.commit()
    cur.close()
    conn.close()


# Main UI
st.title("🍑 SoleOps Inventory Manager")

render_sidebar_brand()
render_sidebar_user_widget()

user_id = st.session_state.get("user_id", 1)

tab1, tab2, tab3 = st.tabs(["📦 Inventory", "➕ Add Item", "📊 Analytics"])

with tab1:
    st.subheader("Current Inventory")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_brand = st.text_input("Filter by Brand")
    with col2:
        filter_status = st.selectbox("Status", ["", "in_stock", "listed", "sold"])
    with col3:
        filter_size = st.text_input("Size")
    with col4:
        filter_platform = st.selectbox("Platform", ["", "StockX", "GOAT", "eBay", "Grailed"])
    
    filters = {}
    if filter_brand:
        filters["brand"] = filter_brand
    if filter_status:
        filters["status"] = filter_status
    if filter_size:
        filters["size"] = filter_size
    if filter_platform:
        filters["platform"] = filter_platform
    
    inventory = get_inventory(user_id, filters if filters else None)
    
    if inventory:
        df = pd.DataFrame(inventory)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No inventory items found. Add some items to get started!")

with tab2:
    st.subheader("Add New Item")
    
    with st.form("add_item_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            brand = st.text_input("Brand*", placeholder="Nike, Adidas, etc.")
            model = st.text_input("Model*", placeholder="Air Jordan 1 Retro High OG")
            colorway = st.text_input("Colorway", placeholder="Chicago")
            size = st.text_input("Size*", placeholder="10")
            sku = st.text_input("SKU", placeholder="DZ5485-612")
        
        with col2:
            condition = st.selectbox("Condition", ["New", "Used - Like New", "Used - Good", "Used - Fair"])
            purchase_price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
            purchase_date = st.date_input("Purchase Date")
            purchase_source = st.text_input("Purchase Source", placeholder="Nike SNKRS, Foot Locker, etc.")
            status = st.selectbox("Status", ["in_stock", "listed", "sold"])
        
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("Add Item")
        
        if submitted:
            if brand and model and size:
                item_data = {
                    "sku": sku,
                    "brand": brand,
                    "model": model,
                    "colorway": colorway,
                    "size": size,
                    "condition": condition,
                    "purchase_price": purchase_price if purchase_price > 0 else None,
                    "purchase_date": str(purchase_date),
                    "purchase_source": purchase_source,
                    "status": status,
                    "notes": notes
                }
                add_inventory_item(user_id, item_data)
                st.success(f"✅ Added {brand} {model} Size {size} to inventory!")
                st.rerun()
            else:
                st.error("Please fill in all required fields (Brand, Model, Size)")

with tab3:
    st.subheader("Inventory Analytics")
    
    inventory = get_inventory(user_id)
    
    if inventory:
        df = pd.DataFrame(inventory)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", len(df))
        
        with col2:
            in_stock = len(df[df["status"] == "in_stock"])
            st.metric("In Stock", in_stock)
        
        with col3:
            listed = len(df[df["status"] == "listed"])
            st.metric("Listed", listed)
        
        with col4:
            sold = len(df[df["status"] == "sold"])
            st.metric("Sold", sold)
        
        st.subheader("Inventory by Brand")
        brand_counts = df["brand"].value_counts()
        st.bar_chart(brand_counts)
        
        st.subheader("Inventory Value")
        total_value = df["purchase_price"].sum()
        st.metric("Total Purchase Value", f"${total_value:,.2f}" if total_value else "$0.00")
    else:
        st.info("No inventory data to analyze yet.")