# AURA Home Lab — Hardware Guide & Implementation Plan
**For: Darrian Belcher | Current machine: 2016 MacBook Pro 16"**

---

## What You're Building

A home lab server that runs:
- **AURA Compression Service** — cuts Claude API token costs 40-82%
- **Proxmox VE** — hypervisor to run multiple VMs/containers
- **TrueNAS Scale** — NAS for data storage and backups
- **Portainer** — Docker management UI
- **Nginx Proxy Manager** — reverse proxy with SSL for all services

Your MacBook Pro stays your daily driver. The home lab server runs 24/7 headless.

---

## ⚠️ Your MacBook Pro Limitation

The 2016 MacBook Pro 16" has:
- Intel Core i7/i9 (no Apple Silicon — good for x86 VMs)
- 16-32GB RAM (limited for running multiple VMs)
- No ECC RAM support
- Laptop thermals — not designed for 24/7 server load
- No hot-swap drive bays

**Bottom line:** Your Mac is great for development and testing AURA locally.
It is NOT suitable as a permanent home lab server. Get dedicated hardware.

---

## Hardware Recommendation: What to Buy

### 🥇 Best Pick for Your Use Case — Mini PC (Starter Lab)
**~$850 total | Best balance of cost, power, and size**

This is the **Option A** from the AURA docs, tuned for your specific needs:

| Component | Item | Price | Where to Buy |
|-----------|------|-------|--------------|
| **Mini PC** | Beelink SER5 MAX (Ryzen 7 5800H, 32GB RAM, 500GB NVMe) | ~$350 | Amazon / Beelink official |
| **NAS Drives** | 2x WD Red Plus 4TB (RAID 1 = 4TB usable) | ~$160 | Amazon / B&H |
| **USB Dock** | Plugable USB-C 7-in-1 (for extra SATA) | ~$50 | Amazon |
| **Network Switch** | TP-Link TL-SG108 8-port Gigabit | ~$25 | Amazon |
| **USB Drive** | 2x SanDisk 32GB USB 3.0 (Proxmox boot) | ~$20 | Amazon |
| **UPS** | APC BE600M1 (battery backup) | ~$70 | Amazon / Best Buy |
| **Ethernet Cable** | Cat6 10ft x2 | ~$15 | Amazon |

**Total: ~$690**

#### Why the Beelink SER5 MAX specifically:
- Ryzen 7 5800H = 8 cores / 16 threads — runs 4-6 VMs simultaneously
- 32GB DDR4 RAM included — enough for Proxmox + TrueNAS + AURA + budget app
- 2x NVMe slots — one for OS, one for fast VM storage
- 2x 2.5GbE ports — faster than standard gigabit
- 65W TDP — runs cool, ~$8/month in electricity
- Fits in your hand — no rack needed

---

### 🥈 If You Want More Power Later — Custom Build
**~$870 | From the AURA docs Option B**

| Component | Item | Price |
|-----------|------|-------|
| Motherboard | ASRock B450M Pro4 | $80 |
| CPU | AMD Ryzen 5 5600G | $150 |
| RAM | Corsair Vengeance 32GB DDR4-3200 | $120 |
| Boot SSD | Samsung 980 1TB NVMe | $80 |
| Data Drives | 2x Seagate IronWolf 4TB | $200 |
| Case | Fractal Node 202 (ITX) | $100 |
| PSU | Corsair SF450 80+ Gold | $90 |
| Cooler | Noctua NH-L9a-AM4 | $50 |

**Total: ~$870**

---

### 🌐 Network Upgrade (Optional, Phase 2)
Only needed if you want VLANs, IDS/IPS, or WiFi 6 mesh:

| Item | Price |
|------|-------|
| Ubiquiti Dream Machine Pro (firewall + router) | $400 |
| Ubiquiti Switch Pro 24 PoE | $400 |
| 2x Ubiquiti U6-Pro Access Points | $300 |

**Skip this for now.** Your existing router is fine to start.
Add it when you have 5+ devices on the lab network.

---

## What to Buy First (Priority Order)

### Phase 1 — Right Now (~$420)
1. **Beelink SER5 MAX** — $350 (the server itself)
2. **APC UPS BE600M1** — $70 (protect your data from power outages)

### Phase 2 — Within 30 Days (~$230)
3. **2x WD Red Plus 4TB** — $160 (NAS storage for backups)
4. **TP-Link 8-port switch** — $25 (connect server + Mac + NAS)
5. **2x SanDisk 32GB USB** — $20 (Proxmox boot drives, mirrored)
6. **Cat6 cables** — $15

---

## Software Stack (Free)

Everything below is free and open source:

| Software | Purpose | Runs On |
|----------|---------|---------|
| **Proxmox VE 8** | Hypervisor (runs VMs + containers) | Bare metal |
| **TrueNAS Scale** | NAS + ZFS storage | VM in Proxmox |
| **Docker + Portainer** | Container management | LXC in Proxmox |
| **AURA Server** | Compression service (this repo) | Docker container |
| **Nginx Proxy Manager** | Reverse proxy + SSL | Docker container |
| **Tailscale** | VPN — access lab from anywhere | All nodes |

---

## What You Can Do RIGHT NOW (No Hardware Needed)

### ✅ Already Done (this session):
1. `utils/aura_client.py` — AURA client library with graceful fallback
2. `aura/server.py` — Full AURA-compatible compression server (pure Python, no deps)
3. `aura/Dockerfile` — Container definition
4. `aura/docker-compose.yml` — One-command startup
5. `pages/7_ai_insights.py` — Wired AURA into Claude calls + savings display

### ✅ Run AURA locally on your Mac right now:
```bash
# No Docker needed — pure Python, zero dependencies
python aura/server.py

# In another terminal, test it:
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/compression/compress \
  -H "Content-Type: application/json" \
  -d '{"data": "Budget data for February 2026: Total Income: $5000.00, Total Projected Expenses: $4200.00", "mode": "auto"}'
```

### ✅ Install Docker Desktop (free, works on your Mac):
1. Go to: https://www.docker.com/products/docker-desktop/
2. Download "Docker Desktop for Mac" (Intel chip — your 2016 MBP is Intel)
3. Install and open it
4. Then run:
```bash
cd /Users/darrianbelcher/Downloads/darrian-budget/aura
docker-compose up -d
```

### ✅ Set environment variable to point budget app at AURA:
```bash
# Add to your .env file:
AURA_BASE_URL=http://localhost:8000
AURA_ENABLED=true
```

---

## Home Lab Setup Steps (When Hardware Arrives)

### Step 1: Install Proxmox VE
```bash
# On your Mac, download Proxmox VE ISO:
# https://www.proxmox.com/en/downloads

# Create bootable USB (replace /dev/diskX with your USB drive):
diskutil list                          # find your USB drive
diskutil unmountDisk /dev/diskX
sudo dd if=proxmox-ve_8.1-2.iso of=/dev/rdiskX bs=1m status=progress

# Boot the Beelink from USB, follow installer
# Set static IP: 192.168.1.50 (or whatever your router subnet is)
# Access web UI: https://192.168.1.50:8006
```

### Step 2: Create AURA Container in Proxmox
```bash
# In Proxmox web UI:
# Datacenter → Create CT (LXC Container)
# Template: ubuntu-22.04
# CPU: 2 cores
# RAM: 512MB
# Storage: 8GB
# Network: DHCP or static 192.168.1.51

# Inside the container:
apt update && apt install -y python3 git
git clone https://github.com/bookofdarrian/darrian-budget.git
cd darrian-budget
python3 aura/server.py &
```

### Step 3: Point Budget App at Home Lab
```bash
# In .env on CT100 (or any environment):
AURA_BASE_URL=http://100.95.125.112:8000   # home lab Tailscale IP
# OR with Tailscale VPN:
AURA_BASE_URL=http://100.x.x.x:8000     # Tailscale IP (works from anywhere)
```

### Step 4: Set Up TrueNAS for Backups
```bash
# In Proxmox: Create VM for TrueNAS Scale
# Pass through the 2x 4TB WD Red drives to TrueNAS
# Create RAID 1 mirror pool
# Set up dataset: main-pool/budget-backups
# Configure nightly snapshot + replication
```

---

## VLAN Plan (For When You Get the Ubiquiti Gear)

```
VLAN 10: Management  192.168.10.0/24  (Proxmox, switches, APs)
VLAN 20: Servers     192.168.20.0/24  (AURA, budget app, TrueNAS)
VLAN 30: IoT         192.168.30.0/24  (smart home devices)
VLAN 40: Guest       192.168.40.0/24  (guest WiFi, isolated)
VLAN 50: Lab/Test    192.168.50.0/24  (dev VMs, experiments)
```

---

## Cost Summary

| Phase | What | Cost |
|-------|------|------|
| Now (Mac) | Run AURA server.py locally | $0 |
| Now (Mac) | Install Docker Desktop | $0 |
| Phase 1 | Beelink SER5 MAX + UPS | ~$420 |
| Phase 2 | Drives + switch + cables | ~$230 |
| Phase 3 (optional) | Ubiquiti network gear | ~$1,100 |

**Minimum to get a real home lab running: ~$650**

---

## Expected AURA Savings on Your Budget App

Your budget context (expenses + transactions + investments) is typically
800-2,000 tokens per Claude call. With AURA:

| Scenario | Tokens Before | Tokens After | Monthly Savings* |
|----------|--------------|--------------|-----------------|
| Light use (10 calls/mo) | 1,000 | 400 | ~$0.02 |
| Medium use (100 calls/mo) | 1,000 | 400 | ~$0.18 |
| Heavy use (1,000 calls/mo) | 1,000 | 400 | ~$1.80 |
| Multi-user SaaS (10k calls/mo) | 1,000 | 400 | ~$18.00 |

*At claude-opus-4-5 pricing ($3/M input tokens), 60% compression

The real value isn't the dollar savings at personal scale — it's:
1. **Faster responses** (smaller payloads = less latency)
2. **Fitting more context** in the same token window
3. **Infrastructure practice** for when you scale to more users
4. **Learning** — you now understand the full stack from Mac → Docker → home lab → cloud

---

## Quick Reference: Key URLs When Lab Is Running

| Service | URL |
|---------|-----|
| Proxmox Web UI | https://192.168.1.50:8006 |
| AURA Health | http://192.168.1.51:8000/health |
| Portainer | http://192.168.1.51:9000 |
| TrueNAS | http://192.168.1.52 |
| Nginx Proxy Manager | http://192.168.1.51:81 |
