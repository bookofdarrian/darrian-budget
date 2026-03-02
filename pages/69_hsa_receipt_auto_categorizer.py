import streamlit as st
import os
import sys
import tempfile
import base64
from datetime import datetime, date
from decimal import Decimal
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="HSA Receipt Auto-Categorizer", page_icon="🍑", layout="wide")

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
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                merchant VARCHAR(255),
                amount DECIMAL(10, 2),
                category VARCHAR(100),
                is_eligible BOOLEAN DEFAULT FALSE,
                is_reimbursed BOOLEAN DEFAULT FALSE,
                reimbursed_date DATE,
                receipt_image_path TEXT,
                ocr_text TEXT,
                claude_classification JSONB,
                tax_year INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                merchant TEXT,
                amount REAL,
                category TEXT,
                is_eligible INTEGER DEFAULT 0,
                is_reimbursed INTEGER DEFAULT 0,
                reimbursed_date TEXT,
                receipt_image_path TEXT,
                ocr_text TEXT,
                claude_classification TEXT,
                tax_year INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()

_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

HSA_CATEGORIES = [
    "Medical - Doctor Visit",
    "Medical - Hospital",
    "Medical - Lab/Test",
    "Medical - Therapy",
    "Dental - Checkup",
    "Dental - Procedure",
    "Vision - Eye Exam",
    "Vision - Glasses/Contacts",
    "Vision - LASIK",
    "Prescription - Medication",
    "Prescription - Medical Equipment",
    "Mental Health - Therapy",
    "Mental Health - Psychiatry",
    "Chiropractic",
    "Acupuncture",
    "Physical Therapy",
    "First Aid/OTC Medical",
    "Other - HSA Eligible",
    "Not HSA Eligible"
]

ELIGIBLE_CATEGORIES = [cat for cat in HSA_CATEGORIES if cat != "Not HSA Eligible"]

def extract_text_from_image(image_bytes, filename):
    """Extract text from image using pytesseract OCR"""
    try:
        from PIL import Image
        import pytesseract
        import io
        
        image = Image.open(io.BytesIO(image_bytes))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        text = pytesseract.image_to_string(image)
        return text.strip()
    except ImportError:
        return "[OCR libraries not installed. Install pytesseract and Pillow for OCR functionality.]"
    except Exception as e:
        return f"[OCR Error: {str(e)}]"

def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF using pdf2image and pytesseract"""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        
        images = convert_from_bytes(pdf_bytes)
        text_parts = []
        
        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
        
        return "\n\n".join(text_parts).strip()
    except ImportError:
        return "[PDF OCR libraries not installed. Install pdf2image and pytesseract for PDF OCR functionality.]"
    except Exception as e:
        return f"[PDF OCR Error: {str(e)}]"

def classify_receipt_with_claude(ocr_text):
    """Use Claude to classify the receipt and extract details"""
    api_key = get_setting("anthropic_api_key")
    
    if not api_key:
        return {
            "merchant": "Unknown",
            "amount": 0.00,
            "category": "Other - HSA Eligible",
            "is_eligible": False,
            "confidence": 0.0,
            "reasoning": "No API key configured"
        }
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""Analyze this receipt text and extract the following information:
1. Merchant name
2. Total amount
3. Category (choose from: {', '.join(HSA_CATEGORIES)})
4. Whether this is HSA eligible (true/false)
5. Your confidence level (0.0-1.0)
6. Brief reasoning for your classification

Receipt text:
{ocr_text}

Respond in JSON format with keys: merchant, amount, category, is_eligible, confidence, reasoning"""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = json.loads(response.content[0].text)
        return result
    except Exception as e:
        return {
            "merchant": "Unknown",
            "amount": 0.00,
            "category": "Other - HSA Eligible",
            "is_eligible": False,
            "confidence": 0.0,
            "reasoning": f"Error: {str(e)}"
        }

def save_receipt(merchant, amount, category, is_eligible, ocr_text, classification, tax_year, notes):
    """Save receipt to database"""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO hsa_receipts (merchant, amount, category, is_eligible, ocr_text, claude_classification, tax_year, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (merchant, amount, category, is_eligible, ocr_text, json.dumps(classification), tax_year, notes))
    else:
        cur.execute("""
            INSERT INTO hsa_receipts (merchant, amount, category, is_eligible, ocr_text, claude_classification, tax_year, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (merchant, amount, category, 1 if is_eligible else 0, ocr_text, json.dumps(classification), tax_year, notes))
    
    conn.commit()
    cur.close()
    conn.close()

def get_receipts(tax_year=None):
    """Get all receipts, optionally filtered by tax year"""
    conn = get_conn()
    cur = conn.cursor()
    
    if tax_year:
        if USE_POSTGRES:
            cur.execute("SELECT * FROM hsa_receipts WHERE tax_year = %s ORDER BY upload_date DESC", (tax_year,))
        else:
            cur.execute("SELECT * FROM hsa_receipts WHERE tax_year = ? ORDER BY upload_date DESC", (tax_year,))
    else:
        cur.execute("SELECT * FROM hsa_receipts ORDER BY upload_date DESC")
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# Main UI
st.title("🍑 HSA Receipt Auto-Categorizer")
st.markdown("Upload medical receipts to automatically categorize and track HSA-eligible expenses.")

tab1, tab2, tab3 = st.tabs(["📤 Upload Receipt", "📋 View Receipts", "📊 Summary"])

with tab1:
    st.subheader("Upload a New Receipt")
    
    uploaded_file = st.file_uploader("Choose a receipt image or PDF", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    if uploaded_file:
        file_bytes = uploaded_file.read()
        
        # Display the uploaded file
        if uploaded_file.type == "application/pdf":
            st.info("PDF uploaded. Processing...")
            ocr_text = extract_text_from_pdf(file_bytes)
        else:
            st.image(file_bytes, caption="Uploaded Receipt", use_container_width=True)
            ocr_text = extract_text_from_image(file_bytes, uploaded_file.name)
        
        with st.expander("View Extracted Text"):
            st.text(ocr_text)
        
        if st.button("🤖 Classify with AI"):
            with st.spinner("Analyzing receipt..."):
                classification = classify_receipt_with_claude(ocr_text)
            
            st.session_state['classification'] = classification
            st.session_state['ocr_text'] = ocr_text
        
        if 'classification' in st.session_state:
            classification = st.session_state['classification']
            
            st.subheader("Classification Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                merchant = st.text_input("Merchant", value=classification.get('merchant', 'Unknown'))
                amount = st.number_input("Amount", value=float(classification.get('amount', 0.0)), min_value=0.0, step=0.01)
                tax_year = st.number_input("Tax Year", value=datetime.now().year, min_value=2000, max_value=2100)
            
            with col2:
                category = st.selectbox("Category", HSA_CATEGORIES, index=HSA_CATEGORIES.index(classification.get('category', 'Other - HSA Eligible')) if classification.get('category') in HSA_CATEGORIES else 0)
                is_eligible = st.checkbox("HSA Eligible", value=classification.get('is_eligible', False))
                confidence = classification.get('confidence', 0.0)
                st.metric("AI Confidence", f"{confidence:.0%}")
            
            notes = st.text_area("Notes", value=classification.get('reasoning', ''))
            
            if st.button("💾 Save Receipt"):
                save_receipt(merchant, amount, category, is_eligible, st.session_state.get('ocr_text', ''), classification, tax_year, notes)
                st.success("Receipt saved successfully!")
                del st.session_state['classification']
                if 'ocr_text' in st.session_state:
                    del st.session_state['ocr_text']

with tab2:
    st.subheader("Saved Receipts")
    
    year_filter = st.selectbox("Filter by Tax Year", [None, 2024, 2023, 2022, 2021], format_func=lambda x: "All Years" if x is None else str(x))
    
    receipts = get_receipts(year_filter)
    
    if receipts:
        for receipt in receipts:
            with st.expander(f"{receipt[2]} - ${receipt[3]:.2f} ({receipt[4]})"):
                st.write(f"**Date:** {receipt[1]}")
                st.write(f"**Category:** {receipt[4]}")
                st.write(f"**HSA Eligible:** {'✅' if receipt[5] else '❌'}")
                st.write(f"**Tax Year:** {receipt[11]}")
                if receipt[12]:
                    st.write(f"**Notes:** {receipt[12]}")
    else:
        st.info("No receipts found. Upload some receipts to get started!")

with tab3:
    st.subheader("HSA Expense Summary")
    
    summary_year = st.selectbox("Select Tax Year", [2024, 2023, 2022, 2021], key="summary_year")
    
    receipts = get_receipts(summary_year)
    
    if receipts:
        total_amount = sum(r[3] for r in receipts if r[3])
        eligible_amount = sum(r[3] for r in receipts if r[3] and r[5])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Receipts", len(receipts))
        with col2:
            st.metric("Total Amount", f"${total_amount:.2f}")
        with col3:
            st.metric("HSA Eligible", f"${eligible_amount:.2f}")
        
        # Category breakdown
        st.subheader("By Category")
        category_totals = {}
        for receipt in receipts:
            cat = receipt[4] or "Unknown"
            amount = receipt[3] or 0
            category_totals[cat] = category_totals.get(cat, 0) + amount
        
        for cat, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            st.write(f"**{cat}:** ${total:.2f}")
    else:
        st.info(f"No receipts found for {summary_year}.")