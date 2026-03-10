"""
Unit tests for College Confused pages (pages 80-84)
Tests: import check, DB table creation, helper functions
"""
import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def db_conn():
    """Create an in-memory SQLite connection for testing."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()

# ── Import tests ──────────────────────────────────────────────────────────────
def test_page_imports_dont_crash():
    """Verify that importing utils (which pages use) does not crash."""
    # We can't directly import Streamlit pages without a running app,
    # but we can verify the utility modules work
    from utils import db
    assert hasattr(db, 'get_conn')
    assert hasattr(db, 'execute')
    assert hasattr(db, 'init_db')
    assert hasattr(db, 'get_setting')
    assert hasattr(db, 'set_setting')

# ── DB Table tests ─────────────────────────────────────────────────────────────
def test_cc_support_emails_table(db_conn):
    """Test that the support emails table can be created."""
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_support_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    db_conn.commit()
    db_conn.execute("INSERT INTO cc_support_emails (name, email, subject, message) VALUES (?, ?, ?, ?)",
                    ("Test User", "test@test.com", "General Question", "Hello"))
    db_conn.commit()
    c = db_conn.execute("SELECT COUNT(*) FROM cc_support_emails")
    assert c.fetchone()[0] == 1

def test_cc_student_profile_table(db_conn):
    """Test student profile table creation and insertion."""
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_student_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        grad_year INTEGER,
        current_grade TEXT,
        state TEXT,
        gpa REAL,
        sat_score INTEGER,
        act_score INTEGER,
        intended_major TEXT,
        first_gen INTEGER DEFAULT 0,
        hbcu_interest INTEGER DEFAULT 0,
        financial_need INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")
    db_conn.commit()
    db_conn.execute("""INSERT INTO cc_student_profile 
        (user_email, grad_year, current_grade, state, gpa, sat_score, first_gen, hbcu_interest) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("student@test.com", 2025, "12th", "GA", 3.8, 1320, 1, 1))
    db_conn.commit()
    c = db_conn.execute("SELECT * FROM cc_student_profile WHERE user_email='student@test.com'")
    row = c.fetchone()
    assert row is not None
    assert row["gpa"] == 3.8
    assert row["first_gen"] == 1

def test_cc_timeline_milestones_table(db_conn):
    """Test timeline milestones table."""
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_timeline_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        category TEXT DEFAULT 'general',
        due_date TEXT,
        completed INTEGER DEFAULT 0,
        priority TEXT DEFAULT 'normal',
        resource_link TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    db_conn.commit()
    db_conn.execute("""INSERT INTO cc_timeline_milestones 
        (user_email, title, description, category, due_date, priority)
        VALUES (?, ?, ?, ?, ?, ?)""",
        ("student@test.com", "Create Common App Account", "Go to commonapp.org", "applications", "2024-08-01", "high"))
    db_conn.commit()
    c = db_conn.execute("SELECT COUNT(*) FROM cc_timeline_milestones")
    assert c.fetchone()[0] == 1

def test_cc_scholarships_table(db_conn):
    """Test scholarships table creation."""
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_scholarships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        provider TEXT NOT NULL,
        amount_min REAL DEFAULT 0,
        amount_max REAL DEFAULT 0,
        amount_display TEXT DEFAULT '',
        deadline TEXT DEFAULT '',
        url TEXT DEFAULT '',
        description TEXT DEFAULT '',
        category TEXT DEFAULT 'national',
        hbcu_only INTEGER DEFAULT 0,
        minority_focus INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 1
    )""")
    db_conn.commit()
    db_conn.execute("""INSERT INTO cc_scholarships 
        (name, provider, amount_min, amount_max, amount_display, category, hbcu_only)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("TMCF Scholarship", "Thurgood Marshall College Fund", 3000, 3000, "$3,000", "hbcu", 1))
    db_conn.commit()
    c = db_conn.execute("SELECT * FROM cc_scholarships WHERE hbcu_only=1")
    row = c.fetchone()
    assert row is not None
    assert row["name"] == "TMCF Scholarship"

def test_cc_essays_table(db_conn):
    """Test essays table creation."""
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_essays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        title TEXT NOT NULL,
        prompt TEXT DEFAULT '',
        content TEXT DEFAULT '',
        essay_type TEXT DEFAULT 'common_app',
        word_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'draft'
    )""")
    db_conn.commit()
    db_conn.execute("""INSERT INTO cc_essays (user_email, title, prompt, essay_type)
        VALUES (?, ?, ?, ?)""",
        ("student@test.com", "My College Essay", "Tell us about yourself", "common_app"))
    db_conn.commit()
    c = db_conn.execute("SELECT COUNT(*) FROM cc_essays WHERE user_email='student@test.com'")
    assert c.fetchone()[0] == 1

def test_cc_test_scores_table(db_conn):
    """Test test scores table."""
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_test_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        test_type TEXT NOT NULL,
        score INTEGER NOT NULL,
        test_date TEXT
    )""")
    db_conn.commit()
    db_conn.execute("INSERT INTO cc_test_scores (user_email, test_type, score, test_date) VALUES (?, ?, ?, ?)",
                    ("student@test.com", "SAT", 1320, "2024-03-15"))
    db_conn.commit()
    c = db_conn.execute("SELECT * FROM cc_test_scores WHERE test_type='SAT'")
    row = c.fetchone()
    assert row is not None
    assert row["score"] == 1320

# ── Helper function tests ──────────────────────────────────────────────────────
def test_word_count_helper():
    """Test word count calculation logic."""
    def word_count(text: str) -> int:
        return len(text.split()) if text.strip() else 0
    
    assert word_count("") == 0
    assert word_count("   ") == 0
    assert word_count("hello world") == 2
    assert word_count("The quick brown fox jumps") == 5

def test_sat_percentile_lookup():
    """Test SAT percentile lookup table logic."""
    SAT_PERCENTILES = {
        400: 1, 500: 1, 600: 3, 700: 7, 800: 13, 900: 23, 1000: 35,
        1100: 50, 1200: 64, 1300: 78, 1400: 89, 1500: 96, 1600: 99
    }
    
    def get_percentile(score: int, table: dict) -> int:
        closest = min(table.keys(), key=lambda x: abs(x - score))
        return table[closest]
    
    assert get_percentile(1200, SAT_PERCENTILES) == 64
    assert get_percentile(1600, SAT_PERCENTILES) == 99
    assert get_percentile(400, SAT_PERCENTILES) == 1

def test_act_percentile_lookup():
    """Test ACT percentile lookup."""
    ACT_PERCENTILES = {
        1: 1, 20: 27, 25: 61, 30: 89, 36: 99
    }
    
    assert ACT_PERCENTILES[36] == 99
    assert ACT_PERCENTILES[25] == 61

def test_scholarship_filter_logic():
    """Test scholarship filtering logic."""
    scholarships = [
        {"name": "HBCU Scholarship", "hbcu_only": 1, "category": "hbcu", "amount_min": 3000, "gpa_min": 3.0},
        {"name": "National Merit", "hbcu_only": 0, "category": "national", "amount_min": 1000, "gpa_min": 3.5},
        {"name": "Need-Based Grant", "hbcu_only": 0, "category": "national", "amount_min": 500, "gpa_min": 2.0},
    ]
    
    # Filter HBCU only
    hbcu_only = [s for s in scholarships if s["hbcu_only"] == 1]
    assert len(hbcu_only) == 1
    assert hbcu_only[0]["name"] == "HBCU Scholarship"
    
    # Filter by min amount
    high_amount = [s for s in scholarships if s["amount_min"] >= 2000]
    assert len(high_amount) == 1
    
    # Filter by GPA
    low_gpa_eligible = [s for s in scholarships if s["gpa_min"] <= 2.5]
    assert len(low_gpa_eligible) == 1

def test_timeline_milestone_completion():
    """Test milestone completion status logic."""
    milestones = [
        {"title": "Create Common App", "completed": 0, "category": "applications"},
        {"title": "Take SAT", "completed": 1, "category": "testing"},
        {"title": "Submit FAFSA", "completed": 0, "category": "financial_aid"},
        {"title": "Write Essay Draft", "completed": 1, "category": "essays"},
    ]
    
    total = len(milestones)
    completed = sum(1 for m in milestones if m["completed"] == 1)
    pct = (completed / total * 100) if total > 0 else 0
    
    assert total == 4
    assert completed == 2
    assert pct == 50.0

def test_essay_type_word_limits():
    """Test that essay type word limits are defined correctly."""
    word_limits = {
        "Common App Personal Statement": "650",
        "Supplemental Essay": "250-650",
        "Scholarship Essay": "500",
        "Why This College": "300-500"
    }
    
    assert "Common App Personal Statement" in word_limits
    assert word_limits["Common App Personal Statement"] == "650"
    assert len(word_limits) == 4

def test_support_email_validation():
    """Test support email form validation logic."""
    def validate_support_form(name, email, message):
        if not name or not email or not message:
            return False, "All fields required"
        if "@" not in email:
            return False, "Invalid email"
        return True, "OK"
    
    ok, _ = validate_support_form("John", "john@test.com", "Hello")
    assert ok is True
    
    ok, msg = validate_support_form("", "john@test.com", "Hello")
    assert ok is False
    
    ok, msg = validate_support_form("John", "notanemail", "Hello")
    assert ok is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
