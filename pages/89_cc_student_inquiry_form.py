"""
Page 89: CC Student Inquiry Form
Public-facing form for students/parents to request college prep mentorship.

No authentication required. Public form for anyone to submit.
"""

import streamlit as st
import requests
from datetime import datetime, timedelta
import json

st.set_page_config(
    page_title="Get Mentorship | College Confused",
    page_icon="🎓",
    layout="wide"
)

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.cc_speed_to_lead import _ensure_cc_stl_tables, create_student_inquiry

init_db()

# ─── Initialize Tables ──────────────────────────────────────────────────────

def _ensure_tables():
    """Ensure CC Speed to Lead tables exist."""
    conn = get_conn()
    _ensure_cc_stl_tables(conn)
    conn.close()

_ensure_tables()

# ─── Constants ──────────────────────────────────────────────────────────────

GRADE_LEVELS = {
    "9th Grade": "9",
    "10th Grade": "10",
    "11th Grade": "11",
    "12th Grade": "12",
    "College Student": "college",
    "Other": "other"
}

GOALS = {
    "College List Help": "college_list",
    "Essay Help": "essays",
    "FAFSA / Financial Aid": "fafsa",
    "SAT/ACT Prep": "sat_act",
    "General Mentorship": "general",
    "Other": "other"
}

STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
    "Washington D.C.", "International"
]

RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW_MIN = 10
DARRIAN_USER_ID = 1  # Darrian's hardcoded user ID

# ─── Helper Functions ──────────────────────────────────────────────────────

def _get_client_ip():
    """Get client IP address (best effort)."""
    try:
        return requests.get("https://api.ipify.org").text
    except:
        return "unknown"

def _check_rate_limit(ip_address: str) -> Tuple[bool, int]:
    """
    Check if IP has exceeded rate limit.
    
    Returns:
        (allowed: bool, remaining: int)
    """
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    # Count submissions in last N minutes
    cutoff_time = datetime.utcnow() - timedelta(minutes=RATE_LIMIT_WINDOW_MIN)
    
    count_row = db_exec(conn, f"""
        SELECT COUNT(*) FROM cc_student_inquiries
        WHERE ip_address = {ph} AND created_at > datetime(?)
    """, (ip_address, cutoff_time.isoformat())).fetchone()
    
    count = count_row[0] if count_row else 0
    conn.close()
    
    allowed = count < RATE_LIMIT_MAX
    remaining = max(0, RATE_LIMIT_MAX - count)
    
    return allowed, remaining

def _validate_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[1]

def _submit_form(name, email, phone, grade_level, goal, region, major_interest):
    """
    Submit the inquiry form. Returns success/error tuple.
    """
    # Validate inputs
    if not name or len(name) < 2:
        return False, "❌ Please enter your full name."
    
    if not email or not _validate_email(email):
        return False, "❌ Please enter a valid email address."
    
    if not grade_level:
        return False, "❌ Please select your grade level."
    
    if not goal:
        return False, "❌ Please tell us what you need help with."
    
    if not region:
        return False, "❌ Please select your state/region."
    
    # Rate limiting
    client_ip = _get_client_ip()
    allowed, remaining = _check_rate_limit(client_ip)
    
    if not allowed:
        return False, f"⏳ Too many submissions. Please try again in {RATE_LIMIT_WINDOW_MIN} minutes."
    
    # Create inquiry
    try:
        conn = get_conn()
        inquiry_id = create_student_inquiry(
            email=email,
            phone=phone or None,
            name=name,
            grade_level=grade_level,
            goal=goal,
            region=region,
            major_interest=major_interest or None,
            ip_address=client_ip,
            conn=conn
        )
        conn.close()
        
        # Fetch the created inquiry to check routing
        conn = get_conn()
        ph = "%s" if USE_POSTGRES else "?"
        inquiry_row = db_exec(conn, f"""
            SELECT routed_to_mentor_id, qualification_status
            FROM cc_student_inquiries
            WHERE id = {ph}
        """, (inquiry_id,)).fetchone()
        
        routed_to_mentor = inquiry_row[0] if inquiry_row else None
        qualification_status = inquiry_row[1] if inquiry_row else None
        conn.close()
        
        if qualification_status == "unqualified":
            return False, "⚠️ Thanks for your interest. We couldn't verify your information. Please try again or email hello@collegeconfused.org."
        elif routed_to_mentor:
            return True, f"✅ Thanks! We've matched you with a mentor. You'll hear from them in the next 5 minutes."
        else:
            return True, f"⚠️ Thanks! We're matching you with a mentor. You'll hear from us within 24 hours."
    
    except Exception as e:
        if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
            return False, f"📧 Looks like you've already submitted with this email. Check your inbox for a response!"
        return False, f"❌ Something went wrong. Please try again or email hello@collegeconfused.org"

# ─── Page Layout ────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .hero-section {
        background: linear-gradient(135deg, #6C63FF 0%, #5A4FD9 100%);
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .hero-section h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    .hero-section p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.95;
    }
</style>
""", unsafe_allow_html=True)

# Hero section
st.markdown("""
<div class="hero-section">
    <h1>🎓 Get Mentored by College Experts</h1>
    <p>We connect you with mentors who've helped 500+ students land full-ride scholarships — zero cost, no signup.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Quick Inquiry Form")
st.markdown("Fill out the form below and we'll match you with the right mentor in minutes.")

# ─── Form ───────────────────────────────────────────────────────────────────

with st.form("student_inquiry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Your Name *", placeholder="e.g., Sarah Johnson")
        phone = st.text_input("Phone Number", placeholder="+1 (555) 123-4567")
    
    with col2:
        email = st.text_input("Email Address *", placeholder="your@email.com")
        grade_level = st.selectbox("Grade Level *", [""] + list(GRADE_LEVELS.keys()))
    
    goal = st.selectbox("What do you need help with? *", [""] + list(GOALS.keys()))
    
    col3, col4 = st.columns(2)
    
    with col3:
        region = st.selectbox("Your State/Region *", [""] + STATES)
    
    with col4:
        major_interest = st.text_input("Major/Field Interest", placeholder="e.g., Computer Science, Pre-Med")
    
    # Rate limit check (show CAPTCHA if needed)
    client_ip = _get_client_ip()
    allowed, remaining = _check_rate_limit(client_ip)
    
    if allowed:
        is_human = st.checkbox("I'm not a robot", value=False)
    else:
        st.warning(f"⏳ You've submitted {RATE_LIMIT_MAX - remaining} times in the last {RATE_LIMIT_WINDOW_MIN} minutes. Please wait before trying again.")
        is_human = False
    
    submitted = st.form_submit_button("📧 Submit Inquiry", type="primary", disabled=not is_human or not allowed)
    
    if submitted:
        success, message = _submit_form(
            name=name,
            email=email,
            phone=phone,
            grade_level=GRADE_LEVELS.get(grade_level, grade_level),
            goal=GOALS.get(goal, goal),
            region=region,
            major_interest=major_interest
        )
        
        if success:
            st.success(message)
            st.balloons()
            
            # Show what to expect
            st.markdown("""
            ### ✅ What Happens Next
            
            - **Warm email** from your mentor within 5 minutes
            - **Personalized guidance** tailored to YOUR goal
            - **Option to book** a free mentorship call
            - **No cost, ever** — College Confused is a nonprofit
            
            ### 📅 Schedule a Call Today
            Check your email and click the calendar link to book your first call!
            """)
        else:
            st.error(message)

# ─── Footer ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
### About College Confused
We're a nonprofit college prep platform founded by Darrian Belcher, who helped 25+ students get into college and secured $500K+ in scholarships.

**100% free.** No paywall. No gatekeeping. Just real mentors who've been there.

Have questions? Email: **hello@collegeconfused.org**
""")
