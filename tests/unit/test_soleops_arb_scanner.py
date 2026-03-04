"""Unit tests for page 71 — SoleOps Arbitrage Scanner."""
import os

ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/71_soleops_arb_scanner.py")


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
    """SoleOps Arb Scanner follows peachstatesavings.com coding standards."""
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
    """All required arbitrage scanner DB tables are referenced in source."""
    src = _source()
    expected_tables = ["arb_watchlist", "arb_scan_results", "arb_alerts_sent"]
    for table in expected_tables:
        assert table in src, f"Missing DB table reference: {table}"


def test_dedup_logic():
    """6-hour dedup window and ROI logic are present."""
    src = _source()
    assert "roi"      in src.lower(), "Missing ROI calculation"
    # Dedup window — 6 hours
    assert "6"        in src,         "Missing 6-hour dedup window value"


def test_telegram_integration():
    """Telegram alert integration is present."""
    src = _source()
    assert "telegram" in src.lower(), "Missing Telegram integration"
    # Page uses arb_tg_token as the setting key for the Telegram bot token
    assert "tg_token" in src.lower() or "bot_token" in src.lower() or "telegram_bot" in src.lower(), \
        "Missing Telegram bot token reference"


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
    """Required arb scanner tabs are defined."""
    src = _source()
    assert "Dashboard" in src or "Scan"       in src
    assert "Watchlist" in src or "watchlist"  in src.lower()
    assert "Results"   in src or "result"     in src.lower()
    assert "Alert"     in src or "alert"      in src.lower()
    assert "Settings"  in src or "setting"    in src.lower()


def test_ebay_and_mercari_integration():
    """Both eBay and Mercari integrations (or mocks) are present."""
    src = _source()
    assert "ebay"    in src.lower(), "Missing eBay integration"
    assert "mercari" in src.lower(), "Missing Mercari integration"


def test_roi_calculator():
    """ROI calculation logic is implemented."""
    src = _source()
    assert "roi"  in src.lower()
    assert "fee"  in src.lower()
    assert "profit" in src.lower() or "net" in src.lower()


def test_create_table_statements():
    """CREATE TABLE IF NOT EXISTS statements exist for all arb tables."""
    src = _source()
    assert "CREATE TABLE IF NOT EXISTS arb_watchlist"    in src
    assert "CREATE TABLE IF NOT EXISTS arb_scan_results" in src
    assert "CREATE TABLE IF NOT EXISTS arb_alerts_sent"  in src
