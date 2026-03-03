import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Dividend Income Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

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


def _ensure_tables():
    """Create dividend tracking tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dividend_holdings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                ticker VARCHAR(20) NOT NULL,
                company_name VARCHAR(255),
                shares DECIMAL(18, 6) NOT NULL DEFAULT 0,
                cost_basis DECIMAL(18, 2) NOT NULL DEFAULT 0,
                dividend_yield DECIMAL(8, 4),
                annual_dividend_per_share DECIMAL(18, 6),
                payment_frequency VARCHAR(20) DEFAULT 'quarterly',
                drip_enabled BOOLEAN DEFAULT FALSE,
                sector VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dividend_payments (
                id SERIAL PRIMARY KEY,
                holding_id INTEGER NOT NULL REFERENCES dividend_holdings(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                payment_date DATE NOT NULL,
                amount DECIMAL(18, 2) NOT NULL,
                shares_at_payment DECIMAL(18, 6),
                dividend_per_share DECIMAL(18, 6),
                reinvested BOOLEAN DEFAULT FALSE,
                shares_purchased DECIMAL(18, 6),
                purchase_price DECIMAL(18, 4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividend_holdings_user 
            ON dividend_holdings(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividend_payments_user 
            ON dividend_payments(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividend_payments_date 
            ON dividend_payments(payment_date)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dividend_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                company_name TEXT,
                shares REAL NOT NULL DEFAULT 0,
                cost_basis REAL NOT NULL DEFAULT 0,
                dividend_yield REAL,
                annual_dividend_per_share REAL,
                payment_frequency TEXT DEFAULT 'quarterly',
                drip_enabled INTEGER DEFAULT 0,
                sector TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dividend_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holding_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                shares_at_payment REAL,
                dividend_per_share REAL,
                reinvested INTEGER DEFAULT 0,
                shares_purchased REAL,
                purchase_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (holding_id) REFERENCES dividend_holdings(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividend_holdings_user 
            ON dividend_holdings(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividend_payments_user 
            ON dividend_payments(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_dividend_payments_date 
            ON dividend_payments(payment_date)
        """)
    
    conn.commit()


def get_user_id():
    """Get the current user ID from session state."""
    return st.session_state.get("user_id", 1)


def get_holdings(user_id):
    """Get all dividend holdings for a user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, ticker, company_name, shares, cost_basis, dividend_yield,
               annual_dividend_per_share, payment_frequency, drip_enabled, sector, notes
        FROM dividend_holdings
        WHERE user_id = ?
        ORDER BY ticker
    """.replace("?", "%s" if USE_POSTGRES else "?"), (user_id,))
    rows = cur.fetchall()
    return rows


def add_holding(user_id, ticker, company_name, shares, cost_basis, dividend_yield,
                annual_dividend_per_share, payment_frequency, drip_enabled, sector, notes):
    """Add a new dividend holding."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO dividend_holdings 
        (user_id, ticker, company_name, shares, cost_basis, dividend_yield,
         annual_dividend_per_share, payment_frequency, drip_enabled, sector, notes)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (user_id, ticker, company_name, shares, cost_basis, dividend_yield,
          annual_dividend_per_share, payment_frequency, drip_enabled, sector, notes))
    conn.commit()


def update_holding(holding_id, ticker, company_name, shares, cost_basis, dividend_yield,
                   annual_dividend_per_share, payment_frequency, drip_enabled, sector, notes):
    """Update an existing dividend holding."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        UPDATE dividend_holdings
        SET ticker = {placeholder}, company_name = {placeholder}, shares = {placeholder},
            cost_basis = {placeholder}, dividend_yield = {placeholder},
            annual_dividend_per_share = {placeholder}, payment_frequency = {placeholder},
            drip_enabled = {placeholder}, sector = {placeholder}, notes = {placeholder},
            updated_at = CURRENT_TIMESTAMP
        WHERE id = {placeholder}
    """, (ticker, company_name, shares, cost_basis, dividend_yield,
          annual_dividend_per_share, payment_frequency, drip_enabled, sector, notes, holding_id))
    conn.commit()


def delete_holding(holding_id):
    """Delete a dividend holding."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM dividend_holdings WHERE id = {placeholder}", (holding_id,))
    conn.commit()


def add_payment(holding_id, user_id, payment_date, amount, shares_at_payment,
                dividend_per_share, reinvested, shares_purchased, purchase_price):
    """Add a new dividend payment."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO dividend_payments
        (holding_id, user_id, payment_date, amount, shares_at_payment,
         dividend_per_share, reinvested, shares_purchased, purchase_price)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (holding_id, user_id, payment_date, amount, shares_at_payment,
          dividend_per_share, reinvested, shares_purchased, purchase_price))
    conn.commit()


def get_payments(user_id, start_date=None, end_date=None):
    """Get dividend payments for a user within a date range."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    
    query = """
        SELECT dp.id, dp.holding_id, dh.ticker, dh.company_name, dp.payment_date,
               dp.amount, dp.shares_at_payment, dp.dividend_per_share,
               dp.reinvested, dp.shares_purchased, dp.purchase_price
        FROM dividend_payments dp
        JOIN dividend_holdings dh ON dp.holding_id = dh.id
        WHERE dp.user_id = {placeholder}
    """.replace("{placeholder}", placeholder)
    
    params = [user_id]
    
    if start_date:
        query += f" AND dp.payment_date >= {placeholder}"
        params.append(start_date)
    
    if end_date:
        query += f" AND dp.payment_date <= {placeholder}"
        params.append(end_date)
    
    query += " ORDER BY dp.payment_date DESC"
    
    cur.execute(query, params)
    return cur.fetchall()


def get_monthly_summary(user_id, year):
    """Get monthly dividend summary for a year."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT EXTRACT(MONTH FROM payment_date) as month, SUM(amount) as total
            FROM dividend_payments
            WHERE user_id = {placeholder}
            AND EXTRACT(YEAR FROM payment_date) = {placeholder}
            GROUP BY EXTRACT(MONTH FROM payment_date)
            ORDER BY month
        """, (user_id, year))
    else:
        cur.execute(f"""
            SELECT CAST(strftime('%m', payment_date) AS INTEGER) as month, SUM(amount) as total
            FROM dividend_payments
            WHERE user_id = {placeholder}
            AND strftime('%Y', payment_date) = {placeholder}
            GROUP BY strftime('%m', payment_date)
            ORDER BY month
        """, (user_id, str(year)))
    
    return cur.fetchall()


# Initialize tables
_ensure_tables()

# Main content
st.title("💰 Dividend Income Tracker")

user_id = get_user_id()

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Holdings", "💵 Payments", "📅 Calendar"])

with tab1:
    st.subheader("Dividend Dashboard")
    
    holdings = get_holdings(user_id)
    
    if holdings:
        # Calculate totals
        total_value = sum(float(h[3]) * float(h[4]) / float(h[3]) if h[3] else 0 for h in holdings)
        total_annual_income = sum(float(h[3]) * float(h[6]) if h[6] else 0 for h in holdings)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Holdings", len(holdings))
        
        with col2:
            st.metric("Total Cost Basis", f"${sum(float(h[4]) for h in holdings):,.2f}")
        
        with col3:
            st.metric("Est. Annual Income", f"${total_annual_income:,.2f}")
        
        with col4:
            avg_yield = (total_annual_income / sum(float(h[4]) for h in holdings) * 100) if holdings else 0
            st.metric("Avg. Yield", f"{avg_yield:.2f}%")
        
        # Monthly summary chart
        st.subheader("Monthly Dividend Income")
        current_year = datetime.now().year
        monthly_data = get_monthly_summary(user_id, current_year)
        
        if monthly_data:
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            monthly_dict = {int(m[0]): float(m[1]) for m in monthly_data}
            
            chart_data = pd.DataFrame({
                "Month": month_names,
                "Dividends": [monthly_dict.get(i+1, 0) for i in range(12)]
            })
            
            st.bar_chart(chart_data.set_index("Month"))
        else:
            st.info("No dividend payments recorded for this year yet.")
    else:
        st.info("No holdings yet. Add your first dividend stock in the Holdings tab!")

with tab2:
    st.subheader("Manage Holdings")
    
    # Add new holding form
    with st.expander("➕ Add New Holding"):
        with st.form("add_holding_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                ticker = st.text_input("Ticker Symbol", max_chars=20).upper()
                company_name = st.text_input("Company Name")
                shares = st.number_input("Number of Shares", min_value=0.0, step=0.01)
                cost_basis = st.number_input("Total Cost Basis ($)", min_value=0.0, step=0.01)
            
            with col2:
                dividend_yield = st.number_input("Dividend Yield (%)", min_value=0.0, max_value=100.0, step=0.01)
                annual_div = st.number_input("Annual Dividend per Share ($)", min_value=0.0, step=0.01)
                payment_freq = st.selectbox("Payment Frequency", 
                                           ["quarterly", "monthly", "semi-annual", "annual"])
                drip = st.checkbox("DRIP Enabled")
            
            sector = st.selectbox("Sector", ["Technology", "Healthcare", "Financial", "Consumer", 
                                             "Energy", "Utilities", "Real Estate", "Industrial", 
                                             "Materials", "Communication", "Other"])
            notes = st.text_area("Notes")
            
            if st.form_submit_button("Add Holding"):
                if ticker and shares > 0:
                    add_holding(user_id, ticker, company_name, shares, cost_basis, 
                               dividend_yield, annual_div, payment_freq, drip, sector, notes)
                    st.success(f"Added {ticker} to your holdings!")
                    st.rerun()
                else:
                    st.error("Please enter a ticker and number of shares.")
    
    # Display existing holdings
    holdings = get_holdings(user_id)
    
    if holdings:
        for h in holdings:
            holding_id, ticker, company_name, shares, cost_basis, div_yield, annual_div, freq, drip, sector, notes = h
            
            with st.expander(f"{ticker} - {company_name or 'N/A'}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Shares:** {shares}")
                    st.write(f"**Cost Basis:** ${cost_basis:,.2f}")
                
                with col2:
                    st.write(f"**Yield:** {div_yield or 0:.2f}%")
                    st.write(f"**Annual Div/Share:** ${annual_div or 0:.4f}")
                
                with col3:
                    st.write(f"**Frequency:** {freq}")
                    st.write(f"**DRIP:** {'Yes' if drip else 'No'}")
                
                st.write(f"**Sector:** {sector}")
                if notes:
                    st.write(f"**Notes:** {notes}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Delete", key=f"del_{holding_id}"):
                        delete_holding(holding_id)
                        st.success(f"Deleted {ticker}")
                        st.rerun()

with tab3:
    st.subheader("Dividend Payments")
    
    holdings = get_holdings(user_id)
    
    if holdings:
        # Add payment form
        with st.expander("➕ Record New Payment"):
            with st.form("add_payment_form"):
                holding_options = {f"{h[1]} - {h[2] or 'N/A'}": h[0] for h in holdings}
                selected_holding = st.selectbox("Select Holding", list(holding_options.keys()))
                
                col1, col2 = st.columns(2)
                
                with col1:
                    payment_date = st.date_input("Payment Date", value=date.today())
                    amount = st.number_input("Total Amount ($)", min_value=0.0, step=0.01)
                    shares_at_payment = st.number_input("Shares at Payment", min_value=0.0, step=0.01)
                
                with col2:
                    div_per_share = st.number_input("Dividend per Share ($)", min_value=0.0, step=0.0001)
                    reinvested = st.checkbox("Reinvested (DRIP)")
                    
                    if reinvested:
                        shares_purchased = st.number_input("Shares Purchased", min_value=0.0, step=0.0001)
                        purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, step=0.01)
                    else:
                        shares_purchased = None
                        purchase_price = None
                
                if st.form_submit_button("Record Payment"):
                    holding_id = holding_options[selected_holding]
                    add_payment(holding_id, user_id, payment_date, amount, shares_at_payment,
                               div_per_share, reinvested, shares_purchased, purchase_price)
                    st.success("Payment recorded!")
                    st.rerun()
        
        # Display recent payments
        st.subheader("Recent Payments")
        payments = get_payments(user_id)
        
        if payments:
            df = pd.DataFrame(payments, columns=[
                "ID", "Holding ID", "Ticker", "Company", "Date", "Amount",
                "Shares", "Div/Share", "Reinvested", "Shares Bought", "Price"
            ])
            
            df = df[["Date", "Ticker", "Amount", "Shares", "Div/Share", "Reinvested"]]
            df["Amount"] = df["Amount"].apply(lambda x: f"${x:,.2f}")
            df["Reinvested"] = df["Reinvested"].apply(lambda x: "Yes" if x else "No")
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No payments recorded yet.")
    else:
        st.info("Add holdings first before recording payments.")

with tab4:
    st.subheader("Dividend Calendar")
    
    holdings = get_holdings(user_id)
    
    if holdings:
        st.write("**Expected Payment Schedule:**")
        
        for h in holdings:
            ticker = h[1]
            freq = h[7]
            annual_div = h[6] or 0
            shares = h[3]
            
            expected_per_payment = (annual_div * shares) / (4 if freq == "quarterly" else 
                                                           12 if freq == "monthly" else
                                                           2 if freq == "semi-annual" else 1)
            
            st.write(f"**{ticker}**: {freq.capitalize()} - Est. ${expected_per_payment:,.2f} per payment")
    else:
        st.info("Add holdings to see your dividend calendar.")