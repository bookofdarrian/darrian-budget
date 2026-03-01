"""Unit tests for pages/28_smart_home_connect.py"""
import importlib
import importlib.util
import sqlite3
import sys
import tempfile
import types
import os
import unittest


# ── helpers ────────────────────────────────────────────────────────────────────

class _FakeCtx:
    """Minimal context manager stub for st.tabs(), st.expander(), st.columns(), etc."""
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    # column/tab attribute stubs so code inside `with tab:` can call st-like methods
    def __getattr__(self, name):
        return lambda *a, **k: _FakeCtx()


def _make_col_list(spec):
    """Return the right number of _FakeCtx columns based on spec."""
    if isinstance(spec, int):
        n = spec
    elif isinstance(spec, (list, tuple)):
        n = len(spec)
    else:
        n = 5
    return [_FakeCtx() for _ in range(max(n, 1))]


def _stub_streamlit():
    """Return a minimal streamlit stub module."""
    mod = types.ModuleType("streamlit")
    mod.set_page_config = lambda **k: None
    mod.markdown = lambda *a, **k: None
    mod.title = lambda *a, **k: None
    mod.caption = lambda *a, **k: None
    mod.write = lambda *a, **k: None
    mod.columns = lambda spec, *a, **k: _make_col_list(spec)
    mod.sidebar = types.SimpleNamespace(
        markdown=lambda *a, **k: None,
        page_link=lambda *a, **k: None,
    )
    mod.tabs = lambda labels: [_FakeCtx() for _ in labels]
    mod.expander = lambda *a, **k: _FakeCtx()
    mod.divider = lambda: None
    mod.subheader = lambda *a, **k: None
    mod.info = lambda *a, **k: None
    mod.success = lambda *a, **k: None
    mod.progress = lambda *a, **k: None
    mod.code = lambda *a, **k: None
    mod.metric = lambda *a, **k: None
    mod.rerun = lambda: None
    return mod


def _load_page(db_path: str):
    """Import the page module with a live SQLite DB at db_path."""
    # Stub streamlit FIRST — utils.auth imports it at module level
    sys.modules["streamlit"] = _stub_streamlit()

    import utils.db as db_mod
    import utils.auth as auth_mod

    # Each call to get_conn opens a fresh connection to the file-based DB
    def _make_conn():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        return c

    db_mod.get_conn = _make_conn
    db_mod.USE_POSTGRES = False
    db_mod.execute = lambda conn, sql, params=None: conn.execute(sql, params or [])
    db_mod.init_db = lambda: None
    db_mod.get_setting = lambda k: None
    db_mod.set_setting = lambda k, v: None

    auth_mod.require_login = lambda: None
    auth_mod.render_sidebar_brand = lambda: None
    auth_mod.render_sidebar_user_widget = lambda: None
    auth_mod.inject_css = lambda: None

    spec = importlib.util.spec_from_file_location(
        f"p28_{os.path.basename(db_path)}", "pages/28_smart_home_connect.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── tests ──────────────────────────────────────────────────────────────────────

class TestSmartHomeConnectConstants(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.unlink(self.tmp)

    def test_phase_steps_nonempty(self):
        """PHASE1/2/3_STEPS and QUICK_WINS are non-empty lists."""
        mod = _load_page(self.tmp)
        self.assertIsInstance(mod.PHASE1_STEPS, list)
        self.assertGreater(len(mod.PHASE1_STEPS), 0, "PHASE1_STEPS should not be empty")
        self.assertIsInstance(mod.PHASE2_STEPS, list)
        self.assertGreater(len(mod.PHASE2_STEPS), 0, "PHASE2_STEPS should not be empty")
        self.assertIsInstance(mod.PHASE3_STEPS, list)
        self.assertGreater(len(mod.PHASE3_STEPS), 0, "PHASE3_STEPS should not be empty")
        self.assertIsInstance(mod.QUICK_WINS, list)
        self.assertGreater(len(mod.QUICK_WINS), 0, "QUICK_WINS should not be empty")

    def test_step_tuples_have_required_fields(self):
        """Each PHASE step tuple has at least (step_key, label, tip)."""
        mod = _load_page(self.tmp)
        for step in mod.PHASE1_STEPS + mod.PHASE2_STEPS + mod.PHASE3_STEPS:
            self.assertGreaterEqual(len(step), 3, f"Step tuple too short: {step}")
            self.assertIsInstance(step[0], str, "step_key must be a string")


class TestSmartHomeConnectDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.unlink(self.tmp)

    def test_ensure_tables_creates_table(self):
        """_ensure_tables() creates the smart_home_connect table."""
        _load_page(self.tmp)
        conn = sqlite3.connect(self.tmp)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='smart_home_connect'"
        )
        self.assertIsNotNone(cur.fetchone(), "smart_home_connect table must exist")
        conn.close()

    def test_load_progress_returns_dict(self):
        """_load_progress() returns a dict (empty initially)."""
        mod = _load_page(self.tmp)
        result = mod._load_progress()
        self.assertIsInstance(result, dict)

    def test_set_and_load_step(self):
        """_set_step persists a step; _load_progress retrieves it."""
        mod = _load_page(self.tmp)
        mod._set_step("test_key", True)
        progress = mod._load_progress()
        self.assertIn("test_key", progress)
        self.assertTrue(progress["test_key"]["done"])

    def test_set_step_undo(self):
        """_set_step can mark a step done then undone."""
        mod = _load_page(self.tmp)
        mod._set_step("undo_key", True)
        mod._set_step("undo_key", False)
        progress = mod._load_progress()
        self.assertFalse(bool(progress["undo_key"]["done"]))


class TestSmartHomeConnectHelpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        self.mod = _load_page(self.tmp)

    def tearDown(self):
        if os.path.exists(self.tmp):
            os.unlink(self.tmp)

    def test_pct_empty(self):
        self.assertEqual(self.mod._pct({}, []), 0)

    def test_pct_half(self):
        prog = {"a": {"done": 1}, "b": {"done": 0}}
        self.assertEqual(self.mod._pct(prog, ["a", "b"]), 50)

    def test_pct_full(self):
        prog = {"a": {"done": 1}, "b": {"done": 1}}
        self.assertEqual(self.mod._pct(prog, ["a", "b"]), 100)

    def test_pct_none_done(self):
        prog = {"a": {"done": 0}}
        self.assertEqual(self.mod._pct(prog, ["a"]), 0)


if __name__ == "__main__":
    unittest.main()
