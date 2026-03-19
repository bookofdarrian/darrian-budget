import streamlit as st
import datetime
import json
from decimal import Decimal

st.set_page_config(page_title="Wedding Budget Planner", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_budgets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                wedding_name TEXT NOT NULL,
                wedding_date DATE,
                total_budget DECIMAL(12,2) DEFAULT 0,
                partner1_name TEXT,
                partner2_name TEXT,
                venue_location TEXT,
                guest_count_estimate INTEGER DEFAULT 100,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_categories (
                id SERIAL PRIMARY KEY,
                wedding_id INTEGER REFERENCES wedding_budgets(id) ON DELETE CASCADE,
                category_name TEXT NOT NULL,
                allocated_amount DECIMAL(12,2) DEFAULT 0,
                spent_amount DECIMAL(12,2) DEFAULT 0,
                allocation_percentage DECIMAL(5,2) DEFAULT 0,
                priority INTEGER DEFAULT 5,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_vendors (
                id SERIAL PRIMARY KEY,
                wedding_id INTEGER REFERENCES wedding_budgets(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES wedding_categories(id) ON DELETE SET NULL,
                vendor_name TEXT NOT NULL,
                vendor_type TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                website TEXT,
                contract_amount DECIMAL(12,2) DEFAULT 0,
                deposit_amount DECIMAL(12,2) DEFAULT 0,
                deposit_paid BOOLEAN DEFAULT FALSE,
                deposit_date DATE,
                contract_signed BOOLEAN DEFAULT FALSE,
                contract_date DATE,
                status TEXT DEFAULT 'researching',
                rating INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_payments (
                id SERIAL PRIMARY KEY,
                wedding_id INTEGER REFERENCES wedding_budgets(id) ON DELETE CASCADE,
                vendor_id INTEGER REFERENCES wedding_vendors(id) ON DELETE CASCADE,
                payment_name TEXT NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                due_date DATE,
                paid_date DATE,
                is_paid BOOLEAN DEFAULT FALSE,
                payment_method TEXT,
                confirmation_number TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_guests (
                id SERIAL PRIMARY KEY,
                wedding_id INTEGER REFERENCES wedding_budgets(id) ON DELETE CASCADE,
                guest_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                party_size INTEGER DEFAULT 1,
                relationship TEXT,
                side TEXT,
                rsvp_status TEXT DEFAULT 'pending',
                rsvp_date DATE,
                meal_preference TEXT,
                dietary_restrictions TEXT,
                table_number INTEGER,
                gift_received BOOLEAN DEFAULT FALSE,
                gift_description TEXT,
                thank_you_sent BOOLEAN DEFAULT FALSE,
                address TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                wedding_name TEXT NOT NULL,
                wedding_date DATE,
                total_budget REAL DEFAULT 0,
                partner1_name TEXT,
                partner2_name TEXT,
                venue_location TEXT,
                guest_count_estimate INTEGER DEFAULT 100,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wedding_id INTEGER,
                category_name TEXT NOT NULL,
                allocated_amount REAL DEFAULT 0,
                spent_amount REAL DEFAULT 0,
                allocation_percentage REAL DEFAULT 0,
                priority INTEGER DEFAULT 5,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wedding_id) REFERENCES wedding_budgets(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wedding_id INTEGER,
                category_id INTEGER,
                vendor_name TEXT NOT NULL,
                vendor_type TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                website TEXT,
                contract_amount REAL DEFAULT 0,
                deposit_amount REAL DEFAULT 0,
                deposit_paid INTEGER DEFAULT 0,
                deposit_date DATE,
                contract_signed INTEGER DEFAULT 0,
                contract_date DATE,
                status TEXT DEFAULT 'researching',
                rating INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wedding_id) REFERENCES wedding_budgets(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES wedding_categories(id) ON DELETE SET NULL
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wedding_id INTEGER,
                vendor_id INTEGER,
                payment_name TEXT NOT NULL,
                amount REAL NOT NULL,
                due_date DATE,
                paid_date DATE,
                is_paid INTEGER DEFAULT 0,
                payment_method TEXT,
                confirmation_number TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wedding_id) REFERENCES wedding_budgets(id) ON DELETE CASCADE,
                FOREIGN KEY (vendor_id) REFERENCES wedding_vendors(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wedding_guests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wedding_id INTEGER,
                guest_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                party_size INTEGER DEFAULT 1,
                relationship TEXT,
                side TEXT,
                rsvp_status TEXT DEFAULT 'pending',
                rsvp_date DATE,
                meal_preference TEXT,
                dietary_restrictions TEXT,
                table_number INTEGER,
                gift_received INTEGER DEFAULT 0,
                gift_description TEXT,
                thank_you_sent INTEGER DEFAULT 0,
                address TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wedding_id) REFERENCES wedding_budgets(id) ON DELETE CASCADE
            )
        """)
    
    conn.commit()

_ensure_tables()

# Main page content
st.title("💒 Wedding Budget Planner")

tabs = st.tabs(["📊 Overview", "💰 Budget", "👥 Vendors", "💳 Payments", "🎉 Guests"])

with tabs[0]:
    st.header("Overview")
    st.write("Welcome to your Wedding Budget Planner!")

with tabs[1]:
    st.header("Budget")
    st.write("Manage your wedding budget here.")

with tabs[2]:
    st.header("Vendors")
    st.write("Track your wedding vendors here.")

with tabs[3]:
    st.header("Payments")
    st.write("Manage payment schedules here.")

with tabs[4]:
    st.header("Guests")
    st.write("Manage your guest list here.")