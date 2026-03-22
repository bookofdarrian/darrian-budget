import streamlit as st
import json
import os
from datetime import datetime, timedelta, time
from typing import Optional, Dict, List, Any
import pytz

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Daily Briefing Digest", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def _ph(count: int = 1) -> str:
    """Return correct placeholder(s) for current DB backend."""
    placeholder = "%s" if USE_POSTGRES else "?"
    return ", ".join([placeholder] * count)

def _ensure_tables():
    """Create all required tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Main briefings table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_daily_briefings (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            briefing_date DATE NOT NULL,
            briefing_content TEXT NOT NULL,
            market_data JSON,
            stale_inventory_data JSON,
            opportunities_data JSON,
            pending_orders_data JSON,
            delivery_status VARCHAR(50) DEFAULT 'pending',
            telegram_message_id VARCHAR(100),
            delivered_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Briefing settings table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_briefing_settings (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            delivery_time TIME DEFAULT '08:00:00',
            timezone VARCHAR(50) DEFAULT 'America/New_York',
            telegram_chat_id VARCHAR(100),
            include_market_moves BOOLEAN DEFAULT TRUE,
            include_stale_inventory BOOLEAN DEFAULT TRUE,
            include_opportunities BOOLEAN DEFAULT TRUE,
            include_pending_orders BOOLEAN DEFAULT TRUE,
            stale_threshold_days INTEGER DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ensure soleops_inventory exists for stale inventory checks
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_inventory (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku VARCHAR(100),
            name VARCHAR(255) NOT NULL,
            brand VARCHAR(100),
            size VARCHAR(20),
            condition VARCHAR(50),
            purchase_price DECIMAL(10,2),
            list_price DECIMAL(10,2),
            platform VARCHAR(50),
            status VARCHAR(50) DEFAULT 'active',
            listed_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ensure soleops_orders exists for pending orders
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_orders (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            order_id VARCHAR(100),
            platform VARCHAR(50),
            item_name VARCHAR(255),
            sale_price DECIMAL(10,2),
            buyer_name VARCHAR(255),
            status VARCHAR(50) DEFAULT 'pending',
            order_date TIMESTAMP,
            shipped_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ensure soleops_watchlist exists for market moves
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_watchlist (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku VARCHAR(100),
            name VARCHAR(255) NOT NULL,
            target_buy_price DECIMAL(10,2),
            current_market_price DECIMAL(10,2),
            price_24h_ago DECIMAL(10,2),
            last_updated TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Price history for market moves
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_price_history (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            sku VARCHAR(100),
            price DECIMAL(10,2),
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()

def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Get user's briefing settings."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM soleops_briefing_settings WHERE user_id = {_ph()}", (user_id,))
    row = cur.fetchone()
    if row:
        columns = [desc[0] for desc in cur.description]
        return dict(zip(columns, row))
    return {}

def save_user_settings(user_id: int, settings: Dict[str, Any]) -> None:
    """Save user's briefing settings."""
    conn = get_conn()
    cur = conn.cursor()
    
    existing = get_user_settings(user_id)
    if existing:
        cur.execute(f"""
            UPDATE soleops_briefing_settings 
            SET enabled = {_ph()}, delivery_time = {_ph()}, timezone = {_ph()},
                telegram_chat_id = {_ph()}, include_market_moves = {_ph()},
                include_stale_inventory = {_ph()}, include_opportunities = {_ph()},
                include_pending_orders = {_ph()}, stale_threshold_days = {_ph()},
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = {_ph()}
        """, (
            settings.get('enabled', True),
            settings.get('delivery_time', '08:00:00'),
            settings.get('timezone', 'America/New_York'),
            settings.get('telegram_chat_id'),
            settings.get('include_market_moves', True),
            settings.get('include_stale_inventory', True),
            settings.get('include_opportunities', True),
            settings.get('include_pending_orders', True),
            settings.get('stale_threshold_days', 30),
            user_id
        ))
    else:
        cur.execute(f"""
            INSERT INTO soleops_briefing_settings 
            (user_id, enabled, delivery_time, timezone, telegram_chat_id,
             include_market_moves, include_stale_inventory, include_opportunities,
             include_pending_orders, stale_threshold_days)
            VALUES ({_ph(10)})
        """, (
            user_id,
            settings.get('enabled', True),
            settings.get('delivery_time', '08:00:00'),
            settings.get('timezone', 'America/New_York'),
            settings.get('telegram_chat_id'),
            settings.get('include_market_moves', True),
            settings.get('include_stale_inventory', True),
            settings.get('include_opportunities', True),
            settings.get('include_pending_orders', True),
            settings.get('stale_threshold_days', 30)
        ))
    conn.commit()

def get_stale_inventory(user_id: int, threshold_days: int = 30) -> List[Dict[str, Any]]:
    """Get inventory items that have been listed for more than threshold days."""
    conn = get_conn()
    cur = conn.cursor()
    cutoff_date = datetime.now() - timedelta(days=threshold_days)
    cur.execute(f"""
        SELECT * FROM soleops_inventory 
        WHERE user_id = {_ph()} AND status = 'active' 
        AND listed_date < {_ph()}
        ORDER BY listed_date ASC
    """, (user_id, cutoff_date.date()))
    rows = cur.fetchall()
    if rows:
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    return []

def get_pending_orders(user_id: int) -> List[Dict[str, Any]]:
    """Get pending orders that need attention."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT * FROM soleops_orders 
        WHERE user_id = {_ph()} AND status = 'pending'
        ORDER BY order_date ASC
    """, (user_id,))
    rows = cur.fetchall()
    if rows:
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    return []

def generate_briefing(user_id: int, settings: Dict[str, Any]) -> str:
    """Generate the daily briefing content."""
    briefing_parts = []
    briefing_parts.append("🍑 **SoleOps Daily Briefing**")
    briefing_parts.append(f"📅 {datetime.now().strftime('%A, %B %d, %Y')}")
    briefing_parts.append("---")
    
    if settings.get('include_stale_inventory', True):
        stale_data = get_stale_inventory(user_id, settings.get('stale_threshold_days', 30))
        if stale_data:
            briefing_parts.append(f"📦 **Stale Inventory ({len(stale_data)} items)**")
            for item in stale_data[:5]:
                briefing_parts.append(f"  • {item.get('name', 'Unknown')} - Listed: {item.get('listed_date', 'N/A')}")
            if len(stale_data) > 5:
                briefing_parts.append(f"  ... and {len(stale_data) - 5} more")
            briefing_parts.append("")
    
    if settings.get('include_pending_orders', True):
        pending = get_pending_orders(user_id)
        if pending:
            briefing_parts.append(f"📋 **Pending Orders ({len(pending)})**")
            for order in pending[:5]:
                briefing_parts.append(f"  • {order.get('item_name', 'Unknown')} - {order.get('platform', 'N/A')}")
            if len(pending) > 5:
                briefing_parts.append(f"  ... and {len(pending) - 5} more")
            briefing_parts.append("")
    
    return "\n".join(briefing_parts)

# Initialize tables
_ensure_tables()

# Main UI
st.title("🍑 SoleOps Daily Briefing Digest")
st.markdown("Configure your daily briefing preferences and view past briefings.")

user_id = st.session_state.get('user_id', 1)

# Load settings
settings = get_user_settings(user_id)

tab1, tab2, tab3 = st.tabs(["⚙️ Settings", "📋 Preview", "📜 History"])

with tab1:
    st.subheader("Briefing Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        enabled = st.checkbox("Enable Daily Briefings", value=settings.get('enabled', True))
        delivery_time = st.time_input("Delivery Time", value=time(8, 0))
        timezone = st.selectbox("Timezone", options=pytz.common_timezones, 
                               index=pytz.common_timezones.index(settings.get('timezone', 'America/New_York')))
    
    with col2:
        telegram_chat_id = st.text_input("Telegram Chat ID", value=settings.get('telegram_chat_id', ''))
        stale_threshold = st.number_input("Stale Inventory Threshold (days)", 
                                          min_value=7, max_value=365, 
                                          value=settings.get('stale_threshold_days', 30))
    
    st.subheader("Include in Briefing")
    col3, col4 = st.columns(2)
    with col3:
        include_market = st.checkbox("Market Moves", value=settings.get('include_market_moves', True))
        include_stale = st.checkbox("Stale Inventory", value=settings.get('include_stale_inventory', True))
    with col4:
        include_opps = st.checkbox("Opportunities", value=settings.get('include_opportunities', True))
        include_pending = st.checkbox("Pending Orders", value=settings.get('include_pending_orders', True))
    
    if st.button("💾 Save Settings"):
        new_settings = {
            'enabled': enabled,
            'delivery_time': str(delivery_time),
            'timezone': timezone,
            'telegram_chat_id': telegram_chat_id,
            'include_market_moves': include_market,
            'include_stale_inventory': include_stale,
            'include_opportunities': include_opps,
            'include_pending_orders': include_pending,
            'stale_threshold_days': stale_threshold
        }
        save_user_settings(user_id, new_settings)
        st.success("Settings saved successfully!")

with tab2:
    st.subheader("Briefing Preview")
    if st.button("🔄 Generate Preview"):
        preview_settings = {
            'include_market_moves': settings.get('include_market_moves', True),
            'include_stale_inventory': settings.get('include_stale_inventory', True),
            'include_opportunities': settings.get('include_opportunities', True),
            'include_pending_orders': settings.get('include_pending_orders', True),
            'stale_threshold_days': settings.get('stale_threshold_days', 30)
        }
        briefing = generate_briefing(user_id, preview_settings)
        st.markdown(briefing)

with tab3:
    st.subheader("Briefing History")
    st.info("Past briefings will appear here once delivered.")