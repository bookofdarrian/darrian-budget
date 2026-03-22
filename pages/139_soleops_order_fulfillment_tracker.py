import streamlit as st
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Order Fulfillment Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
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
    """Return placeholder(s) for SQL queries based on database type."""
    placeholder = "%s" if USE_POSTGRES else "?"
    return ", ".join([placeholder] * count)


def _ensure_tables():
    """Create necessary database tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Orders table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_orders (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            order_id TEXT,
            buyer_name TEXT NOT NULL,
            item_sku TEXT,
            item_name TEXT NOT NULL,
            sale_price REAL NOT NULL,
            sale_date TEXT NOT NULL,
            shipping_deadline TEXT NOT NULL,
            carrier TEXT,
            tracking_number TEXT,
            label_url TEXT,
            status TEXT DEFAULT 'pending',
            shipped_date TEXT,
            delivered_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Fulfillment settings table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_fulfillment_settings (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER UNIQUE NOT NULL,
            default_carrier TEXT DEFAULT 'USPS',
            auto_print_labels INTEGER DEFAULT 0,
            shipping_notification_hours INTEGER DEFAULT 24,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Get user's fulfillment settings."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT default_carrier, auto_print_labels, shipping_notification_hours FROM soleops_fulfillment_settings WHERE user_id = {_ph()}", (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "default_carrier": row[0],
            "auto_print_labels": bool(row[1]),
            "shipping_notification_hours": row[2]
        }
    return {
        "default_carrier": "USPS",
        "auto_print_labels": False,
        "shipping_notification_hours": 24
    }


def save_user_settings(user_id: int, settings: Dict[str, Any]):
    """Save user's fulfillment settings."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO soleops_fulfillment_settings (user_id, default_carrier, auto_print_labels, shipping_notification_hours, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                default_carrier = EXCLUDED.default_carrier,
                auto_print_labels = EXCLUDED.auto_print_labels,
                shipping_notification_hours = EXCLUDED.shipping_notification_hours,
                updated_at = EXCLUDED.updated_at
        """, (user_id, settings["default_carrier"], int(settings["auto_print_labels"]), settings["shipping_notification_hours"], datetime.now().isoformat()))
    else:
        cur.execute(f"SELECT id FROM soleops_fulfillment_settings WHERE user_id = {_ph()}", (user_id,))
        exists = cur.fetchone()
        if exists:
            cur.execute(f"""
                UPDATE soleops_fulfillment_settings 
                SET default_carrier = {_ph()}, auto_print_labels = {_ph()}, shipping_notification_hours = {_ph()}, updated_at = {_ph()}
                WHERE user_id = {_ph()}
            """, (settings["default_carrier"], int(settings["auto_print_labels"]), settings["shipping_notification_hours"], datetime.now().isoformat(), user_id))
        else:
            cur.execute(f"""
                INSERT INTO soleops_fulfillment_settings (user_id, default_carrier, auto_print_labels, shipping_notification_hours, updated_at)
                VALUES ({_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()})
            """, (user_id, settings["default_carrier"], int(settings["auto_print_labels"]), settings["shipping_notification_hours"], datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def get_orders(user_id: int, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get orders for a user with optional status filter."""
    conn = get_conn()
    cur = conn.cursor()
    
    if status_filter:
        cur.execute(f"""
            SELECT id, platform, order_id, buyer_name, item_sku, item_name, sale_price, 
                   sale_date, shipping_deadline, carrier, tracking_number, label_url, 
                   status, shipped_date, delivered_date, notes, created_at, updated_at
            FROM soleops_orders 
            WHERE user_id = {_ph()} AND status = {_ph()}
            ORDER BY shipping_deadline ASC
        """, (user_id, status_filter))
    else:
        cur.execute(f"""
            SELECT id, platform, order_id, buyer_name, item_sku, item_name, sale_price, 
                   sale_date, shipping_deadline, carrier, tracking_number, label_url, 
                   status, shipped_date, delivered_date, notes, created_at, updated_at
            FROM soleops_orders 
            WHERE user_id = {_ph()}
            ORDER BY shipping_deadline ASC
        """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    orders = []
    for row in rows:
        orders.append({
            "id": row[0],
            "platform": row[1],
            "order_id": row[2],
            "buyer_name": row[3],
            "item_sku": row[4],
            "item_name": row[5],
            "sale_price": row[6],
            "sale_date": row[7],
            "shipping_deadline": row[8],
            "carrier": row[9],
            "tracking_number": row[10],
            "label_url": row[11],
            "status": row[12],
            "shipped_date": row[13],
            "delivered_date": row[14],
            "notes": row[15],
            "created_at": row[16],
            "updated_at": row[17]
        })
    
    return orders


def add_order(user_id: int, order_data: Dict[str, Any]) -> int:
    """Add a new order."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO soleops_orders (user_id, platform, order_id, buyer_name, item_sku, item_name, 
                                    sale_price, sale_date, shipping_deadline, carrier, notes, status)
        VALUES ({_ph(12)})
    """, (user_id, order_data["platform"], order_data.get("order_id"), order_data["buyer_name"],
          order_data.get("item_sku"), order_data["item_name"], order_data["sale_price"],
          order_data["sale_date"], order_data["shipping_deadline"], order_data.get("carrier"),
          order_data.get("notes"), "pending"))
    
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    
    return order_id


def update_order_status(order_id: int, status: str, tracking_number: Optional[str] = None, carrier: Optional[str] = None):
    """Update order status and optionally tracking info."""
    conn = get_conn()
    cur = conn.cursor()
    
    now = datetime.now().isoformat()
    
    if status == "shipped":
        cur.execute(f"""
            UPDATE soleops_orders 
            SET status = {_ph()}, tracking_number = {_ph()}, carrier = {_ph()}, shipped_date = {_ph()}, updated_at = {_ph()}
            WHERE id = {_ph()}
        """, (status, tracking_number, carrier, now, now, order_id))
    elif status == "delivered":
        cur.execute(f"""
            UPDATE soleops_orders 
            SET status = {_ph()}, delivered_date = {_ph()}, updated_at = {_ph()}
            WHERE id = {_ph()}
        """, (status, now, now, order_id))
    else:
        cur.execute(f"""
            UPDATE soleops_orders 
            SET status = {_ph()}, updated_at = {_ph()}
            WHERE id = {_ph()}
        """, (status, now, order_id))
    
    conn.commit()
    conn.close()


def delete_order(order_id: int):
    """Delete an order."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM soleops_orders WHERE id = {_ph()}", (order_id,))
    conn.commit()
    conn.close()


# Initialize tables
_ensure_tables()

# Main UI
st.title("🍑 SoleOps Order Fulfillment Tracker")

user_id = st.session_state.get("user_id", 1)
settings = get_user_settings(user_id)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📦 Orders", "➕ Add Order", "📊 Dashboard", "⚙️ Settings"])

with tab1:
    st.subheader("Order Management")
    
    # Filter options
    col1, col2 = st.columns([1, 3])
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "pending", "shipped", "delivered", "cancelled"])
    
    filter_val = None if status_filter == "All" else status_filter
    orders = get_orders(user_id, filter_val)
    
    if orders:
        for order in orders:
            with st.expander(f"📦 {order['item_name']} - {order['buyer_name']} ({order['status'].upper()})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Platform:** {order['platform']}")
                    st.write(f"**Order ID:** {order['order_id'] or 'N/A'}")
                    st.write(f"**SKU:** {order['item_sku'] or 'N/A'}")
                with col2:
                    st.write(f"**Sale Price:** ${order['sale_price']:.2f}")
                    st.write(f"**Sale Date:** {order['sale_date']}")
                    st.write(f"**Ship By:** {order['shipping_deadline']}")
                with col3:
                    st.write(f"**Carrier:** {order['carrier'] or 'Not set'}")
                    st.write(f"**Tracking:** {order['tracking_number'] or 'Not set'}")
                
                if order['notes']:
                    st.write(f"**Notes:** {order['notes']}")
                
                # Action buttons
                st.markdown("---")
                action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                
                with action_col1:
                    if order['status'] == 'pending':
                        if st.button("Mark Shipped", key=f"ship_{order['id']}"):
                            st.session_state[f"show_ship_form_{order['id']}"] = True
                
                with action_col2:
                    if order['status'] == 'shipped':
                        if st.button("Mark Delivered", key=f"deliver_{order['id']}"):
                            update_order_status(order['id'], "delivered")
                            st.rerun()
                
                with action_col3:
                    if order['status'] not in ['cancelled', 'delivered']:
                        if st.button("Cancel", key=f"cancel_{order['id']}"):
                            update_order_status(order['id'], "cancelled")
                            st.rerun()
                
                with action_col4:
                    if st.button("Delete", key=f"delete_{order['id']}"):
                        delete_order(order['id'])
                        st.rerun()
                
                # Ship form
                if st.session_state.get(f"show_ship_form_{order['id']}", False):
                    with st.form(key=f"ship_form_{order['id']}"):
                        carrier = st.selectbox("Carrier", ["USPS", "UPS", "FedEx", "DHL", "Other"], key=f"carrier_{order['id']}")
                        tracking = st.text_input("Tracking Number", key=f"tracking_{order['id']}")
                        if st.form_submit_button("Confirm Shipment"):
                            update_order_status(order['id'], "shipped", tracking, carrier)
                            st.session_state[f"show_ship_form_{order['id']}"] = False
                            st.rerun()
    else:
        st.info("No orders found. Add your first order in the 'Add Order' tab.")

with tab2:
    st.subheader("Add New Order")
    
    with st.form("add_order_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            platform = st.selectbox("Platform", ["eBay", "StockX", "GOAT", "Poshmark", "Mercari", "Grailed", "Other"])
            order_id = st.text_input("Order ID (Optional)")
            buyer_name = st.text_input("Buyer Name")
            item_sku = st.text_input("Item SKU (Optional)")
        
        with col2:
            item_name = st.text_input("Item Name")
            sale_price = st.number_input("Sale Price", min_value=0.0, step=0.01)
            sale_date = st.date_input("Sale Date", value=datetime.now())
            shipping_deadline = st.date_input("Shipping Deadline", value=datetime.now() + timedelta(days=3))
        
        carrier = st.selectbox("Preferred Carrier", ["USPS", "UPS", "FedEx", "DHL", "Other"], index=["USPS", "UPS", "FedEx", "DHL", "Other"].index(settings["default_carrier"]))
        notes = st.text_area("Notes (Optional)")
        
        if st.form_submit_button("Add Order"):
            if buyer_name and item_name and sale_price > 0:
                order_data = {
                    "platform": platform,
                    "order_id": order_id,
                    "buyer_name": buyer_name,
                    "item_sku": item_sku,
                    "item_name": item_name,
                    "sale_price": sale_price,
                    "sale_date": sale_date.isoformat(),
                    "shipping_deadline": shipping_deadline.isoformat(),
                    "carrier": carrier,
                    "notes": notes
                }
                add_order(user_id, order_data)
                st.success("Order added successfully!")
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

with tab3:
    st.subheader("Fulfillment Dashboard")
    
    all_orders = get_orders(user_id)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    
    pending_count = len([o for o in all_orders if o['status'] == 'pending'])
    shipped_count = len([o for o in all_orders if o['status'] == 'shipped'])
    delivered_count = len([o for o in all_orders if o['status'] == 'delivered'])
    total_revenue = sum(o['sale_price'] for o in all_orders if o['status'] != 'cancelled')
    
    with col1:
        st.metric("Pending Orders", pending_count)
    with col2:
        st.metric("Shipped Orders", shipped_count)
    with col3:
        st.metric("Delivered Orders", delivered_count)
    with col4:
        st.metric("Total Revenue", f"${total_revenue:.2f}")
    
    # Urgent orders
    st.markdown("---")
    st.subheader("⚠️ Orders Needing Attention")
    
    today = datetime.now().date()
    urgent_orders = [o for o in all_orders if o['status'] == 'pending' and datetime.fromisoformat(o['shipping_deadline']).date() <= today + timedelta(days=1)]
    
    if urgent_orders:
        for order in urgent_orders:
            deadline = datetime.fromisoformat(order['shipping_deadline']).date()
            if deadline < today:
                st.error(f"🚨 OVERDUE: {order['item_name']} for {order['buyer_name']} - was due {order['shipping_deadline']}")
            else:
                st.warning(f"⚠️ DUE TODAY/TOMORROW: {order['item_name']} for {order['buyer_name']} - due {order['shipping_deadline']}")
    else:
        st.success("No urgent orders! You're all caught up.")

with tab4:
    st.subheader("Fulfillment Settings")
    
    with st.form("settings_form"):
        default_carrier = st.selectbox("Default Carrier", ["USPS", "UPS", "FedEx", "DHL", "Other"], 
                                       index=["USPS", "UPS", "FedEx", "DHL", "Other"].index(settings["default_carrier"]))
        auto_print = st.checkbox("Auto-print Labels (Coming Soon)", value=settings["auto_print_labels"], disabled=True)
        notification_hours = st.number_input("Shipping Reminder (hours before deadline)", 
                                             min_value=1, max_value=72, value=settings["shipping_notification_hours"])
        
        if st.form_submit_button("Save Settings"):
            new_settings = {
                "default_carrier": default_carrier,
                "auto_print_labels": auto_print,
                "shipping_notification_hours": notification_hours
            }
            save_user_settings(user_id, new_settings)
            st.success("Settings saved!")
            st.rerun()