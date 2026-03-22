import streamlit as st
import json
import datetime
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Debt Payoff Planner", page_icon="🍑", layout="wide")
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
    """Create debts table if it doesn't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name VARCHAR(255) NOT NULL,
                balance DECIMAL(12, 2) NOT NULL,
                interest_rate DECIMAL(5, 2) NOT NULL,
                minimum_payment DECIMAL(10, 2) NOT NULL,
                due_date INTEGER DEFAULT 1,
                debt_type VARCHAR(50) DEFAULT 'other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_paid_off BOOLEAN DEFAULT FALSE
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                balance REAL NOT NULL,
                interest_rate REAL NOT NULL,
                minimum_payment REAL NOT NULL,
                due_date INTEGER DEFAULT 1,
                debt_type TEXT DEFAULT 'other',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_paid_off INTEGER DEFAULT 0
            )
        """)
    
    conn.commit()
    conn.close()


def get_all_debts(user_id: int = 1) -> List[Dict]:
    """Retrieve all active debts for a user."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, name, balance, interest_rate, minimum_payment, due_date, debt_type, created_at
            FROM debts
            WHERE user_id = %s AND is_paid_off = FALSE
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cur.execute("""
            SELECT id, name, balance, interest_rate, minimum_payment, due_date, debt_type, created_at
            FROM debts
            WHERE user_id = ? AND is_paid_off = 0
            ORDER BY created_at DESC
        """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    debts = []
    for row in rows:
        debts.append({
            "id": row[0],
            "name": row[1],
            "balance": float(row[2]),
            "interest_rate": float(row[3]),
            "minimum_payment": float(row[4]),
            "due_date": row[5],
            "debt_type": row[6],
            "created_at": row[7]
        })
    return debts


def add_debt(user_id: int, name: str, balance: float, interest_rate: float, 
             minimum_payment: float, due_date: int, debt_type: str) -> int:
    """Add a new debt entry."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO debts (user_id, name, balance, interest_rate, minimum_payment, due_date, debt_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, name, balance, interest_rate, minimum_payment, due_date, debt_type))
        debt_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO debts (user_id, name, balance, interest_rate, minimum_payment, due_date, debt_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, balance, interest_rate, minimum_payment, due_date, debt_type))
        debt_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return debt_id


def update_debt(debt_id: int, name: str, balance: float, interest_rate: float,
                minimum_payment: float, due_date: int, debt_type: str):
    """Update an existing debt."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            UPDATE debts
            SET name = %s, balance = %s, interest_rate = %s, minimum_payment = %s,
                due_date = %s, debt_type = %s
            WHERE id = %s
        """, (name, balance, interest_rate, minimum_payment, due_date, debt_type, debt_id))
    else:
        cur.execute("""
            UPDATE debts
            SET name = ?, balance = ?, interest_rate = ?, minimum_payment = ?,
                due_date = ?, debt_type = ?
            WHERE id = ?
        """, (name, balance, interest_rate, minimum_payment, due_date, debt_type, debt_id))
    
    conn.commit()
    conn.close()


def delete_debt(debt_id: int):
    """Delete a debt entry."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("DELETE FROM debts WHERE id = %s", (debt_id,))
    else:
        cur.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
    
    conn.commit()
    conn.close()


def mark_debt_paid(debt_id: int):
    """Mark a debt as paid off."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("UPDATE debts SET is_paid_off = TRUE WHERE id = %s", (debt_id,))
    else:
        cur.execute("UPDATE debts SET is_paid_off = 1 WHERE id = ?", (debt_id,))
    
    conn.commit()
    conn.close()


def calculate_payoff_schedule(debts: List[Dict], extra_payment: float, method: str) -> Tuple[List[Dict], int, float]:
    """
    Calculate payoff schedule using snowball or avalanche method.
    Returns: (monthly_schedule, total_months, total_interest_paid)
    """
    if not debts:
        return [], 0, 0.0
    
    # Create working copies
    working_debts = []
    for d in debts:
        working_debts.append({
            "name": d["name"],
            "balance": d["balance"],
            "interest_rate": d["interest_rate"],
            "minimum_payment": d["minimum_payment"],
            "original_balance": d["balance"]
        })
    
    # Sort based on method
    if method == "snowball":
        # Smallest balance first
        working_debts.sort(key=lambda x: x["balance"])
    else:  # avalanche
        # Highest interest rate first
        working_debts.sort(key=lambda x: x["interest_rate"], reverse=True)
    
    schedule = []
    month = 0
    total_interest = 0.0
    max_months = 600  # 50 years cap
    
    while any(d["balance"] > 0.01 for d in working_debts) and month < max_months:
        month += 1
        month_data = {"month": month, "debts": [], "total_paid": 0, "total_remaining": 0}
        
        # Calculate minimum payments and apply interest
        available_extra = extra_payment
        
        for debt in working_debts:
            if debt["balance"] <= 0.01:
                continue
            
            # Apply monthly interest
            monthly_rate = debt["interest_rate"] / 100 / 12
            interest_charge = debt["balance"] * monthly_rate
            debt["balance"] += interest_charge
            total_interest += interest_charge
        
        # Pay minimums first
        for debt in working_debts:
            if debt["balance"] <= 0.01:
                continue
            
            payment = min(debt["minimum_payment"], debt["balance"])
            debt["balance"] -= payment
            month_data["total_paid"] += payment
        
        # Apply extra payment to target debt
        for debt in working_debts:
            if debt["balance"] <= 0.01:
                continue
            if available_extra <= 0:
                break
            
            extra_applied = min(available_extra, debt["balance"])
            debt["balance"] -= extra_applied
            available_extra -= extra_applied
            month_data["total_paid"] += extra_applied
            break  # Only apply to first (priority) debt
        
        # Record month data
        for debt in working_debts:
            month_data["debts"].append({
                "name": debt["name"],
                "balance": max(0, debt["balance"])
            })
            month_data["total_remaining"] += max(0, debt["balance"])
        
        schedule.append(month_data)
        
        if month_data["total_remaining"] < 0.01:
            break
    
    return schedule, month, total_interest


def get_debt_summary(debts: List[Dict]) -> Dict:
    """Calculate summary statistics for debts."""
    if not debts:
        return {
            "total_balance": 0,
            "total_minimum": 0,
            "avg_interest_rate": 0,
            "highest_interest": None,
            "smallest_balance": None,
            "debt_count": 0
        }
    
    total_balance = sum(d["balance"] for d in debts)
    total_minimum = sum(d["minimum_payment"] for d in debts)
    
    # Weighted average interest rate
    if total_balance > 0:
        avg_interest = sum(d["balance"] * d["interest_rate"] for d in debts) / total_balance
    else:
        avg_interest = 0
    
    highest_interest = max(debts, key=lambda x: x["interest_rate"])
    smallest_balance = min(debts, key=lambda x: x["balance"])
    
    return {
        "total_balance": total_balance,
        "total_minimum": total_minimum,
        "avg_interest_rate": avg_interest,
        "highest_interest": highest_interest,
        "smallest_balance": smallest_balance,
        "debt_count": len(debts)
    }


def get_ai_advice(debts: List[Dict], extra_payment: float, snowball_months: int, 
                  avalanche_months: int, snowball_interest: float, avalanche_interest: float) -> str:
    """Get personalized payoff advice from Claude."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Set your Anthropic API key in Settings to receive personalized AI advice."
    
    summary = get_debt_summary(debts)
    
    debt_list = "\n".join([
        f"- {d['name']}: ${d['balance']:,.2f} at {d['interest_rate']}% APR, ${d['minimum_payment']}/mo minimum"
        for d in debts
    ])
    
    prompt = f"""You are a supportive financial advisor helping someone pay off debt. Be encouraging and practical.

Current Debt Situation:
{debt_list}

Total Debt: ${summary['total_balance']:,.2f}
Total Monthly Minimums: ${summary['total_minimum']:,.2f}
Average Interest Rate: {summary['avg_interest_rate']:.2f}%
Extra Monthly Payment Available: ${extra_payment:,.2f}

Payoff Projections:
- Snowball Method (smallest balance first): {snowball_months} months, ${snowball_interest:,.2f} total interest
- Avalanche Method (highest interest first): {avalanche_months} months, ${avalanche_interest:,.2f} total interest

Interest Savings with Avalanche: ${snowball_interest - avalanche_interest:,.2f}
Time Difference: {snowball_months - avalanche_months} months

Please provide:
1. A recommendation on which method to use and why (considering both math and psychology)
2. One specific actionable tip to accelerate their debt payoff
3. An encouraging motivational message personalized to their situation

Keep your response concise (under 250 words) and use emojis to make it friendly."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"⚠️ Error getting AI advice: {str(e)}"


def get_motivation_tip(debts: List[Dict], progress_pct: float) -> str:
    """Get a quick motivation tip based on progress."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "💪 Keep going! Every payment brings you closer to financial freedom."
    
    summary = get_debt_summary(debts)
    
    prompt = f"""Generate a single, short (1-2 sentences) motivational message for someone paying off ${summary['total_balance']:,.2f} in debt.
They have {summary['debt_count']} debts. Progress: {progress_pct:.1f}% of original debt paid off.
Be encouraging, specific, and use an emoji. Focus on the positive."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except:
        tips = [
            "💪 Every payment is a step toward freedom!",
            "🎯 You're making progress - keep the momentum!",
            "🌟 Financial independence is within reach!",
            "🔥 Stay focused - your future self will thank you!",
            "💰 Each dollar paid is stress lifted!"
        ]
        import random
        return random.choice(tips)


# Initialize tables
_ensure_tables()

# Main UI
st.title("💳 Debt Payoff Planner")
st.markdown("*Compare snowball vs avalanche methods and get AI-powered payoff strategies*")

# Get user debts
user_id = st.session_state.get("user_id", 1)
debts = get_all_debts(user_id)
summary = get_debt_summary(debts)

# Summary metrics at top
if debts:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Debt", f"${summary['total_balance']:,.2f}")
    with col2:
        st.metric("Monthly Minimums", f"${summary['total_minimum']:,.2f}")
    with col3:
        st.metric("Avg Interest Rate", f"{summary['avg_interest_rate']:.1f}%")
    with col4:
        st.metric("Number of Debts", summary['debt_count'])

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Payoff Calculator", "➕ Manage Debts", "📈 Visualizations", "🤖 AI Insights"])

with tab1:
    st.subheader("Debt Payoff Calculator")
    
    if not debts:
        st.info("👋 Add your debts in the 'Manage Debts' tab to get started!")
    else:
        # Extra payment input
        col1, col2 = st.columns([2, 1])
        with col1:
            extra_payment = st.slider(
                "Extra Monthly Payment",
                min_value=0,
                max_value=2000,
                value=100,
                step=25,
                help="Amount above minimum payments you can put toward debt"
            )
        with col2:
            st.metric("Total Monthly Payment", f"${summary['total_minimum'] + extra_payment:,.2f}")
        
        # Calculate both methods
        snowball_schedule, snowball_months, snowball_interest = calculate_payoff_schedule(
            debts, extra_payment, "snowball"
        )
        avalanche_schedule, avalanche_months, avalanche_interest = calculate_payoff_schedule(
            debts, extra_payment, "avalanche"
        )
        
        # Comparison
        st.markdown("### 📊 Method Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ❄️ Snowball Method")
            st.markdown("*Pay smallest balance first for quick wins*")
            
            if snowball_months > 0:
                payoff_date = datetime.date.today() + datetime.timedelta(days=snowball_months * 30)
                st.metric("Payoff Time", f"{snowball_months} months")
                st.metric("Total Interest Paid", f"${snowball_interest:,.2f}")
                st.metric("Debt-Free Date", payoff_date.strftime("%B %Y"))
            else:
                st.warning("Unable to calculate - check minimum payments")
        
        with col2:
            st.markdown("#### 🏔️ Avalanche Method")
            st.markdown("*Pay highest interest first to save money*")
            
            if avalanche_months > 0:
                payoff_date = datetime.date.today() + datetime.timedelta(days=avalanche_months * 30)
                st.metric("Payoff Time", f"{avalanche_months} months")
                st.metric("Total Interest Paid", f"${avalanche_interest:,.2f}")
                st.metric("Debt-Free Date", payoff_date.strftime("%B %Y"))
            else:
                st.warning("Unable to calculate - check minimum payments")
        
        # Savings comparison
        if snowball_months > 0 and avalanche_months > 0:
            interest_saved = snowball_interest - avalanche_interest
            time_saved = snowball_months - avalanche_months
            
            st.markdown("---")
            st.markdown("### 💡 Avalanche Advantage")
            
            adv_col1, adv_col2, adv_col3 = st.columns(3)
            with adv_col1:
                st.metric("Interest Saved", f"${interest_saved:,.2f}", 
                         delta=f"-${interest_saved:,.2f}" if interest_saved > 0 else None,
                         delta_color="inverse")
            with adv_col2:
                st.metric("Time Saved", f"{time_saved} months",
                         delta=f"-{time_saved} mo" if time_saved > 0 else None,
                         delta_color="inverse")
            with adv_col3:
                if interest_saved > 0:
                    pct_saved = (interest_saved / snowball_interest) * 100 if snowball_interest > 0 else 0
                    st.metric("Savings %", f"{pct_saved:.1f}%")
                else:
                    st.metric("Savings %", "0%")
        
        # Payment order recommendation
        st.markdown("---")
        st.markdown("### 🎯 Recommended Payment Order")
        
        method_choice = st.radio(
            "Select Method",
            ["Avalanche (Save Money)", "Snowball (Quick Wins)"],
            horizontal=True
        )
        
        if "Avalanche" in method_choice:
            sorted_debts = sorted(debts, key=lambda x: x["interest_rate"], reverse=True)
            st.markdown("*Paying highest interest rates first:*")
        else:
            sorted_debts = sorted(debts, key=lambda x: x["balance"])
            st.markdown("*Paying smallest balances first:*")
        
        for i, debt in enumerate(sorted_debts, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            st.markdown(f"{emoji} **{debt['name']}** - ${debt['balance']:,.2f} @ {debt['interest_rate']}%")

with tab2:
    st.subheader("Manage Your Debts")
    
    # Add new debt form
    with st.expander("➕ Add New Debt", expanded=not debts):
        with st.form("add_debt_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Debt Name", placeholder="e.g., Chase Credit Card")
                new_balance = st.number_input("Current Balance", min_value=0.0, value=0.0, step=100.0)
                new_interest = st.number_input("Interest Rate (APR %)", min_value=0.0, max_value=100.0, value=18.0, step=0.5)
            
            with col2:
                new_minimum = st.number_input("Minimum Payment", min_value=0.0, value=0.0, step=10.0)
                new_due_date = st.number_input("Due Date (day of month)", min_value=1, max_value=31, value=15)
                new_type = st.selectbox("Debt Type", [
                    "Credit Card",
                    "Student Loan",
                    "Auto Loan",
                    "Personal Loan",
                    "Medical Debt",
                    "Mortgage",
                    "Other"
                ])
            
            submitted = st.form_submit_button("Add Debt", use_container_width=True)
            
            if submitted:
                if new_name and new_balance > 0:
                    add_debt(user_id, new_name, new_balance, new_interest, 
                            new_minimum, new_due_date, new_type)
                    st.success(f"✅ Added {new_name} to your debt list!")
                    st.rerun()
                else:
                    st.error("Please enter a debt name and balance greater than $0")
    
    # List existing debts
    if debts:
        st.markdown("### Your Debts")
        
        for debt in debts:
            with st.expander(f"💳 {debt['name']} - ${debt['balance']:,.2f}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**Balance:** ${debt['balance']:,.2f}")
                    st.markdown(f"**Interest Rate:** {debt['interest_rate']}%")
                    st.markdown(f"**Type:** {debt['debt_type']}")
                
                with col2:
                    st.markdown(f"**Minimum Payment:** ${debt['minimum_payment']:,.2f}")
                    st.markdown(f"**Due Date:** {debt['due_date']}th of month")
                    if debt['created_at']:
                        st.markdown(f"**Added:** {str(debt['created_at'])[:10]}")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{debt['id']}"):
                        delete_debt(debt['id'])
                        st.success("Debt deleted!")
                        st.rerun()
                    
                    if st.button("✅ Paid Off!", key=f"paid_{debt['id']}"):
                        mark_debt_paid(debt['id'])
                        st.balloons()
                        st.success(f"🎉 Congratulations on paying off {debt['name']}!")
                        st.rerun()
                
                # Edit form
                st.markdown("---")
                with st.form(f"edit_form_{debt['id']}"):
                    st.markdown("**Edit Debt:**")
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        edit_name = st.text_input("Name", value=debt['name'], key=f"edit_name_{debt['id']}")
                        edit_balance = st.number_input("Balance", value=debt['balance'], key=f"edit_bal_{debt['id']}")
                        edit_interest = st.number_input("Interest Rate", value=debt['interest_rate'], key=f"edit_int_{debt['id']}")
                    
                    with edit_col2:
                        edit_minimum = st.number_input("Minimum Payment", value=debt['minimum_payment'], key=f"edit_min_{debt['id']}")
                        edit_due = st.number_input("Due Date", value=debt['due_date'], min_value=1, max_value=31, key=f"edit_due_{debt['id']}")
                        edit_type = st.selectbox("Type", [
                            "Credit Card", "Student Loan", "Auto Loan", "Personal Loan", 
                            "Medical Debt", "Mortgage", "Other"
                        ], index=["Credit Card", "Student Loan", "Auto Loan", "Personal Loan", 
                                 "Medical Debt", "Mortgage", "Other"].index(debt['debt_type']) 
                                 if debt['debt_type'] in ["Credit Card", "Student Loan", "Auto Loan", 
                                                         "Personal Loan", "Medical Debt", "Mortgage", "Other"] else 6,
                        key=f"edit_type_{debt['id']}")
                    
                    if st.form_submit_button("Save Changes"):
                        update_debt(debt['id'], edit_name, edit_balance, edit_interest,
                                   edit_minimum, edit_due, edit_type)
                        st.success("Debt updated!")
                        st.rerun()
    else:
        st.info("No debts added yet. Use the form above to add your first debt!")

with tab3:
    st.subheader("Payoff Visualizations")
    
    if not debts:
        st.info("Add debts to see visualizations!")
    else:
        extra_payment = st.session_state.get("viz_extra", 100)
        extra_payment = st.slider(
            "Extra Monthly Payment for Visualization",
            min_value=0,
            max_value=2000,
            value=100,
            step=25,
            key="viz_extra_slider"
        )
        
        # Calculate schedules
        snowball_schedule, snowball_months, snowball_interest = calculate_payoff_schedule(
            debts, extra_payment, "snowball"
        )
        avalanche_schedule, avalanche_months, avalanche_interest = calculate_payoff_schedule(
            debts, extra_payment, "avalanche"
        )
        
        # Debt breakdown pie chart
        st.markdown("### 🥧 Debt Breakdown")
        
        import pandas as pd
        
        debt_df = pd.DataFrame([
            {"Debt": d["name"], "Balance": d["balance"], "Interest Rate": f"{d['interest_rate']}%"}
            for d in debts
        ])
        
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(debt_df.set_index("Debt")["Balance"])
        with col2:
            st.dataframe(debt_df, use_container_width=True)
        
        # Payoff timeline comparison
        st.markdown("### 📉 Balance Over Time")
        
        # Build comparison data
        max_months = max(len(snowball_schedule), len(avalanche_schedule))
        
        if max_months > 0:
            timeline_data = []
            for i in range(min(max_months, 120)):  # Cap at 10 years for readability
                row = {"Month": i + 1}
                
                if i < len(snowball_schedule):
                    row["Snowball"] = snowball_schedule[i]["total_remaining"]
                else:
                    row["Snowball"] = 0
                
                if i < len(avalanche_schedule):
                    row["Avalanche"] = avalanche_schedule[i]["total_remaining"]
                else:
                    row["Avalanche"] = 0
                
                timeline_data.append(row)
            
            timeline_df = pd.DataFrame(timeline_data)
            st.line_chart(timeline_df.set_index("Month")[["Snowball", "Avalanche"]])
        
        # Monthly payment breakdown
        st.markdown("### 💵 Monthly Payment Allocation")
        
        total_payment = summary["total_minimum"] + extra_payment
        
        payment_data = []
        for d in debts:
            pct = (d["minimum_payment"] / total_payment) * 100 if total_payment > 0 else 0
            payment_data.append({
                "Debt": d["name"],
                "Minimum": d["minimum_payment"],
                "Percentage": f"{pct:.1f}%"
            })
        
        if extra_payment > 0:
            extra_pct = (extra_payment / total_payment) * 100
            payment_data.append({
                "Debt": "Extra Payment",
                "Minimum": extra_payment,
                "Percentage": f"{extra_pct:.1f}%"
            })
        
        st.dataframe(pd.DataFrame(payment_data), use_container_width=True)

with tab4:
    st.subheader("🤖 AI-Powered Insights")
    
    if not debts:
        st.info("Add debts to get personalized AI advice!")
    else:
        # Calculate for AI context
        extra_payment = st.slider(
            "Extra Monthly Payment",
            min_value=0,
            max_value=2000,
            value=100,
            step=25,
            key="ai_extra"
        )
        
        snowball_schedule,