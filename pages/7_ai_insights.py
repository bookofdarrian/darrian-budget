import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime
from utils.db import get_conn, init_db

# Auto-load API key from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
_env_key = os.environ.get("ANTHROPIC_API_KEY", "")

st.set_page_config(page_title="AI Insights", page_icon="🤖", layout="wide")
init_db()

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("💰 Budget Dashboard")
st.sidebar.markdown("---")
months = []
for m in range(1, 13):
    months.append(datetime(2025, m, 1).strftime("%Y-%m"))
for m in range(1, 13):
    months.append(datetime(2026, m, 1).strftime("%Y-%m"))
current_month = datetime.now().strftime("%Y-%m")
default_idx = months.index(current_month) if current_month in months else 0
selected_month = st.sidebar.selectbox("📅 Month", months, index=default_idx)

st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")

st.title("🤖 AI Insights")
st.caption("Claude analyzes your spending, flags patterns, and gives personalized budget recommendations.")

# ── API Key setup ─────────────────────────────────────────────────────────────
st.markdown("---")
# Auto-populate from .env key if session doesn't have one yet
if "api_key" not in st.session_state and _env_key:
    st.session_state["api_key"] = _env_key

with st.expander("🔑 API Key Settings", expanded="api_key" not in st.session_state):
    if st.session_state.get("api_key"):
        st.success("✅ API key loaded automatically from your .env file.")
    st.markdown("To update your key, paste a new one below:")
    api_key_input = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-api03-...",
        value=st.session_state.get("api_key", "")
    )
    if st.button("Save Key", type="primary"):
        if api_key_input.startswith("sk-ant-"):
            st.session_state["api_key"] = api_key_input
            st.success("API key saved!")
            st.rerun()
        else:
            st.error("That doesn't look like a valid Anthropic key. It should start with 'sk-ant-'")

api_key = st.session_state.get("api_key", "")

if not api_key:
    st.info("👆 Enter your Anthropic API key above to unlock AI features.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
conn = get_conn()
expense_df  = pd.read_sql("SELECT * FROM expenses  WHERE month = ?", conn, params=(selected_month,))
income_df   = pd.read_sql("SELECT * FROM income    WHERE month = ?", conn, params=(selected_month,))
txn_df      = pd.read_sql("SELECT * FROM bank_transactions WHERE month = ?", conn, params=(selected_month,))
all_expenses = pd.read_sql("SELECT * FROM expenses ORDER BY month", conn)
conn.close()

total_income    = income_df['amount'].sum()
total_projected = expense_df['projected'].sum()
total_actual    = expense_df['actual'].sum()
savings         = total_income - total_actual

# ── Build context string for Claude ──────────────────────────────────────────
def build_budget_context(month: str) -> str:
    month_label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")

    lines = [
        f"Budget data for {month_label}:",
        f"  Total Income: ${total_income:,.2f}",
        f"  Total Projected Expenses: ${total_projected:,.2f}",
        f"  Total Actual Expenses: ${total_actual:,.2f}",
        f"  Savings: ${savings:,.2f}",
        f"  Savings Rate: {(savings/total_income*100) if total_income else 0:.1f}%",
        "",
        "Expense breakdown (Category | Subcategory | Projected | Actual | Difference):",
    ]
    for _, row in expense_df.iterrows():
        diff = row['actual'] - row['projected']
        lines.append(
            f"  {row['category']} | {row['subcategory']} | "
            f"${row['projected']:,.2f} | ${row['actual']:,.2f} | "
            f"{'OVER' if diff > 0 else 'under'} by ${abs(diff):,.2f}"
        )

    if not txn_df.empty:
        lines += ["", "Individual transactions this month (description | amount):"]
        for _, row in txn_df.iterrows():
            lines.append(f"  {row['description']} | ${row['amount']:,.2f}")

    # Multi-month trend
    if len(all_expenses['month'].unique()) > 1:
        lines += ["", "Multi-month spending trends (actual totals by category):"]
        trend = all_expenses.groupby(['month', 'category'])['actual'].sum().reset_index()
        for cat in trend['category'].unique():
            cat_data = trend[trend['category'] == cat].sort_values('month')
            vals = ", ".join(f"{r['month']}: ${r['actual']:,.2f}" for _, r in cat_data.iterrows())
            lines.append(f"  {cat}: {vals}")

    return "\n".join(lines)


def ask_claude(prompt: str, context: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a friendly, practical personal finance advisor. "
                        "You have access to the following budget data:\n\n"
                        f"{context}\n\n"
                        f"{prompt}\n\n"
                        "Be specific, use the actual numbers from the data, and keep your response concise and actionable. "
                        "Use bullet points where helpful. Don't be preachy."
                    )
                }
            ]
        )
        return message.content[0].text
    except anthropic.AuthenticationError:
        return "❌ Invalid API key. Please check your key in the settings above."
    except anthropic.RateLimitError:
        return "❌ Rate limit hit. Wait a moment and try again."
    except Exception as e:
        return f"❌ Error: {e}"


# ── AI Feature Tabs ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Monthly Summary", "💡 Budget Tips", "🏷️ Auto-Categorize", "💬 Ask Anything"
])

context = build_budget_context(selected_month)
month_label = datetime.strptime(selected_month, "%Y-%m").strftime("%B %Y")

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Monthly Summary
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(f"📊 AI Summary — {month_label}")
    st.caption("Claude reads your full budget and writes a plain-English summary of how your month went.")

    if st.button("Generate Monthly Summary", type="primary", key="btn_summary"):
        with st.spinner("Claude is analyzing your budget..."):
            response = ask_claude(
                f"Write a concise monthly budget summary for {month_label}. "
                "Cover: how income compared to spending, which categories were over/under budget, "
                "biggest individual transactions, and one or two things that stand out. "
                "Keep it under 200 words, conversational tone.",
                context
            )
        st.markdown(response)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Budget Tips
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("💡 Personalized Budget Recommendations")
    st.caption("Based on your actual spending patterns, Claude suggests specific adjustments.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 Suggest Budget Adjustments", type="primary", key="btn_adjust"):
            with st.spinner("Analyzing spending patterns..."):
                response = ask_claude(
                    "Look at my projected vs actual spending. "
                    "Which projected amounts are consistently wrong (too high or too low)? "
                    "Give me 3-5 specific recommendations to adjust my projected budget amounts "
                    "to better match my real spending. Be specific with dollar amounts.",
                    context
                )
            st.markdown(response)

    with col2:
        if st.button("✂️ Where Can I Cut Back?", type="secondary", key="btn_cut"):
            with st.spinner("Finding savings opportunities..."):
                response = ask_claude(
                    "Looking at my spending, identify 3-5 specific areas where I could realistically "
                    "cut back without drastically changing my lifestyle. "
                    "For each one, suggest a specific dollar amount I could save and how. "
                    "Focus on the highest-impact changes first.",
                    context
                )
            st.markdown(response)

    st.markdown("---")
    if st.button("📈 Savings Goal Analysis", key="btn_savings"):
        savings_goal = st.session_state.get("savings_goal", 10000)
        with st.spinner("Running savings projection..."):
            response = ask_claude(
                f"Based on my current income and spending patterns, project my savings over the next 6 months. "
                f"If I have a savings goal of ${savings_goal:,}, when will I reach it at my current rate? "
                f"What would I need to change to reach it 2 months sooner?",
                context
            )
        st.markdown(response)

    savings_goal_input = st.number_input(
        "Set your savings goal ($)", min_value=0, value=st.session_state.get("savings_goal", 10000), step=500
    )
    if savings_goal_input != st.session_state.get("savings_goal"):
        st.session_state["savings_goal"] = savings_goal_input

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Auto-Categorize Transactions
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🏷️ Auto-Categorize Bank Transactions")
    st.caption("Claude reads your uncategorized transactions and suggests which budget line each one belongs to.")

    conn = get_conn()
    uncategorized = pd.read_sql(
        "SELECT * FROM bank_transactions WHERE month=? AND (category IS NULL OR category='')",
        conn, params=(selected_month,)
    )
    expense_cats = pd.read_sql(
        "SELECT DISTINCT category, subcategory FROM expenses WHERE month=?",
        conn, params=(selected_month,)
    )
    conn.close()

    if uncategorized.empty:
        st.success("✅ All transactions for this month are already categorized!")
    else:
        st.info(f"Found **{len(uncategorized)} uncategorized** transactions.")
        st.dataframe(
            uncategorized[['date', 'description', 'amount']].rename(columns={
                'date': 'Date', 'description': 'Description', 'amount': 'Amount ($)'
            }),
            use_container_width=True, hide_index=True
        )

        if st.button("🤖 Auto-Categorize All", type="primary", key="btn_autocat"):
            # Build category list for Claude
            cat_list = "\n".join(
                f"  - {r['category']} › {r['subcategory']}"
                for _, r in expense_cats.iterrows()
            )
            txn_list = "\n".join(
                f"  ID {r['id']}: {r['description']} (${r['amount']:.2f})"
                for _, r in uncategorized.iterrows()
            )

            prompt = (
                f"I have these budget categories:\n{cat_list}\n\n"
                f"And these uncategorized transactions:\n{txn_list}\n\n"
                "For each transaction ID, suggest the best matching category in the format:\n"
                "ID <number>: <Category> › <Subcategory>\n"
                "If none fit, write: ID <number>: Uncategorized\n"
                "Only output the ID lines, nothing else."
            )

            with st.spinner("Claude is categorizing your transactions..."):
                raw_response = ask_claude(prompt, "")

            st.markdown("**Claude's suggestions:**")
            st.code(raw_response)

            # Parse Claude's response and apply
            suggestions = {}
            for line in raw_response.strip().split('\n'):
                m = __import__('re').match(r'ID\s+(\d+):\s+(.+?)\s*›\s*(.+)', line.strip())
                if m:
                    txn_id = int(m.group(1))
                    cat    = m.group(2).strip()
                    sub    = m.group(3).strip()
                    suggestions[txn_id] = (cat, sub)

            if suggestions:
                if st.button(f"✅ Apply {len(suggestions)} suggestions", type="primary", key="btn_apply_cats"):
                    conn = get_conn()
                    for txn_id, (cat, sub) in suggestions.items():
                        conn.execute(
                            "UPDATE bank_transactions SET category=?, subcategory=? WHERE id=?",
                            (cat, sub, txn_id)
                        )
                    conn.commit()
                    conn.close()
                    st.success(f"Applied {len(suggestions)} categories! Go to Bank Import → Review & Apply to push them to your budget.")
                    st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — Ask Anything
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("💬 Ask Claude About Your Budget")
    st.caption("Ask anything about your finances — Claude has full context of your budget data.")

    # Quick question buttons
    st.markdown("**Quick questions:**")
    qcol1, qcol2, qcol3 = st.columns(3)
    quick_q = None
    with qcol1:
        if st.button("How much did I spend on food?"):
            quick_q = "How much did I spend on food and dining this month? Break it down by subcategory."
    with qcol2:
        if st.button("What's my biggest expense?"):
            quick_q = "What was my single biggest expense category this month and how does it compare to my budget?"
    with qcol3:
        if st.button("Am I on track to save?"):
            quick_q = "Based on my income and spending, am I on track to save money this month? What's my savings rate?"

    st.markdown("---")
    user_question = st.text_area(
        "Or ask your own question:",
        value=quick_q or "",
        placeholder="e.g. 'How much did I spend at Chevron this month?' or 'What would happen to my savings if I cut dining out by $100?'",
        height=80
    )

    if st.button("Ask Claude", type="primary", key="btn_ask") and user_question:
        with st.spinner("Thinking..."):
            response = ask_claude(user_question, context)
        st.markdown("### Claude's Answer")
        st.markdown(response)
