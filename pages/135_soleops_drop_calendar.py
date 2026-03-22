import streamlit as st
import datetime
import json
import requests
from typing import Optional, List, Dict, Any
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Drop Calendar", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_drops (
                id SERIAL PRIMARY KEY,
                shoe_name TEXT NOT NULL,
                brand TEXT NOT NULL,
                colorway TEXT,
                retail_price DECIMAL(10,2),
                release_date DATE NOT NULL,
                release_time TIME,
                retailer TEXT,
                predicted_resale DECIMAL(10,2),
                watchlist BOOLEAN DEFAULT FALSE,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_drop_alerts (
                id SERIAL PRIMARY KEY,
                drop_id INTEGER REFERENCES soleops_drops(id) ON DELETE CASCADE,
                alert_type TEXT NOT NULL,
                alert_time TIMESTAMP NOT NULL,
                sent_at TIMESTAMP,
                user_id TEXT NOT NULL
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_name TEXT NOT NULL,
                brand TEXT NOT NULL,
                colorway TEXT,
                retail_price REAL,
                release_date DATE NOT NULL,
                release_time TEXT,
                retailer TEXT,
                predicted_resale REAL,
                watchlist INTEGER DEFAULT 0,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_drop_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drop_id INTEGER REFERENCES soleops_drops(id) ON DELETE CASCADE,
                alert_type TEXT NOT NULL,
                alert_time TIMESTAMP NOT NULL,
                sent_at TIMESTAMP,
                user_id TEXT NOT NULL
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

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

# Get current user
user_id = st.session_state.get("user_id", "default_user")

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def get_all_drops(user_id: str, filters: Dict = None) -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    query = f"SELECT * FROM soleops_drops WHERE user_id = {ph}"
    params = [user_id]
    
    if filters:
        if filters.get("brand"):
            query += f" AND brand = {ph}"
            params.append(filters["brand"])
        if filters.get("min_price") is not None:
            query += f" AND retail_price >= {ph}"
            params.append(filters["min_price"])
        if filters.get("max_price") is not None:
            query += f" AND retail_price <= {ph}"
            params.append(filters["max_price"])
        if filters.get("watchlist_only"):
            if USE_POSTGRES:
                query += " AND watchlist = TRUE"
            else:
                query += " AND watchlist = 1"
        if filters.get("min_profit") is not None:
            query += f" AND (predicted_resale - retail_price) >= {ph}"
            params.append(filters["min_profit"])
    
    query += " ORDER BY release_date ASC"
    cur.execute(query, params)
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def get_drop_by_id(drop_id: int, user_id: str) -> Optional[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM soleops_drops WHERE id = {ph} AND user_id = {ph}", (drop_id, user_id))
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(zip(columns, row))
    return None

def add_drop(data: Dict, user_id: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO soleops_drops (shoe_name, brand, colorway, retail_price, release_date, release_time, retailer, predicted_resale, watchlist, user_id)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (data.get("shoe_name"), data.get("brand"), data.get("colorway"), data.get("retail_price"),
          data.get("release_date"), data.get("release_time"), data.get("retailer"), 
          data.get("predicted_resale"), data.get("watchlist", False), user_id))
    conn.commit()
    drop_id = cur.lastrowid
    conn.close()
    return drop_id

def update_drop(drop_id: int, data: Dict, user_id: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        UPDATE soleops_drops SET shoe_name = {ph}, brand = {ph}, colorway = {ph}, retail_price = {ph},
        release_date = {ph}, release_time = {ph}, retailer = {ph}, predicted_resale = {ph}, watchlist = {ph}
        WHERE id = {ph} AND user_id = {ph}
    """, (data.get("shoe_name"), data.get("brand"), data.get("colorway"), data.get("retail_price"),
          data.get("release_date"), data.get("release_time"), data.get("retailer"),
          data.get("predicted_resale"), data.get("watchlist", False), drop_id, user_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0

def delete_drop(drop_id: int, user_id: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM soleops_drops WHERE id = {ph} AND user_id = {ph}", (drop_id, user_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0

def toggle_watchlist(drop_id: int, user_id: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    if USE_POSTGRES:
        cur.execute(f"UPDATE soleops_drops SET watchlist = NOT watchlist WHERE id = {ph} AND user_id = {ph}", (drop_id, user_id))
    else:
        cur.execute(f"UPDATE soleops_drops SET watchlist = CASE WHEN watchlist = 1 THEN 0 ELSE 1 END WHERE id = {ph} AND user_id = {ph}", (drop_id, user_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0

# Main UI
st.title("🍑 SoleOps Drop Calendar")

tab1, tab2, tab3 = st.tabs(["📅 Calendar", "➕ Add Drop", "📊 Analytics"])

with tab1:
    st.subheader("Upcoming Drops")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        brand_filter = st.selectbox("Brand", ["All", "Nike", "Adidas", "Jordan", "New Balance", "Other"])
    with col2:
        min_price = st.number_input("Min Price", min_value=0, value=0)
    with col3:
        max_price = st.number_input("Max Price", min_value=0, value=1000)
    with col4:
        watchlist_only = st.checkbox("Watchlist Only")
    
    filters = {}
    if brand_filter != "All":
        filters["brand"] = brand_filter
    if min_price > 0:
        filters["min_price"] = min_price
    if max_price < 1000:
        filters["max_price"] = max_price
    if watchlist_only:
        filters["watchlist_only"] = True
    
    drops = get_all_drops(user_id, filters if filters else None)
    
    today = datetime.date.today()
    
    if drops:
        for drop in drops:
            release_date = drop.get("release_date")
            if isinstance(release_date, str):
                release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d").date()
            
            days_until = (release_date - today).days if release_date else 0
            
            with st.expander(f"**{drop.get('shoe_name')}** - {drop.get('brand')} | {release_date}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Colorway:** {drop.get('colorway', 'N/A')}")
                    st.write(f"**Retail:** ${drop.get('retail_price', 0):.2f}")
                with col2:
                    st.write(f"**Retailer:** {drop.get('retailer', 'N/A')}")
                    st.write(f"**Predicted Resale:** ${drop.get('predicted_resale', 0):.2f}")
                with col3:
                    if days_until > 0:
                        st.info(f"🗓️ {days_until} days until drop")
                    elif days_until == 0:
                        st.success("🔥 Dropping TODAY!")
                    else:
                        st.warning(f"📦 Dropped {abs(days_until)} days ago")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    watchlist_status = drop.get("watchlist")
                    if USE_POSTGRES:
                        is_watchlist = watchlist_status is True
                    else:
                        is_watchlist = watchlist_status == 1
                    
                    if st.button("⭐ Remove from Watchlist" if is_watchlist else "☆ Add to Watchlist", key=f"watch_{drop.get('id')}"):
                        toggle_watchlist(drop.get("id"), user_id)
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{drop.get('id')}"):
                        delete_drop(drop.get("id"), user_id)
                        st.rerun()
    else:
        st.info("No drops found. Add some drops to get started!")

with tab2:
    st.subheader("Add New Drop")
    
    with st.form("add_drop_form"):
        shoe_name = st.text_input("Shoe Name*")
        brand = st.selectbox("Brand*", ["Nike", "Adidas", "Jordan", "New Balance", "Other"])
        colorway = st.text_input("Colorway")
        retail_price = st.number_input("Retail Price ($)", min_value=0.0, step=10.0)
        release_date = st.date_input("Release Date*", min_value=datetime.date.today())
        release_time = st.time_input("Release Time")
        retailer = st.text_input("Retailer")
        predicted_resale = st.number_input("Predicted Resale ($)", min_value=0.0, step=10.0)
        add_to_watchlist = st.checkbox("Add to Watchlist")
        
        submitted = st.form_submit_button("Add Drop")
        
        if submitted:
            if shoe_name and brand:
                drop_data = {
                    "shoe_name": shoe_name,
                    "brand": brand,
                    "colorway": colorway,
                    "retail_price": retail_price,
                    "release_date": release_date,
                    "release_time": str(release_time) if release_time else None,
                    "retailer": retailer,
                    "predicted_resale": predicted_resale,
                    "watchlist": add_to_watchlist
                }
                add_drop(drop_data, user_id)
                st.success(f"Added {shoe_name} to your drop calendar!")
                st.rerun()
            else:
                st.error("Please fill in required fields (Shoe Name and Brand)")

with tab3:
    st.subheader("Drop Analytics")
    
    all_drops = get_all_drops(user_id)
    
    if all_drops:
        total_drops = len(all_drops)
        total_retail = sum(d.get("retail_price", 0) or 0 for d in all_drops)
        total_predicted = sum(d.get("predicted_resale", 0) or 0 for d in all_drops)
        potential_profit = total_predicted - total_retail
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Drops", total_drops)
        with col2:
            st.metric("Total Retail", f"${total_retail:.2f}")
        with col3:
            st.metric("Total Predicted Resale", f"${total_predicted:.2f}")
        with col4:
            st.metric("Potential Profit", f"${potential_profit:.2f}")
        
        # Brand breakdown
        st.subheader("Drops by Brand")
        brand_counts = {}
        for drop in all_drops:
            brand = drop.get("brand", "Unknown")
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        
        for brand, count in brand_counts.items():
            st.write(f"**{brand}:** {count} drops")
    else:
        st.info("No drops to analyze yet. Add some drops to see analytics!")