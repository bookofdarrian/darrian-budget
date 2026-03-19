import streamlit as st
import json
import datetime
from datetime import timedelta
import time
import re
import urllib.parse

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Competitor Price Tracker", page_icon="🍑", layout="wide")

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_competitor_prices (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(255) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                competitor_seller VARCHAR(255),
                competitor_price DECIMAL(10,2) NOT NULL,
                our_price DECIMAL(10,2) NOT NULL,
                price_diff DECIMAL(10,2),
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_competitor_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(255) NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                competitor_price DECIMAL(10,2),
                our_price DECIMAL(10,2),
                recommendation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_competitor_watchlist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(255) NOT NULL,
                product_name VARCHAR(500),
                our_price DECIMAL(10,2),
                min_price DECIMAL(10,2),
                target_margin DECIMAL(5,2) DEFAULT 20.00,
                auto_reprice BOOLEAN DEFAULT FALSE,
                last_scanned TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_competitor_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                competitor_seller TEXT,
                competitor_price REAL NOT NULL,
                our_price REAL NOT NULL,
                price_diff REAL,
                detected_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_competitor_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                competitor_price REAL,
                our_price REAL,
                recommendation TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_competitor_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                product_name TEXT,
                our_price REAL,
                min_price REAL,
                target_margin REAL DEFAULT 20.00,
                auto_reprice INTEGER DEFAULT 0,
                last_scanned TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.sidebar.markdown("---")
st.sidebar.markdown("### 👟 SoleOps")
st.sidebar.page_link("pages/65_sneaker_inventory_analyzer.py", label="📦 Inventory Analyzer", icon="📦")
st.sidebar.page_link("pages/68_soleops_price_monitor.py", label="💰 Price Monitor", icon="💰")
st.sidebar.page_link("pages/69_soleops_pnl_dashboard.py", label="📈 P&L Dashboard", icon="📈")
st.sidebar.page_link("pages/71_soleops_arb_scanner.py", label="🔍 Arb Scanner", icon="🔍")

user_id = st.session_state.get("user_id", 1)

def get_watchlist():
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, sku, product_name, our_price, min_price, target_margin, auto_reprice, last_scanned
        FROM soleops_competitor_watchlist
        WHERE user_id = {ph}
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def add_to_watchlist(sku, product_name, our_price, min_price, target_margin):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_competitor_watchlist (user_id, sku, product_name, our_price, min_price, target_margin)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, sku, product_name, our_price, min_price, target_margin))
    conn.commit()
    conn.close()

def remove_from_watchlist(item_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_competitor_watchlist WHERE id = {ph} AND user_id = {ph}", (item_id, user_id))
    conn.commit()
    conn.close()

def update_watchlist_price(item_id, our_price, min_price):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        UPDATE soleops_competitor_watchlist 
        SET our_price = {ph}, min_price = {ph}
        WHERE id = {ph} AND user_id = {ph}
    """, (our_price, min_price, item_id, user_id))
    conn.commit()
    conn.close()

def save_competitor_price(sku, platform, competitor_seller, competitor_price, our_price):
    price_diff = our_price - competitor_price
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_competitor_prices 
        (user_id, sku, platform, competitor_seller, competitor_price, our_price, price_diff)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, sku, platform, competitor_seller, competitor_price, our_price, price_diff))
    conn.commit()
    conn.close()
    return price_diff

def create_alert(sku, alert_type, competitor_price, our_price, recommendation):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_competitor_alerts 
        (user_id, sku, alert_type, competitor_price, our_price, recommendation)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, sku, alert_type, competitor_price, our_price, recommendation))
    conn.commit()
    conn.close()

def get_alerts(acknowledged=False):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    ack_val = acknowledged if USE_POSTGRES else (1 if acknowledged else 0)
    cur.execute(f"""
        SELECT id, sku, alert_type, competitor_price, our_price, recommendation, created_at
        FROM soleops_competitor_alerts
        WHERE user_id = {ph} AND acknowledged = {ph}
        ORDER BY created_at DESC
        LIMIT 50
    """, (user_id, ack_val))
    rows = cur.fetchall()
    conn.close()
    return rows

def acknowledge_alert(alert_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    ack_val = True if USE_POSTGRES else 1
    cur.execute(f"""
        UPDATE soleops_competitor_alerts 
        SET acknowledged = {ph}
        WHERE id = {ph} AND user_id = {ph}
    """, (ack_val, alert_id, user_id))
    conn.commit()
    conn.close()

def get_competitor_price_history(sku, days=30):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT platform, competitor_seller, competitor_price, our_price, price_diff, detected_at
            FROM soleops_competitor_prices
            WHERE user_id = {ph} AND sku = {ph} AND detected_at >= NOW() - INTERVAL '{days} days'
            ORDER BY detected_at DESC
        """, (user_id, sku))
    else:
        cutoff = (datetime.datetime.now() - timedelta(days=days)).isoformat()
        cur.execute(f"""
            SELECT platform, competitor_seller, competitor_price, our_price, price_diff, detected_at
            FROM soleops_competitor_prices
            WHERE user_id = {ph} AND sku = {ph} AND detected_at >= {ph}
            ORDER BY detected_at DESC
        """, (user_id, sku, cutoff))
    rows = cur.fetchall()
    conn.close()
    return rows

def simulate_ebay_search(sku):
    """Simulated eBay search - replace with real API in production"""
    import random
    base_price = random.uniform(150, 350)
    results = []
    sellers = ["sneaker_king_2026", "kicksdealer_pro", "shoemaster99", "urban_kicks_atl", "sole_connect_nyc"]
    for i in range(random.randint(3, 8)):
        price_variance = random.uniform(-0.15, 0.15)
        results.append({
            "seller": random.choice(sellers),
            "price": round(base_price * (1 + price_variance), 2),
            "condition": random.choice(["New", "New with tags", "New without box"]),
            "shipping": random.choice([0, 9.99, 12.99, 14.99]),
            "listing_type": random.choice(["Buy It Now", "Auction"]),
            "watchers": random.randint(0, 25)
        })
    return results

def simulate_mercari_search(sku):
    """Simulated Mercari search - replace with real scraper in production"""
    import random
    base_price = random.uniform(140, 320)
    results = []
    sellers = ["Sneakerhead_Mike", "ATL_Reseller", "Kicks4Days", "SoleCollector_GA", "HeatCheck_ATL"]
    for i in range(random.randint(2, 6)):
        price_variance = random.uniform(-0.12, 0.18)
        results.append({
            "seller": random.choice(sellers),
            "price": round(base_price * (1 + price_variance), 2),
            "condition": random.choice(["New", "Like new", "Good"]),
            "shipping": random.choice([0, 7.99, 10.99]),
            "likes": random.randint(0, 50)
        })
    return results

def calculate_price_position(our_price, competitor_prices):
    if not competitor_prices:
        return {"position": "No data", "rank": 0, "total": 0, "avg_diff": 0}
    
    prices = sorted([p["price"] + p.get("shipping", 0) for p in competitor_prices])
    total_price = our_price
    rank = sum(1 for p in prices if p < total_price) + 1
    avg_competitor = sum(prices) / len(prices)
    avg_diff = our_price - avg_competitor
    
    return {
        "position": f"{rank} of {len(prices) + 1}",
        "rank": rank,
        "total": len(prices) + 1,
        "avg_diff": round(avg_diff, 2),
        "lowest_competitor": min(prices),
        "highest_competitor": max(prices),
        "avg_competitor": round(avg_competitor, 2)
    }

def get_ai_repricing_recommendation(sku, our_price, competitor_data, target_margin=20):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return generate_rule_based_recommendation(our_price, competitor_data, target_margin)
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are a sneaker resale pricing expert. Analyze this competitive pricing data and provide a specific repricing recommendation.

SKU: {sku}
Our Current Price: ${our_price:.2f}
Target Profit Margin: {target_margin}%

Competitor Listings:
{json.dumps(competitor_data, indent=2)}

Provide a JSON response with:
1. "recommended_price": The optimal price to set
2. "strategy": One of ["HOLD", "LOWER", "RAISE", "AGGRESSIVE_CUT"]
3. "reasoning": 2-3 sentences explaining the recommendation
4. "urgency": One of ["LOW", "MEDIUM", "HIGH"]
5. "expected_impact": Brief note on expected outcome

Consider:
- Price position relative to competitors
- Platform fees (eBay ~13%, Mercari ~10%)
- Shipping costs typically $12-15
- Market velocity (watchers/likes indicate demand)
- Undercut strategies for fast sales vs. margin preservation

Return ONLY valid JSON, no additional text."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = json.loads(response.content[0].text)
        return result
    except Exception as e:
        return generate_rule_based_recommendation(our_price, competitor_data, target_margin)

def generate_rule_based_recommendation(our_price, competitor_data, target_margin):
    if not competitor_data:
        return {
            "recommended_price": our_price,
            "strategy": "HOLD",
            "reasoning": "No competitor data available. Maintain current pricing until market data is collected.",
            "urgency": "LOW",
            "expected_impact": "Monitor for new listings"
        }
    
    all_prices = []
    for platform, listings in competitor_data.items():
        for listing in listings:
            total = listing["price"] + listing.get("shipping", 0)
            all_prices.append(total)
    
    if not all_prices:
        return {
            "recommended_price": our_price,
            "strategy": "HOLD",
            "reasoning": "No competitor data available.",
            "urgency": "LOW",
            "expected_impact": "Monitor for new listings"
        }
    
    min_competitor = min(all_prices)
    avg_competitor = sum(all_prices) / len(all_prices)
    
    if our_price > avg_competitor * 1.15:
        new_price = round(avg_competitor * 1.05, 2)
        return {
            "recommended_price": max(new_price, our_price * 0.85),
            "strategy": "LOWER",
            "reasoning": f"Your price is 15%+ above market average (${avg_competitor:.2f}). Recommend reducing to stay competitive.",
            "urgency": "HIGH",
            "expected_impact": "Faster sale, maintain visibility"
        }
    elif our_price > min_competitor * 1.10:
        return {
            "recommended_price": round(min_competitor * 1.02, 2),
            "strategy": "AGGRESSIVE_CUT",
            "reasoning": f"Lowest competitor at ${min_competitor:.2f}. Consider aggressive pricing to win the sale.",
            "urgency": "MEDIUM",
            "expected_impact": "Win buy box, faster turnover"
        }
    elif our_price < avg_competitor * 0.90:
        return {
            "recommended_price": round(avg_competitor * 0.95, 2),
            "strategy": "RAISE",
            "reasoning": f"Your price is below market. You can increase price and still be competitive.",
            "urgency": "LOW",
            "expected_impact": "Higher margins without sacrificing sales"
        }
    else:
        return {
            "recommended_price": our_price,
            "strategy": "HOLD",
            "reasoning": "Your price is well-positioned in the current market.",
            "urgency": "LOW",
            "expected_impact": "Maintain current position"
        }

def scan_competitors_for_sku(sku, our_price):
    """Run competitor scan for a single SKU"""
    ebay_results = simulate_ebay_search(sku)
    mercari_results = simulate_mercari_search(sku)
    
    for listing in ebay_results:
        price_diff = save_competitor_price(
            sku, "eBay", listing["seller"], listing["price"], our_price
        )
        if price_diff > 0 and listing["price"] < our_price * 0.9:
            recommendation = get_ai_repricing_recommendation(
                sku, our_price, {"eBay": [listing]}
            )
            create_alert(
                sku, "UNDERCUT",
                listing["price"], our_price,
                recommendation.get("reasoning", "Competitor undercutting your price")
            )
    
    for listing in mercari_results:
        price_diff = save_competitor_price(
            sku, "Mercari", listing["seller"], listing["price"], our_price
        )
        if price_diff > 0 and listing["price"] < our_price * 0.9:
            recommendation = get_ai_repricing_recommendation(
                sku, our_price, {"Mercari": [listing]}
            )
            create_alert(
                sku, "UNDERCUT",
                listing["price"], our_price,
                recommendation.get("reasoning", "Competitor undercutting your price")
            )
    
    return {
        "eBay": ebay_results,
        "Mercari": mercari_results
    }

st.title("🎯 SoleOps Competitor Price Tracker")
st.markdown("Monitor competitor pricing across eBay and Mercari. Get alerts when you're undercut and AI-powered repricing recommendations.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "👀 Watchlist", "🔔 Alerts", "📈 Price History", "🔍 Manual Scan"
])

with tab1:
    st.subheader("Competitor Monitoring Dashboard")
    
    watchlist = get_watchlist()
    pending_alerts = get_alerts(acknowledged=False)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 SKUs Tracked", len(watchlist))
    with col2:
        st.metric("🔔 Pending Alerts", len(pending_alerts))
    with col3:
        conn = get_conn()
        cur = conn.cursor()
        ph = "%s" if USE_POSTGRES else "?"
        if USE_POSTGRES:
            cur.execute(f"""
                SELECT COUNT(DISTINCT sku) FROM soleops_competitor_prices
                WHERE user_id = {ph} AND detected_at >= NOW() - INTERVAL '24 hours'
            """, (user_id,))
        else:
            cutoff = (datetime.datetime.now() - timedelta(hours=24)).isoformat()
            cur.execute(f"""
                SELECT COUNT(DISTINCT sku) FROM soleops_competitor_prices
                WHERE user_id = {ph} AND detected_at >= {ph}
            """, (user_id, cutoff))
        scans_24h = cur.fetchone()[0]
        conn.close()
        st.metric("🔄 Scans (24h)", scans_24h)
    with col4:
        undercut_count = len([a for a in pending_alerts if "UNDERCUT" in str(a)])
        st.metric("⚠️ Undercuts", undercut_count, delta=f"-{undercut_count}" if undercut_count > 0 else None, delta_color="inverse")
    
    st.markdown("---")
    
    if watchlist:
        st.subheader("Price Position Overview")
        
        for item in watchlist[:5]:
            item_id, sku, product_name, our_price, min_price, target_margin, auto_reprice, last_scanned = item
            
            with st.expander(f"**{product_name or sku}** — ${our_price:.2f}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    history = get_competitor_price_history(sku, days=7)
                    if history:
                        ebay_prices = [h[2] for h in history if h[0] == "eBay"]
                        mercari_prices = [h[2] for h in history if h[0] == "Mercari"]
                        
                        if ebay_prices or mercari_prices:
                            import pandas as pd
                            chart_data = []
                            if ebay_prices:
                                chart_data.append({"Platform": "eBay", "Avg Price": sum(ebay_prices)/len(ebay_prices)})
                            if mercari_prices:
                                chart_data.append({"Platform": "Mercari", "Avg Price": sum(mercari_prices)/len(mercari_prices)})
                            chart_data.append({"Platform": "Your Price", "Avg Price": our_price})
                            
                            df = pd.DataFrame(chart_data)
                            st.bar_chart(df.set_index("Platform"))
                    else:
                        st.info("No competitor data yet. Run a scan to collect pricing.")
                
                with col2:
                    st.markdown(f"**SKU:** `{sku}`")
                    st.markdown(f"**Min Price:** ${min_price:.2f}" if min_price else "**Min Price:** Not set")
                    st.markdown(f"**Target Margin:** {target_margin}%")
                    st.markdown(f"**Last Scan:** {last_scanned or 'Never'}")
                    
                    if st.button("🔄 Scan Now", key=f"scan_{item_id}"):
                        with st.spinner("Scanning competitors..."):
                            results = scan_competitors_for_sku(sku, our_price)
                            st.success(f"Found {len(results.get('eBay', []))} eBay + {len(results.get('Mercari', []))} Mercari listings")
                            st.rerun()
    else:
        st.info("👋 No SKUs in your watchlist yet. Add items in the Watchlist tab to start monitoring competitors.")

with tab2:
    st.subheader("Competitor Watchlist")
    st.markdown("Add SKUs to monitor competitor pricing automatically.")
    
    with st.form("add_watchlist"):
        col1, col2 = st.columns(2)
        with col1:
            new_sku = st.text_input("SKU / Style Code", placeholder="e.g., DQ8423-100")
            new_product = st.text_input("Product Name", placeholder="e.g., Air Jordan 1 Low Golf")
        with col2:
            new_price = st.number_input("Your Current Price ($)", min_value=0.0, value=200.0, step=5.0)
            new_min = st.number_input("Minimum Price ($)", min_value=0.0, value=150.0, step=5.0, help="Floor price - won't recommend below this")
        
        new_margin = st.slider("Target Profit Margin (%)", min_value=5, max_value=50, value=20)
        
        if st.form_submit_button("➕ Add to Watchlist", use_container_width=True):
            if new_sku:
                add_to_watchlist(new_sku, new_product, new_price, new_min, new_margin)
                st.success(f"Added {new_sku} to watchlist!")
                st.rerun()
            else:
                st.error("Please enter a SKU")
    
    st.markdown("---")
    
    watchlist = get_watchlist()
    if watchlist:
        st.markdown(f"**{len(watchlist)} items in watchlist**")
        
        for item in watchlist:
            item_id, sku, product_name, our_price, min_price, target_margin, auto_reprice, last_scanned = item
            
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.markdown(f"**{product_name or 'Unnamed'}**")
                    st.caption(f"SKU: {sku}")
                with col2:
                    st.metric("Your Price", f"${our_price:.2f}")
                with col3:
                    st.metric("Min Price", f"${min_price:.2f}" if min_price else "Not set")
                with col4:
                    if st.button("🗑️", key=f"del_{item_id}", help="Remove from watchlist"):
                        remove_from_watchlist(item_id)
                        st.rerun()
                st.markdown("---")
    else:
        st.info("Your watchlist is empty. Add SKUs above to start tracking competitor prices.")

with tab3:
    st.subheader("🔔 Price Alerts")
    
    alert_filter = st.radio("Show alerts:", ["Pending", "Acknowledged", "All"], horizontal=True)
    
    if alert_filter == "All":
        pending = get_alerts(acknowledged=False)
        acked = get_alerts(acknowledged=True)
        alerts = pending + acked
    else:
        alerts = get_alerts(acknowledged=(alert_filter == "Acknowledged"))
    
    if alerts:
        for alert in alerts:
            alert_id, sku, alert_type, comp_price, our_price, recommendation, created_at = alert
            
            if alert_type == "UNDERCUT":
                alert_color = "🔴"
                alert_label = "Undercut Alert"
            elif alert_type == "PRICE_DROP":
                alert_color = "🟡"
                alert_label = "Price Drop"
            else:
                alert_color = "🔵"
                alert_label = alert_type
            
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.markdown(f"### {alert_color}")
                    st.caption(alert_label)
                with col2:
                    st.markdown(f"**{sku}**")
                    if comp_price and our_price:
                        diff = our_price - comp_price
                        pct = (diff / our_price) * 100 if our_price > 0 else 0
                        st.markdown(f"Competitor: **${comp_price:.2f}** | Your price: **${our_price:.2f}** | Diff: **${diff:.2f}** ({pct:.1f}%)")
                    if recommendation:
                        st.info(recommendation)
                    st.caption(f"Created: {created_at}")
                with col3:
                    if alert_filter != "Acknowledged":
                        if st.button("✓ Acknowledge", key=f"ack_{alert_id}"):
                            acknowledge_alert(alert_id)
                            st.rerun()
                st.markdown("---")
    else:
        if alert_filter == "Pending":
            st.success("🎉 No pending alerts! Your prices are competitive.")
        else:
            st.info("No alerts to display.")

with tab4:
    st.subheader("📈 Competitor Price History")
    
    watchlist = get_watchlist()
    if watchlist:
        sku_options = {f"{item[2] or item[1]} ({item[1]})": item[1] for item in watchlist}
        selected_display = st.selectbox("Select SKU", list(sku_options.keys()))
        selected_sku = sku_options[selected_display]
        
        days_range = st.slider("Days of history", min_value=7, max_value=90, value=30)
        
        history = get_competitor_price_history(selected_sku, days=days_range)
        
        if history:
            import pandas as pd
            
            df_data = []
            for row in history:
                platform, seller, comp_price, our_price, price_diff, detected_at = row
                df_data.append({
                    "Date": detected_at,
                    "Platform": platform,
                    "Seller": seller,
                    "Competitor Price": comp_price,
                    "Your Price": our_price,
                    "Difference": price_diff
                })
            
            df = pd.DataFrame(df_data)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Price Trend**")
                if len(df) > 1:
                    chart_df = df.groupby("Platform")["Competitor Price"].mean().reset_