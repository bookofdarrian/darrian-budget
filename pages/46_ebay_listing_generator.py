import streamlit as st
import json
import re
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import requests
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
                user_id INTEGER,
                sneaker_brand TEXT,
                sneaker_model TEXT,
                sneaker_size TEXT,
                sneaker_condition TEXT,
                sneaker_colorway TEXT,
                sneaker_sku TEXT,
                original_price DECIMAL(10,2),
                generated_title TEXT,
                generated_description TEXT,
                recommended_price DECIMAL(10,2),
                min_price DECIMAL(10,2),
                max_price DECIMAL(10,2),
                avg_sold_price DECIMAL(10,2),
                median_sold_price DECIMAL(10,2),
                num_comps INTEGER DEFAULT 0,
                market_data JSONB,
                image_data TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_cache (
                id SERIAL PRIMARY KEY,
                search_query TEXT,
                category_id TEXT,
                results JSONB,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ebay_listings_user ON ebay_listings(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ebay_market_cache_query ON ebay_market_cache(search_query)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sneaker_brand TEXT,
                sneaker_model TEXT,
                sneaker_size TEXT,
                sneaker_condition TEXT,
                sneaker_colorway TEXT,
                sneaker_sku TEXT,
                original_price REAL,
                generated_title TEXT,
                generated_description TEXT,
                recommended_price REAL,
                min_price REAL,
                max_price REAL,
                avg_sold_price REAL,
                median_sold_price REAL,
                num_comps INTEGER DEFAULT 0,
                market_data TEXT,
                image_data TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ebay_market_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_query TEXT,
                category_id TEXT,
                results TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


_ensure_tables()


# Sidebar Navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


# Constants
SNEAKER_BRANDS = [
    "Nike", "Jordan", "Adidas", "New Balance", "Yeezy", "Puma", "Reebok", 
    "Converse", "Vans", "ASICS", "Saucony", "Under Armour", "Other"
]

CONDITION_OPTIONS = [
    "Brand New with Box",
    "Brand New without Box", 
    "New with Defects",
    "Pre-owned - Excellent",
    "Pre-owned - Good",
    "Pre-owned - Fair"
]

SHOE_SIZES = [str(i) for i in range(4, 16)] + ["4.5", "5.5", "6.5", "7.5", "8.5", "9.5", "10.5", "11.5", "12.5", "13.5", "14.5"]
SHOE_SIZES = sorted(set(SHOE_SIZES), key=lambda x: float(x))


def get_ebay_oauth_token() -> Optional[str]:
    """Get eBay OAuth token from settings or environment."""
    token = get_setting("ebay_oauth_token")
    if not token:
        token = os.environ.get("EBAY_OAUTH_TOKEN")
    return token


def generate_listing_title(brand: str, model: str, size: str, condition: str, colorway: str = "") -> str:
    """Generate an eBay listing title."""
    title_parts = [brand, model]
    if colorway:
        title_parts.append(colorway)
    title_parts.append(f"Size {size}")
    if "New" in condition:
        title_parts.append("NEW")
    return " ".join(title_parts)[:80]  # eBay title limit is 80 chars


def generate_listing_description(brand: str, model: str, size: str, condition: str, colorway: str = "", sku: str = "") -> str:
    """Generate an eBay listing description."""
    description = f"""
<h2>{brand} {model}</h2>

<p><strong>Size:</strong> {size}</p>
<p><strong>Condition:</strong> {condition}</p>
"""
    if colorway:
        description += f"<p><strong>Colorway:</strong> {colorway}</p>\n"
    if sku:
        description += f"<p><strong>SKU:</strong> {sku}</p>\n"
    
    description += """
<p>Thank you for viewing this listing!</p>
"""
    return description


# Main page content
st.title("🍑 eBay Listing Generator")
st.markdown("Generate optimized eBay listings for sneakers")

# Input form
with st.form("listing_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        brand = st.selectbox("Brand", SNEAKER_BRANDS)
        model = st.text_input("Model", placeholder="e.g., Air Jordan 1 Retro High OG")
        size = st.selectbox("Size", SHOE_SIZES)
    
    with col2:
        condition = st.selectbox("Condition", CONDITION_OPTIONS)
        colorway = st.text_input("Colorway", placeholder="e.g., Chicago")
        sku = st.text_input("SKU (optional)", placeholder="e.g., 555088-101")
    
    original_price = st.number_input("Original Purchase Price ($)", min_value=0.0, step=1.0)
    
    submitted = st.form_submit_button("Generate Listing")

if submitted:
    if not model:
        st.error("Please enter a model name")
    else:
        title = generate_listing_title(brand, model, size, condition, colorway)
        description = generate_listing_description(brand, model, size, condition, colorway, sku)
        
        st.subheader("Generated Title")
        st.code(title)
        
        st.subheader("Generated Description")
        st.markdown(description, unsafe_allow_html=True)
        
        # Save to database
        conn = get_conn()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO ebay_listings 
                (user_id, sneaker_brand, sneaker_model, sneaker_size, sneaker_condition, 
                 sneaker_colorway, sneaker_sku, original_price, generated_title, generated_description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (st.session_state.get("user_id", 1), brand, model, size, condition, 
                  colorway, sku, original_price, title, description))
        else:
            cur.execute("""
                INSERT INTO ebay_listings 
                (user_id, sneaker_brand, sneaker_model, sneaker_size, sneaker_condition, 
                 sneaker_colorway, sneaker_sku, original_price, generated_title, generated_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (st.session_state.get("user_id", 1), brand, model, size, condition, 
                  colorway, sku, original_price, title, description))
        
        conn.commit()
        conn.close()
        
        st.success("Listing saved successfully!")