import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import io

st.set_page_config(page_title="SoleOps Sold Order Tracker", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS soleops_sold_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                order_id VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                sku VARCHAR(100),
                item_name VARCHAR(255),
                buyer_name VARCHAR(255),
                buyer_email VARCHAR(255),
                sale_price DECIMAL(10,2) NOT NULL,
                platform_fees DECIMAL(10,2) DEFAULT 0,
                shipping_cost DECIMAL(10,2) DEFAULT 0,
                cogs DECIMAL(10,2) DEFAULT 0,
                net_profit DECIMAL(10,2) DEFAULT 0,
                sold_date DATE NOT NULL,
                shipped_date DATE,
                delivered_date DATE,
                tracking_number VARCHAR(100),
                carrier VARCHAR(50),
                status VARCHAR(50) DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_user_id ON soleops_sold_orders(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_platform ON soleops_sold_orders(platform)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_status ON soleops_sold_orders(status)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_sold_date ON soleops_sold_orders(sold_date)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sold_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                sku TEXT,
                item_name TEXT,
                buyer_name TEXT,
                buyer_email TEXT,
                sale_price REAL NOT NULL,
                platform_fees REAL DEFAULT 0,
                shipping_cost REAL DEFAULT 0,
                cogs REAL DEFAULT 0,
                net_profit REAL DEFAULT 0,
                sold_date TEXT NOT NULL,
                shipped_date TEXT,
                delivered_date TEXT,
                tracking_number TEXT,
                carrier TEXT,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_user_id ON soleops_sold_orders(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_platform ON soleops_sold_orders(platform)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_status ON soleops_sold_orders(status)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_orders_sold_date ON soleops_sold_orders(sold_date)
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

PLATFORM_FEES = {
    "eBay": {"rate": 0.1325, "fixed": 0.30, "name": "eBay (13.25% + $0.30)"},
    "Mercari": {"rate": 0.10, "fixed": 0, "name": "Mercari (10%)"},
    "Depop": {"rate": 0.10, "fixed": 0, "name": "Depop (10%)"},
    "StockX": {"rate": 0.10, "fixed": 0, "name": "StockX (10%)"},
    "GOAT": {"rate": 0.095, "fixed": 5, "name": "GOAT (9.5% + $5)"},
    "Local/Cash": {"rate": 0, "fixed": 0, "name": "Local/Cash (0%)"},
    "Other": {"rate": 0, "fixed": 0, "name": "Other"}
}

ORDER_STATUSES = ["pending", "shipped", "in_transit", "delivered", "cancelled", "returned"]
CARRIERS = ["USPS", "UPS", "FedEx", "DHL", "Other"]

def calculate_platform_fees(sale_price: float, platform: str) -> float:
    if platform not in PLATFORM_FEES:
        return 0
    fee_info = PLATFORM_FEES[platform]
    return round(sale_price * fee_info["rate"] + fee_info["fixed"], 2)

def calculate_net_profit(sale_price: float, platform_fees: float, shipping_cost: float, cogs: float) -> float:
    return round(sale_price - platform_fees - shipping_cost - cogs, 2)

def get_user_id():
    return st.session_state.get("user_id", 1)

def add_sold_order(order_data: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO soleops_sold_orders 
            (user_id, order_id, platform, sku, item_name, buyer_name, buyer_email,
             sale_price, platform_fees, shipping_cost, cogs, net_profit,
             sold_date, shipped_date, tracking_number, carrier, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, order_data["order_id"], order_data["platform"], order_data.get("sku"),
            order_data.get("item_name"), order_data.get("buyer_name"), order_data.get("buyer_email"),
            order_data["sale_price"], order_data["platform_fees"], order_data["shipping_cost"],
            order_data["cogs"], order_data["net_profit"], order_data["sold_date"],
            order_data.get("shipped_date"), order_data.get("tracking_number"),
            order_data.get("carrier"), order_data.get("status", "pending"), order_data.get("notes")
        ))
        order_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO soleops_sold_orders 
            (user_id, order_id, platform, sku, item_name, buyer_name, buyer_email,
             sale_price, platform_fees, shipping_cost, cogs, net_profit,
             sold_date, shipped_date, tracking_number, carrier, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, order_data["order_id"], order_data["platform"], order_data.get("sku"),
            order_data.get("item_name"), order_data.get("buyer_name"), order_data.get("buyer_email"),
            order_data["sale_price"], order_data["platform_fees"], order_data["shipping_cost"],
            order_data["cogs"], order_data["net_profit"], order_data["sold_date"],
            order_data.get("shipped_date"), order_data.get("tracking_number"),
            order_data.get("carrier"), order_data.get("status", "pending"), order_data.get("notes")
        ))
        order_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return order_id

def update_sold_order(order_id: int, order_data: dict) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    if USE_POSTGRES:
        cur.execute("""
            UPDATE soleops_sold_orders SET
                order_id = %s, platform = %s, sku = %s, item_name = %s,
                buyer_name = %s, buyer_email = %s, sale_price = %s,
                platform_fees = %s, shipping_cost = %s, cogs = %s, net_profit = %s,
                sold_date = %s, shipped_date = %s, tracking_number = %s,
                carrier = %s, status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
        """, (
            order_data["order_id"], order_data["platform"], order_data.get("sku"),
            order_data.get("item_name"), order_data.get("buyer_name"), order_data.get("buyer_email"),
            order_data["sale_price"], order_data["platform_fees"], order_data["shipping_cost"],
            order_data["cogs"], order_data["net_profit"], order_data["sold_date"],
            order_data.get("shipped_date"), order_data.get("tracking_number"),
            order_data.get("carrier"), order_data.get("status"), order_data.get("notes"),
            order_id, user_id
        ))
    else:
        cur.execute("""
            UPDATE soleops_sold_orders SET
                order_id = ?, platform = ?, sku = ?, item_name = ?,
                buyer_name = ?, buyer_email = ?, sale_price = ?,
                platform_fees = ?, shipping_cost = ?, cogs = ?, net_profit = ?,
                sold_date = ?, shipped_date = ?, tracking_number = ?,
                carrier = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (
            order_data["order_id"], order_data["platform"], order_data.get("sku"),
            order_data.get("item_name"), order_data.get("buyer_name"), order_data.get("buyer_email"),
            order_data["sale_price"], order_data["platform_fees"], order_data["shipping_cost"],
            order_data["cogs"], order_data["net_profit"], order_data["sold_date"],
            order_data.get("shipped_date"), order_data.get("tracking_number"),
            order_data.get("carrier"), order_data.get("status"), order_data.get("notes"),
            order_id, user_id
        ))
    
    conn.commit()
    conn.close()
    return True

def delete_sold_order(order_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM soleops_sold_orders WHERE id = %s AND user_id = %s", (order_id, user_id))
    else:
        cur.execute("DELETE FROM soleops_sold_orders WHERE id = ? AND user_id = ?", (order_id, user_id))
    
    conn.commit()
    conn.close()
    return True

def get_sold_orders(platform: str = None, status: str = None, start_date: str = None, end_date: str = None) -> list:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    query = "SELECT * FROM soleops_sold_orders WHERE user_id = "
    params = [user_id]
    
    if USE_POSTGRES:
        query += "%s"
    else:
        query += "?"
    
    if platform and platform != "All":
        if USE_POSTGRES:
            query += " AND platform = %s"
        else:
            query += " AND platform = ?"
        params.append(platform)
    
    if status and status != "All":
        if USE_POSTGRES:
            query += " AND status = %s"
        else:
            query += " AND status = ?"
        params.append(status)
    
    if start_date:
        if USE_POSTGRES:
            query += " AND sold_date >= %s"
        else:
            query += " AND sold_date >= ?"
        params.append(start_date)
    
    if end_date:
        if USE_POSTGRES:
            query += " AND sold_date <= %s"
        else:
            query += " AND sold_date <= ?"
        params.append(end_date)
    
    query += " ORDER BY sold_date DESC, created_at DESC"
    
    cur.execute(query, tuple(params))
    
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def get_order_by_id(order_id: int) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    if USE_POSTGRES:
        cur.execute("SELECT * FROM soleops_sold_orders WHERE id = %s AND user_id = %s", (order_id, user_id))
    else:
        cur.execute("SELECT * FROM soleops_sold_orders WHERE id = ? AND user_id = ?", (order_id, user_id))
    
    row = cur.fetchone()
    
    if row:
        columns = [desc[0] for desc in cur.description]
        conn.close()
        return dict(zip(columns, row))
    
    conn.close()
    return None

def get_sales_summary(start_date: str = None, end_date: str = None) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    query = """
        SELECT 
            COUNT(*) as total_orders,
            COALESCE(SUM(sale_price), 0) as total_revenue,
            COALESCE(SUM(platform_fees), 0) as total_fees,
            COALESCE(SUM(shipping_cost), 0) as total_shipping,
            COALESCE(SUM(cogs), 0) as total_cogs,
            COALESCE(SUM(net_profit), 0) as total_profit,
            COALESCE(AVG(net_profit), 0) as avg_profit
        FROM soleops_sold_orders WHERE user_id = 
    """
    params = [user_id]
    
    if USE_POSTGRES:
        query += "%s"
    else:
        query += "?"
    
    if start_date:
        if USE_POSTGRES:
            query += " AND sold_date >= %s"
        else:
            query += " AND sold_date >= ?"
        params.append(start_date)
    
    if end_date:
        if USE_POSTGRES:
            query += " AND sold_date <= %s"
        else:
            query += " AND sold_date <= ?"
        params.append(end_date)
    
    cur.execute(query, tuple(params))
    row = cur.fetchone()
    
    conn.close()
    
    return {
        "total_orders": row[0] or 0,
        "total_revenue": float(row[1] or 0),
        "total_fees": float(row[2] or 0),
        "total_shipping": float(row[3] or 0),
        "total_cogs": float(row[4] or 0),
        "total_profit": float(row[5] or 0),
        "avg_profit": float(row[6] or 0)
    }

def get_platform_breakdown(start_date: str = None, end_date: str = None) -> list:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    query = """
        SELECT 
            platform,
            COUNT(*) as order_count,
            COALESCE(SUM(sale_price), 0) as revenue,
            COALESCE(SUM(net_profit), 0) as profit
        FROM soleops_sold_orders WHERE user_id = 
    """
    params = [user_id]
    
    if USE_POSTGRES:
        query += "%s"
    else:
        query += "?"
    
    if start_date:
        if USE_POSTGRES:
            query += " AND sold_date >= %s"
        else:
            query += " AND sold_date >= ?"
        params.append(start_date)
    
    if end_date:
        if USE_POSTGRES:
            query += " AND sold_date <= %s"
        else:
            query += " AND sold_date <= ?"
        params.append(end_date)
    
    query += " GROUP BY platform ORDER BY profit DESC"
    
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    
    conn.close()
    
    return [{"platform": r[0], "order_count": r[1], "revenue": float(r[2]), "profit": float(r[3])} for r in rows]

def get_sales_trend(days: int = 30) -> list:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    if USE_POSTGRES:
        query = """
            SELECT 
                sold_date,
                COUNT(*) as order_count,
                COALESCE(SUM(sale_price), 0) as revenue,
                COALESCE(SUM(net_profit), 0) as profit
            FROM soleops_sold_orders 
            WHERE user_id = %s AND sold_date >= %s
            GROUP BY sold_date
            ORDER BY sold_date
        """
    else:
        query = """
            SELECT 
                sold_date,
                COUNT(*) as order_count,
                COALESCE(SUM(sale_price), 0) as revenue,
                COALESCE(SUM(net_profit), 0) as profit
            FROM soleops_sold_orders 
            WHERE user_id = ? AND sold_date >= ?
            GROUP BY sold_date
            ORDER BY sold_date
        """
    
    cur.execute(query, (user_id, start_date))
    rows = cur.fetchall()
    
    conn.close()
    
    return [{"date": r[0], "order_count": r[1], "revenue": float(r[2]), "profit": float(r[3])} for r in rows]

def check_repeat_buyer(buyer_name: str, buyer_email: str = None) -> dict:
    if not buyer_name:
        return {"is_repeat": False, "order_count": 0, "total_spent": 0}
    
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    if USE_POSTGRES:
        query = """
            SELECT COUNT(*) as order_count, COALESCE(SUM(sale_price), 0) as total_spent
            FROM soleops_sold_orders
            WHERE user_id = %s AND (buyer_name = %s
        """
        params = [user_id, buyer_name]
        
        if buyer_email:
            query += " OR buyer_email = %s"
            params.append(buyer_email)
        
        query += ")"
    else:
        query = """
            SELECT COUNT(*) as order_count, COALESCE(SUM(sale_price), 0) as total_spent
            FROM soleops_sold_orders
            WHERE user_id = ? AND (buyer_name = ?
        """
        params = [user_id, buyer_name]
        
        if buyer_email:
            query += " OR buyer_email = ?"
            params.append(buyer_email)
        
        query += ")"
    
    cur.execute(query, tuple(params))
    row = cur.fetchone()
    
    conn.close()
    
    order_count = row[0] or 0
    return {
        "is_repeat": order_count > 1,
        "order_count": order_count,
        "total_spent": float(row[1] or 0)
    }

def get_inventory_items() -> list:
    conn = get_conn()
    cur = conn.cursor()
    
    user_id = get_user_id()
    
    try:
        if USE_POSTGRES:
            cur.execute("""
                SELECT sku, name, purchase_price 
                FROM soleops_inventory 
                WHERE user_id = %s AND status = 'active'
                ORDER BY name
            """, (user_id,))
        else:
            cur.execute("""
                SELECT sku, name, purchase_price 
                FROM soleops_inventory 
                WHERE user_id = ? AND status = 'active'
                ORDER BY name
            """, (user_id,))
        
        rows = cur.fetchall()
        conn.close()
        return [{"sku": r[0], "name": r[1], "purchase_price": float(r[2] or 0)} for r in rows]
    except:
        conn.close()
        return []

def export_orders_to_csv(orders: list) -> str:
    output = io.StringIO()
    
    if not orders:
        return ""
    
    fieldnames = [
        "order_id", "platform", "sku", "item_name", "buyer_name",
        "sale_price", "platform_fees", "shipping_cost", "cogs", "net_profit",
        "sold_date", "shipped_date", "tracking_number", "carrier", "status", "notes"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for order in orders:
        row = {k: order.get(k, "") for k in fieldnames}
        writer.writerow(row)
    
    return output.getvalue()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("📦 SoleOps Sold Order Tracker")
st.markdown("Track all your sneaker sales across platforms with profit calculations and shipping status.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "➕ New Order", "📋 All Orders", "📈 Analytics", "⚙️ Settings"])

with tab1:
    st.subheader("Sales Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        dash_start = st.date_input("From", value=datetime.now() - timedelta(days=30), key="dash_start")
    with col2:
        dash_end = st.date_input("To", value=datetime.now(), key="dash_end")
    
    summary = get_sales_summary(dash_start.strftime("%Y-%m-%d"), dash_end.strftime("%Y-%m-%d"))
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", summary["total_orders"])
    
    with col2:
        st.metric("Total Revenue", f"${summary['total_revenue']:,.2f}")
    
    with col3:
        st.metric("Total Fees", f"${summary['total_fees']:,.2f}")
    
    with col4:
        profit_color = "normal" if summary["total_profit"] >= 0 else "inverse"
        st.metric("Net Profit", f"${summary['total_profit']:,.2f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Avg Profit Per Pair")
        st.metric("Average", f"${summary['avg_profit']:,.2f}")
    
    with col2:
        st.subheader("Cost Breakdown")
        st.write(f"**COGS:** ${summary['total_cogs']:,.2f}")
        st.write(f"**Shipping:** ${summary['total_shipping']:,.2f}")
        st.write(f"**Platform Fees:** ${summary['total_fees']:,.2f}")
    
    st.markdown("---")
    
    st.subheader("Platform Breakdown")
    platform_data = get_platform_breakdown(dash_start.strftime("%Y-%m-%d"), dash_end.strftime("%Y-%m-%d"))
    
    if platform_data:
        df_platform = pd.DataFrame(platform_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_revenue = px.pie(df_platform, values="revenue", names="platform", title="Revenue by Platform")
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        with col2:
            fig_profit = px.bar(df_platform, x="platform", y="profit", title="Profit by Platform",
                               color="platform", text="profit")
            fig_profit.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
            st.plotly_chart(fig_profit, use_container_width=True)
        
        st.dataframe(df_platform, use_container_width=True, hide_index=True)
    else:
        st.info("No sales data for the selected period.")
    
    st.markdown("---")
    
    st.subheader("Recent Orders")
    recent_orders = get_sold_orders()[:5]
    
    if recent_orders:
        for order in recent_orders:
            status_emoji = {
                "pending": "🟡",
                "shipped": "📦",
                "in_transit": "🚚",
                "delivered": "✅",
                "cancelled": "❌",
                "returned": "↩️"
            }.get(order["status"], "⚪")
            
            with st.expander(f"{status_emoji} {order['order_id']} - {order['item_name'] or order['sku'] or 'Unknown'} | ${order['net_profit']:.2f} profit"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Platform:** {order['platform']}")
                    st.write(f"**Buyer:** {order['buyer_name'] or 'N/A'}")
                with col2:
                    st.write(f"**Sale Price:** ${order['sale_price']:.2f}")
                    st.write(f"**Fees:** ${order['platform_fees']:.2f}")
                with col3:
                    st.write(f"**Sold:** {order['sold_date']}")
                    st.write(f"**Status:** {order['status'].title()}")
    else:
        st.info("No orders yet. Add your first sale!")

with tab2:
    st.subheader("Add New Sale")
    
    with st.form("new_order_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            new_order_id = st.text_input("Order ID *", placeholder="e.g., eBay-12345678")
            new_platform = st.selectbox("Platform *", list(PLATFORM_FEES.keys()))
            
            inventory_items = get_inventory_items()
            sku_options = [""] + [f"{item['sku']} - {item['name']}" for item in inventory_items]
            selected_sku = st.selectbox("Select from Inventory", sku_options)
            
            if selected_sku:
                sku_code = selected_sku.split(" - ")[0]
                item_info = next((i for i in inventory_items if i["sku"] == sku_code), None)
                new_sku = sku_code
                new_item_name = item_info["name"] if item_info else ""
                default_cogs = item_info["purchase_price"] if item_info else 0.0
            else:
                new_sku = st.text_input("SKU", placeholder="e.g., AJ1-CHICAGO-10")
                new_item_name = st.text_input("Item Name", placeholder="e.g., Air Jordan 1 Chicago")
                default_cogs = 0.0
            
            new_buyer_name = st.text_input("Buyer Name")
            new_buyer_email = st.text_input("Buyer Email")
        
        with col2:
            new_sale_price = st.number_input("Sale Price *", min_value=0.0, step=1.0, format="%.2f")
            
            auto_fees = calculate_platform_fees(new_sale_price, new_platform)
            new_platform_fees = st.number_input("Platform Fees", min_value=0.0, value=auto_fees, step=0.01, format="%.2f",
                                                help=f"Auto-calculated: {PLATFORM_FEES[new_platform]['name']}")
            
            new_shipping_cost = st.number_input("Shipping Cost", min_value=0.0, step=0.01, format="%.2f")
            
            if selected_sku and item_info:
                new_cogs = st.number_input("Cost of Goods (COGS)", min_value=0.0, value=default_cogs, step=0.01, format="%.2f")
            else:
                new_cogs = st.number_