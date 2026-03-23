# 🍑 Peach State Savings — Personal Finance OS

> *"The Marathon Continues."* — Nipsey Hussle

**Live at → [peachstatesavings.com](https://peachstatesavings.com)**

A full-stack, self-hosted personal finance and life operating system built entirely from scratch by **Darrian Belcher** — Software Engineer at Visa, HBCU grad, reseller, creator, and community builder.

---

## 🔢 By the Numbers

| Metric | Count |
|--------|-------|
| 📄 Pages / Features | 154+ |
| 💾 Lines of Code | 92,000+ |
| 🔀 Git Commits | 688+ |
| 🌿 Branches | 274+ |
| 🧪 Unit Tests | 100+ |
| 🚀 Uptime | Self-hosted home lab |

---

## 🏗️ What This Is

This isn't a budget app. It's a **personal operating system** that covers:

### 💰 Finance
- Budget tracking, expense categories, savings rate optimizer
- RSU/ESPP vest tracker, portfolio dashboard
- Paycheck calculator, debt payoff planner, retirement optimizer
- Tax projections, HSA receipt categorizer, investment rebalancer
- Net worth tracking, dividend income, crypto portfolio

### 👟 SoleOps — Sneaker Resale Empire
- Full inventory management (buy/sell/hold)
- Cross-platform listing manager (eBay, StockX, GOAT, Mercari)
- AI listing generator, price predictor, market trend analyzer
- Profit margin optimizer, sales velocity tracker
- Competitor price tracker, drop calendar, arbitrage scanner

### 🤖 AI-Powered
- Personal AI assistant (Claude Opus)
- Proactive AI engine — runs overnight, surfaces insights
- AI notes with summarization, expansion, task extraction
- AI career intelligence, morning briefing agent
- Creative studio — manga, film, script development (private)

### 🎬 Creator Tools
- Content planning across all channels (bookofdarrian, College Confused, SoleOps)
- Social media manager, video AI studio
- Media library with Spotify integration

### 🏠 Homelab & Security
- Self-hosted on Proxmox CT100 @ home lab
- Docker, Nginx reverse proxy, PostgreSQL
- Tailscale VPN, Grafana/Prometheus monitoring
- GitHub Actions CI/CD pipeline (all 5 environments)

---

## 🛠️ Tech Stack

```
Backend:    Python 3.11 · Streamlit · PostgreSQL (prod) · SQLite (local)
AI:         Anthropic Claude Opus (claude-opus-4-5)
Auth:       Custom bcrypt auth with session management
Payments:   Stripe (Pro tier — $4.99/mo)
Infra:      Proxmox · Docker · Nginx · Tailscale
CI/CD:      GitHub Actions (feature → dev → qa → staging → main)
Voice:      OpenAI Whisper (local, on-device, ⌥M hotkey)
```

---

## 🔱 Subscription Tiers

| Tier | Price | Description |
|------|-------|-------------|
| 🐾 Panther Papers | Free | Core financial tools, Ubuntu community spirit |
| ⭐ Pro | $4.99/mo | All features, AI tools, SoleOps platform |
| 🔱 Sovereign | Invite-only (25+) | Hand-picked by Darrian. Earned, not bought. |

---

## 🚀 Quick Start (Development)

```bash
# Clone and enter
git clone https://github.com/bookofdarrian/darrian-budget.git
cd darrian-budget

# Virtual environment
python -m venv venv
source venv/bin/activate     # Mac/Linux
# venv\Scripts\activate      # Windows

# Install
pip install -r requirements.txt

# Run
streamlit run app.py
# Opens at http://localhost:8501
```

---

## 🗂️ Project Structure

```
darrian-budget/
├── app.py                       # Main overview dashboard
├── pages/                       # 154+ feature pages
│   ├── 00_landing.py            # Public landing page
│   ├── 0_pricing.py             # Three-tier pricing
│   ├── 10-13_*.py               # Finance: RSU, portfolio, market, backtesting
│   ├── 100-102_*.py             # Family, donations, tax projection
│   ├── 103-141_soleops_*.py     # Full SoleOps resale platform
│   ├── 143_video_ai_studio.py   # Video & AI image studio
│   ├── 147_proactive_ai_engine.py
│   └── 148_creative_studio.py  # 🎬 The Marathon Studio (private)
├── utils/
│   ├── auth.py                  # Auth, sessions, tier checks
│   ├── db.py                    # DB helpers (SQLite/PostgreSQL)
│   └── voice_input.py           # Whisper voice input widget
├── whisper_daemon.py            # System-wide ⌥M dictation daemon
├── tests/unit/                  # 100+ unit tests
├── .github/workflows/           # CI/CD (lint, test, deploy per env)
├── monitoring/                  # Prometheus + Grafana stack
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 🧪 Testing

```bash
source venv/bin/activate
pytest tests/ -v

# Syntax check all pages
find pages/ utils/ -name "*.py" | xargs python3 -m py_compile && echo "✅ All OK"
```

---

## 🌍 SDLC Pipeline

Every change goes through the full pipeline — no exceptions:

```
feature/* → dev → qa → staging → main (prod)
```

- GitHub Actions runs tests + syntax checks at every stage
- Tests must PASS before deploy runs
- Production deploy includes health check with automatic rollback

---

## 👤 About the Builder

**Darrian Belcher** — Software Engineer at Visa Inc., HBCU alumnus, sneaker reseller, content creator, and community builder.

- 🏛️ NC A&T State University (HBCU)
- 💳 Full-time SWE at Visa
- 👟 404 Sole Archive — sneaker resale business
- 🎬 bookofdarrian · College Confused · SoleOps (YouTube/content)
- 🌍 Virginia · North Carolina · The Peach State
- 💜 Gullah Geechee heritage
- 🔱 Building tools to get people out of poverty and keep wealth in community

---

## 📬 Connect

| Platform | Link |
|----------|------|
| 🌐 Site | [peachstatesavings.com](https://peachstatesavings.com) |
| 💼 LinkedIn | [linkedin.com/in/darrianbelcher](https://linkedin.com/in/darrianbelcher) |
| 🐙 GitHub | [github.com/bookofdarrian](https://github.com/bookofdarrian) |
| 🐦 X/Twitter | [@bookofdarrian](https://twitter.com/bookofdarrian) |
| 📸 Instagram | [@bookofdarrian](https://instagram.com/bookofdarrian) |

---

*Built with purpose. Deployed with discipline. The Marathon Continues. 💜*
