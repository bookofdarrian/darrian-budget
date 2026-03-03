import streamlit as st
import datetime
import json
from decimal import Decimal
import base64

st.set_page_config(page_title="Insurance Tracker", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ph(count=1):
    return ", ".join(["%s"] * count) if USE_POSTGRES else ", ".join(["?"] * count)

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS insurance_policies (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            user_id INTEGER DEFAULT 1,
            policy_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            policy_number TEXT,
            coverage_amount REAL DEFAULT 0,
            deductible REAL DEFAULT 0,
            premium_amount REAL DEFAULT 0,
            premium_frequency TEXT DEFAULT 'monthly',
            start_date DATE,
            end_date DATE,
            renewal_date DATE,
            auto_renew INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS insurance_claims (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            policy_id INTEGER NOT NULL,
            claim_date DATE NOT NULL,
            claim_amount REAL DEFAULT 0,
            description TEXT,
            status TEXT DEFAULT 'pending',
            resolution_date DATE,
            payout_amount REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (policy_id) REFERENCES insurance_policies(id)
        )
    """)
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS insurance_documents (
            id {'SERIAL PRIMARY KEY' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'},
            policy_id INTEGER NOT NULL,
            document_name TEXT NOT NULL,
            document_type TEXT,
            file_data {'BYTEA' if USE_POSTGRES else 'BLOB'},
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (policy_id) REFERENCES insurance_policies(id)
        )
    """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def calculate_annual_premium_cost(user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT policy_type, premium_amount, premium_frequency 
        FROM insurance_policies 
        WHERE user_id = {_ph()}
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    total = 0
    by_type = {}
    
    frequency_multipliers = {
        'monthly': 12,
        'quarterly': 4,
        'semi-annual': 2,
        'annual': 1
    }
    
    for row in rows:
        policy_type, premium, frequency = row
        multiplier = frequency_multipliers.get(frequency, 12)
        annual = float(premium or 0) * multiplier
        total += annual
        by_type[policy_type] = by_type.get(policy_type, 0) + annual
    
    return total, by_type

def get_upcoming_renewals(user_id=1, days_ahead=90):
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.date.today()
    future_date = today + datetime.timedelta(days=days_ahead)
    
    cur.execute(f"""
        SELECT id, policy_type, provider, renewal_date, auto_renew
        FROM insurance_policies
        WHERE user_id = {_ph()} AND renewal_date IS NOT NULL
        AND renewal_date BETWEEN {_ph()} AND {_ph()}
        ORDER BY renewal_date ASC
    """, (user_id, today, future_date))
    rows = cur.fetchall()
    conn.close()
    
    renewals = []
    for row in rows:
        days_until = (row[3] - today).days if isinstance(row[3], datetime.date) else 0
        renewals.append({
            'id': row[0],
            'policy_type': row[1],
            'provider': row[2],
            'renewal_date': row[3],
            'auto_renew': row[4],
            'days_until': days_until
        })
    return renewals

def analyze_coverage_gaps(user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT policy_type, coverage_amount, deductible
        FROM insurance_policies
        WHERE user_id = {_ph()}
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    policies_by_type = {}
    for row in rows:
        ptype = row[0]
        if ptype not in policies_by_type:
            policies_by_type[ptype] = []
        policies_by_type[ptype].append({
            'coverage': row[1],
            'deductible': row[2]
        })
    
    gaps = []
    recommended_types = ['Health', 'Auto', 'Renters', 'Life', 'Umbrella']
    
    for rtype in recommended_types:
        if rtype not in policies_by_type:
            gaps.append(f"No {rtype} insurance policy found")
    
    return gaps

# Main page content
st.title("🍑 Insurance Tracker")

# Display annual premium cost
total_annual, by_type = calculate_annual_premium_cost()
st.metric("Total Annual Premium Cost", f"${total_annual:,.2f}")

if by_type:
    st.subheader("Premium Costs by Type")
    for ptype, cost in by_type.items():
        st.write(f"- {ptype}: ${cost:,.2f}")

# Display upcoming renewals
st.subheader("Upcoming Renewals (Next 90 Days)")
renewals = get_upcoming_renewals()
if renewals:
    for renewal in renewals:
        st.write(f"- {renewal['policy_type']} ({renewal['provider']}): {renewal['renewal_date']} - {renewal['days_until']} days away")
else:
    st.info("No upcoming renewals in the next 90 days")

# Display coverage gaps
st.subheader("Coverage Analysis")
gaps = analyze_coverage_gaps()
if gaps:
    for gap in gaps:
        st.warning(gap)
else:
    st.success("No coverage gaps detected")