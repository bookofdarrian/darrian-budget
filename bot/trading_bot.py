import sys, os, json, sqlite3, argparse, time, logging
from datetime import datetime, date, timedelta
import pytz, requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ET = pytz.timezone("America/New_York")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "budget.db")
PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL  = "https://api.alpaca.markets"
DEFAULT_WATCHLIST = ["AAPL", "MSFT", "NVDA", "QQQ", "SPY"]
MAX_POS_PCT   = 0.05
MAX_DAY_LOSS  = 0.02
MIN_IV_RANK   = 30

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("trading_bot")


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables():
    conn = _get_db()
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS bot_decisions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "timestamp TEXT NOT NULL, ticker TEXT NOT NULL,"
        "strategy TEXT NOT NULL, signal TEXT NOT NULL,"
        "reason TEXT, action_taken TEXT DEFAULT 'pending',"
        "order_id TEXT, price REAL, quantity REAL,"
        "option_symbol TEXT, option_expiry TEXT,"
        "option_strike REAL, option_type TEXT,"
        "premium REAL, market_mode TEXT DEFAULT 'paper', pnl REAL);"
        "CREATE TABLE IF NOT EXISTS bot_positions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "opened_at TEXT, ticker TEXT, position_type TEXT,"
        "quantity REAL, entry_price REAL, current_price REAL,"
        "stop_loss REAL, take_profit REAL, status TEXT DEFAULT 'open',"
        "closed_at TEXT, pnl REAL, option_symbol TEXT,"
        "option_expiry TEXT, option_strike REAL, option_type TEXT,"
        "market_mode TEXT DEFAULT 'paper');"
        "CREATE TABLE IF NOT EXISTS bot_config ("
        "key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);"
        "CREATE TABLE IF NOT EXISTS bot_daily_summary ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "trade_date TEXT UNIQUE, trades INTEGER DEFAULT 0,"
        "winners INTEGER DEFAULT 0, losers INTEGER DEFAULT 0,"
        "gross_pnl REAL DEFAULT 0, net_pnl REAL DEFAULT 0, summary_ai TEXT);"
    )
    conn.commit()
    conn.close()


def _get_setting(key, default=""):
    try:
        conn = _get_db()
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row and row[0] else default
    except Exception:
        return default


def _get_bot_config(key, default=""):
    try:
        conn = _get_db()
        row = conn.execute("SELECT value FROM bot_config WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row and row[0] else default
    except Exception:
        return default


def _log_decision(ticker, strategy, signal, reason, action_taken,
                  price=None, qty=None, order_id=None, option_symbol=None,
                  option_expiry=None, option_strike=None, option_type=None,
                  premium=None, mode="paper"):
    try:
        conn = _get_db()
        conn.execute(
            "INSERT INTO bot_decisions (timestamp,ticker,strategy,signal,reason,"
            "action_taken,order_id,price,quantity,option_symbol,option_expiry,"
            "option_strike,option_type,premium,market_mode) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S"),
             ticker, strategy, signal, reason, action_taken, order_id,
             price, qty, option_symbol, option_expiry, option_strike,
             option_type, premium, mode)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"Failed to log decision: {e}")


def _is_market_open():
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    ot = now.replace(hour=9, minute=30, second=0, microsecond=0)
    ct = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return ot <= now < ct


class AlpacaClient:
    def __init__(self, api_key, secret_key, paper=True):
        self.base = PAPER_URL if paper else LIVE_URL
        self.hdrs = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def get(self, ep):
        try:
            r = requests.get(f"{self.base}{ep}", headers=self.hdrs, timeout=15)
            return r.json() if r.ok else None
        except Exception as e:
            log.warning(f"GET {ep}: {e}")
            return None

    def post(self, ep, payload):
        try:
            r = requests.post(f"{self.base}{ep}", json=payload, headers=self.hdrs, timeout=15)
            return r.json()
        except Exception as e:
            log.warning(f"POST {ep}: {e}")
            return None

    def account(self): return self.get("/v2/account")
    def positions(self): return self.get("/v2/positions") or []

    def place_order(self, symbol, qty, side, otype="market", lp=None, ac="us_equity"):
        p = {"symbol": symbol, "qty": str(qty), "side": side,
             "type": otype, "time_in_force": "day", "asset_class": ac}
        if otype == "limit" and lp:
            p["limit_price"] = str(round(lp, 2))
        return self.post("/v2/orders", p)


def _calc_indicators(ticker):
    try:
        import yfinance as yf
        df = yf.download(ticker, period="65d", interval="1d", progress=False)
        if df.empty or len(df) < 30:
            return None
        cl = df["Close"].squeeze()
        cur = float(cl.iloc[-1])
        delta = cl.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        sma10 = float(cl.rolling(10).mean().iloc[-1])
        sma30 = float(cl.rolling(30).mean().iloc[-1])
        high20 = float(cl.rolling(20).max().iloc[-2])
        rets = cl.pct_change().dropna()
        hv = float(rets.rolling(20).std().iloc[-1] * (252 ** 0.5) * 100)
        hv_lo = float(rets.rolling(20).std().rolling(252).min().iloc[-1] * (252 ** 0.5) * 100)
        hv_hi = float(rets.rolling(20).std().rolling(252).max().iloc[-1] * (252 ** 0.5) * 100)
        ivr = (hv - hv_lo) / (hv_hi - hv_lo) * 100 if hv_hi > hv_lo else 0.0
        vol = float(df["Volume"].iloc[-1])
        vavg = float(df["Volume"].rolling(20).mean().iloc[-1])
        return {
            "ticker": ticker, "price": cur, "rsi": round(rsi, 1),
            "sma10": round(sma10, 2), "sma30": round(sma30, 2),
            "high20": round(high20, 2), "hv20": round(hv, 1),
            "iv_rank": round(ivr, 1),
            "vol_ratio": round(vol / vavg if vavg > 0 else 1.0, 2),
        }
    except Exception as e:
        log.warning(f"Indicators {ticker}: {e}")
        return None


def _tech_signal(ind):
    sigs = []
    if ind["rsi"] < 35: sigs.append(("buy", f"RSI {ind['rsi']} oversold"))
    elif ind["rsi"] > 65: sigs.append(("sell", f"RSI {ind['rsi']} overbought"))
    if ind["sma10"] > ind["sma30"]: sigs.append(("buy", f"SMA10>{ind['sma30']:.0f}"))
    elif ind["sma10"] < ind["sma30"]: sigs.append(("sell", f"SMA10<{ind['sma30']:.0f}"))
    if ind["price"] > ind["high20"]: sigs.append(("buy", "Momentum above 20d high"))
    buys = [s for s in sigs if s[0] == "buy"]
    sells = [s for s in sigs if s[0] == "sell"]
    if len(buys) >= 2: return "buy", " | ".join(r for _, r in buys)
    if len(sells) >= 2: return "sell", " | ".join(r for _, r in sells)
    if buys and not sells: return "buy", buys[0][1]
    if sells and not buys: return "sell", sells[0][1]
    return "hold", "No clear signal"


def _next_expiry():
    today = date.today()
    nm = today.replace(day=1)
    if today.month == 12:
        nm = nm.replace(month=1, year=today.year + 1)
    else:
        nm = nm.replace(month=today.month + 1)
    d, n = nm, 0
    while n < 3:
        if d.weekday() == 4:
            n += 1
            if n < 3:
                d += timedelta(days=1)
        else:
            d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _ai_decision(ind, equity, positions, mode="paper"):
    api_key = _get_setting("anthropic_api_key", "")
    if not api_key:
        sig, reason = _tech_signal(ind)
        return {"signal": sig, "strategy": "technical", "reason": reason, "position_size_pct": 0.03}
    tech_sig, tech_reason = _tech_signal(ind)
    pos_str = "\n".join(
        f"  {p.get('symbol','?')} | {p.get('qty','?')} | P&L ${float(p.get('unrealized_pl', 0)):+.2f}"
        for p in positions[:8]
    ) or "  none"
    expiry = _next_expiry()
    prompt = (
        f"AI trading bot. Mode={mode.upper()}\n"
        f"Account equity=${equity:,.0f} max_pos={MAX_POS_PCT * 100:.0f}%\n"
        f"Positions:\n{pos_str}\n"
        f"{ind['ticker']}: price={ind['price']:.2f} rsi={ind['rsi']} "
        f"sma10={ind['sma10']:.0f} sma30={ind['sma30']:.0f} "
        f"20dh={ind['high20']:.0f} ivrank={ind['iv_rank']:.0f} vol={ind['vol_ratio']:.1f}x\n"
        f"tech={tech_sig.upper()}: {tech_reason}\n"
        f"Strategies: buy_stock sell_stock sell_csp sell_cc buy_call buy_put hold\n"
        f"Rules: ivrank>{MIN_IV_RANK}->sell premium; momentum+vol>1.5->buy; uncertain->hold\n"
        f'Respond ONLY JSON: {{"signal":"hold","strategy":"name","reason":"1 sentence",'
        f'"option_type":"put","option_strike_offset":-0.05,'
        f'"option_expiry":"{expiry}","position_size_pct":0.03,"confidence":0.6}}'
    )
    try:
        import anthropic, re
        msg = anthropic.Anthropic(api_key=api_key).messages.create(
            model="claude-opus-4-5", max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        res = json.loads(m.group(0)) if m else {}
        res.setdefault("signal", "hold")
        res.setdefault("strategy", "ai_decided")
        res.setdefault("reason", raw[:200])
        res.setdefault("position_size_pct", 0.03)
        return res
    except Exception as e:
        log.warning(f"Claude error: {e}")
        sig, reason = _tech_signal(ind)
        return {"signal": sig, "strategy": "fallback_tech",
                "reason": f"Claude unavailable. {reason}", "position_size_pct": 0.03}


def _occ(ticker, expiry, opt_type, strike):
    exp = expiry.replace("-", "")[2:]
    ot = "C" if opt_type == "call" else "P"
    return f"{ticker}{exp}{ot}{int(round(strike * 1000)):08d}"


def _exec_stock(client, ticker, side, price, equity, pct, dry_run):
    qty = max(1, int(equity * min(pct, MAX_POS_PCT) / price))
    log.info(f"  {side.upper()} {qty}x {ticker} @ ~${price:.2f}")
    if dry_run:
        return "DRY_RUN"
    res = client.place_order(ticker, qty, side)
    if res and "id" in res:
        log.info(f"  Order: {res['id']} ({res.get('status')})")
        return res["id"]
    log.warning(f"  Order failed: {res}")
    return None


def _exec_option(client, ticker, signal, dec, price, equity, dry_run):
    ot = dec.get("option_type", "put")
    exp = dec.get("option_expiry", _next_expiry())
    strike = round(price * (1 + float(dec.get("option_strike_offset", -0.05))) / 5) * 5
    sym = _occ(ticker, exp, ot, strike)
    side = "sell" if signal in ("sell_csp", "sell_cc") else "buy"
    log.info(f"  {side.upper()} 1x {sym} (strike=${strike}, exp={exp})")
    if dry_run:
        return "DRY_RUN"
    res = client.place_order(sym, 1, side, ac="us_option")
    if res and "id" in res:
        log.info(f"  Option order: {res['id']} ({res.get('status')})")
        return res["id"]
    log.warning(f"  Option failed: {res}")
    return None


def _monitor(client, dry_run, mode):
    for p in client.positions():
        pct = float(p.get("unrealized_plpc", 0)) * 100
        sym = p.get("symbol", "")
        qty = float(p.get("qty", 0))
        if pct >= 50:
            log.info(f"  TAKE PROFIT: {sym} +{pct:.1f}%")
            if not dry_run:
                client.place_order(sym, qty, "sell")
            _log_decision(sym, "monitor", "sell", f"Take profit +{pct:.1f}%", "executed", mode=mode)
        elif pct <= -8:
            log.info(f"  STOP LOSS: {sym} {pct:.1f}%")
            if not dry_run:
                client.place_order(sym, qty, "sell")
            _log_decision(sym, "monitor", "sell", f"Stop loss {pct:.1f}%", "executed", mode=mode)


def _circuit_breaker(client):
    a = client.account()
    if not a:
        return False
    eq = float(a.get("equity", 0))
    leq = float(a.get("last_equity", eq))
    pct = (eq - leq) / leq if leq > 0 else 0
    if pct <= -MAX_DAY_LOSS:
        log.warning(f"CIRCUIT BREAKER: day P&L={pct * 100:.2f}%")
        return True
    return False


def run(paper=True, dry_run=False):
    mode = "paper" if paper else "live"
    dry_str = "(DRY RUN)" if dry_run else ""
    log.info(f"Peach State Savings Trading Bot -- {mode.upper()} {dry_str}")
    _ensure_tables()

    if not _is_market_open():
        log.info(f"Market closed at {datetime.now(ET).strftime('%H:%M ET')}. Exiting.")
        return

    api_key = _get_setting("alpaca_api_key", "")
    secret = _get_setting("alpaca_secret_key", "")
    if not api_key or not secret:
        log.error("Alpaca keys not in DB. Set them via the app settings page.")
        return

    client = AlpacaClient(api_key, secret, paper=paper)
    acct = client.account()
    if not acct or "equity" not in acct:
        log.error("Cannot connect to Alpaca.")
        return

    equity = float(acct["equity"])
    log.info(f"Account equity: ${equity:,.2f}")

    if _circuit_breaker(client):
        return

    wl = _get_bot_config("watchlist", "")
    watchlist = [t.strip().upper() for t in wl.split(",") if t.strip()] or DEFAULT_WATCHLIST
    log.info(f"Watchlist: {watchlist}")

    positions = client.positions()
    _monitor(client, dry_run, mode)

    for ticker in watchlist:
        log.info(f"--- {ticker} ---")
        ind = _calc_indicators(ticker)
        if not ind:
            continue
        log.info(f"  price={ind['price']:.2f} rsi={ind['rsi']} ivrank={ind['iv_rank']:.0f}")
        dec = _ai_decision(ind, equity, positions, mode)
        signal = dec.get("signal", "hold")
        strategy = dec.get("strategy", "ai")
        reason = dec.get("reason", "")
        pct = float(dec.get("position_size_pct", 0.03))
        log.info(f"  Signal: {signal.upper()} | {strategy} | {reason[:100]}")

        if signal == "hold":
            _log_decision(ticker, strategy, signal, reason, "skipped", mode=mode)
            continue

        oid = osym = oexp = otype = ostr = None
        if signal in ("buy_stock", "sell_stock"):
            oid = _exec_stock(client, ticker,
                              "buy" if signal == "buy_stock" else "sell",
                              ind["price"], equity, pct, dry_run)
        elif signal in ("sell_csp", "sell_cc", "buy_call", "buy_put"):
            otype = dec.get("option_type", "put")
            ostr = round(ind["price"] * (1 + float(dec.get("option_strike_offset", -0.05))) / 5) * 5
            oexp = dec.get("option_expiry", _next_expiry())
            osym = _occ(ticker, oexp, otype, ostr)
            oid = _exec_option(client, ticker, signal, dec, ind["price"], equity, dry_run)

        act = "executed" if (oid and oid != "DRY_RUN") else ("dry_run" if dry_run else "failed")
        _log_decision(ticker, strategy, signal, reason, act,
                      price=ind["price"], order_id=oid,
                      option_symbol=osym, option_expiry=oexp,
                      option_strike=ostr, option_type=otype, mode=mode)
        time.sleep(0.5)

    log.info("Bot run complete.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Peach State Savings AI Trading Bot")
    ap.add_argument("--live", action="store_true", help="Live Alpaca account (REAL MONEY)")
    ap.add_argument("--dry-run", action="store_true", help="Log signals only, no orders")
    args = ap.parse_args()
    if args.live:
        print("WARNING: LIVE MODE -- real money! Ctrl+C in 5s to cancel...")
        time.sleep(5)
    run(paper=not args.live, dry_run=args.dry_run)
