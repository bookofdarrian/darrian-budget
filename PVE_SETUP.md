# Proxmox VE Server Configuration Guide
**Host: `pue` @ `100.117.1.50:8006` | Updated: 2026-02-26**

---

## Confirmed Server State (from terminal session 2026-02-26)

```
Hostname:   pue
Kernel:     6.8.12-1-pve (Proxmox patched kernel)
PVE:        Proxmox VE (running at https://100.117.1.50:8006)
```

### Network Interfaces (confirmed via `ip addr show`)

| Interface | Type | State | IP | Notes |
|-----------|------|-------|----|-------|
| `lo` | Loopback | UP | `127.0.0.1/8` | Normal |
| `enp2s0` (aka `enx78553607ea20`) | Physical NIC | UP | *(none — enslaved to bridge)* | MAC: `78:55:36:07:ea:20` |
| `wlp3s0` (aka `wlxf068e3e18c3c`) | WiFi | **DOWN** | *(none)* | Not used — leave off |
| **`umbro`** | **Linux Bridge** | **UP** | **`100.117.1.50/24`** | **Proxmox host bridge — all VMs/CTs attach here** |

> **Note:** The bridge is named `umbro` instead of the default `vmbr0`. This is fine — Proxmox uses whatever bridge name is in `/etc/network/interfaces`. All containers and VMs should be configured to use `umbro` as their bridge.

---

## Step 1 — Run the Post-Install Script

SSH into the Proxmox host from your Mac:

```bash
ssh root@100.117.1.50
```

Copy the setup script to the host and run it:

```bash
# Option A — from your Mac, copy the script over:
scp proxmox_setup.sh root@100.117.1.50:/root/
ssh root@100.117.1.50 "bash /root/proxmox_setup.sh"

# Option B — paste directly in the SSH session:
# (copy contents of proxmox_setup.sh, paste into terminal)
```

The script does 9 things automatically:
1. ✅ Disables the paid enterprise repo → enables free no-subscription repo
2. ✅ Full system update (`apt upgrade`)
3. ✅ Installs essential tools (htop, curl, git, vim, etc.)
4. ✅ Hardens SSH (rate limits, timeouts)
5. ✅ Installs + configures fail2ban (blocks brute-force on SSH + Proxmox UI)
6. ✅ Verifies the `umbro` bridge is up with correct IP
7. ✅ Reports storage status
8. ✅ Enables automatic security updates
9. ✅ Prints full status report

---

## Step 2 — Verify Network Interfaces File

After running the script, verify `/etc/network/interfaces` matches the confirmed config:

```bash
cat /etc/network/interfaces
```

It should look like this (see `proxmox_network.conf` in this repo):

```
auto lo
iface lo inet loopback

auto enp2s0
iface enp2s0 inet manual

auto umbro
iface umbro inet static
    address  100.117.1.50/24
    gateway  100.117.1.1
    dns-nameservers 1.1.1.1 8.8.8.8
    bridge-ports enp2s0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes

iface wlp3s0 inet manual
```

If it's different, copy the corrected version:

```bash
# From your Mac:
scp proxmox_network.conf root@100.117.1.50:/etc/network/interfaces
ssh root@100.117.1.50 "systemctl restart networking && ip addr show umbro"
```

---

## Step 3 — Dismiss the "No Subscription" Popup

Every time you open the Proxmox web UI, a popup says:
> *"You do not have a valid subscription for this server."*

**Fix it permanently:**

```bash
# SSH into Proxmox host:
ssh root@100.117.1.50

# Patch the JS file that shows the popup:
sed -i.bak "s/data.status !== 'Active'/false/g" \
    /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js

# Restart the web proxy:
systemctl restart pveproxy
```

Now refresh the browser — no more popup. ✅

---

## Step 4 — Verify CT100 is Running

In the Proxmox web UI (`https://100.117.1.50:8006`) or via SSH:

```bash
# Check container status:
pct status 100

# Expected output:
# status: running

# If stopped, start it:
pct start 100

# View container config:
pct config 100
```

CT100 should show:
- **IP:** `100.117.1.171`
- **Bridge:** `umbro`
- **OS:** Ubuntu 22.04
- **Cores:** 4
- **RAM:** 4096 MB

---

## Step 5 — Verify All Docker Services in CT100

SSH into CT100 (the Docker host):

```bash
ssh root@100.117.1.171
# or via Tailscale:
ssh root@100.95.125.112
```

Check all containers:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output:

```
NAMES                STATUS          PORTS
budget-app           Up X hours      0.0.0.0:8501->8501/tcp
aura                 Up X hours      0.0.0.0:8000->8000/tcp
portainer            Up X hours      0.0.0.0:9000->9000/tcp
nginx-proxy-manager  Up X hours      0.0.0.0:80->80/tcp, 0.0.0.0:81->81/tcp, 0.0.0.0:443->443/tcp
code-server          Up X hours      0.0.0.0:8080->8080/tcp
```

If any container is down:

```bash
cd /opt/darrian-budget   # or wherever docker-compose.yml lives
docker compose up -d
```

---

## Step 6 — Verify Tailscale on CT100

```bash
# Inside CT100:
tailscale status
```

Expected:
```
100.95.125.112  docker-host  ...  online
100.74.143.69   macbook      ...  online
```

If Tailscale is down:
```bash
tailscale up
```

---

## Step 7 — Deploy Monitoring Stack (if not done)

```bash
# Inside CT100:
cd /opt/monitoring
cp .env.example .env
nano .env   # fill in GRAFANA_ADMIN_PASSWORD, PUSHOVER keys

docker compose up -d

# Verify:
docker ps | grep -E "grafana|prometheus|alertmanager|node-exporter|cadvisor"
```

Then open Grafana: `http://100.117.1.171:3000`
- Login: `admin` / your password
- Import dashboard ID `1860` (Node Exporter Full)

---

## Quick Diagnostic Commands (run on Proxmox host)

```bash
# Full system health check:
pveversion                          # PVE version
pct list                            # all containers
qm list                             # all VMs
pvesm status                        # storage pools
ip addr show umbro                  # bridge IP
systemctl status pvedaemon pveproxy # core PVE services
fail2ban-client status              # banned IPs
journalctl -u pvedaemon -n 50       # recent PVE logs
df -h                               # disk usage
free -h                             # RAM usage
uptime                              # load average
```

---

## Network Topology (Confirmed)

```
Internet
   │
   ▼
Gigstreem Gateway / Home Router
   │
   ▼
TP-Link Switch (TL-SG108)
   │
   ▼
Beelink Mini PC — eth: enp2s0 → bridge: umbro @ 100.117.1.50
   │  (Proxmox VE host — hostname: pue)
   │
   └── CT100 (Ubuntu 22.04 LXC) @ 100.117.1.171
         bridge: umbro
         ├── budget-app      → :8501
         ├── aura            → :8000
         ├── portainer       → :9000
         ├── nginx-proxy-mgr → :80/:81/:443
         ├── code-server     → :8080
         └── tailscale       → 100.95.125.112 (remote access)
```

---

## All Service URLs

### Local Network (100.117.1.x)
| Service | URL |
|---------|-----|
| **Proxmox Web UI** | https://100.117.1.50:8006 |
| Budget App | http://100.117.1.171:8501 |
| AURA Health | http://100.117.1.171:8000/health |
| Portainer | http://100.117.1.171:9000 |
| Nginx Proxy Manager | http://100.117.1.171:81 |
| code-server (VS Code) | http://100.117.1.171:8080 |
| Grafana | http://100.117.1.171:3000 |
| Prometheus | http://100.117.1.171:9090 |

### Via Tailscale (from anywhere)
| Service | URL |
|---------|-----|
| Budget App | http://100.95.125.112:8501 |
| AURA | http://100.95.125.112:8000/health |
| Portainer | http://100.95.125.112:9000 |
| Proxmox | https://100.95.125.112:8006 |
| NPM | http://100.95.125.112:81 |
| code-server | http://100.95.125.112:8080 |
| Grafana | http://100.95.125.112:3000 |

### Public Internet (Railway)
| Service | URL |
|---------|-----|
| Budget App (primary) | https://www.peachstatesavings.com |
| Budget App (mirror) | https://darrian-todo-production.up.railway.app |

---

## Troubleshooting

### "Can't reach Proxmox UI"
```bash
# Check pveproxy is running:
systemctl status pveproxy
# Restart if needed:
systemctl restart pveproxy
# Verify port is open:
ss -tlnp | grep 8006
```

### "umbro bridge lost its IP"
```bash
systemctl restart networking
ip addr show umbro
# Should show 100.117.1.50/24
```

### "CT100 won't start"
```bash
pct status 100
pct start 100
# Check logs:
journalctl -u pve-container@100 -n 50
```

### "Docker containers down in CT100"
```bash
ssh root@100.117.1.171
docker ps -a                    # see all containers including stopped
docker compose -f /opt/darrian-budget/docker-compose.yml up -d
```

### "fail2ban blocked my IP"
```bash
# On Proxmox host:
fail2ban-client status sshd
fail2ban-client set sshd unbanip YOUR_IP
```
