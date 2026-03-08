# Feature Backlog — Autonomous AI Dev Queue
**Owner: Darrian Belcher | Updated: 2026-03-08**

> The overnight AI dev system reads this file every night and picks the
> highest-priority uncompleted item to build autonomously.
> Completed items are marked [DONE] ✅ by the Git Agent.

---

## 🆕 NEW FEATURES — Added 2026-03-08

### Darrian's Feature Requests

- [x] **Todo: Brain Dump section** — Always-visible text area on every todo view. Paste raw text, voice transcript, or notes → Claude AI extracts individual tasks and adds them to the list. [DONE] ✅ (pages/22_todo.py)
- [x] **Todo: Calendar integration restored** — Google Calendar now a top-level tab alongside "My Tasks". Sync tasks with due dates as events, view upcoming events, manage auth — all without scrolling. [DONE] ✅ (pages/22_todo.py)
- [x] **Resale Price Advisor** — page 72 — Upload item photo → Claude Vision identifies product → searches eBay & Mercari sold comps → AI recommends listing price, Buy It Now vs Auction, shipping strategy, platform ranking, and ROI calculation. [DONE] ✅ (pages/72_resale_price_advisor.py)
- [x] **Sandbox / Privacy Mode** — page 73 — Per-user isolated SQLite DB (`data/sandbox_{user}.db`), completely separate from the shared production DB. Admin grants access, 7-day auto-expiry on inactivity, JSON export, raw .db download, one-click wipe. [DONE] ✅ (pages/73_sandbox_mode.py — 331/331 tests passing)

### Reddit Insights (r/claude, 2026-03-08) — Applied to Our Agent System

- [x] **Scheduled Autonomous Tasks** — Added `agent_scheduled_tasks` table + ⏰ tab in Agent Dashboard. Daily/weekly/monthly scheduler with next_run calculator. Seeds 4 defaults (weekly digest, daily price alert, monthly report, weekly reseller report). Cron wiring instructions included. [DONE] ✅ (pages/30_agent_dashboard.py — 331/331 tests passing)
- [ ] **Agent: Google Drive Connector** — MCP-based Google Drive integration so agents can read/write budget export files, receipts, and reports directly from Drive without manual uploads. Google Drive is already a native Claude connector.
- [ ] **Agent: Background File Organizer** — Autonomous agent that runs weekly, scans uploaded receipts and documents, and organizes them into labeled folders/categories. Surfaces "you have 12 uncategorized receipts" alerts.
- [ ] **Creator Companion: Auto-Brief Synthesizer** — Point the agent at a folder of briefs, notes, and meeting exports → Claude synthesizes a finished content brief or script outline. No more 30-min manual organizing sessions.

---

## 🚀 SOLEOPS SAAS — BUILD THIS MONTH (30-Day Sprint)

**Goal: Launch SoleOps as a standalone paid SaaS for sneaker resellers**
**Revenue target: $500 MRR by Day 90 | See SOLE_OPS_ROADMAP.md for full plan**

### Week 1 — Core Feature Polish
- [x] **SoleOps: Sneaker Inventory Analyzer** — page 65 — Core SoleOps feature. [DONE] ✅ (pages/65_sneaker_inventory_analyzer.py — 34/34 tests passing)
- [x] **SoleOps: Price Monitor Dashboard** — page 68 — Live eBay + Mercari price per SKU with side-by-side comparison. "If you sold today on eBay: $X | Mercari: $X". Profit-after-fees calculator (real-time). Historical price chart per shoe. [DONE] ✅ (pages/68_soleops_price_monitor.py — 58/58 tests passing)
- [x] **SoleOps: P&L Dashboard** — page 69 — Per-pair profit (COGS → sale price → platform fees → net). Platform breakdown chart (eBay vs Mercari vs StockX profit margins). Monthly P&L trend. Best/worst performers table. Schedule C tax summary. [DONE] ✅ (pages/69_soleops_pnl_dashboard.py — 58/58 tests passing)

### Week 2 — Stripe Paywall + Deploy
- [x] **SoleOps: Stripe Subscription Paywall** — page 70 — Free/Starter/Pro/Pro+ tiers, Stripe checkout, admin MRR dashboard, subscription management. [DONE] ✅ (pages/70_soleops_stripe_paywall.py — 58/58 tests passing)
- [ ] **SoleOps: User Registration Flow** — update auth — Email/password registration page for new SoleOps users. Stripe checkout integration → subscription active → unlock features. Welcome email via Gmail SMTP.

### Week 3–4 — Growth Features
- [x] **SoleOps: Arbitrage Scanner** — page 71 — Watchlist of target shoes + max buy price. Mercari scanner alerts when watchlist pair appears below buy threshold. eBay comp auto-pulls for ROI estimate. "Buy signal" Telegram alert with direct Mercari link. [DONE] ✅ (pages/71_soleops_arb_scanner.py — 58/58 tests passing)
- [ ] **SoleOps: AI Listing Generator Polish** — improve page 34 — Connect eBay market data to auto-suggest price. Add "Mercari variant" of the description. One-click eBay API draft (Sell API). Add listing performance tracker (did the AI title work? how fast did it sell?).
- [ ] **SoleOps: Weekly Reseller Report Email** — automated — Claude-generated weekly summary emailed to each user. "You have 3 stale pairs. eBay market is up 8% on Jordan 1s. Best opportunity this week: [X]." Cron job on CT100.

---

## ⭐ HIGHEST PRIORITY — Darrian's Personal Vision Features

**THESE MUST BE BUILT NEXT — in this exact order:**

- [x] Sneaker Inventory Analyzer — page 65 — [DONE] ✅ (pages/65_sneaker_inventory_analyzer.py — 34/34 tests passing)
- [x] Health & Wellness AI Hub — page 66 — Mood logs, workouts, medications, doctor visits, vaccines, Claude AI insights, Apple Health CSV import, daily check-in. [DONE] ✅ (pages/66_health_wellness_hub.py — 58/58 tests passing)
- [x] Life Experience & Travel Model — page 67 — Trips, flights, hotels, memories, life milestones timeline, Claude AI travel advisor, iTunes music API. [DONE] ✅ (pages/67_life_travel_model.py — 58/58 tests passing)

---

## HIGH PRIORITY

- [x] Sneaker Price Alert Bot (eBay + Mercari polling every 30 min, Telegram alerts for buy/sell signals) [DONE] ✅
- [x] HSA Receipt Auto-Categorizer (OCR + Claude classification, unreimbursed balance tracker) [DONE] ✅
- [x] eBay Listing Generator (AI-optimized 80-char titles, descriptions, pricing from market data) [DONE] ✅
- [x] RSU Vest Calendar + Tax Withholding Optimizer (12-month view, underpayment alerts) [DONE] ✅
- [x] Debt Payoff Planner (snowball vs avalanche comparison, Claude motivation tips, payoff timeline chart) [DONE] ✅
- [x] Subscription Tracker (detect recurring charges, categorize, show monthly burn, cancel recommendations) [DONE] ✅
- [x] Investment Portfolio Rebalancer (target allocation vs actual, buy/sell suggestions to rebalance) [DONE] ✅
- [x] Crypto Portfolio Tracker (multi-wallet + exchange aggregation, P&L, tax lot tracking) [DONE] ✅
- [x] Financial Goal Simulator (Monte Carlo projections, probability of success, inflation-adjusted) [DONE] ✅
- [x] Emergency Fund Tracker (3-6 month goal tracker, contribution log, Claude savings rate advice) [DONE] ✅
- [x] Tax Document Vault (upload + organize tax docs, year-over-year comparison, AI tips) [DONE] ✅
- [x] Cash Flow Forecast (30/60/90 day cash flow projection, income vs expense waterfall chart) [DONE] ✅
- [x] Savings Rate Optimizer (track savings rate over time, AI suggestions to increase it) [DONE] ✅
- [x] Bill Reminder Notifications (smart bill calendar, overdue alerts, payment history) [DONE] ✅
- [x] AI Budget Chat (natural language chat interface over your financial data, Claude-powered) [DONE] ✅

---

## MEDIUM PRIORITY

- [x] Monthly Financial Email Report (1st of month cron, Claude narrative, Gmail SMTP) [DONE] ✅
- [x] Telegram Budget Bot (natural language expense logging, Ollama NLP, Postgres write) [DONE] ✅
- [x] Rent vs Buy Calculator (Atlanta-specific, Zillow data, break-even analysis) [DONE] ✅
- [x] Stripe Revenue Dashboard (MRR, ARR, churn rate, ARPU, LTV, cohort chart) [DONE] ✅
- [x] Weekly Spending Digest (auto-generated weekly summary email, top categories) [DONE] ✅
- [x] Family Budget Sharing (multi-user shared expense categories, contribution tracker) [DONE] ✅
- [x] Loan Amortization Calculator (any loan type, extra payment scenarios, payoff chart) [DONE] ✅
- [x] Credit Score Tracker (manual entry + factor analysis, trend chart, improvement tips) [DONE] ✅
- [x] Recurring Income Tracker (freelance, dividends, rent — all recurring income sources) [DONE] ✅
- [x] Net Worth Goal Tracker (milestone tracking, milestone celebrations, trend line) [DONE] ✅
- [x] Dividend Income Tracker (portfolio dividends, yield tracking, projected annual income) [DONE] ✅
- [x] Retirement Contribution Optimizer (401k/IRA/HSA maximizer based on income + employer match) [DONE] ✅
- [x] Side Income Tracker (freelance gigs, reselling, all side hustles — P&L per stream) [DONE] ✅

> ⚠️ NOTE: "Paycheck Calculator v2" is an UPDATE to existing page 16, not a new page.
> ⚠️ NOTE: "404 Sole Archive P&L Dashboard" overlaps significantly with SoleOps P&L (page 69) — consider merging.

- [ ] **Tax Loss Harvesting Assistant** — page 74 — Scan investment portfolio for unrealized losses, wash sale warnings, optimal timing recommendations, Schedule D impact estimate
- [ ] **Net Worth Projection** — page 75 — 5/10/20 year wealth trajectory with Monte Carlo, savings rate + return assumptions, inflation-adjusted, milestone alerts
- [ ] **Insurance Tracker** — page 76 — Health, auto, renters/homeowners coverage summary, premium tracking, renewal calendar, Claude comparison tips
- [ ] **ESPP Lot Tracker** — page 77 — Track each Visa ESPP purchase period, 15% discount capture, qualifying vs disqualifying disposition calculator, optimal hold/sell timing, Schedule D export. Completely separate from RSU tracker.
- [ ] **Real-Time Tax Liability Estimator** — page 78 — YTD income + deductions + withholding → live estimated federal + GA state tax bill so no April surprises. Accounts for RSU vests, ESPP sales, side income.
- [ ] **Automated Bank Reconciliation** — page 79 — Auto-match imported transactions to expected bills/income entries. Flag unknowns, suggest categories, reduce manual work by 80%.
- [ ] **Depop Marketplace Integration** — page 80 — Add Depop to the resale ecosystem (Price Advisor + Arbitrage Scanner). Search sold comps, generate Depop-optimized listings, compare eBay vs Mercari vs Depop fees + estimated profit.
- [ ] **MCP Financial Data Server** — page 81 / utils/mcp_server.py — Expose budget data as an MCP resource so Claude can query your finances directly in Claude.ai conversations. Google Drive connector + budget DB → instant AI-powered answers about your money without opening the app.
- [ ] **SoleOps: Customer CRM** — page 82 — Track repeat buyers, buyer notes, feedback per sale, ban list, top customer insights. Turns one-time buyers into loyal customers. eBay + Mercari buyer ID import.
- [ ] **Content Performance Dashboard** — page 83 — Pull YouTube/IG/TikTok analytics into Creator Companion. Views, revenue, upload cadence, best-performing content, CPM trends. Claude AI content strategy recommendations.

---

## LOW PRIORITY

- [x] Car/Mileage Tracker (404 Sole Archive IRS deduction, $0.67/mile, Schedule C) [DONE] ✅
- [x] Cloudflare Worker edge cache (cold-start loading page, static asset cache) [DONE] ✅
- [x] Health Cost Tracker (gym + medical + HSA integration, annual summary) [DONE] ✅
- [x] Uptime Kuma status page (monitor all services, phone alerts) [DONE] ✅
- [x] Grafana + Prometheus monitoring stack (CPU, RAM, disk, container health) [DONE] ✅
- [ ] **Grocery Budget Tracker** — Kroger API or manual entry, weekly spend vs budget, smart shopping list, Claude meal-plan-to-budget optimizer
- [ ] **Home Equity Dashboard** — Zillow Zestimate, mortgage balance, equity %, appreciation rate, refinance break-even calculator
- [ ] **Habit Tracker** — Daily streaks (gym, water, sleep, journaling), ties into Health Hub, Claude motivation + streak recovery tips
- [ ] **Password Manager Integration** — 1Password or Bitwarden API, audit weak/reused passwords, breach monitoring alerts
- [ ] **Paycheck v2 Update** — UPDATE to page 16 (not new page) — Add GA state tax rates, Visa RSU supplemental withholding rate (22% federal + 6% GA), ESPP paycheck impact, pre-tax vs Roth 401k optimizer

---

## COMPLETED (pages 31–64)

| Page | Feature |
|------|---------|
| 31 | Sneaker Price Alert Bot |
| 32-33 | HSA Receipt Categorizer |
| 34 | eBay Listing Generator |
| 35 | RSU Vest Calendar |
| 36 | Monthly Financial Email Report |
| 37 | Telegram Budget Bot |
| 38 | Rent vs Buy Calculator |
| 39 | Stripe Revenue Dashboard |
| 40 | Car/Mileage Tracker |
| 41 | Health Cost Tracker |
| 42 | Uptime Kuma Status Page |
| 43 | Grafana + Prometheus Monitoring |
| 44 | Cloudflare Worker Edge Cache |
| 45 | Debt Payoff Planner |
| 46 | Subscription Tracker |
| 47 | Investment Rebalancer |
| 48 | Crypto Portfolio Tracker |
| 49 | Financial Goal Simulator |
| 50 | Emergency Fund Tracker |
| 51 | Tax Document Vault |
| 52 | Cash Flow Forecast |
| 53 | Savings Rate Optimizer |
| 54 | Bill Reminder Notifications |
| 55 | AI Budget Chat |
| 56 | Weekly Spending Digest |
| 57 | Family Budget Sharing |
| 58 | Loan Amortization Calculator |
| 59 | Credit Score Tracker |
| 60 | Recurring Income Tracker |
| 61 | Net Worth Goal Tracker |
| 62 | Dividend Income Tracker |
| 63 | Retirement Contribution Optimizer |
| 64 | Side Income Tracker |
| 65 | SoleOps Sneaker Inventory Analyzer |
| 66 | Health & Wellness AI Hub |
| 67 | Life Experience & Travel Model |
| 68 | SoleOps Price Monitor Dashboard |
| 69 | SoleOps P&L Dashboard |
| 70 | SoleOps Stripe Subscription Paywall |
| 71 | SoleOps Arbitrage Scanner |
