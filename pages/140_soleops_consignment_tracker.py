import streamlit as st
import datetime
from decimal import Decimal, ROUND_HALF_UP
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Consignment Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_consignment_shops (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                shop_name VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                default_fee_percent DECIMAL(5,2) DEFAULT 20.00,
                contact_info TEXT,
                payment_terms VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_consignment_items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                name VARCHAR(255) NOT NULL,
                size VARCHAR(20),
                consignment_shop_id INTEGER REFERENCES soleops_consignment_shops(id),
                date_sent DATE,
                asking_price DECIMAL(10,2),
                original_cost DECIMAL(10,2) DEFAULT 0,
                consignment_fee_percent DECIMAL(5,2),
                status VARCHAR(50) DEFAULT 'Sent',
                listed_date DATE,
                sold_date DATE,
                sold_price DECIMAL(10,2),
                payout_received DECIMAL(10,2),
                payout_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_consignment_shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shop_name TEXT NOT NULL,
                location TEXT,
                default_fee_percent REAL DEFAULT 20.00,
                contact_info TEXT,
                payment_terms TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_consignment_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                name TEXT NOT NULL,
                size TEXT,
                consignment_shop_id INTEGER,
                date_sent DATE,
                asking_price REAL,
                original_cost REAL DEFAULT 0,
                consignment_fee_percent REAL,
                status TEXT DEFAULT 'Sent',
                listed_date DATE,
                sold_date DATE,
                sold_price REAL,
                payout_received REAL,
                payout_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consignment_shop_id) REFERENCES soleops_consignment_shops(id)
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id():
    return st.session_state.get("user_id", 1)

def calculate_consignment_profit(sold_price, fee_percent, original_cost):
    if sold_price is None or sold_price == 0:
        return None
    sold = Decimal(str(sold_price))
    fee = Decimal(str(fee_percent)) / Decimal("100")
    cost = Decimal(str(original_cost)) if original_cost else Decimal("0")
    consignment_fee = (sold * fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    payout = sold - consignment_fee
    net_profit = payout - cost
    return {
        "sold_price": float(sold),
        "consignment_fee": float(consignment_fee),
        "expected_payout": float(payout),
        "net_profit": float(net_profit),
        "profit_margin": float((net_profit / sold * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if sold > 0 else 0
    }

def calculate_direct_sale_profit(sold_price, original_cost, platform_fee_percent=12.9):
    if sold_price is None or sold_price == 0:
        return None
    sold = Decimal(str(sold_price))
    fee = Decimal(str(platform_fee_percent)) / Decimal("100")
    cost = Decimal(str(original_cost)) if original_cost else Decimal("0")
    platform_fee = (sold * fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net = sold - platform_fee - cost
    return {
        "sold_price": float(sold),
        "platform_fee": float(platform_fee),
        "net_profit": float(net),
        "profit_margin": float((net / sold * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if sold > 0 else 0
    }

def get_shops(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT id, shop_name, location, default_fee_percent, contact_info, payment_terms FROM soleops_consignment_shops WHERE user_id = {ph} ORDER BY shop_name", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_shop_by_id(shop_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT id, shop_name, location, default_fee_percent, contact_info, payment_terms FROM soleops_consignment_shops WHERE id = {ph}", (shop_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_shop(user_id, shop_name, location, default_fee_percent, contact_info, payment_terms):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_consignment_shops (user_id, shop_name, location, default_fee_percent, contact_info, payment_terms)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, shop_name, location, default_fee_percent, contact_info, payment_terms))
    conn.commit()
    conn.close()

def update_shop(shop_id, shop_name, location, default_fee_percent, contact_info, payment_terms):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        UPDATE soleops_consignment_shops 
        SET shop_name = {ph}, location = {ph}, default_fee_percent = {ph}, contact_info = {ph}, payment_terms = {ph}
        WHERE id = {ph}
    """, (shop_name, location, default_fee_percent, contact_info, payment_terms, shop_id))
    conn.commit()
    conn.close()

def delete_shop(shop_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_consignment_shops WHERE id = {ph}", (shop_id,))
    conn.commit()
    conn.close()

def get_items(user_id, status_filter=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    query = f"""
        SELECT i.id, i.sku, i.name, i.size, i.consignment_shop_id, s.shop_name, i.date_sent, 
               i.asking_price, i.original_cost, i.consignment_fee_percent, i.status, i.listed_date,
               i.sold_date, i.sold_price, i.payout_received, i.payout_date, i.notes, s.payment_terms
        FROM soleops_consignment_items i
        LEFT JOIN soleops_consignment_shops s ON i.consignment_shop_id = s.id
        WHERE i.user_id = {ph}
    """
    params = [user_id]
    if status_filter:
        if isinstance(status_filter, list):
            placeholders = ", ".join([ph for _ in status_filter])
            query += f" AND i.status IN ({placeholders})"
            params.extend(status_filter)
        else:
            query += f" AND i.status = {ph}"
            params.append(status_filter)
    query += " ORDER BY i.date_sent DESC"
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return rows

def add_item(user_id, sku, name, size, consignment_shop_id, date_sent, asking_price, original_cost, consignment_fee_percent, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_consignment_items 
        (user_id, sku, name, size, consignment_shop_id, date_sent, asking_price, original_cost, consignment_fee_percent, status, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'Sent', {ph})
    """, (user_id, sku, name, size, consignment_shop_id, date_sent, asking_price, original_cost, consignment_fee_percent, notes))
    conn.commit()
    conn.close()

def update_item_status(item_id, new_status, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    updates = [f"status = {ph}"]
    params = [new_status]
    if new_status == "Listed" and "listed_date" in kwargs:
        updates.append(f"listed_date = {ph}")
        params.append(kwargs["listed_date"])
    if new_status == "Sold":
        if "sold_date" in kwargs:
            updates.append(f"sold_date = {ph}")
            params.append(kwargs["sold_date"])
        if "sold_price" in kwargs:
            updates.append(f"sold_price = {ph}")
            params.append(kwargs["sold_price"])
    if new_status == "Payout Received":
        if "payout_received" in kwargs:
            updates.append(f"payout_received = {ph}")
            params.append(kwargs["payout_received"])
        if "payout_date" in kwargs:
            updates.append(f"payout_date = {ph}")
            params.append(kwargs["payout_date"])
    params.append(item_id)
    cur.execute(f"UPDATE soleops_consignment_items SET {', '.join(updates)} WHERE id = {ph}", tuple(params))
    conn.commit()
    conn.close()

def update_item(item_id, sku, name, size, consignment_shop_id, date_sent, asking_price, original_cost, consignment_fee_percent, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        UPDATE soleops_consignment_items 
        SET sku = {ph}, name = {ph}, size = {ph}, consignment_shop_id = {ph}, date_sent = {ph}, 
            asking_price = {ph}, original_cost = {ph}, consignment_fee_percent = {ph}, notes = {ph}
        WHERE id = {ph}
    """, (sku, name, size, consignment_shop_id, date_sent, asking_price, original_cost, consignment_fee_percent, notes, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_consignment_items WHERE id = {ph}", (item_id,))
    conn.commit()
    conn.close()

def parse_payment_terms_days(payment_terms):
    if not payment_terms:
        return 14
    terms = payment_terms.lower()
    if "7" in terms or "week" in terms:
        return 7
    if "30" in terms or "month" in terms:
        return 30
    if "14" in terms or "two week" in terms:
        return 14
    return 14

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

# Main content
st.title("👟 SoleOps Consignment Tracker")
st.caption("Track sneakers sent to consignment shops with fees, sale status, and profit calculation")

user_id = get_user_id()

tab1, tab2, tab3, tab4 = st.tabs(["📦 Active Consignments", "✅ Sold Items", "🏪 Consignment Shops", "📊 Analytics"])

with tab1:
    st.subheader("Active Consignments")
    
    shops = get_shops(user_id)
    if not shops:
        st.warning("⚠️ Please add a consignment shop first in the 'Consignment Shops' tab")
    else:
        with st.expander("➕ Add New Consignment Item", expanded=False):
            with st.form("add_item_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Sneaker Name *", placeholder="Air Jordan 1 Retro High OG")
                    new_sku = st.text_input("SKU", placeholder="555088-134")
                    new_size = st.text_input("Size", placeholder="10.5")
                    new_original_cost = st.number_input("Original Cost ($)", min_value=0.0, value=0.0, step=1.0)
                with col2:
                    shop_options = {s[0]: f"{s[1]} ({s[2] or 'No location'})" for s in shops}
                    selected_shop_id = st.selectbox("Consignment Shop *", options=list(shop_options.keys()), format_func=lambda x: shop_options[x])
                    selected_shop = next((s for s in shops if s[0] == selected_shop_id), None)
                    default_fee = selected_shop[3] if selected_shop else 20.0
                    new_fee_percent = st.number_input("Consignment Fee %", min_value=0.0, max_value=100.0, value=float(default_fee), step=0.5)
                    new_asking_price = st.number_input("Asking Price ($)", min_value=0.0, value=0.0, step=1.0)
                    new_date_sent = st.date_input("Date Sent", value=datetime.date.today())
                
                new_notes = st.text_area("Notes", placeholder="Any special instructions or details...")
                
                if new_asking_price > 0:
                    preview = calculate_consignment_profit(new_asking_price, new_fee_percent, new_original_cost)
                    if preview:
                        st.info(f"💰 **Expected Payout Preview**: ${preview['expected_payout']:.2f} (Fee: ${preview['consignment_fee']:.2f}) | Net Profit: ${preview['net_profit']:.2f}")
                
                if st.form_submit_button("Add Item", type="primary"):
                    if new_name and selected_shop_id:
                        add_item(user_id, new_sku, new_name, new_size, selected_shop_id, new_date_sent, new_asking_price, new_original_cost, new_fee_percent, new_notes)
                        st.success("✅ Item added to consignment!")
                        st.rerun()
                    else:
                        st.error("Please fill in required fields (Name and Shop)")
    
    st.markdown("---")
    
    active_items = get_items(user_id, status_filter=["Sent", "Listed", "Sold"])
    
    if not active_items:
        st.info("📦 No active consignment items. Add your first item above!")
    else:
        for item in active_items:
            item_id, sku, name, size, shop_id, shop_name, date_sent, asking_price, original_cost, fee_percent, status, listed_date, sold_date, sold_price, payout_received, payout_date, notes, payment_terms = item
            
            status_colors = {"Sent": "🟡", "Listed": "🟢", "Sold": "🔵", "Payout Received": "✅"}
            status_icon = status_colors.get(status, "⚪")
            
            with st.expander(f"{status_icon} {name} - Size {size or 'N/A'} | {shop_name or 'Unknown Shop'} | Status: {status}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**SKU:** {sku or 'N/A'}")
                    st.write(f"**Date Sent:** {date_sent}")
                    st.write(f"**Asking Price:** ${asking_price:.2f}" if asking_price else "**Asking Price:** Not set")
                    st.write(f"**Original Cost:** ${original_cost:.2f}" if original_cost else "**Original Cost:** $0.00")
                    st.write(f"**Consignment Fee:** {fee_percent}%")
                
                with col2:
                    if status == "Listed" and listed_date:
                        st.write(f"**Listed Date:** {listed_date}")
                    if status in ["Sold", "Payout Received"]:
                        st.write(f"**Sold Date:** {sold_date}")
                        st.write(f"**Sold Price:** ${sold_price:.2f}" if sold_price else "**Sold Price:** N/A")
                        if sold_price and fee_percent:
                            profit_calc = calculate_consignment_profit(sold_price, fee_percent, original_cost)
                            if profit_calc:
                                st.write(f"**Expected Payout:** ${profit_calc['expected_payout']:.2f}")
                                st.write(f"**Net Profit:** ${profit_calc['net_profit']:.2f}")
                    
                    if status == "Sold" and sold_date and payment_terms:
                        days_since_sold = (datetime.date.today() - sold_date).days if isinstance(sold_date, datetime.date) else 0
                        payment_due_days = parse_payment_terms_days(payment_terms)
                        if days_since_sold > payment_due_days:
                            st.error(f"⚠️ **OVERDUE PAYOUT** - {days_since_sold - payment_due_days} days past due!")
                
                with col3:
                    if notes:
                        st.write(f"**Notes:** {notes}")
                
                st.markdown("---")
                
                status_col1, status_col2, status_col3, status_col4 = st.columns(4)
                
                with status_col1:
                    if status == "Sent":
                        if st.button("📋 Mark as Listed", key=f"list_{item_id}"):
                            update_item_status(item_id, "Listed", listed_date=datetime.date.today())
                            st.rerun()
                
                with status_col2:
                    if status in ["Sent", "Listed"]:
                        with st.form(f"sold_form_{item_id}"):
                            sold_price_input = st.number_input("Sold Price ($)", min_value=0.0, value=float(asking_price) if asking_price else 0.0, key=f"sold_price_{item_id}")
                            if st.form_submit_button("💵 Mark as Sold"):
                                update_item_status(item_id, "Sold", sold_date=datetime.date.today(), sold_price=sold_price_input)
                                st.rerun()
                
                with status_col3:
                    if status == "Sold":
                        expected_payout = 0
                        if sold_price and fee_percent:
                            calc = calculate_consignment_profit(sold_price, fee_percent, original_cost)
                            expected_payout = calc['expected_payout'] if calc else 0
                        with st.form(f"payout_form_{item_id}"):
                            payout_input = st.number_input("Payout Amount ($)", min_value=0.0, value=expected_payout, key=f"payout_{item_id}")
                            if st.form_submit_button("✅ Mark Payout Received"):
                                update_item_status(item_id, "Payout Received", payout_received=payout_input, payout_date=datetime.date.today())
                                st.rerun()
                
                with status_col4:
                    if st.button("🗑️ Delete", key=f"del_{item_id}"):
                        delete_item(item_id)
                        st.rerun()

with tab2:
    st.subheader("Sold Items (Payout Received)")
    
    sold_items = get_items(user_id, status_filter="Payout Received")
    
    if not sold_items:
        st.info("📦 No completed sales yet. Items will appear here after payout is received.")
    else:
        total_revenue = 0
        total_profit = 0
        
        for item in sold_items:
            item_id, sku, name, size, shop_id, shop_name, date_sent, asking_price, original_cost, fee_percent, status, listed_date, sold_date, sold_price, payout_received, payout_date, notes, payment_terms = item
            
            if payout_received:
                total_revenue += float(payout_received)
            if sold_price and fee_percent:
                calc = calculate_consignment_profit(sold_price, fee_percent, original_cost)
                if calc:
                    total_profit += calc['net_profit']
            
            with st.expander(f"✅ {name} - Size {size or 'N/A'} | Sold: ${sold_price:.2f}" if sold_price else f"✅ {name} - Size {size or 'N/A'}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**SKU:** {sku or 'N/A'}")
                    st.write(f"**Shop:** {shop_name or 'Unknown'}")
                    st.write(f"**Date Sent:** {date_sent}")
                with col2:
                    st.write(f"**Sold Date:** {sold_date}")
                    st.write(f"**Sold Price:** ${sold_price:.2f}" if sold_price else "N/A")
                    st.write(f"**Payout Received:** ${payout_received:.2f}" if payout_received else "N/A")
                    st.write(f"**Payout Date:** {payout_date}")
                with col3:
                    if sold_price and fee_percent:
                        calc = calculate_consignment_profit(sold_price, fee_percent, original_cost)
                        if calc:
                            st.metric("Net Profit", f"${calc['net_profit']:.2f}", f"{calc['profit_margin']:.1f}%")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Total Revenue", f"${total_revenue:.2f}")
        with col2:
            st.metric("📈 Total Profit", f"${total_profit:.2f}")

with tab3:
    st.subheader("Manage Consignment Shops")
    
    with st.expander("➕ Add New Shop", expanded=False):
        with st.form("add_shop_form"):
            col1, col2 = st.columns(2)
            with col1:
                shop_name = st.text_input("Shop Name *", placeholder="Flight Club NYC")
                shop_location = st.text_input("Location", placeholder="New York, NY")
                shop_fee = st.number_input("Default Fee %", min_value=0.0, max_value=100.0, value=20.0, step=0.5)
            with col2:
                shop_contact = st.text_area("Contact Info", placeholder="Email, phone, address...")
                shop_terms = st.selectbox("Payment Terms", ["7 days after sale", "14 days after sale", "30 days after sale", "Upon request", "Other"])
            
            if st.form_submit_button("Add Shop", type="primary"):
                if shop_name:
                    add_shop(user_id, shop_name, shop_location, shop_fee, shop_contact, shop_terms)
                    st.success(f"✅ Added {shop_name}")
                    st.rerun()
                else:
                    st.error("Shop name is required")
    
    st.markdown("---")
    
    shops = get_shops(user_id)
    if not shops:
        st.info("🏪 No consignment shops added yet. Add your first shop above!")
    else:
        for shop in shops:
            shop_id, shop_name, location, default_fee, contact_info, payment_terms = shop
            
            with st.expander(f"🏪 {shop_name} - {location or 'No location'} | Fee: {default_fee}%"):
                with st.form(f"edit_shop_{shop_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_name = st.text_input("Shop Name", value=shop_name, key=f"name_{shop_id}")
                        edit_location = st.text_input("Location", value=location or "", key=f"loc_{shop_id}")
                        edit_fee = st.number_input("Default Fee %", min_value=0.0, max_value=100.0, value=float(default_fee), key=f"fee_{shop_id}")
                    with col2:
                        edit_contact = st.text_area("Contact Info", value=contact_info or "", key=f"contact_{shop_id}")
                        edit_terms = st.text_input("Payment Terms", value=payment_terms or "", key=f"terms_{shop_id}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.form_submit_button("💾 Update Shop"):
                            update_shop(shop_id, edit_name, edit_location, edit_fee, edit_contact, edit_terms)
                            st.success("Shop updated!")
                            st.rerun()
                    with col_btn2:
                        if st.form_submit_button("🗑️ Delete Shop", type="secondary"):
                            delete_shop(shop_id)
                            st.rerun()

with tab4:
    st.subheader("Consignment Analytics")
    
    all_items = get_items(user_id)
    
    if not all_items:
        st.info("📊 Add some consignment items to see analytics!")
    else:
        total_consigned_value = 0
        total_sold_value = 0
        pending_payouts = 0
        profit_by_shop = {}
        overdue_items = []
        
        for item in all_items:
            item_id, sku, name, size, shop_id, shop_name, date_sent, asking_price, original_cost, fee_percent, status, listed_date, sold_date, sold_price, payout_received, payout_date, notes, payment_terms = item
            
            if asking_price and status in ["Sent", "Listed"]:
                total_consigned_value += float(asking_price)
            
            if sold_price and status in ["Sold", "Payout Received"]:
                total_sold_value += float(sold_price)
            
            if status == "Sold" and sold_price and fee_percent:
                calc = calculate_consignment_profit(sold_price, fee_percent, original_cost)
                if calc:
                    pending_payouts += calc['expected_payout']
                    
                    if sold_date and payment_terms:
                        sold_dt = sold_date if isinstance(sold_date, datetime.date) else datetime.date.fromisoformat(str(sold_date))
                        days_since = (datetime.date.today() - sold_dt).days
                        due_days = parse_payment_terms_days(payment_terms)
                        if days_since > due_days:
                            overdue_items.append({
                                "name": name,
                                "shop": shop_name,
                                "sold_date": sold_date,
                                "days_overdue": days_since - due_days,
                                "expected_payout": calc['expected_payout']
                            })
            
            if status == "Payout Received" and sold_price and fee_percent:
                calc = calculate_consignment_profit(sold_price, fee_percent, original_cost)
                if calc:
                    shop_key = shop_name or "Unknown"
                    if shop_key not in profit_by_shop:
                        profit_by_shop[shop_key] = {"profit": 0, "count": 0, "revenue": 0}