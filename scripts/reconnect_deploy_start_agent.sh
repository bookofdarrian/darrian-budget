#!/usr/bin/env bash
# Quick reconnect script — run when homelab comes back online
# Usage: bash scripts/reconnect_deploy_start_agent.sh
set -euo pipefail

SERVER="root@100.95.125.112"
echo "🔄 Checking server connectivity..."

if ssh -o ConnectTimeout=10 "$SERVER" "echo 'SERVER ONLINE'" 2>/dev/null; then
  echo "✅ Server is online! Deploying and starting agent..."
  
  ssh "$SERVER" bash -s <<'EOF'
    cd /opt/darrian-budget
    git fetch origin main
    git reset --hard origin/main
    docker restart darrian-budget
    echo "✅ darrian-budget deployed"
    
    # Start the 4-hour autonomous sprint in background
    nohup bash scripts/autonomous_4hr_sprint_2026-04-03.sh > /var/log/autonomous-sprint-$(date +%Y%m%d).log 2>&1 &
    echo "🚀 Autonomous 4hr sprint started (PID: $!)"
    
    # Also deploy CC if directory exists
    if [ -d /opt/college-confused ]; then
      cp cc_app.py /opt/college-confused/cc_app.py
      cp pages/8*_cc_*.py pages/9*_cc_*.py pages/153_cc_*.py /opt/college-confused/pages/ 2>/dev/null || true
      cp cc_global_css.py /opt/college-confused/ 2>/dev/null || true
      systemctl restart college-confused 2>/dev/null || docker restart college-confused 2>/dev/null || true
      echo "✅ collegeconfused.org deployed"
    fi
EOF
  
  echo "🏁 All done! Agent is running in background."
else
  echo "❌ Server still offline. Try again later."
  echo "   Tip: Check if Proxmox/CT100 needs a restart at home."
fi
