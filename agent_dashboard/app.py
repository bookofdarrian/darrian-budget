#!/usr/bin/env python3
"""
Agent Dashboard — Standalone Dash App
Live monitoring for the Overnight AI Dev System.
Replaces pages/30_agent_dashboard.py (Streamlit-free).

Run locally:   python agent_dashboard/app.py
On homelab:    python /opt/agent-dashboard/app.py
URL:           http://localhost:8502  |  http://100.95.125.112:8502
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# ── Repo root on path ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# ── Try to import DB utils (graceful fallback to log-file-only mode) ──────────
try:
    from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False
    USE_POSTGRES = False

# ── Constants ─────────────────────────────────────────────────────────────────
LOG_FILE     = os.environ.get("AGENT_LOG_FILE", "/var/log/overnight-dev.log")
BACKLOG_PATH = ROOT / "BACKLOG.md"
PORT         = int(os.environ.get("DASHBOARD_PORT", 8502))

# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_tables():
    if not DB_AVAILABLE:
        return
    try:
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
    except Exception:
        pass


def _load_runs() -> list:
    if not DB_AVAILABLE:
        return []
    try:
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
    except Exception:
        return []


def _load_active_run():
    if not DB_AVAILABLE:
        return None
    try:
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
    except Exception:
        return None


def _load_logs(run_id=None, limit=60) -> list:
    if not DB_AVAILABLE:
        return []
    try:
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
        return list(reversed(result))  # oldest first
    except Exception:
        return []


def _read_log_file(limit=100) -> list:
    """Read last N lines directly from /var/log/overnight-dev.log."""
    try:
        p = Path(LOG_FILE)
        if not p.exists():
            return []
        lines = p.read_text(errors="replace").splitlines()
        # Deduplicate consecutive identical lines (start-agents can spawn two instances)
        deduped = []
        for line in lines[-limit * 2:]:
            if not deduped or line != deduped[-1]:
                deduped.append(line)
        return deduped[-limit:]
    except Exception:
        return []


def _parse_backlog() -> dict:
    text = ""
    for p in [BACKLOG_PATH, Path("/app/BACKLOG.md"), Path("/root/darrian-budget/BACKLOG.md")]:
        if p.exists():
            text = p.read_text()
            break
    if not text:
        return {"total": 0, "done": 0, "pending": [], "completed": [], "yours": []}

    pending, completed, yours = [], [], []
    section = "HIGH"
    for line in text.split("\n"):
        upper = line.upper()
        if "## HIGH" in upper or "### HIGH" in upper:
            section = "HIGH"
        elif "## MEDIUM" in upper or "### MEDIUM" in upper:
            section = "MEDIUM"
        elif "## LOW" in upper or "### LOW" in upper:
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
    try:
        repo = ROOT
        # On server, use repo path
        server_repo = Path("/root/darrian-budget")
        if server_repo.exists():
            repo = server_repo
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           cwd=str(repo), timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Init DB
# ─────────────────────────────────────────────────────────────────────────────
if DB_AVAILABLE:
    try:
        init_db()
        _ensure_tables()
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# Dash App
# ─────────────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="🤖 Agent Dashboard — Peach State Savings",
    update_title=None,
)
server = app.server  # expose Flask server (for gunicorn if needed)

# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = dbc.Container(
    fluid=True,
    style={"paddingTop": "24px", "paddingBottom": "48px"},
    children=[
        # Auto-refresh every 5 seconds
        dcc.Interval(id="interval", interval=5_000, n_intervals=0),

        # ── Header ────────────────────────────────────────────────────────────
        dbc.Row([
            dbc.Col([
                html.H2("🤖 Agent Dashboard", className="mb-0 fw-bold"),
                html.Small(
                    "Live monitoring for the Overnight AI Dev System — "
                    "watch features being built in real time.",
                    className="text-muted",
                ),
            ], width=9),
            dbc.Col([
                html.Div(
                    id="last-updated",
                    className="text-end text-muted small mt-2",
                )
            ], width=3),
        ], className="mb-3 align-items-center"),

        html.Hr(className="my-2"),

        # ── Status banner (updates on interval) ───────────────────────────────
        html.Div(id="status-banner", className="mb-3"),

        # ── Metrics cards (updates on interval) ───────────────────────────────
        html.Div(id="metrics-row", className="mb-4"),

        # ── Tabs ──────────────────────────────────────────────────────────────
        dbc.Tabs(
            id="main-tabs",
            active_tab="tab-live",
            children=[
                dbc.Tab(label="📡  Live Log",       tab_id="tab-live"),
                dbc.Tab(label="📋  Backlog",         tab_id="tab-backlog"),
                dbc.Tab(label="📜  Build History",   tab_id="tab-history"),
                dbc.Tab(label="🌿  Git Activity",    tab_id="tab-git"),
            ],
            className="mb-3",
        ),

        # Tab content (updates on interval + tab switch)
        html.Div(id="tab-content"),

        html.Hr(className="mt-5 mb-3"),

        # ── How to start agents (collapsible) ─────────────────────────────────
        dbc.Accordion([
            dbc.AccordionItem(
                title="▶️  How to start the agents",
                children=[
                    dcc.Markdown("""
**Start manually:**
```bash
ssh root@100.95.125.112
bash /root/start-agents.sh
```

**Watch live logs:**
```bash
ssh root@100.95.125.112 "tail -f /var/log/overnight-dev.log"
```

**Schedule nightly at 11 PM:**
```bash
echo "0 23 * * * root bash /root/start-agents.sh >> /var/log/overnight-dev.log 2>&1" >> /etc/crontab
```
                    """),
                ],
            )
        ], start_collapsed=True),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("status-banner",  "children"),
    Output("metrics-row",    "children"),
    Output("last-updated",   "children"),
    Input("interval",        "n_intervals"),
)
def update_header(n):
    active = _load_active_run()
    runs   = _load_runs()
    now_ts = datetime.now().strftime("%H:%M:%S")

    # ── Status banner ─────────────────────────────────────────────────────────
    if active:
        elapsed = ""
        try:
            started = datetime.strptime(str(active["started_at"])[:19], "%Y-%m-%d %H:%M:%S")
            mins    = int((datetime.now() - started).total_seconds() / 60)
            elapsed = f" — running for {mins}m"
        except Exception:
            pass
        name   = active.get("display_name") or active.get("feature_name", "…")
        banner = dbc.Alert(
            [html.Strong("🟢  AGENT RUNNING"), " — Building: ", html.Strong(name), elapsed],
            color="success",
            className="mb-0",
        )
    elif runs and runs[0]["status"] == "success":
        last   = runs[0]
        banner = dbc.Alert(
            [
                html.Strong("⚡  Idle"),
                " — Last build: ",
                html.Strong(last.get("display_name") or last.get("feature_name", "?")),
                f"  ✅  {str(last.get('ended_at', ''))[:16]}",
            ],
            color="info",
            className="mb-0",
        )
    elif runs and runs[0]["status"] == "failed":
        last   = runs[0]
        banner = dbc.Alert(
            [
                html.Strong("⚠️  Idle"),
                " — Last build: ",
                html.Strong(last.get("display_name", "?")),
                f" ❌ Failed — {str(last.get('error_msg', ''))[:80]}",
            ],
            color="warning",
            className="mb-0",
        )
    else:
        banner = dbc.Alert(
            "⏸️  Idle — No agents currently running. "
            "SSH in and run:  bash /root/start-agents.sh",
            color="secondary",
            className="mb-0",
        )

    # ── Backlog metrics ────────────────────────────────────────────────────────
    bl    = _parse_backlog()
    total = bl["total"]
    done  = bl["done"]
    pct   = int(done / total * 100) if total > 0 else 0

    def _metric_card(value, label):
        return dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4(str(value), className="card-title text-center fw-bold mb-0"),
                    html.P(label, className="text-center text-muted small mb-0"),
                ]),
                className="h-100",
            ),
            xs=6, md=3,
        )

    metrics = dbc.Row([
        _metric_card(total,               "📊 Total Features"),
        _metric_card(done,                "✅ Completed"),
        _metric_card(len(bl["pending"]),  "⏳ Pending"),
        _metric_card(f"{pct}%",           "🎯 Progress"),
    ], className="g-2 mb-2")

    return banner, metrics, f"Last updated: {now_ts}"


@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs",    "active_tab"),
    Input("interval",     "n_intervals"),
)
def render_tab(active_tab, n):
    if active_tab == "tab-live":
        return _render_live_log()
    if active_tab == "tab-backlog":
        return _render_backlog()
    if active_tab == "tab-history":
        return _render_history()
    if active_tab == "tab-git":
        return _render_git()
    return html.Div("Select a tab.")


# ─────────────────────────────────────────────────────────────────────────────
# Tab renderers
# ─────────────────────────────────────────────────────────────────────────────

_LEVEL_STYLE = {
    "INFO":    {"background": "#1a2e1a", "color": "#a5d6a7"},
    "SUCCESS": {"background": "#1b3a1b", "color": "#69f0ae"},
    "WARNING": {"background": "#2e2000", "color": "#ffcc80"},
    "ERROR":   {"background": "#2e0000", "color": "#ef9a9a"},
    "NOTIFY":  {"background": "#0d1f3c", "color": "#90caf9"},
}
_LEVEL_ICONS = {
    "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "NOTIFY": "📣",
}


def _detect_level(line: str) -> str:
    l = line.upper()
    if "SUCCESS" in l or "✅" in l or "PASSED" in l or "SYNTAX_OK" in l:
        return "SUCCESS"
    if "WARNING" in l or "⚠" in l:
        return "WARNING"
    if "ERROR" in l or "❌" in l or "FAILED" in l or "TRACEBACK" in l:
        return "ERROR"
    if "NOTIFY" in l or "📣" in l:
        return "NOTIFY"
    return "INFO"


def _log_row(level: str, ts: str, msg: str) -> html.Div:
    style = dict(_LEVEL_STYLE.get(level.upper(), _LEVEL_STYLE["INFO"]))
    style.update({
        "padding": "4px 10px",
        "borderRadius": "3px",
        "marginBottom": "2px",
        "fontFamily": "monospace",
        "fontSize": "12px",
    })
    icon = _LEVEL_ICONS.get(level.upper(), "•")
    return html.Div(
        [
            html.Span(f"[{ts}]  " if ts else "", style={"opacity": "0.55", "marginRight": "6px"}),
            html.Span(icon + "  "),
            html.Span(msg),
        ],
        style=style,
    )


def _render_live_log():
    active = _load_active_run()

    # Try DB logs first
    if active:
        run_id = active["id"]
        title  = f"Live output for: {active.get('feature_name', 'current run')}"
    else:
        runs   = _load_runs()
        run_id = runs[0]["id"] if runs else None
        title  = "Last 60 DB log entries from most recent run."

    db_logs = _load_logs(run_id=run_id, limit=60)

    if db_logs:
        rows = [
            _log_row(
                e.get("level", "INFO"),
                str(e.get("created_at", ""))[:19],
                e.get("message", ""),
            )
            for e in db_logs
        ]
        return html.Div([
            html.P(title, className="text-muted small mb-2"),
            html.Div(rows, style={"maxHeight": "540px", "overflowY": "auto"}),
        ])

    # Fallback: raw log file
    raw = _read_log_file(limit=100)
    if raw:
        rows = [_log_row(_detect_level(line), "", line) for line in raw]
        return html.Div([
            html.P(
                [html.Span("📄  Raw log file ", className="text-muted"),
                 html.Code(LOG_FILE, className="text-muted")],
                className="small mb-2",
            ),
            html.Div(rows, style={"maxHeight": "540px", "overflowY": "auto"}),
        ])

    return dbc.Alert(
        "No log entries yet. Logs appear here as the agent runs.",
        color="secondary",
    )


def _render_backlog():
    bl    = _parse_backlog()
    total = bl["total"]
    done  = bl["done"]
    pct   = int(done / total * 100) if total > 0 else 0
    priority_icons = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}

    if total == 0:
        return dbc.Alert(
            "BACKLOG.md not found or empty. Add features to BACKLOG.md in the repo root.",
            color="secondary",
        )

    parts = [
        dbc.Progress(
            value=pct,
            label=f"{pct}%  ({done}/{total} features complete)",
            className="mb-4",
            style={"height": "24px"},
        ),
    ]

    if bl["pending"]:
        pending_items = []
        for i, (task, priority) in enumerate(bl["pending"]):
            icon     = priority_icons.get(priority, "⚪")
            next_tag = html.Span(" 🎯 ← NEXT", className="text-warning fw-bold") if i == 0 else ""
            pending_items.append(
                dbc.ListGroupItem(
                    [html.Span(f"{icon}  {task} "), next_tag],
                    style={"fontWeight": "600" if i == 0 else "normal",
                           "backgroundColor": "#1c2e1c" if i == 0 else ""},
                )
            )
        parts += [
            html.H6("⏳  Pending — agents pick from top", className="mt-2 mb-2"),
            dbc.ListGroup(pending_items, className="mb-3"),
        ]

    if bl["yours"]:
        yours_items = [
            dbc.ListGroupItem(f"{priority_icons.get(p, '⚪')}  {t}")
            for t, p in bl["yours"]
        ]
        parts += [
            html.H6("🔒  Claimed By You (agents skip)", className="mt-3 mb-2"),
            dbc.ListGroup(yours_items, className="mb-3"),
        ]

    if bl["completed"]:
        done_items = [
            dbc.ListGroupItem(
                f"✅  {t}",
                style={"textDecoration": "line-through", "color": "#666"},
            )
            for t in bl["completed"]
        ]
        parts.append(
            dbc.Accordion([
                dbc.AccordionItem(
                    title=f"✅  Completed ({len(bl['completed'])})",
                    children=[dbc.ListGroup(done_items)],
                )
            ], start_collapsed=True, className="mt-2")
        )

    return html.Div(parts)


def _render_history():
    runs = _load_runs()
    if not runs:
        return dbc.Alert(
            "No builds yet. Start the agents and runs will appear here.",
            color="secondary",
        )

    items = []
    for run in runs:
        status  = run.get("status", "unknown")
        name    = run.get("display_name") or run.get("feature_name") or "Unknown"
        started = str(run.get("started_at", ""))[:16]
        ended   = str(run.get("ended_at",   ""))[:16]
        pr_url  = run.get("pr_url", "")
        err     = run.get("error_msg", "")

        icon = {"running": "🟢", "success": "✅", "failed": "❌"}.get(status, "⚪")

        duration = ""
        try:
            s        = datetime.strptime(started, "%Y-%m-%d %H:%M")
            e        = datetime.strptime(ended,   "%Y-%m-%d %H:%M")
            duration = f" ({int((e - s).total_seconds() / 60)}m)"
        except Exception:
            pass

        right_col = ""
        if pr_url and status == "success":
            right_col = html.A(
                "→ Open PR", href=pr_url, target="_blank",
                className="btn btn-sm btn-outline-success",
            )
        elif status == "failed" and err:
            right_col = html.Small(f"❌ {err[:50]}", className="text-danger")

        color = {"running": "success", "success": "light", "failed": "warning"}.get(
            status, "secondary"
        )
        items.append(
            dbc.ListGroupItem(
                dbc.Row([
                    dbc.Col(html.Span(f"{icon}  {name}", className="fw-semibold"), width=6),
                    dbc.Col(html.Small(f"🕐  {started}{duration}", className="text-muted"), width=4),
                    dbc.Col(right_col, width=2, className="text-end"),
                ], align="center"),
                color=color,
            )
        )

    return dbc.ListGroup(items)


def _render_git():
    log_raw = _run_git('git log --oneline -15 --format="%h|%s|%cr|%an"')
    commit_items = []

    if log_raw:
        for line in log_raw.split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) != 4:
                continue
            sha, msg, when, author = parts
            is_agent  = "overnight ai" in author.lower() or "auto-built" in msg.lower()
            tag_color = "success"  if is_agent else "primary"
            tag_label = "🤖 AGENT" if is_agent else "👤 DARRIAN"
            commit_items.append(
                dbc.ListGroupItem([
                    dbc.Badge(tag_label, color=tag_color, className="me-2"),
                    html.Code(sha + "  ", style={"fontSize": "11px", "color": "#aaa"}),
                    html.Span(msg[:72]),
                    html.Small(f"  {when}", className="text-muted ms-2"),
                ])
            )

    commit_section = (
        dbc.ListGroup(commit_items)
        if commit_items
        else dbc.Alert("Git log not available.", color="secondary")
    )

    # Feature branches
    branches_raw     = _run_git("git branch -r --format='%(refname:short)'")
    feature_branches = []
    if branches_raw:
        feature_branches = [
            b.replace("origin/", "").strip()
            for b in branches_raw.split("\n")
            if "feature/" in b
        ]

    branch_section = html.Div()
    if feature_branches:
        branch_section = html.Div([
            html.H6(f"🌿  Active Feature Branches ({len(feature_branches)})", className="mt-4 mb-2"),
            html.Div([
                dbc.Badge(b, color="secondary", pill=True, className="me-1 mb-1")
                for b in feature_branches[:15]
            ]),
        ])

    links_card = dbc.Card(
        dbc.CardBody([
            html.H6("🔗  Quick Links", className="mb-3"),
            html.A(
                "📋  GitHub Pull Requests",
                href="https://github.com/bookofdarrian/darrian-budget/pulls",
                target="_blank",
                className="d-block mb-2",
            ),
            html.A(
                "⚙️  GitHub Actions",
                href="https://github.com/bookofdarrian/darrian-budget/actions",
                target="_blank",
                className="d-block mb-2",
            ),
            html.A(
                "📊  Commit History",
                href="https://github.com/bookofdarrian/darrian-budget/commits/main",
                target="_blank",
                className="d-block",
            ),
        ]),
        className="mt-4",
    )

    return html.Div([
        html.H6("📝  Recent Commits", className="mb-2"),
        commit_section,
        branch_section,
        links_card,
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"")
    print(f"  🤖  Agent Dashboard")
    print(f"  ─────────────────────────────────────")
    print(f"  Local:    http://localhost:{PORT}")
    print(f"  Homelab:  http://100.95.125.112:{PORT}")
    print(f"  Log file: {LOG_FILE}")
    print(f"  DB mode:  {'Postgres' if USE_POSTGRES else 'SQLite' if DB_AVAILABLE else 'log-file only'}")
    print(f"")
    app.run(debug=False, host="0.0.0.0", port=PORT)
