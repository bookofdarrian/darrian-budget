"""Unit tests for page 68 — SoleOps Price Monitor Dashboard."""
import os

ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/68_soleops_price_monitor.py")


def _source() -> str:
    with open(PAGE_PATH) as f:
        return f.read()


def test_page_file_exists_and_syntax():
    """Page file exists on disk and compiles without syntax errors."""
    assert os.path.exists(PAGE_PATH), f"Missing: {PAGE_PATH}"
    src = _source()
    assert len(src) > 500, "Page file is suspiciously short (<500 chars)"
    compile(src, PAGE_PATH, "exec")


def test_required_patterns():
    """SoleOps Price Monitor follows peachstatesavings.com coding standards."""
    src = _source()
    assert "def _ensure_tables" in src,       "Missing _ensure_tables() function"
    assert "get_conn"           in src,       "Missing get_conn import/usage"
    assert "require_login"      in src,       "Missing require_login"
    assert "render_sidebar_brand" in src,     "Missing render_sidebar_brand"
    assert "USE_POSTGRES"       in src,       "Missing USE_POSTGRES flag"
    assert "init_db"            in src,       "Missing init_db()"
    assert "inject_css"         in src,       "Missing inject_css()"
    assert "conn.close()"       in src,       "Missing conn.close() — potential connection leak"


def test_db_table_names():
    """Required SoleOps price monitor DB tables are referenced in source."""
    src = _source()
    expected_tables = ["soleops_watchlist", "soleops_price_history"]
    for table in expected_tables:
        assert table in src, f"Missing DB table reference: {table}"


def test_fee_constants():
    """eBay and Mercari platform fee rates are defined."""
    src = _source()
    assert "0.129" in src or "12.9" in src,  "Missing eBay fee rate (12.9%)"
    assert "0.10"  in src or "MERCARI" in src, "Missing Mercari fee rate"


def test_sidebar_links():
    """All required sidebar page_link calls are present."""
    src = _source()
    assert 'page_link("app.py"'                         in src
    assert 'page_link("pages/22_todo.py"'               in src
    assert 'page_link("pages/24_creator_companion.py"'  in src
    assert 'page_link("pages/25_notes.py"'              in src
    assert 'page_link("pages/26_media_library.py"'      in src
    assert 'page_link("pages/17_personal_assistant.py"' in src


def test_ebay_integration():
    """eBay API or mock fallback is implemented."""
    src = _source()
    assert "ebay" in src.lower(), "Missing eBay integration"


def test_mercari_integration():
    """Mercari mock/integration is implemented."""
    src = _source()
    assert "mercari" in src.lower(), "Missing Mercari integration"


def test_profit_calculator():
    """Profit-after-fees calculation logic is present."""
    src = _source()
    assert "profit" in src.lower(), "Missing profit calculation"
    assert "fee" in src.lower(),    "Missing fee calculation"


def test_tabs_present():
    """Required tabs are defined in the page."""
    src = _source()
    assert "Watchlist"    in src or "watchlist"  in src.lower()
    assert "Price"        in src
    assert "Profit"       in src or "Calculator" in src


def test_create_table_statements():
    """CREATE TABLE IF NOT EXISTS statements exist."""
    src = _source()
    assert "CREATE TABLE IF NOT EXISTS" in src
