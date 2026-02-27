# Recovery Commands — CT100 Offline
**Generated: 2026-02-26 | Run these on the Proxmox host console**

---

## Situation
- CT100 (Docker host @ 100.117.1.171, Tailscale 100.95.125.112) went offline ~40 min ago
- Mac can't reach Proxmox directly (different subnets: Mac=172.17.84.x, PVE=100.117.1.x)
- Must use physical access to Proxmox host OR the Proxmox web UI

---

## Option A — Use the Proxmox Web UI (easiest)

1. Open browser → **https://100.117.1.50:8006**
   (you're on the same local network as the Beelink, so this works)
2. Login: `root` / your password
3. Left sidebar → **pve** → **CT100** → click **Start** (green button)
4. Wait 30 seconds → click **Console** tab
5. Run the commands in Step 2 below inside the console

---

## Option B — Use the Proxmox Shell directly

In the Proxmox web UI:
- Left sidebar → **pve** → **Shell** (this opens a terminal on the Proxmox HOST)

Or if you have a keyboard/monitor on the Beelink, log in as root there.

---

## Step 1 — Start CT100 (run on Proxmox HOST shell)

```bash
# Check CT100 status:
pct status 100

# Start it if stopped:
pct start 100

# Wait for it to boot, then verify:
sleep 10 && pct status 100
# Should say: status: running
```

---

## Step 2 — Fix Tailscale in CT100 (run INSIDE CT100)

Enter CT100's shell from the Proxmox host:
```bash
pct enter 100
```

Now you're inside CT100. Run:
```bash
# Check Tailscale status:
tailscale status

# If it says "stopped" or "not running":
systemctl start tailscaled
tailscale up

# If it needs re-authentication:
tailscale up --reset
# → copy the URL it gives you → open in browser → authenticate

# Verify Tailscale is back:
tailscale ip -4
# Should show: 100.95.125.112

# Check all Docker containers:
docker ps --format "table {{.Names}}\t{{.Status}}"

# If containers are down:
cd /opt/darrian-budget
docker compose up -d

# Exit CT100 back to Proxmox host:
exit
```

---

## Step 3 — Run the Post-Install Script on Proxmox HOST

While you're in the Proxmox shell, run the setup script.
Copy and paste this entire block:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/bookofdarrian/darrian-budget/main/proxmox_setup.sh)" 2>&1
```

**OR** — paste the script contents directly.
The script is at: `/Users/darrianbelcher/Downloads/darrian-budget/proxmox_setup.sh`
Open it in VS Code, select all, copy, paste into the Proxmox shell.

---

## Step 4 — Fix the "No Subscription" Popup

In the Proxmox HOST shell:
```bash
sed -i.bak "s/data.status !== 'Active'/false/g" \
    /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js
systemctl restart pveproxy
```

Refresh the browser → popup is gone. ✅

---

## Step 5 — Verify Everything is Back

From the Proxmox HOST shell:
```bash
# CT100 running?
pct status 100

# CT100 network reachable?
ping -c 3 100.117.1.171

# All services up? (run inside CT100)
pct enter 100
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
tailscale status
exit
```

---

## After CT100 is Back Online

Your Mac will automatically reconnect via Tailscale.
Test from Mac terminal:
```bash
curl http://100.95.125.112:8501/healthz   # budget app
curl http://100.95.125.112:8000/health    # AURA
```

Then copy and run the setup script on the Proxmox host:
```bash
scp /Users/darrianbelcher/Downloads/darrian-budget/proxmox_setup.sh root@100.117.1.50:/root/
ssh root@100.117.1.50 "bash /root/proxmox_setup.sh"
```

---

## Why CT100 Went Offline

Most likely causes:
1. **CT100 was stopped** — check `pct status 100` → start with `pct start 100`
2. **Tailscale daemon crashed** — `systemctl restart tailscaled` inside CT100
3. **Proxmox host rebooted** — CT100 should auto-start (check `pct config 100 | grep onboot`)
   - If `onboot: 0`, fix it: `pct set 100 --onboot 1`

To make CT100 always auto-start on Proxmox reboot:
```bash
pct set 100 --onboot 1
```
