"""
Unit tests for:
  - pages/85_soleops_inventory_manager.py
  - pages/86_soleops_listing_generator.py

Tests cover:
  1. Import checks (both pages can be imported without errors)
  2. DB table creation (_ensure_tables)
  3. Helper function correctness (_calc_fee, _calc_profit, _days_since, _get_tier)
  4. Data enrichment (_enrich_inventory on sample DataFrames)
  5. _generate_listing mock (no real API call)
"""
import sys
import os
import sqlite3
import types
import importlib
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

# ── Ensure project root is on path ────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── StopExecution sentinel raised by st.stop() stub ──────────────────────────
class _StopExecution(Exception):
    """Raised by the st.stop() stub to mimic Streamlit halting execution."""


# ── Minimal Streamlit stub so pages don't crash on import ─────────────────────
def _make_st_stub():
    st = types.ModuleType("streamlit")

    # Void / display-only calls
    for attr in [
        "set_page_config", "title", "caption", "subheader", "markdown",
        "info", "success", "error", "warning", "divider", "rerun",
        "balloons", "toast", "dataframe", "code", "progress",
        "metric", "write", "image", "pyplot",
    ]:
        setattr(st, attr, MagicMock(return_value=None))

    # Input widgets — return safe primitive defaults so comparisons don't crash
    st.text_input         = MagicMock(return_value="")
    st.text_area          = MagicMock(return_value="")
    st.number_input       = MagicMock(return_value=0.0)
    st.date_input         = MagicMock(return_value=date.today())
    st.selectbox          = MagicMock(return_value="")
    st.multiselect        = MagicMock(return_value=[])
    st.checkbox           = MagicMock(return_value=False)
    st.radio              = MagicMock(return_value=None)
    st.slider             = MagicMock(return_value=0)
    st.button             = MagicMock(return_value=False)
    st.file_uploader      = MagicMock(return_value=None)
    st.download_button    = MagicMock(return_value=None)
    # form_submit_button returns False → prevents form submit logic from running
    st.form_submit_button = MagicMock(return_value=False)

    # st.stop() must actually halt execution like Streamlit does
    st.stop = MagicMock(side_effect=_StopExecution)

    # session_state
    class _SS(dict):
        def __getattr__(self, k):
            return self.get(k)
        def __setattr__(self, k, v):
            self[k] = v
        def pop(self, k, *args):
            return dict.pop(self, k, *args)

    st.session_state = _SS()
    st.sidebar = MagicMock()

    # Context-manager helper
    def _cm():
        m = MagicMock()
        m.__enter__ = lambda s: s
        m.__exit__  = MagicMock(return_value=False)
        return m

    st.expander  = MagicMock(return_value=_cm())
    st.container = MagicMock(return_value=_cm())
    st.form      = MagicMock(return_value=_cm())
    st.spinner   = MagicMock(return_value=_cm())

    # columns returns list of context-manager mocks
    def _columns(*args, **kwargs):
        n = args[0] if args else 2
        if isinstance(n, (list, tuple)):
            n = len(n)
        cols = [_cm() for _ in range(int(n))]
        return cols

    def _tabs(names):
        return [_cm() for _ in names]

    st.columns = _columns
    st.tabs    = _tabs
    return st


# ── Stub utils ─────────────────────────────────────────────────────────────────
def _make_db_stub(db_path: str):
    """Return a db module backed by the given SQLite file."""
    db = types.ModuleType("utils.db")
    conn_store = {"conn": None}

    def get_conn():
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        return c

    def execute(conn, sql, params=()):
        sql_pg = sql.replace("?", "?")  # already using ? for sqlite
        cur = conn.execute(sql_pg, params)
        return cur

    def init_db():
        pass

    def get_setting(key, default=""):
        return default

    def set_setting(key, value):
        pass

    db.get_conn     = get_conn
    db.execute      = execute
    db.init_db      = init_db
    db.get_setting  = get_setting
    db.set_setting  = set_setting
    db.USE_POSTGRES = False
    return db


def _make_auth_stub():
    auth = types.ModuleType("utils.auth")
    auth.require_login              = MagicMock(return_value=None)
    auth.render_sidebar_brand       = MagicMock(return_value=None)
    auth.render_sidebar_user_widget = MagicMock(return_value=None)
    auth.inject_css                 = MagicMock(return_value=None)
    auth.inject_soleops_css         = MagicMock(return_value=None)
    auth.inject_cc_css              = MagicMock(return_value=None)
    return auth


def _make_altair_stub():
    """Stub altair so page 85 can import it without the real package."""
    alt = types.ModuleType("altair")
    # Chart and all encoding helpers return chainable mocks
    for _attr in [
        "Chart", "Color", "Axis", "Scale", "Tooltip", "X", "Y",
        "condition", "value", "datum", "Size", "Shape", "Order",
        "Color", "Opacity",
    ]:
        setattr(alt, _attr, MagicMock(return_value=MagicMock()))
    return alt


def _make_anthropic_stub():
    """Stub anthropic so imports don't fail in test environments without it."""
    anth = types.ModuleType("anthropic")
    anth.Anthropic = MagicMock()
    return anth


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS — SNEAKER INVENTORY ANALYZER (Page 65)
# ═══════════════════════════════════════════════════════════════════════════════
class TestSoleOpsInventoryManager(unittest.TestCase):
    """Tests for pages/65_sneaker_inventory_analyzer.py — SoleOps inventory helpers."""

    def setUp(self):
        import tempfile
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        self.db_file.close()

        # Build lightweight stubs for heavy optional deps
        altair_stub = types.ModuleType("altair")
        for _attr in ["Chart", "Color", "Axis", "Scale", "Tooltip", "X", "Y",
                      "condition", "value", "datum"]:
            setattr(altair_stub, _attr, MagicMock())

        plotly_stub = types.ModuleType("plotly")
        px_stub = types.ModuleType("plotly.express")
        go_stub = types.ModuleType("plotly.graph_objects")
        for _attr in ["bar", "line", "scatter", "pie", "histogram", "Figure"]:
            setattr(px_stub, _attr, MagicMock(return_value=MagicMock()))
            setattr(go_stub, _attr, MagicMock(return_value=MagicMock()))

        self._st_patch  = patch.dict(sys.modules, {"streamlit": _make_st_stub()})
        self._db_stub   = _make_db_stub(self.db_path)
        self._auth_stub = _make_auth_stub()
        self._db_patch  = patch.dict(sys.modules, {
            "utils.db":            self._db_stub,
            "utils.auth":          self._auth_stub,
            "altair":              altair_stub,
            "plotly":              plotly_stub,
            "plotly.express":      px_stub,
            "plotly.graph_objects": go_stub,
        })
        self._st_patch.start()
        self._db_patch.start()

        if "sneaker_inv" in sys.modules:
            del sys.modules["sneaker_inv"]
        spec = importlib.util.spec_from_file_location(
            "sneaker_inv",
            os.path.join(ROOT, "pages", "65_sneaker_inventory_analyzer.py"),
        )
        self.mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(self.mod)
        except _StopExecution:
            pass

    def tearDown(self):
        self._st_patch.stop()
        self._db_patch.stop()
        import os as _os
        try:
            _os.unlink(self.db_path)
        except Exception:
            pass

    # ── 1. Import check ────────────────────────────────────────────────────────
    def test_import(self):
        self.assertTrue(hasattr(self.mod, "_ensure_tables"))
        self.assertTrue(hasattr(self.mod, "_calc_profit"))
        self.assertTrue(hasattr(self.mod, "_get_aging_tier"))
        self.assertTrue(hasattr(self.mod, "_calc_days_listed"))
        self.assertTrue(hasattr(self.mod, "_get_suggested_price"))
        self.assertTrue(hasattr(self.mod, "_mark_sold"))
        self.assertTrue(hasattr(self.mod, "_delete_item"))
        self.assertTrue(hasattr(self.mod, "_load_inventory"))
        self.assertTrue(hasattr(self.mod, "_create_item"))

    # ── 2. DB table creation ───────────────────────────────────────────────────
    def test_ensure_tables_creates_soleops_inventory(self):
        conn = sqlite3.connect(self.db_path)
        cur  = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='soleops_inventory'"
        )
        self.assertIsNotNone(cur.fetchone(), "soleops_inventory table should exist")
        conn.close()

    # ── 3a. _calc_profit helpers ──────────────────────────────────────────────
    def test_calc_profit_ebay(self):
        profit = self.mod._calc_profit(200.0, 150.0, "eBay")
        fee    = round(200.0 * 0.129 + 0.30, 2)
        expected = round(200.0 - fee - 150.0, 2)
        self.assertAlmostEqual(profit, expected, places=2)

    def test_calc_profit_mercari(self):
        profit = self.mod._calc_profit(200.0, 150.0, "Mercari")
        fee    = round(200.0 * 0.10 + 0.30, 2)
        expected = round(200.0 - fee - 150.0, 2)
        self.assertAlmostEqual(profit, expected, places=2)

    def test_calc_profit_stockx(self):
        profit = self.mod._calc_profit(200.0, 150.0, "StockX")
        fee    = round(200.0 * 0.115, 2)
        expected = round(200.0 - fee - 150.0, 2)
        self.assertAlmostEqual(profit, expected, places=2)

    def test_calc_profit_positive_sale(self):
        """Selling at a profit returns a positive float."""
        profit = self.mod._calc_profit(300.0, 150.0, "eBay")
        self.assertIsInstance(profit, float)
        self.assertGreater(profit, 0)

    def test_calc_profit_loss(self):
        """Selling below cost returns a negative value."""
        profit = self.mod._calc_profit(100.0, 200.0, "eBay")
        self.assertLess(profit, 0)

    # ── 3b. _calc_days_listed ─────────────────────────────────────────────────
    def test_calc_days_listed_today(self):
        days = self.mod._calc_days_listed(str(date.today()))
        self.assertEqual(days, 0)

    def test_calc_days_listed_one_week_ago(self):
        one_week = str(date.today() - timedelta(days=7))
        days = self.mod._calc_days_listed(one_week)
        self.assertEqual(days, 7)

    def test_calc_days_listed_none(self):
        days = self.mod._calc_days_listed(None)
        self.assertEqual(days, 0)

    def test_calc_days_listed_invalid(self):
        days = self.mod._calc_days_listed("not-a-date")
        self.assertEqual(days, 0)

    # ── 3c. _get_aging_tier ───────────────────────────────────────────────────
    def test_get_tier_fresh(self):
        tier = self.mod._get_aging_tier(3)
        self.assertEqual(tier["label"], "🟢 Fresh")
        self.assertAlmostEqual(tier["drop_pct"], 0.0)

    def test_get_tier_warm(self):
        tier = self.mod._get_aging_tier(10)
        self.assertEqual(tier["label"], "🟡 Warm")
        self.assertAlmostEqual(tier["drop_pct"], 0.05)

    def test_get_tier_aging(self):
        tier = self.mod._get_aging_tier(17)
        self.assertEqual(tier["label"], "🟠 Aging")
        self.assertAlmostEqual(tier["drop_pct"], 0.10)

    def test_get_tier_stale(self):
        tier = self.mod._get_aging_tier(25)
        self.assertEqual(tier["label"], "🔴 Stale")
        self.assertAlmostEqual(tier["drop_pct"], 0.15)

    def test_get_tier_critical(self):
        tier = self.mod._get_aging_tier(35)
        self.assertEqual(tier["label"], "⚫ Critical")
        self.assertAlmostEqual(tier["drop_pct"], 0.20)

    # ── 3d. _get_suggested_price ──────────────────────────────────────────────
    def test_suggested_price_fresh_no_drop(self):
        """Fresh items (< 7 days) should not have a price drop."""
        new_price, reason = self.mod._get_suggested_price(200.0, 3)
        self.assertEqual(new_price, 200.0)

    def test_suggested_price_stale_drops(self):
        """Stale items (21–30 days) should have a 15% price drop."""
        new_price, reason = self.mod._get_suggested_price(200.0, 25)
        self.assertAlmostEqual(new_price, 170.0, places=1)

    # ── 4. _create_item and load round-trip ───────────────────────────────────
    def test_add_and_load_item(self):
        self.mod._create_item(
            user_id=0,
            shoe_name="Jordan 4 Red Thunder",
            brand="Jordan",
            colorway="Black/Fire Red",
            size="10",
            cost_basis=180.0,
            condition="New with box",
            listed_date=None,
            listed_price=None,
            listed_platform="Unlisted",
            notes="Test note",
        )
        items = self.mod._load_inventory(user_id=0, status="inventory")
        self.assertTrue(len(items) > 0)
        self.assertEqual(items[0]["shoe_name"], "Jordan 4 Red Thunder")
        self.assertAlmostEqual(items[0]["cost_basis"], 180.0, places=2)

    def test_delete_item(self):
        self.mod._create_item(
            user_id=0,
            shoe_name="Delete Me",
            brand="",
            colorway="",
            size="9",
            cost_basis=100.0,
            condition="New with box",
            listed_date=None,
            listed_price=None,
            listed_platform="Unlisted",
            notes="",
        )
        items = self.mod._load_inventory(user_id=0, status="inventory")
        item_id = int(items[0]["id"])
        self.mod._delete_item(item_id)
        items_after = self.mod._load_inventory(user_id=0, status="inventory")
        self.assertEqual(len(items_after), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS — AI LISTING GENERATOR (Page 86)
# ═══════════════════════════════════════════════════════════════════════════════
class TestSoleOpsListingGenerator(unittest.TestCase):
    """Tests for pages/86_soleops_listing_generator.py"""

    def setUp(self):
        import tempfile
        self.db_file  = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path  = self.db_file.name
        self.db_file.close()

        self._st_patch  = patch.dict(sys.modules, {"streamlit": _make_st_stub()})
        self._db_stub   = _make_db_stub(self.db_path)
        self._auth_stub = _make_auth_stub()
        self._db_patch  = patch.dict(sys.modules, {
            "utils.db":    self._db_stub,
            "utils.auth":  self._auth_stub,
            "anthropic":   _make_anthropic_stub(),
        })
        self._st_patch.start()
        self._db_patch.start()

        if "listing_gen" in sys.modules:
            del sys.modules["listing_gen"]
        spec = importlib.util.spec_from_file_location(
            "listing_gen",
            os.path.join(ROOT, "pages", "86_soleops_listing_generator.py"),
        )
        self.mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(self.mod)
        except _StopExecution:
            pass  # st.stop() was called — module functions are still accessible

    def tearDown(self):
        self._st_patch.stop()
        self._db_patch.stop()
        import os as _os
        try:
            _os.unlink(self.db_path)
        except Exception:
            pass

    # ── 1. Import check ────────────────────────────────────────────────────────
    def test_import(self):
        self.assertTrue(hasattr(self.mod, "_ensure_tables"))
        self.assertTrue(hasattr(self.mod, "_generate_listing"))
        self.assertTrue(hasattr(self.mod, "_save_draft"))
        self.assertTrue(hasattr(self.mod, "_load_drafts"))
        self.assertTrue(hasattr(self.mod, "_delete_draft"))
        self.assertTrue(hasattr(self.mod, "_fetch_ebay_avg"))
        self.assertTrue(hasattr(self.mod, "_fetch_mercari_avg"))

    # ── 2. DB table creation ───────────────────────────────────────────────────
    def test_ensure_tables_creates_listing_drafts(self):
        conn = sqlite3.connect(self.db_path)
        cur  = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='soleops_listing_drafts'"
        )
        self.assertIsNotNone(cur.fetchone(), "soleops_listing_drafts table should exist")
        conn.close()

    # ── 3. _generate_listing — no API key returns error ───────────────────────
    def test_generate_listing_no_api_key_returns_error(self):
        result = self.mod._generate_listing(
            shoe_name="Jordan 1 Chicago",
            sku="555088-101",
            size="10",
            condition="Deadstock / New (DS)",
            colorway="Varsity Red/White",
            extra_notes="OG box included",
            target_platform="Both",
            cogs=150.0,
            ebay_avg=220.0,
            mercari_avg=200.0,
            api_key="",
        )
        self.assertIn("error", result)
        self.assertIn("API key", result["error"])

    # ── 4. _generate_listing — mocked Claude response ─────────────────────────
    def test_generate_listing_mocked_claude(self):
        mock_response_json = """{
  "ebay_title": "Nike Air Jordan 1 High OG Chicago Size 10 Deadstock DS 555088-101",
  "ebay_description": "Up for sale is a deadstock pair of the iconic Air Jordan 1 High OG Chicago.\\n\\nCondition: Brand new, never worn. Original box included.\\n\\nSize: Men's US 10, true to size.\\n\\nShipping: Ships same or next business day via USPS Priority Mail with tracking.",
  "mercari_description": "Selling my DS Jordan 1 Chicago size 10! Never worn, OG box included. Ships fast! Open to reasonable offers 🙏",
  "pricing_strategy": "List at $209 on eBay — 5% below the $220 avg — to generate views in the first 48 hours. At $209 your net after eBay fees is roughly $182, giving you a solid $32 profit on the $150 cost basis. Expect to sell within 3-5 days at this price.",
  "keywords": "Jordan 1, Jordan 1 Chicago, Air Jordan 1, Jordan 1 OG, 555088-101, Deadstock, Chicago colorway, size 10, sneakers, kicks",
  "suggested_price": 209.0
}"""
        mock_content = MagicMock()
        mock_content.text = mock_response_json

        mock_message = MagicMock()
        mock_message.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = self.mod._generate_listing(
                shoe_name="Air Jordan 1 High OG Chicago",
                sku="555088-101",
                size="10",
                condition="Deadstock / New (DS)",
                colorway="Varsity Red/White/Black",
                extra_notes="OG box included",
                target_platform="Both",
                cogs=150.0,
                ebay_avg=220.0,
                mercari_avg=200.0,
                api_key="sk-ant-test-key",
            )

        self.assertNotIn("error", result)
        self.assertIn("ebay_title",           result)
        self.assertIn("ebay_description",     result)
        self.assertIn("mercari_description",  result)
        self.assertIn("pricing_strategy",     result)
        self.assertIn("keywords",             result)
        self.assertIn("suggested_price",      result)
        self.assertAlmostEqual(float(result["suggested_price"]), 209.0, places=1)
        self.assertLessEqual(len(result["ebay_title"]), 80,
                             "eBay title must be 80 chars or less")

    # ── 5. Draft save and load round-trip ─────────────────────────────────────
    def test_save_and_load_draft(self):
        self.mod._save_draft({
            "shoe_name":            "Jordan 4 Red Thunder",
            "sku":                  "CT8527-016",
            "size":                 "10",
            "condition":            "Deadstock / New (DS)",
            "colorway":             "Black/Fire Red",
            "extra_notes":          "OG box",
            "target_platform":      "Both",
            "cogs":                 180.0,
            "ebay_avg_price":       240.0,
            "mercari_avg_price":    220.0,
            "suggested_price":      228.0,
            "ebay_title":           "Nike Air Jordan 4 Retro Red Thunder CT8527-016 Size 10 DS",
            "ebay_description":     "Test eBay description",
            "mercari_description":  "Test Mercari description",
            "pricing_strategy":     "List at $228 on eBay for fast sale.",
            "keywords":             "Jordan 4, Red Thunder, CT8527-016",
            "status":               "draft",
        })
        df = self.mod._load_drafts()
        self.assertFalse(df.empty)
        self.assertEqual(df.iloc[0]["shoe_name"], "Jordan 4 Red Thunder")
        self.assertAlmostEqual(float(df.iloc[0]["suggested_price"]), 228.0, places=1)

    def test_delete_draft(self):
        self.mod._save_draft({
            "shoe_name":            "Delete Me Draft",
            "sku":                  "",
            "size":                 "9",
            "condition":            "Like New (VNDS)",
            "colorway":             "",
            "extra_notes":          "",
            "target_platform":      "eBay",
            "cogs":                 100.0,
            "ebay_avg_price":       160.0,
            "mercari_avg_price":    0.0,
            "suggested_price":      152.0,
            "ebay_title":           "Test Shoe Size 9 VNDS",
            "ebay_description":     "",
            "mercari_description":  "",
            "pricing_strategy":     "",
            "keywords":             "",
            "status":               "draft",
        })
        df = self.mod._load_drafts()
        draft_id = int(df.iloc[0]["id"])
        self.mod._delete_draft(draft_id)
        df_after = self.mod._load_drafts()
        self.assertTrue(df_after.empty)

    # ── 6. Price fetch fallback (network fails → mock data) ───────────────────
    def test_fetch_ebay_avg_fallback_when_no_token(self):
        """With no eBay API key stored, _fetch_ebay_avg should return mock data."""
        result = self.mod._fetch_ebay_avg("Jordan 1 Chicago size 10")
        self.assertIn("avg",   result)
        self.assertIn("count", result)
        self.assertTrue(result["mock"], "Should fall back to mock when no API key")
        self.assertGreater(result["avg"], 0)

    def test_fetch_mercari_avg_fallback_on_network_error(self):
        """With network error, _fetch_mercari_avg should return mock data."""
        with patch("requests.post", side_effect=Exception("Network error")):
            result = self.mod._fetch_mercari_avg("Jordan 1 Chicago size 10")
        self.assertIn("avg",   result)
        self.assertTrue(result["mock"])
        self.assertGreater(result["avg"], 0)

    # ── 7. _update_draft_status ───────────────────────────────────────────────
    def test_update_draft_status(self):
        self.mod._save_draft({
            "shoe_name":            "Status Test Shoe",
            "sku":                  "",
            "size":                 "10",
            "condition":            "Like New (VNDS)",
            "colorway":             "",
            "extra_notes":          "",
            "target_platform":      "eBay",
            "cogs":                 120.0,
            "ebay_avg_price":       180.0,
            "mercari_avg_price":    0.0,
            "suggested_price":      171.0,
            "ebay_title":           "Status Test Shoe Size 10 VNDS",
            "ebay_description":     "",
            "mercari_description":  "",
            "pricing_strategy":     "",
            "keywords":             "",
            "status":               "draft",
        })
        df = self.mod._load_drafts()
        draft_id = int(df.iloc[0]["id"])

        self.mod._update_draft_status(draft_id, "published")
        df_after = self.mod._load_drafts()
        self.assertEqual(df_after.iloc[0]["status"], "published")


if __name__ == "__main__":
    unittest.main(verbosity=2)
