# Tailscale & Remote Access Guide
**For: Darrian Belcher | Updated: 2026-02-25**

---

## What is Tailscale?

Tailscale is a VPN that connects all your devices into one private network.
Think of it like being on the same WiFi — even when you're not home.

**Your Tailscale network:**
| Device | Tailscale IP | Status |
|--------|-------------|--------|
| Home Lab Server (CT100) | `100.95.125.112` | ✅ Always on |
| MacBook Pro | `100.74.143.69` | ✅ Connected |
| iPhone | Install from App Store | ⏳ Not yet |

---

## How to Turn Tailscale On/Off

### On Your Mac
- Look for the **Tailscale icon** in your menu bar (top right of screen)
- Click it → toggle **Connected / Disconnected**
- When connected, you can reach your home lab from anywhere

### On Your iPhone (after installing)
- Open the **Tailscale app**
- Tap the toggle to turn VPN **on or off**
- When on, you can access your home lab from cellular data

---

## Your Websites — What They Are & How to Access Them

### 🍑 Budget App (Peach State Savings)
Your personal finance app — expenses, income, investments, goals, etc.

| Where | URL | Works Without Tailscale? |
|-------|-----|--------------------------|
| Public (Railway) | https://www.peachstatesavings.com | ✅ Yes — anyone can access |
| Home Lab (local) | http://100.117.1.171:8501 | ❌ Home network only |
| Home Lab (Tailscale) | http://100.95.125.112:8501 | ✅ Yes — from anywhere with Tailscale on |

**When to use which:**
- At home on WiFi → any of the three work
- Away from home (phone on cellular) → use `peachstatesavings.com` OR turn on Tailscale and use `100.95.125.112:8501`
- Want to avoid Railway costs → use Tailscale URL

---

### 🤖 AURA (AI Compression Server)
Runs in the background — you don't visit this directly.
It compresses your Claude AI requests to save money on API costs.

| Where | URL |
|-------|-----|
| Home Lab (local) | http://100.117.1.171:8000/health |
| Home Lab (Tailscale) | http://100.95.125.112:8000/health |

**To check if it's running:** Open either URL — you should see:
```json
{"status": "healthy", "service": "AURA Compression Service"}
```

---

### 🐳 Portainer (Docker Manager)
A web UI to see and manage all your running containers on the home lab.

| Where | URL |
|-------|-----|
| Home Lab (local) | http://100.117.1.171:9000 |
| Home Lab (Tailscale) | http://100.95.125.112:9000 |

**Use this to:** Start/stop containers, view logs, check resource usage.

---

### 🔀 Nginx Proxy Manager (NPM)
Controls how web traffic is routed on your home lab. Handles SSL certs.

| Where | URL |
|-------|-----|
| Home Lab (local) | http://100.117.1.171:81 |
| Home Lab (Tailscale) | http://100.95.125.112:81 |

---

### 🖥️ Proxmox (Server Hypervisor)
The main control panel for your Beelink server — manage VMs and containers.

| Where | URL |
|-------|-----|
| Home Lab (local) | https://100.117.1.50:8006 |
| Home Lab (Tailscale) | https://100.95.125.112:8006 |

> ⚠️ Click through the SSL warning — it's a self-signed cert, it's safe.

---

## Accessing From Your Phone (Step by Step)

### Access the Budget App on iPhone
1. Install **Tailscale** from App Store → sign in with `dbelcher003@`
2. Toggle Tailscale **ON**
3. Open **Safari** → type: `http://100.95.125.112:8501`
4. Budget app loads! 🎉

### Access the Budget App WITHOUT Tailscale
Just go to: **https://www.peachstatesavings.com**
This always works — no Tailscale needed. It's hosted on Railway 24/7.

---

## SSH Into Your Devices From iPhone

Install **Termius** (free, App Store) — it's a terminal/SSH app.

### SSH into your home lab server:
- Host: `100.95.125.112`
- Username: `root`
- Password: your CT100 password
- Then run Docker commands, check logs, etc.

### SSH into your Mac:
1. First enable on Mac: **System Settings → General → Sharing → Remote Login → ON**
2. In Termius: Host `100.74.143.69` → Username: `darrianbelcher`

---

## See Your Mac's Desktop on Your Phone

1. Enable on Mac: **System Settings → General → Sharing → Screen Sharing → ON**
2. Install **Jump Desktop** (App Store, free tier available)
3. Connect to: `100.74.143.69`
4. Your full Mac desktop appears on your phone screen

---

## Quick Cheat Sheet

| I want to... | Do this |
|-------------|---------|
| Use budget app from anywhere | Go to `peachstatesavings.com` |
| Use budget app via home lab | Turn on Tailscale → `100.95.125.112:8501` |
| Check if home lab is running | Turn on Tailscale → `100.95.125.112:8000/health` |
| Manage Docker containers | Turn on Tailscale → `100.95.125.112:9000` |
| SSH into home lab from phone | Termius → `100.95.125.112` |
| Control Mac from phone | Jump Desktop → `100.74.143.69` |
| Access Proxmox | Turn on Tailscale → `https://100.95.125.112:8006` |

---

## Troubleshooting

**"I can't reach 100.95.125.112"**
→ Make sure Tailscale is turned ON on your device
→ Check that CT100 is running: SSH into Proxmox → `pct status 100`

**"Budget app won't load"**
→ Try the Railway URL first: `peachstatesavings.com`
→ If that works but home lab doesn't, CT100 may need a restart

**"Tailscale says disconnected"**
→ On Mac: click menu bar icon → Connect
→ On iPhone: open Tailscale app → toggle ON

**"I forgot my Tailscale account"**
→ Account: `dbelcher003@` (same email you used to sign up)
→ Go to https://login.tailscale.com to manage devices
