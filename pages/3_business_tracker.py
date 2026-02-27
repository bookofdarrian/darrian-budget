import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, execute, get_setting, set_setting
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Business Income Tracker — Peach State Savings", page_icon="💼", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("Business Income Tracker")
inject_css()


# ── eBay API helpers ──────────────────────────────────────────────────────────
def _ebay_get_token(client_id: str, client_secret: str) -> str | None:
    """Get an eBay OAuth application token (Client Credentials flow)."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data="grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope",
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None


def ebay_search_sold(query: str, client_id: str, client_secret: str, limit: int = 10) -> list[dict]:
    """
    Search eBay for recently sold sneaker listings using the Browse API.
    Returns list of {title, price, currency, condition, url}.
    """
    token = _ebay_get_token(client_id, client_secret)
    if not token:
        return []

    resp = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "q": query,
            "category_ids": "15709",   # Sneakers category
            "filter": "buyingOptions:{FIXED_PRICE},conditions:{USED|NEW}",
            "sort": "newlyListed",
            "limit": limit,
            "fieldgroups": "MATCHING_ITEMS",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        return []

    items = resp.json().get("itemSummaries", [])
    results = []
    for item in items:
        price_info = item.get("price", {})
        results.append({
            "title":     item.get("title", ""),
            "price":     float(price_info.get("value", 0)),
            "currency":  price_info.get("currency", "USD"),
            "condition": item.get("condition", ""),
            "url":       item.get("itemWebUrl", ""),
            "source":    "eBay",
        })
    return results


# ── KicksDB Sneaker Price helpers ─────────────────────────────────────────────
def kicksdb_search_sneakers(query: str, api_key: str, source: str = "stockx", limit: int = 10) -> list[dict]:
    """
    Search for sneaker prices using KicksDB API (kicks.dev).
    Free tier: 1,000 requests/month — no credit card required.
    source: 'stockx' or 'goat'
    Returns list of {title, sku, min_price, max_price, avg_price, url}.
    """
    resp = requests.get(
        f"https://api.kicks.dev/v3/{source}/products",
        headers={"Authorization": api_key},
        params={"query": query, "limit": limit},
        timeout=15,
    )
    if resp.status_code != 200:
        return []

    items = resp.json().get("data", [])
    results = []
    for item in items:
        results.append({
            "title":     item.get("title", ""),
            "sku":       item.get("sku", ""),
            "brand":     item.get("brand", ""),
            "min_price": float(item.get("min_price") or 0),
            "max_price": float(item.get("max_price") or 0),
            "avg_price": float(item.get("avg_price") or 0),
            "source":    source.upper(),
        })
    return results

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",              icon="📊")
st.sidebar.page_link("pages/18_real_estate_bot.py", label="🏠 Real Estate Bot", icon="🏠")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",              icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",                icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py",   label="Business Tracker 🔒",   icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",        icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",           icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",        icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights 🔒",        icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",       icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth 🔒",          icon="💎")
st.sidebar.page_link("pages/0_pricing.py",        label="⭐ Upgrade to Pro",     icon="⭐")
render_sidebar_user_widget()

st.title("💼 Business Income Tracker — Resale & Side Hustle")
st.caption("Track your sneaker resale, freelance, or any side business income. Includes eBay & StockX market lookups.")

conn = get_conn()
inv_df = read_sql("SELECT * FROM sole_archive ORDER BY date DESC", conn)
conn.close()

sold = inv_df[inv_df['status'] == 'sold']
inventory = inv_df[inv_df['status'] == 'inventory']

total_revenue = sold['sell_price'].sum()
total_fees = sold['fees'].sum() + sold['shipping'].sum()
total_profit = total_revenue - sold['buy_price'].sum() - total_fees
inventory_value = inventory['buy_price'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Profit (Sold)", f"${total_profit:,.2f}")
col2.metric("📦 Inventory Items", len(inventory))
col3.metric("🏷️ Inventory Cost Basis", f"${inventory_value:,.2f}")
col4.metric("✅ Units Sold", len(sold))

st.markdown("---")

with st.expander("➕ Add New Pair to Inventory"):
    col1, col2, col3 = st.columns(3)
    with col1:
        item = st.text_input("Sneaker (e.g. Jordan 1 Chicago)")
        size = st.text_input("Size")
        buy_price = st.number_input("Buy Price ($)", min_value=0.0, step=5.0)
    with col2:
        sell_price = st.number_input("Sell Price ($) — leave 0 if not sold", min_value=0.0, step=5.0)
        platform = st.selectbox("Platform", ["—", "StockX", "GOAT", "eBay", "Facebook", "Other"])
        fees = st.number_input("Platform Fees ($)", min_value=0.0, step=1.0)
    with col3:
        shipping = st.number_input("Shipping ($)", min_value=0.0, step=1.0)
        status = st.selectbox("Status", ["inventory", "sold"])
        date = st.date_input("Date", value=datetime.today())
        notes = st.text_input("Notes")

    if st.button("Add Pair", type="primary"):
        if item:
            conn = get_conn()
            execute(conn,
                "INSERT INTO sole_archive (date, item, size, buy_price, sell_price, platform, fees, shipping, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(date), item, size, buy_price, sell_price, platform if platform != "—" else None, fees, shipping, status, notes)
            )
            conn.commit()
            conn.close()
            st.success(f"Added {item} ({size})!")
            st.rerun()
        else:
            st.error("Sneaker name is required.")

tab1, tab2 = st.tabs(["📦 Inventory", "✅ Sold"])

with tab1:
    if inventory.empty:
        st.info("No inventory yet. Add your first pair above.")
    else:
        disp = inventory[['id', 'date', 'item', 'size', 'buy_price', 'notes']].copy()
        disp.columns = ['ID', 'Date', 'Sneaker', 'Size', 'Cost Basis', 'Notes']
        st.dataframe(disp, use_container_width=True, hide_index=True)

with tab2:
    if sold.empty:
        st.info("No sales recorded yet.")
    else:
        sold_disp = sold.copy()
        sold_disp['profit'] = sold_disp['sell_price'] - sold_disp['buy_price'] - sold_disp['fees'] - sold_disp['shipping']
        disp = sold_disp[['id', 'date', 'item', 'size', 'buy_price', 'sell_price', 'fees', 'shipping', 'profit', 'platform']].copy()
        disp.columns = ['ID', 'Date', 'Sneaker', 'Size', 'Cost', 'Sale Price', 'Fees', 'Shipping', 'Net Profit', 'Platform']

        def color_profit(val):
            return "color: #21c354" if val > 0 else "color: #ff4b4b"

        styled = disp.style.format({
            "Cost": "${:.2f}", "Sale Price": "${:.2f}",
            "Fees": "${:.2f}", "Shipping": "${:.2f}", "Net Profit": "${:.2f}"
        }).map(color_profit, subset=["Net Profit"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

if not inventory.empty:
    st.markdown("---")
    st.subheader("Mark Pair as Sold")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sell_id = st.selectbox("Select Item", inventory['id'].tolist(),
                               format_func=lambda x: inventory[inventory['id'] == x]['item'].values[0] + " — " + str(inventory[inventory['id'] == x]['size'].values[0]))
    with col2:
        sp = st.number_input("Sale Price ($)", min_value=0.0, step=5.0, key="sp")
        plat = st.selectbox("Platform", ["StockX", "GOAT", "eBay", "Facebook", "Other"], key="plat")
    with col3:
        f = st.number_input("Fees ($)", min_value=0.0, step=1.0, key="f")
        sh = st.number_input("Shipping ($)", min_value=0.0, step=1.0, key="sh")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Mark Sold", type="primary"):
            conn = get_conn()
            execute(conn,
                "UPDATE sole_archive SET status = 'sold', sell_price = ?, platform = ?, fees = ?, shipping = ? WHERE id = ?",
                (sp, plat, f, sh, sell_id)
            )
            conn.commit()
            conn.close()
            st.success("Marked as sold!")
            st.rerun()

# ── eBay Market Value Lookup ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔍 eBay Market Value Lookup")
st.caption("Search eBay's live listings to see what your sneakers are currently selling for.")

# Load saved eBay credentials
_ebay_id  = get_setting("ebay_client_id", "")
_ebay_sec = get_setting("ebay_client_secret", "")

with st.expander("⚙️ eBay API Credentials", expanded=not bool(_ebay_id)):
    st.markdown("""
**How to get your free eBay API keys:**
1. Go to [developer.ebay.com](https://developer.ebay.com) and sign in with your eBay account
2. Click **Get a User Token** → **Create App**
3. Copy your **Production App ID (Client ID)** and **Production Cert ID (Client Secret)**
4. Paste them below — these are stored locally and never shared
    """)
    new_id  = st.text_input("eBay Client ID (App ID)",     value=_ebay_id,  type="password", key="ebay_id_input")
    new_sec = st.text_input("eBay Client Secret (Cert ID)", value=_ebay_sec, type="password", key="ebay_sec_input")
    if st.button("💾 Save eBay Credentials", key="save_ebay"):
        set_setting("ebay_client_id",     new_id.strip())
        set_setting("ebay_client_secret", new_sec.strip())
        _ebay_id  = new_id.strip()
        _ebay_sec = new_sec.strip()
        st.success("eBay credentials saved!")
        st.rerun()

if _ebay_id and _ebay_sec:
    col_search, col_size = st.columns([3, 1])
    with col_search:
        # Pre-fill from inventory if available
        default_query = ""
        if not inventory.empty:
            default_query = str(inventory.iloc[0]["item"])
        search_query = st.text_input(
            "Search eBay for sneaker",
            value=default_query,
            placeholder="e.g. Jordan 1 Retro High OG Chicago Size 10",
            key="ebay_search_q"
        )
    with col_size:
        result_count = st.selectbox("Results", [5, 10, 20], index=1, key="ebay_limit")

    if st.button("🔍 Search eBay", type="primary", key="ebay_search_btn") and search_query.strip():
        with st.spinner(f"Searching eBay for '{search_query}'..."):
            try:
                results = ebay_search_sold(search_query.strip(), _ebay_id, _ebay_sec, limit=result_count)
            except Exception as e:
                results = []
                st.error(f"eBay API error: {e}")

        if not results:
            st.warning("No results found. Try a different search term (e.g. 'Jordan 1 Chicago 10' or 'Yeezy 350 Zebra').")
        else:
            prices = [r["price"] for r in results if r["price"] > 0]
            if prices:
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Listings Found", len(results))
                m2.metric("Avg Price",  f"${avg_price:,.2f}")
                m3.metric("Low",        f"${min_price:,.2f}")
                m4.metric("High",       f"${max_price:,.2f}")

            results_df = pd.DataFrame(results)
            results_df["price_fmt"] = results_df["price"].map("${:,.2f}".format)
            results_df["link"] = results_df["url"].apply(lambda u: f"[View on eBay]({u})" if u else "")

            st.dataframe(
                results_df[["title", "price_fmt", "condition", "link"]].rename(columns={
                    "title":     "Listing Title",
                    "price_fmt": "Price",
                    "condition": "Condition",
                    "link":      "Link",
                }),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Link": st.column_config.LinkColumn("Link", display_text="View →")
                }
            )
else:
    st.info("🔑 eBay account pending approval (1 business day). Use the KicksDB lookup below in the meantime.")

# ── KicksDB Sneaker Price Lookup ──────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 StockX & GOAT Price Lookup (KicksDB)")
st.caption("Real StockX + GOAT pricing data — **1,000 free requests/month, no credit card required.** Sign up at kicks.dev.")

_kicks_key = get_setting("kicksdb_api_key", "")

with st.expander("⚙️ KicksDB API Key Setup", expanded=not bool(_kicks_key)):
    st.markdown("""
**How to get your free KicksDB API key (2 minutes, no credit card):**
1. Go to [sneakersapi.dev](https://sneakersapi.dev) (KicksDB)
2. Click **Get started for free**
3. Create an account — free tier gives you **1,000 requests/month**
4. Copy your API key from the dashboard
5. Paste it below
    """)
    new_kicks = st.text_input("KicksDB API Key", value=_kicks_key, type="password", key="kicks_key_input")
    if st.button("💾 Save KicksDB Key", key="save_kicks"):
        set_setting("kicksdb_api_key", new_kicks.strip())
        _kicks_key = new_kicks.strip()
        st.success("KicksDB key saved!")
        st.rerun()

if _kicks_key:
    col_k1, col_k2, col_k3 = st.columns([3, 1, 1])
    with col_k1:
        default_q2 = ""
        if not inventory.empty:
            default_q2 = str(inventory.iloc[0]["item"])
        kicks_query = st.text_input(
            "Search sneaker name or SKU",
            value=default_q2,
            placeholder="e.g. Jordan 1 Chicago, Yeezy 350 Zebra, CT8527-100",
            key="kicks_search_q"
        )
    with col_k2:
        kicks_source = st.selectbox("Platform", ["stockx", "goat"], key="kicks_source",
                                     format_func=lambda x: "StockX" if x == "stockx" else "GOAT")
    with col_k3:
        kicks_limit = st.selectbox("Results", [5, 10], index=1, key="kicks_limit")

    if st.button("📊 Search Market Prices", type="primary", key="kicks_search_btn") and kicks_query.strip():
        with st.spinner(f"Fetching {kicks_source.upper()} prices for '{kicks_query}'..."):
            try:
                kicks_results = kicksdb_search_sneakers(kicks_query.strip(), _kicks_key,
                                                         source=kicks_source, limit=kicks_limit)
            except Exception as e:
                kicks_results = []
                st.error(f"KicksDB error: {e}")

        if not kicks_results:
            st.warning("No results found. Try a different name or SKU (e.g. 'Jordan 1 Retro High OG Chicago' or '555088-101').")
        else:
            min_prices = [r["min_price"] for r in kicks_results if r["min_price"] > 0]
            avg_prices = [r["avg_price"] for r in kicks_results if r["avg_price"] > 0]
            max_prices = [r["max_price"] for r in kicks_results if r["max_price"] > 0]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Results Found", len(kicks_results))
            m2.metric("Lowest Ask",  f"${min(min_prices):,.2f}" if min_prices else "—")
            m3.metric("Avg Price",   f"${sum(avg_prices)/len(avg_prices):,.2f}" if avg_prices else "—")
            m4.metric("Highest",     f"${max(max_prices):,.2f}" if max_prices else "—")

            kicks_df = pd.DataFrame(kicks_results)
            display_df = kicks_df[["title", "sku", "brand", "min_price", "avg_price", "max_price", "source"]].copy()
            display_df.columns = ["Sneaker", "SKU", "Brand", "Lowest Ask ($)", "Avg Price ($)", "Highest ($)", "Platform"]
            display_df["Lowest Ask ($)"] = display_df["Lowest Ask ($)"].apply(lambda x: f"${x:,.2f}" if x > 0 else "—")
            display_df["Avg Price ($)"]  = display_df["Avg Price ($)"].apply(lambda x: f"${x:,.2f}" if x > 0 else "—")
            display_df["Highest ($)"]    = display_df["Highest ($)"].apply(lambda x: f"${x:,.2f}" if x > 0 else "—")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("🔑 Add your free KicksDB API key above to search StockX & GOAT prices (1,000 free requests/month, no credit card).")

# ── Sole Alert Bot — Status + Alert Log + Price History ──────────────────────
st.markdown("---")
st.subheader("🤖 Sole Alert Bot — Live Status")
st.caption("The bot runs every 30 min on CT100 and pings @sole_archive_alerts_bot when profit opportunities appear.")

conn = get_conn()

# ── Bot status metrics ────────────────────────────────────────────────────────
try:
    alert_df = read_sql("""
        SELECT platform, profit, alerted_at, item, size
        FROM alert_log
        ORDER BY alerted_at DESC
        LIMIT 100
    """, conn)
    has_alert_log = True
except Exception:
    alert_df = pd.DataFrame()
    has_alert_log = False

try:
    history_df = read_sql("""
        SELECT item, size, ebay_avg, mercari_avg, checked_at
        FROM price_history
        ORDER BY checked_at DESC
        LIMIT 500
    """, conn)
    has_price_history = True
except Exception:
    history_df = pd.DataFrame()
    has_price_history = False

conn.close()

if has_alert_log and not alert_df.empty:
    total_alerts = len(alert_df)
    total_profit_alerted = alert_df['profit'].sum()
    last_alert = pd.to_datetime(alert_df['alerted_at'].iloc[0]).strftime("%b %d %I:%M %p") if not alert_df.empty else "—"
    ebay_alerts = len(alert_df[alert_df['platform'] == 'ebay'])
    mercari_alerts = len(alert_df[alert_df['platform'] == 'mercari'])
    arb_alerts = len(alert_df[alert_df['platform'] == 'arb'])

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("📨 Total Alerts Sent", total_alerts)
    b2.metric("💰 Total Profit Signaled", f"${total_profit_alerted:,.0f}")
    b3.metric("🕐 Last Alert", last_alert)
    b4.metric("🔵 Arb Signals", arb_alerts)

    st.markdown("#### 📋 Recent Alerts")
    alert_display = alert_df.copy()
    alert_display['alerted_at'] = pd.to_datetime(alert_display['alerted_at']).dt.strftime("%b %d %I:%M %p")
    alert_display['profit'] = alert_display['profit'].apply(lambda x: f"${x:,.0f}")
    alert_display['platform'] = alert_display['platform'].map({
        'ebay': '🟢 eBay Sell',
        'mercari': '🟢 Mercari Sell',
        'arb': '🔵 Arb Buy',
    }).fillna(alert_display['platform'])
    alert_display.columns = ['Platform', 'Profit', 'Time', 'Sneaker', 'Size']
    st.dataframe(alert_display[['Time', 'Platform', 'Sneaker', 'Size', 'Profit']],
                 use_container_width=True, hide_index=True)
else:
    st.info(
        "📭 No alerts sent yet — the bot hasn't run or no profitable opportunities found.\n\n"
        "**To go live:**\n"
        "1. Add inventory below (or above in the Add New Pair section)\n"
        "2. Save your eBay credentials in the section above\n"
        "3. Reboot CT100 → Proxmox UI → CT100 → Reboot\n"
        "4. Tell Darrian to set the Telegram env vars + cron job"
    )

# ── Price History Chart ───────────────────────────────────────────────────────
if has_price_history and not history_df.empty:
    st.markdown("#### 📈 Price History")
    items_with_history = history_df['item'].unique().tolist()
    selected_chart_item = st.selectbox("Select sneaker to chart", items_with_history, key="chart_item_select")

    item_history = history_df[history_df['item'] == selected_chart_item].copy()
    item_history['checked_at'] = pd.to_datetime(item_history['checked_at'])
    item_history = item_history.sort_values('checked_at')
    item_history = item_history.set_index('checked_at')[['ebay_avg', 'mercari_avg']].rename(columns={
        'ebay_avg': 'eBay Avg ($)',
        'mercari_avg': 'Mercari Avg ($)',
    })
    st.line_chart(item_history, use_container_width=True)

# ── Quick Inventory Add (bot-focused) ────────────────────────────────────────
st.markdown("---")
st.subheader("📦 Add Inventory for Bot Monitoring")
st.caption("Items added here are automatically monitored by the alert bot every 30 minutes.")

with st.form("bot_inventory_form", clear_on_submit=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        bot_item = st.text_input("Sneaker Name", placeholder="Jordan 1 Chicago")
        bot_size = st.text_input("Size", placeholder="10")
    with fc2:
        bot_cost = st.number_input("Your Cost Basis ($)", min_value=0.0, step=5.0,
                                    help="What you paid — the bot uses this to calculate profit")
        bot_notes = st.text_input("Notes (optional)", placeholder="Bought at outlet, DS")
    with fc3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Bot will alert when:**")
        _thresh = get_setting("min_profit_threshold", "30")
        st.markdown(f"• eBay profit > **${_thresh}** after fees")
        st.markdown(f"• Mercari profit > **${_thresh}** after fees")
        st.markdown(f"• Arb profit > **${float(_thresh)*1.5:.0f}** (1.5× threshold)")

    submitted = st.form_submit_button("➕ Add to Bot Inventory", type="primary")
    if submitted:
        if bot_item.strip():
            conn = get_conn()
            execute(conn,
                "INSERT INTO sole_archive (date, item, size, buy_price, sell_price, platform, fees, shipping, status, notes) VALUES (?, ?, ?, ?, 0, NULL, 0, 0, 'inventory', ?)",
                (datetime.today().strftime("%Y-%m-%d"), bot_item.strip(), bot_size.strip(), bot_cost, bot_notes.strip())
            )
            conn.commit()
            conn.close()
            st.success(f"✅ Added **{bot_item}** (Sz {bot_size}) at ${bot_cost:.0f} — bot will monitor this every 30 min!")
            st.rerun()
        else:
            st.error("Sneaker name is required.")

# ── Alert Threshold Setting ───────────────────────────────────────────────────
with st.expander("⚙️ Bot Alert Settings"):
    st.markdown("These settings control when the bot fires alerts. Changes take effect on the next bot run.")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        cur_thresh = float(get_setting("min_profit_threshold", "30"))
        new_thresh = st.number_input("Min Profit Threshold ($)", value=cur_thresh, min_value=5.0, step=5.0,
                                      help="Bot only alerts when net profit exceeds this amount")
    with col_t2:
        cur_ebay_fee = float(get_setting("ebay_fee_rate", "0.129"))
        new_ebay_fee = st.number_input("eBay Fee Rate", value=cur_ebay_fee, min_value=0.0, max_value=0.5, step=0.001, format="%.3f",
                                        help="eBay's fee as a decimal (12.9% = 0.129)")
    with col_t3:
        cur_merc_fee = float(get_setting("mercari_fee_rate", "0.10"))
        new_merc_fee = st.number_input("Mercari Fee Rate", value=cur_merc_fee, min_value=0.0, max_value=0.5, step=0.01, format="%.2f",
                                        help="Mercari's fee as a decimal (10% = 0.10)")

    if st.button("💾 Save Bot Settings", key="save_bot_settings"):
        set_setting("min_profit_threshold", str(new_thresh))
        set_setting("ebay_fee_rate", str(new_ebay_fee))
        set_setting("mercari_fee_rate", str(new_merc_fee))
        st.success("Bot settings saved! These will be picked up on the next cron run.")
        st.rerun()

# ── CT100 Deploy Instructions ─────────────────────────────────────────────────
with st.expander("🚀 CT100 Deploy Checklist — Go Live in 3 Steps"):
    st.markdown("""
### 3 Steps to Go Fully Live

**Step 1 — Add Inventory** ✅ (do it above)
Add your shoes + cost basis using the form above. The bot reads directly from this database.

**Step 2 — Save eBay API Keys** ✅ (do it in the eBay section above)
Budget app → Business Tracker → eBay API Credentials section → paste your keys → Save.

**Step 3 — Reboot CT100 + Set Env Vars**
```bash
# SSH into CT100 (Tailscale must be connected on your Mac)
ssh root@100.95.125.112

# Edit environment variables
nano /etc/environment

# Add these lines (fill in your real values):
DATABASE_URL=postgres://user:password@host.railway.app:5432/railway
TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
EBAY_CLIENT_ID=DarrianB-404Sole-PRD-xxxxxxxxxxxx-xxxxxxxx
EBAY_CLIENT_SECRET=PRD-xxxxxxxxxxxxxxxxxxxx-xxxxxxxx-xxxx-xxxx

# Save (Ctrl+O, Enter, Ctrl+X), then reload:
source /etc/environment

# Deploy the bot:
cd /Users/darrianbelcher/Downloads/darrian-budget/sole_alert_bot
./deploy.sh

# Test it:
python3 /opt/sole-alert/alert.py --test     # sends test Telegram message
python3 /opt/sole-alert/alert.py --dry-run  # shows what alerts would fire
```

**After reboot:** Tell me and I'll set the Telegram env vars + cron job in 2 minutes.

---
### Alert Types You'll Receive

| Alert | When | Example |
|-------|------|---------|
| 🟢 eBay Sell Signal | eBay avg − cost − fees > $30 | "Jordan 1 Chicago Sz 10: eBay avg $285, cost $180, net profit $87 → list it now" |
| 🟢 Mercari Sell Signal | Mercari avg − cost − fees > $30 | Same but Mercari (10% fees vs eBay's 13% = more profit per flip) |
| 🔵 Arb Opportunity | Mercari low → eBay avg profit > $45 | "Nike Dunk Panda Sz 11 on Mercari $95, eBay avg $165 → buy + flip for $52 profit" |

**Checks every 30 minutes, 8am–midnight. No spam — same item suppressed for 4 hours.**
    """)
