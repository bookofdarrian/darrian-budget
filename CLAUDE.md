# CLAUDE.md — Darrian Belcher's Project Context
**Last Updated: 2026-03-10**

> This file is read by Claude Code at startup. It contains everything needed to
> understand the project, standards, and current priorities.

---

## 🚨 CRITICAL ANTI-PATTERNS — Production Killers

> See `BUGFIX_PATTERNS.md` for full details on each bug, root causes, and fixes.
> These patterns WILL crash the app in production (PostgreSQL) even though they work in dev (SQLite).

### ❌ #1 — `conn.execute()` — CRASHES ON POSTGRESQL
```python
# ❌ NEVER DO THIS:
conn.execute("CREATE TABLE IF NOT EXISTS ...")
rows = conn.execute("SELECT * FROM ...").fetchall()

# ✅ ALWAYS DO THIS:
from utils.db import execute as db_exec
db_exec(conn, "CREATE TABLE IF NOT EXISTS ...")
rows = db_exec(conn, "SELECT * FROM ...").fetchall()
```
**Root cause:** SQLite allows `connection.execute()` but psycopg2 does NOT. Use `db_exec(conn, ...)` always.
**Detection:** `grep -rn "conn\.execute(" pages/ --include="*.py"` (must return empty)

### ❌ #2 — `conn.executescript()` — CRASHES ON POSTGRESQL
```python
# ❌ NEVER: conn.executescript("CREATE TABLE a; CREATE TABLE b;")
# ✅ ALWAYS: separate db_exec() calls, one per statement
```

### ❌ #3 — Direct `?` placeholders with raw psycopg2 cursor
Use `db_exec()` which auto-translates `?` → `%s` for PostgreSQL.

### ❌ #4 — Hardcoded API keys
```python
# ❌ NEVER: api_key = "sk-ant-abc123"
# ✅ ALWAYS: api_key = get_setting("anthropic_api_key")
```

### ❌ #5 — `st.experimental_rerun()`
```python
# ❌ NEVER: st.experimental_rerun()
# ✅ ALWAYS: st.rerun()
```

### PRE-COMMIT SCAN (Run before EVERY commit)
```bash
# These must ALL return empty output:
grep -rn "conn\.execute(" pages/ --include="*.py"
grep -rn "conn\.executescript(" pages/ --include="*.py"  
grep -rn "experimental_rerun" pages/ --include="*.py"
```

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

### 🏗️ Build Agents
| Agent | Model | Role |
|-------|-------|------|
| `planner` | **claude-opus-4-5** | Architecture, feature planning, DB design |
| `backend-engineer` | **claude-sonnet-4-5** | DB helpers, APIs, business logic |
| `ui-engineer` | **claude-sonnet-4-5** | Streamlit pages, charts, forms |
| `sole-ops-domain` | **claude-sonnet-4-5** | Sneaker market expertise, pricing logic |
| `test-engineer` | **claude-haiku-4-5** | pytest unit tests |
| `git-agent` | **claude-haiku-4-5** | Branches, commits, SDLC pipeline |

### 🧠 Intelligence Agents (Personal Strategy)
| Agent | Model | Role |
|-------|-------|------|
| `morning-briefing` | **claude-opus-4-5** | Daily prioritized action plan from brain dump |
| `business-strategist` | **claude-opus-4-5** | Business idea evaluation, market sizing, MVP plans |
| `soleops-intel` | **claude-opus-4-5** | Sneaker resale market intelligence, pricing, platforms |
| `health-coach` | **claude-opus-4-5** | Health, wellness, and energy management |
| `cc-content-creator` | **claude-opus-4-5** | Creator content strategy and planning |
| `ai-career-intelligence` | **claude-opus-4-5** | AI/tech layoff tracking + career defense, filtered for Darrian's profile |
| `ai-tools-researcher` | **claude-opus-4-5** | Evaluates new AI tools against Darrian's actual stack — no hype |
| `resume-reviewer` | **claude-opus-4-5** | Red-lines resume + LinkedIn with recruiter eye — paste content, get rewrites |

### 🤖 AI Career Intelligence Agent — How to Use
The `ai-career-intelligence` agent is your personal career defense system. Use it when:
- You want a current briefing on AI/tech layoff landscape (TPM-specific)
- You want to know which AI tools to adopt and WHY they matter for your specific situation
- You need concrete career positioning moves — not generic advice

**Prompt it with:** "Give me a career intelligence briefing" or "Research [specific tool]" or "What should I be doing this week for career protection?"

**Key context file it uses:** `AI_CAREER_INTEL.md` (living research document — update as your situation changes)

### 🔬 AI Tools Researcher Agent — How to Use
The `ai-tools-researcher` agent evaluates specific tools OR does weekly sweeps across 7 research categories. Use it when:
- A new AI tool is trending and you want to know if it matters for YOUR stack
- You want a weekly sweep of what's worth adopting
- You want to know what competitors are building in the SoleOps/PSS space

**Prompt it with:** "Evaluate [tool name]" or "Do a weekly AI tools sweep" or "What's entering the sneaker resale AI space?"

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
# ⚠️ CRITICAL: Do NOT put emojis in label= when icon= is also set.
# Streamlit renders icon= as the left icon AND also renders label= text.
# Emoji in both = doubled icons on every page. Use icon= only for the emoji.
st.sidebar.page_link("app.py",                          label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",               icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",            icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",              icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",      icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant", icon="🤖")
st.sidebar.page_link("pages/147_proactive_ai_engine.py",label="Proactive AI",       icon="🧠")
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

## 🚨 DEPLOYMENT ARCHITECTURE — READ BEFORE EVERY DEPLOY

**This is the actual production setup. Getting this wrong means changes don't appear.**

### Port Map (CT100 @ 100.95.125.112)
| Port | Service | What it serves |
|------|---------|----------------|
| **8501** | `darrian-budget` **Docker container** | **PSS + College Confused + SoleOps** — ALL sites route here via Nginx Proxy Manager |
| 8502 | `college-confused` systemd service | Secondary / legacy — NOT what the browser hits |
| 8503 | (unused / old deploy target) | |

### Reverse Proxy
- **Nginx Proxy Manager** runs as a Docker container (`nginx-proxy-manager`)
- ALL domain routing (`peachstatesavings.com`, `collegeconfused.org`, `soleops.app`) goes through NPM → port 8501
- There is NO `/etc/nginx/sites-enabled/` — standard nginx is NOT used

### Code Update Flow
```
git push origin main
→ ssh root@100.95.125.112
→ cd /opt/darrian-budget && git pull origin main
→ docker restart darrian-budget   ← THIS IS THE REQUIRED STEP
```

### ⚠️ CRITICAL: git pull alone is NOT enough
The `darrian-budget` Docker container mounts `/opt/darrian-budget:/app` as a volume.
File changes from `git pull` ARE reflected immediately on disk inside the container.
BUT **Streamlit caches page modules in memory** — the old page code stays loaded until the container restarts.

**NEVER say "try a hard refresh" without first:**
1. Checking which port/service the domain actually routes to (`docker ps`, check NPM)
2. Restarting the correct container: `docker restart darrian-budget`
3. Verifying the content is correct inside the container: `docker exec darrian-budget grep 'search_term' /app/pages/XX_page.py`

### The full correct deploy command after any code change:
```bash
ssh root@100.95.125.112 "cd /opt/darrian-budget && git pull origin main && docker restart darrian-budget && sleep 5 && docker exec darrian-budget grep -c 'expected_string' /app/pages/XX_page.py && echo LIVE"
```

---

## 👤 Owner

**Darrian Belcher** | darrian@peachstatesavings.com
- TPM at Visa (Fortune 500)
- GT Data Analytics (in progress)
- 404 Sole Archive — sneaker resale business
- Self-hosted homelab: CT100 @ 100.95.125.112 (Tailscale)
