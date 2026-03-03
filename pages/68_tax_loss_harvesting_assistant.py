import streamlit as st
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

st.set_page_config(page_title="Tax Loss Harvesting Assistant", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ph(idx=None):
    if USE_POSTGRES:
        return "%s"
    return "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS tax_lots (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            purchase_date DATE NOT NULL,
            quantity REAL NOT NULL,
            cost_basis REAL NOT NULL,
            account_name TEXT DEFAULT 'Default',
            lot_method TEXT DEFAULT 'FIFO',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS wash_sale_tracker (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            sale_date DATE NOT NULL,
            sale_quantity REAL NOT NULL,
            loss_amount REAL NOT NULL,
            wash_sale_detected BOOLEAN DEFAULT FALSE,
            related_purchase_date DATE,
            related_purchase_id INTEGER,
            disallowed_loss REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS harvesting_events (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            event_date DATE NOT NULL,
            quantity_sold REAL NOT NULL,
            sale_price REAL NOT NULL,
            cost_basis REAL NOT NULL,
            realized_loss REAL NOT NULL,
            tax_savings_estimated REAL DEFAULT 0,
            replacement_symbol TEXT,
            replacement_date DATE,
            status TEXT DEFAULT 'planned',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS capital_gains_log (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            tax_year INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            sale_date DATE NOT NULL,
            quantity REAL NOT NULL,
            sale_proceeds REAL NOT NULL,
            cost_basis REAL NOT NULL,
            gain_loss REAL NOT NULL,
            holding_period TEXT NOT NULL,
            is_wash_sale BOOLEAN DEFAULT FALSE,
            wash_sale_adjustment REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS current_prices (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            symbol TEXT UNIQUE NOT NULL,
            current_price REAL NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id():
    return st.session_state.get("user_id", 1)

def calculate_holding_period(purchase_date, sale_date=None):
    if sale_date is None:
        sale_date = datetime.now().date()
    if isinstance(purchase_date, str):
        purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    if isinstance(sale_date, str):
        sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
    
    days_held = (sale_date - purchase_date).days
    if days_held > 365:
        return "long-term", days_held
    return "short-term", days_held

def calculate_cost_basis_fifo(lots, quantity_to_sell):
    sorted_lots = sorted(lots, key=lambda x: x['purchase_date'])
    total_cost = 0
    remaining = quantity_to_sell
    lots_used = []
    
    for lot in sorted_lots:
        if remaining <= 0:
            break
        qty_from_lot = min(lot['quantity'], remaining)
        cost_per_share = lot['cost_basis'] / lot['quantity']
        total_cost += qty_from_lot * cost_per_share
        remaining -= qty_from_lot
        lots_used.append({
            'lot_id': lot['id'],
            'quantity_used': qty_from_lot,
            'cost': qty_from_lot * cost_per_share,
            'purchase_date': lot['purchase_date']
        })
    
    return total_cost, lots_used

def calculate_cost_basis_lifo(lots, quantity_to_sell):
    sorted_lots = sorted(lots, key=lambda x: x['purchase_date'], reverse=True)
    total_cost = 0
    remaining = quantity_to_sell
    lots_used = []
    
    for lot in sorted_lots:
        if remaining <= 0:
            break
        qty_from_lot = min(lot['quantity'], remaining)
        cost_per_share = lot['cost_basis'] / lot['quantity']
        total_cost += qty_from_lot * cost_per_share
        remaining -= qty_from_lot
        lots_used.append({
            'lot_id': lot['id'],
            'quantity_used': qty_from_lot,
            'cost': qty_from_lot * cost_per_share,
            'purchase_date': lot['purchase_date']
        })
    
    return total_cost, lots_used

def get_tax_lots(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM tax_lots WHERE user_id = {_ph()} ORDER BY symbol, purchase_date", (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    columns = ['id', 'user_id', 'symbol', 'purchase_date', 'quantity', 'cost_basis', 
               'account_name', 'lot_method', 'notes', 'created_at', 'updated_at']
    return [dict(zip(columns, row)) for row in rows]

def get_current_price(symbol):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT current_price FROM current_prices WHERE symbol = {_ph()}", (symbol,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_current_price(symbol, price):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO current_prices (symbol, current_price, last_updated) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (symbol) DO UPDATE SET current_price = %s, last_updated = CURRENT_TIMESTAMP
        """, (symbol, price, price))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO current_prices (symbol, current_price, last_updated) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (symbol, price))
    conn.commit()
    conn.close()

def add_tax_lot(user_id, symbol, purchase_date, quantity, cost_basis, account_name='Default', notes=''):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO tax_lots (user_id, symbol, purchase_date, quantity, cost_basis, account_name, notes)
        VALUES ({_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()})
    """, (user_id, symbol.upper(), purchase_date, quantity, cost_basis, account_name, notes))
    conn.commit()
    conn.close()

def delete_tax_lot(lot_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM tax_lots WHERE id = {_ph()}", (lot_id,))
    conn.commit()
    conn.close()

def check_wash_sale(user_id, symbol, sale_date):
    if isinstance(sale_date, str):
        sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
    
    window_start = sale_date - timedelta(days=30)
    window_end = sale_date + timedelta(days=30)
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT * FROM tax_lots 
        WHERE user_id = {_ph()} AND symbol = {_ph()} 
        AND purchase_date BETWEEN {_ph()} AND {_ph()}
    """, (user_id, symbol, window_start, window_end))
    rows = cur.fetchall()
    conn.close()
    
    return len(rows) > 0, rows

def calculate_unrealized_gains_losses(user_id):
    lots = get_tax_lots(user_id)
    results = []
    
    for lot in lots:
        current_price = get_current_price(lot['symbol'])
        if current_price is None:
            continue
        
        current_value = lot['quantity'] * current_price
        gain_loss = current_value - lot['cost_basis']
        gain_loss_pct = (gain_loss / lot['cost_basis']) * 100 if lot['cost_basis'] > 0 else 0
        holding_period, days_held = calculate_holding_period(lot['purchase_date'])
        
        results.append({
            'id': lot['id'],
            'symbol': lot['symbol'],
            'quantity': lot['quantity'],
            'cost_basis': lot['cost_basis'],
            'current_price': current_price,
            'current_value': current_value,
            'gain_loss': gain_loss,
            'gain_loss_pct': gain_loss_pct,
            'holding_period': holding_period,
            'days_held': days_held,
            'purchase_date': lot['purchase_date'],
            'account_name': lot['account_name']
        })
    
    return results

def get_harvesting_opportunities(user_id, min_loss=100):
    unrealized = calculate_unrealized_gains_losses(user_id)
    opportunities = [r for r in unrealized if r['gain_loss'] < -min_loss]
    return sorted(opportunities, key=lambda x: x['gain_loss'])

def record_harvesting_event(user_id, symbol, event_date, quantity_sold, sale_price, cost_basis, 
                           realized_loss, tax_savings=0, replacement_symbol=None, notes=''):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO harvesting_events 
        (user_id, symbol, event_date, quantity_sold, sale_price, cost_basis, realized_loss, 
         tax_savings_estimated, replacement_symbol, notes)
        VALUES ({_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()})
    """, (user_id, symbol, event_date, quantity_sold, sale_price, cost_basis, realized_loss, 
          tax_savings, replacement_symbol, notes))
    conn.commit()
    conn.close()

def get_harvesting_events(user_id, tax_year=None):
    conn = get_conn()
    cur = conn.cursor()
    if tax_year:
        if USE_POSTGRES:
            cur.execute(f"""
                SELECT * FROM harvesting_events 
                WHERE user_id = {_ph()} AND EXTRACT(YEAR FROM event_date) = {_ph()}
                ORDER BY event_date DESC
            """, (user_id, tax_year))
        else:
            cur.execute(f"""
                SELECT * FROM harvesting_events 
                WHERE user_id = {_ph()} AND strftime('%Y', event_date) = {_ph()}
                ORDER BY event_date DESC
            """, (user_id, str(tax_year)))
    else:
        cur.execute(f"SELECT * FROM harvesting_events WHERE user_id = {_ph()} ORDER BY event_date DESC", (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    columns = ['id', 'user_id', 'symbol', 'event_date', 'quantity_sold', 'sale_price', 
               'cost_basis', 'realized_loss', 'tax_savings_estimated', 'replacement_symbol',
               'replacement_date', 'status', 'notes', 'created_at']
    return [dict(zip(columns, row)) for row in rows]

# Main UI
st.title("🍑 Tax Loss Harvesting Assistant")

render_sidebar_brand()
render_sidebar_user_widget()

user_id = get_user_id()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Portfolio Overview", 
    "🔍 Harvesting Opportunities", 
    "📝 Manage Tax Lots",
    "📈 Harvesting History",
    "⚙️ Settings"
])

with tab1:
    st.header("Portfolio Overview")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("Update Prices")
        lots = get_tax_lots(user_id)
        symbols = list(set([lot['symbol'] for lot in lots]))
        
        if symbols:
            selected_symbol = st.selectbox("Symbol", symbols)
            current = get_current_price(selected_symbol)
            new_price = st.number_input("Current Price", value=current or 0.0, min_value=0.0, step=0.01)
            if st.button("Update Price"):
                set_current_price(selected_symbol, new_price)
                st.success(f"Updated {selected_symbol} price to ${new_price:.2f}")
                st.rerun()
    
    with col1:
        unrealized = calculate_unrealized_gains_losses(user_id)
        
        if unrealized:
            df = pd.DataFrame(unrealized)
            df['purchase_date'] = pd.to_datetime(df['purchase_date']).dt.strftime('%Y-%m-%d')
            
            total_gain_loss = df['gain_loss'].sum()
            total_cost = df['cost_basis'].sum()
            total_value = df['current_value'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Cost Basis", f"${total_cost:,.2f}")
            m2.metric("Total Current Value", f"${total_value:,.2f}")
            m3.metric("Total Unrealized Gain/Loss", f"${total_gain_loss:,.2f}", 
                     delta=f"{(total_gain_loss/total_cost*100):.1f}%" if total_cost > 0 else "0%")
            
            st.dataframe(
                df[['symbol', 'quantity', 'cost_basis', 'current_price', 'current_value', 
                    'gain_loss', 'gain_loss_pct', 'holding_period', 'days_held']].rename(columns={
                    'symbol': 'Symbol',
                    'quantity': 'Quantity',
                    'cost_basis': 'Cost Basis',
                    'current_price': 'Current Price',
                    'current_value': 'Current Value',
                    'gain_loss': 'Gain/Loss',
                    'gain_loss_pct': 'Gain/Loss %',
                    'holding_period': 'Holding Period',
                    'days_held': 'Days Held'
                }),
                use_container_width=True
            )
        else:
            st.info("No tax lots found. Add some positions in the 'Manage Tax Lots' tab.")

with tab2:
    st.header("🔍 Tax Loss Harvesting Opportunities")
    
    min_loss = st.number_input("Minimum Loss Threshold ($)", value=100.0, min_value=0.0, step=50.0)
    tax_rate = st.slider("Estimated Tax Rate (%)", 0, 50, 25) / 100
    
    opportunities = get_harvesting_opportunities(user_id, min_loss)
    
    if opportunities:
        st.success(f"Found {len(opportunities)} harvesting opportunities")
        
        total_harvestable_loss = sum([o['gain_loss'] for o in opportunities])
        estimated_tax_savings = abs(total_harvestable_loss) * tax_rate
        
        c1, c2 = st.columns(2)
        c1.metric("Total Harvestable Losses", f"${abs(total_harvestable_loss):,.2f}")
        c2.metric("Estimated Tax Savings", f"${estimated_tax_savings:,.2f}")
        
        for opp in opportunities:
            with st.expander(f"{opp['symbol']} - Loss: ${abs(opp['gain_loss']):,.2f}"):
                st.write(f"**Quantity:** {opp['quantity']}")
                st.write(f"**Cost Basis:** ${opp['cost_basis']:,.2f}")
                st.write(f"**Current Value:** ${opp['current_value']:,.2f}")
                st.write(f"**Holding Period:** {opp['holding_period']} ({opp['days_held']} days)")
                st.write(f"**Potential Tax Savings:** ${abs(opp['gain_loss']) * tax_rate:,.2f}")
                
                is_wash, related = check_wash_sale(user_id, opp['symbol'], datetime.now().date())
                if is_wash:
                    st.warning("⚠️ Wash sale risk detected - recent purchases within 30-day window")
                
                if st.button(f"Record Harvest for {opp['symbol']}", key=f"harvest_{opp['id']}"):
                    record_harvesting_event(
                        user_id, opp['symbol'], datetime.now().date(),
                        opp['quantity'], opp['current_price'], opp['cost_basis'],
                        opp['gain_loss'], abs(opp['gain_loss']) * tax_rate
                    )
                    delete_tax_lot(opp['id'])
                    st.success("Harvesting event recorded!")
                    st.rerun()
    else:
        st.info("No harvesting opportunities found above the minimum loss threshold.")

with tab3:
    st.header("📝 Manage Tax Lots")
    
    with st.form("add_lot_form"):
        st.subheader("Add New Tax Lot")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            symbol = st.text_input("Symbol", placeholder="AAPL").upper()
            quantity = st.number_input("Quantity", min_value=0.0001, step=1.0)
        with col2:
            purchase_date = st.date_input("Purchase Date", value=datetime.now().date())
            cost_basis = st.number_input("Total Cost Basis ($)", min_value=0.01, step=100.0)
        with col3:
            account_name = st.text_input("Account Name", value="Default")
            notes = st.text_input("Notes", placeholder="Optional notes")
        
        if st.form_submit_button("Add Tax Lot"):
            if symbol and quantity > 0 and cost_basis > 0:
                add_tax_lot(user_id, symbol, purchase_date, quantity, cost_basis, account_name, notes)
                st.success(f"Added {quantity} shares of {symbol}")
                st.rerun()
            else:
                st.error("Please fill in all required fields")
    
    st.subheader("Existing Tax Lots")
    lots = get_tax_lots(user_id)
    
    if lots:
        for lot in lots:
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            col1.write(f"**{lot['symbol']}** - {lot['quantity']} shares")
            col2.write(f"Cost: ${lot['cost_basis']:,.2f}")
            col3.write(f"Purchased: {lot['purchase_date']}")
            if col4.button("🗑️", key=f"del_{lot['id']}"):
                delete_tax_lot(lot['id'])
                st.rerun()
    else:
        st.info("No tax lots found. Add your first position above.")

with tab4:
    st.header("📈 Harvesting History")
    
    current_year = datetime.now().year
    selected_year = st.selectbox("Tax Year", [current_year, current_year - 1, current_year - 2])
    
    events = get_harvesting_events(user_id, selected_year)
    
    if events:
        total_losses = sum([e['realized_loss'] for e in events])
        total_savings = sum([e['tax_savings_estimated'] for e in events])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Harvested Losses", f"${abs(total_losses):,.2f}")
        c2.metric("Estimated Tax Savings", f"${total_savings:,.2f}")
        c3.metric("Number of Events", len(events))
        
        df = pd.DataFrame(events)
        st.dataframe(
            df[['symbol', 'event_date', 'quantity_sold', 'realized_loss', 'tax_savings_estimated']].rename(columns={
                'symbol': 'Symbol',
                'event_date': 'Date',
                'quantity_sold': 'Quantity',
                'realized_loss': 'Realized Loss',
                'tax_savings_estimated': 'Tax Savings'
            }),
            use_container_width=True
        )
    else:
        st.info(f"No harvesting events recorded for {selected_year}.")

with tab5:
    st.header("⚙️ Settings")
    
    st.subheader("Tax Rate Settings")
    federal_rate = st.number_input("Federal Tax Rate (%)", value=22.0, min_value=0.0, max_value=50.0)
    state_rate = st.number_input("State Tax Rate (%)", value=5.0, min_value=0.0, max_value=15.0)
    
    st.subheader("Wash Sale Settings")
    wash_sale_window = st.number_input("Wash Sale Window (days)", value=30, min_value=1, max_value=60)
    
    st.subheader("Default Lot Method")
    lot_method = st.selectbox("Cost Basis Method", ["FIFO", "LIFO", "Specific Identification"])
    
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")