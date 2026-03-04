# 🖥️ Windows Workstation Setup Guide
### Darrian Belcher | 12th Gen Intel® Core™ i7 | Visa Inc.
### Topics: Agentic AI Dev · AI Notes & To-Do · SDLC · Homelab Bridge

---

> **Data Separation Principle (read this first)**
>
> You already have the right instinct: **work data stays on Visa systems, personal projects stay on your homelab.** This guide respects that completely. The bridge between the two is *skills and workflows*, not data. Everything in Section 4 keeps the two networks air-gapped while letting you bring the same engineering muscle to both sides.

---

## 1. Core Software Stack (Windows)

### 1.1 Install These First

| Tool | Purpose | Download |
|---|---|---|
| **VS Code** | Primary IDE | https://code.visualstudio.com |
| **Git for Windows** | Version control | https://git-scm.com/download/win |
| **Python 3.11** (user install) | Local scripting | https://python.org |
| **WSL2 + Ubuntu 22.04** | Linux environment inside Windows | `wsl --install` in PowerShell (Admin) |
| **Windows Terminal** | Tabbed terminal with WSL | Microsoft Store |
| **Docker Desktop** | Containerized apps | https://docker.com *(check with IT first)* |
| **Tailscale** | Secure VPN to homelab | https://tailscale.com/download *(personal projects only — see §4)* |

### 1.2 VS Code Extensions

```
# Install via VS Code Extensions panel or:
# code --install-extension <id>

Cline (saoudrizwan.claude-dev)         # AI coding agent
GitHub Copilot                          # AI autocomplete (get Visa license)
GitLens                                 # Git blame, history, PRs
Python (ms-python.python)              # Python dev
Pylance                                 # Type checking
Even Better TOML                        # pyproject.toml support
Conventional Commits                   # Commit message helper
GitGraph                               # Visual branch history
Todo Tree                              # Highlights TODO/FIXME in code
Markdown All in One                    # Rich Markdown preview
```

### 1.3 Git Configuration (Windows)

```powershell
# In Windows Terminal (PowerShell or WSL)
git config --global user.name "Darrian Belcher"
git config --global user.email "darbelch@visa.com"       # for Visa repos
git config --global core.autocrlf true                   # Windows line endings
git config --global init.defaultBranch main
git config --global pull.rebase false

# For personal repos (run inside your personal project folders):
git config user.email "darrian@peachstatesavings.com"
```

---

## 2. Agentic Autonomous Agents (Windows)

### 2.1 What You Already Have (Homelab)
Your homelab CT100 (`100.95.125.112`) runs:
- **Overnight AI Dev Orchestrator** — picks features from BACKLOG.md, builds pages, runs QA, promotes through git pipeline automatically
- **Agent Dashboard** — Plotly Dash app at port 8502 showing live logs and build history

### 2.2 Run Agents Locally on Windows (Personal Projects)

```powershell
# Open WSL2 Ubuntu terminal
wsl

# Clone your repo
cd ~
git clone https://github.com/bookofdarrian/darrian-budget.git
cd darrian-budget

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set env vars (never commit these)
export ANTHROPIC_API_KEY="sk-ant-..."
export DATABASE_URL="postgresql://..."   # or leave blank for SQLite

# Run the agent loop
python3 /opt/overnight-dev/orchestrator.py
```

### 2.3 Cline in VS Code (Personal + Professional)

**For personal projects:**
- Open `darrian-budget/` in VS Code
- Use Cline with your Anthropic API key
- Let it build pages, write tests, commit — same as the overnight system but interactive

**For Visa work:**
- Open your Visa project in a SEPARATE VS Code window
- Use **GitHub Copilot** (get enterprise license from Visa IT) — Microsoft-approved, zero data leakage
- Cline: only use with **local models** (Ollama) on Visa code — never send proprietary code to external APIs
- OR use Visa's approved AI tools (ask your manager/security team)

### 2.4 Set Up Cline for Work (Air-Gapped)

```json
// VS Code settings.json — for your Visa window only
{
  "cline.apiProvider": "ollama",           // local, no external API
  "cline.ollamaBaseUrl": "http://localhost:11434",
  "cline.ollamaModelId": "codellama:13b"  // or llama3
}
```

Install Ollama on Windows: https://ollama.com/download/windows

```powershell
# Pull a coding model
ollama pull codellama:13b
ollama pull llama3.2
```

This gives you AI coding assistance on Visa code with **zero data leaving your laptop**.

---

## 3. AI To-Do List & Notes (Windows)

### 3.1 Personal (synced to homelab)
Your `peachstatesavings.com` app already has:
- **Page 22** — AI-powered To-Do with categories, priorities, deadlines
- **Page 25** — Notes (Apple Notes / Notion replacement)

Access via browser at `http://peachstatesavings.com` or `http://100.95.125.112:8501` on Tailscale.

### 3.2 Professional Notes (Work-Safe, No Cloud Risk)

**Option A: Obsidian (Recommended)**
- Download: https://obsidian.md
- Store vault in `C:\Users\darbelch\Documents\ObsidianWork\`
- NO cloud sync = zero data risk
- Use Dataview plugin for task tracking
- Use Local GPT plugin with Ollama for AI summaries

**Obsidian folder structure:**
```
ObsidianWork/
├── Daily/           # Daily standup notes
├── Projects/        # One note per project
├── Meetings/        # Meeting notes
├── Decisions/       # Architecture decision records
└── Learning/        # Things you're learning at Visa
```

**Option B: VS Code + Todo Tree extension**
- `TODO:`, `FIXME:`, `HACK:`, `NOTE:` tags are highlighted across all files
- Use `tasks.json` in your workspace for structured task tracking

**Option C: Notion (if IT-approved)**
- Check with Visa IT whether Notion is on the approved software list
- If approved: great for project wikis, sprint boards, stakeholder docs

### 3.3 Conventional Commits as Documentation

Every commit message IS documentation when you do it right:
```
feat: add payment retry logic with exponential backoff

- Retries up to 3 times on 5xx errors
- 15s, 30s, 60s delays
- Sends alert on final failure

Closes #VIS-4821
```

Use the **Conventional Commits** VS Code extension to enforce format.

---

## 4. Software Delivery Process (SDLC)

This mirrors exactly what you've built for peachstatesavings.com — the same discipline applies professionally.

### 4.1 Branch Strategy

```
main (prod)
  └── staging
        └── qa
              └── dev
                    └── feature/VIS-1234-payment-retry   ← you work here
```

**Branch naming:**
```
feature/VIS-4821-retry-logic
bugfix/VIS-4900-null-pointer-receipts
hotfix/VIS-5001-critical-auth-bypass
chore/update-dependencies-q1-2026
```

### 4.2 Daily Workflow

```powershell
# Morning: sync your branch
git fetch origin
git checkout feature/VIS-4821-retry-logic
git rebase origin/dev              # or merge, per team convention

# Work on code...

# Before committing: run lint + tests
python -m flake8 src/
python -m pytest tests/ -v

# Commit with conventional format
git add .
git commit -m "feat(payments): add exponential backoff retry

- Retries on 5xx: 15s, 30s, 60s delays
- Max 3 attempts before dead letter queue
- Unit tests: 12/12 passing

Closes #VIS-4821"

# Push
git push origin feature/VIS-4821-retry-logic
```

### 4.3 Pre-commit Hooks (same as your personal repo)

```yaml
# .pre-commit-config.yaml (add to your Visa project)
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: detect-private-key         # catches accidental secret commits
      - id: no-commit-to-branch
        args: ['--branch', 'main', '--branch', 'staging']

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

```powershell
pip install pre-commit
pre-commit install
```

### 4.4 GitHub Actions CI/CD (Professional)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [dev, staging, main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v --tb=short
      - run: python -m flake8 src/

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit
      - run: bandit -r src/ -ll    # catches security issues
```

### 4.5 PR Checklist Template

Create `.github/pull_request_template.md`:

```markdown
## What does this PR do?
Brief description of the change.

## Type of change
- [ ] feat: New feature
- [ ] fix: Bug fix
- [ ] refactor: Code refactoring
- [ ] chore: Dependency update / tooling
- [ ] docs: Documentation only

## Testing
- [ ] Unit tests added/updated
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] No hardcoded secrets or credentials

## Checklist
- [ ] Conventional commit message
- [ ] No TODO/FIXME left behind
- [ ] PR title is clear and concise
- [ ] Linked to Jira ticket (if applicable)
```

---

## 5. Homelab → Visa Workstation Bridge

### 5.1 The Right Mental Model

```
┌─────────────────────────┐     ┌────────────────────────────────┐
│    VISA WORKSTATION     │     │      PERSONAL HOMELAB          │
│  (Managed, Corp WiFi)   │     │  (CT100, 100.95.125.112)       │
│                         │     │                                │
│  Work code, Visa data   │     │  peachstatesavings.com         │
│  GitHub Copilot         │     │  Overnight AI Agents           │
│  Jira, Confluence       │     │  Personal DB, Notes, Budget    │
│  Approved tools only    │     │  Tailscale mesh                │
└─────────────────────────┘     └────────────────────────────────┘
            │                               │
            └─────── SKILLS TRANSFER ───────┘
                (not data, not connections)
```

**What crosses the bridge:** Your Git discipline, Python skills, CI/CD knowledge, AI prompting techniques, code review habits — all transferable skills.

**What NEVER crosses:** Work code, Visa data, customer data, internal URLs, credentials.

### 5.2 Tailscale on Visa Laptop (Personal Use Only)

> ⚠️ **Check Visa IT policy first.** If Tailscale is not on the approved software list, skip this. Use it only on your personal machine.

If approved for personal-use software on managed devices:

```powershell
# Install Tailscale (personal account, NOT Visa tenant)
winget install Tailscale.Tailscale

# Log in with your PERSONAL Google/GitHub account
# This joins your personal tailnet — NOT Visa's network
# Access homelab from anywhere:
ssh root@100.95.125.112     # works from Visa WiFi (your tunnel, personal traffic)
open http://peachstatesavings.com  # personal app, personal data
```

**Why this is safe:**
- Tailscale encrypts all traffic end-to-end
- Your personal tailnet is completely separate from Visa's network
- No Visa data ever goes through Tailscale
- It's just like using your phone's hotspot for personal browsing

**If IT doesn't allow it:** Use your phone as a mobile hotspot for homelab access — keeps it 100% off the Visa network.

### 5.3 Cross-Pollination: Skills You're Building That Apply at Visa

| What you build personally | Professional equivalent |
|---|---|
| Overnight AI Dev Orchestrator | CI/CD pipeline automation, GitHub Actions |
| BACKLOG.md + feature branches | Jira + sprint planning + PR workflow |
| `_ensure_tables()` pattern | Database migration management (Alembic, Flyway) |
| `pytest` unit tests | TDD/BDD at Visa — same pattern, bigger codebase |
| PostgreSQL on homelab | Enterprise PostgreSQL / Oracle at scale |
| Anthropic Claude API | Azure OpenAI / AWS Bedrock (enterprise AI) |
| Monitoring stack (Prometheus + Grafana) | Visa monitoring: DataDog, Splunk, PagerDuty |
| Docker + Proxmox | Kubernetes at Visa — same concepts, more replicas |
| Conventional commits + PR template | Visa code review standards, change management |

### 5.4 Propose AI Tooling at Visa

Since you're building agentic systems personally, you have direct credibility to propose these internally. Framework for a Visa AI pitch:

```
Problem:  [specific inefficiency in your team's workflow]
Solution: [AI-assisted automation — language that resonates at Visa]
Risk:     Low — uses Azure OpenAI (Microsoft contract, enterprise SLA)
Data:     Stays within Visa's Azure tenant — zero external exposure
ROI:      [hours saved per sprint × team size × hourly rate]
Pilot:    2-week proof of concept with your own squad
```

Tools Visa is likely already approved for (or easy to get approved):
- **GitHub Copilot Enterprise** — in-IDE AI, stays in your GitHub org
- **Azure OpenAI** — Microsoft contract, enterprise data protection
- **Microsoft Copilot** (M365) — already in your Outlook/Teams
- **Jira AI features** — if Visa uses Atlassian

---

## 6. Quick Start Checklist (Do These This Week)

### Day 1 — Foundation
- [ ] Install VS Code, Git, Python 3.11, WSL2, Windows Terminal
- [ ] Configure Git with Visa email + GPG signing (ask team for standard)
- [ ] Install VS Code extensions (GitLens, Pylance, Todo Tree minimum)
- [ ] Set up Obsidian vault at `C:\Users\darbelch\Documents\ObsidianWork\`

### Day 2 — AI Tools
- [ ] Request GitHub Copilot Enterprise license from Visa IT
- [ ] Install Ollama + `codellama:13b` for local/safe AI on work code
- [ ] Install Cline with Ollama backend (for Visa code — no external API)
- [ ] Check with IT: Tailscale personal use policy

### Day 3 — SDLC
- [ ] Add `.pre-commit-config.yaml` to your main Visa project
- [ ] Run `pre-commit install` and test it
- [ ] Create `.github/pull_request_template.md` in your repo
- [ ] Set up GitHub Actions CI workflow if not already present

### Day 4 — Bridge Personal → Professional
- [ ] Review your homelab CI/CD patterns and identify 1 thing to propose to your team
- [ ] Draft a 1-page AI tool proposal (use §5.4 framework)
- [ ] Start a "Learning" note in Obsidian linking homelab lessons to Visa use cases

---

## 7. Data Separation Rules (Absolute)

```
✅ OK: Access peachstatesavings.com from Visa WiFi (personal data, personal app)
✅ OK: Use Tailscale to SSH your homelab from Visa WiFi
✅ OK: Learn Docker/Python/Git on homelab, apply skills at Visa
✅ OK: Use Ollama locally on Visa laptop for AI assistance on work code

❌ NEVER: Copy Visa code to your homelab or personal GitHub
❌ NEVER: Use your personal Anthropic API key on Visa code
❌ NEVER: Store Visa credentials, keys, or data outside Visa systems
❌ NEVER: Connect personal devices to Visa WiFi (you already know this)
❌ NEVER: Route Visa data through personal services (Dropbox, iCloud, etc.)
```

---

## 8. Hardware Notes (12th Gen Intel i7)

Your Windows machine likely has:
- **P-cores** (Performance): Use for Docker, WSL2, heavy compilation
- **E-cores** (Efficiency): Good for background processes (Tailscale, Ollama serving)
- **Intel Iris Xe GPU**: Can accelerate Ollama with `--gpu-layers` flag on some models

### WSL2 Performance Tips

```powershell
# Create .wslconfig in C:\Users\darbelch\
[wsl2]
memory=8GB            # Limit WSL2 RAM (adjust based on your total RAM)
processors=6          # Use 6 of your P-cores for WSL2
localhostForwarding=true
```

### Ollama Performance

```powershell
# Run Ollama with GPU acceleration (if driver supports it)
$env:OLLAMA_MAX_LOADED_MODELS = "2"
ollama serve

# Test a model
ollama run codellama:7b "Explain what this Python function does: def _ensure_tables(): ..."
```

---

*Guide written: March 2, 2026*
*Stack: Windows 11 · WSL2 Ubuntu 22.04 · Python 3.11 · VS Code · Tailscale · Ollama*
*For questions: peachstatesavings.com homelab or darrian@peachstatesavings.com*
