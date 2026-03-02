import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import io

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Car/Mileage Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

IRS_MILEAGE_RATE_2026 = 0.67
BUSINESS_NAME = "404 Sole Archive"


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_logs (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                purpose TEXT NOT NULL,
                start_odometer NUMERIC(10, 1) NOT NULL,
                end_odometer NUMERIC(10, 1) NOT NULL,
                miles NUMERIC(10, 1) NOT NULL,
                business_flag BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                purpose TEXT NOT NULL,
                start_odometer REAL NOT NULL,
                end_odometer REAL NOT NULL,
                miles REAL NOT NULL,
                business_flag INTEGER DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()


def calculate_deduction(miles: float, rate: float = IRS_MILEAGE_RATE_2026) -> float:
    return round(miles * rate, 2)


def add_mileage_log(log_date, purpose, start_odometer, end_odometer, business_flag, notes):
    miles = end_odometer - start_odometer
    if miles < 0:
        return False, "End odometer must be greater than start odometer"
    
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO mileage_logs (date, purpose, start_odometer, end_odometer, miles, business_flag, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (log_date, purpose, start_odometer, end_odometer, miles, business_flag, notes))
    else:
        cur.execute("""
            INSERT INTO mileage_logs (date, purpose, start_odometer, end_odometer, miles, business_flag, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(log_date), purpose, start_odometer, end_odometer, miles, 1 if business_flag else 0, notes))
    conn.commit()
    conn.close()
    return True, "Trip logged successfully"


def update_mileage_log(log_id, log_date, purpose, start_odometer, end_odometer, business_flag, notes):
    miles = end_odometer - start_odometer
    if miles < 0:
        return False, "End odometer must be greater than start odometer"
    
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            UPDATE mileage_logs 
            SET date = %s, purpose = %s, start_odometer = %s, end_odometer = %s, 
                miles = %s, business_flag = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (log_date, purpose, start_odometer, end_odometer, miles, business_flag, notes, log_id))
    else:
        cur.execute("""
            UPDATE mileage_logs 
            SET date = ?, purpose = ?, start_odometer = ?, end_odometer = ?, 
                miles = ?, business_flag = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (str(log_date), purpose, start_odometer, end_odometer, miles, 1 if business_flag else 0, notes, log_id))
    conn.commit()
    conn.close()
    return True, "Trip updated successfully"


def delete_mileage_log(log_id):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("DELETE FROM mileage_logs WHERE id = %s", (log_id,))
    else:
        cur.execute("DELETE FROM mileage_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()


def get_all_logs(year=None):
    conn = get_conn()
    cur = conn.cursor()
    if year:
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, date, purpose, start_odometer, end_odometer, miles, business_flag, notes
                FROM mileage_logs
                WHERE EXTRACT(YEAR FROM date) = %s
                ORDER BY date DESC
            """, (year,))
        else:
            cur.execute("""
                SELECT id, date, purpose, start_odometer, end_odometer, miles, business_flag, notes
                FROM mileage_logs
                WHERE strftime('%Y', date) = ?
                ORDER BY date DESC
            """, (str(year),))
    else:
        cur.execute("""
            SELECT id, date, purpose, start_odometer, end_odometer, miles, business_flag, notes
            FROM mileage_logs
            ORDER BY date DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_last_odometer():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT end_odometer FROM mileage_logs ORDER BY date DESC, id DESC LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0.0


def get_summary_stats(year=None):
    logs = get_all_logs(year)
    total_miles = sum(row[5] for row in logs)
    business_miles = sum(row[5] for row in logs if row[6])
    personal_miles = total_miles - business_miles
    deduction = calculate_deduction(business_miles)
    return {
        "total_miles": total_miles,
        "business_miles": business_miles,
        "personal_miles": personal_miles,
        "deduction": deduction,
        "trip_count": len(logs)
    }


# Ensure tables exist
_ensure_tables()

# Sidebar
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🚗 Car/Mileage Tracker")
st.markdown(f"**Business:** {BUSINESS_NAME} | **IRS Rate:** ${IRS_MILEAGE_RATE_2026}/mile")

# Year filter
current_year = datetime.now().year
years = list(range(current_year, current_year - 5, -1))
selected_year = st.selectbox("Filter by Year", [None] + years, format_func=lambda x: "All Years" if x is None else str(x))

# Summary stats
stats = get_summary_stats(selected_year)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Miles", f"{stats['total_miles']:.1f}")
with col2:
    st.metric("Business Miles", f"{stats['business_miles']:.1f}")
with col3:
    st.metric("Personal Miles", f"{stats['personal_miles']:.1f}")
with col4:
    st.metric("Tax Deduction", f"${stats['deduction']:.2f}")

st.divider()

# Add new trip
st.subheader("➕ Log New Trip")
with st.form("add_trip_form"):
    col1, col2 = st.columns(2)
    with col1:
        trip_date = st.date_input("Date", value=date.today())
        purpose = st.text_input("Purpose/Destination", placeholder="e.g., Post office, customer delivery")
    with col2:
        last_odo = get_last_odometer()
        start_odo = st.number_input("Start Odometer", value=float(last_odo), min_value=0.0, step=0.1)
        end_odo = st.number_input("End Odometer", value=float(last_odo), min_value=0.0, step=0.1)
    
    business_flag = st.checkbox("Business Trip", value=True)
    notes = st.text_area("Notes (optional)", placeholder="Additional details...")
    
    if st.form_submit_button("Log Trip", type="primary"):
        if not purpose:
            st.error("Please enter a purpose/destination")
        else:
            success, msg = add_mileage_log(trip_date, purpose, start_odo, end_odo, business_flag, notes)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

st.divider()

# Display logs
st.subheader("📋 Trip History")
logs = get_all_logs(selected_year)

if logs:
    df = pd.DataFrame(logs, columns=["ID", "Date", "Purpose", "Start Odo", "End Odo", "Miles", "Business", "Notes"])
    df["Business"] = df["Business"].apply(lambda x: "✅" if x else "❌")
    df["Deduction"] = df.apply(lambda row: f"${calculate_deduction(row['Miles']):.2f}" if row["Business"] == "✅" else "-", axis=1)
    
    st.dataframe(df[["Date", "Purpose", "Start Odo", "End Odo", "Miles", "Business", "Deduction", "Notes"]], 
                 use_container_width=True, hide_index=True)
    
    # Export option
    csv = df.to_csv(index=False)
    st.download_button("📥 Export to CSV", csv, "mileage_logs.csv", "text/csv")
    
    # Delete option
    st.subheader("🗑️ Delete Trip")
    delete_id = st.selectbox("Select trip to delete", df["ID"].tolist(), 
                              format_func=lambda x: f"ID {x}: {df[df['ID']==x]['Date'].values[0]} - {df[df['ID']==x]['Purpose'].values[0]}")
    if st.button("Delete Selected Trip", type="secondary"):
        delete_mileage_log(delete_id)
        st.success("Trip deleted")
        st.rerun()
else:
    st.info("No trips logged yet. Add your first trip above!")