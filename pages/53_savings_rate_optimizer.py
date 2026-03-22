import streamlit as st
import json
import datetime
from decimal import Decimal
import traceback

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Savings Rate Optimizer", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _get_placeholder():
    return "%s" if USE_POSTGRES else "?"


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS savings_rate_analysis (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                analysis_date DATE NOT NULL,
                total_income DECIMAL(12,2) NOT NULL,
                total_expenses DECIMAL(12,2) NOT NULL,
                savings_amount DECIMAL(12,2) NOT NULL,
                savings_rate DECIMAL(5,2) NOT NULL,
                ai_recommendations TEXT,
                spending_leaks TEXT,
                scenario_projections TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_name VARCHAR(255) NOT NULL,
                target_amount DECIMAL(12,2) NOT NULL,
                current_amount DECIMAL(12,2) DEFAULT 0,
                target_date DATE,
                priority INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS savings_rate_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                analysis_date DATE NOT NULL,
                total_income REAL NOT NULL,
                total_expenses REAL NOT NULL,
                savings_amount REAL NOT NULL,
                savings_rate REAL NOT NULL,
                ai_recommendations TEXT,
                spending_leaks TEXT,
                scenario_projections TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                goal_name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date DATE,
                priority INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_financial_summary(user_id, months=3):
    """Calculate current savings rate from income/expenses tables"""
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=months * 30)
    
    total_income = 0
    total_expenses = 0
    expense_breakdown = {}
    
    try:
        cur.execute(f"""
            SELECT COALESCE(SUM(amount), 0) FROM income 
            WHERE user_id = {ph} AND date >= {ph} AND date <= {ph}
        """, (user_id, start_date, end_date))
        result = cur.fetchone()
        total_income = float(result[0]) if result and result[0] else 0
    except Exception:
        pass
    
    try:
        cur.execute(f"""
            SELECT category, COALESCE(SUM(amount), 0) FROM expenses 
            WHERE user_id = {ph} AND date >= {ph} AND date <= {ph}
            GROUP BY category
        """, (user_id, start_date, end_date))
        for row in cur.fetchall():
            category = row[0] or "Uncategorized"
            amount = float(row[1]) if row[1] else 0
            expense_breakdown[category] = amount
            total_expenses += amount
    except Exception:
        pass
    
    conn.close()
    
    savings_amount = total_income - total_expenses
    savings_rate = (savings_amount / total_income * 100) if total_income > 0 else 0
    
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "savings_amount": savings_amount,
        "savings_rate": round(savings_rate, 2),
        "expense_breakdown": expense_breakdown,
        "months_analyzed": months
    }


def get_spending_leaks(expense_breakdown, total_income):
    """Identify potential spending leaks based on category analysis"""
    leaks = []
    
    benchmarks = {
        "Food": 15,
        "Dining": 10,
        "Entertainment": 5,
        "Shopping": 10,
        "Subscriptions": 3,
        "Transportation": 15,
        "Utilities": 10,
        "Housing": 30,
        "Healthcare": 8,
        "Personal": 5
    }
    
    if total_income <= 0:
        return leaks
    
    for category, amount in expense_breakdown.items():
        percentage = (amount / total_income) * 100
        
        for benchmark_cat, benchmark_pct in benchmarks.items():
            if benchmark_cat.lower() in category.lower():
                if percentage > benchmark_pct * 1.2:
                    leaks.append({
                        "category": category,
                        "amount": amount,
                        "percentage": round(percentage, 1),
                        "benchmark": benchmark_pct,
                        "overspend": round(amount - (total_income * benchmark_pct / 100), 2),
                        "severity": "high" if percentage > benchmark_pct * 1.5 else "medium"
                    })
                break
    
    return sorted(leaks, key=lambda x: x["overspend"], reverse=True)


def calculate_scenario_projections(current_savings, monthly_income, goals):
    """Project time-to-goal for different savings rate scenarios"""
    scenarios = [10, 15, 20, 25, 30, 35, 40, 50]
    projections = {}
    
    for rate in scenarios:
        monthly_savings = monthly_income * (rate / 100)
        scenario_goals = []
        
        for goal in goals:
            target = goal.get("target_amount", 0)
            current = goal.get("current_amount", 0)
            remaining = target - current
            
            if remaining <= 0:
                months_to_goal = 0
            elif monthly_savings > 0:
                months_to_goal = remaining / monthly_savings
            else:
                months_to_goal = float('inf')
            
            scenario_goals.append({
                "goal_name": goal.get("goal_name", "Unknown"),
                "target_amount": target,
                "current_amount": current,
                "months_to_goal": round(months_to_goal, 1) if months_to_goal != float('inf') else None,
                "projected_date": (datetime.date.today() + datetime.timedelta(days=months_to_goal * 30)).isoformat() if months_to_goal != float('inf') and months_to_goal > 0 else None
            })
        
        projections[rate] = {
            "monthly_savings": round(monthly_savings, 2),
            "annual_savings": round(monthly_savings * 12, 2),
            "goals": scenario_goals
        }
    
    return projections


def get_ai_recommendations(financial_summary, spending_leaks, goals):
    """Get AI-powered recommendations using Claude"""
    api_key = get_setting("anthropic_api_key")
    
    if not api_key:
        return None
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are a personal finance advisor. Analyze the following financial data and provide actionable recommendations to optimize the user's savings rate.

FINANCIAL SUMMARY (Last {financial_summary['months_analyzed']} months):
- Total Income: ${financial_summary['total_income']:,.2f}
- Total Expenses: ${financial_summary['total_expenses']:,.2f}
- Current Savings: ${financial_summary['savings_amount']:,.2f}
- Current Savings Rate: {financial_summary['savings_rate']}%

EXPENSE BREAKDOWN:
{json.dumps(financial_summary['expense_breakdown'], indent=2)}

IDENTIFIED SPENDING LEAKS:
{json.dumps(spending_leaks, indent=2)}

SAVINGS GOALS:
{json.dumps(goals, indent=2)}

Please provide:
1. An assessment of the current savings rate (is it healthy? how does it compare to recommended 20%+ rate?)
2. Top 3 specific, actionable recommendations to increase savings rate
3. Which spending categories have the most optimization potential
4. A realistic target savings rate based on their income and expenses
5. Any lifestyle adjustments that could have the biggest impact

Keep your response concise, practical, and encouraging. Format with clear sections."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
    except Exception as e:
        return f"AI analysis unavailable: {str(e)}"


def save_analysis(user_id, financial_summary, spending_leaks, scenario_projections, ai_recommendations):
    """Save analysis snapshot to database"""
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    cur.execute(f"""
        INSERT INTO savings_rate_analysis 
        (user_id, analysis_date, total_income, total_expenses, savings_amount, 
         savings_rate, ai_recommendations, spending_leaks, scenario_projections)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (
        user_id,
        datetime.date.today(),
        financial_summary["total_income"],
        financial_summary["total_expenses"],
        financial_summary["savings_amount"],
        financial_summary["savings_rate"],
        ai_recommendations or "",
        json.dumps(spending_leaks),
        json.dumps(scenario_projections)
    ))
    
    conn.commit()
    conn.close()


def get_analysis_history(user_id, limit=10):
    """Get historical analysis records"""
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    cur.execute(f"""
        SELECT id, analysis_date, total_income, total_expenses, savings_amount, savings_rate
        FROM savings_rate_analysis 
        WHERE user_id = {ph}
        ORDER BY analysis_date DESC
        LIMIT {ph}
    """, (user_id, limit))
    
    rows = cur.fetchall()
    conn.close()
    return rows


def get_goals(user_id):
    """Get active savings goals"""
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    is_active_val = True if USE_POSTGRES else 1
    
    cur.execute(f"""
        SELECT id, goal_name, target_amount, current_amount, target_date, priority
        FROM savings_goals 
        WHERE user_id = {ph} AND is_active = {ph}
        ORDER BY priority
    """, (user_id, is_active_val))
    
    rows = cur.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "goal_name": r[1],
            "target_amount": float(r[2]) if r[2] else 0,
            "current_amount": float(r[3]) if r[3] else 0,
            "target_date": r[4],
            "priority": r[5]
        }
        for r in rows
    ]


def add_goal(user_id, goal_name, target_amount, current_amount, target_date, priority):
    """Add a new savings goal"""
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    cur.execute(f"""
        INSERT INTO savings_goals (user_id, goal_name, target_amount, current_amount, target_date, priority)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, goal_name, target_amount, current_amount, target_date, priority))
    
    conn.commit()
    conn.close()


def update_goal(goal_id, goal_name, target_amount, current_amount, target_date, priority):
    """Update an existing goal"""
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    cur.execute(f"""
        UPDATE savings_goals 
        SET goal_name = {ph}, target_amount = {ph}, current_amount = {ph}, 
            target_date = {ph}, priority = {ph}
        WHERE id = {ph}
    """, (goal_name, target_amount, current_amount, target_date, priority, goal_id))
    
    conn.commit()
    conn.close()


def delete_goal(goal_id):
    """Delete a savings goal"""
    conn = get_conn()
    cur = conn.cursor()
    ph = _get_placeholder()
    
    cur.execute(f"DELETE FROM savings_goals WHERE id = {ph}", (goal_id,))
    conn.commit()
    conn.close()


_ensure_tables()

st.title("💰 Savings Rate Optimizer")
st.markdown("*AI-powered analysis to maximize your savings and reach your goals faster*")

user_id = st.session_state.get("user_id", 1)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "🎯 Goals", "📈 Scenarios", "📜 History"])

with tab1:
    st.subheader("Current Financial Analysis")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        months_to_analyze = st.selectbox("Analysis Period", [1, 3, 6, 12], index=1, format_func=lambda x: f"{x} month{'s' if x > 1 else ''}")
    
    if st.button("🔄 Run Analysis", type="primary"):
        with st.spinner("Analyzing your finances..."):
            financial_summary = get_financial_summary(user_id, months_to_analyze)
            spending_leaks = get_spending_leaks(financial_summary["expense_breakdown"], financial_summary["total_income"])
            goals = get_goals(user_id)
            scenario_projections = calculate_scenario_projections(
                financial_summary["savings_amount"],
                financial_summary["total_income"] / months_to_analyze,
                goals
            )
            ai_recommendations = get_ai_recommendations(financial_summary, spending_leaks, goals)
            
            save_analysis(user_id, financial_summary, spending_leaks, scenario_projections, ai_recommendations)
            
            st.session_state["last_analysis"] = {
                "financial_summary": financial_summary,
                "spending_leaks": spending_leaks,
                "scenario_projections": scenario_projections,
                "ai_recommendations": ai_recommendations
            }
        
        st.success("Analysis complete!")
        st.rerun()
    
    if "last_analysis" in st.session_state:
        analysis = st.session_state["last_analysis"]
        fs = analysis["financial_summary"]
        
        st.markdown("### 📊 Financial Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Income", f"${fs['total_income']:,.2f}", help=f"Last {fs['months_analyzed']} month(s)")
        
        with col2:
            st.metric("Total Expenses", f"${fs['total_expenses']:,.2f}")
        
        with col3:
            savings_color = "normal" if fs['savings_amount'] >= 0 else "inverse"
            st.metric("Net Savings", f"${fs['savings_amount']:,.2f}")
        
        with col4:
            rate_status = "🟢" if fs['savings_rate'] >= 20 else "🟡" if fs['savings_rate'] >= 10 else "🔴"
            st.metric("Savings Rate", f"{rate_status} {fs['savings_rate']}%", help="Target: 20%+")
        
        st.markdown("### 💸 Expense Breakdown")
        if fs["expense_breakdown"]:
            import pandas as pd
            expense_df = pd.DataFrame([
                {"Category": cat, "Amount": amt, "% of Income": round(amt / fs['total_income'] * 100, 1) if fs['total_income'] > 0 else 0}
                for cat, amt in sorted(fs["expense_breakdown"].items(), key=lambda x: x[1], reverse=True)
            ])
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.bar_chart(expense_df.set_index("Category")["Amount"])
            with col2:
                st.dataframe(expense_df, hide_index=True, use_container_width=True)
        else:
            st.info("No expense data found for the selected period.")
        
        if analysis["spending_leaks"]:
            st.markdown("### 🚨 Spending Leaks Detected")
            for leak in analysis["spending_leaks"]:
                severity_icon = "🔴" if leak["severity"] == "high" else "🟡"
                with st.expander(f"{severity_icon} {leak['category']} - ${leak['overspend']:,.2f} over benchmark"):
                    st.write(f"**Current Spending:** ${leak['amount']:,.2f} ({leak['percentage']}% of income)")
                    st.write(f"**Benchmark:** {leak['benchmark']}% of income")
                    st.write(f"**Potential Savings:** ${leak['overspend']:,.2f}/period")
                    st.progress(min(leak["benchmark"] / leak["percentage"], 1.0))
        
        if analysis["ai_recommendations"]:
            st.markdown("### 🤖 AI Recommendations")
            st.markdown(analysis["ai_recommendations"])
    else:
        st.info("👆 Click 'Run Analysis' to analyze your current savings rate and get AI-powered recommendations.")
        
        st.markdown("### What this tool analyzes:")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            - 📈 **Income vs Expenses** - Your actual savings rate
            - 💰 **Spending Patterns** - Where your money goes
            - 🚨 **Spending Leaks** - Categories where you overspend
            """)
        with col2:
            st.markdown("""
            - 🎯 **Goal Projections** - Time to reach your targets
            - 🤖 **AI Insights** - Personalized recommendations
            - 📊 **Scenario Analysis** - What-if calculations
            """)

with tab2:
    st.subheader("🎯 Savings Goals")
    
    goals = get_goals(user_id)
    
    with st.expander("➕ Add New Goal", expanded=len(goals) == 0):
        with st.form("new_goal_form"):
            goal_name = st.text_input("Goal Name", placeholder="e.g., Emergency Fund, House Down Payment")
            col1, col2 = st.columns(2)
            with col1:
                target_amount = st.number_input("Target Amount ($)", min_value=0.0, step=100.0, value=10000.0)
                current_amount = st.number_input("Current Amount ($)", min_value=0.0, step=100.0, value=0.0)
            with col2:
                target_date = st.date_input("Target Date", value=datetime.date.today() + datetime.timedelta(days=365))
                priority = st.selectbox("Priority", [1, 2, 3, 4, 5], format_func=lambda x: f"{x} - {'High' if x == 1 else 'Medium' if x <= 3 else 'Low'}")
            
            if st.form_submit_button("Add Goal", type="primary"):
                if goal_name:
                    add_goal(user_id, goal_name, target_amount, current_amount, target_date, priority)
                    st.success(f"Added goal: {goal_name}")
                    st.rerun()
                else:
                    st.error("Please enter a goal name.")
    
    if goals:
        st.markdown("### Active Goals")
        for goal in goals:
            progress = (goal["current_amount"] / goal["target_amount"] * 100) if goal["target_amount"] > 0 else 0
            remaining = goal["target_amount"] - goal["current_amount"]
            
            with st.expander(f"🎯 {goal['goal_name']} - {progress:.1f}% complete"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.metric("Progress", f"${goal['current_amount']:,.2f}", f"of ${goal['target_amount']:,.2f}")
                    st.progress(min(progress / 100, 1.0))
                
                with col2:
                    st.metric("Remaining", f"${remaining:,.2f}")
                    if goal["target_date"]:
                        days_left = (goal["target_date"] - datetime.date.today()).days if isinstance(goal["target_date"], datetime.date) else 0
                        st.write(f"📅 Target: {goal['target_date']} ({days_left} days left)")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{goal['id']}"):
                        delete_goal(goal["id"])
                        st.success("Goal deleted!")
                        st.rerun()
                
                with st.form(f"edit_goal_{goal['id']}"):
                    st.markdown("**Update Goal**")
                    new_current = st.number_input("Current Amount", value=goal["current_amount"], key=f"curr_{goal['id']}")
                    if st.form_submit_button("Update"):
                        update_goal(goal["id"], goal["goal_name"], goal["target_amount"], new_current, goal["target_date"], goal["priority"])
                        st.success("Goal updated!")
                        st.rerun()
    else:
        st.info("No savings goals yet. Add your first goal above!")

with tab3:
    st.subheader("📈 Savings Scenario Projections")
    
    goals = get_goals(user_id)
    
    if "last_analysis" in st.session_state:
        fs = st.session_state["last_analysis"]["financial_summary"]
        monthly_income = fs["total_income"] / fs["months_analyzed"]
        
        st.markdown(f"**Monthly Income Estimate:** ${monthly_income:,.2f}")
        
        scenario_projections = calculate_scenario_projections(
            fs["savings_amount"],
            monthly_income,
            goals
        )
        
        st.markdown("### Compare Savings Rate Scenarios")
        
        import pandas as pd
        
        scenario_data = []
        for rate, data in scenario_projections.items():
            row = {
                "Savings Rate": f"{rate}%",
                "Monthly Savings": f"${data['monthly_savings']:,.2f}",
                "Annual Savings": f"${data['annual_savings']:,.2f}"
            }
            for goal in data["goals"]:
                months = goal["months_to_goal"]
                if months is not None and months != float('inf'):
                    years = months / 12
                    row[goal["goal_name"]] = f"{years:.1f} years" if years >= 1 else f"{months:.0f} months"
                else:
                    row[goal["goal_name"]] = "N/A"
            scenario_data.append(row)
        
        scenario_df = pd.DataFrame(scenario_data)
        st.dataframe(scenario_df, hide_index=True, use_container_width=True)
        
        st.markdown("### Interactive Calculator")
        
        custom_rate = st.slider("Custom Savings Rate (%)", min_value=5, max_value=70, value=20, step=5)
        custom_monthly = monthly_income * (custom_rate / 100)
        custom_annual = custom_monthly * 12
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Monthly Savings", f"${custom_monthly:,.2f}")
        with col2:
            st.metric("Annual Savings", f"${custom_annual:,.2f}")
        with col3:
            five_year = custom_annual * 5
            st.metric("5-Year Total", f"${five_year:,.2f}")
        
        if goals:
            st.markdown("### Goal Timelines at Selected Rate")
            for goal in goals:
                remaining = goal["target_amount"] - goal["current_amount"]
                if remaining > 0 and custom_monthly > 0:
                    months_needed = remaining / custom_monthly
                    target_date = datetime.date.today() + datetime.timedelta(days=months_needed * 30)
                    st.write(f"🎯 **{goal['goal_name']}**: {months_needed:.1f} months (by {target_date.strftime('%B %Y')})")
                elif remaining <= 0:
                    st.write(f"✅ **{goal['goal_name']}**: Already achieved!")
    else:
        st.info("Run an analysis first to see scenario projections.")

with tab4:
    st.subheader("📜 Analysis History")
    
    history = get_analysis_history(user_id, 20)
    
    if history:
        import pandas as pd
        
        history_data = []
        for row in history:
            history_data.append({
                "Date": row[1],
                "Income": f"${float(row[2]):,.2f}" if row[2] else "$0.00",
                "Expenses": f"${float(row[3]):,.2f}" if row[3] else "$0.00",
                "Savings": f"${float(row[4]):,.2f}" if row[4] else "$0.00",
                "Rate": f"{float(row[5]):.1f}%" if row[5] else "0%"
            })
        
        st.dataframe(pd.DataFrame(history_data), hide_index=True, use_container_width=True)
        
        st.markdown("### Savings Rate Trend")
        trend_data = pd.DataFrame([
            {"Date": str(row[1]), "Savings Rate": float(row[5]) if row[5] else 0}
            for row in reversed(history)
        ])
        
        if len(trend_data) > 1:
            st.line_chart(trend_data.set_index("Date"))
        else:
            st.info("Need more data points to show trend chart.")
    else:
        st.info("No analysis history yet. Run your first analysis to start tracking!")

st.markdown("---")
st.markdown("*💡 Tip: Financial experts recommend saving at least 20% of your income. Use the scenario projections to find the right balance for your goals.*")