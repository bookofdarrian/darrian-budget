import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json
from typing import List, Dict, Tuple, Optional
import math

st.set_page_config(page_title="Loan Amortization Calculator", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cursor = conn.cursor()
    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_schedules (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                loan_name VARCHAR(255) NOT NULL,
                loan_type VARCHAR(50) NOT NULL,
                principal DECIMAL(15, 2) NOT NULL,
                annual_rate DECIMAL(8, 5) NOT NULL,
                term_months INTEGER NOT NULL,
                start_date DATE NOT NULL,
                extra_payment DECIMAL(15, 2) DEFAULT 0,
                extra_payment_frequency VARCHAR(20) DEFAULT 'monthly',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_comparisons (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                comparison_name VARCHAR(255) NOT NULL,
                loan_ids TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                loan_name TEXT NOT NULL,
                loan_type TEXT NOT NULL,
                principal REAL NOT NULL,
                annual_rate REAL NOT NULL,
                term_months INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                extra_payment REAL DEFAULT 0,
                extra_payment_frequency TEXT DEFAULT 'monthly',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                comparison_name TEXT NOT NULL,
                loan_ids TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

def calculate_monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    if annual_rate == 0:
        return principal / term_months
    monthly_rate = annual_rate / 100 / 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
    return payment

def generate_amortization_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
    start_date: date,
    extra_payment: float = 0,
    extra_payment_frequency: str = 'monthly'
) -> List[Dict]:
    schedule = []
    balance = principal
    monthly_rate = annual_rate / 100 / 12
    base_payment = calculate_monthly_payment(principal, annual_rate, term_months)
    
    cumulative_interest = 0
    cumulative_principal = 0
    payment_number = 0
    current_date = start_date
    
    while balance > 0.01 and payment_number < term_months * 2:
        payment_number += 1
        interest_payment = balance * monthly_rate
        principal_payment = min(base_payment - interest_payment, balance)
        
        extra_this_month = 0
        if extra_payment_frequency == 'monthly':
            extra_this_month = extra_payment
        elif extra_payment_frequency == 'quarterly' and payment_number % 3 == 0:
            extra_this_month = extra_payment
        elif extra_payment_frequency == 'annually' and payment_number % 12 == 0:
            extra_this_month = extra_payment
        elif extra_payment_frequency == 'one_time' and payment_number == 1:
            extra_this_month = extra_payment
        
        extra_this_month = min(extra_this_month, balance - principal_payment)
        total_principal = principal_payment + extra_this_month
        total_payment = interest_payment + total_principal
        
        balance -= total_principal
        cumulative_interest += interest_payment
        cumulative_principal += total_principal
        
        schedule.append({
            'payment_number': payment_number,
            'payment_date': current_date,
            'payment': total_payment,
            'principal': total_principal,
            'interest': interest_payment,
            'extra_payment': extra_this_month,
            'balance': max(balance, 0),
            'cumulative_interest': cumulative_interest,
            'cumulative_principal': cumulative_principal
        })
        
        current_date = current_date + relativedelta(months=1)
    
    return schedule

# Main UI
st.title("🍑 Loan Amortization Calculator")

with st.sidebar:
    render_sidebar_brand()
    render_sidebar_user_widget()

tab1, tab2 = st.tabs(["Calculator", "Saved Loans"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Loan Details")
        loan_name = st.text_input("Loan Name", value="My Loan")
        principal = st.number_input(
            "Principal Amount ($)",
            min_value=0.0,
            value=250000.0,
            step=1000.0
        )
        annual_rate = st.number_input(
            "Annual Interest Rate (%)",
            min_value=0.0,
            max_value=30.0,
            value=6.5,
            step=0.125
        )
        term = st.number_input(
            "Loan Term (months)",
            min_value=1,
            max_value=480,
            value=360,
            step=12
        )
        start_date = st.date_input("Start Date", value=date.today())
    
    with col2:
        st.subheader("Extra Payments")
        extra_payment = st.number_input(
            "Extra Payment Amount ($)",
            min_value=0.0,
            value=0.0,
            step=100.0
        )
        extra_frequency = st.selectbox(
            "Extra Payment Frequency",
            options=['monthly', 'quarterly', 'annually', 'one_time'],
            index=0
        )
    
    if st.button("Calculate", type="primary"):
        schedule = generate_amortization_schedule(
            principal=principal,
            annual_rate=annual_rate,
            term_months=term,
            start_date=start_date,
            extra_payment=extra_payment,
            extra_payment_frequency=extra_frequency
        )
        
        if schedule:
            df = pd.DataFrame(schedule)
            
            st.subheader("Summary")
            col1, col2, col3, col4 = st.columns(4)
            monthly_payment = calculate_monthly_payment(principal, annual_rate, term)
            total_interest = df['cumulative_interest'].iloc[-1]
            total_paid = df['cumulative_principal'].iloc[-1] + total_interest
            months_saved = term - len(schedule)
            
            col1.metric("Monthly Payment", f"${monthly_payment:,.2f}")
            col2.metric("Total Interest", f"${total_interest:,.2f}")
            col3.metric("Total Paid", f"${total_paid:,.2f}")
            col4.metric("Months Saved", f"{months_saved}")
            
            st.subheader("Amortization Schedule")
            st.dataframe(df, use_container_width=True)
            
            st.subheader("Balance Over Time")
            fig = px.line(df, x='payment_number', y='balance', title='Loan Balance Over Time')
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Saved Loans")
    st.info("No saved loans yet. Use the calculator to create and save loans.")