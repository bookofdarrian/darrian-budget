"""
Agent Dashboard — Page 30
Live monitoring dashboard for the Overnight AI Dev System.
Shows agent status, live logs, backlog progress, and build history.
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
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",         icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",           icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",   icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# ── DB helpers ────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
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


# ── Init tables ───────────────────────────────────────────────────────────────
_ensure_tables()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🤖 Agent Dashboard")
st.caption("Live monitoring for the Overnight AI Dev System — watch features being built in real time.")

# ── Auto-refresh control ──────────────────────────────────────────────────────
active_run = _load_active_run()

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

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_live, tab_backlog, tab_history, tab_git = st.tabs([
    "📡 Live Log",
    "📋 Backlog",
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
        # Build a colored log display
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

# ── Tab 3: Build History ──────────────────────────────────────────────────────
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

# ── Tab 4: Git Activity ───────────────────────────────────────────────────────
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

    # Link to GitHub
    st.markdown("""
**🔗 Quick Links**
- [📋 GitHub PRs](https://github.com/bookofdarrian/darrian-budget/pulls)
- [⚙️ GitHub Actions](https://github.com/bookofdarrian/darrian-budget/actions)
- [📊 Commits](https://github.com/bookofdarrian/darrian-budget/commits/main)
""")
