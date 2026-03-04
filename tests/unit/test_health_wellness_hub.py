"""Unit tests for page 66 — Health & Wellness AI Hub."""
import os
import sqlite3
import unittest.mock as mock

ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/66_health_wellness_hub.py")


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
    """Health & Wellness Hub page follows peachstatesavings.com coding standards."""
    src = _source()
    assert "def _ensure_tables" in src,       "Missing _ensure_tables() function"
    assert "get_conn"           in src,       "Missing get_conn import/usage"
    assert "require_login"      in src,       "Missing require_login"
    assert "render_sidebar_brand" in src,     "Missing render_sidebar_brand"
    assert "USE_POSTGRES"       in src,       "Missing USE_POSTGRES flag"
    assert "init_db"            in src,       "Missing init_db()"
    assert "inject_css"         in src,       "Missing inject_css()"
    assert "conn.close()"       in src,       "Missing conn.close() — potential connection leak"
    assert "claude-opus-4-5"    in src,       "Missing claude-opus-4-5 model string"
    assert "anthropic_api_key"  in src,       "Missing anthropic_api_key lookup"


def test_db_table_names():
    """All required health & wellness DB tables are referenced in source."""
    src = _source()
    expected_tables = [
        "hw_mood_logs",
        "hw_workouts",
        "hw_medications",
        "hw_doctor_visits",
        "hw_vaccines",
        "hw_health_goals",
    ]
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
    """All 5 required tabs are defined."""
    src = _source()
    assert "Daily Check-In"   in src or "check" in src.lower()
    assert "Workout"          in src
    assert "Medication"       in src
    assert "Doctor"           in src or "Vaccine" in src
    assert "AI Health"        in src or "Insights" in src


def test_mood_options_defined():
    """Mood options constant is defined with expected values."""
    src = _source()
    assert "MOOD_OPTIONS" in src
    assert "Great"  in src
    assert "Neutral" in src


def test_ai_guard():
    """AI calls are guarded with api_key check."""
    src = _source()
    assert "if not api_key" in src, "Missing api_key null-check before AI call"


def test_ensure_tables_compiles():
    """_ensure_tables function is syntactically sound (compile check)."""
    src = _source()
    compile(src, PAGE_PATH, "exec")
    # Extract _ensure_tables body to verify it has CREATE TABLE IF NOT EXISTS
    assert "CREATE TABLE IF NOT EXISTS hw_mood_logs"    in src
    assert "CREATE TABLE IF NOT EXISTS hw_workouts"     in src
    assert "CREATE TABLE IF NOT EXISTS hw_medications"  in src
    assert "CREATE TABLE IF NOT EXISTS hw_doctor_visits" in src
    assert "CREATE TABLE IF NOT EXISTS hw_vaccines"     in src
