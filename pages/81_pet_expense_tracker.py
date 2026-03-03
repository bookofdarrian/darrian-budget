import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Pet Expense Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                species VARCHAR(50) NOT NULL,
                breed VARCHAR(100),
                birth_date DATE,
                weight DECIMAL(10,2),
                microchip_id VARCHAR(50),
                photo_url TEXT,
                notes TEXT,
                monthly_budget DECIMAL(10,2) DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pet_expenses (
                id SERIAL PRIMARY KEY,
                pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(50),
                description TEXT,
                amount DECIMAL(10,2) NOT NULL,
                expense_date DATE NOT NULL,
                vendor VARCHAR(100),
                receipt_url TEXT,
                is_recurring BOOLEAN DEFAULT FALSE,
                recurring_frequency VARCHAR(20),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pet_vet_visits (
                id SERIAL PRIMARY KEY,
                pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                visit_date DATE NOT NULL,
                vet_name VARCHAR(100),
                clinic_name VARCHAR(100),
                visit_type VARCHAR(50) NOT NULL,
                diagnosis TEXT,
                treatment TEXT,
                weight_at_visit DECIMAL(10,2),
                total_cost DECIMAL(10,2),
                next_visit_date DATE,
                vaccinations_given TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pet_medications (
                id SERIAL PRIMARY KEY,
                pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                medication_name VARCHAR(100) NOT NULL,
                dosage VARCHAR(50),
                frequency VARCHAR(50),
                start_date DATE,
                end_date DATE,
                prescribing_vet VARCHAR(100),
                pharmacy VARCHAR(100),
                cost_per_refill DECIMAL(10,2),
                pills_per_refill INTEGER,
                pills_remaining INTEGER,
                last_refill_date DATE,
                next_refill_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pet_insurance (
                id SERIAL PRIMARY KEY,
                pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                provider VARCHAR(100) NOT NULL,
                policy_number VARCHAR(50),
                plan_name VARCHAR(100),
                monthly_premium DECIMAL(10,2),
                annual_deductible DECIMAL(10,2),
                reimbursement_rate INTEGER,
                annual_limit DECIMAL(10,2),
                coverage_start_date DATE,
                coverage_end_date DATE,
                waiting_period_days INTEGER,
                exclusions TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pet_insurance_claims (
                id SERIAL PRIMARY KEY,
                insurance_id INTEGER REFERENCES pet_insurance(id) ON DELETE CASCADE,
                pet_id INTEGER,
                user_id INTEGER NOT NULL,
                claim_date DATE NOT NULL,
                claim_amount DECIMAL(10,2) NOT NULL,
                reimbursed_amount DECIMAL(10,2),
                status VARCHAR(50) DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()

_ensure_tables()

st.title("🐾 Pet Expense Tracker")
st.markdown("Track all pet-related expenses, vet visits, medications, and insurance claims.")

# Placeholder for main app content
st.info("Pet Expense Tracker is ready to use. Add your pets and start tracking expenses!")