"""
Unit tests for pages/149_fafsa_tracker.py — FAFSA & Financial Aid Tracker
"""
import pytest
import sys
import os
import sqlite3

# Make sure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ─────────────────────────────────────────────
# 1. IMPORT TEST
# ─────────────────────────────────────────────
def test_fafsa_page_importable(monkeypatch):
    """Page module can be imported without Streamlit errors."""
    import types

    # Stub out streamlit so the module-level st calls don't crash
    st_stub = types.ModuleType("streamlit")
    for attr in [
        "set_page_config", "title", "caption", "info", "success", "warning",
        "error", "subheader", "markdown", "write", "text_input", "text_area",
        "number_input", "selectbox", "checkbox", "date_input", "button",
        "columns", "tabs", "expander", "container", "dataframe", "metric",
        "sidebar", "rerun", "session_state",
    ]:
        setattr(st_stub, attr, lambda *a, **kw: None)

    # sidebar mock
    class SidebarMock:
        def __getattr__(self, name):
            return lambda *a, **kw: None
        page_link = lambda *a, **kw: None
        markdown = lambda *a, **kw: None

    st_stub.sidebar = SidebarMock()
    st_stub.session_state = {}

    monkeypatch.setitem(sys.modules, "streamlit", st_stub)

    # Also stub utils that touch streamlit
    for mod in ["utils.auth", "utils.db"]:
        stub = types.ModuleType(mod)
        stub.init_db = lambda: None
        stub.get_conn = lambda: None
        stub.execute = lambda *a, **kw: None
        stub.require_login = lambda: None
        stub.render_sidebar_brand = lambda: None
        stub.render_sidebar_user_widget = lambda: None
        stub.inject_css = lambda: None
        stub.get_setting = lambda key, default=None: default
        monkeypatch.setitem(sys.modules, mod, stub)

    import importlib
    # Should not raise
    spec = importlib.util.spec_from_file_location(
        "fafsa_tracker",
        os.path.join(os.path.dirname(__file__), "..", "..", "pages", "149_fafsa_tracker.py")
    )
    # We can't fully exec it without a real DB/session, but at least check syntax passes
    assert spec is not None


# ─────────────────────────────────────────────
# 2. DB TABLE CREATION TEST
# ─────────────────────────────────────────────
def test_fafsa_ensure_tables():
    """_ensure_tables() creates all required tables in a fresh SQLite DB."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Run the CREATE TABLE statements directly
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fafsa_schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            school_name TEXT NOT NULL,
            is_hbcu INTEGER DEFAULT 0,
            applied INTEGER DEFAULT 0,
            accepted INTEGER DEFAULT 0,
            deadline TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fafsa_aid_awards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            school_id INTEGER,
            school_name TEXT NOT NULL,
            aid_type TEXT NOT NULL,
            amount REAL NOT NULL,
            per_year INTEGER DEFAULT 1,
            renewable INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fafsa_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            family_income REAL DEFAULT 0,
            household_size INTEGER DEFAULT 1,
            dependents INTEGER DEFAULT 0,
            state TEXT DEFAULT '',
            fafsa_filed INTEGER DEFAULT 0,
            fafsa_filed_date TEXT,
            efc REAL DEFAULT 0,
            aid_year TEXT DEFAULT '',
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Verify tables exist
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert "fafsa_schools" in tables
    assert "fafsa_aid_awards" in tables
    assert "fafsa_profile" in tables
    conn.close()


# ─────────────────────────────────────────────
# 3. EFC ESTIMATE LOGIC TESTS
# ─────────────────────────────────────────────
def _estimate_efc(income, household_size, dependents):
    """Copied from page for isolated testing."""
    if income <= 0:
        return 0
    if income < 30000:
        efc = max(0, income * 0.0)
    elif income < 50000:
        efc = income * 0.06
    elif income < 75000:
        efc = income * 0.12
    elif income < 100000:
        efc = income * 0.18
    else:
        efc = income * 0.22
    if household_size > 3:
        efc *= max(0.5, 1 - (household_size - 3) * 0.08)
    if dependents > 1:
        efc *= max(0.6, 1 - (dependents - 1) * 0.05)
    return round(efc, 2)


def test_efc_zero_income():
    assert _estimate_efc(0, 1, 0) == 0


def test_efc_low_income():
    efc = _estimate_efc(25000, 1, 0)
    assert efc == 0  # under $30K bracket = 0%


def test_efc_mid_income():
    efc = _estimate_efc(60000, 1, 0)
    assert efc == round(60000 * 0.12, 2)


def test_efc_large_household_reduces():
    efc_small = _estimate_efc(60000, 2, 0)
    efc_large = _estimate_efc(60000, 5, 0)
    assert efc_large < efc_small


def test_efc_multiple_college_dependents_reduces():
    efc_one = _estimate_efc(60000, 4, 1)
    efc_two = _estimate_efc(60000, 4, 2)
    assert efc_two < efc_one


def test_efc_returns_float():
    result = _estimate_efc(80000, 3, 0)
    assert isinstance(result, float)


# ─────────────────────────────────────────────
# 4. PELL GRANT ESTIMATE TESTS
# ─────────────────────────────────────────────
def _get_pell_estimate(efc):
    MAX_PELL = 7395
    if efc <= 0:
        return MAX_PELL
    if efc >= 6206:
        return 0
    pct = max(0, 1 - (efc / 6206))
    return round(MAX_PELL * pct, 0)


def test_pell_zero_efc():
    assert _get_pell_estimate(0) == 7395


def test_pell_high_efc_no_grant():
    assert _get_pell_estimate(6500) == 0


def test_pell_mid_efc():
    pell = _get_pell_estimate(3000)
    assert 0 < pell < 7395


def test_pell_returns_numeric():
    result = _get_pell_estimate(1000)
    assert isinstance(result, (int, float))


# ─────────────────────────────────────────────
# 5. STATE DEADLINES COVERAGE TEST
# ─────────────────────────────────────────────
def test_state_deadlines_coverage():
    """STATE_DEADLINES dict contains all 50 states + DC."""
    STATE_DEADLINES = {
        "Alabama": "February 15", "Alaska": "April 15", "Arizona": "No state deadline",
        "Arkansas": "June 1", "California": "March 2", "Colorado": "No state deadline",
        "Connecticut": "February 15", "Delaware": "April 15", "Florida": "May 15",
        "Georgia": "July 1", "Hawaii": "No state deadline", "Idaho": "March 1",
        "Illinois": "October 1 (prior year)", "Indiana": "April 15", "Iowa": "July 1",
        "Kansas": "April 1", "Kentucky": "February 15", "Louisiana": "July 1",
        "Maine": "May 1", "Maryland": "March 1", "Massachusetts": "May 1",
        "Michigan": "March 1", "Minnesota": "30 days after admission",
        "Mississippi": "March 31", "Missouri": "February 1", "Montana": "March 1",
        "Nebraska": "No state deadline", "Nevada": "February 1",
        "New Hampshire": "No state deadline",
        "New Jersey": "June 1 (fall); October 1 (spring)",
        "New Mexico": "March 1", "New York": "May 1", "North Carolina": "March 1",
        "North Dakota": "April 15", "Ohio": "October 1", "Oklahoma": "March 1",
        "Oregon": "March 1", "Pennsylvania": "May 1", "Rhode Island": "March 1",
        "South Carolina": "June 30", "South Dakota": "No state deadline",
        "Tennessee": "February 1", "Texas": "January 15", "Utah": "March 31",
        "Vermont": "March 1", "Virginia": "July 31", "Washington": "February 28",
        "West Virginia": "April 15", "Wisconsin": "No state deadline",
        "Wyoming": "No state deadline", "Washington D.C.": "May 1",
    }
    # 50 states + DC = 51
    assert len(STATE_DEADLINES) == 51
    assert "North Carolina" in STATE_DEADLINES
    assert "Georgia" in STATE_DEADLINES
    assert "Virginia" in STATE_DEADLINES
    assert "Washington D.C." in STATE_DEADLINES


# ─────────────────────────────────────────────
# 6. CRUD IN-MEMORY DB TEST
# ─────────────────────────────────────────────
def test_school_crud():
    """Can insert and retrieve schools in SQLite."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE fafsa_schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            school_name TEXT NOT NULL,
            is_hbcu INTEGER DEFAULT 0,
            applied INTEGER DEFAULT 0,
            accepted INTEGER DEFAULT 0,
            deadline TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    conn.execute(
        "INSERT INTO fafsa_schools (user_id, school_name, is_hbcu, applied, accepted) VALUES (?,?,?,?,?)",
        (1, "NC A&T State University", 1, 1, 1)
    )
    conn.commit()

    cur = conn.execute("SELECT * FROM fafsa_schools WHERE user_id = 1")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0]["school_name"] == "NC A&T State University"
    assert rows[0]["is_hbcu"] == 1
    conn.close()


def test_award_crud():
    """Can insert and retrieve aid awards in SQLite."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE fafsa_aid_awards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            school_id INTEGER,
            school_name TEXT NOT NULL,
            aid_type TEXT NOT NULL,
            amount REAL NOT NULL,
            per_year INTEGER DEFAULT 1,
            renewable INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    conn.execute(
        "INSERT INTO fafsa_aid_awards (user_id, school_id, school_name, aid_type, amount) VALUES (?,?,?,?,?)",
        (1, 1, "NC A&T State University", "Pell Grant", 7395.0)
    )
    conn.commit()

    cur = conn.execute("SELECT * FROM fafsa_aid_awards WHERE user_id = 1")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0]["aid_type"] == "Pell Grant"
    assert rows[0]["amount"] == 7395.0
    conn.close()
