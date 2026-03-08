"""
Unit Tests — Todo Brain Dump + Resale Price Advisor
Tests for:
  - pages/22_todo.py  (brain dump, DB tables, helpers)
  - pages/72_resale_price_advisor.py  (DB tables, market search helpers, pricing logic)
"""
import sys
import os
import json
import sqlite3
import types

import pytest

# ── Ensure project root is on path ────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TODO_PAGE   = os.path.join(PROJECT_ROOT, "pages", "22_todo.py")
RESALE_PAGE = os.path.join(PROJECT_ROOT, "pages", "72_resale_price_advisor.py")


# ══════════════════════════════════════════════════════════════════════════════
# ── Streamlit stub (follows existing test_budget_app.py pattern) ──────────────
# ══════════════════════════════════════════════════════════════════════════════

def _stub_streamlit():
    """Minimal streamlit stub so page modules can be exec'd in tests."""
    if "streamlit" in sys.modules:
        return sys.modules["streamlit"]
    mod = types.ModuleType("streamlit")
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
    mod.slider                = lambda *a, **k: 30
    mod.progress              = lambda *a, **k: None
    mod.metric                = lambda *a, **k: None
    mod.expander              = lambda *a, **k: _ctx()
    mod.container             = lambda *a, **k: _ctx()
    mod.form                  = lambda *a, **k: _ctx()
    mod.status                = lambda *a, **k: _ctx()
    mod.tabs                  = lambda labels: [_ctx() for _ in labels]
    mod.columns               = lambda *a, **k: [_ctx()] * (a[0] if a and isinstance(a[0], int) else len(a[0]) if a else 2)
    mod.form_submit_button    = lambda *a, **k: False
    mod.session_state         = {}
    mod.sidebar               = types.SimpleNamespace(
        markdown=lambda *a, **k: None,
        page_link=lambda *a, **k: None,
        expander=lambda *a, **k: _ctx(),
        text_input=lambda *a, **k: "",
        button=lambda *a, **k: False,
    )
    sys.modules["streamlit"] = mod
    # Also stub sub-modules used by some pages
    for sub in ["streamlit.components", "streamlit.components.v1"]:
        sys.modules.setdefault(sub, types.ModuleType(sub))
    return mod


class _ctx:
    """Context manager stub for st.expander / st.container / st.form / st.tabs."""
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def __call__(self, *a, **k):
        return self
    # Proxy common widget calls inside with-blocks
    markdown = lambda self, *a, **k: None
    caption  = lambda self, *a, **k: None
    write    = lambda self, *a, **k: None
    button   = lambda self, *a, **k: False
    text_input = lambda self, *a, **k: ""
    metric   = lambda self, *a, **k: None
    update   = lambda self, *a, **k: None


# ══════════════════════════════════════════════════════════════════════════════
# ── Shared fixture: fresh SQLite DB + monkey-patched utils ───────────────────
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def stub_st():
    """Auto-stub streamlit before every test."""
    _stub_streamlit()
    yield


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Spin up a fresh SQLite DB and monkey-patch utils.db helpers."""
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


# ══════════════════════════════════════════════════════════════════════════════
# ── Helper: extract only helper functions/constants from a page file ──────────
# ══════════════════════════════════════════════════════════════════════════════

def _extract_helpers(page_path: str) -> dict:
    """
    Parse the page file with AST, extract only function defs and module-level
    constants/imports, then exec them in a namespace that uses the (already
    monkeypatched) utils.db helpers.
    """
    import ast
    import utils.db as db_mod

    with open(page_path) as f:
        source = f.read()

    tree = ast.parse(source)
    safe_nodes = []
    for node in tree.body:
        if isinstance(node, (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
            ast.Assign, ast.AugAssign, ast.AnnAssign,
            ast.Import, ast.ImportFrom,
        )):
            safe_nodes.append(node)

    safe_module = ast.Module(body=safe_nodes, type_ignores=[])
    code = compile(safe_module, page_path, "exec")

    ns: dict = {
        "__builtins__": __builtins__,
        "__file__":     page_path,          # needed for _Path(__file__) in todo page
        "get_conn":     db_mod.get_conn,
        "USE_POSTGRES": db_mod.USE_POSTGRES,
        "db_exec":      db_mod.execute,
        "get_setting":  db_mod.get_setting,
        "set_setting":  db_mod.set_setting,
        "json":         json,
        "datetime":     __import__("datetime").datetime,
        "date":         __import__("datetime").date,
        "re":           __import__("re"),
        "base64":       __import__("base64"),
        "st":           sys.modules["streamlit"],
    }
    exec(code, ns)
    return ns


# ══════════════════════════════════════════════════════════════════════════════
# ── TESTS: pages/22_todo.py ───────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

class TestTodoBrainDump:
    """Tests for the brain dump + core task helpers in 22_todo.py."""

    def test_todo_page_file_exists(self):
        assert os.path.isfile(TODO_PAGE), "22_todo.py must exist"

    def test_todo_page_syntax(self):
        with open(TODO_PAGE) as f:
            source = f.read()
        compile(source, TODO_PAGE, "exec")  # raises SyntaxError if broken

    def test_ensure_tasks_table_creates_pa_tasks(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pa_tasks'"
        ).fetchone()
        conn.close()
        assert row is not None, "pa_tasks table must be created"

    def test_ensure_tasks_table_creates_brain_dumps(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='todo_brain_dumps'"
        ).fetchone()
        conn.close()
        assert row is not None, "todo_brain_dumps table must be created"

    def test_add_task_inserts_row(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Buy milk", None, "normal", "from the store")
        conn = fake_get_conn()
        row = conn.execute("SELECT * FROM pa_tasks WHERE title='Buy milk'").fetchone()
        conn.close()
        assert row is not None
        assert dict(row)["priority"] == "normal"
        assert dict(row)["status"] == "open"

    def test_add_task_with_brain_dump_source(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Call dentist", None, "high", "morning appt", source="brain_dump")
        conn = fake_get_conn()
        row = conn.execute("SELECT source FROM pa_tasks WHERE title='Call dentist'").fetchone()
        conn.close()
        assert row is not None
        assert dict(row)["source"] == "brain_dump"

    def test_complete_task(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Finish report", None, "high", "")
        conn = fake_get_conn()
        task_id = conn.execute("SELECT id FROM pa_tasks WHERE title='Finish report'").fetchone()[0]
        conn.close()
        ns["_complete_task"](task_id)
        conn = fake_get_conn()
        row = dict(conn.execute("SELECT status FROM pa_tasks WHERE id=?", (task_id,)).fetchone())
        conn.close()
        assert row["status"] == "done"

    def test_reopen_task(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Review PRs", None, "normal", "")
        conn = fake_get_conn()
        task_id = conn.execute("SELECT id FROM pa_tasks WHERE title='Review PRs'").fetchone()[0]
        conn.close()
        ns["_complete_task"](task_id)
        ns["_reopen_task"](task_id)
        conn = fake_get_conn()
        row = dict(conn.execute("SELECT status FROM pa_tasks WHERE id=?", (task_id,)).fetchone())
        conn.close()
        assert row["status"] == "open"

    def test_delete_task(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Delete me", None, "low", "")
        conn = fake_get_conn()
        task_id = conn.execute("SELECT id FROM pa_tasks WHERE title='Delete me'").fetchone()[0]
        conn.close()
        ns["_delete_task"](task_id)
        conn = fake_get_conn()
        row = conn.execute("SELECT id FROM pa_tasks WHERE title='Delete me'").fetchone()
        conn.close()
        assert row is None

    def test_load_tasks_returns_list(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Task A", None, "normal", "")
        ns["_add_task"]("Task B", None, "high", "")
        result = ns["_load_tasks"](["open"])
        assert isinstance(result, list)
        assert len(result) == 2

    def test_load_tasks_respects_status_filter(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Open task", None, "normal", "")
        conn = fake_get_conn()
        task_id = conn.execute("SELECT id FROM pa_tasks WHERE title='Open task'").fetchone()[0]
        conn.close()
        ns["_complete_task"](task_id)
        open_tasks = ns["_load_tasks"](["open"])
        done_tasks = ns["_load_tasks"](["done"])
        assert len(open_tasks) == 0
        assert len(done_tasks) == 1

    def test_save_dump(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_save_dump"]("Call mom\nPay bills\nFix the sink")
        conn = fake_get_conn()
        row = conn.execute("SELECT raw_text FROM todo_brain_dumps").fetchone()
        conn.close()
        assert row is not None
        assert "Call mom" in dict(row)["raw_text"]

    def test_priority_badge_returns_html(self, tmp_db):
        ns = _extract_helpers(TODO_PAGE)
        badge = ns["_priority_badge"]("high")
        assert "<span" in badge
        assert "🔴" in badge

    def test_due_badge_overdue(self, tmp_db):
        ns = _extract_helpers(TODO_PAGE)
        badge = ns["_due_badge"]("2020-01-01")
        assert "Overdue" in badge

    def test_due_badge_empty_for_none(self, tmp_db):
        ns = _extract_helpers(TODO_PAGE)
        assert ns["_due_badge"](None) == ""

    def test_update_task(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(TODO_PAGE)
        ns["_ensure_tasks_table"]()
        ns["_add_task"]("Old title", None, "low", "old notes")
        conn = fake_get_conn()
        task_id = conn.execute("SELECT id FROM pa_tasks").fetchone()[0]
        conn.close()
        ns["_update_task"](task_id, "New title", None, "high", "new notes")
        conn = fake_get_conn()
        row = dict(conn.execute(
            "SELECT title, priority, notes FROM pa_tasks WHERE id=?", (task_id,)
        ).fetchone())
        conn.close()
        assert row["title"] == "New title"
        assert row["priority"] == "high"
        assert row["notes"] == "new notes"

    def test_parse_dump_with_ai_no_key(self, tmp_db):
        """_parse_dump_with_ai returns [] when no API key is configured."""
        ns = _extract_helpers(TODO_PAGE)
        # get_setting is stubbed to return "" → no API key
        result = ns["_parse_dump_with_ai"]("Call mom\nPay bills")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_priority_colors_constant(self, tmp_db):
        ns = _extract_helpers(TODO_PAGE)
        assert "PRIORITY_COLORS" in ns
        assert "high" in ns["PRIORITY_COLORS"]
        assert "normal" in ns["PRIORITY_COLORS"]
        assert "low" in ns["PRIORITY_COLORS"]


# ══════════════════════════════════════════════════════════════════════════════
# ── TESTS: pages/72_resale_price_advisor.py ───────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

class TestResalePriceAdvisor:
    """Tests for Resale Price Advisor (72_resale_price_advisor.py)."""

    def test_resale_page_file_exists(self):
        assert os.path.isfile(RESALE_PAGE), "72_resale_price_advisor.py must exist"

    def test_resale_page_syntax(self):
        with open(RESALE_PAGE) as f:
            source = f.read()
        compile(source, RESALE_PAGE, "exec")

    def test_ensure_tables_creates_resale_price_lookups(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(RESALE_PAGE)
        ns["_ensure_tables"]()
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='resale_price_lookups'"
        ).fetchone()
        conn.close()
        assert row is not None, "resale_price_lookups table must be created"

    def test_save_lookup_inserts_row(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(RESALE_PAGE)
        ns["_ensure_tables"]()
        ns["_save_lookup"]({
            "product_name":           "Nike Air Force 1",
            "brand":                  "Nike",
            "condition":              "Like New",
            "image_provided":         True,
            "recommended_price":      95.0,
            "listing_type":           "Buy It Now",
            "shipping_recommendation":"USPS Priority",
            "platform":               "eBay",
            "ai_analysis":            '{"recommended_price": 95.0}',
            "ebay_comps":             [{"title": "AF1", "price": 90.0}],
            "mercari_comps":          [],
        })
        conn = fake_get_conn()
        row = conn.execute(
            "SELECT * FROM resale_price_lookups WHERE product_name='Nike Air Force 1'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert dict(row)["brand"] == "Nike"
        assert dict(row)["recommended_price"] == 95.0

    def test_load_history_returns_list(self, tmp_db):
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(RESALE_PAGE)
        ns["_ensure_tables"]()
        ns["_save_lookup"]({
            "product_name": "Jordan 1 Retro High OG", "brand": "Nike/Jordan",
            "condition": "Good", "image_provided": False, "recommended_price": 180.0,
            "listing_type": "Auction with BIN", "shipping_recommendation": "Free",
            "platform": "eBay", "ai_analysis": "{}", "ebay_comps": [], "mercari_comps": [],
        })
        result = ns["_load_history"](limit=10)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["product_name"] == "Jordan 1 Retro High OG"

    def test_load_history_respects_limit(self, tmp_db):
        _, _ = tmp_db
        ns = _extract_helpers(RESALE_PAGE)
        ns["_ensure_tables"]()
        for i in range(5):
            ns["_save_lookup"]({
                "product_name": f"Item {i}", "brand": "Brand", "condition": "Good",
                "image_provided": False, "recommended_price": float(i * 10),
                "listing_type": "Buy It Now", "shipping_recommendation": "",
                "platform": "eBay", "ai_analysis": "{}", "ebay_comps": [], "mercari_comps": [],
            })
        result = ns["_load_history"](limit=3)
        assert len(result) == 3

    def test_constants_defined(self, tmp_db):
        ns = _extract_helpers(RESALE_PAGE)
        assert "CONDITIONS" in ns
        assert "PLATFORMS" in ns
        assert "EBAY_FEE_RATE" in ns
        assert ns["EBAY_FEE_RATE"] > 0
        assert "eBay" in ns["PLATFORMS"]
        assert "Mercari" in ns["PLATFORMS"]
        assert len(ns["CONDITIONS"]) >= 5

    def test_identify_product_no_api_key(self, tmp_db):
        """Returns error dict when no API key configured."""
        ns = _extract_helpers(RESALE_PAGE)
        result = ns["_identify_product_with_ai"](
            image_b64="abc", mime_type="image/jpeg",
            brand="Nike", model_hint="Air Force 1",
            condition="Like New", size="10", weight="", extra_notes="",
        )
        assert isinstance(result, dict)
        assert "error" in result

    def test_generate_pricing_recommendation_no_api_key(self, tmp_db):
        """Returns error dict when no API key configured."""
        ns = _extract_helpers(RESALE_PAGE)
        result = ns["_generate_pricing_recommendation"](
            product_info={"product_name": "Nike AF1", "brand": "Nike", "category": "Sneakers"},
            ebay_comps=[{"price": 90.0}, {"price": 100.0}],
            mercari_comps=[{"price": 80.0}],
            condition="Like New",
            user_purchase_price=60.0,
            target_platforms=["eBay", "Mercari"],
        )
        assert isinstance(result, dict)
        assert "error" in result

    def test_scrape_ebay_sold_returns_list_on_failure(self, tmp_db, monkeypatch):
        """_scrape_ebay_sold gracefully returns [] on network error."""
        import unittest.mock as mock
        ns = _extract_helpers(RESALE_PAGE)
        with mock.patch("requests.get", side_effect=Exception("Network error")):
            result = ns["_scrape_ebay_sold"]("Nike Air Force 1", max_results=5)
        assert isinstance(result, list)

    def test_search_mercari_returns_list_on_failure(self, tmp_db, monkeypatch):
        """_search_mercari gracefully returns [] on network error."""
        import unittest.mock as mock
        ns = _extract_helpers(RESALE_PAGE)
        with mock.patch("requests.post", side_effect=Exception("Network error")):
            result = ns["_search_mercari"]("Jordan 1", max_results=5)
        assert isinstance(result, list)

    def test_save_lookup_ebay_comps_json_serialized(self, tmp_db):
        """eBay comps stored as JSON string in DB."""
        fake_get_conn, _ = tmp_db
        ns = _extract_helpers(RESALE_PAGE)
        ns["_ensure_tables"]()
        comps = [{"title": "Test item", "price": 55.0, "sold": True}]
        ns["_save_lookup"]({
            "product_name": "Test Product", "brand": "Test", "condition": "Good",
            "image_provided": False, "recommended_price": 50.0,
            "listing_type": "Buy It Now", "shipping_recommendation": "",
            "platform": "eBay", "ai_analysis": "{}",
            "ebay_comps": comps, "mercari_comps": [],
        })
        conn = fake_get_conn()
        row = dict(conn.execute("SELECT ebay_comps FROM resale_price_lookups").fetchone())
        conn.close()
        parsed = json.loads(row["ebay_comps"])
        assert isinstance(parsed, list)
        assert parsed[0]["price"] == 55.0

    def test_fee_rate_constants_valid(self, tmp_db):
        ns = _extract_helpers(RESALE_PAGE)
        assert 0 < ns["EBAY_FEE_RATE"] < 1
        assert 0 < ns["MERCARI_FEE"] < 1
        assert 0 < ns["DEPOP_FEE"] < 1
