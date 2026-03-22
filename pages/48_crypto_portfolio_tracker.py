import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
from typing import Optional, Dict, List, Tuple
import time

st.set_page_config(page_title="Crypto Portfolio Tracker", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_holdings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                coin_id VARCHAR(100) NOT NULL,
                coin_symbol VARCHAR(20) NOT NULL,
                coin_name VARCHAR(100) NOT NULL,
                quantity DECIMAL(20, 10) NOT NULL,
                avg_purchase_price DECIMAL(20, 10) NOT NULL,
                total_cost DECIMAL(20, 10) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                coin_id VARCHAR(100) NOT NULL,
                coin_symbol VARCHAR(20) NOT NULL,
                coin_name VARCHAR(100) NOT NULL,
                transaction_type VARCHAR(10) NOT NULL,
                quantity DECIMAL(20, 10) NOT NULL,
                price_per_coin DECIMAL(20, 10) NOT NULL,
                total_value DECIMAL(20, 10) NOT NULL,
                fees DECIMAL(20, 10) DEFAULT 0,
                notes TEXT,
                transaction_date TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_price_cache (
                id SERIAL PRIMARY KEY,
                coin_id VARCHAR(100) UNIQUE NOT NULL,
                price_usd DECIMAL(20, 10),
                price_change_24h DECIMAL(10, 4),
                market_cap BIGINT,
                volume_24h BIGINT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                coin_id TEXT NOT NULL,
                coin_symbol TEXT NOT NULL,
                coin_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_purchase_price REAL NOT NULL,
                total_cost REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                coin_id TEXT NOT NULL,
                coin_symbol TEXT NOT NULL,
                coin_name TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price_per_coin REAL NOT NULL,
                total_value REAL NOT NULL,
                fees REAL DEFAULT 0,
                notes TEXT,
                transaction_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crypto_price_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT UNIQUE NOT NULL,
                price_usd REAL,
                price_change_24h REAL,
                market_cap INTEGER,
                volume_24h INTEGER,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


_ensure_tables()


POPULAR_COINS = {
    "bitcoin": {"symbol": "BTC", "name": "Bitcoin"},
    "ethereum": {"symbol": "ETH", "name": "Ethereum"},
    "binancecoin": {"symbol": "BNB", "name": "BNB"},
    "ripple": {"symbol": "XRP", "name": "XRP"},
    "cardano": {"symbol": "ADA", "name": "Cardano"},
    "solana": {"symbol": "SOL", "name": "Solana"},
    "dogecoin": {"symbol": "DOGE", "name": "Dogecoin"},
    "polkadot": {"symbol": "DOT", "name": "Polkadot"},
    "litecoin": {"symbol": "LTC", "name": "Litecoin"},
    "chainlink": {"symbol": "LINK", "name": "Chainlink"},
}


def search_coins(query: str) -> List[Dict]:
    """Search for coins by name or symbol."""
    if not query:
        return []
    
    query = query.lower()
    results = []
    
    for coin_id, info in POPULAR_COINS.items():
        if query in coin_id.lower() or query in info["symbol"].lower() or query in info["name"].lower():
            results.append({
                "id": coin_id,
                "symbol": info["symbol"],
                "name": info["name"]
            })
    
    return results


def get_coin_price(coin_id: str) -> Optional[Dict]:
    """Get current price for a coin from CoinGecko API."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if coin_id in data:
                return {
                    "price_usd": data[coin_id].get("usd", 0),
                    "price_change_24h": data[coin_id].get("usd_24h_change", 0),
                    "market_cap": data[coin_id].get("usd_market_cap", 0),
                    "volume_24h": data[coin_id].get("usd_24h_vol", 0)
                }
    except Exception as e:
        st.warning(f"Could not fetch price for {coin_id}: {e}")
    return None


def get_holdings(user_id: int = 1) -> pd.DataFrame:
    """Get all holdings for a user."""
    conn = get_conn()
    if USE_POSTGRES:
        df = pd.read_sql_query(
            "SELECT * FROM crypto_holdings WHERE user_id = %s ORDER BY total_cost DESC",
            conn, params=(user_id,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM crypto_holdings WHERE user_id = ? ORDER BY total_cost DESC",
            conn, params=(user_id,)
        )
    conn.close()
    return df


def add_transaction(user_id: int, coin_id: str, coin_symbol: str, coin_name: str,
                   transaction_type: str, quantity: float, price_per_coin: float,
                   fees: float = 0, notes: str = "", transaction_date: datetime = None):
    """Add a new transaction and update holdings."""
    conn = get_conn()
    cur = conn.cursor()
    
    if transaction_date is None:
        transaction_date = datetime.now()
    
    total_value = quantity * price_per_coin
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO crypto_transactions 
            (user_id, coin_id, coin_symbol, coin_name, transaction_type, quantity, 
             price_per_coin, total_value, fees, notes, transaction_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, coin_id, coin_symbol, coin_name, transaction_type, quantity,
              price_per_coin, total_value, fees, notes, transaction_date))
        
        cur.execute("SELECT * FROM crypto_holdings WHERE user_id = %s AND coin_id = %s", 
                   (user_id, coin_id))
    else:
        cur.execute("""
            INSERT INTO crypto_transactions 
            (user_id, coin_id, coin_symbol, coin_name, transaction_type, quantity, 
             price_per_coin, total_value, fees, notes, transaction_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, coin_id, coin_symbol, coin_name, transaction_type, quantity,
              price_per_coin, total_value, fees, notes, transaction_date.isoformat()))
        
        cur.execute("SELECT * FROM crypto_holdings WHERE user_id = ? AND coin_id = ?", 
                   (user_id, coin_id))
    
    holding = cur.fetchone()
    
    if transaction_type == "BUY":
        if holding:
            new_quantity = float(holding[5]) + quantity
            new_total_cost = float(holding[7]) + total_value
            new_avg_price = new_total_cost / new_quantity
            
            if USE_POSTGRES:
                cur.execute("""
                    UPDATE crypto_holdings 
                    SET quantity = %s, avg_purchase_price = %s, total_cost = %s, updated_at = %s
                    WHERE user_id = %s AND coin_id = %s
                """, (new_quantity, new_avg_price, new_total_cost, datetime.now(), user_id, coin_id))
            else:
                cur.execute("""
                    UPDATE crypto_holdings 
                    SET quantity = ?, avg_purchase_price = ?, total_cost = ?, updated_at = ?
                    WHERE user_id = ? AND coin_id = ?
                """, (new_quantity, new_avg_price, new_total_cost, datetime.now().isoformat(), user_id, coin_id))
        else:
            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO crypto_holdings 
                    (user_id, coin_id, coin_symbol, coin_name, quantity, avg_purchase_price, total_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, coin_id, coin_symbol, coin_name, quantity, price_per_coin, total_value))
            else:
                cur.execute("""
                    INSERT INTO crypto_holdings 
                    (user_id, coin_id, coin_symbol, coin_name, quantity, avg_purchase_price, total_cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, coin_id, coin_symbol, coin_name, quantity, price_per_coin, total_value))
    
    elif transaction_type == "SELL":
        if holding:
            new_quantity = float(holding[5]) - quantity
            if new_quantity <= 0:
                if USE_POSTGRES:
                    cur.execute("DELETE FROM crypto_holdings WHERE user_id = %s AND coin_id = %s", 
                               (user_id, coin_id))
                else:
                    cur.execute("DELETE FROM crypto_holdings WHERE user_id = ? AND coin_id = ?", 
                               (user_id, coin_id))
            else:
                new_total_cost = new_quantity * float(holding[6])
                if USE_POSTGRES:
                    cur.execute("""
                        UPDATE crypto_holdings 
                        SET quantity = %s, total_cost = %s, updated_at = %s
                        WHERE user_id = %s AND coin_id = %s
                    """, (new_quantity, new_total_cost, datetime.now(), user_id, coin_id))
                else:
                    cur.execute("""
                        UPDATE crypto_holdings 
                        SET quantity = ?, total_cost = ?, updated_at = ?
                        WHERE user_id = ? AND coin_id = ?
                    """, (new_quantity, new_total_cost, datetime.now().isoformat(), user_id, coin_id))
    
    conn.commit()
    conn.close()


def get_transactions(user_id: int = 1) -> pd.DataFrame:
    """Get all transactions for a user."""
    conn = get_conn()
    if USE_POSTGRES:
        df = pd.read_sql_query(
            "SELECT * FROM crypto_transactions WHERE user_id = %s ORDER BY transaction_date DESC",
            conn, params=(user_id,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM crypto_transactions WHERE user_id = ? ORDER BY transaction_date DESC",
            conn, params=(user_id,)
        )
    conn.close()
    return df


# Main UI
st.title("🪙 Crypto Portfolio Tracker")

tab1, tab2, tab3 = st.tabs(["📊 Portfolio", "➕ Add Transaction", "📜 History"])

with tab1:
    st.subheader("Your Holdings")
    
    holdings_df = get_holdings()
    
    if holdings_df.empty:
        st.info("No holdings yet. Add your first transaction to get started!")
    else:
        total_value = 0
        total_cost = 0
        
        for idx, row in holdings_df.iterrows():
            price_data = get_coin_price(row['coin_id'])
            if price_data:
                current_price = price_data['price_usd']
                current_value = row['quantity'] * current_price
                total_value += current_value
                total_cost += row['total_cost']
                
                profit_loss = current_value - row['total_cost']
                profit_pct = (profit_loss / row['total_cost']) * 100 if row['total_cost'] > 0 else 0
                
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                with col1:
                    st.write(f"**{row['coin_name']}** ({row['coin_symbol']})")
                with col2:
                    st.write(f"Qty: {row['quantity']:.6f}")
                with col3:
                    st.write(f"Value: ${current_value:,.2f}")
                with col4:
                    color = "green" if profit_loss >= 0 else "red"
                    st.markdown(f"P/L: <span style='color:{color}'>${profit_loss:,.2f} ({profit_pct:.2f}%)</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        total_pl = total_value - total_cost
        total_pl_pct = (total_pl / total_cost) * 100 if total_cost > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Portfolio Value", f"${total_value:,.2f}")
        with col2:
            st.metric("Total Cost Basis", f"${total_cost:,.2f}")
        with col3:
            st.metric("Total P/L", f"${total_pl:,.2f}", f"{total_pl_pct:.2f}%")

with tab2:
    st.subheader("Add Transaction")
    
    search_query = st.text_input("Search for a coin", placeholder="Bitcoin, ETH, etc.")
    
    if search_query:
        search_results = search_coins(search_query)
        if search_results:
            coin_options = {f"{r['name']} ({r['symbol']})": r for r in search_results}
            selected = st.selectbox("Select coin", list(coin_options.keys()))
            selected_coin = coin_options[selected]
        else:
            st.warning("No coins found matching your search.")
            selected_coin = None
    else:
        selected_coin = None
    
    if selected_coin:
        col1, col2 = st.columns(2)
        with col1:
            trans_type = st.selectbox("Transaction Type", ["BUY", "SELL"])
            quantity = st.number_input("Quantity", min_value=0.0, step=0.001, format="%.6f")
        with col2:
            price = st.number_input("Price per coin (USD)", min_value=0.0, step=0.01, format="%.2f")
            fees = st.number_input("Fees (USD)", min_value=0.0, step=0.01, value=0.0, format="%.2f")
        
        notes = st.text_area("Notes (optional)")
        trans_date = st.date_input("Transaction Date", value=datetime.now())
        
        if st.button("Add Transaction", type="primary"):
            if quantity > 0 and price > 0:
                add_transaction(
                    user_id=1,
                    coin_id=selected_coin['id'],
                    coin_symbol=selected_coin['symbol'],
                    coin_name=selected_coin['name'],
                    transaction_type=trans_type,
                    quantity=quantity,
                    price_per_coin=price,
                    fees=fees,
                    notes=notes,
                    transaction_date=datetime.combine(trans_date, datetime.min.time())
                )
                st.success(f"Transaction added: {trans_type} {quantity} {selected_coin['symbol']} @ ${price}")
                st.rerun()
            else:
                st.error("Please enter valid quantity and price.")

with tab3:
    st.subheader("Transaction History")
    
    transactions_df = get_transactions()
    
    if transactions_df.empty:
        st.info("No transactions yet.")
    else:
        for idx, row in transactions_df.iterrows():
            color = "🟢" if row['transaction_type'] == "BUY" else "🔴"
            st.write(f"{color} **{row['transaction_type']}** {row['quantity']:.6f} {row['coin_symbol']} @ ${row['price_per_coin']:.2f} = ${row['total_value']:.2f}")
            st.caption(f"{row['transaction_date']} | {row['notes'] if row['notes'] else 'No notes'}")
            st.markdown("---")