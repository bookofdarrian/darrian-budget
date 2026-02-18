import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime
from utils.db import get_conn, init_db, read_sql, get_setting
from utils.auth import require_password

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Monthly Trends", page_icon="📈", layout="wide")
init_db()
require_password()

# ── Load API key ──────────────────────────────────────────────────────────────
_env_key = os.environ.get("ANTHROPIC_API_KEY", "")
if "api_key" not in st.session_state:
    if _env_key:
        st.session_state["api_key"] = _env_key
    else:
        _db_key = get_setting("anthropic_api_key", "")
        if _db_key:
            st.session_state["api_key"] = _db_key

api_key = st.session_state.get("api_key", "")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("💰 Budget Dashboard")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="404 Sole Archive",  icon="👟")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",       icon="🤖")

st.title("📈 Monthly Trends")
st.caption("Track your income, spending, and savings across every month — powered by your Navy Federal data.")

# ── Pull all data ─────────────────────────────────────────────────────────────
conn = get_conn()
income_all  = read_sql("SELECT month, SUM(amount) AS income FROM income GROUP BY month", conn)
txn_all     = read_sql("SELECT month, SUM(amount) AS spent FROM bank_transactions GROUP BY month", conn)
txn_raw     = read_sql(
    "SELECT month, date, description, amount, category FROM bank_transactions ORDER BY date DESC", conn
)
txn_cat_all = read_sql(
    """SELECT month, category, SUM(amount) AS spent
       FROM bank_transactions
       WHERE category IS NOT NULL AND category != ''
       GROUP BY month, category""", conn
)
conn.close()

# ── Guard: no data ────────────────────────────────────────────────────────────
if txn_all.empty and income_all.empty:
    st.info("📭 No data yet — import your Navy Federal PDF on the **Bank Import** page first.")
    st.stop()

# ── Build unified month table ─────────────────────────────────────────────────
all_months = set()
if not income_all.empty:
    all_months.update(income_all["month"].tolist())
if not txn_all.empty:
    all_months.update(txn_all["month"].tolist())

trends = pd.DataFrame(sorted(all_months), columns=["month"])

if not income_all.empty:
    trends = pd.merge(trends, income_all, on="month", how="left")
else:
    trends["income"] = 0.0

if not txn_all.empty:
    trends = pd.merge(trends, txn_all, on="month", how="left")
else:
    trends["spent"] = 0.0

trends = trends.fillna(0)
trends["savings"]      = trends["income"] - trends["spent"]
trends["savings_rate"] = (trends["savings"] / trends["income"].replace(0, float("nan"))) * 100
trends["month_label"]  = trends["month"].apply(lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y"))
trends = trends.sort_values("month").reset_index(drop=True)

# ── All-Time KPIs ─────────────────────────────────────────────────────────────
st.subheader("📊 All-Time Summary")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Income",      f"${trends['income'].sum():,.2f}")
k2.metric("Total Spent",       f"${trends['spent'].sum():,.2f}")
k3.metric("Total Saved",       f"${trends['savings'].sum():,.2f}")
avg_sr = trends["savings_rate"].replace([float("inf"), float("-inf")], float("nan")).mean()
k4.metric("Avg Savings Rate",  f"{avg_sr:.1f}%" if not pd.isna(avg_sr) else "—")

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
st.subheader("💵 Income vs. Spending by Month")
chart_df = trends.set_index("month_label")[["income", "spent"]].copy()
chart_df.columns = ["Income", "Spent"]
st.bar_chart(chart_df, use_container_width=True)

st.markdown("---")
st.subheader("💰 Monthly Savings")
savings_chart = trends.set_index("month_label")[["savings"]].copy()
savings_chart.columns = ["Savings"]
st.line_chart(savings_chart, use_container_width=True)

st.markdown("---")
st.subheader("📉 Savings Rate % by Month")
sr_chart = trends.set_index("month_label")[["savings_rate"]].copy()
sr_chart.columns = ["Savings Rate (%)"]
st.line_chart(sr_chart, use_container_width=True)

# ── Category Breakdown ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏷️ Spending by Category")

if not txn_cat_all.empty:
    cat_pivot = txn_cat_all.pivot_table(
        index="month", columns="category", values="spent", aggfunc="sum"
    ).fillna(0)
    cat_pivot.index = cat_pivot.index.map(lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y"))
    st.bar_chart(cat_pivot, use_container_width=True)

    # Category totals across all time
    cat_totals = txn_cat_all.groupby("category")["spent"].sum().sort_values(ascending=False).reset_index()
    cat_totals.columns = ["Category", "Total Spent ($)"]
    cat_totals["Total Spent ($)"] = cat_totals["Total Spent ($)"].map("${:,.2f}".format)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("**All-Time Category Totals**")
        st.dataframe(cat_totals, use_container_width=True, hide_index=True)
else:
    st.info("No categorized transactions yet. Categorize your transactions on the **Bank Import** page.")

# ── Top Merchants ─────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏪 Top Merchants (All Time)")

if not txn_raw.empty:
    merchant_totals = (
        txn_raw.groupby("description")["amount"]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"description": "Merchant", "sum": "Total Spent ($)", "count": "# Transactions"})
        .sort_values("Total Spent ($)", ascending=False)
        .head(20)
    )
    merchant_totals["Total Spent ($)"] = merchant_totals["Total Spent ($)"].map("${:,.2f}".format)
    st.dataframe(merchant_totals, use_container_width=True, hide_index=True)

# ── Month-by-Month Detail Table ───────────────────────────────────────────────
st.markdown("---")
with st.expander("🗂️ View Month-by-Month Detail"):
    display = trends[["month_label", "income", "spent", "savings", "savings_rate"]].copy()
    display.columns = ["Month", "Income", "Spent", "Savings", "Savings Rate (%)"]

    def color_savings(val):
        if isinstance(val, (int, float)) and not pd.isna(val):
            return "color: #21c354" if val >= 0 else "color: #ff4b4b"
        return ""

    styled = display.style \
        .format({
            "Income":          "${:,.2f}",
            "Spent":           "${:,.2f}",
            "Savings":         "${:,.2f}",
            "Savings Rate (%)": "{:.1f}%",
        }) \
        .map(color_savings, subset=["Savings", "Savings Rate (%)"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

# ── AI Spending Insights ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🤖 AI Spending Insights")
st.caption("Claude analyzes your Navy Federal transaction history and gives you real, actionable feedback on your spending habits.")

if not api_key:
    st.warning("🔑 No API key found. Add your Anthropic key on the **AI Insights** page to unlock this feature.")
else:
    # Build rich context from all available data
    def build_trends_context() -> str:
        lines = []

        # Overall summary
        lines.append("=== OVERALL FINANCIAL SUMMARY ===")
        lines.append(f"Months of data: {len(trends)}")
        lines.append(f"Total income across all months: ${trends['income'].sum():,.2f}")
        lines.append(f"Total spending across all months: ${trends['spent'].sum():,.2f}")
        lines.append(f"Total saved: ${trends['savings'].sum():,.2f}")
        if not pd.isna(avg_sr):
            lines.append(f"Average monthly savings rate: {avg_sr:.1f}%")
        lines.append("")

        # Month-by-month breakdown
        lines.append("=== MONTH-BY-MONTH BREAKDOWN ===")
        for _, row in trends.iterrows():
            sr = f"{row['savings_rate']:.1f}%" if not pd.isna(row['savings_rate']) else "N/A"
            lines.append(
                f"{row['month_label']}: Income=${row['income']:,.2f}, "
                f"Spent=${row['spent']:,.2f}, Saved=${row['savings']:,.2f}, "
                f"Savings Rate={sr}"
            )
        lines.append("")

        # Category breakdown
        if not txn_cat_all.empty:
            lines.append("=== SPENDING BY CATEGORY (ALL TIME) ===")
            cat_summary = txn_cat_all.groupby("category")["spent"].sum().sort_values(ascending=False)
            for cat, total in cat_summary.items():
                lines.append(f"  {cat}: ${total:,.2f}")
            lines.append("")

            # Category by month
            lines.append("=== CATEGORY SPENDING BY MONTH ===")
            for month_val in sorted(txn_cat_all["month"].unique()):
                month_data = txn_cat_all[txn_cat_all["month"] == month_val]
                label = datetime.strptime(month_val, "%Y-%m").strftime("%b %Y")
                lines.append(f"{label}:")
                for _, row in month_data.sort_values("spent", ascending=False).iterrows():
                    lines.append(f"  {row['category']}: ${row['spent']:,.2f}")
            lines.append("")

        # Top merchants
        if not txn_raw.empty:
            lines.append("=== TOP 15 MERCHANTS BY TOTAL SPEND ===")
            top_merchants = (
                txn_raw.groupby("description")["amount"]
                .agg(["sum", "count"])
                .sort_values("sum", ascending=False)
                .head(15)
            )
            for merchant, row in top_merchants.iterrows():
                lines.append(f"  {merchant}: ${row['sum']:,.2f} ({int(row['count'])} transactions)")
            lines.append("")

            # Recent transactions (last 30)
            lines.append("=== RECENT TRANSACTIONS (LAST 30) ===")
            recent = txn_raw.head(30)
            for _, row in recent.iterrows():
                cat_label = f" [{row['category']}]" if pd.notna(row.get('category')) and row.get('category') else ""
                lines.append(f"  {row['date']} | {row['description']}{cat_label} | ${row['amount']:,.2f}")

        return "\n".join(lines)

    # claude pricing
    INPUT_COST_PER_M  = 3.00
    OUTPUT_COST_PER_M = 15.00

    def ask_claude_trends(prompt: str, context: str) -> tuple[str, dict]:
        client = anthropic.Anthropic(api_key=api_key)
        try:
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1500,
                messages=[{"role": "user", "content": (
                    "You are a sharp, no-nonsense personal finance advisor analyzing real bank transaction data "
                    "from a Navy Federal Credit Union account. Be specific, use real numbers from the data, "
                    "and give genuinely useful advice — not generic platitudes.\n\n"
                    f"Here is the complete financial data:\n\n{context}\n\n"
                    f"User request: {prompt}\n\n"
                    "FORMATTING RULES:\n"
                    "- Write dollar amounts as 'USD X.XX' or '$X.XX' — avoid the raw dollar sign where possible\n"
                    "- Use plain dashes (-) for bullet points\n"
                    "- No markdown headers (no # or **bold**)\n"
                    "- Be specific with numbers from the actual data\n"
                    "- Keep it under 300 words unless the question requires more detail"
                )}]
            )
            usage = message.usage
            cost = (usage.input_tokens / 1_000_000 * INPUT_COST_PER_M) + \
                   (usage.output_tokens / 1_000_000 * OUTPUT_COST_PER_M)
            return message.content[0].text, {
                "input_tokens":  usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost_usd":      cost,
            }
        except anthropic.AuthenticationError:
            return "❌ Invalid API key. Check your key on the AI Insights page.", {}
        except anthropic.RateLimitError:
            return "❌ Rate limit hit. Wait a moment and try again.", {}
        except Exception as e:
            return f"❌ Error: {e}", {}

    def render_ai_response(text: str):
        cleaned = text.replace("$", "＄")
        st.text(cleaned)

    def show_usage(usage_info: dict):
        if not usage_info:
            return
        with st.expander(f"📊 Token usage — ${usage_info['cost_usd']:.4f}", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("Input tokens",  f"{usage_info['input_tokens']:,}")
            c2.metric("Output tokens", f"{usage_info['output_tokens']:,}")
            c3.metric("Cost",          f"${usage_info['cost_usd']:.4f}")

    context = build_trends_context()

    # ── Insight Buttons ───────────────────────────────────────────────────────
    st.markdown("**Quick Insights — click any to generate:**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Analyze My Spending Habits", type="primary", use_container_width=True, key="btn_habits"):
            with st.spinner("Claude is analyzing your spending patterns..."):
                response, usage = ask_claude_trends(
                    "Analyze my overall spending habits across all months. "
                    "What are my biggest spending categories? Where am I spending the most money? "
                    "Are there any concerning patterns or trends month-over-month? "
                    "What does my spending say about my financial priorities?",
                    context
                )
            st.markdown("#### 🔍 Spending Habits Analysis")
            render_ai_response(response)
            show_usage(usage)

        if st.button("📉 Where Am I Overspending?", type="secondary", use_container_width=True, key="btn_over"):
            with st.spinner("Finding overspending patterns..."):
                response, usage = ask_claude_trends(
                    "Look at my spending data and identify where I'm likely overspending or where my money is "
                    "going that might surprise me. Call out specific merchants or categories that stand out. "
                    "Give me 3-5 specific, actionable things I could cut back on with estimated savings.",
                    context
                )
            st.markdown("#### 📉 Overspending Analysis")
            render_ai_response(response)
            show_usage(usage)

        if st.button("🏪 Top Merchant Breakdown", type="secondary", use_container_width=True, key="btn_merchants"):
            with st.spinner("Analyzing merchant spending..."):
                response, usage = ask_claude_trends(
                    "Break down my top merchants by spending. Which merchants am I visiting most frequently "
                    "and spending the most at? Are there any subscriptions or recurring charges I should review? "
                    "Any merchants that seem excessive given the frequency or amount?",
                    context
                )
            st.markdown("#### 🏪 Merchant Analysis")
            render_ai_response(response)
            show_usage(usage)

    with col2:
        if st.button("📈 Month-Over-Month Trends", type="primary", use_container_width=True, key="btn_mom"):
            with st.spinner("Analyzing monthly trends..."):
                response, usage = ask_claude_trends(
                    "Compare my spending month-over-month. Which months were my best and worst financially? "
                    "Is my spending trending up or down over time? What's driving the changes between months? "
                    "What's my savings trajectory looking like?",
                    context
                )
            st.markdown("#### 📈 Month-Over-Month Analysis")
            render_ai_response(response)
            show_usage(usage)

        if st.button("💡 Personalized Savings Tips", type="secondary", use_container_width=True, key="btn_tips"):
            with st.spinner("Generating personalized tips..."):
                response, usage = ask_claude_trends(
                    "Based on my actual spending data, give me 5 specific, personalized tips to improve my savings rate. "
                    "Reference real merchants and categories from my data — not generic advice. "
                    "For each tip, estimate how much I could save per month if I followed it.",
                    context
                )
            st.markdown("#### 💡 Personalized Savings Tips")
            render_ai_response(response)
            show_usage(usage)

        if st.button("🎯 Financial Health Score", type="secondary", use_container_width=True, key="btn_score"):
            with st.spinner("Calculating your financial health..."):
                response, usage = ask_claude_trends(
                    "Give me an honest financial health assessment based on my spending data. "
                    "Score me on: savings rate, spending discipline, category balance, and overall trajectory. "
                    "Be direct — what am I doing well and what needs immediate attention? "
                    "End with one concrete action I should take this week.",
                    context
                )
            st.markdown("#### 🎯 Financial Health Assessment")
            render_ai_response(response)
            show_usage(usage)

    # ── Custom Question ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Ask a custom question about your spending trends:**")
    custom_q = st.text_area(
        "Your question",
        placeholder="e.g. 'How much did I spend on food across all months?' or 'Which month was my worst for discretionary spending?'",
        height=80,
        label_visibility="collapsed"
    )
    if st.button("Ask Claude", type="primary", key="btn_custom_ask") and custom_q.strip():
        with st.spinner("Thinking..."):
            response, usage = ask_claude_trends(custom_q.strip(), context)
        st.markdown("#### Claude's Answer")
        render_ai_response(response)
        show_usage(usage)
