import streamlit as st
import datetime
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar
from typing import Optional, List, Dict, Any, Tuple

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="RSU Vest Calendar + Tax Optimizer", page_icon="🍑", layout="wide")

init_db()
inject_css()
require_login()

# --- Constants for Tax Calculations ---
FEDERAL_SUPPLEMENTAL_RATE = Decimal("0.22")  # 22% federal supplemental wage rate
SOCIAL_SECURITY_RATE = Decimal("0.062")  # 6.2% Social Security
MEDICARE_RATE = Decimal("0.0145")  # 1.45% Medicare
ADDITIONAL_MEDICARE_RATE = Decimal("0.009")  # 0.9% additional Medicare over $200k
SOCIAL_SECURITY_WAGE_BASE_2024 = Decimal("168600")  # 2024 wage base
SOCIAL_SECURITY_WAGE_BASE_2025 = Decimal("176100")  # 2025 wage base (estimated)

# Georgia state tax brackets (2024)
GA_TAX_BRACKETS = [
    (Decimal("0"), Decimal("750"), Decimal("0.01")),
    (Decimal("750"), Decimal("2250"), Decimal("0.02")),
    (Decimal("2250"), Decimal("3750"), Decimal("0.03")),
    (Decimal("3750"), Decimal("5250"), Decimal("0.04")),
    (Decimal("5250"), Decimal("7000"), Decimal("0.05")),
    (Decimal("7000"), Decimal("999999999"), Decimal("0.055")),
]


def _ensure_tables():
    """Create required database tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                vest_date DATE NOT NULL,
                shares INTEGER NOT NULL,
                grant_price DECIMAL(12, 4) NOT NULL,
                vest_price DECIMAL(12, 4) NOT NULL,
                tax_withheld DECIMAL(12, 2) DEFAULT 0,
                sold_date DATE,
                sale_price DECIMAL(12, 4),
                grant_id VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1 UNIQUE,
                state_code VARCHAR(2) DEFAULT 'GA',
                filing_status VARCHAR(20) DEFAULT 'single',
                estimated_annual_income DECIMAL(12, 2) DEFAULT 0,
                ytd_social_security_wages DECIMAL(12, 2) DEFAULT 0,
                additional_withholding DECIMAL(12, 2) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS estimated_tax_payments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                tax_year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                payment_date DATE,
                federal_amount DECIMAL(12, 2) DEFAULT 0,
                state_amount DECIMAL(12, 2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_vests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                vest_date DATE NOT NULL,
                shares INTEGER NOT NULL,
                grant_price REAL NOT NULL,
                vest_price REAL NOT NULL,
                tax_withheld REAL DEFAULT 0,
                sold_date DATE,
                sale_price REAL,
                grant_id TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rsu_tax_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1 UNIQUE,
                state_code TEXT DEFAULT 'GA',
                filing_status TEXT DEFAULT 'single',
                estimated_annual_income REAL DEFAULT 0,
                ytd_social_security_wages REAL DEFAULT 0,
                additional_withholding REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS estimated_tax_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                tax_year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                payment_date DATE,
                federal_amount REAL DEFAULT 0,
                state_amount REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


def calculate_georgia_tax(income: Decimal) -> Decimal:
    """Calculate Georgia state income tax based on brackets."""
    tax = Decimal("0")
    for lower, upper, rate in GA_TAX_BRACKETS:
        if income > lower:
            taxable_in_bracket = min(income, upper) - lower
            tax += taxable_in_bracket * rate
    return tax


def calculate_rsu_taxes(
    vest_value: Decimal,
    ytd_ss_wages: Decimal = Decimal("0"),
    tax_year: int = 2024
) -> Dict[str, Decimal]:
    """Calculate taxes on RSU vest."""
    ss_wage_base = SOCIAL_SECURITY_WAGE_BASE_2024 if tax_year == 2024 else SOCIAL_SECURITY_WAGE_BASE_2025
    
    # Federal supplemental withholding
    federal_tax = vest_value * FEDERAL_SUPPLEMENTAL_RATE
    
    # Social Security (only up to wage base)
    ss_taxable = max(Decimal("0"), min(vest_value, ss_wage_base - ytd_ss_wages))
    social_security_tax = ss_taxable * SOCIAL_SECURITY_RATE
    
    # Medicare
    medicare_tax = vest_value * MEDICARE_RATE
    
    # Additional Medicare if over $200k
    if ytd_ss_wages + vest_value > Decimal("200000"):
        additional_medicare = vest_value * ADDITIONAL_MEDICARE_RATE
    else:
        additional_medicare = Decimal("0")
    
    # Georgia state tax
    state_tax = calculate_georgia_tax(vest_value)
    
    total_tax = federal_tax + social_security_tax + medicare_tax + additional_medicare + state_tax
    
    return {
        "federal": federal_tax,
        "social_security": social_security_tax,
        "medicare": medicare_tax,
        "additional_medicare": additional_medicare,
        "state": state_tax,
        "total": total_tax
    }


def main():
    """Main application function."""
    _ensure_tables()
    
    st.title("🍑 RSU Vest Calendar + Tax Optimizer")
    
    render_sidebar_brand()
    render_sidebar_user_widget()
    
    tab1, tab2, tab3 = st.tabs(["📅 Vest Calendar", "💰 Tax Calculator", "📊 Tax Payments"])
    
    with tab1:
        st.header("RSU Vest Calendar")
        st.info("Track your RSU vesting schedule here.")
        
    with tab2:
        st.header("Tax Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            vest_value = st.number_input("Vest Value ($)", min_value=0.0, value=10000.0, step=100.0)
            ytd_wages = st.number_input("YTD Social Security Wages ($)", min_value=0.0, value=0.0, step=1000.0)
            tax_year = st.selectbox("Tax Year", [2024, 2025], index=0)
        
        with col2:
            if st.button("Calculate Taxes"):
                taxes = calculate_rsu_taxes(
                    Decimal(str(vest_value)),
                    Decimal(str(ytd_wages)),
                    tax_year
                )
                
                st.subheader("Tax Breakdown")
                st.metric("Federal (22%)", f"${taxes['federal']:,.2f}")
                st.metric("Social Security (6.2%)", f"${taxes['social_security']:,.2f}")
                st.metric("Medicare (1.45%)", f"${taxes['medicare']:,.2f}")
                st.metric("Additional Medicare (0.9%)", f"${taxes['additional_medicare']:,.2f}")
                st.metric("Georgia State", f"${taxes['state']:,.2f}")
                st.metric("Total Estimated Tax", f"${taxes['total']:,.2f}")
                
                net_value = Decimal(str(vest_value)) - taxes['total']
                st.success(f"Net Value After Taxes: ${net_value:,.2f}")
    
    with tab3:
        st.header("Estimated Tax Payments")
        st.info("Track your quarterly estimated tax payments here.")


if __name__ == "__main__":
    main()