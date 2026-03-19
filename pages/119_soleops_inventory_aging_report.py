import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import csv
import io

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Inventory Aging Report", page_icon="🍑", layout="wide")
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


def _ensure_tables():
    """Create necessary tables for inventory aging report."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        # Inventory aging snapshots table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_aging_snapshots (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                snapshot_date DATE NOT NULL,
                bucket_0_30_count INTEGER DEFAULT 0,
                bucket_0_30_value DECIMAL(12,2) DEFAULT 0,
                bucket_31_60_count INTEGER DEFAULT 0,
                bucket_31_60_value DECIMAL(12,2) DEFAULT 0,
                bucket_61_90_count INTEGER DEFAULT 0,
                bucket_61_90_value DECIMAL(12,2) DEFAULT 0,
                bucket_90_plus_count INTEGER DEFAULT 0,
                bucket_90_plus_value DECIMAL(12,2) DEFAULT 0,
                total_inventory_count INTEGER DEFAULT 0,
                total_inventory_value DECIMAL(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, snapshot_date)
            )
        """)
        
        # Sneaker inventory table (if not exists from other SoleOps pages)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                brand VARCHAR(100),
                model VARCHAR(255),
                colorway VARCHAR(255),
                size VARCHAR(20),
                condition VARCHAR(50) DEFAULT 'New',
                purchase_date DATE,
                purchase_price DECIMAL(10,2),
                purchase_source VARCHAR(100),
                listed_price DECIMAL(10,2),
                platform VARCHAR(50),
                status VARCHAR(50) DEFAULT 'In Stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Aging recommendations table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_aging_recommendations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                recommendation_date DATE NOT NULL,
                days_in_stock INTEGER,
                current_price DECIMAL(10,2),
                recommended_price DECIMAL(10,2),
                markdown_percentage DECIMAL(5,2),
                ai_reasoning TEXT,
                status VARCHAR(50) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite versions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_aging_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                snapshot_date DATE NOT NULL,
                bucket_0_30_count INTEGER DEFAULT 0,
                bucket_0_30_value REAL DEFAULT 0,
                bucket_31_60_count INTEGER DEFAULT 0,
                bucket_31_60_value REAL DEFAULT 0,
                bucket_61_90_count INTEGER DEFAULT 0,
                bucket_61_90_value REAL DEFAULT 0,
                bucket_90_plus_count INTEGER DEFAULT 0,
                bucket_90_plus_value REAL DEFAULT 0,
                total_inventory_count INTEGER DEFAULT 0,
                total_inventory_value REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, snapshot_date)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                brand TEXT,
                model TEXT,
                colorway TEXT,
                size TEXT,
                condition TEXT DEFAULT 'New',
                purchase_date DATE,
                purchase_price REAL,
                purchase_source TEXT,
                listed_price REAL,
                platform TEXT,
                status TEXT DEFAULT 'In Stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_aging_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                inventory_id INTEGER NOT NULL,
                recommendation_date DATE NOT NULL,
                days_in_stock INTEGER,
                current_price REAL,
                recommended_price REAL,
                markdown_percentage REAL,
                ai_reasoning TEXT,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_inventory_with_aging(user_id):
    """Get all inventory items with calculated days in stock."""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, sku, brand, model, colorway, size, condition, 
               purchase_date, purchase_price, purchase_source,
               listed_price, platform, status, notes
        FROM soleops_inventory
        WHERE user_id = {ph} AND status = 'In Stock'
        ORDER BY purchase_date ASC
    """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    items = []
    today = datetime.now().date()
    
    for row in rows:
        purchase_date = row[7]
        if purchase_date:
            if isinstance(purchase_date, str):
                purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
            days_in_stock = (today - purchase_date).days
        else:
            days_in_stock = 0
        
        # Determine aging bucket
        if days_in_stock <= 30:
            bucket = "0-30 Days"
        elif days_in_stock <= 60:
            bucket = "31-60 Days"
        elif days_in_stock <= 90:
            bucket = "61-90 Days"
        else:
            bucket = "90+ Days"
        
        items.append({
            "id": row[0],
            "sku": row[1] or "N/A",
            "brand": row[2] or "Unknown",
            "model": row[3] or "Unknown",
            "colorway": row[4] or "",
            "size": row[5] or "",
            "condition": row[6] or "New",
            "purchase_date": row[7],
            "purchase_price": float(row[8]) if row[8] else 0,
            "purchase_source": row[9] or "",
            "listed_price": float(row[10]) if row[10] else 0,
            "platform": row[11] or "",
            "status": row[12] or "In Stock",
            "notes": row[13] or "",
            "days_in_stock": days_in_stock,
            "aging_bucket": bucket
        })
    
    return items


def calculate_aging_buckets(items):
    """Calculate aging bucket statistics."""
    buckets = {
        "0-30 Days": {"count": 0, "value": 0, "items": []},
        "31-60 Days": {"count": 0, "value": 0, "items": []},
        "61-90 Days": {"count": 0, "value": 0, "items": []},
        "90+ Days": {"count": 0, "value": 0, "items": []}
    }
    
    for item in items:
        bucket = item["aging_bucket"]
        buckets[bucket]["count"] += 1
        buckets[bucket]["value"] += item["purchase_price"]
        buckets[bucket]["items"].append(item)
    
    return buckets


def save_aging_snapshot(user_id, buckets):
    """Save daily aging snapshot to database."""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    today = datetime.now().date()
    
    total_count = sum(b["count"] for b in buckets.values())
    total_value = sum(b["value"] for b in buckets.values())
    
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO inventory_aging_snapshots 
            (user_id, snapshot_date, bucket_0_30_count, bucket_0_30_value,
             bucket_31_60_count, bucket_31_60_value, bucket_61_90_count, bucket_61_90_value,
             bucket_90_plus_count, bucket_90_plus_value, total_inventory_count, total_inventory_value)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ON CONFLICT (user_id, snapshot_date) 
            DO UPDATE SET 
                bucket_0_30_count = EXCLUDED.bucket_0_30_count,
                bucket_0_30_value = EXCLUDED.bucket_0_30_value,
                bucket_31_60_count = EXCLUDED.bucket_31_60_count,
                bucket_31_60_value = EXCLUDED.bucket_31_60_value,
                bucket_61_90_count = EXCLUDED.bucket_61_90_count,
                bucket_61_90_value = EXCLUDED.bucket_61_90_value,
                bucket_90_plus_count = EXCLUDED.bucket_90_plus_count,
                bucket_90_plus_value = EXCLUDED.bucket_90_plus_value,
                total_inventory_count = EXCLUDED.total_inventory_count,
                total_inventory_value = EXCLUDED.total_inventory_value
        """, (
            user_id, today,
            buckets["0-30 Days"]["count"], buckets["0-30 Days"]["value"],
            buckets["31-60 Days"]["count"], buckets["31-60 Days"]["value"],
            buckets["61-90 Days"]["count"], buckets["61-90 Days"]["value"],
            buckets["90+ Days"]["count"], buckets["90+ Days"]["value"],
            total_count, total_value
        ))
    else:
        cur.execute(f"""
            INSERT OR REPLACE INTO inventory_aging_snapshots 
            (user_id, snapshot_date, bucket_0_30_count, bucket_0_30_value,
             bucket_31_60_count, bucket_31_60_value, bucket_61_90_count, bucket_61_90_value,
             bucket_90_plus_count, bucket_90_plus_value, total_inventory_count, total_inventory_value)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (
            user_id, today,
            buckets["0-30 Days"]["count"], buckets["0-30 Days"]["value"],
            buckets["31-60 Days"]["count"], buckets["31-60 Days"]["value"],
            buckets["61-90 Days"]["count"], buckets["61-90 Days"]["value"],
            buckets["90+ Days"]["count"], buckets["90+ Days"]["value"],
            total_count, total_value
        ))
    
    conn.commit()
    conn.close()


def get_aging_history(user_id, days=90):
    """Get historical aging snapshots for trend analysis."""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    cutoff_date = (datetime.now() - timedelta(days=days)).date()
    
    cur.execute(f"""
        SELECT snapshot_date, bucket_0_30_count, bucket_0_30_value,
               bucket_31_60_count, bucket_31_60_value,
               bucket_61_90_count, bucket_61_90_value,
               bucket_90_plus_count, bucket_90_plus_value,
               total_inventory_count, total_inventory_value
        FROM inventory_aging_snapshots
        WHERE user_id = {ph} AND snapshot_date >= {ph}
        ORDER BY snapshot_date ASC
    """, (user_id, cutoff_date))
    
    rows = cur.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "date": row[0],
            "0-30 Days": {"count": row[1], "value": float(row[2]) if row[2] else 0},
            "31-60 Days": {"count": row[3], "value": float(row[4]) if row[4] else 0},
            "61-90 Days": {"count": row[5], "value": float(row[6]) if row[6] else 0},
            "90+ Days": {"count": row[7], "value": float(row[8]) if row[8] else 0},
            "total_count": row[9],
            "total_value": float(row[10]) if row[10] else 0
        })
    
    return history


def get_ai_markdown_recommendations(aged_items):
    """Use Claude AI to generate markdown pricing recommendations."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    
    if not aged_items:
        return []
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        # Prepare inventory summary for AI
        inventory_summary = []
        for item in aged_items[:20]:  # Limit to 20 items for API
            inventory_summary.append({
                "model": f"{item['brand']} {item['model']}",
                "size": item['size'],
                "days_in_stock": item['days_in_stock'],
                "purchase_price": item['purchase_price'],
                "listed_price": item['listed_price'],
                "platform": item['platform']
            })
        
        prompt = f"""You are a sneaker resale pricing expert. Analyze this aged inventory and provide markdown pricing recommendations.

Inventory items (60+ days old):
{json.dumps(inventory_summary, indent=2)}

For each item, provide:
1. Recommended markdown percentage (be aggressive for 90+ day items)
2. Suggested new price
3. Brief reasoning (market conditions, seasonal factors, demand trends)

Consider:
- Items 60-90 days: 10-20% markdown typically
- Items 90+ days: 20-35% markdown to move quickly
- Factor in original purchase price to avoid selling at a loss unless necessary
- Consider platform fees (eBay ~13%, Mercari ~10%)

Return a JSON array with objects containing:
- model, size, days_in_stock, current_price, recommended_price, markdown_percentage, reasoning

Return ONLY valid JSON, no other text."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        # Try to extract JSON from response
        if response_text.startswith("["):
            recommendations = json.loads(response_text)
        else:
            # Try to find JSON array in response
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                recommendations = json.loads(json_match.group())
            else:
                return []
        
        return recommendations
        
    except Exception as e:
        st.error(f"AI recommendation error: {str(e)}")
        return []


def save_recommendation(user_id, inventory_id, days_in_stock, current_price, 
                       recommended_price, markdown_pct, reasoning):
    """Save AI recommendation to database."""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    today = datetime.now().date()
    
    cur.execute(f"""
        INSERT INTO inventory_aging_recommendations
        (user_id, inventory_id, recommendation_date, days_in_stock,
         current_price, recommended_price, markdown_percentage, ai_reasoning)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, inventory_id, today, days_in_stock, 
          current_price, recommended_price, markdown_pct, reasoning))
    
    conn.commit()
    conn.close()


def add_sample_inventory(user_id):
    """Add sample inventory for demonstration."""
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    today = datetime.now().date()
    
    sample_items = [
        ("DQ8423-100", "Nike", "Air Force 1 Low", "White/White", "10", "New", 
         today - timedelta(days=15), 90.00, "Foot Locker", 130.00, "eBay"),
        ("DH8009-100", "Nike", "Dunk Low Panda", "White/Black", "9.5", "New",
         today - timedelta(days=45), 110.00, "Nike.com", 165.00, "eBay"),
        ("555088-134", "Jordan", "Air Jordan 1 Retro High OG", "Chicago", "11", "New",
         today - timedelta(days=75), 180.00, "SNKRS", 280.00, "StockX"),
        ("DM9036-104", "Nike", "Air Max 90", "Infrared", "10.5", "New",
         today - timedelta(days=95), 120.00, "Finish Line", 160.00, "Mercari"),
        ("CW2288-111", "Nike", "Air Force 1 '07", "Triple White", "12", "New",
         today - timedelta(days=120), 100.00, "Nike.com", 125.00, "eBay"),
        ("553558-052", "Jordan", "Air Jordan 1 Low", "Shadow", "9", "New",
         today - timedelta(days=35), 130.00, "Champs", 175.00, "Mercari"),
        ("DD1503-101", "Nike", "Dunk High", "Championship White", "10", "New",
         today - timedelta(days=65), 125.00, "Nike.com", 180.00, "eBay"),
        ("CT8532-104", "Jordan", "Air Jordan 4 Retro", "White Oreo", "11", "New",
         today - timedelta(days=105), 200.00, "SNKRS", 275.00, "StockX"),
    ]
    
    for item in sample_items:
        cur.execute(f"""
            INSERT INTO soleops_inventory 
            (user_id, sku, brand, model, colorway, size, condition, 
             purchase_date, purchase_price, purchase_source, listed_price, platform, status)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'In Stock')
        """, (user_id,) + item)
    
    conn.commit()
    conn.close()


def export_aging_report_csv(items, buckets):
    """Generate CSV export of aging report."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Summary section
    writer.writerow(["INVENTORY AGING REPORT"])
    writer.writerow(["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    
    # Bucket summary
    writer.writerow(["AGING BUCKET SUMMARY"])
    writer.writerow(["Bucket", "Item Count", "Total Value", "Avg Value per Item"])
    for bucket_name, bucket_data in buckets.items():
        avg_value = bucket_data["value"] / bucket_data["count"] if bucket_data["count"] > 0 else 0
        writer.writerow([bucket_name, bucket_data["count"], f"${bucket_data['value']:.2f}", f"${avg_value:.2f}"])
    
    writer.writerow([])
    
    # Detailed inventory
    writer.writerow(["DETAILED INVENTORY"])
    writer.writerow(["SKU", "Brand", "Model", "Colorway", "Size", "Condition", 
                    "Purchase Date", "Purchase Price", "Listed Price", "Platform",
                    "Days in Stock", "Aging Bucket"])
    
    for item in items:
        writer.writerow([
            item["sku"], item["brand"], item["model"], item["colorway"],
            item["size"], item["condition"], item["purchase_date"],
            f"${item['purchase_price']:.2f}", f"${item['listed_price']:.2f}",
            item["platform"], item["days_in_stock"], item["aging_bucket"]
        ])
    
    return output.getvalue()


# Initialize tables
_ensure_tables()

# Get user ID
user_id = st.session_state.get("user_id", 1)

# Main UI
st.title("📦 SoleOps Inventory Aging Report")
st.markdown("*Track inventory age, capital at risk, and get AI markdown recommendations*")

# Load inventory data
items = get_inventory_with_aging(user_id)
buckets = calculate_aging_buckets(items)

# Save today's snapshot
if items:
    save_aging_snapshot(user_id, buckets)

# Top metrics
col1, col2, col3, col4, col5 = st.columns(5)

total_items = sum(b["count"] for b in buckets.values())
total_value = sum(b["value"] for b in buckets.values())
aged_items_count = buckets["61-90 Days"]["count"] + buckets["90+ Days"]["count"]
aged_items_value = buckets["61-90 Days"]["value"] + buckets["90+ Days"]["value"]
avg_age = sum(item["days_in_stock"] for item in items) / len(items) if items else 0

with col1:
    st.metric("Total Inventory", f"{total_items} pairs")
with col2:
    st.metric("Capital Tied Up", f"${total_value:,.2f}")
with col3:
    st.metric("Aged Items (60+ days)", f"{aged_items_count} pairs")
with col4:
    st.metric("Capital at Risk", f"${aged_items_value:,.2f}")
with col5:
    st.metric("Avg Days in Stock", f"{avg_age:.0f} days")

st.markdown("---")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Aging Overview", "📋 Detailed Inventory", "🤖 AI Recommendations", 
    "📈 Aging Trends", "⚙️ Settings"
])

with tab1:
    if not items:
        st.info("No inventory items found. Add inventory or load sample data to see aging analysis.")
        if st.button("📦 Load Sample Inventory Data"):
            add_sample_inventory(user_id)
            st.success("Sample inventory loaded!")
            st.rerun()
    else:
        # Aging distribution chart
        st.subheader("📊 Inventory Aging Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Count by bucket
            bucket_df = pd.DataFrame([
                {"Bucket": k, "Count": v["count"], "Value": v["value"]}
                for k, v in buckets.items()
            ])
            
            fig_count = px.bar(
                bucket_df, x="Bucket", y="Count",
                title="Item Count by Aging Bucket",
                color="Bucket",
                color_discrete_map={
                    "0-30 Days": "#2ecc71",
                    "31-60 Days": "#f39c12",
                    "61-90 Days": "#e67e22",
                    "90+ Days": "#e74c3c"
                }
            )
            fig_count.update_layout(showlegend=False)
            st.plotly_chart(fig_count, use_container_width=True)
        
        with col2:
            # Value by bucket
            fig_value = px.bar(
                bucket_df, x="Bucket", y="Value",
                title="Capital Tied Up by Aging Bucket ($)",
                color="Bucket",
                color_discrete_map={
                    "0-30 Days": "#2ecc71",
                    "31-60 Days": "#f39c12",
                    "61-90 Days": "#e67e22",
                    "90+ Days": "#e74c3c"
                }
            )
            fig_value.update_layout(showlegend=False)
            st.plotly_chart(fig_value, use_container_width=True)
        
        # Pie chart of distribution
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = px.pie(
                bucket_df, values="Count", names="Bucket",
                title="Inventory Distribution by Age",
                color="Bucket",
                color_discrete_map={
                    "0-30 Days": "#2ecc71",
                    "31-60 Days": "#f39c12",
                    "61-90 Days": "#e67e22",
                    "90+ Days": "#e74c3c"
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Capital at risk gauge
            risk_pct = (aged_items_value / total_value * 100) if total_value > 0 else 0
            
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=risk_pct,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Capital at Risk (60+ days)"},
                delta={'reference': 20},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#e74c3c" if risk_pct > 30 else "#f39c12" if risk_pct > 15 else "#2ecc71"},
                    'steps': [
                        {'range': [0, 15], 'color': "#d5f5e3"},
                        {'range': [15, 30], 'color': "#fdebd0"},
                        {'range': [30, 100], 'color': "#fadbd8"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 30
                    }
                }
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Bucket details
        st.subheader("📦 Bucket Details")
        
        for bucket_name in ["0-30 Days", "31-60 Days", "61-90 Days", "90+ Days"]:
            bucket_data = buckets[bucket_name]
            if bucket_data["count"] > 0:
                with st.expander(f"{bucket_name}: {bucket_data['count']} items (${bucket_data['value']:,.2f})", expanded=(bucket_name in ["61-90 Days", "90+ Days"])):
                    bucket_items = bucket_data["items"]
                    df = pd.DataFrame(bucket_items)
                    df_display = df[["sku", "brand", "model", "size", "purchase_price", "listed_price", "days_in_stock", "platform"]]
                    df_display.columns = ["SKU", "Brand", "Model", "Size", "Cost", "Listed", "Days", "Platform"]
                    st.dataframe(df_display, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("📋 Detailed Inventory Table")
    
    if not items:
        st.info("No inventory items to display.")
    else:
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            filter_bucket = st.selectbox(
                "Filter by Age Bucket",
                ["All"] + list(buckets.keys())
            )
        
        with col2:
            brands = list(set(item["brand"] for item in items))
            filter_brand = st.selectbox("Filter by Brand", ["All"] + brands)
        
        with col3:
            platforms = list(set(item["platform"] for item in items if item["platform"]))
            filter_platform = st.selectbox("Filter by Platform", ["All"] + platforms)
        
        with col4:
            sort_by = st.selectbox(
                "Sort By",
                ["Days in Stock (High to Low)", "Days in Stock (Low to High)",
                 "Cost (High to Low)", "Cost (Low to High)"]
            )
        
        # Apply filters
        filtered_items = items.copy()
        
        if filter_bucket != "All":
            filtered_items = [i for i in filtered_items if i["aging_bucket"] == filter_bucket]
        
        if filter_brand != "All":
            filtered_items = [i for i in filtered_items if i["brand"] == filter_brand]
        
        if filter_platform != "All":
            filtered_items = [i for i in filtered_items if i["platform"] == filter_platform]