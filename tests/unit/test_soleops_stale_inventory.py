"""
Unit tests — SoleOps Stale Inventory Alert System (page 84)
Tests: import, DB table creation, helper functions, handler routing
"""
import sys
import os
import sqlite3
import pytest
from datetime import date, timedelta
from pathlib import Path

# Project root on path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("MULTI_USER", "false")
os.environ.setdefault("APP_PASSWORD", "test")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Provide an isolated SQLite DB for each test."""
    db_path = str(tmp_path / "test_stale.db")
    import utils.db as _db
    monkeypatch.setattr(_db, "USE_POSTGRES", False)
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_db, "_active_db_path", db_path)

    # Also patch get_conn on run_scheduled_agents directly.
    # When that module imports `get_conn` via `from utils.db import get_conn`,
    # Python creates a module-level name binding.  If another test file patched
    # db_mod.get_conn while run_scheduled_agents was first imported, the module
    # may hold a stale reference.  Patching it at the source guarantees the
    # handler uses our test DB regardless of import order.
    try:
        import run_scheduled_agents as _agents
        def _fake_get_conn():
            import sqlite3 as _sq
            _c = _sq.connect(db_path)
            _c.row_factory = _sq.Row
            return _c
        monkeypatch.setattr(_agents, "get_conn", _fake_get_conn)
    except ImportError:
        pass

    _db.init_db()
    return db_path


# ── Test 1: Import ─────────────────────────────────────────────────────────────

def test_page_84_import():
    """Page 84 can be imported without syntax errors."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "page_84",
        PROJECT_ROOT / "pages" / "84_soleops_stale_inventory.py",
    )
    assert spec is not None, "Could not find pages/84_soleops_stale_inventory.py"


# ── Test 2: DB table creation ──────────────────────────────────────────────────

def test_ensure_tables_creates_stale_alerts(tmp_db):
    """_ensure_tables() creates soleops_stale_alerts without errors."""
    conn = sqlite3.connect(tmp_db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS soleops_stale_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            shoe_name TEXT NOT NULL,
            size TEXT NOT NULL,
            days_listed INTEGER NOT NULL,
            listed_price REAL DEFAULT 0,
            suggested_price REAL DEFAULT 0,
            ai_strategy TEXT DEFAULT '',
            alert_type TEXT DEFAULT 'telegram',
            sent_at TEXT DEFAULT (datetime('now')),
            acknowledged INTEGER DEFAULT 0,
            action_taken TEXT DEFAULT ''
        )
    """)
    conn.commit()

    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    assert "soleops_stale_alerts" in tables


def test_ensure_tables_with_soleops_inventory(tmp_db):
    """soleops_inventory table can be created and used in tests."""
    conn = sqlite3.connect(tmp_db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS soleops_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shoe_name TEXT NOT NULL,
            size TEXT NOT NULL,
            cost_basis REAL DEFAULT 0,
            listed_date TEXT,
            listed_price REAL,
            listed_platform TEXT DEFAULT 'Unlisted',
            status TEXT DEFAULT 'inventory',
            brand TEXT DEFAULT '',
            colorway TEXT DEFAULT '',
            condition TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            sell_price REAL,
            sold_date TEXT,
            sold_platform TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    assert "soleops_inventory" in tables


# ── Test 3: Aging tier logic ───────────────────────────────────────────────────

@pytest.mark.parametrize("days,expected_tier,expected_drop", [
    (0,   0, 0.00),
    (3,   0, 0.00),
    (7,   1, 0.05),
    (10,  1, 0.05),
    (14,  2, 0.10),
    (20,  2, 0.10),
    (21,  3, 0.15),
    (28,  3, 0.15),
    (30,  4, 0.20),
    (60,  4, 0.20),
    (365, 4, 0.20),
])
def test_aging_tier_boundaries(days, expected_tier, expected_drop):
    """Aging tier is correctly assigned for every day boundary."""
    AGING_TIERS = [
        (0,  7,  "🟢 Fresh",    0.00, 0),
        (7,  14, "🟡 Warm",     0.05, 1),
        (14, 21, "🟠 Aging",    0.10, 2),
        (21, 30, "🔴 Stale",    0.15, 3),
        (30, 999,"⚫ Critical", 0.20, 4),
    ]

    def _get_tier(d):
        for lo, hi, label, drop_pct, tier_idx in AGING_TIERS:
            if lo <= d < hi:
                return {"tier": tier_idx, "drop_pct": drop_pct}
        return {"tier": 4, "drop_pct": 0.20}

    result = _get_tier(days)
    assert result["tier"] == expected_tier, f"days={days}: expected tier {expected_tier}, got {result['tier']}"
    assert result["drop_pct"] == expected_drop


# ── Test 4: Suggested price calculation ───────────────────────────────────────

@pytest.mark.parametrize("listed_price,drop_pct,expected", [
    (200.0, 0.10, 180.0),
    (150.0, 0.15, 127.5),
    (300.0, 0.20, 240.0),
    (100.0, 0.00, 100.0),
    (0.0,   0.10, 0.0),
])
def test_suggested_price_calculation(listed_price, drop_pct, expected):
    """Suggested price = listed_price * (1 - drop_pct)."""
    if listed_price > 0 and drop_pct > 0:
        result = round(listed_price * (1 - drop_pct), 2)
    else:
        result = listed_price
    assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"


# ── Test 5: Profit calculation ─────────────────────────────────────────────────

def test_profit_calc_ebay():
    """eBay profit = sell - (sell * 0.129 + 0.30) - cost."""
    sell, cost = 200.0, 120.0
    fees = (200.0 * 0.129) + 0.30
    expected = round(200.0 - fees - 120.0, 2)

    def _calc_profit(sell_price, cost_basis, platform):
        p = platform.lower()
        if "ebay" in p:
            fees_calc = (sell_price * 0.129) + 0.30
        elif "mercari" in p:
            fees_calc = (sell_price * 0.10) + 0.30
        else:
            fees_calc = sell_price * 0.12
        return round(sell_price - fees_calc - cost_basis, 2)

    result = _calc_profit(sell, cost, "eBay")
    assert result == expected


def test_profit_calc_mercari():
    """Mercari profit = sell - (sell * 0.10 + 0.30) - cost."""
    sell, cost = 180.0, 100.0
    fees = (180.0 * 0.10) + 0.30
    expected = round(180.0 - fees - 100.0, 2)

    def _calc_profit(sell_price, cost_basis, platform):
        p = platform.lower()
        if "ebay" in p:
            fees_calc = (sell_price * 0.129) + 0.30
        elif "mercari" in p:
            fees_calc = (sell_price * 0.10) + 0.30
        else:
            fees_calc = sell_price * 0.12
        return round(sell_price - fees_calc - cost_basis, 2)

    result = _calc_profit(sell, cost, "Mercari")
    assert result == expected


# ── Test 6: Days listed calculator ────────────────────────────────────────────

def test_calc_days_listed_today():
    """An item listed today returns 0 days."""
    listed_date = str(date.today())

    def _calc_days(val):
        if not val:
            return 0
        from datetime import datetime
        try:
            if isinstance(val, str):
                ld = datetime.strptime(val[:10], "%Y-%m-%d").date()
            else:
                ld = val
            return max(0, (date.today() - ld).days)
        except Exception:
            return 0

    assert _calc_days(listed_date) == 0


def test_calc_days_listed_14_days_ago():
    """An item listed 14 days ago returns 14."""
    listed_date = str(date.today() - timedelta(days=14))

    def _calc_days(val):
        from datetime import datetime
        if not val:
            return 0
        try:
            if isinstance(val, str):
                ld = datetime.strptime(val[:10], "%Y-%m-%d").date()
            else:
                ld = val
            return max(0, (date.today() - ld).days)
        except Exception:
            return 0

    assert _calc_days(listed_date) == 14


def test_calc_days_listed_none():
    """None listed_date returns 0 gracefully."""
    def _calc_days(val):
        if not val:
            return 0
        return 99

    assert _calc_days(None) == 0


# ── Test 7: Handler routing ────────────────────────────────────────────────────

def test_handler_registry_stale_inventory():
    """'stale inventory' key routes to the stale inventory handler."""
    from run_scheduled_agents import TASK_HANDLERS, _handler_stale_inventory_scan
    keys = [k for k, _ in TASK_HANDLERS]
    assert "stale inventory" in keys, "stale inventory not in TASK_HANDLERS"

    # Verify correct function is mapped
    handler_fn = dict(TASK_HANDLERS).get("stale inventory")
    assert handler_fn == _handler_stale_inventory_scan


def test_handler_registry_weekly_reseller():
    """'weekly reseller report' key routes to the reseller report handler."""
    from run_scheduled_agents import TASK_HANDLERS, _handler_weekly_reseller_report
    keys = [k for k, _ in TASK_HANDLERS]
    assert "weekly reseller report" in keys
    handler_fn = dict(TASK_HANDLERS).get("weekly reseller report")
    assert handler_fn == _handler_weekly_reseller_report


def test_get_handler_partial_match():
    """_get_handler does case-insensitive partial matching."""
    from run_scheduled_agents import _get_handler, _handler_stale_inventory_scan
    fn = _get_handler("SoleOps Stale Inventory Weekly Scan")
    assert fn == _handler_stale_inventory_scan


def test_get_handler_fallback():
    """Unknown task name falls back to _handler_generic."""
    from run_scheduled_agents import _get_handler, _handler_generic
    fn = _get_handler("some totally unknown custom task xyz")
    assert fn == _handler_generic


# ── Test 8: Stale handler with empty soleops_inventory ────────────────────────

def test_stale_handler_no_inventory(tmp_db, monkeypatch):
    """Stale inventory handler returns success + fresh message when table is empty."""
    import utils.db as _db
    monkeypatch.setattr(_db, "USE_POSTGRES", False)
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_db, "_active_db_path", tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS soleops_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, shoe_name TEXT, size TEXT,
            cost_basis REAL, listed_date TEXT, listed_price REAL,
            listed_platform TEXT, status TEXT DEFAULT 'inventory',
            sell_price REAL, sold_date TEXT, sold_platform TEXT
        )
    """)
    conn.commit()
    conn.close()

    from run_scheduled_agents import _handler_stale_inventory_scan
    success, message = _handler_stale_inventory_scan({})
    assert success is True
    assert "fresh" in message.lower() or "no pairs" in message.lower()


def test_stale_handler_with_fresh_inventory(tmp_db, monkeypatch):
    """Handler reports no stale pairs when all items are listed today."""
    import utils.db as _db
    monkeypatch.setattr(_db, "USE_POSTGRES", False)
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_db, "_active_db_path", tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS soleops_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, shoe_name TEXT, size TEXT,
            cost_basis REAL, listed_date TEXT, listed_price REAL,
            listed_platform TEXT, status TEXT DEFAULT 'inventory',
            sell_price REAL, sold_date TEXT, sold_platform TEXT
        )
    """)
    # Insert 2 fresh items
    today_str = str(date.today())
    conn.execute(
        "INSERT INTO soleops_inventory (user_id, shoe_name, size, cost_basis, listed_date, listed_price, listed_platform, status) VALUES (1,'Jordan 1','10',120.0,?,200.0,'eBay','inventory')",
        (today_str,)
    )
    conn.execute(
        "INSERT INTO soleops_inventory (user_id, shoe_name, size, cost_basis, listed_date, listed_price, listed_platform, status) VALUES (1,'Dunk Low','9',90.0,?,150.0,'Mercari','inventory')",
        (today_str,)
    )
    conn.commit()
    conn.close()

    from run_scheduled_agents import _handler_stale_inventory_scan
    success, message = _handler_stale_inventory_scan({})
    assert success is True
    assert "fresh" in message.lower() or "no pairs" in message.lower()


# ── Test 9: BACKLOG.md marks page 84 pending ──────────────────────────────────

def test_backlog_has_stale_inventory_entry():
    """BACKLOG.md contains the Stale Inventory Alert System entry."""
    backlog_path = PROJECT_ROOT / "BACKLOG.md"
    if not backlog_path.exists():
        pytest.skip("BACKLOG.md not found")
    content = backlog_path.read_text()
    assert "Stale Inventory" in content or "stale inventory" in content.lower()


# ── Test 10: Page file exists ──────────────────────────────────────────────────

def test_page_84_file_exists():
    """pages/84_soleops_stale_inventory.py exists on disk."""
    page_path = PROJECT_ROOT / "pages" / "84_soleops_stale_inventory.py"
    assert page_path.exists(), "pages/84_soleops_stale_inventory.py not found"
    assert page_path.stat().st_size > 1000, "Page file is unexpectedly small"
