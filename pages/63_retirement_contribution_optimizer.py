import streamlit as st
import json
from datetime import datetime, date
from decimal import Decimal
import plotly.graph_objects as go
import plotly.express as px
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Retirement Contribution Optimizer", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS retirement_accounts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                account_type VARCHAR(50) NOT NULL,
                account_name VARCHAR(255) NOT NULL,
                current_balance DECIMAL(15,2) DEFAULT 0,
                annual_contribution DECIMAL(15,2) DEFAULT 0,
                employer_match_percent DECIMAL(5,2) DEFAULT 0,
                employer_match_limit DECIMAL(15,2) DEFAULT 0,
                contribution_limit DECIMAL(15,2) DEFAULT 0,
                is_roth BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contribution_scenarios (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                scenario_name VARCHAR(255) NOT NULL,
                annual_income DECIMAL(15,2) NOT NULL,
                filing_status VARCHAR(50) NOT NULL,
                current_age INTEGER NOT NULL,
                retirement_age INTEGER NOT NULL,
                expected_return DECIMAL(5,2) DEFAULT 7.0,
                inflation_rate DECIMAL(5,2) DEFAULT 3.0,
                contributions_json TEXT,
                projections_json TEXT,
                ai_recommendations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS retirement_user_profile (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                annual_income DECIMAL(15,2) DEFAULT 0,
                filing_status VARCHAR(50) DEFAULT 'single',
                current_age INTEGER DEFAULT 30,
                retirement_age INTEGER DEFAULT 65,
                risk_tolerance VARCHAR(50) DEFAULT 'moderate',
                state VARCHAR(50) DEFAULT 'GA',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS retirement_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_type TEXT NOT NULL,
                account_name TEXT NOT NULL,
                current_balance REAL DEFAULT 0,
                annual_contribution REAL DEFAULT 0,
                employer_match_percent REAL DEFAULT 0,
                employer_match_limit REAL DEFAULT 0,
                contribution_limit REAL DEFAULT 0,
                is_roth INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contribution_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                scenario_name TEXT NOT NULL,
                annual_income REAL NOT NULL,
                filing_status TEXT NOT NULL,
                current_age INTEGER NOT NULL,
                retirement_age INTEGER NOT NULL,
                expected_return REAL DEFAULT 7.0,
                inflation_rate REAL DEFAULT 3.0,
                contributions_json TEXT,
                projections_json TEXT,
                ai_recommendations TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS retirement_user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                annual_income REAL DEFAULT 0,
                filing_status TEXT DEFAULT 'single',
                current_age INTEGER DEFAULT 30,
                retirement_age INTEGER DEFAULT 65,
                risk_tolerance TEXT DEFAULT 'moderate',
                state TEXT DEFAULT 'GA',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

# 2026 Tax Brackets
TAX_BRACKETS_2026 = {
    'single': [
        (11600, 0.10),
        (47150, 0.12),
        (100525, 0.22),
        (191950, 0.24),
        (243725, 0.32),
        (609350, 0.35),
        (float('inf'), 0.37)
    ],
    'married_filing_jointly': [
        (23200, 0.10),
        (94300, 0.12),
        (201050, 0.22),
        (383900, 0.24),
        (487450, 0.32),
        (731200, 0.35),
        (float('inf'), 0.37)
    ],
    'married_filing_separately': [
        (11600, 0.10),
        (47150, 0.12),
        (100525, 0.22),
        (191950, 0.24),
        (243725, 0.32),
        (365600, 0.35),
        (float('inf'), 0.37)
    ],
    'head_of_household': [
        (16550, 0.10),
        (63100, 0.12),
        (100500, 0.22),
        (191950, 0.24),
        (243700, 0.32),
        (609350, 0.35),
        (float('inf'), 0.37)
    ]
}

# 2026 Contribution Limits
CONTRIBUTION_LIMITS_2026 = {
    '401k': 23500,
    '401k_catchup': 7500,
    'ira': 7000,
    'ira_catchup': 1000,
    'hsa_individual': 4300,
    'hsa_family': 8550,
    'hsa_catchup': 1000
}

def calculate_tax(income, filing_status):
    """Calculate federal tax based on income and filing status"""
    brackets = TAX_BRACKETS_2026.get(filing_status, TAX_BRACKETS_2026['single'])
    tax = 0
    prev_limit = 0
    for limit, rate in brackets:
        if income <= limit:
            tax += (income - prev_limit) * rate
            break
        else:
            tax += (limit - prev_limit) * rate
            prev_limit = limit
    return tax

def get_user_profile(user_id):
    """Get or create user profile"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM retirement_user_profile WHERE user_id = %s" if USE_POSTGRES else "SELECT * FROM retirement_user_profile WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        cols = ['id', 'user_id', 'annual_income', 'filing_status', 'current_age', 'retirement_age', 'risk_tolerance', 'state', 'updated_at']
        return dict(zip(cols, row))
    return None

def save_user_profile(user_id, data):
    """Save user profile"""
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO retirement_user_profile (user_id, annual_income, filing_status, current_age, retirement_age, risk_tolerance, state, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                annual_income = EXCLUDED.annual_income,
                filing_status = EXCLUDED.filing_status,
                current_age = EXCLUDED.current_age,
                retirement_age = EXCLUDED.retirement_age,
                risk_tolerance = EXCLUDED.risk_tolerance,
                state = EXCLUDED.state,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, data['annual_income'], data['filing_status'], data['current_age'], data['retirement_age'], data['risk_tolerance'], data['state']))
    else:
        cur.execute("""
            INSERT INTO retirement_user_profile (user_id, annual_income, filing_status, current_age, retirement_age, risk_tolerance, state, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                annual_income = excluded.annual_income,
                filing_status = excluded.filing_status,
                current_age = excluded.current_age,
                retirement_age = excluded.retirement_age,
                risk_tolerance = excluded.risk_tolerance,
                state = excluded.state,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, data['annual_income'], data['filing_status'], data['current_age'], data['retirement_age'], data['risk_tolerance'], data['state']))
    conn.commit()
    conn.close()

def get_retirement_accounts(user_id):
    """Get all retirement accounts for user"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM retirement_accounts WHERE user_id = %s AND is_active = TRUE ORDER BY account_name" if USE_POSTGRES else "SELECT * FROM retirement_accounts WHERE user_id = ? AND is_active = 1 ORDER BY account_name", (user_id,))
    rows = cur.fetchall()
    conn.close()
    cols = ['id', 'user_id', 'account_type', 'account_name', 'current_balance', 'annual_contribution', 'employer_match_percent', 'employer_match_limit', 'contribution_limit', 'is_roth', 'is_active', 'created_at', 'updated_at']
    return [dict(zip(cols, row)) for row in rows]

def save_retirement_account(user_id, data):
    """Save retirement account"""
    conn = get_conn()
    cur = conn.cursor()
    if data.get('id'):
        if USE_POSTGRES:
            cur.execute("""
                UPDATE retirement_accounts SET
                    account_type = %s, account_name = %s, current_balance = %s,
                    annual_contribution = %s, employer_match_percent = %s, employer_match_limit = %s,
                    contribution_limit = %s, is_roth = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
            """, (data['account_type'], data['account_name'], data['current_balance'],
                  data['annual_contribution'], data['employer_match_percent'], data['employer_match_limit'],
                  data['contribution_limit'], data['is_roth'], data['id'], user_id))
        else:
            cur.execute("""
                UPDATE retirement_accounts SET
                    account_type = ?, account_name = ?, current_balance = ?,
                    annual_contribution = ?, employer_match_percent = ?, employer_match_limit = ?,
                    contribution_limit = ?, is_roth = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (data['account_type'], data['account_name'], data['current_balance'],
                  data['annual_contribution'], data['employer_match_percent'], data['employer_match_limit'],
                  data['contribution_limit'], data['is_roth'], data['id'], user_id))
    else:
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO retirement_accounts (user_id, account_type, account_name, current_balance,
                    annual_contribution, employer_match_percent, employer_match_limit, contribution_limit, is_roth)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, data['account_type'], data['account_name'], data['current_balance'],
                  data['annual_contribution'], data['employer_match_percent'], data['employer_match_limit'],
                  data['contribution_limit'], data['is_roth']))
        else:
            cur.execute("""
                INSERT INTO retirement_accounts (user_id, account_type, account_name, current_balance,
                    annual_contribution, employer_match_percent, employer_match_limit, contribution_limit, is_roth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, data['account_type'], data['account_name'], data['current_balance'],
                  data['annual_contribution'], data['employer_match_percent'], data['employer_match_limit'],
                  data['contribution_limit'], data['is_roth']))
    conn.commit()
    conn.close()

def delete_retirement_account(account_id, user_id):
    """Soft delete retirement account"""
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("UPDATE retirement_accounts SET is_active = FALSE WHERE id = %s AND user_id = %s", (account_id, user_id))
    else:
        cur.execute("UPDATE retirement_accounts SET is_active = 0 WHERE id = ? AND user_id = ?", (account_id, user_id))
    conn.commit()
    conn.close()

def calculate_projections(profile, accounts, years_to_project=None):
    """Calculate retirement projections"""
    if not profile:
        return []
    
    if years_to_project is None:
        years_to_project = profile['retirement_age'] - profile['current_age']
    
    projections = []
    current_balance = sum(float(a['current_balance'] or 0) for a in accounts)
    annual_contribution = sum(float(a['annual_contribution'] or 0) for a in accounts)
    employer_match = sum(min(float(a['annual_contribution'] or 0) * float(a['employer_match_percent'] or 0) / 100, float(a['employer_match_limit'] or 0)) for a in accounts)
    
    expected_return = 0.07  # 7% default
    inflation_rate = 0.03  # 3% default
    
    for year in range(years_to_project + 1):
        age = profile['current_age'] + year
        # Apply growth
        if year > 0:
            current_balance = current_balance * (1 + expected_return) + annual_contribution + employer_match
        
        real_balance = current_balance / ((1 + inflation_rate) ** year)
        
        projections.append({
            'year': year,
            'age': age,
            'balance': current_balance,
            'real_balance': real_balance,
            'contributions': annual_contribution * year if year > 0 else 0,
            'employer_match_total': employer_match * year if year > 0 else 0
        })
    
    return projections

def optimize_contributions(profile, accounts):
    """Generate optimization recommendations"""
    if not profile or not accounts:
        return []
    
    recommendations = []
    annual_income = float(profile.get('annual_income', 0))
    
    for account in accounts:
        contribution = float(account['annual_contribution'] or 0)
        match_percent = float(account['employer_match_percent'] or 0)
        match_limit = float(account['employer_match_limit'] or 0)
        
        # Check if getting full employer match
        if match_percent > 0 and match_limit > 0:
            needed_for_full_match = (match_limit / match_percent) * 100
            if contribution < needed_for_full_match:
                recommendations.append({
                    'account': account['account_name'],
                    'type': 'employer_match',
                    'priority': 'high',
                    'message': f"Increase contribution to ${needed_for_full_match:,.0f} to get full employer match of ${match_limit:,.0f}"
                })
    
    # Check contribution limits
    total_401k = sum(float(a['annual_contribution'] or 0) for a in accounts if '401k' in a['account_type'].lower())
    if total_401k < CONTRIBUTION_LIMITS_2026['401k']:
        remaining = CONTRIBUTION_LIMITS_2026['401k'] - total_401k
        recommendations.append({
            'account': '401(k)',
            'type': 'limit',
            'priority': 'medium',
            'message': f"You can contribute ${remaining:,.0f} more to your 401(k) before hitting the limit"
        })
    
    return recommendations

# Main UI
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🍑 Retirement Contribution Optimizer")
st.markdown("Optimize your retirement contributions for maximum tax efficiency and growth")

user_id = st.session_state.get('user_id', 1)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Profile", "💼 Accounts", "📈 Projections", "🎯 Optimizer"])

with tab1:
    st.subheader("Your Financial Profile")
    
    profile = get_user_profile(user_id)
    
    col1, col2 = st.columns(2)
    
    with col1:
        annual_income = st.number_input("Annual Income", value=float(profile['annual_income']) if profile else 75000.0, step=1000.0, format="%.2f")
        filing_status = st.selectbox("Filing Status", 
            options=['single', 'married_filing_jointly', 'married_filing_separately', 'head_of_household'],
            index=['single', 'married_filing_jointly', 'married_filing_separately', 'head_of_household'].index(profile['filing_status']) if profile else 0)
        current_age = st.number_input("Current Age", value=profile['current_age'] if profile else 30, min_value=18, max_value=100)
    
    with col2:
        retirement_age = st.number_input("Target Retirement Age", value=profile['retirement_age'] if profile else 65, min_value=50, max_value=100)
        risk_tolerance = st.selectbox("Risk Tolerance",
            options=['conservative', 'moderate', 'aggressive'],
            index=['conservative', 'moderate', 'aggressive'].index(profile['risk_tolerance']) if profile else 1)
        state = st.text_input("State", value=profile['state'] if profile else 'GA')
    
    if st.button("Save Profile", type="primary"):
        save_user_profile(user_id, {
            'annual_income': annual_income,
            'filing_status': filing_status,
            'current_age': current_age,
            'retirement_age': retirement_age,
            'risk_tolerance': risk_tolerance,
            'state': state
        })
        st.success("Profile saved!")
        st.rerun()

with tab2:
    st.subheader("Retirement Accounts")
    
    accounts = get_retirement_accounts(user_id)
    
    # Add new account form
    with st.expander("➕ Add New Account"):
        col1, col2 = st.columns(2)
        with col1:
            new_account_type = st.selectbox("Account Type", options=['401k', '403b', 'Traditional IRA', 'Roth IRA', 'Roth 401k', 'HSA', 'SEP IRA'])
            new_account_name = st.text_input("Account Name", placeholder="e.g., Company 401k")
            new_balance = st.number_input("Current Balance", value=0.0, step=100.0)
        with col2:
            new_contribution = st.number_input("Annual Contribution", value=0.0, step=100.0)
            new_match_percent = st.number_input("Employer Match %", value=0.0, step=0.5)
            new_match_limit = st.number_input("Employer Match Limit ($)", value=0.0, step=100.0)
        
        new_is_roth = st.checkbox("Is Roth Account?")
        
        if st.button("Add Account"):
            save_retirement_account(user_id, {
                'account_type': new_account_type,
                'account_name': new_account_name,
                'current_balance': new_balance,
                'annual_contribution': new_contribution,
                'employer_match_percent': new_match_percent,
                'employer_match_limit': new_match_limit,
                'contribution_limit': CONTRIBUTION_LIMITS_2026.get(new_account_type.lower().replace(' ', ''), 0),
                'is_roth': new_is_roth
            })
            st.success("Account added!")
            st.rerun()
    
    # Display existing accounts
    for account in accounts:
        with st.expander(f"💼 {account['account_name']} ({account['account_type']})"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.metric("Balance", f"${float(account['current_balance'] or 0):,.2f}")
                st.metric("Annual Contribution", f"${float(account['annual_contribution'] or 0):,.2f}")
            with col2:
                st.metric("Employer Match", f"{float(account['employer_match_percent'] or 0):.1f}%")
                st.metric("Match Limit", f"${float(account['employer_match_limit'] or 0):,.2f}")
            with col3:
                if st.button("🗑️ Delete", key=f"del_{account['id']}"):
                    delete_retirement_account(account['id'], user_id)
                    st.rerun()

with tab3:
    st.subheader("Retirement Projections")
    
    profile = get_user_profile(user_id)
    accounts = get_retirement_accounts(user_id)
    
    if profile and accounts:
        projections = calculate_projections(profile, accounts)
        
        if projections:
            # Create projection chart
            fig = go.Figure()
            
            years = [p['year'] for p in projections]
            balances = [p['balance'] for p in projections]
            real_balances = [p['real_balance'] for p in projections]
            
            fig.add_trace(go.Scatter(x=years, y=balances, mode='lines', name='Nominal Balance', line=dict(color='#4CAF50', width=3)))
            fig.add_trace(go.Scatter(x=years, y=real_balances, mode='lines', name='Real Balance (Inflation Adjusted)', line=dict(color='#2196F3', width=3, dash='dash')))
            
            fig.update_layout(
                title='Retirement Balance Projection',
                xaxis_title='Years',
                yaxis_title='Balance ($)',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            final = projections[-1]
            with col1:
                st.metric("Projected Balance at Retirement", f"${final['balance']:,.0f}")
            with col2:
                st.metric("Real Value (Today's Dollars)", f"${final['real_balance']:,.0f}")
            with col3:
                st.metric("Total Contributions", f"${final['contributions']:,.0f}")
            with col4:
                st.metric("Total Employer Match", f"${final['employer_match_total']:,.0f}")
    else:
        st.info("Please set up your profile and add retirement accounts to see projections.")

with tab4:
    st.subheader("Contribution Optimizer")
    
    profile = get_user_profile(user_id)
    accounts = get_retirement_accounts(user_id)
    
    if profile and accounts:
        recommendations = optimize_contributions(profile, accounts)
        
        if recommendations:
            for rec in recommendations:
                priority_color = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rec['priority'], '⚪')
                st.markdown(f"{priority_color} **{rec['account']}**: {rec['message']}")
        else:
            st.success("Your retirement contributions are well optimized!")
        
        # Tax impact analysis
        st.subheader("Tax Impact Analysis")
        
        annual_income = float(profile['annual_income'])
        pre_tax_contributions = sum(float(a['annual_contribution'] or 0) for a in accounts if not a['is_roth'])
        
        tax_without_contributions = calculate_tax(annual_income, profile['filing_status'])
        tax_with_contributions = calculate_tax(annual_income - pre_tax_contributions, profile['filing_status'])
        tax_savings = tax_without_contributions - tax_with_contributions
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tax Without Contributions", f"${tax_without_contributions:,.0f}")
        with col2:
            st.metric("Tax With Contributions", f"${tax_with_contributions:,.0f}")
        with col3:
            st.metric("Annual Tax Savings", f"${tax_savings:,.0f}", delta=f"-${tax_savings:,.0f}")
    else:
        st.info("Please set up your profile and add retirement accounts to see optimization recommendations.")