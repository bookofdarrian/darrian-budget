# Home Lab Site Hosting Guide
**For: Darrian Belcher | Updated: 2026-02-25**

---

## Current Status — What's Already Done ✅

All phases 1–5 are **complete**. Everything is running on CT100 at `100.117.1.171`.

| Service | Status | URL |
|---------|--------|-----|
| Proxmox VE 9.1.1 | ✅ Running | https://100.117.1.50:8006 |
| AURA Compression Server | ✅ Live | http://100.117.1.171:8000/health |
| Budget App (Streamlit) | ✅ Live | http://100.117.1.171:8501 |
| Vikunja (Todo App) | ✅ Live | http://100.117.1.171:3456 |
| Portainer (Docker UI) | ✅ Live | http://100.117.1.171:9000 |
| Nginx Proxy Manager | ✅ Live | http://100.117.1.171:81 |
| **Tailscale VPN** | ⏳ **← DO THIS NEXT** | Remote access from anywhere |

> **The only thing missing:** Tailscale. Without it, your home lab is only reachable on your local network.
> Once Tailscale is installed, you can access everything from your phone, work, or anywhere in the world.

---

## The Big Picture — How It All Connects

```
Internet
   │
   ▼
Your Router (172.17.84.1)
   │
   ▼
TP-Link Switch
   │
   ▼
Beelink (100.117.1.50) ← Proxmox hypervisor ✅
   └── CT100 (100.117.1.171) ← Docker host ✅
         ├── AURA container      → port 8000  ✅
         ├── Budget App          → port 8501  ✅
         ├── Vikunja (Todo)      → port 3456  ✅
         ├── Portainer UI        → port 9000  ✅
         └── Nginx Proxy Manager → port 81    ✅

Tailscale VPN ← INSTALL THIS NEXT
   └── Gives you a 100.64.x.x IP for the Beelink
   └── Access all services from anywhere via that IP
```

---

## ✅ Phase 1 — Hardware & Network (DONE)

Hardware is wired, Beelink is online. Nothing to do here.

---

## ✅ Phase 2 — Proxmox (DONE)

Proxmox VE 9.1.1 is running at https://100.117.1.50:8006

---

## ✅ Phase 3 — Docker Host Container (DONE)

CT100 is running Ubuntu 22.04 with Docker at `100.117.1.171`.

---

## ✅ Phase 4 — All Services Deployed (DONE)

All containers are running and healthy. Auto-restart is configured.

---

## ✅ Phase 5 — Nginx Proxy Manager (DONE)

NPM is live at http://100.117.1.171:81

---

## 🔒 Phase 6 — Tailscale VPN (DO THIS NOW)

> **What Tailscale does:** Creates an encrypted mesh VPN between all your devices.
> Your Beelink gets a permanent `100.64.x.x` IP that works from anywhere — no port forwarding, no dynamic DNS, no firewall rules needed.

### Step 1 — Install Tailscale on the Proxmox Host (Beelink)

SSH into Proxmox from your Mac:
```bash
ssh root@100.117.1.50
```

Install and start Tailscale:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

You'll see a message like:
```
To authenticate, visit:
  https://login.tailscale.com/a/xxxxxxxxxxxxxxxx
```

Open that URL → log in with Google, GitHub, or email → your Beelink is now on your Tailscale network.

Get your Beelink's Tailscale IP (save this — you'll use it everywhere):
```bash
tailscale ip -4
# Example output: 100.64.12.34
```

### Step 2 — Install Tailscale on Your Mac

**Option A — GUI app (recommended):**
Download from https://tailscale.com/download/mac → installs as a menu bar app → sign in with same account.

**Option B — Homebrew:**
```bash
brew install tailscale
sudo tailscaled &
sudo tailscale up
```

### Step 3 — Install Tailscale on Your iPhone

1. App Store → search **"Tailscale"** → Install
2. Open → Sign in with the same account
3. Toggle the VPN switch on

### Step 4 — Test Remote Access

Replace `100.117.1.171` with your Beelink's **Tailscale IP** (the `100.64.x.x` from Step 1):

| Service | Remote URL (via Tailscale) |
|---------|---------------------------|
| Budget App | `http://100.64.x.x:8501` |
| AURA Health | `http://100.64.x.x:8000/health` |
| Vikunja (Todo) | `http://100.64.x.x:3456` |
| Portainer | `http://100.64.x.x:9000` |
| Proxmox | `https://100.64.x.x:8006` |
| Nginx Proxy Manager | `http://100.64.x.x:81` |

**The real test:** Turn off your phone's WiFi (use cellular only) and open `http://100.64.x.x:8501`.
If the budget app loads → Tailscale is working perfectly. 🎉

### Step 5 — (Optional) Point Railway AURA at Your Home Lab

Once Tailscale is confirmed working, you can cut Claude API costs by routing your Railway-hosted budget app through your home lab AURA server:

In Railway dashboard → `darrian-budget` project → **Variables**:
```
AURA_BASE_URL=http://100.64.x.x:8000
AURA_ENABLED=true
```

> ⚠️ Only do this after verifying AURA responds at `http://100.64.x.x:8000/health` from outside your home network (e.g., from your phone on cellular).

---

## 💾 Phase 7 — TrueNAS Storage (When Drives Arrive)

> **Prerequisite:** 2x WD Red Plus 4TB drives + dual-bay USB enclosure

### Step 1 — Connect the Drives
Plug the dual-bay enclosure (with both WD Red drives installed) into the Beelink via USB 3.0.

### Step 2 — Create TrueNAS VM in Proxmox
In Proxmox web UI:
1. Upload TrueNAS Scale ISO: **Datacenter → pve → local → ISO Images → Upload**
2. Create VM: **Create VM**
   - OS: TrueNAS Scale ISO
   - CPU: 2 cores
   - RAM: 8192 MB (TrueNAS needs RAM for ZFS)
   - Disk: 32GB (just for the OS)
3. After VM is created, pass through the USB enclosure:
   - VM → Hardware → Add → USB Device → select your enclosure

### Step 3 — Install TrueNAS Scale
Boot the VM → follow the installer → set a root password → reboot.
Access TrueNAS web UI at the VM's IP (check Proxmox for the assigned IP).

### Step 4 — Create a RAID 1 Mirror Pool
In TrueNAS web UI:
1. **Storage → Create Pool**
2. Name: `tank`
3. Layout: **Mirror** (RAID 1 — one drive mirrors the other, survives one drive failure)
4. Add both WD Red drives → Create

### Step 5 — Create a Dataset for Backups
1. **Storage → tank → Add Dataset**
2. Name: `budget-backups`
3. Share type: Generic

### Step 6 — Configure Nightly Snapshots
1. **Data Protection → Periodic Snapshot Tasks → Add**
2. Dataset: `tank/budget-backups`
3. Schedule: Daily at 2:00 AM
4. Keep: 30 snapshots

---

## 🌍 Phase 8 — (Optional) Public Domain + Real SSL

> **Do you need this?** Only if you want to replace Railway entirely and host at your own domain.
> Your Railway apps at `peachstatesavings.com` already handle this for free.

### Step 1 — Get a Domain
- **Free:** [duckdns.org](https://www.duckdns.org) — gives you `yourname.duckdns.org`
- **Paid:** Namecheap or Cloudflare (~$10/year for `.com`)

### Step 2 — Port Forward on Your Router
In your router admin panel (usually `172.17.84.1`):
- Forward port **80** → `100.117.1.171` (CT100)
- Forward port **443** → `100.117.1.171` (CT100)

### Step 3 — Add SSL in Nginx Proxy Manager
In NPM (http://100.117.1.171:81):
1. **Hosts → Proxy Hosts → Edit** your budget proxy host
2. **SSL tab** → Request a new SSL certificate → Let's Encrypt
3. Enable **Force SSL** and **HTTP/2 Support**
4. Save

Now `https://budget.yourdomain.com` works from anywhere with a real SSL cert. 🔒

---

## Quick Reference — All URLs

### ✅ Live Now (Local Network Only)
| Service | URL |
|---------|-----|
| Proxmox Web UI | https://100.117.1.50:8006 |
| Budget App | http://100.117.1.171:8501 |
| AURA Health | http://100.117.1.171:8000/health |
| Vikunja (Todo) | http://100.117.1.171:3456 |
| Portainer | http://100.117.1.171:9000 |
| Nginx Proxy Manager | http://100.117.1.171:81 |

### ⏳ After Tailscale (From Anywhere) ← NEXT STEP
| Service | URL |
|---------|-----|
| Budget App | http://100.64.x.x:8501 |
| AURA | http://100.64.x.x:8000 |
| Vikunja (Todo) | http://100.64.x.x:3456 |
| Proxmox | https://100.64.x.x:8006 |
| Portainer | http://100.64.x.x:9000 |

### 🌐 Railway (Public Internet — Always On)
| Service | URL |
|---------|-----|
| Budget App (primary) | https://www.peachstatesavings.com |
| Budget App (mirror) | https://darrian-todo-production.up.railway.app |

---

## Checklist — Current Status

- [x] Hardware wired (Beelink → Switch → Router)
- [x] UPS battery connected and charging
- [x] Proxmox installed on Beelink
- [x] LXC container created (CT100 @ 100.117.1.171)
- [x] Docker installed in container
- [x] Repo cloned on container
- [x] All services started with docker compose
- [x] Nginx Proxy Manager configured
- [x] `.local` domains added to Mac's /etc/hosts
- [ ] **Tailscale installed on Beelink + Mac + iPhone** ← DO THIS NEXT
- [ ] Railway updated to use home lab AURA URL (after Tailscale)
- [ ] TrueNAS set up with RAID 1 (when drives arrive)
- [ ] (Optional) Real domain + SSL configured
