import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Automated Listings Sync", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_listings_sync (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                listing_id VARCHAR(255),
                sync_status VARCHAR(50) DEFAULT 'pending',
                last_synced TIMESTAMP,
                price DECIMAL(10,2),
                quantity INTEGER DEFAULT 1,
                title VARCHAR(500),
                listing_url TEXT,
                master_price DECIMAL(10,2),
                master_quantity INTEGER DEFAULT 1,
                has_conflict BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sync_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                listing_sync_id INTEGER REFERENCES soleops_listings_sync(id) ON DELETE CASCADE,
                sku VARCHAR(100),
                platform VARCHAR(50),
                action VARCHAR(100),
                status VARCHAR(50),
                error_message TEXT,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_platform_connections (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                ebay_connected BOOLEAN DEFAULT FALSE,
                ebay_last_sync TIMESTAMP,
                mercari_connected BOOLEAN DEFAULT FALSE,
                mercari_last_sync TIMESTAMP,
                depop_connected BOOLEAN DEFAULT FALSE,
                depop_last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_listings_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                listing_id TEXT,
                sync_status TEXT DEFAULT 'pending',
                last_synced TIMESTAMP,
                price REAL,
                quantity INTEGER DEFAULT 1,
                title TEXT,
                listing_url TEXT,
                master_price REAL,
                master_quantity INTEGER DEFAULT 1,
                has_conflict INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                listing_sync_id INTEGER,
                sku TEXT,
                platform TEXT,
                action TEXT,
                status TEXT,
                error_message TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (listing_sync_id) REFERENCES soleops_listings_sync(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_platform_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                ebay_connected INTEGER DEFAULT 0,
                ebay_last_sync TIMESTAMP,
                mercari_connected INTEGER DEFAULT 0,
                mercari_last_sync TIMESTAMP,
                depop_connected INTEGER DEFAULT 0,
                depop_last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_sync_status(user_id, sku=None, platform=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    query = f"SELECT * FROM soleops_listings_sync WHERE user_id = {ph}"
    params = [user_id]
    if sku:
        query += f" AND sku = {ph}"
        params.append(sku)
    if platform:
        query += f" AND platform = {ph}"
        params.append(platform)
    query += " ORDER BY updated_at DESC"
    cur.execute(query, params)
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows

def get_platform_connections(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM soleops_platform_connections WHERE user_id = {ph}", (user_id,))
    row = cur.fetchone()
    if row:
        cols = [desc[0] for desc in cur.description]
        result = dict(zip(cols, row))
    else:
        cur.execute(f"INSERT INTO soleops_platform_connections (user_id) VALUES ({ph})", (user_id,))
        conn.commit()
        result = {
            "ebay_connected": False, "ebay_last_sync": None,
            "mercari_connected": False, "mercari_last_sync": None,
            "depop_connected": False, "depop_last_sync": None
        }
    conn.close()
    return result

def update_platform_connection(user_id, platform, connected):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    col_name = f"{platform.lower()}_connected"
    if USE_POSTGRES:
        cur.execute(f"""
            UPDATE soleops_platform_connections 
            SET {col_name} = {ph}, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = {ph}
        """, (connected, user_id))
    else:
        cur.execute(f"""
            UPDATE soleops_platform_connections 
            SET {col_name} = {ph}, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = {ph}
        """, (1 if connected else 0, user_id))
    conn.commit()
    conn.close()

def add_listing_sync(user_id, sku, platform, listing_id, price, quantity, title, listing_url, master_price, master_quantity):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    has_conflict = abs(float(price or 0) - float(master_price or 0)) > 0.01 or int(quantity or 0) != int(master_quantity or 0)
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO soleops_listings_sync 
            (user_id, sku, platform, listing_id, price, quantity, title, listing_url, master_price, master_quantity, has_conflict, sync_status)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'pending')
            RETURNING id
        """, (user_id, sku, platform, listing_id, price, quantity, title, listing_url, master_price, master_quantity, has_conflict))
        listing_id_result = cur.fetchone()[0]
    else:
        cur.execute(f"""
            INSERT INTO soleops_listings_sync 
            (user_id, sku, platform, listing_id, price, quantity, title, listing_url, master_price, master_quantity, has_conflict, sync_status)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'pending')
        """, (user_id, sku, platform, listing_id, price, quantity, title, listing_url, master_price, master_quantity, 1 if has_conflict else 0))
        listing_id_result = cur.lastrowid
    conn.commit()
    conn.close()
    log_sync_action(user_id, listing_id_result, sku, platform, "created", "success", None, {"price": price, "quantity": quantity})
    return listing_id_result

def update_listing_sync(listing_id, user_id, price=None, quantity=None, sync_status=None, last_synced=None, master_price=None, master_quantity=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params = []
    if price is not None:
        updates.append(f"price = {ph}")
        params.append(price)
    if quantity is not None:
        updates.append(f"quantity = {ph}")
        params.append(quantity)
    if sync_status is not None:
        updates.append(f"sync_status = {ph}")
        params.append(sync_status)
    if last_synced is not None:
        updates.append(f"last_synced = {ph}")
        params.append(last_synced)
    if master_price is not None:
        updates.append(f"master_price = {ph}")
        params.append(master_price)
    if master_quantity is not None:
        updates.append(f"master_quantity = {ph}")
        params.append(master_quantity)
    
    cur.execute(f"SELECT price, quantity, master_price, master_quantity FROM soleops_listings_sync WHERE id = {ph} AND user_id = {ph}", (listing_id, user_id))
    row = cur.fetchone()
    if row:
        current_price = price if price is not None else row[0]
        current_qty = quantity if quantity is not None else row[1]
        current_master_price = master_price if master_price is not None else row[2]
        current_master_qty = master_quantity if master_quantity is not None else row[3]
        has_conflict = abs(float(current_price or 0) - float(current_master_price or 0)) > 0.01 or int(current_qty or 0) != int(current_master_qty or 0)
        if USE_POSTGRES:
            updates.append(f"has_conflict = {ph}")
        else:
            updates.append(f"has_conflict = {ph}")
        params.append(has_conflict if USE_POSTGRES else (1 if has_conflict else 0))
    
    params.extend([listing_id, user_id])
    cur.execute(f"UPDATE soleops_listings_sync SET {', '.join(updates)} WHERE id = {ph} AND user_id = {ph}", params)
    conn.commit()
    conn.close()

def delete_listing_sync(listing_id, user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT sku, platform FROM soleops_listings_sync WHERE id = {ph} AND user_id = {ph}", (listing_id, user_id))
    row = cur.fetchone()
    if row:
        log_sync_action(user_id, listing_id, row[0], row[1], "deleted", "success", None, None)
    cur.execute(f"DELETE FROM soleops_listings_sync WHERE id = {ph} AND user_id = {ph}", (listing_id, user_id))
    conn.commit()
    conn.close()

def bulk_sync_listings(user_id, listing_ids, action="sync"):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    results = {"success": 0, "errors": 0, "messages": []}
    for lid in listing_ids:
        try:
            if action == "sync":
                cur.execute(f"SELECT sku, platform, master_price, master_quantity FROM soleops_listings_sync WHERE id = {ph} AND user_id = {ph}", (lid, user_id))
                row = cur.fetchone()
                if row:
                    sku, platform, master_price, master_qty = row
                    if USE_POSTGRES:
                        cur.execute(f"""
                            UPDATE soleops_listings_sync 
                            SET price = {ph}, quantity = {ph}, sync_status = 'synced', 
                                last_synced = CURRENT_TIMESTAMP, has_conflict = FALSE, updated_at = CURRENT_TIMESTAMP
                            WHERE id = {ph} AND user_id = {ph}
                        """, (master_price, master_qty, lid, user_id))
                    else:
                        cur.execute(f"""
                            UPDATE soleops_listings_sync 
                            SET price = {ph}, quantity = {ph}, sync_status = 'synced', 
                                last_synced = CURRENT_TIMESTAMP, has_conflict = 0, updated_at = CURRENT_TIMESTAMP
                            WHERE id = {ph} AND user_id = {ph}
                        """, (master_price, master_qty, lid, user_id))
                    log_sync_action(user_id, lid, sku, platform, "bulk_sync", "success", None, {"synced_price": master_price, "synced_qty": master_qty})
                    results["success"] += 1
            elif action == "mark_pending":
                cur.execute(f"UPDATE soleops_listings_sync SET sync_status = 'pending', updated_at = CURRENT_TIMESTAMP WHERE id = {ph} AND user_id = {ph}", (lid, user_id))
                results["success"] += 1
        except Exception as e:
            results["errors"] += 1
            results["messages"].append(f"Error on listing {lid}: {str(e)}")
    conn.commit()
    conn.close()
    return results

def log_sync_action(user_id, listing_sync_id, sku, platform, action, status, error_message=None, details=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        cur.execute(f"""
            INSERT INTO soleops_sync_logs (user_id, listing_sync_id, sku, platform, action, status, error_message, details)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id, listing_sync_id, sku, platform, action, status, error_message, json.dumps(details) if details else None))
    else:
        cur.execute(f"""
            INSERT INTO soleops_sync_logs (user_id, listing_sync_id, sku, platform, action, status, error_message, details)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id, listing_sync_id, sku, platform, action, status, error_message, json.dumps(details) if details else None))
    conn.commit()
    conn.close()

def get_sync_logs(user_id, limit=50):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT * FROM soleops_sync_logs 
        WHERE user_id = {ph} 
        ORDER BY created_at DESC 
        LIMIT {ph}
    """, (user_id, limit))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows

def get_listings_with_conflicts(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        cur.execute(f"SELECT * FROM soleops_listings_sync WHERE user_id = {ph} AND has_conflict = TRUE ORDER BY updated_at DESC", (user_id,))
    else:
        cur.execute(f"SELECT * FROM soleops_listings_sync WHERE user_id = {ph} AND has_conflict = 1 ORDER BY updated_at DESC", (user_id,))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows

def get_claude_optimization_suggestions(listings):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        listings_summary = []
        for l in listings[:10]:
            listings_summary.append({
                "sku": l.get("sku"),
                "platform": l.get("platform"),
                "title": l.get("title"),
                "price": l.get("price"),
                "sync_status": l.get("sync_status")
            })
        prompt = f"""You are a sneaker resale expert. Analyze these listings and provide optimization suggestions for each platform (eBay, Mercari, Depop).

Listings:
{json.dumps(listings_summary, indent=2)}

For each listing, provide:
1. Title optimization suggestions (platform-specific best practices)
2. Pricing strategy recommendation
3. Listing improvement tips
4. Cross-platform sync recommendations

Format your response as actionable bullet points for each listing."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error getting AI suggestions: {str(e)}"

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
st.title("🔄 SoleOps Automated Listings Sync")
st.markdown("Auto-sync inventory listings across eBay, Mercari, and Depop with bulk update capabilities.")

user_id = get_user_id()
connections = get_platform_connections(user_id)

# Platform connection status
st.markdown("### 🔌 Platform Connections")
col1, col2, col3 = st.columns(3)

with col1:
    ebay_status = "🟢 Connected" if connections.get("ebay_connected") else "🔴 Not Connected"
    ebay_last = connections.get("ebay_last_sync")
    st.metric("eBay", ebay_status)
    if ebay_last:
        st.caption(f"Last sync: {ebay_last}")
    if st.button("Toggle eBay", key="toggle_ebay"):
        update_platform_connection(user_id, "ebay", not connections.get("ebay_connected"))
        st.rerun()

with col2:
    mercari_status = "🟢 Connected" if connections.get("mercari_connected") else "🔴 Not Connected"
    mercari_last = connections.get("mercari_last_sync")
    st.metric("Mercari", mercari_status)
    if mercari_last:
        st.caption(f"Last sync: {mercari_last}")
    if st.button("Toggle Mercari", key="toggle_mercari"):
        update_platform_connection(user_id, "mercari", not connections.get("mercari_connected"))
        st.rerun()

with col3:
    depop_status = "🟢 Connected" if connections.get("depop_connected") else "🔴 Not Connected"
    depop_last = connections.get("depop_last_sync")
    st.metric("Depop", depop_status)
    if depop_last:
        st.caption(f"Last sync: {depop_last}")
    if st.button("Toggle Depop", key="toggle_depop"):
        update_platform_connection(user_id, "depop", not connections.get("depop_connected"))
        st.rerun()

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Sync Dashboard", "⚡ Bulk Actions", "📜 Sync History", "🤖 AI Optimization", "⚠️ Conflicts"])

with tab1:
    st.markdown("### Sync Dashboard")
    
    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        filter_status = st.selectbox("Filter by Status", ["All", "synced", "pending", "error"], key="filter_status")
    with fcol2:
        filter_platform = st.selectbox("Filter by Platform", ["All", "eBay", "Mercari", "Depop"], key="filter_platform")
    with fcol3:
        filter_sku = st.text_input("Search SKU", key="filter_sku")
    
    # Get listings
    listings = get_sync_status(user_id)
    
    # Apply filters
    if filter_status != "All":
        listings = [l for l in listings if l.get("sync_status") == filter_status]
    if filter_platform != "All":
        listings = [l for l in listings if l.get("platform") == filter_platform]
    if filter_sku:
        listings = [l for l in listings if filter_sku.lower() in (l.get("sku") or "").lower()]
    
    # Summary metrics
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    all_listings = get_sync_status(user_id)
    with mcol1:
        st.metric("Total Listings", len(all_listings))
    with mcol2:
        synced = len([l for l in all_listings if l.get("sync_status") == "synced"])
        st.metric("Synced", synced)
    with mcol3:
        pending = len([l for l in all_listings if l.get("sync_status") == "pending"])
        st.metric("Pending", pending)
    with mcol4:
        errors = len([l for l in all_listings if l.get("sync_status") == "error"])
        st.metric("Errors", errors)
    
    st.markdown("---")
    
    # Add new listing
    with st.expander("➕ Add New Listing Sync", expanded=False):
        with st.form("add_listing_form"):
            acol1, acol2 = st.columns(2)
            with acol1:
                new_sku = st.text_input("SKU *")
                new_platform = st.selectbox("Platform *", ["eBay", "Mercari", "Depop"])
                new_listing_id = st.text_input("Platform Listing ID")
                new_title = st.text_input("Listing Title")
            with acol2:
                new_price = st.number_input("Platform Price", min_value=0.0, step=0.01)
                new_quantity = st.number_input("Quantity", min_value=0, value=1)
                new_master_price = st.number_input("Master Price", min_value=0.0, step=0.01)
                new_master_qty = st.number_input("Master Quantity", min_value=0, value=1)
            new_url = st.text_input("Listing URL")
            
            if st.form_submit_button("Add Listing"):
                if new_sku and new_platform:
                    add_listing_sync(user_id, new_sku, new_platform, new_listing_id, new_price, new_quantity, new_title, new_url, new_master_price, new_master_qty)
                    st.success("Listing added!")
                    st.rerun()
                else:
                    st.error("SKU and Platform are required")
    
    # Display listings
    if listings:
        for listing in listings:
            status_icon = {"synced": "🟢", "pending": "🟡", "error": "🔴"}.get(listing.get("sync_status"), "⚪")
            conflict_badge = "⚠️ CONFLICT" if listing.get("has_conflict") else ""
            
            with st.expander(f"{status_icon} {listing.get('sku')} - {listing.get('platform')} {conflict_badge}"):
                lcol1, lcol2, lcol3 = st.columns(3)
                with lcol1:
                    st.write(f"**Title:** {listing.get('title') or 'N/A'}")
                    st.write(f"**Listing ID:** {listing.get('listing_id') or 'N/A'}")
                    if listing.get("listing_url"):
                        st.markdown(f"[View Listing]({listing.get('listing_url')})")
                with lcol2:
                    st.write(f"**Platform Price:** ${listing.get('price') or 0:.2f}")
                    st.write(f"**Platform Qty:** {listing.get('quantity') or 0}")
                    st.write(f"**Last Synced:** {listing.get('last_synced') or 'Never'}")
                with lcol3:
                    st.write(f"**Master Price:** ${listing.get('master_price') or 0:.2f}")
                    st.write(f"**Master Qty:** {listing.get('master_quantity') or 0}")
                    st.write(f"**Status:** {listing.get('sync_status')}")
                
                # Actions
                bcol1, bcol2, bcol3 = st.columns(3)
                with bcol1:
                    if st.button("🔄 Sync Now", key=f"sync_{listing['id']}"):
                        update_listing_sync(listing['id'], user_id, 
                                          price=listing.get('master_price'),
                                          quantity=listing.get('master_quantity'),
                                          sync_status='synced',
                                          last_synced=datetime.now())
                        log_sync_action(user_id, listing['id'], listing.get('sku'), listing.get('platform'), "manual_sync", "success")
                        st.success("Synced!")
                        st.rerun()
                with bcol2:
                    if st.button("✏️ Edit", key=f"edit_{listing['id']}"):
                        st.session_state[f"editing_{listing['id']}"] = True
                with bcol3:
                    if st.button("🗑️ Delete", key=f"del_{listing['id']}"):
                        delete_listing_sync(listing['id'], user_id)
                        st.success("Deleted!")
                        st.rerun()
                
                # Edit form
                if st.session_state.get(f"editing_{listing['id']}"):
                    with st.form(f"edit_form_{listing['id']}"):
                        ecol1, ecol2 = st.columns(2)
                        with ecol1:
                            edit_price = st.number_input("Platform Price", value=float(listing.get('price') or 0), key=f"ep_{listing['id']}")
                            edit_qty = st.number_input("Quantity", value=int(listing.get('quantity') or 0), key=f"eq_{listing['id']}")
                        with ecol2:
                            edit_master_price = st.number_input("Master Price", value=float(listing.get('master_price') or 0), key=f"emp_{listing['id']}")
                            edit_master_qty = st.number_input("Master Qty", value=int(listing.get('master_quantity') or 0), key=f"emq_{listing['id']}")
                        edit_status = st.selectbox("Status", ["pending", "synced", "error"], 
                                                   index=["pending", "synced", "error"].index(listing.get('sync_status') or 'pending'),
                                                   key=f"es_{listing['id']}")
                        
                        if st.form_submit_button("Save Changes"):
                            update_listing_sync(listing['id'], user_id, 
                                              price=edit_price, quantity=edit_qty,
                                              sync_status=edit_status,
                                              master_price=edit_master_price,
                                              master_quantity=edit_master_qty)
                            log_sync_action(user_id, listing['id'], listing.get('sku'), listing.get('platform'), "updated", "success")
                            st.session_state[f"editing_{listing['id']}"] = False
                            st.success("Updated!")
                            st.rerun()
    else:
        st.info("No listings found. Add your first listing above!")

with tab2:
    st.markdown("### ⚡ Bulk Actions")
    
    all_listings = get_sync_status(user_id)
    
    if all_listings:
        st.write(f"**{len(all_listings)} listings available for bulk actions**")
        
        # Selection
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            select_by_status = st.multiselect("Select by Status", ["synced", "pending", "error"], key="bulk_status")
        with bcol2:
            select_by_platform = st.multiselect("Select by Platform", ["eBay", "Mercari", "Depop"], key="bulk_platform")
        
        # Filter selected listings
        selected_listings = all_listings
        if select_by_status:
            selected_listings = [l for l in selected_listings if l.get("sync_status") in select_by_status]
        if select_by_platform:
            selected_listings