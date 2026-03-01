# 📊 Homelab Monitoring Stack
**Grafana + Prometheus + Node Exporter + cAdvisor + Alertmanager**

Beautiful dashboards for CPU, RAM, disk, network, and every container — with instant phone alerts when anything crashes.

---

## What's Included

| Service | Purpose | Port |
|---------|---------|------|
| **Prometheus** | Metrics database (30-day retention) | 9090 |
| **Grafana** | Dashboards & alert UI | 3000 |
| **Node Exporter** | Host CPU, RAM, disk, network, filesystem | 9100 |
| **cAdvisor** | Per-container CPU, RAM, network, I/O | 8080 |
| **Alertmanager** | Routes alerts → iPhone (Pushover/Telegram) | 9093 |

---

## ⚡ Quick Start (5 minutes)

### Step 1 — Copy to your server

```bash
# On your Mac, push the monitoring folder to CT100
scp -r monitoring/ root@100.117.1.171:/opt/monitoring
```

Or if you're already SSH'd into CT100:
```bash
cd /opt
git pull   # if you have the repo cloned here
```

### Step 2 — Configure alerts

```bash
cd /opt/monitoring
cp .env.example .env
nano .env   # fill in your Pushover keys (see below)
```

### Step 3 — Launch

```bash
docker-compose up -d
```

That's it. All 5 containers start automatically. ✅

---

## 📱 Phone Alerts Setup (Pushover — Recommended)

**Cost:** Free 30-day trial, then **$5 one-time** (worth every penny)

1. Go to **[pushover.net](https://pushover.net)** → Create account
2. Note your **User Key** (top of dashboard)
3. Click **"Create an Application"** → Name it "Homelab" → Submit
4. Note the **API Token**
5. Install **Pushover** app on your iPhone → sign in with same account
6. Add to your `.env`:
   ```
   PUSHOVER_USER_KEY=your_user_key
   PUSHOVER_API_TOKEN=your_api_token
   ```
7. Restart: `docker-compose restart alertmanager`

**Test it:**
```bash
curl -s \
  --form-string "token=YOUR_API_TOKEN" \
  --form-string "user=YOUR_USER_KEY" \
  --form-string "title=🧪 Test Alert" \
  --form-string "message=Homelab monitoring is working!" \
  https://api.pushover.net/1/messages.json
```

---

## 📱 Phone Alerts Setup (Telegram — Free)

1. Open Telegram → search **@BotFather** → send `/newbot`
2. Follow prompts → get your **BOT_TOKEN**
3. Message your new bot once (any message)
4. Get your chat ID:
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   # Look for: "chat":{"id": 123456789}
   ```
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABCdef...
   TELEGRAM_CHAT_ID=123456789
   ```
6. In `alertmanager/alertmanager.yml`, uncomment the `telegram-phone` receiver and change the default route receiver to `telegram-phone`

---

## 📊 Import Dashboard 1860 (Node Exporter Full)

This is the best server monitoring dashboard ever made. Import it in 30 seconds:

1. Open Grafana: **http://100.117.1.171:3000**
2. Login: `admin` / `homelab2026` (or whatever you set in `.env`)
3. Left sidebar → **Dashboards** → **Import**
4. Enter ID: **`1860`** → click **Load**
5. Select datasource: **Prometheus** → **Import**

You now have 30+ panels showing everything about your server. 🎉

**Other great dashboard IDs to import:**
| ID | Name | What it shows |
|----|------|---------------|
| **1860** | Node Exporter Full | CPU, RAM, disk, network — everything |
| **893** | Docker and system monitoring | Container overview |
| **14282** | Cadvisor Exporter | Per-container deep dive |
| **3662** | Prometheus 2.0 Overview | Prometheus internals |

---

## 🚨 Alert Rules

All alerts are in `prometheus/rules/host_alerts.yml`:

### Host Alerts
| Alert | Threshold | Severity |
|-------|-----------|----------|
| HighCPUUsage | CPU > 85% for 5min | ⚠️ Warning |
| CriticalCPUUsage | CPU > 95% for 2min | 🚨 Critical |
| HighMemoryUsage | RAM > 85% for 5min | ⚠️ Warning |
| CriticalMemoryUsage | RAM > 95% for 2min | 🚨 Critical |
| DiskSpaceWarning | Disk > 80% full | ⚠️ Warning |
| DiskSpaceCritical | Disk > 90% full | 🚨 Critical |
| DiskFillingSoon | Disk full in < 4 hours | ⚠️ Warning |
| HostDown | Node Exporter unreachable 1min | 🚨 Critical |
| HighNetworkReceive | Inbound > 100 MB/s | ⚠️ Warning |
| HighNetworkTransmit | Outbound > 100 MB/s | ⚠️ Warning |
| HighSystemLoad | Load > CPUs × 2 for 10min | ⚠️ Warning |
| HighSwapUsage | Swap > 80% | ⚠️ Warning |

### Container Alerts
| Alert | Trigger | Severity |
|-------|---------|----------|
| ContainerRestarted | Any container restarts | ⚠️ Warning |
| ContainerDown | Key container missing 2min | 🚨 Critical |
| ContainerHighCPU | Container CPU > 80% | ⚠️ Warning |
| ContainerHighMemory | Container RAM > 90% of limit | ⚠️ Warning |
| ContainerOOMKilled | Container killed by OOM | 🚨 Critical |

---

## 🌐 All URLs

### Local Network
| Service | URL |
|---------|-----|
| **Grafana** | http://100.117.1.171:3000 |
| Prometheus | http://100.117.1.171:9090 |
| Alertmanager | http://100.117.1.171:9093 |
| Node Exporter metrics | http://100.117.1.171:9100/metrics |
| cAdvisor | http://100.117.1.171:8080 |

### Via Tailscale (from anywhere)
| Service | URL |
|---------|-----|
| **Grafana** | http://100.95.125.112:3000 |
| Prometheus | http://100.95.125.112:9090 |
| Alertmanager | http://100.95.125.112:9093 |

---

## 🔧 Common Commands

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f grafana
docker-compose logs -f prometheus
docker-compose logs -f alertmanager

# Reload Prometheus config (no restart needed)
curl -X POST http://localhost:9090/-/reload

# Reload Alertmanager config (no restart needed)
curl -X POST http://localhost:9093/-/reload

# Stop everything
docker-compose down

# Stop and wipe all data (nuclear option)
docker-compose down -v
```

---

## 📁 File Structure

```
monitoring/
├── docker-compose.yml              # All 5 services
├── .env.example                    # Copy to .env, fill in keys
├── .env                            # Your secrets (gitignored)
│
├── prometheus/
│   ├── prometheus.yml              # Scrape config + alert rules
│   └── rules/
│       └── host_alerts.yml         # All alert rules
│
├── alertmanager/
│   └── alertmanager.yml            # Alert routing → Pushover/Telegram/email
│
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── prometheus.yml      # Auto-connects Prometheus datasource
        ├── dashboards/
        │   └── dashboards.yml      # Auto-loads dashboard JSON files
        └── alerting/
            └── alertmanager.yml    # Connects Grafana alerts → Alertmanager
```

---

## 💡 Tips

- **Dashboard 1860** is the gold standard. Import it first.
- Prometheus keeps **30 days** of metrics by default. Change `--storage.tsdb.retention.time` in docker-compose.yml if you want more/less.
- cAdvisor runs **privileged** — this is required to read container stats from the Docker socket.
- All containers are on the `monitoring` bridge network and talk to each other by service name (e.g., `prometheus:9090`).
- The `.env` file is gitignored — your Pushover keys stay private.
