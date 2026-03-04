import streamlit as st
import datetime
import calendar
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="RSU Vest Calendar & Tax Optimizer", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# === CONSTANTS ===
FEDERAL_SUPPLEMENTAL_RATE = Decimal("0.22")  # 22% federal supplemental wage rate
FEDERAL_HIGH_SUPPLEMENTAL_RATE = Decimal("0.37")  # 37% for amounts over $1M
GA_STATE_TAX_RATE = Decimal("0.0549")  # Georgia state tax rate (5.49% as of 2024)
SOCIAL_SECURITY_RATE = Decimal("0.062")  # 6.2% Social Security
MEDICARE_RATE = Decimal("0.0145")  # 1.45% Medicare
MEDICARE_ADDITIONAL_RATE = Decimal("0.009")  # 0.9% additional Medicare for high earners
SOCIAL_SECURITY_WAGE_BASE_2024 = Decimal("168600")  # 2024 SS wage base
MEDICARE_ADDITIONAL_THRESHOLD = Decimal("200000")  # Single filer threshold
SAFE_HARBOR_PERCENTAGE = Decimal("1.10")  # 110% of prior year tax for high earners
QUARTERLY_DUE_DATES = [
    (4, 15),  # Q1: April 15
    (6, 15),  # Q2: June 15
    (9, 15),  # Q3: September 15
    (1, 15),  # Q4: January 15 (next year)
]


def _ensure_tables():
    """Create RSU vests table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                vest_date DATE NOT NULL,
                shares INTEGER NOT NULL,
                price_at_vest DECIMAL(12, 2) NOT NULL,
                fmv DECIMAL(12, 2) NOT NULL,
                tax_withheld DECIMAL(12, 2) DEFAULT 0,
                sold BOOLEAN DEFAULT FALSE,
                sale_price DECIMAL(12, 2),
                sale_date DATE,
                company_name VARCHAR(100) DEFAULT 'Company',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1 UNIQUE,
                filing_status VARCHAR(20) DEFAULT 'single',
                prior_year_tax DECIMAL(12, 2) DEFAULT 0,
                prior_year_agi DECIMAL(12, 2) DEFAULT 0,
                ytd_wages DECIMAL(12, 2) DEFAULT 0,
                ytd_tax_withheld DECIMAL(12, 2) DEFAULT 0,
                expected_other_income DECIMAL(12, 2) DEFAULT 0,
                state VARCHAR(2) DEFAULT 'GA',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_quarterly_estimates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                tax_year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                amount_due DECIMAL(12, 2) DEFAULT 0,
                amount_paid DECIMAL(12, 2) DEFAULT 0,
                due_date DATE NOT NULL,
                paid_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, tax_year, quarter)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                vest_date TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price_at_vest REAL NOT NULL,
                fmv REAL NOT NULL,
                tax_withheld REAL DEFAULT 0,
                sold INTEGER DEFAULT 0,
                sale_price REAL,
                sale_date TEXT,
                company_name TEXT DEFAULT 'Company',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 UNIQUE,
                filing_status TEXT DEFAULT 'single',
                prior_year_tax REAL DEFAULT 0,
                prior_year_agi REAL DEFAULT 0,
                ytd_wages REAL DEFAULT 0,
                ytd_tax_withheld REAL DEFAULT 0,
                expected_other_income REAL DEFAULT 0,
                state TEXT DEFAULT 'GA',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_quarterly_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                tax_year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                amount_due REAL DEFAULT 0,
                amount_paid REAL DEFAULT 0,
                due_date TEXT NOT NULL,
                paid_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, tax_year, quarter)
            )
        """)
    
    conn.commit()
    conn.close()


# === TAX CALCULATION HELPERS ===

def calculate_federal_supplemental_tax(income: Decimal) -> Decimal:
    """Calculate federal tax on supplemental wages (RSU income)."""
    if income <= Decimal("1000000"):
        return income * FEDERAL_SUPPLEMENTAL_RATE
    else:
        # First $1M at 22%, excess at 37%
        base_tax = Decimal("1000000") * FEDERAL_SUPPLEMENTAL_RATE
        excess_tax = (income - Decimal("1000000")) * FEDERAL_HIGH_SUPPLEMENTAL_RATE
        return base_tax + excess_tax


def calculate_ga_state_tax(income: Decimal) -> Decimal:
    """Calculate Georgia state income tax."""
    return income * GA_STATE_TAX_RATE


def calculate_social_security_tax(income: Decimal, ytd_wages: Decimal = Decimal("0")) -> Decimal:
    """Calculate Social Security tax considering wage base limit."""
    remaining_base = max(Decimal("0"), SOCIAL_SECURITY_WAGE_BASE_2024 - ytd_wages)
    taxable_amount = min(income, remaining_base)
    return taxable_amount * SOCIAL_SECURITY_RATE


def calculate_medicare_tax(income: Decimal, ytd_wages: Decimal = Decimal("0")) -> Decimal:
    """Calculate Medicare tax including additional Medicare tax for high earners."""
    base_medicare = income * MEDICARE_RATE
    
    # Additional Medicare tax on income over threshold
    total_wages = ytd_wages + income
    if total_wages > MEDICARE_ADDITIONAL_THRESHOLD:
        excess_over_threshold = total_wages - MEDICARE_ADDITIONAL_THRESHOLD
        # Only apply to the portion of current income that's over threshold
        additional_taxable = min(income, excess_over_threshold)
        additional_medicare = additional_taxable * MEDICARE_ADDITIONAL_RATE
        return base_medicare + additional_medicare
    
    return base_medicare


def calculate_fica_taxes(income: Decimal, ytd_wages: Decimal = Decimal("0")) -> Dict[str, Decimal]:
    """Calculate both Social Security and Medicare taxes."""
    return {
        "social_security": calculate_social_security_tax(income, ytd_wages),
        "medicare": calculate_medicare_tax(income, ytd_wages),
    }


def calculate_total_tax_liability(
    rsu_income: Decimal,
    ytd_wages: Decimal = Decimal("0"),
    state: str = "GA"
) -> Dict[str, Decimal]:
    """Calculate complete tax liability for RSU vesting."""
    federal = calculate_federal_supplemental_tax(rsu_income)
    state_tax = calculate_ga_state_tax(rsu_income) if state == "GA" else Decimal("0")
    fica = calculate_fica_taxes(rsu_income, ytd_wages)
    
    total = federal + state_tax + fica["social_security"] + fica["medicare"]
    
    return {
        "federal": federal,
        "state": state_tax,
        "social_security": fica["social_security"],
        "medicare": fica["medicare"],
        "total": total,
        "effective_rate": (total / rsu_income * 100) if rsu_income > 0 else Decimal("0"),
    }


def calculate_safe_harbor_amount(prior_year_tax: Decimal, prior_year_agi: Decimal) -> Decimal:
    """Calculate safe harbor amount to avoid underpayment penalty."""
    # If AGI > $150K, must pay 110% of prior year tax
    if prior_year_agi > Decimal("150000"):
        return prior_year_tax * SAFE_HARBOR_PERCENTAGE
    else:
        return prior_year_tax


def check_underpayment_risk(
    ytd_tax_withheld: Decimal,
    estimated_annual_tax: Decimal,
    prior_year_tax: Decimal,
    prior_year_agi: Decimal
) -> Dict[str, Any]:
    """Check if there's an underpayment risk."""
    safe_harbor = calculate_safe_harbor_amount(prior_year_tax, prior_year_agi)
    
    # Current year liability method (90% of current year tax)
    current_year_method = estimated_annual_tax * Decimal("0.90")
    
    # Required payment is the lesser of the two methods
    required_payment = min(safe_harbor, current_year_method)
    
    shortfall = max(Decimal("0"), required_payment - ytd_tax_withheld)
    
    return {
        "safe_harbor_amount": safe_harbor,
        "current_year_method": current_year_method,
        "required_payment": required_payment,
        "ytd_withheld": ytd_tax_withheld,
        "shortfall": shortfall,
        "at_risk": shortfall > Decimal("0"),
        "risk_level": "HIGH" if shortfall > Decimal("5000") else "MEDIUM" if shortfall > Decimal("1000") else "LOW",
    }


def get_next_quarterly_due_date(from_date: datetime.date = None) -> Tuple[datetime.date, int]:
    """Get the next quarterly estimated tax payment due date."""
    if from_date is None:
        from_date = datetime.date.today()
    
    year = from_date.year
    
    for i, (month, day) in enumerate(QUARTERLY_DUE_DATES):
        # Q4 is due in January of next year
        due_year = year + 1 if i == 3 else year
        due_date = datetime.date(due_year, month, day)
        
        if due_date > from_date:
            return due_date, i + 1
    
    # If we're past all due dates, return Q1 of next year
    return datetime.date(year + 1, 4, 15), 1


# === DATABASE OPERATIONS ===

def get_all_vests(user_id: int = 1) -> List[Dict]:
    """Get all RSU vests for a user."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, vest_date, shares, price_at_vest, fmv, tax_withheld, 
               sold, sale_price, sale_date, company_name, notes
        FROM rsu_vests 
        WHERE user_id = {placeholder}
        ORDER BY vest_date DESC
    """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    vests = []
    for row in rows:
        vest_date = row[1]
        if isinstance(vest_date, str):
            vest_date = datetime.datetime.strptime(vest_date, "%Y-%m-%d").date()
        
        sale_date = row[8]
        if sale_date and isinstance(sale_date, str):
            sale_date = datetime.datetime.strptime(sale_date, "%Y-%m-%d").date()
        
        vests.append({
            "id": row[0],
            "vest_date": vest_date,
            "shares": row[2],
            "price_at_vest": Decimal(str(row[3])),
            "fmv": Decimal(str(row[4])),
            "tax_withheld": Decimal(str(row[5] or 0)),
            "sold": bool(row[6]),
            "sale_price": Decimal(str(row[7])) if row[7] else None,
            "sale_date": sale_date,
            "company_name": row[9] or "Company",
            "notes": row[10],
        })
    
    return vests


def add_vest(
    vest_date: datetime.date,
    shares: int,
    price_at_vest: Decimal,
    fmv: Decimal,
    tax_withheld: Decimal = Decimal("0"),
    company_name: str = "Company",
    notes: str = "",
    user_id: int = 1
) -> int:
    """Add a new RSU vest."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO rsu_vests (user_id, vest_date, shares, price_at_vest, fmv, tax_withheld, company_name, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, vest_date, shares, float(price_at_vest), float(fmv), float(tax_withheld), company_name, notes))
        vest_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO rsu_vests (user_id, vest_date, shares, price_at_vest, fmv, tax_withheld, company_name, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, vest_date.isoformat(), shares, float(price_at_vest), float(fmv), float(tax_withheld), company_name, notes))
        vest_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return vest_id


def update_vest(vest_id: int, **kwargs) -> bool:
    """Update an existing RSU vest."""
    if not kwargs:
        return False
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Build dynamic update query
    set_clauses = []
    values = []
    
    for key, value in kwargs.items():
        if key in ["vest_date", "shares", "price_at_vest", "fmv", "tax_withheld", 
                   "sold", "sale_price", "sale_date", "company_name", "notes"]:
            placeholder = "%s" if USE_POSTGRES else "?"
            set_clauses.append(f"{key} = {placeholder}")
            
            if isinstance(value, Decimal):
                value = float(value)
            elif isinstance(value, datetime.date) and not USE_POSTGRES:
                value = value.isoformat()
            elif key == "sold" and not USE_POSTGRES:
                value = 1 if value else 0
            
            values.append(value)
    
    if not set_clauses:
        conn.close()
        return False
    
    placeholder = "%s" if USE_POSTGRES else "?"
    values.append(vest_id)
    
    query = f"UPDATE rsu_vests SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = {placeholder}"
    cur.execute(query, values)
    
    conn.commit()
    conn.close()
    return True


def delete_vest(vest_id: int) -> bool:
    """Delete an RSU vest."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM rsu_vests WHERE id = {placeholder}", (vest_id,))
    
    conn.commit()
    conn.close()
    return True


def get_tax_settings(user_id: int = 1) -> Dict:
    """Get tax settings for a user."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT filing_status, prior_year_tax, prior_year_agi, ytd_wages, 
               ytd_tax_withheld, expected_other_income, state
        FROM rsu_tax_settings 
        WHERE user_id = {placeholder}
    """, (user_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "filing_status": row[0],
            "prior_year_tax": Decimal(str(row[1] or 0)),
            "prior_year_agi": Decimal(str(row[2] or 0)),
            "ytd_wages": Decimal(str(row[3] or 0)),
            "ytd_tax_withheld": Decimal(str(row[4] or 0)),
            "expected_other_income": Decimal(str(row[5] or 0)),
            "state": row[6] or "GA",
        }
    
    return {
        "filing_status": "single",
        "prior_year_tax": Decimal("0"),
        "prior_year_agi": Decimal("0"),
        "ytd_wages": Decimal("0"),
        "ytd_tax_withheld": Decimal("0"),
        "expected_other_income": Decimal("0"),
        "state": "GA",
    }


def save_tax_settings(settings: Dict, user_id: int = 1) -> bool:
    """Save tax settings for a user."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO rsu_tax_settings 
                (user_id, filing_status, prior_year_tax, prior_year_agi, ytd_wages, 
                 ytd_tax_withheld, expected_other_income, state)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                filing_status = EXCLUDED.filing_status,
                prior_year_tax = EXCLUDED.prior_year_tax,
                prior_year_agi = EXCLUDED.prior_year_agi,
                ytd_wages = EXCLUDED.ytd_wages,
                ytd_tax_withheld = EXCLUDED.ytd_tax_withheld,
                expected_other_income = EXCLUDED.expected_other_income,
                state = EXCLUDED.state,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id,
            settings["filing_status"],
            float(settings["prior_year_tax"]),
            float(settings["prior_year_agi"]),
            float(settings["ytd_wages"]),
            float(settings["ytd_tax_withheld"]),
            float(settings["expected_other_income"]),
            settings["state"],
        ))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO rsu_tax_settings 
                (user_id, filing_status, prior_year_tax, prior_year_agi, ytd_wages, 
                 ytd_tax_withheld, expected_other_income, state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            settings["filing_status"],
            float(settings["prior_year_tax"]),
            float(settings["prior_year_agi"]),
            float(settings["ytd_wages"]),
            float(settings["ytd_tax_withheld"]),
            float(settings["expected_other_income"]),
            settings["state"],
        ))
    
    conn.commit()
    conn.close()
    return True


def get_vests_for_year(year: int, user_id: int = 1) -> List[Dict]:
    """Get all vests for a specific year."""
    all_vests = get_all_vests(user_id)
    return [v for v in all_vests if v["vest_date"].year == year]


def get_vests_for_month(year: int, month: int, user_id: int = 1) -> List[Dict]:
    """Get all vests for a specific month."""
    all_vests = get_all_vests(user_id)
    return [v for v in all_vests if v["vest_date"].year == year and v["vest_date"].month == month]


# === UI COMPONENTS ===

def render_calendar_view(year: int, month: int, vests: List[Dict]):
    """Render a calendar view for a month with vest events."""
    cal = calendar.Calendar(firstweekday=6)  # Start week on Sunday
    month_days = cal.monthdayscalendar(year, month)
    
    # Create a mapping of days to vests
    vest_by_day = {}
    for vest in vests:
        day = vest["vest_date"].day
        if day not in vest_by_day:
            vest_by_day[day] = []
        vest_by_day[day].append(vest)
    
    # Header
    month_name = calendar.month_name[month]
    st.markdown(f"### {month_name} {year}")
    
    # Day headers
    cols = st.columns(7)
    for i, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
        cols[i].markdown(f"**{day_name}**")
    
    # Calendar grid
    today = datetime.date.today()
    
    for week in month_days:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].markdown("")
            else:
                is_today = (year == today.year and month == today.month and day == today.day)
                has_vest = day in vest_by_day
                
                # Style the day
                if has_vest:
                    total_value = sum(v["fmv"] for v in vest_by_day[day])
                    day_content = f"**{day}** 💰"
                    cols[i].markdown(f"<div style='background-color: #4CAF50; color: white; padding: 5px; border-radius: 5px; text-align: center;'>{day_content}<br/>${total_value:,.0f}</div>", unsafe_allow_html=True)
                elif is_today:
                    cols[i].markdown(f"<div style='background-color: #2196F3; color: white; padding: 5px; border-radius: 5px; text-align: center;'><b>{day}</b></div>", unsafe_allow_html=True)
                else:
                    cols[i].markdown(f"<div style='padding: 5px; text-align: center;'>{day}</div>", unsafe_allow_html=True)


def render_vest_form(editing_vest: Optional[Dict] = None):
    """Render the vest entry/edit form."""
    with st.form("vest_form", clear_on_submit=True):
        st.subheader("📝 " + ("Edit Vest" if editing_vest else "Add New Vest"))
        
        col1, col2 = st.columns(2)
        
        with col1:
            vest_date = st.date_input(
                "Vest Date",
                value=editing_vest["vest_date"] if editing_vest else datetime.date.today(),
            )
            shares = st.number_input(
                "Number of Shares",
                min_value=1,
                value=editing_vest["shares"] if editing_vest else 100,
            )
            price_at_vest = st.number_input(
                "Price at Vest ($)",
                min_value=0.01,
                value=float(editing_vest["price_at_vest"]) if editing_vest else 100.00,
                format="%.2f",
            )
        
        with col2:
            company_name = st.text_input(
                "Company Name",
                value=editing_vest["company_name"] if editing_vest else "Company",
            )
            tax_withheld = st.number_input(
                "Tax Withheld ($)",
                min_value=0.0,
                value=float(editing_vest["tax_withheld"]) if editing_vest else 0.0,
                format="%.2f",
            )
            notes = st.text_area(
                "Notes",
                value=editing_vest["notes"] if editing_vest else "",
            )
        
        # Auto-calculate FMV
        fmv = Decimal(str(shares)) * Decimal(str(price_at_vest))
        st.info(f"💵 Fair Market Value (FMV): **${fmv:,.2f}**")
        
        col_submit, col_cancel = st.columns(2)
        
        with col_submit:
            submitted = st.form_submit_button("💾 Save Vest", use_container_width=True)
        
        with col_cancel:
            if editing_vest:
                cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
            else:
                cancelled = False
        
        if submitted:
            return {
                "action": "save",
                "data": {
                    "vest_date": vest_date,
                    "shares": shares,
                    "price_at_vest": Decimal(str(price_at_vest)),
                    "fmv": fmv,
                    "tax_withheld": Decimal(str(tax_withheld)),
                    "company_name": company_name,
                    "notes": notes,
                }
            }
        elif cancelled:
            return {"action": "cancel"}
    
    return None


def render_tax_settings_form(current_settings: Dict):
    """Render the tax settings form."""
    with st.form("tax_settings_form"):
        st.subheader("⚙️ Tax Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            filing_status = st.selectbox(
                "Filing Status",
                options=["single", "married_filing_jointly", "married_filing_separately", "head_of_household"],
                index=["single", "married_filing_jointly", "married_filing_separately", "head_of_household"].index(current_settings["filing_status"]),
                format_func=lambda x: x.replace("_", " ").title(),
            )
            prior_year_tax = st.number_input(
                "Prior Year Total Tax ($)",
                min_value=0.0,
                value=float(current_settings["prior_year_tax"]),
                format="%.2f",
                help="From last year's tax return (Form 1040, line 24)",
            )
            prior_year_agi = st.number_input(
                "Prior Year AGI ($)",
                min_value=0.0,
                value=float(current_settings["prior_year_agi"]),
                format="%.2f",
                help="From last year's tax return (Form 1040, line 11)",
            )
        
        with col2:
            state = st.selectbox(
                "State",
                options=["GA", "Other"],
                index=0 if current_settings["state"] == "GA" else 1,
            )
            ytd_wages = st.number_input(
                "YTD W-2 Wages ($)",
                min_value=0.0,
                value=float(current_settings["ytd_wages"]),
                format="%.2f",
                help="Year-to-date wages from your paystub",
            )
            ytd_tax_withheld = st.number_input(
                "YTD Tax Withheld ($)",
                min_value=0.0,
                value=float(current_settings["ytd_tax_withheld"]),
                format="%.2f",
                help="Year-to-date federal tax withheld",
            )
        
        expected_other_income = st.number_input(
            "Expected Other Income ($)",
            min_value=0.0,
            value=float(current_settings["expected_other_income"]),
            format="%.2f",
            help="Interest, dividends, capital gains, etc.",
        )
        
        if st.form_submit_button("💾 Save Settings", use_container_width=True):
            return {
                "filing_status": filing_status,
                "prior_year_tax": Decimal(str(prior_year_tax)),
                "prior_year_agi": Decimal(str(prior_year_agi)),
                "ytd_wages": Decimal(str(ytd_wages)),
                "ytd_tax_withheld": Decimal(str(ytd_tax_withheld)),
                "expected_other_income": Decimal(str(expected_other_income)),
                "state": state,
            }
    
    return None


def render_underpayment_alerts(vests: List[Dict], tax_settings: Dict):
    """Render underpayment alerts and recommendations."""
    if not vests:
        st.info("📊 Add some vests to see underpayment analysis.")
        return
    
    # Calculate total RSU income for the year
    current_year = datetime.date.today().year
    year_vests = [v for v in vests if v["vest_date"].year == current_year]
    
    total_rsu_income = sum(v["fmv"] for v in year_vests)
    total_withheld = sum(v["tax_withheld"] for v in year_vests)
    
    if total_rsu_income == 0:
        st.info("📊 No vests recorded for the current year.")
        return