"""
tests/unit/test_token_tracking.py

Unit tests for token tracking + BYOK feature:
  1. token_usage table creation
  2. log_token_usage() writes a row
  3. get_token_usage_summary() returns correct aggregates
  4. get_token_usage_detail() returns rows in order
  5. used_byok flag is stored correctly
  6. utils/ai.py importable
  7. get_api_key() BYOK session-state priority
  8. call_claude() returns error string when no key available
  9. call_claude() logs token usage on success (mocked)
 10. Page 57 importable
"""

import os
import sys
import types
import sqlite3
import importlib
import unittest
from unittest.mock import MagicMock, patch

# ── Point tests at the project root ──────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _stub_streamlit():
    """Minimal streamlit stub for test environments without a running server."""
    if "streamlit" in sys.modules:
        return sys.modules["streamlit"]
    mod = types.ModuleType("streamlit")
    mod.set_page_config = lambda **k: None
    mod.markdown = lambda *a, **k: None
    mod.title = lambda *a, **k: None
    mod.write = lambda *a, **k: None
    mod.stop = lambda: None
    mod.rerun = lambda: None
    mod.session_state = {}
    mod.sidebar = types.SimpleNamespace(
        markdown=lambda *a, **k: None,
        page_link=lambda *a, **k: None,
    )
    sys.modules["streamlit"] = mod
    return mod


# Stub streamlit before importing utils.db or utils.ai so their top-level
# `import streamlit as st` doesn't fail in headless test environments.
_stub_streamlit()

# Use an in-memory SQLite DB so tests never touch production data
import utils.db as db_module

_TEST_DB = ":memory:"


def _make_test_conn():
    conn = sqlite3.connect(_TEST_DB)
    conn.row_factory = sqlite3.Row
    return conn


# Patch get_auth_conn to return an in-memory DB for all tests
class TokenTrackingTests(unittest.TestCase):

    def setUp(self):
        """Create a fresh in-memory DB with the token_usage table for each test."""
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("""CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            site TEXT NOT NULL DEFAULT 'pss',
            page TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            used_byok INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY, value TEXT
        )""")
        self._conn.commit()

    def tearDown(self):
        self._conn.close()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _patch_auth_conn(self):
        """Return a patcher that routes get_auth_conn() to our in-memory DB.

        Uses a MagicMock wrapper that intercepts close() calls so the shared
        self._conn stays open for post-call assertions.  All other methods
        (execute, cursor, commit, …) are forwarded to the real connection.
        """
        real_conn = self._conn
        mock_conn = MagicMock(wraps=real_conn)
        mock_conn.close = MagicMock(return_value=None)   # no-op — keep conn alive
        patcher = patch.object(db_module, "get_auth_conn", return_value=mock_conn)
        return patcher

    # ── 1. Table creation ─────────────────────────────────────────────────────
    def test_ensure_token_usage_table_creates_table(self):
        """_ensure_token_usage_table() should not raise even if table exists."""
        with self._patch_auth_conn():
            db_module._ensure_token_usage_table()
        cur = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='token_usage'")
        self.assertIsNotNone(cur.fetchone(), "token_usage table should exist")

    # ── 2. log_token_usage writes a row ───────────────────────────────────────
    def test_log_token_usage_inserts_row(self):
        with self._patch_auth_conn():
            db_module.log_token_usage(
                user_email="test@example.com",
                page="test_page",
                model="claude-opus-4-5",
                input_tokens=100,
                output_tokens=200,
                site="pss",
                used_byok=False,
            )
        row = self._conn.execute("SELECT * FROM token_usage").fetchone()
        self.assertIsNotNone(row, "Should have inserted one row")
        self.assertEqual(row["user_email"], "test@example.com")
        self.assertEqual(row["input_tokens"], 100)
        self.assertEqual(row["output_tokens"], 200)
        self.assertEqual(row["total_tokens"], 300)
        self.assertEqual(row["used_byok"], 0)

    # ── 3. log_token_usage with BYOK=True ─────────────────────────────────────
    def test_log_token_usage_byok_flag(self):
        with self._patch_auth_conn():
            db_module.log_token_usage(
                user_email="byok@example.com",
                page="some_page",
                model="claude-haiku-3-5",
                input_tokens=50,
                output_tokens=80,
                site="soleops",
                used_byok=True,
            )
        row = self._conn.execute("SELECT * FROM token_usage WHERE user_email='byok@example.com'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["used_byok"], 1)
        self.assertEqual(row["site"], "soleops")

    # ── 4. get_token_usage_summary aggregates ─────────────────────────────────
    def test_get_token_usage_summary(self):
        # Insert two rows for same user
        self._conn.execute(
            "INSERT INTO token_usage (user_email, site, page, model, input_tokens, output_tokens, total_tokens, used_byok) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("agg@test.com", "pss", "pg1", "claude-opus-4-5", 100, 200, 300, 0)
        )
        self._conn.execute(
            "INSERT INTO token_usage (user_email, site, page, model, input_tokens, output_tokens, total_tokens, used_byok) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("agg@test.com", "pss", "pg2", "claude-opus-4-5", 50, 75, 125, 1)
        )
        self._conn.commit()
        with self._patch_auth_conn():
            summary = db_module.get_token_usage_summary()
        self.assertEqual(len(summary), 1)
        row = summary[0]
        self.assertEqual(row["user_email"], "agg@test.com")
        self.assertEqual(int(row["calls"]), 2)
        self.assertEqual(int(row["total_input"]), 150)
        self.assertEqual(int(row["total_output"]), 275)
        self.assertEqual(int(row["total_tokens"]), 425)
        self.assertEqual(int(row["byok_calls"]), 1)

    # ── 5. get_token_usage_detail returns rows in DESC order ──────────────────
    def test_get_token_usage_detail_ordering(self):
        self._conn.execute(
            "INSERT INTO token_usage (user_email, site, page, model, input_tokens, output_tokens, total_tokens, used_byok, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("order@test.com", "pss", "page_a", "claude-opus-4-5", 10, 20, 30, 0, "2026-01-01 10:00:00")
        )
        self._conn.execute(
            "INSERT INTO token_usage (user_email, site, page, model, input_tokens, output_tokens, total_tokens, used_byok, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ("order@test.com", "pss", "page_b", "claude-opus-4-5", 20, 30, 50, 0, "2026-01-02 10:00:00")
        )
        self._conn.commit()
        with self._patch_auth_conn():
            detail = db_module.get_token_usage_detail(user_email="order@test.com", limit=10)
        self.assertEqual(len(detail), 2)
        # Most recent first
        self.assertEqual(detail[0]["page"], "page_b")
        self.assertEqual(detail[1]["page"], "page_a")

    # ── 6. get_token_usage_detail with no filter returns all rows ─────────────
    def test_get_token_usage_detail_no_filter(self):
        for i in range(3):
            self._conn.execute(
                "INSERT INTO token_usage (user_email, site, page, model, input_tokens, output_tokens, total_tokens, used_byok) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (f"user{i}@test.com", "pss", "pg", "claude-opus-4-5", i * 10, i * 20, i * 30, 0)
            )
        self._conn.commit()
        with self._patch_auth_conn():
            detail = db_module.get_token_usage_detail(limit=50)
        self.assertEqual(len(detail), 3)


# ── utils/ai.py tests ─────────────────────────────────────────────────────────
class AIUtilsImportTest(unittest.TestCase):

    def test_ai_module_importable(self):
        """utils/ai.py should import without errors."""
        import utils.ai as ai_module
        self.assertTrue(hasattr(ai_module, "call_claude"))
        self.assertTrue(hasattr(ai_module, "get_api_key"))
        self.assertTrue(hasattr(ai_module, "render_byok_expander"))
        self.assertTrue(hasattr(ai_module, "DEFAULT_MODEL"))

    def test_call_claude_no_key_returns_warning(self):
        """call_claude() should return an error string when no key is available."""
        import utils.ai as ai_module

        # Patch session state to have no byok key and app key empty
        mock_session = {}
        with patch("utils.ai.st") as mock_st, \
             patch("utils.ai.get_setting", return_value=""):
            mock_st.session_state = mock_session
            text, usage = ai_module.call_claude(
                messages=[{"role": "user", "content": "hello"}],
                user_email="test@test.com",
            )
        self.assertTrue(text.startswith("⚠️"), f"Expected warning, got: {text}")
        self.assertEqual(usage["input_tokens"], 0)
        self.assertEqual(usage["output_tokens"], 0)

    def test_get_api_key_prefers_byok(self):
        """get_api_key() should return the BYOK session key over the app key."""
        import utils.ai as ai_module

        mock_session = {"byok_api_key": "sk-ant-test-byok-key"}
        with patch("utils.ai.st") as mock_st, \
             patch("utils.ai.get_setting", return_value="sk-ant-app-key"):
            mock_st.session_state = mock_session
            key, is_byok = ai_module.get_api_key("test@test.com")

        self.assertEqual(key, "sk-ant-test-byok-key")
        self.assertTrue(is_byok)

    def test_get_api_key_falls_back_to_app_key(self):
        """get_api_key() should return the app key when no BYOK key is set."""
        import utils.ai as ai_module

        mock_session = {}
        with patch("utils.ai.st") as mock_st, \
             patch("utils.ai.get_setting", return_value="sk-ant-app-key"):
            mock_st.session_state = mock_session
            key, is_byok = ai_module.get_api_key("test@test.com")

        self.assertEqual(key, "sk-ant-app-key")
        self.assertFalse(is_byok)

    def test_call_claude_logs_tokens_on_success(self):
        """call_claude() should call log_token_usage after a successful API response."""
        import utils.ai as ai_module

        # Build a fake Anthropic response
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text="Hello!")]
        fake_response.usage.input_tokens = 42
        fake_response.usage.output_tokens = 17

        mock_session = {}
        with patch("utils.ai.st") as mock_st, \
             patch("utils.ai.get_setting", return_value="sk-ant-fakekey"), \
             patch("utils.ai.log_token_usage") as mock_log, \
             patch("anthropic.Anthropic") as MockAnthropic:
            mock_st.session_state = mock_session
            MockAnthropic.return_value.messages.create.return_value = fake_response

            text, usage = ai_module.call_claude(
                messages=[{"role": "user", "content": "test"}],
                page="test_page",
                site="pss",
                user_email="track@test.com",
            )

        self.assertEqual(text, "Hello!")
        self.assertEqual(usage["input_tokens"], 42)
        self.assertEqual(usage["output_tokens"], 17)
        mock_log.assert_called_once_with(
            user_email="track@test.com",
            page="test_page",
            model=ai_module.DEFAULT_MODEL,
            input_tokens=42,
            output_tokens=17,
            site="pss",
            used_byok=False,
        )

    def test_call_claude_byok_flag_passed_to_log(self):
        """call_claude() should pass used_byok=True when BYOK key is active."""
        import utils.ai as ai_module

        fake_response = MagicMock()
        fake_response.content = [MagicMock(text="Hi!")]
        fake_response.usage.input_tokens = 10
        fake_response.usage.output_tokens = 5

        mock_session = {"byok_api_key": "sk-ant-byok"}
        with patch("utils.ai.st") as mock_st, \
             patch("utils.ai.get_setting", return_value="sk-ant-appkey"), \
             patch("utils.ai.log_token_usage") as mock_log, \
             patch("anthropic.Anthropic") as MockAnthropic:
            mock_st.session_state = mock_session
            MockAnthropic.return_value.messages.create.return_value = fake_response

            _, usage = ai_module.call_claude(
                messages=[{"role": "user", "content": "hi"}],
                user_email="byok_user@test.com",
                page="byok_page",
                site="soleops",
            )

        self.assertTrue(usage["used_byok"])
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args
        self.assertTrue(call_kwargs.kwargs.get("used_byok") or
                        (call_kwargs.args and call_kwargs.args[-1] is True))


# ── Page 58 import test ───────────────────────────────────────────────────────
class Page57ImportTest(unittest.TestCase):

    def test_page_57_syntax(self):
        """pages/58_token_usage_dashboard.py should compile without errors."""
        import py_compile
        page_path = os.path.join(PROJECT_ROOT, "pages", "58_token_usage_dashboard.py")
        result = py_compile.compile(page_path, doraise=True)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
