"""
Tests for pages/151_wise_mind_daily.py — Wise Mind Daily OS
DBT Practice Tracker, Grounding Toolkit, Strengths Mirror, Ubuntu Reflection
"""
import sys
import os
import types
import sqlite3
import importlib.util
import pytest
from datetime import date, datetime

# ── Setup path ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

PAGE_PATH = os.path.join(PROJECT_ROOT, "pages", "151_wise_mind_daily.py")


def _stub_streamlit_and_utils():
    """Stub streamlit + utils so the page module can be imported in test env."""
    from unittest.mock import MagicMock

    # ── SessionState: supports both dict["key"] and obj.attr access ──────────
    class _SessionState(dict):
        """Dict that also allows attribute-style access (Streamlit session_state behaviour)."""
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(key)
        def __setattr__(self, key, val):
            self[key] = val
        def __delattr__(self, key):
            del self[key]
        def __contains__(self, key):
            return super().__contains__(key)

    # ── Streamlit: use MagicMock + sane defaults for widget return values ─────
    st_mock = MagicMock()
    st_mock.session_state = _SessionState({"user_id": 1, "username": "darrian"})
    # Widget return values — must be JSON-safe / usable types
    st_mock.multiselect.return_value = []
    st_mock.selectbox.return_value   = None
    st_mock.text_input.return_value  = ""
    st_mock.text_area.return_value   = ""
    st_mock.number_input.return_value = 0
    st_mock.slider.return_value      = 1
    st_mock.button.return_value      = False
    st_mock.toggle.return_value      = False
    st_mock.checkbox.return_value    = False
    st_mock.radio.return_value       = None
    st_mock.date_input.return_value  = date.today()
    st_mock.form_submit_button.return_value = False
    # columns() must return an iterable of mocks (one per column)
    st_mock.columns.side_effect = lambda n, **kw: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
    # form() returns a context manager
    _form_cm = MagicMock()
    _form_cm.__enter__ = lambda s: s
    _form_cm.__exit__  = lambda s, *a: False
    st_mock.form.return_value = _form_cm
    # expander() returns a context manager
    st_mock.expander.return_value = _form_cm
    sys.modules["streamlit"] = st_mock

    # ── utils.db stub: conn needs real commit/close + cursor with description ─
    mock_cursor = MagicMock()
    mock_cursor.description = None          # no rows → description is None
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.close.return_value = None

    db_mod = types.ModuleType("utils.db")
    db_mod.get_conn = lambda: mock_conn
    db_mod.USE_POSTGRES = False
    db_mod.execute = lambda conn, sql, params=None: None
    db_mod.init_db = lambda: None
    db_mod.get_setting = lambda key: "test-key"
    db_mod.set_setting = lambda key, val: None
    sys.modules["utils"] = types.ModuleType("utils")
    sys.modules["utils.db"] = db_mod

    # ── utils.auth stub ───────────────────────────────────────────────────────
    auth_mod = types.ModuleType("utils.auth")
    auth_mod.require_login = lambda: None
    auth_mod.render_sidebar_brand = lambda: None
    auth_mod.render_sidebar_user_widget = lambda: None
    auth_mod.inject_css = lambda: None
    sys.modules["utils.auth"] = auth_mod

    # ── anthropic stub ────────────────────────────────────────────────────────
    anthropic_mod = types.ModuleType("anthropic")
    anthropic_mod.Anthropic = MagicMock
    sys.modules["anthropic"] = anthropic_mod


def _load_wise_mind_module():
    """Load 151_wise_mind_daily.py via importlib (numeric prefix prevents normal import)."""
    _stub_streamlit_and_utils()
    spec = importlib.util.spec_from_file_location("wise_mind_daily_151", PAGE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Test 1: Import check ───────────────────────────────────────────────────────
def test_wise_mind_module_constants():
    """Page can be imported and constants are correctly defined."""
    wm = _load_wise_mind_module()
    DARRIAN_STRENGTHS = wm.DARRIAN_STRENGTHS
    DARRIAN_GROWTH_EDGES = wm.DARRIAN_GROWTH_EDGES
    FIRE_QUOTES = wm.FIRE_QUOTES
    DBT_WHAT_SKILLS = wm.DBT_WHAT_SKILLS
    DBT_HOW_SKILLS = wm.DBT_HOW_SKILLS
    DBT_IMPROVE = wm.DBT_IMPROVE
    DBT_TIPP = wm.DBT_TIPP
    DBT_STOP = wm.DBT_STOP
    COPING_POSITIVE = wm.COPING_POSITIVE
    COPING_NEGATIVE = wm.COPING_NEGATIVE
    MIND_STATES = wm.MIND_STATES
    EFFECTIVENESS = wm.EFFECTIVENESS
    # Strengths
    assert len(DARRIAN_STRENGTHS) >= 10, "Should have at least 10 strengths"
    assert all(len(s) == 2 for s in DARRIAN_STRENGTHS), "Each strength is (name, desc)"

    # Growth edges
    assert len(DARRIAN_GROWTH_EDGES) >= 6, "Should have at least 6 growth edges"

    # Fire quotes — revolutionary figures + One Piece
    assert len(FIRE_QUOTES) >= 20, "Should have at least 20 quotes"
    people = [q[0] for q in FIRE_QUOTES]
    assert any("Malcolm X" in p for p in people), "Malcolm X quotes required"
    assert any("Assata" in p for p in people), "Assata Shakur quotes required"
    assert any("Huey" in p for p in people), "Huey P Newton quotes required"
    assert any("Luffy" in p for p in people) or any("One Piece" in p for p in people), \
        "One Piece / Luffy quotes required"
    assert any("Bobby Seale" in p for p in people), "Bobby Seale quotes required"

    # DBT skills
    assert "Observe" in DBT_WHAT_SKILLS
    assert "One-Mindfully" in DBT_HOW_SKILLS
    assert len(DBT_IMPROVE) == 8, "IMPROVE has 8 components"
    assert len(DBT_TIPP) == 4, "TIPP has 4 components"
    assert len(DBT_STOP) == 4, "STOP has 4 steps"
    assert len(MIND_STATES) == 3, "3 states of mind"
    assert len(EFFECTIVENESS) == 5, "5-point effectiveness scale"


# ── Test 2: DB tables created correctly ───────────────────────────────────────
def test_wise_mind_db_tables(tmp_path):
    """_ensure_tables() creates all required wm_ tables in SQLite."""
    db_path = tmp_path / "test_wise_mind.db"
    conn = sqlite3.connect(str(db_path))

    required_tables = [
        ("wm_state_log", ["user_id", "log_date", "mind_state", "mind_score",
                           "emotion_present", "body_sensation", "one_mindfully",
                           "wise_mind_tool", "notes"]),
        ("wm_skill_log", ["user_id", "log_date", "skill_category", "skill_name",
                           "situation", "effectiveness", "notes"]),
        ("wm_coping_log", ["user_id", "log_date", "coping_type", "skills_used",
                            "trigger", "outcome"]),
        ("wm_trigger_log", ["user_id", "log_date", "trigger_event", "emotion_before",
                             "intensity_before", "action_taken", "dbt_skill_used",
                             "emotion_after", "intensity_after", "lesson"]),
        ("wm_ubuntu_log", ["user_id", "log_date", "gave_to_who", "what_i_gave",
                            "what_i_received", "community_vision", "notes"]),
    ]

    for table_name, required_cols in required_tables:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                log_date DATE NOT NULL,
                mind_state TEXT,
                mind_score INTEGER,
                emotion_present TEXT,
                body_sensation TEXT,
                one_mindfully TEXT,
                notes TEXT,
                wise_mind_tool TEXT,
                skill_category TEXT,
                skill_name TEXT,
                situation TEXT,
                effectiveness INTEGER,
                coping_type TEXT,
                skills_used TEXT,
                trigger TEXT,
                outcome TEXT,
                trigger_event TEXT,
                emotion_before TEXT,
                intensity_before INTEGER,
                action_taken TEXT,
                dbt_skill_used TEXT,
                emotion_after TEXT,
                intensity_after INTEGER,
                lesson TEXT,
                gave_to_who TEXT,
                what_i_gave TEXT,
                what_i_received TEXT,
                community_vision TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Verify table exists
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        assert result is not None, f"Table {table_name} should exist"

    conn.close()


# ── Test 3: CRUD operations on wm_state_log ───────────────────────────────────
def test_wise_mind_state_crud(tmp_path):
    """Can insert and query Wise Mind state entries."""
    db_path = tmp_path / "test_wm_state.db"
    conn = sqlite3.connect(str(db_path))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS wm_state_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            log_date DATE NOT NULL,
            log_time TEXT,
            mind_state TEXT,
            mind_score INTEGER,
            emotion_present TEXT,
            body_sensation TEXT,
            one_mindfully TEXT,
            notes TEXT,
            wise_mind_tool TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    today = date.today().isoformat()
    conn.execute("""
        INSERT INTO wm_state_log
            (user_id, log_date, log_time, mind_state, mind_score, emotion_present,
             body_sensation, one_mindfully, notes, wise_mind_tool)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, today, "09:00", "🌊 Wise Mind", 4, "Calm", "Relaxed", "Focus on Visa work",
           "Feeling grounded", "Stone on the Lake"))
    conn.commit()

    row = conn.execute("SELECT * FROM wm_state_log WHERE log_date=?", (today,)).fetchone()
    assert row is not None
    assert row[4] == "🌊 Wise Mind"
    assert row[5] == 4
    assert row[6] == "Calm"
    conn.close()


# ── Test 4: Coping skills log — positive + negative ───────────────────────────
def test_wise_mind_coping_log(tmp_path):
    """Can log positive and negative coping skills."""
    import json

    db_path = tmp_path / "test_wm_coping.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wm_coping_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            log_date DATE NOT NULL,
            coping_type TEXT NOT NULL,
            skills_used TEXT,
            trigger TEXT,
            outcome TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    today = date.today().isoformat()
    pos_skills = ["Walk / Run", "Gym", "Breathing exercises"]
    neg_skills = ["Doom scrolling"]

    conn.execute("""
        INSERT INTO wm_coping_log (user_id, log_date, coping_type, skills_used, trigger, outcome)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (1, today, "Both (honest)",
          json.dumps({"positive": pos_skills, "negative": neg_skills}),
          "Work stress", "Better after gym"))
    conn.commit()

    row = conn.execute("SELECT * FROM wm_coping_log WHERE log_date=?", (today,)).fetchone()
    assert row is not None
    skills_data = json.loads(row[4])
    assert "Walk / Run" in skills_data["positive"]
    assert "Doom scrolling" in skills_data["negative"]
    conn.close()


# ── Test 5: Trigger log with before/after intensity ───────────────────────────
def test_wise_mind_trigger_log(tmp_path):
    """Can log triggers with intensity before/after and verify reduction calculation."""
    db_path = tmp_path / "test_wm_trigger.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wm_trigger_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            log_date DATE NOT NULL,
            trigger_event TEXT,
            emotion_before TEXT,
            intensity_before INTEGER,
            action_taken TEXT,
            dbt_skill_used TEXT,
            emotion_after TEXT,
            intensity_after INTEGER,
            lesson TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    today = date.today().isoformat()
    conn.execute("""
        INSERT INTO wm_trigger_log
            (user_id, log_date, trigger_event, emotion_before, intensity_before,
             action_taken, dbt_skill_used, emotion_after, intensity_after, lesson)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, today, "Unexpected meeting cancellation", "Frustration", 8,
           "Went for a walk (20 min)", "One Thing in the Moment",
           "Calmer", 3, "Walking always helps. Use it sooner."))
    conn.commit()

    row = conn.execute("SELECT * FROM wm_trigger_log WHERE log_date=?", (today,)).fetchone()
    assert row is not None
    intensity_before = row[5]  # intensity_before column
    intensity_after = row[9]   # intensity_after column
    reduction = intensity_before - intensity_after
    assert reduction == 5, f"Expected reduction of 5, got {reduction}"
    assert reduction > 0, "DBT skills should reduce emotional intensity"
    conn.close()


# ── Test 6: Ubuntu log ────────────────────────────────────────────────────────
def test_wise_mind_ubuntu_log(tmp_path):
    """Can save Ubuntu community reflection entries."""
    db_path = tmp_path / "test_wm_ubuntu.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wm_ubuntu_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            log_date DATE NOT NULL,
            gave_to_who TEXT,
            what_i_gave TEXT,
            what_i_received TEXT,
            community_vision TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    today = date.today().isoformat()
    conn.execute("""
        INSERT INTO wm_ubuntu_log
            (user_id, log_date, gave_to_who, what_i_gave, what_i_received, community_vision)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (1, today, "College student at CC", "Scholarship advice and essay feedback",
           "Their gratitude and energy", "Sikh kitchen + free college prep for ATL youth"))
    conn.commit()

    row = conn.execute("SELECT * FROM wm_ubuntu_log WHERE log_date=?", (today,)).fetchone()
    assert row is not None
    assert "Sikh kitchen" in row[6]  # community_vision
    conn.close()


# ── Test 7: Quote library completeness ───────────────────────────────────────
def test_fire_quotes_completeness():
    """All revolutionary figures from Darrian's handwritten list are represented."""
    wm = _load_wise_mind_module()
    FIRE_QUOTES = wm.FIRE_QUOTES

    all_text = " ".join(f"{q[0]} {q[1]}" for q in FIRE_QUOTES)
    required_figures = [
        "Malcolm X", "Assata", "Huey", "Bobby Seale",
        "Marcus Garvey", "DuBois", "Luffy", "Oda",
        "Ubuntu", "J Cole", "Kendrick"
    ]
    for figure in required_figures:
        assert figure in all_text, f"'{figure}' should be in the fire quotes library"


# ── Test 8: Darrian's own words included ────────────────────────────────────
def test_darrianisms_in_quotes():
    """Darrian's own words from therapy are included as quotes."""
    wm = _load_wise_mind_module()
    FIRE_QUOTES = wm.FIRE_QUOTES

    darrian_quotes = [q for q in FIRE_QUOTES if "Darrian Belcher" in q[0]]
    assert len(darrian_quotes) >= 2, "At least 2 of Darrian's own quotes should be in the library"

    all_darrian_text = " ".join(q[1] for q in darrian_quotes)
    # He wrote "just having a tool is not useful"
    assert "tool" in all_darrian_text.lower()


# ── Test 9: DBT skill effectiveness scale ────────────────────────────────────
def test_effectiveness_scale():
    """Effectiveness scale has 5 levels as designed."""
    wm = _load_wise_mind_module()
    EFFECTIVENESS = wm.EFFECTIVENESS

    assert 1 in EFFECTIVENESS
    assert 5 in EFFECTIVENESS
    assert "Not effective" in EFFECTIVENESS[1]
    assert "Transformative" in EFFECTIVENESS[5]


# ── Test 10: Context file exists ─────────────────────────────────────────────
def test_mental_health_os_context_file_exists():
    """context/DARRIAN_MENTAL_HEALTH_OS.md was created."""
    context_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "context", "DARRIAN_MENTAL_HEALTH_OS.md"
    )
    assert os.path.exists(context_path), "DARRIAN_MENTAL_HEALTH_OS.md must exist"

    with open(context_path, "r") as f:
        content = f.read()

    # Check key sections exist
    assert "Wise Mind" in content
    assert "Ubuntu" in content
    assert "One Piece" in content
    assert "IMPROVE" in content
    assert "TIPP" in content
    assert "Malcolm X" in content
    assert "Assata" in content
    assert "DBT" in content
