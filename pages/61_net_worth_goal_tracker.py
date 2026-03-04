import streamlit as st
import datetime
import json
from decimal import Decimal
import anthropic

st.set_page_config(page_title="Net Worth Goal Tracker", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_name VARCHAR(255) NOT NULL,
                target_amount DECIMAL(15,2) NOT NULL,
                target_date DATE,
                priority INTEGER DEFAULT 1,
                notes TEXT,
                is_achieved BOOLEAN DEFAULT FALSE,
                achieved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_milestones (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                milestone_name VARCHAR(255) NOT NULL,
                amount_reached DECIMAL(15,2) NOT NULL,
                reached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                celebration_shown BOOLEAN DEFAULT FALSE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_snapshots (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                snapshot_date DATE NOT NULL,
                total_assets DECIMAL(15,2) DEFAULT 0,
                total_liabilities DECIMAL(15,2) DEFAULT 0,
                net_worth DECIMAL(15,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                goal_name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                target_date TEXT,
                priority INTEGER DEFAULT 1,
                notes TEXT,
                is_achieved INTEGER DEFAULT 0,
                achieved_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                milestone_name TEXT NOT NULL,
                amount_reached REAL NOT NULL,
                reached_at TEXT DEFAULT CURRENT_TIMESTAMP,
                celebration_shown INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS net_worth_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                snapshot_date TEXT NOT NULL,
                total_assets REAL DEFAULT 0,
                total_liabilities REAL DEFAULT 0,
                net_worth REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

def get_current_user_id():
    return st.session_state.get("user_id", 1)

def calculate_current_net_worth(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    total_assets = 0
    total_liabilities = 0
    
    try:
        cur.execute(f"SELECT SUM(value) FROM assets WHERE user_id = {ph}", (user_id,))
        result = cur.fetchone()
        if result and result[0]:
            total_assets = float(result[0])
    except:
        pass
    
    try:
        cur.execute(f"SELECT SUM(balance) FROM liabilities WHERE user_id = {ph}", (user_id,))
        result = cur.fetchone()
        if result and result[0]:
            total_liabilities = float(result[0])
    except:
        pass
    
    try:
        cur.execute(f"SELECT SUM(current_value) FROM portfolio WHERE user_id = {ph}", (user_id,))
        result = cur.fetchone()
        if result and result[0]:
            total_assets += float(result[0])
    except:
        pass
    
    try:
        cur.execute(f"SELECT balance FROM goals WHERE user_id = {ph} AND goal_type = 'savings'", (user_id,))
        results = cur.fetchall()
        for r in results:
            if r[0]:
                total_assets += float(r[0])
    except:
        pass
    
    conn.close()
    
    net_worth = total_assets - total_liabilities
    return total_assets, total_liabilities, net_worth

def get_net_worth_history(user_id, days=365):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT snapshot_date, total_assets, total_liabilities, net_worth 
            FROM net_worth_snapshots 
            WHERE user_id = {ph} AND snapshot_date >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY snapshot_date
        """, (user_id,))
    else:
        cur.execute(f"""
            SELECT snapshot_date, total_assets, total_liabilities, net_worth 
            FROM net_worth_snapshots 
            WHERE user_id = {ph} AND snapshot_date >= date('now', '-{days} days')
            ORDER BY snapshot_date
        """, (user_id,))
    
    results = cur.fetchall()
    conn.close()
    return results

def get_goals(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        SELECT id, goal_name, target_amount, target_date, priority, notes, is_achieved, achieved_at, created_at
        FROM net_worth_goals 
        WHERE user_id = {ph}
        ORDER BY priority, target_amount
    """, (user_id,))
    
    results = cur.fetchall()
    conn.close()
    return results

def add_goal(user_id, goal_name, target_amount, target_date=None, priority=1, notes=None):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"""
        INSERT INTO net_worth_goals (user_id, goal_name, target_amount, target_date, priority, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, goal_name, target_amount, target_date, priority, notes))
    
    conn.commit()
    conn.close()

def delete_goal(goal_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    cur.execute(f"DELETE FROM net_worth_goals WHERE id = {ph}", (goal_id,))
    conn.commit()
    conn.close()

def mark_goal_achieved(goal_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    now = datetime.datetime.now().isoformat()
    if USE_POSTGRES:
        cur.execute(f"UPDATE net_worth_goals SET is_achieved = TRUE, achieved_at = {ph} WHERE id = {ph}", (now, goal_id))
    else:
        cur.execute(f"UPDATE net_worth_goals SET is_achieved = 1, achieved_at = {ph} WHERE id = {ph}", (now, goal_id))
    
    conn.commit()
    conn.close()

def save_snapshot(user_id, total_assets, total_liabilities, net_worth):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    today = datetime.date.today().isoformat()
    
    # Check if snapshot exists for today
    cur.execute(f"SELECT id FROM net_worth_snapshots WHERE user_id = {ph} AND snapshot_date = {ph}", (user_id, today))
    existing = cur.fetchone()
    
    if existing:
        cur.execute(f"""
            UPDATE net_worth_snapshots 
            SET total_assets = {ph}, total_liabilities = {ph}, net_worth = {ph}
            WHERE id = {ph}
        """, (total_assets, total_liabilities, net_worth, existing[0]))
    else:
        cur.execute(f"""
            INSERT INTO net_worth_snapshots (user_id, snapshot_date, total_assets, total_liabilities, net_worth)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
        """, (user_id, today, total_assets, total_liabilities, net_worth))
    
    conn.commit()
    conn.close()

def get_ai_advice(net_worth, goals, history):
    try:
        client = anthropic.Anthropic()
        
        goals_text = ""
        for g in goals:
            goals_text += f"- {g[1]}: ${g[2]:,.2f} target\n"
        
        history_text = ""
        if history:
            for h in history[-12:]:
                history_text += f"- {h[0]}: ${h[3]:,.2f}\n"
        
        prompt = f"""Based on the following financial information, provide brief, actionable advice for reaching net worth goals:

Current Net Worth: ${net_worth:,.2f}

Goals:
{goals_text if goals_text else "No goals set yet"}

Recent History (last 12 snapshots):
{history_text if history_text else "No history yet"}

Provide 3-5 specific, practical tips to help reach these goals. Keep advice concise and actionable."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    except Exception as e:
        return f"Unable to generate AI advice: {str(e)}"

# Main UI
render_sidebar_brand()
render_sidebar_user_widget()

st.title("🍑 Net Worth Goal Tracker")

user_id = get_current_user_id()
total_assets, total_liabilities, net_worth = calculate_current_net_worth(user_id)

# Save today's snapshot
save_snapshot(user_id, total_assets, total_liabilities, net_worth)

# Display current net worth
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Assets", f"${total_assets:,.2f}")

with col2:
    st.metric("Total Liabilities", f"${total_liabilities:,.2f}")

with col3:
    st.metric("Net Worth", f"${net_worth:,.2f}")

st.divider()

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Goals", "📈 History", "➕ Add Goal", "🤖 AI Advice"])

with tab1:
    st.subheader("Your Net Worth Goals")
    
    goals = get_goals(user_id)
    
    if not goals:
        st.info("No goals set yet. Add a goal to get started!")
    else:
        for goal in goals:
            goal_id, goal_name, target_amount, target_date, priority, notes, is_achieved, achieved_at, created_at = goal
            
            progress = min(100, (net_worth / float(target_amount)) * 100) if float(target_amount) > 0 else 0
            
            with st.expander(f"{'✅' if is_achieved else '🎯'} {goal_name} - ${float(target_amount):,.2f}"):
                st.progress(progress / 100)
                st.write(f"Progress: {progress:.1f}%")
                st.write(f"Current: ${net_worth:,.2f} / Target: ${float(target_amount):,.2f}")
                
                if target_date:
                    st.write(f"Target Date: {target_date}")
                
                if notes:
                    st.write(f"Notes: {notes}")
                
                if is_achieved:
                    st.success(f"Achieved on: {achieved_at}")
                else:
                    remaining = float(target_amount) - net_worth
                    st.write(f"Remaining: ${remaining:,.2f}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Mark Achieved", key=f"achieve_{goal_id}"):
                            mark_goal_achieved(goal_id)
                            st.rerun()
                    with col2:
                        if st.button("Delete", key=f"delete_{goal_id}"):
                            delete_goal(goal_id)
                            st.rerun()

with tab2:
    st.subheader("Net Worth History")
    
    history = get_net_worth_history(user_id)
    
    if history:
        import pandas as pd
        
        df = pd.DataFrame(history, columns=["Date", "Assets", "Liabilities", "Net Worth"])
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
        
        st.line_chart(df["Net Worth"])
        
        st.dataframe(df.sort_index(ascending=False))
    else:
        st.info("No history yet. Your net worth will be tracked over time.")

with tab3:
    st.subheader("Add New Goal")
    
    with st.form("add_goal_form"):
        goal_name = st.text_input("Goal Name", placeholder="e.g., First $100K")
        target_amount = st.number_input("Target Amount ($)", min_value=0.0, step=1000.0)
        target_date = st.date_input("Target Date (optional)", value=None)
        priority = st.slider("Priority", 1, 5, 3)
        notes = st.text_area("Notes (optional)")
        
        submitted = st.form_submit_button("Add Goal")
        
        if submitted:
            if goal_name and target_amount > 0:
                add_goal(user_id, goal_name, target_amount, target_date.isoformat() if target_date else None, priority, notes)
                st.success("Goal added successfully!")
                st.rerun()
            else:
                st.error("Please enter a goal name and target amount.")

with tab4:
    st.subheader("AI-Powered Advice")
    
    if st.button("Get Personalized Advice"):
        with st.spinner("Generating advice..."):
            goals = get_goals(user_id)
            history = get_net_worth_history(user_id)
            advice = get_ai_advice(net_worth, goals, history)
            st.markdown(advice)
    
    st.divider()
    
    st.markdown("### General Tips")
    st.markdown(
        "**Keep expenses low** - The wealth equation is simple: "
        "spend less than you earn and invest the difference."
    )
    st.markdown(
        "**Automate savings** - Set up automatic transfers to savings and investment accounts."
    )
    st.markdown(
        "**Track regularly** - Review your net worth monthly to stay on track."
    )
    st.markdown(
        "**Reduce high-interest debt** - Pay off credit cards and high-interest loans first."
    )
    st.markdown(
        "**Diversify investments** - Don't put all your eggs in one basket."
    )