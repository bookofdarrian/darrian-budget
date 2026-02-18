import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, execute
from utils.auth import require_password

st.set_page_config(page_title="404 Sole Archive", page_icon="👟", layout="wide")
init_db()
require_password()

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
