import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
import calendar
import io
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Car/Mileage Tracker", page_icon="🍑", layout="wide")
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

# IRS Standard Mileage Rates
IRS_MILEAGE_RATES = {
    2024: Decimal("0.67"),
    2025: Decimal("0.70"),
    2026: Decimal("0.70"),
}

DEFAULT_BUSINESS_NAME = "404 Sole Archive"

def _ensure_tables():
    """Create mileage_logs table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                trip_date DATE NOT NULL,
                start_location TEXT NOT NULL,
                end_location TEXT NOT NULL,
                miles DECIMAL(10, 2) NOT NULL,
                purpose TEXT NOT NULL,
                business_name TEXT DEFAULT '404 Sole Archive',
                odometer_start DECIMAL(10, 1),
                odometer_end DECIMAL(10, 1),
                round_trip BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_logs_user_date 
            ON mileage_logs(user_id, trip_date)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_logs_business 
            ON mileage_logs(business_name)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                trip_date DATE NOT NULL,
                start_location TEXT NOT NULL,
                end_location TEXT NOT NULL,
                miles REAL NOT NULL,
                purpose TEXT NOT NULL,
                business_name TEXT DEFAULT '404 Sole Archive',
                odometer_start REAL,
                odometer_end REAL,
                round_trip INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_logs_user_date 
            ON mileage_logs(user_id, trip_date)
        """)
    
    conn.commit()
    conn.close()

def get_irs_rate(year: int) -> Decimal:
    """Get IRS mileage rate for given year."""
    return IRS_MILEAGE_RATES.get(year, Decimal("0.67"))

def calculate_deduction(miles: float, year: int) -> Decimal:
    """Calculate IRS deduction for given miles and year."""
    rate = get_irs_rate(year)
    return Decimal(str(miles)) * rate

def add_mileage_log(user_id: int, trip_date: date, start_location: str, 
                    end_location: str, miles: float, purpose: str,
                    business_name: str = DEFAULT_BUSINESS_NAME,
                    odometer_start: float = None, odometer_end: float = None,
                    round_trip: bool = False, notes: str = None) -> bool:
    """Add a new mileage log entry."""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO mileage_logs 
                (user_id, trip_date, start_location, end_location, miles, purpose, 
                 business_name, odometer_start, odometer_end, round_trip, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, trip_date, start_location, end_location, miles, purpose,
                  business_name, odometer_start, odometer_end, round_trip, notes))
        else:
            cur.execute("""
                INSERT INTO mileage_logs 
                (user_id, trip_date, start_location, end_location, miles, purpose, 
                 business_name, odometer_start, odometer_end, round_trip, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, trip_date, start_location, end_location, miles, purpose,
                  business_name, odometer_start, odometer_end, round_trip, notes))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding mileage log: {e}")
        return False
    finally:
        conn.close()

def get_mileage_logs(user_id: int, start_date: date = None, end_date: date = None):
    """Get mileage logs for a user, optionally filtered by date range."""
    conn = get_conn()
    cur = conn.cursor()
    
    query = "SELECT * FROM mileage_logs WHERE user_id = "
    params = [user_id]
    
    if USE_POSTGRES:
        query += "%s"
        if start_date:
            query += " AND trip_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND trip_date <= %s"
            params.append(end_date)
    else:
        query += "?"
        if start_date:
            query += " AND trip_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND trip_date <= ?"
            params.append(end_date)
    
    query += " ORDER BY trip_date DESC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def delete_mileage_log(log_id: int) -> bool:
    """Delete a mileage log entry."""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("DELETE FROM mileage_logs WHERE id = %s", (log_id,))
        else:
            cur.execute("DELETE FROM mileage_logs WHERE id = ?", (log_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting mileage log: {e}")
        return False
    finally:
        conn.close()

# Initialize tables
_ensure_tables()

# Main page content
st.title("🚗 Car/Mileage Tracker")
st.markdown("Track your business mileage for tax deductions.")

# Get current user
user_id = st.session_state.get("user_id", 1)

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["📝 Log Trip", "📊 View Logs", "📈 Reports"])

with tab1:
    st.subheader("Log a New Trip")
    
    col1, col2 = st.columns(2)
    
    with col1:
        trip_date = st.date_input("Trip Date", value=date.today())
        start_location = st.text_input("Start Location")
        end_location = st.text_input("End Location")
        miles = st.number_input("Miles", min_value=0.0, step=0.1)
    
    with col2:
        purpose = st.text_input("Business Purpose")
        business_name = st.text_input("Business Name", value=DEFAULT_BUSINESS_NAME)
        round_trip = st.checkbox("Round Trip (doubles miles)")
        notes = st.text_area("Notes (optional)")
    
    if st.button("Log Trip", type="primary"):
        if start_location and end_location and miles > 0 and purpose:
            actual_miles = miles * 2 if round_trip else miles
            if add_mileage_log(user_id, trip_date, start_location, end_location,
                              actual_miles, purpose, business_name, notes=notes,
                              round_trip=round_trip):
                st.success(f"Trip logged: {actual_miles} miles")
                st.rerun()
        else:
            st.warning("Please fill in all required fields.")

with tab2:
    st.subheader("Mileage Logs")
    
    logs = get_mileage_logs(user_id)
    
    if logs:
        df = pd.DataFrame(logs)
        st.dataframe(df[['trip_date', 'start_location', 'end_location', 'miles', 'purpose', 'business_name']])
        
        # Delete functionality
        log_ids = [log['id'] for log in logs]
        if log_ids:
            delete_id = st.selectbox("Select log to delete", log_ids)
            if st.button("Delete Selected Log"):
                if delete_mileage_log(delete_id):
                    st.success("Log deleted")
                    st.rerun()
    else:
        st.info("No mileage logs found. Start by logging a trip!")

with tab3:
    st.subheader("Mileage Reports")
    
    current_year = date.today().year
    selected_year = st.selectbox("Select Year", [2024, 2025, 2026], index=[2024, 2025, 2026].index(current_year) if current_year in [2024, 2025, 2026] else 0)
    
    year_start = date(selected_year, 1, 1)
    year_end = date(selected_year, 12, 31)
    
    year_logs = get_mileage_logs(user_id, year_start, year_end)
    
    if year_logs:
        total_miles = sum(log['miles'] for log in year_logs)
        deduction = calculate_deduction(total_miles, selected_year)
        rate = get_irs_rate(selected_year)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Miles", f"{total_miles:,.1f}")
        col2.metric("IRS Rate", f"${rate}/mile")
        col3.metric("Tax Deduction", f"${deduction:,.2f}")
        
        st.markdown("---")
        st.markdown(f"**{selected_year} Summary:** {len(year_logs)} trips logged with {total_miles:,.1f} total miles for a potential tax deduction of **${deduction:,.2f}**")
    else:
        st.info(f"No mileage logs found for {selected_year}.")