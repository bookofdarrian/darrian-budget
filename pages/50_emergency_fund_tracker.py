import streamlit as st
import datetime
from decimal import Decimal
import json

st.set_page_config(page_title="Emergency Fund Tracker", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emergency_fund (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                target_months INTEGER DEFAULT 6,
                current_balance DECIMAL(12,2) DEFAULT 0,
                monthly_contribution DECIMAL(12,2) DEFAULT 0,
                fund_name VARCHAR(100) DEFAULT 'Emergency Fund',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emergency_fund_transactions (
                id SERIAL PRIMARY KEY,
                fund_id INTEGER REFERENCES emergency_fund(id) ON DELETE CASCADE,
                amount DECIMAL(12,2) NOT NULL,
                transaction_type VARCHAR(20) NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emergency_fund (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                target_months INTEGER DEFAULT 6,
                current_balance REAL DEFAULT 0,
                monthly_contribution REAL DEFAULT 0,
                fund_name TEXT DEFAULT 'Emergency Fund',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS emergency_fund_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_id INTEGER REFERENCES emergency_fund(id) ON DELETE CASCADE,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Sidebar navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_monthly_expenses_average():
    """Calculate average monthly expenses from the expenses table"""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    
    try:
        # Get expenses from last 6 months
        if USE_POSTGRES:
            cur.execute("""
                SELECT COALESCE(AVG(monthly_total), 0) as avg_expenses
                FROM (
                    SELECT DATE_TRUNC('month', date) as month, SUM(amount) as monthly_total
                    FROM expenses
                    WHERE date >= CURRENT_DATE - INTERVAL '6 months'
                    GROUP BY DATE_TRUNC('month', date)
                ) monthly_expenses
            """)
        else:
            cur.execute("""
                SELECT COALESCE(AVG(monthly_total), 0) as avg_expenses
                FROM (
                    SELECT strftime('%Y-%m', date) as month, SUM(amount) as monthly_total
                    FROM expenses
                    WHERE date >= date('now', '-6 months')
                    GROUP BY strftime('%Y-%m', date)
                ) monthly_expenses
            """)
        
        result = cur.fetchone()
        avg = float(result[0]) if result and result[0] else 0
    except Exception as e:
        avg = 0
    finally:
        conn.close()
    
    return avg

def get_or_create_fund(user_id):
    """Get existing fund or create a new one"""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"SELECT * FROM emergency_fund WHERE user_id = {placeholder}", (user_id,))
    fund = cur.fetchone()
    
    if not fund:
        cur.execute(f"""
            INSERT INTO emergency_fund (user_id, target_months, current_balance, monthly_contribution, fund_name)
            VALUES ({placeholder}, 6, 0, 0, 'Emergency Fund')
        """, (user_id,))
        conn.commit()
        cur.execute(f"SELECT * FROM emergency_fund WHERE user_id = {placeholder}", (user_id,))
        fund = cur.fetchone()
    
    conn.close()
    
    columns = ['id', 'user_id', 'target_months', 'current_balance', 'monthly_contribution', 'fund_name', 'created_at', 'updated_at']
    return dict(zip(columns, fund))

def update_fund_settings(fund_id, target_months, monthly_contribution, fund_name):
    """Update fund settings"""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        cur.execute(f"""
            UPDATE emergency_fund 
            SET target_months = {placeholder}, monthly_contribution = {placeholder}, 
                fund_name = {placeholder}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {placeholder}
        """, (target_months, monthly_contribution, fund_name, fund_id))
    else:
        cur.execute(f"""
            UPDATE emergency_fund 
            SET target_months = {placeholder}, monthly_contribution = {placeholder}, 
                fund_name = {placeholder}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {placeholder}
        """, (target_months, monthly_contribution, fund_name, fund_id))
    
    conn.commit()
    conn.close()

def add_transaction(fund_id, amount, transaction_type, note):
    """Add a transaction and update balance"""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    
    # Add transaction
    cur.execute(f"""
        INSERT INTO emergency_fund_transactions (fund_id, amount, transaction_type, note)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (fund_id, amount, transaction_type, note))
    
    # Update balance
    balance_change = amount if transaction_type == 'deposit' else -amount
    cur.execute(f"""
        UPDATE emergency_fund 
        SET current_balance = current_balance + {placeholder}, updated_at = CURRENT_TIMESTAMP
        WHERE id = {placeholder}
    """, (balance_change, fund_id))
    
    conn.commit()
    conn.close()

def get_transactions(fund_id, limit=20):
    """Get recent transactions for a fund"""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    
    cur.execute(f"""
        SELECT id, amount, transaction_type, note, created_at
        FROM emergency_fund_transactions
        WHERE fund_id = {placeholder}
        ORDER BY created_at DESC
        LIMIT {placeholder}
    """, (fund_id, limit))
    
    transactions = cur.fetchall()
    conn.close()
    
    columns = ['id', 'amount', 'transaction_type', 'note', 'created_at']
    return [dict(zip(columns, t)) for t in transactions]

def delete_transaction(transaction_id, fund_id):
    """Delete a transaction and update balance"""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    
    # Get transaction details first
    cur.execute(f"""
        SELECT amount, transaction_type FROM emergency_fund_transactions WHERE id = {placeholder}
    """, (transaction_id,))
    tx = cur.fetchone()
    
    if tx:
        amount, tx_type = tx
        balance_change = -amount if tx_type == 'deposit' else amount
        
        # Delete transaction
        cur.execute(f"DELETE FROM emergency_fund_transactions WHERE id = {placeholder}", (transaction_id,))
        
        # Update balance
        cur.execute(f"""
            UPDATE emergency_fund 
            SET current_balance = current_balance + {placeholder}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {placeholder}
        """, (balance_change, fund_id))
        
        conn.commit()
    
    conn.close()

def get_ai_recommendations(fund_data, monthly_expenses, transactions):
    """Get AI recommendations for emergency fund savings"""
    api_key = get_setting("anthropic_api_key")
    
    if not api_key:
        return "⚠️ Please configure your Anthropic API key in settings to get AI recommendations."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        target_amount = monthly_expenses * fund_data['target_months']
        current_balance = float(fund_data['current_balance'])
        monthly_contribution = float(fund_data['monthly_contribution'])
        progress_pct = (current_balance / target_amount * 100) if target_amount > 0 else 0
        
        # Calculate months to goal
        remaining = target_amount - current_balance
        months_to_goal = (remaining / monthly_contribution) if monthly_contribution > 0 else float('inf')
        
        recent_tx_summary = ""
        if transactions:
            deposits = sum(t['amount'] for t in transactions if t['transaction_type'] == 'deposit')
            withdrawals = sum(t['amount'] for t in transactions if t['transaction_type'] == 'withdrawal')
            recent_tx_summary = f"Recent activity: ${deposits:,.2f} deposited, ${withdrawals:,.2f} withdrawn in last {len(transactions)} transactions."
        
        prompt = f"""You are a personal finance advisor helping someone build their emergency fund.

Current Situation:
- Target: {fund_data['target_months']} months of expenses (${target_amount:,.2f})
- Current Balance: ${current_balance:,.2f}
- Progress: {progress_pct:.1f}%
- Monthly Contribution: ${monthly_contribution:,.2f}
- Average Monthly Expenses: ${monthly_expenses:,.2f}
- Months to reach goal at current rate: {months_to_goal:.1f if months_to_goal != float('inf') else 'N/A (no contributions)'}
{recent_tx_summary}

Provide personalized recommendations in these areas:
1. Is their target (3-6 months) appropriate for their situation?
2. Is their current savings rate optimal? Suggest specific amounts if they should save more.
3. Timeline projection and motivation
4. Tips for accelerating progress (if applicable)
5. When they should consider stopping contributions (if close to goal)

Keep response concise (under 300 words), actionable, and encouraging. Use bullet points."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
        
    except Exception as e:
        return f"⚠️ Error getting AI recommendations: {str(e)}"

# Main UI
st.title("🏦 Emergency Fund Tracker")
st.markdown("Track your progress toward financial security with a 3-6 month emergency fund.")

user_id = get_user_id()
fund = get_or_create_fund(user_id)
monthly_expenses = get_monthly_expenses_average()

# Fund Overview Section
col1, col2, col3, col4 = st.columns(4)

target_amount = monthly_expenses * fund['target_months'] if monthly_expenses > 0 else fund['target_months'] * 3000
current_balance = float(fund['current_balance'])
progress = min((current_balance / target_amount * 100) if target_amount > 0 else 0, 100)

with col1:
    st.metric("Current Balance", f"${current_balance:,.2f}")

with col2:
    st.metric("Target Amount", f"${target_amount:,.2f}", 
              help=f"{fund['target_months']} months × ${monthly_expenses:,.2f}/month")

with col3:
    remaining = max(target_amount - current_balance, 0)
    st.metric("Remaining", f"${remaining:,.2f}")

with col4:
    monthly_contrib = float(fund['monthly_contribution'])
    if monthly_contrib > 0 and remaining > 0:
        months_left = remaining / monthly_contrib
        st.metric("Months to Goal", f"{months_left:.1f}")
    else:
        st.metric("Months to Goal", "∞" if remaining > 0 else "✓")

# Progress Bar
st.markdown("### 📊 Progress to Goal")

# Custom progress bar with color coding
if progress < 25:
    bar_color = "#ff4b4b"  # Red
    status = "🔴 Just Getting Started"
elif progress < 50:
    bar_color = "#ffa500"  # Orange
    status = "🟠 Making Progress"
elif progress < 75:
    bar_color = "#ffdd00"  # Yellow
    status = "🟡 Halfway There"
elif progress < 100:
    bar_color = "#90EE90"  # Light Green
    status = "🟢 Almost There!"
else:
    bar_color = "#00ff00"  # Green
    status = "✅ Goal Reached!"

st.markdown(f"""
<div style="background-color: #f0f0f0; border-radius: 10px; padding: 3px;">
    <div style="background-color: {bar_color}; width: {progress}%; height: 30px; border-radius: 8px; 
                display: flex; align-items: center; justify-content: center; color: black; font-weight: bold;">
        {progress:.1f}%
    </div>
</div>
<p style="text-align: center; margin-top: 10px; font-size: 18px;">{status}</p>
""", unsafe_allow_html=True)

st.markdown("---")

# Two-column layout for main content
left_col, right_col = st.columns([1, 1])

with left_col:
    # Add Transaction Section
    st.markdown("### 💰 Add Transaction")
    
    with st.form("add_transaction_form"):
        tx_col1, tx_col2 = st.columns(2)
        
        with tx_col1:
            tx_type = st.selectbox("Type", ["deposit", "withdrawal"])
        
        with tx_col2:
            tx_amount = st.number_input("Amount ($)", min_value=0.01, value=100.00, step=10.00)
        
        tx_note = st.text_input("Note (optional)", placeholder="e.g., Monthly contribution, Tax refund")
        
        submitted = st.form_submit_button("Add Transaction", use_container_width=True)
        
        if submitted:
            if tx_type == "withdrawal" and tx_amount > current_balance:
                st.error("❌ Insufficient funds for withdrawal!")
            else:
                add_transaction(fund['id'], tx_amount, tx_type, tx_note)
                st.success(f"✅ {tx_type.capitalize()} of ${tx_amount:,.2f} recorded!")
                st.rerun()
    
    # Fund Settings
    st.markdown("### ⚙️ Fund Settings")
    
    with st.form("fund_settings_form"):
        fund_name = st.text_input("Fund Name", value=fund['fund_name'])
        
        settings_col1, settings_col2 = st.columns(2)
        
        with settings_col1:
            target_months = st.selectbox(
                "Target Months of Expenses",
                options=[3, 4, 5, 6, 9, 12],
                index=[3, 4, 5, 6, 9, 12].index(fund['target_months']) if fund['target_months'] in [3, 4, 5, 6, 9, 12] else 3
            )
        
        with settings_col2:
            monthly_contribution_input = st.number_input(
                "Monthly Contribution ($)",
                min_value=0.00,
                value=float(fund['monthly_contribution']),
                step=50.00
            )
        
        if monthly_expenses > 0:
            st.info(f"💡 Your average monthly expenses: **${monthly_expenses:,.2f}**")
        else:
            st.warning("⚠️ No expense data found. Add expenses to calculate your target automatically.")
            manual_expenses = st.number_input("Enter estimated monthly expenses ($)", min_value=0.00, value=3000.00, step=100.00)
        
        save_settings = st.form_submit_button("Save Settings", use_container_width=True)
        
        if save_settings:
            update_fund_settings(fund['id'], target_months, monthly_contribution_input, fund_name)
            st.success("✅ Settings updated!")
            st.rerun()

with right_col:
    # Transaction History
    st.markdown("### 📜 Transaction History")
    
    transactions = get_transactions(fund['id'], limit=20)
    
    if transactions:
        for tx in transactions:
            tx_icon = "➕" if tx['transaction_type'] == 'deposit' else "➖"
            tx_color = "#00ff00" if tx['transaction_type'] == 'deposit' else "#ff4b4b"
            tx_date = tx['created_at']
            if isinstance(tx_date, str):
                tx_date = tx_date[:10]
            else:
                tx_date = tx_date.strftime("%Y-%m-%d") if tx_date else "N/A"
            
            tx_note = tx['note'] if tx['note'] else "No note"
            
            with st.container():
                tcol1, tcol2, tcol3 = st.columns([3, 1, 1])
                with tcol1:
                    st.markdown(f"""
                    <div style="padding: 10px; border-left: 4px solid {tx_color}; margin-bottom: 10px; background: rgba(255,255,255,0.05); border-radius: 5px;">
                        <strong>{tx_icon} ${tx['amount']:,.2f}</strong> - {tx['transaction_type'].capitalize()}<br>
                        <small style="color: #888;">{tx_date} | {tx_note}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with tcol2:
                    st.write("")
                with tcol3:
                    if st.button("🗑️", key=f"del_{tx['id']}", help="Delete transaction"):
                        delete_transaction(tx['id'], fund['id'])
                        st.rerun()
    else:
        st.info("📭 No transactions yet. Add your first contribution above!")

# AI Recommendations Section
st.markdown("---")
st.markdown("### 🤖 AI-Powered Recommendations")

if st.button("Get Personalized Recommendations", use_container_width=True):
    with st.spinner("Analyzing your emergency fund strategy..."):
        effective_expenses = monthly_expenses if monthly_expenses > 0 else 3000
        recommendations = get_ai_recommendations(fund, effective_expenses, transactions)
        st.session_state['ai_recommendations'] = recommendations

if 'ai_recommendations' in st.session_state:
    st.markdown(st.session_state['ai_recommendations'])

# Quick Stats Section
st.markdown("---")
st.markdown("### 📈 Quick Stats")

stats_col1, stats_col2, stats_col3 = st.columns(3)

with stats_col1:
    # Calculate total deposits
    all_transactions = get_transactions(fund['id'], limit=1000)
    total_deposits = sum(t['amount'] for t in all_transactions if t['transaction_type'] == 'deposit')
    st.metric("Total Deposited", f"${total_deposits:,.2f}")

with stats_col2:
    total_withdrawals = sum(t['amount'] for t in all_transactions if t['transaction_type'] == 'withdrawal')
    st.metric("Total Withdrawn", f"${total_withdrawals:,.2f}")

with stats_col3:
    # Savings rate (contribution as % of expenses)
    if monthly_expenses > 0:
        savings_rate = (float(fund['monthly_contribution']) / monthly_expenses) * 100
        st.metric("Savings Rate", f"{savings_rate:.1f}%", help="Monthly contribution as % of expenses")
    else:
        st.metric("Savings Rate", "N/A")

# Educational Tips
with st.expander("💡 Emergency Fund Tips"):
    st.markdown("""
    **Why 3-6 months?**
    - 3 months: Good baseline if you have stable employment and low expenses
    - 6 months: Recommended if you're self-employed, have variable income, or are the sole earner
    - 9-12 months: Consider if you work in a volatile industry or have high fixed expenses
    
    **Where to keep your emergency fund:**
    - High-yield savings account (HYSA) - Currently 4-5% APY
    - Money market account
    - Short-term CDs (with no early withdrawal penalty)
    
    **When to use your emergency fund:**
    - ✅ Job loss or reduced income
    - ✅ Medical emergencies
    - ✅ Urgent home or car repairs
    - ❌ Vacations or entertainment
    - ❌ Non-urgent purchases
    - ❌ Investment opportunities
    
    **Tips for building faster:**
    - Automate monthly transfers on payday
    - Direct deposit tax refunds directly to savings
    - Sell unused items and save the proceeds
    - Use windfalls (bonuses, gifts) to boost your fund
    """)