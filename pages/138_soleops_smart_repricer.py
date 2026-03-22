import streamlit as st
import json
import datetime
from decimal import Decimal, ROUND_HALF_UP
import requests

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Smart Repricer", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

PH = "%s" if USE_POSTGRES else "?"


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS repricing_rules (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            rule_name TEXT NOT NULL,
            strategy TEXT NOT NULL,
            beat_by_percent REAL DEFAULT 0,
            floor_price REAL DEFAULT 0,
            min_margin_percent REAL DEFAULT 10,
            max_discount_percent REAL DEFAULT 30,
            apply_to_stale_only INTEGER DEFAULT 0,
            stale_days_threshold INTEGER DEFAULT 30,
            is_active INTEGER DEFAULT 1,
            auto_apply INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS repricing_history (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            inventory_id INTEGER,
            sku TEXT,
            item_name TEXT,
            platform TEXT,
            old_price REAL NOT NULL,
            new_price REAL NOT NULL,
            price_change REAL NOT NULL,
            change_percent REAL NOT NULL,
            rule_id INTEGER,
            rule_name TEXT,
            reason TEXT,
            margin_before REAL,
            margin_after REAL,
            was_auto_applied INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES repricing_rules(id)
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS repricing_queue (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            inventory_id INTEGER,
            sku TEXT,
            item_name TEXT,
            platform TEXT,
            current_price REAL NOT NULL,
            recommended_price REAL NOT NULL,
            price_change REAL NOT NULL,
            change_percent REAL NOT NULL,
            rule_id INTEGER,
            rule_name TEXT,
            reason TEXT,
            competitor_price REAL,
            market_avg_price REAL,
            cost_basis REAL,
            current_margin REAL,
            projected_margin REAL,
            priority_score REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES repricing_rules(id)
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_competitor_prices (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT,
            item_name TEXT,
            platform TEXT,
            competitor_name TEXT,
            competitor_price REAL,
            shipping_cost REAL DEFAULT 0,
            total_price REAL,
            condition TEXT,
            listing_url TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_market_trends (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT,
            item_name TEXT,
            platform TEXT,
            avg_price_7d REAL,
            avg_price_30d REAL,
            price_trend TEXT,
            trend_percent REAL,
            volume_7d INTEGER,
            volume_30d INTEGER,
            demand_score REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_inventory (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku TEXT,
            item_name TEXT,
            platform TEXT,
            current_price REAL,
            cost_basis REAL,
            quantity INTEGER DEFAULT 1,
            listed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()


_ensure_tables()

st.title("🍑 SoleOps Smart Repricer")
st.markdown("Automatically optimize your pricing to maximize profits and stay competitive.")