# CLAUDE.md — Darrian Belcher's Project Context
**Last Updated: 2026-03-10**

> This file is read by Claude Code at startup. It contains everything needed to
> understand the project, standards, and current priorities.

---

## 🎯 PRIMARY GOALS RIGHT NOW: SoleOps SaaS + College Confused

### 🔥 Goal 1 — SoleOps (Monetization Priority)
**Finish and launch SoleOps as a standalone paid SaaS for sneaker resellers:**
- Pages 65–73 built and deployed — core feature set complete
- NOW: Close the remaining revenue gaps below
- Pricing: $9.99/mo (Starter), $19.99/mo (Pro), $29.99/mo (Pro+)
- Goal: 10 beta users in 30 days, $500 MRR by Day 90
- Distribution: r/flipping, r/sneakermarket, reseller Discord servers

**SoleOps remaining work (build in this order):**
1. **User Registration Flow** — email/password reg + Stripe checkout + welcome email (HIGHEST PRIORITY)
2. **AI Listing Generator Polish** (page 34) — eBay API draft, Mercari variant, performance tracker
3. **Weekly Reseller Report Email** — Claude-generated cron, per-user personalization
4. **Stale Inventory Alert System** (page 84) — already has skeleton, needs full build-out
5. **SoleOps Customer CRM** (page 82) — repeat buyer tracking, VIP buyers, ban list

**Existing SoleOps assets:**
- `sole_alert_bot/` — full price alert bot (eBay + Mercari + arb detection)
- `pages/31_sneaker_price_alert_bot.py` — Streamlit UI for alerts
- `pages/34_ebay_listing_generator.py` — AI listing generator (needs polish)
- `pages/65–71, 73, 84` — full SoleOps feature suite
- `utils/stripe_utils.py` — Stripe payments already wired
- `utils/db.py` — shared DB utilities

---

### 🎓 Goal 2 — College Confused (Mission Priority)
**Build out College Confused as a full nonprofit college prep platform:**
- Nonprofit founded by Darrian Belcher (25 acceptances, 7 full rides, $500K+ in scholarships)
- Target users: Students, parents, first-gen families, school counselors, community mentors
- 100% FREE — no paywalls, no subscriptions, no gatekeeping ever
- Pages 80–84 built: Home, Timeline, Scholarships, Essay Station, SAT/ACT Prep
- Domain: collegeconfused.org (planned standalone site)

**College Confused remaining work (build in this order):**
1. **CC: College List Builder** (page 85) — search/filter colleges by major, location, cost, acceptance rate, HBCU; save to personal list; compare side-by-side
2. **CC: FAFSA Guide + EFC Calculator** (page 86) — step-by-step FAFSA walkthrough, plain-English EFC/SAI calculator, dependency status guide, deadline tracker
3. **CC: Application Tracker** (page 87) — track all schools applied to, deadlines, requirements, decisions, scholarship status; Common App checklist
4. **CC: Recommendation Letter Tracker** (page 88) — log recommenders, send reminders, track submission status, thank-you note generator
5. **CC: Interview Prep AI** (page 89) — mock interview Q&A with Claude, college-specific interview tips, behavioral question bank, confidence score
6. **CC: Financial Aid Appeal Generator** (page 90) — Claude drafts professional financial aid appeal letters, comparator award letter analyzer

**College Confused context for agents:**
- All CC pages use `🎓` icon and `#6C63FF` purple color scheme
- CC sidebar: `render_sidebar_brand()` + CC section links (80–84 + new pages)
- CC pages are for a PUBLIC audience — write for 8th graders and grandparents (plain English)
- NEVER paywall CC features — this is a nonprofit
- AI calls use same `claude-opus-4-5` pattern via `get_setting("anthropic_api_key")`
- CC tables prefixed with `cc_` (e.g., `cc_timeline`, `cc_scholarships`, `cc_support_emails`)

---

## 📦 Projects in This Repo

### 1. darrian-budget / peachstatesavings.com (ACTIVE — secondary focus)
- Personal finance app, 63+ pages built and deployed
- Self-hosted on CT100 homelab @ 100.95.125.112, Nginx → peachstatesavings.com
- Autonomous overnight AI dev system builds new pages nightly
- Stack: Python 3.11+, Streamlit, PostgreSQL, Claude API

### 2. SoleOps / 404 Sole Archive SaaS (ACTIVE — primary focus)
- Sneaker reseller operations platform being extracted from darrian-budget
- Stack: Same as above + Stripe paywall
- GitHub: https://github.com/bookofdarrian/darrian-budget (same repo for now)

### 3. sole_alert_bot/ (PRODUCTION)
- Standalone price alert bot running on CT100 as a cron job
- Polls eBay + Mercari every 30 min, fires Telegram alerts

---

## 🤖 Agent Team (Claude Code Sub-Agents)

This project uses Claude Code Agent Teams. Agents are in `.claude/agents/`:

| Agent | Model | Role |
|-------|-------|------|
| `planner` | **claude-opus-4-5** | Architecture, feature planning, DB design |
| `backend-engineer` | **claude-sonnet-4-5** | DB helpers, APIs, business logic |
| `ui-engineer` | **claude-sonnet-4-5** | Streamlit pages, charts, forms |
| `sole-ops-domain` | **claude-sonnet-4-5** | Sneaker market expertise, pricing logic |
| `test-engineer` | **claude-haiku-4-5** | pytest unit tests |
| `git-agent` | **claude-haiku-4-5** | Branches, commits, SDLC pipeline |

**Workflow for any new feature:**
1. `planner` → design and plan
2. `sole-ops-domain` → validate business logic (for SoleOps features)
3. `backend-engineer` → write DB + helpers
4. `ui-engineer` → write Streamlit page
5. `test-engineer` → write + run tests
6. `git-agent` → branch, commit, push, PR

---

## 🏗️ SDLC Pipeline

```
feature branch → dev → qa → staging → main (prod)
```

- Branch naming: `feature/XX-page-name`, `bugfix/description`, `hotfix/fix`
- Conventional commits: `feat:`, `fix:`, `refactor:`, `chore:`, `test:`
- Tests MUST pass before committing
- NEVER push directly to `main`

---

## 💻 Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| UI Framework | Streamlit (stable APIs only) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI | Anthropic Claude (claude-opus-4-5) |
| Payments | Stripe (stripe_utils.py already wired) |
| Hosting | Self-hosted CT100 @ 100.95.125.112, Tailscale |
| Domain | peachstatesavings.com (Nginx proxy) |
| Monitoring | Grafana + Prometheus (monitoring/ dir) |
| Alerts | Telegram bot |

---

## 📐 Coding Standards (Non-Negotiable)

### Page Structure (every page, in this exact order)
```python
import streamlit as st
# imports...

st.set_page_config(page_title="...", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# Constants
SOME_CONST = "value"

# DB helpers
def _ensure_tables(): ...
_ensure_tables()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
render_sidebar_user_widget()

# Content
st.title("🍑 Page Title")
```

### Database
- `_ensure_tables()` at module load
- `get_conn()` + `conn.close()` always
- SQLite placeholder: `?` | PostgreSQL placeholder: `%s`
- Use `ph = "%s" if USE_POSTGRES else "?"` for dynamic queries

### AI Calls
```python
api_key = get_setting("anthropic_api_key")
if not api_key:
    st.warning("API key not configured")
    return
# model: claude-opus-4-5 always
```

### No hardcoded: API keys, tokens, IPs, passwords, credentials

---

## 📋 Current Backlog (High Priority)

See `BACKLOG.md` for the full queue.

### 🔥 SoleOps — Immediate (Revenue Unlocking)
1. **SoleOps: User Registration Flow** — email/password + Stripe checkout + welcome email ← BUILD FIRST
2. **SoleOps: AI Listing Generator Polish** (page 34) — eBay API draft, Mercari variant, perf tracker
3. **SoleOps: Weekly Reseller Report Email** — Claude-generated cron job, per-user
4. **SoleOps: Stale Inventory Alert System** (page 84) — full build-out of existing skeleton
5. **SoleOps: Customer CRM** (page 82) — buyer tracking, VIP list

### 🎓 College Confused — Immediate (Platform Growth)
1. **CC: College List Builder** (page 85) — college search, compare, save personal list
2. **CC: FAFSA Guide + EFC Calculator** (page 86) — plain-English FAFSA walkthrough
3. **CC: Application Tracker** (page 87) — all schools, deadlines, decisions
4. **CC: Recommendation Letter Tracker** (page 88) — log recommenders, track submissions
5. **CC: Interview Prep AI** (page 89) — mock interviews with Claude, behavioral Q&A bank

See `SOLE_OPS_ROADMAP.md` for the full SoleOps product plan.

---

## 🔑 Key Files to Know

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app entry point |
| `utils/db.py` | DB connection, get_setting, set_setting |
| `utils/auth.py` | require_login, sidebar helpers, inject_css |
| `utils/stripe_utils.py` | Stripe payment processing |
| `sole_alert_bot/alert.py` | Price alert bot (production) |
| `sole_alert_bot/ebay_search.py` | eBay API client |
| `sole_alert_bot/mercari_search.py` | Mercari search |
| `sole_alert_bot/scan_arb.py` | Arbitrage scanner |
| `BACKLOG.md` | Overnight AI dev feature queue |
| `SOLE_OPS_ROADMAP.md` | SoleOps SaaS product roadmap |
| `AUTONOMOUS_AI_DEV_SYSTEM.md` | How the overnight agent system works |

---

## 🔒 Security Rules

- Never commit `.env`, API keys, tokens, passwords
- Never commit `.spotify_token_cache`
- All secrets in `app_settings` table or environment variables
- No hardcoded IPs or hostnames

---

## 👤 Owner

**Darrian Belcher** | darrian@peachstatesavings.com
- TPM at Visa (Fortune 500)
- GT Data Analytics (in progress)
- 404 Sole Archive — sneaker resale business
- Self-hosted homelab: CT100 @ 100.95.125.112 (Tailscale)
