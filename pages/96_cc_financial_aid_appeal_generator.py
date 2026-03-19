import streamlit as st
import json
from datetime import datetime, date
from decimal import Decimal
import os

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="CC: Financial Aid Appeal Generator", page_icon="🍑", layout="wide")

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_financial_aid_appeals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                school_name TEXT NOT NULL,
                original_award DECIMAL(12,2),
                requested_amount DECIMAL(12,2),
                appeal_reason TEXT,
                comparator_schools TEXT,
                appeal_letter_draft TEXT,
                status TEXT DEFAULT 'draft',
                submitted_date DATE,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_award_letters (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                school_name TEXT NOT NULL,
                tuition DECIMAL(12,2),
                grants DECIMAL(12,2),
                scholarships DECIMAL(12,2),
                loans DECIMAL(12,2),
                work_study DECIMAL(12,2),
                net_cost DECIMAL(12,2),
                upload_path TEXT,
                parsed_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_financial_aid_appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                school_name TEXT NOT NULL,
                original_award REAL,
                requested_amount REAL,
                appeal_reason TEXT,
                comparator_schools TEXT,
                appeal_letter_draft TEXT,
                status TEXT DEFAULT 'draft',
                submitted_date DATE,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cc_award_letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                school_name TEXT NOT NULL,
                tuition REAL,
                grants REAL,
                scholarships REAL,
                loans REAL,
                work_study REAL,
                net_cost REAL,
                upload_path TEXT,
                parsed_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# Helper functions
def get_user_id():
    return st.session_state.get("user_id", 1)

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def format_currency(amount):
    if amount is None:
        return "$0.00"
    return f"${float(amount):,.2f}"

def parse_award_letter_with_claude(text_content, school_name):
    """Use Claude to parse award letter text into structured data"""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None, "Anthropic API key not configured. Please set it in Settings."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""Analyze this financial aid award letter and extract the following information in JSON format:
- tuition: Total cost of attendance (tuition, fees, room, board)
- grants: Total grants (federal, state, institutional) - FREE money
- scholarships: Total scholarships - FREE money
- loans: Total loans offered (federal, private)
- work_study: Work-study amount offered
- net_cost: Calculate as tuition - grants - scholarships (do NOT subtract loans or work-study)

Return ONLY valid JSON with these exact keys. Use 0 for any missing values.

School: {school_name}
Award Letter Content:
{text_content}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        parsed_data = json.loads(response_text)
        return parsed_data, None
        
    except Exception as e:
        return None, f"Error parsing award letter: {str(e)}"

def generate_appeal_letter_with_claude(appeal_data):
    """Use Claude to generate an appeal letter"""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None, "Anthropic API key not configured. Please set it in Settings."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""Generate a professional financial aid appeal letter with the following details:

School Name: {appeal_data.get('school_name', '')}
Original Award: {format_currency(appeal_data.get('original_award', 0))}
Requested Amount: {format_currency(appeal_data.get('requested_amount', 0))}
Appeal Reason: {appeal_data.get('appeal_reason', '')}
Comparator Schools: {appeal_data.get('comparator_schools', '')}

Write a compelling, professional appeal letter that:
1. Opens with gratitude for the admission and initial award
2. Clearly states the request for additional aid
3. Provides specific reasons and evidence
4. References competing offers if applicable
5. Closes professionally with contact information placeholder

Return ONLY the letter text, ready to be customized with personal details."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text, None
        
    except Exception as e:
        return None, f"Error generating appeal letter: {str(e)}"

def save_award_letter(user_id, school_name, tuition, grants, scholarships, loans, work_study, net_cost, parsed_data=None):
    """Save award letter to database"""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        INSERT INTO cc_award_letters (user_id, school_name, tuition, grants, scholarships, loans, work_study, net_cost, parsed_data)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, school_name, tuition, grants, scholarships, loans, work_study, net_cost, json.dumps(parsed_data) if parsed_data else None))
    
    conn.commit()
    conn.close()

def get_award_letters(user_id):
    """Get all award letters for a user"""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        SELECT id, school_name, tuition, grants, scholarships, loans, work_study, net_cost, created_at
        FROM cc_award_letters
        WHERE user_id = {ph}
        ORDER BY created_at DESC
    """, (user_id,))
    
    results = cur.fetchall()
    conn.close()
    return results

def save_appeal(user_id, school_name, original_award, requested_amount, appeal_reason, comparator_schools, appeal_letter_draft, status='draft'):
    """Save appeal to database"""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        INSERT INTO cc_financial_aid_appeals (user_id, school_name, original_award, requested_amount, appeal_reason, comparator_schools, appeal_letter_draft, status)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, school_name, original_award, requested_amount, appeal_reason, comparator_schools, appeal_letter_draft, status))
    
    conn.commit()
    conn.close()

def get_appeals(user_id):
    """Get all appeals for a user"""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        SELECT id, school_name, original_award, requested_amount, appeal_reason, status, created_at, appeal_letter_draft
        FROM cc_financial_aid_appeals
        WHERE user_id = {ph}
        ORDER BY created_at DESC
    """, (user_id,))
    
    results = cur.fetchall()
    conn.close()
    return results

def delete_award_letter(letter_id):
    """Delete an award letter"""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"DELETE FROM cc_award_letters WHERE id = {ph}", (letter_id,))
    
    conn.commit()
    conn.close()

def delete_appeal(appeal_id):
    """Delete an appeal"""
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"DELETE FROM cc_financial_aid_appeals WHERE id = {ph}", (appeal_id,))
    
    conn.commit()
    conn.close()

# Main UI
st.title("📜 Financial Aid Appeal Generator")
st.markdown("Compare award letters and generate compelling appeal letters to maximize your financial aid.")

tab1, tab2, tab3 = st.tabs(["📊 Award Letters", "✍️ Create Appeal", "📁 My Appeals"])

with tab1:
    st.subheader("Enter Award Letter Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        school_name = st.text_input("School Name", key="award_school")
        tuition = st.number_input("Total Cost of Attendance", min_value=0.0, step=100.0, key="award_tuition")
        grants = st.number_input("Total Grants (Free Money)", min_value=0.0, step=100.0, key="award_grants")
        scholarships = st.number_input("Total Scholarships (Free Money)", min_value=0.0, step=100.0, key="award_scholarships")
    
    with col2:
        loans = st.number_input("Total Loans Offered", min_value=0.0, step=100.0, key="award_loans")
        work_study = st.number_input("Work-Study Amount", min_value=0.0, step=100.0, key="award_work_study")
        
        net_cost = tuition - grants - scholarships
        st.metric("Net Cost (Out of Pocket)", format_currency(net_cost))
    
    if st.button("Save Award Letter", type="primary"):
        if school_name:
            save_award_letter(get_user_id(), school_name, tuition, grants, scholarships, loans, work_study, net_cost)
            st.success(f"Award letter for {school_name} saved!")
            st.rerun()
        else:
            st.error("Please enter a school name.")
    
    st.markdown("---")
    st.subheader("Your Award Letters")
    
    letters = get_award_letters(get_user_id())
    
    if letters:
        for letter in letters:
            letter_id, school, tuit, gr, sch, ln, ws, nc, created = letter
            
            with st.expander(f"🎓 {school} - Net Cost: {format_currency(nc)}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Cost", format_currency(tuit))
                    st.metric("Grants", format_currency(gr))
                
                with col2:
                    st.metric("Scholarships", format_currency(sch))
                    st.metric("Loans", format_currency(ln))
                
                with col3:
                    st.metric("Work-Study", format_currency(ws))
                    st.metric("Net Cost", format_currency(nc))
                
                if st.button("🗑️ Delete", key=f"del_letter_{letter_id}"):
                    delete_award_letter(letter_id)
                    st.rerun()
    else:
        st.info("No award letters saved yet. Add your first one above!")

with tab2:
    st.subheader("Create Financial Aid Appeal")
    
    letters = get_award_letters(get_user_id())
    
    if letters:
        school_options = [l[1] for l in letters]
        selected_school = st.selectbox("Select School to Appeal", school_options)
        
        selected_letter = next((l for l in letters if l[1] == selected_school), None)
        
        if selected_letter:
            st.info(f"Current net cost at {selected_school}: {format_currency(selected_letter[7])}")
        
        requested_amount = st.number_input("Requested Additional Aid Amount", min_value=0.0, step=500.0)
        
        appeal_reason = st.text_area(
            "Reason for Appeal",
            placeholder="Describe your circumstances: changed financial situation, competing offers, special circumstances, etc."
        )
        
        other_schools = [s for s in school_options if s != selected_school]
        comparator_schools = st.multiselect("Comparator Schools (with better offers)", other_schools)
        
        if st.button("Generate Appeal Letter", type="primary"):
            if appeal_reason:
                with st.spinner("Generating appeal letter..."):
                    appeal_data = {
                        'school_name': selected_school,
                        'original_award': selected_letter[7] if selected_letter else 0,
                        'requested_amount': requested_amount,
                        'appeal_reason': appeal_reason,
                        'comparator_schools': ", ".join(comparator_schools)
                    }
                    
                    letter_text, error = generate_appeal_letter_with_claude(appeal_data)
                    
                    if error:
                        st.error(error)
                    else:
                        st.session_state['generated_letter'] = letter_text
                        st.session_state['appeal_data'] = appeal_data
                        st.success("Appeal letter generated!")
            else:
                st.error("Please provide a reason for your appeal.")
        
        if 'generated_letter' in st.session_state:
            st.markdown("---")
            st.subheader("Generated Appeal Letter")
            
            edited_letter = st.text_area(
                "Edit your letter",
                value=st.session_state['generated_letter'],
                height=400
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Save Appeal", type="primary"):
                    appeal_data = st.session_state['appeal_data']
                    save_appeal(
                        get_user_id(),
                        appeal_data['school_name'],
                        appeal_data['original_award'],
                        appeal_data['requested_amount'],
                        appeal_data['appeal_reason'],
                        appeal_data['comparator_schools'],
                        edited_letter
                    )
                    st.success("Appeal saved!")
                    del st.session_state['generated_letter']
                    del st.session_state['appeal_data']
                    st.rerun()
            
            with col2:
                st.download_button(
                    "📥 Download Letter",
                    edited_letter,
                    file_name=f"appeal_letter_{selected_school.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
    else:
        st.warning("Please add at least one award letter first to create an appeal.")

with tab3:
    st.subheader("Your Appeals")
    
    appeals = get_appeals(get_user_id())
    
    if appeals:
        for appeal in appeals:
            appeal_id, school, orig, req, reason, status, created, letter_draft = appeal
            
            status_colors = {
                'draft': '🟡',
                'submitted': '🔵',
                'approved': '🟢',
                'denied': '🔴'
            }
            
            with st.expander(f"{status_colors.get(status, '⚪')} {school} - {status.upper()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Original Net Cost", format_currency(orig))
                    st.write(f"**Reason:** {reason[:200]}..." if len(reason) > 200 else f"**Reason:** {reason}")
                
                with col2:
                    st.metric("Requested Additional Aid", format_currency(req))
                    st.write(f"**Created:** {created}")
                
                if letter_draft:
                    st.text_area("Appeal Letter", value=letter_draft, height=200, disabled=True, key=f"letter_{appeal_id}")
                    
                    st.download_button(
                        "📥 Download Letter",
                        letter_draft,
                        file_name=f"appeal_{school.replace(' ', '_')}.txt",
                        mime="text/plain",
                        key=f"download_{appeal_id}"
                    )
                
                if st.button("🗑️ Delete Appeal", key=f"del_appeal_{appeal_id}"):
                    delete_appeal(appeal_id)
                    st.rerun()
    else:
        st.info("No appeals created yet. Go to 'Create Appeal' to get started!")

st.markdown("---")
st.markdown("""
**Tips for a Successful Appeal:**
- Be specific about your circumstances
- Reference competing offers with specific numbers
- Maintain a professional, grateful tone
- Follow up within 1-2 weeks if no response
- Keep records of all communications
""")