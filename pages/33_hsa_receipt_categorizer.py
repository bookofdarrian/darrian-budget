import streamlit as st
import os
import sys
from datetime import datetime, date
from decimal import Decimal
import json
import tempfile
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="HSA Receipt Categorizer", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id SERIAL PRIMARY KEY,
                receipt_date DATE NOT NULL,
                vendor VARCHAR(255),
                amount DECIMAL(10,2) NOT NULL,
                category VARCHAR(100),
                is_hsa_eligible BOOLEAN DEFAULT FALSE,
                reimbursed BOOLEAN DEFAULT FALSE,
                reimbursed_date DATE,
                ocr_text TEXT,
                notes TEXT,
                file_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_contributions (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                contribution_amount DECIMAL(10,2) NOT NULL,
                employer_match DECIMAL(10,2) DEFAULT 0,
                contribution_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                is_eligible BOOLEAN DEFAULT TRUE,
                description TEXT
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_date DATE NOT NULL,
                vendor TEXT,
                amount REAL NOT NULL,
                category TEXT,
                is_hsa_eligible INTEGER DEFAULT 0,
                reimbursed INTEGER DEFAULT 0,
                reimbursed_date DATE,
                ocr_text TEXT,
                notes TEXT,
                file_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                contribution_amount REAL NOT NULL,
                employer_match REAL DEFAULT 0,
                contribution_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_eligible INTEGER DEFAULT 1,
                description TEXT
            )
        """)
    
    conn.commit()
    
    default_categories = [
        ("Doctor Visits", True, "Primary care, specialists, urgent care"),
        ("Prescriptions", True, "Prescription medications"),
        ("Dental", True, "Dental exams, cleanings, procedures"),
        ("Vision", True, "Eye exams, glasses, contacts"),
        ("Mental Health", True, "Therapy, counseling, psychiatry"),
        ("Lab Tests", True, "Blood work, imaging, diagnostics"),
        ("Medical Equipment", True, "CPAP, crutches, wheelchairs"),
        ("OTC Medicine", True, "Over-the-counter medications (with prescription)"),
        ("Hospital", True, "Hospital stays, surgeries, ER visits"),
        ("Physical Therapy", True, "PT, chiropractic, acupuncture"),
        ("Cosmetic", False, "Cosmetic procedures (not eligible)"),
        ("Gym Membership", False, "General fitness (not eligible)"),
        ("Other Medical", True, "Other qualifying medical expenses"),
        ("Non-Medical", False, "Non-medical expenses (not eligible)")
    ]
    
    for name, is_eligible, description in default_categories:
        try:
            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO hsa_categories (name, is_eligible, description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (name, is_eligible, description))
            else:
                cur.execute("""
                    INSERT OR IGNORE INTO hsa_categories (name, is_eligible, description)
                    VALUES (?, ?, ?)
                """, (name, is_eligible, description))
        except:
            pass
    
    conn.commit()
    conn.close()

_ensure_tables()