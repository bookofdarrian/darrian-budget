#!/usr/bin/env bash
# Waits 30s after login for Chrome to be ready, then opens morning workspaces.
# Controlled by: ~/Library/LaunchAgents/com.bookofdarrian.work-tabs.plist

REPO_DIR="/Users/darriansingh/Downloads/darrian-budget"
LOG_FILE="$HOME/Library/Logs/work-tabs.log"

sleep 30

{
  echo "[$(date '+%F %T')] Opening morning work tab groups..."
  cd "$REPO_DIR" || exit 1
  /usr/bin/python3 scripts/open_work_tab_groups_macos.py chrome
  echo "[$(date '+%F %T')] Done."
} >> "$LOG_FILE" 2>&1
