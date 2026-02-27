# 404 Sole Archive — Price Alert Bot
**Checks eBay + Mercari every 30 min. Fires Telegram alerts when your inventory is profitable.**

---

## What It Does

| Alert Type | Trigger | Example |
|------------|---------|---------|
| 🟢 **eBay Sell Signal** | eBay avg price − your cost − fees > $30 | "Jordan 1 Chicago Sz 10: eBay avg $285, cost $180, net profit $87" |
| 🟢 **Mercari Sell Signal** | Mercari avg price − your cost − fees > $30 | "Yeezy 350 Zebra Sz 9: Mercari avg $210, cost $160, net profit $39" |
| 🔵 **Arb Opportunity** | Mercari low price → flip on eBay profit > $45 | "Buy on Mercari for $140, sell on eBay avg $230, profit $72" |

All alerts go to your phone via Telegram. No app to open, no manual checking.

---

## Files

```
sole_alert_bot/
├── alert.py           ← Main bot (run this via cron)
├── ebay_search.py     ← eBay Browse API helpers
├── mercari_search.py  ← Mercari internal API (no key needed)
├── setup_db.sql       ← Creates price_history + alert_log tables
├── requirements.txt   ← psycopg2-binary, requests
├── .env.example       ← All env vars with instructions
├── deploy.sh          ← One-command deploy to CT100
└── README.md          ← This file
```

---

## Setup (One Time)

### Step 1 — Create a Telegram Bot (5 minutes, free)

1. Open Telegram → search **@BotFather** → tap it
2. Send: `/newbot`
3. Name it: `404 Sole Archive Alerts` (or anything)
4. Username: `sole_archive_bot` (must end in `bot`)
5. BotFather gives you a token like: `7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
6. **Message your new bot once** (send it "hi") — this activates the chat
7. Get your chat ID — open this URL in your browser (replace YOUR_TOKEN):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
   Look for `"chat":{"id":123456789}` — that number is your `TELEGRAM_CHAT_ID`

### Step 2 — Set Environment Variables on CT100

SSH into CT100:
```bash
ssh root@100.95.125.112
```

Edit `/etc/environment` (persists across reboots):
```bash
nano /etc/environment
```

Add these lines (fill in your real values):
```bash
DATABASE_URL=postgres://user:password@host.railway.app:5432/railway
TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
EBAY_CLIENT_ID=DarrianB-404Sole-PRD-xxxxxxxxxxxx-xxxxxxxx
EBAY_CLIENT_SECRET=PRD-xxxxxxxxxxxxxxxxxxxx-xxxxxxxx-xxxx-xxxx
```

Save (`Ctrl+O`, `Enter`, `Ctrl+X`), then reload:
```bash
source /etc/environment
```

> **Where to find your eBay credentials:**
> Budget app → Business Tracker → eBay API Credentials section
> (they're already saved there from when you set up the market lookup)

### Step 3 — Deploy to CT100

From your **Mac** (Tailscale must be connected):
```bash
cd /Users/darrianbelcher/Downloads/darrian-budget/sole_alert_bot
chmod +x deploy.sh
./deploy.sh
```

The deploy script:
- Copies all files to `/opt/sole-alert/` on CT100
- Installs Python deps (`psycopg2-binary`, `requests`)
- Creates the DB tables (`price_history`, `alert_log`)
- Installs the cron job (every 30 min, 8am–midnight)
- Sends a test Telegram message

### Step 4 — Verify It Works

```bash
# On CT100 — send a test Telegram message
python3 /opt/sole-alert/alert.py --test

# Dry run — see what alerts would fire without sending them
python3 /opt/sole-alert/alert.py --dry-run

# Real run — check prices and send real alerts
python3 /opt/sole-alert/alert.py

# Watch the logs
tail -f /var/log/sole-alert.log
```

---

## Manual Deploy (if deploy.sh doesn't work)

```bash
# On your Mac:
scp sole_alert_bot/*.py sole_alert_bot/setup_db.sql sole_alert_bot/requirements.txt \
    root@100.95.125.112:/opt/sole-alert/

# On CT100:
pip3 install psycopg2-binary requests
psql $DATABASE_URL -f /opt/sole-alert/setup_db.sql

# Add cron job:
crontab -e
# Add this line:
*/30 8-23 * * * /usr/bin/python3 /opt/sole-alert/alert.py >> /var/log/sole-alert.log 2>&1
```

---

## Tuning

All tunable via environment variables — no code changes needed:

| Variable | Default | What it does |
|----------|---------|--------------|
| `MIN_PROFIT_THRESHOLD` | `30` | Min net profit ($) to trigger a sell alert |
| `EBAY_FEE_RATE` | `0.129` | eBay fee rate (12.9%) |
| `EBAY_FEE_FIXED` | `0.30` | eBay fixed fee per sale |
| `MERCARI_FEE_RATE` | `0.10` | Mercari fee rate (10%) |
| `MERCARI_FEE_FIXED` | `0.30` | Mercari fixed fee per sale |

**To raise the alert threshold to $50:**
```bash
echo 'export MIN_PROFIT_THRESHOLD=50' >> /etc/environment
source /etc/environment
```

---

## How Alerts Are Suppressed (No Spam)

The bot logs every alert it sends to the `alert_log` table. If it already alerted
you about the same item on the same platform within the last **4 hours**, it skips
the alert. This means:
- You won't get 48 alerts/day for the same shoe
- You will get re-alerted if the price is still good after 4 hours

---

## Mercari API Note

Mercari has no official public API. The bot uses their internal search endpoint
(`https://api.mercari.com/v2/entities:search`) which the website uses in the browser.
This is the same approach used by the open-source `mercarius` Python package.

**If Mercari searches stop returning results:**
1. Check the log: `tail /var/log/sole-alert.log`
2. Test manually: `python3 /opt/sole-alert/mercari_search.py`
3. If broken, check https://github.com/marvinody/mercarius for an updated payload
4. eBay alerts will continue working regardless — Mercari is a bonus

---

## Price History in Budget App

Every time the bot runs, it logs prices to the `price_history` table in Postgres.
This data is available for charting in the budget app — you can add a price trend
chart to `pages/3_business_tracker.py` using:

```python
# In pages/3_business_tracker.py — add a "Price History" tab
conn = get_conn()
history = read_sql("""
    SELECT checked_at, ebay_avg, mercari_avg
    FROM price_history
    WHERE item = %s AND size = %s
    ORDER BY checked_at DESC
    LIMIT 200
""", conn, params=(selected_item, selected_size))
st.line_chart(history.set_index("checked_at")[["ebay_avg", "mercari_avg"]])
```

---

## Cron Schedule

```
*/30 8-23 * * *   →   Every 30 minutes from 8:00 AM to 11:30 PM
```

To check/edit the cron job on CT100:
```bash
crontab -l          # view current cron jobs
crontab -e          # edit cron jobs
```

To run 24/7 instead of just daytime:
```
*/30 * * * *   /usr/bin/python3 /opt/sole-alert/alert.py >> /var/log/sole-alert.log 2>&1
```
