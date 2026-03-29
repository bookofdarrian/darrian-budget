# Cline CLI — Benefits & Integration Guide
# darrian-budget / Peach State Savings
# Last Updated: 2026-03-28

---

## 🔥 What Is Cline CLI?

`cline` is the **terminal-native version of the Cline VS Code extension** you already use.
Same AI model (Claude Sonnet 4.6), same context, same project rules — but scriptable, automatable,
and runnable **without opening VS Code**. Think of it as your coding AI that lives in the terminal.

Already installed at: `/Users/darrianbelcher/.npm-global/bin/cline`
Already configured: `claude-sonnet-4.6` via Cline provider (synced with your VS Code extension)
Project rules: `.clinerules` (root of this repo — auto-loaded on every `cline` command)

---

## 🎯 Why This Matters FOR YOUR SPECIFIC SYSTEM

### 1. 🤖 Integrate Into the Overnight Agent System
Your `run_scheduled_agents.py` already runs nightly tasks (stale inventory scan, health insights,
spending digest). Now you can add **AI-powered code generation** as a scheduled task:

```python
# In run_scheduled_agents.py — add this handler:
def _handler_overnight_page_build(task: dict) -> tuple[bool, str]:
    """Build a new backlog page using Cline CLI overnight."""
    import subprocess
    backlog_item = task.get('backlog_item', '')
    if not backlog_item:
        return False, "No backlog item specified"
    
    result = subprocess.run([
        "/Users/darrianbelcher/.npm-global/bin/cline",
        "--yolo",                          # auto-approve all file writes
        "--act",                           # act mode (not plan)
        "--timeout", "300",                # 5 min max
        "-c", "/Users/darrianbelcher/Downloads/darrian-budget",
        f"Build the next backlog item: {backlog_item}. "
        f"Follow .clinerules strictly. Create feature branch, build page, run tests, commit."
    ], capture_output=True, text=True, timeout=360,
       cwd="/Users/darrianbelcher/Downloads/darrian-budget")
    
    return result.returncode == 0, (result.stdout or result.stderr)[:500]
```

### 2. ⚡ Terminal-Only Workflow (No VS Code Required)
Build pages from anywhere — SSH into your homelab, run from a script, trigger from cron:

```bash
# Build a new SoleOps page from the terminal
cd /Users/darrianbelcher/Downloads/darrian-budget
cline --yolo --act "Build pages/103_soleops_user_registration.py — full email/password reg + Stripe checkout. Follow .clinerules."

# Quick fix without opening VS Code
cline --act "Fix the conn.execute() pattern in pages/119_soleops_inventory_aging_report.py"

# Plan before you build
cline --plan "Design the CC FAFSA Guide page (page 86) — what tables, what AI prompts, what UI sections?"
```

### 3. 📋 Kanban Task Board
Built-in project task management in the terminal:

```bash
cline kanban   # opens visual kanban board for your tasks
```

Use this to track SoleOps/CC build queue without a separate tool.

### 4. 📜 Task History + Resume
Never lose work again:

```bash
cline history                  # list all past tasks with IDs
cline --continue               # resume the most recent task from this directory
cline --taskId abc123          # resume a specific task by ID
```

Especially useful when a build gets interrupted — just `--continue`.

### 5. 🧠 Extended Thinking (Architecture Mode)
For complex architecture decisions:

```bash
cline --plan --thinking 8096 "Design the SoleOps multi-tenant architecture for 100 users"
```

### 6. 🔌 MCP Server Management
Manage your MCP tools directly:

```bash
cline mcp              # list installed MCP servers
cline mcp add          # add a new MCP server
```

---

## 🏃 Practical Commands for THIS Codebase

### Build a New Page (Full SDLC)
```bash
cline --yolo --act "
Build pages/91_cc_college_list_builder.py — CC College List Builder.
1. Create feature branch: feature/cc-college-list-builder
2. Build full page following .clinerules (page structure, sidebar, db pattern)
3. Syntax check: python3 -m py_compile pages/91_cc_college_list_builder.py
4. Add tests to tests/unit/
5. Run pytest tests/ -v
6. Conventional commit: feat: add CC College List Builder (page 91)
7. Push and merge to dev
"
```

### Fix a Production Bug Fast
```bash
cline --act --yolo "
Scan all pages in pages/ for conn.execute() pattern (not db_exec).
Fix every occurrence. Run pre-commit scan to verify clean.
Commit as: fix: replace conn.execute with db_exec across all pages
"
```

### Daily Morning Brief (Pipe to Terminal)
```bash
cline --act --json "
Read BACKLOG.md and AI_CAREER_INTEL.md.
Give me a 5-bullet morning brief: top 3 build priorities today, 1 career action, 1 SoleOps revenue move.
Output plain text, no code.
" | python3 -c "import sys,json; [print(m['content']) for m in json.load(sys.stdin) if m.get('type')=='text']"
```

### Pre-Deploy Safety Check
```bash
cline --act "
Run the pre-commit scan:
  grep -rn 'conn\.execute(' pages/ --include='*.py'
  grep -rn 'conn\.executescript(' pages/ --include='*.py'
  grep -rn 'experimental_rerun' pages/ --include='*.py'
Report: PASS if all empty, FAIL with file:line if any found.
"
```

### SoleOps Revenue Move
```bash
cline --act --yolo "
Check pages/103_soleops_user_registration.py status.
If incomplete, identify what's missing and build the next logical section.
Follow .clinerules strictly.
"
```

---

## 🔧 Integration With run_scheduled_agents.py

Add Cline CLI as a scheduled overnight task in your Agent Dashboard:

**In the Agent Dashboard UI (page with scheduled tasks), add:**
| Task Name | Schedule | Backlog Item |
|-----------|----------|--------------|
| Overnight Page Build | Daily @ 11pm | Next item from BACKLOG.md |
| Weekly Code Audit | Weekly Mon @ 8am | Scan all pages for anti-patterns |
| SoleOps Beta Prep | Daily @ 10pm | Next SoleOps revenue-unlocking feature |

**Handler to add in run_scheduled_agents.py:**
```python
def _handler_cline_page_build(task: dict) -> tuple[bool, str]:
    """Trigger Cline CLI to build the next backlog page."""
    import subprocess
    from pathlib import Path
    
    # Read BACKLOG.md to find next item
    backlog_path = Path("/Users/darrianbelcher/Downloads/darrian-budget/BACKLOG.md")
    backlog_content = backlog_path.read_text()[:2000] if backlog_path.exists() else ""
    
    cline_bin = "/Users/darrianbelcher/.npm-global/bin/cline"
    prompt = (
        f"Build the NEXT highest priority item from this backlog:\n\n{backlog_content}\n\n"
        "Rules: Follow .clinerules strictly. Create feature branch. Build full page. "
        "Run syntax check and pytest. Commit with conventional commit message. Push to dev."
    )
    
    result = subprocess.run(
        [cline_bin, "--yolo", "--act", "--timeout", "600", prompt],
        capture_output=True, text=True, timeout=660,
        cwd="/Users/darrianbelcher/Downloads/darrian-budget"
    )
    
    success = result.returncode == 0
    output = (result.stdout or result.stderr or "No output")[:500]
    return success, output

# Register in TASK_HANDLERS list:
# ("overnight page build",  _handler_cline_page_build),
# ("cline page build",      _handler_cline_page_build),
```

---

## 🛠️ Shell Aliases (Add to ~/.zshrc)

```bash
# Cline shortcuts for darrian-budget
alias pss='cd /Users/darrianbelcher/Downloads/darrian-budget'
alias cline-build='cline --yolo --act -c /Users/darrianbelcher/Downloads/darrian-budget'
alias cline-plan='cline --plan -c /Users/darrianbelcher/Downloads/darrian-budget'
alias cline-fix='cline --yolo --act -c /Users/darrianbelcher/Downloads/darrian-budget'
alias cline-audit='cline --act -c /Users/darrianbelcher/Downloads/darrian-budget "Run pre-commit scan and report any conn.execute, conn.executescript, or experimental_rerun violations"'
```

Usage:
```bash
cline-build "Build the SoleOps Weekly Reseller Report email page"
cline-plan "Design the CC FAFSA calculator — what formula, what UI?"
cline-audit
```

---

## 📊 Cline CLI vs VS Code Extension — When to Use Each

| Situation | Use |
|-----------|-----|
| Building a new page with full context | VS Code extension (sidebar chat) |
| Quick terminal fix on remote server | `cline --act` |
| Overnight automated builds | `cline --yolo --act` via cron/agent |
| Architecture planning | `cline --plan --thinking` |
| Reviewing task history | `cline history` |
| Managing backlog as kanban | `cline kanban` |
| Pre-deploy safety check | `cline --act "run pre-commit scan"` |
| Building from SSH on homelab | `cline --yolo --act` |

---

## ⚡ Yolo Mode Warning

`--yolo` auto-approves **all file reads, writes, and terminal commands** without confirmation.

**Safe for:**
- Building new pages (feature branches, nothing overwriting prod)
- Automated overnight builds
- Scheduled agent tasks

**Do NOT use for:**
- Anything near `main` branch without review
- Anything that touches the prod server directly
- DB migrations

Always use feature branches: `cline --yolo --act "Create branch first: git checkout -b feature/xxx"`

---

## 🚀 Quick Start Commands

```bash
# 1. Verify it's working
cline --version
# → 2.11.0

# 2. Check current config
cline config

# 3. See task history
cline history

# 4. Run your first task
cd /Users/darrianbelcher/Downloads/darrian-budget
cline --act "List the top 5 files in pages/ by line count. No code changes."

# 5. Open kanban board
cline kanban

# 6. Build something (with yolo)
cline --yolo --act "Build the next item from BACKLOG.md following .clinerules strictly"
```

---

## 📍 Key Paths

| Resource | Path |
|----------|------|
| Cline binary | `/Users/darrianbelcher/.npm-global/bin/cline` |
| Cline data dir | `/Users/darrianbelcher/.cline/data/` |
| Global state | `/Users/darrianbelcher/.cline/data/globalState.json` |
| Task history | `/Users/darrianbelcher/.cline/data/workspaces/` |
| Project rules | `/Users/darrianbelcher/Downloads/darrian-budget/.clinerules` |
| Model | `claude-sonnet-4.6` via Cline provider |
