#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APPLY_WIFI_ORDER="${APPLY_WIFI_ORDER:-0}"
PREFERRED_WIFI_SSIDS="${PREFERRED_WIFI_SSIDS:-Verizon,Gigstreem,Verizon Line,Dual-SIM Hotspot}"
OPEN_TAB_GROUPS="${OPEN_TAB_GROUPS:-0}"

log() {
  echo "[REMOTE-SETUP] $1"
}

log "Starting macOS remote-work bootstrap..."

# 1) DisplayLink for portable USB displays
if [ -d "/Applications/DisplayLink Manager.app" ]; then
  log "DisplayLink Manager installed"
  open -a "DisplayLink Manager" || true
else
  log "DisplayLink Manager missing. Install with: brew install --cask displaylink"
fi

# 2) Bookmarks in Chrome/Safari
if [ -f "$REPO_DIR/install_bookmarks.py" ]; then
  log "Applying Chrome + Safari bookmarks"
  python3 "$REPO_DIR/install_bookmarks.py" || true
else
  log "install_bookmarks.py not found"
fi

# 2.5) Optional tab workspace launch
if [ "$OPEN_TAB_GROUPS" = "1" ]; then
  if [ -f "$REPO_DIR/scripts/open_work_tab_groups_macos.py" ]; then
    log "Opening Chrome tab workspace groups"
    python3 "$REPO_DIR/scripts/open_work_tab_groups_macos.py" chrome || true
  else
    log "Tab group launcher not found"
  fi
else
  log "Tab groups not auto-opened. To enable: OPEN_TAB_GROUPS=1 bash scripts/remote_work_bootstrap_macos.sh"
fi

# 3) Optional Wi-Fi preference ordering
WIFI_DEVICE="$(networksetup -listallhardwareports | awk '/Wi-Fi|AirPort/{getline; gsub("Device: ", ""); print; exit}')"
if [ -z "$WIFI_DEVICE" ]; then
  log "Could not detect Wi-Fi device"
  exit 0
fi

log "Detected Wi-Fi device: $WIFI_DEVICE"
IFS=',' read -r -a ssids <<< "$PREFERRED_WIFI_SSIDS"

if [ "$APPLY_WIFI_ORDER" = "1" ]; then
  idx=0
  for ssid in "${ssids[@]}"; do
    ssid_trimmed="$(echo "$ssid" | sed 's/^ *//;s/ *$//')"
    [ -z "$ssid_trimmed" ] && continue
    networksetup -addpreferredwirelessnetworkatindex "$WIFI_DEVICE" "$ssid_trimmed" "$idx" || true
    idx=$((idx + 1))
  done
  log "Applied preferred Wi-Fi order"
else
  log "Dry run only for Wi-Fi ordering."
  log "To apply, run: APPLY_WIFI_ORDER=1 bash scripts/remote_work_bootstrap_macos.sh"
  log "SSID order: $PREFERRED_WIFI_SSIDS"
fi

log "Bootstrap complete"
