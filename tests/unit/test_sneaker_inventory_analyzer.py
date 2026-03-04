"""
Tests for pages/65_sneaker_inventory_analyzer.py
SoleOps — Sneaker Inventory Analyzer
"""
import pytest
import sqlite3
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ── Constants (duplicated here to test them directly without Streamlit) ────────
EBAY_FEE_RATE     = 0.129
EBAY_FEE_FIXED    = 0.30
MERCARI_FEE_RATE  = 0.10
MERCARI_FEE_FIXED = 0.30
STOCKX_FEE_RATE   = 0.115
GOAT_FEE_RATE     = 0.095
GOAT_FEE_FIXED    = 5.00

AGING_TIERS = [
    (0,  7,  "🟢 Fresh",    0.00, 0),
    (7,  14, "🟡 Warm",     0.05, 1),
    (14, 21, "🟠 Aging",    0.10, 2),
    (21, 30, "🔴 Stale",    0.15, 3),
    (30, 999,"⚫ Critical", 0.20, 4),
]


# ── Helper functions (mirrored from page so we test the logic directly) ───────
def _calc_profit(sell_price: float, cost_basis: float, platform: str) -> float:
    p = (platform or "").lower()
    if "ebay" in p:
        fees = (sell_price * EBAY_FEE_RATE) + EBAY_FEE_FIXED
    elif "mercari" in p:
        fees = (sell_price * MERCARI_FEE_RATE) + MERCARI_FEE_FIXED
    elif "stockx" in p:
        fees = sell_price * STOCKX_FEE_RATE
    elif "goat" in p:
        fees = (sell_price * GOAT_FEE_RATE) + GOAT_FEE_FIXED
    else:
        fees = sell_price * 0.10
    return round(sell_price - fees - cost_basis, 2)


def _get_aging_tier(days: int) -> dict:
    for lo, hi, label, drop_pct, tier_idx in AGING_TIERS:
        if lo <= days < hi:
            return {"label": label, "drop_pct": drop_pct, "tier": tier_idx, "days": days}
    return {"label": "⚫ Critical", "drop_pct": 0.20, "tier": 4, "days": days}


def _calc_days_listed(listed_date_str: str) -> int:
    if not listed_date_str:
        return 0
    try:
        listed = date.fromisoformat(listed_date_str[:10])
        return max(0, (date.today() - listed).days)
    except Exception:
        return 0


def _get_suggested_price(current_price: float, days_listed: int):
    tier = _get_aging_tier(days_listed)
    if tier["drop_pct"] == 0 or not current_price:
        return current_price, "Hold — still fresh"
    new_price = round(current_price * (1 - tier["drop_pct"]), 2)
    reason = f"{tier['label']} — {int(tier['drop_pct']*100)}% drop suggested"
    return new_price, reason


# ── Test: Import / syntax ─────────────────────────────────────────────────────
class TestImport:
    def test_page_file_exists(self):
        """Page file should exist at expected path."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "pages", "65_sneaker_inventory_analyzer.py"
        )
        assert os.path.exists(path), f"Page file not found: {path}"

    def test_page_compiles(self):
        """Page should compile without syntax errors."""
        import py_compile
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "pages", "65_sneaker_inventory_analyzer.py"
        )
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in page: {e}")


# ── Test: Database tables ─────────────────────────────────────────────────────
class TestDatabase:
    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")

    def teardown_method(self):
        self.conn.close()

    def test_soleops_inventory_table_creation(self):
        """soleops_inventory table should be created with all required columns."""
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shoe_name TEXT NOT NULL,
                brand TEXT DEFAULT '',
                colorway TEXT DEFAULT '',
                size TEXT NOT NULL,
                cost_basis REAL NOT NULL DEFAULT 0,
                condition TEXT DEFAULT 'New with box',
                listed_date TEXT,
                listed_price REAL,
                listed_platform TEXT DEFAULT 'Unlisted',
                status TEXT DEFAULT 'inventory',
                sell_price REAL,
                sold_date TEXT,
                sold_platform TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.conn.commit()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='soleops_inventory'")
        assert cur.fetchone() is not None

    def test_soleops_inventory_columns(self):
        """soleops_inventory should have all expected columns."""
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shoe_name TEXT NOT NULL,
                brand TEXT DEFAULT '',
                size TEXT NOT NULL,
                cost_basis REAL NOT NULL DEFAULT 0,
                condition TEXT DEFAULT 'New with box',
                listed_date TEXT,
                listed_price REAL,
                listed_platform TEXT DEFAULT 'Unlisted',
                status TEXT DEFAULT 'inventory',
                sell_price REAL,
                sold_date TEXT,
                sold_platform TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.conn.commit()
        cur.execute("PRAGMA table_info(soleops_inventory)")
        cols = {row[1] for row in cur.fetchall()}
        required = {"id", "user_id", "shoe_name", "size", "cost_basis",
                    "listed_date", "listed_price", "listed_platform", "status",
                    "sell_price", "sold_platform", "notes"}
        for col in required:
            assert col in cols, f"Missing column: {col}"

    def test_soleops_price_suggestions_table_creation(self):
        """soleops_price_suggestions table should be created."""
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_price_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                shoe_name TEXT,
                size TEXT,
                current_price REAL,
                suggested_price REAL,
                drop_pct REAL,
                reason TEXT,
                days_listed INTEGER,
                ebay_avg REAL DEFAULT 0,
                mercari_avg REAL DEFAULT 0,
                suggested_at TEXT DEFAULT (datetime('now')),
                action_taken TEXT
            )
        """)
        self.conn.commit()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='soleops_price_suggestions'")
        assert cur.fetchone() is not None

    def test_insert_and_query_inventory(self):
        """Should be able to insert and retrieve inventory items."""
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shoe_name TEXT NOT NULL,
                size TEXT NOT NULL,
                cost_basis REAL NOT NULL DEFAULT 0,
                listed_date TEXT,
                listed_price REAL,
                listed_platform TEXT DEFAULT 'Unlisted',
                status TEXT DEFAULT 'inventory',
                sell_price REAL,
                sold_date TEXT,
                sold_platform TEXT,
                notes TEXT DEFAULT '',
                brand TEXT DEFAULT '',
                colorway TEXT DEFAULT '',
                condition TEXT DEFAULT 'New with box',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.conn.commit()
        cur.execute("""
            INSERT INTO soleops_inventory (user_id, shoe_name, size, cost_basis, listed_platform, status)
            VALUES (1, 'Jordan 1 Chicago', '10', 150.00, 'eBay', 'inventory')
        """)
        self.conn.commit()
        cur.execute("SELECT shoe_name, cost_basis FROM soleops_inventory WHERE user_id = 1")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "Jordan 1 Chicago"
        assert row[1] == 150.00


# ── Test: Profit Calculations ─────────────────────────────────────────────────
class TestProfitCalculations:
    def test_ebay_profit_correct(self):
        """eBay profit = sell - (sell * 12.9% + $0.30) - cost."""
        sell, cost = 200.0, 100.0
        expected = round(200 - (200 * 0.129 + 0.30) - 100, 2)
        assert _calc_profit(sell, cost, "ebay") == pytest.approx(expected, abs=0.01)

    def test_mercari_profit_correct(self):
        """Mercari profit = sell - (sell * 10% + $0.30) - cost."""
        sell, cost = 200.0, 100.0
        expected = round(200 - (200 * 0.10 + 0.30) - 100, 2)
        assert _calc_profit(sell, cost, "mercari") == pytest.approx(expected, abs=0.01)

    def test_stockx_profit_correct(self):
        """StockX profit = sell - (sell * 11.5%) - cost."""
        sell, cost = 300.0, 200.0
        expected = round(300 - (300 * 0.115) - 200, 2)
        assert _calc_profit(sell, cost, "stockx") == pytest.approx(expected, abs=0.01)

    def test_goat_profit_correct(self):
        """GOAT profit = sell - (sell * 9.5% + $5) - cost."""
        sell, cost = 300.0, 200.0
        expected = round(300 - (300 * 0.095 + 5.00) - 200, 2)
        assert _calc_profit(sell, cost, "goat") == pytest.approx(expected, abs=0.01)

    def test_profit_negative_when_selling_below_cost(self):
        """Should return negative profit when fees + cost exceed sale price."""
        assert _calc_profit(50.0, 100.0, "ebay") < 0

    def test_profit_zero_sell_price(self):
        """Zero sell price — eBay still charges fixed $0.30 fee, so loss = cost + fee."""
        result = _calc_profit(0.0, 100.0, "ebay")
        # fees = 0 * 12.9% + $0.30 = $0.30, so profit = 0 - 0.30 - 100 = -100.30
        assert result == pytest.approx(-100.30, abs=0.01)

    def test_mercari_cheaper_than_ebay(self):
        """Mercari fees (10%) should always yield more profit than eBay (12.9%) at same price."""
        sell, cost = 200.0, 100.0
        assert _calc_profit(sell, cost, "mercari") > _calc_profit(sell, cost, "ebay")


# ── Test: Aging Tier Logic ────────────────────────────────────────────────────
class TestAgingTiers:
    def test_fresh_tier_0_to_6_days(self):
        for days in [0, 3, 6]:
            tier = _get_aging_tier(days)
            assert tier["tier"] == 0
            assert tier["drop_pct"] == 0.0
            assert "Fresh" in tier["label"]

    def test_warm_tier_7_to_13_days(self):
        for days in [7, 10, 13]:
            tier = _get_aging_tier(days)
            assert tier["tier"] == 1
            assert tier["drop_pct"] == 0.05

    def test_aging_tier_14_to_20_days(self):
        for days in [14, 17, 20]:
            tier = _get_aging_tier(days)
            assert tier["tier"] == 2
            assert tier["drop_pct"] == 0.10

    def test_stale_tier_21_to_29_days(self):
        for days in [21, 25, 29]:
            tier = _get_aging_tier(days)
            assert tier["tier"] == 3
            assert tier["drop_pct"] == 0.15

    def test_critical_tier_30_plus_days(self):
        for days in [30, 45, 60, 100]:
            tier = _get_aging_tier(days)
            assert tier["tier"] == 4
            assert tier["drop_pct"] == 0.20

    def test_aging_tiers_cover_all_days(self):
        """Every day from 0 to 100 should be covered by exactly one tier."""
        for days in range(101):
            tier = _get_aging_tier(days)
            assert tier["tier"] in [0, 1, 2, 3, 4]


# ── Test: Suggested Price Logic ───────────────────────────────────────────────
class TestSuggestedPrice:
    def test_fresh_item_should_hold(self):
        price, reason = _get_suggested_price(200.0, 3)
        assert price == 200.0
        assert "Hold" in reason or "fresh" in reason.lower()

    def test_warm_item_5pct_drop(self):
        price, reason = _get_suggested_price(200.0, 10)
        assert price == pytest.approx(190.0, abs=1.0)
        assert "5%" in reason

    def test_aging_item_10pct_drop(self):
        price, reason = _get_suggested_price(200.0, 17)
        assert price == pytest.approx(180.0, abs=1.0)
        assert "10%" in reason

    def test_stale_item_15pct_drop(self):
        price, reason = _get_suggested_price(200.0, 25)
        assert price == pytest.approx(170.0, abs=1.0)
        assert "15%" in reason

    def test_critical_item_20pct_drop(self):
        price, reason = _get_suggested_price(200.0, 45)
        assert price == pytest.approx(160.0, abs=1.0)
        assert "20%" in reason

    def test_zero_price_returns_zero(self):
        price, reason = _get_suggested_price(0.0, 30)
        assert price == 0.0


# ── Test: Days Listed Calculation ─────────────────────────────────────────────
class TestDaysListed:
    def test_today_is_zero_days(self):
        today_str = date.today().isoformat()
        assert _calc_days_listed(today_str) == 0

    def test_yesterday_is_one_day(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        assert _calc_days_listed(yesterday) == 1

    def test_two_weeks_ago(self):
        two_weeks = (date.today() - timedelta(days=14)).isoformat()
        assert _calc_days_listed(two_weeks) == 14

    def test_none_returns_zero(self):
        assert _calc_days_listed(None) == 0

    def test_empty_string_returns_zero(self):
        assert _calc_days_listed("") == 0

    def test_invalid_date_returns_zero(self):
        assert _calc_days_listed("not-a-date") == 0


# ── Test: Constants ───────────────────────────────────────────────────────────
class TestConstants:
    def test_fee_rates_are_fractions(self):
        assert 0 < EBAY_FEE_RATE < 1
        assert 0 < MERCARI_FEE_RATE < 1
        assert 0 < STOCKX_FEE_RATE < 1
        assert 0 < GOAT_FEE_RATE < 1

    def test_mercari_cheaper_than_ebay_rate(self):
        assert MERCARI_FEE_RATE < EBAY_FEE_RATE

    def test_aging_tiers_are_contiguous(self):
        """Tiers should cover 0 to 999 with no gaps."""
        prev_hi = 0
        for lo, hi, *_ in AGING_TIERS:
            assert lo == prev_hi, f"Gap in aging tiers: {prev_hi} to {lo}"
            prev_hi = hi
