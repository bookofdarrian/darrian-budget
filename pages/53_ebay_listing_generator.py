import streamlit as st
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="eBay Listing Generator", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS ebay_listings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                product_name VARCHAR(255),
                brand VARCHAR(100),
                model VARCHAR(100),
                size VARCHAR(20),
                condition_grade VARCHAR(50),
                title VARCHAR(80),
                description TEXT,
                price DECIMAL(10,2),
                market_avg DECIMAL(10,2),
                market_low DECIMAL(10,2),
                market_high DECIMAL(10,2),
                comparable_count INTEGER DEFAULT 0,
                image_data TEXT,
                keywords TEXT,
                status VARCHAR(50) DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_cache (
                id SERIAL PRIMARY KEY,
                search_hash VARCHAR(64) UNIQUE,
                search_query VARCHAR(255),
                results_json TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                brand TEXT,
                model TEXT,
                size TEXT,
                condition_grade TEXT,
                title TEXT,
                description TEXT,
                price REAL,
                market_avg REAL,
                market_low REAL,
                market_high REAL,
                comparable_count INTEGER DEFAULT 0,
                image_data TEXT,
                keywords TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_hash TEXT UNIQUE,
                search_query TEXT,
                results_json TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

CONDITION_GRADES = [
    "New with Box",
    "New without Box",
    "New with Defects",
    "Pre-owned - Excellent",
    "Pre-owned - Good",
    "Pre-owned - Fair"
]

SNEAKER_BRANDS = [
    "Nike", "Jordan", "Adidas", "Yeezy", "New Balance", "Asics",
    "Puma", "Reebok", "Converse", "Vans", "Under Armour", "Other"
]

SHOE_SIZES = [str(s) for s in [4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 14, 15, 16]]

def get_search_hash(query: str) -> str:
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

def get_cached_market_data(search_query: str) -> Optional[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    search_hash = get_search_hash(search_query)
    cache_hours = 24
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT results_json, fetched_at FROM ebay_market_cache 
            WHERE search_hash = %s AND fetched_at > NOW() - INTERVAL '%s hours'
        """, (search_hash, cache_hours))
    else:
        cur.execute("""
            SELECT results_json, fetched_at FROM ebay_market_cache 
            WHERE search_hash = ? AND fetched_at > datetime('now', ?)
        """, (search_hash, f'-{cache_hours} hours'))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None

def cache_market_data(search_query: str, results: Dict):
    conn = get_conn()
    cur = conn.cursor()
    search_hash = get_search_hash(search_query)
    results_json = json.dumps(results)
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO ebay_market_cache (search_hash, search_query, results_json)
            VALUES (%s, %s, %s)
            ON CONFLICT (search_hash) DO UPDATE SET results_json = %s, fetched_at = CURRENT_TIMESTAMP
        """, (search_hash, search_query, results_json, results_json))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO ebay_market_cache (search_hash, search_query, results_json, fetched_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (search_hash, search_query, results_json))
    
    conn.commit()
    conn.close()

def generate_ebay_title(brand: str, model: str, size: str, condition: str) -> str:
    """Generate an optimized eBay title (max 80 chars)"""
    title_parts = [brand, model, f"Size {size}"]
    if "New" in condition:
        title_parts.append("NEW")
    title = " ".join(title_parts)
    if len(title) > 80:
        title = title[:77] + "..."
    return title

def generate_ebay_description(brand: str, model: str, size: str, condition: str, keywords: str = "") -> str:
    """Generate a detailed eBay description"""
    description = f"""
<h2>{brand} {model}</h2>

<h3>Product Details:</h3>
<ul>
<li><strong>Brand:</strong> {brand}</li>
<li><strong>Model:</strong> {model}</li>
<li><strong>Size:</strong> {size}</li>
<li><strong>Condition:</strong> {condition}</li>
</ul>

<h3>Description:</h3>
<p>Authentic {brand} {model} in {condition.lower()} condition. Size {size}.</p>

<h3>Shipping:</h3>
<p>Ships within 1-2 business days. All items are carefully packaged to ensure safe delivery.</p>

<p>Thank you for shopping with us!</p>
"""
    return description.strip()

# Main page content
st.title("🛒 eBay Listing Generator")
st.markdown("Create optimized eBay listings for your sneakers and shoes.")

tab1, tab2, tab3 = st.tabs(["📝 Create Listing", "📋 My Listings", "📊 Market Research"])

with tab1:
    st.subheader("📝 Create New Listing")
    
    col1, col2 = st.columns(2)
    
    with col1:
        brand = st.selectbox("Brand", SNEAKER_BRANDS)
        model = st.text_input("Model", placeholder="e.g., Air Jordan 1 Retro High OG")
        size = st.selectbox("Size (US)", SHOE_SIZES)
    
    with col2:
        condition = st.selectbox("Condition", CONDITION_GRADES)
        price = st.number_input("Price ($)", min_value=0.0, step=5.0)
        keywords = st.text_input("Additional Keywords", placeholder="e.g., Chicago, Bred, 2023")
    
    if st.button("Generate Listing", type="primary"):
        if brand and model and size:
            title = generate_ebay_title(brand, model, size, condition)
            description = generate_ebay_description(brand, model, size, condition, keywords)
            
            st.success("Listing generated successfully!")
            
            st.markdown("### Generated Title")
            st.code(title)
            st.caption(f"Character count: {len(title)}/80")
            
            st.markdown("### Generated Description")
            st.markdown(description, unsafe_allow_html=True)
        else:
            st.error("Please fill in Brand, Model, and Size fields.")

with tab2:
    st.subheader("📋 My Listings")
    
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("SELECT id, title, price, status, created_at FROM ebay_listings ORDER BY created_at DESC")
    else:
        cur.execute("SELECT id, title, price, status, created_at FROM ebay_listings ORDER BY created_at DESC")
    
    listings = cur.fetchall()
    conn.close()
    
    if listings:
        for listing in listings:
            with st.expander(f"{listing[1]} - ${listing[2]:.2f}"):
                st.write(f"Status: {listing[3]}")
                st.write(f"Created: {listing[4]}")
    else:
        st.info("No listings yet. Create your first listing in the 'Create Listing' tab!")

with tab3:
    st.subheader("📊 Market Research")
    
    search_query = st.text_input("Search for comparable listings", placeholder="e.g., Jordan 1 Chicago Size 10")
    
    if st.button("Search Market"):
        if search_query:
            cached_data = get_cached_market_data(search_query)
            if cached_data:
                st.info("Using cached market data")
                st.json(cached_data)
            else:
                st.warning("Market research feature requires eBay API integration.")
        else:
            st.error("Please enter a search query.")