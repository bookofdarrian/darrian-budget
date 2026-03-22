import streamlit as st
import json
from datetime import datetime, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Credit Score Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_scores (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                score INTEGER NOT NULL,
                bureau VARCHAR(50) NOT NULL,
                factors_json TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_score_alerts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 1,
                milestone INTEGER NOT NULL,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified BOOLEAN DEFAULT FALSE
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                score INTEGER NOT NULL,
                bureau TEXT NOT NULL,
                factors_json TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_score_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                milestone INTEGER NOT NULL,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified INTEGER DEFAULT 0
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

def get_all_scores(user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, score, bureau, factors_json, recorded_at
        FROM credit_scores
        WHERE user_id = {ph}
        ORDER BY recorded_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_latest_score(user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, score, bureau, factors_json, recorded_at
        FROM credit_scores
        WHERE user_id = {ph}
        ORDER BY recorded_at DESC
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_score(user_id, score, bureau, factors):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    factors_json = json.dumps(factors) if factors else None
    cur.execute(f"""
        INSERT INTO credit_scores (user_id, score, bureau, factors_json, recorded_at)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, score, bureau, factors_json, datetime.now()))
    conn.commit()
    conn.close()
    check_milestones(user_id, score)

def update_score(score_id, score, bureau, factors):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    factors_json = json.dumps(factors) if factors else None
    cur.execute(f"""
        UPDATE credit_scores
        SET score = {ph}, bureau = {ph}, factors_json = {ph}
        WHERE id = {ph}
    """, (score, bureau, factors_json, score_id))
    conn.commit()
    conn.close()

def delete_score(score_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM credit_scores WHERE id = {ph}", (score_id,))
    conn.commit()
    conn.close()

def get_score_by_id(score_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, score, bureau, factors_json, recorded_at
        FROM credit_scores
        WHERE id = {ph}
    """, (score_id,))
    row = cur.fetchone()
    conn.close()
    return row

def calculate_trend(user_id=1):
    scores = get_all_scores(user_id)
    if len(scores) < 2:
        return None, None
    latest = scores[0][1]
    previous = scores[1][1]
    change = latest - previous
    pct_change = (change / previous * 100) if previous > 0 else 0
    return change, pct_change

def get_score_rating(score):
    if score >= 800:
        return "Exceptional", "🏆"
    elif score >= 740:
        return "Very Good", "🌟"
    elif score >= 670:
        return "Good", "✅"
    elif score >= 580:
        return "Fair", "⚠️"
    else:
        return "Poor", "🔴"

def check_milestones(user_id, score):
    milestones = [700, 750, 800, 850]
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    for milestone in milestones:
        if score >= milestone:
            cur.execute(f"""
                SELECT id FROM credit_score_alerts
                WHERE user_id = {ph} AND milestone = {ph}
            """, (user_id, milestone))
            existing = cur.fetchone()
            if not existing:
                cur.execute(f"""
                    INSERT INTO credit_score_alerts (user_id, milestone, achieved_at, notified)
                    VALUES ({ph}, {ph}, {ph}, {ph})
                """, (user_id, milestone, datetime.now(), False if USE_POSTGRES else 0))
    conn.commit()
    conn.close()

def get_unnotified_milestones(user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    notified_val = False if USE_POSTGRES else 0
    cur.execute(f"""
        SELECT id, milestone, achieved_at FROM credit_score_alerts
        WHERE user_id = {ph} AND notified = {ph}
        ORDER BY milestone DESC
    """, (user_id, notified_val))
    rows = cur.fetchall()
    conn.close()
    return rows

def mark_milestone_notified(alert_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    notified_val = True if USE_POSTGRES else 1
    cur.execute(f"""
        UPDATE credit_score_alerts SET notified = {ph} WHERE id = {ph}
    """, (notified_val, alert_id))
    conn.commit()
    conn.close()

def get_ai_recommendations(score, factors):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "Configure your Anthropic API key in settings to get AI-powered recommendations."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        factors_text = ""
        if factors:
            factors_text = "\n".join([f"- {k}: {v}" for k, v in factors.items()])
        
        prompt = f"""You are a financial advisor specializing in credit improvement. 
        
The user has a credit score of {score}.

Their credit factors are:
{factors_text if factors_text else "No specific factors provided."}

Please provide:
1. A brief assessment of their credit standing
2. 3-5 specific, actionable recommendations to improve their credit score
3. Any warnings or things to avoid
4. Estimated timeline for potential improvement

Keep your response concise, friendly, and actionable. Use bullet points where appropriate."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error getting AI recommendations: {str(e)}"

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

# Main content
st.title("📈 Credit Score Tracker")
st.markdown("Track your credit score history, analyze factors, and get AI-powered improvement tips.")

# Check for milestone celebrations
milestones = get_unnotified_milestones()
for m in milestones:
    alert_id, milestone, achieved_at = m
    st.balloons()
    st.success(f"🎉 Congratulations! You've reached a credit score of {milestone}+!")
    mark_milestone_notified(alert_id)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "➕ Add Score", "📜 History", "🤖 AI Insights"])

with tab1:
    latest = get_latest_score()
    
    if latest:
        score_id, score, bureau, factors_json, recorded_at = latest
        rating, emoji = get_score_rating(score)
        change, pct_change = calculate_trend()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            delta_str = f"{change:+d}" if change else None
            st.metric("Current Score", score, delta=delta_str)
        
        with col2:
            st.metric("Rating", f"{emoji} {rating}")
        
        with col3:
            st.metric("Bureau", bureau)
        
        with col4:
            if isinstance(recorded_at, str):
                recorded_at = datetime.fromisoformat(recorded_at)
            st.metric("Last Updated", recorded_at.strftime("%b %d, %Y"))
        
        st.markdown("---")
        
        # Score trend chart
        all_scores = get_all_scores()
        if len(all_scores) >= 2:
            st.subheader("📈 Score History")
            
            import pandas as pd
            
            chart_data = []
            for row in reversed(all_scores):
                s_id, s_score, s_bureau, s_factors, s_date = row
                if isinstance(s_date, str):
                    s_date = datetime.fromisoformat(s_date)
                chart_data.append({
                    "Date": s_date,
                    "Score": s_score,
                    "Bureau": s_bureau
                })
            
            df = pd.DataFrame(chart_data)
            
            # Line chart
            st.line_chart(df.set_index("Date")["Score"], use_container_width=True)
            
            # Score range visualization
            st.subheader("📊 Score Range")
            col1, col2 = st.columns([3, 1])
            with col1:
                progress = min(max((score - 300) / 550, 0), 1)
                st.progress(progress)
                st.caption("300 ────────────────────────────────────────────── 850")
            with col2:
                if score >= 800:
                    st.success("Exceptional!")
                elif score >= 740:
                    st.info("Very Good")
                elif score >= 670:
                    st.warning("Good")
                else:
                    st.error("Needs Work")
        
        # Factor breakdown
        if factors_json:
            st.markdown("---")
            st.subheader("🔍 Credit Factors")
            
            factors = json.loads(factors_json) if isinstance(factors_json, str) else factors_json
            
            if factors:
                cols = st.columns(min(len(factors), 3))
                factor_icons = {
                    "payment_history": "💳",
                    "credit_utilization": "📊",
                    "credit_age": "📅",
                    "credit_mix": "🎯",
                    "hard_inquiries": "🔍",
                    "total_accounts": "📁",
                    "derogatory_marks": "⚠️"
                }
                
                for i, (key, value) in enumerate(factors.items()):
                    with cols[i % 3]:
                        icon = factor_icons.get(key, "📌")
                        display_key = key.replace("_", " ").title()
                        st.metric(f"{icon} {display_key}", value)
    else:
        st.info("👋 Welcome! Add your first credit score to start tracking.")
        st.markdown("""
        ### Getting Started
        1. Click the **Add Score** tab
        2. Enter your credit score from any major bureau
        3. Optionally add credit factors for detailed analysis
        4. Get AI-powered recommendations to improve your score
        """)

with tab2:
    st.subheader("➕ Add New Credit Score")
    
    with st.form("add_score_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_score = st.number_input("Credit Score", min_value=300, max_value=850, value=700, step=1)
        
        with col2:
            bureau = st.selectbox("Credit Bureau", ["Experian", "Equifax", "TransUnion", "FICO", "VantageScore", "Other"])
        
        st.markdown("#### Credit Factors (Optional)")
        st.caption("These help provide more detailed analysis and recommendations.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            payment_history = st.selectbox("Payment History", ["Excellent", "Good", "Fair", "Poor", "N/A"])
            credit_utilization = st.number_input("Credit Utilization %", min_value=0, max_value=100, value=30)
        
        with col2:
            credit_age = st.text_input("Average Credit Age", placeholder="e.g., 5 years")
            credit_mix = st.selectbox("Credit Mix", ["Excellent", "Good", "Fair", "Limited", "N/A"])
        
        with col3:
            hard_inquiries = st.number_input("Hard Inquiries (last 2 years)", min_value=0, max_value=50, value=0)
            total_accounts = st.number_input("Total Accounts", min_value=0, max_value=100, value=5)
        
        derogatory = st.selectbox("Derogatory Marks", ["None", "1", "2", "3+"])
        
        submitted = st.form_submit_button("💾 Save Score", use_container_width=True)
        
        if submitted:
            factors = {}
            if payment_history != "N/A":
                factors["payment_history"] = payment_history
            if credit_utilization is not None:
                factors["credit_utilization"] = f"{credit_utilization}%"
            if credit_age:
                factors["credit_age"] = credit_age
            if credit_mix != "N/A":
                factors["credit_mix"] = credit_mix
            if hard_inquiries is not None:
                factors["hard_inquiries"] = hard_inquiries
            if total_accounts is not None:
                factors["total_accounts"] = total_accounts
            if derogatory != "None":
                factors["derogatory_marks"] = derogatory
            
            add_score(1, new_score, bureau, factors)
            st.success(f"✅ Credit score of {new_score} from {bureau} saved!")
            st.rerun()

with tab3:
    st.subheader("📜 Score History")
    
    all_scores = get_all_scores()
    
    if all_scores:
        for row in all_scores:
            score_id, score, bureau, factors_json, recorded_at = row
            rating, emoji = get_score_rating(score)
            
            if isinstance(recorded_at, str):
                recorded_at = datetime.fromisoformat(recorded_at)
            
            with st.expander(f"{emoji} {score} - {bureau} ({recorded_at.strftime('%b %d, %Y')})"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.metric("Score", score)
                    st.caption(f"Rating: {rating}")
                
                with col2:
                    st.metric("Bureau", bureau)
                    st.caption(f"Recorded: {recorded_at.strftime('%Y-%m-%d %H:%M')}")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{score_id}"):
                        delete_score(score_id)
                        st.success("Score deleted!")
                        st.rerun()
                
                if factors_json:
                    factors = json.loads(factors_json) if isinstance(factors_json, str) else factors_json
                    if factors:
                        st.markdown("**Factors:**")
                        for key, value in factors.items():
                            st.caption(f"• {key.replace('_', ' ').title()}: {value}")
    else:
        st.info("No credit scores recorded yet. Add your first score to start tracking!")

with tab4:
    st.subheader("🤖 AI-Powered Credit Insights")
    
    latest = get_latest_score()
    
    if latest:
        score_id, score, bureau, factors_json, recorded_at = latest
        factors = json.loads(factors_json) if factors_json else {}
        
        rating, emoji = get_score_rating(score)
        st.info(f"Analyzing your credit score of **{score}** ({rating}) from {bureau}")
        
        if st.button("🔮 Get AI Recommendations", use_container_width=True):
            with st.spinner("Analyzing your credit profile..."):
                recommendations = get_ai_recommendations(score, factors)
                st.markdown("### 💡 Personalized Recommendations")
                st.markdown(recommendations)
        
        st.markdown("---")
        st.subheader("📚 General Credit Tips")
        
        tips_col1, tips_col2 = st.columns(2)
        
        with tips_col1:
            st.markdown("""
            **To Improve Your Score:**
            - 💳 Pay all bills on time
            - 📉 Keep credit utilization below 30%
            - 📅 Don't close old accounts
            - 🔍 Limit hard inquiries
            - 📊 Maintain a healthy credit mix
            """)
        
        with tips_col2:
            st.markdown("""
            **Things to Avoid:**
            - ❌ Missing payments
            - ❌ Maxing out credit cards
            - ❌ Opening too many accounts at once
            - ❌ Closing your oldest accounts
            - ❌ Ignoring errors on credit reports
            """)
        
        st.markdown("---")
        st.subheader("🎯 Score Milestones")
        
        milestones_data = [
            (700, "Good Credit", "Qualify for most credit cards and loans"),
            (750, "Very Good Credit", "Access to better interest rates"),
            (800, "Exceptional Credit", "Best rates and premium cards"),
            (850, "Perfect Score", "Maximum possible score!")
        ]
        
        for milestone, label, benefit in milestones_data:
            if score >= milestone:
                st.success(f"✅ {milestone}+ ({label}): {benefit}")
            else:
                points_needed = milestone - score
                st.warning(f"🎯 {milestone} ({label}): Need {points_needed} more points - {benefit}")
    else:
        st.info("Add a credit score first to get AI-powered insights and recommendations.")

# Footer
st.markdown("---")
st.caption("💡 Tip: Update your credit score monthly to track progress accurately. Most bureaus update scores once a month.")