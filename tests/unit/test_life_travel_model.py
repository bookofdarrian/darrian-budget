"""Unit tests for page 67 — Life Experience & Travel Model."""
import os

ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/67_life_travel_model.py")


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
    """Life & Travel page follows peachstatesavings.com coding standards."""
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
    """All required travel & life DB tables are referenced in source."""
    src = _source()
    expected_tables = ["trips", "flights", "hotels", "memories", "life_milestones"]
    for table in expected_tables:
        assert table in src, f"Missing DB table reference: {table}"


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
    """Required tabs/sections are defined."""
    src = _source()
    assert "Trip"         in src
    assert "Journal"      in src or "Memor" in src
    assert "Milestone"    in src
    assert "AI"           in src
    assert "Flight"       in src or "Hotel" in src


def test_ai_guard():
    """AI calls are guarded with api_key check."""
    src = _source()
    assert "if not api_key" in src, "Missing api_key null-check before AI call"


def test_claude_model():
    """Uses correct Claude model."""
    src = _source()
    assert "claude-opus-4-5" in src, "Missing or wrong Claude model"


def test_create_table_statements():
    """CREATE TABLE IF NOT EXISTS for each DB table."""
    src = _source()
    assert "CREATE TABLE IF NOT EXISTS" in src
