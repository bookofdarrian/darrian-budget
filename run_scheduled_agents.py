#!/usr/bin/env python3
"""
run_scheduled_agents.py
=======================
Scheduled Agent Task Runner — Peach State Savings
Run this script from a cron job every 15 minutes on CT100.

What it does:
  1. Connects to the production DB (SQLite or Postgres)
  2. Finds every row in agent_scheduled_tasks where enabled=1 AND next_run <= now()
  3. Dispatches each due task to the appropriate handler function
  4. Updates last_run, run_count, and next_run for each task
  5. Logs everything to agent_log (visible in the Agent Dashboard UI)

Cron setup (on CT100):
  # Every 15 minutes check for due tasks
  echo "*/15 * * * * root cd /app && python3 run_scheduled_agents.py >> /var/log/sched-agents.log 2>&1" >> /etc/crontab

  # OR, to also run the overnight BACKLOG agent at 11 PM:
  echo "0 23 * * * root bash /root/start-agents.sh >> /var/log/overnight-dev.log 2>&1" >> /etc/crontab

Usage:
  python3 run_scheduled_agents.py            # normal run
  python3 run_scheduled_agents.py --dry-run  # show what would run, don't commit
  python3 run_scheduled_agents.py --verbose  # extra logging
  python3 run_scheduled_agents.py --force "Weekly Spending Digest"  # run one task by name right now
"""

import sys
import os
import subprocess
import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# ── Project root ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, get_setting, init_db


# ══════════════════════════════════════════════════════════════════════════════
# ── Config ────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

LOG_FILE = Path("/var/log/sched-agents.log")
VENV_PYTHON = str(PROJECT_ROOT / "venv" / "bin" / "python3")
if not Path(VENV_PYTHON).exists():
    VENV_PYTHON = sys.executable

# ── Colours (only when stdout is a terminal) ─────────────────────────────────
_IS_TTY = sys.stdout.isatty()
def _g(s): return f"\033[0;32m{s}\033[0m" if _IS_TTY else s
def _y(s): return f"\033[0;33m{s}\033[0m" if _IS_TTY else s
def _r(s): return f"\033[0;31m{s}\033[0m" if _IS_TTY else s
def _b(s): return f"\033[0;34m{s}\033[0m" if _IS_TTY else s


# ══════════════════════════════════════════════════════════════════════════════
# ── Logging ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _log(level: str, message: str, verbose: bool = False, run_id: int | None = None) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {"INFO": "ℹ️ ", "SUCCESS": "✅", "WARNING": "⚠️ ", "ERROR": "❌", "NOTIFY": "📣"}
    icon = icons.get(level.upper(), "•")
    print(f"[{ts}] {icon} {level:<8} {message}")

    # Write to agent_log table so it shows in the Agent Dashboard UI
    try:
        conn = get_conn()
        ph = "%s" if USE_POSTGRES else "?"
        db_exec(conn, f"""
            INSERT INTO agent_log (run_id, level, message)
            VALUES ({ph}, {ph}, {ph})
        """, (run_id, level.upper(), message))
        conn.commit()
        conn.close()
    except Exception:
        pass  # Don't crash the runner if logging fails


# ══════════════════════════════════════════════════════════════════════════════
# ── Next-run calculator ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _calc_next_run(schedule_type: str, schedule_day: int, schedule_hour: int) -> str:
    """Pure Python — no Streamlit dependency."""
    now = datetime.now()
    target = now.replace(minute=0, second=0, microsecond=0, hour=schedule_hour)

    if schedule_type == "daily":
        if target <= now:
            target += timedelta(days=1)

    elif schedule_type == "weekly":
        days_ahead = schedule_day - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        candidate = (now + timedelta(days=days_ahead)).replace(
            hour=schedule_hour, minute=0, second=0, microsecond=0
        )
        if candidate <= now:
            candidate += timedelta(weeks=1)
        target = candidate

    elif schedule_type == "monthly":
        try:
            candidate = now.replace(
                day=schedule_day, hour=schedule_hour, minute=0, second=0, microsecond=0
            )
        except ValueError:
            candidate = now.replace(
                day=28, hour=schedule_hour, minute=0, second=0, microsecond=0
            )
        if candidate <= now:
            if now.month == 12:
                candidate = candidate.replace(year=now.year + 1, month=1)
            else:
                try:
                    candidate = candidate.replace(month=now.month + 1)
                except ValueError:
                    candidate = candidate.replace(month=now.month + 1, day=28)
        target = candidate

    return target.strftime("%Y-%m-%d %H:%M:%S")


# ══════════════════════════════════════════════════════════════════════════════
# ── Task handlers ─────────────────────────────────────────────────────────────
# Each handler receives the task dict and returns (success: bool, message: str)
# ══════════════════════════════════════════════════════════════════════════════

def _run_subprocess(script_path: str, args: list[str] | None = None, timeout: int = 300) -> tuple[bool, str]:
    """Run a Python script in the venv and return (success, output)."""
    cmd = [VENV_PYTHON, script_path] + (args or [])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            return True, result.stdout.strip()[:500]
        return False, (result.stderr or result.stdout).strip()[:500]
    except subprocess.TimeoutExpired:
        return False, f"Timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


def _handler_weekly_spending_digest(task: dict) -> tuple[bool, str]:
    """Generate + email the weekly spending digest."""
    script = PROJECT_ROOT / "pages" / "56_weekly_spending_digest.py"
    if not script.exists():
        return False, "pages/56_weekly_spending_digest.py not found"
    # The digest page can be called with a trigger flag
    ok, msg = _run_subprocess(str(script), ["--send-now"])
    if not ok:
        # Try calling the digest directly via a utility module if available
        return False, f"Could not auto-send digest: {msg}. Open the app and click Send manually."
    return ok, msg


def _handler_daily_price_alert(task: dict) -> tuple[bool, str]:
    """Refresh sneaker price alerts via sole_alert_bot scanner."""
    scanner = PROJECT_ROOT / "sole_alert_bot" / "scan_arb.py"
    ebay_search = PROJECT_ROOT / "sole_alert_bot" / "ebay_search.py"
    if scanner.exists():
        return _run_subprocess(str(scanner))
    elif ebay_search.exists():
        return _run_subprocess(str(ebay_search))
    return False, "sole_alert_bot scanner not found — ensure sole_alert_bot/ scripts are in place"


def _handler_monthly_financial_report(task: dict) -> tuple[bool, str]:
    """Trigger the monthly financial email report."""
    script = PROJECT_ROOT / "pages" / "36_monthly_financial_email_report.py"
    if not script.exists():
        return False, "pages/36_monthly_financial_email_report.py not found"
    ok, msg = _run_subprocess(str(script), ["--send-now"])
    if not ok:
        return False, f"Could not auto-send report: {msg}. Open the app and click Send manually."
    return ok, msg


def _handler_stale_inventory_scan(task: dict) -> tuple[bool, str]:
    """
    SoleOps: Scan all inventory for pairs 14+ days old.
    Generates Claude markdown strategy and sends Telegram digest.
    """
    try:
        from datetime import datetime as _dt, date as _date
        import requests as _req

        conn = get_conn()
        ph = "%s" if USE_POSTGRES else "?"
        cur = conn.execute("""
            SELECT id, shoe_name, size, cost_basis, listed_date, listed_price, listed_platform
            FROM soleops_inventory
            WHERE status = 'inventory'
            ORDER BY listed_date ASC
        """)
        rows = cur.fetchall()
        conn.close()

        stale = []
        for r in rows:
            listed_date_val = r[4]
            if not listed_date_val:
                continue
            try:
                if isinstance(listed_date_val, str):
                    ld = _dt.strptime(str(listed_date_val)[:10], "%Y-%m-%d").date()
                else:
                    ld = listed_date_val
                days = max(0, (_date.today() - ld).days)
            except Exception:
                continue

            if days < 14:
                continue

            listed_price = float(r[5]) if r[5] else 0.0
            cost_basis   = float(r[3]) if r[3] else 0.0

            if days >= 30:
                drop_pct, tier_label = 0.20, "⚫ Critical"
            elif days >= 21:
                drop_pct, tier_label = 0.15, "🔴 Stale"
            elif days >= 14:
                drop_pct, tier_label = 0.10, "🟠 Aging"
            else:
                drop_pct, tier_label = 0.05, "🟡 Warm"

            sugg_price = round(listed_price * (1 - drop_pct), 2) if listed_price > 0 else 0.0
            stale.append({
                "shoe_name": r[1], "size": r[2], "cost_basis": cost_basis,
                "listed_price": listed_price, "listed_platform": r[6] or "Unknown",
                "days_listed": days, "suggested_price": sugg_price,
                "tier_label": tier_label,
            })

        if not stale:
            return True, "Stale scan: no pairs 14+ days old — all inventory is fresh!"

        total_at_risk = sum(i["listed_price"] - i["cost_basis"] for i in stale if i["listed_price"])
        lines = [
            "⏰ <b>SOLEOPS WEEKLY STALE SCAN</b>",
            f"📊 {len(stale)} pairs need attention\n",
        ]
        for item in stale[:8]:
            lines.append(
                f"{item['tier_label']} <b>{item['shoe_name']}</b> Sz {item['size']} — "
                f"{item['days_listed']}d → drop to <b>${item['suggested_price']:.0f}</b>"
            )
        if len(stale) > 8:
            lines.append(f"...and {len(stale) - 8} more pairs")
        lines.append(f"\n💰 Total $ at risk: ${total_at_risk:,.0f}")
        lines.append("\n📱 Open SoleOps → peachstatesavings.com")

        token   = get_setting("telegram_bot_token")
        chat_id = get_setting("telegram_chat_id")
        if token and chat_id:
            r = _req.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": "\n".join(lines), "parse_mode": "HTML"},
                timeout=10,
            )
            if r.status_code == 200:
                return True, f"Stale scan: {len(stale)} pairs alerted via Telegram."
            return False, f"Telegram error {r.status_code}"
        return True, f"Stale scan: {len(stale)} stale pairs found (Telegram not configured)."
    except Exception as e:
        return False, f"Stale inventory scan error: {str(e)}"


def _handler_weekly_reseller_report(task: dict) -> tuple[bool, str]:
    """
    Generate SoleOps weekly reseller report.
    Pulls last 7 days of sold inventory + current stale pairs.
    Sends Claude-generated narrative via Telegram + optional email.
    """
    try:
        from datetime import datetime as _dt, date as _date, timedelta as _td
        import requests as _req

        today = _date.today()
        week_ago = today - _td(days=7)

        conn = get_conn()
        # Last 7 days sold
        cur = conn.execute("""
            SELECT shoe_name, size, sell_price, cost_basis, sold_platform, sold_date
            FROM soleops_inventory
            WHERE status = 'sold' AND sold_date >= ?
            ORDER BY sold_date DESC
        """, (str(week_ago),)) if not USE_POSTGRES else conn.execute("""
            SELECT shoe_name, size, sell_price, cost_basis, sold_platform, sold_date
            FROM soleops_inventory
            WHERE status = 'sold' AND sold_date >= %s
            ORDER BY sold_date DESC
        """, (str(week_ago),))
        sold_rows = cur.fetchall()

        # Current inventory count
        cur2 = conn.execute("SELECT COUNT(*) FROM soleops_inventory WHERE status = 'inventory'")
        inv_count = cur2.fetchone()[0]

        # Stale pairs
        cur3 = conn.execute("""
            SELECT shoe_name, size, listed_date, listed_price, listed_platform
            FROM soleops_inventory
            WHERE status = 'inventory' AND listed_date IS NOT NULL
        """)
        inv_rows = cur3.fetchall()
        conn.close()

        stale_count = 0
        for r in inv_rows:
            try:
                ld = _dt.strptime(str(r[2])[:10], "%Y-%m-%d").date()
                if (today - ld).days >= 14:
                    stale_count += 1
            except Exception:
                pass

        # P&L summary
        pairs_sold = len(sold_rows)
        gross_rev  = sum(float(r[2]) if r[2] else 0 for r in sold_rows)
        total_cogs = sum(float(r[3]) if r[3] else 0 for r in sold_rows)
        net_profit = gross_rev - total_cogs - (gross_rev * 0.12)

        # Platform breakdown
        plat_counts: dict = {}
        for r in sold_rows:
            p = r[4] or "Unknown"
            plat_counts[p] = plat_counts.get(p, 0) + 1
        best_plat = max(plat_counts, key=plat_counts.get) if plat_counts else "—"

        # Build Telegram message
        sold_lines = "\n".join([
            f"  • {r[0]} Sz {r[1]} — ${float(r[2]) if r[2] else 0:.0f} on {r[4] or '?'}"
            for r in sold_rows[:5]
        ]) or "  None this week"

        msg = (
            f"📊 <b>SOLEOPS WEEKLY REPORT</b> — {today.strftime('%b %d, %Y')}\n\n"
            f"<b>🔢 Summary</b>\n"
            f"  Pairs sold: {pairs_sold}\n"
            f"  Gross revenue: ${gross_rev:.0f}\n"
            f"  Net profit (est.): ${net_profit:.0f}\n"
            f"  Best platform: {best_plat}\n\n"
            f"<b>📦 Inventory</b>\n"
            f"  Total pairs: {inv_count}\n"
            f"  Stale (14d+): {stale_count}\n\n"
            f"<b>✅ Sold This Week</b>\n{sold_lines}\n\n"
            f"📱 Open SoleOps → peachstatesavings.com"
        )

        token   = get_setting("telegram_bot_token")
        chat_id = get_setting("telegram_chat_id")
        if token and chat_id:
            r = _req.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
                timeout=10,
            )
            if r.status_code == 200:
                return True, f"Weekly reseller report sent: {pairs_sold} pairs sold, ${net_profit:.0f} net profit."
            return False, f"Telegram error {r.status_code}"
        return True, (
            f"Weekly report generated: {pairs_sold} pairs sold this week, "
            f"${net_profit:.0f} net profit. "
            "Configure Telegram to auto-send."
        )
    except Exception as e:
        return False, f"Weekly reseller report error: {str(e)}"


def _handler_generic(task: dict) -> tuple[bool, str]:
    """
    Fallback handler for custom tasks. Logs the task as due and
    notifies via agent_log so it shows in the dashboard.
    The overnight BACKLOG agent can then pick it up.
    """
    return True, (
        f"Custom task '{task['task_name']}' was due. "
        f"Backlog item: {task.get('backlog_item', 'N/A')}. "
        f"Add a dedicated handler in run_scheduled_agents.py to auto-execute."
    )


# ── Task handler registry ─────────────────────────────────────────────────────
# Maps task_name (case-insensitive, partial match) → handler function
TASK_HANDLERS: list[tuple[str, callable]] = [
    ("weekly spending digest",          _handler_weekly_spending_digest),
    ("daily price alert",               _handler_daily_price_alert),
    ("monthly financial email report",  _handler_monthly_financial_report),
    ("stale inventory",                 _handler_stale_inventory_scan),
    ("weekly reseller report",          _handler_weekly_reseller_report),
]


def _get_handler(task_name: str) -> callable:
    name_lower = task_name.lower()
    for key, fn in TASK_HANDLERS:
        if key in name_lower:
            return fn
    return _handler_generic


# ══════════════════════════════════════════════════════════════════════════════
# ── DB helpers ────────────────────────────────────────────────────────════════
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_tables() -> None:
    """Create agent_scheduled_tasks, agent_runs, agent_log if they don't exist."""
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_scheduled_tasks (
                id SERIAL PRIMARY KEY, task_name TEXT NOT NULL,
                description TEXT DEFAULT '', backlog_item TEXT DEFAULT '',
                schedule_type TEXT DEFAULT 'weekly', schedule_day INTEGER DEFAULT 1,
                schedule_hour INTEGER DEFAULT 23, last_run TEXT, next_run TEXT,
                enabled BOOLEAN DEFAULT TRUE, run_count INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'darrian',
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )""")
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id SERIAL PRIMARY KEY, feature_name TEXT DEFAULT '',
                display_name TEXT DEFAULT '', status TEXT DEFAULT 'running',
                pr_url TEXT DEFAULT '', page_file TEXT DEFAULT '',
                started_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                ended_at TEXT DEFAULT NULL, error_msg TEXT DEFAULT '')""")
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_log (
                id SERIAL PRIMARY KEY, run_id INTEGER DEFAULT NULL,
                level TEXT DEFAULT 'INFO', message TEXT NOT NULL,
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')))""")
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, task_name TEXT NOT NULL,
                description TEXT DEFAULT '', backlog_item TEXT DEFAULT '',
                schedule_type TEXT DEFAULT 'weekly', schedule_day INTEGER DEFAULT 1,
                schedule_hour INTEGER DEFAULT 23, last_run TEXT, next_run TEXT,
                enabled INTEGER DEFAULT 1, run_count INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'darrian',
                created_at TEXT DEFAULT (datetime('now')))""")
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, feature_name TEXT DEFAULT '',
                display_name TEXT DEFAULT '', status TEXT DEFAULT 'running',
                pr_url TEXT DEFAULT '', page_file TEXT DEFAULT '',
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT DEFAULT NULL, error_msg TEXT DEFAULT '')""")
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER DEFAULT NULL,
                level TEXT DEFAULT 'INFO', message TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')))""")
    conn.commit()
    conn.close()


def _get_due_tasks() -> list[dict]:
    """Return all enabled tasks whose next_run is in the past."""
    conn = get_conn()
    if USE_POSTGRES:
        c = conn.execute("""
            SELECT * FROM agent_scheduled_tasks
            WHERE enabled = TRUE
              AND next_run IS NOT NULL
              AND next_run::timestamp <= NOW()
            ORDER BY next_run ASC
        """)
    else:
        c = conn.execute("""
            SELECT * FROM agent_scheduled_tasks
            WHERE enabled = 1
              AND next_run IS NOT NULL
              AND next_run <= datetime('now')
            ORDER BY next_run ASC
        """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _mark_task_ran(task_id: int, schedule_type: str, schedule_day: int, schedule_hour: int) -> None:
    """Update last_run, increment run_count, and set next_run."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    next_run = _calc_next_run(schedule_type, schedule_day, schedule_hour)
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"""
        UPDATE agent_scheduled_tasks
        SET last_run = {ph}, run_count = run_count + 1, next_run = {ph}
        WHERE id = {ph}
    """, (now, next_run, task_id))
    conn.commit()
    conn.close()


def _create_agent_run(task_name: str) -> int:
    """Insert a row into agent_runs for this scheduled task and return the run_id."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        c = db_exec(conn, f"""
            INSERT INTO agent_runs (feature_name, display_name, status)
            VALUES ({ph}, {ph}, 'running')
            RETURNING id
        """, (f"scheduled:{task_name}", task_name))
        run_id = c.fetchone()[0]
    else:
        db_exec(conn, f"""
            INSERT INTO agent_runs (feature_name, display_name, status)
            VALUES ({ph}, {ph}, 'running')
        """, (f"scheduled:{task_name}", task_name))
        run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return run_id


def _close_agent_run(run_id: int, success: bool, error_msg: str = "") -> None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "success" if success else "failed"
    db_exec(conn, f"""
        UPDATE agent_runs
        SET status = {ph}, ended_at = {ph}, error_msg = {ph}
        WHERE id = {ph}
    """, (status, now, error_msg[:500], run_id))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ── Main ──────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def main(dry_run: bool = False, verbose: bool = False, force_task: str | None = None) -> int:
    init_db()           # ensure core app tables exist
    _ensure_tables()    # ensure agent-specific tables exist

    start_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(_b(f"\n{'='*60}"))
    print(_b(f"⏰  Scheduled Agent Runner — {start_ts}"))
    print(_b(f"   dry_run={dry_run}  verbose={verbose}  force={force_task!r}"))
    print(_b(f"{'='*60}\n"))

    # ── Find due tasks ────────────────────────────────────────
    if force_task:
        # Load all tasks and filter by name
        conn = get_conn()
        rows = conn.execute("SELECT * FROM agent_scheduled_tasks").fetchall()
        conn.close()
        all_tasks = [dict(r) for r in rows]
        due_tasks = [t for t in all_tasks if force_task.lower() in t["task_name"].lower()]
        if not due_tasks:
            print(_r(f"No task matching '{force_task}' found."))
            return 1
    else:
        due_tasks = _get_due_tasks()

    if not due_tasks:
        print(_g("✅  No tasks due right now. Nothing to do."))
        return 0

    print(f"📋  Found {len(due_tasks)} task(s) due:\n")
    for t in due_tasks:
        print(f"   → {t['task_name']} | schedule: {t['schedule_type']} | "
              f"next_run was: {(t.get('next_run') or 'now')[:16]}")
    print()

    # ── Run each due task ─────────────────────────────────────
    results: list[tuple[str, bool, str]] = []

    for task in due_tasks:
        task_name = task["task_name"]
        handler = _get_handler(task_name)

        print(_b(f"▶️  Running: {task_name}"))
        if verbose:
            print(f"   Handler: {handler.__name__}")
            print(f"   Backlog: {task.get('backlog_item', 'N/A')}")

        if dry_run:
            print(_y(f"   [DRY RUN] Would execute {handler.__name__}"))
            results.append((task_name, True, "dry-run"))
            continue

        # Create agent_run record
        run_id: int | None = None
        try:
            run_id = _create_agent_run(task_name)
        except Exception as e:
            if verbose:
                print(_y(f"   Could not create agent_run record: {e}"))

        # Execute handler
        try:
            success, message = handler(task)
        except Exception as e:
            success, message = False, f"Unhandled exception: {e}"

        # Log result
        level = "SUCCESS" if success else "ERROR"
        _log(level, f"[{task_name}] {message}", verbose=verbose, run_id=run_id)

        # Close agent_run record
        if run_id is not None:
            _close_agent_run(run_id, success, "" if success else message)

        # Update task timestamps
        _mark_task_ran(
            task["id"],
            task.get("schedule_type", "weekly"),
            task.get("schedule_day", 0),
            task.get("schedule_hour", 8),
        )

        results.append((task_name, success, message))

        icon = _g("✅") if success else _r("❌")
        print(f"   {icon} {'Done' if success else 'FAILED'}: {message[:120]}\n")

    # ── Summary ───────────────────────────────────────────────
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed

    print(_b(f"\n{'='*60}"))
    print(_b(f"📊  Summary: {passed} succeeded, {failed} failed"))
    if failed:
        for name, ok, msg in results:
            if not ok:
                print(_r(f"   ❌ {name}: {msg[:80]}"))
    print(_b(f"{'='*60}\n"))

    return 0 if failed == 0 else 1


# ══════════════════════════════════════════════════════════════════════════════
# ── CLI entry point ───────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Peach State Savings — Scheduled Agent Task Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check what's due and run it
  python3 run_scheduled_agents.py

  # See what would run without executing
  python3 run_scheduled_agents.py --dry-run

  # Run a specific task by name right now (ignores next_run)
  python3 run_scheduled_agents.py --force "Daily Price Alert Refresh"

  # Extra logging
  python3 run_scheduled_agents.py --verbose

Cron setup on CT100 (check every 15 min):
  echo "*/15 * * * * root cd /app && python3 run_scheduled_agents.py >> /var/log/sched-agents.log 2>&1" >> /etc/crontab
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would run, don't execute")
    parser.add_argument("--verbose", "-v", action="store_true", help="Extra output")
    parser.add_argument("--force", metavar="TASK_NAME", help="Force-run a task by name right now")
    args = parser.parse_args()

    sys.exit(main(dry_run=args.dry_run, verbose=args.verbose, force_task=args.force))
