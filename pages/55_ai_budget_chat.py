import streamlit as st
import json
from datetime import datetime, timedelta
from decimal import Decimal
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="AI Budget Chat | Peach State Savings", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_history_user_session 
            ON chat_history(user_id, session_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_history_created 
            ON chat_history(created_at)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_session_id():
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return st.session_state.chat_session_id

def save_message(user_id: int, session_id: str, role: str, content: str):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO chat_history (user_id, session_id, role, content, created_at)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, session_id, role, content, datetime.now()))
    conn.commit()
    conn.close()

def load_conversation(user_id: int, session_id: str, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT role, content, created_at FROM chat_history
        WHERE user_id = {ph} AND session_id = {ph}
        ORDER BY created_at DESC
        LIMIT {ph}
    """, (user_id, session_id, limit))
    rows = cur.fetchall()
    conn.close()
    messages = [{"role": r[0], "content": r[1], "created_at": r[2]} for r in reversed(rows)]
    return messages

def get_all_sessions(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT DISTINCT session_id, MIN(created_at) as started
        FROM chat_history
        WHERE user_id = {ph}
        GROUP BY session_id
        ORDER BY started DESC
        LIMIT 20
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]

def delete_session(user_id: int, session_id: str):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        DELETE FROM chat_history WHERE user_id = {ph} AND session_id = {ph}
    """, (user_id, session_id))
    conn.commit()
    conn.close()

def get_financial_context(user_id: int) -> dict:
    context = {
        "recent_expenses": [],
        "recent_income": [],
        "budgets": [],
        "goals": [],
        "net_worth": None,
        "monthly_summary": {}
    }
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    try:
        cur.execute(f"""
            SELECT category, amount, description, expense_date 
            FROM expenses 
            WHERE user_id = {ph} 
            ORDER BY expense_date DESC 
            LIMIT 30
        """, (user_id,))
        rows = cur.fetchall()
        context["recent_expenses"] = [
            {"category": r[0], "amount": float(r[1]) if r[1] else 0, "description": r[2], "date": str(r[3])}
            for r in rows
        ]
    except:
        pass
    
    try:
        cur.execute(f"""
            SELECT source, amount, income_date 
            FROM income 
            WHERE user_id = {ph} 
            ORDER BY income_date DESC 
            LIMIT 20
        """, (user_id,))
        rows = cur.fetchall()
        context["recent_income"] = [
            {"source": r[0], "amount": float(r[1]) if r[1] else 0, "date": str(r[2])}
            for r in rows
        ]
    except:
        pass
    
    try:
        cur.execute(f"""
            SELECT name, target_amount, current_amount, deadline 
            FROM goals 
            WHERE user_id = {ph}
        """, (user_id,))
        rows = cur.fetchall()
        context["goals"] = [
            {"name": r[0], "target": float(r[1]) if r[1] else 0, "current": float(r[2]) if r[2] else 0, "deadline": str(r[3]) if r[3] else None}
            for r in rows
        ]
    except:
        pass
    
    try:
        cur.execute(f"""
            SELECT category, budget_amount 
            FROM budgets 
            WHERE user_id = {ph}
        """, (user_id,))
        rows = cur.fetchall()
        context["budgets"] = [
            {"category": r[0], "amount": float(r[1]) if r[1] else 0}
            for r in rows
        ]
    except:
        pass
    
    if context["recent_expenses"]:
        total_expenses = sum(e["amount"] for e in context["recent_expenses"])
        categories = {}
        for e in context["recent_expenses"]:
            cat = e["category"] or "Uncategorized"
            categories[cat] = categories.get(cat, 0) + e["amount"]
        context["monthly_summary"]["total_expenses"] = total_expenses
        context["monthly_summary"]["by_category"] = categories
    
    if context["recent_income"]:
        total_income = sum(i["amount"] for i in context["recent_income"])
        context["monthly_summary"]["total_income"] = total_income
    
    conn.close()
    return context

def build_system_prompt(financial_context: dict) -> str:
    context_summary = json.dumps(financial_context, indent=2, default=str)
    
    system_prompt = f"""You are a helpful AI financial assistant for Peach State Savings, a personal budget management application.

Your role is to:
1. Answer questions about the user's finances based on their actual data
2. Provide personalized budgeting advice and spending insights
3. Help users understand their spending patterns and suggest improvements
4. Offer encouragement and practical tips for reaching financial goals
5. Explain financial concepts in simple, friendly terms

USER'S CURRENT FINANCIAL DATA:
{context_summary}

GUIDELINES:
- Be conversational, friendly, and encouraging
- Reference specific numbers from their data when relevant
- If asked about data you don't have, explain what's missing
- Provide actionable advice, not just observations
- Use emojis sparingly to keep things friendly 🍑
- Format currency as $X,XXX.XX
- When discussing spending, always consider context (necessities vs discretionary)
- Suggest specific, achievable improvements
- If the user seems stressed about finances, be supportive and focus on progress

IMPORTANT:
- Never make up data that isn't provided
- If financial data is empty, acknowledge it and offer to help them get started
- Keep responses concise but helpful (aim for 2-4 paragraphs unless detail is needed)
- Always be honest if you're uncertain about something
"""
    return system_prompt

def call_claude_api(messages: list, financial_context: dict) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Anthropic API key not configured. Please add your API key in Settings to use the AI chat assistant."
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        system_prompt = build_system_prompt(financial_context)
        
        api_messages = []
        for msg in messages[-10:]:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=api_messages
        )
        
        return response.content[0].text
    
    except anthropic.AuthenticationError:
        return "⚠️ Invalid API key. Please check your Anthropic API key in Settings."
    except anthropic.RateLimitError:
        return "⚠️ Rate limit exceeded. Please wait a moment and try again."
    except Exception as e:
        return f"⚠️ Error communicating with AI: {str(e)}"

def format_quick_query(query_type: str, financial_context: dict) -> str:
    if query_type == "spending_summary":
        return "Give me a summary of my recent spending. What are my top expense categories and how much have I spent in total?"
    elif query_type == "budget_status":
        return "How am I doing against my budgets? Am I on track or overspending in any categories?"
    elif query_type == "savings_tips":
        return "Based on my spending patterns, what are some specific ways I could save more money?"
    elif query_type == "goal_progress":
        return "How am I progressing toward my financial goals? What should I focus on?"
    elif query_type == "weekly_review":
        return "Give me a weekly financial review. Summarize my spending and income from the past 7 days."
    elif query_type == "expense_analysis":
        return "Analyze my expenses and identify any unusual spending or areas where I might be overspending."
    return query_type

st.title("🍑 AI Budget Chat Assistant")
st.markdown("Ask me anything about your finances, spending habits, or budgeting goals!")

user_id = get_user_id()
session_id = get_session_id()

with st.sidebar:
    st.markdown("---")
    st.subheader("💬 Chat Sessions")
    
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.chat_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if "messages" in st.session_state:
            del st.session_state.messages
        st.rerun()
    
    sessions = get_all_sessions(user_id)
    if sessions:
        st.markdown("**Previous Chats:**")
        for sess_id, started in sessions:
            col1, col2 = st.columns([3, 1])
            with col1:
                label = started.strftime("%b %d, %H:%M") if hasattr(started, 'strftime') else str(started)[:16]
                if st.button(f"📄 {label}", key=f"sess_{sess_id}", use_container_width=True):
                    st.session_state.chat_session_id = sess_id
                    if "messages" in st.session_state:
                        del st.session_state.messages
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{sess_id}"):
                    delete_session(user_id, sess_id)
                    if st.session_state.get("chat_session_id") == sess_id:
                        st.session_state.chat_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                        if "messages" in st.session_state:
                            del st.session_state.messages
                    st.rerun()

if "messages" not in st.session_state:
    loaded = load_conversation(user_id, session_id)
    if loaded:
        st.session_state.messages = [{"role": m["role"], "content": m["content"]} for m in loaded]
    else:
        st.session_state.messages = []

if not st.session_state.messages:
    st.markdown("""
    ### 👋 Welcome to your AI Budget Assistant!
    
    I can help you with:
    - 📊 **Spending summaries** and analysis
    - 💰 **Budget tracking** and recommendations  
    - 🎯 **Goal progress** and planning
    - 💡 **Personalized savings tips**
    
    Use the quick actions below or type your own question!
    """)

st.markdown("### ⚡ Quick Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Spending Summary", use_container_width=True):
        query = format_quick_query("spending_summary", {})
        st.session_state.pending_query = query
        st.rerun()
    
    if st.button("🎯 Goal Progress", use_container_width=True):
        query = format_quick_query("goal_progress", {})
        st.session_state.pending_query = query
        st.rerun()

with col2:
    if st.button("💰 Budget Status", use_container_width=True):
        query = format_quick_query("budget_status", {})
        st.session_state.pending_query = query
        st.rerun()
    
    if st.button("📅 Weekly Review", use_container_width=True):
        query = format_quick_query("weekly_review", {})
        st.session_state.pending_query = query
        st.rerun()

with col3:
    if st.button("💡 Savings Tips", use_container_width=True):
        query = format_quick_query("savings_tips", {})
        st.session_state.pending_query = query
        st.rerun()
    
    if st.button("🔍 Expense Analysis", use_container_width=True):
        query = format_quick_query("expense_analysis", {})
        st.session_state.pending_query = query
        st.rerun()

st.markdown("---")

chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if st.session_state.get("pending_query"):
    user_input = st.session_state.pending_query
    del st.session_state.pending_query
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message(user_id, session_id, "user", user_input)
    
    with st.chat_message("user"):
        st.markdown(user_input)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            financial_context = get_financial_context(user_id)
            response = call_claude_api(st.session_state.messages, financial_context)
        st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    save_message(user_id, session_id, "assistant", response)
    st.rerun()

if prompt := st.chat_input("Ask me about your finances..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(user_id, session_id, "user", prompt)
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            financial_context = get_financial_context(user_id)
            response = call_claude_api(st.session_state.messages, financial_context)
        st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    save_message(user_id, session_id, "assistant", response)
    st.rerun()

with st.expander("ℹ️ Tips for better conversations"):
    st.markdown("""
    **Get the most out of your AI assistant:**
    
    - **Be specific**: Instead of "how am I doing?", try "how much did I spend on food this month?"
    - **Ask follow-ups**: Continue the conversation to dive deeper into topics
    - **Request comparisons**: "Compare my spending this month vs last month"
    - **Get actionable advice**: "What's one thing I can do this week to save $50?"
    - **Set context**: "I'm trying to save for a house down payment - what should I prioritize?"
    
    **Example questions:**
    - "What's my biggest expense category?"
    - "Am I on track to meet my savings goal?"
    - "Where can I cut back without major lifestyle changes?"
    - "Should I be worried about my current spending level?"
    """)

st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.session_state.messages:
        if st.button("🗑️ Clear This Conversation", use_container_width=True):
            delete_session(user_id, session_id)
            st.session_state.chat_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.rerun()