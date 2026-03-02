import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="HSA Receipt Auto-Categorizer", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
import json
from datetime import datetime, date
from decimal import Decimal
import io
import base64

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                is_qualified BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                vendor VARCHAR(500),
                amount DECIMAL(10, 2) NOT NULL,
                receipt_date DATE NOT NULL,
                category_id INTEGER REFERENCES hsa_categories(id),
                category_name VARCHAR(255),
                ocr_text TEXT,
                ai_confidence DECIMAL(5, 2),
                reimbursement_status VARCHAR(50) DEFAULT 'unreimbursed',
                reimbursed_date DATE,
                reimbursed_amount DECIMAL(10, 2),
                notes TEXT,
                receipt_image BYTEA,
                receipt_filename VARCHAR(500),
                tax_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            INSERT INTO hsa_categories (name, description, is_qualified) VALUES
            ('Doctor Visit', 'Office visits, consultations, examinations', TRUE),
            ('Prescription', 'Prescription medications', TRUE),
            ('Dental', 'Dental care, cleanings, procedures', TRUE),
            ('Vision', 'Eye exams, glasses, contacts', TRUE),
            ('Medical Equipment', 'Durable medical equipment, supplies', TRUE),
            ('Lab/Testing', 'Blood work, diagnostic tests, imaging', TRUE),
            ('Mental Health', 'Therapy, counseling, psychiatry', TRUE),
            ('Hospital', 'Hospital stays, emergency room', TRUE),
            ('Physical Therapy', 'PT, OT, rehabilitation', TRUE),
            ('Pharmacy OTC', 'Over-the-counter medicines (qualified)', TRUE),
            ('Other Medical', 'Other qualified medical expenses', TRUE),
            ('Non-Qualified', 'Non-qualified expenses (taxable)', FALSE)
            ON CONFLICT (name) DO NOTHING
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_qualified INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vendor TEXT,
                amount REAL NOT NULL,
                receipt_date DATE NOT NULL,
                category_id INTEGER REFERENCES hsa_categories(id),
                category_name TEXT,
                ocr_text TEXT,
                ai_confidence REAL,
                reimbursement_status TEXT DEFAULT 'unreimbursed',
                reimbursed_date DATE,
                reimbursed_amount REAL,
                notes TEXT,
                receipt_image BLOB,
                receipt_filename TEXT,
                tax_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        categories = [
            ('Doctor Visit', 'Office visits, consultations, examinations', 1),
            ('Prescription', 'Prescription medications', 1),
            ('Dental', 'Dental care, cleanings, procedures', 1),
            ('Vision', 'Eye exams, glasses, contacts', 1),
            ('Medical Equipment', 'Durable medical equipment, supplies', 1),
            ('Lab/Testing', 'Blood work, diagnostic tests, imaging', 1),
            ('Mental Health', 'Therapy, counseling, psychiatry', 1),
            ('Hospital', 'Hospital stays, emergency room', 1),
            ('Physical Therapy', 'PT, OT, rehabilitation', 1),
            ('Pharmacy OTC', 'Over-the-counter medicines (qualified)', 1),
            ('Other Medical', 'Other qualified medical expenses', 1),
            ('Non-Qualified', 'Non-qualified expenses (taxable)', 0)
        ]
        for name, desc, qualified in categories:
            cur.execute("INSERT OR IGNORE INTO hsa_categories (name, description, is_qualified) VALUES (?, ?, ?)", 
                       (name, desc, qualified))
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, is_qualified FROM hsa_categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def extract_text_from_image(image_bytes, filename):
    """Extract text from image using pytesseract OCR"""
    try:
        import pytesseract
        from PIL import Image
        
        if filename.lower().endswith('.pdf'):
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(image_bytes)
                text_parts = []
                for img in images:
                    text_parts.append(pytesseract.image_to_string(img))
                return "\n".join(text_parts)
            except ImportError:
                return "PDF processing requires pdf2image library. Please upload an image file instead."
        else:
            img = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(img)
            return text
    except ImportError:
        return f"[OCR libraries not installed. Filename: {filename}]"
    except Exception as e:
        return f"[OCR Error: {str(e)}]"

def classify_receipt_with_claude(ocr_text, categories):
    """Use Claude to classify receipt from OCR text"""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None, "Anthropic API key not configured"
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        category_list = "\n".join([f"- {c[1]}: {c[2]}" for c in categories])
        
        prompt = f"""Analyze this receipt text extracted via OCR and extract the following information.
Return your response as valid JSON only, no other text.

Receipt OCR Text:
{ocr_text}

Available medical expense categories:
{category_list}

Extract and return JSON with these fields:
{{
    "vendor": "Name of the medical provider/pharmacy/vendor",
    "amount": 0.00,
    "date": "YYYY-MM-DD",
    "category": "Best matching category name from the list above",
    "is_medical": true,
    "confidence": 0.95,
    "notes": "Brief description of the expense"
}}

If you cannot determine a field, use null. For amount, extract the total paid.
For date, use the service/purchase date. Confidence should be 0.0-1.0."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        
        result = json.loads(response_text)
        return result, None
        
    except json.JSONDecodeError as e:
        return None, f"Failed to parse AI response as JSON: {str(e)}"
    except Exception as e:
        return None, f"AI classification error: {str(e)}"

def save_receipt(user_id, vendor, amount, receipt_date, category_id, category_name, 
                 ocr_text, ai_confidence, notes, receipt_image, receipt_filename, 
                 reimbursement_status='unreimbursed'):
    conn = get_conn()
    cur = conn.cursor()
    
    tax_year = receipt_date.year if isinstance(receipt_date, date) else datetime.strptime(receipt_date, '%Y-%m-%d').year
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO hsa_receipts 
            (user_id, vendor, amount, receipt_date, category_id, category_name, 
             ocr_text, ai_confidence, notes, receipt_image, receipt_filename, 
             reimbursement_status, tax_year)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, vendor, amount, receipt_date, category_id, category_name,
              ocr_text, ai_confidence, notes, receipt_image, receipt_filename,
              reimbursement_status, tax_year))
        receipt_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO hsa_receipts 
            (user_id, vendor, amount, receipt_date, category_id, category_name,
             ocr_text, ai_confidence, notes, receipt_image, receipt_filename,
             reimbursement_status, tax_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, vendor, amount, receipt_date, category_id, category_name,
              ocr_text, ai_confidence, notes, receipt_image, receipt_filename,
              reimbursement_status, tax_year))
        receipt_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return receipt_id

def get_receipts(user_id=None, tax_year=None, status=None):
    conn = get_conn()
    cur = conn.cursor()
    
    query = "SELECT * FROM hsa_receipts WHERE 1=1"
    params = []
    
    ph = "%s" if USE_POSTGRES else "?"
    
    if user_id:
        query += f" AND user_id = {ph}"
        params.append(user_id)
    if tax_year:
        query += f" AND tax_year = {ph}"
        params.append(tax_year)
    if status:
        query += f" AND reimbursement_status = {ph}"
        params.append(status)
    
    query += " ORDER BY receipt_date DESC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    
    if cur.description:
        columns = [desc[0] for desc in cur.description]
        receipts = [dict(zip(columns, row)) for row in rows]
    else:
        receipts = []
    
    conn.close()
    return receipts

def update_receipt(receipt_id, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    set_clauses = []
    params = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {ph}")
        params.append(value)
    
    params.append(receipt_id)
    
    query = f"UPDATE hsa_receipts SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = {ph}"
    cur.execute(query, params)
    conn.commit()
    conn.close()

def delete_receipt(receipt_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM hsa_receipts WHERE id = {ph}", (receipt_id,))
    conn.commit()
    conn.close()

def get_balance_summary(tax_year=None):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    if tax_year:
        cur.execute(f"""
            SELECT 
                COALESCE(SUM(amount), 0) as total_expenses,
                COALESCE(SUM(CASE WHEN reimbursement_status = 'reimbursed' THEN COALESCE(reimbursed_amount, amount) ELSE 0 END), 0) as total_reimbursed,
                COALESCE(SUM(CASE WHEN reimbursement_status = 'unreimbursed' THEN amount ELSE 0 END), 0) as unreimbursed_balance,
                COUNT(*) as receipt_count
            FROM hsa_receipts
            WHERE tax_year = {ph}
        """, (tax_year,))
    else:
        cur.execute("""
            SELECT 
                COALESCE(SUM(amount), 0) as total_expenses,
                COALESCE(SUM(CASE WHEN reimbursement_status = 'reimbursed' THEN COALESCE(reimbursed_amount, amount) ELSE 0 END), 0) as total_reimbursed,
                COALESCE(SUM(CASE WHEN reimbursement_status = 'unreimbursed' THEN amount ELSE 0 END), 0) as unreimbursed_balance,
                COUNT(*) as receipt_count
            FROM hsa_receipts
        """)
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            'total_expenses': float(row[0] or 0),
            'total_reimbursed': float(row[1] or 0),
            'unreimbursed_balance': float(row[2] or 0),
            'receipt_count': int(row[3] or 0)
        }
    return {'total_expenses': 0, 'total_reimbursed': 0, 'unreimbursed_balance': 0, 'receipt_count': 0}

def get_category_breakdown(tax_year=None):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    if tax_year:
        cur.execute(f"""
            SELECT category_name, 
                   COUNT(*) as count,
                   SUM(amount) as total
            FROM hsa_receipts
            WHERE tax_year = {ph} AND category_name IS NOT NULL
            GROUP BY category_name
            ORDER BY total DESC
        """, (tax_year,))
    else:
        cur.execute("""
            SELECT category_name,
                   COUNT(*) as count,
                   SUM(amount) as total
            FROM hsa_receipts
            WHERE category_name IS NOT NULL
            GROUP BY category_name
            ORDER BY total DESC
        """)
    
    rows = cur.fetchall()
    conn.close()
    return rows

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("🏥 HSA Receipt Auto-Categorizer")
st.markdown("OCR-powered receipt scanning with AI classification to auto-categorize medical expenses and track unreimbursed HSA balance.")

tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Receipt", "📋 Receipt History", "💰 Balance Dashboard", "⚙️ Settings"])

with tab1:
    st.subheader("Upload & Categorize Receipt")
    
    uploaded_file = st.file_uploader(
        "Upload receipt image or PDF",
        type=['png', 'jpg', 'jpeg', 'pdf', 'gif', 'bmp'],
        help="Supported formats: PNG, JPG, JPEG, PDF, GIF, BMP"
    )
    
    if uploaded_file:
        file_bytes = uploaded_file.read()
        filename = uploaded_file.name
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Receipt Preview:**")
            if filename.lower().endswith('.pdf'):
                st.info("📄 PDF file uploaded. Preview not available.")
            else:
                st.image(file_bytes, caption=filename, use_container_width=True)
        
        with col2:
            st.markdown("**OCR Extraction:**")
            
            with st.spinner("Extracting text from receipt..."):
                ocr_text = extract_text_from_image(file_bytes, filename)
            
            st.text_area("Extracted Text", ocr_text, height=200, disabled=True)
            
            categories = get_categories()
            
            if st.button("🤖 Auto-Classify with AI", type="primary"):
                with st.spinner("Analyzing receipt with Claude..."):
                    result, error = classify_receipt_with_claude(ocr_text, categories)
                
                if error:
                    st.error(error)
                elif result:
                    st.session_state['ai_result'] = result
                    st.session_state['ocr_text'] = ocr_text
                    st.session_state['file_bytes'] = file_bytes
                    st.session_state['filename'] = filename
                    st.success("✅ AI classification complete!")
                    st.rerun()
    
    if 'ai_result' in st.session_state:
        st.markdown("---")
        st.subheader("📝 Review & Save Receipt")
        
        result = st.session_state['ai_result']
        categories = get_categories()
        category_names = [c[1] for c in categories]
        
        col1, col2 = st.columns(2)
        
        with col1:
            vendor = st.text_input("Vendor", value=result.get('vendor') or '')
            
            try:
                amount = float(result.get('amount') or 0)
            except (ValueError, TypeError):
                amount = 0.0
            amount = st.number_input("Amount ($)", min_value=0.0, value=amount, step=0.01)
            
            try:
                date_str = result.get('date')
                if date_str:
                    receipt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                else:
                    receipt_date = date.today()
            except (ValueError, TypeError):
                receipt_date = date.today()
            receipt_date = st.date_input("Receipt Date", value=receipt_date)
        
        with col2:
            suggested_category = result.get('category', 'Other Medical')
            if suggested_category in category_names:
                default_idx = category_names.index(suggested_category)
            else:
                default_idx = category_names.index('Other Medical') if 'Other Medical' in category_names else 0
            
            selected_category = st.selectbox("Category", category_names, index=default_idx)
            
            category_id = None
            for c in categories:
                if c[1] == selected_category:
                    category_id = c[0]
                    break
            
            confidence = result.get('confidence', 0.5)
            st.metric("AI Confidence", f"{confidence * 100:.0f}%")
            
            status = st.selectbox("Reimbursement Status", 
                                 ['unreimbursed', 'reimbursed', 'pending', 'denied'])
        
        notes = st.text_area("Notes", value=result.get('notes') or '')
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Receipt", type="primary"):
                if amount <= 0:
                    st.error("Please enter a valid amount")
                else:
                    receipt_id = save_receipt(
                        user_id=1,
                        vendor=vendor,
                        amount=amount,
                        receipt_date=receipt_date,
                        category_id=category_id,
                        category_name=selected_category,
                        ocr_text=st.session_state.get('ocr_text', ''),
                        ai_confidence=confidence,
                        notes=notes,
                        receipt_image=st.session_state.get('file_bytes'),
                        receipt_filename=st.session_state.get('filename'),
                        reimbursement_status=status
                    )
                    st.success(f"✅ Receipt saved! (ID: {receipt_id})")
                    
                    for key in ['ai_result', 'ocr_text', 'file_bytes', 'filename']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
        
        with col2:
            if st.button("🗑️ Discard"):
                for key in ['ai_result', 'ocr_text', 'file_bytes', 'filename']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

with tab2:
    st.subheader("Receipt History")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        current_year = date.today().year
        years = list(range(current_year, current_year - 10, -1))
        filter_year = st.selectbox("Tax Year", ["All Years"] + years, key="hist_year")
    with col2:
        filter_status = st.selectbox("Status", ["All", "unreimbursed", "reimbursed", "pending", "denied"], key="hist_status")
    with col3:
        st.write("")
    
    tax_year_filter = None if filter_year == "All Years" else filter_year
    status_filter = None if filter_status == "All" else filter_status
    
    receipts = get_receipts(tax_year=tax_year_filter, status=status_filter)
    
    if not receipts:
        st.info("📭 No receipts found. Upload your first receipt above!")
    else:
        st.markdown(f"**{len(receipts)} receipts found**")
        
        for receipt in receipts:
            with st.expander(f"📄 {receipt.get('vendor', 'Unknown')} - ${receipt.get('amount', 0):.2f} ({receipt.get('receipt_date')})"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**Category:** {receipt.get('category_name', 'Uncategorized')}")
                    st.markdown(f"**Date:** {receipt.get('receipt_date')}")
                    st.markdown(f"**Tax Year:** {receipt.get('tax_year')}")
                
                with col2:
                    status_emoji = {
                        'unreimbursed': '🔴',
                        'reimbursed': '✅',
                        'pending': '🟡',
                        'denied': '❌'
                    }
                    status = receipt.get('reimbursement_status', 'unreimbursed')
                    st.markdown(f"**Status:** {status_emoji.get(status, '⚪')} {status.title()}")
                    
                    if receipt.get('ai_confidence'):
                        st.markdown(f"**AI Confidence:** {float(receipt['ai_confidence']) * 100:.0f}%")
                    
                    if receipt.get('notes'):
                        st.markdown(f"**Notes:** {receipt['notes']}")
                
                with col3:
                    receipt_id = receipt['id']
                    
                    if st.button("✅ Mark Reimbursed", key=f"reimburse_{receipt_id}"):
                        update_receipt(receipt_id, 
                                      reimbursement_status='reimbursed',
                                      reimbursed_date=date.today(),
                                      reimbursed_amount=receipt['amount'])
                        st.success("Updated!")
                        st.rerun()
                    
                    if st.button("🗑️ Delete", key=f"delete_{receipt_id}"):
                        delete_receipt(receipt_id)
                        st.success("Deleted!")
                        st.rerun()

with tab3:
    st.subheader("Balance Dashboard")
    
    current_year = date.today().year
    years = list(range(current_year, current_year - 10, -1))
    selected_year = st.selectbox("Select Tax Year", ["All Time"] + years, key="dash_year")
    
    year_filter = None if selected_year == "All Time" else selected_year
    summary = get_balance_summary(year_filter)
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Medical Expenses",
            f"${summary['total_expenses']:,.2f}",
            help="Total of all qualified medical expenses"
        )
    
    with col2:
        st.metric(
            "Reimbursed",
            f"${summary['total_reimbursed']:,.2f}",
            help="Amount already reimbursed from HSA"
        )
    
    with col3:
        st.metric(
            "Unreimbursed Balance",
            f"${summary['unreimbursed_balance']:,.2f}",
            delta=f"+{summary['unreimbursed_balance']:,.2f}" if summary['unreimbursed_balance'] > 0 else None,
            help="Available for future HSA reimbursement"
        )
    
    with col4:
        st.metric(
            "Receipt Count",
            summary['receipt_count'],
            help="Total receipts on file"
        )
    
    st.markdown("---")
    st.subheader("📊 Expenses by Category")
    
    breakdown = get_category_breakdown(year_filter)
    
    if breakdown:
        import pandas as pd
        df = pd.DataFrame(breakdown, columns=['Category', 'Count', 'Total'])
        df['Total'] = df['Total'].apply(lambda x: float(x) if x else 0)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(df.set_index('Category')['Total'])
        
        with col2:
            st.dataframe(
                df.style.format({'Total': '${:,.2f}'}),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No categorized expenses yet.")
    
    st.markdown("---")
    st.subheader("📅 Annual Summary")
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT tax_year,
               COUNT(*) as receipt_count,
               SUM(amount) as total_expenses,
               SUM(CASE WHEN reimbursement_status = 'unreimbursed' THEN amount ELSE 0 END) as unreimbursed
        FROM hsa_receipts
        WHERE tax_year IS NOT NULL
        GROUP BY tax_year
        ORDER BY tax_year DESC
    """)
    annual_data = cur.fetchall()
    conn.close()
    
    if annual_data:
        import pandas as pd
        annual_df = pd.DataFrame(annual_data, columns=['Year', 'Receipts', 'Total Expenses', 'Unreimbursed'])
        annual_df['Total Expenses'] = annual_df['Total Expenses'].apply(lambda x: float(x) if x else 0)
        annual_df['Unreimbursed'] = annual_df['Unreimbursed'].apply(lambda x: float(x) if x else 0)
        
        st.dataframe(
            annual_df.style.format({
                'Total Expenses': '${:,.2f}',
                'Unreimbursed': '${:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No annual data available yet.")

with tab4:
    st.subheader("Settings")
    
    st.markdown("### API Configuration")
    
    current_key = get_setting("anthropic_api_key") or ""
    masked_key = current_key[:10] + "..." + current_key[-4:] if len(current_key) > 14 else "Not configured"
    st.markdown(f"**Current Anthropic API Key:** `{masked_key}`")
    
    new_key = st.text_input("Update Anthropic API Key", type="password", 
                            help="Enter your Anthropic API key for AI classification")
    if st.button("Save API Key"):
        if new_key:
            set_setting("anthropic_api_key", new_key)
            st.success("✅ API key saved!")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### Category Management")
    
    categories = get_categories()
    
    st.markdown("**Current Categories:**")
    for cat in categories:
        qualified = "✅ Qualified" if cat[3] else "❌ Non-Qualified"
        st.markdown(f"- **{cat[1]}**: {cat[2]} ({qualified})")
    
    st.markdown("---")
    st.markdown("### Data Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export All Receipts (CSV)"):
            receipts = get_receipts()
            if receipts:
                import pandas as pd
                export_data