import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from decimal import Decimal
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Sole PnL Dashboard", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
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
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_inventory_pl (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100),
                brand VARCHAR(100),
                model VARCHAR(255),
                colorway VARCHAR(255),
                size VARCHAR(20),
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                source VARCHAR(100),
                condition VARCHAR(50),
                notes TEXT,
                status VARCHAR(50) DEFAULT 'in_stock',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_sales_pl (
                id SERIAL PRIMARY KEY,
                inventory_id INTEGER REFERENCES sneaker_inventory_pl(id),
                sale_price DECIMAL(10,2),
                platform VARCHAR(50),
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                platform_fee DECIMAL(10,2) DEFAULT 0,
                payment_processing_fee DECIMAL(10,2) DEFAULT 0,
                other_fees DECIMAL(10,2) DEFAULT 0,
                sale_date DATE,
                buyer_location VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_fee_config (
                id SERIAL PRIMARY KEY,
                platform VARCHAR(50) UNIQUE,
                base_fee_percent DECIMAL(5,2),
                payment_processing_percent DECIMAL(5,2),
                flat_fee DECIMAL(10,2) DEFAULT 0,
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_expenses_pl (
                id SERIAL PRIMARY KEY,
                expense_type VARCHAR(100),
                amount DECIMAL(10,2),
                expense_date DATE,
                description TEXT,
                receipt_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default platform fees if not exists
        cur.execute("""
            INSERT INTO platform_fee_config (platform, base_fee_percent, payment_processing_percent, flat_fee, notes)
            VALUES 
                ('eBay', 13.25, 0, 0.30, 'Standard eBay seller fee + payment processing'),
                ('Mercari', 10.0, 0, 0, 'Flat 10%% seller fee'),
                ('StockX', 9.5, 3.0, 0, 'Transaction fee + payment processing'),
                ('GOAT', 9.5, 2.9, 0, 'Commission + payment processing'),
                ('Facebook Marketplace', 5.0, 0, 0, 'Shipping label fee only'),
                ('OfferUp', 0, 0, 0, 'Local sales - no fees'),
                ('Direct/Cash', 0, 0, 0, 'Direct sale - no fees')
            ON CONFLICT (platform) DO NOTHING
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_inventory_pl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                purchase_price REAL,
                purchase_date TEXT,
                source TEXT,
                condition TEXT,
                notes TEXT,
                status TEXT DEFAULT 'in_stock',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_sales_pl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                sale_price REAL,
                platform TEXT,
                shipping_cost REAL DEFAULT 0,
                platform_fee REAL DEFAULT 0,
                payment_processing_fee REAL DEFAULT 0,
                other_fees REAL DEFAULT 0,
                sale_date TEXT,
                buyer_location TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_fee_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT UNIQUE,
                base_fee_percent REAL,
                payment_processing_percent REAL,
                flat_fee REAL DEFAULT 0,
                notes TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_expenses_pl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_type TEXT,
                amount REAL,
                expense_date TEXT,
                description TEXT,
                receipt_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default platform fees for SQLite
        platforms = [
            ('eBay', 13.25, 0, 0.30, 'Standard eBay seller fee + payment processing'),
            ('Mercari', 10.0, 0, 0, 'Flat 10% seller fee'),
            ('StockX', 9.5, 3.0, 0, 'Transaction fee + payment processing'),
            ('GOAT', 9.5, 2.9, 0, 'Commission + payment processing'),
            ('Facebook Marketplace', 5.0, 0, 0, 'Shipping label fee only'),
            ('OfferUp', 0, 0, 0, 'Local sales - no fees'),
            ('Direct/Cash', 0, 0, 0, 'Direct sale - no fees')
        ]
        for platform in platforms:
            cur.execute("""
                INSERT OR IGNORE INTO platform_fee_config (platform, base_fee_percent, payment_processing_percent, flat_fee, notes)
                VALUES (?, ?, ?, ?, ?)
            """, platform)
    
    conn.commit()

_ensure_tables()

st.title("🍑 Sole PnL Dashboard")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📦 Inventory", "💰 Sales", "💸 Expenses", "⚙️ Settings"])

with tab1:
    st.header("Profit & Loss Overview")
    
    conn = get_conn()
    
    # Get summary stats
    if USE_POSTGRES:
        inventory_df = pd.read_sql("SELECT * FROM sneaker_inventory_pl", conn)
        sales_df = pd.read_sql("SELECT * FROM sneaker_sales_pl", conn)
        expenses_df = pd.read_sql("SELECT * FROM sneaker_expenses_pl", conn)
    else:
        inventory_df = pd.read_sql("SELECT * FROM sneaker_inventory_pl", conn)
        sales_df = pd.read_sql("SELECT * FROM sneaker_sales_pl", conn)
        expenses_df = pd.read_sql("SELECT * FROM sneaker_expenses_pl", conn)
    
    # Calculate metrics
    total_inventory_cost = inventory_df['purchase_price'].sum() if not inventory_df.empty else 0
    total_revenue = sales_df['sale_price'].sum() if not sales_df.empty else 0
    total_fees = (sales_df['platform_fee'].sum() + sales_df['payment_processing_fee'].sum() + 
                  sales_df['shipping_cost'].sum() + sales_df['other_fees'].sum()) if not sales_df.empty else 0
    total_expenses = expenses_df['amount'].sum() if not expenses_df.empty else 0
    
    # Get COGS for sold items
    if not sales_df.empty:
        sold_inventory_ids = sales_df['inventory_id'].tolist()
        sold_items = inventory_df[inventory_df['id'].isin(sold_inventory_ids)]
        cogs = sold_items['purchase_price'].sum()
    else:
        cogs = 0
    
    gross_profit = total_revenue - cogs - total_fees
    net_profit = gross_profit - total_expenses
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    with col2:
        st.metric("COGS", f"${cogs:,.2f}")
    with col3:
        st.metric("Gross Profit", f"${gross_profit:,.2f}")
    with col4:
        st.metric("Net Profit", f"${net_profit:,.2f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Inventory Status")
        if not inventory_df.empty:
            status_counts = inventory_df['status'].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index, title="Inventory by Status")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No inventory data yet")
    
    with col2:
        st.subheader("Sales by Platform")
        if not sales_df.empty:
            platform_sales = sales_df.groupby('platform')['sale_price'].sum().reset_index()
            fig = px.bar(platform_sales, x='platform', y='sale_price', title="Revenue by Platform")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales data yet")

with tab2:
    st.header("📦 Inventory Management")
    
    with st.expander("➕ Add New Inventory Item", expanded=False):
        with st.form("add_inventory"):
            col1, col2, col3 = st.columns(3)
            with col1:
                sku = st.text_input("SKU")
                brand = st.text_input("Brand")
                model = st.text_input("Model")
            with col2:
                colorway = st.text_input("Colorway")
                size = st.text_input("Size")
                purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
            with col3:
                purchase_date = st.date_input("Purchase Date")
                source = st.text_input("Source")
                condition = st.selectbox("Condition", ["New", "Used - Like New", "Used - Good", "Used - Fair"])
            
            notes = st.text_area("Notes")
            
            if st.form_submit_button("Add Item"):
                conn = get_conn()
                cur = conn.cursor()
                if USE_POSTGRES:
                    cur.execute("""
                        INSERT INTO sneaker_inventory_pl (sku, brand, model, colorway, size, purchase_price, purchase_date, source, condition, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (sku, brand, model, colorway, size, purchase_price, purchase_date, source, condition, notes))
                else:
                    cur.execute("""
                        INSERT INTO sneaker_inventory_pl (sku, brand, model, colorway, size, purchase_price, purchase_date, source, condition, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (sku, brand, model, colorway, size, purchase_price, str(purchase_date), source, condition, notes))
                conn.commit()
                st.success("Item added successfully!")
                st.rerun()
    
    # Display inventory
    conn = get_conn()
    inventory_df = pd.read_sql("SELECT * FROM sneaker_inventory_pl ORDER BY created_at DESC", conn)
    
    if not inventory_df.empty:
        st.dataframe(inventory_df, use_container_width=True)
    else:
        st.info("No inventory items yet. Add your first item above!")

with tab3:
    st.header("💰 Sales Management")
    
    conn = get_conn()
    available_inventory = pd.read_sql("SELECT * FROM sneaker_inventory_pl WHERE status = 'in_stock'", conn)
    
    with st.expander("➕ Record New Sale", expanded=False):
        if not available_inventory.empty:
            with st.form("add_sale"):
                inventory_options = {f"{row['brand']} {row['model']} - Size {row['size']} (${row['purchase_price']})": row['id'] 
                                    for _, row in available_inventory.iterrows()}
                
                selected_item = st.selectbox("Select Item", list(inventory_options.keys()))
                
                col1, col2 = st.columns(2)
                with col1:
                    sale_price = st.number_input("Sale Price ($)", min_value=0.0, step=0.01)
                    platform = st.selectbox("Platform", ["eBay", "Mercari", "StockX", "GOAT", "Facebook Marketplace", "OfferUp", "Direct/Cash"])
                    sale_date = st.date_input("Sale Date")
                with col2:
                    shipping_cost = st.number_input("Shipping Cost ($)", min_value=0.0, step=0.01)
                    platform_fee = st.number_input("Platform Fee ($)", min_value=0.0, step=0.01)
                    payment_processing_fee = st.number_input("Payment Processing Fee ($)", min_value=0.0, step=0.01)
                
                other_fees = st.number_input("Other Fees ($)", min_value=0.0, step=0.01)
                buyer_location = st.text_input("Buyer Location")
                notes = st.text_area("Notes")
                
                if st.form_submit_button("Record Sale"):
                    inventory_id = inventory_options[selected_item]
                    conn = get_conn()
                    cur = conn.cursor()
                    
                    if USE_POSTGRES:
                        cur.execute("""
                            INSERT INTO sneaker_sales_pl (inventory_id, sale_price, platform, shipping_cost, platform_fee, payment_processing_fee, other_fees, sale_date, buyer_location, notes)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (inventory_id, sale_price, platform, shipping_cost, platform_fee, payment_processing_fee, other_fees, sale_date, buyer_location, notes))
                        cur.execute("UPDATE sneaker_inventory_pl SET status = 'sold' WHERE id = %s", (inventory_id,))
                    else:
                        cur.execute("""
                            INSERT INTO sneaker_sales_pl (inventory_id, sale_price, platform, shipping_cost, platform_fee, payment_processing_fee, other_fees, sale_date, buyer_location, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (inventory_id, sale_price, platform, shipping_cost, platform_fee, payment_processing_fee, other_fees, str(sale_date), buyer_location, notes))
                        cur.execute("UPDATE sneaker_inventory_pl SET status = 'sold' WHERE id = ?", (inventory_id,))
                    
                    conn.commit()
                    st.success("Sale recorded successfully!")
                    st.rerun()
        else:
            st.warning("No items available for sale. Add inventory first!")
    
    # Display sales
    sales_df = pd.read_sql("SELECT * FROM sneaker_sales_pl ORDER BY created_at DESC", conn)
    
    if not sales_df.empty:
        st.dataframe(sales_df, use_container_width=True)
    else:
        st.info("No sales recorded yet.")

with tab4:
    st.header("💸 Expenses")
    
    with st.expander("➕ Add Expense", expanded=False):
        with st.form("add_expense"):
            col1, col2 = st.columns(2)
            with col1:
                expense_type = st.selectbox("Expense Type", ["Shipping Supplies", "Storage", "Travel", "Marketing", "Software/Tools", "Other"])
                amount = st.number_input("Amount ($)", min_value=0.0, step=0.01)
            with col2:
                expense_date = st.date_input("Date")
                description = st.text_input("Description")
            
            if st.form_submit_button("Add Expense"):
                conn = get_conn()
                cur = conn.cursor()
                if USE_POSTGRES:
                    cur.execute("""
                        INSERT INTO sneaker_expenses_pl (expense_type, amount, expense_date, description)
                        VALUES (%s, %s, %s, %s)
                    """, (expense_type, amount, expense_date, description))
                else:
                    cur.execute("""
                        INSERT INTO sneaker_expenses_pl (expense_type, amount, expense_date, description)
                        VALUES (?, ?, ?, ?)
                    """, (expense_type, amount, str(expense_date), description))
                conn.commit()
                st.success("Expense added!")
                st.rerun()
    
    conn = get_conn()
    expenses_df = pd.read_sql("SELECT * FROM sneaker_expenses_pl ORDER BY expense_date DESC", conn)
    
    if not expenses_df.empty:
        st.dataframe(expenses_df, use_container_width=True)
    else:
        st.info("No expenses recorded yet.")

with tab5:
    st.header("⚙️ Platform Fee Configuration")
    
    conn = get_conn()
    fees_df = pd.read_sql("SELECT * FROM platform_fee_config", conn)
    
    if not fees_df.empty:
        st.dataframe(fees_df, use_container_width=True)
    
    st.info("Platform fees are used to estimate costs when recording sales.")