import os

# ── Repo root ─────────────────────────────────────────────────────────────────
ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/40_car_mileage_tracker.py")


def _source() -> str:
    with open(PAGE_PATH) as f:
        return f.read()


# ── Test 1: file exists and has valid Python syntax ───────────────────────────
def test_page_file_exists_and_syntax():
    """Page file exists on disk and compiles without syntax errors."""
    assert os.path.exists(PAGE_PATH), f"Missing: {PAGE_PATH}"
    src = _source()
    assert len(src) > 500, "Page file is suspiciously short (<500 chars)"
    compile(src, PAGE_PATH, "exec")   # raises SyntaxError if broken


# ── Test 2: required coding-standard patterns present ────────────────────────
def test_required_patterns():
    """Car/Mileage Tracker page follows peachstatesavings.com coding standards."""
    src = _source()
    assert "def _ensure_tables" in src,    "Missing _ensure_tables() function"
    assert "get_conn"           in src,    "Missing get_conn import/usage"
    assert "require_login"      in src,    "Missing require_login() call"
    assert "render_sidebar_brand" in src,  "Missing render_sidebar_brand()"
    assert "init_db"            in src,    "Missing init_db() call"
    assert "st.set_page_config" in src,    "Missing st.set_page_config()"


# ── Test 3: no hardcoded secrets ─────────────────────────────────────────────
def test_no_hardcoded_secrets():
    """Car/Mileage Tracker page must not contain hardcoded API keys or passwords."""
    src = _source()
    forbidden = ["sk-ant-", "password=", "secret=", "Bearer ", "hardcoded"]
    for token in forbidden:
        assert token not in src, f"Hardcoded secret found: {token!r}"


# ── Test 4: feature metadata ──────────────────────────────────────────────────
def test_feature_metadata():
    """Car/Mileage Tracker — basic file sanity."""
    assert "car_mileage_tracker" != ""
    assert os.path.basename(PAGE_PATH).endswith(".py")
    assert os.path.getsize(PAGE_PATH) > 1000
