# AI Efficiency Master Guide — Darrian Belcher
**Created: 2026-03-16 | Owner: Darrian Belcher**
**Stack: Claude, Whisper, Remotion, v0, Coolors, Claude Skills, MCP**

> This guide evaluates every AI tool and tip you've encountered, rates them
> for YOUR specific use cases (Peach State Savings, SoleOps, College Confused,
> content creation), and gives you a concrete action plan to implement the best ones.

---

## 🏆 TL;DR — What to Actually Do (Priority Order)

| # | Action | Impact | Time to Implement |
|---|--------|--------|------------------|
| 1 | Set up **Whisper + Claude Voice Workflow** (Wispr Flow) | 🔥🔥🔥 | 30 min |
| 2 | Build **Claude Skills** for your 5 core tasks | 🔥🔥🔥 | 2–3 hrs |
| 3 | Use **Claude Desktop + MCP** as your command center | 🔥🔥🔥 | 1 hr |
| 4 | **Remotion** for College Confused + SoleOps content | 🔥🔥 | 4–6 hrs |
| 5 | Redesign all 3 sites with **v0 + Coolors palettes** below | 🔥🔥 | 3–4 hrs |
| 6 | Evaluate **Obsidian** — verdict: stick with Peach State Notes | 🔥 | 15 min read |

---

## 1. 🎙️ WHISPER + CLAUDE VOICE WORKFLOW — DO THIS FIRST

### What It Is
OpenAI Whisper is a speech-to-text model. Wired into the right tools, you can
**talk instead of type** — and get Claude-quality responses via voice.

### The 2026 Recommended Setup (Tested, Real)

**Option A — Wispr Flow (Best for Mac, $9/mo)**
- Runs as a Mac background app
- Press a hotkey → speak → it transcribes anywhere (VS Code, browser, Slack, email)
- Natively pipes to Claude, GPT-4, or whatever
- Works in EVERY app — not just a dedicated interface
- **This is what the viral TikToks are showing**

**Option B — Claude Code /voice command (Free, already in your terminal)**
- Claude Code now has a built-in `/voice` command
- In your Cline terminal: type `/voice` → speak your next instruction
- No extra app, uses Whisper under the hood
- **Best for development sessions — talk your Cline instructions**

**Option C — Build it yourself in your homelab (Best for privacy, free)**
```python
# Install in your venv:
# pip install openai-whisper pyaudio

import whisper, pyaudio, wave, anthropic, os

model = whisper.load_model("base")  # runs locally, no API cost

def record_audio(seconds=10, filename="input.wav"):
    """Record from mic for N seconds, save to WAV."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1,
                    rate=16000, input=True, frames_per_buffer=1024)
    frames = [stream.read(1024) for _ in range(0, int(16000/1024 * seconds))]
    stream.stop_stream(); stream.close(); p.terminate()
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1); wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000); wf.writeframes(b''.join(frames)); wf.close()

def voice_to_claude(seconds=10):
    """Record voice → transcribe → send to Claude → speak response."""
    record_audio(seconds)
    result = model.transcribe("input.wav")
    text = result["text"].strip()
    print(f"You said: {text}")
    
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": text}]
    )
    response = msg.content[0].text
    print(f"Claude: {response}")
    # Optional: pipe to macOS TTS
    os.system(f'say "{response[:200]}"')
    return response

if __name__ == "__main__":
    voice_to_claude(seconds=15)
```

### Your Specific Use Cases for Voice

| Use Case | How to Use It |
|----------|--------------|
| **Drafting work emails (Visa)** | Speak the context → Wispr Flow → Claude drafts professional email → paste into Gmail |
| **SoleOps ideas while driving** | "Add to backlog: Add Depop platform to arbitrage scanner" → auto-appends to BACKLOG.md via voice |
| **College Confused content ideas** | Voice-capture essay prompts, scholarship tips → Claude expands into full CC page content |
| **Cline sessions** | Use `/voice` in terminal instead of typing long feature requests |
| **Telegram budget bot** | You already have this — voice note in Telegram → Whisper transcribes → logs expense |

### Verdict: ⭐⭐⭐⭐⭐ — IMPLEMENT IMMEDIATELY
**Wispr Flow ($9/mo) + Claude Code /voice = the fastest way to 2x your AI output speed.**
Start with Wispr Flow for daily work, build the local version on CT100 for privacy-sensitive tasks.

---

## 2. 🤖 CLAUDE DESKTOP vs. TERMINAL vs. CLINE — THE REAL ANSWER

### What Your Coworker Said
> "Only use Claude Desktop or directly through the terminal — it's faster."

### My Verdict: They're All Right. Here's Why

#### Claude Desktop (claude.ai app)
- **Best for:** Conversations, brainstorming, writing, quick questions
- **Why it's fast:** No browser overhead, direct app = snappier
- **Secret power: MCP Connectors** — Claude Desktop can connect directly to:
  - Your Google Drive (read/write files)
  - Your GitHub repo (review code)
  - Your Postgres DB (answer questions about your data)
  - Your file system (read files you point it to)
- **Verdict for you:** Use for strategy sessions, email drafts, content ideas, market research

#### Terminal / Claude Code (your current Cline setup)
- **Best for:** Writing code, building features, file editing
- **Why it's fast:** No UI layer, direct file access, can run commands
- **Your setup is already optimal:** Cline + Claude Opus = the gold standard
- **Verdict for you:** Keep using exactly as you are for dev work

#### Claude.ai in browser
- **Best for:** Nothing specific — it's the worst of both worlds
- **Slower than Desktop app, less powerful than Cline**
- **Verdict for you:** Replace with Desktop app immediately

### The Optimal Stack for YOU

```
┌─────────────────────────────────────────────────────────┐
│  TASK TYPE           │  TOOL                            │
├─────────────────────────────────────────────────────────┤
│  Writing code        │  Cline (terminal/VS Code)        │
│  Feature planning    │  Claude Desktop + BACKLOG.md     │
│  Email drafting      │  Wispr Flow → Claude Desktop     │
│  Quick questions     │  Claude Desktop                  │
│  DB queries          │  Claude Desktop + MCP (Postgres) │
│  Content creation    │  Claude Desktop + Skills (below) │
│  Overnight work      │  Your autonomous agent system    │
│  Research            │  Claude Desktop + Perplexity     │
└─────────────────────────────────────────────────────────┘
```

### Setting Up Claude Desktop MCP for Your Homelab

Install Claude Desktop → Settings → MCP Servers → Add these:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "/Users/darrianbelcher/Downloads/darrian-budget"]
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres",
               "postgresql://localhost/darrian_budget"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN" }
    },
    "google-drive": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gdrive"]
    }
  }
}
```

**What this gives you:**
- Ask Claude Desktop: "What did I spend on food last month?" → it queries Postgres directly
- Ask: "What's in my BACKLOG.md?" → it reads the file
- Ask: "Create a content brief for my next College Confused video" → saves to Google Drive
- Ask: "What PRs are open on my repo?" → reads GitHub

### MCP Financial Data Server (Already in Your BACKLOG — Page 81)
This is the ultimate endgame: your entire Peach State Savings DB is exposed as
an MCP resource. Then from any Claude conversation: "Am I on track for $500k by 35?"

---

## 3. 📋 CLAUDE SKILLS — YOUR BIGGEST MULTIPLIER

### What Claude Skills Are
Skills are **saved, reusable Claude workflows** that you can trigger with a single click.
Think of them like saved prompts on steroids — they carry full context, tools, and
multi-step instructions. Live in Claude Desktop.

**Created: Nov 2025 | Platform: claude.ai + Claude Desktop**

### The 5 Skills You Need Right Now

---

#### Skill 1: Content Creation — College Confused
```
Name: 📚 CC Content Creator
Icon: 🎓

System prompt:
You are the content brain for College Confused, a nonprofit college prep platform 
founded by Darrian Belcher (25 acceptances, 7 full rides, $500K+ in scholarships).

AUDIENCE: First-gen students, ages 15-22, parents of color, school counselors.
TONE: Big brother/mentor. Real. No corporate speak. No jargon. Plain English.
ALWAYS: Use specific examples. Cite real scholarships/deadlines when possible.
NEVER: Use condescending language. Never paywall advice. Never be vague.

When I give you a topic, produce:
1. A TikTok script (60 sec, hook in first 3 words, CTA at end)
2. An Instagram carousel (7 slides: hook → 5 value points → CTA)  
3. A YouTube outline (intro hook, 5-7 main points, outro CTA)
4. A CC app page feature idea related to this topic

Use Darrian's personal story angles when relevant: first-gen, HBCU research, 
scholarship hunting, essay writing, FAFSA struggles.
```

**Trigger:** Type the topic (e.g., "FAFSA deadline stress") → get 4 pieces of content

---

#### Skill 2: SoleOps Market Research Bot
```
Name: 👟 SoleOps Intel
Icon: 👟

System prompt:
You are Darrian's sneaker resale intelligence assistant for SoleOps / 404 Sole Archive.

CONTEXT: Darrian resells sneakers on eBay and Mercari. He uses the SoleOps 
platform (his own Streamlit app at peachstatesavings.com) for inventory tracking,
P&L, arbitrage scanning, and AI listing generation.

When I give you a shoe or resale business question, provide:
1. Current market sentiment (is this shoe hot/cold right now?)
2. Optimal platform (eBay vs Mercari vs StockX vs Depop — and why)
3. Pricing strategy (BIN vs auction, optimal price point)
4. Listing title suggestion (eBay 80-char keyword-optimized)
5. Risk assessment (counterfeit prevalence, return risk, demand volatility)
6. Sourcing angle (where to find at under market — Mercari, FCFS drops, etc.)

Always think about: sell-through rate, fee structure, buyer demographics per platform.
Current fee reference: eBay ~12.9%, Mercari ~10%, StockX ~9.5%.
```

**Trigger:** "Jordan 4 Military Black size 10 — bought at $180" → full market Intel

---

#### Skill 3: Business Entrepreneur Bot
```
Name: 🚀 Business Strategist
Icon: 💼

System prompt:
You are Darrian Belcher's personal business strategist and entrepreneur coach.

DARRIAN'S CONTEXT:
- TPM at Visa (Fortune 500) — project/program management background
- GT Data Analytics (in progress) — data-driven thinking
- SoleOps — sneaker resale SaaS ($500 MRR target, 90 days)
- College Confused — nonprofit college prep (content + app)
- Peach State Savings — personal finance app (peachstatesavings.com)
- Located: Atlanta metro area (moving soon)
- Homelab: CT100 Proxmox, self-hosted AI stack

When I bring you a business idea, provide:
1. Market size estimate (TAM/SAM/SOM — quick, not academic)
2. Competitive landscape (who's doing this, what's their weakness)
3. Unfair advantage Darrian has (TPM skills, tech stack, personal story)
4. Revenue model options (ranked by realistic path to $1k/mo)
5. 30-day MVP plan (what to build in this repo to test the idea)
6. Risks/blockers (be honest, not hype)

Reference existing assets: Stripe paywall, Streamlit app, Postgres DB,
Claude API, homelab compute, existing user base.
```

---

#### Skill 4: Health Bot (Homelab Integrated)
```
Name: 🏥 Health Coach
Icon: 💪

System prompt:
You are Darrian's personal health and wellness AI, integrated with his 
homelab health data from Peach State Savings (pages/66_health_wellness_hub.py).

DARRIAN'S HEALTH CONTEXT:
- Tracks: mood logs, workouts, medications, doctor visits, vaccines
- Goal: tie health habits to performance at work and in business
- Apple Health CSV data importable via Health Hub page
- Health data stored in SQLite/Postgres on homelab

When I share health data or ask a health question:
1. Pattern recognition — what trends are you seeing in the data?
2. Correlation insight — "Your mood is 3x higher on gym days"
3. Optimization recommendation — specific, actionable, not generic
4. Risk flag — anything in the data that needs a doctor (say so clearly)
5. Homelab integration idea — what data could we auto-track via smart home?

IMPORTANT: You are a wellness coach, not a doctor. Always recommend 
professional medical consultation for anything clinical.

Data format Darrian uses: 
- Mood: 1-10 scale logged daily
- Workouts: type, duration, intensity
- Sleep: hours (from Apple Health)
- Weight, water intake, supplements
```

---

#### Skill 5: Daily Productivity Briefing
```
Name: ☀️ Morning Briefing
Icon: ☀️

System prompt:
You are Darrian's daily AI chief of staff. When I paste my daily context, 
generate a prioritized morning briefing.

INPUT FORMAT (paste each morning):
- Today's meetings/obligations
- Pending items from yesterday
- Current BACKLOG priority
- Energy level (1-10)
- Anything on my mind

OUTPUT FORMAT:
## 🎯 Top 3 Priorities for Today
[ranked by impact, not urgency]

## ⚡ Quick Wins (< 15 min each)
[3-5 items that move needles fast]

## 🧠 When You Have Focus Time
[the one deep work item worth protecting time for]

## 🚫 Don't Touch Today
[what to intentionally defer]

## 💡 One Strategic Insight
[one thing to think about that's bigger than today's tasks]
```

---

### How to Create a Skill in Claude Desktop
1. Open Claude Desktop → click your name/avatar → **Skills**
2. Click **+ New Skill**
3. Paste the system prompt above
4. Save with the name and icon
5. Access via the **@** mention in any conversation or from the sidebar

---

## 4. 🎬 REMOTION — VIDEO EDITING FOR CONTENT CREATION

### What Remotion Is
Remotion lets you **write React/JavaScript code that renders to real MP4 video**.
Instead of drag-and-drop editors, you write components. Claude writes the code.

### The 2026 Reality
- **Claude Code + Remotion** is now a legit production stack (see Medium article above)
- Claude can write a full Remotion composition from a text description
- Renders to real .mp4, .gif, or .webm files
- Animations, transitions, text overlays, data visualizations, charts in video

### Your Use Cases

#### Use Case A: College Confused TikTok/Reels Templates
```bash
# Install Remotion
npx create-video@latest college-confused-templates
cd college-confused-templates
npm install
```

**Ask Claude to generate:**
```
Write a Remotion composition for a 60-second TikTok-style video with:
- Purple background (#6C63FF — College Confused brand color)
- Bold white text animating in word-by-word
- 7 slides: hook → 5 tips → CTA
- Fade transitions between slides
- Bottom progress bar showing slide number
- Export at 1080x1920 (vertical/TikTok)
Input: an array of slide texts I'll pass as a prop
```

**Result:** One Remotion template → Claude fills in new content → renders 100 videos

#### Use Case B: SoleOps Price Alert Videos
```
Write a Remotion composition for a 15-second "buy signal" alert video:
- Dark sneaker-themed background
- Show shoe name, size, buy price, sell price, profit in bold
- Animated profit number counting up
- Export as 1080x1080 (square for IG)
```

#### Use Case C: Peach State Savings Monthly Report Video
```
Write a Remotion composition that takes my monthly financial summary
(income, expenses, savings rate, net worth delta) and generates a 
30-second animated financial recap:
- Show numbers counting up
- Green/red trend arrows
- Export as 1920x1080 (landscape for YouTube)
```

### Remotion vs. Traditional Editing for YOU

| Factor | Remotion | CapCut/Premiere |
|--------|----------|----------------|
| Time per video | ~5 min (once template exists) | 30-60 min |
| Consistency | Perfect every time | Varies |
| Data-driven content | ✅ (pass data as props) | ❌ |
| Learning curve | High initially | Low |
| Batch generation | ✅ 100 videos from one template | ❌ |
| B-roll footage | ❌ needs external footage | ✅ |

**Verdict: ⭐⭐⭐⭐ — HIGH VALUE for YOUR use case**
Your content is information-dense (financial tips, sneaker data, college stats) —
not lifestyle/vlog. Remotion is PERFECT for data-driven content like yours.
It's NOT great for talking-head videos with B-roll. Use Remotion for graphics/
text-based content, your phone camera for talking head.

### Installation
```bash
# Requires Node.js (you have npm)
npm init video@latest
# Pick: Hello World template → customize from there
# Render: npx remotion render

# Install Claude helper for Remotion
npx @remotion/ai-helper  # generates compositions from natural language
```

---

## 5. 🎨 WEB DESIGN REDESIGN — ALL THREE SITES

### Tools: Coolors + v0 by Vercel

#### Coolors (coolors.co)
- **What it is:** Color palette generator — paste a hex code, get a harmonious 5-color palette
- **Free tier:** Yes, fully functional
- **How to use:** Go to coolors.co → generate → lock your brand color → keep generating

#### v0 by Vercel (v0.dev)
- **What it is:** Type a UI description → get production-ready React/Tailwind code instantly
- **2026 update:** Now generates full pages, not just components
- **Free tier:** 200 credits/month (generous for your use)
- **Best use:** Describe the page you want → copy the JSX → use as inspiration for Streamlit CSS

**Note on "Varient"** — you may have heard of "Vercel v0" (the tool is called v0, made by Vercel).
There's also a tool called "Variant" for design systems — but v0 is the dominant AI design tool.
I'll cover v0 as the primary recommendation.

---

### Site 1: Peach State Savings (peachstatesavings.com)

#### Current: Default Streamlit + your inject_css
#### Recommended Palette (via Coolors)

```python
# Add to utils/auth.py inject_css() — replace current CSS variables

PEACH_STATE_COLORS = {
    "primary":     "#FF6B35",  # Warm Peach-Orange (brand anchor)
    "secondary":   "#004E89",  # Deep Navy Blue (trust/finance)
    "accent":      "#1A936F",  # Emerald Green (money/growth)
    "warning":     "#F18F01",  # Amber (alerts)
    "bg_dark":     "#0D1117",  # Near-black background
    "bg_card":     "#161B22",  # Card background
    "text_primary":"#E6EDF3",  # Off-white text
    "text_muted":  "#8B949E",  # Muted text
}
```

**CSS Theme Block for inject_css():**
```python
def inject_css():
    st.markdown("""
    <style>
    /* ── Peach State Savings 2.0 Theme ── */
    :root {
        --primary:    #FF6B35;
        --secondary:  #004E89;
        --accent:     #1A936F;
        --warning:    #F18F01;
        --bg:         #0D1117;
        --bg-card:    #161B22;
        --text:       #E6EDF3;
        --text-muted: #8B949E;
        --border:     #30363D;
        --radius:     12px;
        --shadow:     0 4px 24px rgba(0,0,0,0.4);
    }

    /* Dark background */
    .stApp { background-color: var(--bg); color: var(--text); }
    
    /* Cards */
    .stMetric, [data-testid="metric-container"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1rem 1.25rem;
        box-shadow: var(--shadow);
    }
    
    /* Primary button */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary), #FF8C5A);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(255,107,53,0.4);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0D1117;
        border-right: 1px solid var(--border);
    }
    
    /* Input fields */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text);
    }
    .stTextInput input:focus { border-color: var(--primary); }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        color: var(--text-muted);
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom-color: var(--primary) !important;
    }
    
    /* Headers */
    h1 { color: var(--primary); font-weight: 700; }
    h2 { color: var(--text); font-weight: 600; }
    h3 { color: var(--text-muted); font-weight: 500; }
    
    /* Success/Error/Warning */
    .stSuccess { background: rgba(26,147,111,0.15); border: 1px solid var(--accent); }
    .stError   { background: rgba(255,69,58,0.15);  border: 1px solid #FF453A; }
    .stWarning { background: rgba(241,143,1,0.15);  border: 1px solid var(--warning); }
    </style>
    """, unsafe_allow_html=True)
```

**v0 Prompt for Peach State Savings landing page design:**
```
Design a dark-themed personal finance dashboard landing page.
Colors: #FF6B35 (primary), #004E89 (secondary), #0D1117 (background), #1A936F (accent).
Style: Bloomberg Terminal meets Apple — clean, data-dense, professional.
Include: hero section with "Your AI-Powered Wealth OS", 4 feature cards,
a mock financial chart, and a login CTA button.
Mobile responsive. Tailwind CSS.
```
→ Go to v0.dev → paste this → use the output as design inspiration / extract the card layout

---

### Site 2: SoleOps (soleops.app / your subdomain)

#### Brand Identity
SoleOps is a **B2B SaaS for sneaker resellers** — it should feel like a pro tool,
not a personal finance app. Think Shopify meets StockX analytics.

#### Recommended Palette

```python
SOLEOPS_COLORS = {
    "primary":   "#00D4FF",  # Electric Cyan (sneaker/tech energy)
    "secondary": "#7B2FBE",  # Deep Purple (premium/exclusive)
    "accent":    "#FF3CAC",  # Hot Pink/Magenta (trending/alert)
    "success":   "#00FF87",  # Neon Green (profit/gain)
    "danger":    "#FF4757",  # Red (loss/alert)
    "bg":        "#0A0A0F",  # Near-black
    "bg_card":   "#12121A",  # Dark card
    "border":    "#1E1E2E",  # Subtle border
}
```

**CSS Theme Block:**
```python
# Add a SOLEOPS_CSS constant and apply via st.markdown for SoleOps pages (65-73, 84-86)
SOLEOPS_CSS = """
<style>
.stApp { background: #0A0A0F; }
h1 { 
    background: linear-gradient(90deg, #00D4FF, #7B2FBE);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
/* Profit metric = green glow */
.profit-positive { color: #00FF87; text-shadow: 0 0 8px rgba(0,255,135,0.4); }
/* Loss metric = red */
.profit-negative { color: #FF4757; }
/* Cards with cyan border */
.sole-card {
    background: #12121A;
    border: 1px solid #00D4FF33;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 0 20px rgba(0,212,255,0.05);
}
</style>
"""
```

**v0 Prompt for SoleOps:**
```
Design a dark SaaS dashboard for sneaker resellers called "SoleOps".
Colors: #00D4FF (primary), #7B2FBE (secondary), #0A0A0F (background), #00FF87 (profit green).
Style: Vercel/Linear dark — premium, fast, data-dense.
Include: inventory count cards, a P&L chart, a "Buy Signals" alert feed,
and a sidebar navigation. Neon accents on hover. Professional.
```

---

### Site 3: College Confused (collegeconfused.org)

#### Brand Identity
CC is a **nonprofit for first-gen students**. It should feel warm, approachable,
energetic, and trustworthy — like a cool older sibling who went to college.
NOT corporate. NOT intimidating. NOT clinical.

#### Recommended Palette

```python
CC_COLORS = {
    "primary":    "#6C63FF",  # Current purple — KEEP THIS (strong brand)
    "secondary":  "#FF6584",  # Warm Pink-Coral (energy/youth)
    "accent":     "#43E97B",  # Fresh Green (success/acceptance)
    "highlight":  "#FFC300",  # Gold/Yellow (scholarships/achievement)
    "bg":         "#FAFAFA",  # Light mode (accessibility for all devices)
    "bg_card":    "#FFFFFF",  # White cards
    "text":       "#1A1A2E",  # Deep navy text
    "text_muted": "#6B7280",  # Gray muted
}
```

**CSS Theme Block:**
```python
CC_CSS = """
<style>
/* College Confused — Warm Light Theme */
.stApp { background: #FAFAFA; }

/* Hero gradient */
.cc-hero {
    background: linear-gradient(135deg, #6C63FF 0%, #FF6584 100%);
    color: white;
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
}

/* Card */
.cc-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 16px rgba(108,99,255,0.08);
    border: 1px solid #F0EEFF;
    transition: transform 0.2s ease;
}
.cc-card:hover { transform: translateY(-2px); }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6C63FF, #7B78FF);
    color: white;
    border: none;
    border-radius: 25px;  /* pill shape — friendly */
    font-weight: 600;
}

/* Achievement badge */
.cc-badge {
    background: #FFC300;
    color: #1A1A2E;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-weight: 700;
    font-size: 0.85rem;
}

/* Scholarship highlight */
.scholarship-amount {
    color: #43E97B;
    font-size: 1.5rem;
    font-weight: 800;
}
</style>
"""
```

**v0 Prompt for College Confused:**
```
Design a warm, approachable web app for first-generation college students
called "College Confused". Colors: #6C63FF (primary purple), #FF6584 (coral),
#43E97B (success green), white background.
Style: Friendly, modern, NOT corporate — like Duolingo meets Notion.
Include: a welcome hero section with "Get into college. Get paid for it.",
scholarship counter widget, timeline progress bar, essay helper card,
and a "Start Here" CTA. Mobile-first. Accessible.
```

---

## 6. 🧩 OBSIDIAN vs. PEACH STATE SAVINGS NOTES — THE VERDICT

### What Obsidian Is
A local markdown note-taking app with a **knowledge graph** — it connects notes
via [[wikilinks]] and shows you a visual web of how ideas connect.

### The Honest Comparison for You

| Feature | Obsidian | Your PSS Notes Page (page 25) |
|---------|----------|-------------------------------|
| Knowledge graph | ✅ Beautiful | ❌ Not built |
| AI integration | ✅ (with plugins) | ✅ Claude built-in |
| Mobile app | ✅ (paid sync) | ✅ (your web app) |
| Financial data link | ❌ | ✅ Connected to your DB |
| Customization | ✅ Infinite | ✅ You control the code |
| Cost | Free (sync = $8/mo) | $0 (your infrastructure) |
| Privacy | ✅ Local files | ✅ Your homelab |
| Works offline | ✅ Always | ❌ Needs connection |
| Version history | ✅ Git-based | ✅ (built in PSS) |
| Quick capture | ✅ Excellent | ⚠️ Web form friction |

### Verdict: **Use Obsidian for Personal Knowledge, PSS for App-Tied Notes**

**Use Obsidian for:**
- Personal journal / daily notes
- Learning notes (GT coursework, books, podcasts)
- Idea capture + connections (the graph is genuinely useful)
- Drafting content ideas (links CC ideas → SoleOps ideas → budget ideas)
- Anything you want to keep forever, offline, private

**Use PSS Notes (page 25) for:**
- Notes that reference financial data ("this month's budget insight")
- SoleOps strategy notes (linked to inventory)
- Team/app-related context
- Pinned AI summaries from your agents

**The hybrid setup:**
```
Obsidian (local vault on Mac) 
    ↓ sync via iCloud Drive (free, already have it per ICLOUD_STORAGE_GUIDE.md)
    ↓ Obsidian mobile (free, uses iCloud sync)

PSS Notes (page 25) 
    → for app-context notes
    → agent-generated summaries land here (Monthly Expense Audit agent)
```

**Bottom line:** Obsidian does not replace PSS Notes — they're for different jobs.
Obsidian is your personal brain. PSS Notes is your business/financial brain.
Both are worth having. You don't have to choose.

---

## 7. 🤖 AGENTS & SKILLS FOR YOUR SPECIFIC TASKS

### Agent Architecture for YOUR Work

Based on your existing agent system + your content needs, here are the specific
agents you should build. These live in `.claude/agents/` for Claude Code, or
as Claude Skills in Claude Desktop, or as Python scripts on CT100.

---

### Agent 1: College Confused Content Pipeline

**What it does:** Given a topic, generates the full content package automatically.

**Implementation: Claude Code Sub-Agent**
```markdown
# .claude/agents/cc-content-creator.md

You are the College Confused content production agent.

When triggered with a topic, you MUST:
1. Write a 60-second TikTok script (hook in first 3 words)
2. Write an Instagram carousel (7 slides, clear text, no jargon)
3. Write a YouTube video outline (5-7 points, 8-12 min runtime)
4. Identify the matching CC app page to link in the CTA
5. Suggest 3 hashtag clusters for each platform
6. Write the caption for each platform

Context:
- Darrian's story: 25 college acceptances, 7 full rides, $500K+ scholarships
- Audience: first-gen students, 15-22, parents, counselors
- Tone: older sibling mentor. Real. Direct. No jargon.
- CTA always links to: collegeconfused.org or the specific CC app page

Output format: Markdown with clearly labeled sections for each deliverable.
```

**Run with:**
```bash
# Create a script for this in your repo
cat > run_cc_content.sh << 'EOF'
#!/bin/bash
TOPIC="$1"
claude --agent cc-content-creator "Generate full content package for topic: $TOPIC"
EOF
chmod +x run_cc_content.sh
./run_cc_content.sh "FAFSA deadline tips"
```

---

### Agent 2: TikTok/IG/YouTube Idea Bank Populator

**What it does:** Monitors trending topics in your niches and adds content ideas
to your Creator Companion (page 24) automatically.

**Implementation: Scheduled Python Script on CT100**
```python
# /opt/agents/content_idea_bot.py
# Runs daily at 7am via cron

import anthropic, psycopg2, os
from datetime import datetime

NICHES = [
    "college admissions 2026",
    "sneaker reselling market",
    "first generation college students",
    "personal finance for young adults",
    "Atlanta entrepreneur"
]

def generate_content_ideas(niche: str, client: anthropic.Anthropic) -> list[dict]:
    prompt = f"""
    Generate 3 viral content ideas for the niche: "{niche}"
    
    For each idea, provide:
    - hook: the first 3 words that stop the scroll
    - angle: the unique angle that makes this different
    - platform: TikTok / IG / YouTube (best fit)
    - content_type: talking head / text overlay / tutorial / storytime
    - estimated_engagement: why this will perform
    
    Format as JSON array.
    Today's date: {datetime.now().strftime("%B %d, %Y")}
    """
    
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    import json, re
    text = msg.content[0].text
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return []

def save_ideas(ideas: list, niche: str, conn):
    cur = conn.cursor()
    for idea in ideas:
        cur.execute("""
            INSERT INTO creator_ideas (niche, hook, angle, platform, content_type, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (niche, idea.get('hook'), idea.get('angle'), 
              idea.get('platform'), idea.get('content_type')))
    conn.commit()

if __name__ == "__main__":
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    
    for niche in NICHES:
        ideas = generate_content_ideas(niche, client)
        save_ideas(ideas, niche, conn)
        print(f"✅ Generated {len(ideas)} ideas for: {niche}")
    
    conn.close()
```

**Cron:** `0 7 * * * /opt/agents/content_idea_bot.py`

---

### Agent 3: SoleOps Market Intelligence Bot

**What it does:** Daily morning brief on sneaker market conditions, delivered to Telegram.

**Implementation: Add to your existing `run_scheduled_agents.py`**
```python
def run_soleops_morning_intel():
    """Generates daily sneaker market brief → Telegram."""
    from sole_alert_bot.ebay_search import ebay_search_sold
    
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    
    # Get your inventory
    cur = conn.cursor()
    cur.execute(f"SELECT item, size, buy_price FROM sole_archive WHERE status = {ph}", ("inventory",))
    inventory = cur.fetchall()
    conn.close()
    
    if not inventory:
        return
    
    inventory_summary = "\n".join([f"- {item} Sz {size} (cost ${cost})" 
                                    for item, size, cost in inventory[:10]])
    
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return
    
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""
        You are a sneaker resale market analyst. Based on this inventory:
        {inventory_summary}
        
        Generate a 5-sentence morning brief covering:
        1. Which pair should be listed/relisted TODAY (highest market momentum)
        2. Any pairs to hold (market dipping)
        3. One sourcing opportunity to watch for this week
        
        Be specific. Be brief. Numbers > adjectives.
        """}]
    )
    
    brief = msg.content[0].text
    send_telegram_alert(f"👟 SoleOps Morning Intel\n\n{brief}")
```

---

### Agent 4: Business Market Research Bot

**What it does:** When you're evaluating a new business idea, this agent does
the competitive research for you in 60 seconds.

**Claude Skill (add to Claude Desktop):**
```
Name: 🔍 Market Research Bot
Trigger: Give me a business idea or market to research

System Prompt:
You are Darrian's rapid market research analyst. Your job is to evaluate
business ideas quickly and honestly — no hype, no fluff.

When given a business idea, immediately produce:

## Market Overview
- TAM (Total Addressable Market): $X
- Key players: [top 3 with their weakness]
- Market trend: Growing/Flat/Declining + why

## Darrian's Edge
- What skills from Visa (TPM, Fortune 500 experience) apply
- What tech assets he already has (list from his stack)
- What personal story creates credibility here

## Revenue Path
- Fastest path to $1,000/mo: [specific steps]
- Fastest path to $10,000/mo: [specific steps]
- Revenue model ranked: [#1 best, #2 fallback, #3 stretch]

## 30-Day MVP
- What to build in his existing Streamlit app to test this
- What page number it would be (he's at page 88 currently)
- Key metric to prove/disprove the idea in 30 days

## Honest Risk Assessment
- Top 3 reasons this fails
- What would need to be true for this to succeed

Be specific. Be honest. Reference Darrian's existing stack when relevant.
```

---

### Agent 5: Health Bot Integrated with Homelab

**What it does:** Reads data from your Health Hub (page 66), correlates with
smart home data (sleep quality via Home Assistant), generates weekly insight.

**Implementation: Scheduled Agent**
```python
def run_weekly_health_insights():
    """Weekly health data analysis → saves to PSS Notes as pinned memo."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    
    # Get last 7 days of health data
    cur.execute(f"""
        SELECT log_date, mood_score, energy_level, workout_done, sleep_hours, notes
        FROM health_logs 
        WHERE log_date >= DATE('now', '-7 days')
        ORDER BY log_date
    """)
    health_data = cur.fetchall()
    
    if not health_data:
        conn.close()
        return
    
    data_str = "\n".join([
        f"{row[0]}: mood={row[1]}/10, energy={row[2]}/10, "
        f"workout={'yes' if row[3] else 'no'}, sleep={row[4]}hrs"
        for row in health_data
    ])
    
    api_key = get_setting("anthropic_api_key")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": f"""
        Analyze this week's health data for Darrian:
        {data_str}
        
        Provide:
        1. Key pattern (one sentence — what's the most important thing the data shows)
        2. Correlation insight (what correlates with high/low mood and energy?)
        3. One specific recommendation for next week
        4. One smart home automation that could improve the data (e.g., "Set a 10pm phone 
           lock through Home Assistant to improve sleep hours")
        
        Format as a brief memo, 150 words max.
        """}]
    )
    
    # Save as pinned note in PSS Notes
    cur.execute(f"""
        INSERT INTO notes (title, content, category, is_pinned, created_at)
        VALUES ({ph},{ph},{ph},{ph}, CURRENT_TIMESTAMP)
    """, ("Weekly Health Insight", msg.content[0].text, "health", True))
    
    conn.commit()
    conn.close()
```

---

## 8. 📱 COMPLETE TOOL STACK RECOMMENDATION

### Tier 1 — Implement This Week (High leverage, low cost)

| Tool | Use | Cost | Setup Time |
|------|-----|------|-----------|
| **Wispr Flow** | Voice → Claude anywhere | $9/mo | 30 min |
| **Claude Desktop** | Command center + MCP | Free (API cost) | 1 hr |
| **Claude Skills** (5 above) | Reusable task templates | Free | 2-3 hrs |
| **Coolors.co** | Color palette generation | Free | 15 min |
| **v0.dev** | UI design inspiration | Free (200/mo) | As needed |

### Tier 2 — Implement This Month

| Tool | Use | Cost | Setup Time |
|------|-----|------|-----------|
| **Remotion** | Video content at scale | Free + render | 4-6 hrs |
| **NotebookLM** | Deep learning from docs | Free | 30 min |
| **Obsidian** | Personal knowledge base | Free | 1 hr |
| **Perplexity AI** | Quick research | Free/$20/mo | Immediate |
| **n8n (self-hosted)** | Workflow automation | Free (homelab) | 3-4 hrs |

### Tier 3 — Future (When Ready)

| Tool | Use | Cost | Notes |
|------|-----|------|-------|
| **MCP Financial Server** (page 81) | Your DB in Claude | Dev time | Already in BACKLOG |
| **Local Whisper on CT100** | Private voice processing | Free | Homelab compute |
| **Fine-tuned model** | PSS/SoleOps-specific AI | $100-500 | After 1,000+ entries |

---

## 9. 🧠 PROMPT ENGINEERING — ADVANCED TIPS FOR YOUR WORKFLOW

### The Most Important Patterns You Probably Aren't Using

#### 1. System Prompt Priming (for every Claude Desktop conversation)
Start every conversation with context about YOU:
```
I'm Darrian Belcher — TPM at Visa, building SoleOps (sneaker resale SaaS),
College Confused (college prep nonprofit), and Peach State Savings (finance app).
Tech stack: Python, Streamlit, PostgreSQL, Claude API, self-hosted homelab.
Goal today: [specific goal]
```

#### 2. Chain-of-Draft Prompting (faster than Chain-of-Thought)
Instead of asking Claude to think step by step, ask for rough drafts first:
```
Give me 3 rough draft approaches to [problem] — not polished, just the core idea.
Then I'll pick one and you refine it.
```

#### 3. Constraint-First Prompting (get better code faster)
Put constraints BEFORE the request:
```
Constraints: Python only, use existing get_conn() from utils/db.py, 
under 100 lines, must pass syntax check.
Task: Build a function that...
```

#### 4. Persona-Switch for Different Content Modes
```
Switch to [CC mentor persona] — warm, first-gen focused, 8th-grade reading level
Switch to [SoleOps analyst persona] — data-driven, sneaker market expert
Switch to [PSS CFO persona] — financial analyst, tax-aware, conservative
```

#### 5. The "One More Iteration" Rule
After Claude gives an output, ALWAYS say:
```
"Good. Now make it 20% shorter and 40% more specific."
```
This single prompt improves almost every Claude output by 30-50%.

---

## 10. 🗺️ IMPLEMENTATION ROADMAP

### This Week (Days 1-7)
- [ ] Install Wispr Flow ($9/mo) — download from wisprflow.ai
- [ ] Download Claude Desktop app (claude.ai/download)
- [ ] Configure MCP servers (filesystem + Postgres) per Section 2
- [ ] Create 5 Claude Skills per Section 3
- [ ] Apply Peach State Savings CSS theme to `utils/auth.py`

### This Month (Days 8-30)
- [ ] Install Obsidian + set up iCloud sync vault
- [ ] Install Remotion (`npm init video@latest`)
- [ ] Build first Remotion CC TikTok template
- [ ] Apply SoleOps CSS theme to SoleOps pages (65-73)
- [ ] Apply College Confused CSS theme to CC pages (80-88)
- [ ] Add Content Idea Bot to CT100 cron (Section 7)
- [ ] Add Weekly Health Insights agent to `run_scheduled_agents.py`

### Next 90 Days
- [ ] Build MCP Financial Data Server (page 81 — already in BACKLOG)
- [ ] Build SoleOps Morning Intel Agent
- [ ] Build Remotion templates for all 3 platforms
- [ ] Voice-integrate Telegram bot (Whisper on CT100)
- [ ] Build full v0-designed College Confused standalone site

---

## 11. 🔑 THE BIG INSIGHT

You already have the best possible foundation:
- ✅ Your own AI agent system running overnight
- ✅ A Claude API setup with Cline (the best coding workflow available)
- ✅ A homelab with always-on compute
- ✅ Three distinct products (PSS, SoleOps, CC) that can be cross-promoted
- ✅ A day job at Visa giving you Fortune 500 credibility

**The gap is not tools. The gap is reusable workflows.**

The TikTok tips you've seen are mostly showing you individual tools, but the real
unlock is **chaining them together**:

```
Voice idea (Wispr Flow) 
  → Claude Skill expands it 
    → Remotion renders the video 
      → Auto-published via n8n 
        → Performance data back to Creator Companion (page 24)
          → Claude analyzes what worked 
            → New ideas generated overnight
```

That loop — when fully built — means you can produce College Confused content
**at scale without grinding**. The same loop works for SoleOps market research
and Peach State Savings insights.

Build the loop. The tools are just pieces of it.

---

*Guide generated by Cline (Claude Opus) | 2026-03-16*
*Tailored to Darrian Belcher's specific stack and projects*
*Update this file as tools evolve — the AI landscape shifts every 90 days*
