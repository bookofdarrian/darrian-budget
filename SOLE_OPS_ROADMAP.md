# SoleOps — 404 Sole Archive SaaS Product Roadmap
**Owner: Darrian Belcher | Created: 2026-03-04**
**Target: $9.99–$29.99/mo | First 10 users: 30 days | First 100 users: 90 days**

---

## 🎯 The Product

**SoleOps** is a sneaker reseller operations platform for serious eBay, Mercari, StockX, and GOAT sellers.

> "Stop leaving money on the table. Know exactly when to list, when to hold, and when to drop the price."

**Core value prop:**
- Real-time price monitoring with Telegram alerts (no manual checking)
- AI-generated eBay/Mercari listings that rank and convert
- Inventory aging tracker that tells you exactly when to reprice
- Full P&L by pair, by platform, by month — with fee calculations built in

---

## 🏗️ Phase 1 — MVP (Week 1–2): Extract & Polish Existing Tools

Everything exists in darrian-budget. Phase 1 is extraction + Stripe paywall.

### Week 1: Core Feature Polish

- [ ] **Price Monitor Dashboard** (from pages/31 + sole_alert_bot/)
  - Live eBay + Mercari price chart per SKU
  - Side-by-side: "If you sold today on eBay: $X | Mercari: $X"
  - Profit after fees calculator (real-time)
  - Telegram alert toggle per item

- [ ] **Inventory Aging Analyzer** (page 65 — from BACKLOG.md)
  - Days listed per SKU
  - Color-coded aging: green (<7d) → yellow (7–14d) → orange (14–21d) → red (21d+)
  - Auto-suggested price drop based on aging tier
  - "Stale pairs" alert view
  - Velocity chart: days listed vs sale price across sold history

- [ ] **AI Listing Generator** (polish pages/34)
  - eBay title (80 chars, keyword-rich, no ALL CAPS)
  - Full description with condition details
  - Suggested price (5% below eBay avg for fast sale)
  - One-click copy OR direct eBay API draft
  - Mercari description variant (different tone)

- [ ] **P&L Dashboard** (from pages/64 + pages/3)
  - Per-pair profit (COGS → sale price → fees → net)
  - Platform breakdown (eBay vs Mercari vs StockX profit margins)
  - Monthly P&L chart
  - Best/worst performers
  - Schedule C tax summary (COGS, mileage deductions)

### Week 2: Stripe Paywall + Auth

- [ ] Add Stripe subscription paywall
  - Free tier: 5 inventory items, no Telegram alerts
  - Starter ($9.99/mo): 50 items, Telegram alerts, AI listings
  - Pro ($19.99/mo): unlimited items, all features, StockX data
  - Pro+ ($29.99/mo): multi-platform listing API, priority support

- [ ] User registration + login flow
  - Email/password registration
  - Stripe checkout → subscription active → full access
  - Subscription status check on every page load

- [ ] Deploy as standalone app (separate from darrian-budget)
  - New Streamlit app: soleops.io (or 404soleops.com)
  - CT100 homelab: separate port (8502) behind Nginx

---

## 📊 Phase 2 — Growth Features (Week 3–6)

### Arbitrage Scanner
- Watchlist of target shoes + max buy price
- Mercari scanner: alert when any pair on watchlist appears below buy threshold
- eBay comp pulls automatically for ROI estimate
- "Buy signal" Telegram alert with direct Mercari link

### StockX Price Layer
- Pull StockX "last sale" prices via unofficial API or StockX integration
- Compare: "Your pair is listed at $220 on eBay. StockX last sale: $195. eBay is better."
- Helps users decide optimal platform per pair

### Shipping Cost Integration
- Pirateship API integration (best USPS/UPS rates)
- True profit = sale price - fees - SHIPPING - COGS
- Shipping cost estimator by shoe size/weight

### Mobile-Optimized Views
- Streamlit's responsive layout works on mobile
- Quick-add inventory from phone (photo → OCR → auto-fill form)
- Fast inventory status check from phone

---

## 🚀 Phase 3 — Scale (Month 2–3)

### Cross-Platform Listing (Direct API Push)
- Fill out the SoleOps form once
- One click → drafts listing on eBay (via eBay Sell API)
- One click → creates listing on Mercari (via automation)
- Eliminates 15–30 min per pair of manual listing work

### Bulk Import
- CSV import from eBay Sold History
- CSV import from Mercari sales export
- Automatically seeds inventory + COGS from purchase receipts

### Multi-User / Team Accounts
- Couples who resell together
- Small reseller teams (1 buyer, 1 lister)
- Shared inventory, separate profit tracking

### Community Features
- "Hot pairs" leaderboard (what's selling fastest in your size range)
- Anonymized market data from all SoleOps users
- Weekly "Reseller Report" email: what to buy this week

---

## 💰 Pricing & Revenue Projections

| Tier | Price | Features | Target Users |
|------|-------|----------|-------------|
| Free | $0 | 5 items, manual price check only | Trial users |
| Starter | $9.99/mo | 50 items, Telegram alerts, AI listings | Casual resellers (10–20 pairs/mo) |
| Pro | $19.99/mo | Unlimited items, StockX data, arb scanner | Serious resellers (30–50 pairs/mo) |
| Pro+ | $29.99/mo | Direct API listing, multi-user, bulk import | Power sellers (50+ pairs/mo) |

### Revenue Milestones

| Month | Users | MRR | ARR |
|-------|-------|-----|-----|
| Month 1 | 10 beta (free) | $0 | — |
| Month 2 | 30 (10 paid Starter) | $100 | — |
| Month 3 | 100 (50 paid mixed) | $750 | $9,000 |
| Month 6 | 300 (150 paid mixed) | $2,500 | $30,000 |
| Month 12 | 800 (400 paid mixed) | $7,200 | $86,400 |

**Break-even:** ~15 Pro users ($300 MRR) covers hosting + Claude API costs.

---

## 📣 Distribution Strategy

### Launch Channels (Month 1)

1. **r/flipping** — Post "I built a tool that tells me exactly when to drop my eBay prices"
   - Show real data from 404 Sole Archive
   - Show the before/after: manual checking vs SoleOps alerts
   - Offer 30-day free Pro trial for first 20 signups

2. **r/sneakermarket + r/sneakers** — "Here's how I track profit per pair across eBay and Mercari"
   - Show P&L dashboard screenshot (with real Darrian data)
   - Don't hard-sell — let the data speak

3. **Reseller Discord servers** — Find 3-5 active servers, offer beta access
   - Resell Calendar Discord
   - Sneaker cook groups
   - Sole Collector Discord

4. **YouTube** — Film a 5-minute demo: "How I automate my sneaker resale pricing"
   - Show Telegram alert firing in real time
   - Show AI generating a listing
   - Post on 404 Sole Archive channel / TikTok

### Retention Strategy

- Weekly "Reseller Report" email (automated, Claude-generated summary)
- Telegram alerts = daily active usage (sticky feature)
- Price drop suggestions = saves money = users credit SoleOps
- Monthly P&L email = "look how much you made using SoleOps"

---

## 🛠️ Tech Architecture

```
SoleOps App (Streamlit, port 8502)
├── Auth: email/password + Stripe subscription check
├── DB: PostgreSQL (shared with darrian-budget or separate schema)
├── Price Data: sole_alert_bot/ integrations (eBay API + Mercari)
├── AI: Claude claude-opus-4-5 via Anthropic API
├── Payments: Stripe (monthly subscriptions)
├── Alerts: Telegram bot (existing infrastructure)
└── Hosting: CT100 homelab → Nginx → soleops.io
```

**Reused from darrian-budget:**
- `utils/db.py` — DB connection, get_setting, set_setting
- `utils/auth.py` — Auth system (extend for Stripe subscription check)
- `utils/stripe_utils.py` — Stripe integration
- `sole_alert_bot/` — All price monitoring code
- `pages/34_ebay_listing_generator.py` — AI listing code
- `pages/31_sneaker_price_alert_bot.py` — Alert UI

---

## 📅 30-Day Sprint Plan

| Week | Focus | Deliverable |
|------|-------|-------------|
| Week 1 | Polish core features | Inventory analyzer + price dashboard working |
| Week 2 | Stripe paywall + deploy | soleops.io live with free + paid tiers |
| Week 3 | Beta launch | Post in r/flipping + 3 Discord servers |
| Week 4 | Iterate on feedback | Fix top 3 complaints, add most-requested feature |

**Success metric for Month 1:** 10 people using it regularly (paid or free trial).
**Success metric for Month 3:** $500 MRR (25 paid users).

---

## 🔑 The Unfair Advantage

You're not building this as an outsider guessing what resellers need.
**You ARE the user.** Your 404 Sole Archive data is the first dataset.
Your own frustrations are the product requirements.

The Telegram alerts already fire for your real inventory.
The AI listing generator already saved you time.
The price drop algorithm is already calibrated to your profit thresholds.

**Ship it, use it daily, let others see it working on your business, then sell it.**
