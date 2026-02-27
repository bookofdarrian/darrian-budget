# Homelab Use Cases — Darrian's Personalized Roadmap
**Owner: Darrian Belcher | Created: 2026-02-25**

> Based on your actual setup: Beelink SER Mini PC, Proxmox VE, CT100 Docker host,
> Tailscale VPN, AURA compression server, budget app at peachstatesavings.com,
> 404 Sole Archive resale business, RSU/ESPP income, and WD Red drives incoming.

---

## Your Current Stack (What You Already Have Running)

```
Beelink (Proxmox) → CT100 (Docker)
  ├── Budget App (Streamlit)     → peachstatesavings.com
  ├── AURA Compression Server    → cuts Claude API costs
  ├── Portainer                  → Docker management UI
  ├── Nginx Proxy Manager        → reverse proxy
  ├── code-server (VS Code)      → browser-based IDE
  └── Tailscale VPN              → remote access from anywhere
```

You have a **real, production-grade homelab** already. The question is what to
build on top of it. Here's what makes the most sense for YOU specifically.

---

## 🥇 Tier 1 — Do These First (High Impact, Low Effort)

These directly extend what you already have and solve real problems you face today.

---

### 1. 🗄️ TrueNAS + Automated Budget App Backups
**Why it's #1 for you:** Your drives are arriving TODAY. This is the next logical step
and protects the financial data you've been building for months.

**What you get:**
- RAID 1 mirror — one drive can die, zero data loss
- Nightly snapshots of your Postgres database
- 30-day history — roll back to any day if you accidentally delete data
- A real NAS you can dump files to from your Mac

**How to set it up:**
```
Proxmox → Create TrueNAS VM → pass through USB enclosure
TrueNAS → Create mirror pool "tank" → dataset "budget-backups"
Set up nightly pg_dump → rsync to TrueNAS
```

**Effort:** Medium (2-3 hours) | **Value:** Critical — you have real financial data to protect

---

### 2. 🤖 Ollama — Run AI Models Locally (Free Claude Alternative)
**Why it's #2 for you:** You're already paying for Claude API calls. Your Beelink has
a Ryzen 7 with 32GB RAM — that's enough to run Llama 3.1 8B or Mistral 7B locally.
Zero API cost. Runs 24/7 on your homelab.

**⚠️ Honest caveat — what "wiring it into the budget app" actually means:**

Right now `pages/7_ai_insights.py` calls Claude via the Anthropic SDK directly.
The `ask_claude()` function is hardcoded to `claude-opus-4-5`. There is no Ollama
fallback built in yet — that would require you to add a second code path that calls
`http://100.95.125.112:11434/api/generate` instead of Anthropic's API.

**What Ollama actually gives you:**
- A free, local LLM you can query from your terminal, browser, or any app
- A replacement for Claude on NEW tools you build (not automatic in the budget app)
- A private AI that never sends your financial data to Anthropic's servers
- A learning sandbox — experiment with prompts, models, and AI features at zero cost

**What it does NOT do automatically:**
- It does NOT replace Claude in your existing budget app without code changes
- It will NOT be as smart as Claude for financial analysis (Llama 8B vs Claude Opus)
- It does NOT save you money on existing Claude calls unless you rewrite `ask_claude()`

**Realistic use cases for you right now:**
- Run it as a local chatbot for quick questions (no API key, no cost)
- Use it to prototype new budget app features before paying for Claude API calls
- Ask it about 404 Sole Archive pricing, sneaker market trends, etc.
- Build a separate simple chat UI (Open WebUI) that talks to Ollama — like a free ChatGPT

**How to set it up:**
```bash
# In CT100:
docker run -d --name ollama \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  --restart unless-stopped \
  ollama/ollama

# Pull a model (8B fits in your 32GB RAM easily):
docker exec ollama ollama pull llama3.1:8b

# Test it from your Mac (Tailscale connected):
curl http://100.95.125.112:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "What is a good budget for groceries?", "stream": false}'
```

**Add a chat UI (Open WebUI — looks like ChatGPT):**
```yaml
# Add to docker-compose.yml:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports: ["3002:8080"]
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on: [ollama]
    restart: unless-stopped
```
Access at `http://100.95.125.112:3002` — full ChatGPT-like UI, free, private.

**Effort:** Low (30 min) | **Value:** Medium — free AI sandbox, not a drop-in Claude replacement

---

### 3. 📊 Grafana + Prometheus — Monitor Everything
**Why it's #3 for you:** You're a data person. You track expenses, income, RSUs,
investments. You should also be tracking your homelab's health the same way.

**What you get:**
- Real-time dashboards: CPU, RAM, disk, network on your Beelink
- Alerts when a container goes down (email/phone notification)
- Track budget app uptime — know before users do if it's down
- Looks impressive and teaches you observability (valuable skill)

**How to set it up:**
```yaml
# Add to your docker-compose.yml:
  prometheus:
    image: prom/prometheus
    ports: ["9090:9090"]
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter
    ports: ["9100:9100"]
    restart: unless-stopped
```

Access Grafana at `http://100.95.125.112:3000` → import dashboard ID `1860`
(Node Exporter Full) → instant beautiful server metrics.

**Effort:** Low (1 hour) | **Value:** High — visibility into your lab + real skill

---

### 4. 🔐 Vaultwarden — Self-Hosted Password Manager
**Why it's #4 for you:** You have financial accounts, Railway, Proxmox, Tailscale,
Postgres, Stripe — that's a lot of passwords. Vaultwarden is a self-hosted
Bitwarden-compatible server. Your passwords stay on YOUR hardware.

**What you get:**
- Full Bitwarden app on Mac + iPhone (free)
- Passwords stored on your homelab, not someone else's cloud
- Works with Tailscale — accessible from anywhere
- Browser extension autofills everything

**How to set it up:**
```yaml
# Add to docker-compose.yml:
  vaultwarden:
    image: vaultwarden/server:latest
    ports: ["8888:80"]
    volumes:
      - vaultwarden-data:/data
    restart: unless-stopped
```

Access at `http://100.95.125.112:8888` → create account → install Bitwarden
app on Mac + iPhone → point it at your server URL.

**Effort:** Low (45 min) | **Value:** High — security + privacy

---

## 🥈 Tier 2 — Do These Next (Medium Effort, High Payoff)

---

### 5. 📦 Automated Postgres Backups to TrueNAS
**Why:** Your budget app uses Postgres on Railway. If Railway has an outage or you
exceed the free tier, you lose data. A nightly backup to your local NAS is insurance.

**What you get:**
- Nightly `pg_dump` of your Railway Postgres database
- Stored on your RAID 1 NAS (survives a drive failure)
- 30-day retention — restore any day's data
- Completely automated — set it and forget it

**How to set it up:**
```bash
# Create a backup script on CT100:
cat > /opt/backup-postgres.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y-%m-%d)
pg_dump $DATABASE_URL > /mnt/truenas/budget-backups/budget-$DATE.sql
find /mnt/truenas/budget-backups -name "*.sql" -mtime +30 -delete
EOF

# Add to crontab (runs at 2 AM daily):
echo "0 2 * * * /opt/backup-postgres.sh" | crontab -
```

**Effort:** Low (1 hour after TrueNAS is set up) | **Value:** Critical

---

### 6. 🏠 Home Assistant — Smart Home Automation Hub
**Why it's relevant to you:** You're already running a homelab. Home Assistant is the
most popular self-hosted smart home platform. It runs perfectly as a VM in Proxmox.

**What you get:**
- Control smart plugs, lights, thermostats from one dashboard
- Automate things: "turn off all lights when I leave home"
- Track electricity usage — feed it into your budget app
- Works with Alexa, Google Home, Apple HomeKit
- 100% local — no cloud subscription fees

**How to set it up:**
```
Proxmox → Create VM → Upload Home Assistant OS image
VM: 2 cores, 4GB RAM, 32GB disk
Access at http://[VM-IP]:8123
```

**Effort:** Medium (2 hours) | **Value:** High if you have any smart home devices

---

### 7. 📸 Immich — Self-Hosted Google Photos with Built-In AI
**Why it's relevant to you:** You're already planning iCloud 200GB ($2.99/mo).
With 4TB of NAS storage incoming, you could host your own photo library instead —
and get AI features that are actually better than iCloud's.

**What Immich's AI does natively (no extra setup):**
- **Face recognition** — automatically groups photos by person, you name them once
- **Object/scene detection** — search "sneakers", "Jordan 1", "receipt", "car" and it finds matching photos
- **CLIP semantic search** — type "red shoes on white background" and it finds photos that match the *concept*, not just the filename
- **Smart albums** — auto-albums by location, date, people, or detected objects
- **Duplicate detection** — finds and flags duplicate photos automatically

**How the AI actually works under the hood:**
Immich ships with two built-in AI microservices:
- `immich-machine-learning` — runs CLIP (image embeddings) + facial recognition models locally
- All inference runs on YOUR hardware — no photos sent to any cloud AI service
- On your Ryzen 7 (CPU inference), expect ~1-3 seconds per photo during initial indexing
- After initial index, search is instant

**What this means for you specifically:**
- Search your entire photo library by typing "404 Sole Archive" or "sneaker" — finds every shoe photo
- Search "receipt" — instantly pulls every receipt photo (useful for HSA reimbursements)
- Search "Jordan 1 Chicago" — CLIP understands the concept, not just the filename
- Face-tag yourself, family, friends — auto-organizes every photo by person

**Storage math with your 4TB NAS:**
| Content | Size per item | 4TB capacity |
|---------|--------------|--------------|
| iPhone photos (12MP) | ~4MB | ~1,000,000 photos |
| iPhone 4K video (1 min) | ~350MB | ~11,000 minutes |
| RAW photos | ~25MB | ~160,000 photos |

**How to set it up (full stack):**
```yaml
# docker-compose.yml — full Immich stack:
  immich-server:
    image: ghcr.io/immich-app/immich-server:release
    ports: ["2283:2283"]
    volumes:
      - /mnt/truenas/photos:/usr/src/app/upload
    environment:
      - DB_HOSTNAME=immich-postgres
      - REDIS_HOSTNAME=immich-redis
    depends_on: [immich-postgres, immich-redis]
    restart: unless-stopped

  immich-machine-learning:
    image: ghcr.io/immich-app/immich-machine-learning:release
    volumes:
      - immich-model-cache:/cache
    restart: unless-stopped

  immich-redis:
    image: redis:6.2-alpine
    restart: unless-stopped

  immich-postgres:
    image: tensorchord/pgvecto-rs:pg14-v0.2.0
    environment:
      POSTGRES_PASSWORD: immich
      POSTGRES_USER: immich
      POSTGRES_DB: immich
    volumes:
      - immich-pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  immich-model-cache:
  immich-pgdata:
```

Access at `http://100.95.125.112:2283` → install **Immich** iPhone app → Settings →
point server URL at `http://100.95.125.112:2283` → enable auto-backup.

**First-time AI indexing:** After uploading photos, go to Administration → Jobs →
run "Smart Search" and "Face Detection" — it processes every photo once, then stays
current automatically as new photos come in.

**Effort:** Medium (2-3 hours) | **Value:** Very High — replaces iCloud+, Google Photos, AND gives you private AI search over your entire photo library

---

### 8. 💹 404 Sole Archive — Dedicated Inventory Database
**Why it's specific to you:** Your resale business is tracked in the budget app but
deserves its own dedicated service. You could run a proper inventory management
system on your homelab.

**What you get:**
- Dedicated database for shoe inventory (cost basis, purchase date, condition)
- Track profit per pair, per platform (StockX, GOAT, eBay)
- Price alerts — scrape StockX/GOAT prices and alert when a pair hits your target
- Tax reporting — auto-generate Schedule C data at year end
- Separate from your personal budget — cleaner accounting

**How to build it:**
```
Option A: Add a dedicated "inventory" schema to your existing Postgres
Option B: Run a separate Baserow (self-hosted Airtable) container
Option C: Build a new Streamlit page (you already know how)
```

**Effort:** Medium (3-4 hours) | **Value:** High — you have a real business to track

---

## 🥉 Tier 3 — When You're Ready to Level Up

---

### 9. 🌐 Public Domain + Real SSL (peachstatesavings.com → Homelab)
**Why:** Right now Railway hosts your public site. Once you're confident in your
homelab's uptime, you can cut Railway costs entirely and host at home.

**What you get:**
- No Railway hosting fees
- Full control over your stack
- Real SSL cert (Let's Encrypt, free) via NPM
- Custom domain pointing to your homelab via Cloudflare Tunnel (no port forwarding)

**How to set it up:**
```
Cloudflare → Add domain → Create Tunnel → point to CT100:8501
NPM → Add SSL cert → Force HTTPS
Railway → Remove budget app (keep Postgres for now or migrate to local)
```

**Effort:** Medium (2-3 hours) | **Value:** Saves Railway costs, full ownership

---

### 10. 🧪 Dev/Staging Environment — Test Before You Break Prod
**Why it's relevant to you:** You've been making changes directly to the Railway
production app. One bad deploy = peachstatesavings.com is down.

**What you get:**
- A staging CT (CT101) that mirrors production
- Test new budget app features locally before pushing to Railway
- Break things safely — prod is untouched
- Git workflow: `main` → Railway (prod), `dev` → homelab (staging)

**How to set it up:**
```
Proxmox → Clone CT100 → CT101 (staging)
CT101 runs budget app on port 8502
Test at http://100.95.125.112:8502 before pushing to Railway
```

**Effort:** Low (1 hour) | **Value:** High — protects your production app

---

### 11. 📡 Uptime Kuma — Public Status Page
**Why:** If you ever share peachstatesavings.com with others (or just want peace of
mind), Uptime Kuma gives you a beautiful status page and sends alerts when anything
goes down.

**What you get:**
- Monitor all your services (budget app, AURA, Railway, etc.)
- Phone/email alerts when something goes down
- Public status page: `status.yourdomain.com`
- Tracks response time history

**How to set it up:**
```yaml
  uptime-kuma:
    image: louislam/uptime-kuma:1
    ports: ["3001:3001"]
    volumes:
      - uptime-kuma:/app/data
    restart: unless-stopped
```

**Effort:** Very Low (20 min) | **Value:** Medium — peace of mind

---

### 12. 🔬 Proxmox Cluster + Second Node (Future)
**Why:** Once you're comfortable with one Proxmox node, adding a second (even a
cheap $150 mini PC) gives you live migration — move VMs between nodes with zero
downtime. This is enterprise-grade infrastructure at home.

**What you get:**
- High availability — if Beelink reboots, VMs migrate to node 2
- Learn clustering (valuable DevOps skill)
- More compute for running more services

**Effort:** High | **Value:** High for learning, overkill for personal use right now

---

## 📋 Recommended Order of Operations

```
TODAY (drives arrive):
  1. ✅ Finish Tailscale on iPhone
  2. 🔜 Set up TrueNAS (Phase 7 from HOMELAB_HOSTING_GUIDE.md)
  3. 🔜 Set up automated Postgres backups to TrueNAS

THIS WEEK:
  4. Deploy Ollama (free AI — 30 min)
  5. Deploy Grafana + Prometheus (monitoring — 1 hour)
  6. Deploy Vaultwarden (passwords — 45 min)

THIS MONTH:
  7. Deploy Immich (photos — replaces iCloud+)
  8. Build 404 Sole Archive dedicated tracker
  9. Set up staging environment (CT101)

WHEN READY:
  10. Migrate off Railway → host at home with Cloudflare Tunnel
  11. Add Uptime Kuma status page
  12. (Eventually) Second Proxmox node
```

---

## 💰 Cost/Savings Summary

| Use Case | Monthly Cost | Monthly Savings |
|----------|-------------|-----------------|
| Ollama (local AI) | $0 | ~$5-20 in Claude API costs |
| Immich (vs iCloud 200GB) | $0 | $2.99/mo |
| Vaultwarden (vs 1Password) | $0 | $3-5/mo |
| Self-hosted vs Railway | $0 | $5-20/mo (when ready) |
| TrueNAS backups | $0 | Priceless (data protection) |
| **Total potential savings** | | **~$16-48/month** |

Your homelab hardware is already paid for. Every service you self-host is pure savings.

---

## 🎯 The Big Picture — What This Builds Toward

You're not just saving money. You're building:

1. **A real DevOps portfolio** — Proxmox, Docker, Nginx, Tailscale, TrueNAS, Grafana
   are all enterprise tools. You're learning them at home for free.

2. **Infrastructure for peachstatesavings.com** — If you ever add paying users
   (Stripe is already wired in), you have the backend to support it.

3. **A platform for 404 Sole Archive** — Dedicated inventory DB, price scrapers,
   tax reporting. Your resale business deserves real infrastructure.

4. **Financial data sovereignty** — Your budget, transactions, and net worth data
   live on hardware you own, not someone else's cloud.
