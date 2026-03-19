import streamlit as st
import json
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Annual Tax Projection Dashboard", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

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


def _ph(count=1):
    """Return correct placeholder(s) for SQL queries."""
    placeholder = "%s" if USE_POSTGRES else "?"
    if count == 1:
        return placeholder
    return ", ".join([placeholder] * count)


def _ensure_tables():
    """Create all necessary tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Tax projections summary table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS tax_projections (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            w2_income REAL DEFAULT 0,
            rsu_income REAL DEFAULT 0,
            espp_income REAL DEFAULT 0,
            side_income REAL DEFAULT 0,
            federal_withheld REAL DEFAULT 0,
            state_withheld REAL DEFAULT 0,
            estimated_payments REAL DEFAULT 0,
            deductions_json TEXT DEFAULT '{{}}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, year)
        )
    """)
    
    # Individual income entries table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS tax_income_entries (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            income_type TEXT NOT NULL,
            amount REAL NOT NULL,
            withholding REAL DEFAULT 0,
            entry_date DATE NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Estimated quarterly payments table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS tax_estimated_payments (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            federal_amount REAL DEFAULT 0,
            state_amount REAL DEFAULT 0,
            payment_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


# 2026 Federal Tax Brackets (MFJ - Married Filing Jointly used as default, can adjust)
FEDERAL_BRACKETS_2026_SINGLE = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float('inf'), 0.37)
]

FEDERAL_BRACKETS_2026_MFJ = [
    (23200, 0.10),
    (94300, 0.12),
    (201050, 0.22),
    (383900, 0.24),
    (487450, 0.32),
    (731200, 0.35),
    (float('inf'), 0.37)
]

# Georgia state tax - 5.49% flat rate for 2026
GA_STATE_RATE = 0.0549

# Standard deductions for 2026
STANDARD_DEDUCTION_SINGLE = 14600
STANDARD_DEDUCTION_MFJ = 29200

# RSU/ESPP supplemental withholding rates
FEDERAL_SUPPLEMENTAL_RATE = 0.22
GA_SUPPLEMENTAL_RATE = 0.06

# Self-employment tax rate
SE_TAX_RATE = 0.153  # 15.3% (12.4% SS + 2.9% Medicare)
SE_INCOME_THRESHOLD = 400

# SALT cap
SALT_CAP = 10000


def calculate_federal_tax(taxable_income: float, filing_status: str = "single") -> float:
    """Calculate federal income tax based on 2026 brackets."""
    brackets = FEDERAL_BRACKETS_2026_SINGLE if filing_status == "single" else FEDERAL_BRACKETS_2026_MFJ
    
    tax = 0.0
    prev_bracket = 0
    
    for bracket_max, rate in brackets:
        if taxable_income <= prev_bracket:
            break
        taxable_in_bracket = min(taxable_income, bracket_max) - prev_bracket
        tax += taxable_in_bracket * rate
        prev_bracket = bracket_max
    
    return round(tax, 2)


def calculate_ga_state_tax(taxable_income: float) -> float:
    """Calculate Georgia state tax at flat 5.49% rate."""
    if taxable_income <= 0:
        return 0.0
    return round(taxable_income * GA_STATE_RATE, 2)


def calculate_se_tax(side_income: float) -> tuple:
    """Calculate self-employment tax for side income over $400."""
    if side_income <= SE_INCOME_THRESHOLD:
        return 0.0, 0.0
    
    # SE tax is on 92.35% of net self-employment income
    se_income = side_income * 0.9235
    se_tax = se_income * SE_TAX_RATE
    
    # Deductible portion (employer half of SE tax)
    se_deduction = se_tax / 2
    
    return round(se_tax, 2), round(se_deduction, 2)


def calculate_effective_rate(tax: float, income: float) -> float:
    """Calculate effective tax rate."""
    if income <= 0:
        return 0.0
    return round((tax / income) * 100, 2)


def get_or_create_projection(user_id: int, year: int) -> dict:
    """Get or create a tax projection for the given year."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, w2_income, rsu_income, espp_income, side_income,
               federal_withheld, state_withheld, estimated_payments, deductions_json
        FROM tax_projections
        WHERE user_id = {_ph()} AND year = {_ph()}
    """, (user_id, year))
    
    row = cur.fetchone()
    
    if row:
        result = {
            'id': row[0],
            'w2_income': row[1] or 0,
            'rsu_income': row[2] or 0,
            'espp_income': row[3] or 0,
            'side_income': row[4] or 0,
            'federal_withheld': row[5] or 0,
            'state_withheld': row[6] or 0,
            'estimated_payments': row[7] or 0,
            'deductions': json.loads(row[8]) if row[8] else {}
        }
    else:
        cur.execute(f"""
            INSERT INTO tax_projections (user_id, year, deductions_json)
            VALUES ({_ph()}, {_ph()}, {_ph()})
        """, (user_id, year, '{}'))
        conn.commit()
        
        cur.execute(f"""
            SELECT id FROM tax_projections
            WHERE user_id = {_ph()} AND year = {_ph()}
        """, (user_id, year))
        new_id = cur.fetchone()[0]
        
        result = {
            'id': new_id,
            'w2_income': 0,
            'rsu_income': 0,
            'espp_income': 0,
            'side_income': 0,
            'federal_withheld': 0,
            'state_withheld': 0,
            'estimated_payments': 0,
            'deductions': {}
        }
    
    conn.close()
    return result


def update_projection(projection_id: int, **kwargs):
    """Update a tax projection."""
    conn = get_conn()
    cur = conn.cursor()
    
    updates = []
    values = []
    
    for key, value in kwargs.items():
        if key == 'deductions':
            updates.append(f"deductions_json = {_ph()}")
            values.append(json.dumps(value))
        else:
            updates.append(f"{key} = {_ph()}")
            values.append(value)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(projection_id)
    
    cur.execute(f"""
        UPDATE tax_projections
        SET {', '.join(updates)}
        WHERE id = {_ph()}
    """, values)
    
    conn.commit()
    conn.close()


def add_income_entry(user_id: int, year: int, income_type: str, amount: float, 
                     withholding: float, entry_date: date, notes: str = ""):
    """Add an income entry and update the projection totals."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO tax_income_entries 
        (user_id, year, income_type, amount, withholding, entry_date, notes)
        VALUES ({_ph(7)})
    """, (user_id, year, income_type, amount, withholding, entry_date, notes))
    
    conn.commit()
    conn.close()
    
    # Recalculate projection totals
    recalculate_projection_totals(user_id, year)


def get_income_entries(user_id: int, year: int) -> list:
    """Get all income entries for a user and year."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, income_type, amount, withholding, entry_date, notes, created_at
        FROM tax_income_entries
        WHERE user_id = {_ph()} AND year = {_ph()}
        ORDER BY entry_date DESC
    """, (user_id, year))
    
    rows = cur.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'income_type': r[1],
        'amount': r[2],
        'withholding': r[3],
        'entry_date': r[4],
        'notes': r[5],
        'created_at': r[6]
    } for r in rows]


def delete_income_entry(entry_id: int, user_id: int, year: int):
    """Delete an income entry and recalculate totals."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        DELETE FROM tax_income_entries
        WHERE id = {_ph()} AND user_id = {_ph()}
    """, (entry_id, user_id))
    
    conn.commit()
    conn.close()
    
    recalculate_projection_totals(user_id, year)


def recalculate_projection_totals(user_id: int, year: int):
    """Recalculate projection totals from income entries."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get totals by income type
    cur.execute(f"""
        SELECT income_type, SUM(amount), SUM(withholding)
        FROM tax_income_entries
        WHERE user_id = {_ph()} AND year = {_ph()}
        GROUP BY income_type
    """, (user_id, year))
    
    totals = {row[0]: {'amount': row[1], 'withholding': row[2]} for row in cur.fetchall()}
    
    w2_income = totals.get('W2', {}).get('amount', 0) or 0
    rsu_income = totals.get('RSU', {}).get('amount', 0) or 0
    espp_income = totals.get('ESPP', {}).get('amount', 0) or 0
    side_income = totals.get('1099', {}).get('amount', 0) or 0
    side_income += totals.get('Side Income', {}).get('amount', 0) or 0
    
    federal_withheld = sum(t.get('withholding', 0) or 0 for t in totals.values())
    
    # Estimate state withholding (typically ~6% of federal for GA)
    state_withheld = federal_withheld * 0.27  # Rough estimate
    
    # Update projection
    cur.execute(f"""
        UPDATE tax_projections
        SET w2_income = {_ph()}, rsu_income = {_ph()}, espp_income = {_ph()},
            side_income = {_ph()}, federal_withheld = {_ph()}, 
            state_withheld = {_ph()}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = {_ph()} AND year = {_ph()}
    """, (w2_income, rsu_income, espp_income, side_income, federal_withheld, 
          state_withheld, user_id, year))
    
    conn.commit()
    conn.close()


def get_estimated_payments(user_id: int, year: int) -> list:
    """Get estimated quarterly payments."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, quarter, federal_amount, state_amount, payment_date
        FROM tax_estimated_payments
        WHERE user_id = {_ph()} AND year = {_ph()}
        ORDER BY quarter
    """, (user_id, year))
    
    rows = cur.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'quarter': r[1],
        'federal_amount': r[2],
        'state_amount': r[3],
        'payment_date': r[4]
    } for r in rows]


def add_estimated_payment(user_id: int, year: int, quarter: int, 
                          federal_amount: float, state_amount: float, payment_date: date):
    """Add or update an estimated quarterly payment."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Check if payment exists
    cur.execute(f"""
        SELECT id FROM tax_estimated_payments
        WHERE user_id = {_ph()} AND year = {_ph()} AND quarter = {_ph()}
    """, (user_id, year, quarter))
    
    existing = cur.fetchone()
    
    if existing:
        cur.execute(f"""
            UPDATE tax_estimated_payments
            SET federal_amount = {_ph()}, state_amount = {_ph()}, payment_date = {_ph()}
            WHERE id = {_ph()}
        """, (federal_amount, state_amount, payment_date, existing[0]))
    else:
        cur.execute(f"""
            INSERT INTO tax_estimated_payments
            (user_id, year, quarter, federal_amount, state_amount, payment_date)
            VALUES ({_ph(6)})
        """, (user_id, year, quarter, federal_amount, state_amount, payment_date))
    
    conn.commit()
    conn.close()


def get_ai_tax_tips(projection: dict, tax_summary: dict, filing_status: str) -> str:
    """Get AI-powered tax optimization tips."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Set your Anthropic API key in Settings to get AI tax tips."
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are a tax advisor for a Visa TPM in Georgia. Analyze this 2026 tax projection and provide actionable tips:

**Income Summary:**
- W2 Income: ${projection['w2_income']:,.2f}
- RSU Vests: ${projection['rsu_income']:,.2f}
- ESPP Sales: ${projection['espp_income']:,.2f}
- Side Income (1099): ${projection['side_income']:,.2f}
- Total Gross: ${tax_summary['total_income']:,.2f}

**Withholdings:**
- Federal Withheld YTD: ${projection['federal_withheld']:,.2f}
- GA State Withheld YTD: ${projection['state_withheld']:,.2f}
- Estimated Payments Made: ${projection['estimated_payments']:,.2f}

**Estimated Liability:**
- Federal Tax: ${tax_summary['federal_tax']:,.2f}
- GA State Tax: ${tax_summary['state_tax']:,.2f}
- SE Tax (if applicable): ${tax_summary['se_tax']:,.2f}
- Total Tax: ${tax_summary['total_tax']:,.2f}

**Balance:**
- Balance Due (Refund): ${tax_summary['balance_due']:,.2f}
- Filing Status: {filing_status}

Provide 3-5 specific, actionable tips. Consider:
1. Underpayment penalty risk (safe harbor rules)
2. 401k contribution optimization
3. HSA max contribution opportunity
4. RSU withholding at 22% supplemental rate
5. Quarterly estimated payment timing
6. Any deduction opportunities

Keep tips concise and actionable. Start each tip with an emoji."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        return f"⚠️ Error getting AI tips: {str(e)}"


def calculate_full_tax_summary(projection: dict, filing_status: str) -> dict:
    """Calculate complete tax summary."""
    total_income = (projection['w2_income'] + projection['rsu_income'] + 
                   projection['espp_income'] + projection['side_income'])
    
    # Calculate SE tax and deduction
    se_tax, se_deduction = calculate_se_tax(projection['side_income'])
    
    # Get deductions
    deductions = projection.get('deductions', {})
    standard_ded = STANDARD_DEDUCTION_SINGLE if filing_status == 'single' else STANDARD_DEDUCTION_MFJ
    
    # Itemized deductions
    mortgage_interest = deductions.get('mortgage_interest', 0)
    salt_paid = min(deductions.get('salt', 0), SALT_CAP)  # SALT cap
    charitable = deductions.get('charitable', 0)
    other_itemized = deductions.get('other', 0)
    
    itemized_total = mortgage_interest + salt_paid + charitable + other_itemized
    
    # Use larger of standard or itemized
    use_itemized = itemized_total > standard_ded
    total_deductions = itemized_total if use_itemized else standard_ded
    
    # Add SE deduction (above the line)
    total_deductions += se_deduction
    
    # Add 401k and HSA contributions (if tracked)
    retirement_contrib = deductions.get('401k', 0) + deductions.get('hsa', 0)
    
    # Calculate taxable income
    taxable_income = max(0, total_income - total_deductions - retirement_contrib)
    
    # Calculate taxes
    federal_tax = calculate_federal_tax(taxable_income, filing_status)
    state_tax = calculate_ga_state_tax(taxable_income)
    
    # Total tax includes SE tax
    total_tax = federal_tax + state_tax + se_tax
    
    # Calculate balance due
    total_withheld = (projection['federal_withheld'] + projection['state_withheld'] + 
                      projection['estimated_payments'])
    balance_due = total_tax - total_withheld
    
    # Safe harbor check (110% of prior year or 100% of current year)
    # Simplified: check if withholdings cover 90% of current year liability
    safe_harbor_met = total_withheld >= (total_tax * 0.9)
    
    return {
        'total_income': total_income,
        'taxable_income': taxable_income,
        'total_deductions': total_deductions,
        'use_itemized': use_itemized,
        'standard_deduction': standard_ded,
        'itemized_deduction': itemized_total,
        'federal_tax': federal_tax,
        'state_tax': state_tax,
        'se_tax': se_tax,
        'se_deduction': se_deduction,
        'total_tax': total_tax,
        'total_withheld': total_withheld,
        'balance_due': balance_due,
        'safe_harbor_met': safe_harbor_met,
        'federal_effective_rate': calculate_effective_rate(federal_tax, total_income),
        'total_effective_rate': calculate_effective_rate(total_tax, total_income)
    }


# Initialize tables
_ensure_tables()

# Main UI
st.title("🧾 Annual Tax Projection Dashboard")
st.caption("Real-time YTD tax liability estimator — never be surprised in April")

user_id = st.session_state.get('user_id', 1)
current_year = datetime.now().year

# Year selector and filing status
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    selected_year = st.selectbox("Tax Year", [current_year, current_year + 1, current_year - 1], index=0)
with col2:
    filing_status = st.selectbox("Filing Status", ["single", "married_joint"], 
                                  format_func=lambda x: "Single" if x == "single" else "Married Filing Jointly")

# Get projection data
projection = get_or_create_projection(user_id, selected_year)
tax_summary = calculate_full_tax_summary(projection, filing_status)

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "💰 Income Entry", "✂️ Deductions", "📅 Estimated Payments", "🤖 AI Tips"
])

with tab1:
    st.subheader("YTD Income Summary")
    
    # Income summary cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("W2 Income", f"${projection['w2_income']:,.0f}")
    with col2:
        st.metric("RSU Vests", f"${projection['rsu_income']:,.0f}")
    with col3:
        st.metric("ESPP Sales", f"${projection['espp_income']:,.0f}")
    with col4:
        st.metric("Side Income", f"${projection['side_income']:,.0f}")
    
    # Total income
    st.metric("**Total Gross Income**", f"${tax_summary['total_income']:,.0f}", 
              help="Sum of all income sources before deductions")
    
    st.divider()
    
    # Tax Liability Gauge
    st.subheader("Estimated Tax Liability")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Federal Tax")
        st.metric("Estimated Federal Tax", f"${tax_summary['federal_tax']:,.0f}",
                  delta=f"{tax_summary['federal_effective_rate']:.1f}% effective rate",
                  delta_color="off")
        
        st.metric("Federal Withheld YTD", f"${projection['federal_withheld']:,.0f}")
        
        federal_balance = tax_summary['federal_tax'] - projection['federal_withheld'] - projection['estimated_payments']
        balance_color = "🔴" if federal_balance > 0 else "🟢"
        st.metric(f"{balance_color} Federal Balance", 
                  f"${abs(federal_balance):,.0f} {'Due' if federal_balance > 0 else 'Refund'}")
    
    with col2:
        st.markdown("### Georgia State Tax")
        st.metric("Estimated GA Tax", f"${tax_summary['state_tax']:,.0f}",
                  delta=f"{GA_STATE_RATE*100:.2f}% flat rate",
                  delta_color="off")
        
        st.metric("GA Withheld YTD", f"${projection['state_withheld']:,.0f}")
        
        state_balance = tax_summary['state_tax'] - projection['state_withheld']
        balance_color = "🔴" if state_balance > 0 else "🟢"
        st.metric(f"{balance_color} GA Balance",
                  f"${abs(state_balance):,.0f} {'Due' if state_balance > 0 else 'Refund'}")
    
    # Self-employment tax (if applicable)
    if tax_summary['se_tax'] > 0:
        st.divider()
        st.markdown("### Self-Employment Tax")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("SE Tax (15.3%)", f"${tax_summary['se_tax']:,.0f}",
                      help="Social Security (12.4%) + Medicare (2.9%) on side income")
        with col2:
            st.metric("SE Deduction", f"-${tax_summary['se_deduction']:,.0f}",
                      help="Deductible employer portion of SE tax")
    
    st.divider()
    
    # Overall Summary
    st.subheader("📊 Overall Tax Position")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Estimated Tax", f"${tax_summary['total_tax']:,.0f}")
    with col2:
        st.metric("Total Withheld/Paid", f"${tax_summary['total_withheld']:,.0f}")
    with col3:
        balance = tax_summary['balance_due']
        if balance > 0:
            st.metric("🔴 Balance Due", f"${balance:,.0f}", delta="Underpaid", delta_color="inverse")
        else:
            st.metric("🟢 Estimated Refund", f"${abs(balance):,.0f}", delta="Overpaid", delta_color="normal")
    
    # Safe Harbor Warning
    st.divider()
    if tax_summary['safe_harbor_met']:
        st.success("✅ **Safe Harbor Met** — Your withholdings cover at least 90% of estimated tax. No underpayment penalty expected.")
    else:
        shortfall = (tax_summary['total_tax'] * 0.9) - tax_summary['total_withheld']
        st.warning(f"""
        ⚠️ **Safe Harbor Warning** — You may owe an underpayment penalty.
        
        **Shortfall:** ${shortfall:,.0f} more needed to avoid penalty.
        
        **Options:**
        1. Increase W2 withholding (adjust W-4)
        2. Make estimated quarterly payment
        3. Increase 401k contributions to reduce taxable income
        """)
    
    # Deduction Summary
    st.divider()
    st.subheader("Deduction Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Standard Deduction", f"${tax_summary['standard_deduction']:,.0f}")
        st.metric("Itemized Total", f"${tax_summary['itemized_deduction']:,.0f}")
    with col2:
        method = "Itemized" if tax_summary['use_itemized'] else "Standard"
        st.metric(f"Using: {method}", f"${tax_summary['total_deductions']:,.0f}")
        st.metric("Taxable Income", f"${tax_summary['taxable_income']:,.0f}")

with tab2:
    st.subheader("📝 Income Entry")
    
    # Add new income entry
    with st.expander("➕ Add Income Entry", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            income_type = st.selectbox("Income Type", 
                                       ["W2", "RSU", "ESPP", "1099", "Side Income"],
                                       help="W2=Paycheck, RSU=Stock vests, ESPP=Employee stock purchase, 1099=Contract work")
            amount = st.number_input("Gross Amount ($)", min_value=0.0, step=100.0)
        with col2:
            withholding = st.number_input("Federal Withholding ($)", min_value=0.0, step=50.0,
                                          help="Amount withheld for federal taxes")
            entry_date = st.date_input("Date", value=date.today())
        
        notes = st.text_input("Notes (optional)", placeholder="e.g., Q1 RSU vest, February paycheck")
        
        # Auto-calculate supplemental withholding for RSU
        if income_type == "RSU":
            suggested_withholding = amount * FEDERAL_SUPPLEMENTAL_RATE
            st.info(f"💡 RSU Tip: Federal supplemental rate is 22%. Suggested withholding: ${suggested_withholding:,.0f}")
        
        if st.button("Add Entry", type="primary"):
            if amount > 0:
                add_income_entry(user_id, selected_year, income_type, amount, withholding, entry_date, notes)
                st.success(f"✅ Added {income_type} income entry: ${amount:,.2f}")
                st.re