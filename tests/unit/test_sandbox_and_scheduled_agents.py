"""
Unit Tests — Sandbox Mode + Scheduled Agent Tasks
Tests for:
  - pages/73_sandbox_mode.py  (sandbox grants, isolated SQLite, export, expiry)
  - pages/30_agent_dashboard.py  (agent_scheduled_tasks DB, next_run calc, CRUD)
"""
import sys
import os
import json
import sqlite3
import types
from datetime import datetime, timedelta

import pytest

# ── Project root on path ──────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SANDBOX_PAGE = os.path.join(PROJECT_ROOT, "pages", "73_sandbox_mode.py")
AGENT_PAGE   = os.path.join(PROJECT_ROOT, "pages", "30_agent_dashboard.py")


# ══════════════════════════════════════════════════════════════════════════════
# ── Streamlit stub ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _stub_streamlit():
    # Always (re-)apply stub attrs — even if streamlit is already in sys.modules
    # from another test file that didn't set all attributes.
    mod = sys.modules.get("streamlit") or types.ModuleType("streamlit")
    mod.set_page_config       = lambda **k: None
    mod.markdown              = lambda *a, **k: None
    mod.title                 = lambda *a, **k: None
    mod.caption               = lambda *a, **k: None
    mod.write                 = lambda *a, **k: None
    mod.info                  = lambda *a, **k: None
    mod.success               = lambda *a, **k: None
    mod.warning               = lambda *a, **k: None
    mod.error                 = lambda *a, **k: None
    mod.toast                 = lambda *a, **k: None
    mod.stop                  = lambda: None
    mod.rerun                 = lambda: None
    mod.divider               = lambda: None
    mod.subheader             = lambda *a, **k: None
    mod.text_input            = lambda *a, **k: ""
    mod.text_area             = lambda *a, **k: ""
    mod.number_input          = lambda *a, **k: 0.0
    mod.selectbox             = lambda *a, **k: None
    mod.multiselect           = lambda *a, **k: []
    mod.radio                 = lambda *a, **k: None
    mod.checkbox              = lambda *a, **k: False
    mod.button                = lambda *a, **k: False
    mod.date_input            = lambda *a, **k: None
    mod.file_uploader         = lambda *a, **k: None
    mod.image                 = lambda *a, **k: None
    mod.slider                = lambda *a, **k: 8
    mod.progress              = lambda *a, **k: None
    mod.metric                = lambda *a, **k: None
    mod.expander              = lambda *a, **k: _ctx()
    mod.container             = lambda *a, **k: _ctx()
    mod.form                  = lambda *a, **k: _ctx()
    mod.status                = lambda *a, **k: _ctx()
    mod.toggle                = lambda *a, **k: False
    mod.download_button       = lambda *a, **k: None
    mod.tabs                  = lambda labels: [_ctx() for _ in labels]
    mod.columns               = lambda *a, **k: [_ctx()] * (a[0] if a and isinstance(a[0], int) else len(a[0]) if a else 2)
    mod.form_submit_button    = lambda *a, **k: False
    mod.session_state         = {"username": "darrian"}
    mod.sidebar               = types.SimpleNamespace(
        markdown=lambda *a, **k: None,
        page_link=lambda *a, **k: None,
        expander=lambda *a, **k: _ctx(),
        text_input=lambda *a, **k: "",
        button=lambda *a, **k: False,
    )
    sys.modules["streamlit"] = mod
    for sub in ["streamlit.components", "streamlit.components.v1"]:
        sys.modules.setdefault(sub, types.ModuleType(sub))
    return mod


class _ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __call__(self, *a, **k): return self
    markdown = lambda self, *a, **k: None
    caption  = lambda self, *a, **k: None
    write    = lambda self, *a, **k: None
    button   = lambda self, *a, **k: False
    text_input = lambda self, *a, **k: ""
    metric   = lambda self, *a, **k: None
    update   = lambda self, *a, **k: None


# ══════════════════════════════════════════════════════════════════════════════
# ── Fixtures ──────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def stub_st():
    _stub_streamlit()
    yield


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    import utils.db as db_mod
    monkeypatch.setattr(db_mod, "USE_POSTGRES", False)

    def fake_get_conn():
        c = sqlite3.connect(str(db_file), check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(db_mod, "get_conn", fake_get_conn)
    monkeypatch.setattr(db_mod, "get_setting", lambda key, default="": default)
    monkeypatch.setattr(db_mod, "set_setting", lambda key, val: None)
    yield fake_get_conn, db_file


def _extract_helpers(page_path: str) -> dict:
    import ast
    import utils.db as db_mod

    with open(page_path) as f:
        source = f.read()

    tree = ast.parse(source)
    safe_nodes = [
        node for node in tree.body
        if isinstance(node, (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
            ast.Assign, ast.AugAssign, ast.AnnAssign,
            ast.Import, ast.ImportFrom,
        ))
    ]
    safe_module = ast.Module(body=safe_nodes, type_ignores=[])
    code = compile(safe_module, page_path, "exec")

    ns: dict = {
        "__builtins__": __builtins__,
        "__file__":     page_path,
        "get_conn":     db_mod.get_conn,
        "USE_POSTGRES": db_mod.USE_POSTGRES,
        "db_exec":      db_mod.execute,
        "get_setting":  db_mod.get_setting,
        "set_setting":  db_mod.set_setting,
        "json":         json,
        "datetime":     datetime,
        "timedelta":    timedelta,
        "re":           __import__("re"),
        "base64":       __import__("base64"),
        "st":           sys.modules["streamlit"],
    }
    exec(code, ns)
    return ns


# ══════════════════════════════════════════════════════════════════════════════
# ── TESTS: pages/73_sandbox_mode.py ──────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

class TestSandboxMode:
    """Tests for the Sandbox / Privacy Mode page."""

    def test_sandbox_page_exists(self):
        assert os.path.isfile(SANDBOX_PAGE)

    def test_sandbox_page_syntax(self):
        compile(open(SANDBOX_PAGE).read(), SANDBOX_PAGE, "exec")

    def test_ensure_tables_creates_sandbox_grants(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        ns["_ensure_tables"]()
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sandbox_grants'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_grant_sandbox_inserts_row(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        ns["_ensure_tables"]()
        ns["_grant_sandbox"]("alice", "darrian", "Test sandbox")
        conn = fake_get_conn()
        row = conn.execute("SELECT * FROM sandbox_grants WHERE username='alice'").fetchone()
        conn.close()
        assert row is not None
        assert dict(row)["granted_by"] == "darrian"
        assert dict(row)["active"] == 1

    def test_get_grant_returns_dict(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        ns["_ensure_tables"]()
        ns["_grant_sandbox"]("bob", "darrian")
        result = ns["_get_grant"]("bob")
        assert result is not None
        assert isinstance(result, dict)
        assert result["username"] == "bob"

    def test_get_grant_returns_none_for_missing(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        ns["_ensure_tables"]()
        result = ns["_get_grant"]("nobody")
        assert result is None

    def test_revoke_sandbox(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        ns["_ensure_tables"]()
        ns["_grant_sandbox"]("carol", "darrian")
        ns["_revoke_sandbox"]("carol")
        # After revoke, active=0 so _get_grant should return None
        result = ns["_get_grant"]("carol")
        assert result is None

    def test_list_grants_returns_all(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        ns["_ensure_tables"]()
        ns["_grant_sandbox"]("user1", "darrian")
        ns["_grant_sandbox"]("user2", "darrian")
        grants = ns["_list_grants"]()
        assert len(grants) == 2

    def test_sandbox_db_path_uses_safe_name(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        path = ns["_sandbox_db_path"]("darrian")
        assert "sandbox_darrian" in str(path)
        assert path.suffix == ".db"

    def test_sandbox_db_path_sanitizes_special_chars(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        path = ns["_sandbox_db_path"]("user@evil/../etc/passwd")
        # Should not contain slashes or @ symbols in filename
        assert "/" not in path.name
        assert "@" not in path.name

    def test_init_sandbox_db_creates_tables(self, tmp_db, tmp_path, monkeypatch):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        # Redirect DATA_DIR to tmp_path so we don't pollute real data/
        from pathlib import Path
        monkeypatch.setitem(ns, "DATA_DIR", tmp_path)
        # Re-define sandbox db path using patched DATA_DIR
        def patched_path(username):
            safe = "".join(c for c in username if c.isalnum() or c in "-_")
            return tmp_path / f"sandbox_{safe}.db"
        monkeypatch.setitem(ns, "_sandbox_db_path", patched_path)
        ns["_init_sandbox_db"]("testuser")
        db_file = tmp_path / "sandbox_testuser.db"
        assert db_file.exists()
        conn = sqlite3.connect(str(db_file))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "expenses" in tables
        assert "income" in tables
        assert "pa_tasks" in tables
        assert "sandbox_meta" in tables

    def test_sandbox_summary_returns_dict(self, tmp_db, tmp_path, monkeypatch):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        from pathlib import Path
        monkeypatch.setitem(ns, "DATA_DIR", tmp_path)
        def patched_path(username):
            safe = "".join(c for c in username if c.isalnum() or c in "-_")
            return tmp_path / f"sandbox_{safe}.db"
        monkeypatch.setitem(ns, "_sandbox_db_path", patched_path)
        def patched_conn(username):
            path = patched_path(username)
            c = sqlite3.connect(str(path), check_same_thread=False)
            c.row_factory = sqlite3.Row
            return c
        monkeypatch.setitem(ns, "_get_sandbox_conn", patched_conn)
        ns["_init_sandbox_db"]("summaryuser")
        summary = ns["_sandbox_summary"]("summaryuser")
        assert isinstance(summary, dict)
        assert "expenses" in summary
        assert summary["expenses"] == 0

    def test_export_sandbox_as_json(self, tmp_db, tmp_path, monkeypatch):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        from pathlib import Path
        monkeypatch.setitem(ns, "DATA_DIR", tmp_path)
        def patched_path(username):
            safe = "".join(c for c in username if c.isalnum() or c in "-_")
            return tmp_path / f"sandbox_{safe}.db"
        monkeypatch.setitem(ns, "_sandbox_db_path", patched_path)
        def patched_conn(username):
            path = patched_path(username)
            c = sqlite3.connect(str(path), check_same_thread=False)
            c.row_factory = sqlite3.Row
            return c
        monkeypatch.setitem(ns, "_get_sandbox_conn", patched_conn)
        ns["_init_sandbox_db"]("exportuser")
        json_str = ns["_export_sandbox_as_json"]("exportuser")
        data = json.loads(json_str)
        assert "exported_at" in data
        assert "tables" in data
        assert "expenses" in data["tables"]

    def test_wipe_sandbox_db_deletes_file(self, tmp_db, tmp_path, monkeypatch):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        from pathlib import Path
        monkeypatch.setitem(ns, "DATA_DIR", tmp_path)
        def patched_path(username):
            safe = "".join(c for c in username if c.isalnum() or c in "-_")
            return tmp_path / f"sandbox_{safe}.db"
        monkeypatch.setitem(ns, "_sandbox_db_path", patched_path)
        def patched_conn(username):
            path = patched_path(username)
            c = sqlite3.connect(str(path), check_same_thread=False)
            c.row_factory = sqlite3.Row
            return c
        monkeypatch.setitem(ns, "_get_sandbox_conn", patched_conn)
        ns["_init_sandbox_db"]("wipeuser")
        db_file = patched_path("wipeuser")
        assert db_file.exists()
        ns["_wipe_sandbox_db"]("wipeuser")
        assert not db_file.exists()

    def test_wipe_nonexistent_db_does_not_raise(self, tmp_db, tmp_path, monkeypatch):
        _, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        from pathlib import Path
        monkeypatch.setitem(ns, "DATA_DIR", tmp_path)
        def patched_path(username):
            return tmp_path / f"sandbox_{username}.db"
        monkeypatch.setitem(ns, "_sandbox_db_path", patched_path)
        # Should not raise even if file doesn't exist
        ns["_wipe_sandbox_db"]("ghostuser")

    def test_expire_old_sandboxes(self, tmp_db, tmp_path, monkeypatch):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        monkeypatch.setitem(ns, "DATA_DIR", tmp_path)
        def patched_path(username):
            return tmp_path / f"sandbox_{username}.db"
        monkeypatch.setitem(ns, "_sandbox_db_path", patched_path)
        ns["_ensure_tables"]()
        ns["_grant_sandbox"]("staleuser", "darrian")
        # Set last_accessed to 30 days ago (exceeds SANDBOX_TTL_DAYS=7)
        old_time = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        conn = fake_get_conn()
        conn.execute(
            "UPDATE sandbox_grants SET last_accessed = ? WHERE username = 'staleuser'",
            (old_time,)
        )
        conn.commit()
        conn.close()
        expired = ns["_expire_old_sandboxes"]()
        assert "staleuser" in expired

    def test_fmt_bytes(self, tmp_db):
        ns = _extract_helpers(SANDBOX_PAGE)
        assert "B" in ns["_fmt_bytes"](500)
        assert "KB" in ns["_fmt_bytes"](2048)
        assert "MB" in ns["_fmt_bytes"](2 * 1024 * 1024)

    def test_sandbox_ttl_days_constant(self):
        ns = _extract_helpers(SANDBOX_PAGE)
        assert "SANDBOX_TTL_DAYS" in ns
        assert ns["SANDBOX_TTL_DAYS"] > 0

    def test_update_last_accessed(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(SANDBOX_PAGE)
        ns["_ensure_tables"]()
        ns["_grant_sandbox"]("accesstest", "darrian")
        ns["_update_last_accessed"]("accesstest")
        conn = fake_get_conn()
        row = dict(conn.execute(
            "SELECT last_accessed FROM sandbox_grants WHERE username='accesstest'"
        ).fetchone())
        conn.close()
        assert row["last_accessed"] is not None


# ══════════════════════════════════════════════════════════════════════════════
# ── TESTS: pages/30_agent_dashboard.py scheduled tasks ───────────────────────
# ══════════════════════════════════════════════════════════════════════════════

class TestScheduledAgentTasks:
    """Tests for the scheduled tasks feature in the Agent Dashboard."""

    def test_agent_dashboard_page_exists(self):
        assert os.path.isfile(AGENT_PAGE)

    def test_agent_dashboard_syntax(self):
        compile(open(AGENT_PAGE).read(), AGENT_PAGE, "exec")

    def test_ensure_tables_creates_agent_scheduled_tasks(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_scheduled_tasks'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_calc_next_run_daily(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        result = ns["_calc_next_run"]("daily", 0, 2)  # 2 AM daily
        dt = datetime.strptime(result[:16], "%Y-%m-%d %H:%M")
        assert dt > datetime.now()
        assert dt.hour == 2

    def test_calc_next_run_weekly(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        result = ns["_calc_next_run"]("weekly", 0, 8)  # Monday 8 AM
        dt = datetime.strptime(result[:16], "%Y-%m-%d %H:%M")
        assert dt > datetime.now()
        assert dt.weekday() == 0  # Monday
        assert dt.hour == 8

    def test_calc_next_run_monthly(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        result = ns["_calc_next_run"]("monthly", 1, 9)  # 1st of month 9 AM
        dt = datetime.strptime(result[:16], "%Y-%m-%d %H:%M")
        assert dt > datetime.now()
        assert dt.day == 1
        assert dt.hour == 9

    def test_create_scheduled_task_inserts_row(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_create_scheduled_task"](
            "Weekly Digest", "Send weekly report", "page 56",
            "weekly", 0, 8, "darrian"
        )
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT * FROM agent_scheduled_tasks WHERE task_name='Weekly Digest'"
        ).fetchone()
        conn.close()
        assert row is not None
        d = dict(row)
        assert d["schedule_type"] == "weekly"
        assert d["schedule_day"] == 0
        assert d["schedule_hour"] == 8
        assert d["enabled"] == 1

    def test_list_scheduled_tasks_returns_list(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_create_scheduled_task"]("Task A", "", "", "daily", 0, 7, "darrian")
        ns["_create_scheduled_task"]("Task B", "", "", "weekly", 1, 9, "darrian")
        tasks = ns["_list_scheduled_tasks"]()
        assert isinstance(tasks, list)
        assert len(tasks) == 2

    def test_toggle_scheduled_task_disable(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_create_scheduled_task"]("Toggle Test", "", "", "daily", 0, 7, "darrian")
        conn = fake_get_conn()
        tid = conn.execute("SELECT id FROM agent_scheduled_tasks WHERE task_name='Toggle Test'").fetchone()[0]
        conn.close()
        ns["_toggle_scheduled_task"](tid, False)
        conn = fake_get_conn()
        row = dict(conn.execute("SELECT enabled FROM agent_scheduled_tasks WHERE id=?", (tid,)).fetchone())
        conn.close()
        assert row["enabled"] == 0

    def test_toggle_scheduled_task_enable(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_create_scheduled_task"]("Enable Test", "", "", "daily", 0, 10, "darrian")
        conn = fake_get_conn()
        tid = conn.execute("SELECT id FROM agent_scheduled_tasks WHERE task_name='Enable Test'").fetchone()[0]
        conn.close()
        ns["_toggle_scheduled_task"](tid, False)
        ns["_toggle_scheduled_task"](tid, True)
        conn = fake_get_conn()
        row = dict(conn.execute("SELECT enabled FROM agent_scheduled_tasks WHERE id=?", (tid,)).fetchone())
        conn.close()
        assert row["enabled"] == 1

    def test_delete_scheduled_task(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_create_scheduled_task"]("Delete Me", "", "", "monthly", 1, 9, "darrian")
        conn = fake_get_conn()
        tid = conn.execute("SELECT id FROM agent_scheduled_tasks WHERE task_name='Delete Me'").fetchone()[0]
        conn.close()
        ns["_delete_scheduled_task"](tid)
        conn = fake_get_conn()
        row = conn.execute("SELECT id FROM agent_scheduled_tasks WHERE id=?", (tid,)).fetchone()
        conn.close()
        assert row is None

    def test_seed_default_tasks_populates_table(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_seed_default_scheduled_tasks"]("darrian")
        tasks = ns["_list_scheduled_tasks"]()
        assert len(tasks) >= 4
        task_names = [t["task_name"] for t in tasks]
        assert "Weekly Spending Digest" in task_names
        assert "Daily Price Alert Refresh" in task_names

    def test_seed_does_not_duplicate_if_called_twice(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_seed_default_scheduled_tasks"]("darrian")
        ns["_seed_default_scheduled_tasks"]("darrian")  # called again
        tasks = ns["_list_scheduled_tasks"]()
        assert len(tasks) == len(set(t["task_name"] for t in tasks))  # no duplicates

    def test_next_run_is_in_future(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        ns["_create_scheduled_task"]("Future Check", "", "", "weekly", 3, 22, "darrian")
        tasks = ns["_list_scheduled_tasks"]()
        assert len(tasks) == 1
        next_run_str = tasks[0]["next_run"]
        dt = datetime.strptime(next_run_str[:16], "%Y-%m-%d %H:%M")
        assert dt > datetime.now()

    def test_agent_runs_table_created(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_runs'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_agent_log_table_created(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(AGENT_PAGE)
        ns["_ensure_tables"]()
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_log'"
        ).fetchone()
        conn.close()
        assert row is not None
