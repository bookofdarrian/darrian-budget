import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import csv
import io
from typing import Optional, List, Dict, Any

st.set_page_config(page_title="SoleOps Customer CRM", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ph(count: int = 1) -> str:
    """Return correct placeholder(s) for SQL queries."""
    placeholder = "%s" if USE_POSTGRES else "?"
    return ", ".join([placeholder] * count)

def _ensure_tables():
    """Create all necessary tables for the Customer CRM."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Main customers table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_customers (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            buyer_id TEXT,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            email TEXT,
            vip_status BOOLEAN DEFAULT FALSE,
            banned BOOLEAN DEFAULT FALSE,
            notes TEXT,
            first_purchase_date DATE,
            total_orders INTEGER DEFAULT 0,
            total_revenue REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Customer orders junction table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_customer_orders (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            customer_id INTEGER NOT NULL,
            order_id TEXT,
            platform TEXT NOT NULL,
            sale_date DATE,
            amount REAL DEFAULT 0.0,
            item_sku TEXT,
            item_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES soleops_customers(id)
        )
    """)
    
    # Customer feedback table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_customer_feedback (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            customer_id INTEGER NOT NULL,
            feedback_type TEXT,
            rating INTEGER,
            comment TEXT,
            feedback_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES soleops_customers(id)
        )
    """)
    
    # Customer communications table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS soleops_customer_communications (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            customer_id INTEGER NOT NULL,
            channel TEXT,
            direction TEXT,
            subject TEXT,
            message TEXT,
            comm_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES soleops_customers(id)
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
def get_user_id() -> int:
    """Get current user ID from session."""
    return st.session_state.get("user_id", 1)

def get_all_customers(user_id: int, filters: Dict = None) -> List[Dict]:
    """Fetch all customers with optional filters."""
    conn = get_conn()
    cur = conn.cursor()
    
    query = f"""
        SELECT id, buyer_id, platform, username, email, vip_status, banned, 
               notes, first_purchase_date, total_orders, total_revenue, created_at, updated_at
        FROM soleops_customers
        WHERE user_id = {_ph()}
    """
    params = [user_id]
    
    if filters:
        if filters.get("platform"):
            query += f" AND platform = {_ph()}"
            params.append(filters["platform"])
        if filters.get("vip_only"):
            query += " AND vip_status = TRUE"
        if filters.get("banned_only"):
            query += " AND banned = TRUE"
        if filters.get("min_orders"):
            query += f" AND total_orders >= {_ph()}"
            params.append(filters["min_orders"])
        if filters.get("min_revenue"):
            query += f" AND total_revenue >= {_ph()}"
            params.append(filters["min_revenue"])
        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            query += f" AND (username LIKE {_ph()} OR email LIKE {_ph()} OR buyer_id LIKE {_ph()})"
            params.extend([search_term, search_term, search_term])
    
    query += " ORDER BY total_revenue DESC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    customers = []
    for row in rows:
        customers.append({
            "id": row[0],
            "buyer_id": row[1],
            "platform": row[2],
            "username": row[3],
            "email": row[4],
            "vip_status": bool(row[5]),
            "banned": bool(row[6]),
            "notes": row[7],
            "first_purchase_date": row[8],
            "total_orders": row[9],
            "total_revenue": row[10],
            "created_at": row[11],
            "updated_at": row[12]
        })
    
    return customers

def get_customer_by_id(customer_id: int) -> Optional[Dict]:
    """Fetch a single customer by ID."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, buyer_id, platform, username, email, vip_status, banned, 
               notes, first_purchase_date, total_orders, total_revenue, created_at, updated_at
        FROM soleops_customers
        WHERE id = {_ph()}
    """, (customer_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "buyer_id": row[1],
            "platform": row[2],
            "username": row[3],
            "email": row[4],
            "vip_status": bool(row[5]),
            "banned": bool(row[6]),
            "notes": row[7],
            "first_purchase_date": row[8],
            "total_orders": row[9],
            "total_revenue": row[10],
            "created_at": row[11],
            "updated_at": row[12]
        }
    return None

def create_customer(user_id: int, data: Dict) -> int:
    """Create a new customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO soleops_customers 
        (user_id, buyer_id, platform, username, email, vip_status, banned, notes, first_purchase_date, total_orders, total_revenue)
        VALUES ({_ph(11)})
    """, (
        user_id,
        data.get("buyer_id"),
        data.get("platform"),
        data.get("username"),
        data.get("email"),
        data.get("vip_status", False),
        data.get("banned", False),
        data.get("notes"),
        data.get("first_purchase_date"),
        data.get("total_orders", 0),
        data.get("total_revenue", 0.0)
    ))
    
    if USE_POSTGRES:
        cur.execute("SELECT lastval()")
        customer_id = cur.fetchone()[0]
    else:
        customer_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    
    return customer_id

def update_customer(customer_id: int, data: Dict):
    """Update an existing customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        UPDATE soleops_customers
        SET buyer_id = {_ph()}, platform = {_ph()}, username = {_ph()}, email = {_ph()},
            vip_status = {_ph()}, banned = {_ph()}, notes = {_ph()}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {_ph()}
    """, (
        data.get("buyer_id"),
        data.get("platform"),
        data.get("username"),
        data.get("email"),
        data.get("vip_status", False),
        data.get("banned", False),
        data.get("notes"),
        customer_id
    ))
    
    conn.commit()
    conn.close()

def delete_customer(customer_id: int):
    """Delete a customer and related records."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"DELETE FROM soleops_customer_communications WHERE customer_id = {_ph()}", (customer_id,))
    cur.execute(f"DELETE FROM soleops_customer_feedback WHERE customer_id = {_ph()}", (customer_id,))
    cur.execute(f"DELETE FROM soleops_customer_orders WHERE customer_id = {_ph()}", (customer_id,))
    cur.execute(f"DELETE FROM soleops_customers WHERE id = {_ph()}", (customer_id,))
    
    conn.commit()
    conn.close()

def get_customer_orders(customer_id: int) -> List[Dict]:
    """Fetch all orders for a customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, order_id, platform, sale_date, amount, item_sku, item_name, created_at
        FROM soleops_customer_orders
        WHERE customer_id = {_ph()}
        ORDER BY sale_date DESC
    """, (customer_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    orders = []
    for row in rows:
        orders.append({
            "id": row[0],
            "order_id": row[1],
            "platform": row[2],
            "sale_date": row[3],
            "amount": row[4],
            "item_sku": row[5],
            "item_name": row[6],
            "created_at": row[7]
        })
    
    return orders

def add_customer_order(customer_id: int, data: Dict):
    """Add an order to a customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO soleops_customer_orders 
        (customer_id, order_id, platform, sale_date, amount, item_sku, item_name)
        VALUES ({_ph(7)})
    """, (
        customer_id,
        data.get("order_id"),
        data.get("platform"),
        data.get("sale_date"),
        data.get("amount", 0.0),
        data.get("item_sku"),
        data.get("item_name")
    ))
    
    # Update customer totals
    cur.execute(f"""
        UPDATE soleops_customers
        SET total_orders = total_orders + 1,
            total_revenue = total_revenue + {_ph()},
            updated_at = CURRENT_TIMESTAMP
        WHERE id = {_ph()}
    """, (data.get("amount", 0.0), customer_id))
    
    conn.commit()
    conn.close()

def get_customer_feedback(customer_id: int) -> List[Dict]:
    """Fetch all feedback for a customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, feedback_type, rating, comment, feedback_date, created_at
        FROM soleops_customer_feedback
        WHERE customer_id = {_ph()}
        ORDER BY feedback_date DESC
    """, (customer_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    feedback = []
    for row in rows:
        feedback.append({
            "id": row[0],
            "feedback_type": row[1],
            "rating": row[2],
            "comment": row[3],
            "feedback_date": row[4],
            "created_at": row[5]
        })
    
    return feedback

def add_customer_feedback(customer_id: int, data: Dict):
    """Add feedback for a customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO soleops_customer_feedback 
        (customer_id, feedback_type, rating, comment, feedback_date)
        VALUES ({_ph(5)})
    """, (
        customer_id,
        data.get("feedback_type"),
        data.get("rating"),
        data.get("comment"),
        data.get("feedback_date")
    ))
    
    conn.commit()
    conn.close()

def get_customer_communications(customer_id: int) -> List[Dict]:
    """Fetch all communications for a customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, channel, direction, subject, message, comm_timestamp, created_at
        FROM soleops_customer_communications
        WHERE customer_id = {_ph()}
        ORDER BY comm_timestamp DESC
    """, (customer_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    comms = []
    for row in rows:
        comms.append({
            "id": row[0],
            "channel": row[1],
            "direction": row[2],
            "subject": row[3],
            "message": row[4],
            "comm_timestamp": row[5],
            "created_at": row[6]
        })
    
    return comms

def add_customer_communication(customer_id: int, data: Dict):
    """Add a communication log for a customer."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO soleops_customer_communications 
        (customer_id, channel, direction, subject, message, comm_timestamp)
        VALUES ({_ph(6)})
    """, (
        customer_id,
        data.get("channel"),
        data.get("direction"),
        data.get("subject"),
        data.get("message"),
        data.get("comm_timestamp", datetime.now())
    ))
    
    conn.commit()
    conn.close()

def import_from_sold_orders(user_id: int) -> int:
    """Import customers from existing sold orders table."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Check if soleops_sold_orders table exists
    try:
        cur.execute("""
            SELECT buyer_username, buyer_email, platform, sale_date, sale_price, sku, item_name
            FROM soleops_sold_orders
            WHERE user_id = %s
        """ if USE_POSTGRES else """
            SELECT buyer_username, buyer_email, platform, sale_date, sale_price, sku, item_name
            FROM soleops_sold_orders
            WHERE user_id = ?
        """, (user_id,))
        
        orders = cur.fetchall()
    except Exception:
        conn.close()
        return 0
    
    imported_count = 0
    customer_cache = {}
    
    for order in orders:
        buyer_username = order[0]
        buyer_email = order[1]
        platform = order[2]
        sale_date = order[3]
        sale_price = order[4] or 0.0
        sku = order[5]
        item_name = order[6]
        
        if not buyer_username:
            continue
        
        # Create cache key
        cache_key = f"{platform}_{buyer_username}"
        
        if cache_key not in customer_cache:
            # Check if customer already exists
            cur.execute(f"""
                SELECT id FROM soleops_customers
                WHERE user_id = {_ph()} AND platform = {_ph()} AND username = {_ph()}
            """, (user_id, platform, buyer_username))
            
            existing = cur.fetchone()
            
            if existing:
                customer_cache[cache_key] = existing[0]
            else:
                # Create new customer
                cur.execute(f"""
                    INSERT INTO soleops_customers 
                    (user_id, platform, username, email, first_purchase_date, total_orders, total_revenue)
                    VALUES ({_ph(7)})
                """, (user_id, platform, buyer_username, buyer_email, sale_date, 0, 0.0))
                
                if USE_POSTGRES:
                    cur.execute("SELECT lastval()")
                    customer_id = cur.fetchone()[0]
                else:
                    customer_id = cur.lastrowid
                
                customer_cache[cache_key] = customer_id
                imported_count += 1
        
        customer_id = customer_cache[cache_key]
        
        # Add order
        cur.execute(f"""
            INSERT INTO soleops_customer_orders 
            (customer_id, platform, sale_date, amount, item_sku, item_name)
            VALUES ({_ph(6)})
        """, (customer_id, platform, sale_date, sale_price, sku, item_name))
        
        # Update customer totals
        cur.execute(f"""
            UPDATE soleops_customers
            SET total_orders = total_orders + 1,
                total_revenue = total_revenue + {_ph()},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {_ph()}
        """, (sale_price, customer_id))
    
    conn.commit()
    conn.close()
    
    return imported_count

def merge_customers(primary_id: int, secondary_id: int):
    """Merge two customer records into one."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get secondary customer data
    secondary = get_customer_by_id(secondary_id)
    if not secondary:
        conn.close()
        return
    
    # Move orders to primary customer
    cur.execute(f"""
        UPDATE soleops_customer_orders
        SET customer_id = {_ph()}
        WHERE customer_id = {_ph()}
    """, (primary_id, secondary_id))
    
    # Move feedback to primary customer
    cur.execute(f"""
        UPDATE soleops_customer_feedback
        SET customer_id = {_ph()}
        WHERE customer_id = {_ph()}
    """, (primary_id, secondary_id))
    
    # Move communications to primary customer
    cur.execute(f"""
        UPDATE soleops_customer_communications
        SET customer_id = {_ph()}
        WHERE customer_id = {_ph()}
    """, (primary_id, secondary_id))
    
    # Update primary customer totals
    cur.execute(f"""
        UPDATE soleops_customers
        SET total_orders = total_orders + {_ph()},
            total_revenue = total_revenue + {_ph()},
            updated_at = CURRENT_TIMESTAMP
        WHERE id = {_ph()}
    """, (secondary["total_orders"], secondary["total_revenue"], primary_id))
    
    # Delete secondary customer
    cur.execute(f"DELETE FROM soleops_customers WHERE id = {_ph()}", (secondary_id,))
    
    conn.commit()
    conn.close()

def get_top_customers(user_id: int, limit: int = 10) -> List[Dict]:
    """Get top customers by revenue."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, username, platform, total_orders, total_revenue, vip_status
        FROM soleops_customers
        WHERE user_id = {_ph()} AND banned = FALSE
        ORDER BY total_revenue DESC
        LIMIT {_ph()}
    """, (user_id, limit))
    
    rows = cur.fetchall()
    conn.close()
    
    customers = []
    for row in rows:
        customers.append({
            "id": row[0],
            "username": row[1],
            "platform": row[2],
            "total_orders": row[3],
            "total_revenue": row[4],
            "vip_status": bool(row[5])
        })
    
    return customers

def get_customer_stats(user_id: int) -> Dict:
    """Get aggregate customer statistics."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_customers,
            SUM(CASE WHEN vip_status = TRUE THEN 1 ELSE 0 END) as vip_count,
            SUM(CASE WHEN banned = TRUE THEN 1 ELSE 0 END) as banned_count,
            SUM(total_orders) as total_orders,
            SUM(total_revenue) as total_revenue,
            AVG(total_orders) as avg_orders_per_customer,
            AVG(total_revenue) as avg_revenue_per_customer
        FROM soleops_customers
        WHERE user_id = {_ph()}
    """, (user_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "total_customers": row[0] or 0,
            "vip_count": row[1] or 0,
            "banned_count": row[2] or 0,
            "total_orders": row[3] or 0,
            "total_revenue": row[4] or 0.0,
            "avg_orders_per_customer": row[5] or 0.0,
            "avg_revenue_per_customer": row[6] or 0.0
        }
    
    return {
        "total_customers": 0,
        "vip_count": 0,
        "banned_count": 0,
        "total_orders": 0,
        "total_revenue": 0.0,
        "avg_orders_per_customer": 0.0,
        "avg_revenue_per_customer": 0.0
    }

def get_ai_customer_insights(customer: Dict, orders: List[Dict], feedback: List[Dict]) -> str:
    """Get AI-powered insights for a customer."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Configure your Anthropic API key in Settings to enable AI insights."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        # Build context
        order_summary = f"{len(orders)} orders totaling ${customer['total_revenue']:.2f}"
        if orders:
            recent_order = orders[0]
            days_since_last = (datetime.now().date() - datetime.strptime(str(recent_order['sale_date']), '%Y-%m-%d').date()).days if recent_order['sale_date'] else 'unknown'
            order_summary += f", last purchase {days_since_last} days ago"
        
        feedback_summary = f"{len(feedback)} feedback records"
        if feedback:
            avg_rating = sum(f['rating'] for f in feedback if f['rating']) / len([f for f in feedback if f['rating']]) if any(f['rating'] for f in feedback) else 0
            feedback_summary += f", average rating: {avg_rating:.1f}/5"
        
        prompt = f"""Analyze this customer profile for a sneaker reseller and provide actionable insights:

Customer: {customer['username']} ({customer['platform']})
VIP Status: {'Yes' if customer['vip_status'] else 'No'}
Orders: {order_summary}
Feedback: {feedback_summary}
Notes: {customer.get('notes', 'None')}

Provide brief, actionable insights in these areas:
1. Repeat Buyer Prediction: Will they buy again? Why?
2. Churn Risk: Low/Medium/High and why
3. Personalized Outreach: One specific suggestion to increase loyalty

Keep each section to 1-2 sentences. Be direct and actionable."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        return f"⚠️ AI analysis unavailable: {str(e)}"

def import_from_csv(user_id: int, csv_content: str, platform: str) -> int:
    """Import customers from CSV file."""
    imported = 0
    
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            # Try to map common column names
            username = row.get("buyer_username") or row.get("Buyer Username") or row.get("username") or row.get("Username") or ""
            email = row.get("buyer_email") or row.get("Buyer Email") or row.get("email") or row.get("Email") or ""
            order_id = row.get("order_id") or row.get("Order ID") or row.get("Transaction ID") or ""
            sale_date_str = row.get("sale_date") or row.get("Sale Date") or row.get("Date") or ""
            amount_str = row.get("amount") or row.get("Amount") or row.get("Sale Price") or row.get("Total") or "0"
            item_name = row.get("item_name") or row.get("Item") or row.get("Title") or ""
            sku = row.get("sku") or row.get("SKU") or row.get("Item Number") or ""
            
            if not username:
                continue
            
            # Parse amount
            try:
                amount = float(str(amount_str).replace("$", "").replace(",", ""))
            except ValueError:
                amount = 0.0
            
            # Parse date
            sale_date = None
            if sale_date_str:
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y"]:
                    try:
                        sale_date = datetime.strptime(sale_date_str, fmt).date()
                        break
                    except ValueError:
                        continue
            
            # Check if customer exists
            conn = get_conn()
            cur = conn.cursor()
            
            cur.execute(f"""
                SELECT id FROM soleops_customers
                WHERE user_id = {_ph()} AND platform = {_ph()} AND username = {_ph()}
            """, (user_id, platform, username))
            
            existing = cur.fetchone()
            
            if existing:
                customer_id = existing[0]
            else:
                # Create new customer
                cur.execute(f"""
                    INSERT INTO soleops_customers 
                    (user_id, platform, username, email, first_purchase_date, total_orders, total_revenue)
                    VALUES ({_ph(7)})
                """, (user_id, platform, username, email, sale_date, 0, 0.0))
                
                if USE_POSTGRES:
                    cur.execute("SELECT lastval()")
                    customer_id = cur.fetchone()[0]
                else:
                    customer_id = cur.lastrowid
                
                imported += 1
            
            # Add order if we have details
            if order_id or sale_date or amount > 0:
                cur.execute(f"""
                    INSERT INTO soleops_customer_orders 
                    (customer_id, order_id, platform, sale_date, amount, item_sku, item_name)
                    VALUES ({_ph(7)})
                """, (customer_id, order_id, platform, sale_date, amount, sku, item_name))
                
                # Update customer totals
                cur.execute(f"""
                    UPDATE soleops_customers
                    SET total_orders = total_orders + 1,
                        total_revenue = total_revenue + {_ph()},
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = {_ph()}
                """, (amount, customer_id))
            
            conn.commit()
            conn.close()
            
    except Exception as e:
        st.error(f"Error importing CSV: {str(e)}")
    
    return imported

# Main UI
st.title("👥 SoleOps Customer CRM")
st.caption("Track repeat buyers across platforms and build lasting customer relationships")

user_id = get_user_id()
stats = get_customer_stats(user_id)

# Stats row
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Customers", stats["total_customers"])
with col2:
    st.metric("VIP Customers", stats["vip_count"])
with col3:
    st.metric("Banned", stats["banned_count"])
with col4:
    st.metric("Total Revenue", f"${stats['total_revenue']:,.2f}")
with col5:
    st.metric("Avg Revenue/Customer", f"${stats['avg_revenue_per_customer']:,.2f}")

st.markdown("---")

# Main tabs
tab_list, tab_vip, tab_banned, tab_feedback, tab_comms, tab_import = st.tabs([
    "👥 Customer List", "⭐ VIP Customers", "🚫 Ban List", 
    "📝 Feedback History", "💬 Communications", "📥 Import"
])

# Tab: Customer List
with tab_list:
    # Filters
    with st.expander("🔍 Filters", expanded=False):
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        
        with fcol1:
            filter_platform = st.selectbox