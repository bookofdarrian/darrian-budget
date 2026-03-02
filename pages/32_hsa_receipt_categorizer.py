import streamlit as st
import os
import io
import tempfile
from datetime import datetime, date, timedelta
from decimal import Decimal
import json
import base64

st.set_page_config(page_title="HSA Receipt Categorizer", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

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

# Database placeholder helper
def ph(idx=1):
    """Return the appropriate placeholder for the database type."""
    return "%s" if USE_POSTGRES else "?"

def phs(count):
    """Return multiple placeholders separated by commas."""
    return ", ".join([ph() for _ in range(count)])

def _ensure_tables():
    """Create HSA receipts table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id SERIAL PRIMARY KEY,
                receipt_date DATE NOT NULL,
                provider VARCHAR(255) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT,
                reimbursed BOOLEAN DEFAULT FALSE,
                reimbursed_date DATE,
                receipt_image_path TEXT,
                ocr_text TEXT,
                ai_classification_raw TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hsa_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_date DATE NOT NULL,
                provider VARCHAR(255) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT,
                reimbursed BOOLEAN DEFAULT 0,
                reimbursed_date DATE,
                receipt_image_path TEXT,
                ocr_text TEXT,
                ai_classification_raw TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Constants
CATEGORIES = ["medical", "dental", "vision", "rx", "mental_health", "therapy", "lab_work", "other"]
CATEGORY_LABELS = {
    "medical": "🏥 Medical",
    "dental": "🦷 Dental",
    "vision": "👓 Vision",
    "rx": "💊 Prescription (Rx)",
    "mental_health": "🧠 Mental Health",
    "therapy": "🩹 Physical Therapy",
    "lab_work": "🧪 Lab Work",
    "other": "📋 Other"
}

# Upload directory
UPLOAD_DIR = "uploads/hsa_receipts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def extract_text_from_image(image_bytes, filename):
    """Extract text from image using pytesseract OCR."""
    try:
        from PIL import Image
        import pytesseract
        
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except ImportError:
        return "[OCR unavailable - pytesseract not installed]"
    except Exception as e:
        return f"[OCR error: {str(e)}]"

def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF using pdf2image and pytesseract."""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        
        images = convert_from_bytes(pdf_bytes)
        all_text = []
        for img in images:
            text = pytesseract.image_to_string(img)
            all_text.append(text)
        return "\n\n".join(all_text).strip()
    except ImportError:
        return "[OCR unavailable - pdf2image or pytesseract not installed]"
    except Exception as e:
        return f"[PDF OCR error: {str(e)}]"

def classify_receipt_with_claude(ocr_text):
    """Use Claude to classify the medical receipt."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None, "Anthropic API key not configured"
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""Analyze this medical receipt/bill text and extract the following information in JSON format:

Receipt Text:
{ocr_text}

Please extract and return ONLY a valid JSON object with these fields:
{{
    "provider": "Name of the medical provider/facility",
    "date": "Date of service in YYYY-MM-DD format (use best guess if unclear)",
    "amount": "Total amount as a number (no currency symbols)",
    "category": "One of: medical, dental, vision, rx, mental_health, therapy, lab_work, other",
    "description": "Brief description of the service/items",
    "confidence": "high, medium, or low based on text clarity"
}}

If any field cannot be determined, use null. Return ONLY the JSON object, no other text."""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        # Try to parse JSON from response
        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text)
            return result, None
        except json.JSONDecodeError:
            return None, f"Failed to parse AI response: {response_text[:200]}"
            
    except ImportError:
        return None, "Anthropic library not installed"
    except Exception as e:
        return None, f"AI classification error: {str(e)}"

def save_receipt_file(uploaded_file):
    """Save uploaded file and return the path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in ".-_")
    filename = f"{timestamp}_{safe_name}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getvalue())
    
    return filepath

def add_receipt(receipt_date, provider, amount, category, description, reimbursed, receipt_image_path, ocr_text, ai_raw):
    """Insert a new HSA receipt into the database."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO hsa_receipts (receipt_date, provider, amount, category, description, reimbursed, receipt_image_path, ocr_text, ai_classification_raw)
        VALUES ({phs(9)})
    """, (receipt_date, provider, amount, category, description, reimbursed, receipt_image_path, ocr_text, ai_raw))
    
    conn.commit()
    conn.close()

def update_receipt(receipt_id, receipt_date, provider, amount, category, description, reimbursed, reimbursed_date):
    """Update an existing HSA receipt."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        UPDATE hsa_receipts
        SET receipt_date = {ph()}, provider = {ph()}, amount = {ph()}, category = {ph()}, 
            description = {ph()}, reimbursed = {ph()}, reimbursed_date = {ph()}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph()}
    """, (receipt_date, provider, amount, category, description, reimbursed, reimbursed_date, receipt_id))
    
    conn.commit()
    conn.close()

def delete_receipt(receipt_id):
    """Delete an HSA receipt."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get the file path first to delete the file
    cur.execute(f"SELECT receipt_image_path FROM hsa_receipts WHERE id = {ph()}", (receipt_id,))
    row = cur.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.remove(row[0])
        except:
            pass
    
    cur.execute(f"DELETE FROM hsa_receipts WHERE id = {ph()}", (receipt_id,))
    conn.commit()
    conn.close()

def get_receipts(start_date=None, end_date=None, category=None, reimbursed=None):
    """Fetch HSA receipts with optional filters."""
    conn = get_conn()
    cur = conn.cursor()
    
    query = "SELECT id, receipt_date, provider, amount, category, description, reimbursed, reimbursed_date, receipt_image_path, ocr_text, created_at FROM hsa_receipts WHERE 1=1"
    params = []
    
    if start_date:
        query += f" AND receipt_date >= {ph()}"
        params.append(start_date)
    if end_date:
        query += f" AND receipt_date <= {ph()}"
        params.append(end_date)
    if category and category != "all":
        query += f" AND category = {ph()}"
        params.append(category)
    if reimbursed is not None:
        query += f" AND reimbursed = {ph()}"
        params.append(reimbursed)
    
    query += " ORDER BY receipt_date DESC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    return rows

def get_summary_stats():
    """Get summary statistics for HSA receipts."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Total unreimbursed
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM hsa_receipts WHERE reimbursed = FALSE")
    unreimbursed_total = float(cur.fetchone()[0])
    
    # Total reimbursed
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM hsa_receipts WHERE reimbursed = TRUE")
    reimbursed_total = float(cur.fetchone()[0])
    
    # Total all time
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM hsa_receipts")
    all_time_total = float(cur.fetchone()[0])
    
    # Count by category
    cur.execute("SELECT category, COUNT(*), SUM(amount) FROM hsa_receipts GROUP BY category")
    category_stats = cur.fetchall()
    
    # This year unreimbursed
    year_start = date(date.today().year, 1, 1)
    cur.execute(f"SELECT COALESCE(SUM(amount), 0) FROM hsa_receipts WHERE reimbursed = FALSE AND receipt_date >= {ph()}", (year_start,))
    ytd_unreimbursed = float(cur.fetchone()[0])
    
    conn.close()
    
    return {
        "unreimbursed_total": unreimbursed_total,
        "reimbursed_total": reimbursed_total,
        "all_time_total": all_time_total,
        "category_stats": category_stats,
        "ytd_unreimbursed": ytd_unreimbursed
    }

# Main UI
st.title("🏥 HSA Receipt Auto-Categorizer")
st.markdown("Track medical expenses, auto-categorize with AI, and manage your unreimbursed HSA balance for tax-advantaged growth.")

# Summary metrics at top
stats = get_summary_stats()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Unreimbursed Balance", f"${stats['unreimbursed_total']:,.2f}", help="Total available for future tax-free withdrawal")
with col2:
    st.metric("📅 YTD Unreimbursed", f"${stats['ytd_unreimbursed']:,.2f}", help="This year's unreimbursed expenses")
with col3:
    st.metric("✅ Total Reimbursed", f"${stats['reimbursed_total']:,.2f}")
with col4:
    st.metric("📊 All-Time Expenses", f"${stats['all_time_total']:,.2f}")

st.markdown("---")

# Tabs for different functions
tab1, tab2, tab3 = st.tabs(["📤 Upload Receipt", "📋 Receipt List", "📊 Analytics"])

with tab1:
    st.subheader("Upload & Categorize Receipt")
    
    # Check for API key
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        st.warning("⚠️ Anthropic API key not configured. AI auto-categorization will be unavailable. Set it in Settings.")
    
    uploaded_file = st.file_uploader(
        "Upload receipt image or PDF",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Supported formats: PNG, JPG, JPEG, PDF"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📄 Uploaded File")
            
            # Show preview for images
            if uploaded_file.type.startswith("image/"):
                st.image(uploaded_file, use_container_width=True)
            else:
                st.info(f"📁 PDF uploaded: {uploaded_file.name}")
        
        with col2:
            st.markdown("### 🤖 AI Analysis")
            
            # Process button
            if st.button("🔍 Extract & Classify", type="primary", use_container_width=True):
                with st.spinner("Processing receipt..."):
                    # Extract text
                    file_bytes = uploaded_file.getvalue()
                    
                    if uploaded_file.type == "application/pdf":
                        ocr_text = extract_text_from_pdf(file_bytes)
                    else:
                        ocr_text = extract_text_from_image(file_bytes, uploaded_file.name)
                    
                    st.session_state["ocr_text"] = ocr_text
                    
                    # Show OCR result
                    with st.expander("📝 OCR Extracted Text", expanded=False):
                        st.text(ocr_text if ocr_text else "No text extracted")
                    
                    # AI Classification
                    if api_key and ocr_text and not ocr_text.startswith("["):
                        classification, error = classify_receipt_with_claude(ocr_text)
                        
                        if classification:
                            st.session_state["ai_classification"] = classification
                            st.success("✅ AI classification complete!")
                            
                            # Show classification
                            st.json(classification)
                        elif error:
                            st.warning(f"⚠️ {error}")
                            st.session_state["ai_classification"] = None
                    else:
                        st.session_state["ai_classification"] = None
            
            # Manual entry / edit form
            st.markdown("### ✏️ Receipt Details")
            
            # Pre-fill from AI if available
            ai_data = st.session_state.get("ai_classification", {}) or {}
            
            with st.form("receipt_form"):
                # Date
                default_date = date.today()
                if ai_data.get("date"):
                    try:
                        default_date = datetime.strptime(ai_data["date"], "%Y-%m-%d").date()
                    except:
                        pass
                
                receipt_date = st.date_input("Service Date", value=default_date)
                
                # Provider
                provider = st.text_input("Provider/Facility", value=ai_data.get("provider", ""))
                
                # Amount
                default_amount = 0.0
                if ai_data.get("amount"):
                    try:
                        default_amount = float(ai_data["amount"])
                    except:
                        pass
                amount = st.number_input("Amount ($)", min_value=0.0, step=0.01, value=default_amount)
                
                # Category
                default_category_idx = 0
                if ai_data.get("category") in CATEGORIES:
                    default_category_idx = CATEGORIES.index(ai_data["category"])
                
                category = st.selectbox(
                    "Category",
                    options=CATEGORIES,
                    index=default_category_idx,
                    format_func=lambda x: CATEGORY_LABELS.get(x, x)
                )
                
                # Description
                description = st.text_area("Description", value=ai_data.get("description", ""), height=80)
                
                # Reimbursement status
                reimbursed = st.checkbox("Already Reimbursed", value=False)
                
                submitted = st.form_submit_button("💾 Save Receipt", type="primary", use_container_width=True)
                
                if submitted:
                    if not provider:
                        st.error("Please enter a provider name")
                    elif amount <= 0:
                        st.error("Please enter a valid amount")
                    else:
                        # Save file
                        filepath = save_receipt_file(uploaded_file)
                        
                        # Save to database
                        ocr_text = st.session_state.get("ocr_text", "")
                        ai_raw = json.dumps(ai_data) if ai_data else None
                        
                        add_receipt(
                            receipt_date=receipt_date,
                            provider=provider,
                            amount=amount,
                            category=category,
                            description=description,
                            reimbursed=reimbursed,
                            receipt_image_path=filepath,
                            ocr_text=ocr_text,
                            ai_raw=ai_raw
                        )
                        
                        st.success(f"✅ Receipt saved: ${amount:.2f} from {provider}")
                        
                        # Clear session state
                        st.session_state.pop("ocr_text", None)
                        st.session_state.pop("ai_classification", None)
                        
                        st.rerun()

with tab2:
    st.subheader("📋 Receipt History")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_start = st.date_input("From Date", value=date.today() - timedelta(days=365), key="filter_start")
    with col2:
        filter_end = st.date_input("To Date", value=date.today(), key="filter_end")
    with col3:
        filter_category = st.selectbox(
            "Category",
            options=["all"] + CATEGORIES,
            format_func=lambda x: "All Categories" if x == "all" else CATEGORY_LABELS.get(x, x),
            key="filter_category"
        )
    with col4:
        filter_reimbursed = st.selectbox(
            "Reimbursement Status",
            options=["all", "unreimbursed", "reimbursed"],
            format_func=lambda x: {"all": "All", "unreimbursed": "❌ Unreimbursed", "reimbursed": "✅ Reimbursed"}.get(x, x),
            key="filter_reimbursed"
        )
    
    # Apply filters
    reimbursed_filter = None
    if filter_reimbursed == "unreimbursed":
        reimbursed_filter = False
    elif filter_reimbursed == "reimbursed":
        reimbursed_filter = True
    
    receipts = get_receipts(
        start_date=filter_start,
        end_date=filter_end,
        category=filter_category if filter_category != "all" else None,
        reimbursed=reimbursed_filter
    )
    
    # Summary for filtered results
    if receipts:
        filtered_total = sum(float(r[3]) for r in receipts)
        filtered_unreimbursed = sum(float(r[3]) for r in receipts if not r[6])
        
        st.info(f"📊 Showing **{len(receipts)}** receipts | Total: **${filtered_total:,.2f}** | Unreimbursed: **${filtered_unreimbursed:,.2f}**")
    
    # Receipt list
    if not receipts:
        st.info("No receipts found matching your filters. Upload your first receipt above!")
    else:
        for receipt in receipts:
            rid, rdate, provider, amount, category, description, reimbursed, reimb_date, img_path, ocr_text, created = receipt
            
            with st.expander(f"{'✅' if reimbursed else '❌'} {rdate} — {provider} — ${float(amount):,.2f} — {CATEGORY_LABELS.get(category, category)}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Provider:** {provider}")
                    st.markdown(f"**Date:** {rdate}")
                    st.markdown(f"**Amount:** ${float(amount):,.2f}")
                    st.markdown(f"**Category:** {CATEGORY_LABELS.get(category, category)}")
                    if description:
                        st.markdown(f"**Description:** {description}")
                    st.markdown(f"**Status:** {'✅ Reimbursed' if reimbursed else '❌ Not Reimbursed'}")
                    if reimbursed and reimb_date:
                        st.markdown(f"**Reimbursed On:** {reimb_date}")
                    
                    # Show image if available
                    if img_path and os.path.exists(img_path):
                        if img_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(img_path, width=300)
                        else:
                            st.markdown(f"📎 [View Receipt File]({img_path})")
                
                with col2:
                    st.markdown("**Quick Actions**")
                    
                    # Toggle reimbursement
                    if not reimbursed:
                        if st.button("✅ Mark Reimbursed", key=f"reimb_{rid}"):
                            update_receipt(rid, rdate, provider, amount, category, description, True, date.today())
                            st.success("Marked as reimbursed!")
                            st.rerun()
                    else:
                        if st.button("↩️ Mark Unreimbursed", key=f"unreimb_{rid}"):
                            update_receipt(rid, rdate, provider, amount, category, description, False, None)
                            st.success("Marked as unreimbursed!")
                            st.rerun()
                    
                    # Delete
                    if st.button("🗑️ Delete", key=f"del_{rid}", type="secondary"):
                        delete_receipt(rid)
                        st.success("Receipt deleted!")
                        st.rerun()
                
                # Edit form
                with st.form(f"edit_form_{rid}"):
                    st.markdown("---")
                    st.markdown("**Edit Receipt**")
                    
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        new_date = st.date_input("Date", value=rdate, key=f"edit_date_{rid}")
                        new_provider = st.text_input("Provider", value=provider, key=f"edit_provider_{rid}")
                        new_amount = st.number_input("Amount", value=float(amount), min_value=0.0, step=0.01, key=f"edit_amount_{rid}")
                    
                    with edit_col2:
                        cat_idx = CATEGORIES.index(category) if category in CATEGORIES else 0
                        new_category = st.selectbox("Category", options=CATEGORIES, index=cat_idx, format_func=lambda x: CATEGORY_LABELS.get(x, x), key=f"edit_cat_{rid}")
                        new_description = st.text_area("Description", value=description or "", key=f"edit_desc_{rid}")
                        new_reimbursed = st.checkbox("Reimbursed", value=reimbursed, key=f"edit_reimb_{rid}")
                    
                    if st.form_submit_button("💾 Save Changes"):
                        new_reimb_date = date.today() if new_reimbursed and not reimbursed else reimb_date
                        update_receipt(rid, new_date, new_provider, new_amount, new_category, new_description, new_reimbursed, new_reimb_date)
                        st.success("Receipt updated!")
                        st.rerun()

with tab3:
    st.subheader("📊 HSA Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 Unreimbursed Balance Growth")
        st.markdown("""
        Your unreimbursed HSA expenses can be reimbursed **at any time in the future**, 
        allowing your HSA investments to grow tax-free. The longer you wait, the more 
        tax-advantaged growth you capture!
        """)
        
        # Calculate potential growth scenarios
        unreimbursed = stats["unreimbursed_total"]
        if unreimbursed > 0:
            st.markdown("#### Potential Future Value")
            
            years = [5, 10, 15, 20]
            growth_rate = 0.07  # 7% annual return assumption
            
            growth_data = []
            for y in years:
                future_value = unreimbursed * ((1 + growth_rate) ** y)
                growth_data.append({
                    "Years": y,
                    "Future Value": f"${future_value:,.2f}",
                    "Tax-Free Growth": f"${future_value - unreimbursed:,.2f}"
                })
            
            st.table(growth_data)
            st.caption("*Assumes 7% average annual return. Past performance does not guarantee future results.*")
        else:
            st.info("Upload receipts to track your unreimbursed balance!")
    
    with col2:
        st.markdown("### 📈 Spending by Category")
        
        if stats["category_stats"]:
            import pandas as pd
            
            cat_data = []
            for cat, count, total in stats["category_stats"]:
                cat_data.append({
                    "Category": CATEGORY_LABELS.get(cat, cat),
                    "Count": count,
                    "Total": float(total) if total else 0
                })
            
            df = pd.DataFrame(cat_data)
            df = df.sort_values("Total", ascending=False)
            
            # Simple bar chart using native Streamlit
            st.bar_chart(df.set_index("Category")["Total"])
            
            # Table view
            st.dataframe(
                df.style.format({"Total": "${:,.2f}"}),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No expense data yet. Upload some receipts to see analytics!")
    
    # Tax tips section
    st.markdown("---")
    st.markdown("### 💡 HSA Tax Strategy Tips")
    
    tips_col1, tips_col2 = st.columns(2)
    
    with tips_col1:
        st.markdown("""
        **Triple Tax Advantage:**
        1. ✅ **Pre-tax contributions** reduce taxable income
        2. ✅ **Tax-free growth** on investments
        3. ✅ **Tax-free withdrawals** for qualified medical expenses
        
        **No Time Limit:**
        Keep receipts indefinitely — you can reimburse yourself years later!
        """)
    
    with tips_col2:
        st.markdown("""
        **Best Practices:**
        - 📸 Photograph receipts immediately
        - 📁 Store originals in a safe place
        - 💰 Pay out-of-pocket if you can afford it
        - 📈 Let HSA investments grow
        - 🏦 Reimburse yourself in retirement for tax-free income
        """)
    
    # Export functionality
    st.markdown("---")
    st.markdown("### 📤 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export All Receipts (CSV)", use_container_width=True):
            all_receipts = get_receipts()
            if all_receipts:
                import pandas as pd
                
                df = pd.DataFrame(all_receipts, columns=[
                    "ID", "Date", "Provider", "Amount", "Category", "Description",
                    "Reimbursed", "Reimbursed Date", "File Path", "OCR Text", "Created"
                ])
                
                csv = df.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"hsa_receipts_export_{date.today()}.csv",
                    mime="text/csv"
                )
            else:
                st.warning