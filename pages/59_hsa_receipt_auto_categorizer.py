import streamlit as st
import os
import io
import base64
import json
import tempfile
from datetime import datetime, date
from decimal import Decimal
import pandas as pd

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="HSA Receipt Auto-Categorizer", page_icon="🍑", layout="wide")
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

# HSA-eligible expense categories
HSA_CATEGORIES = [
    "Medical - Doctor Visit",
    "Medical - Hospital",
    "Medical - Lab/Testing",
    "Medical - Surgery",
    "Dental - Checkup",
    "Dental - Procedure",
    "Vision - Eye Exam",
    "Vision - Glasses/Contacts",
    "Vision - LASIK",
    "Pharmacy - Prescription",
    "Pharmacy - OTC (HSA-eligible)",
    "Mental Health - Therapy",
    "Mental Health - Psychiatry",
    "Physical Therapy",
    "Chiropractic",
    "Acupuncture",
    "Medical Equipment/Supplies",
    "Hearing Aids",
    "Other HSA-Eligible",
    "Not HSA-Eligible"
]

def _ensure_tables():
    """Create HSA receipt tracking tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                image_data BYTEA,
                image_filename TEXT,
                ocr_text TEXT,
                category TEXT,
                amount DECIMAL(10, 2),
                expense_date DATE,
                vendor TEXT,
                description TEXT,
                is_hsa_eligible BOOLEAN DEFAULT TRUE,
                reimbursed BOOLEAN DEFAULT FALSE,
                reimbursed_date DATE,
                reimbursed_amount DECIMAL(10, 2),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_balance (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                year INTEGER NOT NULL,
                total_eligible DECIMAL(10, 2) DEFAULT 0,
                total_reimbursed DECIMAL(10, 2) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                annual_contribution_limit DECIMAL(10, 2) DEFAULT 4150.00,
                family_contribution_limit DECIMAL(10, 2) DEFAULT 8300.00,
                catch_up_contribution DECIMAL(10, 2) DEFAULT 1000.00,
                is_family_plan BOOLEAN DEFAULT FALSE,
                is_catch_up_eligible BOOLEAN DEFAULT FALSE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                image_data BLOB,
                image_filename TEXT,
                ocr_text TEXT,
                category TEXT,
                amount REAL,
                expense_date TEXT,
                vendor TEXT,
                description TEXT,
                is_hsa_eligible INTEGER DEFAULT 1,
                reimbursed INTEGER DEFAULT 0,
                reimbursed_date TEXT,
                reimbursed_amount REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_balance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                year INTEGER NOT NULL,
                total_eligible REAL DEFAULT 0,
                total_reimbursed REAL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                annual_contribution_limit REAL DEFAULT 4150.00,
                family_contribution_limit REAL DEFAULT 8300.00,
                catch_up_contribution REAL DEFAULT 1000.00,
                is_family_plan INTEGER DEFAULT 0,
                is_catch_up_eligible INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
    
    conn.commit()

def get_receipts(user_id=1, category_filter=None, reimbursed_filter=None):
    """Get all receipts with optional filters."""
    conn = get_conn()
    cur = conn.cursor()
    
    query = "SELECT * FROM hsa_receipts WHERE user_id = ?"
    params = [user_id]
    
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)
    
    if reimbursed_filter is not None:
        if USE_POSTGRES:
            query += " AND reimbursed = %s"
        else:
            query += " AND reimbursed = ?"
        params.append(1 if reimbursed_filter else 0)
    
    query += " ORDER BY expense_date DESC"
    
    if USE_POSTGRES:
        query = query.replace("?", "%s")
    
    cur.execute(query, params)
    return cur.fetchall()

def add_receipt(user_id, image_data, image_filename, ocr_text, category, amount, expense_date, vendor, description, is_hsa_eligible, notes):
    """Add a new receipt."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO hsa_receipts (user_id, image_data, image_filename, ocr_text, category, amount, expense_date, vendor, description, is_hsa_eligible, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, image_data, image_filename, ocr_text, category, amount, expense_date, vendor, description, is_hsa_eligible, notes))
        receipt_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO hsa_receipts (user_id, image_data, image_filename, ocr_text, category, amount, expense_date, vendor, description, is_hsa_eligible, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, image_data, image_filename, ocr_text, category, amount, expense_date, vendor, description, 1 if is_hsa_eligible else 0, notes))
        receipt_id = cur.lastrowid
    
    conn.commit()
    return receipt_id

# Initialize tables
_ensure_tables()

# Main page content
st.title("🏥 HSA Receipt Auto-Categorizer")
st.markdown("Upload and manage your HSA-eligible receipts.")

# Tabs for different functions
tab1, tab2, tab3 = st.tabs(["📤 Upload Receipt", "📋 View Receipts", "📊 Summary"])

with tab1:
    st.subheader("Upload New Receipt")
    
    uploaded_file = st.file_uploader("Choose a receipt image", type=["png", "jpg", "jpeg", "pdf"])
    
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Receipt", use_column_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            category = st.selectbox("Category", HSA_CATEGORIES)
            amount = st.number_input("Amount ($)", min_value=0.0, step=0.01)
            expense_date = st.date_input("Expense Date", value=date.today())
        
        with col2:
            vendor = st.text_input("Vendor/Provider")
            description = st.text_area("Description")
            is_hsa_eligible = st.checkbox("HSA Eligible", value=True)
        
        notes = st.text_area("Notes (optional)")
        
        if st.button("Save Receipt", type="primary"):
            image_data = uploaded_file.getvalue()
            receipt_id = add_receipt(
                user_id=1,
                image_data=image_data,
                image_filename=uploaded_file.name,
                ocr_text="",
                category=category,
                amount=amount,
                expense_date=expense_date,
                vendor=vendor,
                description=description,
                is_hsa_eligible=is_hsa_eligible,
                notes=notes
            )
            st.success(f"Receipt saved successfully! (ID: {receipt_id})")

with tab2:
    st.subheader("View Receipts")
    
    col1, col2 = st.columns(2)
    with col1:
        category_filter = st.selectbox("Filter by Category", ["All"] + HSA_CATEGORIES)
    with col2:
        reimbursed_filter = st.selectbox("Filter by Reimbursement Status", ["All", "Reimbursed", "Not Reimbursed"])
    
    # Apply filters
    cat_filter = None if category_filter == "All" else category_filter
    reimb_filter = None
    if reimbursed_filter == "Reimbursed":
        reimb_filter = True
    elif reimbursed_filter == "Not Reimbursed":
        reimb_filter = False
    
    receipts = get_receipts(user_id=1, category_filter=cat_filter, reimbursed_filter=reimb_filter)
    
    if receipts:
        for receipt in receipts:
            with st.expander(f"{receipt[7]} - ${receipt[6]} - {receipt[5]}"):
                st.write(f"**Category:** {receipt[5]}")
                st.write(f"**Amount:** ${receipt[6]}")
                st.write(f"**Date:** {receipt[7]}")
                st.write(f"**Vendor:** {receipt[8]}")
                st.write(f"**Description:** {receipt[9]}")
    else:
        st.info("No receipts found.")

with tab3:
    st.subheader("HSA Summary")
    
    receipts = get_receipts(user_id=1)
    
    if receipts:
        total_eligible = sum(r[6] for r in receipts if r[10])
        total_reimbursed = sum(r[13] or 0 for r in receipts if r[11])
        pending_reimbursement = total_eligible - total_reimbursed
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Eligible Expenses", f"${total_eligible:,.2f}")
        col2.metric("Total Reimbursed", f"${total_reimbursed:,.2f}")
        col3.metric("Pending Reimbursement", f"${pending_reimbursement:,.2f}")
    else:
        st.info("No receipts to summarize.")