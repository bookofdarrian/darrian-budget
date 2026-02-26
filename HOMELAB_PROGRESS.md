# Home Lab Progress Log
**Owner: Darrian Belcher | Updated: 2026-02-25**

---

## Hardware Purchased ✅

| Item | Status | Notes |
|------|--------|-------|
| Beelink SER Series Mini PC | ✅ In hand | The home lab server — runs Proxmox + AURA |
| TP-Link 8-Port Gigabit Switch (TL-SG108) | ✅ In hand | Unmanaged, plug and play |
| Plugable USB-C 7-in-1 Hub (USBC-7IN1) | ✅ In hand | 1x HDMI, 3x USB-A, SD/microSD, USB-C passthrough — NO ethernet |
| UPS Battery Backup | ✅ In hand | Connect battery before first use (yellow STOP label) |
| 2x WD Red Plus 4TB NAS HDD (WD40EFPX) | 🛒 Buying today | Walmart ~$17.74 each — confirmed correct drives |
| Dual-bay 3.5" USB 3.0 enclosure | 🛒 Buying today | Best Buy — needed to connect bare SATA drives to Beelink |
| 2x USB flash drives 32GB+ | 🛒 Buying today | Proxmox boot installer |
| 2x Cat6 ethernet cables | 🛒 Buying today | Router→switch, switch→Beelink |

## Hardware Still Needed (Later)

| Item | Price | Notes |
|------|-------|-------|
| USB-C to HDMI cable | ~$12 | 2nd external monitor from MacBook's 2nd Thunderbolt port |
| Ubiquiti gear (optional Phase 3) | ~$1,100 | VLANs, IDS/IPS, WiFi 6 — skip for now |

---

## Network Plan

**Current situation (2026-02-25):**
- MacBook IP: `172.17.84.3` (on WiFi via home router, subnet `172.17.84.x`)
- Beelink IP: `100.117.1.42` (on ethernet via Gigstreem gateway, subnet `100.117.1.x`)
- ⚠️ They are on DIFFERENT subnets — cannot communicate directly yet
- Fix: Connect both devices to the SAME router/switch (see below)

**Target network layout:**
```
Home Router (172.17.84.1)
  └── TP-Link Switch Port 1
        ├── Port 2 → Beelink ethernet → gets 172.17.84.x IP
        ├── Port 3 → MacBook ethernet (optional)
        └── Port 4+ → future devices
```

**To fix the subnet mismatch:**
Move the Beelink's ethernet cable from the Gigstreem gateway to the TP-Link switch,
which is connected to your home router (172.17.84.x network).

---

## ✅ Current Live Services (All Running on CT100 @ 100.117.1.171)

| Service | Status | URL |
|---------|--------|-----|
| Proxmox VE 9.1.1 | ✅ Running | https://100.117.1.50:8006 |
| AURA Compression Server | ✅ **LIVE & HEALTHY** | http://100.117.1.171:8000/health |
| Budget App (Streamlit) | ✅ **LIVE & HEALTHY** | http://100.117.1.171:8501 |
| Vikunja (Todo App) | ✅ **LIVE** | http://100.117.1.171:3456 |
| Portainer (Docker UI) | ✅ **LIVE** | http://100.117.1.171:9000 |
| Nginx Proxy Manager | ✅ **LIVE** | http://100.117.1.171:81 |
| TrueNAS Scale | ⏳ Waiting for drives | — |
| **Tailscale VPN** | ⏳ **← NEXT STEP** | Needed for remote access |

> **Note (2026-02-25):** Llama/Ollama was never deployed to the homelab — confirmed by full audit of CT100 and Proxmox host. No llama containers or compose entries exist. Vikunja is the active to-do app.

**Docker host container:** CT100 at `100.117.1.171` (Ubuntu 22.04, 4 cores, 4GB RAM, 50GB disk)
**All services auto-restart** on reboot (`restart: unless-stopped`)

---

## 🚀 NEXT STEP: Install Tailscale (Phase 6)

> **Why this matters:** Right now your home lab is only accessible on your local network (`100.117.1.x`).
> Tailscale gives you a secure VPN tunnel so you can reach everything from your phone, work, or anywhere — no port forwarding needed.

### Step 1 — Install Tailscale on the Proxmox Host (Beelink)

SSH into your Proxmox host from your Mac:
```bash
ssh root@100.117.1.50
```

Then install Tailscale:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

You'll get a URL like:
```
To authenticate, visit:
  https://login.tailscale.com/a/xxxxxxxxxxxxxxxx
```

Open that URL in your browser, log in with Google/GitHub/email, and your Beelink joins your Tailscale network.

Get your Tailscale IP:
```bash
tailscale ip -4
# Returns something like: 100.64.x.x  ← save this!
```

### Step 2 — Install Tailscale on Your Mac

```bash
brew install tailscale
sudo tailscaled &
sudo tailscale up
```

Or download the GUI app: https://tailscale.com/download/mac
(Easier — installs as a menu bar app)

### Step 3 — Install Tailscale on Your iPhone

1. App Store → search "Tailscale" → Install
2. Open app → Sign in with same account as Step 1
3. Toggle VPN on

### Step 4 — Verify Remote Access

Once all devices are on Tailscale, replace `100.117.1.171` with your Beelink's **Tailscale IP** (`100.64.x.x`):

| Service | New Remote URL |
|---------|---------------|
| Budget App | `http://100.64.x.x:8501` |
| AURA | `http://100.64.x.x:8000/health` |
| Vikunja (Todo) | `http://100.64.x.x:3456` |
| Portainer | `http://100.64.x.x:9000` |
| Proxmox | `https://100.64.x.x:8006` |

Test from your phone (turn off WiFi, use cellular) — if it loads, you're done! 🎉

### Step 5 — (Optional) Update Railway to Use Home Lab AURA

Once Tailscale is working, you can point your Railway-hosted budget app at your home lab AURA server to save on Claude API costs:

In Railway dashboard → `darrian-budget` project → Variables:
```
AURA_BASE_URL=http://100.64.x.x:8000
AURA_ENABLED=true
```

> ⚠️ Only do this after confirming AURA is reachable via Tailscale IP from outside your home network.

---

## Master Setup Checklist (Do In Order)

### 🔌 Phase 1 — Hardware & Network
- [x] **Step 1** — Connect UPS battery
- [x] **Step 2** — Wire network: Router → Switch → Beelink
- [x] **Step 3** — Verify Beelink and MacBook are on same subnet

### 💿 Phase 2 — Install Proxmox
- [x] **Step 4** — Download Proxmox VE ISO
- [x] **Step 5** — Flash Proxmox to USB
- [x] **Step 6** — Install Proxmox on Beelink
- [x] **Step 7** — Access Proxmox web UI ✅ https://100.117.1.50:8006

### 🐳 Phase 3 — Docker Host Container
- [x] **Step 8** — Create Ubuntu 22.04 LXC container (CT100 @ 100.117.1.171)
- [x] **Step 9** — Install Docker inside the container
- [x] **Step 10** — Clone repo into container

### 🌐 Phase 4 — Deploy Your Websites
- [x] **Step 11** — Create `.env` with Railway env vars
- [x] **Step 12** — Create `docker-compose.yml`
- [x] **Step 13** — Create `Dockerfile` for budget app
- [x] **Step 14** — Launch all containers ✅ All running
- [x] **Step 15** — Test each service ✅ All healthy

### 🔀 Phase 5 — Nginx Proxy Manager
- [x] **Step 16** — Log into NPM ✅ http://100.117.1.171:81
- [x] **Step 17** — Change default NPM password
- [x] **Step 18** — Add proxy hosts
- [x] **Step 19** — Add `.local` domains to Mac's `/etc/hosts`

### 🔒 Phase 6 — Tailscale VPN (Remote Access) ← YOU ARE HERE
- [ ] **Step 20** — Install Tailscale on Proxmox host (Beelink)
- [ ] **Step 21** — Install Tailscale on Mac
- [ ] **Step 22** — Install Tailscale on iPhone
- [ ] **Step 23** — Verify remote access via Tailscale IP
- [ ] **Step 24** — (Optional) Update Railway env vars to use home lab AURA

### 💾 Phase 7 — TrueNAS Storage (When Drives Arrive)
- [ ] **Step 25** — Connect dual-bay enclosure with 2x WD Red 4TB drives
- [ ] **Step 26** — Create TrueNAS VM in Proxmox (pass through USB enclosure)
- [ ] **Step 27** — Set up RAID 1 mirror pool in TrueNAS
- [ ] **Step 28** — Create dataset for budget app backups
- [ ] **Step 29** — Configure nightly snapshots

### 🌍 Phase 8 — (Optional) Public Domain + SSL
- [ ] **Step 30** — Get a domain (free: duckdns.org, paid: Namecheap ~$10/yr)
- [ ] **Step 31** — Port forward 80 + 443 on your router to CT100
- [ ] **Step 32** — Add SSL cert in NPM (Let's Encrypt, free)
- [ ] **Step 33** — Access budget app at `https://budget.yourdomain.com` from anywhere

---

## AURA — Already Built in This Repo

| File | Purpose |
|------|---------|
| `aura/server.py` | AURA compression server (pure Python, zero deps) |
| `aura/Dockerfile` | Container definition |
| `aura/docker-compose.yml` | One-command startup |
| `utils/aura_client.py` | Client library wired into budget app |
| `pages/7_ai_insights.py` | Claude calls use AURA compression |

**Test AURA locally on Mac right now (no hardware needed):**
```bash
python aura/server.py
# In another terminal:
curl http://localhost:8000/health
```

---

## 📚 Guide Files (Read These)

| File | What It Covers |
|------|---------------|
| `HOMELAB_PROGRESS.md` | **This file** — master checklist and status |
| `HOMELAB_HOSTING_GUIDE.md` | Full site hosting walkthrough (phases 1-7) |
| `WEBSITE_HOSTING_SETUP.md` | ⭐ Step-by-step website deployment guide |
| `AURA_HARDWARE_GUIDE.md` | Hardware recommendations and AURA setup |
| `ICLOUD_STORAGE_GUIDE.md` | ⭐ How to expand iCloud storage + smart storage strategy |

---

## iCloud Storage — Quick Reference

> **Full guide:** See `ICLOUD_STORAGE_GUIDE.md`

| Plan | Storage | Price |
|------|---------|-------|
| Free | 5 GB | $0 |
| iCloud+ 50 GB | 50 GB | $0.99/mo |
| **iCloud+ 200 GB** | **200 GB** | **$2.99/mo ← Best value** |
| iCloud+ 2 TB | 2 TB | $9.99/mo |

**To upgrade right now:**
- iPhone: Settings → [Your Name] → iCloud → Manage Account Storage → Change Storage Plan
- Mac: Apple menu → System Settings → [Your Name] → iCloud → Manage → Change Storage Plan

**Smart strategy with your home lab:**
- iCloud 200 GB ($2.99/mo) for photos + iPhone backup
- Home lab NAS (4TB free) for everything else — saves you $7/mo vs. 2TB iCloud

---

## Key Context for Cline

- **Daily driver:** 2016 MacBook Pro (Intel, 2x Thunderbolt 3 USB-C ports)
- **Home lab server:** Beelink SER Mini PC (AMD Ryzen 7, 32GB RAM, 500GB NVMe)
- **Budget app (primary):** https://www.peachstatesavings.com (darrian-budget Railway project)
- **Budget app (mirror):** https://darrian-todo-production.up.railway.app (darrian-todo Railway project — todo app replaced with budget app 2026-02-25)
- **Goal:** Run AURA on home lab to cut Claude API costs, host budget app locally
- **Plugable dock:** USBC-7IN1 — 1 HDMI only, no ethernet — used for MacBook peripherals
- **3-monitor setup:** Dock HDMI → Monitor 1, MacBook USB-C port 2 → Monitor 2, MacBook screen → Monitor 3
- **Network:** Mac on 172.17.84.x (WiFi), Beelink on 100.117.1.x (different subnet — fix via TP-Link switch)

---

## Quick Reference — All URLs

### Live Now (Direct IP — Local Network Only)
| Service | URL |
|---------|-----|
| Proxmox Web UI | https://100.117.1.50:8006 |
| Budget App | http://100.117.1.171:8501 |
| AURA Health | http://100.117.1.171:8000/health |
| Vikunja (Todo) | http://100.117.1.171:3456 |
| Portainer | http://100.117.1.171:9000 |
| Nginx Proxy Manager | http://100.117.1.171:81 |
| TrueNAS | ⏳ Not yet (waiting for drives) |

### After Tailscale (Remote Access — From Anywhere) ← NEXT STEP
| Service | URL |
|---------|-----|
| Budget App | http://100.64.x.x:8501 |
| AURA | http://100.64.x.x:8000 |
| Vikunja (Todo) | http://100.64.x.x:3456 |
| Proxmox | https://100.64.x.x:8006 |
| Portainer | http://100.64.x.x:9000 |

### Railway (Public Internet — Always On)
| Service | URL |
|---------|-----|
| Budget App (primary) | https://www.peachstatesavings.com |
| Budget App (mirror) | https://darrian-todo-production.up.railway.app |
