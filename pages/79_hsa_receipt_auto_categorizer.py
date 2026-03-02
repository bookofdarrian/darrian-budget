import streamlit as st
import os
import sys
import json
import re
from datetime import datetime, date
from decimal import Decimal
import tempfile
import base64
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="HSA Receipt Auto-Categorizer", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

IRS_502_ELIGIBLE_CATEGORIES = {
    "medical": {
        "name": "Medical Services",
        "description": "Doctor visits, surgery, hospital services",
        "keywords": ["doctor", "physician", "hospital", "clinic", "urgent care", "emergency", "surgery", "medical", "health", "treatment", "exam", "consultation"]
    },
    "dental": {
        "name": "Dental",
        "description": "Dental care, cleanings, procedures",
        "keywords": ["dental", "dentist", "orthodontist", "teeth", "oral", "crown", "filling", "root canal", "cleaning"]
    },
    "vision": {
        "name": "Vision",
        "description": "Eye exams, glasses, contacts, LASIK",
        "keywords": ["vision", "eye", "optical", "optometrist", "ophthalmologist", "glasses", "contacts", "lens", "lasik"]
    },
    "pharmacy": {
        "name": "Pharmacy/Prescriptions",
        "description": "Prescription medications",
        "keywords": ["pharmacy", "rx", "prescription", "cvs", "walgreens", "rite aid", "medication", "drug"]
    },
    "mental_health": {
        "name": "Mental Health",
        "description": "Therapy, counseling, psychiatry",
        "keywords": ["therapy", "counseling", "psychiatr", "psycholog", "mental health", "behavioral"]
    },
    "physical_therapy": {
        "name": "Physical Therapy",
        "description": "PT, chiropractic, rehabilitation",
        "keywords": ["physical therapy", "pt", "chiropract", "rehabilitation", "rehab", "massage therapy"]
    },
    "lab_tests": {
        "name": "Lab Tests & Diagnostics",
        "description": "Blood work, imaging, diagnostic tests",
        "keywords": ["lab", "laboratory", "blood", "test", "diagnostic", "x-ray", "mri", "ct scan", "imaging", "radiology"]
    },
    "medical_equipment": {
        "name": "Medical Equipment",
        "description": "Durable medical equipment, supplies",
        "keywords": ["equipment", "supplies", "bandage", "first aid", "brace", "crutch", "wheelchair", "monitor", "thermometer"]
    },
    "hearing": {
        "name": "Hearing",
        "description": "Hearing aids, audiology",
        "keywords": ["hearing", "audiology", "audiologist", "hearing aid"]
    },
    "fertility": {
        "name": "Fertility Treatment",
        "description": "IVF, fertility medications",
        "keywords": ["fertility", "ivf", "reproductive", "obgyn", "ob-gyn"]
    },
    "other_eligible": {
        "name": "Other HSA-Eligible",
        "description": "Other IRS 502 eligible expenses",
        "keywords": ["acupuncture", "ambulance", "insulin", "oxygen"]
    },
    "not_eligible": {
        "name": "Not HSA-Eligible",
        "description": "Cosmetic, general wellness, non-medical",
        "keywords": ["cosmetic", "gym", "vitamins", "supplements", "spa", "beauty", "whitening"]
    }
}

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                image_path TEXT,
                image_data BYTEA,
                ocr_text TEXT,
                vendor TEXT,
                amount DECIMAL(10, 2),
                receipt_date DATE,
                category TEXT,
                subcategory TEXT,
                is_hsa_eligible BOOLEAN DEFAULT FALSE,
                is_reimbursed BOOLEAN DEFAULT FALSE,
                reimbursed_date DATE,
                reimbursed_amount DECIMAL(10, 2),
                notes TEXT,
                confidence_score DECIMAL(3, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_balance_summary (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                year INTEGER,
                total_eligible DECIMAL(12, 2) DEFAULT 0,
                total_reimbursed DECIMAL(12, 2) DEFAULT 0,
                unreimbursed_balance DECIMAL(12, 2) DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_category_rules (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                vendor_pattern TEXT,
                category TEXT,
                is_eligible BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                image_path TEXT,
                image_data BLOB,
                ocr_text TEXT,
                vendor TEXT,
                amount DECIMAL(10, 2),
                receipt_date DATE,
                category TEXT,
                subcategory TEXT,
                is_hsa_eligible BOOLEAN DEFAULT 0,
                is_reimbursed BOOLEAN DEFAULT 0,
                reimbursed_date DATE,
                reimbursed_amount DECIMAL(10, 2),
                notes TEXT,
                confidence_score DECIMAL(3, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_balance_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                year INTEGER,
                total_eligible DECIMAL(12, 2) DEFAULT 0,
                total_reimbursed DECIMAL(12, 2) DEFAULT 0,
                unreimbursed_balance DECIMAL(12, 2) DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, year)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_category_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                vendor_pattern TEXT,
                category TEXT,
                is_eligible BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

def categorize_receipt(ocr_text, vendor=""):
    """Categorize receipt based on OCR text and vendor name."""
    text_lower = (ocr_text + " " + vendor).lower()
    
    best_match = None
    best_score = 0
    
    for cat_key, cat_info in IRS_502_ELIGIBLE_CATEGORIES.items():
        score = 0
        for keyword in cat_info["keywords"]:
            if keyword in text_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_match = cat_key
    
    if best_match is None:
        best_match = "other_eligible"
    
    is_eligible = best_match != "not_eligible"
    confidence = min(best_score / 3.0, 1.0) if best_score > 0 else 0.3
    
    return {
        "category": best_match,
        "category_name": IRS_502_ELIGIBLE_CATEGORIES[best_match]["name"],
        "is_eligible": is_eligible,
        "confidence": confidence
    }

def main():
    render_sidebar_brand()
    render_sidebar_user_widget()
    
    st.title("🏥 HSA Receipt Auto-Categorizer")
    st.markdown("Upload medical receipts to automatically categorize and track HSA-eligible expenses.")
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload Receipt", "📋 View Receipts", "📊 Summary"])
    
    with tab1:
        st.subheader("Upload a Receipt")
        
        uploaded_file = st.file_uploader("Choose a receipt image", type=["png", "jpg", "jpeg", "pdf"])
        
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Receipt", use_column_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                vendor = st.text_input("Vendor Name", "")
                amount = st.number_input("Amount ($)", min_value=0.0, step=0.01)
            with col2:
                receipt_date = st.date_input("Receipt Date", date.today())
                category = st.selectbox(
                    "Category",
                    options=list(IRS_502_ELIGIBLE_CATEGORIES.keys()),
                    format_func=lambda x: IRS_502_ELIGIBLE_CATEGORIES[x]["name"]
                )
            
            notes = st.text_area("Notes (optional)")
            
            if st.button("Save Receipt", type="primary"):
                conn = get_conn()
                cur = conn.cursor()
                
                image_data = uploaded_file.getvalue()
                is_eligible = category != "not_eligible"
                
                if USE_POSTGRES:
                    cur.execute("""
                        INSERT INTO hsa_receipts 
                        (image_data, vendor, amount, receipt_date, category, is_hsa_eligible, notes, confidence_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (image_data, vendor, amount, receipt_date, category, is_eligible, notes, 1.0))
                else:
                    cur.execute("""
                        INSERT INTO hsa_receipts 
                        (image_data, vendor, amount, receipt_date, category, is_hsa_eligible, notes, confidence_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (image_data, vendor, amount, receipt_date, category, is_eligible, notes, 1.0))
                
                conn.commit()
                st.success("Receipt saved successfully!")
    
    with tab2:
        st.subheader("Saved Receipts")
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, vendor, amount, receipt_date, category, is_hsa_eligible, is_reimbursed FROM hsa_receipts ORDER BY receipt_date DESC")
        receipts = cur.fetchall()
        
        if receipts:
            for receipt in receipts:
                rid, vendor, amount, rdate, category, eligible, reimbursed = receipt
                status = "✅ Eligible" if eligible else "❌ Not Eligible"
                reimb_status = "💰 Reimbursed" if reimbursed else "⏳ Pending"
                
                with st.expander(f"{vendor or 'Unknown'} - ${amount:.2f} ({rdate})"):
                    st.write(f"**Category:** {IRS_502_ELIGIBLE_CATEGORIES.get(category, {}).get('name', category)}")
                    st.write(f"**HSA Status:** {status}")
                    st.write(f"**Reimbursement:** {reimb_status}")
        else:
            st.info("No receipts saved yet. Upload your first receipt!")
    
    with tab3:
        st.subheader("HSA Summary")
        
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                SUM(CASE WHEN is_hsa_eligible THEN amount ELSE 0 END) as total_eligible,
                SUM(CASE WHEN is_reimbursed THEN reimbursed_amount ELSE 0 END) as total_reimbursed,
                COUNT(*) as total_receipts
            FROM hsa_receipts
        """)
        result = cur.fetchone()
        
        total_eligible = result[0] or 0
        total_reimbursed = result[1] or 0
        total_receipts = result[2] or 0
        unreimbursed = total_eligible - total_reimbursed
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Receipts", total_receipts)
        col2.metric("Total Eligible", f"${total_eligible:.2f}")
        col3.metric("Reimbursed", f"${total_reimbursed:.2f}")
        col4.metric("Unreimbursed", f"${unreimbursed:.2f}")
        
        with st.expander("ℹ️ HSA-Eligible Expenses (IRS Publication 502)"):
            st.markdown("""
            **Common HSA-Eligible Expenses:**
            - Doctor and hospital visits
            - Prescription medications
            - Dental care (cleanings, fillings, braces)
            - Vision care (exams, glasses, contacts)
            - Mental health services
            - Physical therapy
            - Medical equipment and supplies
            
            **Not Eligible:**
            - Cosmetic procedures
            - General vitamins/supplements
            - Gym memberships
            - Teeth whitening
            
            For a complete list, see [IRS Publication 502](https://www.irs.gov/publications/p502).
            """)

if __name__ == "__main__":
    main()