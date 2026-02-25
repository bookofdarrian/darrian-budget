# Home Lab Progress Log
**Owner: Darrian Belcher | Updated: 2025-02-25**

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

**Current situation (2025-02-25):**
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

## Software Setup Status

| Service | Status | URL When Running |
|---------|--------|-----------------|
| Proxmox VE 8 | ⏳ Not started | https://192.168.1.50:8006 |
| AURA Compression Server | ⏳ Not started | http://192.168.1.51:8000/health |
| Portainer (Docker UI) | ⏳ Not started | http://192.168.1.51:9000 |
| Nginx Proxy Manager | ⏳ Not started | http://192.168.1.51:81 |
| TrueNAS Scale | ⏳ Waiting for drives | http://192.168.1.52 |
| Tailscale VPN | ⏳ Not started | Needed for Railway → home lab connection |

---

## Setup Steps (In Order)

- [ ] **Step 1** — Connect UPS battery (open compartment, plug in internal connector, charge 30 min)
- [ ] **Step 2** — Wire network: Router → Switch Port 1, Beelink → Switch Port 2
- [ ] **Step 3** — Download Proxmox VE 8 ISO: https://www.proxmox.com/en/downloads/proxmox-virtual-environment/iso
- [ ] **Step 4** — Flash Proxmox to USB on Mac:
  ```bash
  diskutil list
  diskutil unmountDisk /dev/diskX
  sudo dd if=~/Downloads/proxmox-ve_8.x-x.iso of=/dev/rdiskX bs=1m status=progress
  ```
- [ ] **Step 5** — Install Proxmox on Beelink (F7 at boot → select USB → NVMe target → IP: 192.168.1.50)
- [ ] **Step 6** — Access Proxmox web UI: https://192.168.1.50:8006 (root + your password)
- [ ] **Step 7** — Create Ubuntu 22.04 LXC container (2 cores, 512MB RAM, 8GB disk, DHCP)
- [ ] **Step 8** — Deploy AURA in container:
  ```bash
  apt update && apt install -y python3 git
  git clone https://github.com/bookofdarrian/darrian-budget.git
  cd darrian-budget && python3 aura/server.py &
  curl http://localhost:8000/health
  ```
- [ ] **Step 9** — Install Tailscale on Proxmox node:
  ```bash
  curl -fsSL https://tailscale.com/install.sh | sh && tailscale up
  ```
- [ ] **Step 10** — Set Railway env vars:
  ```
  AURA_BASE_URL=http://100.x.x.x:8000   # Tailscale IP
  AURA_ENABLED=true
  ```
- [ ] **Step 11** — Deploy Portainer (Docker UI)
- [ ] **Step 12** — Deploy Nginx Proxy Manager
- [ ] **Step 13** — (When drives arrive) Set up dual-bay enclosure → TrueNAS VM → RAID 1 mirror

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

## Key Context for Cline

- **Daily driver:** 2016 MacBook Pro (Intel, 2x Thunderbolt 3 USB-C ports)
- **Home lab server:** Beelink SER Mini PC (AMD Ryzen 7, 32GB RAM, 500GB NVMe)
- **Budget app:** Deployed on Railway at https://darrian-budget.up.railway.app
- **Goal:** Run AURA on home lab to cut Claude API costs, use Beelink as dev/test environment
- **Plugable dock:** USBC-7IN1 — 1 HDMI only, no ethernet — used for MacBook peripherals
- **3-monitor setup:** Dock HDMI → Monitor 1, MacBook USB-C port 2 → Monitor 2, MacBook screen → Monitor 3
