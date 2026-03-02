import streamlit as st
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
import io

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Car Mileage Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

IRS_MILEAGE_RATE_2024 = Decimal("0.67")
IRS_MILEAGE_RATE_2025 = Decimal("0.70")
IRS_MILEAGE_RATE_2026 = Decimal("0.70")

BUSINESS_PURPOSES = [
    "Client Meeting",
    "Inventory Pickup",
    "Shipping/Drop-off",
    "Trade Show/Event",
    "Photography/Content",
    "Bank/Financial",
    "Supply Run",
    "Consignment Drop-off",
    "Authentication Service",
    "Other Business"
]

DEFAULT_BUSINESS = "404 Sole Archive"


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_trips (
                id SERIAL PRIMARY KEY,
                trip_date DATE NOT NULL,
                purpose VARCHAR(255) NOT NULL,
                start_location VARCHAR(500) NOT NULL,
                end_location VARCHAR(500) NOT NULL,
                miles DECIMAL(10, 2) NOT NULL,
                business_name VARCHAR(255) DEFAULT '404 Sole Archive',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_trips_date ON mileage_trips(trip_date)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_trips_business ON mileage_trips(business_name)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mileage_trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_date DATE NOT NULL,
                purpose VARCHAR(255) NOT NULL,
                start_location VARCHAR(500) NOT NULL,
                end_location VARCHAR(500) NOT NULL,
                miles DECIMAL(10, 2) NOT NULL,
                business_name VARCHAR(255) DEFAULT '404 Sole Archive',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_trips_date ON mileage_trips(trip_date)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mileage_trips_business ON mileage_trips(business_name)
        """)
    
    conn.commit()
    conn.close()


def get_irs_rate_for_year(year: int) -> Decimal:
    rates = {
        2024: Decimal("0.67"),
        2025: Decimal("0.70"),
        2026: Decimal("0.70"),
    }
    return rates.get(year, Decimal("0.70"))


def calculate_deduction(miles: Decimal, year: int = None) -> Decimal:
    if year is None:
        year = datetime.now().year
    rate = get_irs_rate_for_year(year)
    return Decimal(str(miles)) * rate


def add_trip(trip_date, purpose, start_location, end_location, miles, business_name=DEFAULT_BUSINESS, notes=""):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO mileage_trips (trip_date, purpose, start_location, end_location, miles, business_name, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (trip_date, purpose, start_location, end_location, miles, business_name, notes))
        trip_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO mileage_trips (trip_date, purpose, start_location, end_location, miles, business_name, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (trip_date, purpose, start_location, end_location, miles, business_name, notes))
        trip_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return trip_id


def update_trip(trip_id, trip_date, purpose, start_location, end_location, miles, business_name, notes):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            UPDATE mileage_trips
            SET trip_date = %s, purpose = %s, start_location = %s, end_location = %s,
                miles = %s, business_name = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (trip_date, purpose, start_location, end_location, miles, business_name, notes, trip_id))
    else:
        cur.execute("""
            UPDATE mileage_trips
            SET trip_date = ?, purpose = ?, start_location = ?, end_location = ?,
                miles = ?, business_name = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (trip_date, purpose, start_location, end_location, miles, business_name, notes, trip_id))
    
    conn.commit()
    conn.close()