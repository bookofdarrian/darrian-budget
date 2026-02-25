import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime
from utils.db import init_db, load_investment_context, get_setting
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Portfolio Analysis — Peach State Savings", page_icon="🗂️", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("Portfolio Analysis")
inject_css()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights 🔒",    icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth 🔒",      icon="💎")
st.sidebar.page_link("pages/10_rsu_espp.py",      label="RSU/ESPP Advisor 🔒", icon="📈")
st.sidebar.page_link("pages/11_portfolio.py",     label="Portfolio Analysis 🔒", icon="🗂️")
st.sidebar.page_link("pages/12_market_news.py",   label="Market News 🔒",    icon="📰")
st.sidebar.page_link("pages/13_backtesting.py",   label="Strategy Backtest 🔒", icon="🔬")
st.sidebar.page_link("pages/14_trading_bot.py",   label="Paper Trading Bot 🔒", icon="🤖")
st.sidebar.page_link("pages/0_pricing.py",        label="⭐ Upgrade to Pro", icon="⭐")
render_sidebar_user_widget()

_env_key = os.environ.get("ANTHROPIC_API_KEY", "")
if "api_key" not in st.session_state:
    if _env_key:
        st.session_state["api_key"] = _env_key
    else:
        _db_key = get_setting("anthropic_api_key", "")
        if _db_key:
            st.session_state["api_key"] = _db_key
api_key = st.session_state.get("api_key", "")

st.title("🗂️ Portfolio Analysis")
st.caption("Analyze sector exposure, concentration risk, and get AI-powered rebalancing recommendations.")

if not api_key:
    st.warning("⚠️ No Anthropic API key found. Go to AI Insights to save your key.")
    st.stop()

_inv = load_investment_context()

# ── Holdings Input ─────────────────────────────────────────────────────────────
st.subheader("📋 Your Holdings")
st.caption("Enter your current portfolio positions. Your investment account balances from AI Insights are pre-loaded.")

if "holdings" not in st.session_state:
    inv_401k = float(_inv.get("bal_401k", 0) or 0)
    inv_roth = float(_inv.get("bal_roth", 0) or 0)
    inv_hsa  = float(_inv.get("bal_hsa", 0) or 0)
    inv_brok = float(_inv.get("bal_brokerage", 0) or 0)
    st.session_state["holdings"] = []
    if inv_401k > 0:
        st.session_state["holdings"].append({"Name": "401(k) — Target Date Fund", "Ticker": "FXAIX", "Value": inv_401k, "Sector": "Diversified", "Account": "401(k)"})
    if inv_roth > 0:
        st.session_state["holdings"].append({"Name": "Roth IRA — Index Fund", "Ticker": "VTI", "Value": inv_roth, "Sector": "Diversified", "Account": "Roth IRA"})
    if inv_hsa > 0:
        st.session_state["holdings"].append({"Name": "HSA — Invested", "Ticker": "FZROX", "Value": inv_hsa, "Sector": "Diversified", "Account": "HSA"})
    if inv_brok > 0:
        st.session_state["holdings"].append({"Name": "Cash Management", "Ticker": "CASH", "Value": inv_brok, "Sector": "Cash", "Account": "Brokerage"})

SECTORS = ["Diversified", "Technology", "Healthcare", "Financials", "Consumer Discretionary",
           "Consumer Staples", "Energy", "Industrials", "Materials", "Real Estate",
           "Utilities", "Communication Services", "Cash", "Bonds", "Crypto", "Other"]
ACCOUNTS = ["401(k)", "Roth IRA", "HSA", "Brokerage", "Cash Management", "Other"]

with st.expander("➕ Add / Edit Holdings", expanded=len(st.session_state["holdings"]) == 0):
    h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 2, 2])
    with h1: new_name    = st.text_input("Name", placeholder="e.g. Apple Inc.", key="h_name")
    with h2: new_ticker  = st.text_input("Ticker", placeholder="AAPL", key="h_ticker")
    with h3: new_value   = st.number_input("Value ($)", min_value=0.0, step=100.0, key="h_value")
    with h4: new_sector  = st.selectbox("Sector", SECTORS, key="h_sector")
    with h5: new_account = st.selectbox("Account", ACCOUNTS, key="h_account")

    if st.button("➕ Add Holding", key="add_holding"):
        if new_name and new_value > 0:
            st.session_state["holdings"].append({
                "Name": new_name, "Ticker": new_ticker.upper(),
                "Value": new_value, "Sector": new_sector, "Account": new_account
            })
            st.rerun()

    if st.session_state["holdings"]:
        if st.button("🗑️ Clear All Holdings", key="clear_holdings"):
            st.session_state["holdings"] = []
            st.rerun()

if not st.session_state["holdings"]:
    st.info("📭 No holdings yet. Add positions above to start your analysis.")
    st.stop()

holdings_df = pd.DataFrame(st.session_state["holdings"])
total_value = holdings_df["Value"].sum()
holdings_df["Weight (%)"] = (holdings_df["Value"] / total_value * 100).round(2)

# ── KPI Row ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("💼 Total Portfolio",   f"${total_value:,.2f}")
k2.metric("📊 # of Positions",    str(len(holdings_df)))
k3.metric("🏆 Largest Position",  holdings_df.loc[holdings_df["Value"].idxmax(), "Name"])
k4.metric("⚖️ Largest Weight",    f"{holdings_df['Weight (%)'].max():.1f}%")

st.markdown("---")

st.subheader("📋 Holdings Summary")
st.dataframe(
    holdings_df.style.format({"Value": "${:,.2f}", "Weight (%)": "{:.2f}%"}),
    use_container_width=True, hide_index=True
)

st.markdown("---")
col_sector, col_account = st.columns(2)

with col_sector:
    st.subheader("🏭 Sector Allocation")
    sector_df = holdings_df.groupby("Sector")["Value"].sum().reset_index()
    sector_df["Weight (%)"] = (sector_df["Value"] / total_value * 100).round(2)
    sector_df = sector_df.sort_values("Value", ascending=False)
    st.dataframe(
        sector_df.style.format({"Value": "${:,.2f}", "Weight (%)": "{:.2f}%"}),
        use_container_width=True, hide_index=True
    )
    st.bar_chart(sector_df.set_index("Sector")["Weight (%)"])

with col_account:
    st.subheader("🏦 Account Allocation")
    account_df = holdings_df.groupby("Account")["Value"].sum().reset_index()
    account_df["Weight (%)"] = (account_df["Value"] / total_value * 100).round(2)
    account_df = account_df.sort_values("Value", ascending=False)
    st.dataframe(
        account_df.style.format({"Value": "${:,.2f}", "Weight (%)": "{:.2f}%"}),
        use_container_width=True, hide_index=True
    )
    st.bar_chart(account_df.set_index("Account")["Weight (%)"])

# ── Concentration Risk ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("⚠️ Concentration Risk")
top5 = holdings_df.nlargest(5, "Value")[["Name", "Ticker", "Value", "Weight (%)", "Sector"]]
for _, row in top5.iterrows():
    pct = row["Weight (%)"]
    color = "🔴" if pct > 25 else "🟡" if pct > 15 else "🟢"
    st.markdown(f"{color} **{row['Name']}** ({row['Ticker']}) — {pct:.1f}% of portfolio (${row['Value']:,.2f})")

diversified_pct    = holdings_df[holdings_df["Sector"] == "Diversified"]["Value"].sum() / total_value * 100
single_stock_pct   = holdings_df[holdings_df["Sector"] != "Diversified"]["Value"].sum() / total_value * 100
cr1, cr2 = st.columns(2)
cr1.metric("🌐 Diversified Funds",    f"{diversified_pct:.1f}%",  help="% in index funds / target date funds")
cr2.metric("🎯 Single Stock/Sector",  f"{single_stock_pct:.1f}%", help="% in individual stocks or sector funds")

# ── AI Analysis ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🤖 AI Portfolio Analysis")

tab_overview, tab_rebalance, tab_risk = st.tabs(["📊 Portfolio Overview", "⚖️ Rebalancing Advice", "🔍 Risk Assessment"])

def build_portfolio_context():
    lines = [
        f"Total Portfolio Value: ${total_value:,.2f}",
        f"Number of positions: {len(holdings_df)}",
        "",
        "Holdings (Name | Ticker | Value | Weight | Sector | Account):",
    ]
    for _, row in holdings_df.iterrows():
        lines.append(f"  {row['Name']} | {row['Ticker']} | ${row['Value']:,.2f} | {row['Weight (%)']:.1f}% | {row['Sector']} | {row['Account']}")
    lines += ["", "Sector breakdown:"]
    for _, row in sector_df.iterrows():
        lines.append(f"  {row['Sector']}: ${row['Value']:,.2f} ({row['Weight (%)']:.1f}%)")
    inv_notes = _inv.get("notes", "")
    if inv_notes:
        lines.append(f"\nAdditional context: {inv_notes}")
    return "\n".join(lines)

def ask_claude_portfolio(prompt, context):
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": (
                "You are a portfolio analyst. Analyze this portfolio and give specific, actionable advice.\n\n"
                f"{context}\n\n{prompt}\n\n"
                "RULES: No markdown formatting. No dollar signs (write USD X). Plain dashes for bullets. Be specific with numbers."
            )}]
        )
        return msg.content[0].text.replace("$", "＄"), msg.usage
    except Exception as e:
        return f"Error: {e}", None

ctx = build_portfolio_context()

with tab_overview:
    if st.button("📊 Generate Portfolio Overview", type="primary", key="btn_port_overview"):
        with st.spinner("Analyzing your portfolio..."):
            resp, usage = ask_claude_portfolio(
                "Give a concise portfolio overview: overall health, diversification quality, biggest strengths and weaknesses. Under 200 words.",
                ctx
            )
        st.text(resp)
        if usage:
            cost = (usage.input_tokens / 1_000_000 * 3.0) + (usage.output_tokens / 1_000_000 * 15.0)
            st.caption(f"📊 ${cost:.4f} — {usage.input_tokens + usage.output_tokens:,} tokens")

with tab_rebalance:
    target_stocks = st.slider("Target Stock Allocation (%)", 0, 100, 80, key="target_stocks")
    target_bonds  = st.slider("Target Bond/Cash Allocation (%)", 0, 100, 20, key="target_bonds")
    if st.button("⚖️ Get Rebalancing Recommendations", type="primary", key="btn_rebalance"):
        with st.spinner("Calculating rebalancing plan..."):
            resp, usage = ask_claude_portfolio(
                f"My target allocation is {target_stocks}% stocks / {target_bonds}% bonds/cash. "
                "What specific trades should I make to rebalance? List each position to buy/sell with dollar amounts. "
                "Consider tax efficiency (sell in tax-advantaged accounts first).",
                ctx
            )
        st.text(resp)
        if usage:
            cost = (usage.input_tokens / 1_000_000 * 3.0) + (usage.output_tokens / 1_000_000 * 15.0)
            st.caption(f"📊 ${cost:.4f} — {usage.input_tokens + usage.output_tokens:,} tokens")

with tab_risk:
    if st.button("🔍 Run Risk Assessment", type="primary", key="btn_risk"):
        with st.spinner("Assessing portfolio risk..."):
            resp, usage = ask_claude_portfolio(
                "Assess the risk profile of this portfolio. Cover: concentration risk, sector risk, single-stock risk, "
                "liquidity, and overall risk level (conservative/moderate/aggressive). "
                "Give 3 specific actions to reduce risk if needed.",
                ctx
            )
        st.text(resp)
        if usage:
            cost = (usage.input_tokens / 1_000_000 * 3.0) + (usage.output_tokens / 1_000_000 * 15.0)
            st.caption(f"📊 ${cost:.4f} — {usage.input_tokens + usage.output_tokens:,} tokens")

st.markdown("---")
st.download_button(
    "⬇️ Export Holdings as CSV",
    holdings_df.to_csv(index=False).encode(),
    file_name=f"portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)
