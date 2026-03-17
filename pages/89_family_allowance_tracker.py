import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Family Allowance Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                age INTEGER,
                avatar_emoji VARCHAR(10) DEFAULT '👤',
                allowance_amount DECIMAL(10,2) DEFAULT 0,
                payout_frequency VARCHAR(20) DEFAULT 'weekly',
                next_payout_date DATE,
                current_balance DECIMAL(10,2) DEFAULT 0,
                spending_limit_daily DECIMAL(10,2),
                spending_limit_weekly DECIMAL(10,2),
                restricted_categories TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_chores (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                point_value INTEGER DEFAULT 1,
                bonus_amount DECIMAL(10,2) DEFAULT 0,
                frequency VARCHAR(20) DEFAULT 'daily',
                is_required BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chore_completions (
                id SERIAL PRIMARY KEY,
                chore_id INTEGER REFERENCES allowance_chores(id) ON DELETE CASCADE,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                completed_date DATE NOT NULL,
                verified_by VARCHAR(100),
                notes TEXT,
                points_earned INTEGER DEFAULT 0,
                bonus_earned DECIMAL(10,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                transaction_type VARCHAR(20) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                category VARCHAR(50),
                description TEXT,
                transaction_date DATE NOT NULL,
                balance_after DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_savings_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                target_amount DECIMAL(10,2) NOT NULL,
                current_amount DECIMAL(10,2) DEFAULT 0,
                target_date DATE,
                priority INTEGER DEFAULT 1,
                auto_save_percent INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_payouts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                payout_date DATE NOT NULL,
                base_amount DECIMAL(10,2) NOT NULL,
                bonus_amount DECIMAL(10,2) DEFAULT 0,
                deductions DECIMAL(10,2) DEFAULT 0,
                final_amount DECIMAL(10,2) NOT NULL,
                auto_save_amount DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                age INTEGER,
                avatar_emoji VARCHAR(10) DEFAULT '👤',
                allowance_amount DECIMAL(10,2) DEFAULT 0,
                payout_frequency VARCHAR(20) DEFAULT 'weekly',
                next_payout_date DATE,
                current_balance DECIMAL(10,2) DEFAULT 0,
                spending_limit_daily DECIMAL(10,2),
                spending_limit_weekly DECIMAL(10,2),
                restricted_categories TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_chores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                point_value INTEGER DEFAULT 1,
                bonus_amount DECIMAL(10,2) DEFAULT 0,
                frequency VARCHAR(20) DEFAULT 'daily',
                is_required BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chore_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chore_id INTEGER REFERENCES allowance_chores(id) ON DELETE CASCADE,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                completed_date DATE NOT NULL,
                verified_by VARCHAR(100),
                notes TEXT,
                points_earned INTEGER DEFAULT 0,
                bonus_earned DECIMAL(10,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                transaction_type VARCHAR(20) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                category VARCHAR(50),
                description TEXT,
                transaction_date DATE NOT NULL,
                balance_after DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                target_amount DECIMAL(10,2) NOT NULL,
                current_amount DECIMAL(10,2) DEFAULT 0,
                target_date DATE,
                priority INTEGER DEFAULT 1,
                auto_save_percent INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_payouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                family_member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                payout_date DATE NOT NULL,
                base_amount DECIMAL(10,2) NOT NULL,
                bonus_amount DECIMAL(10,2) DEFAULT 0,
                deductions DECIMAL(10,2) DEFAULT 0,
                final_amount DECIMAL(10,2) NOT NULL,
                auto_save_amount DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()

_ensure_tables()

def render_sidebar():
    render_sidebar_brand()
    render_sidebar_user_widget()

def get_family_members(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM family_members WHERE user_id = ? AND is_active = TRUE" if not USE_POSTGRES else "SELECT * FROM family_members WHERE user_id = %s AND is_active = TRUE", (user_id,))
    rows = cur.fetchall()
    if rows:
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    return []

def process_payout(user_id, member_id, amount):
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    
    # Update balance
    cur.execute(f"UPDATE family_members SET current_balance = current_balance + {placeholder} WHERE id = {placeholder}", (amount, member_id))
    
    # Record transaction
    cur.execute(f"""
        INSERT INTO allowance_transactions (user_id, family_member_id, transaction_type, amount, description, transaction_date)
        VALUES ({placeholder}, {placeholder}, 'payout', {placeholder}, 'Allowance payout', {placeholder})
    """, (user_id, member_id, amount, date.today()))
    
    conn.commit()
    return True

def main():
    render_sidebar()
    
    st.title("🍑 Family Allowance Tracker")
    
    user_id = st.session_state.get("user_id", 1)
    
    tab1, tab2, tab3 = st.tabs(["👨‍👩‍👧‍👦 Family Members", "📋 Chores", "💰 Payouts"])
    
    with tab1:
        st.subheader("Family Members")
        members = get_family_members(user_id)
        
        if members:
            for member in members:
                with st.expander(f"{member.get('avatar_emoji', '👤')} {member['name']}"):
                    st.write(f"**Balance:** ${float(member.get('current_balance', 0)):.2f}")
                    st.write(f"**Allowance:** ${float(member.get('allowance_amount', 0)):.2f} ({member.get('payout_frequency', 'weekly')})")
                    
                    if st.button(f"💸 Process Payout", key=f"payout_{member['id']}"):
                        if process_payout(user_id, member['id'], float(member.get('allowance_amount', 0))):
                            st.success(f"Payout processed for {member['name']}!")
                            st.rerun()
        else:
            st.info("No family members added yet.")
        
        with st.form("add_member_form"):
            st.subheader("Add Family Member")
            name = st.text_input("Name")
            age = st.number_input("Age", min_value=1, max_value=100, value=10)
            avatar = st.selectbox("Avatar", ["👤", "👦", "👧", "👨", "👩", "🧒", "👶"])
            allowance = st.number_input("Allowance Amount", min_value=0.0, value=10.0, step=0.50)
            frequency = st.selectbox("Payout Frequency", ["daily", "weekly", "biweekly", "monthly"])
            
            if st.form_submit_button("Add Member"):
                conn = get_conn()
                cur = conn.cursor()
                placeholder = "%s" if USE_POSTGRES else "?"
                cur.execute(f"""
                    INSERT INTO family_members (user_id, name, age, avatar_emoji, allowance_amount, payout_frequency)
                    VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
                """, (user_id, name, age, avatar, allowance, frequency))
                conn.commit()
                st.success(f"Added {name} to family!")
                st.rerun()
    
    with tab2:
        st.subheader("Chores Management")
        st.info("Chore management features coming soon!")
    
    with tab3:
        st.subheader("Payout History")
        st.info("Payout history features coming soon!")

if __name__ == "__main__":
    main()