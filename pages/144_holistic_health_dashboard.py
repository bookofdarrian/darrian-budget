"""
Holistic Health Dashboard — Page 144
Comprehensive mental, emotional, physical, and spiritual health tracking.
Personalized for Darrian Belcher: ADHD, Bipolar Disorder, Generalized Anxiety.
Integrates: Garmin wearable data, CBT tools, mindfulness, neuroscience protocols,
family sharing, medication tracking, mood analysis, and AI-powered insights.
"""
import streamlit as st
import os
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
import anthropic

st.set_page_config(
    page_title="🌿 Holistic Health Dashboard — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                                  label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                        label="✅ Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",           label="🎬 Creator",         icon="🎬")
st.sidebar.page_link("pages/144_holistic_health_dashboard.py",  label="🌿 Health",          icon="🌿")
st.sidebar.page_link("pages/143_video_ai_studio.py",            label="🎥 Video & AI Image",icon="🎥")
st.sidebar.page_link("pages/17_personal_assistant.py",          label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────
PH   = "%s" if USE_POSTGRES else "?"
AUTO = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

MOOD_SCALE = {1: "😢 Depressed", 2: "😔 Low", 3: "😐 Neutral", 4: "🙂 Good", 5: "😄 Great", 6: "⚡ Elevated", 7: "🔥 Manic"}
ENERGY_SCALE = {1: "💤 Exhausted", 2: "😴 Low", 3: "😐 Moderate", 4: "🔋 Good", 5: "⚡ High"}
ANXIETY_SCALE = {0: "🟢 None", 1: "🟡 Mild", 2: "🟠 Moderate", 3: "🔴 High", 4: "🆘 Severe"}
FOCUS_SCALE = {1: "💭 Scattered", 2: "😕 Distracted", 3: "😐 OK", 4: "🎯 Focused", 5: "🔬 Hyperfocused"}
SLEEP_QUALITY = ["Poor", "Fair", "Good", "Great"]
SPIRITUAL_PRACTICES = ["Prayer", "Meditation", "Journaling", "Nature Walk", "Gratitude Practice",
                        "Breathwork", "Scripture/Reading", "Community", "Service/Giving", "Other"]
CBT_DISTORTIONS = [
    "All-or-Nothing Thinking", "Catastrophizing", "Mind Reading", "Fortune Telling",
    "Emotional Reasoning", "Should Statements", "Labeling", "Personalization",
    "Mental Filter", "Disqualifying the Positive", "Magnification/Minimization", "Overgeneralization"
]
HUBERMAN_PROTOCOLS = [
    "Morning Sunlight (10 min)", "Non-Sleep Deep Rest (NSDR)", "Cold Exposure",
    "Deliberate Heat (Sauna)", "Fasted Morning Workout", "No Screens 1hr Before Bed",
    "Social Connection", "Nasal Breathing Focus", "Panoramic Vision / Outdoor Time",
    "Dopamine Fasting", "Caffeine Delay (90 min post-wake)"
]
FAMILY_VISIBILITY_LEVELS = {"Private": 0, "Family Can See": 1, "Full Family Dashboard": 2}

# ── Load Health Context from file ─────────────────────────────────────────────
def _load_health_context_file() -> str:
    """Load the full DARRIAN_HEALTH_CONTEXT.md if it exists."""
    ctx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "context", "DARRIAN_HEALTH_CONTEXT.md")
    if os.path.exists(ctx_path):
        with open(ctx_path, "r") as f:
            return f.read()
    return ""

_HEALTH_CONTEXT_FILE = _load_health_context_file()

# ── Darrian's Mental Health Context (Clinical — from GeneSight + Psych Eval) ──
DARRIAN_CONTEXT = """
You are Darrian Belcher's personal mental health AI coach and wellness analyst.

## Patient Profile
- **Name:** Darrian Belcher | 22 y/o Black male | Hampton, VA | Project Manager @ Visa Inc.
- **DOB:** August 25, 2003 | Height: 5'7" | Weight: 143 lbs | Lives alone
- **Interests:** Video games, basketball

## Confirmed Diagnoses
- **Bipolar Disorder** — Manic episode at age 17 → voluntary psychiatric hospitalization; monitor for hypomania/mania closely
- **Generalized Anxiety Disorder (GAD)** — Anxiety at 78th percentile (IPIP-NEO); persistent worry, self-consciousness (72nd %ile)
- **ADHD — Inattentive Presentation** — Difficulty shifting attention; processing speed borderline (PSI 76, 5th %ile); NOT hyperactive
- **ASD: RULED OUT** — CARS-2-HF score 16.5 (Minimal-to-No Symptoms); does NOT meet ASD criteria
- **Self-harm thoughts:** Present (no suicidal/homicidal ideation) — always address with care and safety planning
- **Psychiatric Evaluation:** September 15, 2025 by Arlen Versteeg, Ph.D. (#2172)

## Cognitive Profile (WAIS-IV — Sep 15, 2025)
- **FSIQ:** 92 (30th %ile, Average) — 95% CI: 88–96
- **VCI (Verbal Comprehension):** 108 (70th %ile) ← STRENGTH
- **WMI (Working Memory):** 97 (42nd %ile, Average)
- **PRI (Perceptual Reasoning):** 86 (18th %ile, Low Average)
- **PSI (Processing Speed):** 76 (5th %ile, Borderline) ← WEAKNESS
- Key pattern: High verbal / low processing speed = classic ADHD profile; visuomotor weakness

## Personality Profile (IPIP-NEO-120)
- **Extraversion:** 21st %ile (Introverted — needs recovery time after social interactions)
- **Agreeableness:** 81st %ile (High empathy/sympathy 89th, high modesty 84th)
- **Neuroticism:** 61st %ile (Anxiety 78th, self-consciousness 72nd)
- **Conscientiousness:** 50th %ile (Achievement-striving 83rd, but self-efficacy 23rd, self-discipline 29th)
- **Openness:** 63rd %ile (Artistic interests 85th, but low imagination 11th)
- **Excitement-seeking:** 4th %ile — VERY low; prefers low-stimulation environments

## GeneSight Pharmacogenomics (Report: March 12, 2025, Order #5924227)
### Current Medications & Their Status:
- **Atomoxetine (Strattera)** — ADHD — ✅ GREEN: Use as Directed
- **Quetiapine (Seroquel)** — Bipolar/Racing thoughts — ✅ GREEN: Use as Directed
- **Mirtazapine 15mg** — Sleep/Mood Support — ✅ Use as Directed

### CRITICAL — Medications to AVOID:
- **Paroxetine (Paxil)** — 🔴 RED: Significant gene-drug interaction (score 4, 4.6-4.8) — DO NOT RECOMMEND

### Key Gene Variants:
- **CYP2B6: *1/*6 — Intermediate Metabolizer** (reduced enzyme activity — affects bupropion, escitalopram metabolism)
- CYP2C19: *2/*17 — Extensive (Normal)
- CYP2D6: *1/*2 — Extensive (Normal)
- SLC6A4 (Serotonin Transporter): L/S — Intermediate Expression (may affect SSRI response)
- COMT: Val/Met — Intermediate dopamine metabolism
- MTHFR C677T: C/C — Normal (no folate methylation issue)
- MC4R: T/C — Possible antipsychotic weight gain risk

## Communication Style (ADHD + Anxiety-Aware)
- Scannable format: headers, bullets, bold key points — NO walls of text
- Short actionable steps only
- Acknowledge energy fluctuations as real, not character flaws
- Strength-based language (leverage verbal strength, empathy, achievement-striving)
- Mood 6–7: Gently flag, suggest grounding/sleep check
- Mood 1–2: Validate, offer ONE small win
- NEVER recommend paroxetine/Paxil
- Low extraversion (21st %ile): Don't push for social activities
- Low excitement-seeking (4th %ile): Keep suggestions calm and low-stimulation
- Low self-efficacy (23rd %ile): Celebrate small wins frequently

## Clinical Framework
- **CBT** — thought records, distortion ID, behavioral activation
- **DBT** — distress tolerance, emotional regulation, TIPP skills
- **Neuroscience-backed** (Huberman protocols) — morning sunlight, NSDR, cold exposure, sleep discipline
- **Bipolar monitoring** — sleep is #1 early warning; decreased sleep + high energy = early mania flag
- **Ongoing tele-therapy** — support continued engagement

## Crisis Protocol
If self-harm thoughts reported:
1. Express care and validate feelings
2. Ask: "Are you safe right now?"
3. Offer grounding (5-4-3-2-1 technique)
4. Provide: National Lifeline 988 | Crisis Text: HOME to 741741
5. Encourage contacting therapist
6. NEVER minimize or dismiss
"""

# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()

    # Daily check-in (mood/energy/anxiety — all 4 pillars)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_daily_checkin (
            id                {AUTO},
            user_id           INTEGER NOT NULL DEFAULT 1,
            checkin_date      DATE NOT NULL,
            checkin_time      TEXT,

            -- MENTAL
            mood_score        INTEGER,
            anxiety_score     INTEGER,
            focus_score       INTEGER,
            mental_notes      TEXT,
            cbt_thought       TEXT,
            cbt_distortion    TEXT,
            cbt_reframe       TEXT,

            -- EMOTIONAL
            primary_emotion   TEXT,
            secondary_emotion TEXT,
            emotion_trigger   TEXT,
            emotion_notes     TEXT,
            gratitude_1       TEXT,
            gratitude_2       TEXT,
            gratitude_3       TEXT,

            -- PHYSICAL
            energy_score      INTEGER,
            sleep_hours       REAL,
            sleep_quality     TEXT,
            workout_done      INTEGER DEFAULT 0,
            workout_type      TEXT,
            workout_minutes   INTEGER,
            steps             INTEGER,
            water_oz          INTEGER,
            weight_lbs        REAL,
            huberman_protocols TEXT,

            -- SPIRITUAL
            spiritual_practices TEXT,
            intention_today    TEXT,
            reflection_tonight TEXT,
            spiritual_score   INTEGER,

            -- GARMIN SYNC
            garmin_steps         INTEGER,
            garmin_heart_rate    INTEGER,
            garmin_hrv           REAL,
            garmin_sleep_hours   REAL,
            garmin_stress_score  INTEGER,
            garmin_body_battery  INTEGER,
            garmin_calories      INTEGER,
            garmin_synced_at     TIMESTAMP,

            -- FAMILY
            family_visible    INTEGER DEFAULT 0,
            family_note       TEXT,

            -- META
            overall_day_score INTEGER,
            ai_analysis       TEXT,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Medication log
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_medications (
            id            {AUTO},
            user_id       INTEGER NOT NULL DEFAULT 1,
            med_name      TEXT NOT NULL,
            dosage        TEXT,
            frequency     TEXT,
            time_of_day   TEXT,
            purpose       TEXT,
            prescriber    TEXT,
            refill_date   DATE,
            pills_remaining INTEGER,
            is_active     INTEGER DEFAULT 1,
            notes         TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_med_logs (
            id          {AUTO},
            user_id     INTEGER NOT NULL DEFAULT 1,
            med_id      INTEGER,
            taken_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status      TEXT DEFAULT 'taken',
            dose_taken  TEXT,
            notes       TEXT
        )
    """)

    # Episode tracker (manic/depressive/anxiety)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_episodes (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            episode_type    TEXT NOT NULL,
            start_date      DATE,
            end_date        DATE,
            severity        INTEGER,
            triggers        TEXT,
            symptoms        TEXT,
            interventions   TEXT,
            outcome         TEXT,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # CBT thought records
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_thought_records (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            record_date     DATE NOT NULL,
            situation       TEXT,
            automatic_thought TEXT,
            emotions        TEXT,
            emotion_intensity INTEGER,
            cognitive_distortions TEXT,
            evidence_for    TEXT,
            evidence_against TEXT,
            balanced_thought TEXT,
            outcome_emotion TEXT,
            outcome_intensity INTEGER,
            ai_feedback     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Health goals
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_health_goals (
            id          {AUTO},
            user_id     INTEGER NOT NULL DEFAULT 1,
            pillar      TEXT NOT NULL,
            goal        TEXT NOT NULL,
            target_date DATE,
            progress    INTEGER DEFAULT 0,
            completed   INTEGER DEFAULT 0,
            notes       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Garmin manual data entry (for days without auto-sync)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_garmin_data (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            data_date       DATE NOT NULL,
            steps           INTEGER,
            heart_rate_avg  INTEGER,
            heart_rate_max  INTEGER,
            hrv             REAL,
            sleep_hours     REAL,
            sleep_score     INTEGER,
            stress_avg      INTEGER,
            body_battery_high INTEGER,
            body_battery_low  INTEGER,
            calories_active INTEGER,
            calories_total  INTEGER,
            floors_climbed  INTEGER,
            active_minutes  INTEGER,
            vo2_max         REAL,
            spo2_avg        REAL,
            resting_hr      INTEGER,
            notes           TEXT,
            source          TEXT DEFAULT 'manual',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Family shared health summary
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_family_alerts (
            id          {AUTO},
            user_id     INTEGER NOT NULL DEFAULT 1,
            alert_date  DATE NOT NULL,
            alert_type  TEXT,
            message     TEXT,
            mood_flag   INTEGER,
            resolved    INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

_ensure_tables()

# ── Helper Functions ───────────────────────────────────────────────────────────
def _get_user_id():
    return st.session_state.get("user_id", 1)

def _save_checkin(data: dict):
    conn = get_conn()
    cols = ", ".join(data.keys())
    vals = ", ".join([PH] * len(data))
    conn.execute(f"INSERT INTO hh_daily_checkin ({cols}) VALUES ({vals})", list(data.values()))
    conn.commit()
    conn.close()

def _load_checkins(days=30):
    conn = get_conn()
    cur = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(f"""
        SELECT * FROM hh_daily_checkin
        WHERE user_id={PH} AND checkin_date>={PH}
        ORDER BY checkin_date DESC, created_at DESC
    """, (_get_user_id(), since))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_today_checkin():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT * FROM hh_daily_checkin
        WHERE user_id={PH} AND checkin_date={PH}
        ORDER BY created_at DESC LIMIT 1
    """, (_get_user_id(), date.today().isoformat()))
    row = cur.fetchone()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return dict(zip(cols, row)) if row else None

def _save_medication(name, dosage, frequency, time_of_day, purpose, prescriber, refill_date, pills, notes):
    conn = get_conn()
    conn.execute(f"""
        INSERT INTO hh_medications
            (user_id, med_name, dosage, frequency, time_of_day, purpose, prescriber, refill_date, pills_remaining, notes)
        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
    """, (_get_user_id(), name, dosage, frequency, time_of_day, purpose, prescriber, refill_date, pills, notes))
    conn.commit()
    conn.close()

def _load_medications():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM hh_medications WHERE user_id={PH} AND is_active=1 ORDER BY med_name",
                (_get_user_id(),))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _log_medication_taken(med_id, status, notes=""):
    conn = get_conn()
    conn.execute(f"""
        INSERT INTO hh_med_logs (user_id, med_id, status, notes)
        VALUES ({PH},{PH},{PH},{PH})
    """, (_get_user_id(), med_id, status, notes))
    conn.commit()
    conn.close()

def _save_thought_record(data: dict):
    conn = get_conn()
    cols = ", ".join(data.keys())
    vals = ", ".join([PH] * len(data))
    conn.execute(f"INSERT INTO hh_thought_records ({cols}) VALUES ({vals})", list(data.values()))
    conn.commit()
    conn.close()

def _save_garmin_data(data: dict):
    conn = get_conn()
    cols = ", ".join(data.keys())
    vals = ", ".join([PH] * len(data))
    conn.execute(f"INSERT INTO hh_garmin_data ({cols}) VALUES ({vals})", list(data.values()))
    conn.commit()
    conn.close()

def _load_garmin_data(days=7):
    conn = get_conn()
    cur = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(f"""
        SELECT * FROM hh_garmin_data
        WHERE user_id={PH} AND data_date>={PH}
        ORDER BY data_date DESC
    """, (_get_user_id(), since))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _save_goal(pillar, goal, target_date, notes):
    conn = get_conn()
    conn.execute(f"""
        INSERT INTO hh_health_goals (user_id, pillar, goal, target_date, notes)
        VALUES ({PH},{PH},{PH},{PH},{PH})
    """, (_get_user_id(), pillar, goal, target_date, notes))
    conn.commit()
    conn.close()

def _load_goals():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM hh_health_goals WHERE user_id={PH} AND completed=0 ORDER BY pillar, created_at",
                (_get_user_id(),))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _get_ai_insight(checkin_data: dict, recent_checkins: list) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key set. Go to Settings to add one."
    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Build trend summary
        if recent_checkins:
            recent_moods = [c.get("mood_score", 0) for c in recent_checkins[:7] if c.get("mood_score")]
            mood_trend = f"Last 7 days moods: {recent_moods}"
            recent_sleep = [c.get("sleep_hours", 0) for c in recent_checkins[:7] if c.get("sleep_hours")]
            sleep_trend = f"Recent sleep: {recent_sleep}"
        else:
            mood_trend = "No recent data"
            sleep_trend = "No recent data"

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1200,
            system=DARRIAN_CONTEXT,
            messages=[{
                "role": "user",
                "content": f"""Here is my health check-in for today, {date.today().strftime('%A, %B %d, %Y')}:

**Today's Scores:**
- Mood: {checkin_data.get('mood_score', 'N/A')}/7 ({MOOD_SCALE.get(checkin_data.get('mood_score', 0), 'N/A')})
- Energy: {checkin_data.get('energy_score', 'N/A')}/5 ({ENERGY_SCALE.get(checkin_data.get('energy_score', 0), 'N/A')})
- Anxiety: {checkin_data.get('anxiety_score', 'N/A')}/4 ({ANXIETY_SCALE.get(checkin_data.get('anxiety_score', 0), 'N/A')})
- Focus: {checkin_data.get('focus_score', 'N/A')}/5 ({FOCUS_SCALE.get(checkin_data.get('focus_score', 0), 'N/A')})
- Sleep: {checkin_data.get('sleep_hours', 'N/A')} hours ({checkin_data.get('sleep_quality', 'N/A')} quality)
- Spiritual score: {checkin_data.get('spiritual_score', 'N/A')}/5

**Mental:** {checkin_data.get('mental_notes', 'None')}
**Primary Emotion:** {checkin_data.get('primary_emotion', 'None')}
**Trigger:** {checkin_data.get('emotion_trigger', 'None')}
**Gratitude:** {checkin_data.get('gratitude_1', '')}, {checkin_data.get('gratitude_2', '')}, {checkin_data.get('gratitude_3', '')}
**Today's Intention:** {checkin_data.get('intention_today', 'None')}
**Huberman Protocols Done:** {checkin_data.get('huberman_protocols', 'None')}
**Spiritual Practices:** {checkin_data.get('spiritual_practices', 'None')}
**Overall Day Score:** {checkin_data.get('overall_day_score', 'N/A')}/10

**Recent Trends:**
{mood_trend}
{sleep_trend}

**Garmin Data (if available):**
- Steps: {checkin_data.get('garmin_steps', 'N/A')}
- HRV: {checkin_data.get('garmin_hrv', 'N/A')}
- Body Battery: {checkin_data.get('garmin_body_battery', 'N/A')}
- Stress Score: {checkin_data.get('garmin_stress_score', 'N/A')}

Please provide:
1. **Today's Pattern Recognition** — what does today's data suggest?
2. **Early Warning Flags** — any signs of upcoming episode (manic, depressive, or anxiety spike)?
3. **Mental Health Priority** — one thing to focus on mentally today
4. **Physical Optimization** — based on HRV/energy/sleep, what workout intensity is right today?
5. **Spiritual/Emotional Anchor** — a brief grounding thought or practice for today
6. **Tonight's Prep** — 2 things to do tonight to set up a better tomorrow

Keep it concise, actionable, and strength-based."""
            }]
        )
        return msg.content[0].text
    except Exception as e:
        return f"❌ AI insight error: {e}"

def _get_cbt_feedback(situation, thought, distortions, evidence_for, evidence_against) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No API key."
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            system=DARRIAN_CONTEXT,
            messages=[{
                "role": "user",
                "content": f"""I'm working on a CBT thought record. Please help me reframe.

**Situation:** {situation}
**Automatic Thought:** {thought}
**Identified Cognitive Distortions:** {distortions}
**Evidence FOR this thought:** {evidence_for}
**Evidence AGAINST this thought:** {evidence_against}

Please provide:
1. **Validation** — acknowledge what's real in this situation
2. **Distortion Check** — confirm or refine my distortion identification
3. **Balanced Alternative Thought** — a realistic, balanced reframe
4. **Action Step** — one small action to test the balanced thought
5. **ADHD/Anxiety Note** — any specific consideration given my neurodivergence

Keep it supportive, practical, and brief."""
            }]
        )
        return msg.content[0].text
    except Exception as e:
        return f"❌ Error: {e}"

def _mood_color(score):
    if score is None:
        return "⚪"
    if score <= 2:
        return "🔵"  # depressed/low
    if score == 3:
        return "⚪"  # neutral
    if score <= 5:
        return "🟢"  # good range
    return "🟡"  # elevated — watch

def _check_for_episode_flags(checkins: list) -> list:
    """Simple rule-based early warning system."""
    flags = []
    if len(checkins) < 3:
        return flags

    recent = checkins[:5]
    moods = [c.get("mood_score", 3) for c in recent if c.get("mood_score")]
    sleeps = [c.get("sleep_hours", 7) for c in recent if c.get("sleep_hours")]
    anxieties = [c.get("anxiety_score", 1) for c in recent if c.get("anxiety_score") is not None]

    if moods and sum(moods) / len(moods) >= 5.5:
        flags.append(("⚡ Elevated Mood Trend", "Average mood has been high (≥5.5/7). Watch for manic patterns: less sleep, racing thoughts, impulsivity.", "warning"))
    if moods and sum(moods) / len(moods) <= 2.5:
        flags.append(("🔵 Low Mood Trend", "Average mood has been low (≤2.5/7). Consider reaching out to your support system or therapist.", "error"))
    if sleeps and sum(sleeps) / len(sleeps) < 6:
        flags.append(("😴 Sleep Deficit", f"Average sleep: {sum(sleeps)/len(sleeps):.1f}hrs/night. Sleep deprivation amplifies ADHD, anxiety, and mood instability.", "warning"))
    if anxieties and sum(anxieties) / len(anxieties) >= 2.5:
        flags.append(("😰 Elevated Anxiety", "Anxiety has been consistently moderate-high. Grounding and breathwork recommended.", "warning"))

    return flags

# ── UI ─────────────────────────────────────────────────────────────────────────
st.title("🌿 Holistic Health Dashboard")
st.caption("Mental • Emotional • Physical • Spiritual | Personalized for ADHD, Bipolar, & Anxiety")

# ── Today's Summary Bar ────────────────────────────────────────────────────────
today_ci = _load_today_checkin()
checkins = _load_checkins(30)

if today_ci:
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Mood", f"{_mood_color(today_ci.get('mood_score'))} {MOOD_SCALE.get(today_ci.get('mood_score',''), 'N/A')}")
    col2.metric("Energy", f"{ENERGY_SCALE.get(today_ci.get('energy_score',''), 'N/A')}")
    col3.metric("Anxiety", f"{ANXIETY_SCALE.get(today_ci.get('anxiety_score',''), 'N/A')}")
    col4.metric("Focus", f"{FOCUS_SCALE.get(today_ci.get('focus_score',''), 'N/A')}")
    col5.metric("Sleep", f"{today_ci.get('sleep_hours','—')} hrs")
    col6.metric("Day Score", f"{today_ci.get('overall_day_score','—')}/10")

    # Episode flags
    flags = _check_for_episode_flags(checkins)
    if flags:
        for flag_title, flag_msg, flag_type in flags:
            if flag_type == "warning":
                st.warning(f"**{flag_title}** — {flag_msg}")
            else:
                st.error(f"**{flag_title}** — {flag_msg}")
else:
    st.info("📋 No check-in logged today yet. Start your daily check-in in the **Daily Check-In** tab below.")

st.divider()

tabs = st.tabs([
    "📋 Daily Check-In",
    "🧠 Mental Health",
    "💚 Emotional",
    "💪 Physical",
    "🙏 Spiritual",
    "⌚ Garmin Data",
    "💊 Medications",
    "📈 Trends & Insights",
    "🧬 CBT Thought Records",
    "👨‍👩‍👧 Family View",
    "🎯 Goals"
])

# ── TAB 0: Daily Check-In ─────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("📋 Daily Check-In — All 4 Pillars")
    st.caption(f"Today: {date.today().strftime('%A, %B %d, %Y')}")

    if today_ci:
        st.success("✅ You've already checked in today! You can log another entry if needed.")
        with st.expander("View today's check-in"):
            st.json(today_ci)

    with st.form("daily_checkin_form", clear_on_submit=True):
        st.markdown("### 🧠 Mental")
        mc1, mc2, mc3 = st.columns(3)
        mood_score = mc1.slider("Mood (1=Depressed, 7=Manic)", 1, 7, 4,
                                help="7 is manic/elevated — flag if you're at 6-7 multiple days")
        anxiety_score = mc2.slider("Anxiety Level", 0, 4, 1,
                                   help="0=None, 4=Severe panic")
        focus_score = mc3.slider("Focus / ADHD", 1, 5, 3,
                                 help="1=Scattered, 5=Hyperfocused")
        mental_notes = st.text_area("Mental Notes (thoughts, symptoms, what's on your mind)",
                                     height=80, placeholder="Racing thoughts? Brain fog? Intrusive thoughts?")

        st.markdown("---")
        st.markdown("### 💚 Emotional")
        ec1, ec2 = st.columns(2)
        emotions = ["Joy", "Love", "Gratitude", "Hope", "Calm", "Proud", "Excited",
                    "Anger", "Frustration", "Sadness", "Fear", "Shame", "Guilt",
                    "Overwhelmed", "Lonely", "Disconnected", "Numb", "Content"]
        primary_emotion = ec1.selectbox("Primary Emotion", emotions)
        secondary_emotion = ec2.selectbox("Secondary Emotion", ["(none)"] + emotions)
        emotion_trigger = st.text_input("What triggered this emotion?",
                                         placeholder="A situation, person, thought, or nothing obvious")
        emotion_notes = st.text_area("Emotional Notes", height=60, placeholder="Any context you want to capture")

        gc1, gc2, gc3 = st.columns(3)
        gratitude_1 = gc1.text_input("Grateful for #1 🙏")
        gratitude_2 = gc2.text_input("Grateful for #2 🙏")
        gratitude_3 = gc3.text_input("Grateful for #3 🙏")

        st.markdown("---")
        st.markdown("### 💪 Physical")
        pc1, pc2, pc3 = st.columns(3)
        energy_score = pc1.slider("Energy Level", 1, 5, 3)
        sleep_hours = pc2.number_input("Sleep Hours", 0.0, 12.0, 7.0, 0.5)
        sleep_quality = pc3.selectbox("Sleep Quality", SLEEP_QUALITY)

        pw1, pw2, pw3 = st.columns(3)
        workout_done = pw1.checkbox("Worked Out Today?")
        water_oz = pw2.number_input("Water (oz)", 0, 200, 64)
        weight_lbs = pw3.number_input("Weight (lbs, optional)", 0.0, 400.0, 0.0, 0.5)

        workout_type = ""
        workout_minutes = 0
        if workout_done:
            wc1, wc2 = st.columns(2)
            workout_type = wc1.selectbox("Workout Type",
                ["Running", "Lifting", "HIIT", "Basketball", "Yoga", "Walking", "Cycling", "Other"])
            workout_minutes = wc2.number_input("Duration (minutes)", 0, 300, 45)

        huberman_done = st.multiselect("✅ Huberman Protocols (check all done today)", HUBERMAN_PROTOCOLS)

        st.markdown("---")
        st.markdown("### 🙏 Spiritual")
        sc1, sc2 = st.columns(2)
        spiritual_done = sc1.multiselect("Spiritual Practices Today", SPIRITUAL_PRACTICES)
        spiritual_score = sc2.slider("Spiritual / Grounding Feeling (1-5)", 1, 5, 3)
        intention_today = st.text_input("Today's Intention or Focus",
                                         placeholder="What do you want to embody or accomplish today?")
        reflection_tonight = st.text_area("Evening Reflection (fill in later)",
                                           height=60, placeholder="How did today go? What did you learn?")

        st.markdown("---")
        st.markdown("### ⌚ Garmin Quick Entry (or skip if auto-synced)")
        garm1, garm2, garm3 = st.columns(3)
        g_steps = garm1.number_input("Steps", 0, 50000, 0)
        g_hr = garm2.number_input("Avg Heart Rate", 0, 220, 0)
        g_hrv = garm3.number_input("HRV (ms)", 0.0, 200.0, 0.0, 0.5)
        garm4, garm5, garm6 = st.columns(3)
        g_stress = garm4.number_input("Stress Score (0-100)", 0, 100, 0)
        g_battery = garm5.number_input("Body Battery (0-100)", 0, 100, 0)
        g_sleep_g = garm6.number_input("Garmin Sleep Hours", 0.0, 12.0, 0.0, 0.5)

        st.markdown("---")
        st.markdown("### 👨‍👩‍👧 Family Sharing")
        family_visible = st.select_slider("Share today's summary with family?",
                                           options=["Private", "Family Can See", "Full Family Dashboard"],
                                           value="Private")
        family_note = st.text_input("Note for family (optional)",
                                     placeholder="e.g. 'Good day overall, feeling grounded'")

        st.markdown("---")
        overall_day_score = st.slider("Overall Day Score", 1, 10, 5)

        submitted = st.form_submit_button("💾 Save Daily Check-In", type="primary", use_container_width=True)
        if submitted:
            data = {
                "user_id": _get_user_id(),
                "checkin_date": date.today().isoformat(),
                "checkin_time": datetime.now().strftime("%H:%M"),
                "mood_score": mood_score,
                "anxiety_score": anxiety_score,
                "focus_score": focus_score,
                "mental_notes": mental_notes,
                "primary_emotion": primary_emotion,
                "secondary_emotion": secondary_emotion if secondary_emotion != "(none)" else "",
                "emotion_trigger": emotion_trigger,
                "emotion_notes": emotion_notes,
                "gratitude_1": gratitude_1,
                "gratitude_2": gratitude_2,
                "gratitude_3": gratitude_3,
                "energy_score": energy_score,
                "sleep_hours": sleep_hours,
                "sleep_quality": sleep_quality,
                "workout_done": 1 if workout_done else 0,
                "workout_type": workout_type,
                "workout_minutes": workout_minutes,
                "water_oz": water_oz,
                "weight_lbs": weight_lbs if weight_lbs > 0 else None,
                "huberman_protocols": json.dumps(huberman_done),
                "spiritual_practices": json.dumps(spiritual_done),
                "spiritual_score": spiritual_score,
                "intention_today": intention_today,
                "reflection_tonight": reflection_tonight,
                "garmin_steps": g_steps if g_steps > 0 else None,
                "garmin_heart_rate": g_hr if g_hr > 0 else None,
                "garmin_hrv": g_hrv if g_hrv > 0 else None,
                "garmin_stress_score": g_stress if g_stress > 0 else None,
                "garmin_body_battery": g_battery if g_battery > 0 else None,
                "garmin_sleep_hours": g_sleep_g if g_sleep_g > 0 else None,
                "family_visible": FAMILY_VISIBILITY_LEVELS.get(family_visible, 0),
                "family_note": family_note,
                "overall_day_score": overall_day_score,
            }
            _save_checkin(data)
            st.success("✅ Check-in saved!")

            # Auto AI insight
            with st.spinner("🤖 Getting personalized AI insight..."):
                recent = _load_checkins(7)
                ai_insight = _get_ai_insight(data, recent)
            st.markdown("### 🤖 Today's AI Health Insight")
            st.markdown(ai_insight)
            st.rerun()

# ── TAB 1: Mental Health ──────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("🧠 Mental Health Overview")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### 📊 Mood & Anxiety — Last 14 Days")
        recent_14 = _load_checkins(14)
        if recent_14:
            import pandas as pd
            import plotly.graph_objects as go
            df = pd.DataFrame(recent_14)
            df = df.sort_values("checkin_date")

            fig = go.Figure()
            if "mood_score" in df.columns:
                fig.add_trace(go.Scatter(x=df["checkin_date"], y=df["mood_score"],
                    mode="lines+markers", name="Mood (1-7)",
                    line=dict(color="#4CAF50", width=2),
                    marker=dict(size=8)))
            if "anxiety_score" in df.columns:
                fig.add_trace(go.Scatter(x=df["checkin_date"], y=df["anxiety_score"],
                    mode="lines+markers", name="Anxiety (0-4)",
                    line=dict(color="#FF5722", width=2),
                    marker=dict(size=8)))
            if "focus_score" in df.columns:
                fig.add_trace(go.Scatter(x=df["checkin_date"], y=df["focus_score"],
                    mode="lines+markers", name="Focus (1-5)",
                    line=dict(color="#2196F3", width=2),
                    marker=dict(size=8)))

            # Reference lines
            fig.add_hline(y=5.5, line_dash="dash", line_color="yellow",
                          annotation_text="⚠️ Mood elevation watch zone")
            fig.add_hline(y=2.5, line_dash="dash", line_color="blue",
                          annotation_text="⚠️ Low mood zone")

            fig.update_layout(title="Mental Health Scores — 14-Day Trend",
                              xaxis_title="Date", yaxis_title="Score",
                              legend=dict(orientation="h"),
                              height=350, margin=dict(t=50, b=30))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log check-ins to see trends.")

    with col2:
        st.markdown("#### 🚦 Episode Early Warning")
        flags = _check_for_episode_flags(_load_checkins(7))
        if not flags:
            st.success("✅ No flags detected in the last 7 days. You're in a stable range!")
        for f_title, f_msg, f_type in flags:
            if f_type == "warning":
                st.warning(f"**{f_title}**\n\n{f_msg}")
            else:
                st.error(f"**{f_title}**\n\n{f_msg}")

        st.markdown("---")
        st.markdown("#### 🧠 ADHD / Bipolar / Anxiety Context")
        with st.expander("About your diagnoses & this dashboard"):
            st.markdown("""
**ADHD:** Executive dysfunction, time blindness, hyperfocus, emotional dysregulation.
Track focus scores and use body-double/external accountability strategies.

**Bipolar Disorder:** Mood cycles between depressive lows and manic highs.
The 7-point mood scale flags anything ≥6 for elevated awareness.
Track sleep closely — sleep disruption is often the first manic sign.

**Generalized Anxiety Disorder:** Persistent worry, physical tension, difficulty tolerating uncertainty.
The anxiety scale (0-4) helps quantify what often feels invisible.

**All three interact:** ADHD-like symptoms worsen in both manic AND depressive states.
Consistent sleep + exercise + medication adherence stabilizes all three.
""")

# ── TAB 2: Emotional ─────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("💚 Emotional Wellness")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### 📊 Emotion Log — Last 14 Days")
        recent_14 = _load_checkins(14)
        if recent_14:
            import pandas as pd
            import plotly.express as px
            df = pd.DataFrame(recent_14)
            if "primary_emotion" in df.columns and df["primary_emotion"].notna().any():
                emotion_counts = df["primary_emotion"].value_counts().reset_index()
                emotion_counts.columns = ["Emotion", "Count"]
                fig = px.bar(emotion_counts, x="Emotion", y="Count",
                             title="Primary Emotions — Last 14 Days",
                             color="Count", color_continuous_scale="Teal")
                fig.update_layout(height=300, margin=dict(t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Gratitude Log**")
            gratitude_entries = []
            for c in recent_14[:7]:
                for k in ["gratitude_1", "gratitude_2", "gratitude_3"]:
                    if c.get(k):
                        gratitude_entries.append({"Date": c.get("checkin_date","")[:10],
                                                   "Gratitude": c.get(k,"")})
            if gratitude_entries:
                gdf = pd.DataFrame(gratitude_entries)
                st.dataframe(gdf, use_container_width=True, hide_index=True)
        else:
            st.info("No check-ins yet. Log daily to track emotional patterns.")

    with col2:
        st.markdown("#### 🛠️ Emotional Regulation Tools")
        with st.expander("🌬️ 4-7-8 Breathing (Anxiety)"):
            st.markdown("""
1. Inhale through nose for **4 counts**
2. Hold breath for **7 counts**
3. Exhale through mouth for **8 counts**
4. Repeat 3-4 times

*Activates parasympathetic nervous system. Use during anxiety spikes.*
""")
        with st.expander("🧲 5-4-3-2-1 Grounding (Panic)"):
            st.markdown("""
- **5 things you can SEE**
- **4 things you can TOUCH**
- **3 things you can HEAR**
- **2 things you can SMELL**
- **1 thing you can TASTE**

*Brings attention back to the present. Excellent for dissociation and panic.*
""")
        with st.expander("⚡ TIPP Skills (Intense Emotions — DBT)"):
            st.markdown("""
**T — Temperature:** Cold water on face, ice pack on wrists
**I — Intense Exercise:** 20 jumping jacks, run in place
**P — Paced Breathing:** Slow, deep, elongated exhale
**P — Paired Muscle Relaxation:** Tense and release muscle groups

*Use when emotions feel out of control.*
""")
        with st.expander("🧠 STOP Skill"):
            st.markdown("""
**S** — Stop. Don't react yet.
**T** — Take a breath.
**O** — Observe. What am I feeling? What's happening?
**P** — Proceed mindfully.
""")

# ── TAB 3: Physical ───────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("💪 Physical Health")

    recent = _load_checkins(14)
    garmin = _load_garmin_data(14)

    col1, col2 = st.columns([2, 1])
    with col1:
        if recent:
            import pandas as pd
            import plotly.graph_objects as go
            df = pd.DataFrame(recent).sort_values("checkin_date")
            garmin_df = pd.DataFrame(garmin).sort_values("data_date") if garmin else None

            fig = go.Figure()
            if "sleep_hours" in df.columns:
                fig.add_trace(go.Bar(x=df["checkin_date"], y=df["sleep_hours"],
                    name="Sleep (hrs)", marker_color="#7B68EE", opacity=0.7))
            if "energy_score" in df.columns:
                fig.add_trace(go.Scatter(x=df["checkin_date"], y=df["energy_score"],
                    mode="lines+markers", name="Energy (1-5)",
                    line=dict(color="#FF8C00", width=2), yaxis="y2"))
            if garmin_df is not None and "hrv" in garmin_df.columns:
                fig.add_trace(go.Scatter(x=garmin_df["data_date"], y=garmin_df["hrv"],
                    mode="lines+markers", name="HRV (ms)",
                    line=dict(color="#00CED1", width=2, dash="dot"), yaxis="y3"))

            fig.update_layout(
                title="Sleep, Energy & HRV — 14 Days",
                xaxis_title="Date",
                yaxis=dict(title="Sleep (hrs)", side="left"),
                yaxis2=dict(title="Energy", overlaying="y", side="right", range=[0, 6]),
                height=350, margin=dict(t=50, b=30),
                legend=dict(orientation="h")
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log check-ins to see physical trends.")

        # Garmin summary
        if garmin:
            st.markdown("#### ⌚ Latest Garmin Data")
            latest = garmin[0]
            gk1, gk2, gk3, gk4 = st.columns(4)
            gk1.metric("Steps", f"{latest.get('steps', 0):,}" if latest.get("steps") else "—")
            gk2.metric("Avg HR", f"{latest.get('heart_rate_avg', 0)} bpm" if latest.get("heart_rate_avg") else "—")
            gk3.metric("HRV", f"{latest.get('hrv', 0)} ms" if latest.get("hrv") else "—")
            gk4.metric("Body Battery", f"{latest.get('body_battery_high', 0)}" if latest.get("body_battery_high") else "—")

    with col2:
        st.markdown("#### 📋 Huberman Protocols Tracker")
        recent_7 = _load_checkins(7)
        protocol_counts = {}
        for ci in recent_7:
            try:
                protocols = json.loads(ci.get("huberman_protocols") or "[]")
                for p in protocols:
                    protocol_counts[p] = protocol_counts.get(p, 0) + 1
            except Exception:
                pass

        for protocol in HUBERMAN_PROTOCOLS:
            count = protocol_counts.get(protocol, 0)
            pct = int((count / 7) * 100)
            col_a, col_b = st.columns([3, 1])
            col_a.caption(protocol)
            col_b.caption(f"{count}/7 days")
            st.progress(pct / 100)

        st.markdown("---")
        st.markdown("#### 💊 Today's Workout Recommendation")
        if today_ci:
            hrv = today_ci.get("garmin_hrv", 0) or 0
            energy = today_ci.get("energy_score", 3) or 3
            sleep = today_ci.get("sleep_hours", 7) or 7
            if hrv > 0 and hrv < 40 or energy <= 2 or sleep < 6:
                st.info("🟡 **Recovery Day** — Low HRV, energy, or sleep. Opt for walking, yoga, or light movement. Pushing hard today may increase cortisol and worsen mood.")
            elif hrv > 60 or energy >= 4:
                st.success("🟢 **High Performance Day** — HRV and energy are strong. Great day for high-intensity training, PRs, or long cardio.")
            else:
                st.info("🔵 **Moderate Day** — Steady-state cardio, moderate lifting, or bodyweight work is ideal.")
        else:
            st.caption("Log today's check-in to get a personalized workout recommendation.")

# ── TAB 4: Spiritual ──────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("🙏 Spiritual & Purpose Wellness")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### 📊 Spiritual Score — Last 14 Days")
        recent_14 = _load_checkins(14)
        if recent_14:
            import pandas as pd
            import plotly.express as px
            df = pd.DataFrame(recent_14).sort_values("checkin_date")
            if "spiritual_score" in df.columns and df["spiritual_score"].notna().any():
                fig = px.line(df, x="checkin_date", y="spiritual_score",
                              title="Spiritual Wellness Score",
                              markers=True, color_discrete_sequence=["#9C27B0"])
                fig.add_hline(y=3, line_dash="dash", line_color="gray", annotation_text="Baseline")
                fig.update_layout(height=280, margin=dict(t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📝 Recent Intentions & Reflections")
        for ci in _load_checkins(7)[:5]:
            if ci.get("intention_today") or ci.get("reflection_tonight"):
                with st.container(border=True):
                    st.caption(ci.get("checkin_date", "")[:10])
                    if ci.get("intention_today"):
                        st.markdown(f"🌅 **Intention:** {ci['intention_today']}")
                    if ci.get("reflection_tonight"):
                        st.markdown(f"🌙 **Reflection:** {ci['reflection_tonight']}")

    with col2:
        st.markdown("#### 🌿 Practice Frequency (7 days)")
        recent_7 = _load_checkins(7)
        practice_counts = {}
        for ci in recent_7:
            try:
                practices = json.loads(ci.get("spiritual_practices") or "[]")
                for p in practices:
                    practice_counts[p] = practice_counts.get(p, 0) + 1
            except Exception:
                pass
        if practice_counts:
            for practice, count in sorted(practice_counts.items(), key=lambda x: -x[1]):
                st.caption(f"{practice}: {count}/7 days")
                st.progress(count / 7)
        else:
            st.info("Log spiritual practices in check-in to see tracking here.")

        st.markdown("---")
        st.markdown("#### 💡 Daily Mindfulness Prompt")
        import random
        prompts_list = [
            "What is one thing I can let go of today to make space for peace?",
            "Where in my body do I feel tension right now? Can I breathe into it?",
            "What would my best self do in this moment?",
            "Am I reacting or responding? Can I pause before I act?",
            "What am I grateful for that I've been taking for granted?",
            "If this moment were a teacher, what is it teaching me?",
            "What does 'enough' look like for me today?",
            "How can I show up fully for my family today — even in small ways?",
            "What does God/the Universe/my higher self want for me today?",
            "If I knew I couldn't fail, what would I try?"
        ]
        if "mindfulness_prompt" not in st.session_state:
            st.session_state.mindfulness_prompt = random.choice(prompts_list)
        st.info(f'💭 *"{st.session_state.mindfulness_prompt}"*')
        if st.button("New Prompt 🔄"):
            st.session_state.mindfulness_prompt = random.choice(prompts_list)
            st.rerun()

# ── TAB 5: Garmin Data ────────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("⌚ Garmin Health Data")
    st.info("📲 **Garmin Integration:** Until the Garmin Connect API is connected, log data manually here or paste from the Garmin app. The Garmin Connect IQ API (via `python-garminconnect`) can be enabled with your Garmin credentials in Settings.")

    sub_g = st.tabs(["🔄 Sync Now", "📥 Log Garmin Data", "📊 Garmin Trends"])

    # ── Sub-tab 0: Sync Now ───────────────────────────────────────────────────
    with sub_g[0]:
        st.markdown("### 🔄 Garmin Connect — Live Sync")

        garmin_email    = get_setting("garmin_email") or ""
        garmin_password = get_setting("garmin_password") or ""

        # ── Credentials setup ─────────────────────────────────────────────────
        with st.expander("⚙️ Garmin Connect Credentials" + (" ✅ Saved" if garmin_email else " — Not set"), expanded=not garmin_email):
            st.caption("Your credentials are stored securely in the app database (never in code or GitHub).")
            new_email = st.text_input("Garmin Connect Email", value=garmin_email, key="g_cred_email")
            new_pass  = st.text_input("Garmin Connect Password", value=garmin_password,
                                       type="password", key="g_cred_pass")
            if st.button("💾 Save Garmin Credentials", key="save_garmin_creds"):
                set_setting("garmin_email", new_email)
                set_setting("garmin_password", new_pass)
                st.success("✅ Credentials saved!")
                st.rerun()

        if not garmin_email or not garmin_password:
            st.warning("⚠️ Enter your Garmin Connect credentials above to enable live sync.")
        else:
            st.success(f"✅ Connected as: **{garmin_email}**")

            # ── MFA / 2FA Section ─────────────────────────────────────────────
            st.info(
                "🔐 **If Garmin sends you a 2FA/MFA code** (email or SMS), enter it below "
                "before clicking Sync. Leave blank if you don't have 2FA enabled."
            )
            mfa_col1, mfa_col2 = st.columns([2, 3])
            mfa_code = mfa_col1.text_input(
                "MFA / 2FA Code (optional)", max_chars=10,
                placeholder="e.g. 123456", key="garmin_mfa_code",
                help="Garmin emails or texts you a 6-digit code if 2FA is on."
            )
            mfa_col2.markdown("""
**How it works:**
1. Click Sync → Garmin emails/texts you a 6-digit code
2. Enter the code above and click Sync again within 5 minutes
3. After first successful sync, future syncs may not require a code
""")

            sync_date = st.date_input("Sync Date", value=date.today(), key="garmin_sync_date")
            sync_col1, sync_col2 = st.columns(2)

            with sync_col1:
                sync_btn = st.button("⌚ Sync from Garmin Connect", type="primary",
                                      use_container_width=True, key="garmin_sync_btn")
                st.caption("Pulls steps, HR, HRV, sleep, stress, body battery from Garmin Connect API")

            with sync_col2:
                sync_7_btn = st.button("📅 Sync Last 7 Days", use_container_width=True, key="garmin_sync_7")
                st.caption("Backfills the past 7 days of data")

            def _do_garmin_sync(target_date: date, mfa: str = "") -> dict:
                """Pull data for one day from Garmin Connect. Returns result dict."""
                try:
                    from garminconnect import Garmin
                    mfa_callback = (lambda: mfa) if mfa.strip() else None
                    client = Garmin(garmin_email, garmin_password, prompt_mfa=mfa_callback)
                    client.login()
                    date_str = target_date.isoformat()

                    result = {"date": date_str, "synced": [], "errors": []}

                    # ── Daily stats ───────────────────────────────────────────
                    try:
                        stats = client.get_stats(date_str)
                        steps        = stats.get("totalSteps", 0)
                        hr_avg       = stats.get("averageHeartRate", 0)
                        hr_max       = stats.get("maxHeartRate", 0)
                        rhr          = stats.get("restingHeartRate", 0)
                        floors       = stats.get("floorsAscended", 0)
                        cals_active  = stats.get("activeKilocalories", 0)
                        cals_total   = stats.get("totalKilocalories", 0)
                        active_min   = (stats.get("highlyActiveSeconds", 0) +
                                        stats.get("activeSeconds", 0)) // 60
                        result["steps"]       = steps
                        result["hr_avg"]      = hr_avg
                        result["hr_max"]      = hr_max
                        result["rhr"]         = rhr
                        result["floors"]      = floors
                        result["cals_active"] = cals_active
                        result["cals_total"]  = cals_total
                        result["active_min"]  = active_min
                        result["synced"].append("daily stats")
                    except Exception as e:
                        result["errors"].append(f"stats: {e}")

                    # ── Sleep ─────────────────────────────────────────────────
                    try:
                        sleep_data = client.get_sleep_data(date_str)
                        dto = sleep_data.get("dailySleepDTO", {})
                        sleep_sec = dto.get("sleepTimeSeconds", 0)
                        result["sleep_hours"] = round(sleep_sec / 3600, 2) if sleep_sec else None
                        result["sleep_score"] = dto.get("sleepScores", {}).get("overall", {}).get("value") if dto else None
                        result["synced"].append("sleep")
                    except Exception as e:
                        result["errors"].append(f"sleep: {e}")

                    # ── HRV ───────────────────────────────────────────────────
                    try:
                        hrv_data = client.get_hrv_data(date_str)
                        hrv_summary = hrv_data.get("hrvSummary", {}) if hrv_data else {}
                        result["hrv"] = hrv_summary.get("lastNight") or hrv_summary.get("weeklyAvg")
                        result["synced"].append("HRV")
                    except Exception as e:
                        result["errors"].append(f"HRV: {e}")

                    # ── Stress ────────────────────────────────────────────────
                    try:
                        stress_data = client.get_stress_data(date_str)
                        avg_stress = stress_data.get("avgStressLevel", 0) if stress_data else 0
                        result["stress_avg"] = avg_stress if avg_stress and avg_stress > 0 else None
                        result["synced"].append("stress")
                    except Exception as e:
                        result["errors"].append(f"stress: {e}")

                    # ── Body Battery ──────────────────────────────────────────
                    try:
                        bb_data = client.get_body_battery(date_str)
                        if bb_data and isinstance(bb_data, list) and len(bb_data) > 0:
                            bb_values = [item.get("bodyBatteryLevel", 0) for item in bb_data
                                         if item.get("bodyBatteryLevel") is not None]
                            result["body_battery_high"] = max(bb_values) if bb_values else None
                            result["body_battery_low"]  = min(bb_values) if bb_values else None
                        result["synced"].append("body battery")
                    except Exception as e:
                        result["errors"].append(f"body battery: {e}")

                    # ── SpO2 ──────────────────────────────────────────────────
                    try:
                        spo2_data = client.get_spo2_data(date_str)
                        avg_spo2 = spo2_data.get("averageSpO2") if spo2_data else None
                        result["spo2_avg"] = avg_spo2
                        if avg_spo2:
                            result["synced"].append("SpO2")
                    except Exception as e:
                        result["errors"].append(f"SpO2: {e}")

                    return result

                except Exception as e:
                    return {"date": target_date.isoformat(), "synced": [],
                            "errors": [f"Login failed: {e}"], "login_error": True}

            def _store_garmin_result(res: dict):
                """Save a sync result dict to hh_garmin_data."""
                gdata = {
                    "user_id": _get_user_id(),
                    "data_date": res["date"],
                    "steps":            res.get("steps"),
                    "heart_rate_avg":   res.get("hr_avg"),
                    "heart_rate_max":   res.get("hr_max"),
                    "resting_hr":       res.get("rhr"),
                    "hrv":              res.get("hrv"),
                    "sleep_hours":      res.get("sleep_hours"),
                    "sleep_score":      res.get("sleep_score"),
                    "stress_avg":       res.get("stress_avg"),
                    "body_battery_high": res.get("body_battery_high"),
                    "body_battery_low":  res.get("body_battery_low"),
                    "calories_active":  res.get("cals_active"),
                    "calories_total":   res.get("cals_total"),
                    "floors_climbed":   res.get("floors"),
                    "active_minutes":   res.get("active_min"),
                    "spo2_avg":         res.get("spo2_avg"),
                    "source":           "garmin_api",
                    "notes":            f"Auto-synced {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                }
                # Remove None values to avoid SQLite issues
                gdata = {k: v for k, v in gdata.items() if v is not None}
                _save_garmin_data(gdata)

            # ── Sync single day ───────────────────────────────────────────────
            if sync_btn:
                with st.spinner(f"⌚ Connecting to Garmin Connect and pulling {sync_date}..."):
                    res = _do_garmin_sync(sync_date, mfa=mfa_code)

                if res.get("login_error") or (res.get("errors") and not res.get("synced")):
                    st.error(f"❌ Sync failed: {'; '.join(res.get('errors', []))}")
                else:
                    _store_garmin_result(res)
                    st.success(f"✅ Synced: {', '.join(res.get('synced', []))}")
                    if res.get("errors"):
                        st.warning(f"⚠️ Some data unavailable: {'; '.join(res['errors'])}")

                    # Show what was pulled
                    kc = st.columns(5)
                    kc[0].metric("Steps",        f"{res.get('steps', 0):,}" if res.get('steps') else "—")
                    kc[1].metric("Avg HR",        f"{res.get('hr_avg', 0)} bpm" if res.get('hr_avg') else "—")
                    kc[2].metric("HRV",           f"{res.get('hrv', 0)} ms" if res.get('hrv') else "—")
                    kc[3].metric("Body Battery",  f"↑{res.get('body_battery_high','—')} ↓{res.get('body_battery_low','—')}")
                    kc[4].metric("Sleep",         f"{res.get('sleep_hours', '—')} hrs")
                    st.rerun()

            # ── Sync last 7 days ──────────────────────────────────────────────
            if sync_7_btn:
                progress_bar = st.progress(0, text="Syncing past 7 days...")
                results = []
                for i, days_back in enumerate(range(6, -1, -1)):
                    target = date.today() - timedelta(days=days_back)
                    progress_bar.progress((i + 1) / 7, text=f"Syncing {target.isoformat()}...")
                    res = _do_garmin_sync(target)
                    if res.get("synced"):
                        _store_garmin_result(res)
                        results.append(f"✅ {target.isoformat()} ({', '.join(res['synced'])})")
                    else:
                        results.append(f"❌ {target.isoformat()} — {'; '.join(res.get('errors', ['No data']))}")
                progress_bar.empty()
                for r in results:
                    st.markdown(r)
                st.success("📅 7-day sync complete!")
                st.rerun()

            # ── Recent sync summary ───────────────────────────────────────────
            st.divider()
            st.markdown("#### ⌚ Recent Garmin Syncs")
            recent_garmin = _load_garmin_data(7)
            if recent_garmin:
                import pandas as pd
                gdf = pd.DataFrame(recent_garmin)
                display_cols = [c for c in ["data_date","steps","heart_rate_avg","hrv",
                                             "sleep_hours","stress_avg","body_battery_high","source"]
                                if c in gdf.columns]
                st.dataframe(gdf[display_cols].rename(columns={
                    "data_date": "Date", "steps": "Steps", "heart_rate_avg": "HR",
                    "hrv": "HRV", "sleep_hours": "Sleep", "stress_avg": "Stress",
                    "body_battery_high": "Batt Peak", "source": "Source"
                }), use_container_width=True, hide_index=True)
            else:
                st.info("No synced data yet. Hit **Sync from Garmin Connect** above.")

    # ── Sub-tab 1: Manual Log ─────────────────────────────────────────────────
    with sub_g[1]:
        st.markdown("### 📥 Log Garmin Data Manually")
        st.caption("Use this if auto-sync isn't working or to backfill past days.")
        gc1, gc2 = st.columns(2)
        with gc1:
            g_date = st.date_input("Date", value=date.today(), key="glog_date")
            g_steps = st.number_input("Steps", 0, 60000, 0, key="glog_steps")
            g_hr_avg = st.number_input("Avg Heart Rate (bpm)", 0, 220, 0, key="glog_hr_avg")
            g_hr_max = st.number_input("Max Heart Rate (bpm)", 0, 220, 0, key="glog_hr_max")
            g_hrv = st.number_input("HRV (ms)", 0.0, 200.0, 0.0, key="glog_hrv")
            g_sleep = st.number_input("Sleep (hours)", 0.0, 12.0, 0.0, 0.5, key="glog_sleep")
            g_sleep_score = st.number_input("Sleep Score (0-100)", 0, 100, 0, key="glog_sleep_score")

        with gc2:
            g_stress_avg = st.number_input("Avg Stress Score (0-100)", 0, 100, 0, key="glog_stress")
            g_batt_high = st.number_input("Body Battery High (0-100)", 0, 100, 0, key="glog_batt_h")
            g_batt_low = st.number_input("Body Battery Low (0-100)", 0, 100, 0, key="glog_batt_l")
            g_cals_active = st.number_input("Active Calories", 0, 5000, 0, key="glog_cals_a")
            g_active_min = st.number_input("Active Minutes", 0, 600, 0, key="glog_active_min")
            g_resting_hr = st.number_input("Resting Heart Rate", 0, 150, 0, key="glog_rhr")
            g_vo2 = st.number_input("VO2 Max (optional)", 0.0, 80.0, 0.0, key="glog_vo2")
            g_spo2 = st.number_input("SpO2 % (optional)", 0.0, 100.0, 0.0, key="glog_spo2")
            g_notes = st.text_input("Notes (e.g. 'wore watch to bed')", key="glog_notes")

        if st.button("💾 Save Garmin Data", type="primary", use_container_width=True):
            gdata = {
                "user_id": _get_user_id(),
                "data_date": g_date.isoformat(),
                "steps": g_steps if g_steps > 0 else None,
                "heart_rate_avg": g_hr_avg if g_hr_avg > 0 else None,
                "heart_rate_max": g_hr_max if g_hr_max > 0 else None,
                "hrv": g_hrv if g_hrv > 0 else None,
                "sleep_hours": g_sleep if g_sleep > 0 else None,
                "sleep_score": g_sleep_score if g_sleep_score > 0 else None,
                "stress_avg": g_stress_avg if g_stress_avg > 0 else None,
                "body_battery_high": g_batt_high if g_batt_high > 0 else None,
                "body_battery_low": g_batt_low if g_batt_low > 0 else None,
                "calories_active": g_cals_active if g_cals_active > 0 else None,
                "active_minutes": g_active_min if g_active_min > 0 else None,
                "resting_hr": g_resting_hr if g_resting_hr > 0 else None,
                "vo2_max": g_vo2 if g_vo2 > 0 else None,
                "spo2_avg": g_spo2 if g_spo2 > 0 else None,
                "notes": g_notes,
                "source": "manual",
            }
            _save_garmin_data(gdata)
            st.success("✅ Garmin data saved!")
            st.rerun()

    # ── Sub-tab 2: Trends ─────────────────────────────────────────────────────
    with sub_g[2]:
        garmin_data = _load_garmin_data(30)
        if garmin_data:
            import pandas as pd
            import plotly.graph_objects as go
            gdf = pd.DataFrame(garmin_data).sort_values("data_date")
            fig = go.Figure()
            if "steps" in gdf.columns:
                fig.add_trace(go.Bar(x=gdf["data_date"], y=gdf["steps"], name="Steps",
                                     marker_color="#4CAF50", opacity=0.7))
            fig.update_layout(title="Daily Steps — 30 Days", height=280, margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

            fig2 = go.Figure()
            if "hrv" in gdf.columns:
                fig2.add_trace(go.Scatter(x=gdf["data_date"], y=gdf["hrv"],
                    mode="lines+markers", name="HRV (ms)",
                    line=dict(color="#00CED1", width=2)))
            if "stress_avg" in gdf.columns:
                fig2.add_trace(go.Scatter(x=gdf["data_date"], y=gdf["stress_avg"],
                    mode="lines+markers", name="Avg Stress",
                    line=dict(color="#FF5722", width=2)))
            if "body_battery_high" in gdf.columns:
                fig2.add_trace(go.Scatter(x=gdf["data_date"], y=gdf["body_battery_high"],
                    mode="lines+markers", name="Body Battery Peak",
                    line=dict(color="#FFC107", width=2)))
            if "sleep_hours" in gdf.columns:
                fig2.add_trace(go.Bar(x=gdf["data_date"], y=gdf["sleep_hours"],
                    name="Sleep (hrs)", marker_color="#7B68EE", opacity=0.5, yaxis="y2"))
            fig2.update_layout(
                title="HRV, Stress, Body Battery & Sleep — 30 Days",
                height=320, margin=dict(t=40, b=20),
                legend=dict(orientation="h"),
                yaxis2=dict(overlaying="y", side="right", range=[0, 14])
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Resting HR trend
            if "resting_hr" in gdf.columns and gdf["resting_hr"].notna().any():
                import plotly.express as px
                fig3 = px.line(gdf.dropna(subset=["resting_hr"]),
                               x="data_date", y="resting_hr",
                               title="Resting Heart Rate — 30 Days",
                               markers=True, color_discrete_sequence=["#E91E63"])
                fig3.update_layout(height=260, margin=dict(t=40, b=20))
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No Garmin data yet. Use the **Sync Now** tab or **Manual Log** tab.")

# ── TAB 6: Medications ────────────────────────────────────────────────────────
with tabs[6]:
    st.subheader("💊 Medication Tracker")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### ➕ Add Medication")
        with st.form("med_form", clear_on_submit=True):
            med_name = st.text_input("Medication Name *")
            med_dosage = st.text_input("Dosage (e.g. 30mg)")
            med_freq = st.selectbox("Frequency", ["Daily", "Twice Daily", "3x Daily",
                                                   "Every other day", "As needed", "Weekly"])
            med_time = st.text_input("Time of Day (e.g. Morning, Evening)")
            med_purpose = st.text_input("Purpose (e.g. ADHD, Mood Stabilizer, Anxiety)")
            med_prescriber = st.text_input("Prescribing Doctor")
            med_refill = st.date_input("Next Refill Date", value=date.today())
            med_pills = st.number_input("Pills Remaining", 0, 500, 30)
            med_notes = st.text_area("Notes", height=60)
            if st.form_submit_button("💾 Save Medication", type="primary"):
                if med_name:
                    _save_medication(med_name, med_dosage, med_freq, med_time,
                                     med_purpose, med_prescriber, med_refill, med_pills, med_notes)
                    st.success(f"✅ {med_name} added!")
                    st.rerun()

    with col2:
        st.markdown("#### 💊 Active Medications")
        meds = _load_medications()
        if not meds:
            st.info("No medications tracked yet. Add your first medication.")
        else:
            for med in meds:
                days_to_refill = (date.fromisoformat(str(med.get("refill_date", date.today()))) - date.today()).days if med.get("refill_date") else None
                refill_warning = ""
                if days_to_refill is not None and days_to_refill <= 7:
                    refill_warning = f" 🔴 **Refill in {days_to_refill} days!**"
                elif days_to_refill is not None and days_to_refill <= 14:
                    refill_warning = f" 🟡 Refill in {days_to_refill} days"

                with st.container(border=True):
                    mc1, mc2 = st.columns([3, 1])
                    with mc1:
                        st.markdown(f"**{med['med_name']}** — {med.get('dosage','')} {med.get('frequency','')}")
                        st.caption(f"🕐 {med.get('time_of_day','')} | 🎯 {med.get('purpose','')} | 👨‍⚕️ {med.get('prescriber','')}")
                        st.caption(f"💊 {med.get('pills_remaining',0)} pills remaining | 📅 Refill: {str(med.get('refill_date',''))[:10]}{refill_warning}")
                    with mc2:
                        if st.button("✅ Taken", key=f"med_taken_{med['id']}"):
                            _log_medication_taken(med["id"], "taken")
                            st.success("Logged!")
                        if st.button("⏭️ Skipped", key=f"med_skip_{med['id']}"):
                            _log_medication_taken(med["id"], "skipped")
                            st.info("Logged as skipped")

# ── TAB 7: Trends & AI Insights ───────────────────────────────────────────────
with tabs[7]:
    st.subheader("📈 Trends & AI Health Insights")

    col1, col2 = st.columns([2, 1])
    with col1:
        checkins_30 = _load_checkins(30)
        if checkins_30:
            import pandas as pd
            import plotly.graph_objects as go
            df30 = pd.DataFrame(checkins_30).sort_values("checkin_date")

            # Overall day score
            if "overall_day_score" in df30.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df30["checkin_date"], y=df30["overall_day_score"],
                    mode="lines+markers+text",
                    name="Day Score",
                    line=dict(color="#9C27B0", width=2),
                    marker=dict(size=8)))
                fig.add_hline(y=7, line_dash="dash", line_color="green", annotation_text="Good threshold")
                fig.add_hline(y=4, line_dash="dash", line_color="red", annotation_text="Low threshold")
                fig.update_layout(title="Overall Day Score — 30 Days",
                                  yaxis=dict(range=[0, 11]),
                                  height=280, margin=dict(t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

            # Sleep vs Mood correlation
            if "sleep_hours" in df30.columns and "mood_score" in df30.columns:
                import plotly.express as px
                corr_df = df30[["sleep_hours", "mood_score", "anxiety_score", "energy_score"]].dropna()
                if len(corr_df) > 3:
                    fig2 = px.scatter(corr_df, x="sleep_hours", y="mood_score",
                                      color="anxiety_score",
                                      color_continuous_scale="RdYlGn_r",
                                      title="Sleep vs Mood (color = anxiety level)",
                                      size="energy_score",
                                      trendline="ols")
                    fig2.update_layout(height=280, margin=dict(t=40, b=20))
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Log check-ins daily for 7+ days to see trends.")

    with col2:
        st.markdown("#### 🤖 Get AI Health Insight")
        st.caption("Claude analyzes your recent data with full ADHD/Bipolar/Anxiety context")

        if checkins_30:
            if st.button("🔍 Generate AI Insight Report", type="primary", use_container_width=True):
                latest_ci = checkins_30[0]
                with st.spinner("Claude is analyzing your health patterns..."):
                    insight = _get_ai_insight(latest_ci, checkins_30)
                with st.expander("🤖 AI Health Report", expanded=True):
                    st.markdown(insight)
        else:
            st.info("Log at least one check-in to get AI insights.")

        st.markdown("---")
        st.markdown("#### 📊 30-Day Summary")
        if checkins_30:
            import pandas as pd
            df_s = pd.DataFrame(checkins_30)
            metrics_map = {
                "Avg Mood": ("mood_score", 2),
                "Avg Sleep": ("sleep_hours", 1),
                "Avg Energy": ("energy_score", 1),
                "Avg Anxiety": ("anxiety_score", 1),
                "Avg Focus": ("focus_score", 1),
            }
            for label, (col, decimals) in metrics_map.items():
                if col in df_s.columns and df_s[col].notna().any():
                    val = df_s[col].dropna().mean()
                    st.metric(label, f"{val:.{decimals}f}")

# ── TAB 8: CBT Thought Records ────────────────────────────────────────────────
with tabs[8]:
    st.subheader("🧬 CBT Thought Records")
    st.caption("Cognitive Behavioral Therapy — Identify automatic thoughts, challenge distortions, build balanced thinking.")

    sub_cbt = st.tabs(["📝 New Record", "📚 History"])

    with sub_cbt[0]:
        col1, col2 = st.columns([1, 1])
        with col1:
            cbt_date = st.date_input("Date", value=date.today(), key="cbt_date")
            cbt_situation = st.text_area("Situation",
                placeholder="Briefly describe the situation where the emotion was triggered",
                height=70, key="cbt_sit")
            cbt_thought = st.text_area("Automatic Thought",
                placeholder="What went through your mind? What did you tell yourself?",
                height=70, key="cbt_thought")
            cbt_emotions = st.text_input("Emotions felt", placeholder="e.g. Anxiety, Shame, Anger",
                                          key="cbt_emotions")
            cbt_intensity = st.slider("Emotion Intensity (%)", 0, 100, 50, key="cbt_intensity")
            cbt_distortions = st.multiselect("Cognitive Distortions Identified",
                                              CBT_DISTORTIONS, key="cbt_distortions")

        with col2:
            cbt_evidence_for = st.text_area("Evidence FOR this thought",
                placeholder="What facts support this thought? (Be honest)",
                height=80, key="cbt_ev_for")
            cbt_evidence_against = st.text_area("Evidence AGAINST this thought",
                placeholder="What facts contradict this thought?",
                height=80, key="cbt_ev_against")
            cbt_balanced = st.text_area("My Balanced Thought (after reflection)",
                placeholder="A more realistic, balanced way of seeing this",
                height=80, key="cbt_balanced")
            cbt_outcome_emotion = st.text_input("Outcome Emotion", key="cbt_outcome_emotion")
            cbt_outcome_intensity = st.slider("Outcome Intensity (%)", 0, 100, 30, key="cbt_outcome_int")

            get_ai_cbt = st.checkbox("🤖 Get Claude's CBT Feedback", value=True)

        if st.button("💾 Save Thought Record", type="primary", use_container_width=True):
            if cbt_situation and cbt_thought:
                ai_feedback = ""
                if get_ai_cbt:
                    with st.spinner("Getting CBT feedback from Claude..."):
                        ai_feedback = _get_cbt_feedback(
                            cbt_situation, cbt_thought,
                            ", ".join(cbt_distortions),
                            cbt_evidence_for, cbt_evidence_against
                        )

                _save_thought_record({
                    "user_id": _get_user_id(),
                    "record_date": cbt_date.isoformat(),
                    "situation": cbt_situation,
                    "automatic_thought": cbt_thought,
                    "emotions": cbt_emotions,
                    "emotion_intensity": cbt_intensity,
                    "cognitive_distortions": json.dumps(cbt_distortions),
                    "evidence_for": cbt_evidence_for,
                    "evidence_against": cbt_evidence_against,
                    "balanced_thought": cbt_balanced,
                    "outcome_emotion": cbt_outcome_emotion,
                    "outcome_intensity": cbt_outcome_intensity,
                    "ai_feedback": ai_feedback
                })
                st.success("✅ Thought record saved!")
                if ai_feedback:
                    with st.expander("🤖 Claude's CBT Feedback", expanded=True):
                        st.markdown(ai_feedback)
                st.rerun()
            else:
                st.warning("Please fill in the situation and automatic thought.")

    with sub_cbt[1]:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM hh_thought_records WHERE user_id={PH} ORDER BY record_date DESC LIMIT 20",
                    (_get_user_id(),))
        rows = cur.fetchall()
        cols_tr = [d[0] for d in cur.description]
        conn.close()
        records = [dict(zip(cols_tr, r)) for r in rows]

        if not records:
            st.info("No thought records yet. Create your first one in the 'New Record' tab.")
        else:
            for r in records:
                with st.expander(f"📅 {r.get('record_date','')[:10]} — {r.get('automatic_thought','')[:60]}..."):
                    st.markdown(f"**Situation:** {r.get('situation','')}")
                    st.markdown(f"**Thought:** {r.get('automatic_thought','')}")
                    st.markdown(f"**Emotions:** {r.get('emotions','')} ({r.get('emotion_intensity',0)}% → {r.get('outcome_intensity',0)}%)")
                    try:
                        distortions = json.loads(r.get("cognitive_distortions") or "[]")
                        if distortions:
                            st.markdown(f"**Distortions:** {', '.join(distortions)}")
                    except Exception:
                        pass
                    if r.get("balanced_thought"):
                        st.markdown(f"**Balanced Thought:** {r['balanced_thought']}")
                    if r.get("ai_feedback"):
                        st.markdown("**🤖 Claude's Feedback:**")
                        st.markdown(r["ai_feedback"])

# ── TAB 9: Family View ────────────────────────────────────────────────────────
with tabs[9]:
    st.subheader("👨‍👩‍👧 Family Wellness Dashboard")
    st.info("🔒 Only entries you marked as 'Family Can See' or 'Full Family Dashboard' are shown here. This page can be shared with family members to provide reassurance and early awareness — especially important after your recent manic episode.")

    family_checkins = []
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT checkin_date, mood_score, energy_score, anxiety_score, sleep_hours,
               overall_day_score, family_note, primary_emotion, family_visible
        FROM hh_daily_checkin
        WHERE user_id={PH} AND family_visible > 0
        ORDER BY checkin_date DESC LIMIT 30
    """, (_get_user_id(),))
    rows = cur.fetchall()
    cols_f = [d[0] for d in cur.description]
    conn.close()
    family_checkins = [dict(zip(cols_f, r)) for r in rows]

    if not family_checkins:
        st.warning("No shared check-ins yet. When logging a check-in, set sharing to 'Family Can See' to allow family members to see your wellness summary here.")
    else:
        st.markdown("#### 📊 Recent Wellness Summary (Shared with Family)")
        for ci in family_checkins[:14]:
            mood = ci.get("mood_score", 3)
            mood_label = MOOD_SCALE.get(mood, "")
            mood_icon = "🟢" if 3 <= mood <= 5 else ("🟡" if mood >= 6 else "🔵")
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 1, 2])
                col1.markdown(f"**{str(ci.get('checkin_date',''))[:10]}**")
                col2.markdown(f"{mood_icon} {mood_label}")
                col3.markdown(ci.get("family_note") or f"Feeling: {ci.get('primary_emotion','')}")

        st.divider()
        st.markdown("#### 🚨 Family Alert System")
        st.caption("Flags are shown when mood patterns suggest an episode may be developing.")
        all_recent = _load_checkins(7)
        flags = _check_for_episode_flags(all_recent)
        if not flags:
            st.success("✅ **All Clear** — Wellness patterns are in a stable range over the last 7 days.")
        else:
            for f_title, f_msg, f_type in flags:
                if f_type == "warning":
                    st.warning(f"**{f_title}** — {f_msg}")
                else:
                    st.error(f"🚨 **{f_title}** — {f_msg}")

        st.divider()
        st.markdown("""
#### 💬 For Family Members
- **Green range (Mood 3-5):** Stable. Darrian is doing well.
- **Yellow (Mood 6-7):** Elevated mood. Gently check in. Don't create conflict. Suggest sleep, calming activities.
- **Blue (Mood 1-2):** Low mood. Offer support, not advice. Show up, be present.
- **What helps most:** Consistency, low-stimulation environment, reminders about medications, and calm reassurance.
- **When to be concerned:** 3+ consecutive days at mood 6-7 with reduced sleep, high spending, or grandiose plans.
""")

# ── TAB 10: Goals ─────────────────────────────────────────────────────────────
with tabs[10]:
    st.subheader("🎯 Health Goals")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### ➕ Add Health Goal")
        with st.form("goal_form", clear_on_submit=True):
            g_pillar = st.selectbox("Pillar", ["🧠 Mental", "💚 Emotional", "💪 Physical", "🙏 Spiritual"])
            g_goal = st.text_area("Goal", height=80,
                placeholder="e.g. 'Log a daily check-in every day for 30 days'")
            g_target = st.date_input("Target Date")
            g_notes = st.text_area("Notes / Strategy", height=60)
            if st.form_submit_button("💾 Save Goal", type="primary"):
                if g_goal:
                    _save_goal(g_pillar, g_goal, g_target.isoformat(), g_notes)
                    st.success("Goal saved!")
                    st.rerun()

    with col2:
        st.markdown("#### 🎯 Active Goals")
        goals = _load_goals()
        if not goals:
            st.info("No goals set yet. Add your first health goal!")
        else:
            by_pillar = {}
            for g in goals:
                p = g.get("pillar", "Other")
                by_pillar.setdefault(p, []).append(g)

            for pillar, pillar_goals in by_pillar.items():
                st.markdown(f"**{pillar}**")
                for g in pillar_goals:
                    with st.container(border=True):
                        col_a, col_b = st.columns([3, 1])
                        col_a.markdown(g["goal"])
                        col_a.caption(f"Target: {str(g.get('target_date',''))[:10]} | Progress: {g.get('progress',0)}%")
                        st.progress(int(g.get("progress", 0)) / 100)
                        if g.get("notes"):
                            col_a.caption(f"📝 {g['notes']}")

                        with col_b:
                            new_progress = st.number_input("% Done", 0, 100,
                                int(g.get("progress", 0)), key=f"goal_progress_{g['id']}")
                            if st.button("Update", key=f"goal_update_{g['id']}"):
                                conn = get_conn()
                                conn.execute(f"UPDATE hh_health_goals SET progress={PH} WHERE id={PH}",
                                             (new_progress, g["id"]))
                                conn.commit()
                                conn.close()
                                st.rerun()
                            if st.button("✅ Done", key=f"goal_done_{g['id']}"):
                                conn = get_conn()
                                conn.execute(f"UPDATE hh_health_goals SET completed=1, progress=100 WHERE id={PH}",
                                             (g["id"],))
                                conn.commit()
                                conn.close()
                                st.success("Goal completed! 🎉")
                                st.rerun()
