"""
Agent Dashboard — Page 30
Live monitoring dashboard for the Overnight AI Dev System.
Shows agent status, live logs, backlog progress, build history,
and scheduled task management.
"""
import streamlit as st
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="🤖 Agent Dashboard — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",         icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",           icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",   icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


# ══════════════════════════════════════════════════════════════════════════════
# ── DB helpers ────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_tables() -> None:
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_scheduled_tasks (
                id SERIAL PRIMARY KEY,
                task_name       TEXT NOT NULL,
                description     TEXT DEFAULT '',
                backlog_item    TEXT DEFAULT '',
                schedule_type   TEXT DEFAULT 'weekly',
                schedule_day    INTEGER DEFAULT 1,
                schedule_hour   INTEGER DEFAULT 23,
                last_run        TEXT,
                next_run        TEXT,
                enabled         BOOLEAN DEFAULT TRUE,
                run_count       INTEGER DEFAULT 0,
                created_by      TEXT DEFAULT 'darrian',
                created_at      TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id SERIAL PRIMARY KEY,
                feature_name TEXT DEFAULT '',
                display_name TEXT DEFAULT '',
                status TEXT DEFAULT 'running',
                pr_url TEXT DEFAULT '',
                page_file TEXT DEFAULT '',
                started_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                ended_at TEXT DEFAULT NULL,
                error_msg TEXT DEFAULT ''
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_log (
                id SERIAL PRIMARY KEY,
                run_id INTEGER DEFAULT NULL,
                level TEXT DEFAULT 'INFO',
                message TEXT NOT NULL,
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name       TEXT NOT NULL,
                description     TEXT DEFAULT '',
                backlog_item    TEXT DEFAULT '',
                schedule_type   TEXT DEFAULT 'weekly',
                schedule_day    INTEGER DEFAULT 1,
                schedule_hour   INTEGER DEFAULT 23,
                last_run        TEXT,
                next_run        TEXT,
                enabled         INTEGER DEFAULT 1,
                run_count       INTEGER DEFAULT 0,
                created_by      TEXT DEFAULT 'darrian',
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT DEFAULT '',
                display_name TEXT DEFAULT '',
                status TEXT DEFAULT 'running',
                pr_url TEXT DEFAULT '',
                page_file TEXT DEFAULT '',
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT DEFAULT NULL,
                error_msg TEXT DEFAULT ''
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS agent_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER DEFAULT NULL,
                level TEXT DEFAULT 'INFO',
                message TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()
    conn.close()


# ── Scheduled task helpers ────────────────────────────────────────────────────

def _calc_next_run(schedule_type: str, schedule_day: int, schedule_hour: int) -> str:
    """
    Compute the next wall-clock run time (ISO string) for a scheduled task.
    schedule_type: 'daily' | 'weekly' | 'monthly'
    schedule_day:  for weekly → 0=Mon…6=Sun; for monthly → 1–28 (day of month)
    schedule_hour: 0–23
    """
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
            candidate = now.replace(day=schedule_day, hour=schedule_hour, minute=0, second=0, microsecond=0)
        except ValueError:
            candidate = now.replace(day=28, hour=schedule_hour, minute=0, second=0, microsecond=0)
        if candidate <= now:
            # advance one month
            if now.month == 12:
                candidate = candidate.replace(year=now.year + 1, month=1)
            else:
                try:
                    candidate = candidate.replace(month=now.month + 1)
                except ValueError:
                    candidate = candidate.replace(month=now.month + 1, day=28)
        target = candidate

    return target.strftime("%Y-%m-%d %H:%M:%S")


def _list_scheduled_tasks() -> list[dict]:
    conn = get_conn()
    rows = db_exec(conn, 
        "SELECT * FROM agent_scheduled_tasks ORDER BY next_run ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _create_scheduled_task(
    task_name: str,
    description: str,
    backlog_item: str,
    schedule_type: str,
    schedule_day: int,
    schedule_hour: int,
    created_by: str,
) -> None:
    next_run = _calc_next_run(schedule_type, schedule_day, schedule_hour)
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"""
        INSERT INTO agent_scheduled_tasks
            (task_name, description, backlog_item, schedule_type, schedule_day,
             schedule_hour, next_run, created_by)
        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
    """, (task_name, description, backlog_item, schedule_type, schedule_day,
          schedule_hour, next_run, created_by))
    conn.commit()
    conn.close()


def _toggle_scheduled_task(task_id: int, enabled: bool) -> None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    val = enabled if USE_POSTGRES else (1 if enabled else 0)
    db_exec(conn, f"UPDATE agent_scheduled_tasks SET enabled = {ph} WHERE id = {ph}", (val, task_id))
    conn.commit()
    conn.close()


def _delete_scheduled_task(task_id: int) -> None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"DELETE FROM agent_scheduled_tasks WHERE id = {ph}", (task_id,))
    conn.commit()
    conn.close()


def _seed_default_scheduled_tasks(created_by: str) -> None:
    """Seed helpful default scheduled tasks if table is empty."""
    existing = _list_scheduled_tasks()
    if existing:
        return
    defaults = [
        (
            "Weekly Spending Digest",
            "Auto-generate weekly spending summary and email report every Monday at 8 AM.",
            "Weekly Spending Digest (page 56)",
            "weekly", 0, 8,
        ),
        (
            "Daily Price Alert Refresh",
            "Re-scan eBay/Mercari for sneaker price alerts every day at 7 AM.",
            "Sneaker Price Alert Bot (page 31)",
            "daily", 0, 7,
        ),
        (
            "Monthly Financial Email Report",
            "Email full monthly financial report on the 1st of every month at 9 AM.",
            "Monthly Financial Email Report (page 36)",
            "monthly", 1, 9,
        ),
        (
            "Weekly Reseller Report",
            "Claude-generated weekly SoleOps reseller summary every Sunday at 8 PM.",
            "SoleOps: Weekly Reseller Report Email",
            "weekly", 6, 20,
        ),
    ]
    for task_name, desc, backlog_item, stype, sday, shour in defaults:
        _create_scheduled_task(task_name, desc, backlog_item, stype, sday, shour, created_by)


# ── Agent run helpers ─────────────────────────────────────────────────────────

def _load_runs() -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM agent_runs ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _load_active_run() -> dict | None:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM agent_runs WHERE status='running' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if row is None:
        conn.close()
        return None
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = dict(zip(cols, row))
    else:
        result = dict(row)
    conn.close()
    return result


def _load_logs(run_id: int | None = None, limit: int = 60) -> list[dict]:
    conn = get_conn()
    if run_id is not None:
        c = db_exec(conn,
            "SELECT * FROM agent_log WHERE run_id=? ORDER BY id DESC LIMIT ?",
            (run_id, limit))
    else:
        c = db_exec(conn,
            "SELECT * FROM agent_log ORDER BY id DESC LIMIT ?",
            (limit,))
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return list(reversed(result))  # oldest first for display


def _parse_backlog() -> dict:
    """Parse BACKLOG.md and return stats."""
    backlog_paths = [
        Path(__file__).parent.parent / "BACKLOG.md",
        Path("/app/BACKLOG.md"),
    ]
    text = ""
    for p in backlog_paths:
        if p.exists():
            text = p.read_text()
            break

    if not text:
        return {"total": 0, "done": 0, "pending": [], "completed": [], "yours": []}

    pending, completed, yours = [], [], []
    section = "HIGH"
    for line in text.split("\n"):
        upper = line.upper()
        if "HIGH" in upper:
            section = "HIGH"
        elif "MEDIUM" in upper:
            section = "MEDIUM"
        elif "LOW" in upper:
            section = "LOW"

        if line.startswith("- [x]"):
            completed.append(line[6:].strip())
        elif line.startswith("- [ ]"):
            task = line[6:].strip()
            if "[YOU]" in task:
                yours.append((task.replace("[YOU]", "").strip(), section))
            else:
                pending.append((task, section))

    return {
        "total": len(pending) + len(completed) + len(yours),
        "done": len(completed),
        "pending": pending,
        "completed": completed,
        "yours": yours,
    }


def _run_git(cmd: str) -> str:
    repo = Path(__file__).parent.parent
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(repo), timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""


# ── Init tables + seed defaults ───────────────────────────────────────────────
_ensure_tables()
_seed_default_scheduled_tasks(st.session_state.get("username", "darrian"))

# ══════════════════════════════════════════════════════════════════════════════
# ── Page header ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

st.title("🤖 Agent Dashboard")
st.caption("Live monitoring for the Overnight AI Dev System — watch features being built in real time.")

# ── Auto-refresh control ──────────────────────────────────────────────────────
try:
    active_run = _load_active_run()
except Exception:
    active_run = None

col_refresh, col_auto = st.columns([1, 3])
with col_refresh:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
with col_auto:
    auto_refresh = st.toggle("⚡ Auto-refresh every 5s", value=(active_run is not None))

if auto_refresh:
    time.sleep(5)
    st.rerun()

st.divider()

# ── Status banner ─────────────────────────────────────────────────────────────
if active_run:
    elapsed = ""
    try:
        started = datetime.strptime(str(active_run["started_at"])[:19], "%Y-%m-%d %H:%M:%S")
        elapsed = f" — running for {int((datetime.now() - started).total_seconds() / 60)}m"
    except Exception:
        pass
    st.success(f"🟢 **AGENT RUNNING** — Building: **{active_run.get('display_name') or active_run.get('feature_name', '...')}**{elapsed}")
else:
    runs = _load_runs()
    if runs and runs[0]["status"] == "success":
        last = runs[0]
        st.info(f"⚡ **Idle** — Last build: **{last.get('display_name', last.get('feature_name', '?'))}** ✅ {last.get('ended_at', '')[:16]}")
    elif runs and runs[0]["status"] == "failed":
        last = runs[0]
        st.warning(f"⚠️ **Idle** — Last build: **{last.get('display_name', '?')}** ❌ Failed — {last.get('error_msg', '')[:80]}")
    else:
        st.info("⏸️ **Idle** — No agents currently running. SSH in and run `bash /root/start-agents.sh` to start.")

# ── How to start ──────────────────────────────────────────────────────────────
with st.expander("▶️ How to start the agents"):
    st.code("""ssh root@100.95.125.112
bash /root/start-agents.sh

# Or watch the log live:
tail -f /var/log/overnight-dev.log""", language="bash")
    st.caption("Agents run automatically at 11 PM nightly (after you set the cron).")
    st.code("""echo "0 23 * * * root bash /root/start-agents.sh >> /var/log/overnight-dev.log 2>&1" >> /etc/crontab""", language="bash")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ── Tabs ──────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

tab_live, tab_backlog, tab_sched, tab_history, tab_git = st.tabs([
    "📡 Live Log",
    "📋 Backlog",
    "⏰ Scheduled Tasks",
    "📜 Build History",
    "🌿 Git Activity",
])

# ── Tab 1: Live Log ───────────────────────────────────────────────────────────
with tab_live:
    if active_run:
        st.markdown(f"**Live output for:** `{active_run.get('feature_name', 'current run')}`")
        run_id = active_run["id"]
    else:
        st.caption("Showing last 60 log entries from most recent run.")
        runs = _load_runs()
        run_id = runs[0]["id"] if runs else None

    logs = _load_logs(run_id=run_id, limit=60)

    if not logs:
        st.info("No log entries yet. Logs appear here as the agent runs.")
    else:
        level_colors = {
            "INFO":    "#e8f5e9",
            "SUCCESS": "#c8e6c9",
            "WARNING": "#fff3e0",
            "ERROR":   "#ffebee",
            "NOTIFY":  "#e3f2fd",
        }
        log_html = []
        for entry in logs:
            level = entry.get("level", "INFO").upper()
            msg   = entry.get("message", "")
            ts    = str(entry.get("created_at", ""))[:19]
            bg    = level_colors.get(level, "#fafafa")
            icon  = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "NOTIFY": "📣"}.get(level, "•")
            log_html.append(
                f'<div style="background:{bg};padding:4px 10px;border-radius:4px;'
                f'margin-bottom:2px;font-family:monospace;font-size:12px;">'
                f'<span style="color:#888;">[{ts}]</span> {icon} {msg}</div>'
            )
        st.markdown("\n".join(log_html), unsafe_allow_html=True)

# ── Tab 2: Backlog ────────────────────────────────────────────────────────────
with tab_backlog:
    bl = _parse_backlog()
    total = bl["total"]
    done  = bl["done"]
    pct   = int(done / total * 100) if total > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 Total Features",  total)
    m2.metric("✅ Completed",       done)
    m3.metric("⏳ Pending",         len(bl["pending"]))
    m4.metric("🔒 Claimed by You",  len(bl["yours"]))

    st.progress(pct / 100, text=f"{pct}% complete ({done}/{total} features)")
    st.divider()

    if bl["pending"]:
        st.markdown("**⏳ Pending (agents pick from top)**")
        priority_colors = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}
        for i, (task, priority) in enumerate(bl["pending"]):
            badge = priority_colors.get(priority, "⚪")
            next_tag = "  🎯 **← NEXT TONIGHT**" if i == 0 else ""
            st.markdown(f"{badge} {task}{next_tag}")

    if bl["yours"]:
        st.divider()
        st.markdown("**🔒 Claimed By You (agents skip these)**")
        for task, priority in bl["yours"]:
            badge = priority_colors.get(priority, "⚪")
            st.markdown(f"{badge} {task}")

    if bl["completed"]:
        st.divider()
        with st.expander(f"✅ Completed ({len(bl['completed'])})"):
            for task in bl["completed"]:
                st.markdown(f"✅ ~~{task}~~")

    if total == 0:
        st.info("BACKLOG.md not found or empty. Add features to `BACKLOG.md` in the repo root.")

# ── Tab 3: Scheduled Tasks ────────────────────────────────────────────────────
with tab_sched:
    st.subheader("⏰ Scheduled Agent Tasks")
    st.caption(
        "Set up recurring tasks that run autonomously — daily, weekly, or monthly — "
        "without you having to remember. Inspired by Claude Desktop's scheduled task system."
    )

    sched_tasks = _list_scheduled_tasks()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Metrics row ──────────────────────────────────────────────────────────
    enabled_count = sum(1 for t in sched_tasks if t.get("enabled"))
    sm1, sm2, sm3 = st.columns(3)
    sm1.metric("Total Scheduled", len(sched_tasks))
    sm2.metric("Enabled", enabled_count)
    sm3.metric("Disabled", len(sched_tasks) - enabled_count)

    st.markdown("---")

    # ── Add new task form ─────────────────────────────────────────────────────
    with st.expander("➕ Add New Scheduled Task", expanded=False):
        with st.form("new_sched_task", clear_on_submit=True):
            nf1, nf2 = st.columns(2)
            new_name = nf1.text_input("Task Name *", placeholder="Weekly Spending Digest")
            new_stype = nf2.selectbox("Schedule", ["daily", "weekly", "monthly"])

            new_desc = st.text_area("Description", placeholder="What does this task do?", height=70)
            new_backlog = st.text_input("Backlog Item (optional)", placeholder="Link to BACKLOG.md item")

            df1, df2, df3 = st.columns(3)
            day_labels = {
                "daily": ["Every day"],
                "weekly": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "monthly": [str(d) for d in range(1, 29)],
            }

            if new_stype == "daily":
                new_day = 0
                df1.caption("Runs every day")
            elif new_stype == "weekly":
                day_choice = df1.selectbox("Day of Week", day_labels["weekly"])
                new_day = day_labels["weekly"].index(day_choice)
            else:
                new_day = int(df1.selectbox("Day of Month", day_labels["monthly"]))

            new_hour = df2.slider("Hour (24h)", min_value=0, max_value=23, value=8)
            df3.caption(f"Next run: {_calc_next_run(new_stype, new_day, new_hour)[:16]}")

            if st.form_submit_button("✅ Create Scheduled Task", use_container_width=True):
                if new_name.strip():
                    _create_scheduled_task(
                        new_name.strip(), new_desc.strip(), new_backlog.strip(),
                        new_stype, new_day, new_hour,
                        st.session_state.get("username", "darrian"),
                    )
                    st.success(f"✅ Scheduled task **{new_name}** created!")
                    st.rerun()
                else:
                    st.error("Task Name is required.")

    st.markdown("---")

    # ── Task cards ────────────────────────────────────────────────────────────
    DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    if not sched_tasks:
        st.info("No scheduled tasks yet. Add one above or reload the page to seed defaults.")
    else:
        for task in sched_tasks:
            tid       = task["id"]
            name      = task["task_name"]
            desc      = task["description"] or ""
            stype     = task.get("schedule_type", "weekly")
            sday      = task.get("schedule_day", 0)
            shour     = task.get("schedule_hour", 8)
            next_run  = (task.get("next_run") or "—")[:16]
            last_run  = (task.get("last_run") or "Never")[:16]
            run_count = task.get("run_count", 0)
            enabled   = bool(task.get("enabled"))

            # Human-readable schedule label
            if stype == "daily":
                sched_label = f"Daily @ {shour:02d}:00"
            elif stype == "weekly":
                day_label = DAY_NAMES[sday] if 0 <= sday <= 6 else str(sday)
                sched_label = f"Every {day_label} @ {shour:02d}:00"
            else:
                sched_label = f"Monthly day {sday} @ {shour:02d}:00"

            # Is overdue?
            overdue = False
            try:
                nr = datetime.strptime(next_run, "%Y-%m-%d %H:%M")
                overdue = enabled and (nr < datetime.now())
            except Exception:
                pass

            status_icon = "🟢" if enabled else "⚫"
            overdue_badge = "  ⚠️ **OVERDUE**" if overdue else ""

            with st.container():
                tc1, tc2, tc3, tc4 = st.columns([4, 2, 2, 2])
                tc1.markdown(f"{status_icon} **{name}**{overdue_badge}")
                tc1.caption(desc[:80] if desc else "")
                tc2.metric("Schedule", sched_label)
                tc3.metric("Next Run", next_run)
                tc4.metric("Runs", run_count)

                bc1, bc2, bc3 = st.columns(3)
                if enabled:
                    if bc1.button("⏸ Disable", key=f"dis_{tid}", use_container_width=True):
                        _toggle_scheduled_task(tid, False)
                        st.rerun()
                else:
                    if bc1.button("▶️ Enable", key=f"en_{tid}", use_container_width=True):
                        _toggle_scheduled_task(tid, True)
                        st.rerun()
                bc2.caption(f"Last: {last_run}")
                if bc3.button("🗑️ Delete", key=f"del_{tid}", use_container_width=True):
                    _delete_scheduled_task(tid)
                    st.rerun()

                st.divider()

    # ── Cron setup instructions ───────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚙️ How to wire this into the actual cron / agent runner"):
        st.markdown("""
        The scheduled tasks table is a **task queue** for the overnight agent system.
        To make them actually run automatically, the agent runner script needs to check
        this table before deciding what to build next.

        **Option A — Add to the existing overnight cron:**
        ```bash
        # On CT100, edit /root/start-agents.sh to check agent_scheduled_tasks
        # for any row where enabled=1 AND next_run <= NOW()
        # run that task, update last_run + run_count + next_run
        ```

        **Option B — Dedicated scheduler cron (recommended):**
        ```bash
        # Every 15 minutes, check for due tasks
        echo "*/15 * * * * root python3 /app/run_scheduled_agents.py >> /var/log/sched-agents.log 2>&1" >> /etc/crontab
        ```

        **The scheduler picks up any task where:**
        - `enabled = 1`
        - `next_run <= datetime('now')`

        After running, it updates `last_run = NOW()` and recalculates `next_run`.
        """)

# ── Tab 4: Build History ──────────────────────────────────────────────────────
with tab_history:
    runs = _load_runs()
    if not runs:
        st.info("No builds yet. Start the agents and runs will appear here.")
    else:
        for run in runs:
            status  = run.get("status", "unknown")
            name    = run.get("display_name") or run.get("feature_name") or "Unknown"
            started = str(run.get("started_at", ""))[:16]
            ended   = str(run.get("ended_at", ""))[:16]
            pr_url  = run.get("pr_url", "")
            err     = run.get("error_msg", "")

            icon = {"running": "🟢", "success": "✅", "failed": "❌"}.get(status, "⚪")
            duration = ""
            try:
                s = datetime.strptime(started, "%Y-%m-%d %H:%M")
                e = datetime.strptime(ended, "%Y-%m-%d %H:%M")
                duration = f" ({int((e - s).total_seconds() / 60)}m)"
            except Exception:
                pass

            with st.container():
                c1, c2, c3 = st.columns([4, 2, 2])
                c1.markdown(f"{icon} **{name}**")
                c2.caption(f"🕐 {started}{duration}")
                if pr_url and status == "success":
                    c3.markdown(f"[→ Open PR]({pr_url})")
                elif status == "failed" and err:
                    c3.caption(f"❌ {err[:40]}")
            st.divider()

# ── Tab 5: Git Activity ───────────────────────────────────────────────────────
with tab_git:
    log_raw = _run_git('git log --oneline -15 --format="%h|%s|%cr|%an"')
    if log_raw:
        st.markdown("**📝 Recent Commits**")
        for line in log_raw.split("\n"):
            if "|" in line:
                parts = line.split("|", 3)
                if len(parts) == 4:
                    sha, msg, when, author = parts
                    is_agent = "overnight ai" in author.lower() or "auto-built" in msg.lower()
                    tag = "🟢 AGENT" if is_agent else "🔵 DARRIAN"
                    st.markdown(f"`{sha}` **{tag}** — {msg[:65]}  *{when}*")
    else:
        st.caption("Git log not available inside container.")

    st.divider()

    branches_raw = _run_git("git branch -r --format='%(refname:short)'")
    if branches_raw:
        feature_branches = [
            b.replace("origin/", "").strip()
            for b in branches_raw.split("\n")
            if "feature/" in b
        ]
        if feature_branches:
            st.markdown(f"**🌿 Active Feature Branches ({len(feature_branches)})**")
            for b in feature_branches[:12]:
                st.markdown(f"` {b} `")
        else:
            st.caption("No active feature branches.")

    st.divider()

    st.markdown("""
**🔗 Quick Links**
- [📋 GitHub PRs](https://github.com/bookofdarrian/darrian-budget/pulls)
- [⚙️ GitHub Actions](https://github.com/bookofdarrian/darrian-budget/actions)
- [📊 Commits](https://github.com/bookofdarrian/darrian-budget/commits/main)
""")
