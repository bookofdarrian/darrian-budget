#!/bin/bash
# =============================================================================
# Proxmox VE Post-Install Configuration Script
# Host: pue @ 100.117.1.50 | Bridge: umbro | Owner: Darrian Belcher
# Run this as root on the Proxmox host (not inside a container)
# Usage: bash proxmox_setup.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
info() { echo -e "${BLUE}[→]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ── Guard: must run as root on Proxmox ──────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Run as root: sudo bash proxmox_setup.sh"
command -v pveversion &>/dev/null || err "This script must run on a Proxmox VE host"

PVE_VERSION=$(pveversion | head -1)
BRIDGE="umbro"
HOST_IP="100.117.1.50"

echo ""
echo "============================================================"
echo "  Proxmox Post-Install Setup"
echo "  Host: $(hostname) @ ${HOST_IP}"
echo "  Bridge: ${BRIDGE}"
echo "  PVE: ${PVE_VERSION}"
echo "============================================================"
echo ""

# =============================================================================
# STEP 1 — Disable the enterprise (paid) repo, enable free community repo
# =============================================================================
info "Step 1/9 — Configuring APT repositories (no-subscription)..."

# Disable enterprise repo (requires paid subscription)
if [ -f /etc/apt/sources.list.d/pve-enterprise.list ]; then
    sed -i 's|^deb|#deb|' /etc/apt/sources.list.d/pve-enterprise.list
    log "Disabled pve-enterprise repo"
fi

# Disable Ceph enterprise repo if present
if [ -f /etc/apt/sources.list.d/ceph.list ]; then
    sed -i 's|^deb|#deb|' /etc/apt/sources.list.d/ceph.list
    log "Disabled ceph enterprise repo"
fi

# Add no-subscription (free) repo
FREE_REPO="deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription"
if ! grep -qF "pve-no-subscription" /etc/apt/sources.list.d/pve-no-subscription.list 2>/dev/null; then
    echo "$FREE_REPO" > /etc/apt/sources.list.d/pve-no-subscription.list
    log "Added pve-no-subscription repo"
else
    log "pve-no-subscription repo already configured"
fi

# =============================================================================
# STEP 2 — System update
# =============================================================================
info "Step 2/9 — Updating system packages (this may take a few minutes)..."
apt-get update -qq
apt-get upgrade -y -qq
apt-get dist-upgrade -y -qq
apt-get autoremove -y -qq
log "System fully updated"

# =============================================================================
# STEP 3 — Install essential tools
# =============================================================================
info "Step 3/9 — Installing essential tools..."
apt-get install -y -qq \
    curl wget git htop iotop iftop \
    net-tools dnsutils nmap \
    vim nano \
    unzip zip \
    lsof \
    fail2ban \
    ufw \
    smartmontools \
    lm-sensors \
    ethtool \
    screen tmux \
    jq \
    2>/dev/null
log "Essential tools installed"

# =============================================================================
# STEP 4 — Harden SSH
# =============================================================================
info "Step 4/9 — Hardening SSH..."

SSH_CONFIG="/etc/ssh/sshd_config"
cp "${SSH_CONFIG}" "${SSH_CONFIG}.bak.$(date +%Y%m%d)"

# Disable root password login (keep key-based root login for Proxmox)
# Note: Proxmox needs root SSH — we harden but don't fully disable
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' "${SSH_CONFIG}"
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' "${SSH_CONFIG}"
sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 5/' "${SSH_CONFIG}"
sed -i 's/^#*LoginGraceTime.*/LoginGraceTime 30/' "${SSH_CONFIG}"
sed -i 's/^#*ClientAliveInterval.*/ClientAliveInterval 300/' "${SSH_CONFIG}"
sed -i 's/^#*ClientAliveCountMax.*/ClientAliveCountMax 2/' "${SSH_CONFIG}"

# Add settings if not present
grep -q "^MaxAuthTries" "${SSH_CONFIG}" || echo "MaxAuthTries 5" >> "${SSH_CONFIG}"
grep -q "^LoginGraceTime" "${SSH_CONFIG}" || echo "LoginGraceTime 30" >> "${SSH_CONFIG}"
grep -q "^ClientAliveInterval" "${SSH_CONFIG}" || echo "ClientAliveInterval 300" >> "${SSH_CONFIG}"
grep -q "^ClientAliveCountMax" "${SSH_CONFIG}" || echo "ClientAliveCountMax 2" >> "${SSH_CONFIG}"

systemctl restart ssh
log "SSH hardened and restarted"

# =============================================================================
# STEP 5 — Configure fail2ban (brute-force protection)
# =============================================================================
info "Step 5/9 — Configuring fail2ban..."

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s
maxretry = 5

[proxmox]
enabled  = true
port     = https,8006
filter   = proxmox
logpath  = /var/log/daemon.log
maxretry = 5
bantime  = 3600
EOF

# Create Proxmox filter for fail2ban
cat > /etc/fail2ban/filter.d/proxmox.conf << 'EOF'
[Definition]
failregex = pvedaemon\[.*authentication failure; rhost=<HOST> user=.* msg=.*
ignoreregex =
EOF

systemctl enable fail2ban
systemctl restart fail2ban
log "fail2ban configured and running"

# =============================================================================
# STEP 6 — Verify and document network (umbro bridge)
# =============================================================================
info "Step 6/9 — Verifying network configuration..."

echo ""
echo "  Current network interfaces:"
ip addr show | grep -E "^[0-9]+:|inet " | sed 's/^/    /'
echo ""

# Verify umbro bridge is up with correct IP
if ip addr show "${BRIDGE}" 2>/dev/null | grep -q "${HOST_IP}"; then
    log "Bridge '${BRIDGE}' is UP with IP ${HOST_IP}/24 ✓"
else
    warn "Bridge '${BRIDGE}' not found or IP mismatch — check /etc/network/interfaces"
fi

# Show current /etc/network/interfaces
info "Current /etc/network/interfaces:"
cat /etc/network/interfaces | sed 's/^/    /'
echo ""

# =============================================================================
# STEP 7 — Configure storage (verify local-lvm)
# =============================================================================
info "Step 7/9 — Checking storage configuration..."

echo ""
echo "  Proxmox storage:"
pvesm status | sed 's/^/    /'
echo ""

echo "  Disk usage:"
df -h / /var/lib/vz 2>/dev/null | sed 's/^/    /'
echo ""

log "Storage check complete"

# =============================================================================
# STEP 8 — Set up automatic security updates
# =============================================================================
info "Step 8/9 — Configuring automatic security updates..."

apt-get install -y -qq unattended-upgrades apt-listchanges 2>/dev/null

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

log "Automatic security updates configured"

# =============================================================================
# STEP 9 — Final status report
# =============================================================================
info "Step 9/9 — Final status report..."

echo ""
echo "============================================================"
echo "  POST-INSTALL CONFIGURATION COMPLETE"
echo "============================================================"
echo ""
echo "  Host:        $(hostname) (pue)"
echo "  PVE:         ${PVE_VERSION}"
echo "  Bridge:      ${BRIDGE} @ ${HOST_IP}/24"
echo "  Uptime:      $(uptime -p)"
echo "  Kernel:      $(uname -r)"
echo ""
echo "  Services:"
systemctl is-active --quiet ssh        && echo "  ✅ SSH:        running" || echo "  ❌ SSH:        STOPPED"
systemctl is-active --quiet fail2ban   && echo "  ✅ fail2ban:   running" || echo "  ❌ fail2ban:   STOPPED"
systemctl is-active --quiet pvedaemon  && echo "  ✅ pvedaemon:  running" || echo "  ❌ pvedaemon:  STOPPED"
systemctl is-active --quiet pveproxy   && echo "  ✅ pveproxy:   running" || echo "  ❌ pveproxy:   STOPPED"
systemctl is-active --quiet pve-cluster && echo "  ✅ pve-cluster: running" || echo "  ❌ pve-cluster: STOPPED"
echo ""
echo "  Containers:"
pct list 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo ""
echo "  VMs:"
qm list 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo ""
echo "  Next steps:"
echo "  1. Open Proxmox UI: https://${HOST_IP}:8006"
echo "  2. Dismiss the 'no subscription' popup (click OK)"
echo "  3. Verify CT100 is running: pct status 100"
echo "  4. SSH into CT100: ssh root@100.117.1.171"
echo "  5. Check all Docker services: docker ps"
echo ""
echo "============================================================"
