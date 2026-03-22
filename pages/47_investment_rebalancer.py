import streamlit as st
import json
import hashlib
from datetime import datetime, date
from decimal import Decimal
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Investment Rebalancer", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ph(n=1):
    return ", ".join(["%s"] * n) if USE_POSTGRES else ", ".join(["?"] * n)

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS target_allocations (
            id {"SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"},
            user_id INTEGER NOT NULL,
            asset_class TEXT NOT NULL,
            ticker TEXT,
            target_weight REAL NOT NULL,
            min_weight REAL DEFAULT 0,
            max_weight REAL DEFAULT 100,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, asset_class, ticker)
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS rebalance_history (
            id {"SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"},
            user_id INTEGER NOT NULL,
            rebalance_date DATE NOT NULL,
            portfolio_value REAL NOT NULL,
            drift_score REAL,
            recommendations TEXT,
            tax_loss_suggestions TEXT,
            executed BOOLEAN DEFAULT FALSE,
            execution_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id {"SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"},
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            shares REAL NOT NULL,
            cost_basis REAL NOT NULL,
            current_price REAL,
            current_value REAL,
            purchase_date DATE,
            account_type TEXT DEFAULT 'taxable',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, ticker, account_type)
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS rebalance_actions (
            id {"SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"},
            user_id INTEGER NOT NULL,
            rebalance_id INTEGER,
            action_type TEXT NOT NULL,
            ticker TEXT NOT NULL,
            shares REAL NOT NULL,
            estimated_value REAL NOT NULL,
            reason TEXT,
            tax_impact REAL DEFAULT 0,
            executed BOOLEAN DEFAULT FALSE,
            executed_at TIMESTAMP,
            execution_price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("⚖️ Investment Portfolio Rebalancer")
st.markdown("*AI-powered portfolio analysis with tax-loss harvesting recommendations*")

user_id = st.session_state.get("user_id", 1)

ASSET_CLASSES = [
    "US Large Cap",
    "US Mid Cap", 
    "US Small Cap",
    "International Developed",
    "Emerging Markets",
    "US Bonds",
    "International Bonds",
    "TIPS",
    "REITs",
    "Commodities",
    "Cash/Money Market",
    "Crypto",
    "Individual Stocks",
    "Other"
]

ACCOUNT_TYPES = ["taxable", "traditional_ira", "roth_ira", "401k", "hsa"]

def get_target_allocations():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, asset_class, ticker, target_weight, min_weight, max_weight, notes
        FROM target_allocations
        WHERE user_id = {_ph()}
        ORDER BY target_weight DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def save_target_allocation(asset_class, ticker, target_weight, min_weight, max_weight, notes):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO target_allocations (user_id, asset_class, ticker, target_weight, min_weight, max_weight, notes, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, asset_class, ticker) DO UPDATE SET
                target_weight = EXCLUDED.target_weight,
                min_weight = EXCLUDED.min_weight,
                max_weight = EXCLUDED.max_weight,
                notes = EXCLUDED.notes,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, asset_class, ticker, target_weight, min_weight, max_weight, notes))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO target_allocations (user_id, asset_class, ticker, target_weight, min_weight, max_weight, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, asset_class, ticker, target_weight, min_weight, max_weight, notes))
    
    conn.commit()
    cur.close()
    conn.close()

def save_holding(ticker, asset_class, shares, cost_basis, current_price, purchase_date, account_type):
    conn = get_conn()
    cur = conn.cursor()
    current_value = shares * current_price if current_price else 0
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO portfolio_holdings (user_id, ticker, asset_class, shares, cost_basis, current_price, current_value, purchase_date, account_type, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, ticker, account_type) DO UPDATE SET
                asset_class = EXCLUDED.asset_class,
                shares = EXCLUDED.shares,
                cost_basis = EXCLUDED.cost_basis,
                current_price = EXCLUDED.current_price,
                current_value = EXCLUDED.current_value,
                purchase_date = EXCLUDED.purchase_date,
                last_updated = CURRENT_TIMESTAMP
        """, (user_id, ticker, asset_class, shares, cost_basis, current_price, current_value, purchase_date, account_type))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO portfolio_holdings (user_id, ticker, asset_class, shares, cost_basis, current_price, current_value, purchase_date, account_type, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, ticker, asset_class, shares, cost_basis, current_price, current_value, purchase_date, account_type))
    
    conn.commit()
    cur.close()
    conn.close()

def get_holdings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, ticker, asset_class, shares, cost_basis, current_price, current_value, purchase_date, account_type
        FROM portfolio_holdings
        WHERE user_id = {_ph()}
        ORDER BY current_value DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def delete_holding(holding_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM portfolio_holdings WHERE id = {_ph()} AND user_id = {_ph()}", (holding_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_target_allocation(alloc_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM target_allocations WHERE id = {_ph()} AND user_id = {_ph()}", (alloc_id, user_id))
    conn.commit()
    cur.close()
    conn.close()

# Main UI
tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio", "🎯 Target Allocations", "⚖️ Rebalance", "📈 History"])

with tab1:
    st.subheader("Current Holdings")
    
    with st.expander("➕ Add New Holding"):
        col1, col2 = st.columns(2)
        with col1:
            h_ticker = st.text_input("Ticker Symbol", key="new_ticker")
            h_asset_class = st.selectbox("Asset Class", ASSET_CLASSES, key="new_asset_class")
            h_shares = st.number_input("Shares", min_value=0.0, step=0.01, key="new_shares")
            h_cost_basis = st.number_input("Cost Basis (per share)", min_value=0.0, step=0.01, key="new_cost")
        with col2:
            h_current_price = st.number_input("Current Price", min_value=0.0, step=0.01, key="new_price")
            h_purchase_date = st.date_input("Purchase Date", key="new_date")
            h_account_type = st.selectbox("Account Type", ACCOUNT_TYPES, key="new_account")
        
        if st.button("Add Holding"):
            if h_ticker and h_shares > 0:
                save_holding(h_ticker, h_asset_class, h_shares, h_cost_basis, h_current_price, h_purchase_date, h_account_type)
                st.success(f"Added {h_ticker}")
                st.rerun()
            else:
                st.error("Please enter ticker and shares")
    
    holdings = get_holdings()
    if holdings:
        df = pd.DataFrame(holdings, columns=["ID", "Ticker", "Asset Class", "Shares", "Cost Basis", "Current Price", "Current Value", "Purchase Date", "Account Type"])
        df["Gain/Loss"] = (df["Current Price"] - df["Cost Basis"]) * df["Shares"]
        df["Gain/Loss %"] = ((df["Current Price"] - df["Cost Basis"]) / df["Cost Basis"] * 100).round(2)
        
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True)
        
        total_value = df["Current Value"].sum()
        total_cost = (df["Cost Basis"] * df["Shares"]).sum()
        total_gain = total_value - total_cost
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Portfolio Value", f"${total_value:,.2f}")
        col2.metric("Total Cost Basis", f"${total_cost:,.2f}")
        col3.metric("Total Gain/Loss", f"${total_gain:,.2f}", f"{(total_gain/total_cost*100):.2f}%" if total_cost > 0 else "0%")
        
        # Pie chart
        fig = px.pie(df, values="Current Value", names="Asset Class", title="Portfolio by Asset Class")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No holdings yet. Add your first holding above.")

with tab2:
    st.subheader("Target Asset Allocation")
    
    with st.expander("➕ Add Target Allocation"):
        col1, col2 = st.columns(2)
        with col1:
            t_asset_class = st.selectbox("Asset Class", ASSET_CLASSES, key="target_asset")
            t_ticker = st.text_input("Specific Ticker (optional)", key="target_ticker")
            t_target = st.number_input("Target Weight (%)", min_value=0.0, max_value=100.0, step=0.5, key="target_weight")
        with col2:
            t_min = st.number_input("Min Weight (%)", min_value=0.0, max_value=100.0, step=0.5, key="target_min")
            t_max = st.number_input("Max Weight (%)", min_value=0.0, max_value=100.0, value=100.0, step=0.5, key="target_max")
            t_notes = st.text_input("Notes", key="target_notes")
        
        if st.button("Save Target"):
            save_target_allocation(t_asset_class, t_ticker, t_target, t_min, t_max, t_notes)
            st.success("Target allocation saved")
            st.rerun()
    
    allocations = get_target_allocations()
    if allocations:
        df_alloc = pd.DataFrame(allocations, columns=["ID", "Asset Class", "Ticker", "Target %", "Min %", "Max %", "Notes"])
        st.dataframe(df_alloc.drop(columns=["ID"]), use_container_width=True)
        
        total_target = df_alloc["Target %"].sum()
        if abs(total_target - 100) > 0.01:
            st.warning(f"Target allocations sum to {total_target:.1f}%. Should equal 100%.")
        else:
            st.success("Target allocations sum to 100% ✓")
    else:
        st.info("No target allocations set. Add your desired asset allocation above.")

with tab3:
    st.subheader("Rebalance Analysis")
    
    holdings = get_holdings()
    allocations = get_target_allocations()
    
    if holdings and allocations:
        df_holdings = pd.DataFrame(holdings, columns=["ID", "Ticker", "Asset Class", "Shares", "Cost Basis", "Current Price", "Current Value", "Purchase Date", "Account Type"])
        df_alloc = pd.DataFrame(allocations, columns=["ID", "Asset Class", "Ticker", "Target %", "Min %", "Max %", "Notes"])
        
        total_value = df_holdings["Current Value"].sum()
        
        # Calculate current allocation by asset class
        current_alloc = df_holdings.groupby("Asset Class")["Current Value"].sum().reset_index()
        current_alloc["Current %"] = (current_alloc["Current Value"] / total_value * 100).round(2)
        
        # Merge with targets
        comparison = df_alloc[["Asset Class", "Target %"]].merge(current_alloc, on="Asset Class", how="outer").fillna(0)
        comparison["Drift"] = comparison["Current %"] - comparison["Target %"]
        comparison["Action Needed"] = comparison["Drift"].apply(lambda x: "SELL" if x > 2 else ("BUY" if x < -2 else "OK"))
        
        st.dataframe(comparison, use_container_width=True)
        
        # Drift chart
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Target %", x=comparison["Asset Class"], y=comparison["Target %"]))
        fig.add_trace(go.Bar(name="Current %", x=comparison["Asset Class"], y=comparison["Current %"]))
        fig.update_layout(barmode="group", title="Target vs Current Allocation")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add holdings and target allocations to see rebalance recommendations.")

with tab4:
    st.subheader("Rebalance History")
    st.info("Rebalance history will appear here after you execute rebalancing actions.")