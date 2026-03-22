import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from decimal import Decimal
import io
import csv

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Arbitrage Watchlist Manager", page_icon="🍑", layout="wide")
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


def _ph(count=1):
    """Return placeholder string(s) based on database type."""
    if USE_POSTGRES:
        return ", ".join(["%s"] * count)
    return ", ".join(["?"] * count)


def _ensure_tables():
    """Create all required tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Watchlist categories/tags table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_arb_watchlist_tags (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#3498db',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Watchlist priorities table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_arb_watchlist_priorities (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            watchlist_item_id INTEGER,
            sku TEXT NOT NULL,
            priority_score INTEGER DEFAULT 50,
            profit_potential DECIMAL(10,2),
            market_demand TEXT DEFAULT 'medium',
            volatility TEXT DEFAULT 'low',
            notes TEXT,
            tag_ids TEXT,
            max_buy_price DECIMAL(10,2),
            target_sell_price DECIMAL(10,2),
            estimated_roi DECIMAL(5,2),
            last_market_check TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Watchlist items table (enhanced)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_arb_watchlist_items (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            brand TEXT,
            colorway TEXT,
            retail_price DECIMAL(10,2),
            max_buy_price DECIMAL(10,2),
            target_sell_price DECIMAL(10,2),
            current_market_price DECIMAL(10,2),
            size TEXT,
            condition TEXT DEFAULT 'new',
            tag_ids TEXT,
            priority_score INTEGER DEFAULT 50,
            is_active BOOLEAN DEFAULT TRUE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Import history table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_arb_import_history (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            filename TEXT,
            items_imported INTEGER DEFAULT 0,
            items_failed INTEGER DEFAULT 0,
            import_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def get_user_id():
    """Get current user ID from session."""
    return st.session_state.get("user_id", 1)


def get_all_tags(user_id):
    """Fetch all tags for a user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, name, color, description FROM soleops_arb_watchlist_tags WHERE user_id = {_ph()} ORDER BY name",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "color": r[2], "description": r[3]} for r in rows]


def create_tag(user_id, name, color, description):
    """Create a new tag."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO soleops_arb_watchlist_tags (user_id, name, color, description) VALUES ({_ph(4)})",
        (user_id, name, color, description)
    )
    conn.commit()
    conn.close()


def update_tag(tag_id, name, color, description):
    """Update an existing tag."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE soleops_arb_watchlist_tags SET name = {_ph()}, color = {_ph()}, description = {_ph()}, updated_at = CURRENT_TIMESTAMP WHERE id = {_ph()}",
        (name, color, description, tag_id)
    )
    conn.commit()
    conn.close()


def delete_tag(tag_id):
    """Delete a tag."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM soleops_arb_watchlist_tags WHERE id = {_ph()}", (tag_id,))
    conn.commit()
    conn.close()


def get_all_watchlist_items(user_id, active_only=True):
    """Fetch all watchlist items for a user."""
    conn = get_conn()
    cur = conn.cursor()
    query = f"SELECT id, sku, name, brand, colorway, retail_price, max_buy_price, target_sell_price, current_market_price, size, condition, tag_ids, priority_score, is_active, notes, created_at, updated_at FROM soleops_arb_watchlist_items WHERE user_id = {_ph()}"
    if active_only:
        query += " AND is_active = TRUE"
    query += " ORDER BY priority_score DESC, name"
    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [{
        "id": r[0], "sku": r[1], "name": r[2], "brand": r[3], "colorway": r[4],
        "retail_price": r[5], "max_buy_price": r[6], "target_sell_price": r[7],
        "current_market_price": r[8], "size": r[9], "condition": r[10],
        "tag_ids": r[11], "priority_score": r[12], "is_active": r[13],
        "notes": r[14], "created_at": r[15], "updated_at": r[16]
    } for r in rows]


def create_watchlist_item(user_id, sku, name, brand, colorway, retail_price, max_buy_price, target_sell_price, size, condition, tag_ids, priority_score, notes):
    """Create a new watchlist item."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO soleops_arb_watchlist_items (user_id, sku, name, brand, colorway, retail_price, max_buy_price, target_sell_price, size, condition, tag_ids, priority_score, notes) VALUES ({_ph(13)})",
        (user_id, sku, name, brand, colorway, retail_price, max_buy_price, target_sell_price, size, condition, tag_ids, priority_score, notes)
    )
    conn.commit()
    conn.close()


def update_watchlist_item(item_id, sku, name, brand, colorway, retail_price, max_buy_price, target_sell_price, size, condition, tag_ids, priority_score, is_active, notes):
    """Update an existing watchlist item."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE soleops_arb_watchlist_items SET sku = {_ph()}, name = {_ph()}, brand = {_ph()}, colorway = {_ph()}, retail_price = {_ph()}, max_buy_price = {_ph()}, target_sell_price = {_ph()}, size = {_ph()}, condition = {_ph()}, tag_ids = {_ph()}, priority_score = {_ph()}, is_active = {_ph()}, notes = {_ph()}, updated_at = CURRENT_TIMESTAMP WHERE id = {_ph()}",
        (sku, name, brand, colorway, retail_price, max_buy_price, target_sell_price, size, condition, tag_ids, priority_score, is_active, notes, item_id)
    )
    conn.commit()
    conn.close()


def delete_watchlist_item(item_id):
    """Delete a watchlist item."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM soleops_arb_watchlist_items WHERE id = {_ph()}", (item_id,))
    conn.commit()
    conn.close()


# Initialize tables
_ensure_tables()

# Main UI
st.title("🍑 SoleOps Arbitrage Watchlist Manager")

user_id = get_user_id()

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📋 Watchlist", "🏷️ Tags", "📥 Import/Export", "📊 Analytics"])

with tab1:
    st.subheader("Watchlist Items")
    
    # Add new item form
    with st.expander("➕ Add New Item"):
        col1, col2 = st.columns(2)
        with col1:
            new_sku = st.text_input("SKU", key="new_sku")
            new_name = st.text_input("Name", key="new_name")
            new_brand = st.text_input("Brand", key="new_brand")
            new_colorway = st.text_input("Colorway", key="new_colorway")
        with col2:
            new_retail = st.number_input("Retail Price", min_value=0.0, key="new_retail")
            new_max_buy = st.number_input("Max Buy Price", min_value=0.0, key="new_max_buy")
            new_target_sell = st.number_input("Target Sell Price", min_value=0.0, key="new_target_sell")
            new_size = st.text_input("Size", key="new_size")
        
        new_condition = st.selectbox("Condition", ["new", "used", "deadstock"], key="new_condition")
        new_priority = st.slider("Priority Score", 0, 100, 50, key="new_priority")
        new_notes = st.text_area("Notes", key="new_notes")
        
        if st.button("Add Item"):
            if new_sku and new_name:
                create_watchlist_item(user_id, new_sku, new_name, new_brand, new_colorway, new_retail, new_max_buy, new_target_sell, new_size, new_condition, "", new_priority, new_notes)
                st.success("Item added successfully!")
                st.rerun()
            else:
                st.error("SKU and Name are required.")
    
    # Display watchlist items
    show_inactive = st.checkbox("Show inactive items", value=False)
    items = get_all_watchlist_items(user_id, active_only=not show_inactive)
    
    if items:
        for item in items:
            with st.expander(f"{item['name']} ({item['sku']}) - Priority: {item['priority_score']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Brand:** {item['brand'] or 'N/A'}")
                    st.write(f"**Colorway:** {item['colorway'] or 'N/A'}")
                    st.write(f"**Size:** {item['size'] or 'N/A'}")
                with col2:
                    st.write(f"**Retail:** ${item['retail_price'] or 0:.2f}")
                    st.write(f"**Max Buy:** ${item['max_buy_price'] or 0:.2f}")
                    st.write(f"**Target Sell:** ${item['target_sell_price'] or 0:.2f}")
                with col3:
                    st.write(f"**Condition:** {item['condition']}")
                    st.write(f"**Active:** {'Yes' if item['is_active'] else 'No'}")
                
                if item['notes']:
                    st.write(f"**Notes:** {item['notes']}")
                
                if st.button("Delete", key=f"del_{item['id']}"):
                    delete_watchlist_item(item['id'])
                    st.success("Item deleted!")
                    st.rerun()
    else:
        st.info("No watchlist items found. Add your first item above!")

with tab2:
    st.subheader("Manage Tags")
    
    # Add new tag
    with st.expander("➕ Add New Tag"):
        tag_name = st.text_input("Tag Name", key="tag_name")
        tag_color = st.color_picker("Tag Color", "#3498db", key="tag_color")
        tag_desc = st.text_input("Description", key="tag_desc")
        
        if st.button("Create Tag"):
            if tag_name:
                create_tag(user_id, tag_name, tag_color, tag_desc)
                st.success("Tag created!")
                st.rerun()
            else:
                st.error("Tag name is required.")
    
    # Display tags
    tags = get_all_tags(user_id)
    if tags:
        for tag in tags:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"<span style='background-color: {tag['color']}; padding: 2px 8px; border-radius: 4px;'>{tag['name']}</span> - {tag['description'] or 'No description'}", unsafe_allow_html=True)
            with col3:
                if st.button("🗑️", key=f"del_tag_{tag['id']}"):
                    delete_tag(tag['id'])
                    st.rerun()
    else:
        st.info("No tags created yet.")

with tab3:
    st.subheader("Import/Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Import from CSV**")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            if st.button("Import"):
                st.info("Import functionality coming soon!")
    
    with col2:
        st.write("**Export to CSV**")
        if st.button("Export Watchlist"):
            items = get_all_watchlist_items(user_id, active_only=False)
            if items:
                df = pd.DataFrame(items)
                csv_data = df.to_csv(index=False)
                st.download_button("Download CSV", csv_data, "watchlist_export.csv", "text/csv")
            else:
                st.warning("No items to export.")

with tab4:
    st.subheader("Analytics")
    
    items = get_all_watchlist_items(user_id, active_only=False)
    
    if items:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Items", len(items))
        with col2:
            active_count = sum(1 for i in items if i['is_active'])
            st.metric("Active Items", active_count)
        with col3:
            avg_priority = sum(i['priority_score'] or 0 for i in items) / len(items)
            st.metric("Avg Priority", f"{avg_priority:.1f}")
        
        st.markdown("---")
        
        # Priority distribution
        st.write("**Priority Distribution**")
        priority_data = pd.DataFrame(items)
        if 'priority_score' in priority_data.columns:
            st.bar_chart(priority_data['priority_score'].value_counts().sort_index())
    else:
        st.info("Add items to your watchlist to see analytics.")

st.markdown("---")
st.caption("SoleOps Arbitrage Watchlist Manager v1.0")