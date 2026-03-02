# AI Tips & Frameworks — From YouTube Research
**Owner: Darrian Belcher | Created: 2026-03-02**

> Insights from Hank Green, Edan Meyer, and "How I Learn Things Really Fast"
> translated into actionable steps for the budget app, overnight dev system,
> and personal learning workflows.

---

## 1. Hank Green — "My Biggest Fear About AI"

**On choice removal:**
People prefer their choices taken away (TikTok algorithm > chronological).
Your overnight dev system is the right move: AI executes, YOU decide what to build.
Never let AI pick the "what" — only the "how."

**On creativity:** AI replaces creation, social media replaces analysis.
Counter: Use AI for implementation. Keep product vision, UX taste, and
business judgment 100% human.

**On domain-specific models:**
Smaller, focused models beat large general-purpose ones.

Applied to your system:
- Separate focused agents (DB bot, UI bot, test bot) instead of one mega-agent
- Feed each agent ONLY the context it needs
- Use Claude Haiku for tests, Claude Opus for architecture/planning
- Future: fine-tune a local Llama model on your own codebase

**Cost structure with your homelab:**
- Homelab hardware: already paid for ($0/month marginal)
- Claude API: ~$5-10/month (with AURA 40% compression)
- Overnight dev runs: ~$1/night x 30 = $30/month max
- Total: ~$40/month for a fully automated dev team

---

## 2. Edan Meyer — "The AI Scaling Problem"

**On autonomous agents:**
Build an agent that has goals, controls its own data stream, and teaches
itself. It should want to learn without human intervention.

Applied to your overnight system — self-learning loop to add to orchestrator.py:

    def update_backlog_from_results(plan, qa_passed, error=""):
        backlog = Path(BACKLOG_PATH).read_text()
        if qa_passed:
            backlog = backlog.replace(
                f"- [ ] {plan['description'][:50]}",
                f"- [x] {plan['description'][:50]}"
            )
        else:
            note = f"\n  > Previous attempt failed: {error[:100]}"
            backlog = backlog.replace(
                f"- [ ] {plan['description'][:50]}",
                f"- [ ] {plan['description'][:50]}{note}"
            )
        Path(BACKLOG_PATH).write_text(backlog)

The goal-driven loop:
  Night 1: Pick feature -> Build -> QA passes -> Ship -> Check off backlog
  Night 2: Reads git history -> avoids rebuilding what exists
  Night 3: Sees "HSA tracker exists" -> skips -> picks next item

---

## 3. "How I Learn Things Really Fast (with AI)"

### The 5-Step Framework
  1. GOAL     - Define what you are trying to achieve (keep it in mind always)
  2. RESEARCH - Perplexity AI: how did others solve this? Reddit, Twitter, docs
  3. PRIMING  - NotebookLM: upload course/video, generate study guide + quizzes
  4. FORMAT   - Convert to preferred format: audio podcast, slides, dashboard
  5. DIVE     - Layer in more detail at each level

### Applied to Tech Learning (example: real-time Streamlit updates)
1. Goal: "Price alerts appear instantly without page refresh"
2. Research (Perplexity): "streamlit real-time updates 2025 reddit"
3. Priming (NotebookLM): upload Streamlit docs, generate quiz
4. Format: Ask Cline to build minimal example first
5. Dive: Add Postgres LISTEN/NOTIFY, then WebSocket if needed

### Applied to Business Learning (example: sneaker market timing)
1. Goal: "Know when to buy Jordan 1s in the resale cycle"
2. Research: Perplexity -> "Jordan 1 resale cycle reddit stockx"
3. Priming: Upload market report to NotebookLM, quiz yourself
4. Format: Ask Claude to make an interactive dashboard tab
5. Dive: Build price history chart with your eBay + Mercari data

---

## 4. General AI Tips (Synthesized)

### Energy Management Over Time Management
Your energy map:
  High energy (morning):     Strategic decisions, PR reviews, feature planning
  Medium energy (afternoon): Active Cline sessions, reviewing AI output
  Low energy (evening):      Add items to BACKLOG.md, let overnight system run
  Night:                     Agents work autonomously

Rule: Never start a complex Cline session when tired. Add it to BACKLOG.md.

### Learn Multiple Topics in Parallel (1 Hour Each)
Better to do 1 hour of 5 topics than 5 hours of 1 topic.

Week structure:
  Mon: 1hr - Streamlit/Python (budget app feature)
  Tue: 1hr - DevOps/homelab (Proxmox, Docker, monitoring)
  Wed: 1hr - Finance/investing (RSU strategy, ESPP)
  Thu: 1hr - Business (404 Sole Archive, pricing, sourcing)
  Fri: 1hr - AI/ML (agent patterns, prompt engineering)

### Right Tool for Each Job
  Perplexity AI         - Quick factual research
  NotebookLM            - Deep document learning + quizzes
  Cline + Claude Opus   - Code generation and editing
  Gamma or Manus        - Slide decks
  Google AI Studio      - Audio/podcast format learning
  Overnight orchestrator- Autonomous feature development

### Prompt Tips for Cline
1. State the goal first: "I want to build X that does Y for Z reason"
2. Give constraints: "Must follow .clinerules, use existing get_conn() pattern"
3. Reference existing files: "See how pages/22_todo.py does the sidebar"
4. One feature per session: never ask Cline to build 3 things at once
5. Use BACKLOG.md as prompt prep: detailed backlog items = better Cline output

---

## 5. Fix for the Cline Image-Size Error

### What Happened
  image exceeds 5 MB maximum: 8256568 bytes > 5242880 bytes

A screenshot ~8MB was attached. Anthropic API limit is 5MB.
isRetryable: false means retrying never helps — fix the image first.

### Fix Options

Option 1 (Mac terminal - recommended):
  sips -Z 1920 screenshot.png --out screenshot_small.png
  Add alias to ~/.zshrc: alias shrink='sips -Z 1920 "$1" --out "$1"'

Option 2 (Preview.app):
  File -> Export -> JPEG -> Quality 70% = 8MB becomes ~1.5MB

Option 3 (crop first):
  Use Cmd+Shift+4 to screenshot only the relevant area instead of full screen

Option 4 (best for Cline):
  Paste the text/error message instead of a screenshot.
  Text = no size limit AND more useful for debugging.

---

## 6. New Rules to Add to .clinerules/rule.txt

## AUTONOMOUS DEV SYSTEM
- Check BACKLOG.md before starting any feature (avoid duplicates)
- When completing a feature, check it off in BACKLOG.md
- Each Cline session = ONE feature, ONE PR, ONE approval
- Use Claude Haiku for tests/simple tasks, Claude Opus for architecture

## LEARNING FRAMEWORK
1. Define the goal in one sentence before writing any code
2. Check NEXT_USECASES.md for existing implementation guidance
3. Reference a similar existing page before building new patterns
4. Keep sessions focused: one feature at a time

## IMAGE ATTACHMENTS IN CLINE
- Never attach images larger than 4MB
- Use text/error messages instead of screenshots when possible
- Resize with: sips -Z 1920 image.png --out image.png
