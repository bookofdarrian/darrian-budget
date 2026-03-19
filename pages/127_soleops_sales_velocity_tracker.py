import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Sales Velocity Tracker", page_icon="🍑", layout="wide")

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


def _ensure_tables():
    """Create sales velocity table if not exists"""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sales_velocity (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                list_date DATE NOT NULL,
                sold_date DATE,
                days_to_sell INTEGER,
                list_price DECIMAL(10,2) NOT NULL,
                sold_price DECIMAL(10,2),
                size VARCHAR(20),
                brand VARCHAR(100),
                model VARCHAR(200),
                condition VARCHAR(50) DEFAULT 'New',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_velocity_thresholds (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                fast_mover_days INTEGER DEFAULT 7,
                slow_mover_days INTEGER DEFAULT 30,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sales_velocity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                list_date DATE NOT NULL,
                sold_date DATE,
                days_to_sell INTEGER,
                list_price REAL NOT NULL,
                sold_price REAL,
                size TEXT,
                brand TEXT,
                model TEXT,
                condition TEXT DEFAULT 'New',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_velocity_thresholds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                fast_mover_days INTEGER DEFAULT 7,
                slow_mover_days INTEGER DEFAULT 30,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_user_thresholds(user_id: int) -> Dict[str, int]:
    """Get user's velocity thresholds"""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT fast_mover_days, slow_mover_days FROM soleops_velocity_thresholds WHERE user_id = {ph}", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {"fast_mover_days": row[0], "slow_mover_days": row[1]}
    return {"fast_mover_days": 7, "slow_mover_days": 30}


def set_user_thresholds(user_id: int, fast_days: int, slow_days: int):
    """Set user's velocity thresholds"""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO soleops_velocity_thresholds (user_id, fast_mover_days, slow_mover_days, updated_at)
            VALUES ({ph}, {ph}, {ph}, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                fast_mover_days = EXCLUDED.fast_mover_days,
                slow_mover_days = EXCLUDED.slow_mover_days,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, fast_days, slow_days))
    else:
        cur.execute(f"SELECT id FROM soleops_velocity_thresholds WHERE user_id = {ph}", (user_id,))
        if cur.fetchone():
            cur.execute(f"""
                UPDATE soleops_velocity_thresholds 
                SET fast_mover_days = {ph}, slow_mover_days = {ph}, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = {ph}
            """, (fast_days, slow_days, user_id))
        else:
            cur.execute(f"""
                INSERT INTO soleops_velocity_thresholds (user_id, fast_mover_days, slow_mover_days)
                VALUES ({ph}, {ph}, {ph})
            """, (user_id, fast_days, slow_days))
    
    conn.commit()
    conn.close()


def add_listing(user_id: int, sku: str, platform: str, list_date: datetime, list_price: float,
                size: str = None, brand: str = None, model: str = None, condition: str = "New", notes: str = None):
    """Add a new listing"""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_sales_velocity (user_id, sku, platform, list_date, list_price, size, brand, model, condition, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, sku, platform, list_date, list_price, size, brand, model, condition, notes))
    
    conn.commit()
    conn.close()


def mark_as_sold(listing_id: int, sold_date: datetime, sold_price: float):
    """Mark a listing as sold"""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    # Get list_date to calculate days_to_sell
    cur.execute(f"SELECT list_date FROM soleops_sales_velocity WHERE id = {ph}", (listing_id,))
    row = cur.fetchone()
    if row:
        list_date = row[0]
        if isinstance(list_date, str):
            list_date = datetime.strptime(list_date, "%Y-%m-%d").date()
        days_to_sell = (sold_date - list_date).days
        
        cur.execute(f"""
            UPDATE soleops_sales_velocity 
            SET sold_date = {ph}, sold_price = {ph}, days_to_sell = {ph}
            WHERE id = {ph}
        """, (sold_date, sold_price, days_to_sell, listing_id))
    
    conn.commit()
    conn.close()


def get_listings(user_id: int, sold_only: bool = False, active_only: bool = False) -> pd.DataFrame:
    """Get listings for user"""
    conn = get_conn()
    
    ph = "%s" if USE_POSTGRES else "?"
    query = f"SELECT * FROM soleops_sales_velocity WHERE user_id = {ph}"
    
    if sold_only:
        query += " AND sold_date IS NOT NULL"
    elif active_only:
        query += " AND sold_date IS NULL"
    
    query += " ORDER BY created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df


def delete_listing(listing_id: int):
    """Delete a listing"""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_sales_velocity WHERE id = {ph}", (listing_id,))
    
    conn.commit()
    conn.close()


# Initialize tables
_ensure_tables()

# Main UI
st.title("🍑 SoleOps Sales Velocity Tracker")
st.markdown("Track how fast your inventory sells across platforms")

user_id = st.session_state.get("user_id", 1)
thresholds = get_user_thresholds(user_id)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Add Listing", "📦 Inventory", "⚙️ Settings"])

with tab1:
    st.subheader("Sales Velocity Dashboard")
    
    sold_df = get_listings(user_id, sold_only=True)
    active_df = get_listings(user_id, active_only=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Listings", len(active_df))
    
    with col2:
        st.metric("Total Sold", len(sold_df))
    
    with col3:
        if len(sold_df) > 0:
            avg_days = sold_df["days_to_sell"].mean()
            st.metric("Avg Days to Sell", f"{avg_days:.1f}")
        else:
            st.metric("Avg Days to Sell", "N/A")
    
    with col4:
        if len(sold_df) > 0:
            total_profit = (sold_df["sold_price"] - sold_df["list_price"]).sum()
            st.metric("Total Profit", f"${total_profit:.2f}")
        else:
            st.metric("Total Profit", "$0.00")
    
    if len(sold_df) > 0:
        st.subheader("Sales Velocity by Platform")
        platform_stats = sold_df.groupby("platform").agg({
            "days_to_sell": "mean",
            "id": "count",
            "sold_price": "sum"
        }).reset_index()
        platform_stats.columns = ["Platform", "Avg Days to Sell", "Items Sold", "Total Revenue"]
        
        fig = px.bar(platform_stats, x="Platform", y="Avg Days to Sell", 
                     title="Average Days to Sell by Platform",
                     color="Avg Days to Sell",
                     color_continuous_scale=["green", "yellow", "red"])
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(platform_stats, use_container_width=True)

with tab2:
    st.subheader("Add New Listing")
    
    with st.form("add_listing_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            sku = st.text_input("SKU *", placeholder="e.g., NIKE-AJ1-001")
            platform = st.selectbox("Platform *", ["StockX", "GOAT", "eBay", "Poshmark", "Mercari", "Depop", "Grailed", "Other"])
            list_date = st.date_input("List Date *", value=datetime.now().date())
            list_price = st.number_input("List Price ($) *", min_value=0.01, step=0.01)
        
        with col2:
            brand = st.text_input("Brand", placeholder="e.g., Nike")
            model = st.text_input("Model", placeholder="e.g., Air Jordan 1 Retro High OG")
            size = st.text_input("Size", placeholder="e.g., 10.5")
            condition = st.selectbox("Condition", ["New", "Like New", "Good", "Fair", "Poor"])
        
        notes = st.text_area("Notes", placeholder="Any additional notes...")
        
        submitted = st.form_submit_button("Add Listing", type="primary")
        
        if submitted:
            if sku and platform and list_price:
                add_listing(user_id, sku, platform, list_date, list_price, size, brand, model, condition, notes)
                st.success("Listing added successfully!")
                st.rerun()
            else:
                st.error("Please fill in all required fields (SKU, Platform, List Price)")

with tab3:
    st.subheader("Inventory Management")
    
    view_option = st.radio("View", ["Active Listings", "Sold Items", "All"], horizontal=True)
    
    if view_option == "Active Listings":
        df = get_listings(user_id, active_only=True)
    elif view_option == "Sold Items":
        df = get_listings(user_id, sold_only=True)
    else:
        df = get_listings(user_id)
    
    if len(df) > 0:
        for idx, row in df.iterrows():
            with st.expander(f"{row['sku']} - {row['platform']} - ${row['list_price']:.2f}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Brand:** {row['brand'] or 'N/A'}")
                    st.write(f"**Model:** {row['model'] or 'N/A'}")
                    st.write(f"**Size:** {row['size'] or 'N/A'}")
                
                with col2:
                    st.write(f"**Condition:** {row['condition']}")
                    st.write(f"**List Date:** {row['list_date']}")
                    if row['sold_date']:
                        st.write(f"**Sold Date:** {row['sold_date']}")
                        st.write(f"**Days to Sell:** {row['days_to_sell']}")
                
                with col3:
                    st.write(f"**List Price:** ${row['list_price']:.2f}")
                    if row['sold_price']:
                        st.write(f"**Sold Price:** ${row['sold_price']:.2f}")
                        profit = row['sold_price'] - row['list_price']
                        st.write(f"**Profit:** ${profit:.2f}")
                
                if not row['sold_date']:
                    st.markdown("---")
                    st.write("**Mark as Sold**")
                    sold_col1, sold_col2, sold_col3 = st.columns(3)
                    with sold_col1:
                        sold_date = st.date_input("Sold Date", value=datetime.now().date(), key=f"sold_date_{row['id']}")
                    with sold_col2:
                        sold_price = st.number_input("Sold Price ($)", min_value=0.01, value=float(row['list_price']), key=f"sold_price_{row['id']}")
                    with sold_col3:
                        if st.button("Mark Sold", key=f"mark_sold_{row['id']}"):
                            mark_as_sold(row['id'], sold_date, sold_price)
                            st.success("Marked as sold!")
                            st.rerun()
                
                if st.button("Delete", key=f"delete_{row['id']}", type="secondary"):
                    delete_listing(row['id'])
                    st.success("Listing deleted!")
                    st.rerun()
    else:
        st.info("No listings found. Add your first listing in the 'Add Listing' tab!")

with tab4:
    st.subheader("Settings")
    
    st.write("**Velocity Thresholds**")
    st.write("Define what constitutes fast and slow movers for your business.")
    
    with st.form("threshold_form"):
        fast_days = st.number_input("Fast Mover (days)", min_value=1, value=thresholds["fast_mover_days"],
                                    help="Items that sell within this many days are considered fast movers")
        slow_days = st.number_input("Slow Mover (days)", min_value=1, value=thresholds["slow_mover_days"],
                                    help="Items that take longer than this to sell are considered slow movers")
        
        if st.form_submit_button("Save Thresholds"):
            if fast_days >= slow_days:
                st.error("Fast mover days must be less than slow mover days")
            else:
                set_user_thresholds(user_id, fast_days, slow_days)
                st.success("Thresholds saved!")
                st.rerun()