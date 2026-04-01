# Complete Setup Guide — Todo, Notes & Autonomous AI Dev System
**Owner: Darrian Belcher | Created: 2026-03-02**
**App:** peachstatesavings.com | **Repo:** bookofdarrian/darrian-budget

---

## PART 1 — Todo App (pages/22_todo.py)

### What It Does
- Full task manager backed by PostgreSQL (`pa_tasks` table)
- Google Calendar sync — create tasks here, they appear on your calendar
- Voice input — speak a task, it transcribes automatically
- **Agent Dev Queue** — live view of autonomous agent backlog (built in)

### How to Use It

#### Adding a Task
1. Go to `peachstatesavings.com/pages/22_todo`
2. Click **➕ Add New Task**
3. Fill in: Title, Due Date (optional), Priority (Low/Medium/High), Notes
4. Or click 🎤 to speak the task title
5. Click **Add Task** — it saves to PostgreSQL instantly

#### Managing Tasks
- **Complete:** Click ✅ on any open task
- **Edit:** Click ✏️ to change title, due date, priority, or notes
- **Delete:** Click 🗑️ to remove permanently
- **Reopen:** In the Completed tab, click 🔄 to reopen a task

#### Filters & Views
- Use the **Status** dropdown: Open / Completed / All
- Use the **Priority** dropdown: All / High / Medium / Low
- Sort by: Due Date or Priority

#### Google Calendar Sync
1. Scroll to **📅 Google Calendar** section
2. Click **📁 Upload credentials.json**
3. Upload your `credentials.json` from Google Cloud Console
4. Click **🔗 Authorize Google Calendar**
5. Complete the OAuth flow in the popup
6. Go to **📤 Sync Tasks → Calendar** tab
7. Click **Sync Selected Tasks** to push tasks to your Google Calendar

**Setup Google OAuth (one-time):**
1. Go to console.cloud.google.com
2. Create project → Enable Google Calendar API
3. Create OAuth 2.0 Credentials → Desktop app
4. Download `credentials.json`
5. Upload it in the app (stored in your DB, not the file system)

---

## PART 2 — Notes App (pages/25_notes.py)

### What It Does
- Full replacement for Apple Notes, Google Docs, Notion
- Rich markdown editor with live preview
- AI summarization, expansion, task extraction
- Notebooks (group notes into collections)
- Templates (reusable note formats)
- Apple Notes XML import
- Export to Markdown

### Tab-by-Tab Guide

#### 📚 All Notes (Browse Tab)
- **Search:** Type in the search box to filter by title, content, or tag
- **Filter by category:** Personal, Work, Finance, Ideas, etc.
- **Filter by tag:** Click any tag to see notes with that tag
- **Pin notes:** Click 📌 to keep important notes at the top
- **Archive notes:** Click 📦 to hide without deleting
- Click any note card to open it in the Editor

#### ✍️ Editor Tab
- **Create new:** Click **+ New Note** button
- **Edit existing:** Select a note from Browse, it opens here
- Write in Markdown — preview updates live
- Fields: Title, Category, Tags (comma-separated), Color
- Click **💾 Save** to persist changes
- Click **🗑️ Delete** to permanently remove

#### 🤖 AI Tools Tab
- Select any note, then use AI to:
  - **Summarize** — get the key points in bullet form
  - **Expand** — elaborate on a brief note into full paragraphs
  - **Extract Tasks** — pull out action items as a to-do list
  - **Improve Writing** — fix grammar, flow, and clarity
- Requires Anthropic API key in app settings (Settings page)

#### 📓 Notebooks Tab
- **Create Notebook:** Name, description, icon emoji, color
- **Add notes to notebook:** Open a note → assign notebook from the dropdown
- **Browse notebook:** Click a notebook to see all its notes
- Good for: "404 Sole Archive", "Visa Work", "Budget Planning", "Ideas"

#### 📄 Templates Tab
- **Create Template:** Name, category, content (markdown), icon
- **Use Template:** Click **Use** to create a new note pre-filled with template content
- Built-in templates: Meeting Notes, Daily Journal, Project Brief
- Create your own: e.g., "Sneaker Flip Analysis", "Monthly Budget Review"

#### 📥 Import / Export Tab
- **Apple Notes Import:**
  1. On your Mac: Open Notes.app → File → Export All Notes (or specific notes)
  2. Or: File → Library → Export Library (saves as `.xml`)
  3. Upload the XML file in this tab
  4. All notes import with original dates and titles
- **Export to Markdown:**
  1. Select which notes to export (All, Pinned, by Category)
  2. Click Export — downloads a `.md` file
  3. Use this for backup or to open in Obsidian/Notion

---

## PART 3 — Autonomous AI Dev System

### Overview
Multiple AI agents (running on CT100 homelab) build features while you sleep.
You approve one PR in the morning to push to production.

### Architecture
```
11 PM: Orchestrator on CT100 wakes up
  → Reads BACKLOG.md
  → Skips items tagged [YOU]
  → Picks highest-priority unclaimed item
  → Planner agent breaks it into subtasks
  → Backend agent writes DB schema + helpers
  → UI agent writes Streamlit page
  → Test agent writes pytest unit tests
  → QA agent runs py_compile + pytest
  → Git agent: feature → dev → qa → staging
  → Opens PR to main (waits for YOUR approval)
Morning: You check Telegram, review PR, click Approve
```

### One-Time Setup (CT100)

#### Step 1: SSH into CT100
```bash
ssh root@100.95.125.112
```

#### Step 2: Clone repo and install dependencies
```bash
cd /opt
git clone https://github.com/bookofdarrian/darrian-budget.git darrian-budget
cd darrian-budget
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip3 install anthropic requests
git config user.email "darrian@peachstatesavings.com"
git config user.name "Overnight AI Dev"
gh auth login
```

#### Step 3: Create the orchestrator
```bash
mkdir -p /opt/overnight-dev
# Copy the full script from AUTONOMOUS_AI_DEV_SYSTEM.md
nano /opt/overnight-dev/orchestrator.py
```

#### Step 4: Set environment variables
```bash
cat >> /etc/environment << 'EOF'
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ANTHROPIC_API_KEY=your_api_key
EOF
source /etc/environment
```

**Get your Telegram bot:**
1. Message @BotFather → `/newbot` → copy token
2. Message your bot once
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → find `chat_id`

**Get your Anthropic API key from the app:**
```bash
cd /opt/darrian-budget && source venv/bin/activate
python3 -c "from utils.db import get_conn, get_setting; conn=get_conn(); print(get_setting('anthropic_api_key', conn)); conn.close()"
```

#### Step 5: Test dry run
```bash
source /etc/environment
python3 /opt/overnight-dev/orchestrator.py
# Watch for Telegram notification on your phone
```

#### Step 6: Schedule the cron
```bash
echo "0 23 * * * root source /etc/environment && bash /opt/darrian-budget/scripts/run_autonomous_nightly.sh" >> /etc/crontab
```

---



### Nightly reliability hardening (new)
```bash
# Standardize runtime and run preflight before orchestrator
bash /opt/darrian-budget/scripts/autonomous_preflight.sh

# Generate quick telemetry snapshot
python3 /opt/darrian-budget/scripts/nightly_telemetry_report.py

# Weekly restore drill (run Sundays at 3:30 AM)
echo "30 3 * * 0 root bash /opt/darrian-budget/scripts/weekly_restore_drill.sh >> /var/log/restore-drill.log 2>&1" >> /etc/crontab
```

Failure labels used in notifications/logging:
- `[ENV]` environment/setup/runtime issues
- `[TEST]` test failures
- `[GIT]` branch/merge/push failures
- `[DEPLOY]` deploy/health/restart failures

## PART 4 — Working in Tandem With Agents

### The Claim System

The only coordination you need is one `[YOU]` tag in BACKLOG.md:

```markdown
# In BACKLOG.md:
- [ ] [YOU] Sneaker Price Alert Bot    ← YOU own this, agents skip it
- [ ] RSU Vest Calendar                ← agents will build this tonight
- [ ] HSA Receipt Auto-Categorizer    ← agents queue
```

### From the Todo App (Easiest)
1. Scroll down to **🤖 Agent Dev Queue** on the Todo page
2. Click **🔒** next to any queue item to claim it
3. The `[YOU]` tag is added to BACKLOG.md automatically
4. Click **↩** to unclaim and return to agents

### From the Terminal
```bash
cd ~/Downloads/darrian-budget
# Edit BACKLOG.md to add [YOU]:
nano BACKLOG.md
# Run status board to verify:
python3 status.py
```

### Your Daily Rhythm

| Time | What You Do | What Agents Do |
|------|-------------|----------------|
| Morning | `python3 status.py` → review PR → click Approve | — |
| Before coding | Claim your feature in todo app or BACKLOG.md | — |
| Daytime | Code your feature (Cline + VS Code) | Sleep |
| Evening | Push your branch | — |
| 11 PM | Sleep | Wake up, pick unclaimed feature, build it |
| Next morning | 2 features progressed overnight | Done for night |

### Which Features Are Best for You vs Agents

| You + Cline | Agents |
|---|---|
| Complex UX decisions | Simple CRUD pages |
| Features needing your personal data | Data pipelines + cron jobs |
| Anything exploratory/POC | Unit test files |
| Business logic requiring your judgment | Alert bots + scrapers |

---

## PART 5 — Status Board (Terminal)

Run from repo root anytime:
```bash
cd ~/Downloads/darrian-budget
python3 status.py
```

Shows:
- 🧑‍💻 **YOUR FEATURES** — items you've claimed
- 🤖 **AGENT QUEUE** — next item highlighted with 🎯
- 🌿 **ACTIVE BRANCHES** — [YOU] vs [AGENT] labeled
- 📬 **OPEN PRs** — waiting your approval with direct links
- 📝 **RECENT COMMITS** — [D] Darrian vs [A] Agent tagged
- Progress bar: 0% → 100% across all backlog items

---

## PART 6 — SDLC Pipeline Reference

Every feature goes through:
```
feature/name → dev → qa → staging → main (prod)
```

Only `main` requires your manual approval. All other promotions are automatic.

### Promoting Code Manually (if needed)
```bash
cd ~/Downloads/darrian-budget

# Promote dev → qa
git checkout qa && git merge dev && git push origin qa

# Promote qa → staging
git checkout staging && git merge qa && git push origin staging

# Promote staging → main (triggers manual approval in GitHub Actions)
git checkout main && git merge staging && git push origin main

# Approve at:
# https://github.com/bookofdarrian/darrian-budget/actions
```

### Starting a New Feature (You)
```bash
git checkout dev && git pull origin dev
git checkout -b feature/your-feature-name
# code with Cline...
git add . && git commit -m "feat: description"
git push origin feature/your-feature-name
# Then merge: feature → dev → qa → staging → main
```

---

## PART 7 — Quick Reference

### Key URLs
| Resource | URL |
|---|---|
| Production app | https://peachstatesavings.com |
| Todo page | https://peachstatesavings.com/pages/22_todo |
| Notes page | https://peachstatesavings.com/pages/25_notes |
| GitHub repo | https://github.com/bookofdarrian/darrian-budget |
| GitHub Actions | https://github.com/bookofdarrian/darrian-budget/actions |
| Grafana monitoring | http://100.95.125.112:3000 |

### Key Files
| File | Purpose |
|---|---|
| `BACKLOG.md` | Feature queue for agents — edit to claim/add features |
| `AUTONOMOUS_AI_DEV_SYSTEM.md` | Full agent architecture + orchestrator script |
| `AI_TIPS_FROM_YOUTUBE.md` | AI learning frameworks + image-size error fix |
| `status.py` | Terminal status board (`python3 status.py`) |
| `SDLC_PROCESS.md` | Full pipeline documentation |
| `.clinerules/rule.txt` | Coding standards (read by Cline and agents) |

### Common Commands
```bash
# Status board
python3 status.py

# Run tests
cd ~/Downloads/darrian-budget && source venv/bin/activate && pytest tests/ -v

# Syntax check a page
python3 -m py_compile pages/22_todo.py && echo OK

# Check agent log (on CT100)
ssh root@100.95.125.112 "tail -50 /var/log/overnight-dev.log"

# Fix image-size error in Cline (shrink before attaching)
sips -Z 1920 screenshot.png --out screenshot.png
```

### Adding a New Feature to the Backlog
Simply add a line to `BACKLOG.md`:
```markdown
- [ ] My New Feature (short description of what it does)
```
Agents will pick it up the next night. Add `[YOU]` to work on it yourself.

---

## PART 8 — Notes App AI Tips

Based on the YouTube insights, here's how to use the Notes app as a learning tool:

### The Learning Framework in Notes
1. **Goal Note:** Create a note titled "GOAL: [What I'm Learning]" — keep it pinned
2. **Research Dump:** Paste Perplexity results into a note; tag it `research`
3. **NotebookLM Output:** Paste study guides + quizzes into notes; tag `priming`
4. **Processing:** Use AI Tools → Summarize to condense; Extract Tasks for action items
5. **Final Reference:** Use AI Tools → Improve Writing for clean final notes

### Recommended Notebooks
- **Learning** — notes from study sessions, summarized by AI
- **404 Sole Archive** — sneaker research, market notes, supplier contacts
- **Visa Work** — project notes, meeting summaries, code decisions
- **Budget Planning** — financial analysis, goal tracking, RSU vesting notes
- **Ideas** — quick captures (use voice input on the Todo page, then expand in Notes)

---

## PART 9 — Remote Work Connectivity Profile

Use the dedicated runbook for monitor, bookmarks, and multi-network fallback setup:

- `REMOTE_WORK_CONNECTIVITY_RUNBOOK.md`

Bootstrap command (safe dry run for Wi-Fi ordering):

```bash
cd ~/Downloads/darrian-budget
bash scripts/remote_work_bootstrap_macos.sh
```

To apply preferred SSID ordering:

```bash
cd ~/Downloads/darrian-budget
APPLY_WIFI_ORDER=1 PREFERRED_WIFI_SSIDS="Gigstreem,Verizon,Verizon Line,Dual-SIM Hotspot" bash scripts/remote_work_bootstrap_macos.sh
```
