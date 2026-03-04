import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv
import io
from anthropic import Anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Cash Flow Forecast", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar navigation
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
    """Create all required tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        # Cash flow forecasts table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cash_flow_forecasts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                forecast_date DATE NOT NULL,
                projected_date DATE NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT,
                amount DECIMAL(12,2) NOT NULL,
                flow_type VARCHAR(20) NOT NULL,
                confidence_score DECIMAL(5,2) DEFAULT 0.80,
                source VARCHAR(50),
                is_recurring BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Historical patterns table for ML-like predictions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS spending_patterns (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                category VARCHAR(100) NOT NULL,
                day_of_month INTEGER,
                day_of_week INTEGER,
                avg_amount DECIMAL(12,2),
                frequency VARCHAR(20),
                last_occurrence DATE,
                pattern_confidence DECIMAL(5,2) DEFAULT 0.75,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Income patterns table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS income_patterns (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                source VARCHAR(100) NOT NULL,
                expected_day INTEGER,
                expected_amount DECIMAL(12,2),
                frequency VARCHAR(20) DEFAULT 'monthly',
                confidence_score DECIMAL(5,2) DEFAULT 0.90,
                last_received DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Account balance snapshots
        cur.execute("""
            CREATE TABLE IF NOT EXISTS balance_snapshots (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                snapshot_date DATE NOT NULL,
                account_name VARCHAR(100) DEFAULT 'Main',
                balance DECIMAL(12,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Forecast alerts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forecast_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                alert_date DATE NOT NULL,
                alert_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) DEFAULT 'warning',
                message TEXT NOT NULL,
                projected_balance DECIMAL(12,2),
                is_acknowledged BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite version
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cash_flow_forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                forecast_date TEXT NOT NULL,
                projected_date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                flow_type TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.80,
                source TEXT,
                is_recurring INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS spending_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                day_of_month INTEGER,
                day_of_week INTEGER,
                avg_amount REAL,
                frequency TEXT,
                last_occurrence TEXT,
                pattern_confidence REAL DEFAULT 0.75,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS income_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                expected_day INTEGER,
                expected_amount REAL,
                frequency TEXT DEFAULT 'monthly',
                confidence_score REAL DEFAULT 0.90,
                last_received TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS balance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                snapshot_date TEXT NOT NULL,
                account_name TEXT DEFAULT 'Main',
                balance REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forecast_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                alert_date TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT DEFAULT 'warning',
                message TEXT NOT NULL,
                projected_balance REAL,
                is_acknowledged INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


def get_current_balance(user_id):
    """Get the most recent balance snapshot."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT balance FROM balance_snapshots 
            WHERE user_id = %s 
            ORDER BY snapshot_date DESC LIMIT 1
        """, (user_id,))
    else:
        cur.execute("""
            SELECT balance FROM balance_snapshots 
            WHERE user_id = ? 
            ORDER BY snapshot_date DESC LIMIT 1
        """, (user_id,))
    
    result = cur.fetchone()
    return float(result[0]) if result else 0.0


def save_balance_snapshot(user_id, balance, account_name="Main"):
    """Save a balance snapshot."""
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.now().date()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO balance_snapshots (user_id, snapshot_date, account_name, balance)
            VALUES (%s, %s, %s, %s)
        """, (user_id, today, account_name, balance))
    else:
        cur.execute("""
            INSERT INTO balance_snapshots (user_id, snapshot_date, account_name, balance)
            VALUES (?, ?, ?, ?)
        """, (user_id, today.isoformat(), account_name, balance))
    
    conn.commit()


def get_forecasts(user_id, start_date, end_date):
    """Get forecasts for a date range."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, projected_date, category, description, amount, flow_type, confidence_score, source, is_recurring
            FROM cash_flow_forecasts 
            WHERE user_id = %s AND projected_date BETWEEN %s AND %s
            ORDER BY projected_date
        """, (user_id, start_date, end_date))
    else:
        cur.execute("""
            SELECT id, projected_date, category, description, amount, flow_type, confidence_score, source, is_recurring
            FROM cash_flow_forecasts 
            WHERE user_id = ? AND projected_date BETWEEN ? AND ?
            ORDER BY projected_date
        """, (user_id, start_date.isoformat(), end_date.isoformat()))
    
    rows = cur.fetchall()
    return [
        {
            'id': r[0],
            'projected_date': r[1] if isinstance(r[1], datetime) else datetime.fromisoformat(r[1]) if isinstance(r[1], str) else r[1],
            'category': r[2],
            'description': r[3],
            'amount': float(r[4]),
            'flow_type': r[5],
            'confidence_score': float(r[6]) if r[6] else 0.8,
            'source': r[7],
            'is_recurring': bool(r[8])
        }
        for r in rows
    ]


def add_forecast(user_id, projected_date, category, description, amount, flow_type, confidence_score=0.8, source="manual", is_recurring=False):
    """Add a new forecast entry."""
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.now().date()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO cash_flow_forecasts 
            (user_id, forecast_date, projected_date, category, description, amount, flow_type, confidence_score, source, is_recurring)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, today, projected_date, category, description, amount, flow_type, confidence_score, source, is_recurring))
    else:
        cur.execute("""
            INSERT INTO cash_flow_forecasts 
            (user_id, forecast_date, projected_date, category, description, amount, flow_type, confidence_score, source, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, today.isoformat(), projected_date.isoformat() if isinstance(projected_date, datetime) else projected_date, 
              category, description, amount, flow_type, confidence_score, source, 1 if is_recurring else 0))
    
    conn.commit()


def delete_forecast(forecast_id):
    """Delete a forecast entry."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM cash_flow_forecasts WHERE id = %s", (forecast_id,))
    else:
        cur.execute("DELETE FROM cash_flow_forecasts WHERE id = ?", (forecast_id,))
    
    conn.commit()


def generate_forecast_chart(forecasts, current_balance, start_date, end_date):
    """Generate a cash flow forecast chart."""
    dates = []
    balances = []
    inflows = []
    outflows = []
    
    current_date = start_date
    running_balance = current_balance
    
    while current_date <= end_date:
        day_inflow = 0
        day_outflow = 0
        
        for f in forecasts:
            f_date = f['projected_date']
            if isinstance(f_date, str):
                f_date = datetime.fromisoformat(f_date).date()
            elif isinstance(f_date, datetime):
                f_date = f_date.date()
            
            if f_date == current_date:
                if f['flow_type'] == 'income':
                    day_inflow += f['amount'] * f['confidence_score']
                else:
                    day_outflow += f['amount'] * f['confidence_score']
        
        running_balance += day_inflow - day_outflow
        
        dates.append(current_date)
        balances.append(running_balance)
        inflows.append(day_inflow)
        outflows.append(day_outflow)
        
        current_date += timedelta(days=1)
    
    fig = go.Figure()
    
    # Balance line
    fig.add_trace(go.Scatter(
        x=dates,
        y=balances,
        mode='lines+markers',
        name='Projected Balance',
        line=dict(color='#2E86AB', width=3),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.1)'
    ))
    
    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Zero Balance")
    
    # Warning threshold
    fig.add_hline(y=500, line_dash="dot", line_color="orange", annotation_text="Warning Threshold")
    
    fig.update_layout(
        title="Cash Flow Forecast",
        xaxis_title="Date",
        yaxis_title="Balance ($)",
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig


def get_alerts(user_id):
    """Get active alerts for the user."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, alert_date, alert_type, severity, message, projected_balance, is_acknowledged
            FROM forecast_alerts 
            WHERE user_id = %s AND is_acknowledged = FALSE
            ORDER BY alert_date
        """, (user_id,))
    else:
        cur.execute("""
            SELECT id, alert_date, alert_type, severity, message, projected_balance, is_acknowledged
            FROM forecast_alerts 
            WHERE user_id = ? AND is_acknowledged = 0
            ORDER BY alert_date
        """, (user_id,))
    
    rows = cur.fetchall()
    return [
        {
            'id': r[0],
            'alert_date': r[1],
            'alert_type': r[2],
            'severity': r[3],
            'message': r[4],
            'projected_balance': float(r[5]) if r[5] else 0,
            'is_acknowledged': bool(r[6])
        }
        for r in rows
    ]


def acknowledge_alert(alert_id):
    """Mark an alert as acknowledged."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("UPDATE forecast_alerts SET is_acknowledged = TRUE WHERE id = %s", (alert_id,))
    else:
        cur.execute("UPDATE forecast_alerts SET is_acknowledged = 1 WHERE id = ?", (alert_id,))
    
    conn.commit()


# Initialize tables
_ensure_tables()

# Get user ID
user_id = st.session_state.get('user_id', 1)

# Main UI
st.title("💰 Cash Flow Forecast")
st.markdown("Predict and manage your future cash flow")

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Forecast", "➕ Add Entry", "⚙️ Settings", "🔔 Alerts"])

with tab1:
    # Date range selector
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        start_date = st.date_input("Start Date", datetime.now().date())
    
    with col2:
        end_date = st.date_input("End Date", datetime.now().date() + timedelta(days=30))
    
    with col3:
        current_balance = get_current_balance(user_id)
        new_balance = st.number_input("Current Balance ($)", value=current_balance, step=100.0)
        if st.button("Update Balance"):
            save_balance_snapshot(user_id, new_balance)
            st.success("Balance updated!")
            st.rerun()
    
    # Get forecasts
    forecasts = get_forecasts(user_id, start_date, end_date)
    
    if forecasts:
        # Display chart
        fig = generate_forecast_chart(forecasts, current_balance, start_date, end_date)
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary metrics
        total_income = sum(f['amount'] for f in forecasts if f['flow_type'] == 'income')
        total_expenses = sum(f['amount'] for f in forecasts if f['flow_type'] == 'expense')
        net_flow = total_income - total_expenses
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Balance", f"${current_balance:,.2f}")
        col2.metric("Projected Income", f"${total_income:,.2f}")
        col3.metric("Projected Expenses", f"${total_expenses:,.2f}")
        col4.metric("Net Cash Flow", f"${net_flow:,.2f}", delta=f"${net_flow:,.2f}")
        
        # Forecast table
        st.subheader("Forecast Details")
        df = pd.DataFrame(forecasts)
        df['projected_date'] = pd.to_datetime(df['projected_date']).dt.date
        df['amount'] = df['amount'].apply(lambda x: f"${x:,.2f}")
        df['confidence_score'] = df['confidence_score'].apply(lambda x: f"{x*100:.0f}%")
        
        st.dataframe(
            df[['projected_date', 'category', 'description', 'amount', 'flow_type', 'confidence_score']],
            use_container_width=True,
            hide_index=True
        )
        
        # Delete option
        st.subheader("Manage Entries")
        forecast_to_delete = st.selectbox(
            "Select entry to delete",
            options=[(f['id'], f"{f['projected_date']} - {f['category']} - ${f['amount']:.2f}") for f in forecasts],
            format_func=lambda x: x[1]
        )
        
        if st.button("Delete Selected", type="secondary"):
            delete_forecast(forecast_to_delete[0])
            st.success("Entry deleted!")
            st.rerun()
    else:
        st.info("No forecasts found for the selected date range. Add entries in the 'Add Entry' tab.")

with tab2:
    st.subheader("Add Forecast Entry")
    
    col1, col2 = st.columns(2)
    
    with col1:
        entry_date = st.date_input("Date", datetime.now().date() + timedelta(days=1), key="entry_date")
        category = st.selectbox("Category", [
            "Salary", "Freelance", "Investment", "Rent", "Utilities", 
            "Groceries", "Transportation", "Entertainment", "Healthcare",
            "Insurance", "Subscriptions", "Other Income", "Other Expense"
        ])
        flow_type = st.selectbox("Type", ["income", "expense"])
    
    with col2:
        amount = st.number_input("Amount ($)", min_value=0.0, step=10.0)
        confidence = st.slider("Confidence Score", 0.0, 1.0, 0.8, 0.05)
        is_recurring = st.checkbox("Recurring Entry")
    
    description = st.text_input("Description (optional)")
    
    if st.button("Add Entry", type="primary"):
        if amount > 0:
            add_forecast(user_id, entry_date, category, description, amount, flow_type, confidence, "manual", is_recurring)
            st.success("Forecast entry added!")
            st.rerun()
        else:
            st.error("Please enter a valid amount.")

with tab3:
    st.subheader("Forecast Settings")
    
    # Warning threshold
    warning_threshold = st.number_input(
        "Low Balance Warning Threshold ($)", 
        value=float(get_setting("forecast_warning_threshold") or 500),
        step=100.0
    )
    
    if st.button("Save Settings"):
        set_setting("forecast_warning_threshold", str(warning_threshold))
        st.success("Settings saved!")

with tab4:
    st.subheader("Active Alerts")
    
    alerts = get_alerts(user_id)
    
    if alerts:
        for alert in alerts:
            severity_color = "🔴" if alert['severity'] == 'critical' else "🟡"
            with st.expander(f"{severity_color} {alert['alert_type']} - {alert['alert_date']}"):
                st.write(alert['message'])
                if alert['projected_balance']:
                    st.write(f"Projected Balance: ${alert['projected_balance']:,.2f}")
                if st.button("Acknowledge", key=f"ack_{alert['id']}"):
                    acknowledge_alert(alert['id'])
                    st.rerun()
    else:
        st.success("No active alerts!")