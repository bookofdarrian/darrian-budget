import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, execute, get_setting, set_setting
from utils.auth import require_password

st.set_page_config(page_title="404 Sole Archive", page_icon="👟", layout="wide")
init_db()
require_password()


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
        })
    return results

st.sidebar.title("💰 Budget Dashboard")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")

st.title("👟 404 Sole Archive — Resale Tracker")

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
    st.info("🔑 Add your eBay API credentials above to enable market value lookups.")
