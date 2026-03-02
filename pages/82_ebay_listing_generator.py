import streamlit as st
import json
import re
from datetime import datetime
from typing import Optional, Dict, List, Any
import requests

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
                category VARCHAR(255),
                condition VARCHAR(50),
                brand VARCHAR(100),
                keywords TEXT,
                comp_data JSONB,
                status VARCHAR(50) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_comps_cache (
                id SERIAL PRIMARY KEY,
                search_query VARCHAR(255),
                comp_data JSONB,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                category TEXT,
                condition TEXT,
                brand TEXT,
                keywords TEXT,
                comp_data TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_comps_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_query TEXT,
                comp_data TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# eBay API Helper Functions
def fetch_ebay_sold_comps(search_query: str, category_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch comparable sold listings from eBay API"""
    ebay_app_id = get_setting("ebay_app_id")
    
    if not ebay_app_id:
        return {"error": "eBay App ID not configured", "listings": [], "stats": {}}
    
    # Check cache first
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT comp_data, fetched_at FROM ebay_comps_cache 
        WHERE search_query = {placeholder}
        ORDER BY fetched_at DESC LIMIT 1
    """, (search_query,))
    
    cached = cur.fetchone()
    if cached:
        fetched_at = cached[1]
        if isinstance(fetched_at, str):
            fetched_at = datetime.fromisoformat(fetched_at)
        
        hours_old = (datetime.now() - fetched_at).total_seconds() / 3600
        if hours_old < 24:
            conn.close()
            comp_data = cached[0]
            if isinstance(comp_data, str):
                comp_data = json.loads(comp_data)
            return comp_data
    
    conn.close()
    
    # Fetch from eBay Finding API
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
            "paginationInput.entriesPerPage": "50"
        }
        
        if category_id:
            params["categoryId"] = category_id
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        listings = []
        stats = {"avg_price": 0, "min_price": 0, "max_price": 0, "count": 0}
        
        # Parse response
        search_result = data.get("findCompletedItemsResponse", [{}])[0]
        items = search_result.get("searchResult", [{}])[0].get("item", [])
        
        prices = []
        for item in items:
            price = float(item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("__value__", 0))
            prices.append(price)
            listings.append({
                "title": item.get("title", [""])[0],
                "price": price,
                "url": item.get("viewItemURL", [""])[0],
                "end_time": item.get("listingInfo", [{}])[0].get("endTime", [""])[0]
            })
        
        if prices:
            stats["avg_price"] = sum(prices) / len(prices)
            stats["min_price"] = min(prices)
            stats["max_price"] = max(prices)
            stats["count"] = len(prices)
        
        result = {"listings": listings, "stats": stats}
        
        # Cache the result
        conn = get_conn()
        cur = conn.cursor()
        comp_data_str = json.dumps(result)
        cur.execute(f"""
            INSERT INTO ebay_comps_cache (search_query, comp_data)
            VALUES ({placeholder}, {placeholder})
        """, (search_query, comp_data_str))
        conn.commit()
        conn.close()
        
        return result
        
    except Exception as e:
        return {"error": str(e), "listings": [], "stats": {}}


def generate_listing_keywords(product_name: str, features: str) -> str:
    """Generate keywords for eBay listing"""
    return f"{product_name} {features}"


def generate_ebay_listing(product_name: str, description: str, condition: str, brand: str) -> Dict[str, Any]:
    """Generate an eBay listing from product details"""
    features = description[:50] if description else ""
    
    listing = {
        "title": product_name[:80],
        "description": description,
        "condition": condition,
        "brand": brand,
        "keywords": generate_listing_keywords(product_name, features)
    }
    
    return listing


# Main Page Content
st.title("🍑 eBay Listing Generator")

tab1, tab2, tab3 = st.tabs(["Create Listing", "Saved Listings", "Settings"])

with tab1:
    st.subheader("Create New Listing")
    
    col1, col2 = st.columns(2)
    
    with col1:
        product_name = st.text_input("Product Name", max_chars=80)
        brand = st.text_input("Brand")
        condition = st.selectbox("Condition", ["New", "Like New", "Very Good", "Good", "Acceptable"])
        price = st.number_input("Price ($)", min_value=0.0, step=0.01)
    
    with col2:
        category = st.text_input("Category")
        sku = st.text_input("SKU")
        description = st.text_area("Description", height=150)
    
    if st.button("Generate Listing"):
        if product_name:
            listing = generate_ebay_listing(product_name, description, condition, brand)
            listing["price"] = price
            listing["category"] = category
            listing["sku"] = sku
            
            st.success("Listing generated!")
            st.json(listing)
        else:
            st.error("Please enter a product name")

with tab2:
    st.subheader("Saved Listings")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ebay_listings ORDER BY created_at DESC")
    listings = cur.fetchall()
    conn.close()
    
    if listings:
        for listing in listings:
            with st.expander(f"{listing[2]} - ${listing[4]}"):
                st.write(f"SKU: {listing[1]}")
                st.write(f"Description: {listing[3]}")
                st.write(f"Status: {listing[10]}")
    else:
        st.info("No saved listings yet")

with tab3:
    st.subheader("eBay API Settings")
    
    current_app_id = get_setting("ebay_app_id") or ""
    new_app_id = st.text_input("eBay App ID", value=current_app_id, type="password")
    
    if st.button("Save Settings"):
        set_setting("ebay_app_id", new_app_id)
        st.success("Settings saved!")