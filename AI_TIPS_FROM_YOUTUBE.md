# AI Tips & Frameworks — From YouTube Research
**Owner: Darrian Belcher | Updated: 2026-03-17**

> Insights from Hank Green, Edan Meyer, Tina Huang (3 videos)
> translated into actionable steps for the budget app, overnight dev system,
> personal learning workflows, and Visa workstation upgrade.

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

## 3. Tina Huang — "How I Learn Things Really Fast"

### The Jigsaw Puzzle Analogy
Learning = assembling a puzzle:
- **Goal** = picking WHICH puzzle to solve
- **Research** = finding the missing pieces
- **Priming** = sorting pieces before assembly
- **Comprehension** = assembling it, layer by layer
- **Implementation** = connecting all patches into the complete picture

### The 5-Step Framework
  1. GOAL           - Define the EXACT end result (not a vague topic)
  2. RESEARCH       - Perplexity AI: how did others solve this? Reddit, Twitter, docs
  3. PRIMING        - NotebookLM: upload course/video, generate study guide + quiz
  4. COMPREHENSION  - Layer 1: concepts only → Layer 2: examples → Layer 3: deep details
  5. IMPLEMENTATION - Build/apply it (active recall = 10x better than passive reading)

### Time Allocation Without AI
  | Stage | % of Time |
  |-------|-----------|
  | Goal | 0–5% |
  | Research | 0–10% |
  | Priming | 2–5% |
  | Comprehension | 40–60% |
  | Implementation | 20–40% |

### Time Savings WITH AI (saves ~20 hours per 30-hour learning goal)
  | Stage | AI Tool | Time Saved |
  |-------|---------|-----------|
  | Research | Perplexity Deep Research | ~3 hours |
  | Priming | NotebookLM study guide + quiz | ~1 hour |
  | Comprehension | Format conversion + ChatGPT Audio | ~7 hours |
  | Implementation | Claude Code / Manus / Gamma | ~6 hours |

### Stage-by-Stage AI Tool Guide

**RESEARCH → Perplexity AI**
- Search: "how to learn [TOPIC] fast reddit 2025"
- Ask: "What are the top 3 courses for [TOPIC] for [YOUR SPECIFIC GOAL]?"
- Use Deep Research mode for complex technical topics
- Set a 20-min timer — ADHD rabbit hole risk is real here

**PRIMING → NotebookLM**
- Upload your resources (docs, videos, PDFs)
- "Generate a study guide with key topics"
- "Generate a quiz I should take BEFORE studying"
- Take the quiz without Googling — the point is priming, not scoring
- Skim course titles/headers for 15-20 minutes
- For coding: look at starter code / final product FIRST

**COMPREHENSION → ChatGPT Audio + NotebookLM + Google AI Studio**
- Pass 1 (2x speed): definitions, major concepts, full examples ONLY
- Pass 2: normal speed, fill gaps
- Pass 3: deep dive on weak areas
- NEVER deep-dive one concept before finishing the overview
- Format conversion for audio learners:
  Google AI Studio prompt: "Transform this text into a single-person podcast script.
  Only include definitions, concepts, and full examples. No commentary."
- Format conversion for visual learners:
  Claude/Sonnet: "Build an interactive diagram or dashboard from these notes"
- Talk through confusion: ChatGPT Audio Mode — talk it out loud
- Note organization: messy notes → NotebookLM → Claude → interactive dashboard

**IMPLEMENTATION → Claude Code / Windsurf / Manus / Gamma**
- For code: Cline + Claude Opus (complex) or Bolt.new (standalone web)
- For essays/reports: NotebookLM outline → ChatGPT write
- For slides: Gamma or Manus
- For data analysis: Claude → interactive dashboard
- Start SMALL — minimum viable version first, iterate

### Comprehension: Layered Learning Detail
- Do NOT try to master one concept before moving on
- Get an overview of ALL topics first, then deepen
- Example (personal finance): first pass covers budgeting → saving → debt → investing
  Each topic: only note definition + major concept + one full example
  Second pass: go deeper into each
- This is in contrast to getting stuck on one concept and banging your head against the wall

### ADHD/Bipolar Adaptation of the Framework

**Energy Management Over Time Management** (Tina's #1 tip)
The mistake: scheduling study based on WHEN you have time
The fix: scheduling study based on WHEN you have ENERGY

For ADHD + Bipolar:
  🔥 High energy (morning): Complex comprehension, new concepts, implementation
  ⚡ Medium energy (afternoon): Second-pass review, examples, practice
  😴 Low energy (evening): Priming only, light audio at 1x, note review
  🚫 Burnout day: Do NOT study. Your brain consolidates memory during rest.

**ADHD-Specific Rules:**
1. 20-min timer on research phase (Perplexity rabbit hole is dangerous)
2. Priming = perfect for ADHD: fast, low-stakes, creates dopamine via curiosity
3. Format conversion is critical: if a textbook kills you, turn it into audio
4. Never go >90 min on any single topic in one session
5. Interleaving keeps novelty high = more dopamine = more focus

**Bipolar-Specific Rules:**
1. High days: cap total study at 90 minutes. Hyperfocus → crash later.
2. Low days: even 15 minutes of priming counts. Show up anyway.
3. Track which stage you're in so you can resume exactly where you left off

### Interleaving (Tina's #2 tip)
Learning multiple topics SIMULTANEOUSLY outperforms blocking (one topic per day).

Instead of: Monday = personal finance, Tuesday = AI agents, Wednesday = Spanish
Do this:   Each day = 1hr Spanish + 1hr personal finance + 2hr AI agents

Benefits:
- Proven better long-term retention vs. blocked studying
- Keeps novelty high (ADHD brain loves this)
- Prevents burnout on any one topic
- Mimics real-world context switching

Applied to Darrian's learning weeks:
  Mon: 30min System Design + 30min Sneaker Business
  Tue: 30min AI Agents + 20min Cloud/DevOps
  Wed: 30min College Confused content + 30min Personal Finance
  Thu: 30min Career Growth + 20min Domain knowledge
  Fri: 1hr free choice (highest interest topic)
  Weekend: longer sessions (up to 2-3hr total, mixed)

---

## 4. Tina Huang — "My Favorite AI Workflow Right Now" (Hyper-Specific Apps)

### What is a Hyper-Specific App?
**Definition:** Using AI-assisted coding to build software for very specific personal/business
use cases that would NEVER exist as commercial software.

**Why build them:**
- Custom features impossible to find in commercial software
- Essentially free to build ($10-20) and run (homelab = $0/month)
- Full control over data and privacy
- No coding required to START (although coding knowledge helps ceiling)
- Build in 2-3 hours vs. months without AI tools

### Three Categories (where to find your first app idea)

**Category 1: Bane of Your Existence** (must do but hate it)
  Examples: accounting, bookkeeping, tax forms, expense reports, email triage
  → Already built: pages/32_hsa_receipt_vault.py, pages/51_tax_document_vault.py

**Category 2: Procrastinating On** (important but always deferred)
  Examples: health tracking, inventory updates, financial reviews, note organization
  → Built: pages/40_car_mileage_tracker.py, pages/41_health_cost_tracker.py

**Category 3: Want But Can't** (blocked by skills/time/resources)
  Examples: manga generator, custom slide maker, AI trading system, game
  → Already built: pages/29_ai_trading_bot.py

### The 5-Step Build Process
  Step 1: IDENTIFY which workflow to automate (use the 3 categories above)
  Step 2: MAP the current workflow (list every manual step)
  Step 3: SCOPE which steps the app should handle (not necessarily all of them)
  Step 4: BUILD using AI-assisted coding + PRD (product requirements doc)
  Step 5: HOST (own hardware/homelab, VPS, or cloud)

### Building: The TFCDC / "Tiny Ferrets Carry Dangerous Code" Framework

**T — Thinking** (4 levels of thinking to do BEFORE prompting):
  1. Logical: What IS this thing?
  2. Analytical: How does it work?
  3. Computational: How do I implement it correctly?
  4. Procedural: How do I make it excellent?
  → Express all 4 levels in your PRD

**F — Frameworks:**
  Don't reinvent the wheel. List existing libraries the AI should use.
  Python + Streamlit = PSS pages. React + Tailwind = web apps (Bolt).
  Ask AI: "What frameworks exist for [feature]?"

**C — Checkpoints:**
  Version control with git at every working milestone.
  PSS SDLC: feature → dev → qa → staging → main

**D — Debugging:**
  Copy exact error message to AI. Include screenshot.
  If stuck >3 attempts: git reset and try different approach.

**C — Context:**
  More context = better output. Include mock-ups, examples, existing code references.
  "See how pages/22_todo.py handles the sidebar pattern"

### Hosting Decision (Tina's 3 options applied to Darrian's setup)

  **Own Hardware (CT100 homelab) → DEFAULT CHOICE**
  - Already paid for, privacy, free to run
  - Best for: new PSS pages (just add file), personal tools, private data
  - Deploy: git push → systemctl restart streamlit

  **VPS (Hetzner/DigitalOcean, ~$4-6/mo)**
  - Best for: public-facing tools, College Confused if >100 users
  - Recommended: Hetzner CAX11 €3.79/mo + Coolify for deployment GUI

  **Cloud (Railway/Render/Fly.io)**
  - Best for: demos, prototypes, open-source projects
  - Avoid for: sensitive data, tools that need to always be up

### College Confused Hosting Assessment (Blunt)

**STAY IN STREAMLIT/PSS** for now. Here's why:
  - Already built and working (pages 80-88)
  - Integrated with PSS auth/DB — free to run on homelab
  - AI features use existing Anthropic key
  - SDLC pipeline already set up

**Move CC to its own platform WHEN:**
  - >100 active users (Streamlit performance degrades)
  - You want mobile app experience
  - You need public registration (without PSS account)
  - You need payments/monetization

**Migration path when ready:**
  - Frontend: Next.js + Tailwind (build with Bolt.new)
  - Backend: FastAPI on Hetzner VPS
  - DB: Postgres (migrate_to_postgres.py already exists)
  - Auth: Clerk or Supabase Auth
  - Host: Hetzner VPS + Coolify (~$6/month)

---

## 5. Tina Huang — "Vibe Coding Fundamentals in 33 Minutes"

### What is Vibe Coding?
Fully giving in to AI for code generation. You describe in natural language what you want,
the LLM builds it. No keyboard required for basic interactions.
Coined by Andrej Karpathy (OpenAI co-founder) Feb 2025.

### The 5 Principles (TFCDC — The Friendly Cat Dances Constantly)
  T = Thinking     F = Frameworks     C = Checkpoints     D = Debugging     C = Context

**Think through ALL 4 levels before prompting:**
  1. Logical: chess game → "what is the game?"
  2. Analytical: "how do I play? what are the rules?"
  3. Computational: "how do I enforce the rules in code?"
  4. Procedural: "how do I make it excellent? win strategies?"

**Best practice: PRD (Product Requirements Document)**
  - Defines purpose, features, functionalities, behaviors
  - Goes into your AI coding tool to kick off the build
  - Include: project overview, tech stack, key features (MVP first), data requirements,
    integration points, edge cases
  - Generate your PRD by asking Claude/ChatGPT: "Help me write a PRD for X"

**Tool Selection Guide:**
  | Scenario | Tool |
  |----------|------|
  | Complex, multi-file PSS pages | Cline + Claude Opus (current setup) |
  | Standalone web apps | Bolt.new |
  | Complete beginner | Replit |
  | Pro dev, scalable | Windsurf or Cursor |
  | Large parallel builds | Claude Code CLI |

**Minimal Viable Product Mindset:**
  ALWAYS start with minimum features needed to function.
  Get it working FIRST, iterate after.
  Don't ask AI to build 10 features at once — that's where errors compound.

**Two Modes at All Times:**
  Mode 1: IMPLEMENTING new feature
    → Provide full context, PRD, frameworks, documentation
    → Incremental changes, commit checkpoints, test each feature
  Mode 2: DEBUGGING errors
    → Understand your project structure first (ask AI to explain file structure)
    → Paste EXACT error message
    → Screenshot the UI issue
    → Point to the specific file/line
    → If loop >3 attempts: git reset

**Rules file tip:**
  Add a .clinerules or system prompt to your AI coding tool with:
  - "Limit code changes to minimum when implementing a new feature"
  - "Always follow the existing db.py and auth.py patterns"
  - "Check BACKLOG.md before starting any feature"

### Git/GitHub Crash Course (for vibe coders)
  git init                          # start tracking
  git add .                         # stage all files
  git commit -m "feat: initial"     # save version
  git log                           # see history
  git reset --hard HEAD~1           # roll back if broken
  git push origin feature/my-app   # push to GitHub

### Tina's Key Lessons from Vibe Coding
  1. Understand the HIGH-LEVEL structure (frontend/backend/DB), not the low-level code
  2. The more context you give AI, the better the output
  3. Debug with method: identify → solution → apply → test → repeat
  4. Learn ALONGSIDE the AI (ask it to explain the file structure)
  5. Always start small (MVP mindset)

---

## 6. Tina Huang — "Every AI Model Explained"

### The Plane Analogy
  Flagship = large commercial airline (most capable, expensive, slower)
  Mid-tier = Boeing 737 workhorses (80% of use cases, balanced)
  Light = private jet (fast, cheap, less capable)
  Open Source = buy your own plane (private, free, you maintain it)
  Specialist = search/rescue helicopter (optimized for one thing)

### Model Quick Reference (2026)

**Flagship Models:**
  | Model | Strengths | Weakness |
  |-------|-----------|---------|
  | Claude Opus 4.5 | Code, writing, best overall | Slow, most expensive, no image gen |
  | GPT-4o / GPT-5 | Well-rounded, multimodal, chains actions | Not the best at any one thing |
  | Gemini 2.5 Pro | Multimodal king, 2M context, video/image | |
  | Grok 4 | Highest EQ, empathetic, FAST, cheap for flagship | |

**Mid-Tier Models (your daily drivers):**
  | Model | Best For |
  |-------|---------|
  | Claude Sonnet 4.5 | Code, writing, daily driver — best balance |
  | GPT-4o-mini | Budget OpenAI option |

**Light Models (speed priority):**
  | Model | Best For |
  |-------|---------|
  | Gemini 2.5 Flash | Fastest quality, retains 90-95% of Pro's capability |
  | Claude Haiku | Cheapest Claude, great for tests and simple queries |

**Open Source (privacy + free):**
  | Model | Best For |
  |-------|---------|
  | Kimi K2.5 | Flagship quality + open source. Run locally or via Perplexity |
  | Llama 3.3 | Run locally on homelab CT100 |
  | Qwen | Multilingual, strong on reasoning |

  Use open source for: financial data analysis, email reading, anything sensitive
  Run on CT100 homelab = completely private, no data leaks, free after hardware cost

**Specialist Models:**
  | Model | Best For |
  |-------|---------|
  | Perplexity Sonar | Research with verified citations (built on Llama) |

### Decision Tree for Model Selection
  Is data PRIVATE (financial, health, emails)?
  → YES: Use open source (Kimi/Llama) on CT100 homelab
  → NO: Continue...
    Speed #1 priority?
    → YES: Gemini 2.5 Flash or Claude Haiku
    → NO: Continue...
      Coding or writing task?
      → YES: Claude Opus 4.5 (complex) or Sonnet 4.5 (daily use)
      → NO: Continue...
        Multimodal (images/video)?
        → YES: Gemini 2.5 Pro
        → NO: Claude Sonnet 4.5 (your default)

### Perplexity as Model Aggregator
Tina uses Perplexity to access multiple models without paying for each subscription:
- GPT-5.2, Claude Opus 4.6, Grok, Gemini, Kimi K2 — all via one Perplexity sub
- Model Council feature: compare 3 models side-by-side on the same prompt
- Saves ~$80-100/month in individual subscriptions
- Great for evaluating which model is best for a specific task

### Darrian's Default Model Stack
  PSS page AI features  → Claude Opus 4.5 via get_setting("anthropic_api_key")
  Financial analysis    → Kimi K2 / Llama on CT100 (privacy)
  Quick summaries       → Claude Haiku (cheap)
  Research              → Perplexity Sonar
  Code generation       → Claude Opus 4.5 (via Cline)
  Slide decks           → Gamma or Manus
  Learning research     → Perplexity
  Document learning     → NotebookLM

---

## 7. General Synthesized Tips

### Energy Management Over Time Management
Your energy map:
  High energy (morning):     Strategic decisions, PR reviews, feature planning, comprehension
  Medium energy (afternoon): Active Cline sessions, reviewing AI output, examples/practice
  Low energy (evening):      Add items to BACKLOG.md, light priming, let overnight system run
  Night:                     Agents work autonomously

Rule: Never start a complex Cline session when tired. Add it to BACKLOG.md instead.

### Learn Multiple Topics in Parallel (Interleaving)
Better to do 1 hour of 5 topics than 5 hours of 1 topic.

Week structure:
  Mon: 30min - System Design / Architecture
  Tue: 30min - DevOps/homelab (Proxmox, Docker, monitoring)
  Wed: 30min - Finance/investing (RSU strategy, ESPP, SoleOps P&L)
  Thu: 30min - Business (SoleOps pricing, sourcing, scaling)
  Fri: 30min - AI/ML (agent patterns, prompt engineering, new models)
  Commute: Audio (reinforcement of whatever you studied that day)

### The Right AI Tool for Each Job
  Perplexity AI         - Resource finding, Reddit research, course comparison
  NotebookLM            - Deep document learning, study guides, quizzes, format conversion
  Google AI Studio      - Text/doc → audio podcast script (audio learners)
  ChatGPT Audio Mode    - Talk through confusion out loud
  Claude Opus 4.5       - Code, writing, interactive dashboards
  Gamma or Manus        - Slide decks in minutes
  Cline + Claude        - PSS pages, hyper-specific app building
  Bolt.new              - Standalone web apps, no-code friendly
  Kimi K2 / Llama       - Private data analysis on homelab

### The Full PSS Learning Ecosystem
  pages/89_learning_system.py  → Learning goals tracker + ADHD schedule + AI coach
  pages/90_ai_workflow_hub.py  → Hyper-specific app planner + model advisor + TFCDC guide
  WORKSTATION_AI_UPGRADE.md    → Send to Visa workstation for work productivity
  AI_TIPS_FROM_YOUTUBE.md      → This file (canonical reference)

---

## 8. Prompt Tips for Cline (Updated)
1. State the goal first: "I want to build X that does Y for Z reason"
2. Give constraints: "Must follow .clinerules, use existing get_conn() pattern"
3. Reference existing files: "See how pages/22_todo.py does the sidebar"
4. One feature per session: never ask Cline to build 3 things at once
5. Use BACKLOG.md as prompt prep: detailed backlog items = better Cline output
6. Include framework hints: "Use the _ensure_tables() pattern from pages/25_notes.py"
7. Specify the model tier: complex architecture → Claude Opus; simple tasks → Haiku

---

## 9. Fix for the Cline Image-Size Error

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
  Use Cmd+Shift+4 to screenshot only the relevant area

Option 4 (best for Cline):
  Paste the text/error message instead of a screenshot.
  Text = no size limit AND more useful for debugging.

---

## 10. .clinerules Additions (from Tina's vibe coding video)

```
## VIBE CODING RULES (from Tina Huang's framework)
- Always create a PRD before starting any new page or feature
- Limit code changes to the MINIMUM when implementing a feature
- Do NOT change unrelated files during implementation
- Start with MVP — minimum viable features that work
- Commit checkpoints after each working milestone
- When debugging: copy exact error → give to AI → accept fix → test → repeat
- If bug persists >3 cycles: git reset and approach differently

## LEARNING SYSTEM RULES
- Check BACKLOG.md before starting any feature (avoid duplicates)
- Reference similar existing pages before building new patterns
- Energy management: complex Cline sessions only when energy is HIGH
- One feature per session: context switching kills quality

## AUTONOMOUS DEV SYSTEM
- When completing a feature, check it off in BACKLOG.md
- Each Cline session = ONE feature, ONE PR, ONE approval
- Use Claude Haiku for tests/simple tasks, Claude Opus for architecture
```
