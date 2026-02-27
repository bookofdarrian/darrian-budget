import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, load_investment_context, save_investment_context, get_setting, set_setting
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.aura_client import compress_for_claude, get_status as aura_status

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
_env_key = os.environ.get("ANTHROPIC_API_KEY", "")

st.set_page_config(page_title="AI Insights — Peach State Savings", page_icon="🍑", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("AI Insights (Claude AI analysis)")
inject_css()

# ── Load API key: env var → DB fallback → session state ──────────────────────
if "api_key" not in st.session_state:
    if _env_key:
        st.session_state["api_key"] = _env_key
    else:
        # Try loading from database (persisted from a previous manual entry)
        _db_key = get_setting("anthropic_api_key", "")
        if _db_key:
            st.session_state["api_key"] = _db_key

# ── Load saved investment context from DB into session state (once per session) ──
if "inv_loaded_from_db" not in st.session_state:
    _saved = load_investment_context()
    st.session_state["inv_401k"]               = float(_saved.get("bal_401k", 0) or 0)
    st.session_state["inv_401k_contrib_ytd"]   = float(_saved.get("contrib_401k_ytd", 0) or 0)
    st.session_state["inv_401k_employer_match"] = float(_saved.get("match_401k_ytd", 0) or 0)
    st.session_state["inv_roth"]               = float(_saved.get("bal_roth", 0) or 0)
    st.session_state["inv_roth_contrib_ytd"]   = float(_saved.get("contrib_roth_ytd", 0) or 0)
    st.session_state["inv_hsa"]                = float(_saved.get("bal_hsa", 0) or 0)
    st.session_state["inv_hsa_contrib_ytd"]    = float(_saved.get("contrib_hsa_ytd", 0) or 0)
    st.session_state["inv_brokerage"]          = float(_saved.get("bal_brokerage", 0) or 0)
    st.session_state["inv_notes"]              = _saved.get("notes", "") or ""
    st.session_state["inv_loaded_from_db"]     = True

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
st.sidebar.page_link("pages/18_real_estate_bot.py", label="🏠 Real Estate Bot", icon="🏠")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth",         icon="💎")

st.title("🤖 AI Insights")
st.caption("Claude analyzes your spending, flags patterns, and gives personalized budget recommendations.")

# ── Investment Accounts Context Panel ─────────────────────────────────────────
with st.expander("📈 Investment Accounts Context (Fidelity 401k, Roth IRA, HSA, etc.)", expanded=False):
    st.markdown(
        "**Claude can't automatically connect to Fidelity** — their API is enterprise-only and "
        "Plaid's Fidelity investment integration requires a business account. "
        "Enter your balances manually below and Claude will include them in every analysis."
    )
    st.caption("ℹ️ Values are saved to the database and will persist across page refreshes and app restarts.")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("##### 🏦 Fidelity Accounts")
        # Use session_state keys directly so values persist across reruns without
        # the value= / key= mismatch that causes fields to reset to 0 after Save.
        st.number_input(
            "401(k) Balance ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_401k",
            help="Your current Fidelity 401(k) total balance"
        )
        st.number_input(
            "401(k) YTD Contributions ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_401k_contrib_ytd",
            help="How much you've contributed to your 401(k) this year"
        )
        st.number_input(
            "401(k) Employer Match YTD ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_401k_employer_match",
            help="Employer contributions received this year"
        )
        st.number_input(
            "Roth IRA Balance ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_roth",
            help="Your current Fidelity Roth IRA total balance"
        )
        st.number_input(
            "Roth IRA YTD Contributions ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_roth_contrib_ytd",
            help="How much you've contributed to your Roth IRA this year (2025 limit: $7,000)"
        )

    with col_right:
        st.markdown("##### 🏥 HSA & Other")
        st.number_input(
            "HSA Balance ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_hsa",
            help="Your current HSA total balance"
        )
        st.number_input(
            "HSA YTD Contributions ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_hsa_contrib_ytd",
            help="How much you've contributed to your HSA this year (2025 individual limit: $4,300)"
        )
        st.number_input(
            "Cash Management / High Yield Balance ($)",
            min_value=0.0, step=100.0, format="%.2f",
            key="inv_brokerage",
            help="Fidelity Cash Management Individual or other high-yield / spend-save accounts"
        )
        st.text_area(
            "Additional Investment Notes",
            key="inv_notes",
            placeholder="e.g. 'Employer matches 4% of salary', 'Invested in target-date 2055 fund', 'HSA invested in index funds'",
            height=120,
            help="Any extra context about your investments you want Claude to know"
        )

    if st.button("💾 Save Investment Context", type="primary", key="btn_save_investments"):
        # Values are already in session_state via the widget keys above
        save_investment_context({
            "bal_401k":         st.session_state.get("inv_401k", 0),
            "contrib_401k_ytd": st.session_state.get("inv_401k_contrib_ytd", 0),
            "match_401k_ytd":   st.session_state.get("inv_401k_employer_match", 0),
            "bal_roth":         st.session_state.get("inv_roth", 0),
            "contrib_roth_ytd": st.session_state.get("inv_roth_contrib_ytd", 0),
            "bal_hsa":          st.session_state.get("inv_hsa", 0),
            "contrib_hsa_ytd":  st.session_state.get("inv_hsa_contrib_ytd", 0),
            "bal_brokerage":    st.session_state.get("inv_brokerage", 0),
            "notes":            st.session_state.get("inv_notes", ""),
        })
        st.success("✅ Investment context saved to database! Claude will now include this in all analyses.")
        st.rerun()

    # Show current saved state summary
    _any_inv = any([
        st.session_state.get("inv_401k", 0),
        st.session_state.get("inv_roth", 0),
        st.session_state.get("inv_hsa", 0),
        st.session_state.get("inv_brokerage", 0),
    ])
    if _any_inv:
        total_inv = (
            st.session_state.get("inv_401k", 0) +
            st.session_state.get("inv_roth", 0) +
            st.session_state.get("inv_hsa", 0) +
            st.session_state.get("inv_brokerage", 0)
        )
        st.info(f"✅ **Investment context active** — Total tracked: **${total_inv:,.2f}** across all accounts. Claude will use this data.")
    else:
        st.warning("⚠️ No investment data entered yet. Fill in your balances above and click Save.")

st.markdown("---")
_key_loaded = bool(st.session_state.get("api_key"))
with st.expander("🔑 API Key Settings", expanded=not _key_loaded):
    if _key_loaded:
        st.success("✅ API key loaded — you're all set.")
    st.markdown("Paste your Anthropic key below to save it permanently to the database:")
    api_key_input = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-api03-...",
                                   value=st.session_state.get("api_key", ""))
    if st.button("💾 Save Key to Database", type="primary"):
        if api_key_input.startswith("sk-ant-"):
            st.session_state["api_key"] = api_key_input
            set_setting("anthropic_api_key", api_key_input)
            st.success("✅ API key saved to database! It will auto-load on every future visit.")
            st.rerun()
        else:
            st.error("That doesn't look like a valid Anthropic key.")

api_key = st.session_state.get("api_key", "")
if not api_key:
    st.info("👆 Enter your Anthropic API key above to unlock AI features.")
    st.stop()

conn = get_conn()
expense_df   = read_sql("SELECT * FROM expenses WHERE month = ?", conn, params=(selected_month,))
income_df    = read_sql("SELECT * FROM income WHERE month = ?", conn, params=(selected_month,))
txn_df       = read_sql("SELECT * FROM bank_transactions WHERE month = ?", conn, params=(selected_month,))
all_expenses = read_sql("SELECT * FROM expenses ORDER BY month", conn)
conn.close()

total_income    = income_df['amount'].sum()
total_projected = expense_df['projected'].sum()
total_actual    = expense_df['actual'].sum()
savings         = total_income - total_actual


def build_investment_context() -> str:
    """Build investment account context from session state."""
    inv_401k               = st.session_state.get("inv_401k", 0)
    inv_401k_contrib_ytd   = st.session_state.get("inv_401k_contrib_ytd", 0)
    inv_401k_employer_match = st.session_state.get("inv_401k_employer_match", 0)
    inv_roth               = st.session_state.get("inv_roth", 0)
    inv_roth_contrib_ytd   = st.session_state.get("inv_roth_contrib_ytd", 0)
    inv_hsa                = st.session_state.get("inv_hsa", 0)
    inv_hsa_contrib_ytd    = st.session_state.get("inv_hsa_contrib_ytd", 0)
    inv_brokerage          = st.session_state.get("inv_brokerage", 0)
    inv_notes              = st.session_state.get("inv_notes", "")

    any_data = any([inv_401k, inv_roth, inv_hsa, inv_brokerage])
    if not any_data:
        return ""

    total_inv = inv_401k + inv_roth + inv_hsa + inv_brokerage
    lines = [
        "",
        "Investment & Retirement Accounts (Fidelity / external — not in transaction data):",
        f"  Total Investment Portfolio Value: ${total_inv:,.2f}",
    ]
    if inv_401k > 0:
        lines.append(f"  401(k) Balance: ${inv_401k:,.2f}")
        if inv_401k_contrib_ytd > 0:
            lines.append(f"    → YTD Employee Contributions: ${inv_401k_contrib_ytd:,.2f} (2025 limit: $23,500)")
        if inv_401k_employer_match > 0:
            lines.append(f"    → YTD Employer Match Received: ${inv_401k_employer_match:,.2f}")
    if inv_roth > 0:
        lines.append(f"  Roth IRA Balance: ${inv_roth:,.2f}")
        if inv_roth_contrib_ytd > 0:
            remaining_roth = max(0, 7000 - inv_roth_contrib_ytd)
            lines.append(f"    → YTD Contributions: ${inv_roth_contrib_ytd:,.2f} (2025 limit: $7,000 — ${remaining_roth:,.2f} remaining)")
    if inv_hsa > 0:
        lines.append(f"  HSA Balance: ${inv_hsa:,.2f}")
        if inv_hsa_contrib_ytd > 0:
            remaining_hsa = max(0, 4300 - inv_hsa_contrib_ytd)
            lines.append(f"    → YTD Contributions: ${inv_hsa_contrib_ytd:,.2f} (2025 individual limit: $4,300 — ${remaining_hsa:,.2f} remaining)")
    if inv_brokerage > 0:
        lines.append(f"  Cash Management / High Yield Account: ${inv_brokerage:,.2f}")
    if inv_notes.strip():
        lines.append(f"  Additional context: {inv_notes.strip()}")
    return "\n".join(lines)


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
        lines.append(f"  {row['category']} | {row['subcategory']} | ${row['projected']:,.2f} | ${row['actual']:,.2f} | {'OVER' if diff > 0 else 'under'} by ${abs(diff):,.2f}")
    if not txn_df.empty:
        lines += ["", "Individual transactions this month (description | amount):"]
        for _, row in txn_df.iterrows():
            lines.append(f"  {row['description']} | ${row['amount']:,.2f}")
    if len(all_expenses['month'].unique()) > 1:
        lines += ["", "Multi-month spending trends (actual totals by category):"]
        trend = all_expenses.groupby(['month', 'category'])['actual'].sum().reset_index()
        for cat in trend['category'].unique():
            cat_data = trend[trend['category'] == cat].sort_values('month')
            vals = ", ".join(f"{r['month']}: ${r['actual']:,.2f}" for _, r in cat_data.iterrows())
            lines.append(f"  {cat}: {vals}")

    # Append investment account context if available
    inv_context = build_investment_context()
    if inv_context:
        lines.append(inv_context)

    return "\n".join(lines)


# claude-opus-4-5 pricing (per million tokens)
INPUT_COST_PER_M  = 3.00   # $3.00 per 1M input tokens
OUTPUT_COST_PER_M = 15.00  # $15.00 per 1M output tokens

def ask_claude(prompt: str, context: str) -> tuple[str, dict]:
    """
    Compress context via AURA (if available) then send to Claude.
    Returns (response_text, usage_info).
    usage_info includes AURA savings data when compression was used.
    """
    client = anthropic.Anthropic(api_key=api_key)

    # ── AURA compression ──────────────────────────────────────────────────────
    # Only compress non-empty context (categorize tab passes "" intentionally)
    aura_result = None
    if context.strip():
        aura_result = compress_for_claude(context, mode="auto")
        effective_context = aura_result.compressed
    else:
        effective_context = context

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": (
                "You are a friendly, practical personal finance advisor. "
                f"You have access to the following budget data:\n\n{effective_context}\n\n{prompt}\n\n"
                "IMPORTANT FORMATTING RULES: "
                "1. Write dollar amounts as 'USD X.XX' or 'X dollars' — never use the dollar sign symbol. "
                "2. Do NOT use any markdown formatting — no asterisks for bold, no underscores for italic, no pound signs for headers. "
                "3. Use plain dashes (-) for bullet points. "
                "4. Be specific with numbers, concise, and actionable. Don't be preachy."
            )}]
        )
        usage = message.usage
        input_tokens  = usage.input_tokens
        output_tokens = usage.output_tokens
        cost = (input_tokens / 1_000_000 * INPUT_COST_PER_M) + (output_tokens / 1_000_000 * OUTPUT_COST_PER_M)
        usage_info = {
            "input_tokens":  input_tokens,
            "output_tokens": output_tokens,
            "total_tokens":  input_tokens + output_tokens,
            "cost_usd":      cost,
        }
        # Attach AURA stats if compression ran
        if aura_result and not aura_result.fallback_used:
            usage_info["aura_original_tokens"]  = aura_result.original_tokens
            usage_info["aura_compressed_tokens"] = aura_result.compressed_tokens
            usage_info["aura_savings_pct"]       = aura_result.savings_pct
            usage_info["aura_mode"]              = aura_result.mode_used
            usage_info["aura_ms"]                = aura_result.processing_time_ms
        return message.content[0].text, usage_info
    except anthropic.AuthenticationError:
        return "❌ Invalid API key. Please check your key in the settings above.", {}
    except anthropic.RateLimitError:
        return "❌ Rate limit hit. Wait a moment and try again.", {}
    except Exception as e:
        return f"❌ Error: {e}", {}


def render_response(text: str):
    """Render Claude's response as clean plain text — no markdown, no LaTeX."""
    # Replace any stray dollar signs with fullwidth equivalent just in case
    cleaned = text.replace("$", "＄")
    # Use st.text() for completely plain rendering — no markdown interpretation at all
    st.text(cleaned)


def show_usage(usage_info: dict):
    """Render a small token/cost badge below a response, including AURA savings."""
    if not usage_info:
        return
    aura_savings = usage_info.get("aura_savings_pct", 0)
    label = f"📊 Token usage — ${usage_info['cost_usd']:.4f} this prompt"
    if aura_savings:
        label += f"  ·  ⚡ AURA saved {aura_savings:.0f}%"
    with st.expander(label, expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("Input tokens",  f"{usage_info['input_tokens']:,}")
        c2.metric("Output tokens", f"{usage_info['output_tokens']:,}")
        c3.metric("Cost",          f"${usage_info['cost_usd']:.4f}")
        st.caption("Pricing: claude-opus-4-5 — $3/M input · $15/M output")
        if aura_savings:
            st.markdown("---")
            a1, a2, a3 = st.columns(3)
            a1.metric("Original tokens",    f"{usage_info.get('aura_original_tokens', 0):,}")
            a2.metric("After compression",  f"{usage_info.get('aura_compressed_tokens', 0):,}")
            a3.metric("AURA savings",       f"{aura_savings:.1f}%")
            st.caption(
                f"AURA mode: {usage_info.get('aura_mode', '—')}  ·  "
                f"Compression time: {usage_info.get('aura_ms', 0):.0f}ms"
            )


# ── AURA status banner ────────────────────────────────────────────────────────
_aura = aura_status()
if _aura["available"]:
    st.sidebar.success("⚡ AURA: Active")
else:
    st.sidebar.info("⚡ AURA: Offline (no savings)")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Monthly Summary", "💡 Budget Tips", "🏷️ Auto-Categorize", "💬 Ask Anything"])
context = build_budget_context(selected_month)
month_label = datetime.strptime(selected_month, "%Y-%m").strftime("%B %Y")

with tab1:
    st.subheader(f"📊 AI Summary — {month_label}")
    st.caption("Claude reads your full budget and writes a plain-English summary of how your month went.")
    if st.button("Generate Monthly Summary", type="primary", key="btn_summary"):
        with st.spinner("Claude is analyzing your budget..."):
            response, usage = ask_claude(
                f"Write a concise monthly budget summary for {month_label}. Cover: how income compared to spending, "
                "which categories were over/under budget, biggest individual transactions, and one or two things that stand out. "
                "Keep it under 200 words, conversational tone.", context)
        render_response(response)
        show_usage(usage)

with tab2:
    st.subheader("💡 Personalized Budget Recommendations")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 Suggest Budget Adjustments", type="primary", key="btn_adjust"):
            with st.spinner("Analyzing spending patterns..."):
                response, usage = ask_claude("Look at my projected vs actual spending. Which projected amounts are consistently wrong? "
                    "Give me 3-5 specific recommendations to adjust my projected budget amounts. Be specific with dollar amounts.", context)
            render_response(response)
            show_usage(usage)
    with col2:
        if st.button("✂️ Where Can I Cut Back?", type="secondary", key="btn_cut"):
            with st.spinner("Finding savings opportunities..."):
                response, usage = ask_claude("Identify 3-5 specific areas where I could realistically cut back without drastically changing my lifestyle. "
                    "For each one, suggest a specific dollar amount I could save and how.", context)
            render_response(response)
            show_usage(usage)
    st.markdown("---")
    if st.button("📈 Savings Goal Analysis", key="btn_savings"):
        savings_goal = st.session_state.get("savings_goal", 10000)
        with st.spinner("Running savings projection..."):
            response, usage = ask_claude(f"Project my savings over the next 6 months. If I have a savings goal of ${savings_goal:,}, "
                "when will I reach it? What would I need to change to reach it 2 months sooner?", context)
        render_response(response)
        show_usage(usage)
    savings_goal_input = st.number_input("Set your savings goal ($)", min_value=0, value=st.session_state.get("savings_goal", 10000), step=500)
    if savings_goal_input != st.session_state.get("savings_goal"):
        st.session_state["savings_goal"] = savings_goal_input

with tab3:
    st.subheader("🏷️ Auto-Categorize Bank Transactions")
    conn = get_conn()
    uncategorized = read_sql("SELECT * FROM bank_transactions WHERE month=? AND (category IS NULL OR category='')", conn, params=(selected_month,))
    expense_cats  = read_sql("SELECT DISTINCT category, subcategory FROM expenses WHERE month=?", conn, params=(selected_month,))
    conn.close()
    if uncategorized.empty:
        st.success("✅ All transactions for this month are already categorized!")
    else:
        st.info(f"Found **{len(uncategorized)} uncategorized** transactions.")
        st.dataframe(uncategorized[['date', 'description', 'amount']].rename(
            columns={'date': 'Date', 'description': 'Description', 'amount': 'Amount ($)'}),
            use_container_width=True, hide_index=True)
        if st.button("🤖 Auto-Categorize All", type="primary", key="btn_autocat"):
            cat_list = "\n".join(f"  - {r['category']} › {r['subcategory']}" for _, r in expense_cats.iterrows())
            txn_list = "\n".join(f"  ID {r['id']}: {r['description']} (${r['amount']:.2f})" for _, r in uncategorized.iterrows())
            prompt = (f"I have these budget categories:\n{cat_list}\n\nAnd these uncategorized transactions:\n{txn_list}\n\n"
                      "For each transaction ID, suggest the best matching category in the format:\n"
                      "ID <number>: <Category> › <Subcategory>\nIf none fit, write: ID <number>: Uncategorized\nOnly output the ID lines.")
            with st.spinner("Claude is categorizing your transactions..."):
                raw_response, usage = ask_claude(prompt, "")
            st.markdown("**Claude's suggestions:**")
            show_usage(usage)
            st.code(raw_response)
            suggestions = {}
            for line in raw_response.strip().split('\n'):
                m = __import__('re').match(r'ID\s+(\d+):\s+(.+?)\s*›\s*(.+)', line.strip())
                if m:
                    suggestions[int(m.group(1))] = (m.group(2).strip(), m.group(3).strip())
            if suggestions:
                if st.button(f"✅ Apply {len(suggestions)} suggestions", type="primary", key="btn_apply_cats"):
                    conn = get_conn()
                    from utils.db import execute as db_execute
                    for txn_id, (cat, sub) in suggestions.items():
                        db_execute(conn, "UPDATE bank_transactions SET category=?, subcategory=? WHERE id=?", (cat, sub, txn_id))
                    conn.commit()
                    conn.close()
                    st.success(f"Applied {len(suggestions)} categories!")
                    st.rerun()

with tab4:
    st.subheader("💬 Ask Claude About Your Budget")
    st.markdown("**Quick questions:**")
    quick_q = None
    if st.button("🍔 How much did I spend on food?", use_container_width=True):
        quick_q = "How much did I spend on food and dining this month? Break it down by subcategory."
    if st.button("💸 What's my biggest expense?", use_container_width=True):
        quick_q = "What was my single biggest expense category this month and how does it compare to my budget?"
    if st.button("🏦 Am I on track to save?", use_container_width=True):
        quick_q = "Based on my income and spending, am I on track to save money this month? What's my savings rate?"
    if st.button("📈 How are my investments doing?", use_container_width=True):
        quick_q = "Based on my investment account balances (401k, Roth IRA, HSA, Cash Management) and my monthly savings rate, give me a snapshot of my overall financial health."
    st.markdown("---")
    user_question = st.text_area("Or ask your own question:", value=quick_q or "",
        placeholder="e.g. 'How much did I spend at Chevron?' or 'What would happen if I cut dining out by $100?'", height=80)
    if st.button("Ask Claude", type="primary", key="btn_ask") and user_question:
        with st.spinner("Thinking..."):
            response, usage = ask_claude(user_question, context)
        st.markdown("### Claude's Answer")
        render_response(response)
        show_usage(usage)
