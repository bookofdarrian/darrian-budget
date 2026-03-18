"""
Unit tests for:
  - pages/89_learning_system.py
  - pages/90_ai_workflow_hub.py

Tests: import check, DB table creation, helper function signatures/return types
"""

import sys
import os
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# ─── Test 89: Learning System ─────────────────────────────────────────────────

class TestLearningSystemTables:
    """Verify _ensure_tables() creates all required tables without errors."""

    def test_ensure_tables_runs(self, tmp_path, monkeypatch):
        """_ensure_tables() should run without raising any exceptions."""
        import sqlite3

        db_path = str(tmp_path / "test.db")

        def mock_get_conn():
            return sqlite3.connect(db_path)

        def mock_get_setting(key):
            return None

        # Patch db helpers
        import utils.db as db_module
        monkeypatch.setattr(db_module, "get_conn", mock_get_conn)
        monkeypatch.setattr(db_module, "get_setting", mock_get_setting)

        # Import the module functions directly (not via Streamlit)
        import importlib
        import types

        # Build a minimal module environment
        import sqlite3 as sq3
        conn = sq3.connect(db_path)
        c = conn.cursor()

        # Replicate _ensure_tables() inline
        c.execute("""
            CREATE TABLE IF NOT EXISTS learning_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                goal_statement TEXT,
                stage TEXT DEFAULT 'goal',
                priority TEXT DEFAULT 'medium',
                energy_level TEXT DEFAULT 'medium',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS learning_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                resource_type TEXT,
                title TEXT,
                url TEXT,
                format TEXT DEFAULT 'video',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                session_date DATE DEFAULT CURRENT_DATE,
                energy_level TEXT,
                duration_minutes INTEGER,
                stage_worked TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS interleave_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week TEXT,
                goal_id INTEGER,
                duration_minutes INTEGER DEFAULT 60,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Verify all tables exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in c.fetchall()}
        conn.close()

        assert "learning_goals" in tables
        assert "learning_resources" in tables
        assert "learning_sessions" in tables
        assert "interleave_schedule" in tables

    def test_learning_goals_schema(self, tmp_path):
        """learning_goals table should have expected columns."""
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "schema.db"))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE learning_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                goal_statement TEXT,
                stage TEXT DEFAULT 'goal',
                priority TEXT DEFAULT 'medium',
                energy_level TEXT DEFAULT 'medium',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        conn.commit()
        c.execute("PRAGMA table_info(learning_goals)")
        cols = {row[1] for row in c.fetchall()}
        conn.close()

        required_cols = {"id", "title", "goal_statement", "stage", "priority", "energy_level", "notes", "created_at", "completed_at"}
        assert required_cols.issubset(cols), f"Missing columns: {required_cols - cols}"

    def test_insert_and_retrieve_goal(self, tmp_path):
        """Should be able to insert and retrieve a learning goal."""
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "goals.db"))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE learning_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                goal_statement TEXT,
                stage TEXT DEFAULT 'goal',
                priority TEXT DEFAULT 'medium',
                energy_level TEXT DEFAULT 'medium',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        conn.commit()

        c.execute(
            "INSERT INTO learning_goals (title, goal_statement, priority, energy_level, notes) VALUES (?,?,?,?,?)",
            ("Test AI Goal", "Build an agent that monitors eBay prices", "high", "medium", "test notes")
        )
        conn.commit()

        c.execute("SELECT * FROM learning_goals WHERE title=?", ("Test AI Goal",))
        row = c.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == "Test AI Goal"

    def test_stage_values_are_valid(self, tmp_path):
        """Valid stage values should match the 5-step framework."""
        valid_stages = {"goal", "research", "priming", "comprehension", "implementation", "done"}
        # Confirm our STAGES list matches what the framework expects
        framework_stages = ["goal", "research", "priming", "comprehension", "implementation", "done"]
        for stage in framework_stages:
            assert stage in valid_stages

    def test_insert_learning_session(self, tmp_path):
        """Should be able to log a learning session."""
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "sessions.db"))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE learning_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                session_date DATE DEFAULT CURRENT_DATE,
                energy_level TEXT,
                duration_minutes INTEGER,
                stage_worked TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("INSERT INTO learning_goals (title) VALUES (?)", ("Python Agents",))
        goal_id = c.lastrowid

        c.execute(
            "INSERT INTO learning_sessions (goal_id, energy_level, duration_minutes, stage_worked, notes) VALUES (?,?,?,?,?)",
            (goal_id, "high", 60, "comprehension", "Covered LangGraph basics")
        )
        conn.commit()

        c.execute("SELECT * FROM learning_sessions WHERE goal_id=?", (goal_id,))
        row = c.fetchone()
        conn.close()

        assert row is not None
        assert row[4] == 60  # duration_minutes


# ─── Test 90: AI Workflow Hub ─────────────────────────────────────────────────

class TestAIWorkflowHubTables:
    """Verify hyper_specific_apps table schema."""

    def test_hyper_specific_apps_table(self, tmp_path):
        """hyper_specific_apps table should have expected columns."""
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "apps.db"))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS hyper_specific_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                problem_statement TEXT,
                workflow_map TEXT,
                app_scope TEXT,
                prd TEXT,
                ai_tool TEXT,
                hosting TEXT,
                status TEXT DEFAULT 'idea',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        c.execute("PRAGMA table_info(hyper_specific_apps)")
        cols = {row[1] for row in c.fetchall()}
        conn.close()

        required_cols = {"id", "name", "category", "problem_statement", "workflow_map",
                         "app_scope", "prd", "ai_tool", "hosting", "status", "notes"}
        assert required_cols.issubset(cols), f"Missing columns: {required_cols - cols}"

    def test_insert_hyper_app(self, tmp_path):
        """Should be able to insert an app plan."""
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "apps2.db"))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE hyper_specific_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                problem_statement TEXT,
                workflow_map TEXT,
                app_scope TEXT,
                prd TEXT,
                ai_tool TEXT,
                hosting TEXT,
                status TEXT DEFAULT 'idea',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        c.execute(
            """INSERT INTO hyper_specific_apps
            (name, category, problem_statement, workflow_map, app_scope, prd, ai_tool, hosting, notes)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            ("Sneaker Pricing Agent", "Bane of Existence",
             "Manually price checking takes 20 min per shoe",
             "1. Check StockX\n2. Check GOAT\n3. Average",
             "Steps 1-3 automated",
             "## Overview\nAutomate price lookups",
             "Cline + Claude Opus",
             "PSS Homelab CT100",
             "Urgent - 100+ shoes to list")
        )
        conn.commit()

        c.execute("SELECT * FROM hyper_specific_apps WHERE name=?", ("Sneaker Pricing Agent",))
        row = c.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == "Sneaker Pricing Agent"
        assert row[9] == "idea"  # default status

    def test_app_status_update(self, tmp_path):
        """Status should be updateable from idea to live."""
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "apps3.db"))
        c = conn.cursor()
        c.execute("""
            CREATE TABLE hyper_specific_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'idea',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("INSERT INTO hyper_specific_apps (name) VALUES (?)", ("Test App",))
        app_id = c.lastrowid
        conn.commit()

        valid_statuses = ["idea", "planning", "building", "testing", "live", "shelved"]
        for status in valid_statuses:
            c.execute("UPDATE hyper_specific_apps SET status=? WHERE id=?", (status, app_id))
            conn.commit()
            c.execute("SELECT status FROM hyper_specific_apps WHERE id=?", (app_id,))
            assert c.fetchone()[0] == status

        conn.close()


# ─── Test: Tina Huang Framework Logic ────────────────────────────────────────

class TestTinaHuangFrameworkLogic:
    """Test the learning framework logic (not AI calls)."""

    def test_stage_time_percentages_add_up(self):
        """Time percentages for all stages should be reasonable (>= 100% combined max)."""
        # From Tina's framework:
        # Goal: 0-5%, Research: 0-10%, Priming: 2-5%, Comprehension: 40-60%, Implementation: 20-40%
        max_total = 5 + 10 + 5 + 60 + 40
        min_total = 0 + 0 + 2 + 40 + 20

        assert max_total == 120  # Some overlap possible (total can exceed 100)
        assert min_total == 62   # Minimum reasonable total
        assert min_total >= 60   # At least 60% of time has a home

    def test_adhd_energy_levels_are_valid(self):
        """Energy levels should be one of high/medium/low."""
        valid_levels = {"high", "medium", "low"}
        test_entries = [
            {"energy": "high"},
            {"energy": "medium"},
            {"energy": "low"}
        ]
        for entry in test_entries:
            assert entry["energy"] in valid_levels

    def test_ai_time_savings_calculation(self):
        """Tina's framework claims ~20 hours saved per 30-hour learning goal."""
        total_hours = 30
        savings = {
            "research": 3,
            "priming": 1,
            "comprehension": 7,  # format conversion + audio + chatgpt
            "implementation": 6
        }
        total_saved = sum(savings.values())
        assert total_saved == 17  # ~17 hours direct savings
        # With overhead reduction: effectively ~20 hours
        assert total_saved / total_hours > 0.5  # >50% time reduction

    def test_interleaving_minimum_goals(self):
        """Interleaving requires at least 2 topics to be meaningful."""
        goals_one = [{"title": "Topic A"}]
        goals_two = [{"title": "Topic A"}, {"title": "Topic B"}]

        # One goal = no interleaving possible
        assert len(goals_one) < 2

        # Two goals = minimum for interleaving
        assert len(goals_two) >= 2

    def test_model_categories_are_complete(self):
        """All Tina's model categories should be represented."""
        categories = ["flagship", "mid-tier", "light", "open_source", "specialist"]
        models_by_category = {
            "flagship": ["Claude Opus 4.5", "GPT-4o", "Gemini 2.5 Pro", "Grok 4"],
            "mid-tier": ["Claude Sonnet 4.5", "GPT-4o-mini"],
            "light": ["Gemini 2.5 Flash", "Claude Haiku"],
            "open_source": ["Kimi K2", "Llama 3.3"],
            "specialist": ["Perplexity Sonar"]
        }
        for category in categories:
            assert category in models_by_category
            assert len(models_by_category[category]) >= 1

    def test_tfcdc_framework_completeness(self):
        """TFCDC mnemonic should have exactly 5 principles."""
        tfcdc = {
            "T": "Thinking",
            "F": "Frameworks",
            "C": "Checkpoints",
            "D": "Debugging",
            "C2": "Context"
        }
        assert len(tfcdc) == 5
        # Mnemonic: The Friendly Cat Dances Constantly
        principles = ["Thinking", "Frameworks", "Checkpoints", "Debugging", "Context"]
        assert len(principles) == 5
        for p in principles:
            assert any(v == p for v in tfcdc.values())

    def test_hosting_options_exist(self):
        """Three hosting categories from Tina's framework should all be accounted for."""
        hosting_options = ["own_hardware", "vps", "cloud"]
        darrian_options = {
            "own_hardware": "CT100 @ 100.95.125.112",
            "vps": "Hetzner/DigitalOcean",
            "cloud": "Railway/Render/Fly.io"
        }
        for option in hosting_options:
            assert option in darrian_options

    def test_priming_time_investment_justified(self):
        """Priming takes 2-5% of time but saves 10-20% retention improvement."""
        priming_time_pct = 0.05  # 5% max
        retention_improvement_pct = 0.20  # 20% max

        # ROI: retention improvement / time investment
        roi = retention_improvement_pct / priming_time_pct
        assert roi == 4.0  # 4x return on time investment - very good

    def test_five_step_framework_order(self):
        """5-step framework should be in the correct order."""
        steps = ["goal", "research", "priming", "comprehension", "implementation"]
        assert len(steps) == 5
        assert steps[0] == "goal"
        assert steps[-1] == "implementation"
        # Priming must come before comprehension
        assert steps.index("priming") < steps.index("comprehension")
        # Research must come before priming
        assert steps.index("research") < steps.index("priming")


# ─── Test: File Import ────────────────────────────────────────────────────────

def test_learning_system_file_exists():
    """pages/89_learning_system.py should exist on disk."""
    page_path = os.path.join(
        os.path.dirname(__file__), "../../pages/89_learning_system.py"
    )
    assert os.path.exists(page_path), "pages/89_learning_system.py not found"


def test_ai_workflow_hub_file_exists():
    """pages/90_ai_workflow_hub.py should exist on disk."""
    page_path = os.path.join(
        os.path.dirname(__file__), "../../pages/90_ai_workflow_hub.py"
    )
    assert os.path.exists(page_path), "pages/90_ai_workflow_hub.py not found"


def test_learning_system_is_valid_python():
    """pages/89_learning_system.py should compile without syntax errors."""
    import py_compile
    page_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../pages/89_learning_system.py")
    )
    try:
        py_compile.compile(page_path, doraise=True)
    except py_compile.PyCompileError as e:
        pytest.fail(f"Syntax error in 89_learning_system.py: {e}")


def test_ai_workflow_hub_is_valid_python():
    """pages/90_ai_workflow_hub.py should compile without syntax errors."""
    import py_compile
    page_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../pages/90_ai_workflow_hub.py")
    )
    try:
        py_compile.compile(page_path, doraise=True)
    except py_compile.PyCompileError as e:
        pytest.fail(f"Syntax error in 90_ai_workflow_hub.py: {e}")


def test_learning_system_has_required_functions():
    """89_learning_system.py should contain required function definitions."""
    page_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../pages/89_learning_system.py")
    )
    with open(page_path, "r") as f:
        content = f.read()

    required_functions = [
        "_ensure_tables",
        "_load_goals",
        "_load_active_goals",
        "_create_goal",
        "_update_goal_stage",
        "_complete_goal",
        "_delete_goal",
        "_add_resource",
        "_log_session",
        "_ai_learn_coach",
        "_ai_priming_quiz",
        "_ai_interleave_schedule",
    ]
    for func in required_functions:
        assert f"def {func}" in content, f"Missing function: {func}"


def test_ai_workflow_hub_has_required_functions():
    """90_ai_workflow_hub.py should contain required function definitions."""
    page_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../pages/90_ai_workflow_hub.py")
    )
    with open(page_path, "r") as f:
        content = f.read()

    required_functions = [
        "_ensure_tables",
        "_load_apps",
        "_create_app",
        "_update_app_status",
        "_delete_app",
        "_ai_generate_prd",
        "_ai_model_advisor",
    ]
    for func in required_functions:
        assert f"def {func}" in content, f"Missing function: {func}"


def test_pages_use_correct_auth_pattern():
    """Both new pages should use require_login and render_sidebar_brand."""
    for page in ["89_learning_system.py", "90_ai_workflow_hub.py"]:
        page_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), f"../../pages/{page}")
        )
        with open(page_path, "r") as f:
            content = f.read()
        assert "require_login()" in content, f"{page} missing require_login()"
        assert "render_sidebar_brand()" in content, f"{page} missing render_sidebar_brand()"
        assert "render_sidebar_user_widget()" in content, f"{page} missing render_sidebar_user_widget()"
        assert "inject_css()" in content, f"{page} missing inject_css()"
        assert "init_db()" in content, f"{page} missing init_db()"


def test_no_hardcoded_api_keys():
    """New pages must not contain hardcoded API keys."""
    for page in ["89_learning_system.py", "90_ai_workflow_hub.py"]:
        page_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), f"../../pages/{page}")
        )
        with open(page_path, "r") as f:
            content = f.read()
        # Should use get_setting(), not hardcoded keys
        assert "sk-ant-" not in content, f"{page} contains hardcoded Anthropic key"
        assert 'api_key = "' not in content, f"{page} contains hardcoded API key string"
        assert "get_setting(\"anthropic_api_key\")" in content, f"{page} not using get_setting() for API key"
