import streamlit as st
import os
import io
import re
from datetime import datetime, date
from decimal import Decimal
from PIL import Image
import pytesseract
from anthropic import Anthropic

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

# Constants
HSA_CATEGORIES = [
    "Medical",
    "Dental",
    "Vision",
    "Pharmacy",
    "Mental Health",
    "Physical Therapy",
    "Lab/Diagnostic",
    "Medical Equipment",
    "Other HSA-Eligible"
]

UPLOADS_DIR = "uploads/hsa_receipts"
os.makedirs(UPLOADS_DIR, exist_ok=True)


def _ensure_tables():
    """Create HSA receipts table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                image_path TEXT,
                ocr_text TEXT,
                category VARCHAR(100),
                vendor VARCHAR(255),
                amount DECIMAL(10, 2),
                receipt_date DATE,
                reimbursed BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                image_path TEXT,
                ocr_text TEXT,
                category VARCHAR(100),
                vendor VARCHAR(255),
                amount DECIMAL(10, 2),
                receipt_date DATE,
                reimbursed BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from receipt image using OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Use pytesseract for OCR
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        st.error(f"OCR extraction failed: {str(e)}")
        return ""


def classify_receipt_with_claude(ocr_text: str) -> dict:
    """Use Claude AI to classify the receipt and extract details."""
    api_key = get_setting("anthropic_api_key")
    
    if not api_key:
        return {
            "category": "Other HSA-Eligible",
            "vendor": "Unknown",
            "amount": 0.00,
            "date": date.today().isoformat(),
            "confidence": "low",
            "error": "No API key configured"
        }
    
    try:
        client = Anthropic(api_key=api_key)
        
        prompt = f"""Analyze this medical receipt OCR text and extract the following information. 
Return ONLY a JSON object with these fields (no markdown, no explanation):

{{
    "category": "one of: Medical, Dental, Vision, Pharmacy, Mental Health, Physical Therapy, Lab/Diagnostic, Medical Equipment, Other HSA-Eligible",
    "vendor": "name of the medical provider or pharmacy",
    "amount": numeric value of total amount paid (just the number, no $ sign),
    "date": "YYYY-MM-DD format of the service/purchase date",
    "confidence": "high, medium, or low based on how clear the receipt text is"
}}

Receipt OCR Text:
{ocr_text}

If any field cannot be determined, use reasonable defaults:
- category: "Other HSA-Eligible"
- vendor: "Unknown Provider"
- amount: 0.00
- date: today's date
- confidence: "low"
"""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Parse JSON response
        import json
        # Clean up potential markdown formatting
        if response_text.startswith("```"):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        st.warning(f"Claude classification error: {str(e)}")
        return {
            "category": "Other HSA-Eligible",
            "vendor": "Unknown",
            "amount": 0.00,
            "date": date.today().isoformat(),
            "confidence": "low",
            "error": str(e)
        }


def save_receipt(user_id: int, image_path: str, ocr_text: str, category: str, 
                 vendor: str, amount: float, receipt_date: date, notes: str = "") -> int:
    """Save a new HSA receipt to the database."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO hsa_receipts (user_id, image_path, ocr_text, category, vendor, amount, receipt_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, image_path, ocr_text, category, vendor, amount, receipt_date, notes))
        receipt_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO hsa_receipts (user_id, image_path, ocr_text, category, vendor, amount, receipt_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, image_path, ocr_text, category, vendor, amount, receipt_date, notes))
        receipt_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return receipt_id


def get_all_receipts(user_id: int, year: int = None) -> list:
    """Get all receipts for a user, optionally filtered by year."""
    conn = get_conn()
    cur = conn.cursor()
    
    if year:
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, image_path, ocr_text, category, vendor, amount, receipt_date, reimbursed, notes, created_at
                FROM hsa_receipts
                WHERE user_id = %s AND EXTRACT(YEAR FROM receipt_date) = %s
                ORDER BY receipt_date DESC
            """, (user_id, year))
        else:
            cur.execute("""
                SELECT id, image_path, ocr_text, category, vendor, amount, receipt_date, reimbursed, notes, created_at
                FROM hsa_receipts
                WHERE user_id = ? AND strftime('%Y', receipt_date) = ?
                ORDER BY receipt_date DESC
            """, (user_id, str(year)))
    else:
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, image_path, ocr_text, category, vendor, amount, receipt_date, reimbursed, notes, created_at
                FROM hsa_receipts
                WHERE user_id = %s
                ORDER BY receipt_date DESC
            """, (user_id,))
        else:
            cur.execute("""
                SELECT id, image_path, ocr_text, category, vendor, amount, receipt_date, reimbursed, notes, created_at
                FROM hsa_receipts
                WHERE user_id = ?
                ORDER BY receipt_date DESC
            """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    receipts = []
    for row in rows:
        receipts.append({
            "id": row[0],
            "image_path": row[1],
            "ocr_text": row[2],
            "category": row[3],
            "vendor": row[4],
            "amount": float(row[5]) if row[5] else 0.0,
            "receipt_date": row[6],
            "reimbursed": bool(row[7]),
            "notes": row[8],
            "created_at": row[9]
        })
    
    return receipts


def update_reimbursement_status(receipt_id: int, reimbursed: bool):
    """Update the reimbursement status of a receipt."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            UPDATE hsa_receipts SET reimbursed = %s WHERE id = %s
        """, (reimbursed, receipt_id))
    else:
        cur.execute("""
            UPDATE hsa_receipts SET reimbursed = ? WHERE id = ?
        """, (1 if reimbursed else 0, receipt_id))
    
    conn.commit()
    conn.close()


def update_receipt(receipt_id: int, category: str, vendor: str, amount: float, 
                   receipt_date: date, notes: str):
    """Update receipt details."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            UPDATE hsa_receipts 
            SET category = %s, vendor = %s, amount = %s, receipt_date = %s, notes = %s
            WHERE id = %s
        """, (category, vendor, amount, receipt_date, notes, receipt_id))
    else:
        cur.execute("""
            UPDATE hsa_receipts 
            SET category = ?, vendor = ?, amount = ?, receipt_date = ?, notes = ?
            WHERE id = ?
        """, (category, vendor, amount, receipt_date, notes, receipt_id))
    
    conn.commit()
    conn.close()


def delete_receipt(receipt_id: int):
    """Delete a receipt from the database."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM hsa_receipts WHERE id = %s", (receipt_id,))
    else:
        cur.execute("DELETE FROM hsa_receipts WHERE id = ?", (receipt_id,))
    
    conn.commit()
    conn.close()


def get_summary_stats(user_id: int, year: int) -> dict:
    """Get summary statistics for HSA receipts."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        # Total eligible expenses
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM hsa_receipts
            WHERE user_id = %s AND EXTRACT(YEAR FROM receipt_date) = %s
        """, (user_id, year))
        total_eligible = float(cur.fetchone()[0])
        
        # Reimbursed amount
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM hsa_receipts
            WHERE user_id = %s AND EXTRACT(YEAR FROM receipt_date) = %s AND reimbursed = TRUE
        """, (user_id, year))
        total_reimbursed = float(cur.fetchone()[0])
        
        # By category
        cur.execute("""
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM hsa_receipts
            WHERE user_id = %s AND EXTRACT(YEAR FROM receipt_date) = %s
            GROUP BY category
            ORDER BY total DESC
        """, (user_id, year))
        by_category = cur.fetchall()
    else:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM hsa_receipts
            WHERE user_id = ? AND strftime('%Y', receipt_date) = ?
        """, (user_id, str(year)))
        total_eligible = float(cur.fetchone()[0])
        
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM hsa_receipts
            WHERE user_id = ? AND strftime('%Y', receipt_date) = ? AND reimbursed = 1
        """, (user_id, str(year)))
        total_reimbursed = float(cur.fetchone()[0])
        
        cur.execute("""
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM hsa_receipts
            WHERE user_id = ? AND strftime('%Y', receipt_date) = ?
            GROUP BY category
            ORDER BY total DESC
        """, (user_id, str(year)))
        by_category = cur.fetchall()
    
    conn.close()
    
    return {
        "total_eligible": total_eligible,
        "total_reimbursed": total_reimbursed,
        "unreimbursed_balance": total_eligible - total_reimbursed,
        "by_category": [{"category": row[0], "total": float(row[1]), "count": row[2]} for row in by_category]
    }


# Initialize tables
_ensure_tables()

# Get user ID from session
user_id = st.session_state.get("user_id", 1)

# Page header
st.title("🏥 HSA Receipt Auto-Categorizer")
st.markdown("Upload medical receipts for automatic OCR extraction and AI-powered categorization. Track unreimbursed HSA-eligible expenses.")

# Tabs for different views
tab_upload, tab_receipts, tab_summary = st.tabs(["📤 Upload Receipt", "📋 All Receipts", "📊 Annual Summary"])

# Upload Receipt Tab
with tab_upload:
    st.subheader("Upload New Receipt")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload receipt image",
            type=["png", "jpg", "jpeg", "gif", "bmp"],
            help="Supported formats: PNG, JPG, JPEG, GIF, BMP"
        )
        
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Receipt", use_container_width=True)
            
            if st.button("🔍 Extract & Classify", type="primary", use_container_width=True):
                with st.spinner("Extracting text from receipt..."):
                    image_bytes = uploaded_file.getvalue()
                    ocr_text = extract_text_from_image(image_bytes)
                    
                    if ocr_text:
                        st.session_state["ocr_text"] = ocr_text
                        st.session_state["image_bytes"] = image_bytes
                        st.session_state["filename"] = uploaded_file.name
                        
                        with st.spinner("Classifying receipt with AI..."):
                            classification = classify_receipt_with_claude(ocr_text)
                            st.session_state["classification"] = classification
                        
                        st.success("✅ Receipt processed successfully!")
                        st.rerun()
                    else:
                        st.error("Could not extract text from receipt. Please try a clearer image.")
    
    with col2:
        if "ocr_text" in st.session_state and st.session_state["ocr_text"]:
            st.markdown("### 📝 Extracted Text")
            with st.expander("View OCR Text", expanded=False):
                st.text_area("OCR Output", st.session_state["ocr_text"], height=200, disabled=True)
            
            classification = st.session_state.get("classification", {})
            
            st.markdown("### 🏷️ Classification Results")
            
            confidence = classification.get("confidence", "unknown")
            confidence_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "⚪")
            st.info(f"AI Confidence: {confidence_color} {confidence.upper()}")
            
            with st.form("save_receipt_form"):
                category = st.selectbox(
                    "Category",
                    HSA_CATEGORIES,
                    index=HSA_CATEGORIES.index(classification.get("category", "Other HSA-Eligible")) 
                          if classification.get("category") in HSA_CATEGORIES else len(HSA_CATEGORIES) - 1
                )
                
                vendor = st.text_input("Vendor/Provider", value=classification.get("vendor", ""))
                
                amount = st.number_input(
                    "Amount ($)",
                    min_value=0.0,
                    value=float(classification.get("amount", 0.0)),
                    step=0.01,
                    format="%.2f"
                )
                
                try:
                    default_date = datetime.strptime(classification.get("date", date.today().isoformat()), "%Y-%m-%d").date()
                except:
                    default_date = date.today()
                
                receipt_date = st.date_input("Receipt Date", value=default_date)
                
                notes = st.text_area("Notes (optional)", placeholder="Any additional notes about this expense...")
                
                submit = st.form_submit_button("💾 Save Receipt", type="primary", use_container_width=True)
                
                if submit:
                    if not vendor:
                        st.error("Please enter a vendor name.")
                    elif amount <= 0:
                        st.error("Please enter a valid amount greater than $0.")
                    else:
                        # Save image to disk
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{timestamp}_{st.session_state['filename']}"
                        image_path = os.path.join(UPLOADS_DIR, filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(st.session_state["image_bytes"])
                        
                        # Save to database
                        receipt_id = save_receipt(
                            user_id=user_id,
                            image_path=image_path,
                            ocr_text=st.session_state["ocr_text"],
                            category=category,
                            vendor=vendor,
                            amount=amount,
                            receipt_date=receipt_date,
                            notes=notes
                        )
                        
                        # Clear session state
                        for key in ["ocr_text", "image_bytes", "filename", "classification"]:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        st.success(f"✅ Receipt saved successfully! (ID: {receipt_id})")
                        st.balloons()
                        st.rerun()
        else:
            st.info("👆 Upload a receipt image to get started")
            
            st.markdown("### How it works")
            st.markdown("""
            1. **Upload** your medical receipt (image)
            2. **OCR** extracts text from the receipt
            3. **AI Classification** identifies:
               - Expense category
               - Vendor/provider name
               - Amount paid
               - Date of service
            4. **Review & Save** the receipt to your records
            5. **Track** unreimbursed balances over time
            """)

# All Receipts Tab
with tab_receipts:
    st.subheader("All HSA Receipts")
    
    # Filter options
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        current_year = date.today().year
        years = list(range(current_year, current_year - 5, -1))
        selected_year = st.selectbox("Filter by Year", ["All Years"] + years)
    
    with col2:
        filter_reimbursed = st.selectbox("Reimbursement Status", ["All", "Unreimbursed Only", "Reimbursed Only"])
    
    # Get receipts
    if selected_year == "All Years":
        receipts = get_all_receipts(user_id)
    else:
        receipts = get_all_receipts(user_id, int(selected_year))
    
    # Apply reimbursement filter
    if filter_reimbursed == "Unreimbursed Only":
        receipts = [r for r in receipts if not r["reimbursed"]]
    elif filter_reimbursed == "Reimbursed Only":
        receipts = [r for r in receipts if r["reimbursed"]]
    
    if not receipts:
        st.info("📭 No receipts found. Upload your first receipt to get started!")
    else:
        # Summary metrics
        total_amount = sum(r["amount"] for r in receipts)
        unreimbursed = sum(r["amount"] for r in receipts if not r["reimbursed"])
        reimbursed = sum(r["amount"] for r in receipts if r["reimbursed"])
        
        metric_cols = st.columns(4)
        metric_cols[0].metric("Total Receipts", len(receipts))
        metric_cols[1].metric("Total Amount", f"${total_amount:,.2f}")
        metric_cols[2].metric("Unreimbursed", f"${unreimbursed:,.2f}")
        metric_cols[3].metric("Reimbursed", f"${reimbursed:,.2f}")
        
        st.markdown("---")
        
        # Display receipts
        for receipt in receipts:
            with st.expander(
                f"{'✅' if receipt['reimbursed'] else '⏳'} {receipt['vendor']} — ${receipt['amount']:.2f} — {receipt['receipt_date']}",
                expanded=False
            ):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if receipt["image_path"] and os.path.exists(receipt["image_path"]):
                        st.image(receipt["image_path"], caption="Receipt Image", use_container_width=True)
                    else:
                        st.info("📷 No image available")
                
                with col2:
                    st.markdown(f"**Category:** {receipt['category']}")
                    st.markdown(f"**Vendor:** {receipt['vendor']}")
                    st.markdown(f"**Amount:** ${receipt['amount']:.2f}")
                    st.markdown(f"**Date:** {receipt['receipt_date']}")
                    st.markdown(f"**Status:** {'✅ Reimbursed' if receipt['reimbursed'] else '⏳ Unreimbursed'}")
                    
                    if receipt["notes"]:
                        st.markdown(f"**Notes:** {receipt['notes']}")
                    
                    # Action buttons
                    action_cols = st.columns(3)
                    
                    with action_cols[0]:
                        if receipt["reimbursed"]:
                            if st.button("Mark Unreimbursed", key=f"unreimb_{receipt['id']}"):
                                update_reimbursement_status(receipt["id"], False)
                                st.success("Marked as unreimbursed")
                                st.rerun()
                        else:
                            if st.button("Mark Reimbursed ✓", key=f"reimb_{receipt['id']}", type="primary"):
                                update_reimbursement_status(receipt["id"], True)
                                st.success("Marked as reimbursed")
                                st.rerun()
                    
                    with action_cols[1]:
                        if st.button("✏️ Edit", key=f"edit_{receipt['id']}"):
                            st.session_state[f"editing_{receipt['id']}"] = True
                            st.rerun()
                    
                    with action_cols[2]:
                        if st.button("🗑️ Delete", key=f"del_{receipt['id']}"):
                            st.session_state[f"confirm_delete_{receipt['id']}"] = True
                            st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"editing_{receipt['id']}", False):
                        st.markdown("---")
                        st.markdown("### Edit Receipt")
                        with st.form(f"edit_form_{receipt['id']}"):
                            edit_category = st.selectbox(
                                "Category",
                                HSA_CATEGORIES,
                                index=HSA_CATEGORIES.index(receipt['category']) if receipt['category'] in HSA_CATEGORIES else 0,
                                key=f"edit_cat_{receipt['id']}"
                            )
                            edit_vendor = st.text_input("Vendor", value=receipt['vendor'], key=f"edit_vendor_{receipt['id']}")
                            edit_amount = st.number_input("Amount", value=receipt['amount'], min_value=0.0, step=0.01, key=f"edit_amount_{receipt['id']}")
                            
                            try:
                                edit_date_val = receipt['receipt_date'] if isinstance(receipt['receipt_date'], date) else datetime.strptime(str(receipt['receipt_date']), "%Y-%m-%d").date()
                            except:
                                edit_date_val = date.today()
                            
                            edit_date = st.date_input("Date", value=edit_date_val, key=f"edit_date_{receipt['id']}")
                            edit_notes = st.text_area("Notes", value=receipt['notes'] or "", key=f"edit_notes_{receipt['id']}")
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.form_submit_button("💾 Save Changes", type="primary"):
                                    update_receipt(receipt['id'], edit_category, edit_vendor, edit_amount, edit_date, edit_notes)
                                    del st.session_state[f"editing_{receipt['id']}"]
                                    st.success("Receipt updated!")
                                    st.rerun()
                            with col_cancel:
                                if st.form_submit_button("Cancel"):
                                    del st.session_state[f"editing_{receipt['id']}"]
                                    st.rerun()
                    
                    # Delete confirmation
                    if st.session_state.get(f"confirm_delete_{receipt['id']}", False):
                        st.warning("⚠️ Are you sure you want to delete this receipt?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Yes, Delete", key=f"confirm_yes_{receipt['id']}", type="primary"):
                                # Delete image file if exists
                                if receipt["image_path"] and os.path.exists(receipt["image_path"]):
                                    try:
                                        os.remove(receipt["image_path"])
                                    except:
                                        pass
                                delete_receipt(receipt["id"])
                                del st.session_state[f"confirm_delete_{receipt['id']}"]
                                st.success("Receipt deleted!")
                                st.rerun()
                        with col_no:
                            if st.button("Cancel", key=f"confirm_no_{receipt['id']}"):
                                del st.session_state[f"confirm_delete_{receipt['id']}"]
                                st.rerun()

# Annual Summary Tab
with tab_summary:
    st.subheader("📊 Annual HSA Summary")
    
    # Year selector
    current_year = date.today().year
    summary_year = st.selectbox("Select Year", list(range(current_year, current_year - 5, -1)), key="summary_year")
    
    # Get summary stats
    stats = get_summary_stats(user_id, summary_year)
    
    # Display main metrics
    st.markdown("### Overview")
    col1, col2, col3 = st.columns(3)
    
    col1.metric(
        "Total HSA-Eligible Expenses",
        f"${stats['total_eligible']:,.2f}",
        help="Total of all HSA-eligible expenses for the year"
    )
    
    col2.metric(
        "Total Reimbursed",
        f"${stats['total_reimbursed']:,.2f}",
        help="Amount already reimbursed from HSA"
    )
    
    col3.metric(
        "Unreimbursed Balance",
        f"${stats['unreimbursed_balance']:,.2f}",
        delta=f"${stats['unreimbursed_balance']:,.2f} available" if stats['unreimbursed_balance'] > 0 else None,
        delta_color="normal",
        help="Amount you can still reimburse from your HSA"
    )
    
    # Category breakdown
    st.markdown("---")
    st.markdown("### Expenses by Category")
    
    if stats['by_category']:
        # Create a simple bar chart using Streamlit
        import pandas as pd
        
        df = pd.DataFrame(stats['by_category'])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(df.set_index('category')['total'])
        
        with col2:
            st.markdown("#### Category Details")
            for cat in stats['by_category']:
                with st.container():
                    st.markdown(f"**{cat['category']}**")
                    st.markdown(f"- Total: ${cat['total']:,.2f}")
                    st.markdown(f"- Receipts: {cat['count']}")
                    st.markdown("---")
    else:
        st.info(f"No receipts recorded for {summary_year}")
    
    # HSA Limits Information
    st.markdown