# Autonomous Overnight AI Dev System — Darrian Belcher
**Created: 2026-03-02 | Owner: Darrian Belcher**

> **TL;DR:** Multiple specialized AI coding agents work through your SDLC pipeline
> while you sleep. You wake up, review a GitHub PR summary, and click ONE button
> to approve the final deploy to production. Everything else is fully automated.

---

## Is This Possible?

**Yes — and you already have 80% of the infrastructure.**

Your homelab (CT100, Proxmox, Postgres, Tailscale), your SDLC pipeline
(feature → dev → qa → staging → main), your `.clinerules/rule.txt` context,
and your use-case backlog (`NEXT_USECASES.md`, `HOMELAB_USECASES.md`) are the
exact ingredients needed. The missing piece is an **orchestrator script** that
wakes up at night, picks a use case, spins up Cline agents with full project
context, and shepherds the work through the pipeline.

---

## System Architecture

```
YOU (evening): Add feature ideas to BACKLOG.md, go to sleep
       ↓
[11 PM CRON] Orchestrator wakes up on CT100
       ↓
CONTEXT BUILDER
  ├── Reads BACKLOG.md (your feature queue)
  ├── Reads rule.txt (.clinerules — your coding standards)
  ├── Reads SDLC_PROCESS.md (pipeline rules)
  ├── Reads NEXT_USECASES.md + HOMELAB_USECASES.md (use cases)
  └── Reads recent git log (what was already built)
       ↓
PLANNER AGENT (Claude Opus — "the architect")
  ├── Picks the highest-priority backlog item
  ├── Breaks it into subtasks
  └── Assigns subtasks to specialist agents
       ↓
PARALLEL SPECIALIST AGENTS (Claude Opus or Haiku)
  ├── Agent 1: DB Schema Bot — writes _ensure_tables(), migrations
  ├── Agent 2: Backend Bot — writes helper functions, DB queries
  ├── Agent 3: UI Bot — writes Streamlit page with sidebar standard
  └── Agent 4: Test Bot — writes pytest unit tests
       ↓
QA AGENT (Claude Opus — "the reviewer")
  ├── Runs python3 -m py_compile on every new file
  ├── Runs pytest tests/ -v
  ├── Checks rule.txt compliance (sidebar, auth, db patterns)
  └── Auto-fixes issues or flags them for morning review
       ↓
GIT AGENT
  ├── git checkout -b feature/<name>
  ├── git commit (conventional commits format)
  ├── git push origin feature/<name>
  ├── Merges feature → dev → qa → staging
  └── Opens GitHub PR: feature → main with full summary
       ↓
YOU (morning): Read the Telegram summary + GitHub PR
  └── Click "Approve" in GitHub Actions → deploys to production ✅
```

---

## The Three Files You Maintain (That's It)

### 1. `BACKLOG.md` — Your Feature Queue

```markdown
## Priority Queue (agents pick from top)

### HIGH
- [ ] Sneaker Price Alert Bot (eBay + Mercari polling, Telegram alerts)
- [ ] HSA Receipt Auto-Categorizer (OCR + Claude classification)
- [ ] eBay Listing Generator (AI-optimized titles + descriptions)

### MEDIUM
- [ ] RSU Vest Calendar + Tax Withholding Optimizer
- [ ] Monthly Financial Email Report (cron → Gmail SMTP)
- [ ] Telegram Budget Bot (natural language expense logging)

### LOW
- [ ] Car/Mileage Tracker for 404 Sole Archive tax deductions
- [ ] Cloudflare Worker edge cache for peachstatesavings.com
```

Agents read this every night. Completed items get checked off automatically.

### 2. `.clinerules/rule.txt` — Already Exists ✅

Your existing rule.txt IS the agent's coding standard. Every agent reads it
before writing a single line. This is why your code stays consistent.

### 3. `CONTEXT_SNAPSHOT.md` — Auto-Generated Each Night

The orchestrator builds this before agents start. It includes:
- Current git log (last 20 commits)
- List of existing pages and their purposes
- Current DB schema (tables that exist)
- Any errors from previous night's run

---

## Orchestrator Script

Save this as `/opt/overnight-dev/orchestrator.py` on CT100:

```python
#!/usr/bin/env python3
"""
Overnight AI Dev Orchestrator
Runs nightly at 11 PM, picks a backlog item, builds it through the SDLC.
"""
import os, subprocess, json, time, requests
from datetime import datetime
from pathlib import Path
import anthropic

REPO_PATH     = "/opt/darrian-budget"
BACKLOG_PATH  = f"{REPO_PATH}/BACKLOG.md"
RULES_PATH    = "/Users/darrianbelcher/Documents/Cline/Rules/rule.txt"
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
API_KEY        = os.environ["ANTHROPIC_API_KEY"]

client = anthropic.Anthropic(api_key=API_KEY)

def notify(msg: str):
    """Send Telegram notification."""
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
        timeout=10
    )

def run(cmd: str, cwd: str = REPO_PATH) -> tuple[int, str]:
    """Run shell command, return (returncode, output)."""
    r = subprocess.run(cmd, shell=True, cwd=cwd,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr

def build_context() -> str:
    """Build full project context for agents."""
    _, git_log = run("git log --oneline -20")
    _, pages   = run("ls pages/")
    _, tables  = run("""python3 -c "
import sqlite3, os
db = 'data/budget.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
    print([t[0] for t in tables])
    conn.close()
" """)
    rules = Path(RULES_PATH).read_text() if Path(RULES_PATH).exists() else ""
    backlog = Path(BACKLOG_PATH).read_text()
    sdlc = Path(f"{REPO_PATH}/SDLC_PROCESS.md").read_text()[:3000]

    return f"""
=== PROJECT CONTEXT ===
Repo: /opt/darrian-budget (bookofdarrian/darrian-budget)
Stack: Python, Streamlit, SQLite/PostgreSQL, Anthropic Claude
Production: peachstatesavings.com (CT100 homelab)

=== RECENT GIT HISTORY ===
{git_log}

=== EXISTING PAGES ===
{pages}

=== DB TABLES ===
{tables}

=== CODING RULES (.clinerules) ===
{rules[:2000]}

=== SDLC PROCESS ===
{sdlc}

=== FEATURE BACKLOG ===
{backlog}
"""

def pick_next_feature(context: str) -> dict:
    """Use Claude to pick the best next feature and create a plan."""
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are the Planner Agent for Darrian's budget app.

{context}

Pick the single highest-priority uncompleted item from the backlog.
Return JSON with:
{{
  "feature_name": "short kebab-case name",
  "description": "what it does",
  "page_file": "pages/XX_name.py",
  "branch_name": "feature/XX-name",
  "subtasks": ["list", "of", "subtasks"],
  "estimated_complexity": "low|medium|high"
}}

Only return valid JSON, no explanation."""
        }]
    )
    return json.loads(msg.content[0].text)

def write_feature(context: str, plan: dict) -> str:
    """Use Claude to write the full Streamlit page."""
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": f"""You are the Backend + UI Agent for Darrian's budget app.

{context}

Write the complete, production-ready Streamlit page for:
Feature: {plan['feature_name']}
Description: {plan['description']}
File: {plan['page_file']}

Requirements:
1. Follow ALL rules in the .clinerules section above
2. Include _ensure_tables() at top
3. Use get_conn(), require_login(), inject_css(), render_sidebar_brand()
4. Include the standard sidebar (all 7 links per rule.txt)
5. Full CRUD where appropriate
6. AI integration using get_setting("anthropic_api_key")
7. No hardcoded keys or credentials
8. Handle both SQLite (?) and PostgreSQL (%s) placeholders
9. Return ONLY the Python code, no markdown fences."""
        }]
    )
    return msg.content[0].text

def write_tests(context: str, plan: dict, page_code: str) -> str:
    """Use Claude to write pytest unit tests."""
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"""You are the Test Agent for Darrian's budget app.

Write pytest unit tests for this new page:
Feature: {plan['feature_name']}
File: {plan['page_file']}

Page code (first 2000 chars):
{page_code[:2000]}

Write tests covering:
1. Import test — page imports without errors
2. DB test — _ensure_tables() runs without errors
3. Helper function tests — core functions return expected types

Follow the pattern in tests/unit/test_budget_app.py.
Return ONLY the Python test code."""
        }]
    )
    return msg.content[0].text

def run_qa(page_file: str, test_file: str) -> tuple[bool, str]:
    """Run syntax check and tests."""
    code, out = run(f"python3 -m py_compile {page_file} && echo 'SYNTAX_OK'")
    if "SYNTAX_OK" not in out:
        return False, f"Syntax error in {page_file}:\n{out}"

    code, out = run(f"source venv/bin/activate && pytest {test_file} -v 2>&1")
    if code != 0:
        return False, f"Tests failed:\n{out}"

    return True, out

def git_commit_and_push(plan: dict, page_file: str, test_file: str) -> str:
    """Create branch, commit, push, and open PR."""
    branch = plan["branch_name"]
    run(f"git checkout dev && git pull origin dev")
    run(f"git checkout -b {branch}")
    run(f"git add {page_file} {test_file}")
    run(f'git commit -m "feat: {plan[\"description\"][:72]}\n\n- Auto-built by overnight AI dev system\n- Tests: passing\n- Feature: {plan[\"feature_name\"]}"')
    run(f"git push origin {branch}")

    # Merge through pipeline
    for target in ["dev", "qa", "staging"]:
        run(f"git checkout {target} && git pull origin {target}")
        run(f"git merge {branch} --no-ff -m 'chore: merge {branch} into {target}'")
        run(f"git push origin {target}")
        time.sleep(30)  # Wait for CI to run

    # Open PR to main (requires manual approval)
    _, pr_url = run(
        f'gh pr create --base main --head staging '
        f'--title "feat: {plan[\"description\"][:72]}" '
        f'--body "**Auto-built by overnight AI dev system**\n\n'
        f'Feature: {plan[\"feature_name\"]}\n\n'
        f'Subtasks completed:\n' +
        "\n".join(f"- {t}" for t in plan["subtasks"]) +
        f'\n\nTests: ✅ passing\nReady for your manual approval to deploy to production."'
    )
    return pr_url

def main():
    notify("🤖 <b>Overnight Dev System Starting...</b>\nBuilding context and picking next feature.")

    context = build_context()
    plan = pick_next_feature(context)

    notify(f"📋 <b>Tonight's Feature:</b> {plan['feature_name']}\n{plan['description']}")

    # Write the page
    page_code = write_feature(context, plan)
    page_path = f"{REPO_PATH}/{plan['page_file']}"
    Path(page_path).write_text(page_code)

    # Write tests
    test_code = write_tests(context, plan, page_code)
    test_name  = plan['feature_name'].replace('-', '_')
    test_path  = f"{REPO_PATH}/tests/unit/test_{test_name}.py"
    Path(test_path).write_text(test_code)

    # QA
    passed, qa_output = run_qa(page_path, test_path)
    if not passed:
        notify(f"⚠️ <b>QA Failed</b> for {plan['feature_name']}\n{qa_output[:500]}\nNeeds manual review.")
        return

    # Git pipeline
    pr_url = git_commit_and_push(plan, plan['page_file'], f"tests/unit/test_{test_name}.py")

    notify(
        f"✅ <b>Feature Ready!</b> {plan['feature_name']}\n\n"
        f"Pipeline: feature → dev → qa → staging ✅\n"
        f"Tests: passing ✅\n\n"
        f"<b>One action needed from you:</b>\n"
        f"Approve the PR to deploy to production:\n"
        f"{pr_url}"
    )

if __name__ == "__main__":
    main()
```

---

## Setup Instructions (One-Time, ~2 Hours)

### Step 1: Install on CT100

```bash
# SSH into CT100
ssh root@100.95.125.112

# Create the overnight dev directory
mkdir -p /opt/overnight-dev
cd /opt/overnight-dev

# Install dependencies
pip3 install anthropic requests

# Copy the orchestrator script
nano orchestrator.py
# (paste the script above)

# Set environment variables
cat >> /etc/environment << 'EOF'
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ANTHROPIC_API_KEY=your_key_here
EOF

source /etc/environment
```

### Step 2: Clone the repo to CT100

```bash
cd /opt
git clone https://github.com/bookofdarrian/darrian-budget.git darrian-budget
cd darrian-budget

# Set up venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure git
git config user.email "darrian@peachstatesavings.com"
git config user.name "Overnight AI Dev"

# Authenticate gh CLI
gh auth login
```

### Step 3: Schedule the Cron Job

```bash
# Run at 11 PM every night
echo "0 23 * * * root source /etc/environment && bash /opt/darrian-budget/scripts/run_autonomous_nightly.sh" >> /etc/crontab
```

### Step 4: Create BACKLOG.md in Your Repo

```bash
cd /opt/darrian-budget
cat > BACKLOG.md << 'EOF'
# Feature Backlog — Auto-Dev Queue

## HIGH PRIORITY
- [ ] Sneaker Price Alert Bot (eBay + Mercari, Telegram alerts)
- [ ] HSA Receipt Auto-Categorizer (OCR + Claude classification)
- [ ] eBay Listing Generator (AI-optimized titles + descriptions)
- [ ] RSU Vest Calendar + Tax Withholding Optimizer

## MEDIUM PRIORITY
- [ ] Monthly Financial Email Report
- [ ] Telegram Budget Bot (natural language expense logging)
- [ ] Rent vs Buy Calculator (Atlanta-specific)

## LOW PRIORITY
- [ ] Car/Mileage Tracker (404 Sole Archive deductions)
- [ ] Cloudflare Worker edge cache
- [ ] Health Cost Tracker + HSA integration
EOF

git add BACKLOG.md
git commit -m "chore: add autonomous dev backlog"
git push origin dev
```

### Step 5: Test a Dry Run

```bash
# Run manually first to verify it works
python3 /opt/overnight-dev/orchestrator.py
# Check Telegram for the notification
# Check /var/log/overnight-dev.log for details
```

---



### Autonomous preflight (recommended)
Run this before nightly orchestration to fail fast on setup drift:

```bash
bash /opt/darrian-budget/scripts/autonomous_preflight.sh
```

Nightly wrapper (recommended cron target):

```bash
bash /opt/darrian-budget/scripts/run_autonomous_nightly.sh
```

Failure labels now standardized for diagnostics:
- `[ENV]` environment/setup/runtime
- `[TEST]` pytest failures
- `[GIT]` checkout/merge/push/PR failures
- `[DEPLOY]` container/health/deploy failures

## What You Do Each Morning (2 Minutes)

1. **Read Telegram** — bot sends you:
   - What feature was built
   - QA results (pass/fail)
   - Link to the GitHub PR

2. **Review the PR** — glance at the diff on GitHub
   - Is the code reasonable?
   - Do the tests pass in GitHub Actions?

3. **One Click** — Approve the deployment in GitHub Actions
   - `https://github.com/bookofdarrian/darrian-budget/actions`
   - Click the workflow run → Approve → done

**Total morning effort: ~5 minutes if you approve, ~30 min if you want to tweak.**

---

## Context Training — What Makes the Agents Smart About YOUR Project

The orchestrator feeds agents ALL of the following before they write a line:

| Context File | What Agents Learn |
|---|---|
| `.clinerules/rule.txt` | Your coding standards, patterns, sidebar layout |
| `SDLC_PROCESS.md` | Branch naming, commit format, pipeline stages |
| `NEXT_USECASES.md` | Use case ideas + implementation details |
| `HOMELAB_USECASES.md` | Your homelab capabilities and constraints |
| `git log --oneline -20` | What was recently built (no duplicates) |
| `ls pages/` | What pages already exist (naming convention) |
| DB schema | What tables already exist (no conflicts) |

This is effectively "training" on your project without actual fine-tuning —
it's all in-context learning using Claude's 200k token window.

---

## Multi-Agent Roles

| Agent | Model | Job |
|---|---|---|
| Orchestrator | Claude Opus 4.5 | Picks feature, coordinates others |
| Planner | Claude Opus 4.5 | Breaks feature into subtasks |
| Backend Bot | Claude Opus 4.5 | DB schema, helper functions, queries |
| UI Bot | Claude Opus 4.5 | Streamlit page, sidebar, forms |
| Test Bot | Claude Haiku | pytest unit tests (faster/cheaper) |
| QA Bot | Claude Haiku | Syntax check, test runner, compliance check |
| Git Bot | Shell script | Branch, commit, push, PR |

**Cost per night:** ~$0.50–$2.00 in Claude API tokens for a medium-complexity feature.
With AURA compression (already running on CT100), cut that by 40–60%.

---

## Inspired by the YouTube Insights

### From Hank Green ("My Biggest Fear About AI")
> "Smaller trained models on specific data are the future"

**Applied here:** Each agent has a narrow, specific role (DB bot, UI bot, test bot).
No single bloated agent tries to do everything. Each one gets highly specific context
about ONLY what it needs. This is the architecture Hank is describing — domain-specific,
focused models beat general-purpose ones.

### From Edan Meyer ("The AI Scaling Problem")
> "When building an agent, it's about creating one that has goals, can autonomously
> control its data stream and teach itself based on those goals"

**Applied here:** The Planner Agent reads your backlog (goal-driven), controls its
own context (builds CONTEXT_SNAPSHOT.md each night), and tracks what it built
previously via git log (learns from its own history). The agents have a goal
(ship a feature through SDLC) and pursue it without you.

### From "How I Learn Things Really Fast (with AI)"
> "Goal → Research → Priming → Framework → Convert Format → Remove Noise → Notes"

**Applied here for Cline sessions:**
1. **Goal:** Have the feature goal in BACKLOG.md before you start a Cline session
2. **Research:** Use Perplexity to look up implementation patterns first
3. **Priming:** Feed Cline the relevant use-case doc (NEXT_USECASES.md section)
4. **Framework:** Use .clinerules as the framework — Cline reads it automatically
5. **Convert:** Cline converts your idea → working code
6. **Remove noise:** Keep prompts focused on ONE feature at a time
7. **Notes:** Cline updates BACKLOG.md (check off completed items)

---

## Guardrails (What Keeps This Safe)

1. **Never deploys to production automatically** — always stops at a GitHub PR
   waiting for your manual approval. This is hard-coded in the script.

2. **Tests must pass** — if pytest fails, the agent stops and sends you a
   Telegram alert. No broken code gets committed.

3. **Syntax checked** — every file runs `python3 -m py_compile` before commit.

4. **Never touches main branch** — only merges feature → dev → qa → staging.
   The `main` branch stays protected.

5. **Conventional commits** — every commit is formatted and traceable.

6. **Git blame is honest** — commit message says "Auto-built by overnight AI
   dev system" so you always know which code came from the bots.

7. **API key safety** — agents read keys from `get_setting()` / env vars,
   never hardcode credentials. Your `.clinerules/rule.txt` enforces this.

---

## Estimated Timeline to Launch

| Week | Goal |
|---|---|
| Week 1 | Set up CT100, clone repo, install orchestrator, test dry run |
| Week 2 | First live overnight run — Sneaker Price Alert Bot |
| Week 3 | Second run — HSA Receipt Categorizer |
| Month 2+ | Fully automated — wake up to a new feature every morning |

---

## The Big Picture

You're building a **personal software factory** that:
- Runs on your own hardware (free compute)
- Uses your existing SDLC pipeline (no new process to learn)
- Produces code that matches YOUR style (trained on your .clinerules)
- Costs ~$1/night in API tokens
- Requires ~5 minutes of your time per feature

By the time you're at Visa, your budget app will have every feature from
NEXT_USECASES.md built, tested, and deployed — without you spending a single
evening coding.
