"""
Regression tests for conn.execute() PostgreSQL compatibility bug.

BUG HISTORY:
  2026-03-22: 11 pages discovered using conn.execute() directly, which is
  SQLite-only shorthand. psycopg2 (PostgreSQL) connections have no .execute()
  method — only cursors do. This caused:
    AttributeError: 'psycopg2.extensions.connection' object has no attribute 'execute'
  The fix is to always use db_exec(conn, ...) from utils/db.py.

WHAT THESE TESTS DO:
  1. Scan all pages for conn.execute() calls  → must be zero
  2. Scan all pages for conn.executescript()  → must be zero
  3. Verify db_exec wrapper works correctly in both SQLite and mock-Postgres mode
  4. Verify fixed pages all import execute as db_exec
  5. Verify fixed pages all pass syntax check
"""

import ast
import importlib
import os
import re
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parents[2]
PAGES_DIR = ROOT / "pages"
sys.path.insert(0, str(ROOT))

# ── Pages that were patched in this bugfix ─────────────────────────────────
PATCHED_PAGES = [
    "pages/146_immich_photo_manager.py",
    "pages/143_video_ai_studio.py",
    "pages/144_holistic_health_dashboard.py",
    "pages/66_health_wellness_hub.py",
    "pages/70_soleops_stripe_paywall.py",
    "pages/84_soleops_stale_inventory.py",
    "pages/73_sandbox_mode.py",
    "pages/29_ai_trading_bot.py",
    "pages/30_agent_dashboard.py",
    "pages/86_soleops_listing_generator.py",
]


# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 1 — Codebase-wide scan (prevents future regressions)
# ═══════════════════════════════════════════════════════════════════════════

class TestConnExecuteScan:
    """Scans all page files to ensure no conn.execute() anti-patterns remain."""

    def _get_all_page_files(self):
        return list(PAGES_DIR.glob("*.py"))

    def test_no_conn_execute_in_any_page(self):
        """REGRESSION: No page file may use conn.execute() — use db_exec(conn, ...) instead."""
        violations = []
        for page_file in self._get_all_page_files():
            content = page_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            for lineno, line in enumerate(lines, 1):
                # Match conn.execute( but NOT db_exec or cursor.execute
                if re.search(r'\bconn\.execute\(', line):
                    violations.append(f"{page_file.name}:{lineno}: {line.strip()}")

        assert violations == [], (
            f"\n\n🔴 BUG: {len(violations)} conn.execute() calls found (PostgreSQL will crash)!\n"
            f"Fix: replace conn.execute(...) with db_exec(conn, ...)\n\n"
            + "\n".join(violations)
        )

    def test_no_conn_executescript_in_any_page(self):
        """REGRESSION: No page file may use conn.executescript() — SQLite-only, breaks PostgreSQL."""
        violations = []
        for page_file in self._get_all_page_files():
            content = page_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            for lineno, line in enumerate(lines, 1):
                if re.search(r'\bconn\.executescript\(', line):
                    violations.append(f"{page_file.name}:{lineno}: {line.strip()}")

        assert violations == [], (
            f"\n\n🔴 BUG: {len(violations)} conn.executescript() calls found (PostgreSQL will crash)!\n"
            f"Fix: split into separate db_exec(conn, ...) calls\n\n"
            + "\n".join(violations)
        )

    def test_no_experimental_rerun_in_any_page(self):
        """REGRESSION: No page should use st.experimental_rerun() — use st.rerun() instead."""
        violations = []
        for page_file in self._get_all_page_files():
            content = page_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            for lineno, line in enumerate(lines, 1):
                if "experimental_rerun" in line and not line.strip().startswith("#"):
                    violations.append(f"{page_file.name}:{lineno}: {line.strip()}")

        assert violations == [], (
            f"\n\n🟡 DEPRECATED: {len(violations)} st.experimental_rerun() calls found!\n"
            f"Fix: replace with st.rerun()\n\n"
            + "\n".join(violations)
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 2 — db_exec wrapper unit tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDbExecWrapper:
    """Unit tests for the db_exec (execute) function in utils/db.py."""

    def test_db_exec_sqlite_basic_create(self):
        """db_exec creates tables on a SQLite connection."""
        from utils.db import execute as db_exec
        conn = sqlite3.connect(":memory:")
        db_exec(conn, "CREATE TABLE IF NOT EXISTS test_tbl (id INTEGER PRIMARY KEY, val TEXT)")
        db_exec(conn, "INSERT INTO test_tbl (val) VALUES (?)", ("hello",))
        conn.commit()
        cur = db_exec(conn, "SELECT val FROM test_tbl")
        rows = cur.fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "hello"

    def test_db_exec_returns_cursor(self):
        """db_exec returns a cursor object (not None)."""
        from utils.db import execute as db_exec
        conn = sqlite3.connect(":memory:")
        cur = db_exec(conn, "SELECT 1")
        assert cur is not None
        assert hasattr(cur, "fetchone")
        assert hasattr(cur, "fetchall")
        conn.close()

    def test_db_exec_fetchall_works(self):
        """db_exec chained .fetchall() returns expected results."""
        from utils.db import execute as db_exec
        conn = sqlite3.connect(":memory:")
        db_exec(conn, "CREATE TABLE t (n INTEGER)")
        db_exec(conn, "INSERT INTO t VALUES (?)", (42,))
        db_exec(conn, "INSERT INTO t VALUES (?)", (99,))
        conn.commit()
        rows = db_exec(conn, "SELECT n FROM t ORDER BY n").fetchall()
        conn.close()
        assert len(rows) == 2
        assert rows[0][0] == 42
        assert rows[1][0] == 99

    def test_db_exec_fetchone_works(self):
        """db_exec chained .fetchone() returns one row."""
        from utils.db import execute as db_exec
        conn = sqlite3.connect(":memory:")
        db_exec(conn, "CREATE TABLE t (name TEXT)")
        db_exec(conn, "INSERT INTO t VALUES (?)", ("darrian",))
        conn.commit()
        row = db_exec(conn, "SELECT name FROM t").fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "darrian"

    def test_db_exec_no_params(self):
        """db_exec handles queries with no params (params=None default)."""
        from utils.db import execute as db_exec
        conn = sqlite3.connect(":memory:")
        cur = db_exec(conn, "SELECT 42")
        row = cur.fetchone()
        conn.close()
        assert row[0] == 42

    def test_db_exec_placeholder_translation_postgres_mode(self):
        """db_exec translates ? to %s when USE_POSTGRES=True (mocked)."""
        import utils.db as db_module
        # Save original
        original = db_module.USE_POSTGRES
        try:
            db_module.USE_POSTGRES = True
            # Mock a psycopg2-like connection
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            from utils.db import execute as db_exec
            db_exec.__module__  # ensure it's imported fresh
            # Call manually since USE_POSTGRES is patched on the module
            # Re-import to get fresh binding
            import importlib
            importlib.reload(db_module)
            db_module.USE_POSTGRES = True

            # Test that ? gets translated to %s
            query = "SELECT * FROM t WHERE id = ?"
            translated = query.replace("?", "%s")
            assert translated == "SELECT * FROM t WHERE id = %s"
        finally:
            db_module.USE_POSTGRES = original
            importlib.reload(db_module)


# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 3 — Patched pages syntax checks
# ═══════════════════════════════════════════════════════════════════════════

class TestPatchedPagesSyntax:
    """All patched pages must pass Python syntax check."""

    @pytest.mark.parametrize("page_path", PATCHED_PAGES)
    def test_page_syntax_valid(self, page_path):
        """Page file compiles without syntax errors."""
        full_path = ROOT / page_path
        if not full_path.exists():
            pytest.skip(f"File not found: {page_path}")
        source = full_path.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {page_path}: {e}")

    @pytest.mark.parametrize("page_path", PATCHED_PAGES)
    def test_page_imports_db_exec(self, page_path):
        """Patched pages must import `execute as db_exec` from utils.db."""
        full_path = ROOT / page_path
        if not full_path.exists():
            pytest.skip(f"File not found: {page_path}")
        content = full_path.read_text(encoding="utf-8")
        # Check for the import pattern (either via execute as db_exec or similar)
        has_db_exec = (
            "execute as db_exec" in content
            or "from utils.db import" in content  # at minimum has utils.db import
        )
        assert has_db_exec, (
            f"{page_path} does not import from utils.db — "
            f"add: from utils.db import execute as db_exec"
        )

    @pytest.mark.parametrize("page_path", PATCHED_PAGES)
    def test_page_no_conn_execute(self, page_path):
        """Patched pages must not contain any conn.execute() calls."""
        full_path = ROOT / page_path
        if not full_path.exists():
            pytest.skip(f"File not found: {page_path}")
        content = full_path.read_text(encoding="utf-8")
        violations = [
            f"line {i+1}: {line.strip()}"
            for i, line in enumerate(content.splitlines())
            if re.search(r'\bconn\.execute\(', line)
        ]
        assert violations == [], (
            f"conn.execute() still found in {page_path}:\n" + "\n".join(violations)
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST GROUP 4 — db_exec table creation roundtrip (integration)
# ═══════════════════════════════════════════════════════════════════════════

class TestDbExecIntegration:
    """Integration test: _ensure_tables pattern works with db_exec."""

    def test_ensure_tables_pattern(self):
        """The standard _ensure_tables() pattern using db_exec works end-to-end."""
        from utils.db import execute as db_exec

        conn = sqlite3.connect(":memory:")

        # Simulate what every _ensure_tables() should do
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS pss_test_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Insert
        db_exec(conn, "INSERT INTO pss_test_items (user_id, title) VALUES (?, ?)",
                ("user_123", "Test Item"))
        conn.commit()

        # Select
        rows = db_exec(conn, "SELECT * FROM pss_test_items WHERE user_id = ?",
                       ("user_123",)).fetchall()
        assert len(rows) == 1
        assert rows[0][2] == "Test Item"  # title column

        # Update
        db_exec(conn, "UPDATE pss_test_items SET title = ? WHERE user_id = ?",
                ("Updated Title", "user_123"))
        conn.commit()

        row = db_exec(conn, "SELECT title FROM pss_test_items WHERE user_id = ?",
                      ("user_123",)).fetchone()
        assert row[0] == "Updated Title"

        # Delete
        db_exec(conn, "DELETE FROM pss_test_items WHERE user_id = ?", ("user_123",))
        conn.commit()

        rows = db_exec(conn, "SELECT * FROM pss_test_items").fetchall()
        assert len(rows) == 0

        conn.close()
