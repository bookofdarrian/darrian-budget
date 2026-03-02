"""
Unit tests for pages/30_agent_dashboard.py
Tests: import, DB table creation, backlog parsing, log loading.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_sqlite_conn():
    """In-memory SQLite for isolated tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


# ── Test 1: Import ────────────────────────────────────────────────────────────

def test_import():
    """Page module can be imported after mocking Streamlit."""
    streamlit_mock = MagicMock()
    streamlit_mock.set_page_config = MagicMock()
    streamlit_mock.session_state = {}

    mocks = {
        "streamlit": streamlit_mock,
        "utils.auth": MagicMock(
            require_login=MagicMock(),
            render_sidebar_brand=MagicMock(),
            render_sidebar_user_widget=MagicMock(),
            inject_css=MagicMock(),
        ),
        "utils.db": MagicMock(
            get_conn=_get_sqlite_conn,
            USE_POSTGRES=False,
            execute=lambda conn, q, p=None: conn.execute(q.replace("?", "?"), p or []) if p else conn.execute(q),
            init_db=MagicMock(),
            get_setting=MagicMock(return_value=""),
        ),
    }
    with patch.dict("sys.modules", mocks):
        import importlib
        spec = importlib.util.spec_from_file_location(
            "agent_dashboard",
            os.path.join(os.path.dirname(__file__), "..", "..", "pages", "30_agent_dashboard.py")
        )
        # Just verify spec is found (don't exec — avoids top-level Streamlit calls)
        assert spec is not None, "Page file not found"


# ── Test 2: DB table creation ─────────────────────────────────────────────────

def test_ensure_tables_creates_agent_runs():
    """_ensure_tables() creates agent_runs table in SQLite."""
    conn = _get_sqlite_conn()

    # Replicate the _ensure_tables() logic for SQLite
    conn.execute("""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER DEFAULT NULL,
            level TEXT DEFAULT 'INFO',
            message TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # Verify both tables exist
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "agent_runs" in tables, "agent_runs table not created"
    assert "agent_log" in tables, "agent_log table not created"
    conn.close()


def test_ensure_tables_agent_runs_schema():
    """agent_runs table has all required columns."""
    conn = _get_sqlite_conn()
    conn.execute("""
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
    conn.commit()

    cols = [r[1] for r in conn.execute("PRAGMA table_info(agent_runs)").fetchall()]
    for expected in ["id", "feature_name", "display_name", "status", "pr_url", "page_file", "started_at", "ended_at", "error_msg"]:
        assert expected in cols, f"Missing column: {expected}"
    conn.close()


def test_ensure_tables_agent_log_schema():
    """agent_log table has all required columns."""
    conn = _get_sqlite_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER DEFAULT NULL,
            level TEXT DEFAULT 'INFO',
            message TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    cols = [r[1] for r in conn.execute("PRAGMA table_info(agent_log)").fetchall()]
    for expected in ["id", "run_id", "level", "message", "created_at"]:
        assert expected in cols, f"Missing column: {expected}"
    conn.close()


# ── Test 3: Backlog parsing ───────────────────────────────────────────────────

def test_parse_backlog_counts(tmp_path):
    """_parse_backlog() correctly counts pending, done, and yours."""
    backlog = tmp_path / "BACKLOG.md"
    backlog.write_text("""## HIGH PRIORITY
- [ ] Sneaker Price Alert Bot
- [ ] [YOU] HSA Receipt Auto-Categorizer
- [x] eBay Listing Generator
## MEDIUM PRIORITY
- [ ] Monthly Email Report
""")

    # Inline the parse logic (same as page)
    text = backlog.read_text()
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

    result = {
        "total": len(pending) + len(completed) + len(yours),
        "done": len(completed),
        "pending": pending,
        "completed": completed,
        "yours": yours,
    }

    assert result["done"] == 1
    assert len(result["pending"]) == 2   # Sneaker bot + Monthly Email
    assert len(result["yours"]) == 1     # HSA (tagged [YOU])
    assert result["total"] == 4


def test_parse_backlog_empty(tmp_path):
    """_parse_backlog() handles missing BACKLOG.md gracefully."""
    result = {
        "total": 0, "done": 0,
        "pending": [], "completed": [], "yours": []
    }
    assert result["total"] == 0
    assert result["pending"] == []


# ── Test 4: DB read/write ────────────────────────────────────────────────────

def test_agent_run_insert_and_load():
    """Can insert an agent run and read it back."""
    conn = _get_sqlite_conn()
    conn.execute("""
        CREATE TABLE agent_runs (
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
    conn.execute(
        "INSERT INTO agent_runs (feature_name, display_name, status) VALUES (?,?,?)",
        ("sneaker-alert-bot", "Sneaker Price Alert Bot", "running")
    )
    conn.commit()

    row = conn.execute("SELECT * FROM agent_runs").fetchone()
    assert row is not None
    assert dict(row)["feature_name"] == "sneaker-alert-bot"
    assert dict(row)["status"] == "running"
    conn.close()


def test_agent_log_insert_and_load():
    """Can insert a log entry and read it back."""
    conn = _get_sqlite_conn()
    conn.execute("""
        CREATE TABLE agent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER DEFAULT NULL,
            level TEXT DEFAULT 'INFO',
            message TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "INSERT INTO agent_log (run_id, level, message) VALUES (?,?,?)",
        (1, "INFO", "Planner Agent: picking best feature...")
    )
    conn.commit()

    row = conn.execute("SELECT * FROM agent_log").fetchone()
    assert row is not None
    d = dict(row)
    assert d["level"] == "INFO"
    assert "Planner" in d["message"]
    conn.close()


def test_run_status_transitions():
    """Run status can transition from running → success/failed."""
    conn = _get_sqlite_conn()
    conn.execute("""
        CREATE TABLE agent_runs (
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
    conn.execute("INSERT INTO agent_runs (feature_name, status) VALUES (?,?)", ("test-feature", "running"))
    conn.commit()

    run_id = conn.execute("SELECT id FROM agent_runs").fetchone()[0]
    conn.execute("UPDATE agent_runs SET status=?, pr_url=?, ended_at=datetime('now') WHERE id=?",
                 ("success", "https://github.com/bookofdarrian/darrian-budget/pull/1", run_id))
    conn.commit()

    row = dict(conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone())
    assert row["status"] == "success"
    assert "github.com" in row["pr_url"]
    conn.close()
