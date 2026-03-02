import streamlit as st
import json
import re
from datetime import datetime
from typing import Optional, Dict, List, Any
import requests
from io import BytesIO
import base64

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
                sku VARCHAR(100),
                title VARCHAR(100),
                description TEXT,
                price DECIMAL(10,2),
                market_avg DECIMAL(10,2),
                market_min DECIMAL(10,2),
                market_max DECIMAL(10,2),
                brand VARCHAR(100),
                model VARCHAR(200),
                size VARCHAR(20),
                condition VARCHAR(50),
                color VARCHAR(100),
                image_data TEXT,
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
                market_min REAL,
                market_max REAL,
                brand TEXT,
                model TEXT,
                size TEXT,
                condition TEXT,
                color TEXT,
                image_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()


_ensure_tables()


def get_placeholder():
    return "%s" if USE_POSTGRES else "?"


def fetch_ebay_sold_listings(brand: str, model: str, size: str) -> Dict[str, Any]:
    """
    Fetch comparable sold listings from eBay API.
    Falls back to simulated data if API key not configured.
    """
    ebay_app_id = get_setting("ebay_app_id")
    
    if ebay_app_id:
        try:
            search_query = f"{brand} {model} size {size}"
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
                "itemFilter(1).name": "Condition",
                "itemFilter(1).value": "New",
                "sortOrder": "EndTimeSoonest",
                "paginationInput.entriesPerPage": "20"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get("findCompletedItemsResponse", [{}])[0].get("searchResult", [{}])[0].get("item", [])
                
                prices = []
                for item in items:
                    price_info = item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0]
                    price = float(price_info.get("__value__", 0))
                    if price > 0:
                        prices.append(price)
                
                if prices:
                    return {
                        "success": True,
                        "avg_price": round(sum(prices) / len(prices), 2),
                        "min_price": round(min(prices), 2),
                        "max_price": round(max(prices), 2),
                        "num_sold": len(prices),
                        "source": "eBay API"
                    }
        except Exception as e:
            st.warning(f"eBay API error: {str(e)}. Using estimated pricing.")
    
    base_prices = {
        "Nike": {"Dunk": 150, "Air Jordan": 200, "Air Max": 130, "Air Force": 120, "default": 140},
        "Adidas": {"Yeezy": 280, "Ultra Boost": 150, "NMD": 120, "default": 130},
        "New Balance": {"550": 140, "990": 180, "default": 150},
        "Jordan": {"1": 220, "4": 250, "11": 230, "default": 200},
        "default": 150
    }
    
    brand_prices = base_prices.get(brand, base_prices["default"])
    if isinstance(brand_prices, dict):
        base = brand_prices.get(model.split()[0] if model else "default", brand_prices.get("default", 150))
    else:
        base = brand_prices
    
    import random
    variance = random.uniform(0.85, 1.15)
    avg_price = round(base * variance, 2)
    
    return {
        "success": True,
        "avg_price": avg_price,
        "min_price": round(avg_price * 0.8, 2),
        "max_price": round(avg_price * 1.2, 2),
        "num_sold": 0,
        "source": "Estimated"
    }


def get_all_listings():
    """Get all saved listings from database."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ebay_listings ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def main():
    st.title("🍑 eBay Listing Generator")
    
    render_sidebar_brand()
    render_sidebar_user_widget()
    
    # Get total listings count
    listings = get_all_listings()
    total_listings = len(listings)
    
    st.metric("Total Listings", total_listings)
    
    # Display listings
    if listings:
        for listing in listings:
            st.write(listing)
    else:
        st.info("No listings found. Create your first listing!")


if __name__ == "__main__":
    main()