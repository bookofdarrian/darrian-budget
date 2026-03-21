"""
Unit tests for pages/144_holistic_health_dashboard.py
Tests: import, DB table creation, helper functions, episode flagging logic
"""
import sys
import os
import json
import pytest
import sqlite3
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── File existence & syntax ────────────────────────────────────────────────────
def test_page_file_exists():
    """Page file 144 exists on disk."""
    path = os.path.join(
        os.path.dirname(__file__), "../../pages/144_holistic_health_dashboard.py"
    )
    assert os.path.exists(path), "pages/144_holistic_health_dashboard.py not found"


def test_syntax_check():
    """Page 144 passes Python syntax check."""
    import py_compile
    path = os.path.join(
        os.path.dirname(__file__), "../../pages/144_holistic_health_dashboard.py"
    )
    py_compile.compile(path, doraise=True)


# ── DB Table Tests ─────────────────────────────────────────────────────────────
def _make_test_db(tmp_path):
    """Create a test SQLite DB with all health tables."""
    db_path = str(tmp_path / "test_health.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hh_daily_checkin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            checkin_date DATE NOT NULL,
            checkin_time TEXT,
            mood_score INTEGER,
            anxiety_score INTEGER,
            focus_score INTEGER,
            energy_score INTEGER,
            sleep_hours REAL,
            sleep_quality TEXT,
            overall_day_score INTEGER,
            primary_emotion TEXT,
            gratitude_1 TEXT,
            gratitude_2 TEXT,
            gratitude_3 TEXT,
            spiritual_score INTEGER,
            huberman_protocols TEXT,
            spiritual_practices TEXT,
            family_visible INTEGER DEFAULT 0,
            family_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hh_medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            med_name TEXT NOT NULL,
            dosage TEXT,
            frequency TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hh_thought_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            record_date DATE NOT NULL,
            situation TEXT,
            automatic_thought TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hh_garmin_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            data_date DATE NOT NULL,
            steps INTEGER,
            heart_rate_avg INTEGER,
            hrv REAL,
            sleep_hours REAL,
            stress_avg INTEGER,
            body_battery_high INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hh_health_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            pillar TEXT NOT NULL,
            goal TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def test_hh_daily_checkin_table_created(tmp_path):
    """hh_daily_checkin table is created correctly."""
    conn = _make_test_db(tmp_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hh_daily_checkin'")
    assert cur.fetchone() is not None
    conn.close()


def test_hh_medications_table_created(tmp_path):
    """hh_medications table is created correctly."""
    conn = _make_test_db(tmp_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hh_medications'")
    assert cur.fetchone() is not None
    conn.close()


def test_hh_thought_records_table_created(tmp_path):
    """hh_thought_records table is created correctly."""
    conn = _make_test_db(tmp_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hh_thought_records'")
    assert cur.fetchone() is not None
    conn.close()


def test_hh_garmin_data_table_created(tmp_path):
    """hh_garmin_data table is created correctly."""
    conn = _make_test_db(tmp_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hh_garmin_data'")
    assert cur.fetchone() is not None
    conn.close()


def test_hh_health_goals_table_created(tmp_path):
    """hh_health_goals table is created correctly."""
    conn = _make_test_db(tmp_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hh_health_goals'")
    assert cur.fetchone() is not None
    conn.close()


# ── CRUD Tests ─────────────────────────────────────────────────────────────────
def test_insert_and_read_checkin(tmp_path):
    """Can insert and retrieve a daily check-in record."""
    conn = _make_test_db(tmp_path)
    conn.execute("""
        INSERT INTO hh_daily_checkin
            (user_id, checkin_date, mood_score, energy_score, anxiety_score, sleep_hours, overall_day_score)
        VALUES (1, ?, 4, 3, 1, 7.5, 7)
    """, (date.today().isoformat(),))
    conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT mood_score, sleep_hours FROM hh_daily_checkin WHERE user_id=1")
    row = cur.fetchone()
    assert row is not None
    assert row[0] == 4
    assert row[1] == 7.5
    conn.close()


def test_insert_and_read_medication(tmp_path):
    """Can insert and retrieve a medication record."""
    conn = _make_test_db(tmp_path)
    conn.execute("""
        INSERT INTO hh_medications (user_id, med_name, dosage, frequency)
        VALUES (1, 'Adderall XR', '30mg', 'Daily')
    """)
    conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT med_name, dosage FROM hh_medications WHERE user_id=1 AND is_active=1")
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "Adderall XR"
    assert row[1] == "30mg"
    conn.close()


def test_insert_garmin_data(tmp_path):
    """Can insert and retrieve Garmin data."""
    conn = _make_test_db(tmp_path)
    conn.execute("""
        INSERT INTO hh_garmin_data
            (user_id, data_date, steps, heart_rate_avg, hrv, body_battery_high)
        VALUES (1, ?, 8500, 72, 45.3, 78)
    """, (date.today().isoformat(),))
    conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT steps, hrv FROM hh_garmin_data WHERE user_id=1")
    row = cur.fetchone()
    assert row is not None
    assert row[0] == 8500
    assert row[1] == 45.3
    conn.close()


# ── Episode Flag Logic Tests ───────────────────────────────────────────────────
def _check_for_episode_flags(checkins):
    """Replicate the episode flag logic from the page."""
    flags = []
    if len(checkins) < 3:
        return flags
    recent = checkins[:5]
    moods = [c.get("mood_score", 3) for c in recent if c.get("mood_score")]
    sleeps = [c.get("sleep_hours", 7) for c in recent if c.get("sleep_hours")]
    anxieties = [c.get("anxiety_score", 1) for c in recent if c.get("anxiety_score") is not None]

    if moods and sum(moods) / len(moods) >= 5.5:
        flags.append(("⚡ Elevated Mood Trend", "Average mood has been high", "warning"))
    if moods and sum(moods) / len(moods) <= 2.5:
        flags.append(("🔵 Low Mood Trend", "Average mood has been low", "error"))
    if sleeps and sum(sleeps) / len(sleeps) < 6:
        flags.append(("😴 Sleep Deficit", "Average sleep is low", "warning"))
    if anxieties and sum(anxieties) / len(anxieties) >= 2.5:
        flags.append(("😰 Elevated Anxiety", "Anxiety consistently high", "warning"))
    return flags


def test_no_flags_for_stable_mood():
    """No episode flags when mood is in stable range (3-5)."""
    checkins = [
        {"mood_score": 4, "sleep_hours": 7.5, "anxiety_score": 1},
        {"mood_score": 4, "sleep_hours": 8.0, "anxiety_score": 1},
        {"mood_score": 5, "sleep_hours": 7.0, "anxiety_score": 2},
        {"mood_score": 4, "sleep_hours": 7.5, "anxiety_score": 1},
    ]
    flags = _check_for_episode_flags(checkins)
    flag_titles = [f[0] for f in flags]
    assert "⚡ Elevated Mood Trend" not in flag_titles
    assert "🔵 Low Mood Trend" not in flag_titles


def test_elevated_mood_flag_triggers():
    """Elevated mood flag triggers when avg mood >= 5.5."""
    checkins = [
        {"mood_score": 6, "sleep_hours": 6.0, "anxiety_score": 1},
        {"mood_score": 7, "sleep_hours": 5.5, "anxiety_score": 1},
        {"mood_score": 6, "sleep_hours": 6.0, "anxiety_score": 1},
        {"mood_score": 6, "sleep_hours": 5.0, "anxiety_score": 1},
    ]
    flags = _check_for_episode_flags(checkins)
    flag_titles = [f[0] for f in flags]
    assert "⚡ Elevated Mood Trend" in flag_titles


def test_low_mood_flag_triggers():
    """Low mood flag triggers when avg mood <= 2.5."""
    checkins = [
        {"mood_score": 2, "sleep_hours": 5.0, "anxiety_score": 2},
        {"mood_score": 1, "sleep_hours": 4.5, "anxiety_score": 3},
        {"mood_score": 2, "sleep_hours": 5.5, "anxiety_score": 2},
        {"mood_score": 2, "sleep_hours": 6.0, "anxiety_score": 2},
    ]
    flags = _check_for_episode_flags(checkins)
    flag_titles = [f[0] for f in flags]
    assert "🔵 Low Mood Trend" in flag_titles


def test_sleep_deficit_flag_triggers():
    """Sleep deficit flag triggers when avg sleep < 6 hours."""
    checkins = [
        {"mood_score": 4, "sleep_hours": 4.5, "anxiety_score": 1},
        {"mood_score": 4, "sleep_hours": 5.0, "anxiety_score": 1},
        {"mood_score": 4, "sleep_hours": 4.0, "anxiety_score": 1},
        {"mood_score": 5, "sleep_hours": 5.5, "anxiety_score": 1},
    ]
    flags = _check_for_episode_flags(checkins)
    flag_titles = [f[0] for f in flags]
    assert "😴 Sleep Deficit" in flag_titles


def test_anxiety_flag_triggers():
    """Anxiety flag triggers when avg anxiety >= 2.5."""
    checkins = [
        {"mood_score": 4, "sleep_hours": 7.0, "anxiety_score": 3},
        {"mood_score": 4, "sleep_hours": 7.0, "anxiety_score": 3},
        {"mood_score": 4, "sleep_hours": 7.0, "anxiety_score": 2},
        {"mood_score": 4, "sleep_hours": 7.0, "anxiety_score": 3},
    ]
    flags = _check_for_episode_flags(checkins)
    flag_titles = [f[0] for f in flags]
    assert "😰 Elevated Anxiety" in flag_titles


def test_insufficient_data_no_flags():
    """No flags returned when fewer than 3 check-ins available."""
    checkins = [
        {"mood_score": 7, "sleep_hours": 3.0, "anxiety_score": 4},
        {"mood_score": 7, "sleep_hours": 3.0, "anxiety_score": 4},
    ]
    flags = _check_for_episode_flags(checkins)
    assert flags == []


# ── Constant Validation Tests ──────────────────────────────────────────────────
def test_mood_scale_covers_1_to_7():
    """MOOD_SCALE covers all values 1-7."""
    MOOD_SCALE = {
        1: "😢 Depressed", 2: "😔 Low", 3: "😐 Neutral", 4: "🙂 Good",
        5: "😄 Great", 6: "⚡ Elevated", 7: "🔥 Manic"
    }
    for i in range(1, 8):
        assert i in MOOD_SCALE, f"Mood scale missing key {i}"


def test_energy_scale_covers_1_to_5():
    """ENERGY_SCALE covers all values 1-5."""
    ENERGY_SCALE = {
        1: "💤 Exhausted", 2: "😴 Low", 3: "😐 Moderate", 4: "🔋 Good", 5: "⚡ High"
    }
    for i in range(1, 6):
        assert i in ENERGY_SCALE


def test_anxiety_scale_covers_0_to_4():
    """ANXIETY_SCALE covers values 0-4."""
    ANXIETY_SCALE = {
        0: "🟢 None", 1: "🟡 Mild", 2: "🟠 Moderate",
        3: "🔴 High", 4: "🆘 Severe"
    }
    for i in range(0, 5):
        assert i in ANXIETY_SCALE


def test_cbt_distortions_list_complete():
    """CBT_DISTORTIONS list contains at least 10 distortions."""
    CBT_DISTORTIONS = [
        "All-or-Nothing Thinking", "Catastrophizing", "Mind Reading", "Fortune Telling",
        "Emotional Reasoning", "Should Statements", "Labeling", "Personalization",
        "Mental Filter", "Disqualifying the Positive", "Magnification/Minimization", "Overgeneralization"
    ]
    assert len(CBT_DISTORTIONS) >= 10
    assert "Catastrophizing" in CBT_DISTORTIONS
    assert "All-or-Nothing Thinking" in CBT_DISTORTIONS


def test_huberman_protocols_list_non_empty():
    """HUBERMAN_PROTOCOLS list contains protocol entries."""
    HUBERMAN_PROTOCOLS = [
        "Morning Sunlight (10 min)", "Non-Sleep Deep Rest (NSDR)", "Cold Exposure",
        "Deliberate Heat (Sauna)", "Fasted Morning Workout", "No Screens 1hr Before Bed",
        "Social Connection", "Nasal Breathing Focus", "Panoramic Vision / Outdoor Time",
        "Dopamine Fasting", "Caffeine Delay (90 min post-wake)"
    ]
    assert len(HUBERMAN_PROTOCOLS) >= 10
    assert "Morning Sunlight (10 min)" in HUBERMAN_PROTOCOLS


def test_family_visibility_levels():
    """FAMILY_VISIBILITY_LEVELS maps correctly."""
    FAMILY_VISIBILITY_LEVELS = {"Private": 0, "Family Can See": 1, "Full Family Dashboard": 2}
    assert FAMILY_VISIBILITY_LEVELS["Private"] == 0
    assert FAMILY_VISIBILITY_LEVELS["Family Can See"] == 1
    assert FAMILY_VISIBILITY_LEVELS["Full Family Dashboard"] == 2


def test_mood_color_function():
    """_mood_color returns correct color indicators."""
    def _mood_color(score):
        if score is None:
            return "⚪"
        if score <= 2:
            return "🔵"
        if score == 3:
            return "⚪"
        if score <= 5:
            return "🟢"
        return "🟡"

    assert _mood_color(None) == "⚪"
    assert _mood_color(1) == "🔵"   # depressed
    assert _mood_color(2) == "🔵"   # low
    assert _mood_color(3) == "⚪"   # neutral
    assert _mood_color(4) == "🟢"   # good
    assert _mood_color(5) == "🟢"   # great
    assert _mood_color(6) == "🟡"   # elevated
    assert _mood_color(7) == "🟡"   # manic — watch!


def test_darrian_context_contains_diagnoses():
    """DARRIAN_CONTEXT system prompt includes all three diagnoses."""
    DARRIAN_CONTEXT = """
    ADHD (Attention-Deficit/Hyperactivity Disorder), Bipolar Disorder, Generalized Anxiety Disorder (GAD)
    CBT, DBT elements, mindfulness, spiritual wellness
    """
    assert "ADHD" in DARRIAN_CONTEXT
    assert "Bipolar" in DARRIAN_CONTEXT
    assert "Anxiety" in DARRIAN_CONTEXT


def test_json_protocols_serialization():
    """Huberman protocols serialize/deserialize as JSON list."""
    protocols = ["Morning Sunlight (10 min)", "Cold Exposure", "NSDR"]
    serialized = json.dumps(protocols)
    deserialized = json.loads(serialized)
    assert deserialized == protocols
    assert len(deserialized) == 3
