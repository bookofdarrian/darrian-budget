# 🍑 Darrian Belcher — Full Project Context File
### Visa Workstation Feed | Last Updated: 2026-03-10
### For: Cline, Claude Code, GitHub Copilot, Any AI assistant

> **Feed this file to your AI assistant at the start of every session.**
> This is the single source of truth for all active projects, infrastructure, agent systems, and workflows.

---

## 🧠 Who You Are Working With

**Darrian Belcher**
- TPM @ Visa Inc. (Fortune 500, payments technology)
- Georgia Tech — Data Analytics (in progress)
- 404 Sole Archive — sneaker resale business (eBay, Mercari, StockX, GOAT)
- Self-hosted homelab: CT100 @ Tailscale `100.95.125.112`
- GitHub: `bookofdarrian`
- Email: `darrian@peachstatesavings.com`
- Production Site: https://www.peachstatesavings.com

---

## 🚨 AGENT FOCUS — AS OF 2026-03-10

> **Agents: You have TWO active build targets right now. Alternate between them or pick the highest-priority uncompleted item from either product below.**

### 🔥 PRIMARY TARGET 1 — SoleOps SaaS (Revenue)
Build SoleOps into a standalone paid SaaS. **Every feature you build here has revenue potential.**
Remaining work (in priority order):
1. **SoleOps: User Registration Flow** ← BUILD THIS FIRST — email/password + Stripe checkout + welcome email via Gmail SMTP
2. **SoleOps: AI Listing Generator Polish** (page 34) — eBay API draft, Mercari variant, listing performance tracker
3. **SoleOps: Weekly Reseller Report Email** — Claude-generated cron job, per-user personalization, Telegram + email
4. **SoleOps: Stale Inventory Alert System** (page 84) — full build-out, existing skeleton at `pages/84_soleops_stale_inventory.py`
5. **SoleOps: Customer CRM** (page 82) — repeat buyer tracking, VIP buyers, ban list, communication log

### 🎓 PRIMARY TARGET 2 — College Confused (Mission)
Build College Confused as a full nonprofit college prep platform. **Every feature here helps first-gen students win.**
Remaining work (in priority order):
1. **CC: College List Builder** (page 85) — search/filter colleges, HBCU flag, compare side-by-side, save personal list
2. **CC: FAFSA Guide + EFC Calculator** (page 86) — plain-English FAFSA walkthrough, EFC/SAI calculator, deadline tracker
3. **CC: Application Tracker** (page 87) — track all schools, deadlines, requirements, decisions, Common App checklist
4. **CC: Recommendation Letter Tracker** (page 88) — log recommenders, reminders, submission status, thank-you generator
5. **CC: Interview Prep AI** (page 89) — mock interviews with Claude, behavioral Q&A bank, confidence scoring
6. **CC: Financial Aid Appeal Generator** (page 90) — Claude drafts financial aid appeal letters, award letter comparison

**College Confused agent rules:**
- CC pages: `page_icon="🎓"`, purple `#6C63FF` color scheme, `cc_` table prefix
- Always write CC content at an 8th-grade reading level — parents and grandparents use this too
- NEVER paywall any CC feature — nonprofit, 100% free
- CC sidebar links: pages 80–84 + any new CC pages added

---

## 📦 Active Projects (as of 2026-03-10)

### 1. `darrian-budget` / peachstatesavings.com
- **Status:** ACTIVE — 84 pages built and deployed to production
- **Stack:** Python 3.11+, Streamlit, PostgreSQL, Anthropic Claude `claude-opus-4-5`
- **Repo:** https://github.com/bookofdarrian/darrian-budget
- **Production:** https://www.peachstatesavings.com (CT100 homelab, Nginx proxy)
- **DB:** PostgreSQL on CT100 at `172.17.0.3:5432` (migrated off Railway 2026-02-27)
- **Agent:** Overnight autonomous AI dev system builds new pages nightly from BACKLOG.md

### 2. SoleOps — 404 Sole Archive SaaS (PRIMARY FOCUS — REVENUE)
- **Status:** ACTIVE — Pages 65–73, 84 built and deployed (all tests passing)
- **Goal:** Standalone paid SaaS for sneaker resellers — $9.99–$29.99/mo
- **Revenue Target:** $500 MRR by Day 90 | 10 beta users in 30 days
- **Pages Built:**
  - Page 65: Sneaker Inventory Analyzer (34/34 tests ✅)
  - Page 68: SoleOps Price Monitor Dashboard (58/58 tests ✅)
  - Page 69: SoleOps P&L Dashboard (58/58 tests ✅)
  - Page 70: SoleOps Stripe Subscription Paywall (58/58 tests ✅)
  - Page 71: SoleOps Arbitrage Scanner (58/58 tests ✅)
  - Page 72: Resale Price Advisor (✅)
  - Page 73: Sandbox / Privacy Mode (331/331 tests ✅)
  - Page 84: SoleOps Stale Inventory (skeleton — needs full build-out)
- **Next Up (in order):**
  - [ ] SoleOps User Registration Flow (email/password + Stripe checkout + welcome email) ← HIGHEST PRIORITY
  - [ ] SoleOps AI Listing Generator Polish — page 34 (eBay API draft, Mercari variant)
  - [ ] SoleOps Weekly Reseller Report Email (Claude-generated, cron job on CT100)
  - [ ] SoleOps Stale Inventory Alert System — page 84 (full build-out)
  - [ ] SoleOps Customer CRM — page 82 (buyer tracking, VIP list)

### 3. College Confused — Nonprofit College Prep Platform (PRIMARY FOCUS — MISSION)
- **Status:** ACTIVE — Pages 80–84 built and deployed
- **Goal:** Free AI-powered college prep for every student, family, and supporter
- **Founded by:** Darrian Belcher — 25 college acceptances, 7 full rides, $500K+ in scholarships
- **Audience:** Students (8th grade → college), parents, grandparents, first-gen families, counselors
- **Brand:** `🎓` icon, `#6C63FF` purple, plain English always, zero paywalls
- **Pages Built:**
  - Page 80: CC Home / Landing (✅)
  - Page 81: CC Timeline (✅)
  - Page 82: CC Scholarships (✅)
  - Page 83: CC Essay Station (✅)
  - Page 84: CC Test Prep / SAT/ACT (✅)
- **Next Up (in order):**
  - [ ] CC College List Builder — page 85 (college search, compare, HBCU filter, save list)
  - [ ] CC FAFSA Guide + EFC Calculator — page 86 (plain-English walkthrough + calculator)
  - [ ] CC Application Tracker — page 87 (all schools, deadlines, decisions)
  - [ ] CC Recommendation Letter Tracker — page 88 (log recommenders, reminders)
  - [ ] CC Interview Prep AI — page 89 (mock interviews with Claude)
  - [ ] CC Financial Aid Appeal Generator — page 90 (Claude-drafted appeal letters)

### 4. `sole_alert_bot/` — Production Price Alert Bot
- **Status:** PRODUCTION — runs on CT100 as a cron job
- **Function:** Polls eBay + Mercari every 30 min, fires Telegram buy/sell alerts
- **Files:** `sole_alert_bot/alert.py`, `ebay_search.py`, `mercari_search.py`, `scan_arb.py`

---

## 🏗️ Tech Stack Reference

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| UI Framework | Streamlit (stable APIs only, no `st.experimental_*`) |
| Database | SQLite (dev/local) / PostgreSQL (production) |
| AI Model | `claude-opus-4-5` (Anthropic) — always use this |
| Payments | Stripe (`utils/stripe_utils.py` — already wired) |
| Hosting | Self-hosted CT100 homelab → Nginx → peachstatesavings.com |
| Remote Access | Tailscale VPN (always-on mesh) |
| Monitoring | Grafana + Prometheus (`monitoring/` directory) |
| Alerts | Telegram bot (CT100) |
| Compression | AURA server (port 8000 on CT100 — cuts Claude API costs 40–60%) |
| Containers | Docker Compose on CT100 (Ubuntu 22.04 LXC) |
| Orchestration | Proxmox VE 9.1.1 (Beelink Mini PC) |

---

## 🏠 Homelab Infrastructure — Complete Map

### Hardware
| Component | Spec | Status |
|-----------|------|--------|
| Beelink SER Mini PC | AMD Ryzen 7, 32GB RAM, 500GB NVMe | ✅ Running 24/7 |
| TP-Link TL-SG108 Switch | 8-port Gigabit | ✅ Wired |
| UPS Battery Backup | Connected + charging | ✅ Online |
| 2x WD Red Plus 4TB HDDs | For TrueNAS RAID 1 | ⏳ Pending setup |
| Dual-bay USB 3.0 Enclosure | For bare SATA drives | ⏳ Pending |

### Network
```
Home Router (172.17.84.1)
   └── TP-Link Switch
         └── Beelink (100.117.1.50) ← Proxmox VE 9.1.1
               └── CT100 (100.117.1.171) ← Docker host (Ubuntu 22.04)
                     ├── budget-app          → port 8501  ✅
                     ├── budget-postgres     → port 5432  ✅
                     ├── AURA compression    → port 8000  ✅
                     ├── Nginx Proxy Manager → port 81    ✅
                     ├── Portainer (Docker)  → port 9000  ✅
                     ├── code-server (VS Code) → port 8080 ✅
                     ├── Grafana             → port 3000  ✅
                     ├── Prometheus          → port 9090  ✅
                     └── Alertmanager        → port 9093  ✅

Tailscale Mesh VPN (always-on, encrypted)
   ├── CT100 Tailscale IP:    100.95.125.112
   ├── MacBook Pro:           100.74.143.69
   └── iPhone:                (install from App Store)
```

### All Service URLs — Quick Reference

| Service | Local (Home WiFi) | Tailscale (Anywhere) | Public Internet |
|---------|-------------------|----------------------|-----------------|
| Budget App | http://100.117.1.171:8501 | http://100.95.125.112:8501 | https://www.peachstatesavings.com |
| AURA Health | http://100.117.1.171:8000/health | http://100.95.125.112:8000/health | — |
| Portainer | http://100.117.1.171:9000 | http://100.95.125.112:9000 | — |
| Nginx Proxy Manager | http://100.117.1.171:81 | http://100.95.125.112:81 | — |
| code-server (VS Code) | http://100.117.1.171:8080 | http://100.95.125.112:8080 | — |
| Proxmox UI | https://100.117.1.50:8006 | https://100.95.125.112:8006 | — |
| Grafana | http://100.117.1.171:3000 | http://100.95.125.112:3000 | — |
| Prometheus | http://100.117.1.171:9090 | http://100.95.125.112:9090 | — |
| Alertmanager | http://100.117.1.171:9093 | http://100.95.125.112:9093 | — |
| Immich (Photos) | http://100.117.1.171:2283 | http://100.95.125.112:2283 | — |
| Mac (SSH) | — | ssh darrianbelcher@100.74.143.69 | — |
| CT100 (SSH) | ssh root@100.117.1.171 | ssh root@100.95.125.112 | — |

### PostgreSQL Database (Production)
```
Host:     budget-postgres (Docker network: 172.17.0.3)
Port:     5432
Database: budget
User:     budget
Pass:     (stored in CT100 /opt/budget/.env)
DATABASE_URL: postgresql://budget:budget2026secure@budget-postgres:5432/budget
```
> DB was migrated from Railway → local CT100 on 2026-02-27. Railway projects deleted.

---

## 🌐 Websites Connected to Homelab

### peachstatesavings.com (LIVE)
- **How it works:** Cloudflare DNS → Home router port forward (80/443) → CT100 (100.117.1.171) → Nginx Proxy Manager → budget-app:8501
- **SSL:** Let's Encrypt via Nginx Proxy Manager (auto-renews)
- **Always on:** Docker `restart: unless-stopped` — survives reboots automatically
- **Deployment:** `git push origin main` → GitHub Actions → SSH into CT100 → `git pull` → Streamlit restart
- **Monitoring:** Grafana at http://100.95.125.112:3000 (CPU, RAM, disk, container health)
- **Uptime alerts:** Pushover push notifications → iPhone

### getsoleops.com (REGISTERED — primary domain)
- **Plan:** Separate Streamlit app on CT100 port 8502 behind Nginx
- **Timeline:** Week 2 of 30-day sprint
- **Auth:** Email/password + Stripe subscription check
- **Pricing:** Free / Starter $9.99 / Pro $19.99 / Pro+ $29.99

---

## 🤖 Autonomous AI Agent System

### Architecture Overview
```
YOU (evening): Update BACKLOG.md → go to sleep
       ↓
[11 PM CRON] Orchestrator wakes up on CT100
       ↓
CONTEXT BUILDER reads:
  ├── BACKLOG.md          (feature queue)
  ├── rule.txt            (.clinerules — coding standards)
  ├── SDLC_PROCESS.md     (pipeline rules)
  └── git log -20         (what was recently built)
       ↓
CLAUDE CODE AGENT TEAM (Sub-Agents in .claude/agents/)
  ├── planner (opus-4-5)          → feature plan, architecture, DB design
  ├── backend-engineer (sonnet-4-5) → DB helpers, APIs, business logic
  ├── ui-engineer (sonnet-4-5)    → Streamlit page, charts, forms
  ├── sole-ops-domain (sonnet-4-5) → sneaker market logic, pricing
  ├── test-engineer (haiku-4-5)   → pytest unit tests
  └── git-agent (haiku-4-5)       → branch, commit, push, PR
       ↓
QA AGENT
  ├── python3 -m py_compile (syntax check)
  ├── pytest tests/ -v (must pass)
  └── rule.txt compliance check
       ↓
GIT PIPELINE
  feature → dev → qa → staging → GitHub PR (main)
       ↓
YOU (morning): Read Telegram summary → click Approve in GitHub Actions → prod ✅
```

### Orchestrator Script
- **Location:** `/opt/overnight-dev/orchestrator.py` on CT100
- **Trigger:** `cron` at 11 PM nightly
- **Logs:** `/var/log/overnight-dev.log`
- **Notifications:** Telegram bot (morning summary + PR link)

### Claude Code Sub-Agent Files
Location: `.claude/agents/` in the repo root

| Agent File | Model | Responsibility |
|------------|-------|---------------|
| `planner.md` | claude-opus-4-5 | Architecture, feature planning, DB design |
| `backend-engineer.md` | claude-sonnet-4-5 | DB helpers, APIs, business logic |
| `ui-engineer.md` | claude-sonnet-4-5 | Streamlit pages, charts, forms |
| `sole-ops-domain.md` | claude-sonnet-4-5 | Sneaker market expertise, pricing logic |
| `test-engineer.md` | claude-haiku-4-5 | pytest unit tests |
| `git-agent.md` | claude-haiku-4-5 | Branches, commits, SDLC pipeline |

### What Makes Agents Smart About YOUR Project
The orchestrator feeds agents ALL of this context before writing a line:

| Context Source | What Agents Learn |
|---------------|-------------------|
| `rule.txt` (.clinerules) | Coding standards, sidebar pattern, auth pattern, DB pattern |
| `SDLC_PROCESS.md` | Branch naming, commit format, pipeline stages |
| `BACKLOG.md` | What to build next (agents pick highest uncompleted priority) |
| `git log --oneline -20` | What was recently built — prevents duplicates |
| `ls pages/` | What pages exist — maintains naming convention |
| DB schema query | What tables exist — avoids conflicts |
| `CLAUDE.md` | Full project context, current priorities |

### Guardrails (Hard-Coded Safety)
1. **Never deploys to production automatically** — always stops at a GitHub PR awaiting your manual approval
2. **Tests must pass** — `pytest` failure = Telegram alert, no commit
3. **Syntax checked** — `python3 -m py_compile` on every file before commit
4. **Never touches main branch** — only merges feature → dev → qa → staging
5. **Conventional commits** — every commit is formatted and traceable
6. **API key safety** — reads from `get_setting()` only, never hardcodes

### Cost
- ~$0.50–$2.00/night in Claude API tokens for a medium-complexity feature
- AURA compression on CT100 cuts that 40–60%
- **Effective cost: ~$0.25–$1.20/feature**

---

## 📋 SDLC Pipeline (Visa-Style, Non-Negotiable)

### The Pipeline
```
feature branch → dev → qa → staging → main (prod)
```

### Branch Strategy

| Branch | Purpose | Auto-Deploy | Approval |
|--------|---------|------------|---------|
| `main` | PRODUCTION (peachstatesavings.com) | After manual trigger | Manual (you only) |
| `staging` | STAGING — performance tests | Yes (if tests pass) | Auto |
| `qa` | QA — regression tests | Yes (if tests pass) | Auto |
| `dev` | DEV — CT100 homelab | Yes (if tests pass) | Auto |
| `feature/*` | Active development | No | N/A |

### Branch Naming Convention
```
feature/XX-descriptive-name   (XX = page number if applicable)
bugfix/description-of-bug
hotfix/critical-fix
chore/maintenance-task
```

### Conventional Commit Format
```
<type>: <short description (max 72 chars)>

<body: what changed and why>

<footer: closes #issue>
```
Types: `feat:` `fix:` `refactor:` `chore:` `docs:` `test:` `perf:`

### Full Feature Workflow
```bash
# 1. Create feature branch
git checkout -b feature/72-my-new-feature

# 2. Write code + tests
# Syntax check:
python3 -m py_compile pages/72_my_page.py && echo "OK"
# Run tests:
cd /Users/darrianbelcher/Downloads/darrian-budget
source venv/bin/activate
pytest tests/ -v

# 3. Commit
git add .
git commit -m "feat: add new feature

- What it does
- Why it was added"

# 4. Push + promote through pipeline
git push origin feature/72-my-new-feature
git checkout dev && git merge feature/72-my-new-feature && git push origin dev
# (verify in dev, then:)
git checkout qa && git merge dev && git push origin qa
git checkout staging && git merge qa && git push origin staging
git checkout main && git merge staging && git push origin main
# Approve in GitHub Actions → https://github.com/bookofdarrian/darrian-budget/actions
```

### Hotfix (Production Emergency)
```bash
git checkout main && git checkout -b hotfix/critical-fix
# make fix
git commit -m "fix: critical production issue"
git checkout main && git merge hotfix/critical-fix && git push origin main
# Approve immediately in GitHub Actions
```

### Quality Gates

| Gate | Checks |
|------|--------|
| Feature → Dev | Black formatting, Pylint, Flake8, pytest unit tests, Docker build |
| Dev → QA | All above + integration tests, regression tests |
| QA → Staging | All above + load tests (Locust, 100 users), memory profiling |
| Staging → Prod | All above + manual approval (you only) + pre-flight checks |

### GitHub Secrets Required
```
TAILSCALE_AUTHKEY     # For GitHub Actions → CT100 tunnel
PROD_SSH_KEY          # SSH key for CT100 (100.95.125.112)
DEV_SSH_KEY           # SSH key for CT100 dev
STAGING_SSH_KEY       # For staging environment
GITHUB_TOKEN          # Auto-created by GitHub
```

---

## 💻 Coding Standards (Non-Negotiable)

### Every Page Structure (Exact Order)
```python
import streamlit as st
# other imports...

st.set_page_config(page_title="...", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# CONSTANTS
PAGE_TITLE = "My Page"

# DB helpers
def _ensure_tables(): ...
_ensure_tables()

# Sidebar (EXACT PATTERN — all 6 links)
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
render_sidebar_user_widget()

# Page content
st.title("🍑 Page Title")
```

### Database Pattern
```python
def _ensure_tables():
    conn = get_conn()
    db_exec(conn, """CREATE TABLE IF NOT EXISTS my_table (
        id SERIAL PRIMARY KEY,     -- PostgreSQL
        -- id INTEGER PRIMARY KEY AUTOINCREMENT,  -- SQLite
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    )""")
    conn.commit()
    conn.close()

# In queries — always use ph for placeholder
ph = "%s" if USE_POSTGRES else "?"
conn = get_conn()
rows = conn.execute(f"SELECT * FROM table WHERE id = {ph}", (item_id,)).fetchall()
conn.close()
```

### AI Call Pattern
```python
api_key = get_setting("anthropic_api_key")
if not api_key:
    st.warning("⚠️ Anthropic API key not configured. Go to Settings.")
    return

import anthropic
client = anthropic.Anthropic(api_key=api_key)
response = client.messages.create(
    model="claude-opus-4-5",   # always this model
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)
result = response.content[0].text
```

### Key Utilities
| Import | Function | Use |
|--------|---------|-----|
| `utils/db.py` | `get_conn()` | Open DB connection |
| `utils/db.py` | `USE_POSTGRES` | Bool — True on production |
| `utils/db.py` | `execute as db_exec` | Run SQL with auto-retry |
| `utils/db.py` | `init_db()` | Initialize all core tables |
| `utils/db.py` | `get_setting(key)` | Read from app_settings table |
| `utils/db.py` | `set_setting(key, val)` | Write to app_settings table |
| `utils/auth.py` | `require_login()` | Block unauthenticated users |
| `utils/auth.py` | `render_sidebar_brand()` | Logo + brand in sidebar |
| `utils/auth.py` | `render_sidebar_user_widget()` | User info + logout |
| `utils/auth.py` | `inject_css()` | Global CSS |
| `utils/stripe_utils.py` | Stripe helpers | Payments, subscriptions |

### Security Rules (Absolute)
- ❌ Never commit API keys, tokens, passwords
- ❌ Never commit `.env`, `.spotify_token_cache`
- ❌ Never hardcode IPs, hostnames, or credentials in page files
- ✅ All secrets in `app_settings` table via `get_setting()` or env variables
- ✅ Always check `if not api_key:` before AI calls
- ✅ Always `conn.close()` after DB queries

---

## 🧪 Testing Requirements (Every Feature)

### Minimum Tests Per Feature
```python
# tests/unit/test_feature_name.py

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_import():
    """Page imports without errors"""
    import importlib
    spec = importlib.util.spec_from_file_location(
        "page", "pages/XX_page_name.py"
    )
    # Should not raise
    assert spec is not None

def test_ensure_tables(tmp_path, monkeypatch):
    """_ensure_tables() runs without errors"""
    from pages.XX_page_name import _ensure_tables
    _ensure_tables()  # Should not raise

def test_helper_function():
    """Core helper returns expected type"""
    from pages.XX_page_name import _some_helper
    result = _some_helper()
    assert isinstance(result, list)  # or dict, str, etc.
```

### Run Tests
```bash
cd /Users/darrianbelcher/Downloads/darrian-budget
source venv/bin/activate
pytest tests/ -v
```

### Test Files by Feature
| Test File | Covers |
|-----------|--------|
| `tests/unit/test_budget_app.py` | Core app (main reference) |
| `tests/unit/test_agent_dashboard.py` | Page 30 |
| `tests/unit/test_ai_budget_chat.py` | Page 55 |
| `tests/unit/test_bill_reminder_notifications.py` | Page 54 |
| `tests/unit/test_cash_flow_forecast.py` | Page 52 |
| `tests/unit/test_car_mileage_tracker.py` | Page 40 |
| `tests/qa/test_regression.py` | QA regression suite |

---

## 🔒 Tailscale — Remote Access Guide

### What Tailscale Does
Creates an encrypted WireGuard mesh VPN. Your homelab gets a permanent IP that works from **anywhere** — no port forwarding, no dynamic DNS.

### Your Tailscale Network
| Device | Tailscale IP | Status |
|--------|-------------|--------|
| CT100 (homelab) | `100.95.125.112` | ✅ Always on |
| MacBook Pro | `100.74.143.69` | ✅ Connected |
| iPhone | Install from App Store | ⏳ Pending |

### Tailscale Account
- Account: `dbelcher003@` (Google)
- Dashboard: https://login.tailscale.com

### How to Turn On/Off
- **Mac:** Menu bar → Tailscale icon → toggle Connected/Disconnected
- **iPhone:** Open Tailscale app → toggle VPN on/off
- **CT100:** Always on (runs as system service)

### SSH via Tailscale
```bash
# Into CT100 (homelab)
ssh root@100.95.125.112

# Into Mac (must have Remote Login enabled in System Settings → Sharing)
ssh darrianbelcher@100.74.143.69
```

### Troubleshooting Tailscale
```bash
# Check status
tailscale status

# Reconnect
tailscale up

# Check CT100 is running
ssh root@100.95.125.112 "docker ps"
```

---

## 📡 Hotspot & Remote Work Setup (Connect From Anywhere)

### Hardware Hotspot Options

#### Option 1: iPhone as Mobile Hotspot (Zero Cost — Best for Occasional Use)
- **Settings → Personal Hotspot → Allow Others to Join → ON**
- Connect Mac's WiFi to your iPhone hotspot
- Speed: LTE/5G (varies, typically 20–100 Mbps on Verizon/AT&T)
- Use case: Quick access when no WiFi available
- **Pro:** Already in your pocket
- **Con:** Drains iPhone battery fast — bring a charger

#### Option 2: Dedicated 5G Mobile Hotspot (Best for Daily/Travel Use)
Recommended devices:
| Device | Carrier | Speed | Price |
|--------|---------|-------|-------|
| **Inseego MiFi X Pro 5G** | T-Mobile/AT&T/Verizon | 5G Sub-6 / mmWave | ~$199 + plan |
| **Netgear Nighthawk M6 Pro** | AT&T/T-Mobile | 5G mmWave | ~$249 + plan |
| **Verizon Jetpack MiFi 8800L** | Verizon | LTE-A | ~$99 (with plan) |
| **GL.iNet GL-E750 (Mudi)** | Any SIM | LTE Cat-6 | ~$169 unlocked |

**Best plan for hotspot data (2026):**
- T-Mobile: $50/mo unlimited hotspot (50 Mbps throttle after 50GB)
- Verizon: $60/mo with 30GB premium, unlimited deprioritized after
- **Best deal:** Use existing phone plan hotspot data (most unlimited plans include 15–50GB hotspot)

#### Option 3: GL.iNet Travel Router (Best for Hotel/Coffee Shop Security)
- **Device:** GL.iNet GL-MT3000 "Beryl AX" (~$79) or GL-AXT1800 "Slate AX" (~$99)
- **What it does:**
  - Creates a private WiFi network from any public WiFi (hotel, airport, coffee shop)
  - Built-in OpenVPN/WireGuard client — all traffic encrypted
  - Can insert your Tailscale auth key → all devices on your travel router join your tailnet
  - Acts as a firewall between public network and your devices
- **Setup:** Plug into hotel ethernet OR connect to hotel WiFi → share as your own password-protected WiFi
- **Why it matters:** Public WiFi (hotel, Visa office WiFi for personal use, coffee shops) is untrusted. GL.iNet routes all your traffic through VPN before it hits the public network.

### Software VPN for Secure Browsing in Public

#### Primary VPN: Tailscale (Already Running — Best for Homelab Access)
Tailscale IS a VPN — all traffic between your devices is encrypted end-to-end via WireGuard. For accessing your homelab from anywhere (Visa office, coffee shop, airport), Tailscale is all you need.

**To route ALL internet traffic through your homelab via Tailscale (Exit Node):**
```bash
# On CT100 — set it as an exit node
tailscale up --advertise-exit-node

# On your Mac — route all traffic through CT100
tailscale up --exit-node=100.95.125.112 --exit-node-allow-lan-access

# On iPhone — Settings → VPN & Device Management → VPN → Exit Node → select CT100
```
> ⚠️ Enable IP forwarding on CT100 first: `echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf && sysctl -p`

#### Secondary VPN: Commercial VPN (For Browsing Privacy on Public WiFi)
When you're not routing through your homelab, use a commercial VPN:

| Service | Price | Speed | Best For |
|---------|-------|-------|---------|
| **Mullvad** | $5/mo flat | Excellent | Privacy-first, no logs, no account needed |
| **ProtonVPN** | $4/mo (Plus) | Very Good | Swiss privacy law, free tier available |
| **Cloudflare WARP** | Free / $5 Teams | Fast | Cloudflare's network, DNS security |
| **ExpressVPN** | $8/mo | Excellent | Ease of use, fast servers globally |

**Recommended setup:**
- **Tailscale** = primary VPN for homelab access (always install this first)
- **Mullvad or ProtonVPN** = secondary for general secure browsing when at hotels, airports, coffee shops
- **Never use a free VPN** — they monetize your data

#### Cloudflare WARP (Free, Zero Config)
```bash
# Mac install
brew install --cask cloudflare-warp

# Or download: https://1.1.1.1/
# WARP+ encrypts DNS + routes traffic through Cloudflare's edge
# Free tier: unlimited
# Teams tier ($3/mo): policy controls, split tunneling
```

### Tailscale + VPN Together (Recommended Stack)
```
[Your Mac] 
    → Tailscale (WireGuard, connects to homelab)
    → Mullvad/ProtonVPN (encrypts internet browsing)
    → Internet

Result: Your homelab traffic is encrypted via Tailscale.
        Your browsing traffic is encrypted via Mullvad.
        Public WiFi sees only encrypted traffic from two VPN tunnels.
```

**Note for Visa Workstation:** Never route corporate traffic through personal VPNs. Keep Tailscale + Mullvad off Visa network entirely. Use your phone hotspot for personal VPN traffic at Visa.

---

## 🖥️ Visa Workstation Setup (Windows, 12th Gen Intel i7)

### Core Software Stack (Windows)
| Tool | Purpose | Download |
|------|---------|---------|
| VS Code | Primary IDE | https://code.visualstudio.com |
| Git for Windows | Version control | https://git-scm.com/download/win |
| Python 3.11 (user install) | Local scripting | https://python.org |
| WSL2 + Ubuntu 22.04 | Linux environment | `wsl --install` in PowerShell (Admin) |
| Windows Terminal | Tabbed terminal with WSL | Microsoft Store |
| Docker Desktop | Containers (check with IT) | https://docker.com |
| Tailscale | VPN to homelab (PERSONAL use only) | https://tailscale.com/download |
| Ollama | Local AI models (zero data leakage) | https://ollama.com/download/windows |
| Obsidian | Work notes (local vault, no cloud) | https://obsidian.md |

### VS Code Extensions (Install All)
```
saoudrizwan.claude-dev          # Cline — AI coding agent
GitHub.copilot                  # AI autocomplete (get Visa enterprise license)
eamodio.gitlens                 # Git blame, history, PRs
ms-python.python                # Python dev
ms-python.pylance               # Type checking
EditorConfig.EditorConfig       # .editorconfig support
usernamehw.errorlens            # Inline error highlighting
tamasfe.even-better-toml        # pyproject.toml support
vivaxy.vscode-conventional-commits  # Commit message helper
mhutchie.git-graph              # Visual branch history
Gruntfuggly.todo-tree           # Highlights TODO/FIXME
yzhang.markdown-all-in-one      # Rich Markdown preview
```

### Git Configuration (Windows)
```powershell
git config --global user.name "Darrian Belcher"
git config --global user.email "darbelch@visa.com"      # Visa repos
git config --global core.autocrlf true
git config --global init.defaultBranch main
git config --global pull.rebase false

# For PERSONAL repos (run inside personal project folders):
git config user.email "darrian@peachstatesavings.com"
```

### WSL2 Performance Config
Create `C:\Users\darbelch\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=6
localhostForwarding=true
```

### Cline on Visa Workstation (Air-Gapped Mode)
For Visa code — NEVER send work code to external APIs:
```json
// VS Code settings.json (Visa project window only)
{
  "cline.apiProvider": "ollama",
  "cline.ollamaBaseUrl": "http://localhost:11434",
  "cline.ollamaModelId": "codellama:13b"
}
```

```powershell
# Install + run Ollama (stays on-device, zero external calls)
ollama pull codellama:13b
ollama pull llama3.2
ollama serve
```

### Tailscale on Visa Laptop (Personal Use Only)
```powershell
# Check with IT first. If approved:
winget install Tailscale.Tailscale
# Log in with PERSONAL account (dbelcher003@) — NOT Visa SSO
# Your personal tailnet is 100% separate from Visa's network
```
If IT doesn't allow Tailscale on the managed device: **use iPhone hotspot** for all homelab access — keeps it off the Visa network entirely.

### AI Separation Rules (Visa ↔ Personal)
```
✅ OK at Visa: GitHub Copilot Enterprise (Visa license, stays in GitHub org)
✅ OK at Visa: Ollama + local model (zero external calls)
✅ OK at Visa: Azure OpenAI via Visa's tenant (approved Microsoft contract)

❌ NEVER at Visa: Personal Anthropic API key on work code
❌ NEVER at Visa: Cline with Anthropic backend on Visa code
❌ NEVER at Visa: Copy Visa code to personal GitHub/homelab
❌ NEVER: Route Visa data through Tailscale, Mullvad, or personal VPN
```

### Skills Transfer: Personal → Professional
| What you build personally | Visa equivalent |
|--------------------------|----------------|
| Overnight AI Dev Orchestrator | CI/CD pipeline automation, GitHub Actions |
| BACKLOG.md + feature branches | Jira + sprint planning + PR workflow |
| `_ensure_tables()` pattern | Database migration management (Alembic, Flyway) |
| pytest unit tests | TDD/BDD — same pattern, bigger codebase |
| PostgreSQL on homelab | Enterprise PostgreSQL / Oracle at scale |
| Claude API | Azure OpenAI / AWS Bedrock (enterprise AI) |
| Grafana + Prometheus | Visa: DataDog, Splunk, PagerDuty |
| Docker + Proxmox | Kubernetes at Visa — same concepts, more replicas |
| Conventional commits | Visa code review standards, change management |

---

## 🗂️ Pages Directory — Full Reference

| Pages | Feature | Status |
|-------|---------|--------|
| app.py | Main Dashboard / Overview | ✅ Live |
| 0 | Pricing | ✅ |
| 1 | Expenses | ✅ |
| 2 | Income | ✅ |
| 3 | Business Tracker | ✅ |
| 4 | Trends | ✅ |
| 5 | Bank Import | ✅ |
| 6 | Receipts | ✅ |
| 7 | AI Insights (AURA) | ✅ |
| 8 | Goals | ✅ |
| 9 | Net Worth | ✅ |
| 10 | RSU/ESPP Tracker | ✅ |
| 11 | Portfolio | ✅ |
| 12 | Market News | ✅ |
| 13 | Backtesting | ✅ |
| 14 | Trading Bot | ✅ |
| 15 | Bills | ✅ |
| 16 | Paycheck Calculator | ✅ |
| 17 | Personal Assistant (Claude) | ✅ |
| 18 | Real Estate Bot | ✅ |
| 19 | Budget Intake | ✅ |
| 20 | Homelab Dashboard | ✅ |
| 21 | Setup / Homescreen | ✅ |
| 22 | AI To-Do | ✅ |
| 23 | Home Automation | ✅ |
| 24 | Creator Companion | ✅ |
| 25 | Notes (Apple Notes replacement) | ✅ |
| 26 | Media Library (Spotify + Apple Music) | ✅ |
| 27 | Home Assistant | ✅ |
| 28 | Smart Home Connect | ✅ |
| 29 | AI Trading Bot | ✅ |
| 30 | Agent Dashboard | ✅ |
| 31 | Sneaker Price Alert Bot | ✅ |
| 32-33 | HSA Receipt Categorizer | ✅ |
| 34 | eBay Listing Generator | ✅ |
| 35 | RSU Vest Calendar | ✅ |
| 36 | Monthly Financial Email Report | ✅ |
| 37 | Telegram Budget Bot | ✅ |
| 38 | Rent vs Buy Calculator | ✅ |
| 39 | Stripe Revenue Dashboard | ✅ |
| 40 | Car / Mileage Tracker | ✅ |
| 41 | Health Cost Tracker | ✅ |
| 42 | Uptime Kuma Status Page | ✅ |
| 43 | Grafana + Prometheus Monitoring | ✅ |
| 44 | Cloudflare Worker Edge Cache | ✅ |
| 45 | Debt Payoff Planner | ✅ |
| 46 | Subscription Tracker | ✅ |
| 47 | Investment Portfolio Rebalancer | ✅ |
| 48 | Crypto Portfolio Tracker | ✅ |
| 49 | Financial Goal Simulator | ✅ |
| 50 | Emergency Fund Tracker | ✅ |
| 51 | Tax Document Vault | ✅ |
| 52 | Cash Flow Forecast | ✅ |
| 53 | Savings Rate Optimizer | ✅ |
| 54 | Bill Reminder Notifications | ✅ |
| 55 | AI Budget Chat | ✅ |
| 56 | Weekly Spending Digest | ✅ |
| 57 | Family Budget Sharing | ✅ |
| 58 | Loan Amortization Calculator | ✅ |
| 59 | Credit Score Tracker | ✅ |
| 60 | Recurring Income Tracker | ✅ |
| 61 | Net Worth Goal Tracker | ✅ |
| 62 | Dividend Income Tracker | ✅ |
| 63 | Retirement Contribution Optimizer | ✅ |
| 64 | Side Income Tracker | ✅ |
| **65** | **SoleOps: Sneaker Inventory Analyzer** | **✅ 34/34 tests** |
| **66** | **Health & Wellness AI Hub** | **✅ 58/58 tests** |
| **67** | **Life Experience & Travel Model** | **✅ 58/58 tests** |
| **68** | **SoleOps: Price Monitor Dashboard** | **✅ 58/58 tests** |
| **69** | **SoleOps: P&L Dashboard** | **✅ 58/58 tests** |
| **70** | **SoleOps: Stripe Subscription Paywall** | **✅ 58/58 tests** |
| **71** | **SoleOps: Arbitrage Scanner** | **✅ 58/58 tests** |

---

## 📊 SoleOps — 30-Day Sprint Status

### Week 1–2 (DONE ✅)
- [x] Sneaker Inventory Analyzer (page 65)
- [x] Price Monitor Dashboard (page 68)
- [x] P&L Dashboard (page 69)
- [x] Stripe Subscription Paywall (page 70)
- [x] Arbitrage Scanner (page 71)

### Week 2–4 (IN PROGRESS)
- [ ] **User Registration Flow** — email/password reg + Stripe checkout + welcome email via Gmail SMTP
- [ ] **AI Listing Generator Polish** (page 34) — eBay API draft, Mercari variant, performance tracker
- [ ] **Weekly Reseller Report Email** — Claude-generated, cron on CT100, per-user personalization

### SoleOps Pricing Tiers
| Tier | Price | Features |
|------|-------|---------|
| Free | $0 | 5 items, manual price check only |
| Starter | $9.99/mo | 50 items, Telegram alerts, AI listings |
| Pro | $19.99/mo | Unlimited, StockX data, arb scanner |
| Pro+ | $29.99/mo | Direct API listing, multi-user, bulk import |

### Revenue Targets
| Month | Users | MRR |
|-------|-------|-----|
| Month 1 | 10 beta | $0 |
| Month 3 | 100 (50 paid) | $750 |
| Month 6 | 300 (150 paid) | $2,500 |
| Month 12 | 800 (400 paid) | $7,200 |

---

## ⚙️ Recent Git Activity (as of 2026-03-04)

```
e6d0738 chore: mark pages 65-71 SoleOps sprint DONE in BACKLOG
737e060 Merge branch 'qa' into staging
088969c Merge branch 'dev' into qa
973db16 Merge branch 'feature/66-health-wellness-hub' into dev
a289d7c feat: add SoleOps pages 66-71 with tests (58 passing)
1037fb5 chore: mark page 65 SoleOps inventory analyzer done in BACKLOG
8614150 chore: promote qa to staging (page 65 SoleOps inventory analyzer)
268fc4f chore: promote dev to qa (page 65 SoleOps inventory analyzer)
bb5a7b8 chore: merge feature/65-soleops-inventory-analyzer into dev
86807c2 feat: add SoleOps Sneaker Inventory Analyzer (page 65)
```
Current HEAD: `e6d0738` on branch `dev` (also at `origin/main`)

---

## 🚨 Recovery Commands (Homelab Emergency)

### CT100 Down
```bash
# SSH into Proxmox host
ssh root@100.117.1.50

# Restart CT100
pct start 100

# Check status
pct status 100

# If Proxmox host unreachable → physical access to Beelink → power cycle
```

### Budget App Down
```bash
ssh root@100.95.125.112  # Tailscale
cd /opt/budget
docker-compose restart budget-app

# Check logs
docker logs budget-app --tail 50

# Full restart
docker-compose down && docker-compose up -d
```

### Database Issues
```bash
ssh root@100.95.125.112
docker logs budget-postgres --tail 50

# Connect to DB directly
docker exec -it budget-postgres psql -U budget -d budget

# Backup
docker exec budget-postgres pg_dump -U budget budget > /opt/db-backups/emergency_backup_$(date +%Y%m%d).sql
```

### Deploy Latest Code to Production
```bash
ssh root@100.95.125.112
cd /opt/darrian-budget
git pull origin main
docker-compose restart budget-app
```

### Tailscale Down on CT100
```bash
# Physical access or via Proxmox console (pct console 100)
systemctl restart tailscaled
tailscale status
```

---

## 🔑 Stored Credentials Reference

All sensitive values are stored in the `app_settings` table (never in code):

| Key | Description | How to Set |
|-----|-------------|-----------|
| `anthropic_api_key` | Claude API key | Streamlit Settings page → AI Settings |
| `spotify_client_id` | Spotify OAuth | `bc2e5e4a997149f0925465cfb02508d3` |
| `spotify_client_secret` | Spotify OAuth | Settings page |
| `spotify_redirect_uri` | Spotify OAuth | `http://127.0.0.1:8501` |
| `stripe_api_key` | Stripe live/test key | Settings page |
| `telegram_bot_token` | Telegram bot | CT100 `/etc/environment` |
| `telegram_chat_id` | Your Telegram chat | CT100 `/etc/environment` |

**To read/write from Python:**
```python
from utils.db import get_setting, set_setting
api_key = get_setting("anthropic_api_key")
set_setting("some_key", "some_value")
```

---

## 📁 Key Files Quick Reference

| File | What It Is |
|------|-----------|
| `app.py` | Main Streamlit entry point |
| `BACKLOG.md` | Autonomous dev queue (agents read this nightly) |
| `CLAUDE.md` | Claude Code startup context (this type of file) |
| `rule.txt` | `.clinerules/` — all coding standards for agents |
| `SDLC_PROCESS.md` | Full SDLC pipeline documentation |
| `AUTONOMOUS_AI_DEV_SYSTEM.md` | How the overnight agent system works |
| `SOLE_OPS_ROADMAP.md` | SoleOps SaaS 90-day product roadmap |
| `HOMELAB_HOSTING_GUIDE.md` | Full homelab setup phases 1–8 |
| `TAILSCALE_GUIDE.md` | Remote access and VPN guide |
| `HOMELAB_PROGRESS.md` | Master checklist — what's done/pending |
| `VISA_WORKSTATION_SETUP.md` | Windows workstation setup guide |
| `RECOVERY_COMMANDS.md` | Emergency homelab recovery procedures |
| `utils/db.py` | DB connection, get_conn, get_setting, set_setting |
| `utils/auth.py` | require_login, sidebar helpers, inject_css |
| `utils/stripe_utils.py` | Stripe payment processing |
| `aura/server.py` | AURA AI compression server |
| `monitoring/docker-compose.yml` | Grafana + Prometheus stack |
| `sole_alert_bot/alert.py` | Production price alert bot |

---

## 🎯 What to Work On Next (Priority Order)

### 🔥 SoleOps — Immediate (Revenue)
1. **SoleOps: User Registration Flow** ← BUILD FIRST — email/password + Stripe checkout + welcome email via Gmail SMTP
2. **SoleOps: AI Listing Generator Polish** (page 34) — eBay API draft, Mercari variant, performance tracker
3. **SoleOps: Weekly Reseller Report Email** — Claude-generated cron job, per-user personalization
4. **SoleOps: Stale Inventory Alert System** (page 84) — full build-out of existing skeleton
5. **SoleOps: Customer CRM** — repeat buyer tracking, VIP buyers, communication log

### 🎓 College Confused — Immediate (Mission)
1. **CC: College List Builder** (page 85) — college search/filter, HBCU flag, compare, save list
2. **CC: FAFSA Guide + EFC Calculator** (page 86) — plain-English FAFSA + SAI calculator
3. **CC: Application Tracker** (page 87) — all schools, deadlines, decisions, Common App checklist
4. **CC: Recommendation Letter Tracker** (page 88) — log recommenders, track submission status
5. **CC: Interview Prep AI** (page 89) — mock interviews with Claude, behavioral Q&A bank
6. **CC: Financial Aid Appeal Generator** (page 90) — Claude-drafted appeal letters

### Later (After SoleOps + CC complete)
- Tax Loss Harvesting Assistant (page 74)
- Net Worth Projection Engine (page 75)
- Real-Time Tax Liability Estimator (page 78)
- ESPP Lot Tracker (page 77)
- Paycheck Calculator v2 (UPDATE page 16)

### Infrastructure
- [ ] Install Tailscale on iPhone (App Store → `dbelcher003@`)
- [ ] Deploy Grafana monitoring stack (`cd /opt/monitoring && docker-compose up -d`)
- [ ] Import Grafana dashboard 1860 (http://100.95.125.112:3000)
- [ ] Set up TrueNAS RAID 1 (when WD Red drives arrive)
- [ ] Deploy Immich (http://100.95.125.112:2283) for photo backup
- [ ] Delete Railway projects at https://railway.app

---

*Context file generated: 2026-03-04*
*Stack: Python 3.11 · Streamlit · PostgreSQL · Claude claude-opus-4-5 · Tailscale · Proxmox · Docker · Nginx*
*Production: peachstatesavings.com | Homelab: CT100 @ 100.95.125.112*
*Owner: Darrian Belcher | darrian@peachstatesavings.com*
