#!/usr/bin/env python3
"""
homelab_health_telegram.py
==========================
Homelab Health Monitor — sends Telegram status updates.
Similar to the 404 Archive bot pattern but for infrastructure.

Checks all Docker containers, key service endpoints, disk/memory,
and sends a formatted Telegram digest.

Usage:
    python3 scripts/homelab_health_telegram.py              # full health check + Telegram
    python3 scripts/homelab_health_telegram.py --dry-run    # print report, don't send
    python3 scripts/homelab_health_telegram.py --quick      # just container status

Cron (add to CT100 crontab):
    # Health check every 6 hours
    0 */6 * * * cd /opt/darrian-budget && python3 scripts/homelab_health_telegram.py >> /var/log/homelab-health.log 2>&1

    # Quick container check every hour
    0 * * * * cd /opt/darrian-budget && python3 scripts/homelab_health_telegram.py --quick >> /var/log/homelab-health.log 2>&1
"""

import sys
import os
import subprocess
import argparse
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── Telegram helper ───────────────────────────────────────────────────────────

def _get_telegram_creds() -> tuple:
    """Get Telegram creds from env vars first, then DB fallback."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        try:
            from utils.db import get_setting, init_db
            init_db()
            token = token or get_setting("telegram_bot_token") or ""
            chat_id = chat_id or get_setting("telegram_chat_id") or ""
        except Exception:
            pass

    return token, chat_id


def send_telegram(message: str, dry_run: bool = False) -> bool:
    """Send a Telegram message. Returns True on success."""
    if dry_run:
        print(f"\n[DRY RUN] Would send Telegram:\n{message}\n")
        return True

    token, chat_id = _get_telegram_creds()
    if not token or not chat_id:
        print("⚠️  Telegram not configured — set telegram_bot_token + telegram_chat_id in DB")
        return False

    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return True
        print(f"Telegram error {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


# ── System checks ─────────────────────────────────────────────────────────────

def _run(cmd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def check_docker_containers() -> list[dict]:
    """Get status of all Docker containers."""
    raw = _run('docker ps -a --format "{{.Names}}|{{.Status}}"')
    containers = []
    for line in raw.split("\n"):
        if "|" not in line:
            continue
        name, status = line.split("|", 1)
        healthy = "healthy" in status.lower() or ("up" in status.lower() and "unhealthy" not in status.lower())
        containers.append({"name": name, "status": status, "healthy": healthy})
    return containers


def check_endpoints() -> list[dict]:
    """Check key service HTTP endpoints."""
    endpoints = [
        ("Budget App", "http://localhost:8501", 200),
        ("AURA", "http://localhost:8000/health", 200),
        ("Grafana", "http://localhost:3000", [200, 302, 400]),
        ("Immich", "http://localhost:2283", 200),
        ("Portainer", "http://localhost:9000", 200),
    ]
    results = []
    for name, url, expected in endpoints:
        try:
            code = _run(f'curl -s -o /dev/null -w "%{{http_code}}" --max-time 5 {url}')
            code_int = int(code) if code.isdigit() else 0
            if isinstance(expected, list):
                ok = code_int in expected
            else:
                ok = code_int == expected
            results.append({"name": name, "url": url, "code": code_int, "ok": ok})
        except Exception:
            results.append({"name": name, "url": url, "code": 0, "ok": False})
    return results


def check_disk() -> dict:
    """Check disk usage on root partition."""
    raw = _run("df -h / | tail -1")
    parts = raw.split()
    if len(parts) >= 5:
        return {"total": parts[1], "used": parts[2], "avail": parts[3], "pct": parts[4]}
    return {"total": "?", "used": "?", "avail": "?", "pct": "?"}


def check_memory() -> dict:
    """Check memory usage."""
    raw = _run("free -h | grep Mem")
    parts = raw.split()
    if len(parts) >= 4:
        return {"total": parts[1], "used": parts[2], "free": parts[3]}
    return {"total": "?", "used": "?", "free": "?"}


def check_uptime() -> str:
    return _run("uptime -p") or _run("uptime")


def check_cron_health() -> list[dict]:
    """Check if key cron log files have recent entries."""
    logs = [
        ("Sched Agents", "/var/log/sched-agents.log"),
        ("Overnight Dev", "/var/log/overnight-dev.log"),
        ("Sole Alert", "/var/log/sole-alert.log"),
    ]
    results = []
    for name, path in logs:
        last_line = _run(f"tail -1 {path} 2>/dev/null")
        size = _run(f"stat -c%s {path} 2>/dev/null") or "0"
        results.append({
            "name": name,
            "path": path,
            "last_line": last_line[:80] if last_line else "(empty)",
            "size": size,
        })
    return results


# ── Report builders ───────────────────────────────────────────────────────────

def build_quick_report() -> str:
    """Quick container status check."""
    containers = check_docker_containers()
    ts = datetime.now().strftime("%b %d %H:%M")

    up = sum(1 for c in containers if c["healthy"])
    down = len(containers) - up

    lines = [f"🏠 <b>Homelab Quick Check</b> — {ts}\n"]

    if down == 0:
        lines.append(f"✅ All {up} containers healthy\n")
    else:
        lines.append(f"⚠️ {down} container(s) need attention\n")

    for c in containers:
        icon = "✅" if c["healthy"] else "❌"
        lines.append(f"  {icon} {c['name']}")

    return "\n".join(lines)


def build_full_report() -> str:
    """Full health report with endpoints, disk, memory, crons."""
    ts = datetime.now().strftime("%b %d, %Y %H:%M")
    containers = check_docker_containers()
    endpoints = check_endpoints()
    disk = check_disk()
    mem = check_memory()
    uptime = check_uptime()
    crons = check_cron_health()

    up = sum(1 for c in containers if c["healthy"])
    down = len(containers) - up
    ep_ok = sum(1 for e in endpoints if e["ok"])
    ep_fail = len(endpoints) - ep_ok

    # Overall status
    if down == 0 and ep_fail == 0:
        header = "🟢 <b>HOMELAB HEALTHY</b>"
    elif down <= 2 and ep_fail <= 1:
        header = "🟡 <b>HOMELAB DEGRADED</b>"
    else:
        header = "🔴 <b>HOMELAB DOWN</b>"

    lines = [
        f"{header} — {ts}\n",
        f"<b>📦 Containers:</b> {up}/{len(containers)} healthy",
    ]

    # Show unhealthy containers
    unhealthy = [c for c in containers if not c["healthy"]]
    if unhealthy:
        for c in unhealthy:
            lines.append(f"  ❌ {c['name']}: {c['status'][:40]}")

    lines.append(f"\n<b>🌐 Endpoints:</b> {ep_ok}/{len(endpoints)} responding")
    for e in endpoints:
        icon = "✅" if e["ok"] else "❌"
        lines.append(f"  {icon} {e['name']} → HTTP {e['code']}")

    lines.append(f"\n<b>💾 Disk:</b> {disk['used']}/{disk['total']} ({disk['pct']})")
    lines.append(f"<b>🧠 Memory:</b> {mem['used']}/{mem['total']} used")
    lines.append(f"<b>⏱ Uptime:</b> {uptime}")

    lines.append(f"\n<b>⏰ Cron Jobs:</b>")
    for cron in crons:
        lines.append(f"  📋 {cron['name']}: {cron['last_line'][:50]}")

    lines.append(f"\n🔗 Dashboard: http://100.95.125.112:8501")
    lines.append(f"🔗 Portainer: http://100.95.125.112:9000")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Homelab Health Monitor + Telegram")
    parser.add_argument("--dry-run", action="store_true", help="Print report, don't send Telegram")
    parser.add_argument("--quick", action="store_true", help="Quick container check only")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] Homelab health check starting (quick={args.quick}, dry_run={args.dry_run})")

    if args.quick:
        report = build_quick_report()
        # Only send quick alerts if something is down
        containers = check_docker_containers()
        down = sum(1 for c in containers if not c["healthy"])
        if down > 0 or args.dry_run:
            send_telegram(report, dry_run=args.dry_run)
        else:
            print(f"[{ts}] All containers healthy — skipping Telegram (no alert needed)")
    else:
        report = build_full_report()
        send_telegram(report, dry_run=args.dry_run)

    print(report)
    print(f"\n[{ts}] Health check complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
