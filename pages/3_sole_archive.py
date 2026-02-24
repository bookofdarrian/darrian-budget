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
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",              icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",                icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="Business Tracker 🔒",   icon="💼")
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
