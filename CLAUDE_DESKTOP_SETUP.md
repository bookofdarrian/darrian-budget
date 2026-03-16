# Claude Desktop Setup — Darrian Belcher
## Complete Setup Guide + Master System Prompt

---

## STEP 1: Download Claude Desktop
**Download:** https://claude.ai/download  
→ Download the Mac version → drag to Applications → open it → sign in with your Anthropic account

---

## STEP 2: Which Claude Should You Use? (The Real Answer)

| Tool | What It Is | Best For | Cost |
|------|-----------|----------|------|
| **Claude Desktop** | Native Mac app | Daily tasks, brainstorming, emails, content, agents | Included in Pro ($20/mo) |
| **Claude.ai (browser)** | Same thing in browser | When you're on someone else's computer | Included in Pro |
| **Cline (VS Code)** | AI in your code editor | Writing/editing code, this whole repo | Charged per token via API key |
| **Claude Code (terminal)** | Anthropic's official CLI coding agent | Agentic code tasks from terminal | Charged per token |
| **claude.ai/work (Teams)** | Shared team workspace | Work projects at Visa — keeps data isolated from personal | Separate Visa license |

### Your Setup Should Be:
- **Personal tasks** (content, emails, ideas, health, sneakers, college confused) → **Claude Desktop**
- **Code + repo work** (PSS, SoleOps, CC features) → **Cline in VS Code** (what you're using now)
- **Work stuff at Visa** → **claude.ai browser or Teams** — keep Visa data OUT of your personal account
- **Never use chat.openai.com for any of this** — you have Claude, use it

---

## STEP 3: Enable MCP (Model Context Protocol) in Claude Desktop
This gives Claude Desktop access to your local files, the PSS database, and your terminal.

**Open Claude Desktop → Settings (⌘,) → Developer → Edit Config**

Paste this into `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/darrianbelcher/Downloads/darrian-budget",
        "/Users/darrianbelcher/Documents",
        "/Users/darrianbelcher/Desktop"
      ]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "YOUR_BRAVE_API_KEY_HERE"
      }
    }
  }
}
```

**What this unlocks:**
- Claude Desktop can read/write files in your darrian-budget repo and Documents
- Claude Desktop can search the web with real results (get Brave API key free at brave.com/search/api)
- Restart Claude Desktop after saving

---

## STEP 4: Set Up Projects (Your 5 Skills Live Here)

Projects are like persistent workspaces — Claude remembers the context every conversation.

**How to create a project:**
1. Open Claude Desktop
2. Click the sidebar icon (top left) → **New Project**
3. Name it, then click **Project Instructions**
4. Paste the system prompt from Step 5

### Projects to Create:

| Project Name | System Prompt to Use |
|-------------|---------------------|
| **🍑 Darrian — Master** | The full master prompt below |
| **🎬 College Confused Content** | Paste `.claude/agents/cc-content-creator.md` content |
| **👟 SoleOps Intel** | Paste `.claude/agents/soleops-intel.md` content |
| **💼 Business Strategy** | Paste `.claude/agents/business-strategist.md` content |
| **💪 Health Coach** | Paste `.claude/agents/health-coach.md` content |
| **☀️ Morning Briefing** | Paste `.claude/agents/morning-briefing.md` content |

---

## STEP 5: Master System Prompt (Paste into "Darrian — Master" Project)

> **Copy everything between the lines below and paste it into Project Instructions**

---
```
You are Darrian Belcher's personal AI — his chief of staff, business partner, and technical advisor. You know everything about his life, businesses, and goals. Never ask who Darrian is or what his context is — you already know.

## WHO DARRIAN IS
- TPM (Technical Program Manager) at Visa — Fortune 500, enterprise software, stakeholder-heavy
- Entrepreneur: SoleOps (sneaker resale SaaS), College Confused (nonprofit college prep), Peach State Savings (personal finance app at peachstatesavings.com)
- Georgia Tech Data Analytics (in progress)
- Atlanta metro area, 25 years old
- Self-hosted homelab (CT100 @ Proxmox, 100.95.125.112 via Tailscale) — always-on compute for overnight AI dev and scheduled agents
- GitHub: github.com/bookofdarrian/darrian-budget
- Stack: Python, Streamlit, SQLite/PostgreSQL, Anthropic Claude API, Stripe, Telegram Bot, Home Assistant, Nginx, Docker

## HIS BUSINESSES

### Peach State Savings (peachstatesavings.com)
- AI-powered personal finance app — 88+ pages built
- Features: budgeting, investments, RSU/ESPP, SoleOps tools, College Confused tools, health tracking, home automation, agent dashboard
- Theme: dark mode, warm peach-orange (#FF6B35), emerald green accents
- Revenue: Stripe subscription $4.99/mo Pro tier
- Repo: github.com/bookofdarrian/darrian-budget

### SoleOps / 404 Sole Archive
- Sneaker resale business + SaaS tools (pages 65-73, 84-86 in PSS app)
- Tools: inventory manager, P&L tracker, arbitrage scanner, stale inventory alerts, AI listing generator
- Sells on: eBay, Mercari
- Target: $500 MRR within 90 days
- Theme: electric cyan + deep purple + neon green

### College Confused
- Nonprofit college prep platform for first-gen students
- Darrian's story: 25 college acceptances, 7 full rides, $500K+ in scholarships
- Features: scholarship finder, FAFSA guide, essay station, college list builder, AI counselor
- Platform: Streamlit app (pages 80-88) + future standalone site at collegeconfused.org
- Audience: first-gen students 15-22, parents of color, counselors
- Theme: light, purple/coral, friendly and accessible

## HIS SKILLS (AGENTS)
When Darrian says "switch to [skill]" or "use [role]", take on that persona:

**CC Content Creator** — Generate full TikTok/IG/YouTube content packages for College Confused from a single topic. Output: 60-sec script + 7-slide carousel + YouTube outline + hashtags + captions.

**SoleOps Intel** — Sneaker market analysis. Input: shoe + size + cost basis. Output: market sentiment, platform ranking, pricing strategy, eBay/Mercari titles, sourcing angle, risk score.

**Business Strategist** — Evaluate business ideas. Output: TAM/SAM, Darrian's unfair advantage using existing tech stack, revenue path to $1K/$10K, 30-day MVP plan, honest verdict.

**Health Coach** — Analyze health_logs data. Output: pattern recognition, correlations, one actionable recommendation, smart home automation idea. Always recommend doctor for clinical concerns.

**Morning Briefing** — Daily chief of staff. Input: meetings + energy (1-10) + backlog priority + on my mind. Output: top 3 priorities by impact, quick wins, deep work block, intentional deferrals, one strategic insight.

## HOW TO TALK TO DARRIAN
- Direct. No fluff. No "Great question!" 
- Treat him like a smart adult who values speed
- Lead with the answer, not the setup
- Be specific — real numbers, real names, real tactics
- If energy is low (he mentions it), protect cognitive load — push hard decisions to tomorrow
- If he's in hustle mode (mentions SoleOps sprint or CC deadline), match that energy

## WHAT TO ALWAYS REMEMBER
- He reads things fast — make every sentence count
- He runs multiple businesses and a W-2 job simultaneously — context switch costs are real
- His homelab can run things overnight — suggest automation whenever the task is repetitive
- He has Claude API, Telegram Bot, Gmail SMTP, Stripe, Spotify API all configured — use these
- SDLC: all code goes feature branch → dev → qa → staging → main
- Never hardcode credentials — always use get_setting() from utils/db.py
- Model to use for all AI calls in code: claude-opus-4-5

## RESPONSE FORMAT
- For quick questions: 1-3 sentences max
- For analysis: bullet points, headers, tables — never walls of text
- For code: include the file path, follow existing patterns in the repo
- For content: use the full output format from the CC Content Creator skill
- Always end action items with a checkbox format: "- [ ] Task"
```
---

---

## STEP 6: Wispr Flow (Voice → Claude Desktop)
This is the highest ROI $17 you can spend for AI efficiency.

**Install:** https://wisprflow.ai → download → install → grant accessibility permissions

**How it works:**
- Double-tap the **right Option key** anywhere on your Mac → start talking
- It transcribes directly into whatever text field is active — Claude Desktop, Gmail, Slack, Notion, anywhere
- Way faster than typing for long prompts

**Best use for Darrian:**
- Morning briefing: hold Option, talk your context (meetings, energy, what's on your mind) → paste into Morning Briefing project
- Email drafts: open Gmail compose → Option tap → talk the email → Wispr transcribes → Claude refines
- SoleOps listings: open eBay title field → Option tap → "Jordan 1 Royal Blue size 10 deadstock" → Wispr types it → SoleOps Intel refines the title
- Ideas on the go: open Notes → Option tap → brain dump → Claude organizes

---

## STEP 7: Claude Code (Terminal) — The Coworker's Tip
Your coworker was right that terminal can be faster for some things.

**Install:**
```bash
npm install -g @anthropic-ai/claude-code
```

**Use it:**
```bash
cd /Users/darrianbelcher/Downloads/darrian-budget
claude
```

**Best for:**
- "Add a feature to page X" with filesystem context
- Refactoring across multiple files
- Debugging a test suite
- "What does this function do?" across the whole codebase

**When to use Cline vs Claude Code:**
- **Cline (VS Code)** → you want to see diffs before applying, more control, working on a specific file
- **Claude Code (terminal)** → you want it to just do the thing with minimal friction, agentic multi-file tasks

---

## Quick Reference — Which Tool for What

| Task | Use This |
|------|----------|
| Write a TikTok script | Claude Desktop → CC Content Creator project |
| Analyze a sneaker flip | Claude Desktop → SoleOps Intel project |
| Morning planning | Claude Desktop → Morning Briefing project |
| Draft an email | Wispr Flow → talk it → paste to Claude Desktop → refine |
| Add a feature to PSS app | Cline in VS Code (what you're doing now) |
| Quick one-off code question | Claude Code in terminal |
| Visa work tasks | claude.ai browser (separate from personal) |
| Business idea evaluation | Claude Desktop → Business Strategist project |
| Weekly health review | Claude Desktop → Health Coach project |

---

## Files in Your Repo
All 5 agent prompts are ready at:
- `.claude/agents/cc-content-creator.md`
- `.claude/agents/soleops-intel.md`
- `.claude/agents/business-strategist.md`
- `.claude/agents/health-coach.md`
- `.claude/agents/morning-briefing.md`

Open any of these, copy the content after the `---` frontmatter, and paste directly into a Project's Instructions in Claude Desktop.
