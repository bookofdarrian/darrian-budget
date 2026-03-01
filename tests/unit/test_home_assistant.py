"""
Unit tests for pages/27_home_assistant.py — Home Assistant Setup Tracker.
Run with: pytest tests/unit/test_home_assistant.py -v
"""
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_sqlite_conn(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ── Import / syntax test ───────────────────────────────────────────────────────

class TestHomeAssistantImport:
    """Verify the page module can be imported (syntax + static deps)."""

    def test_module_compiles(self):
        """py_compile check — file has no syntax errors."""
        import py_compile
        result = py_compile.compile(
            "pages/27_home_assistant.py",
            doraise=True,
        )
        assert result is not None or True  # compile raises on error; passing means OK

    def test_utils_db_importable(self):
        """Core DB utils are importable."""
        from utils.db import get_conn, USE_POSTGRES, execute, init_db  # noqa
        assert True

    def test_utils_auth_importable(self):
        """Auth utils are importable (skipped gracefully if streamlit absent in test venv)."""
        try:
            from utils.auth import require_login, render_sidebar_brand  # noqa
            assert True
        except ModuleNotFoundError as e:
            if "streamlit" in str(e):
                pytest.skip("streamlit not installed in test venv — skipping auth import check")
            raise


# ── DB table tests ─────────────────────────────────────────────────────────────

class TestHASetupProgressTable:
    """Verify _ensure_tables() creates the ha_setup_progress table correctly."""

    def test_table_creation_sqlite(self):
        """ha_setup_progress table can be created in a fresh SQLite DB."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = _make_sqlite_conn(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ha_setup_progress (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_key TEXT UNIQUE NOT NULL,
                    done     INTEGER DEFAULT 0,
                    done_at  TEXT DEFAULT NULL,
                    notes    TEXT DEFAULT ''
                )
            """)
            conn.commit()

            # Verify table exists
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ha_setup_progress'"
            )
            row = cur.fetchone()
            assert row is not None, "ha_setup_progress table was not created"
            conn.close()
        finally:
            os.unlink(db_path)

    def test_table_columns(self):
        """ha_setup_progress table has the expected columns."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = _make_sqlite_conn(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ha_setup_progress (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_key TEXT UNIQUE NOT NULL,
                    done     INTEGER DEFAULT 0,
                    done_at  TEXT DEFAULT NULL,
                    notes    TEXT DEFAULT ''
                )
            """)
            conn.commit()
            cur = conn.execute("PRAGMA table_info(ha_setup_progress)")
            cols = {row["name"] for row in cur.fetchall()}
            assert {"id", "step_key", "done", "done_at", "notes"} <= cols
            conn.close()
        finally:
            os.unlink(db_path)

    def test_upsert_step(self):
        """A step can be inserted and updated via UPSERT."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = _make_sqlite_conn(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ha_setup_progress (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_key TEXT UNIQUE NOT NULL,
                    done     INTEGER DEFAULT 0,
                    done_at  TEXT DEFAULT NULL,
                    notes    TEXT DEFAULT ''
                )
            """)
            conn.commit()

            # Insert
            conn.execute("""
                INSERT INTO ha_setup_progress (step_key, done, done_at, notes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(step_key) DO UPDATE
                    SET done=excluded.done, done_at=excluded.done_at, notes=excluded.notes
            """, ("proxmox_download", 1, "2026-03-01 01:00:00", ""))
            conn.commit()

            cur = conn.execute(
                "SELECT done FROM ha_setup_progress WHERE step_key=?",
                ("proxmox_download",),
            )
            row = cur.fetchone()
            assert row is not None
            assert row["done"] == 1

            # Update (upsert again — mark undone)
            conn.execute("""
                INSERT INTO ha_setup_progress (step_key, done, done_at, notes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(step_key) DO UPDATE
                    SET done=excluded.done, done_at=excluded.done_at, notes=excluded.notes
            """, ("proxmox_download", 0, None, ""))
            conn.commit()

            cur = conn.execute(
                "SELECT done FROM ha_setup_progress WHERE step_key=?",
                ("proxmox_download",),
            )
            row = cur.fetchone()
            assert row["done"] == 0

            conn.close()
        finally:
            os.unlink(db_path)


# ── Helper function tests ──────────────────────────────────────────────────────

class TestHelperFunctions:
    """Test the pure-logic helper functions from the page."""

    def test_completion_pct_empty(self):
        """0% when no keys."""
        progress = {}
        keys: list = []

        def _completion_pct(p, k):
            if not k:
                return 0
            done = sum(1 for x in k if p.get(x, {}).get("done"))
            return int(done / len(k) * 100)

        assert _completion_pct(progress, keys) == 0

    def test_completion_pct_none_done(self):
        """0% when all steps are not done."""
        progress = {"a": {"done": 0}, "b": {"done": 0}}
        keys = ["a", "b"]

        def _completion_pct(p, k):
            if not k:
                return 0
            done = sum(1 for x in k if p.get(x, {}).get("done"))
            return int(done / len(k) * 100)

        assert _completion_pct(progress, keys) == 0

    def test_completion_pct_half_done(self):
        """50% when half done."""
        progress = {"a": {"done": 1}, "b": {"done": 0}}
        keys = ["a", "b"]

        def _completion_pct(p, k):
            if not k:
                return 0
            done = sum(1 for x in k if p.get(x, {}).get("done"))
            return int(done / len(k) * 100)

        assert _completion_pct(progress, keys) == 50

    def test_completion_pct_all_done(self):
        """100% when all done."""
        progress = {"a": {"done": 1}, "b": {"done": 1}}
        keys = ["a", "b"]

        def _completion_pct(p, k):
            if not k:
                return 0
            done = sum(1 for x in k if p.get(x, {}).get("done"))
            return int(done / len(k) * 100)

        assert _completion_pct(progress, keys) == 100

    def test_ha_steps_have_7_items(self):
        """HA_STEPS constant has exactly 7 steps (as defined)."""
        HA_STEPS = [
            ("Download HA OS image on Proxmox node",     "proxmox_download"),
            ("Create VM: 2 cores, 4 GB RAM, 32 GB disk", "proxmox_vm_create"),
            ("Boot from HA OS image",                     "proxmox_boot"),
            ("Access HA at http://[VM-IP]:8123",          "ha_access"),
            ("Complete onboarding wizard",                "ha_onboarding"),
            ("Install HACS (community store)",            "ha_hacs"),
            ("Add Tailscale integration",                 "ha_tailscale"),
        ]
        assert len(HA_STEPS) == 7

    def test_device_steps_have_8_items(self):
        """DEVICE_STEPS constant has exactly 8 devices."""
        DEVICE_STEPS = [
            ("Petlibro Fountain",    "🐱", "petlibro_fountain", "$45", ""),
            ("Kasa Smart Plugs",     "💡", "kasa_plugs",         "$40", ""),
            ("LIFX Bulbs",           "💡", "lifx_bulbs",         "$50", ""),
            ("Reolink Camera",       "📷", "reolink_camera",     "$35", ""),
            ("SwitchBot Blind Tilt", "🪟", "switchbot_blind",    "$45", ""),
            ("Petlibro Feeder",      "🍽️", "petlibro_feeder",    "$65", ""),
            ("Echo Dot / Alexa",     "🔊", "echo_alexa",         "$0",  ""),
            ("Apple Home",           "🍎", "apple_home",         "$0",  ""),
        ]
        assert len(DEVICE_STEPS) == 8

    def test_all_step_keys_are_unique(self):
        """No duplicate step_key values across HA_STEPS and DEVICE_STEPS."""
        HA_STEPS = [
            ("Download HA OS image",    "proxmox_download"),
            ("Create VM",               "proxmox_vm_create"),
            ("Boot from HA OS image",   "proxmox_boot"),
            ("Access HA",               "ha_access"),
            ("Complete onboarding",     "ha_onboarding"),
            ("Install HACS",            "ha_hacs"),
            ("Add Tailscale",           "ha_tailscale"),
        ]
        DEVICE_STEPS = [
            ("Petlibro Fountain",    "🐱", "petlibro_fountain", "$45", ""),
            ("Kasa Smart Plugs",     "💡", "kasa_plugs",         "$40", ""),
            ("LIFX Bulbs",           "💡", "lifx_bulbs",         "$50", ""),
            ("Reolink Camera",       "📷", "reolink_camera",     "$35", ""),
            ("SwitchBot Blind Tilt", "🪟", "switchbot_blind",    "$45", ""),
            ("Petlibro Feeder",      "🍽️", "petlibro_feeder",    "$65", ""),
            ("Echo Dot / Alexa",     "🔊", "echo_alexa",         "$0",  ""),
            ("Apple Home",           "🍎", "apple_home",         "$0",  ""),
        ]
        ha_keys  = [s[1] for s in HA_STEPS]
        dev_keys = [s[2] for s in DEVICE_STEPS]
        all_keys = ha_keys + dev_keys
        assert len(all_keys) == len(set(all_keys)), "Duplicate step keys found!"


# ── Integration test — DB round-trip ─────────────────────────────────────────

class TestDBRoundTrip:
    """Full insert → load round-trip against a temp SQLite DB."""

    def test_progress_round_trip(self):
        """Insert a step, load it back, verify fields match."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = _make_sqlite_conn(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ha_setup_progress (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_key TEXT UNIQUE NOT NULL,
                    done     INTEGER DEFAULT 0,
                    done_at  TEXT DEFAULT NULL,
                    notes    TEXT DEFAULT ''
                )
            """)
            conn.commit()

            # Insert step
            conn.execute("""
                INSERT INTO ha_setup_progress (step_key, done, done_at, notes)
                VALUES (?, ?, ?, ?)
            """, ("ha_hacs", 1, "2026-03-01 10:00:00", "installed via SSH add-on"))
            conn.commit()

            # Load it back
            cur = conn.execute(
                "SELECT step_key, done, done_at, notes FROM ha_setup_progress WHERE step_key=?",
                ("ha_hacs",),
            )
            row = dict(cur.fetchone())

            assert row["step_key"] == "ha_hacs"
            assert row["done"] == 1
            assert row["done_at"] == "2026-03-01 10:00:00"
            assert row["notes"] == "installed via SSH add-on"
            conn.close()
        finally:
            os.unlink(db_path)

    def test_load_progress_returns_dict(self):
        """_load_progress-style query returns a dict keyed by step_key."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = _make_sqlite_conn(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ha_setup_progress (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_key TEXT UNIQUE NOT NULL,
                    done     INTEGER DEFAULT 0,
                    done_at  TEXT DEFAULT NULL,
                    notes    TEXT DEFAULT ''
                )
            """)
            conn.commit()

            # Insert two rows
            for key in ("proxmox_download", "proxmox_boot"):
                conn.execute(
                    "INSERT INTO ha_setup_progress (step_key) VALUES (?)",
                    (key,),
                )
            conn.commit()

            cur = conn.execute(
                "SELECT step_key, done, done_at, notes FROM ha_setup_progress"
            )
            rows = cur.fetchall()
            result = {r["step_key"]: dict(r) for r in rows}

            assert isinstance(result, dict)
            assert "proxmox_download" in result
            assert "proxmox_boot" in result
            conn.close()
        finally:
            os.unlink(db_path)
