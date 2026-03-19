import streamlit as st
import datetime
import json
from decimal import Decimal

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Cross-Listing Manager", page_icon="🍑", layout="wide")
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

def _ph(count=1):
    """Return placeholder(s) for current DB type."""
    p = "%s" if USE_POSTGRES else "?"
    return ", ".join([p] * count) if count > 1 else p

def _ensure_tables():
    """Create all necessary tables for cross-listing management."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Cross-listings table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_cross_listings (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            inventory_id INTEGER,
            platform TEXT NOT NULL,
            listing_url TEXT,
            listing_status TEXT DEFAULT 'draft',
            listed_price REAL,
            listed_date DATE,
            last_synced TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Listing templates table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_listing_templates (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            title_template TEXT,
            description_template TEXT,
            default_shipping TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Inventory table if not exists (for foreign key reference)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_inventory (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT,
            brand TEXT,
            model TEXT,
            colorway TEXT,
            size TEXT,
            condition TEXT,
            purchase_price REAL,
            purchase_date DATE,
            target_price REAL,
            status TEXT DEFAULT 'in_stock',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id():
    """Get current user ID from session."""
    return st.session_state.get("user_id", 1)

# Platform-specific formatting helpers
def format_ebay_title(brand, model, colorway, size, condition):
    """Format title for eBay (80-char limit)."""
    base = f"{brand} {model} {colorway}"
    suffix = f" Size {size} {condition}"
    max_base = 80 - len(suffix)
    if len(base) > max_base:
        base = base[:max_base-3] + "..."
    return (base + suffix)[:80]

def format_mercari_listing(brand, model, colorway, size, condition, notes=""):
    """Format listing for Mercari with hashtags."""
    title = f"{brand} {model} {colorway} Size {size}"[:80]
    hashtags = f"#sneakers #{brand.lower().replace(' ', '')} #{model.lower().replace(' ', '')} #kicks #forsale"
    description = f"""
{brand} {model}
Colorway: {colorway}
Size: {size}
Condition: {condition}

{notes if notes else 'Ships fast! Check out my other listings!'}

{hashtags}
""".strip()
    return title, description

def format_depop_caption(brand, model, colorway, size, condition, notes=""):
    """Format caption for Depop (short, trendy style)."""
    caption = f"✨ {brand} {model} ✨\n{colorway} | Size {size} | {condition}\n\n"
    if notes:
        caption += f"{notes}\n\n"
    caption += "💫 DM for bundle deals!\n#sneakers #streetwear #vintage #kicks"
    return caption[:2200]  # Depop limit

def get_inventory_items(user_id):
    """Get all inventory items for user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, sku, brand, model, colorway, size, condition, purchase_price, target_price, status, notes
        FROM soleops_inventory
        WHERE user_id = {_ph()}
        ORDER BY created_at DESC
    """, (user_id,))
    items = cur.fetchall()
    conn.close()
    return items

def get_cross_listings(user_id, inventory_id=None, platform=None, status=None):
    """Get cross-listings with optional filters."""
    conn = get_conn()
    cur = conn.cursor()
    
    query = f"""
        SELECT id, inventory_id, platform, listing_url, listing_status, listed_price, listed_date, last_synced, created_at
        FROM soleops_cross_listings
        WHERE user_id = {_ph()}
    """
    params = [user_id]
    
    if inventory_id:
        query += f" AND inventory_id = {_ph()}"
        params.append(inventory_id)
    if platform:
        query += f" AND platform = {_ph()}"
        params.append(platform)
    if status:
        query += f" AND listing_status = {_ph()}"
        params.append(status)
    
    query += " ORDER BY created_at DESC"
    
    cur.execute(query, tuple(params))
    listings = cur.fetchall()
    conn.close()
    return listings

# Main UI
st.title("🍑 SoleOps Cross-Listing Manager")

tab1, tab2, tab3 = st.tabs(["📋 Inventory", "🔗 Cross-Listings", "📝 Templates"])

with tab1:
    st.subheader("Inventory Items")
    items = get_inventory_items(get_user_id())
    if items:
        for item in items:
            st.write(f"**{item[2]} {item[3]}** - Size {item[5]} - {item[9]}")
    else:
        st.info("No inventory items found.")

with tab2:
    st.subheader("Cross-Listings")
    listings = get_cross_listings(get_user_id())
    if listings:
        for listing in listings:
            st.write(f"Platform: {listing[2]} - Status: {listing[4]}")
    else:
        st.info("No cross-listings found.")

with tab3:
    st.subheader("Listing Templates")
    st.info("Templates coming soon!")