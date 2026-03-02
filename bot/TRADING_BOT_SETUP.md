# AI Trading Bot — Homelab Setup Guide
## Peach State Savings | CT100 @ 100.95.125.112

### What This Bot Does
- Runs every 30 minutes on weekdays during market hours (9:30 AM – 4:00 PM ET)
- Fetches live price data (yfinance) for your watchlist
- Calculates RSI, SMA, Momentum, and IV Rank
- Asks Claude to pick the best trade (stocks or options)
- Executes via Alpaca API (paper mode by default)
- Logs every decision to the SQLite DB (visible in the app dashboard)

### Prerequisites

1. **Alpaca account** — Sign up at https://alpaca.markets
   - Paper trading is free and instant
   - Live trading requires identity verification
   
2. **Set API keys in the app** (Settings page or directly in DB):
   ```bash
   sqlite3 /opt/darrian-budget/data/budget.db \
     "INSERT OR REPLACE INTO app_settings VALUES ('alpaca_api_key', 'YOUR_KEY', datetime('now'));
      INSERT OR REPLACE INTO app_settings VALUES ('alpaca_secret_key', 'YOUR_SECRET', datetime('now'));"
   ```

3. **Options trading** — Enable in Alpaca dashboard under Account > Options Trading

### Install on CT100

```bash
# Copy files to homelab
rsync -av /path/to/darrian-budget/ root@100.95.125.112:/opt/darrian-budget/

# On CT100:
cd /opt/darrian-budget
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test run (paper, dry-run — safe)
python3 bot/trading_bot.py --dry-run

# Install systemd service
cp bot/trading_bot.service /etc/systemd/system/
cp bot/trading_bot.timer   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now trading_bot.timer

# Check status
systemctl status trading_bot.timer
journalctl -u trading_bot.service -f
```

### Switch to Live Mode

Edit the timer to pass `--live` flag:
```ini
ExecStart=/opt/darrian-budget/venv/bin/python3 /opt/darrian-budget/bot/trading_bot.py --live
```

**WARNING**: Only do this after 30+ days of paper trading validation.

### Configure Watchlist

In the app dashboard (page 29), or directly:
```bash
sqlite3 /opt/darrian-budget/data/budget.db \
  "INSERT OR REPLACE INTO bot_config VALUES ('watchlist', 'AAPL,MSFT,NVDA,QQQ', datetime('now'));"
```

### Monitoring

View bot activity in the app at `/pages/29_ai_trading_bot.py`.

View raw logs:
```bash
tail -f /var/log/trading_bot.log
```

### Risk Controls Built In
- **Circuit breaker**: Stops trading if account is down >2% in a day
- **Position limit**: Max 5% of portfolio per trade
- **Take profit**: Auto-closes at +50% gain
- **Stop loss**: Auto-closes at -8% loss
- **Market hours**: Only runs 9:30 AM – 4:00 PM ET, Mon–Fri
- **Paper mode default**: Will NOT trade real money unless `--live` flag passed
