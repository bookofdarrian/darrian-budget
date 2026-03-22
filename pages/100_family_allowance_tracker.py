import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from decimal import Decimal
import json
import io
import csv

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Family Allowance Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                birth_date DATE,
                avatar_emoji VARCHAR(10) DEFAULT '👤',
                savings_goal DECIMAL(10,2) DEFAULT 0,
                current_balance DECIMAL(10,2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowances (
                id SERIAL PRIMARY KEY,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                amount DECIMAL(10,2) NOT NULL,
                frequency VARCHAR(20) NOT NULL,
                start_date DATE NOT NULL,
                next_payment_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chores (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                reward_amount DECIMAL(10,2) DEFAULT 0,
                frequency VARCHAR(20) DEFAULT 'one-time',
                is_required BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chore_completions (
                id SERIAL PRIMARY KEY,
                chore_id INTEGER REFERENCES chores(id) ON DELETE CASCADE,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified BOOLEAN DEFAULT FALSE,
                verified_by VARCHAR(100),
                notes TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_transactions (
                id SERIAL PRIMARY KEY,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                transaction_type VARCHAR(20) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                related_chore_id INTEGER REFERENCES chores(id) ON DELETE SET NULL,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                birth_date TEXT,
                avatar_emoji TEXT DEFAULT '👤',
                savings_goal REAL DEFAULT 0,
                current_balance REAL DEFAULT 0,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                start_date TEXT NOT NULL,
                next_payment_date TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                reward_amount REAL DEFAULT 0,
                frequency TEXT DEFAULT 'one-time',
                is_required INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chore_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chore_id INTEGER REFERENCES chores(id) ON DELETE CASCADE,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                verified INTEGER DEFAULT 0,
                verified_by TEXT,
                notes TEXT
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS allowance_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER REFERENCES family_members(id) ON DELETE CASCADE,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                category TEXT,
                related_chore_id INTEGER REFERENCES chores(id) ON DELETE SET NULL,
                transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()


def get_family_members(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM family_members WHERE user_id = ? ORDER BY name", (user_id,))
    return cur.fetchall()


def add_family_member(user_id, name, birth_date, avatar_emoji, savings_goal, notes):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO family_members (user_id, name, birth_date, avatar_emoji, savings_goal, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, name, birth_date, avatar_emoji, savings_goal, notes))
    conn.commit()


def update_member_balance(member_id, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE family_members SET current_balance = current_balance + ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (amount, member_id))
    conn.commit()


def add_transaction(member_id, transaction_type, amount, description, category=None, related_chore_id=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO allowance_transactions (member_id, transaction_type, amount, description, category, related_chore_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (member_id, transaction_type, amount, description, category, related_chore_id))
    conn.commit()
    
    if transaction_type == 'deposit':
        update_member_balance(member_id, amount)
    elif transaction_type == 'withdrawal':
        update_member_balance(member_id, -amount)


def get_transactions(member_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM allowance_transactions WHERE member_id = ? ORDER BY transaction_date DESC
    """, (member_id,))
    return cur.fetchall()


# Initialize tables
_ensure_tables()

# Main page content
st.title("🍑 Family Allowance Tracker")

user_id = st.session_state.get("user_id", 1)

tab1, tab2, tab3, tab4 = st.tabs(["👨‍👩‍👧‍👦 Family Members", "💰 Transactions", "🧹 Chores", "📊 Reports"])

with tab1:
    st.subheader("Manage Family Members")
    
    with st.expander("➕ Add New Family Member"):
        with st.form("add_member_form"):
            member_name = st.text_input("Name")
            member_birth_date = st.date_input("Birth Date", value=None)
            member_avatar = st.selectbox("Avatar", ["👤", "👦", "👧", "👨", "👩", "👴", "👵", "🧒", "🧑"])
            member_savings_goal = st.number_input("Savings Goal ($)", min_value=0.0, value=0.0, step=1.0)
            member_notes = st.text_area("Notes", key="member_notes")
            
            if st.form_submit_button("Add Member"):
                if member_name:
                    add_family_member(user_id, member_name, member_birth_date, member_avatar, member_savings_goal, member_notes)
                    st.success(f"Added {member_name} to the family!")
                    st.rerun()
                else:
                    st.error("Please enter a name")
    
    members = get_family_members(user_id)
    if members:
        for member in members:
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    st.markdown(f"# {member[4]}")  # avatar_emoji
                with col2:
                    st.markdown(f"**{member[2]}**")  # name
                    st.markdown(f"Balance: ${member[6]:.2f}")  # current_balance
                with col3:
                    if member[5] > 0:  # savings_goal
                        progress = min(member[6] / member[5], 1.0)
                        st.progress(progress)
                        st.caption(f"Goal: ${member[5]:.2f}")
                st.markdown("---")
    else:
        st.info("No family members added yet. Add your first family member above!")

with tab2:
    st.subheader("Transactions")
    
    members = get_family_members(user_id)
    if members:
        member_options = {f"{m[4]} {m[2]}": m[0] for m in members}
        selected_member = st.selectbox("Select Family Member", list(member_options.keys()))
        
        if selected_member:
            member_id = member_options[selected_member]
            
            with st.expander("➕ Add Transaction"):
                with st.form("add_transaction_form"):
                    trans_type = st.selectbox("Type", ["deposit", "withdrawal"])
                    trans_amount = st.number_input("Amount ($)", min_value=0.01, value=1.0, step=0.01)
                    trans_description = st.text_input("Description")
                    trans_category = st.selectbox("Category", ["Allowance", "Chore Reward", "Gift", "Savings", "Spending", "Other"])
                    
                    if st.form_submit_button("Add Transaction"):
                        add_transaction(member_id, trans_type, trans_amount, trans_description, trans_category)
                        st.success("Transaction added!")
                        st.rerun()
            
            transactions = get_transactions(member_id)
            if transactions:
                for trans in transactions:
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            icon = "💵" if trans[2] == "deposit" else "💸"
                            st.markdown(f"{icon} **{trans[4]}**")  # description
                            st.caption(f"{trans[5]} - {trans[7]}")  # category, date
                        with col2:
                            color = "green" if trans[2] == "deposit" else "red"
                            sign = "+" if trans[2] == "deposit" else "-"
                            st.markdown(f":{color}[{sign}${trans[3]:.2f}]")
                        st.markdown("---")
            else:
                st.info("No transactions yet for this member.")
    else:
        st.info("Add family members first to track transactions.")

with tab3:
    st.subheader("Chores Management")
    st.info("🚧 Chores feature coming soon!")

with tab4:
    st.subheader("Reports & Analytics")
    
    members = get_family_members(user_id)
    if members:
        # Balance overview
        df = pd.DataFrame(members, columns=['id', 'user_id', 'name', 'birth_date', 'avatar', 'savings_goal', 'balance', 'notes', 'created', 'updated'])
        
        fig = px.bar(df, x='name', y='balance', title='Family Member Balances', color='name')
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Family Balance", f"${df['balance'].sum():.2f}")
        with col2:
            st.metric("Average Balance", f"${df['balance'].mean():.2f}")
        with col3:
            st.metric("Family Members", len(members))
    else:
        st.info("Add family members to see reports.")