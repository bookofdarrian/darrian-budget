import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Bulk Listing Actions", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_bulk_action_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                item_ids TEXT NOT NULL,
                action_details TEXT,
                items_affected INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'completed',
                can_undo BOOLEAN DEFAULT TRUE,
                undo_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                name VARCHAR(255) NOT NULL,
                brand VARCHAR(100),
                size VARCHAR(20),
                color VARCHAR(50),
                condition VARCHAR(50),
                purchase_price DECIMAL(10,2),
                list_price DECIMAL(10,2),
                platform VARCHAR(50),
                status VARCHAR(50) DEFAULT 'active',
                days_listed INTEGER DEFAULT 0,
                ebay_listing_id VARCHAR(100),
                mercari_listing_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_bulk_action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                item_ids TEXT NOT NULL,
                action_details TEXT,
                items_affected INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed',
                can_undo INTEGER DEFAULT 1,
                undo_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                name TEXT NOT NULL,
                brand TEXT,
                size TEXT,
                color TEXT,
                condition TEXT,
                purchase_price REAL,
                list_price REAL,
                platform TEXT,
                status TEXT DEFAULT 'active',
                days_listed INTEGER DEFAULT 0,
                ebay_listing_id TEXT,
                mercari_listing_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
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
def get_user_id():
    return st.session_state.get("user_id", 1)

def get_inventory_items(user_id, status_filter="active"):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    if status_filter == "all":
        cur.execute(f"""
            SELECT id, sku, name, brand, size, color, condition, purchase_price, 
                   list_price, platform, status, days_listed, ebay_listing_id, mercari_listing_id
            FROM soleops_inventory 
            WHERE user_id = {ph}
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cur.execute(f"""
            SELECT id, sku, name, brand, size, color, condition, purchase_price, 
                   list_price, platform, status, days_listed, ebay_listing_id, mercari_listing_id
            FROM soleops_inventory 
            WHERE user_id = {ph} AND status = {ph}
            ORDER BY created_at DESC
        """, (user_id, status_filter))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "sku": row[1] or "",
            "name": row[2],
            "brand": row[3] or "",
            "size": row[4] or "",
            "color": row[5] or "",
            "condition": row[6] or "",
            "purchase_price": float(row[7]) if row[7] else 0.0,
            "list_price": float(row[8]) if row[8] else 0.0,
            "platform": row[9] or "",
            "status": row[10] or "active",
            "days_listed": row[11] or 0,
            "ebay_listing_id": row[12] or "",
            "mercari_listing_id": row[13] or ""
        })
    return items

def log_bulk_action(user_id, action_type, item_ids, action_details, items_affected, undo_data=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO soleops_bulk_action_logs 
        (user_id, action_type, item_ids, action_details, items_affected, undo_data)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, action_type, json.dumps(item_ids), action_details, items_affected, 
          json.dumps(undo_data) if undo_data else None))
    
    conn.commit()
    cur.close()
    conn.close()

def get_action_logs(user_id, limit=50):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, action_type, item_ids, action_details, items_affected, status, can_undo, undo_data, created_at
        FROM soleops_bulk_action_logs
        WHERE user_id = {ph}
        ORDER BY created_at DESC
        LIMIT {ph}
    """, (user_id, limit))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    logs = []
    for row in rows:
        logs.append({
            "id": row[0],
            "action_type": row[1],
            "item_ids": json.loads(row[2]) if row[2] else [],
            "action_details": row[3],
            "items_affected": row[4],
            "status": row[5],
            "can_undo": bool(row[6]) if USE_POSTGRES else bool(row[6]),
            "undo_data": json.loads(row[7]) if row[7] else None,
            "created_at": row[8]
        })
    return logs

def bulk_update_prices(user_id, item_ids, adjustment_type, adjustment_value):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    # Get current prices for undo
    undo_data = []
    for item_id in item_ids:
        cur.execute(f"SELECT id, list_price FROM soleops_inventory WHERE id = {ph} AND user_id = {ph}", 
                   (item_id, user_id))
        row = cur.fetchone()
        if row:
            undo_data.append({"id": row[0], "old_price": float(row[1]) if row[1] else 0})
    
    # Apply price changes
    for item_id in item_ids:
        cur.execute(f"SELECT list_price FROM soleops_inventory WHERE id = {ph} AND user_id = {ph}", 
                   (item_id, user_id))
        row = cur.fetchone()
        if row:
            current_price = float(row[0]) if row[0] else 0
            if adjustment_type == "percentage":
                new_price = current_price * (1 + adjustment_value / 100)
            else:
                new_price = current_price + adjustment_value
            new_price = max(0, round(new_price, 2))
            
            cur.execute(f"""
                UPDATE soleops_inventory 
                SET list_price = {ph}, updated_at = {ph}
                WHERE id = {ph} AND user_id = {ph}
            """, (new_price, datetime.now().isoformat(), item_id, user_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return undo_data

def bulk_relist_items(user_id, item_ids, platforms):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    undo_data = []
    for item_id in item_ids:
        cur.execute(f"SELECT id, platform, days_listed, status FROM soleops_inventory WHERE id = {ph} AND user_id = {ph}", 
                   (item_id, user_id))
        row = cur.fetchone()
        if row:
            undo_data.append({
                "id": row[0], 
                "old_platform": row[1], 
                "old_days_listed": row[2],
                "old_status": row[3]
            })
            
            platform_str = ", ".join(platforms)
            cur.execute(f"""
                UPDATE soleops_inventory 
                SET platform = {ph}, days_listed = 0, status = 'active', updated_at = {ph}
                WHERE id = {ph} AND user_id = {ph}
            """, (platform_str, datetime.now().isoformat(), item_id, user_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return undo_data

def bulk_archive_items(user_id, item_ids):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    undo_data = []
    for item_id in item_ids:
        cur.execute(f"SELECT id, status FROM soleops_inventory WHERE id = {ph} AND user_id = {ph}", 
                   (item_id, user_id))
        row = cur.fetchone()
        if row:
            undo_data.append({"id": row[0], "old_status": row[1]})
            
            cur.execute(f"""
                UPDATE soleops_inventory 
                SET status = 'archived', updated_at = {ph}
                WHERE id = {ph} AND user_id = {ph}
            """, (datetime.now().isoformat(), item_id, user_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return undo_data

def undo_action(user_id, log_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT action_type, undo_data FROM soleops_bulk_action_logs 
        WHERE id = {ph} AND user_id = {ph} AND can_undo = {ph}
    """, (log_id, user_id, True if USE_POSTGRES else 1))
    
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return False
    
    action_type = row[0]
    undo_data = json.loads(row[1]) if row[1] else []
    
    for item in undo_data:
        if action_type == "price_adjustment":
            cur.execute(f"""
                UPDATE soleops_inventory 
                SET list_price = {ph}, updated_at = {ph}
                WHERE id = {ph} AND user_id = {ph}
            """, (item["old_price"], datetime.now().isoformat(), item["id"], user_id))
        elif action_type == "relist":
            cur.execute(f"""
                UPDATE soleops_inventory 
                SET platform = {ph}, days_listed = {ph}, status = {ph}, updated_at = {ph}
                WHERE id = {ph} AND user_id = {ph}
            """, (item["old_platform"], item["old_days_listed"], item["old_status"], 
                  datetime.now().isoformat(), item["id"], user_id))
        elif action_type == "archive":
            cur.execute(f"""
                UPDATE soleops_inventory 
                SET status = {ph}, updated_at = {ph}
                WHERE id = {ph} AND user_id = {ph}
            """, (item["old_status"], datetime.now().isoformat(), item["id"], user_id))
    
    cur.execute(f"""
        UPDATE soleops_bulk_action_logs 
        SET can_undo = {ph}, status = 'undone'
        WHERE id = {ph}
    """, (False if USE_POSTGRES else 0, log_id))
    
    conn.commit()
    cur.close()
    conn.close()
    return True

def get_ai_pricing_suggestions(items):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        items_summary = []
        for item in items[:20]:  # Limit to 20 items for API
            items_summary.append(f"- {item['name']} ({item['brand']}, Size {item['size']}): "
                               f"Listed at ${item['list_price']:.2f}, {item['days_listed']} days listed, "
                               f"Platform: {item['platform']}")
        
        prompt = f"""Analyze these sneaker/resale inventory items and provide bulk pricing suggestions:

{chr(10).join(items_summary)}

For each item category, suggest:
1. Optimal price adjustment percentage or fixed amount
2. Priority items that need immediate price drops (stale inventory)
3. Items that could be priced higher based on demand signals

Respond in a structured format with specific recommendations."""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"

def add_sample_inventory(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    samples = [
        ("SKU001", "Air Jordan 1 Retro High OG", "Nike", "10", "University Blue", "New", 170, 285, "eBay", 15),
        ("SKU002", "Yeezy Boost 350 V2", "Adidas", "9.5", "Zebra", "New", 230, 320, "Mercari", 30),
        ("SKU003", "Nike Dunk Low", "Nike", "11", "Panda", "New", 110, 165, "eBay, Mercari", 7),
        ("SKU004", "New Balance 550", "New Balance", "10.5", "White Green", "New", 130, 180, "eBay", 45),
        ("SKU005", "Air Force 1 Low", "Nike", "12", "Triple White", "New", 90, 125, "Mercari", 60),
        ("SKU006", "Jordan 4 Retro", "Nike", "9", "Military Black", "New", 210, 340, "eBay", 3),
        ("SKU007", "Adidas Samba OG", "Adidas", "10", "White Black", "New", 100, 145, "eBay, Mercari", 22),
        ("SKU008", "Nike SB Dunk Low", "Nike", "11.5", "Court Purple", "Used", 280, 380, "eBay", 55),
    ]
    
    for sample in samples:
        cur.execute(f"""
            INSERT INTO soleops_inventory 
            (user_id, sku, name, brand, size, color, condition, purchase_price, list_price, platform, days_listed)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id,) + sample)
    
    conn.commit()
    cur.close()
    conn.close()

# Main UI
st.title("📦 SoleOps Bulk Listing Actions")
st.markdown("Batch edit, relist, or remove multiple inventory items with one-click actions")

user_id = get_user_id()

# Initialize session state
if "selected_items" not in st.session_state:
    st.session_state.selected_items = set()

tab1, tab2, tab3 = st.tabs(["🎯 Select Items", "⚡ Bulk Actions", "📜 Action History"])

with tab1:
    st.subheader("Select Inventory Items")
    
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        status_filter = st.selectbox("Filter by Status", ["active", "archived", "all"], key="status_filter")
    with col2:
        if st.button("🔄 Refresh Inventory"):
            st.rerun()
    with col3:
        if st.button("📥 Add Sample Data"):
            add_sample_inventory(user_id)
            st.success("Sample inventory added!")
            st.rerun()
    
    items = get_inventory_items(user_id, status_filter)
    
    if not items:
        st.info("No inventory items found. Add some items or click 'Add Sample Data' to get started.")
    else:
        # Select all / Deselect all
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("✅ Select All"):
                st.session_state.selected_items = set(item["id"] for item in items)
                st.rerun()
        with col2:
            if st.button("❌ Clear Selection"):
                st.session_state.selected_items = set()
                st.rerun()
        with col3:
            st.markdown(f"**{len(st.session_state.selected_items)}** items selected")
        
        st.markdown("---")
        
        # Display items as a grid with checkboxes
        for i, item in enumerate(items):
            col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 1, 1, 1, 1])
            
            with col1:
                is_selected = item["id"] in st.session_state.selected_items
                if st.checkbox("", value=is_selected, key=f"item_{item['id']}"):
                    st.session_state.selected_items.add(item["id"])
                else:
                    st.session_state.selected_items.discard(item["id"])
            
            with col2:
                st.markdown(f"**{item['name']}**")
                st.caption(f"SKU: {item['sku']} | {item['brand']} | Size {item['size']}")
            
            with col3:
                st.metric("List Price", f"${item['list_price']:.2f}")
            
            with col4:
                days = item["days_listed"]
                color = "🔴" if days > 45 else "🟡" if days > 20 else "🟢"
                st.markdown(f"{color} **{days}** days")
            
            with col5:
                st.markdown(f"📱 {item['platform']}")
            
            with col6:
                status_emoji = "✅" if item["status"] == "active" else "📦"
                st.markdown(f"{status_emoji} {item['status'].title()}")
            
            if i < len(items) - 1:
                st.markdown("---")

with tab2:
    st.subheader("Bulk Actions")
    
    selected_count = len(st.session_state.selected_items)
    
    if selected_count == 0:
        st.warning("⚠️ Please select items from the 'Select Items' tab first")
    else:
        st.success(f"✅ {selected_count} items selected for bulk action")
        
        action_type = st.selectbox(
            "Choose Action",
            ["💰 Adjust Prices", "🔄 Relist Items", "📦 Archive/Remove Items", "🤖 AI Pricing Suggestions"]
        )
        
        st.markdown("---")
        
        if action_type == "💰 Adjust Prices":
            st.markdown("### Price Adjustment")
            
            col1, col2 = st.columns(2)
            with col1:
                adj_method = st.radio("Adjustment Method", ["Percentage", "Fixed Amount"])
            with col2:
                if adj_method == "Percentage":
                    adj_value = st.number_input("Percentage (%)", min_value=-50.0, max_value=100.0, value=0.0, step=5.0,
                                               help="Positive = increase, Negative = decrease")
                else:
                    adj_value = st.number_input("Amount ($)", min_value=-500.0, max_value=500.0, value=0.0, step=5.0,
                                               help="Positive = increase, Negative = decrease")
            
            # Preview
            if adj_value != 0:
                st.markdown("#### Preview Changes")
                preview_items = get_inventory_items(user_id, "all")
                preview_items = [i for i in preview_items if i["id"] in st.session_state.selected_items][:5]
                
                for item in preview_items:
                    old_price = item["list_price"]
                    if adj_method == "Percentage":
                        new_price = old_price * (1 + adj_value / 100)
                    else:
                        new_price = old_price + adj_value
                    new_price = max(0, round(new_price, 2))
                    
                    change = new_price - old_price
                    change_str = f"+${change:.2f}" if change > 0 else f"-${abs(change):.2f}"
                    st.markdown(f"• {item['name']}: ${old_price:.2f} → **${new_price:.2f}** ({change_str})")
                
                if len(st.session_state.selected_items) > 5:
                    st.caption(f"... and {len(st.session_state.selected_items) - 5} more items")
            
            if st.button("🚀 Apply Price Changes", type="primary"):
                with st.spinner("Applying price changes..."):
                    undo_data = bulk_update_prices(
                        user_id, 
                        list(st.session_state.selected_items), 
                        "percentage" if adj_method == "Percentage" else "fixed",
                        adj_value
                    )
                    log_bulk_action(
                        user_id,
                        "price_adjustment",
                        list(st.session_state.selected_items),
                        f"{adj_method}: {adj_value}{'%' if adj_method == 'Percentage' else '$'}",
                        len(st.session_state.selected_items),
                        undo_data
                    )
                st.success(f"✅ Updated prices for {selected_count} items!")
                st.session_state.selected_items = set()
                st.rerun()
        
        elif action_type == "🔄 Relist Items":
            st.markdown("### Relist Items")
            
            st.markdown("Select platforms to relist on:")
            col1, col2 = st.columns(2)
            with col1:
                list_ebay = st.checkbox("eBay", value=True)
            with col2:
                list_mercari = st.checkbox("Mercari", value=True)
            
            platforms = []
            if list_ebay:
                platforms.append("eBay")
            if list_mercari:
                platforms.append("Mercari")
            
            st.info("ℹ️ Relisting will reset the 'days listed' counter and mark items as active")
            
            if platforms and st.button("🔄 Relist Selected Items", type="primary"):
                with st.spinner("Relisting items..."):
                    undo_data = bulk_relist_items(user_id, list(st.session_state.selected_items), platforms)
                    log_bulk_action(
                        user_id,
                        "relist",
                        list(st.session_state.selected_items),
                        f"Platforms: {', '.join(platforms)}",
                        len(st.session_state.selected_items),
                        undo_data
                    )
                st.success(f"✅ Relisted {selected_count} items on {', '.join(platforms)}!")
                st.session_state.selected_items = set()
                st.rerun()
        
        elif action_type == "📦 Archive/Remove Items":
            st.markdown("### Archive Items")
            
            st.warning("⚠️ This will archive the selected items. They can be restored from Action History.")
            
            # Confirmation
            confirm = st.checkbox("I confirm I want to archive these items")
            
            if confirm and st.button("📦 Archive Selected Items", type="primary"):
                with st.spinner("Archiving items..."):
                    undo_data = bulk_archive_items(user_id, list(st.session_state.selected_items))
                    log_bulk_action(
                        user_id,
                        "archive",
                        list(st.session_state.selected_items),
                        "Archived items",
                        len(st.session_state.selected_items),
                        undo_data
                    )
                st.success(f"✅ Archived {selected_count} items!")
                st.session_state.selected_items = set()
                st.rerun()
        
        elif action_type == "🤖 AI Pricing Suggestions":
            st.markdown("### AI-Powered Pricing Analysis")
            
            if st.button("🧠 Get AI Suggestions", type="primary"):
                with st.spinner("Analyzing inventory with Claude AI..."):
                    all_items = get_inventory_items(user_id, "all")
                    selected_items = [i for i in all_items if i["id"] in st.session_state.selected_items]
                    
                    suggestions = get_ai_pricing_suggestions(selected_items)
                    
                    if suggestions:
                        st.markdown("#### 🤖 Claude's Analysis")
                        st.markdown(suggestions)
                        
                        st.markdown("---")
                        st.markdown("#### Quick Actions Based on AI Suggestions")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("📉 Apply -10% to Stale Items"):
                                stale_ids = [i["id"] for i in selected_items if i["days_listed"] > 30]
                                if stale_ids:
                                    undo_data = bulk_update_prices(user_id, stale_ids, "percentage", -10)
                                    log_bulk_action(user_id, "price_adjustment", stale_ids, 
                                                   "AI-suggested: -10% for stale items", len(stale_ids), undo_data)
                                    st.success(f"Applied -10% to {len(stale_ids)} stale items")
                                    st.rerun()
                        with col2:
                            if st.button("📈 Apply +5% to Fresh Items"):
                                fresh_ids = [i["id"] for i in selected_items if i["days_listed"] < 7]
                                if fresh_ids:
                                    undo_data = bulk_update_prices(user_id, fresh_ids, "percentage", 5)
                                    log_bulk_action(user_id, "price_adjustment", fresh_ids,
                                                   "AI-suggested: +5% for fresh items", len(fresh_ids), undo_data)
                                    st.success(f"Applied +5% to {len(fresh_ids)} fresh items")
                                    st.rerun()
                        with col3:
                            if st.button("🔄 Relist Stale on Both"):
                                stale_ids = [i["id"] for i in selected_items if i["days_listed"] > 30]
                                if stale_ids:
                                    undo_data = bulk_relist_items(user_id, stale_ids, ["eBay", "Mercari"])
                                    log_bulk_action(user_id, "relist", stale_ids,
                                                   "AI-suggested: Relist stale items", len(stale_ids), undo_data)
                                    st.success(f"Relisted {len(stale_ids)} stale items")
                                    st.rerun()
                    else:
                        st.error("Could not get AI suggestions. Please check your API key in settings.")

with tab3:
    st.subheader("Action History")
    
    logs = get_action_logs(user_id)
    
    if not logs:
        st.info("No bulk actions performed yet. Actions will appear here after you perform them.")