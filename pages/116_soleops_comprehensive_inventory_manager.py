import streamlit as st
import pandas as pd
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
import io
import base64

st.set_page_config(page_title="SoleOps Comprehensive Inventory Manager", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS soleops_inventory_items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                brand VARCHAR(100),
                model VARCHAR(200),
                colorway VARCHAR(200),
                size VARCHAR(20),
                condition_grade VARCHAR(20) DEFAULT 'DS',
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                purchase_source VARCHAR(200),
                storage_location VARCHAR(200),
                listed_platforms TEXT,
                list_price DECIMAL(10,2),
                status VARCHAR(50) DEFAULT 'In Stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_photos (
                id SERIAL PRIMARY KEY,
                inventory_item_id INTEGER NOT NULL REFERENCES soleops_inventory_items(id) ON DELETE CASCADE,
                photo_url TEXT,
                photo_type VARCHAR(50) DEFAULT 'main',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                condition_grade TEXT DEFAULT 'DS',
                purchase_price REAL,
                purchase_date TEXT,
                purchase_source TEXT,
                storage_location TEXT,
                listed_platforms TEXT,
                list_price REAL,
                status TEXT DEFAULT 'In Stock',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_item_id INTEGER NOT NULL,
                photo_url TEXT,
                photo_type TEXT DEFAULT 'main',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventory_item_id) REFERENCES soleops_inventory_items(id) ON DELETE CASCADE
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

CONDITION_GRADES = {
    'DS': {'label': 'Deadstock (DS)', 'multiplier': 1.0, 'description': 'Brand new, never worn, with all original packaging'},
    'VNDS': {'label': 'Very Near Deadstock (VNDS)', 'multiplier': 0.90, 'description': 'Tried on once or twice, no visible wear'},
    'PADS': {'label': 'Pass as Deadstock (PADS)', 'multiplier': 0.80, 'description': 'Light wear, could pass as new'},
    'Used': {'label': 'Used', 'multiplier': 0.65, 'description': 'Visible wear, still in good condition'},
    'Beater': {'label': 'Beater', 'multiplier': 0.40, 'description': 'Heavy wear, budget option'}
}

STATUS_OPTIONS = ['In Stock', 'Listed', 'Pending Sale', 'Sold', 'Returned', 'Personal']

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_all_inventory(user_id, filters=None):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    query = f"SELECT * FROM soleops_inventory_items WHERE user_id = {ph}"
    params = [user_id]
    
    if filters:
        if filters.get('brand'):
            query += f" AND brand ILIKE {ph}" if USE_POSTGRES else f" AND brand LIKE {ph}"
            params.append(f"%{filters['brand']}%")
        if filters.get('status'):
            query += f" AND status = {ph}"
            params.append(filters['status'])
        if filters.get('condition_grade'):
            query += f" AND condition_grade = {ph}"
            params.append(filters['condition_grade'])
    
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def add_inventory_item(user_id, item_data):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO soleops_inventory_items 
        (user_id, sku, brand, model, colorway, size, condition_grade, purchase_price, 
         purchase_date, purchase_source, storage_location, listed_platforms, list_price, status, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, item_data.get('sku'), item_data.get('brand'), item_data.get('model'),
          item_data.get('colorway'), item_data.get('size'), item_data.get('condition_grade', 'DS'),
          item_data.get('purchase_price'), item_data.get('purchase_date'), item_data.get('purchase_source'),
          item_data.get('storage_location'), item_data.get('listed_platforms'), item_data.get('list_price'),
          item_data.get('status', 'In Stock'), item_data.get('notes')))
    
    conn.commit()
    conn.close()

def update_inventory_item(item_id, item_data):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        UPDATE soleops_inventory_items SET
        sku = {ph}, brand = {ph}, model = {ph}, colorway = {ph}, size = {ph},
        condition_grade = {ph}, purchase_price = {ph}, purchase_date = {ph},
        purchase_source = {ph}, storage_location = {ph}, listed_platforms = {ph},
        list_price = {ph}, status = {ph}, notes = {ph}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph}
    """, (item_data.get('sku'), item_data.get('brand'), item_data.get('model'),
          item_data.get('colorway'), item_data.get('size'), item_data.get('condition_grade'),
          item_data.get('purchase_price'), item_data.get('purchase_date'), item_data.get('purchase_source'),
          item_data.get('storage_location'), item_data.get('listed_platforms'), item_data.get('list_price'),
          item_data.get('status'), item_data.get('notes'), item_id))
    
    conn.commit()
    conn.close()

def delete_inventory_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_inventory_items WHERE id = {ph}", (item_id,))
    
    conn.commit()
    conn.close()

def display_inventory_card(item):
    with st.container():
        st.markdown(f"### {item.get('brand', 'N/A')} {item.get('model', 'N/A')}")
        st.markdown(f"**Colorway:** {item.get('colorway', 'N/A')}")
        st.markdown(f"**Size:** {item.get('size', 'N/A')}")
        st.markdown(f"**Condition:** {item.get('condition_grade', 'N/A')}")
        st.markdown(f"**Status:** {item.get('status', 'N/A')}")
        st.markdown(f"**Location:** {item.get('storage_location', 'N/A')}")
        
        purchase_price = item.get('purchase_price')
        list_price = item.get('list_price')
        
        if purchase_price:
            st.markdown(f"**Purchase Price:** ${purchase_price:.2f}")
        if list_price:
            st.markdown(f"**List Price:** ${list_price:.2f}")
        
        if purchase_price and list_price:
            profit = float(list_price) - float(purchase_price)
            st.markdown(f"**Potential Profit:** ${profit:.2f}")

# Main UI
st.title("🍑 SoleOps Comprehensive Inventory Manager")

user_id = get_user_id()

tab1, tab2, tab3 = st.tabs(["📦 Inventory", "➕ Add Item", "📊 Analytics"])

with tab1:
    st.subheader("Your Inventory")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_brand = st.text_input("Filter by Brand")
    with col2:
        filter_status = st.selectbox("Filter by Status", [""] + STATUS_OPTIONS)
    with col3:
        filter_condition = st.selectbox("Filter by Condition", [""] + list(CONDITION_GRADES.keys()))
    
    filters = {}
    if filter_brand:
        filters['brand'] = filter_brand
    if filter_status:
        filters['status'] = filter_status
    if filter_condition:
        filters['condition_grade'] = filter_condition
    
    inventory = get_all_inventory(user_id, filters if filters else None)
    
    if inventory:
        for item in inventory:
            with st.expander(f"{item.get('brand', 'N/A')} {item.get('model', 'N/A')} - Size {item.get('size', 'N/A')}"):
                display_inventory_card(item)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", key=f"edit_{item['id']}"):
                        st.session_state['editing_item'] = item
                with col2:
                    if st.button("Delete", key=f"delete_{item['id']}"):
                        delete_inventory_item(item['id'])
                        st.rerun()
    else:
        st.info("No inventory items found. Add some items to get started!")

with tab2:
    st.subheader("Add New Item")
    
    with st.form("add_item_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            brand = st.text_input("Brand")
            model = st.text_input("Model")
            colorway = st.text_input("Colorway")
            size = st.text_input("Size")
            sku = st.text_input("SKU")
        
        with col2:
            condition_grade = st.selectbox("Condition", list(CONDITION_GRADES.keys()))
            purchase_price = st.number_input("Purchase Price", min_value=0.0, step=0.01)
            purchase_date = st.date_input("Purchase Date")
            purchase_source = st.text_input("Purchase Source")
            storage_location = st.text_input("Storage Location")
        
        list_price = st.number_input("List Price", min_value=0.0, step=0.01)
        status = st.selectbox("Status", STATUS_OPTIONS)
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("Add Item")
        
        if submitted:
            item_data = {
                'brand': brand,
                'model': model,
                'colorway': colorway,
                'size': size,
                'sku': sku,
                'condition_grade': condition_grade,
                'purchase_price': purchase_price,
                'purchase_date': purchase_date.isoformat() if purchase_date else None,
                'purchase_source': purchase_source,
                'storage_location': storage_location,
                'list_price': list_price,
                'status': status,
                'notes': notes
            }
            add_inventory_item(user_id, item_data)
            st.success("Item added successfully!")
            st.rerun()

with tab3:
    st.subheader("Inventory Analytics")
    
    all_inventory = get_all_inventory(user_id)
    
    if all_inventory:
        df = pd.DataFrame(all_inventory)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", len(df))
        
        with col2:
            total_cost = df['purchase_price'].sum() if 'purchase_price' in df.columns else 0
            st.metric("Total Investment", f"${total_cost:.2f}")
        
        with col3:
            total_list = df['list_price'].sum() if 'list_price' in df.columns else 0
            st.metric("Total List Value", f"${total_list:.2f}")
        
        with col4:
            potential_profit = total_list - total_cost
            st.metric("Potential Profit", f"${potential_profit:.2f}")
        
        st.markdown("### Status Breakdown")
        if 'status' in df.columns:
            status_counts = df['status'].value_counts()
            st.bar_chart(status_counts)
        
        st.markdown("### Brand Breakdown")
        if 'brand' in df.columns:
            brand_counts = df['brand'].value_counts()
            st.bar_chart(brand_counts)
    else:
        st.info("No inventory data to analyze yet.")