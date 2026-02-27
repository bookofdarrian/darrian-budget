import os
import streamlit as st
import pandas as pd
import anthropic
from datetime import datetime, date
from utils.db import init_db, get_setting
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Strategy Backtesting — Peach State Savings", page_icon="🔬", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("Strategy Backtesting")
inject_css()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/18_real_estate_bot.py", label="🏠 Real Estate Bot", icon="🏠")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py",   label="Business Tracker 🔒", icon="💼")
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

st.title("🔬 Strategy Backtesting")
st.caption("Describe a trading idea in plain English — Claude writes the Python backtest, you run it and see historical results.")

if not api_key:
    st.warning("⚠️ No Anthropic API key found. Go to AI Insights to save your key.")
    st.stop()

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    import yfinance as yf
    yf_available = True
except ImportError:
    yf_available = False

st.info("💡 **How this works:** Pick a strategy template or describe your own → Claude generates Python backtest code → Run it live in the app → See results and charts.")

if not yf_available:
    st.warning("⚠️ yfinance not installed. Run `pip install yfinance` to enable live backtesting.")

st.markdown("---")

# ── Strategy Templates ────────────────────────────────────────────────────────
STRATEGY_TEMPLATES = {
    "SMA Crossover (Golden Cross)": {
        "description": "Buy when the 50-day SMA crosses above the 200-day SMA (Golden Cross). Sell when it crosses below (Death Cross). Classic trend-following strategy.",
        "params": {"ticker": "SPY", "fast_period": 50, "slow_period": 200, "start_date": "2020-01-01"},
    },
    "RSI Mean Reversion": {
        "description": "Buy when RSI drops below 30 (oversold). Sell when RSI rises above 70 (overbought). Works best in range-bound markets.",
        "params": {"ticker": "AAPL", "rsi_period": 14, "oversold": 30, "overbought": 70, "start_date": "2020-01-01"},
    },
    "Momentum (52-Week High Breakout)": {
        "description": "Buy when price breaks above the 52-week high. Hold for 20 days then exit. Momentum strategy.",
        "params": {"ticker": "QQQ", "lookback_days": 252, "hold_days": 20, "start_date": "2020-01-01"},
    },
    "Dollar-Cost Averaging (DCA)": {
        "description": "Invest a fixed dollar amount every month regardless of price. Compare to lump-sum investing.",
        "params": {"ticker": "VTI", "monthly_amount": 500, "start_date": "2020-01-01"},
    },
    "Custom Strategy": {
        "description": "",
        "params": {},
    },
}

tab_template, tab_custom, tab_run, tab_results = st.tabs(["📋 Strategy Templates", "✏️ Custom Strategy", "▶️ Run Backtest", "📊 Results & Analysis"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Strategy Templates
# ═══════════════════════════════════════════════════════════════════════════════
with tab_template:
    st.subheader("📋 Pre-Built Strategy Templates")
    st.caption("Select a strategy to pre-fill the backtest parameters.")

    selected_template = st.selectbox("Choose a strategy", list(STRATEGY_TEMPLATES.keys()), key="template_select")
    template = STRATEGY_TEMPLATES[selected_template]

    if selected_template != "Custom Strategy":
        st.markdown(f"**Description:** {template['description']}")
        st.markdown("**Default Parameters:**")
        for k, v in template["params"].items():
            st.markdown(f"- `{k}`: `{v}`")

        if st.button("📋 Load This Template", type="primary", key="load_template"):
            st.session_state["backtest_strategy"] = selected_template
            st.session_state["backtest_description"] = template["description"]
            st.session_state["backtest_params"] = template["params"].copy()
            st.success(f"✅ Loaded: {selected_template}. Go to the 'Run Backtest' tab.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Custom Strategy
# ═══════════════════════════════════════════════════════════════════════════════
with tab_custom:
    st.subheader("✏️ Describe Your Own Strategy")
    st.caption("Describe your trading idea in plain English. Claude will write the Python backtest code.")

    custom_desc = st.text_area(
        "Strategy Description",
        placeholder=(
            "Example: 'Buy SPY when the VIX is above 25 (fear spike) and sell after 30 days. "
            "The idea is to buy during panic and hold for a month.'\n\n"
            "Or: 'Buy AAPL when it drops more than 5% in a single day. Sell when it recovers 3%.'"
        ),
        height=120,
        key="custom_strategy_desc"
    )

    custom_ticker     = st.text_input("Primary Ticker", value="SPY", key="custom_ticker")
    custom_start      = st.date_input("Backtest Start Date", value=date(2020, 1, 1), key="custom_start")
    custom_capital    = st.number_input("Starting Capital ($)", min_value=1000.0, value=10000.0, step=1000.0, key="custom_capital")

    if st.button("🤖 Generate Backtest Code with Claude", type="primary", key="btn_gen_code", disabled=not custom_desc):
        prompt = f"""Write a Python backtesting script for this strategy:

Strategy: {custom_desc}
Ticker: {custom_ticker}
Start Date: {custom_start}
Starting Capital: ${custom_capital:,.0f}

Requirements:
1. Use yfinance to download price data (import yfinance as yf)
2. Use pandas for all calculations
3. Return a DataFrame called 'results' with columns: Date, Portfolio_Value, Signal, Position
4. Calculate and print: Total Return %, CAGR %, Max Drawdown %, Sharpe Ratio, Win Rate %, Number of Trades
5. Also calculate buy-and-hold benchmark return for comparison
6. Keep it under 80 lines of clean Python
7. No matplotlib (we'll chart in Streamlit)
8. Handle edge cases (no data, division by zero)

Output ONLY the Python code, no explanation, no markdown fences."""

        with st.spinner("Claude is writing your backtest..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                msg = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                generated_code = msg.content[0].text
                # Strip markdown fences if Claude added them
                if "```python" in generated_code:
                    generated_code = generated_code.split("```python")[1].split("```")[0].strip()
                elif "```" in generated_code:
                    generated_code = generated_code.split("```")[1].split("```")[0].strip()

                st.session_state["generated_code"] = generated_code
                st.session_state["backtest_strategy"] = "Custom: " + custom_desc[:50]
                st.session_state["backtest_description"] = custom_desc
                st.session_state["backtest_params"] = {
                    "ticker": custom_ticker,
                    "start_date": str(custom_start),
                    "capital": custom_capital,
                }
                usage = msg.usage
                cost = (usage.input_tokens / 1_000_000 * 3.0) + (usage.output_tokens / 1_000_000 * 15.0)
                st.success(f"✅ Code generated! Go to 'Run Backtest' tab. (Cost: ${cost:.4f})")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state.get("generated_code"):
        st.markdown("**Generated Code Preview:**")
        st.code(st.session_state["generated_code"], language="python")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Run Backtest
# ═══════════════════════════════════════════════════════════════════════════════
with tab_run:
    st.subheader("▶️ Run Backtest")

    strategy_name = st.session_state.get("backtest_strategy", "")
    params        = st.session_state.get("backtest_params", {})

    if not strategy_name:
        st.info("👈 Select a template from 'Strategy Templates' or describe a custom strategy first.")
    else:
        st.markdown(f"**Strategy:** {strategy_name}")

        # ── Parameter overrides ───────────────────────────────────────────────
        st.markdown("#### ⚙️ Parameters")
        bt_ticker  = st.text_input("Ticker", value=params.get("ticker", "SPY"), key="bt_ticker")
        bt_start   = st.date_input("Start Date", value=date(2020, 1, 1), key="bt_start")
        bt_end     = st.date_input("End Date", value=date.today(), key="bt_end")
        bt_capital = st.number_input("Starting Capital ($)", min_value=100.0, value=10000.0, step=500.0, key="bt_capital")

        if not yf_available:
            st.error("yfinance required. Run: pip install yfinance")
        else:
            if st.button("▶️ Run Backtest Now", type="primary", key="btn_run_bt"):
                with st.spinner(f"Downloading {bt_ticker} data and running backtest..."):
                    try:
                        import yfinance as yf
                        import numpy as np

                        df = yf.download(bt_ticker, start=str(bt_start), end=str(bt_end), progress=False)
                        if df.empty:
                            st.error(f"No data found for {bt_ticker}")
                        else:
                            df = df[["Close"]].copy()
                            df.columns = ["Close"]
                            df.index = pd.to_datetime(df.index)

                            # ── Run the appropriate built-in strategy ─────────
                            strat = st.session_state.get("backtest_strategy", "")

                            if "SMA Crossover" in strat:
                                fast = params.get("fast_period", 50)
                                slow = params.get("slow_period", 200)
                                df["SMA_fast"] = df["Close"].rolling(fast).mean()
                                df["SMA_slow"] = df["Close"].rolling(slow).mean()
                                df["Signal"] = 0
                                df.loc[df["SMA_fast"] > df["SMA_slow"], "Signal"] = 1
                                df.loc[df["SMA_fast"] <= df["SMA_slow"], "Signal"] = 0

                            elif "RSI" in strat:
                                period = params.get("rsi_period", 14)
                                delta = df["Close"].diff()
                                gain  = delta.clip(lower=0).rolling(period).mean()
                                loss  = (-delta.clip(upper=0)).rolling(period).mean()
                                rs    = gain / loss.replace(0, float("nan"))
                                df["RSI"] = 100 - (100 / (1 + rs))
                                df["Signal"] = 0
                                df.loc[df["RSI"] < params.get("oversold", 30), "Signal"] = 1
                                df.loc[df["RSI"] > params.get("overbought", 70), "Signal"] = 0

                            elif "DCA" in strat:
                                monthly_amt = params.get("monthly_amount", 500)
                                df["Signal"] = 0
                                df["Month"] = df.index.to_period("M")
                                first_of_month = ~df["Month"].duplicated()
                                df.loc[first_of_month, "Signal"] = 1
                                # DCA: buy fixed $ each month
                                shares = 0.0
                                cash   = bt_capital
                                portfolio_vals = []
                                for idx, row in df.iterrows():
                                    if row["Signal"] == 1 and cash >= monthly_amt:
                                        shares += monthly_amt / row["Close"]
                                        cash   -= monthly_amt
                                    portfolio_vals.append(cash + shares * row["Close"])
                                df["Portfolio_Value"] = portfolio_vals
                                df["Position"] = shares

                            else:
                                # Generic: use generated code or momentum fallback
                                generated = st.session_state.get("generated_code", "")
                                if generated:
                                    try:
                                        local_ns = {"df": df.copy(), "bt_capital": bt_capital, "pd": pd, "np": np}
                                        exec(generated, local_ns)
                                        if "results" in local_ns:
                                            df = local_ns["results"]
                                        elif "df" in local_ns:
                                            df = local_ns["df"]
                                    except Exception as exec_err:
                                        st.warning(f"Generated code error: {exec_err}. Falling back to buy-and-hold.")
                                        df["Signal"] = 1
                                else:
                                    # Momentum fallback
                                    df["Signal"] = 1

                            # ── Portfolio simulation (if not already done) ────
                            if "Portfolio_Value" not in df.columns:
                                df["Position"] = df["Signal"].shift(1).fillna(0)
                                df["Daily_Return"] = df["Close"].pct_change()
                                df["Strategy_Return"] = df["Position"] * df["Daily_Return"]
                                df["Portfolio_Value"] = bt_capital * (1 + df["Strategy_Return"]).cumprod()

                            # ── Buy-and-hold benchmark ────────────────────────
                            df["BuyHold_Value"] = bt_capital * (df["Close"] / df["Close"].iloc[0])

                            # ── Metrics ───────────────────────────────────────
                            final_val   = df["Portfolio_Value"].iloc[-1]
                            total_ret   = (final_val - bt_capital) / bt_capital * 100
                            bh_ret      = (df["BuyHold_Value"].iloc[-1] - bt_capital) / bt_capital * 100
                            years       = (df.index[-1] - df.index[0]).days / 365.25
                            cagr        = ((final_val / bt_capital) ** (1 / max(years, 0.01)) - 1) * 100

                            # Max drawdown
                            rolling_max = df["Portfolio_Value"].cummax()
                            drawdown    = (df["Portfolio_Value"] - rolling_max) / rolling_max
                            max_dd      = drawdown.min() * 100

                            # Sharpe (annualized, risk-free ~5%)
                            if "Strategy_Return" in df.columns:
                                daily_ret = df["Strategy_Return"].dropna()
                            else:
                                daily_ret = df["Portfolio_Value"].pct_change().dropna()
                            sharpe = (daily_ret.mean() - 0.05/252) / (daily_ret.std() + 1e-10) * (252 ** 0.5)

                            st.session_state["bt_results"] = {
                                "df": df,
                                "final_val": final_val,
                                "total_ret": total_ret,
                                "bh_ret": bh_ret,
                                "cagr": cagr,
                                "max_dd": max_dd,
                                "sharpe": sharpe,
                                "ticker": bt_ticker,
                                "capital": bt_capital,
                                "strategy": strat,
                            }
                            st.success("✅ Backtest complete! Go to 'Results & Analysis' tab.")
                    except Exception as e:
                        st.error(f"Backtest error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Results
# ═══════════════════════════════════════════════════════════════════════════════
with tab_results:
    st.subheader("📊 Backtest Results")

    if "bt_results" not in st.session_state:
        st.info("👈 Run a backtest first.")
    else:
        r = st.session_state["bt_results"]
        df_r = r["df"]

        st.markdown(f"**Strategy:** {r['strategy']} | **Ticker:** {r['ticker']} | **Capital:** ${r['capital']:,.0f}")
        st.markdown("---")

        # ── KPI Metrics ───────────────────────────────────────────────────────
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("💰 Final Value",    f"${r['final_val']:,.2f}",
                  delta=f"{r['total_ret']:+.1f}%")
        m2.metric("📈 Strategy Return", f"{r['total_ret']:+.1f}%",
                  delta=f"{r['total_ret'] - r['bh_ret']:+.1f}% vs B&H",
                  delta_color="normal" if r["total_ret"] >= r["bh_ret"] else "inverse")
        m3.metric("📊 Buy & Hold",     f"{r['bh_ret']:+.1f}%")
        m4.metric("📉 Max Drawdown",   f"{r['max_dd']:.1f}%", delta_color="inverse")
        m5.metric("⚡ Sharpe Ratio",   f"{r['sharpe']:.2f}",
                  help="Above 1.0 is good, above 2.0 is excellent")

        st.markdown("---")

        # ── Portfolio Value Chart ─────────────────────────────────────────────
        st.subheader("📈 Portfolio Value Over Time")
        chart_cols = ["Portfolio_Value", "BuyHold_Value"]
        chart_df = df_r[[c for c in chart_cols if c in df_r.columns]].copy()
        chart_df.columns = [c.replace("_", " ") for c in chart_df.columns]
        st.line_chart(chart_df, use_container_width=True)

        # ── Drawdown Chart ────────────────────────────────────────────────────
        st.subheader("📉 Drawdown")
        rolling_max = df_r["Portfolio_Value"].cummax()
        dd_series   = (df_r["Portfolio_Value"] - rolling_max) / rolling_max * 100
        st.area_chart(dd_series.rename("Drawdown (%)"), use_container_width=True)

        st.markdown("---")

        # ── AI Analysis of Results ────────────────────────────────────────────
        st.subheader("🤖 AI Analysis of Backtest Results")
        if st.button("🤖 Analyze These Results with Claude", type="primary", key="btn_analyze_bt"):
            context = f"""Backtest Results:
Strategy: {r['strategy']}
Ticker: {r['ticker']}
Starting Capital: ${r['capital']:,.0f}
Final Value: ${r['final_val']:,.2f}
Total Return: {r['total_ret']:+.1f}%
Buy & Hold Return: {r['bh_ret']:+.1f}%
Alpha vs B&H: {r['total_ret'] - r['bh_ret']:+.1f}%
CAGR: {r['cagr']:.1f}%
Max Drawdown: {r['max_dd']:.1f}%
Sharpe Ratio: {r['sharpe']:.2f}"""

            prompt = """Analyze these backtest results honestly. Cover:
1. Is this strategy actually good or just lucky? (overfitting risk)
2. How does it compare to buy-and-hold? Is the complexity worth it?
3. What are the biggest risks of trading this live?
4. What market conditions would break this strategy?
5. Honest verdict: would you trade this with real money?

Be direct and skeptical. Most backtests look better than live trading. No markdown, no dollar signs."""

            with st.spinner("Claude is analyzing your results..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    msg = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=800,
                        messages=[{"role": "user", "content": f"You are a quantitative analyst who is skeptical of backtests.\n\n{context}\n\n{prompt}"}]
                    )
                    st.text(msg.content[0].text.replace("$", "＄"))
                    usage = msg.usage
                    cost = (usage.input_tokens / 1_000_000 * 3.0) + (usage.output_tokens / 1_000_000 * 15.0)
                    st.caption(f"📊 ${cost:.4f} — {usage.input_tokens + usage.output_tokens:,} tokens")
                except Exception as e:
                    st.error(f"Error: {e}")

        # ── Export ────────────────────────────────────────────────────────────
        st.markdown("---")
        export_df = df_r[["Close", "Portfolio_Value", "BuyHold_Value"]].copy() if "BuyHold_Value" in df_r.columns else df_r[["Close", "Portfolio_Value"]].copy()
        st.download_button(
            "⬇️ Export Results as CSV",
            export_df.to_csv().encode(),
            file_name=f"backtest_{r['ticker']}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption("⚠️ Past performance does not guarantee future results. Backtests are subject to look-ahead bias and overfitting. Always paper trade before using real money.")
