import streamlit as st
import json
import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import base64
from io import BytesIO

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="eBay Listing Generator", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_listings (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100),
                title VARCHAR(80),
                description TEXT,
                price DECIMAL(10, 2),
                market_avg DECIMAL(10, 2),
                condition VARCHAR(50),
                brand VARCHAR(100),
                model VARCHAR(200),
                size VARCHAR(20),
                color VARCHAR(100),
                image_data TEXT,
                status VARCHAR(20) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_comps (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER REFERENCES ebay_listings(id) ON DELETE CASCADE,
                comp_title VARCHAR(255),
                comp_price DECIMAL(10, 2),
                comp_condition VARCHAR(50),
                sold_date DATE,
                source VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                title TEXT,
                description TEXT,
                price REAL,
                market_avg REAL,
                condition TEXT,
                brand TEXT,
                model TEXT,
                size TEXT,
                color TEXT,
                image_data TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_comps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER,
                comp_title TEXT,
                comp_price REAL,
                comp_condition TEXT,
                sold_date DATE,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (listing_id) REFERENCES ebay_listings(id) ON DELETE CASCADE
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

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

def _get_mock_market_data(search_query: str) -> List[Dict]:
    """Return mock market data for demo purposes."""
    return [
        {"title": f"{search_query} - Example Item 1", "price": 29.99, "condition": "Used", "sold_date": datetime.now().date()},
        {"title": f"{search_query} - Example Item 2", "price": 34.99, "condition": "New", "sold_date": datetime.now().date()},
        {"title": f"{search_query} - Example Item 3", "price": 24.99, "condition": "Used", "sold_date": datetime.now().date()},
    ]

# eBay API Helper Functions
def fetch_ebay_sold_listings(search_query: str, limit: int = 10) -> List[Dict]:
    """Fetch recent sold listings from eBay for market comparison."""
    ebay_app_id = get_setting("ebay_app_id")
    
    if not ebay_app_id:
        # Return mock data for demo purposes when no API key
        return _get_mock_market_data(search_query)
    
    try:
        url = "https://svcs.ebay.com/services/search/FindingService/v1"
        params = {
            "OPERATION-NAME": "findCompletedItems",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": ebay_app_id,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "keywords": search_query,
            "itemFilter(0).name": "SoldItemsOnly",
            "itemFilter(0).value": "true",
            "sortOrder": "EndTimeSoonest",
            "paginationInput.entriesPerPage": str(limit)
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("findCompletedItemsResponse", [{}])[0].get("searchResult", [{}])[0].get("item", [])
            
            results = []
            for item in items:
                price = float(item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("__value__", 0))
                title = item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", "")
                condition = item.get("condition", [{}])[0].get("conditionDisplayName", ["Unknown"])[0] if item.get("condition") else "Unknown"
                end_time = item.get("listingInfo", [{}])[0].get("endTime", [""])[0]
                sold_date = datetime.now().date()
                if end_time:
                    try:
                        sold_date = datetime.fromisoformat(end_time.replace("Z", "+00:00")).date()
                    except:
                        pass
                
                results.append({
                    "title": title,
                    "price": price,
                    "condition": condition,
                    "sold_date": sold_date
                })
            
            return results
    except Exception as e:
        st.warning(f"Could not fetch eBay data: {e}")
    
    return _get_mock_market_data(search_query)

def calculate_market_average(comps: List[Dict]) -> float:
    """Calculate average price from comparable listings."""
    if not comps:
        return 0.0
    prices = [c.get("price", 0) for c in comps if c.get("price", 0) > 0]
    return sum(prices) / len(prices) if prices else 0.0

def save_listing(listing_data: Dict) -> int:
    """Save a listing to the database."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO ebay_listings (sku, title, description, price, market_avg, condition, brand, model, size, color, image_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            listing_data.get("sku"),
            listing_data.get("title"),
            listing_data.get("description"),
            listing_data.get("price"),
            listing_data.get("market_avg"),
            listing_data.get("condition"),
            listing_data.get("brand"),
            listing_data.get("model"),
            listing_data.get("size"),
            listing_data.get("color"),
            listing_data.get("image_data"),
            listing_data.get("status", "draft")
        ))
        listing_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO ebay_listings (sku, title, description, price, market_avg, condition, brand, model, size, color, image_data, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            listing_data.get("sku"),
            listing_data.get("title"),
            listing_data.get("description"),
            listing_data.get("price"),
            listing_data.get("market_avg"),
            listing_data.get("condition"),
            listing_data.get("brand"),
            listing_data.get("model"),
            listing_data.get("size"),
            listing_data.get("color"),
            listing_data.get("image_data"),
            listing_data.get("status", "draft")
        ))
        listing_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return listing_id

def get_listings(status: str = None) -> List[Dict]:
    """Get listings from database."""
    conn = get_conn()
    cur = conn.cursor()
    
    if status:
        if USE_POSTGRES:
            cur.execute("SELECT * FROM ebay_listings WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cur.execute("SELECT * FROM ebay_listings WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cur.execute("SELECT * FROM ebay_listings ORDER BY created_at DESC")
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def delete_listing(listing_id: int):
    """Delete a listing from database."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM ebay_listings WHERE id = %s", (listing_id,))
    else:
        cur.execute("DELETE FROM ebay_listings WHERE id = ?", (listing_id,))
    
    conn.commit()
    conn.close()

# Main UI
st.title("🛒 eBay Listing Generator")
st.markdown("Create optimized eBay listings with market research and pricing suggestions.")

tab1, tab2, tab3 = st.tabs(["📝 Create Listing", "📋 My Listings", "⚙️ Settings"])

with tab1:
    st.subheader("Create New Listing")
    
    col1, col2 = st.columns(2)
    
    with col1:
        brand = st.text_input("Brand", placeholder="e.g., Nike, Apple, Samsung")
        model = st.text_input("Model/Product Name", placeholder="e.g., Air Jordan 1, iPhone 14")
        condition = st.selectbox("Condition", ["New", "Like New", "Very Good", "Good", "Acceptable"])
        size = st.text_input("Size (if applicable)", placeholder="e.g., 10.5, Large, 64GB")
        color = st.text_input("Color", placeholder="e.g., Black, Red/White")
    
    with col2:
        sku = st.text_input("SKU (optional)", placeholder="Your internal reference")
        description = st.text_area("Description", height=150, placeholder="Describe your item...")
        uploaded_image = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
    
    # Market Research Section
    st.markdown("---")
    st.subheader("📊 Market Research")
    
    search_query = f"{brand} {model}".strip()
    
    if st.button("🔍 Fetch Market Data", disabled=not search_query):
        with st.spinner("Fetching sold listings..."):
            comps = fetch_ebay_sold_listings(search_query)
            st.session_state["market_comps"] = comps
            st.session_state["market_avg"] = calculate_market_average(comps)
    
    if "market_comps" in st.session_state and st.session_state["market_comps"]:
        comps = st.session_state["market_comps"]
        avg_price = st.session_state.get("market_avg", 0)
        
        st.success(f"Found {len(comps)} comparable sold listings. Average price: ${avg_price:.2f}")
        
        with st.expander("View Comparable Sales"):
            for comp in comps:
                st.write(f"**{comp['title']}** - ${comp['price']:.2f} ({comp['condition']})")
    
    # Pricing
    st.markdown("---")
    st.subheader("💰 Pricing")
    
    suggested_price = st.session_state.get("market_avg", 0)
    price = st.number_input("Your Price", min_value=0.0, value=suggested_price, step=0.01, format="%.2f")
    
    if suggested_price > 0:
        diff = price - suggested_price
        if diff > 0:
            st.info(f"Your price is ${diff:.2f} above market average")
        elif diff < 0:
            st.info(f"Your price is ${abs(diff):.2f} below market average")
        else:
            st.info("Your price matches the market average")
    
    # Generate Title
    st.markdown("---")
    st.subheader("📝 Listing Title")
    
    auto_title = f"{brand} {model}".strip()
    if size:
        auto_title += f" Size {size}"
    if color:
        auto_title += f" {color}"
    if condition and condition != "New":
        auto_title += f" - {condition}"
    
    title = st.text_input("Title (max 80 characters)", value=auto_title[:80], max_chars=80)
    st.caption(f"{len(title)}/80 characters")
    
    # Save Listing
    st.markdown("---")
    
    if st.button("💾 Save Listing", type="primary"):
        if not title:
            st.error("Please provide a title for your listing")
        else:
            image_data = None
            if uploaded_image:
                image_data = base64.b64encode(uploaded_image.read()).decode()
            
            listing_data = {
                "sku": sku,
                "title": title,
                "description": description,
                "price": price,
                "market_avg": st.session_state.get("market_avg", 0),
                "condition": condition,
                "brand": brand,
                "model": model,
                "size": size,
                "color": color,
                "image_data": image_data,
                "status": "draft"
            }
            
            listing_id = save_listing(listing_data)
            st.success(f"Listing saved! ID: {listing_id}")
            
            # Clear market data
            if "market_comps" in st.session_state:
                del st.session_state["market_comps"]
            if "market_avg" in st.session_state:
                del st.session_state["market_avg"]

with tab2:
    st.subheader("My Listings")
    
    status_filter = st.selectbox("Filter by Status", ["All", "draft", "active", "sold"])
    
    listings = get_listings(None if status_filter == "All" else status_filter)
    
    if not listings:
        st.info("No listings found. Create your first listing!")
    else:
        for listing in listings:
            with st.expander(f"{listing['title']} - ${listing['price']:.2f}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**SKU:** {listing.get('sku', 'N/A')}")
                    st.write(f"**Condition:** {listing.get('condition', 'N/A')}")
                    st.write(f"**Brand:** {listing.get('brand', 'N/A')}")
                    st.write(f"**Model:** {listing.get('model', 'N/A')}")
                    st.write(f"**Status:** {listing.get('status', 'draft')}")
                    if listing.get('market_avg'):
                        st.write(f"**Market Avg:** ${listing['market_avg']:.2f}")
                
                with col2:
                    if listing.get('image_data'):
                        image_bytes = base64.b64decode(listing['image_data'])
                        st.image(image_bytes, width=150)
                
                if st.button(f"🗑️ Delete", key=f"del_{listing['id']}"):
                    delete_listing(listing['id'])
                    st.rerun()

with tab3:
    st.subheader("eBay API Settings")
    
    current_app_id = get_setting("ebay_app_id") or ""
    
    st.markdown("""
    To fetch real market data, you need an eBay Developer App ID.
    
    1. Go to [eBay Developer Program](https://developer.ebay.com/)
    2. Create an account and application
    3. Copy your App ID (Client ID) below
    """)
    
    new_app_id = st.text_input("eBay App ID", value=current_app_id, type="password")
    
    if st.button("Save Settings"):
        set_setting("ebay_app_id", new_app_id)
        st.success("Settings saved!")