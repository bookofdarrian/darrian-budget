import streamlit as st
import datetime
from decimal import Decimal
import calendar
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="RSU Vest Calendar + Tax Optimizer", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id SERIAL PRIMARY KEY,
                vest_date DATE NOT NULL,
                shares INTEGER NOT NULL,
                grant_price DECIMAL(12,2) NOT NULL,
                vest_price DECIMAL(12,2),
                withholding_pct DECIMAL(5,2) DEFAULT 22.00,
                sold BOOLEAN DEFAULT FALSE,
                sale_price DECIMAL(12,2),
                sale_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id SERIAL PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vest_date DATE NOT NULL,
                shares INTEGER NOT NULL,
                grant_price REAL NOT NULL,
                vest_price REAL,
                withholding_pct REAL DEFAULT 22.00,
                sold INTEGER DEFAULT 0,
                sale_price REAL,
                sale_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# Tax calculation constants and functions
FEDERAL_BRACKETS_2026 = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float('inf'), 0.37)
]

GEORGIA_BRACKETS = [
    (750, 0.01),
    (2250, 0.02),
    (3750, 0.03),
    (5250, 0.04),
    (7000, 0.05),
    (float('inf'), 0.055)
]

FICA_SOCIAL_SECURITY_RATE = 0.062
FICA_SOCIAL_SECURITY_CAP = 168600
FICA_MEDICARE_RATE = 0.0145
FICA_MEDICARE_ADDITIONAL_RATE = 0.009
FICA_MEDICARE_ADDITIONAL_THRESHOLD = 200000
NII_RATE = 0.038
NII_THRESHOLD = 200000

def calculate_federal_tax(income):
    """Calculate federal income tax using 2026 brackets"""
    tax = 0
    prev_bracket = 0
    for bracket, rate in FEDERAL_BRACKETS_2026:
        if income <= prev_bracket:
            break
        taxable_in_bracket = min(income, bracket) - prev_bracket
        tax += taxable_in_bracket * rate
        prev_bracket = bracket
    return tax

def calculate_georgia_tax(income):
    """Calculate Georgia state income tax"""
    tax = 0
    prev_bracket = 0
    for bracket, rate in GEORGIA_BRACKETS:
        if income <= prev_bracket:
            break
        taxable_in_bracket = min(income, bracket) - prev_bracket
        tax += taxable_in_bracket * rate
        prev_bracket = bracket
    return tax

def calculate_fica(income, ytd_income=0):
    """Calculate FICA taxes (Social Security + Medicare)"""
    ss_taxable = max(0, min(income, FICA_SOCIAL_SECURITY_CAP - ytd_income))
    ss_tax = ss_taxable * FICA_SOCIAL_SECURITY_RATE
    
    medicare_tax = income * FICA_MEDICARE_RATE
    if ytd_income + income > FICA_MEDICARE_ADDITIONAL_THRESHOLD:
        additional_medicare_income = max(0, ytd_income + income - FICA_MEDICARE_ADDITIONAL_THRESHOLD)
        medicare_tax += additional_medicare_income * FICA_MEDICARE_ADDITIONAL_RATE
    
    return ss_tax + medicare_tax

def calculate_nii_tax(investment_income, magi):
    """Calculate Net Investment Income Tax"""
    if magi <= NII_THRESHOLD:
        return 0
    taxable_nii = min(investment_income, magi - NII_THRESHOLD)
    return taxable_nii * NII_RATE

def format_vest_date_display(vest_date):
    """Format vest date for display"""
    vest_date_display = vest_date if isinstance(vest_date, datetime.date) else datetime.datetime.strptime(str(vest_date), "%Y-%m-%d").date()
    return vest_date_display.strftime("%B %d, %Y")

# Main page content
st.title("🍑 RSU Vest Calendar + Tax Optimizer")

st.markdown("""
This tool helps you track your RSU vests and optimize your tax strategy.
""")

# Add vest form
with st.expander("➕ Add New RSU Vest", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        new_vest_date = st.date_input("Vest Date", value=datetime.date.today())
        new_shares = st.number_input("Number of Shares", min_value=1, value=100)
        new_grant_price = st.number_input("Grant Price ($)", min_value=0.01, value=100.00, format="%.2f")
    with col2:
        new_vest_price = st.number_input("Vest Price ($)", min_value=0.01, value=150.00, format="%.2f")
        new_withholding = st.number_input("Withholding %", min_value=0.0, max_value=100.0, value=22.0, format="%.2f")
        new_notes = st.text_input("Notes (optional)")
    
    if st.button("Add Vest"):
        conn = get_conn()
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO rsu_vests (vest_date, shares, grant_price, vest_price, withholding_pct, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (new_vest_date, new_shares, new_grant_price, new_vest_price, new_withholding, new_notes))
        else:
            cur.execute("""
                INSERT INTO rsu_vests (vest_date, shares, grant_price, vest_price, withholding_pct, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_vest_date, new_shares, new_grant_price, new_vest_price, new_withholding, new_notes))
        conn.commit()
        conn.close()
        st.success("Vest added successfully!")
        st.rerun()

# Display existing vests
st.subheader("📅 Your RSU Vests")

conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT * FROM rsu_vests ORDER BY vest_date DESC")
vests = cur.fetchall()
conn.close()

if vests:
    for vest in vests:
        vest_id = vest[0]
        vest_date = vest[1]
        shares = vest[2]
        grant_price = float(vest[3]) if vest[3] else 0
        vest_price = float(vest[4]) if vest[4] else 0
        withholding_pct = float(vest[5]) if vest[5] else 22.0
        sold = vest[6]
        notes = vest[9] if len(vest) > 9 else ""
        
        vest_date_display = format_vest_date_display(vest_date)
        vest_value = shares * vest_price
        gain = shares * (vest_price - grant_price)
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.write(f"**{vest_date_display}**")
                if notes:
                    st.caption(notes)
            with col2:
                st.write(f"{shares} shares")
            with col3:
                st.write(f"Value: ${vest_value:,.2f}")
            with col4:
                st.write(f"Gain: ${gain:,.2f}")
            st.divider()
else:
    st.info("No RSU vests recorded yet. Add your first vest above!")

# Tax Summary
st.subheader("💰 Tax Summary")

if vests:
    total_shares = sum(v[2] for v in vests)
    total_value = sum(v[2] * (float(v[4]) if v[4] else 0) for v in vests)
    total_gain = sum(v[2] * ((float(v[4]) if v[4] else 0) - (float(v[3]) if v[3] else 0)) for v in vests)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Shares", f"{total_shares:,}")
    with col2:
        st.metric("Total Value", f"${total_value:,.2f}")
    with col3:
        st.metric("Total Gain", f"${total_gain:,.2f}")
    
    # Estimated taxes
    st.subheader("📊 Estimated Tax Liability")
    
    federal_tax = calculate_federal_tax(total_gain)
    georgia_tax = calculate_georgia_tax(total_gain)
    fica_tax = calculate_fica(total_gain)
    
    total_tax = federal_tax + georgia_tax + fica_tax
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Federal Tax", f"${federal_tax:,.2f}")
    with col2:
        st.metric("Georgia Tax", f"${georgia_tax:,.2f}")
    with col3:
        st.metric("FICA Tax", f"${fica_tax:,.2f}")
    with col4:
        st.metric("Total Estimated Tax", f"${total_tax:,.2f}")
else:
    st.info("Add RSU vests to see tax summary.")