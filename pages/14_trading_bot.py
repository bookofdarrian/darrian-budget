import os, streamlit as st, pandas as pd, anthropic, requests
from datetime import datetime
from utils.db import init_db, get_setting, set_setting
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError: pass

# ── Alpaca OAuth2 helpers ─────────────────────────────────────────────────────
ALPACA_AUTH_URL = "https://authx.alpaca.markets/v1/oauth2/token"

def _get_oauth_token(client_id: str, client_secret: str) -> tuple[str | None, str | None]:
    """
    Exchange client_id + client_secret for an OAuth2 bearer token.
    Returns (access_token, error_message).
    """
    try:
        r = requests.post(
            ALPACA_AUTH_URL,
            headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            timeout=15,
        )
        _persist_request_id(r)
        if r.status_code == 200:
            return r.json().get("access_token"), None
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return None, str(e)


def _persist_request_id(response: requests.Response):
    """Store the X-Request-ID from any Alpaca response for support/debugging."""
    rid = response.headers.get("X-Request-ID") or response.headers.get("x-request-id")
    if rid:
        if "alpaca_request_ids" not in st.session_state:
            st.session_state["alpaca_request_ids"] = []
        ids = st.session_state["alpaca_request_ids"]
        # Keep last 20 request IDs
        ids.insert(0, {"id": rid, "url": response.url, "status": response.status_code,
                       "ts": datetime.now().strftime("%H:%M:%S")})
        st.session_state["alpaca_request_ids"] = ids[:20]

st.set_page_config(page_title="Paper Trading Bot - Peach State Savings", page_icon="🤖", layout="wide")
init_db(); require_login(); require_pro("Alpaca Paper Trading Bot"); inject_css()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/1_expenses.py", label="Expenses", icon="📋")
st.sidebar.page_link("pages/2_income.py", label="Income", icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py", label="Business Tracker", icon="💼")
st.sidebar.page_link("pages/4_trends.py", label="Monthly Trends", icon="📈")
st.sidebar.page_link("pages/5_bank_import.py", label="Bank Import", icon="🏦")
st.sidebar.page_link("pages/6_receipts.py", label="Receipts & HSA", icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py", label="AI Insights", icon="🤖")
st.sidebar.page_link("pages/8_goals.py", label="Financial Goals", icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py", label="Net Worth", icon="💎")
st.sidebar.page_link("pages/10_rsu_espp.py", label="RSU/ESPP Advisor", icon="📈")
st.sidebar.page_link("pages/11_portfolio.py", label="Portfolio Analysis", icon="🗂️")
st.sidebar.page_link("pages/12_market_news.py", label="Market News", icon="📰")
st.sidebar.page_link("pages/13_backtesting.py", label="Strategy Backtest", icon="🔬")
st.sidebar.page_link("pages/14_trading_bot.py", label="Paper Trading Bot", icon="🤖")
st.sidebar.page_link("pages/0_pricing.py", label="Upgrade to Pro", icon="⭐")
render_sidebar_user_widget()

_ck = os.environ.get("ANTHROPIC_API_KEY", "")
_ak = os.environ.get("ALPACA_API_KEY", "")
_as = os.environ.get("ALPACA_SECRET_KEY", "")
_oci = os.environ.get("ALPACA_CLIENT_ID", "")
_ocs = os.environ.get("ALPACA_CLIENT_SECRET", "")

if "api_key" not in st.session_state:
    if _ck: st.session_state["api_key"] = _ck
    else:
        k = get_setting("anthropic_api_key", "")
        if k: st.session_state["api_key"] = k
if "alpaca_key" not in st.session_state:
    k = _ak or get_setting("alpaca_api_key", "")
    if k: st.session_state["alpaca_key"] = k
if "alpaca_secret" not in st.session_state:
    s = _as or get_setting("alpaca_secret_key", "")
    if s: st.session_state["alpaca_secret"] = s
if "alpaca_client_id" not in st.session_state:
    ci = _oci or get_setting("alpaca_client_id", "")
    if ci: st.session_state["alpaca_client_id"] = ci
if "alpaca_client_secret" not in st.session_state:
    cs = _ocs or get_setting("alpaca_client_secret", "")
    if cs: st.session_state["alpaca_client_secret"] = cs
# OAuth2 bearer token (fetched on demand, not persisted to DB)
if "alpaca_oauth_token" not in st.session_state:
    st.session_state["alpaca_oauth_token"] = ""

api_key = st.session_state.get("api_key", "")
alpaca_key = st.session_state.get("alpaca_key", "")
alpaca_secret = st.session_state.get("alpaca_secret", "")
alpaca_client_id = st.session_state.get("alpaca_client_id", "")
alpaca_client_secret = st.session_state.get("alpaca_client_secret", "")
alpaca_oauth_token = st.session_state.get("alpaca_oauth_token", "")
BASE = "https://paper-api.alpaca.markets"

# ── Auth mode: prefer OAuth2 bearer if token present, else fall back to API keys ──
def _auth_headers() -> dict:
    tok = st.session_state.get("alpaca_oauth_token", "")
    if tok:
        return {"Authorization": f"Bearer {tok}"}
    return {"APCA-API-KEY-ID": alpaca_key, "APCA-API-SECRET-KEY": alpaca_secret}

def _has_auth() -> bool:
    return bool(st.session_state.get("alpaca_oauth_token")) or bool(alpaca_key and alpaca_secret)

st.title("🤖 Alpaca Paper Trading Bot")
st.caption("Connect to Alpaca paper trading, run momentum strategies with fake money, and review performance.")
st.warning("⚠️ Paper trading only. This page connects to Alpaca paper trading sandbox. No real money is used.")

with st.expander("🚀 Setup Guide (5 minutes)", expanded=not _has_auth()):
    setup_tab_keys, setup_tab_oauth = st.tabs(["🔑 API Key / Secret", "🔐 OAuth2 Client Credentials"])

    with setup_tab_keys:
        st.markdown(
            "**Option A — Direct API Keys (simplest for paper trading)**\n\n"
            "1. Sign up free at [alpaca.markets](https://alpaca.markets) (no credit card needed).\n"
            "2. Go to **Paper Trading → API Keys → Generate New Key**.\n"
            "3. Paste your Key ID and Secret below, then click Save."
        )
        c1, c2 = st.columns(2)
        with c1:
            ak_in = st.text_input("Alpaca API Key ID", type="password", value=alpaca_key, placeholder="PKTEST...", key="ak_input")
        with c2:
            as_in = st.text_input("Alpaca Secret Key", type="password", value=alpaca_secret, placeholder="...", key="as_input")
        if st.button("💾 Save API Keys", type="primary", key="save_alpaca"):
            if ak_in.strip() and as_in.strip():
                st.session_state["alpaca_key"] = ak_in.strip()
                st.session_state["alpaca_secret"] = as_in.strip()
                # Clear any OAuth token so key-based auth takes over
                st.session_state["alpaca_oauth_token"] = ""
                set_setting("alpaca_api_key", ak_in.strip())
                set_setting("alpaca_secret_key", as_in.strip())
                alpaca_key = ak_in.strip()
                alpaca_secret = as_in.strip()
                st.success("✅ API keys saved!")
                st.rerun()
            else:
                st.warning("Both fields are required.")

    with setup_tab_oauth:
        st.markdown(
            "**Option B — OAuth2 Client Credentials (Broker API)**\n\n"
            "Use this if you have an Alpaca Broker API app with a `client_id` and `client_secret`.\n"
            "Tokens are fetched via `POST https://authx.alpaca.markets/v1/oauth2/token` "
            "and used as `Authorization: Bearer <token>` on all requests."
        )
        oc1, oc2 = st.columns(2)
        with oc1:
            ci_in = st.text_input("Client ID", type="password", value=alpaca_client_id,
                                  placeholder="20–32 character client ID", key="ci_input")
        with oc2:
            cs_in = st.text_input("Client Secret", type="password", value=alpaca_client_secret,
                                  placeholder="Client secret (≤128 chars)", key="cs_input")
        col_save, col_fetch = st.columns(2)
        with col_save:
            if st.button("💾 Save OAuth2 Credentials", key="save_oauth"):
                if ci_in.strip() and cs_in.strip():
                    st.session_state["alpaca_client_id"] = ci_in.strip()
                    st.session_state["alpaca_client_secret"] = cs_in.strip()
                    set_setting("alpaca_client_id", ci_in.strip())
                    set_setting("alpaca_client_secret", cs_in.strip())
                    alpaca_client_id = ci_in.strip()
                    alpaca_client_secret = cs_in.strip()
                    st.success("✅ OAuth2 credentials saved.")
                else:
                    st.warning("Both Client ID and Client Secret are required.")
        with col_fetch:
            if st.button("🔑 Fetch Token Now", type="primary", key="fetch_token"):
                cid = ci_in.strip() or alpaca_client_id
                csc = cs_in.strip() or alpaca_client_secret
                if not cid or not csc:
                    st.error("Save your Client ID and Secret first.")
                else:
                    with st.spinner("Requesting OAuth2 token from Alpaca..."):
                        tok, err = _get_oauth_token(cid, csc)
                    if tok:
                        st.session_state["alpaca_oauth_token"] = tok
                        alpaca_oauth_token = tok
                        st.success("✅ OAuth2 token obtained! All API calls will now use Bearer auth.")
                        st.rerun()
                    else:
                        st.error(f"Token request failed: {err}")

        if alpaca_oauth_token:
            st.info(f"🟢 Active OAuth2 token: `{alpaca_oauth_token[:12]}...` (session only — not stored to DB)")
            if st.button("🗑️ Clear Token", key="clear_token"):
                st.session_state["alpaca_oauth_token"] = ""
                alpaca_oauth_token = ""
                st.rerun()


def ag(ep):
    if not _has_auth(): return None
    try:
        r = requests.get(f"{BASE}{ep}", headers=_auth_headers(), timeout=10)
        _persist_request_id(r)
        return r.json() if r.status_code == 200 else None
    except: return None


def ap(ep, payload):
    if not _has_auth(): return None
    try:
        r = requests.post(f"{BASE}{ep}", json=payload, headers=_auth_headers(), timeout=10)
        _persist_request_id(r)
        return r.json()
    except Exception as e: return {"error": str(e)}


def ad(ep):
    if not _has_auth(): return False
    try:
        r = requests.delete(f"{BASE}{ep}", headers=_auth_headers(), timeout=10)
        _persist_request_id(r)
        return r.status_code in (200, 204)
    except: return False


if not _has_auth():
    st.info("👆 Add your Alpaca credentials above to get started.")
    st.stop()

t1, t2, t3, t4, t5, t6 = st.tabs(["💼 Account", "📊 Positions", "📋 Orders", "🤖 Run Strategy", "🧠 AI Analysis", "🔑 Auth & Debug"])

with t1:
    st.subheader("💼 Paper Trading Account")
    if st.button("🔄 Refresh Account", key="ref_acct"):
        st.session_state.pop("alpaca_account", None)
    if "alpaca_account" not in st.session_state:
        with st.spinner("Connecting to Alpaca..."):
            st.session_state["alpaca_account"] = ag("/v2/account")
    acct = st.session_state["alpaca_account"]
    if acct and "error" not in str(acct):
        eq = float(acct.get("equity", 0))
        ca = float(acct.get("cash", 0))
        bp = float(acct.get("buying_power", 0))
        pv = float(acct.get("portfolio_value", 0))
        le = float(acct.get("last_equity", eq))
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("💼 Portfolio Value", f"${pv:,.2f}")
        a2.metric("💵 Cash", f"${ca:,.2f}")
        a3.metric("⚡ Buying Power", f"${bp:,.2f}")
        a4.metric("📈 Day P&L", f"${eq - le:+,.2f}", delta_color="normal" if eq >= le else "inverse")
        st.markdown("---")
        st.markdown(f"**Account Status:** `{acct.get('status', 'unknown')}`")
        st.caption("This is a paper trading account — all values are simulated.")
    else:
        st.error("Could not connect to Alpaca. Check your API keys.")
        if acct: st.json(acct)

with t2:
    st.subheader("📊 Open Positions")
    if st.button("🔄 Refresh Positions", key="ref_pos"):
        st.session_state.pop("alpaca_positions", None)
    if "alpaca_positions" not in st.session_state:
        with st.spinner("Loading positions..."):
            st.session_state["alpaca_positions"] = ag("/v2/positions") or []
    positions = st.session_state["alpaca_positions"]
    if not positions:
        st.info("📭 No open positions. Run a strategy to place paper trades.")
    else:
        rows = [{"Symbol": p.get("symbol", ""), "Qty": float(p.get("qty", 0)),
                 "Avg Entry": float(p.get("avg_entry_price", 0)), "Current": float(p.get("current_price", 0)),
                 "Mkt Value": float(p.get("market_value", 0)), "Unreal P&L": float(p.get("unrealized_pl", 0)),
                 "P&L%": float(p.get("unrealized_plpc", 0)) * 100} for p in positions]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        total_pnl = sum(float(p.get("unrealized_pl", 0)) for p in positions)
        st.metric("Total Unrealized P&L", f"${total_pnl:+,.2f}", delta_color="normal" if total_pnl >= 0 else "inverse")
        if st.button("🗑️ Close All Positions", type="secondary", key="close_all"):
            if ad("/v2/positions"):
                st.success("All positions closed.")
                st.session_state.pop("alpaca_positions", None)
                st.rerun()

with t3:
    st.subheader("📋 Recent Orders")
    if st.button("🔄 Refresh Orders", key="ref_ord"):
        st.session_state.pop("alpaca_orders", None)
    if "alpaca_orders" not in st.session_state:
        with st.spinner("Loading orders..."):
            st.session_state["alpaca_orders"] = ag("/v2/orders?status=all&limit=50") or []
    orders = st.session_state["alpaca_orders"]
    if not orders:
        st.info("📭 No orders yet.")
    else:
        rows = [{"Symbol": o.get("symbol", ""), "Side": o.get("side", "").upper(), "Type": o.get("type", ""),
                 "Qty": float(o.get("qty", 0) or 0), "Filled": float(o.get("filled_qty", 0) or 0),
                 "Status": o.get("status", ""), "Submitted": str(o.get("submitted_at", ""))[:16]} for o in orders]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("---")
    st.subheader("📝 Place Manual Order")
    c1, c2, c3, c4 = st.columns(4)
    with c1: mt = st.text_input("Symbol", value="SPY", key="mo_t").upper()
    with c2: ms = st.selectbox("Side", ["buy", "sell"], key="mo_s")
    with c3: mq = st.number_input("Qty", min_value=1, value=1, key="mo_q")
    with c4: mty = st.selectbox("Type", ["market", "limit"], key="mo_ty")
    mlp = None
    if mty == "limit":
        mlp = st.number_input("Limit Price", min_value=0.01, value=100.0, step=0.01, key="mo_lp")
    if st.button("📝 Place Paper Order", type="primary", key="place_order"):
        pl = {"symbol": mt, "qty": str(mq), "side": ms, "type": mty, "time_in_force": "day"}
        if mty == "limit" and mlp: pl["limit_price"] = str(mlp)
        res = ap("/v2/orders", pl)
        if res and "id" in res:
            st.success(f"✅ Order placed! ID: {res['id']} | Status: {res.get('status', 'submitted')}")
            st.session_state.pop("alpaca_orders", None)
        else:
            st.error(f"Order failed: {res}")

with t4:
    st.subheader("🤖 Run Automated Strategy")
    st.caption("Execute a strategy against your paper account using live price data.")
    try:
        import yfinance as yf
        yf_ok = True
    except ImportError:
        yf_ok = False
        st.warning("yfinance not installed. Run: pip install yfinance")
    strat = st.selectbox("Strategy", [
        "Momentum - Buy if price > 20-day high",
        "Mean Reversion - Buy RSI<35, Sell RSI>65",
        "SMA Crossover - Buy if 10d SMA > 30d SMA"
    ], key="bot_strat")
    s1, s2, s3 = st.columns(3)
    with s1: bt = st.text_input("Ticker", value="SPY", key="bot_t").upper()
    with s2: bq = st.number_input("Shares per trade", min_value=1, value=1, key="bot_q")
    with s3: dry = st.checkbox("Dry run (no orders)", value=True, key="bot_dry", help="Preview signals without placing orders")
    if st.button("▶️ Run Strategy Now", type="primary", key="run_strat", disabled=not yf_ok):
        with st.spinner(f"Fetching {bt} data and evaluating strategy..."):
            try:
                import numpy as np
                df = yf.download(bt, period="60d", interval="1d", progress=False)
                if df.empty:
                    st.error(f"No data for {bt}")
                else:
                    df = df[["Close"]].copy()
                    df.columns = ["Close"]
                    cl = df["Close"]
                    sig = None
                    reason = ""
                    if "Momentum" in strat:
                        h20 = cl.rolling(20).max().iloc[-2]
                        cur = float(cl.iloc[-1])
                        if cur > float(h20): sig = "buy"; reason = f"Price {cur:.2f} > 20d high {float(h20):.2f}"
                        else: reason = f"No signal - price {cur:.2f} below 20d high {float(h20):.2f}"
                    elif "RSI" in strat:
                        d = cl.diff()
                        g = d.clip(lower=0).rolling(14).mean()
                        l = (-d.clip(upper=0)).rolling(14).mean()
                        rs = g / l.replace(0, float("nan"))
                        rv = float((100 - (100 / (1 + rs))).iloc[-1])
                        if rv < 35: sig = "buy"; reason = f"RSI {rv:.1f} < 35 (oversold)"
                        elif rv > 65: sig = "sell"; reason = f"RSI {rv:.1f} > 65 (overbought)"
                        else: reason = f"No signal - RSI {rv:.1f} neutral"
                    elif "SMA" in strat:
                        s10 = float(cl.rolling(10).mean().iloc[-1])
                        s30 = float(cl.rolling(30).mean().iloc[-1])
                        if s10 > s30: sig = "buy"; reason = f"10d SMA {s10:.2f} > 30d SMA {s30:.2f}"
                        else: reason = f"No signal - 10d SMA {s10:.2f} < 30d SMA {s30:.2f}"
                    st.markdown(f"**Signal:** {'🟢 BUY' if sig == 'buy' else '🔴 SELL' if sig == 'sell' else '⚪ HOLD'}")
                    st.markdown(f"**Reason:** {reason}")
                    st.line_chart(df["Close"].tail(60), use_container_width=True)
                    if sig and not dry:
                        res = ap("/v2/orders", {"symbol": bt, "qty": str(bq), "side": sig, "type": "market", "time_in_force": "day"})
                        if res and "id" in res: st.success(f"✅ {sig.upper()} order placed! ID: {res['id']}")
                        else: st.error(f"Order failed: {res}")
                    elif sig and dry:
                        st.info(f"🔍 Dry run - would place {sig.upper()} order for {bq} shares of {bt}")
                    else:
                        st.info("No trade signal - holding.")
            except Exception as e:
                st.error(f"Strategy error: {e}")

with t5:
    st.subheader("🧠 AI Trading Performance Analysis")
    st.caption("Claude analyzes your paper trading performance and gives honest feedback.")
    if not api_key:
        st.warning("No Claude API key. Go to AI Insights to save it.")
    else:
        pos_d = st.session_state.get("alpaca_positions", [])
        ord_d = st.session_state.get("alpaca_orders", [])
        acct_d = st.session_state.get("alpaca_account", {})
        if not acct_d:
            st.info("Load account data in the Account tab first.")
        else:
            eq = float(acct_d.get("equity", 0))
            ca = float(acct_d.get("cash", 0))
            sv = 100000
            ctx = (f"Paper Trading Summary:\nStarting Capital: USD {sv:,.0f}\n"
                   f"Current Equity: USD {eq:,.2f}\nCash: USD {ca:,.2f}\n"
                   f"Total P&L: USD {eq - sv:+,.2f} ({(eq / sv - 1) * 100:+.2f}%)\n"
                   f"Open Positions: {len(pos_d)}\nTotal Orders: {len(ord_d)}")
            if pos_d:
                ctx += "\nPositions:\n"
                for p in pos_d[:10]:
                    ctx += f"  {p.get('symbol')} | {p.get('qty')} shares | P&L: USD {float(p.get('unrealized_pl', 0)):+,.2f}\n"
            if st.button("🧠 Analyze My Paper Trading Performance", type="primary", key="btn_ai_t"):
                prompt = ("Analyze this paper trading performance honestly. Cover: "
                          "1. Performance vs buy-and-hold SPY. "
                          "2. Position diversification. "
                          "3. Trading behavior patterns. "
                          "4. Is this worth pursuing with real money? "
                          "5. Top 3 improvements before going live. "
                          "Be direct. Most paper traders underperform buy-and-hold. No markdown, no dollar signs.")
                with st.spinner("Claude is reviewing your trading performance..."):
                    try:
                        client = anthropic.Anthropic(api_key=api_key)
                        msg = client.messages.create(
                            model="claude-opus-4-5", max_tokens=800,
                            messages=[{"role": "user", "content": f"You are a trading coach.\n\n{ctx}\n\n{prompt}"}]
                        )
                        st.text(msg.content[0].text)
                        usage = msg.usage
                        cost = (usage.input_tokens / 1e6 * 3.0) + (usage.output_tokens / 1e6 * 15.0)
                        st.caption(f"Cost: USD {cost:.4f} - {usage.input_tokens + usage.output_tokens:,} tokens")
                    except Exception as e:
                        st.error(f"Error: {e}")

with t6:
    st.subheader("🔑 Authentication Status")

    # ── Current auth mode ────────────────────────────────────────────────────
    tok = st.session_state.get("alpaca_oauth_token", "")
    if tok:
        st.success(f"🟢 **OAuth2 Bearer** — Active token: `{tok[:16]}...`")
        st.caption("All API calls use `Authorization: Bearer <token>`. Token is session-only and not stored to the database.")
        if st.button("🗑️ Revoke Token (clear from session)", key="t6_clear_tok"):
            st.session_state["alpaca_oauth_token"] = ""
            st.rerun()
    elif alpaca_key and alpaca_secret:
        st.success(f"🟡 **API Key / Secret** — Key: `{alpaca_key[:8]}...`")
        st.caption("All API calls use `APCA-API-KEY-ID` / `APCA-API-SECRET-KEY` headers.")
    else:
        st.error("❌ No authentication configured. Use the Setup Guide above.")

    st.markdown("---")

    # ── Re-fetch OAuth2 token ────────────────────────────────────────────────
    st.subheader("🔐 Re-fetch OAuth2 Token")
    st.caption("Use your saved Client ID & Secret to get a fresh bearer token at any time.")
    rf1, rf2 = st.columns(2)
    with rf1:
        rf_cid = st.text_input("Client ID", type="password",
                               value=st.session_state.get("alpaca_client_id", ""),
                               placeholder="Client ID", key="t6_cid")
    with rf2:
        rf_csc = st.text_input("Client Secret", type="password",
                               value=st.session_state.get("alpaca_client_secret", ""),
                               placeholder="Client Secret", key="t6_csc")
    if st.button("🔑 Request New Token", type="primary", key="t6_fetch"):
        cid = rf_cid.strip() or st.session_state.get("alpaca_client_id", "")
        csc = rf_csc.strip() or st.session_state.get("alpaca_client_secret", "")
        if not cid or not csc:
            st.error("Client ID and Client Secret are required.")
        else:
            with st.spinner("Contacting authx.alpaca.markets..."):
                new_tok, err = _get_oauth_token(cid, csc)
            if new_tok:
                st.session_state["alpaca_oauth_token"] = new_tok
                st.success(f"✅ New token obtained: `{new_tok[:16]}...`")
                st.rerun()
            else:
                st.error(f"Token request failed: {err}")

    st.markdown("---")

    # ── X-Request-ID log ─────────────────────────────────────────────────────
    st.subheader("📋 X-Request-ID Log")
    st.caption(
        "Every Alpaca API response includes an `X-Request-ID` header. "
        "These IDs are captured automatically and listed here. "
        "**Include the relevant Request ID in any Alpaca support ticket** to help them trace the call."
    )

    request_ids = st.session_state.get("alpaca_request_ids", [])
    if not request_ids:
        st.info("No request IDs captured yet. Make an API call (e.g. refresh Account) to see IDs here.")
    else:
        rid_rows = [{"Time": r["ts"], "Status": r["status"],
                     "Endpoint": r["url"].replace("https://paper-api.alpaca.markets", "").replace("https://authx.alpaca.markets", "[auth]"),
                     "X-Request-ID": r["id"]} for r in request_ids]
        st.dataframe(pd.DataFrame(rid_rows), use_container_width=True, hide_index=True)

        # Copy-friendly text block of just the IDs
        with st.expander("📋 Copy raw Request IDs"):
            st.code("\n".join(r["id"] for r in request_ids), language=None)

        if st.button("🗑️ Clear Request ID Log", key="clear_rids"):
            st.session_state["alpaca_request_ids"] = []
            st.rerun()

    st.markdown("---")
    st.caption(
        "💡 **Tip:** Request IDs cannot be queried via the Alpaca API — they are only available in the response header at call time. "
        "This log persists for your current browser session only."
    )


st.markdown("---")
st.caption("⚠️ Paper trading uses simulated money. Past paper performance does not predict live trading results. Never risk money you cannot afford to lose.")
