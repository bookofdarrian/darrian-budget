import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Student Loan Refinance Analyzer", page_icon="🍑", layout="wide")

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_loans (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                loan_name VARCHAR(255) NOT NULL,
                loan_type VARCHAR(100),
                servicer VARCHAR(255),
                original_balance DECIMAL(12,2) NOT NULL,
                current_balance DECIMAL(12,2) NOT NULL,
                interest_rate DECIMAL(5,4) NOT NULL,
                monthly_payment DECIMAL(10,2),
                start_date DATE,
                loan_term_months INTEGER,
                is_federal BOOLEAN DEFAULT FALSE,
                pslf_eligible BOOLEAN DEFAULT FALSE,
                pslf_payments_made INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS refinance_offers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                lender VARCHAR(255) NOT NULL,
                offered_rate DECIMAL(5,4) NOT NULL,
                term_months INTEGER NOT NULL,
                monthly_payment DECIMAL(10,2),
                total_interest DECIMAL(12,2),
                closing_costs DECIMAL(10,2) DEFAULT 0,
                offer_date DATE,
                expires_at DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS loan_payments (
                id SERIAL PRIMARY KEY,
                loan_id INTEGER NOT NULL REFERENCES student_loans(id) ON DELETE CASCADE,
                payment_date DATE NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                principal_paid DECIMAL(10,2),
                interest_paid DECIMAL(10,2),
                remaining_balance DECIMAL(12,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                loan_name TEXT NOT NULL,
                loan_type TEXT,
                servicer TEXT,
                original_balance REAL NOT NULL,
                current_balance REAL NOT NULL,
                interest_rate REAL NOT NULL,
                monthly_payment REAL,
                start_date TEXT,
                loan_term_months INTEGER,
                is_federal INTEGER DEFAULT 0,
                pslf_eligible INTEGER DEFAULT 0,
                pslf_payments_made INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS refinance_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lender TEXT NOT NULL,
                offered_rate REAL NOT NULL,
                term_months INTEGER NOT NULL,
                monthly_payment REAL,
                total_interest REAL,
                closing_costs REAL DEFAULT 0,
                offer_date TEXT,
                expires_at TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS loan_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                principal_paid REAL,
                interest_paid REAL,
                remaining_balance REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (loan_id) REFERENCES student_loans(id) ON DELETE CASCADE
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def calculate_monthly_payment(principal, annual_rate, term_months):
    if annual_rate == 0:
        return principal / term_months if term_months > 0 else 0
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal
    payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
    return payment

def calculate_total_interest(principal, monthly_payment, term_months):
    return (monthly_payment * term_months) - principal

def get_user_loans(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM student_loans WHERE user_id = {ph} ORDER BY current_balance DESC", (user_id,))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def get_refinance_offers(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM refinance_offers WHERE user_id = {ph} ORDER BY offered_rate ASC", (user_id,))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def add_loan(user_id, loan_data):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO student_loans (user_id, loan_name, loan_type, servicer, original_balance, 
            current_balance, interest_rate, monthly_payment, start_date, loan_term_months, 
            is_federal, pslf_eligible, pslf_payments_made)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, loan_data['loan_name'], loan_data['loan_type'], loan_data['servicer'],
          loan_data['original_balance'], loan_data['current_balance'], loan_data['interest_rate'],
          loan_data['monthly_payment'], loan_data['start_date'], loan_data['loan_term_months'],
          loan_data['is_federal'], loan_data['pslf_eligible'], loan_data['pslf_payments_made']))
    conn.commit()
    conn.close()

def add_refinance_offer(user_id, offer_data):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO refinance_offers (user_id, lender, offered_rate, term_months, monthly_payment,
            total_interest, closing_costs, offer_date, expires_at, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, offer_data['lender'], offer_data['offered_rate'], offer_data['term_months'],
          offer_data['monthly_payment'], offer_data['total_interest'], offer_data['closing_costs'],
          offer_data['offer_date'], offer_data['expires_at'], offer_data['notes']))
    conn.commit()
    conn.close()

def delete_loan(loan_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM student_loans WHERE id = {ph}", (loan_id,))
    conn.commit()
    conn.close()

def delete_offer(offer_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM refinance_offers WHERE id = {ph}", (offer_id,))
    conn.commit()
    conn.close()

# Main UI
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🎓 Student Loan Refinance Analyzer")

user_id = st.session_state.get("user_id", 1)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Add Loan", "💰 Refinance Offers", "📈 Analysis"])

with tab1:
    st.header("Your Student Loans")
    loans = get_user_loans(user_id)
    
    if loans:
        total_balance = sum(float(loan['current_balance']) for loan in loans)
        avg_rate = sum(float(loan['interest_rate']) * float(loan['current_balance']) for loan in loans) / total_balance if total_balance > 0 else 0
        total_monthly = sum(float(loan['monthly_payment'] or 0) for loan in loans)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Balance", f"${total_balance:,.2f}")
        col2.metric("Weighted Avg Rate", f"{avg_rate:.2%}")
        col3.metric("Total Monthly Payment", f"${total_monthly:,.2f}")
        
        st.subheader("Loan Details")
        for loan in loans:
            with st.expander(f"{loan['loan_name']} - ${float(loan['current_balance']):,.2f}"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Type:** {loan['loan_type']}")
                col1.write(f"**Servicer:** {loan['servicer']}")
                col2.write(f"**Interest Rate:** {float(loan['interest_rate']):.2%}")
                col2.write(f"**Monthly Payment:** ${float(loan['monthly_payment'] or 0):,.2f}")
                col3.write(f"**Federal:** {'Yes' if loan['is_federal'] else 'No'}")
                col3.write(f"**PSLF Eligible:** {'Yes' if loan['pslf_eligible'] else 'No'}")
                
                if st.button(f"Delete Loan", key=f"del_loan_{loan['id']}"):
                    delete_loan(loan['id'])
                    st.rerun()
    else:
        st.info("No loans added yet. Add your first loan in the 'Add Loan' tab.")

with tab2:
    st.header("Add New Loan")
    
    with st.form("add_loan_form"):
        loan_name = st.text_input("Loan Name", placeholder="e.g., Stafford Loan 2020")
        
        col1, col2 = st.columns(2)
        with col1:
            loan_type = st.selectbox("Loan Type", ["Direct Subsidized", "Direct Unsubsidized", "PLUS Loan", "Perkins Loan", "Private Loan", "Other"])
            servicer = st.text_input("Servicer", placeholder="e.g., Nelnet, FedLoan")
            original_balance = st.number_input("Original Balance ($)", min_value=0.0, step=100.0)
            current_balance = st.number_input("Current Balance ($)", min_value=0.0, step=100.0)
        
        with col2:
            interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=30.0, step=0.1) / 100
            monthly_payment = st.number_input("Monthly Payment ($)", min_value=0.0, step=10.0)
            start_date = st.date_input("Loan Start Date")
            loan_term_months = st.number_input("Loan Term (months)", min_value=1, max_value=360, value=120)
        
        col1, col2 = st.columns(2)
        with col1:
            is_federal = st.checkbox("Federal Loan")
        with col2:
            pslf_eligible = st.checkbox("PSLF Eligible")
        
        pslf_payments_made = st.number_input("PSLF Payments Made", min_value=0, max_value=120, value=0) if pslf_eligible else 0
        
        submitted = st.form_submit_button("Add Loan")
        if submitted:
            loan_data = {
                'loan_name': loan_name,
                'loan_type': loan_type,
                'servicer': servicer,
                'original_balance': original_balance,
                'current_balance': current_balance,
                'interest_rate': interest_rate,
                'monthly_payment': monthly_payment,
                'start_date': start_date.isoformat(),
                'loan_term_months': loan_term_months,
                'is_federal': is_federal,
                'pslf_eligible': pslf_eligible,
                'pslf_payments_made': pslf_payments_made
            }
            add_loan(user_id, loan_data)
            st.success("Loan added successfully!")
            st.rerun()

with tab3:
    st.header("Refinance Offers")
    
    loans = get_user_loans(user_id)
    total_balance = sum(float(loan['current_balance']) for loan in loans) if loans else 0
    
    with st.form("add_offer_form"):
        st.subheader("Add Refinance Offer")
        
        col1, col2 = st.columns(2)
        with col1:
            lender = st.text_input("Lender", placeholder="e.g., SoFi, Earnest")
            offered_rate = st.number_input("Offered Rate (%)", min_value=0.0, max_value=30.0, step=0.1) / 100
            term_months = st.selectbox("Term (months)", [60, 84, 120, 180, 240])
        
        with col2:
            closing_costs = st.number_input("Closing Costs ($)", min_value=0.0, step=50.0)
            offer_date = st.date_input("Offer Date")
            expires_at = st.date_input("Expires At", value=date.today() + timedelta(days=30))
        
        notes = st.text_area("Notes")
        
        # Calculate payment and interest
        if total_balance > 0 and offered_rate > 0:
            calc_monthly = calculate_monthly_payment(total_balance, offered_rate, term_months)
            calc_interest = calculate_total_interest(total_balance, calc_monthly, term_months)
            st.info(f"Estimated Monthly Payment: ${calc_monthly:,.2f} | Total Interest: ${calc_interest:,.2f}")
        
        submitted = st.form_submit_button("Add Offer")
        if submitted:
            monthly_payment = calculate_monthly_payment(total_balance, offered_rate, term_months)
            total_interest = calculate_total_interest(total_balance, monthly_payment, term_months)
            
            offer_data = {
                'lender': lender,
                'offered_rate': offered_rate,
                'term_months': term_months,
                'monthly_payment': monthly_payment,
                'total_interest': total_interest,
                'closing_costs': closing_costs,
                'offer_date': offer_date.isoformat(),
                'expires_at': expires_at.isoformat(),
                'notes': notes
            }
            add_refinance_offer(user_id, offer_data)
            st.success("Offer added successfully!")
            st.rerun()
    
    st.subheader("Saved Offers")
    offers = get_refinance_offers(user_id)
    
    if offers:
        for offer in offers:
            with st.expander(f"{offer['lender']} - {float(offer['offered_rate']):.2%}"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Rate:** {float(offer['offered_rate']):.2%}")
                col1.write(f"**Term:** {offer['term_months']} months")
                col2.write(f"**Monthly Payment:** ${float(offer['monthly_payment'] or 0):,.2f}")
                col2.write(f"**Total Interest:** ${float(offer['total_interest'] or 0):,.2f}")
                col3.write(f"**Closing Costs:** ${float(offer['closing_costs'] or 0):,.2f}")
                col3.write(f"**Expires:** {offer['expires_at']}")
                
                if offer['notes']:
                    st.write(f"**Notes:** {offer['notes']}")
                
                if st.button("Delete Offer", key=f"del_offer_{offer['id']}"):
                    delete_offer(offer['id'])
                    st.rerun()
    else:
        st.info("No refinance offers added yet.")

with tab4:
    st.header("Refinance Analysis")
    
    loans = get_user_loans(user_id)
    offers = get_refinance_offers(user_id)
    
    if loans and offers:
        total_balance = sum(float(loan['current_balance']) for loan in loans)
        current_monthly = sum(float(loan['monthly_payment'] or 0) for loan in loans)
        avg_rate = sum(float(loan['interest_rate']) * float(loan['current_balance']) for loan in loans) / total_balance
        
        st.subheader("Current Loans vs Refinance Options")
        
        comparison_data = []
        
        # Current loans projection (simplified)
        avg_term = 120  # Default assumption
        current_interest = calculate_total_interest(total_balance, current_monthly, avg_term) if current_monthly > 0 else 0
        
        comparison_data.append({
            'Option': 'Current Loans',
            'Rate': f"{avg_rate:.2%}",
            'Monthly Payment': f"${current_monthly:,.2f}",
            'Total Interest': f"${current_interest:,.2f}",
            'Total Cost': f"${total_balance + current_interest:,.2f}"
        })
        
        for offer in offers:
            comparison_data.append({
                'Option': offer['lender'],
                'Rate': f"{float(offer['offered_rate']):.2%}",
                'Monthly Payment': f"${float(offer['monthly_payment'] or 0):,.2f}",
                'Total Interest': f"${float(offer['total_interest'] or 0):,.2f}",
                'Total Cost': f"${total_balance + float(offer['total_interest'] or 0) + float(offer['closing_costs'] or 0):,.2f}"
            })
        
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True)
        
        # Best offer recommendation
        if offers:
            best_offer = min(offers, key=lambda x: float(x['total_interest'] or 0) + float(x['closing_costs'] or 0))
            best_savings = current_interest - (float(best_offer['total_interest'] or 0) + float(best_offer['closing_costs'] or 0))
            
            if best_savings > 0:
                st.success(f"💰 Best option: **{best_offer['lender']}** could save you **${best_savings:,.2f}** over the life of the loan!")
            else:
                st.warning("⚠️ Based on current analysis, keeping your existing loans may be more cost-effective.")
    else:
        st.info("Add loans and refinance offers to see comparison analysis.")