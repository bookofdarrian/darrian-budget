import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import requests
import base64
import os

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps AI Listing Generator", page_icon="🍑", layout="wide")
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

def _ph(count: int = 1) -> str:
    """Return SQL placeholder(s) based on database type."""
    ph = "%s" if USE_POSTGRES else "?"
    return ", ".join([ph] * count)

def _ensure_tables():
    """Create all required tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Listing performance tracking table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_listing_performance (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT,
            brand TEXT,
            model TEXT,
            size TEXT,
            platform TEXT NOT NULL,
            title TEXT NOT NULL,
            title_type TEXT DEFAULT 'ai',
            description TEXT,
            list_price REAL,
            suggested_price REAL,
            sold_price REAL,
            views INTEGER DEFAULT 0,
            watchers INTEGER DEFAULT 0,
            days_to_sell INTEGER,
            status TEXT DEFAULT 'active',
            ebay_item_id TEXT,
            mercari_listing_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sold_at TIMESTAMP
        )
    """)
    
    # A/B title testing table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_title_tests (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT,
            title_a TEXT NOT NULL,
            title_b TEXT NOT NULL,
            title_a_type TEXT DEFAULT 'ai',
            title_b_type TEXT DEFAULT 'manual',
            title_a_views INTEGER DEFAULT 0,
            title_b_views INTEGER DEFAULT 0,
            title_a_watchers INTEGER DEFAULT 0,
            title_b_watchers INTEGER DEFAULT 0,
            title_a_sold INTEGER DEFAULT 0,
            title_b_sold INTEGER DEFAULT 0,
            winner TEXT,
            test_started TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            test_ended TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """)
    
    # Market price cache table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_market_price_cache (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            sku TEXT NOT NULL,
            size TEXT,
            platform TEXT NOT NULL,
            avg_price REAL,
            min_price REAL,
            max_price REAL,
            sold_count INTEGER,
            active_count INTEGER,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sku, size, platform)
        )
    """)
    
    # Generated listings history
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_generated_listings (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT,
            brand TEXT,
            model TEXT,
            size TEXT,
            condition TEXT,
            ebay_title TEXT,
            ebay_description TEXT,
            mercari_title TEXT,
            mercari_description TEXT,
            suggested_ebay_price REAL,
            suggested_mercari_price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id() -> int:
    """Get current user ID from session."""
    return st.session_state.get("user_id", 1)

def call_claude_api(prompt: str, max_tokens: int = 2000) -> Optional[str]:
    """Call Claude API with the given prompt."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("content", [{}])[0].get("text", "")
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        return None

# Main page content
st.title("🍑 SoleOps AI Listing Generator")
st.markdown("Generate optimized listings for eBay and Mercari using AI.")

# Input form
with st.form("listing_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        brand = st.text_input("Brand", placeholder="Nike, Adidas, etc.")
        model = st.text_input("Model", placeholder="Air Jordan 1, Yeezy 350, etc.")
        sku = st.text_input("SKU/Style Code", placeholder="555088-101")
    
    with col2:
        size = st.text_input("Size", placeholder="10.5")
        condition = st.selectbox("Condition", ["New", "Like New", "Good", "Fair", "Poor"])
        color = st.text_input("Color", placeholder="White/Black/Red")
    
    additional_details = st.text_area("Additional Details", placeholder="Any special features, flaws, or notes...")
    
    submitted = st.form_submit_button("Generate Listings", type="primary")

if submitted:
    if not brand or not model:
        st.error("Please enter at least the brand and model.")
    else:
        with st.spinner("Generating optimized listings..."):
            prompt = f"""Generate optimized eBay and Mercari listings for the following sneaker:

Brand: {brand}
Model: {model}
SKU: {sku or 'N/A'}
Size: {size or 'N/A'}
Condition: {condition}
Color: {color or 'N/A'}
Additional Details: {additional_details or 'None'}

Please provide:
1. An eBay title (max 80 characters, keyword-optimized)
2. An eBay description (detailed, professional)
3. A Mercari title (max 40 characters)
4. A Mercari description (concise, appealing)

Format your response as JSON with keys: ebay_title, ebay_description, mercari_title, mercari_description"""

            result = call_claude_api(prompt)
            
            if result:
                st.success("Listings generated successfully!")
                st.markdown("### Generated Listings")
                st.text_area("AI Response", result, height=400)
            else:
                st.warning("Could not generate listings. Please check your API key in settings.")