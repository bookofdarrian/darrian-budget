import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import csv
import io
import requests
from typing import Optional, Dict, List, Tuple

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps: Inventory Aging Report", page_icon="🍑", layout="wide")

init_db()
inject_css()
require_login()

def _ensure_tables():
    """Create necessary tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_aging (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                product_name VARCHAR(500) NOT NULL,
                purchase_date DATE NOT NULL,
                days_on_hand INTEGER DEFAULT 0,
                original_price DECIMAL(10,2) NOT NULL,
                current_market_price DECIMAL(10,2),
                aging_tier VARCHAR(20) DEFAULT 'fresh',
                markdown_suggestion TEXT,
                liquidation_strategy TEXT,
                platform VARCHAR(50),
                size VARCHAR(20),
                condition VARCHAR(50),
                notes TEXT,
                last_price_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_aging_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER REFERENCES soleops_inventory_aging(id),
                alert_type VARCHAR(50) NOT NULL,
                alert_message TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_markdown_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER REFERENCES soleops_inventory_aging(id),
                old_price DECIMAL(10,2),
                new_price DECIMAL(10,2),
                markdown_percent DECIMAL(5,2),
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory_aging (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                product_name TEXT NOT NULL,
                purchase_date DATE NOT NULL,
                days_on_hand INTEGER DEFAULT 0,
                original_price REAL NOT NULL,
                current_market_price REAL,
                aging_tier TEXT DEFAULT 'fresh',
                markdown_suggestion TEXT,
                liquidation_strategy TEXT,
                platform TEXT,
                size TEXT,
                condition TEXT,
                notes TEXT,
                last_price_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_aging_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER,
                alert_type TEXT NOT NULL,
                alert_message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_markdown_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER,
                old_price REAL,
                new_price REAL,
                markdown_percent REAL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# Helper functions
def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def calculate_aging_tier(days_on_hand: int) -> str:
    """Calculate aging tier based on days on hand."""
    if days_on_hand <= 30:
        return "fresh"
    elif days_on_hand <= 60:
        return "aging"
    elif days_on_hand <= 90:
        return "stale"
    else:
        return "critical"

def get_tier_color(tier: str) -> str:
    """Get color for aging tier."""
    colors = {
        "fresh": "#28a745",
        "aging": "#ffc107",
        "stale": "#fd7e14",
        "critical": "#dc3545"
    }
    return colors.get(tier, "#6c757d")

def get_tier_emoji(tier: str) -> str:
    """Get emoji for aging tier."""
    emojis = {
        "fresh": "🟢",
        "aging": "🟡",
        "stale": "🟠",
        "critical": "🔴"
    }
    return emojis.get(tier, "⚪")

def calculate_days_on_hand(purchase_date) -> int:
    """Calculate days on hand from purchase date."""
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    today = datetime.now().date()
    return (today - purchase_date).days

def fetch_market_price(sku: str, product_name: str) -> Optional[float]:
    """Fetch current market price from eBay/Mercari comps (simulated)."""
    # In production, this would call actual eBay/Mercari APIs
    # For now, return None to indicate manual price entry needed
    return None

def generate_markdown_suggestion(days_on_hand: int, original_price: float, current_market_price: Optional[float]) -> str:
    """Generate markdown suggestion based on aging tier."""
    tier = calculate_aging_tier(days_on_hand)
    
    suggestions = {
        "fresh": "No markdown needed. Item is selling well within normal timeframe.",
        "aging": f"Consider 10% markdown to ${original_price * 0.9:.2f}. Item approaching stale status.",
        "stale": f"Recommend 15-20% markdown to ${original_price * 0.85:.2f} - ${original_price * 0.80:.2f}. List on multiple platforms.",
        "critical": f"Urgent: 25%+ markdown to ${original_price * 0.75:.2f} or consider consignment/bundle deal."
    }
    
    if current_market_price and current_market_price < original_price:
        market_diff = ((original_price - current_market_price) / original_price) * 100
        suggestions[tier] += f" Market price is {market_diff:.1f}% below your cost."
    
    return suggestions.get(tier, "Unable to generate suggestion.")

def get_claude_liquidation_strategy(item: Dict) -> str:
    """Get Claude AI liquidation strategy for stale/critical items."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "Configure Anthropic API key in settings for AI-powered strategies."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are a sneaker resale expert. Analyze this stale inventory item and provide a specific liquidation strategy:

Product: {item.get('product_name', 'Unknown')}
SKU: {item.get('sku', 'Unknown')}
Size: {item.get('size', 'Unknown')}
Condition: {item.get('condition', 'Unknown')}
Days on Hand: {item.get('days_on_hand', 0)}
Original Price: ${item.get('original_price', 0):.2f}
Current Market Price: ${item.get('current_market_price', 0):.2f if item.get('current_market_price') else 'Unknown'}

Provide a concise 3-5 sentence liquidation strategy including:
1. Recommended pricing action
2. Best platform(s) to list on
3. Any bundling or promotion tactics
4. Timeline recommendation"""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        return f"AI strategy unavailable: {str(e)}"

def get_user_inventory(user_id: int) -> List[Dict]:
    """Get all inventory items for a user."""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        SELECT id, sku, product_name, purchase_date, days_on_hand, 
               original_price, current_market_price, aging_tier,
               markdown_suggestion, liquidation_strategy, platform,
               size, condition, notes, last_price_check, created_at
        FROM soleops_inventory_aging
        WHERE user_id = {ph}
        ORDER BY days_on_hand DESC
    """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "sku": row[1],
            "product_name": row[2],
            "purchase_date": row[3],
            "days_on_hand": row[4],
            "original_price": row[5],
            "current_market_price": row[6],
            "aging_tier": row[7],
            "markdown_suggestion": row[8],
            "liquidation_strategy": row[9],
            "platform": row[10],
            "size": row[11],
            "condition": row[12],
            "notes": row[13],
            "last_price_check": row[14],
            "created_at": row[15]
        })
    
    return items

def add_inventory_item(user_id: int, data: Dict) -> bool:
    """Add new inventory item."""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    days_on_hand = calculate_days_on_hand(data['purchase_date'])
    aging_tier = calculate_aging_tier(days_on_hand)
    markdown_suggestion = generate_markdown_suggestion(
        days_on_hand, 
        data['original_price'],
        data.get('current_market_price')
    )
    
    try:
        cur.execute(f"""
            INSERT INTO soleops_inventory_aging 
            (user_id, sku, product_name, purchase_date, days_on_hand, 
             original_price, current_market_price, aging_tier, 
             markdown_suggestion, platform, size, condition, notes)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (
            user_id, data['sku'], data['product_name'], data['purchase_date'],
            days_on_hand, data['original_price'], data.get('current_market_price'),
            aging_tier, markdown_suggestion, data.get('platform'),
            data.get('size'), data.get('condition'), data.get('notes')
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Error adding item: {e}")
        return False

def update_inventory_item(item_id: int, user_id: int, data: Dict) -> bool:
    """Update inventory item."""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    days_on_hand = calculate_days_on_hand(data['purchase_date'])
    aging_tier = calculate_aging_tier(days_on_hand)
    markdown_suggestion = generate_markdown_suggestion(
        days_on_hand,
        data['original_price'],
        data.get('current_market_price')
    )
    
    try:
        cur.execute(f"""
            UPDATE soleops_inventory_aging
            SET sku = {ph}, product_name = {ph}, purchase_date = {ph},
                days_on_hand = {ph}, original_price = {ph}, current_market_price = {ph},
                aging_tier = {ph}, markdown_suggestion = {ph}, platform = {ph},
                size = {ph}, condition = {ph}, notes = {ph}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {ph} AND user_id = {ph}
        """, (
            data['sku'], data['product_name'], data['purchase_date'],
            days_on_hand, data['original_price'], data.get('current_market_price'),
            aging_tier, markdown_suggestion, data.get('platform'),
            data.get('size'), data.get('condition'), data.get('notes'),
            item_id, user_id
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Error updating item: {e}")
        return False

def delete_inventory_item(item_id: int, user_id: int) -> bool:
    """Delete inventory item."""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    try:
        cur.execute(f"""
            DELETE FROM soleops_inventory_aging
            WHERE id = {ph} AND user_id = {ph}
        """, (item_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        st.error(f"Error deleting item: {e}")
        return False

def apply_bulk_markdown(user_id: int, item_ids: List[int], markdown_percent: float) -> int:
    """Apply bulk markdown to selected items."""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    updated = 0
    for item_id in item_ids:
        try:
            # Get current price
            cur.execute(f"""
                SELECT original_price, current_market_price
                FROM soleops_inventory_aging
                WHERE id = {ph} AND user_id = {ph}
            """, (item_id, user_id))
            row = cur.fetchone()
            
            if row:
                old_price = row[1] if row[1] else row[0]
                new_price = old_price * (1 - markdown_percent / 100)
                
                # Update price
                cur.execute(f"""
                    UPDATE soleops_inventory_aging
                    SET current_market_price = {ph}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = {ph} AND user_id = {ph}
                """, (new_price, item_id, user_id))
                
                # Log markdown history
                cur.execute(f"""
                    INSERT INTO soleops_markdown_history
                    (user_id, inventory_id, old_price, new_price, markdown_percent, reason)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """, (user_id, item_id, old_price, new_price, markdown_percent, f"Bulk markdown {markdown_percent}%"))
                
                updated += 1
        except Exception as e:
            st.error(f"Error updating item {item_id}: {e}")
    
    conn.commit()
    conn.close()
    return updated

def refresh_all_aging_data(user_id: int) -> int:
    """Refresh aging calculations for all items."""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    # Get all items
    cur.execute(f"""
        SELECT id, purchase_date, original_price, current_market_price
        FROM soleops_inventory_aging
        WHERE user_id = {ph}
    """, (user_id,))
    
    rows = cur.fetchall()
    updated = 0
    
    for row in rows:
        item_id, purchase_date, original_price, current_market_price = row
        days_on_hand = calculate_days_on_hand(purchase_date)
        aging_tier = calculate_aging_tier(days_on_hand)
        markdown_suggestion = generate_markdown_suggestion(days_on_hand, original_price, current_market_price)
        
        cur.execute(f"""
            UPDATE soleops_inventory_aging
            SET days_on_hand = {ph}, aging_tier = {ph}, markdown_suggestion = {ph},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {ph}
        """, (days_on_hand, aging_tier, markdown_suggestion, item_id))
        updated += 1
    
    conn.commit()
    conn.close()
    return updated

def get_tier_distribution(items: List[Dict]) -> Dict[str, int]:
    """Get distribution of items by aging tier."""
    distribution = {"fresh": 0, "aging": 0, "stale": 0, "critical": 0}
    for item in items:
        tier = item.get('aging_tier', 'fresh')
        if tier in distribution:
            distribution[tier] += 1
    return distribution

def get_weekly_digest(items: List[Dict]) -> Dict:
    """Generate weekly aging digest summary."""
    total_items = len(items)
    total_value = sum(item.get('original_price', 0) for item in items)
    
    # Get tier counts
    distribution = get_tier_distribution(items)
    
    # Get top 5 at-risk items (critical and stale, sorted by days)
    at_risk = [item for item in items if item.get('aging_tier') in ['critical', 'stale']]
    at_risk_sorted = sorted(at_risk, key=lambda x: x.get('days_on_hand', 0), reverse=True)[:5]
    
    # Calculate potential loss
    at_risk_value = sum(item.get('original_price', 0) for item in at_risk)
    
    return {
        "total_items": total_items,
        "total_value": total_value,
        "distribution": distribution,
        "at_risk_items": at_risk_sorted,
        "at_risk_value": at_risk_value,
        "at_risk_count": len(at_risk)
    }

def export_to_csv(items: List[Dict]) -> str:
    """Export inventory aging report to CSV."""
    output = io.StringIO()
    fieldnames = [
        'SKU', 'Product Name', 'Purchase Date', 'Days on Hand', 
        'Aging Tier', 'Original Price', 'Current Market Price',
        'Platform', 'Size', 'Condition', 'Markdown Suggestion', 'Notes'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for item in items:
        writer.writerow({
            'SKU': item.get('sku', ''),
            'Product Name': item.get('product_name', ''),
            'Purchase Date': item.get('purchase_date', ''),
            'Days on Hand': item.get('days_on_hand', 0),
            'Aging Tier': item.get('aging_tier', ''),
            'Original Price': item.get('original_price', 0),
            'Current Market Price': item.get('current_market_price', ''),
            'Platform': item.get('platform', ''),
            'Size': item.get('size', ''),
            'Condition': item.get('condition', ''),
            'Markdown Suggestion': item.get('markdown_suggestion', ''),
            'Notes': item.get('notes', '')
        })
    
    return output.getvalue()

# Main UI
st.title("📦 SoleOps: Inventory Aging Report")
st.markdown("Track inventory age, identify stale items, and get AI-powered liquidation strategies.")

user_id = st.session_state.get("user_id", 1)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "📋 Inventory List", "➕ Add Item", "🤖 AI Strategies", "📧 Weekly Digest"
])

# Get inventory data
items = get_user_inventory(user_id)

with tab1:
    st.subheader("Aging Overview")
    
    if not items:
        st.info("No inventory items found. Add items to start tracking aging.")
    else:
        # Refresh button
        col_refresh, col_export = st.columns([1, 1])
        with col_refresh:
            if st.button("🔄 Refresh Aging Data", use_container_width=True):
                updated = refresh_all_aging_data(user_id)
                st.success(f"Refreshed {updated} items")
                st.rerun()
        
        with col_export:
            csv_data = export_to_csv(items)
            st.download_button(
                "📥 Export to CSV",
                data=csv_data,
                file_name=f"aging_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Metrics row
        distribution = get_tier_distribution(items)
        total_value = sum(item.get('original_price', 0) for item in items)
        at_risk_value = sum(
            item.get('original_price', 0) 
            for item in items 
            if item.get('aging_tier') in ['stale', 'critical']
        )
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Items", len(items))
        with col2:
            st.metric("Total Value", f"${total_value:,.2f}")
        with col3:
            st.metric("At Risk Value", f"${at_risk_value:,.2f}")
        with col4:
            avg_days = sum(item.get('days_on_hand', 0) for item in items) / len(items) if items else 0
            st.metric("Avg Days on Hand", f"{avg_days:.0f}")
        with col5:
            critical_count = distribution.get('critical', 0) + distribution.get('stale', 0)
            st.metric("Items Needing Action", critical_count)
        
        st.markdown("---")
        
        # Charts row
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("Aging Tier Distribution")
            
            # Pie chart
            fig = px.pie(
                values=list(distribution.values()),
                names=[f"{get_tier_emoji(k)} {k.title()}" for k in distribution.keys()],
                color=list(distribution.keys()),
                color_discrete_map={
                    "fresh": "#28a745",
                    "aging": "#ffc107",
                    "stale": "#fd7e14",
                    "critical": "#dc3545"
                },
                hole=0.4
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        
        with chart_col2:
            st.subheader("Inventory Value by Tier")
            
            # Calculate value by tier
            tier_values = {"fresh": 0, "aging": 0, "stale": 0, "critical": 0}
            for item in items:
                tier = item.get('aging_tier', 'fresh')
                tier_values[tier] += item.get('original_price', 0)
            
            fig = px.bar(
                x=list(tier_values.keys()),
                y=list(tier_values.values()),
                color=list(tier_values.keys()),
                color_discrete_map={
                    "fresh": "#28a745",
                    "aging": "#ffc107",
                    "stale": "#fd7e14",
                    "critical": "#dc3545"
                },
                labels={'x': 'Aging Tier', 'y': 'Total Value ($)'}
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # Days on hand histogram
        st.subheader("Days on Hand Distribution")
        days_data = [item.get('days_on_hand', 0) for item in items]
        fig = px.histogram(
            x=days_data,
            nbins=20,
            labels={'x': 'Days on Hand', 'y': 'Number of Items'},
            color_discrete_sequence=['#667eea']
        )
        fig.add_vline(x=30, line_dash="dash", line_color="green", annotation_text="Fresh/Aging")
        fig.add_vline(x=60, line_dash="dash", line_color="orange", annotation_text="Aging/Stale")
        fig.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Stale/Critical")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Inventory List")
    
    if not items:
        st.info("No inventory items found. Add items in the 'Add Item' tab.")
    else:
        # Filters
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            tier_filter = st.multiselect(
                "Filter by Tier",
                ["fresh", "aging", "stale", "critical"],
                default=[]
            )
        
        with filter_col2:
            platform_options = list(set(item.get('platform') for item in items if item.get('platform')))
            platform_filter = st.multiselect("Filter by Platform", platform_options, default=[])
        
        with filter_col3:
            sort_by = st.selectbox(
                "Sort by",
                ["Days on Hand (High to Low)", "Days on Hand (Low to High)", 
                 "Price (High to Low)", "Price (Low to High)"]
            )
        
        # Apply filters
        filtered_items = items.copy()
        if tier_filter:
            filtered_items = [i for i in filtered_items if i.get('aging_tier') in tier_filter]
        if platform_filter:
            filtered_items = [i for i in filtered_items if i.get('platform') in platform_filter]
        
        # Apply sorting
        if "Days on Hand (High to Low)" in sort_by:
            filtered_items.sort(key=lambda x: x.get('days_on_hand', 0), reverse=True)
        elif "Days on Hand (Low to High)" in sort_by:
            filtered_items.sort(key=lambda x: x.get('days_on_hand', 0))
        elif "Price (High to Low)" in sort_by:
            filtered_items.sort(key=lambda x: x.get('original_price', 0), reverse=True)
        elif "Price (Low to High)" in sort_by:
            filtered_items.sort(key=lambda x: x.get('original_price', 0))
        
        st.markdown(f"**Showing {len(filtered_items)} of {len(items)} items**")
        
        # Bulk actions
        st.markdown("### Bulk Actions")
        bulk_col1, bulk_col2, bulk_col3, bulk_col4 = st.columns(4)
        
        # Track selected items in session state
        if 'selected_items' not in st.session_state:
            st.session_state.selected_items = []
        
        with bulk_col1:
            if st.button("📉 10% Markdown", use_container_width=True):
                if st.session_state.selected_items:
                    updated = apply_bulk_markdown(user_id, st.session_state.selected_items, 10)
                    st.success(f"Applied 10% markdown to {updated} items")
                    st.rerun()
                else:
                    st.warning("Select items first")
        
        with bulk_col2:
            if st.button("📉 15% Markdown", use_container_width=True):
                if st.session_state.selected_items:
                    updated = apply_bulk_markdown(user_id, st.session_state.selected_items, 15)
                    st.success(f"Applied 15% markdown to {updated} items")
                    st.rerun()
                else:
                    st.warning("Select items first")
        
        with bulk_col3:
            if st.button("📉 20% Markdown", use_container_width=True):
                if st.session_state.selected_items:
                    updated = apply_bulk_markdown(user_id, st.session_state.selected_items, 20)
                    st.success(f"Applied 20% markdown to {updated} items")
                    st.rerun()
                else:
                    st.warning("Select items first")
        
        with bulk_col4:
            if st.button("🗑️ Clear Selection", use_container_width=True):
                st.session_state.selected_items = []
                st.rerun()
        
        st.markdown(f"**Selected: {len(st.session_state.selected_items)} items**")
        
        st.markdown("---")
        
        # Inventory table
        for item in filtered_items:
            tier = item.get('aging_tier', 'fresh')
            tier_color = get_tier_color(tier)
            tier_emoji = get_tier_emoji(tier)
            
            with st.container():
                col1, col2, col3, col4,