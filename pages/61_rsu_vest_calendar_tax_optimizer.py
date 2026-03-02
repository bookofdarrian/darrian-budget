import streamlit as st
import datetime
import calendar
import csv
import io
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="RSU Vest Calendar + Tax Optimizer", page_icon="🍑", layout="wide")
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

# 2024 Federal Tax Brackets (Single Filer)
FEDERAL_TAX_BRACKETS_SINGLE = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float('inf'), 0.37)
]

# 2024 Federal Tax Brackets (Married Filing Jointly)
FEDERAL_TAX_BRACKETS_MFJ = [
    (23200, 0.10),
    (94300, 0.12),
    (201050, 0.22),
    (383900, 0.24),
    (487450, 0.32),
    (731200, 0.35),
    (float('inf'), 0.37)
]

# Georgia State Tax Brackets (2024)
GEORGIA_TAX_BRACKETS = [
    (750, 0.01),
    (2250, 0.02),
    (3750, 0.03),
    (5250, 0.04),
    (7000, 0.05),
    (float('inf'), 0.0549)
]

# Supplemental wage withholding rates
FEDERAL_SUPPLEMENTAL_RATE = 0.22
GEORGIA_SUPPLEMENTAL_RATE = 0.0549
SOCIAL_SECURITY_RATE = 0.062
MEDICARE_RATE = 0.0145
SOCIAL_SECURITY_WAGE_BASE = 168600


def _ensure_tables():
    """Create required database tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                vest_date DATE NOT NULL,
                shares DECIMAL(12, 4) NOT NULL,
                grant_price DECIMAL(12, 4) NOT NULL,
                vest_price DECIMAL(12, 4) NOT NULL,
                withheld_amount DECIMAL(12, 2) DEFAULT 0,
                sold_amount DECIMAL(12, 2) DEFAULT 0,
                grant_id TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                filing_status TEXT DEFAULT 'single',
                state TEXT DEFAULT 'GA',
                base_salary DECIMAL(12, 2) DEFAULT 0,
                other_income DECIMAL(12, 2) DEFAULT 0,
                estimated_deductions DECIMAL(12, 2) DEFAULT 0,
                quarterly_payments DECIMAL(12, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                vest_date TEXT NOT NULL,
                shares REAL NOT NULL,
                grant_price REAL NOT NULL,
                vest_price REAL NOT NULL,
                withheld_amount REAL DEFAULT 0,
                sold_amount REAL DEFAULT 0,
                grant_id TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                filing_status TEXT DEFAULT 'single',
                state TEXT DEFAULT 'GA',
                base_salary REAL DEFAULT 0,
                other_income REAL DEFAULT 0,
                estimated_deductions REAL DEFAULT 0,
                quarterly_payments REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()


def get_user_id() -> int:
    """Get current user ID from session."""
    return st.session_state.get("user_id", 1)


def calculate_supplemental_withholding(income: float, state: str = "GA") -> Dict[str, float]:
    """Calculate supplemental wage withholding (22% federal + state)."""
    federal = income * FEDERAL_SUPPLEMENTAL_RATE
    
    if state == "GA":
        state_tax = income * GEORGIA_SUPPLEMENTAL_RATE
    else:
        state_tax = 0.0
    
    social_security = income * SOCIAL_SECURITY_RATE
    medicare = income * MEDICARE_RATE
    
    return {
        "federal": federal,
        "state": state_tax,
        "social_security": social_security,
        "medicare": medicare,
        "total": federal + state_tax + social_security + medicare
    }


def calculate_federal_tax(taxable_income: float, filing_status: str = "single") -> float:
    """Calculate federal income tax based on brackets."""
    if filing_status == "married_jointly":
        brackets = FEDERAL_TAX_BRACKETS_MFJ
    else:
        brackets = FEDERAL_TAX_BRACKETS_SINGLE
    
    tax = 0.0
    prev_limit = 0
    
    for limit, rate in brackets:
        if taxable_income <= prev_limit:
            break
        taxable_in_bracket = min(taxable_income, limit) - prev_limit
        tax += taxable_in_bracket * rate
        prev_limit = limit
    
    return tax


def calculate_georgia_tax(taxable_income: float) -> float:
    """Calculate Georgia state income tax based on brackets."""
    tax = 0.0
    prev_limit = 0
    
    for limit, rate in GEORGIA_TAX_BRACKETS:
        if taxable_income <= prev_limit:
            break
        taxable_in_bracket = min(taxable_income, limit) - prev_limit
        tax += taxable_in_bracket * rate
        prev_limit = limit
    
    return tax


def get_vests(user_id: int, year: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all RSU vests for a user, optionally filtered by year."""
    _ensure_tables()
    conn = get_conn()
    cur = conn.cursor()
    
    if year:
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, vest_date, shares, grant_price, vest_price, 
                       withheld_amount, sold_amount, grant_id, notes
                FROM rsu_vests 
                WHERE user_id = %s AND EXTRACT(YEAR FROM vest_date) = %s
                ORDER BY vest_date
            """, (user_id, year))
        else:
            cur.execute("""
                SELECT id, vest_date, shares, grant_price, vest_price,
                       withheld_amount, sold_amount, grant_id, notes
                FROM rsu_vests 
                WHERE user_id = ? AND strftime('%Y', vest_date) = ?
                ORDER BY vest_date
            """, (user_id, str(year)))
    else:
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, vest_date, shares, grant_price, vest_price,
                       withheld_amount, sold_amount, grant_id, notes
                FROM rsu_vests 
                WHERE user_id = %s
                ORDER BY vest_date
            """, (user_id,))
        else:
            cur.execute("""
                SELECT id, vest_date, shares, grant_price, vest_price,
                       withheld_amount, sold_amount, grant_id, notes
                FROM rsu_vests 
                WHERE user_id = ?
                ORDER BY vest_date
            """, (user_id,))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    vests = []
    for row in rows:
        vest_date = row[1]
        if isinstance(vest_date, str):
            vest_date = datetime.datetime.strptime(vest_date, "%Y-%m-%d").date()
        
        vests.append({
            "id": row[0],
            "vest_date": vest_date,
            "shares": float(row[2]),
            "grant_price": float(row[3]),
            "vest_price": float(row[4]),
            "withheld_amount": float(row[5] or 0),
            "sold_amount": float(row[6] or 0),
            "grant_id": row[7],
            "notes": row[8]
        })
    
    return vests


def add_vest(user_id: int, vest_date: datetime.date, shares: float, grant_price: float,
             vest_price: float, withheld_amount: float = 0, sold_amount: float = 0,
             grant_id: str = "", notes: str = "") -> int:
    """Add a new RSU vest record."""
    _ensure_tables()
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO rsu_vests (user_id, vest_date, shares, grant_price, vest_price,
                                   withheld_amount, sold_amount, grant_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, vest_date, shares, grant_price, vest_price,
              withheld_amount, sold_amount, grant_id, notes))
        vest_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO rsu_vests (user_id, vest_date, shares, grant_price, vest_price,
                                   withheld_amount, sold_amount, grant_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, vest_date.isoformat(), shares, grant_price, vest_price,
              withheld_amount, sold_amount, grant_id, notes))
        vest_id = cur.lastrowid
    
    conn.commit()
    cur.close()
    conn.close()
    
    return vest_id


def delete_vest(vest_id: int, user_id: int) -> bool:
    """Delete an RSU vest record."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM rsu_vests WHERE id = %s AND user_id = %s", (vest_id, user_id))
    else:
        cur.execute("DELETE FROM rsu_vests WHERE id = ? AND user_id = ?", (vest_id, user_id))
    
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    
    return deleted


def get_tax_settings(user_id: int) -> Dict[str, Any]:
    """Get tax settings for a user."""
    _ensure_tables()
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT filing_status, state, base_salary, other_income, 
                   estimated_deductions, quarterly_payments
            FROM rsu_tax_settings WHERE user_id = %s
        """, (user_id,))
    else:
        cur.execute("""
            SELECT filing_status, state, base_salary, other_income,
                   estimated_deductions, quarterly_payments
            FROM rsu_tax_settings WHERE user_id = ?
        """, (user_id,))
    
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return {
            "filing_status": row[0],
            "state": row[1],
            "base_salary": float(row[2] or 0),
            "other_income": float(row[3] or 0),
            "estimated_deductions": float(row[4] or 0),
            "quarterly_payments": float(row[5] or 0)
        }
    
    return {
        "filing_status": "single",
        "state": "GA",
        "base_salary": 0,
        "other_income": 0,
        "estimated_deductions": 0,
        "quarterly_payments": 0
    }


def save_tax_settings(user_id: int, settings: Dict[str, Any]) -> None:
    """Save tax settings for a user."""
    _ensure_tables()
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO rsu_tax_settings (user_id, filing_status, state, base_salary,
                                          other_income, estimated_deductions, quarterly_payments)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                filing_status = EXCLUDED.filing_status,
                state = EXCLUDED.state,
                base_salary = EXCLUDED.base_salary,
                other_income = EXCLUDED.other_income,
                estimated_deductions = EXCLUDED.estimated_deductions,
                quarterly_payments = EXCLUDED.quarterly_payments,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, settings["filing_status"], settings["state"],
              settings["base_salary"], settings["other_income"],
              settings["estimated_deductions"], settings["quarterly_payments"]))
    else:
        cur.execute("""
            INSERT INTO rsu_tax_settings (user_id, filing_status, state, base_salary,
                                          other_income, estimated_deductions, quarterly_payments)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                filing_status = excluded.filing_status,
                state = excluded.state,
                base_salary = excluded.base_salary,
                other_income = excluded.other_income,
                estimated_deductions = excluded.estimated_deductions,
                quarterly_payments = excluded.quarterly_payments,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, settings["filing_status"], settings["state"],
              settings["base_salary"], settings["other_income"],
              settings["estimated_deductions"], settings["quarterly_payments"]))
    
    conn.commit()
    cur.close()
    conn.close()


# Main app
st.title("📅 RSU Vest Calendar + Tax Optimizer")

user_id = get_user_id()
current_year = datetime.date.today().year

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📅 Calendar", "➕ Add Vest", "⚙️ Tax Settings", "📊 Tax Analysis"])

with tab1:
    st.subheader("RSU Vest Calendar")
    
    year = st.selectbox("Year", range(current_year - 2, current_year + 5), index=2)
    vests = get_vests(user_id, year)
    
    if vests:
        for vest in vests:
            vest_value = vest["shares"] * vest["vest_price"]
            st.write(f"**{vest['vest_date']}**: {vest['shares']} shares @ ${vest['vest_price']:.2f} = ${vest_value:,.2f}")
            if st.button(f"Delete", key=f"del_{vest['id']}"):
                delete_vest(vest['id'], user_id)
                st.rerun()
    else:
        st.info("No vests recorded for this year.")

with tab2:
    st.subheader("Add New Vest")
    
    with st.form("add_vest_form"):
        vest_date = st.date_input("Vest Date", datetime.date.today())
        shares = st.number_input("Number of Shares", min_value=0.0, step=0.01)
        grant_price = st.number_input("Grant Price ($)", min_value=0.0, step=0.01)
        vest_price = st.number_input("Vest Price ($)", min_value=0.0, step=0.01)
        grant_id = st.text_input("Grant ID (optional)")
        notes = st.text_area("Notes (optional)")
        
        if st.form_submit_button("Add Vest"):
            if shares > 0 and vest_price > 0:
                add_vest(user_id, vest_date, shares, grant_price, vest_price,
                        grant_id=grant_id, notes=notes)
                st.success("Vest added successfully!")
                st.rerun()
            else:
                st.error("Please enter valid share count and vest price.")

with tab3:
    st.subheader("Tax Settings")
    
    settings = get_tax_settings(user_id)
    
    with st.form("tax_settings_form"):
        filing_status = st.selectbox("Filing Status", 
                                     ["single", "married_jointly"],
                                     index=0 if settings["filing_status"] == "single" else 1)
        state = st.selectbox("State", ["GA", "Other"], 
                            index=0 if settings["state"] == "GA" else 1)
        base_salary = st.number_input("Base Salary ($)", value=settings["base_salary"], step=1000.0)
        other_income = st.number_input("Other Income ($)", value=settings["other_income"], step=100.0)
        estimated_deductions = st.number_input("Estimated Deductions ($)", 
                                               value=settings["estimated_deductions"], step=100.0)
        quarterly_payments = st.number_input("Quarterly Tax Payments ($)", 
                                            value=settings["quarterly_payments"], step=100.0)
        
        if st.form_submit_button("Save Settings"):
            save_tax_settings(user_id, {
                "filing_status": filing_status,
                "state": state,
                "base_salary": base_salary,
                "other_income": other_income,
                "estimated_deductions": estimated_deductions,
                "quarterly_payments": quarterly_payments
            })
            st.success("Settings saved!")

with tab4:
    st.subheader("Tax Analysis")
    
    analysis_year = st.selectbox("Analysis Year", range(current_year - 2, current_year + 2), 
                                  index=2, key="analysis_year")
    vests = get_vests(user_id, analysis_year)
    settings = get_tax_settings(user_id)
    
    if vests:
        total_vest_value = sum(v["shares"] * v["vest_price"] for v in vests)
        total_income = settings["base_salary"] + settings["other_income"] + total_vest_value
        taxable_income = max(0, total_income - settings["estimated_deductions"])
        
        federal_tax = calculate_federal_tax(taxable_income, settings["filing_status"])
        state_tax = calculate_georgia_tax(taxable_income) if settings["state"] == "GA" else 0
        
        withholding = calculate_supplemental_withholding(total_vest_value, settings["state"])
        
        st.metric("Total RSU Value", f"${total_vest_value:,.2f}")
        st.metric("Estimated Federal Tax", f"${federal_tax:,.2f}")
        st.metric("Estimated State Tax", f"${state_tax:,.2f}")
        st.metric("RSU Withholding (Supplemental)", f"${withholding['total']:,.2f}")
    else:
        st.info("No vests to analyze for this year.")