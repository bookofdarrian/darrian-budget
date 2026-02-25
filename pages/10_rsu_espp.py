import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime, date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.db import init_db, get_setting
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="RSU/ESPP Advisor - Peach State Savings", page_icon="📈", layout="wide")
init_db()
require_login()
require_pro("RSU/ESPP Decision Support")
inject_css()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",              icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",              icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",                icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="Business Tracker",      icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",        icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",           icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",        icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights",           icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",       icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth",             icon="💎")
st.sidebar.page_link("pages/10_rsu_espp.py",      label="RSU/ESPP Advisor",      icon="📈")
st.sidebar.page_link("pages/11_portfolio.py",     label="Portfolio Analysis",    icon="🗂️")
st.sidebar.page_link("pages/12_market_news.py",   label="Market News",           icon="📰")
st.sidebar.page_link("pages/13_backtesting.py",   label="Strategy Backtest",     icon="🔬")
st.sidebar.page_link("pages/14_trading_bot.py",   label="Paper Trading Bot",     icon="🤖")
st.sidebar.page_link("pages/0_pricing.py",        label="Upgrade to Pro",        icon="⭐")
render_sidebar_user_widget()

# ── API key ───────────────────────────────────────────────────────────────────
_ck = os.environ.get("ANTHROPIC_API_KEY", "")
if "api_key" not in st.session_state:
    if _ck:
        st.session_state["api_key"] = _ck
    else:
        k = get_setting("anthropic_api_key", "")
        if k:
            st.session_state["api_key"] = k
api_key = st.session_state.get("api_key", "")

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📈 RSU / ESPP Decision Support")
st.caption("Model your equity compensation, understand the tax impact, and get AI-powered sell-vs-hold analysis.")

tab_rsu, tab_espp, tab_ai = st.tabs(["🏷️ RSU Vesting", "💰 ESPP Calculator", "🧠 AI Analysis"])

# ─────────────────────────────────────────────────────────────────────────────
with tab_rsu:
    st.subheader("🏷️ RSU Vesting Schedule & Tax Impact")
    st.caption("RSUs are taxed as ordinary income at vest. Model your upcoming vests and their tax cost.")

    c1, c2, c3 = st.columns(3)
    with c1:
        ticker = st.text_input("Company Ticker", value="AAPL", key="rsu_ticker").upper()
        shares_total = st.number_input("Total Granted Shares", min_value=1, value=1000, key="rsu_total")
    with c2:
        vest_schedule = st.selectbox("Vesting Schedule", ["4-year monthly (1/48)", "4-year quarterly (1/16)", "4-year annual (25%/yr)", "3-year annual (33%/yr)", "Custom"], key="rsu_sched")
        grant_price = st.number_input("Grant Price (USD)", min_value=0.01, value=150.0, step=0.01, key="rsu_grant")
    with c3:
        current_price = st.number_input("Current Price (USD)", min_value=0.01, value=175.0, step=0.01, key="rsu_current")
        fed_tax_rate = st.slider("Federal Tax Rate (%)", min_value=10, max_value=37, value=24, key="rsu_fed")

    state_tax = st.slider("State Tax Rate (%)", min_value=0, max_value=15, value=6, key="rsu_state")

    st.markdown("---")

    # Calculate vesting
    if vest_schedule == "4-year monthly (1/48)":
        periods = 48; label = "months"
    elif vest_schedule == "4-year quarterly (1/16)":
        periods = 16; label = "quarters"
    elif vest_schedule == "4-year annual (25%/yr)":
        periods = 4; label = "years"
    elif vest_schedule == "3-year annual (33%/yr)":
        periods = 3; label = "years"
    else:
        periods = st.number_input("Custom periods", min_value=1, value=12, key="rsu_custom_p")
        label = "periods"

    shares_per_period = shares_total / periods
    total_tax_rate = (fed_tax_rate + state_tax) / 100.0

    rows = []
    for i in range(1, min(int(periods) + 1, 13)):
        vest_value = shares_per_period * current_price
        tax_owed = vest_value * total_tax_rate
        net_value = vest_value - tax_owed
        rows.append({
            "Period": i,
            "Shares Vesting": round(shares_per_period, 2),
            "Vest Value (USD)": round(vest_value, 2),
            "Tax Owed (USD)": round(tax_owed, 2),
            "Net After Tax (USD)": round(net_value, 2),
        })

    df_rsu = pd.DataFrame(rows)
    st.dataframe(df_rsu, use_container_width=True, hide_index=True)

    total_vest_value = shares_total * current_price
    total_tax = total_vest_value * total_tax_rate
    total_net = total_vest_value - total_tax
    gain_pct = ((current_price - grant_price) / grant_price) * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Grant Value", f"${total_vest_value:,.0f}")
    m2.metric("Total Tax Owed", f"${total_tax:,.0f}", help=f"{fed_tax_rate + state_tax}% combined rate")
    m3.metric("Net After Tax", f"${total_net:,.0f}")
    m4.metric("Price Gain vs Grant", f"{gain_pct:+.1f}%")

    st.info("Tip: Many companies withhold 22% federal at vest. If your bracket is higher, you may owe more at tax time.")

# ─────────────────────────────────────────────────────────────────────────────
with tab_espp:
    st.subheader("💰 ESPP Calculator")
    st.caption("ESPP lets you buy company stock at a discount. The discount is taxed as ordinary income; gains beyond that are capital gains.")

    c1, c2, c3 = st.columns(3)
    with c1:
        espp_ticker = st.text_input("Company Ticker", value="MSFT", key="espp_ticker").upper()
        espp_contribution = st.number_input("Per-Period Contribution (USD)", min_value=1.0, value=500.0, step=50.0, key="espp_contrib")
        espp_periods = st.number_input("Offering Periods per Year", min_value=1, value=2, key="espp_periods")
    with c2:
        espp_discount = st.slider("ESPP Discount (%)", min_value=5, max_value=15, value=15, key="espp_disc")
        espp_lookback = st.checkbox("Lookback Provision?", value=True, key="espp_look", help="Lookback uses the lower of offering start or end price")
        espp_offering_price = st.number_input("Offering Start Price (USD)", min_value=0.01, value=160.0, step=0.01, key="espp_offer")
    with c3:
        espp_current = st.number_input("Current / End Price (USD)", min_value=0.01, value=175.0, step=0.01, key="espp_cur")
        espp_fed = st.slider("Federal Tax Rate (%)", min_value=10, max_value=37, value=24, key="espp_fed")
        espp_state = st.slider("State Tax Rate (%)", min_value=0, max_value=15, value=6, key="espp_state")

    st.markdown("---")

    base_price = min(espp_offering_price, espp_current) if espp_lookback else espp_current
    purchase_price = base_price * (1 - espp_discount / 100)
    annual_contribution = espp_contribution * espp_periods
    shares_purchased = annual_contribution / purchase_price
    current_value = shares_purchased * espp_current
    discount_income = shares_purchased * (espp_current - purchase_price)
    tax_on_discount = discount_income * (espp_fed + espp_state) / 100
    net_gain = current_value - annual_contribution - tax_on_discount
    immediate_roi = (net_gain / annual_contribution) * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Purchase Price", f"${purchase_price:.2f}", help=f"{espp_discount}% off {'lower of start/end' if espp_lookback else 'end price'}")
    m2.metric("Shares Purchased", f"{shares_purchased:.2f}")
    m3.metric("Current Value", f"${current_value:,.2f}")
    m4.metric("Net Gain After Tax", f"${net_gain:,.2f}", delta=f"{immediate_roi:.1f}% ROI")

    st.markdown("#### Sell Immediately vs Hold")
    sell_now_net = current_value - tax_on_discount - annual_contribution
    st.success(f"Sell immediately: net gain ~${sell_now_net:,.2f} (guaranteed {espp_discount}% discount minus tax)")
    st.warning("Hold longer: subject to stock price risk, but gains beyond discount taxed at lower capital gains rate if held 2+ years from offering start.")

    st.info(f"Immediate guaranteed return: ~{espp_discount}% discount. After {espp_fed + espp_state}% tax on discount, effective return is ~{espp_discount * (1 - (espp_fed + espp_state)/100):.1f}%. Most financial advisors recommend selling immediately to lock in the guaranteed gain.")

# ─────────────────────────────────────────────────────────────────────────────
with tab_ai:
    st.subheader("🧠 AI Analysis: Sell vs Hold Decision")
    st.caption("Claude analyzes your specific RSU/ESPP situation and gives a direct recommendation.")

    if not api_key:
        st.warning("No Claude API key found. Go to AI Insights to save your key.")
    else:
        st.markdown("**Describe your situation for a personalized analysis:**")
        c1, c2 = st.columns(2)
        with c1:
            ai_comp_type = st.selectbox("Compensation Type", ["RSU", "ESPP", "Both RSU and ESPP"], key="ai_comp")
            ai_ticker = st.text_input("Ticker", value="AAPL", key="ai_tick").upper()
            ai_shares = st.number_input("Shares / Value at stake (USD)", min_value=0.0, value=50000.0, step=1000.0, key="ai_shares")
            ai_holding = st.selectbox("Current holding period", ["Just vested / just purchased", "6-12 months", "1-2 years", "2+ years"], key="ai_hold")
        with c2:
            ai_concentration = st.slider("% of net worth in this stock", min_value=0, max_value=100, value=20, key="ai_conc")
            ai_need_cash = st.selectbox("Cash need", ["No immediate need", "Might need in 1 year", "Need cash now"], key="ai_cash")
            ai_sentiment = st.selectbox("Your view on the company", ["Very bullish", "Neutral", "Cautious", "Bearish"], key="ai_sent")
            ai_tax_year = st.selectbox("Tax situation", ["High income year", "Normal income year", "Low income year (e.g. job change)"], key="ai_tax")

        ai_notes = st.text_area("Any other context (optional)", placeholder="e.g. planning to buy a house next year, company has earnings next month...", key="ai_notes")

        if st.button("🧠 Get AI Recommendation", type="primary", key="btn_rsu_ai"):
            context = (
                f"Equity Compensation Analysis Request\n"
                f"Type: {ai_comp_type}\n"
                f"Ticker: {ai_ticker}\n"
                f"Value at stake: ${ai_shares:,.0f}\n"
                f"Holding period: {ai_holding}\n"
                f"Concentration in net worth: {ai_concentration}%\n"
                f"Cash need: {ai_need_cash}\n"
                f"View on company: {ai_sentiment}\n"
                f"Tax situation: {ai_tax_year}\n"
                f"Additional context: {ai_notes or 'None'}"
            )
            prompt = (
                "You are a fee-only financial advisor specializing in equity compensation. "
                "Give a direct, honest sell-vs-hold recommendation for this person's RSU/ESPP situation. "
                "Cover: 1. Concentration risk. 2. Tax optimization (ordinary income vs capital gains). "
                "3. The 'sell immediately' vs 'hold for long-term gains' tradeoff. "
                "4. Your specific recommendation with reasoning. "
                "5. One thing they should do this week. "
                "Be direct. No generic disclaimers. No markdown. No dollar signs."
            )
            with st.spinner("Claude is analyzing your equity compensation..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    msg = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=700,
                        messages=[{"role": "user", "content": f"{context}\n\n{prompt}"}]
                    )
                    st.text(msg.content[0].text)
                    usage = msg.usage
                    cost = (usage.input_tokens / 1e6 * 3.0) + (usage.output_tokens / 1e6 * 15.0)
                    st.caption(f"Cost: ${cost:.4f} - {usage.input_tokens + usage.output_tokens:,} tokens")
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")
st.caption("This tool provides educational information only. Consult a tax professional for advice specific to your situation.")
