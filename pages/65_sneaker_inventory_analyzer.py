import streamlit as st
import json
import datetime
from datetime import timedelta
import requests
from decimal import Decimal
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Sneaker Inventory Analyzer", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS sneaker_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                condition TEXT DEFAULT 'New',
                cogs DECIMAL(10,2) DEFAULT 0,
                purchase_date DATE,
                purchase_source TEXT,
                notes TEXT,
                status TEXT DEFAULT 'in_stock',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_listings (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES sneaker_inventory(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                listing_id TEXT,
                listing_url TEXT,
                current_price DECIMAL(10,2),
                original_price DECIMAL(10,2),
                listed_date DATE,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                offers_received INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_price_history (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER REFERENCES platform_listings(id) ON DELETE CASCADE,
                price DECIMAL(10,2) NOT NULL,
                change_reason TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_sales (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES sneaker_inventory(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                sale_price DECIMAL(10,2) NOT NULL,
                platform_fees DECIMAL(10,2) DEFAULT 0,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                net_profit DECIMAL(10,2),
                sale_date DATE,
                days_to_sell INTEGER,
                buyer_location TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER REFERENCES sneaker_inventory(id) ON DELETE CASCADE,
                alert_type TEXT NOT NULL,
                message TEXT,
                is_sent BOOLEAN DEFAULT FALSE,
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                condition TEXT DEFAULT 'New',
                cogs REAL DEFAULT 0,
                purchase_date TEXT,
                purchase_source TEXT,
                notes TEXT,
                status TEXT DEFAULT 'in_stock',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER REFERENCES sneaker_inventory(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                listing_id TEXT,
                listing_url TEXT,
                current_price REAL,
                original_price REAL,
                listed_date TEXT,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                offers_received INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER REFERENCES platform_listings(id) ON DELETE CASCADE,
                price REAL NOT NULL,
                change_reason TEXT,
                changed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER REFERENCES sneaker_inventory(id) ON DELETE CASCADE,
                platform TEXT NOT NULL,
                sale_price REAL NOT NULL,
                platform_fees REAL DEFAULT 0,
                shipping_cost REAL DEFAULT 0,
                net_profit REAL,
                sale_date TEXT,
                days_to_sell INTEGER,
                buyer_location TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER REFERENCES sneaker_inventory(id) ON DELETE CASCADE,
                alert_type TEXT NOT NULL,
                message TEXT,
                is_sent INTEGER DEFAULT 0,
                sent_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

# Sidebar
with st.sidebar:
    render_sidebar_brand()
    render_sidebar_user_widget()

st.title("👟 Sneaker Inventory Analyzer")
st.markdown("Track your sneaker inventory, listings, and sales across multiple platforms.")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "📊 Analytics", "💰 Sales", "⚙️ Settings"])

with tab1:
    st.subheader("Manage Inventory")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.expander("➕ Add New Sneaker", expanded=False):
            with st.form("add_sneaker_form"):
                sku = st.text_input("SKU *", placeholder="e.g., DQ7891-100")
                brand = st.selectbox("Brand", ["Nike", "Adidas", "Jordan", "New Balance", "Yeezy", "Other"])
                model = st.text_input("Model", placeholder="e.g., Air Jordan 1 Retro High OG")
                colorway = st.text_input("Colorway", placeholder="e.g., Chicago")
                size = st.text_input("Size", placeholder="e.g., 10.5")
                condition = st.selectbox("Condition", ["New", "Used - Like New", "Used - Good", "Used - Fair"])
                cogs = st.number_input("Cost of Goods (COGS)", min_value=0.0, step=0.01)
                purchase_date = st.date_input("Purchase Date", value=datetime.date.today())
                purchase_source = st.text_input("Purchase Source", placeholder="e.g., Nike SNKRS, StockX")
                notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Add Sneaker")
                
                if submitted:
                    if not sku:
                        st.error("SKU is required")
                    else:
                        conn = get_conn()
                        cur = conn.cursor()
                        user_id = st.session_state.get("user_id", 1)
                        
                        if USE_POSTGRES:
                            cur.execute("""
                                INSERT INTO sneaker_inventory 
                                (user_id, sku, brand, model, colorway, size, condition, cogs, purchase_date, purchase_source, notes)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (user_id, sku, brand, model, colorway, size, condition, cogs, purchase_date, purchase_source, notes))
                        else:
                            cur.execute("""
                                INSERT INTO sneaker_inventory 
                                (user_id, sku, brand, model, colorway, size, condition, cogs, purchase_date, purchase_source, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (user_id, sku, brand, model, colorway, size, condition, cogs, str(purchase_date), purchase_source, notes))
                        
                        conn.commit()
                        st.success(f"🎉 Added {model} ({sku}) to inventory!")
                        st.rerun()
    
    # Display inventory
    st.subheader("Current Inventory")
    
    conn = get_conn()
    cur = conn.cursor()
    user_id = st.session_state.get("user_id", 1)
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, sku, brand, model, colorway, size, condition, cogs, purchase_date, purchase_source, status, notes
            FROM sneaker_inventory
            WHERE user_id = %s AND status = 'in_stock'
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cur.execute("""
            SELECT id, sku, brand, model, colorway, size, condition, cogs, purchase_date, purchase_source, status, notes
            FROM sneaker_inventory
            WHERE user_id = ? AND status = 'in_stock'
            ORDER BY created_at DESC
        """, (user_id,))
    
    inventory = cur.fetchall()
    
    if inventory:
        df = pd.DataFrame(inventory, columns=["ID", "SKU", "Brand", "Model", "Colorway", "Size", "Condition", "COGS", "Purchase Date", "Source", "Status", "Notes"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No sneakers in inventory yet. Add your first pair above!")

with tab2:
    st.subheader("Inventory Analytics")
    
    conn = get_conn()
    cur = conn.cursor()
    user_id = st.session_state.get("user_id", 1)
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT brand, COUNT(*) as count, SUM(cogs) as total_cogs
            FROM sneaker_inventory
            WHERE user_id = %s
            GROUP BY brand
        """, (user_id,))
    else:
        cur.execute("""
            SELECT brand, COUNT(*) as count, SUM(cogs) as total_cogs
            FROM sneaker_inventory
            WHERE user_id = ?
            GROUP BY brand
        """, (user_id,))
    
    brand_data = cur.fetchall()
    
    if brand_data:
        df_brands = pd.DataFrame(brand_data, columns=["Brand", "Count", "Total COGS"])
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(df_brands, values="Count", names="Brand", title="Inventory by Brand")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(df_brands, x="Brand", y="Total COGS", title="COGS by Brand")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add some inventory to see analytics!")

with tab3:
    st.subheader("Sales Tracking")
    
    with st.expander("📝 Record a Sale", expanded=False):
        conn = get_conn()
        cur = conn.cursor()
        user_id = st.session_state.get("user_id", 1)
        
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, sku, model, size FROM sneaker_inventory
                WHERE user_id = %s AND status = 'in_stock'
            """, (user_id,))
        else:
            cur.execute("""
                SELECT id, sku, model, size FROM sneaker_inventory
                WHERE user_id = ? AND status = 'in_stock'
            """, (user_id,))
        
        available_items = cur.fetchall()
        
        if available_items:
            item_options = {f"{item[2]} ({item[1]}) - Size {item[3]}": item[0] for item in available_items}
            
            with st.form("record_sale_form"):
                selected_item = st.selectbox("Select Item", list(item_options.keys()))
                platform = st.selectbox("Platform", ["StockX", "GOAT", "eBay", "Grailed", "Poshmark", "Mercari", "Local", "Other"])
                sale_price = st.number_input("Sale Price", min_value=0.0, step=0.01)
                platform_fees = st.number_input("Platform Fees", min_value=0.0, step=0.01)
                shipping_cost = st.number_input("Shipping Cost", min_value=0.0, step=0.01)
                sale_date = st.date_input("Sale Date", value=datetime.date.today())
                
                if st.form_submit_button("Record Sale"):
                    inventory_id = item_options[selected_item]
                    
                    if USE_POSTGRES:
                        cur.execute("SELECT cogs, purchase_date FROM sneaker_inventory WHERE id = %s", (inventory_id,))
                    else:
                        cur.execute("SELECT cogs, purchase_date FROM sneaker_inventory WHERE id = ?", (inventory_id,))
                    
                    item_data = cur.fetchone()
                    cogs = float(item_data[0]) if item_data[0] else 0
                    net_profit = sale_price - platform_fees - shipping_cost - cogs
                    
                    purchase_date_val = item_data[1]
                    if purchase_date_val:
                        if isinstance(purchase_date_val, str):
                            purchase_date_val = datetime.datetime.strptime(purchase_date_val, "%Y-%m-%d").date()
                        days_to_sell = (sale_date - purchase_date_val).days
                    else:
                        days_to_sell = 0
                    
                    if USE_POSTGRES:
                        cur.execute("""
                            INSERT INTO inventory_sales 
                            (inventory_id, platform, sale_price, platform_fees, shipping_cost, net_profit, sale_date, days_to_sell)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (inventory_id, platform, sale_price, platform_fees, shipping_cost, net_profit, sale_date, days_to_sell))
                        
                        cur.execute("UPDATE sneaker_inventory SET status = 'sold' WHERE id = %s", (inventory_id,))
                    else:
                        cur.execute("""
                            INSERT INTO inventory_sales 
                            (inventory_id, platform, sale_price, platform_fees, shipping_cost, net_profit, sale_date, days_to_sell)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (inventory_id, platform, sale_price, platform_fees, shipping_cost, net_profit, str(sale_date), days_to_sell))
                        
                        cur.execute("UPDATE sneaker_inventory SET status = 'sold' WHERE id = ?", (inventory_id,))
                    
                    conn.commit()
                    st.success(f"🎉 Sale recorded! Net profit: ${net_profit:.2f}")
                    st.rerun()
        else:
            st.info("No items available to sell. Add inventory first!")
    
    # Display sales history
    st.subheader("Sales History")
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT s.sale_date, i.model, i.sku, i.size, s.platform, s.sale_price, s.platform_fees, s.shipping_cost, s.net_profit, s.days_to_sell
            FROM inventory_sales s
            JOIN sneaker_inventory i ON s.inventory_id = i.id
            WHERE i.user_id = %s
            ORDER BY s.sale_date DESC
        """, (user_id,))
    else:
        cur.execute("""
            SELECT s.sale_date, i.model, i.sku, i.size, s.platform, s.sale_price, s.platform_fees, s.shipping_cost, s.net_profit, s.days_to_sell
            FROM inventory_sales s
            JOIN sneaker_inventory i ON s.inventory_id = i.id
            WHERE i.user_id = ?
            ORDER BY s.sale_date DESC
        """, (user_id,))
    
    sales = cur.fetchall()
    
    if sales:
        df_sales = pd.DataFrame(sales, columns=["Date", "Model", "SKU", "Size", "Platform", "Sale Price", "Fees", "Shipping", "Net Profit", "Days to Sell"])
        st.dataframe(df_sales, use_container_width=True, hide_index=True)
        
        total_profit = sum(float(s[8]) if s[8] else 0 for s in sales)
        total_sales = sum(float(s[5]) if s[5] else 0 for s in sales)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sales", f"${total_sales:.2f}")
        col2.metric("Total Profit", f"${total_profit:.2f}")
        col3.metric("Items Sold", len(sales))
    else:
        st.info("No sales recorded yet.")

with tab4:
    st.subheader("Settings")
    st.info("Settings coming soon - configure platforms, alerts, and more!")