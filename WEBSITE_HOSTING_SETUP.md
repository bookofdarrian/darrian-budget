# Website Hosting on Your Home Lab — Step-by-Step
**For: Darrian Belcher | Updated: 2025-02-25**

---

## Overview — What You're Doing

You're moving your websites OFF Railway (cloud, costs money) and onto your **Beelink home lab server** (you own it, runs 24/7, free after hardware cost).

**Sites you're hosting:**
| Site | Stack | Port |
|------|-------|------|
| Darrian Budget App | Python / Streamlit | 8501 |
| AURA Compression Server | Python / FastAPI | 8000 |
| Portainer (Docker UI) | Web UI | 9000 |
| Nginx Proxy Manager | Reverse Proxy | 81 |

---

## ⚠️ Prerequisites — Do These First

Before ANY of this works, you need:
- [ ] Beelink plugged into TP-Link switch (same network as your Mac)
- [ ] Proxmox installed on Beelink (see HOMELAB_HOSTING_GUIDE.md Phase 2)
- [ ] LXC container created in Proxmox (see Phase 3)
- [ ] Docker installed inside the container

**If you haven't done those yet — stop here and do them first.**

---

## Step 1 — Verify Your Network Is Ready

On your Mac, open Terminal:

```bash
# Check your Mac's IP (should be 172.17.84.x or 192.168.x.x)
ipconfig getifaddr en0    # WiFi
ipconfig getifaddr en1    # Ethernet (if plugged in)

# Scan for the Beelink on your network
arp -a | grep -v incomplete

# Or use nmap for a full scan:
brew install nmap
nmap -sn 172.17.84.0/24
# Look for the Beelink — it'll show up as a new device
```

Once you find the Beelink's IP, write it down. We'll call it `BEELINK_IP` below.
(It should be something like `172.17.84.50` or `192.168.1.50`)

---

## Step 2 — SSH Into Your Beelink

```bash
# From your Mac:
ssh root@BEELINK_IP

# Example:
ssh root@192.168.1.50

# Accept the fingerprint, enter your Proxmox root password
```

---

## Step 3 — Get Into the Docker Container

In Proxmox, your Docker container is a separate LXC. Access it:

```bash
# Option A: From Proxmox web UI
# → Click your container (e.g. CT 100) → Console tab

# Option B: From Proxmox SSH shell
pct list                    # shows all containers and their IDs
pct enter 100               # replace 100 with your container ID
```

---

## Step 4 — Clone Your Repo Into the Container

```bash
# Inside the docker-host container:
apt update && apt install -y git curl

# Clone your budget app repo
git clone https://github.com/bookofdarrian/darrian-budget.git /root/darrian-budget

# Verify it cloned correctly
ls /root/darrian-budget
# Should see: app.py, requirements.txt, pages/, utils/, aura/, etc.
```

---

## Step 5 — Create the Environment File

Your budget app needs environment variables (database URL, API keys, etc.).
Create a `.env` file in the homelab directory:

```bash
mkdir -p /root/homelab
cat > /root/homelab/.env << 'EOF'
# ── Database ──────────────────────────────────────────────────────────────
# Copy your DATABASE_URL from Railway dashboard → Variables
DATABASE_URL=postgresql://user:password@host:5432/dbname

# ── AURA (internal Docker network — use service name, not IP) ─────────────
AURA_BASE_URL=http://aura:8000
AURA_ENABLED=true

# ── Stripe (if you use it) ────────────────────────────────────────────────
# STRIPE_SECRET_KEY=sk_live_...
# STRIPE_PUBLISHABLE_KEY=pk_live_...

# ── Claude / Anthropic ────────────────────────────────────────────────────
# ANTHROPIC_API_KEY=sk-ant-...

# ── App Settings ──────────────────────────────────────────────────────────
APP_ENV=production
EOF

# IMPORTANT: Edit this file with your real values
nano /root/homelab/.env
```

**Where to get your Railway env vars:**
1. Go to https://railway.app → your project
2. Click **Variables** tab
3. Copy each value into the `.env` file above

---

## Step 6 — Create the Master docker-compose.yml

```bash
cat > /root/homelab/docker-compose.yml << 'EOF'
version: "3.9"

services:

  # ── AURA Compression Server ──────────────────────────────────────────────
  aura:
    build:
      context: /root/darrian-budget/aura
      dockerfile: Dockerfile
    container_name: aura
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - AURA_HOST=0.0.0.0
      - AURA_PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - homelab

  # ── Budget App (Streamlit) ────────────────────────────────────────────────
  budget:
    build:
      context: /root/darrian-budget
      dockerfile: Dockerfile
    container_name: budget-app
    restart: unless-stopped
    ports:
      - "8501:8501"
    env_file:
      - .env
    depends_on:
      aura:
        condition: service_healthy
    networks:
      - homelab
    volumes:
      - budget_data:/app/data

  # ── Portainer (Docker Management UI) ─────────────────────────────────────
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    networks:
      - homelab

  # ── Nginx Proxy Manager ───────────────────────────────────────────────────
  nginx-proxy-manager:
    image: jc21/nginx-proxy-manager:latest
    container_name: nginx-proxy-manager
    restart: unless-stopped
    ports:
      - "80:80"      # HTTP traffic
      - "443:443"    # HTTPS traffic
      - "81:81"      # NPM Admin UI
    volumes:
      - npm_data:/data
      - npm_letsencrypt:/etc/letsencrypt
    networks:
      - homelab

networks:
  homelab:
    driver: bridge

volumes:
  portainer_data:
  npm_data:
  npm_letsencrypt:
  budget_data:
EOF
```

---

## Step 7 — Create the Budget App Dockerfile

The budget app needs a Dockerfile in the repo root. Create it:

```bash
cat > /root/darrian-budget/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start Streamlit
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
EOF
```

---

## Step 8 — Launch Everything

```bash
cd /root/homelab

# Build and start all containers (first run takes 3-5 minutes)
docker compose up -d --build

# Watch the build progress:
docker compose logs -f

# Once it settles, check all containers are running:
docker compose ps
```

**Expected output:**
```
NAME                   STATUS          PORTS
aura                   Up (healthy)    0.0.0.0:8000->8000/tcp
budget-app             Up (healthy)    0.0.0.0:8501->8501/tcp
portainer              Up              0.0.0.0:9000->9000/tcp
nginx-proxy-manager    Up              0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp, 0.0.0.0:81->81/tcp
```

---

## Step 9 — Test Each Service

From your Mac browser, visit each URL (replace `192.168.1.51` with your container's IP):

```bash
# Find your container's IP:
# In Proxmox web UI → click your container → Summary → IP Address
# OR from inside the container:
hostname -I
```

| Service | Test URL | Expected |
|---------|----------|----------|
| Budget App | `http://192.168.1.51:8501` | Streamlit login page |
| AURA Health | `http://192.168.1.51:8000/health` | `{"status": "ok"}` |
| Portainer | `http://192.168.1.51:9000` | Portainer setup page |
| NPM Admin | `http://192.168.1.51:81` | Nginx Proxy Manager login |

---

## Step 10 — Configure Nginx Proxy Manager

### 10A. First Login
Go to `http://192.168.1.51:81`
- Email: `admin@example.com`
- Password: `changeme`
- **Change these immediately** when prompted

### 10B. Add Proxy Hosts (Pretty Local URLs)
Go to **Hosts → Proxy Hosts → Add Proxy Host**

**Budget App:**
- Domain Names: `budget.local`
- Scheme: `http`
- Forward Hostname/IP: `192.168.1.51`
- Forward Port: `8501`
- ✅ Websockets Support (REQUIRED for Streamlit)
- ✅ Block Common Exploits

**AURA:**
- Domain Names: `aura.local`
- Scheme: `http`
- Forward Hostname/IP: `192.168.1.51`
- Forward Port: `8000`

**Portainer:**
- Domain Names: `portainer.local`
- Scheme: `http`
- Forward Hostname/IP: `192.168.1.51`
- Forward Port: `9000`

### 10C. Add .local Domains to Your Mac
```bash
# On your Mac (not the server):
sudo nano /etc/hosts

# Add these lines at the bottom:
192.168.1.51    budget.local
192.168.1.51    aura.local
192.168.1.51    portainer.local
192.168.1.51    npm.local

# Save: Ctrl+O, Enter, Ctrl+X

# Flush DNS cache:
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```

Now visit `http://budget.local` from your Mac — it works! 🎉

---

## Step 11 — Access From Anywhere with Tailscale

Right now your sites only work on your home WiFi.
Tailscale gives you a private VPN so you can access them from anywhere.

### 11A. Install Tailscale on the Beelink (Proxmox host)
```bash
# SSH into Proxmox:
ssh root@192.168.1.50

# Install Tailscale:
curl -fsSL https://tailscale.com/install.sh | sh

# Start and authenticate (opens a URL — open it on your Mac):
tailscale up

# Get your Tailscale IP:
tailscale ip -4
# Note this IP — looks like 100.x.x.x
```

### 11B. Install Tailscale on Your Mac
```bash
brew install tailscale
sudo tailscaled &
sudo tailscale up
```
Or download the app: https://tailscale.com/download/mac

### 11C. Install Tailscale on Your Phone
- iOS: App Store → "Tailscale"
- Android: Play Store → "Tailscale"
- Sign in with the same account

### 11D. Access Your Sites From Anywhere
Replace `192.168.1.51` with your Tailscale IP (`100.x.x.x`):
```
http://100.x.x.x:8501   ← Budget App (from phone, work, anywhere)
http://100.x.x.x:8000   ← AURA
http://100.x.x.x:9000   ← Portainer
http://100.x.x.x:81     ← Nginx Proxy Manager
https://100.x.x.x:8006  ← Proxmox Web UI
```

---

## Step 12 — Update Railway to Use Your Home Lab AURA

Your budget app on Railway can now use your home lab AURA server instead of running without it.

In Railway dashboard → your project → **Variables** tab:
```
AURA_BASE_URL=http://100.x.x.x:8000    ← your Tailscale IP
AURA_ENABLED=true
```

This means:
- Railway hosts the budget app (public URL, SSL, always on)
- Your home lab runs AURA (saves Claude API tokens)
- Best of both worlds until you're ready to fully self-host

---

## Step 13 — (Optional) Real Domain + Public HTTPS

Want `budget.yourdomain.com` accessible from the internet?

### 13A. Get a Free Domain
- **Free:** https://www.duckdns.org → gives you `yourname.duckdns.org`
- **Paid:** Namecheap or Cloudflare (~$10/year for `.com`)

### 13B. Port Forward on Your Router
In your router admin panel (usually `http://172.17.84.1`):
- Add port forward: **External 80** → `192.168.1.51:80`
- Add port forward: **External 443** → `192.168.1.51:443`

### 13C. Point Your Domain to Your Home IP
Get your public IP:
```bash
curl ifconfig.me
```
Set your domain's A record to this IP.

### 13D. Get Free SSL in Nginx Proxy Manager
In NPM → your proxy host → **SSL tab**:
- Request a new SSL certificate (Let's Encrypt)
- ✅ Force SSL
- ✅ HTTP/2 Support
- ✅ HSTS Enabled

Now `https://budget.yourdomain.com` works from anywhere with a real SSL cert! 🔒

---

## Keeping Your Sites Updated

When you push code changes to GitHub, update your home lab:

```bash
# SSH into your container
ssh root@192.168.1.50
pct enter 100

# Pull latest code
cd /root/darrian-budget
git pull origin main

# Rebuild and restart only the budget container
cd /root/homelab
docker compose up -d --build budget

# Check it's running
docker compose ps
docker compose logs budget --tail=50
```

---

## Troubleshooting

### Container won't start
```bash
docker compose logs budget
# Look for Python errors, missing env vars, etc.
```

### Can't reach the site from Mac
```bash
# Check the container IP
hostname -I   # run inside the container

# Check the port is open
curl http://192.168.1.51:8501
```

### Budget app crashes on startup
```bash
# Check for missing environment variables
docker compose exec budget env | grep -E "DATABASE|AURA|STRIPE"

# Check Python errors
docker compose logs budget --tail=100
```

### AURA not connecting
```bash
# Test AURA directly
curl http://192.168.1.51:8000/health

# Check AURA logs
docker compose logs aura
```

---

## Quick Reference — All URLs

### On Your Home Network
| Service | URL |
|---------|-----|
| Budget App | `http://192.168.1.51:8501` |
| Budget App (pretty) | `http://budget.local` |
| AURA Health | `http://192.168.1.51:8000/health` |
| Portainer | `http://192.168.1.51:9000` |
| Nginx Proxy Manager | `http://192.168.1.51:81` |
| Proxmox Web UI | `https://192.168.1.50:8006` |

### From Anywhere (After Tailscale)
| Service | URL |
|---------|-----|
| Budget App | `http://100.x.x.x:8501` |
| AURA | `http://100.x.x.x:8000` |
| Portainer | `http://100.x.x.x:9000` |
| Proxmox | `https://100.x.x.x:8006` |

### Public Internet (After Domain + Port Forward)
| Service | URL |
|---------|-----|
| Budget App | `https://budget.yourdomain.com` |
| AURA | `https://aura.yourdomain.com` |
