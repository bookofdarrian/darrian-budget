import streamlit as st
import json
import base64
import os
from datetime import datetime, date, timedelta
from pathlib import Path

st.set_page_config(page_title="Tax Document Vault", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

UPLOAD_DIR = Path("uploads/tax_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DOC_TYPES = ["W-2", "1099-NEC", "1099-MISC", "1099-INT", "1099-DIV", "1099-B", "1099-K", "1040", "State Return", "Other"]

ESTIMATED_TAX_DEADLINES = {
    "Q1": {"month": 4, "day": 15, "label": "Q1 Estimated Tax"},
    "Q2": {"month": 6, "day": 15, "label": "Q2 Estimated Tax"},
    "Q3": {"month": 9, "day": 15, "label": "Q3 Estimated Tax"},
    "Q4": {"month": 1, "day": 15, "label": "Q4 Estimated Tax (Next Year)"},
}

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_documents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                doc_type VARCHAR(50) NOT NULL,
                tax_year INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                extracted_data JSONB DEFAULT '{}',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_deadlines (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                deadline_type VARCHAR(50) NOT NULL,
                tax_year INTEGER NOT NULL,
                due_date DATE NOT NULL,
                amount_due DECIMAL(12,2) DEFAULT 0,
                paid BOOLEAN DEFAULT FALSE,
                paid_date DATE,
                reminder_sent BOOLEAN DEFAULT FALSE,
                notes TEXT DEFAULT ''
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                doc_type TEXT NOT NULL,
                tax_year INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                extracted_data TEXT DEFAULT '{}',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_deadlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                deadline_type TEXT NOT NULL,
                tax_year INTEGER NOT NULL,
                due_date DATE NOT NULL,
                amount_due REAL DEFAULT 0,
                paid INTEGER DEFAULT 0,
                paid_date DATE,
                reminder_sent INTEGER DEFAULT 0,
                notes TEXT DEFAULT ''
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def classify_document_type(filename: str, extracted_text: str = "") -> str:
    filename_lower = filename.lower()
    text_lower = extracted_text.lower()
    
    if "w-2" in filename_lower or "w2" in filename_lower or "wage and tax statement" in text_lower:
        return "W-2"
    elif "1099-nec" in filename_lower or "1099nec" in filename_lower or "nonemployee compensation" in text_lower:
        return "1099-NEC"
    elif "1099-misc" in filename_lower or "1099misc" in filename_lower:
        return "1099-MISC"
    elif "1099-int" in filename_lower or "1099int" in filename_lower or "interest income" in text_lower:
        return "1099-INT"
    elif "1099-div" in filename_lower or "1099div" in filename_lower or "dividends" in text_lower:
        return "1099-DIV"
    elif "1099-b" in filename_lower or "1099b" in filename_lower or "proceeds from broker" in text_lower:
        return "1099-B"
    elif "1099-k" in filename_lower or "1099k" in filename_lower or "payment card" in text_lower:
        return "1099-K"
    elif "1040" in filename_lower or "u.s. individual income tax return" in text_lower:
        return "1040"
    elif "state" in filename_lower and ("return" in filename_lower or "tax" in filename_lower):
        return "State Return"
    else:
        return "Other"

def extract_data_with_ocr(file_bytes: bytes, file_type: str, doc_type: str) -> dict:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return {"error": "No Anthropic API key configured", "raw_text": ""}
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        base64_image = base64.standard_b64encode(file_bytes).decode("utf-8")
        
        if file_type in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            media_type = file_type
        else:
            media_type = "image/png"
        
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Extract key data from this {doc_type} tax document. Return as JSON with relevant fields like income amounts, payer info, tax withheld, etc."
                        }
                    ],
                }
            ],
        )
        
        return {"extracted": message.content[0].text, "raw_text": ""}
    except Exception as e:
        return {"error": str(e), "raw_text": ""}

def save_document(uploaded_file, doc_type: str, tax_year: int, notes: str = "") -> int:
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{tax_year}_{doc_type}_{timestamp}_{file_name}"
    file_path = UPLOAD_DIR / safe_name
    
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    
    extracted_data = extract_data_with_ocr(file_bytes, uploaded_file.type, doc_type)
    
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO tax_documents (doc_type, tax_year, file_path, file_name, extracted_data, notes)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (doc_type, tax_year, str(file_path), file_name, json.dumps(extracted_data), notes))
        doc_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO tax_documents (doc_type, tax_year, file_path, file_name, extracted_data, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (doc_type, tax_year, str(file_path), file_name, json.dumps(extracted_data), notes))
        doc_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    
    return doc_id

def get_documents(tax_year: int = None) -> list:
    conn = get_conn()
    cur = conn.cursor()
    
    if tax_year:
        if USE_POSTGRES:
            cur.execute("SELECT * FROM tax_documents WHERE tax_year = %s ORDER BY uploaded_at DESC", (tax_year,))
        else:
            cur.execute("SELECT * FROM tax_documents WHERE tax_year = ? ORDER BY uploaded_at DESC", (tax_year,))
    else:
        cur.execute("SELECT * FROM tax_documents ORDER BY uploaded_at DESC")
    
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_document(doc_id: int):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("SELECT file_path FROM tax_documents WHERE id = %s", (doc_id,))
    else:
        cur.execute("SELECT file_path FROM tax_documents WHERE id = ?", (doc_id,))
    
    row = cur.fetchone()
    if row:
        file_path = Path(row[0])
        if file_path.exists():
            file_path.unlink()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM tax_documents WHERE id = %s", (doc_id,))
    else:
        cur.execute("DELETE FROM tax_documents WHERE id = ?", (doc_id,))
    
    conn.commit()
    conn.close()

def get_deadlines(tax_year: int = None) -> list:
    conn = get_conn()
    cur = conn.cursor()
    
    if tax_year:
        if USE_POSTGRES:
            cur.execute("SELECT * FROM tax_deadlines WHERE tax_year = %s ORDER BY due_date", (tax_year,))
        else:
            cur.execute("SELECT * FROM tax_deadlines WHERE tax_year = ? ORDER BY due_date", (tax_year,))
    else:
        cur.execute("SELECT * FROM tax_deadlines ORDER BY due_date")
    
    rows = cur.fetchall()
    conn.close()
    return rows

def add_deadline(deadline_type: str, tax_year: int, due_date: date, amount_due: float = 0, notes: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO tax_deadlines (deadline_type, tax_year, due_date, amount_due, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (deadline_type, tax_year, due_date, amount_due, notes))
    else:
        cur.execute("""
            INSERT INTO tax_deadlines (deadline_type, tax_year, due_date, amount_due, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (deadline_type, tax_year, due_date, amount_due, notes))
    
    conn.commit()
    conn.close()

def mark_deadline_paid(deadline_id: int, paid_date: date = None):
    if paid_date is None:
        paid_date = date.today()
    
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("UPDATE tax_deadlines SET paid = TRUE, paid_date = %s WHERE id = %s", (paid_date, deadline_id))
    else:
        cur.execute("UPDATE tax_deadlines SET paid = 1, paid_date = ? WHERE id = ?", (paid_date, deadline_id))
    
    conn.commit()
    conn.close()

# Main UI
st.title("🍑 Tax Document Vault")

render_sidebar_brand()
render_sidebar_user_widget()

tab1, tab2, tab3 = st.tabs(["📄 Documents", "📅 Deadlines", "📊 Summary"])

with tab1:
    st.header("Upload Tax Documents")
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "png", "jpg", "jpeg"])
    with col2:
        tax_year = st.selectbox("Tax Year", range(datetime.now().year, 2019, -1))
        doc_type = st.selectbox("Document Type", DOC_TYPES)
        notes = st.text_area("Notes (optional)")
    
    if uploaded_file and st.button("Upload Document"):
        with st.spinner("Processing document..."):
            doc_id = save_document(uploaded_file, doc_type, tax_year, notes)
            st.success(f"Document uploaded successfully! ID: {doc_id}")
            st.rerun()
    
    st.header("Your Documents")
    filter_year = st.selectbox("Filter by Year", [None] + list(range(datetime.now().year, 2019, -1)), format_func=lambda x: "All Years" if x is None else str(x))
    
    documents = get_documents(filter_year)
    
    if documents:
        for doc in documents:
            with st.expander(f"{doc[2]} - {doc[3]} ({doc[5]})"):
                st.write(f"**Uploaded:** {doc[7]}")
                st.write(f"**Notes:** {doc[8] or 'None'}")
                
                extracted = json.loads(doc[6]) if doc[6] else {}
                if extracted and "extracted" in extracted:
                    st.write("**Extracted Data:**")
                    st.code(extracted["extracted"])
                
                if st.button(f"Delete", key=f"del_{doc[0]}"):
                    delete_document(doc[0])
                    st.rerun()
    else:
        st.info("No documents uploaded yet.")

with tab2:
    st.header("Tax Deadlines")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        deadline_type = st.text_input("Deadline Type", "Estimated Tax Q1")
    with col2:
        deadline_year = st.selectbox("Year", range(datetime.now().year, 2019, -1), key="deadline_year")
    with col3:
        due_date = st.date_input("Due Date")
    
    amount = st.number_input("Amount Due ($)", min_value=0.0, step=100.0)
    deadline_notes = st.text_input("Notes")
    
    if st.button("Add Deadline"):
        add_deadline(deadline_type, deadline_year, due_date, amount, deadline_notes)
        st.success("Deadline added!")
        st.rerun()
    
    st.subheader("Upcoming Deadlines")
    deadlines = get_deadlines()
    
    for dl in deadlines:
        paid_status = "✅ Paid" if dl[6] else "⏳ Pending"
        due = dl[4]
        if isinstance(due, str):
            due = datetime.strptime(due, "%Y-%m-%d").date()
        
        days_until = (due - date.today()).days
        urgency = "🔴" if days_until < 7 and not dl[6] else "🟡" if days_until < 30 and not dl[6] else "🟢"
        
        with st.expander(f"{urgency} {dl[2]} - {dl[3]} - Due: {due} ({paid_status})"):
            st.write(f"**Amount:** ${dl[5]:,.2f}")
            st.write(f"**Notes:** {dl[9] or 'None'}")
            
            if not dl[6]:
                if st.button(f"Mark as Paid", key=f"pay_{dl[0]}"):
                    mark_deadline_paid(dl[0])
                    st.rerun()

with tab3:
    st.header("Tax Summary")
    
    summary_year = st.selectbox("Select Year", range(datetime.now().year, 2019, -1), key="summary_year")
    
    docs = get_documents(summary_year)
    deadlines = get_deadlines(summary_year)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents Uploaded", len(docs))
    with col2:
        paid_deadlines = sum(1 for d in deadlines if d[6])
        st.metric("Deadlines Completed", f"{paid_deadlines}/{len(deadlines)}")
    with col3:
        total_tax_paid = sum(d[5] for d in deadlines if d[6])
        st.metric("Total Tax Paid", f"${total_tax_paid:,.2f}")
    
    st.subheader("Document Checklist")
    for doc_type in DOC_TYPES:
        has_doc = any(d[2] == doc_type for d in docs)
        status = "✅" if has_doc else "⬜"
        st.write(f"{status} {doc_type}")