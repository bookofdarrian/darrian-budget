# Workstation AI Upgrade Guide
**For: Visa Workstation (Windows) | Owner: Darrian Belcher**  
**Based on: Tina Huang's AI Workflow Videos (2025-2026)**  
**Created: 2026-03-17 | Send this file to your Visa machine**

---

## 🎯 The Goal

Transform your Visa workstation into an AI-powered productivity system using:
1. **Free or already-accessible tools** (no corporate policy issues)
2. **Tina Huang's Hyper-Specific App workflow** for work tasks you hate
3. **The right AI model for each job** 
4. **ADHD/Bipolar-adapted workflows** that respect your energy

---

## ⚠️ Corporate Tool Constraints

Before installing anything on a Visa workstation, check with IT security.  
These recommendations are split into:
- ✅ **Safe** — browser-based, no install required
- ⚡ **Check first** — may need IT approval
- 🏠 **Homelab alternative** — use your CT100 instead

---

## 🛠️ Section 1: AI Tools to Set Up at Work

### 1a. Perplexity AI (Research + Resource Finding)
**✅ Safe — browser-based at perplexity.ai**

**What to use it for at work:**
- Finding documentation for unfamiliar Visa tech stack/frameworks
- "How do other engineers at large companies implement X?"
- Researching compliance/security requirements quickly
- Reddit-style research without the scrolling: `"[topic] site:reddit.com best practices"`

**Key prompts for work:**
```
# Learning a new tech quickly:
"How do engineers at enterprise companies learn [TOPIC] fast? 
What are the best resources from Reddit r/devops r/programming? 
What do they recommend for someone with 2-3 hours per week?"

# Finding internal patterns:
"What are best practices for [VISA TECH STACK COMPONENT] in 2026? 
Focus on enterprise/financial industry patterns."

# Deep Research mode:
Enable Deep Research for regulatory/compliance topics that need citations
```

---

### 1b. NotebookLM (Document Learning + Study Guides)
**✅ Safe — browser-based at notebooklm.google.com**

**What to use it for at work:**
- Upload internal documentation, architecture docs, onboarding materials
- "Generate a study guide from this 50-page architecture doc"
- "Create quiz questions from this RFC/design doc"
- Pre-learning (priming) before a big technical meeting
- Transform boring PRDs into audio podcast format for commute listening

**Key prompts:**
```
# Priming before a meeting:
"Generate a study guide from this document with:
1. Key definitions
2. Major concepts
3. 5 quiz questions I can answer BEFORE the meeting"

# Audio conversion (great for commute):
"Transform this document into a single-person podcast script. 
Only include definitions, concepts, and examples. No commentary or filler."
Then download the audio and listen at 2x on commute.

# Note organization:
"Here are my messy notes from today's architecture review: [paste]
Please organize them into: Key Decisions, Open Questions, Action Items, Definitions"
```

---

### 1c. Claude.ai (Writing, Code Review, Analysis)
**✅ Safe — browser-based at claude.ai**
**⚡ Check if Anthropic Teams is available through Visa**

**What to use it for at work:**
- Code review: paste a diff and ask "What are the risks in this change?"
- Architecture review: "Here's our current design. What are the failure points?"
- Writing: PR descriptions, incident reports, design docs, emails
- Learning: "Explain [concept] to me as if I'm a senior SWE who's never used it"

**Work-specific prompts:**
```
# PR description writer:
"Write a professional PR description for this diff: [paste diff]
Include: What changed, Why it changed, How to test it, Risks"

# Incident report:
"Write a professional incident report based on these notes: [paste]
Format: Timeline, Root Cause, Impact, Resolution, Prevention"

# Learning new tech:
"I'm a senior SWE at Visa (financial services). 
Explain [TOPIC] with examples relevant to high-volume payment processing.
Skip basics, focus on what trips up experienced engineers."

# Email drafting:
"Draft a professional email to my manager explaining: [situation]
Be direct, specific, and solution-oriented. Max 3 paragraphs."
```

---

### 1d. ChatGPT (Audio Mode for Commute/Walking Learning)
**✅ Safe — mobile app + web**

This is Tina's favorite tool for audio learners. The trick:
1. Open ChatGPT mobile app → Advanced Voice Mode
2. Talk through problems OUT LOUD during commute/lunch
3. "I'm confused about X, talk me through it"
4. Use it to prep for meetings by talking through what you know

**Specific use cases:**
- Commute: discuss architecture decisions while driving
- Walking: "What are the tradeoffs of X vs Y in distributed systems?"
- Pre-meeting: talk through what you know, identify gaps
- After learning sessions: explain concepts out loud to reinforce retention

---

### 1e. Google AI Studio (Format Conversion)
**✅ Safe — browser-based at aistudio.google.com**

Transform boring work documents into formats you'll actually absorb:

```
# Text → Audio Podcast (for audio learners):
1. Open Google AI Studio
2. Click "Stream Realtime" tab  
3. Paste your document with this prompt:
"Transform this content into a single-person podcast script. 
Only include definitions, key concepts, and full examples.
No commentary, no filler words, be concise.
[PASTE DOCUMENT]"
4. Download the audio → listen at 2x speed on commute

# Video/Recording → Summary:
Upload a recorded meeting/demo and ask:
"Extract: Key decisions made, Action items assigned to whom, 
Open questions, Technical concepts explained"
```

---

## 🧠 Section 2: ADHD/Bipolar Work Workflow

### Energy Management at Work

```
VISA WORK ENERGY CALENDAR:

Morning (pre-standup, 8-9am):
  🔥 HIGH ENERGY → Complex coding, architecture decisions, code reviews
  → This is your best brain. Protect it. No meetings, no Slack.

Mid-morning (10am-12pm):
  ⚡ GOOD ENERGY → Feature development, writing design docs, PR reviews
  
Lunch (12-1pm):
  😴 LOWER → Admin, documentation updates, Jira tickets, email
  → Use 15 minutes for light learning (podcast/audio)

Post-lunch (1-3pm):  
  ⚡ RECOVERY → Meetings are okay here (not requiring deep work)
  → Use AI tools to prepare for afternoon meetings at 12:45

Late afternoon (3-5pm):
  😴 DECLINING → Wrap up tasks, write tomorrow's notes, respond to email
  → Never start a new complex feature at 4pm

Commute home:
  🎧 PASSIVE → ChatGPT Audio / NotebookLM podcast for learning
  → Let your brain absorb at 2x speed passively
```

### Meeting Prep System (15 minutes before any meeting)
```
1. Open NotebookLM or Claude
2. Paste the meeting agenda/doc
3. Ask: "What are the 3 most important things I need to understand 
   before this meeting? Give me the key background in 2 minutes."
4. Note ONE question you want to ask
5. Done.
```

### ADHD Work Rules
- **Never open Slack + code at the same time.** Notifications = context switching = 23-min recovery
- **Batch email/Slack:** Check at 9am, 12pm, 4pm only
- **One task at a time in your IDE.** If you think of something else, add it to a quick-capture note, don't switch
- **Use the 25-5 Pomodoro:** 25 min focused work, 5 min break. No exceptions.
- **End-of-day brain dump:** 5 min before logging off, write tomorrow's top 3 tasks in a note

---

## 🔧 Section 3: Hyper-Specific Work Apps to Build

Using Tina's framework: identify what takes the most time/annoyance, build an app.

### App Idea 1: Work Learning Tracker
**Problem:** You take courses for Visa certifications and lose track of what you've learned  
**Tool:** NotebookLM + Claude  
**Build:** Simple spreadsheet → Google Sheet with AI-generated study guide links

### App Idea 2: PR Description Generator
**Problem:** Writing good PR descriptions takes 10-15 minutes and you skip it  
**Build with:** Bolt.new → simple web app: paste diff → generate professional PR description  
**Hosting:** Run locally (no Visa data leaves your machine) or Homelab CT100

### App Idea 3: Meeting Prep Agent
**Problem:** You go into meetings under-prepared  
**Build with:** n8n or Make.com (no code) → Reads your calendar → 30 min before each meeting, fetches the agenda, runs through Claude, emails you a briefing  
**⚡ Check IT policy first** for calendar integration

### App Idea 4: Code Review Assistant  
**Problem:** Code reviews take forever; you miss things  
**Build with:** Bolt.new → paste diff → AI gives structured review (security, performance, clarity)  
**Model to use:** Claude Sonnet 4.5 (best code understanding, mid-tier cost)

### App Idea 5: Jira Ticket Writer
**Problem:** Writing good Jira tickets from vague requirements is painful  
**Build with:** Bolt.new → describe problem in plain English → generates Jira-formatted ticket with acceptance criteria  
**Hosting:** Local Chrome extension (free) or web app on homelab

---

## 📚 Section 4: Work Learning System

Apply Tina's 5-step framework to learning at Visa:

### When Learning a New Visa Technology/System

**Step 1 — Goal (5 min)**
- Don't say "learn Kubernetes." Say "be able to deploy my service without help by Friday."
- Write it down before you start.

**Step 2 — Research (20 min max — SET A TIMER)**
- Perplexity: "How do senior engineers at financial companies learn [TOPIC] fast?"
- Ask teammates: "What's the one resource that actually helped you understand this?"
- Pick 2-3 resources MAX. Stop researching.

**Step 3 — Priming (15 min)**
- Upload docs/videos to NotebookLM
- Generate a study guide with key concepts
- Do the quiz BEFORE reading (priming effect: +10-20% retention)
- Skim the architecture diagram/table of contents

**Step 4 — Comprehension (in chunks)**
- First pass: 2x speed, only write down definitions + major concepts + examples
- Never go deeper than 25 min without a break (Pomodoro)
- Convert format: text → audio if needed (Google AI Studio)
- Use ChatGPT Audio on commute for second pass

**Step 5 — Implementation**
- Build something tiny with the new knowledge immediately
- Even a 20-line script that uses the new API counts
- Implementing = 10x better retention than just reading

### Weekly Interleaved Learning (for Visa career growth)
```
INTERLEAVED SCHEDULE (don't study one thing per day — MIX IT):

Monday morning:   30 min — System Design / Architecture
Tuesday lunch:    20 min — Cloud/DevOps (AWS/GCP Visa stack)  
Wednesday morning: 30 min — Leadership/Career growth (staff+)
Thursday lunch:   20 min — Financial/domain knowledge (payments, compliance)
Friday morning:   30 min — New tech/AI integration patterns

Commute (any day): Audio mode — reinforce whatever you studied that day
```

---

## 🤖 Section 5: AI Model Quick Reference for Work

| Task | Best Tool | Why |
|------|-----------|-----|
| Code review / debugging | Claude Sonnet 4.5 via claude.ai | Best code understanding |
| Research + citations | Perplexity Sonar | Verified sources |
| Document learning | NotebookLM | Purpose-built for docs |
| Writing (emails, docs) | Claude Opus 4.5 | Best writing quality |
| Audio learning | ChatGPT Advanced Voice | Best conversational AI |
| Format conversion | Google AI Studio | Free, audio output |
| Quick questions | Gemini 2.5 Flash | Fast, free via AI Studio |
| Sensitive analysis | Local model on CT100 | Privacy - no data leak |

---

## 🔒 Section 6: Privacy at Work

**Never paste into a work AI tool:**
- Customer/cardholder data
- Internal auth tokens, API keys, passwords
- Non-public financial data
- Internal architecture details that are NDA-protected

**Safe to paste:**
- Public documentation
- Generic code patterns (no business logic with sensitive data)
- Your own rough notes and general concepts
- Public tech questions

**For sensitive analysis:**
- Use your homelab CT100 with an open-source model (Kimi K2 / Llama)
- Route through Tailscale from work if needed
- Keep all private data on your own hardware

---

## 🚀 Section 7: Getting Started (This Week)

### Day 1 (Monday)
- [ ] Bookmark: perplexity.ai, notebooklm.google.com, claude.ai, aistudio.google.com
- [ ] Set up ChatGPT mobile app with Advanced Voice Mode
- [ ] Pick ONE upcoming meeting and do the 15-min prep system
- [ ] Pick ONE tech topic you need to learn → start with Perplexity research

### Day 2 (Tuesday)  
- [ ] Take one work document and run it through NotebookLM → generate study guide
- [ ] Try the audio conversion: boring doc → Google AI Studio → podcast script → listen on commute
- [ ] Use Claude to write one PR description or email

### Week 1 Goal
- Establish the morning energy block (8-9am): no Slack, only deep work
- Use AI for one meeting prep, one learning session, one writing task
- Note what saves the most time → double down on that

### Week 2 Goal
- Set up the interleaved learning schedule above
- Build ONE hyper-specific work app (start with PR description generator — Bolt.new, 2 hours)

---

## 📱 Section 8: Mobile Setup

**On your phone (for commute learning):**

1. **ChatGPT** — Advanced Voice Mode for hands-free learning
2. **NotebookLM** — Audio overview of documents while walking/commuting
3. **Perplexity** — Quick research from your phone
4. **Notion or Apple Notes** — Quick capture of ideas before you forget them

**Commute learning protocol:**
- Morning commute: Listen to NotebookLM audio of what you'll be working on today
- Evening commute: ChatGPT Voice — talk through what you learned, solidify understanding
- This alone adds 30-60 min of effective learning time per day with zero extra time spent

---

## 🔗 Resources

| Resource | URL | Notes |
|----------|-----|-------|
| Perplexity AI | perplexity.ai | Best for research |
| NotebookLM | notebooklm.google.com | Best for documents |
| Claude.ai | claude.ai | Best for writing/code |
| Google AI Studio | aistudio.google.com | Free, audio output |
| ChatGPT | chatgpt.com | Voice mode learning |
| Bolt.new | bolt.new | Build hyper-specific apps |
| Gamma | gamma.app | Slide decks in minutes |
| Manus | manus.im | AI slide + doc creation |

**Your PSS App (personal, homelab):**
- Learning System: peachstatesavings.com → 🧠 Learning System
- AI Workflow Hub: peachstatesavings.com → ⚡ AI Workflow
- Access via Tailscale from work: 100.95.125.112:8501

---

*Send this file to Visa workstation. Save as WORKSTATION_AI_UPGRADE.md*  
*Do NOT share publicly — contains homelab IP/personal workflow details*
