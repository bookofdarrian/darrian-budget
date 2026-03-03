# Feature Backlog — Autonomous AI Dev Queue
**Owner: Darrian Belcher | Updated: 2026-03-03**

> The overnight AI dev system reads this file every night and picks the
> highest-priority uncompleted item to build autonomously.
> Completed items are marked [DONE] ✅ by the Git Agent.

---

## ⭐ HIGHEST PRIORITY — Darrian's Personal Vision Features

**THESE MUST BE BUILT NEXT — in this exact order:**

- [ ] Sneaker Inventory Analyzer — page 65 — Build on top of the sneaker bot. Analyze inventory across eBay+Mercari+StockX+GOAT. Track days-listed and velocity per SKU. Age-based pricing: if listed 7+ days suggest 5% drop, 14+ days 10%, 30+ days 15%. Profit margin alerts (show COGS vs current price). Auto-suggest price drops for slow movers. Smart price offer tool for apps that support offers (Mercari). Telegram alert when inventory stalls. Charts showing days-on-market vs sale price vs profit.
- [ ] Health & Wellness AI Hub — page 66 — Workout assistant + mental health hub. DB tables: workouts, medications, mood_logs, health_goals, doctor_visits, vaccines. Connect to Apple Health via exported CSV upload. Medication tracker for ADHD/bipolar/anxiety meds (dosage, schedule, refill reminders). Mood tracking journal with Claude-powered pattern analysis. Recommended workout plans based on body type + preferred exercises (user fills profile). Doctor/dentist visit reminders + vaccine tracker. Upload psych eval PDF + family history for Claude preventative health insights. Daily check-in widget.
- [ ] Life Experience & Travel Model — page 67 — Travel advisor on steroids. DB tables: trips, flights, hotels, memories, ubers, life_milestones. Store trips, flights, Ubers, memories, hotel stays. Connect to Google Calendar API to find available travel windows. AI weekend trip recommendations based on budget + preferences + history. Kayak/Google Flights search via RapidAPI for live pricing. Travel journal with photo uploads (stored in DB). Life milestones timeline. Claude-powered travel insights and destination recommendations based on past trips.

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
- [ ] Tax Loss Harvesting Assistant (scan portfolio for unrealized losses, wash sale warnings, optimize timing)
- [ ] Net Worth Projection (5/10/20 year wealth trajectory with savings rate + investment return assumptions)
- [ ] Paycheck Calculator v2 (federal + GA state + FICA + Visa RSU supplement rate wizard)
- [ ] 404 Sole Archive P&L Dashboard (per-sneaker profit, COGS, platform fees, net margin per sale)
- [ ] Insurance Tracker (health, auto, renters — coverage summary, premium tracking, renewal alerts)

---

## LOW PRIORITY

- [x] Car/Mileage Tracker (404 Sole Archive IRS deduction, $0.67/mile, Schedule C) [DONE] ✅
- [x] Cloudflare Worker edge cache (cold-start loading page, static asset cache) [DONE] ✅
- [x] Health Cost Tracker (gym + medical + HSA integration, annual summary) [DONE] ✅
- [x] Uptime Kuma status page (monitor all services, phone alerts) [DONE] ✅
- [x] Grafana + Prometheus monitoring stack (CPU, RAM, disk, container health) [DONE] ✅
- [ ] Grocery Budget Tracker (Kroger API or manual entry, weekly spend vs budget, smart shopping list)
- [ ] Home Equity Dashboard (Zillow Zestimate, mortgage balance, equity %, appreciation rate)
- [ ] Habit Tracker (daily streaks — gym, water, sleep, journaling — ties into Health Hub)
- [ ] Password Manager Integration (1Password or Bitwarden API — audit weak/reused passwords)

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
