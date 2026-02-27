# Next Most Lucrative Use Cases — New Ideas
**Owner: Darrian Belcher | Created: 2026-02-26**

> These are ideas NOT already in `HOMELAB_USECASES.md`. Each one is evaluated on
> **time-to-value** (how fast you see a return) and **dollar impact** (how much it
> actually makes or saves you). Ranked by combined ROI.

---

## 🏆 Tier S — Highest ROI, Do These First

---

### 1. 💸 Sneaker Price Alert Bot (eBay + Mercari)
**New idea — not in the existing list**

**The problem you have right now:** You manually check eBay and Mercari to know
when to buy or sell. You miss windows. You leave money on the table.

**What this does:**
- Runs on your homelab 24/7 as a lightweight Python script in CT100
- Polls **eBay** (official API — already wired in your app) + **Mercari** (unofficial
  GraphQL endpoint — no API key needed) every 30 minutes
- When a shoe in your inventory has comparable listings drop below your cost basis
  → **"market is soft, hold or relist lower"** alert
- When a shoe on your watchlist appears on Mercari under your target buy price
  → **"buy opportunity"** alert sent to Telegram
- Logs every price check to Postgres — you get a price history chart in the budget app

**Why it's #1:**
Your eBay API client (`_ebay_get_token` + `ebay_search_sold`) is already written
in `pages/3_business_tracker.py`. You just need to move it to a standalone script,
add Mercari, and wire up Telegram alerts. This is 80% already built.

**Realistic dollar impact:** $40–$200 per flip improvement × however many pairs
you move per month. If you flip 4 pairs/month and improve average profit by $50
each = **$200/month extra profit**.

---

**How eBay pricing works (already built — just reuse it):**

Your existing `ebay_search_sold()` function hits the Browse API and returns live
listings. For the alert bot, you call it with the shoe name + size and average
the top 10 prices to get a real-time market price. eBay API key is already saved
in your Postgres `settings` table.

---

**How Mercari works (no API key — uses their internal GraphQL):**

Mercari US has no official public API, but their website uses a GraphQL endpoint
with Automatic Persisted Queries. The query hash is stable and has been used by
the open-source community for years:

```python
# mercari_search.py — drop this in /opt/sole-alert/

import requests, json

MERCARI_URL = "https://api.mercari.com/v2/entities:search"

def mercari_search_sneakers(query: str, limit: int = 20) -> list[dict]:
    """
    Search Mercari US for active sneaker listings.
    No API key required — uses Mercari's internal search endpoint.
    Returns list of {name, price, status, thumbnail_url, item_url}
    """
    headers = {
        "Content-Type": "application/json",
        "X-Platform": "web",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "DPR": "2",
        "X-Requested-With": "XMLHttpRequest",
    }
    payload = {
        "userId": "",
        "pageSize": limit,
        "pageToken": "",
        "searchSessionId": "",
        "indexRouting": "INDEX_ROUTING_UNSPECIFIED",
        "thumbnailTypes": [],
        "searchCondition": {
            "keyword": query,
            "excludeKeyword": "",
            "sort": "SORT_SCORE",
            "order": "ORDER_DESC",
            "status": ["STATUS_ON_SALE"],
            "sizeId": [],
            "brandId": [],
            "sellerId": [],
            "priceMin": 0,
            "priceMax": 0,
            "itemConditionId": [],
            "shippingPayerId": [],
            "shippingFromArea": [],
            "shippingMethod": [],
            "categoryId": [],
            "color": [],
            "hasCoupon": False,
            "attributes": [],
            "itemTypes": [],
            "skuIds": [],
        },
        "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
        "serviceFrom": "suruga",
        "withItemBrand": True,
        "withItemSize": True,
        "withItemPromotions": False,
        "withItemSizes": True,
        "withShopname": False,
    }

    try:
        r = requests.post(MERCARI_URL, headers=headers, json=payload, timeout=15)
        if r.status_code != 200:
            return []
        items = r.json().get("items", [])
        results = []
        for item in items:
            price = item.get("price", 0)
            results.append({
                "name":          item.get("name", ""),
                "price":         int(price) if price else 0,
                "status":        item.get("status", ""),
                "condition":     item.get("itemCondition", {}).get("name", ""),
                "thumbnail_url": item.get("thumbnails", [{}])[0].get("url", ""),
                "item_url":      f"https://www.mercari.com/us/item/{item.get('id', '')}",
                "source":        "Mercari",
            })
        return results
    except Exception:
        return []
```

**⚠️ Mercari API stability note:** This is an unofficial endpoint. Mercari can
change it without notice. If it breaks, the fix is usually just updating the
payload structure. Check the `mercarius` Python package on GitHub for the latest
working payload if needed.

---

**Full alert bot — combining eBay + Mercari:**

```python
# /opt/sole-alert/alert.py — runs in CT100 as a cron job
import requests, os, base64, psycopg2, json
from datetime import datetime

DATABASE_URL   = os.environ["DATABASE_URL"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
EBAY_CLIENT_ID  = os.environ["EBAY_CLIENT_ID"]
EBAY_CLIENT_SECRET = os.environ["EBAY_CLIENT_SECRET"]

def send_alert(msg: str):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
        timeout=10
    )

def get_ebay_token() -> str | None:
    creds = base64.b64encode(f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={"Authorization": f"Basic {creds}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data="grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope",
        timeout=10
    )
    return r.json().get("access_token") if r.status_code == 200 else None

def get_ebay_avg_price(query: str, token: str) -> float:
    r = requests.get(
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": query, "category_ids": "15709",
                "filter": "buyingOptions:{FIXED_PRICE}", "limit": 10},
        timeout=10
    )
    items = r.json().get("itemSummaries", []) if r.status_code == 200 else []
    prices = [float(i["price"]["value"]) for i in items if i.get("price")]
    return sum(prices) / len(prices) if prices else 0.0

def get_mercari_low_price(query: str) -> float:
    # Uses mercari_search_sneakers() from mercari_search.py above
    from mercari_search import mercari_search_sneakers
    results = mercari_search_sneakers(query, limit=20)
    prices = [r["price"] for r in results if r["price"] > 0]
    return min(prices) if prices else 0.0

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Load your inventory with target sell prices
    cur.execute("""
        SELECT item, size, buy_price, notes
        FROM sole_archive
        WHERE status = 'inventory'
    """)
    inventory = cur.fetchall()

    ebay_token = get_ebay_token()

    for item, size, cost_basis, notes in inventory:
        query = f"{item} size {size}"

        # Check eBay
        ebay_avg = get_ebay_avg_price(query, ebay_token) if ebay_token else 0
        # Check Mercari
        mercari_low = get_mercari_low_price(query)

        profit_ebay    = ebay_avg - cost_basis if ebay_avg else 0
        profit_mercari = mercari_low - cost_basis if mercari_low else 0

        # Alert if either platform shows profit > $30
        if profit_ebay > 30:
            send_alert(
                f"🟢 <b>SELL SIGNAL — eBay</b>\n"
                f"👟 {item} (Sz {size})\n"
                f"💰 eBay avg: ${ebay_avg:.0f} | Cost: ${cost_basis:.0f}\n"
                f"📈 Est. profit: ${profit_ebay:.0f} (before fees)"
            )
        if profit_mercari > 30:
            send_alert(
                f"🟢 <b>SELL SIGNAL — Mercari</b>\n"
                f"👟 {item} (Sz {size})\n"
                f"💰 Mercari low: ${mercari_low:.0f} | Cost: ${cost_basis:.0f}\n"
                f"📈 Est. profit: ${profit_mercari:.0f} (before fees)"
            )

        # Log price check to Postgres for history chart
        cur.execute("""
            INSERT INTO price_history (item, size, ebay_avg, mercari_low, checked_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (item, size, ebay_avg, mercari_low, datetime.utcnow()))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
```

**New DB table needed (run once):**
```sql
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    item TEXT,
    size TEXT,
    ebay_avg REAL,
    mercari_low REAL,
    checked_at TIMESTAMP DEFAULT NOW()
);
```

**Telegram bot setup (free, 5 minutes):**
1. Message `@BotFather` on Telegram → `/newbot` → get your token
2. Message your new bot once → get your chat ID from the API
3. Set env vars in CT100: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
   `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `DATABASE_URL`

**Cron schedule on CT100:**
```bash
# Check prices every 30 minutes, 8am–midnight
*/30 8-23 * * * /usr/bin/python3 /opt/sole-alert/alert.py >> /var/log/sole-alert.log 2>&1
```

**eBay vs Mercari — why both matter:**

| Platform | Strength | Fee |
|----------|----------|-----|
| eBay | Huge buyer pool, auction + BIN, official API | ~12.9% + $0.30 |
| Mercari | Lower fees, faster casual buyers, no listing fee | ~10% + $0.30 |

Mercari often has lower asking prices (less competition) which makes it a great
**buy source** — you can find pairs cheaper there and flip on eBay for more.

**Effort:** Low-Medium (3–4 hours) | **Monthly Value:** $100–$400 in improved flip margins

---

### 2. 🧾 HSA Receipt Auto-Categorizer + Reimbursement Tracker
**New idea — not in the existing list**

**The problem:** You have `pages/6_receipts.py` already. But HSA reimbursement
is a manual process — you upload a receipt, you forget about it, you leave
tax-free money sitting unclaimed.

**What this does:**
- When you upload a receipt photo to the budget app, it runs OCR (Tesseract,
  free, runs locally on CT100) to extract the merchant, date, and amount
- Claude (or Ollama locally) classifies it: "Is this HSA-eligible?"
- Tracks a running "unreimbursed HSA balance" — money you've spent out-of-pocket
  that you can pull from your HSA tax-free at any time (even years later)
- Monthly reminder: "You have $847 in unreimbursed HSA expenses. Reimburse yourself."
- Generates a PDF summary for your records (IRS requires documentation)

**Why this is high ROI:**
The HSA triple tax advantage is the best tax shelter available to you. Every
dollar you reimburse yourself from HSA = a dollar you never paid income tax on.
If you're in the 22% federal + 5% Georgia bracket, every $1,000 in HSA
reimbursements = **$270 in tax savings**. Most people leave thousands on the table
because they don't track it.

**Realistic dollar impact:** If you have $3,000/year in medical/dental/vision
expenses and reimburse via HSA = **$810/year in tax savings** (27% combined rate).

**How to add it to the budget app:**
```python
# Add to pages/6_receipts.py — new "HSA Tracker" tab

# New DB table:
# CREATE TABLE hsa_receipts (
#   id INTEGER PRIMARY KEY,
#   date TEXT, merchant TEXT, amount REAL,
#   category TEXT, -- 'medical', 'dental', 'vision', 'rx', 'other'
#   reimbursed INTEGER DEFAULT 0, -- 0 = pending, 1 = reimbursed
#   notes TEXT
# )

# Running total widget:
unreimbursed = read_sql(
    "SELECT SUM(amount) FROM hsa_receipts WHERE reimbursed = 0", conn
).iloc[0, 0] or 0
st.metric("💰 Unreimbursed HSA Balance", f"${unreimbursed:,.2f}",
          help="You can withdraw this tax-free from your HSA at any time")
```

**Effort:** Medium (4–5 hours) | **Annual Value:** $500–$1,500 in tax savings

---

### 3. 📦 Automated eBay/StockX Listing Generator
**New idea — not in the existing list**

**The problem:** Writing eBay listings takes time. You have to describe condition,
write a title that ranks in search, pick the right category, set a competitive price.

**What this does:**
- You enter: shoe name, size, condition (1–10), any flaws
- Claude generates: optimized eBay title (80 chars, keyword-rich), full description,
  suggested price (pulled from KicksDB), recommended category ID
- One-click copy to clipboard — paste directly into eBay's listing form
- Optionally: use eBay's API (you already have it wired in) to **draft the listing
  automatically** — you just review and publish

**Why it's high ROI:**
A well-written eBay listing with the right keywords can sell 20–40% faster and
at a higher price than a generic one. Time savings alone: if you list 8 pairs/month
and this saves 15 minutes per listing = 2 hours/month back. Plus better titles
= better search ranking = higher sell price.

**Realistic dollar impact:** 15% higher average sale price on eBay listings
× your monthly volume. If you sell $2,000/month on eBay, 15% = **$300/month**.

**How to add it to the budget app:**
```python
# Add to pages/3_business_tracker.py — new "Listing Generator" tab

def generate_listing(shoe: str, size: str, condition: int, flaws: str,
                     market_price: float, api_key: str) -> dict:
    prompt = f"""
    Generate an optimized eBay listing for:
    Shoe: {shoe} Size {size}
    Condition: {condition}/10
    Flaws: {flaws or 'None'}
    Market price: ${market_price:.2f}

    Return JSON with:
    - title: 80-char eBay title (keyword-rich, no ALL CAPS)
    - description: 3-paragraph description
    - suggested_price: float (5% below market for fast sale)
    - condition_id: eBay condition ID (1000=New, 3000=Used)
    """
    # Call Claude → parse JSON → display in UI
```

**Effort:** Low-Medium (2–3 hours) | **Monthly Value:** $100–$400 in better pricing + time saved

---

## 🥇 Tier 1 — High ROI, Build After Tier S

---

### 4. 📊 Visa RSU Vest Calendar + Tax Withholding Optimizer
**New idea — not in the existing list**

**The problem:** Your RSU/ESPP page calculates taxes but doesn't tell you
**what to do with your paycheck** in the months your RSUs vest. Vest events
create a tax spike — if you're not prepared, you owe at tax time.

**What this does:**
- Pulls your vesting schedule (you enter it once)
- Shows a 12-month calendar: "In March, ~19 shares vest at ~$340 = $6,460 income,
  $1,421 withheld at 22%, but your actual bracket is 24% → you'll owe $129 more"
- Calculates whether you should increase W-4 withholding or make quarterly
  estimated tax payments to cover the gap
- Integrates with your existing income tracker — vest events auto-appear as income
- Alert 2 weeks before each vest: "RSU vest in 14 days — review your tax position"

**Why it's high ROI:**
Underpayment penalties are 8% annualized right now. More importantly, being
surprised by a $2,000 tax bill in April is a cash flow problem. This turns a
reactive problem into a proactive one.

**Realistic dollar impact:** Avoid $200–$500 in underpayment penalties + interest.
More importantly: **peace of mind and no April surprises**.

**Effort:** Low (2–3 hours — mostly extending existing RSU page) | **Annual Value:** $200–$500

---

### 5. 🏠 Rent vs Buy Calculator (Atlanta-Specific)
**New idea — not in the existing list**

**The problem:** You're relocating to Atlanta for Visa. At some point you'll
decide whether to rent or buy. This is the biggest financial decision of the
next 5 years and most online calculators are generic garbage.

**What this does:**
- Inputs: rent amount, home price, down payment %, mortgage rate, HOA, property tax
- Calculates true cost of ownership (mortgage + taxes + insurance + maintenance
  at 1% of home value/year + opportunity cost of down payment)
- Compares to renting + investing the difference
- Atlanta-specific: pulls Zillow/Redfin median prices for specific zip codes
- Break-even analysis: "You need to stay 4.2 years for buying to beat renting"
- Integrates with your net worth tracker — models both scenarios on your net worth

**Why it's high ROI:**
Buying a home 1 year too early in a flat/declining market can cost $20,000–$50,000.
Renting 2 years too long in a rising market costs the same. Getting this right
is worth more than any other financial decision you'll make in Atlanta.

**Realistic dollar impact:** Making the right rent vs buy decision at the right
time = **$20,000–$50,000 over 5 years**.

**How to add it:**
```python
# New page: pages/17_rent_vs_buy.py
# Inputs: rent, home_price, down_pct, rate, hoa, prop_tax_rate, years
# Key formula: true_own_cost = mortgage + tax + insurance + maintenance
#              - equity_buildup - appreciation
#              vs rent + (down_payment * 0.07 annual investment return)
```

**Effort:** Medium (4–5 hours) | **Long-term Value:** $20,000–$50,000 decision quality

---

### 6. 🤖 Ollama + Budget App Integration (Local AI, Zero API Cost)
**New idea — extends existing Ollama plan with a specific implementation**

The existing use case list says "deploy Ollama" but doesn't say how to actually
wire it into the budget app to save money. Here's the specific implementation:

**What this does:**
- Adds a `LOCAL_AI_ENABLED` flag to the budget app
- When enabled, routes "simple" AI queries to Ollama (Llama 3.1 8B) instead of Claude
- "Simple" = expense categorization, quick summaries, pattern detection
- "Complex" = RSU tax analysis, trading strategy — still uses Claude
- Estimated split: 70% of AI calls are simple → 70% cost reduction

**Cost math:**
```
Current: 100 AI calls/month × $0.05 avg = $5/month to Anthropic
With Ollama routing:
  30 complex calls × $0.05 = $1.50 (Claude)
  70 simple calls × $0.00 = $0.00 (Ollama local)
  Savings: $3.50/month = $42/year
```

**The actual code change needed:**
```python
# utils/aura_client.py — add Ollama fallback

import os, requests, anthropic

OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "")  # http://100.95.125.112:11434
LOCAL_AI_ENABLED = bool(OLLAMA_URL)

def ask_ai(prompt: str, complex_query: bool = False) -> str:
    """Route to Ollama for simple queries, Claude for complex ones."""
    if LOCAL_AI_ENABLED and not complex_query:
        r = requests.post(f"{OLLAMA_URL}/api/generate",
                          json={"model": "llama3.1:8b", "prompt": prompt, "stream": False},
                          timeout=30)
        return r.json()["response"]
    else:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(model="claude-opus-4-5", max_tokens=500,
                                      messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text
```

**Effort:** Medium (3–4 hours) | **Annual Value:** $40–$100 in API cost savings + privacy

---

### 7. 📈 Automated Monthly Financial Report (Email to Yourself)
**New idea — not in the existing list**

**The problem:** Your budget app has all the data but you have to log in to see it.
You want a monthly "state of your finances" without having to remember to check.

**What this does:**
- Runs on the 1st of every month as a cron job on CT100
- Pulls last month's data from Postgres: income, expenses, savings rate, net worth delta
- Claude writes a 3-paragraph narrative summary: "Last month you spent $X on food,
  which is 15% above your average. Your savings rate was 34%. Your net worth grew by $Y."
- Sends it to your email (Gmail SMTP, free) as a clean HTML email
- Optionally: generates a PDF and saves it to TrueNAS as a permanent record

**Why it's high ROI:**
Awareness drives behavior. People who review their finances monthly save 15–20%
more than those who don't. This automates the review so you never skip it.

**Realistic dollar impact:** 15% improvement in savings rate. If you currently
save $1,500/month, 15% more = **$225/month = $2,700/year**.

**How to build it:**
```python
# /opt/monthly-report/report.py — runs on CT100 via cron
import smtplib, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import psycopg2, anthropic

# 1. Query last month's data from Postgres
# 2. Build context string (income, expenses, savings rate, net worth)
# 3. Ask Claude to write a narrative summary
# 4. Send via Gmail SMTP (app password, free)

# Cron: 0 8 1 * * /opt/monthly-report/report.py
```

**Effort:** Medium (3–4 hours) | **Annual Value:** $2,000–$3,000 in improved savings behavior

---

### 8. 🔄 Stripe Subscription Revenue Dashboard
**New idea — not in the existing list**

**The problem:** Stripe is already wired into your app (`utils/stripe_utils.py`).
If you ever have paying users on peachstatesavings.com, you need to track MRR,
churn, LTV, and failed payments — the metrics that actually matter for a SaaS.

**What this does:**
- New page: `pages/18_revenue.py`
- Pulls from Stripe API: active subscriptions, MRR, new subs this month, churned subs
- Calculates: MRR, ARR, churn rate, average revenue per user (ARPU), LTV
- Shows a cohort chart: which month did each subscriber join, are they still active?
- Alerts when a payment fails (before the customer churns)
- Integrates with your existing income tracker — Stripe revenue auto-logs as income

**Why it's high ROI:**
If you ever charge $9.99/month for Pro access and get 50 users, that's $500/month.
Reducing churn by 5% (catching failed payments early) = $25/month saved.
More importantly: **this is the infrastructure to turn peachstatesavings.com into
a real business**.

**Realistic dollar impact:** Depends on user growth. But having the dashboard
ready means you'll actually track it — and what gets measured gets managed.

**Effort:** Low-Medium (2–3 hours — Stripe SDK already installed) | **Value:** Scales with revenue

---

## 🥈 Tier 2 — Medium ROI, Build When Ready

---

### 9. 🏋️ Health & Fitness Cost Tracker (HSA + Gym + Supplements)
**New idea — not in the existing list**

**The problem:** Health spending is scattered — gym membership, supplements,
doctor copays, prescriptions, dental, vision. You don't know your true annual
health cost or what's HSA-eligible.

**What this does:**
- New expense category: "Health" with subcategories (gym, medical, dental, vision, rx, supplements)
- Automatically flags HSA-eligible items (medical, dental, vision, rx)
- Annual health cost summary: "You spent $3,847 on health this year. $2,100 was
  HSA-eligible. You've only reimbursed $800. You have $1,300 in unclaimed HSA money."
- Tracks gym ROI: cost per workout if you log workouts (simple counter)

**Effort:** Low (2 hours — mostly a new expense category + HSA integration) | **Annual Value:** $300–$800 in unclaimed HSA reimbursements

---

### 10. 🚗 Car Expense Tracker + Depreciation Calculator
**New idea — not in the existing list**

**The problem:** Your car is likely your second-largest asset after your home
(or will be). Most people have no idea what their car actually costs per mile.

**What this does:**
- Track: gas, insurance, maintenance, registration, parking
- Calculate: true cost per mile (total annual cost ÷ miles driven)
- Depreciation curve: shows current estimated value vs what you paid
- 404 Sole Archive angle: if you drive to pick up/drop off inventory, those
  miles are **tax-deductible at $0.67/mile (2024 IRS rate)**. Track them.
- Alert when it's cheaper to Uber than own (for low-mileage months)

**Why it's relevant to you specifically:**
Business mileage deduction for 404 Sole Archive. If you drive 2,000 miles/year
for the business = **$1,340 tax deduction** = ~$360 in actual tax savings.

**Effort:** Low-Medium (3 hours) | **Annual Value:** $300–$600 in mileage deductions

---

### 11. 🌐 Cloudflare Worker + Edge Cache for Budget App
**New idea — not in the existing list**

**The problem:** Your budget app on Railway cold-starts when it hasn't been
accessed in a while. Users (including you) wait 10–15 seconds for the first load.

**What this does:**
- Deploy a Cloudflare Worker (free tier: 100,000 requests/day) in front of Railway
- Worker serves a "loading" page instantly while Railway warms up
- Caches static assets (CSS, JS) at the edge — subsequent loads are instant
- Adds DDoS protection and rate limiting for free
- Bonus: Cloudflare Analytics shows you real traffic data

**Why it's high ROI:**
Free performance improvement. Cloudflare's free tier is genuinely free forever.
This makes peachstatesavings.com feel like a professional product.

**Effort:** Low (1–2 hours) | **Value:** Better UX, free CDN, DDoS protection

---

### 12. 📱 Telegram Bot for Budget App (Mobile-First Interface)
**New idea — not in the existing list**

**The problem:** Adding an expense on your phone requires opening a browser,
navigating to the app, finding the expense page, filling out a form. It's slow.
You forget to log things because the friction is too high.

**What this does:**
- Telegram bot (free, runs on CT100) that accepts natural language
- You text: "spent $47 at Publix groceries" → bot parses it and logs to Postgres
- You text: "how much did I spend this month?" → bot replies with a summary
- You text: "add Jordan 1 Chicago size 10 cost $180 to inventory" → logs to sole_archive
- Uses Ollama locally to parse the natural language (free, private)

**Why it's high ROI:**
Reducing friction = more complete data = better insights. If you log 30% more
expenses because it's easier, your budget accuracy improves dramatically.

**Effort:** Medium (4–5 hours) | **Value:** Better data quality, faster logging, mobile access

---

## 💰 Updated ROI Summary

| Use Case | Effort | Monthly Value | Annual Value |
|----------|--------|--------------|--------------|
| 1. Sneaker Price Alert Bot | 3–4 hrs | $100–$400 | $1,200–$4,800 |
| 2. HSA Receipt Auto-Tracker | 4–5 hrs | $40–$125 | $500–$1,500 |
| 3. eBay Listing Generator | 2–3 hrs | $100–$400 | $1,200–$4,800 |
| 4. RSU Vest Calendar | 2–3 hrs | $17–$42 | $200–$500 |
| 5. Rent vs Buy Calculator | 4–5 hrs | one-time | $20k–$50k decision |
| 6. Ollama AI Routing | 3–4 hrs | $3–$8 | $40–$100 |
| 7. Monthly Email Report | 3–4 hrs | $175–$225 | $2,000–$3,000 |
| 8. Stripe Revenue Dashboard | 2–3 hrs | scales | scales with MRR |
| 9. Health Cost Tracker | 2 hrs | $25–$65 | $300–$800 |
| 10. Car/Mileage Tracker | 3 hrs | $25–$50 | $300–$600 |
| 11. Cloudflare Edge Cache | 1–2 hrs | free | free |
| 12. Telegram Budget Bot | 4–5 hrs | indirect | better data quality |

---

## 🎯 Recommended Build Order

```
WEEK 1 (highest immediate dollar impact):
  1. Sneaker Price Alert Bot     → starts improving flip margins immediately
  2. eBay Listing Generator      → faster listings, better prices

WEEK 2 (tax savings):
  3. HSA Receipt Auto-Tracker    → start capturing unreimbursed expenses now
  4. Car/Mileage Tracker         → log 404 Sole Archive miles for tax deduction

WEEK 3 (infrastructure):
  5. Monthly Email Report        → set it and forget it, runs forever
  6. Cloudflare Edge Cache       → 1-2 hours, instant UX improvement

MONTH 2:
  7. RSU Vest Calendar           → before your first vest event
  8. Rent vs Buy Calculator      → before you sign a lease in Atlanta
  9. Telegram Budget Bot         → when you want mobile-first logging

WHEN PEACHSTATESAVINGS.COM HAS USERS:
  10. Stripe Revenue Dashboard   → the moment you have paying subscribers
```

---

## 🔑 The Big Insight

Your existing stack already has:
- ✅ KicksDB API (sneaker prices)
- ✅ eBay API (market data)
- ✅ Stripe (payments)
- ✅ Claude (AI)
- ✅ Postgres (data)
- ✅ Homelab (compute, 24/7)
- ✅ Tailscale (remote access)

**You're not missing tools. You're missing automation.**

The highest-ROI move is to take the data you're already collecting and make it
work for you automatically — price alerts, monthly reports, listing generation —
instead of requiring you to manually check things. Every hour you save on manual
tasks is an hour you can spend on 404 Sole Archive or Visa work.
