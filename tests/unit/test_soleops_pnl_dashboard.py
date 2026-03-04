"""Unit tests for page 69 — SoleOps P&L Dashboard."""
import os

ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/69_soleops_pnl_dashboard.py")


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
    """SoleOps P&L Dashboard follows peachstatesavings.com coding standards."""
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
    """Required P&L DB tables are referenced in source."""
    src = _source()
    assert "soleops_sales" in src, "Missing soleops_sales table"


def test_platform_fees():
    """All major platform fee rates are defined."""
    src = _source()
    assert "0.129" in src or "12.9" in src,  "Missing eBay fee rate (12.9%)"
    assert "0.115" in src or "11.5" in src,  "Missing StockX fee rate (11.5%)"
    assert "GOAT"  in src,                   "Missing GOAT platform"
    assert "Mercari" in src,                 "Missing Mercari platform"


def test_ai_call():
    """Claude AI integration is present."""
    src = _source()
    assert "claude-opus-4-5" in src, "Missing or wrong Claude model"


def test_ai_guard():
    """AI calls are guarded with api_key check."""
    src = _source()
    assert "if not api_key" in src, "Missing api_key null-check before AI call"


def test_sidebar_links():
    """All required sidebar page_link calls are present."""
    src = _source()
    assert 'page_link("app.py"'                         in src
    assert 'page_link("pages/22_todo.py"'               in src
    assert 'page_link("pages/24_creator_companion.py"'  in src
    assert 'page_link("pages/25_notes.py"'              in src
    assert 'page_link("pages/26_media_library.py"'      in src
    assert 'page_link("pages/17_personal_assistant.py"' in src


def test_tabs_present():
    """Required P&L tabs are defined."""
    src = _source()
    assert "Overview"   in src or "overview" in src.lower()
    assert "Sales"      in src
    assert "Platform"   in src
    assert "Monthly"    in src or "Trend" in src
    assert "Tax"        in src or "Schedule" in src


def test_pnl_metrics():
    """Core P&L metric calculations are present."""
    src = _source()
    assert "COGS"    in src or "cogs"    in src.lower(), "Missing COGS calculation"
    assert "profit"  in src.lower(),                     "Missing profit calculation"
    assert "revenue" in src.lower(),                     "Missing revenue calculation"


def test_create_table_statements():
    """CREATE TABLE IF NOT EXISTS statements exist."""
    src = _source()
    assert "CREATE TABLE IF NOT EXISTS soleops_sales" in src
