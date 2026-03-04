# CLAUDE.md — Darrian Belcher's Project Context
**Last Updated: 2026-03-04**

> This file is read by Claude Code at startup. It contains everything needed to
> understand the project, standards, and current priorities.

---

## 🎯 PRIMARY GOAL RIGHT NOW: 404 Sole Archive → SoleOps SaaS

**The #1 focus for the next 30 days is launching SoleOps:**
- Extract sneaker tools from darrian-budget into a standalone SaaS product
- Target users: eBay/Mercari/StockX/GOAT sneaker resellers
- Pricing: $9.99/mo (Starter), $19.99/mo (Pro), $29.99/mo (Pro+)
- Goal: 10 beta users in 30 days, 100 paying users in 90 days
- Distribution: r/flipping, r/sneakermarket, reseller Discord servers

**Existing assets to reuse:**
- `sole_alert_bot/` — full price alert bot (eBay + Mercari + arb detection)
- `pages/31_sneaker_price_alert_bot.py` — Streamlit UI for alerts
- `pages/34_ebay_listing_generator.py` — AI listing generator (80% done)
- `pages/64_side_income_tracker.py` — P&L tracking foundation
- `utils/stripe_utils.py` — Stripe payments already wired
- `utils/db.py` — shared DB utilities

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

See `BACKLOG.md` for the full queue. Highest priority SoleOps features:

1. **Sneaker Inventory Analyzer** (page 65) — inventory aging, price velocity, auto-price-drop suggestions
2. **Health & Wellness AI Hub** (page 66) — personal use
3. **Life Experience & Travel Model** (page 67) — personal use

See `SOLE_OPS_ROADMAP.md` for the full SaaS product plan.

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
