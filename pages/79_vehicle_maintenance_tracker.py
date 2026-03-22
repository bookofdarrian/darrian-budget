import streamlit as st
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Vehicle Maintenance Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
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
            CREATE TABLE IF NOT EXISTS vehicles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name VARCHAR(255) NOT NULL,
                make VARCHAR(100),
                model VARCHAR(100),
                year INTEGER,
                vin VARCHAR(17),
                license_plate VARCHAR(20),
                current_mileage INTEGER DEFAULT 0,
                purchase_date DATE,
                purchase_price DECIMAL(12,2),
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id SERIAL PRIMARY KEY,
                vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
                service_type VARCHAR(100) NOT NULL,
                service_date DATE NOT NULL,
                mileage_at_service INTEGER,
                cost DECIMAL(10,2) DEFAULT 0,
                shop_name VARCHAR(255),
                technician VARCHAR(100),
                parts_used TEXT,
                labor_hours DECIMAL(5,2),
                notes TEXT,
                receipt_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fuel_logs (
                id SERIAL PRIMARY KEY,
                vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
                fill_date DATE NOT NULL,
                mileage INTEGER NOT NULL,
                gallons DECIMAL(6,3) NOT NULL,
                price_per_gallon DECIMAL(5,3) NOT NULL,
                total_cost DECIMAL(8,2) NOT NULL,
                fuel_type VARCHAR(50) DEFAULT 'Regular',
                station_name VARCHAR(255),
                full_tank BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_schedules (
                id SERIAL PRIMARY KEY,
                vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
                service_type VARCHAR(100) NOT NULL,
                interval_miles INTEGER,
                interval_months INTEGER,
                last_service_date DATE,
                last_service_mileage INTEGER,
                estimated_cost DECIMAL(10,2),
                priority VARCHAR(20) DEFAULT 'medium',
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year INTEGER,
                vin TEXT,
                license_plate TEXT,
                current_mileage INTEGER DEFAULT 0,
                purchase_date TEXT,
                purchase_price REAL,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                service_type TEXT NOT NULL,
                service_date TEXT NOT NULL,
                mileage_at_service INTEGER,
                cost REAL DEFAULT 0,
                shop_name TEXT,
                technician TEXT,
                parts_used TEXT,
                labor_hours REAL,
                notes TEXT,
                receipt_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fuel_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                fill_date TEXT NOT NULL,
                mileage INTEGER NOT NULL,
                gallons REAL NOT NULL,
                price_per_gallon REAL NOT NULL,
                total_cost REAL NOT NULL,
                fuel_type TEXT DEFAULT 'Regular',
                station_name TEXT,
                full_tank INTEGER DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                service_type TEXT NOT NULL,
                interval_miles INTEGER,
                interval_months INTEGER,
                last_service_date TEXT,
                last_service_mileage INTEGER,
                estimated_cost REAL,
                priority TEXT DEFAULT 'medium',
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            )
        """)
    
    conn.commit()

_ensure_tables()

def get_vehicles(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM vehicles WHERE user_id = ? AND is_active = 1 ORDER BY name" if not USE_POSTGRES else "SELECT * FROM vehicles WHERE user_id = %s AND is_active = TRUE ORDER BY name", (user_id,))
    return cur.fetchall()

def add_vehicle(user_id, name, make, model, year, vin, license_plate, current_mileage, purchase_date, purchase_price, notes):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO vehicles (user_id, name, make, model, year, vin, license_plate, current_mileage, purchase_date, purchase_price, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (user_id, name, make, model, year, vin, license_plate, current_mileage, purchase_date, purchase_price, notes))
        result = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO vehicles (user_id, name, make, model, year, vin, license_plate, current_mileage, purchase_date, purchase_price, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, make, model, year, vin, license_plate, current_mileage, str(purchase_date) if purchase_date else None, purchase_price, notes))
        result = cur.lastrowid
    conn.commit()
    return result

def add_maintenance_record(vehicle_id, service_type, service_date, mileage, cost, shop_name, technician, parts_used, labor_hours, notes):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO maintenance_records (vehicle_id, service_type, service_date, mileage_at_service, cost, shop_name, technician, parts_used, labor_hours, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (vehicle_id, service_type, service_date, mileage, cost, shop_name, technician, parts_used, labor_hours, notes))
    else:
        cur.execute("""
            INSERT INTO maintenance_records (vehicle_id, service_type, service_date, mileage_at_service, cost, shop_name, technician, parts_used, labor_hours, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vehicle_id, service_type, str(service_date), mileage, cost, shop_name, technician, parts_used, labor_hours, notes))
    conn.commit()

def get_maintenance_records(vehicle_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM maintenance_records WHERE vehicle_id = ? ORDER BY service_date DESC" if not USE_POSTGRES else "SELECT * FROM maintenance_records WHERE vehicle_id = %s ORDER BY service_date DESC", (vehicle_id,))
    return cur.fetchall()

def add_fuel_log(vehicle_id, fill_date, mileage, gallons, price_per_gallon, total_cost, fuel_type, station_name, full_tank, notes):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO fuel_logs (vehicle_id, fill_date, mileage, gallons, price_per_gallon, total_cost, fuel_type, station_name, full_tank, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (vehicle_id, fill_date, mileage, gallons, price_per_gallon, total_cost, fuel_type, station_name, full_tank, notes))
    else:
        cur.execute("""
            INSERT INTO fuel_logs (vehicle_id, fill_date, mileage, gallons, price_per_gallon, total_cost, fuel_type, station_name, full_tank, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vehicle_id, str(fill_date), mileage, gallons, price_per_gallon, total_cost, fuel_type, station_name, 1 if full_tank else 0, notes))
    conn.commit()

def get_fuel_logs(vehicle_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM fuel_logs WHERE vehicle_id = ? ORDER BY fill_date DESC" if not USE_POSTGRES else "SELECT * FROM fuel_logs WHERE vehicle_id = %s ORDER BY fill_date DESC", (vehicle_id,))
    return cur.fetchall()

# Main UI
st.title("🚗 Vehicle Maintenance Tracker")

user_id = st.session_state.get("user_id", 1)

tab1, tab2, tab3, tab4 = st.tabs(["🚙 Vehicles", "🔧 Maintenance", "⛽ Fuel Logs", "📊 Reports"])

with tab1:
    st.subheader("My Vehicles")
    
    with st.expander("➕ Add New Vehicle"):
        with st.form("add_vehicle_form"):
            col1, col2 = st.columns(2)
            with col1:
                v_name = st.text_input("Vehicle Name*", placeholder="e.g., My Honda Civic")
                v_make = st.text_input("Make", placeholder="e.g., Honda")
                v_model = st.text_input("Model", placeholder="e.g., Civic")
                v_year = st.number_input("Year", min_value=1900, max_value=2030, value=2020)
            with col2:
                v_vin = st.text_input("VIN", max_chars=17)
                v_plate = st.text_input("License Plate")
                v_mileage = st.number_input("Current Mileage", min_value=0, value=0)
                v_purchase_date = st.date_input("Purchase Date", value=None)
            
            v_price = st.number_input("Purchase Price", min_value=0.0, value=0.0, format="%.2f")
            v_notes = st.text_area("Notes")
            
            if st.form_submit_button("Add Vehicle"):
                if v_name:
                    add_vehicle(user_id, v_name, v_make, v_model, v_year, v_vin, v_plate, v_mileage, v_purchase_date, v_price, v_notes)
                    st.success("Vehicle added successfully!")
                    st.rerun()
                else:
                    st.error("Vehicle name is required")
    
    vehicles = get_vehicles(user_id)
    if vehicles:
        for v in vehicles:
            with st.container():
                st.markdown(f"### {v[2]}")  # name
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Make/Model:** {v[3] or 'N/A'} {v[4] or ''}")
                    st.write(f"**Year:** {v[5] or 'N/A'}")
                with col2:
                    st.write(f"**VIN:** {v[6] or 'N/A'}")
                    st.write(f"**Plate:** {v[7] or 'N/A'}")
                with col3:
                    st.write(f"**Mileage:** {v[8]:,}" if v[8] else "**Mileage:** N/A")
                st.markdown("---")
    else:
        st.info("No vehicles added yet. Add your first vehicle above!")

with tab2:
    st.subheader("Maintenance Records")
    
    vehicles = get_vehicles(user_id)
    if vehicles:
        vehicle_options = {f"{v[2]} ({v[3]} {v[4]})": v[0] for v in vehicles}
        selected_vehicle = st.selectbox("Select Vehicle", options=list(vehicle_options.keys()), key="maint_vehicle")
        vehicle_id = vehicle_options[selected_vehicle]
        
        with st.expander("➕ Add Maintenance Record"):
            with st.form("add_maintenance_form"):
                col1, col2 = st.columns(2)
                with col1:
                    service_type = st.selectbox("Service Type", ["Oil Change", "Tire Rotation", "Brake Service", "Transmission Service", "Air Filter", "Spark Plugs", "Battery", "Other"])
                    service_date = st.date_input("Service Date", value=date.today())
                    mileage = st.number_input("Mileage at Service", min_value=0, value=0)
                with col2:
                    cost = st.number_input("Cost ($)", min_value=0.0, value=0.0, format="%.2f")
                    shop_name = st.text_input("Shop Name")
                    technician = st.text_input("Technician")
                
                parts_used = st.text_input("Parts Used")
                labor_hours = st.number_input("Labor Hours", min_value=0.0, value=0.0, format="%.2f")
                notes = st.text_area("Notes")
                
                if st.form_submit_button("Add Record"):
                    add_maintenance_record(vehicle_id, service_type, service_date, mileage, cost, shop_name, technician, parts_used, labor_hours, notes)
                    st.success("Maintenance record added!")
                    st.rerun()
        
        records = get_maintenance_records(vehicle_id)
        if records:
            for r in records:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{r[2]}**")  # service_type
                        st.write(f"Date: {r[3]}")
                    with col2:
                        st.write(f"Mileage: {r[4]:,}" if r[4] else "")
                        st.write(f"Shop: {r[6] or 'N/A'}")
                    with col3:
                        st.write(f"**${r[5]:.2f}**" if r[5] else "$0.00")
                    st.markdown("---")
        else:
            st.info("No maintenance records for this vehicle.")
    else:
        st.warning("Please add a vehicle first.")

with tab3:
    st.subheader("Fuel Logs")
    
    vehicles = get_vehicles(user_id)
    if vehicles:
        vehicle_options = {f"{v[2]} ({v[3]} {v[4]})": v[0] for v in vehicles}
        selected_vehicle = st.selectbox("Select Vehicle", options=list(vehicle_options.keys()), key="fuel_vehicle")
        vehicle_id = vehicle_options[selected_vehicle]
        
        with st.expander("➕ Add Fuel Log"):
            with st.form("add_fuel_form"):
                col1, col2 = st.columns(2)
                with col1:
                    fill_date = st.date_input("Fill Date", value=date.today())
                    mileage = st.number_input("Current Mileage", min_value=0, value=0)
                    gallons = st.number_input("Gallons", min_value=0.0, value=0.0, format="%.3f")
                with col2:
                    price_per_gallon = st.number_input("Price per Gallon ($)", min_value=0.0, value=0.0, format="%.3f")
                    fuel_type = st.selectbox("Fuel Type", ["Regular", "Mid-Grade", "Premium", "Diesel", "E85"])
                    station_name = st.text_input("Station Name")
                
                full_tank = st.checkbox("Full Tank", value=True)
                notes = st.text_area("Notes")
                
                total_cost = gallons * price_per_gallon
                st.write(f"**Total Cost: ${total_cost:.2f}**")
                
                if st.form_submit_button("Add Fuel Log"):
                    add_fuel_log(vehicle_id, fill_date, mileage, gallons, price_per_gallon, total_cost, fuel_type, station_name, full_tank, notes)
                    st.success("Fuel log added!")
                    st.rerun()
        
        fuel_logs = get_fuel_logs(vehicle_id)
        if fuel_logs:
            for f in fuel_logs:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{f[2]}**")  # fill_date
                        st.write(f"Station: {f[8] or 'N/A'}")
                    with col2:
                        st.write(f"Mileage: {f[3]:,}")
                        st.write(f"{f[4]:.3f} gal @ ${f[5]:.3f}")
                    with col3:
                        st.write(f"**${f[6]:.2f}**")
                    st.markdown("---")
        else:
            st.info("No fuel logs for this vehicle.")
    else:
        st.warning("Please add a vehicle first.")

with tab4:
    st.subheader("Reports & Analytics")
    
    vehicles = get_vehicles(user_id)
    if vehicles:
        vehicle_options = {f"{v[2]} ({v[3]} {v[4]})": v[0] for v in vehicles}
        selected_vehicle = st.selectbox("Select Vehicle", options=list(vehicle_options.keys()), key="report_vehicle")
        vehicle_id = vehicle_options[selected_vehicle]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Maintenance Summary")
            records = get_maintenance_records(vehicle_id)
            if records:
                total_cost = sum(r[5] or 0 for r in records)
                st.metric("Total Maintenance Cost", f"${total_cost:.2f}")
                st.metric("Total Records", len(records))
            else:
                st.info("No maintenance data available.")
        
        with col2:
            st.markdown("### Fuel Summary")
            fuel_logs = get_fuel_logs(vehicle_id)
            if fuel_logs:
                total_fuel_cost = sum(f[6] or 0 for f in fuel_logs)
                total_gallons = sum(f[4] or 0 for f in fuel_logs)
                st.metric("Total Fuel Cost", f"${total_fuel_cost:.2f}")
                st.metric("Total Gallons", f"{total_gallons:.2f}")
                
                # Calculate MPG if we have enough data
                if len(fuel_logs) >= 2:
                    sorted_logs = sorted(fuel_logs, key=lambda x: x[3])  # sort by mileage
                    first_mileage = sorted_logs[0][3]
                    last_mileage = sorted_logs[-1][3]
                    miles_driven = last_mileage - first_mileage
                    if total_gallons > 0 and miles_driven > 0:
                        avg_mpg = miles_driven / total_gallons
                        st.metric("Average MPG", f"{avg_mpg:.1f}")
            else:
                st.info("No fuel data available.")
    else:
        st.warning("Please add a vehicle first.")