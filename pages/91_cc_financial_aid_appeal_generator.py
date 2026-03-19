import streamlit as st
import json
from datetime import datetime
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Financial Aid Appeal Generator | College Confused", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

CC_THEME = """
<style>
:root {
    --cc-purple: #6B46C1;
    --cc-purple-dark: #553C9A;
    --cc-purple-light: #9F7AEA;
    --cc-bg: #1a1a2e;
    --cc-card: #16213e;
    --cc-text: #e2e8f0;
}
.cc-header {
    background: linear-gradient(135deg, var(--cc-purple) 0%, var(--cc-purple-dark) 100%);
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    color: white;
}
.cc-header h1 {
    margin: 0;
    font-size: 2.5rem;
}
.cc-header p {
    margin: 0.5rem 0 0 0;
    opacity: 0.9;
}
.cc-card {
    background: var(--cc-card);
    border: 1px solid var(--cc-purple);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.cc-stat {
    text-align: center;
    padding: 1rem;
    background: rgba(107, 70, 193, 0.2);
    border-radius: 8px;
    border: 1px solid var(--cc-purple-light);
}
.cc-stat h3 {
    color: var(--cc-purple-light);
    margin: 0;
    font-size: 2rem;
}
.cc-stat p {
    color: var(--cc-text);
    margin: 0.5rem 0 0 0;
    font-size: 0.9rem;
}
.status-draft { background-color: #4a5568; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
.status-submitted { background-color: #3182ce; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
.status-awaiting { background-color: #d69e2e; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
.status-approved { background-color: #38a169; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
.status-denied { background-color: #e53e3e; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
.appeal-letter {
    background: #1e1e2e;
    border: 1px solid var(--cc-purple);
    border-radius: 8px;
    padding: 1.5rem;
    font-family: 'Georgia', serif;
    line-height: 1.8;
    white-space: pre-wrap;
}
</style>
"""

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cc_financial_aid_appeals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                original_award DECIMAL(10,2),
                requested_amount DECIMAL(10,2),
                appeal_letter TEXT,
                family_circumstances TEXT,
                specific_ask TEXT,
                status TEXT DEFAULT 'Draft',
                response_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cc_comparator_awards (
                id SERIAL PRIMARY KEY,
                appeal_id INTEGER REFERENCES cc_financial_aid_appeals(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                total_cost DECIMAL(10,2),
                tuition DECIMAL(10,2),
                room_board DECIMAL(10,2),
                grants_scholarships DECIMAL(10,2),
                loans DECIMAL(10,2),
                work_study DECIMAL(10,2),
                net_cost DECIMAL(10,2),
                award_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cc_financial_aid_appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                original_award REAL,
                requested_amount REAL,
                appeal_letter TEXT,
                family_circumstances TEXT,
                specific_ask TEXT,
                status TEXT DEFAULT 'Draft',
                response_notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cc_comparator_awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appeal_id INTEGER REFERENCES cc_financial_aid_appeals(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                college_name TEXT NOT NULL,
                total_cost REAL,
                tuition REAL,
                room_board REAL,
                grants_scholarships REAL,
                loans REAL,
                work_study REAL,
                net_cost REAL,
                award_details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()

_ensure_tables()

st.markdown(CC_THEME, unsafe_allow_html=True)

st.markdown("""
<div class="cc-header">
    <h1>📝 Financial Aid Appeal Generator</h1>
    <p>Create compelling appeal letters to request more financial aid from colleges</p>
</div>
""", unsafe_allow_html=True)

# Get user_id from session
user_id = st.session_state.get('user_id', 1)

# Get existing appeals
conn = get_conn()
appeals = conn.execute(
    "SELECT * FROM cc_financial_aid_appeals WHERE user_id = ? ORDER BY created_at DESC",
    (user_id,)
).fetchall()

# Convert to list of dicts
appeal_list = []
for a in appeals:
    appeal_list.append({
        'id': a[0],
        'user_id': a[1],
        'college_name': a[2],
        'original_award': a[3],
        'requested_amount': a[4],
        'appeal_letter': a[5],
        'family_circumstances': a[6],
        'specific_ask': a[7],
        'status': a[8],
        'response_notes': a[9],
        'created_at': a[10],
        'updated_at': a[11]
    })

# Sidebar for existing appeals
with st.sidebar:
    render_sidebar_brand()
    render_sidebar_user_widget()
    
    st.markdown("### Your Appeals")
    
    appeal_options = [None] + [a['id'] for a in appeal_list]
    appeal_labels = ["+ New Appeal"] + [f"{a['college_name']} ({a['status']})" for a in appeal_list]
    
    selected_idx = st.selectbox(
        "Select an appeal",
        range(len(appeal_options)),
        format_func=lambda x: appeal_labels[x]
    )
    
    selected_appeal_id = appeal_options[selected_idx]

# Main content
if selected_appeal_id is None:
    st.subheader("Create New Appeal")
    
    with st.form("new_appeal_form"):
        college_name = st.text_input("College Name *")
        original_award = st.number_input("Original Award Amount ($)", min_value=0.0, step=1000.0)
        requested_amount = st.number_input("Requested Amount ($)", min_value=0.0, step=1000.0)
        family_circumstances = st.text_area("Family Circumstances", help="Describe any special circumstances")
        specific_ask = st.text_area("Specific Ask", help="What specifically are you requesting?")
        
        submitted = st.form_submit_button("Create Appeal")
        
        if submitted and college_name:
            conn.execute(
                """INSERT INTO cc_financial_aid_appeals 
                   (user_id, college_name, original_award, requested_amount, family_circumstances, specific_ask)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, college_name, original_award, requested_amount, family_circumstances, specific_ask)
            )
            conn.commit()
            st.success("Appeal created!")
            st.rerun()
else:
    # Display selected appeal
    appeal = next((a for a in appeal_list if a['id'] == selected_appeal_id), None)
    
    if appeal:
        st.subheader(f"Appeal for {appeal['college_name']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Award", f"${appeal['original_award']:,.2f}" if appeal['original_award'] else "N/A")
        with col2:
            st.metric("Requested Amount", f"${appeal['requested_amount']:,.2f}" if appeal['requested_amount'] else "N/A")
        with col3:
            st.markdown(f"**Status:** <span class='status-{appeal['status'].lower()}'>{appeal['status']}</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        if appeal['appeal_letter']:
            st.markdown("### Appeal Letter")
            st.markdown(f"<div class='appeal-letter'>{appeal['appeal_letter']}</div>", unsafe_allow_html=True)
        
        # Update status
        new_status = st.selectbox("Update Status", ["Draft", "Submitted", "Awaiting", "Approved", "Denied"], 
                                   index=["Draft", "Submitted", "Awaiting", "Approved", "Denied"].index(appeal['status']))
        
        if st.button("Update Status"):
            conn.execute(
                "UPDATE cc_financial_aid_appeals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, selected_appeal_id)
            )
            conn.commit()
            st.success("Status updated!")
            st.rerun()
        
        if st.button("Delete Appeal", type="secondary"):
            conn.execute("DELETE FROM cc_financial_aid_appeals WHERE id = ?", (selected_appeal_id,))
            conn.commit()
            st.success("Appeal deleted!")
            st.rerun()