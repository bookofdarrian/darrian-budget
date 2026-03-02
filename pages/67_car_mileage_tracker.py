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

# Constants
IRS_MILEAGE_RATE = Decimal("0.67")  # 2024 IRS standard mileage rate
BUSINESS_NAME = "404 Sole Archive"

def _ensure_tables():
    """Create mileage_trips table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_trips (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                trip_date DATE NOT NULL,
                purpose TEXT NOT NULL,
                start_location TEXT NOT NULL,
                end_location TEXT NOT NULL,
                miles DECIMAL(10, 2) NOT NULL,
                business_use_pct INTEGER DEFAULT 100,
                notes TEXT,
                vehicle_name TEXT,
                odometer_start DECIMAL(10, 1),
                odometer_end DECIMAL(10, 1),
                linked_expense_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster date queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_trips_date 
            ON mileage_trips(trip_date)
        """)
        
        # Create vehicles table for tracking multiple vehicles
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_vehicles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year INTEGER,
                license_plate TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                trip_date DATE NOT NULL,
                purpose TEXT NOT NULL,
                start_location TEXT NOT NULL,
                end_location TEXT NOT NULL,
                miles REAL NOT NULL,
                business_use_pct INTEGER DEFAULT 100,
                notes TEXT,
                vehicle_name TEXT,
                odometer_start REAL,
                odometer_end REAL,
                linked_expense_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year INTEGER,
                license_plate TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

def get_user_id():
    """Get current user ID from session."""
    return st.session_state.get("user_id", 1)

def calculate_deduction(miles: Decimal, business_use_pct: int = 100) -> Decimal:
    """Calculate IRS mileage deduction at $0.67/mile."""
    business_miles = miles * (Decimal(business_use_pct) / Decimal(100))
    return business_miles * IRS_MILEAGE_RATE

def add_trip(trip_date, purpose, start_location, end_location, miles, 
             business_use_pct=100, notes=None, vehicle_name=None,
             odometer_start=None, odometer_end=None, linked_expense_id=None):
    """Add a new mileage trip."""
    conn = get_conn()
    cur = conn.cursor()
    user_id = get_user_id()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        INSERT INTO mileage_trips 
        (user_id, trip_date, purpose, start_location, end_location, miles, 
         business_use_pct, notes, vehicle_name, odometer_start, odometer_end, linked_expense_id)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder},
                {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (user_id, trip_date, purpose, start_location, end_location, miles,
          business_use_pct, notes, vehicle_name, odometer_start, odometer_end, linked_expense_id))
    
    conn.commit()
    conn.close()

def get_trips(start_date=None, end_date=None):
    """Get all trips, optionally filtered by date range."""
    conn = get_conn()
    cur = conn.cursor()
    user_id = get_user_id()
    placeholder = "%s" if USE_POSTGRES else "?"
    
    query = f"SELECT * FROM mileage_trips WHERE user_id = {placeholder}"
    params = [user_id]
    
    if start_date:
        query += f" AND trip_date >= {placeholder}"
        params.append(start_date)
    if end_date:
        query += f" AND trip_date <= {placeholder}"
        params.append(end_date)
    
    query += " ORDER BY trip_date DESC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    
    return [dict(zip(columns, row)) for row in rows]

def delete_trip(trip_id):
    """Delete a trip by ID."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"DELETE FROM mileage_trips WHERE id = {placeholder}", (trip_id,))
    conn.commit()
    conn.close()

def update_trip(trip_id, **kwargs):
    """Update a trip."""
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    
    set_clause = ", ".join([f"{k} = {placeholder}" for k in kwargs.keys()])
    values = list(kwargs.values()) + [trip_id]
    
    cur.execute(f"UPDATE mileage_trips SET {set_clause} WHERE id = {placeholder}", values)
    conn.commit()
    conn.close()

# Initialize tables
_ensure_tables()

# Main UI
st.title("🚗 Car/Mileage Tracker")
st.markdown(f"**IRS Standard Mileage Rate:** ${IRS_MILEAGE_RATE}/mile (2024)")

# Tabs
tab1, tab2, tab3 = st.tabs(["📝 Log Trip", "📊 Trip History", "📈 Reports"])

with tab1:
    st.subheader("Log New Trip")
    
    col1, col2 = st.columns(2)
    
    with col1:
        trip_date = st.date_input("Trip Date", value=date.today())
        purpose = st.text_input("Purpose", placeholder="e.g., Shipping packages, Inventory pickup")
        start_location = st.text_input("Start Location", placeholder="e.g., Home")
        end_location = st.text_input("End Location", placeholder="e.g., Post Office")
    
    with col2:
        miles = st.number_input("Miles", min_value=0.0, step=0.1)
        business_use_pct = st.slider("Business Use %", 0, 100, 100)
        vehicle_name = st.text_input("Vehicle (optional)")
        notes = st.text_area("Notes (optional)")
    
    if st.button("Log Trip", type="primary"):
        if purpose and start_location and end_location and miles > 0:
            add_trip(trip_date, purpose, start_location, end_location, miles,
                    business_use_pct, notes, vehicle_name)
            st.success("Trip logged successfully!")
            st.rerun()
        else:
            st.error("Please fill in all required fields.")

with tab2:
    st.subheader("Trip History")
    
    trips = get_trips()
    
    if trips:
        for trip in trips:
            deduction = calculate_deduction(Decimal(str(trip['miles'])), trip['business_use_pct'])
            with st.expander(f"{trip['trip_date']} - {trip['purpose']} ({trip['miles']} mi)"):
                st.write(f"**From:** {trip['start_location']} → **To:** {trip['end_location']}")
                st.write(f"**Business Use:** {trip['business_use_pct']}%")
                st.write(f"**Deduction:** ${deduction:.2f}")
                if trip['notes']:
                    st.write(f"**Notes:** {trip['notes']}")
                if st.button("Delete", key=f"del_{trip['id']}"):
                    delete_trip(trip['id'])
                    st.rerun()
    else:
        st.info("No trips logged yet.")

with tab3:
    st.subheader("Mileage Reports")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date(date.today().year, 1, 1), key="report_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="report_end")
    
    trips = get_trips(start_date, end_date)
    
    if trips:
        total_miles = sum(Decimal(str(t['miles'])) for t in trips)
        total_deduction = sum(calculate_deduction(Decimal(str(t['miles'])), t['business_use_pct']) for t in trips)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Trips", len(trips))
        col2.metric("Total Miles", f"{total_miles:.1f}")
        col3.metric("Total Deduction", f"${total_deduction:.2f}")
        
        # Create DataFrame for display
        df = pd.DataFrame(trips)
        if not df.empty:
            df['deduction'] = df.apply(
                lambda row: float(calculate_deduction(Decimal(str(row['miles'])), row['business_use_pct'])), 
                axis=1
            )
            st.dataframe(df[['trip_date', 'purpose', 'start_location', 'end_location', 'miles', 'business_use_pct', 'deduction']])
    else:
        st.info("No trips found for the selected date range.")