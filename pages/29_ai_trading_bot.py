import streamlit as st
import sys
import os
import sqlite3
import json
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_conn, init_db, execute as db_exec
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="AI Trading Bot", page_icon="🤖", layout="wide")
init_db()
inject_css()
require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
st.sidebar.page_link("pages/29_ai_trading_bot.py",      label="🤖 AI Trading Bot", icon="📈")
render_sidebar_user_widget()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "budget.db")


def _get_setting(key, default=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        row = db_exec(conn, "SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row and row[0] else default
    except Exception:
        return default


def _set_setting(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        db_exec(conn, 
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)",
            (key, value)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _get_bot_config(key, default=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        row = db_exec(conn, "SELECT value FROM bot_config WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row and row[0] else default
    except Exception:
        return default


def _set_bot_config(key, value):
    try:
        conn = sqlite3.connect(DB_PATH)
        db_exec(conn, 
            "INSERT OR REPLACE INTO bot_config (key, value, updated_at) VALUES (?,?,?)",
            (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _ensure_bot_tables():
    try:
        conn = sqlite3.connect(DB_PATH)
        db_exec(conn,
            "CREATE TABLE IF NOT EXISTS bot_decisions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "timestamp TEXT NOT NULL, ticker TEXT NOT NULL,"
            "strategy TEXT NOT NULL, signal TEXT NOT NULL,"
            "reason TEXT, action_taken TEXT DEFAULT 'pending',"
            "order_id TEXT, price REAL, quantity REAL,"
            "option_symbol TEXT, option_expiry TEXT,"
            "option_strike REAL, option_type TEXT,"
            "premium REAL, market_mode TEXT DEFAULT 'paper', pnl REAL)"
        )
        db_exec(conn,
            "CREATE TABLE IF NOT EXISTS bot_positions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "opened_at TEXT, ticker TEXT, position_type TEXT,"
            "quantity REAL, entry_price REAL, current_price REAL,"
            "stop_loss REAL, take_profit REAL, status TEXT DEFAULT 'open',"
            "closed_at TEXT, pnl REAL, option_symbol TEXT,"
            "option_expiry TEXT, option_strike REAL, option_type TEXT,"
            "market_mode TEXT DEFAULT 'paper')"
        )
        db_exec(conn,
            "CREATE TABLE IF NOT EXISTS bot_config ("
            "key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
        )
        db_exec(conn,
            "CREATE TABLE IF NOT EXISTS bot_daily_summary ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "trade_date TEXT UNIQUE, trades INTEGER DEFAULT 0,"
            "winners INTEGER DEFAULT 0, losers INTEGER DEFAULT 0,"
            "gross_pnl REAL DEFAULT 0, net_pnl REAL DEFAULT 0, summary_ai TEXT)"
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _load_decisions(limit=50, mode_filter=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        q = "SELECT * FROM bot_decisions"
        params = []
        if mode_filter:
            q += " WHERE market_mode=?"
            params.append(mode_filter)
        q += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = db_exec(conn, q, params).fetchall()
        conn.close()
        return [dict(zip([d[0] for d in db_exec(conn, "PRAGMA table_info(bot_decisions)").description if False] +
                         ["id","timestamp","ticker","strategy","signal","reason","action_taken",
                          "order_id","price","quantity","option_symbol","option_expiry",
                          "option_strike","option_type","premium","market_mode","pnl"], row))
                for row in rows]
    except Exception:
        return []


def _load_decisions_v2(limit=50, mode_filter=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM bot_decisions"
        params = []
        if mode_filter:
            q += " WHERE market_mode=?"
            params.append(mode_filter)
        q += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = db_exec(conn, q, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _load_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        total = db_exec(conn, "SELECT COUNT(*) FROM bot_decisions WHERE action_taken='executed'").fetchone()[0]
        executed = db_exec(conn, "SELECT COUNT(*) FROM bot_decisions WHERE action_taken IN ('executed','dry_run')").fetchone()[0]
        by_signal = db_exec(conn, 
            "SELECT signal, COUNT(*) as cnt FROM bot_decisions WHERE action_taken IN ('executed','dry_run') "
            "GROUP BY signal ORDER BY cnt DESC"
        ).fetchall()
        by_ticker = db_exec(conn, 
            "SELECT ticker, COUNT(*) as cnt FROM bot_decisions WHERE action_taken IN ('executed','dry_run') "
            "GROUP BY ticker ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        conn.close()
        return {
            "total_executed": total,
            "total_logged": executed,
            "by_signal": [dict(r) for r in by_signal],
            "by_ticker": [dict(r) for r in by_ticker],
        }
    except Exception:
        return {"total_executed": 0, "total_logged": 0, "by_signal": [], "by_ticker": []}


_ensure_bot_tables()

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🤖 AI Trading Bot Monitor")
st.caption("Peach State Savings — Automated Trading via Alpaca | Claude AI Strategy")

# Status banner
has_alpaca = bool(_get_setting("alpaca_api_key"))
has_claude = bool(_get_setting("anthropic_api_key"))
market_mode = _get_bot_config("market_mode", "paper")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Mode", market_mode.upper(),
              delta="SAFE" if market_mode == "paper" else "LIVE MONEY")
with col2:
    st.metric("Alpaca Keys", "✅ SET" if has_alpaca else "❌ Missing")
with col3:
    st.metric("Claude AI", "✅ SET" if has_claude else "❌ Missing")
with col4:
    stats = _load_stats()
    st.metric("Total Trades Logged", stats["total_logged"])

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_dash, tab_config, tab_log, tab_deploy = st.tabs(
    ["📊 Dashboard", "⚙️ Configuration", "📋 Decision Log", "🚀 Deploy to Homelab"]
)

# ── Tab 1: Dashboard ──────────────────────────────────────────────────────────
with tab_dash:
    st.subheader("Bot Activity Overview")

    if stats["total_logged"] == 0:
        st.info("No bot decisions logged yet. Run the bot to see activity here.")
        st.code(
            "# Test run (paper mode, no orders placed)\n"
            "cd /path/to/darrian-budget\n"
            "source venv/bin/activate\n"
            "python3 bot/trading_bot.py --dry-run",
            language="bash"
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Signals by Type**")
            for item in stats["by_signal"]:
                icon = {"buy_stock": "📈", "sell_stock": "📉", "sell_csp": "💰",
                        "sell_cc": "🎯", "buy_call": "🚀", "buy_put": "🪂",
                        "hold": "⏸"}.get(item["signal"], "•")
                st.metric(f"{icon} {item['signal']}", item["cnt"])
        with c2:
            st.markdown("**Top Tickers**")
            for item in stats["by_ticker"]:
                st.metric(item["ticker"], f"{item['cnt']} signals")

    # Recent decisions
    st.markdown("---")
    st.subheader("Recent Decisions (Last 10)")
    recent = _load_decisions_v2(limit=10)
    if recent:
        for d in recent:
            sig = d.get("signal", "")
            action = d.get("action_taken", "")
            ticker = d.get("ticker", "")
            ts = d.get("timestamp", "")
            reason = d.get("reason", "")
            price = d.get("price")
            opt_sym = d.get("option_symbol")

            color = {"buy_stock": "green", "sell_stock": "red",
                     "sell_csp": "blue", "sell_cc": "blue",
                     "buy_call": "green", "buy_put": "red",
                     "hold": "gray"}.get(sig, "gray")
            icon = {"executed": "✅", "dry_run": "🔵", "skipped": "⏭", "failed": "❌"}.get(action, "•")

            with st.expander(f"{icon} {ts[:16]} | {ticker} | {sig.upper()} | {action}"):
                cols = st.columns(3)
                with cols[0]:
                    if price:
                        st.metric("Price", f"${price:.2f}")
                with cols[1]:
                    if opt_sym:
                        st.text(f"Option: {opt_sym}")
                        st.caption(f"Strike: ${d.get('option_strike', 0):.0f} | {d.get('option_type','').upper()} exp {d.get('option_expiry','')}")
                with cols[2]:
                    st.text(f"Strategy: {d.get('strategy','')}")
                if reason:
                    st.caption(f"Reason: {reason[:300]}")
    else:
        st.info("No decisions logged yet.")

# ── Tab 2: Configuration ──────────────────────────────────────────────────────
with tab_config:
    st.subheader("Bot Configuration")

    with st.form("bot_config_form"):
        st.markdown("**Alpaca API Keys**")
        alpaca_key = st.text_input("Alpaca API Key",
                                    value=_get_setting("alpaca_api_key", ""),
                                    type="password",
                                    placeholder="pk_...")
        alpaca_secret = st.text_input("Alpaca Secret Key",
                                       value=_get_setting("alpaca_secret_key", ""),
                                       type="password",
                                       placeholder="sk_...")

        st.markdown("**Trading Settings**")
        mode = st.selectbox("Trading Mode",
                             options=["paper", "live"],
                             index=0 if _get_bot_config("market_mode", "paper") == "paper" else 1,
                             help="Paper = simulated trades. Live = real money!")
        watchlist = st.text_input("Watchlist (comma-separated)",
                                   value=_get_bot_config("watchlist", "AAPL,MSFT,NVDA,QQQ,SPY"),
                                   placeholder="AAPL,MSFT,NVDA,QQQ,SPY")
        enable_options = st.checkbox("Enable Options Trading (Wheel Strategy)",
                                      value=_get_bot_config("enable_options", "true") == "true")
        enable_stocks = st.checkbox("Enable Stock Trading",
                                     value=_get_bot_config("enable_stocks", "true") == "true")

        st.markdown("**Risk Controls**")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            max_pos = st.slider("Max position size (%)", 1, 10,
                                 int(_get_bot_config("max_position_pct", "5")),
                                 help="% of portfolio per single trade")
        with col_r2:
            max_loss = st.slider("Daily circuit breaker (%)", 1, 10,
                                  int(_get_bot_config("max_daily_loss_pct", "2")),
                                  help="Stop trading if down this % today")

        if mode == "live":
            st.error("⚠️ LIVE MODE will place REAL orders with REAL money. "
                     "Only enable after 30+ days of paper trading.")
            confirm_live = st.checkbox("I understand this uses real money")
        else:
            confirm_live = True

        save = st.form_submit_button("💾 Save Configuration")
        if save:
            if mode == "live" and not confirm_live:
                st.error("Please confirm you understand live mode uses real money.")
            else:
                if alpaca_key: _set_setting("alpaca_api_key", alpaca_key)
                if alpaca_secret: _set_setting("alpaca_secret_key", alpaca_secret)
                _set_bot_config("market_mode", mode)
                _set_bot_config("watchlist", watchlist)
                _set_bot_config("enable_options", "true" if enable_options else "false")
                _set_bot_config("enable_stocks", "true" if enable_stocks else "false")
                _set_bot_config("max_position_pct", str(max_pos))
                _set_bot_config("max_daily_loss_pct", str(max_loss))
                st.success("✅ Configuration saved!")
                st.rerun()

    st.markdown("---")
    st.markdown("**Manual Trigger (Local Machine)**")
    st.caption("These commands run the bot on your local machine for testing:")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        if st.button("🔵 Dry Run (No Orders)"):
            import subprocess
            venv_python = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "bin", "python3")
            bot_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot", "trading_bot.py")
            result = subprocess.run(
                [venv_python, bot_script, "--dry-run"],
                capture_output=True, text=True, timeout=120
            )
            st.code(result.stdout[-2000:] if result.stdout else result.stderr[-2000:], language="text")
    with col_m2:
        if st.button("📄 Paper Trade"):
            import subprocess
            venv_python = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "bin", "python3")
            bot_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot", "trading_bot.py")
            result = subprocess.run(
                [venv_python, bot_script],
                capture_output=True, text=True, timeout=120
            )
            st.code(result.stdout[-2000:] if result.stdout else result.stderr[-2000:], language="text")
    with col_m3:
        st.warning("Live Trade button is disabled in UI for safety. Use CLI --live flag.")

# ── Tab 3: Decision Log ───────────────────────────────────────────────────────
with tab_log:
    st.subheader("Full Decision Log")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        mode_filter = st.selectbox("Filter by Mode", ["all", "paper", "live"])
    with col_f2:
        limit = st.slider("Show last N decisions", 10, 200, 50)

    decisions = _load_decisions_v2(
        limit=limit,
        mode_filter=None if mode_filter == "all" else mode_filter
    )

    if decisions:
        import pandas as pd
        df = pd.DataFrame(decisions)
        display_cols = ["timestamp", "ticker", "strategy", "signal", "action_taken",
                        "price", "option_symbol", "option_strike", "market_mode"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], use_container_width=True)

        csv = df.to_csv(index=False)
        st.download_button("📥 Export CSV", csv, "bot_decisions.csv", "text/csv")
    else:
        st.info("No decisions found.")

# ── Tab 4: Deploy ─────────────────────────────────────────────────────────────
with tab_deploy:
    st.subheader("Deploy to CT100 Homelab")
    st.markdown("""
    The bot runs 24/7 on your homelab as a systemd timer.
    It fires every 30 minutes on weekdays and the script itself checks
    if the market is open before doing anything.
    """)

    st.markdown("**Step 1: Copy project to homelab**")
    st.code(
        "rsync -av --exclude='.git' --exclude='venv' --exclude='data/' \\\n"
        "  /Users/darrianbelcher/Downloads/darrian-budget/ \\\n"
        "  root@100.95.125.112:/opt/darrian-budget/",
        language="bash"
    )

    st.markdown("**Step 2: Set up on CT100**")
    st.code(
        "ssh root@100.95.125.112\n"
        "cd /opt/darrian-budget\n"
        "python3 -m venv venv\n"
        "source venv/bin/activate\n"
        "pip install -r requirements.txt\n\n"
        "# Test dry run first\n"
        "python3 bot/trading_bot.py --dry-run",
        language="bash"
    )

    st.markdown("**Step 3: Install systemd timer**")
    st.code(
        "cp bot/trading_bot.service /etc/systemd/system/\n"
        "cp bot/trading_bot.timer   /etc/systemd/system/\n"
        "systemctl daemon-reload\n"
        "systemctl enable --now trading_bot.timer\n\n"
        "# Verify\n"
        "systemctl status trading_bot.timer\n"
        "journalctl -u trading_bot.service -f",
        language="bash"
    )

    st.markdown("**Step 4: Set Alpaca API keys on CT100**")
    st.code(
        "sqlite3 /opt/darrian-budget/data/budget.db \\\n"
        '  "INSERT OR REPLACE INTO app_settings VALUES (\'alpaca_api_key\', \'YOUR_KEY\', datetime(\'now\'));\n'
        "   INSERT OR REPLACE INTO app_settings VALUES ('alpaca_secret_key', 'YOUR_SECRET', datetime('now'));\"",
        language="bash"
    )

    st.warning("**Paper trade for 30+ days before enabling live mode.** "
               "Switch to live by editing the service file to add `--live` flag.")

    st.markdown("**View live logs from anywhere (Tailscale):**")
    st.code(
        "ssh root@100.95.125.112 'tail -f /var/log/trading_bot.log'",
        language="bash"
    )
