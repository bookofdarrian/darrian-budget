"""
Wise Mind Daily — Page 151
Your personal DBT practice tracker, grounding toolkit, and daily mental wellness OS.
Inspired by: DBT Skills Training (Marsha M. Linehan), One Piece / Eiichiro Oda,
Malcolm X, Assata Shakur, Bobby Seale, Huey P Newton, Marcus Garvey, WEB DuBois,
Ubuntu Philosophy, J Cole, Kendrick Lamar, Brent Faiyaz, JID.
Built for Darrian Belcher — March 2026, post-voluntary hospitalization.
"I am because we are." — Ubuntu
"I don't want to conquer anything. I just think the guy with the most freedom
in the whole ocean is the Pirate King!" — Monkey D. Luffy
"""
import streamlit as st

st.set_page_config(
    page_title="🌊 Wise Mind Daily — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)

import os
import sys
import json
import random
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                                   label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                         label="Todo",               icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",            label="Creator",            icon="🎬")
st.sidebar.page_link("pages/25_notes.py",                        label="Notes",              icon="📝")
st.sidebar.page_link("pages/26_media_library.py",                label="Media Library",      icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",           label="Personal Assistant", icon="🤖")
st.sidebar.page_link("pages/147_proactive_ai_engine.py",         label="Proactive AI",       icon="🧠")
st.sidebar.page_link("pages/144_holistic_health_dashboard.py",   label="Holistic Health",    icon="🌿")
st.sidebar.page_link("pages/151_wise_mind_daily.py",             label="Wise Mind Daily",    icon="🌊")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────
PH   = "%s" if USE_POSTGRES else "?"
AUTO = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

# Darrian's Strengths (self-identified in therapy, March 2026)
DARRIAN_STRENGTHS = [
    ("🧠 Intellect", "You think deeply. Your verbal comprehension is in the 70th percentile. You explain complex things simply — that's rare."),
    ("🔍 Curiosity", "You ask the questions other people are afraid to ask. Curiosity is the engine of every great thing you've built."),
    ("⚙️ Problem Solving", "You troubleshoot systems, people, and processes with a natural eye for root causes."),
    ("🎯 Hyper-Focus", "When you lock in, you lock IN. ADHD is not your enemy — it's your superpower in flow state."),
    ("🔥 Hunger / Drive", "You got yourself into Visa, Georgia Tech, and built 150+ pages of software from scratch. The hunger never lies."),
    ("🤝 Interpersonal Skills", "Your empathy is real. 81st percentile agreeableness. People feel seen around you."),
    ("📡 Technical Communication", "You can explain cloud infra to your grandmother and a PhD to a kid. That bridges worlds."),
    ("🏃 Athletic", "Your body is built. Use it. 5x/week is the goal and you know why."),
    ("🌍 Community Outreach", "You have a gift for bringing people together. The Sikh kitchen vision is real."),
    ("✍️ Writing & Ideation", "The 10 pages you wrote in that facility in 5 days? That's your mind doing what it does."),
    ("🔄 Adaptability", "You've adapted to more change than most people will face in a lifetime. You're still here."),
    ("💎 Beautiful Brown Skin", "Walk in that. No apology, no code-switching needed."),
]

# Darrian's Weaknesses (self-identified — not flaws, growth edges)
DARRIAN_GROWTH_EDGES = [
    ("⏱️ Time Management / Time Blindness", "ADHD PSI at 5th percentile. This is neurological, not character. Systems, alarms, and Pomodoro help."),
    ("🌀 Tunnel Vision", "When you're hyper-focused, peripheral things get missed. One-Mindfully is your counter-skill."),
    ("🗣️ Overtalking", "Your energy runs fast when ideas are firing. Pause, breathe, ask a question instead."),
    ("💭 Negative Self-Talk", "The inner critic is loud. It's lying. When it fires, label it: 'There goes the distortion again.'"),
    ("😔 Lack of Confidence (situational)", "Confidence follows action, not the other way. Ship it. Confidence comes after."),
    ("🧮 Nervous System Regulation", "Your nervous system needs training like your body needs the gym. DBT + cold + breath are your weights."),
    ("🤝 Varying Motivation", "Mood-dependent motivation is Mood-Related/ADHD reality. Build systems that don't require motivation."),
    ("💔 Can Be Overly Hurt (Virgo energy)", "You feel deeply. That's a strength AND an edge. Let yourself feel it. Don't bottle. Don't explode."),
]

# ── Medications & Care (from Tanner Willowbrooke discharge 3/27/2026) ──────────
DARRIAN_MEDS = [
    {
        "name": "OLANZapine (Zyprexa)",
        "dose": "10 mg tablet",
        "schedule": "NIGHT",
        "schedule_detail": "Take 1 tablet (10 mg) by mouth every night.",
        "for": "Mood-Related disorder / mood stabilization",
        "start_date": "March 26, 2026",
        "color": "#7c3aed",
        "icon": "🟣",
        "warnings": [
            "May cause dizziness — stand up slowly",
            "Avoid alcohol and marijuana",
            "May raise blood sugar — check regularly",
            "Don't drive until you know how it affects you",
            "May cause weight gain — track food",
        ],
    },
    {
        "name": "OXcarbazepine (Trileptal)",
        "dose": "150 mg tablet × 2",
        "schedule": "AM + PM",
        "schedule_detail": "Take 1 tablet (150 mg) in the MORNING and 1 tablet (150 mg) in the EVENING.",
        "for": "Mood stabilization / seizure prevention",
        "start_date": "March 27, 2026",
        "color": "#0ea5e9",
        "icon": "🔵",
        "warnings": [
            "DO NOT stop suddenly — increases seizure risk",
            "Birth control pills may not work while on this",
            "Watch for mood changes or thoughts of suicide",
            "Don't drive until you know how it affects you",
        ],
    },
    {
        "name": "atomoxetine (Strattera)",
        "dose": "40 mg capsule",
        "schedule": "DAILY",
        "schedule_detail": "Take 1 capsule (40 mg) once daily. Starting March 28, 2026.",
        "for": "ADHD management",
        "start_date": "March 28, 2026",
        "color": "#f59e0b",
        "icon": "🟡",
        "warnings": [
            "Swallow capsule WHOLE — DO NOT open (eye irritant)",
            "Take at the same time each day",
        ],
    },
    {
        "name": "mirtazapine (Remeron)",
        "dose": "15 mg tablet",
        "schedule": "NIGHT",
        "schedule_detail": "Take 1 tablet (15 mg) by mouth every night.",
        "for": "Depression / sleep support",
        "start_date": "March 26, 2026",
        "color": "#10b981",
        "icon": "🟢",
        "warnings": [
            "Take at the same time each night",
            "May cause drowsiness — good for sleep, careful in AM",
        ],
    },
]

DARRIAN_STOPPED_MEDS = [
    {"name": "QUEtiapine (Seroquel)", "dose": "200 mg", "reason": "Discontinued at discharge 3/27/2026 — DO NOT TAKE"},
]

DARRIAN_APPOINTMENTS = [
    {
        "title": "Beal Wellness",
        "type": "Mental Health Follow-Up",
        "date_str": "3/31/2026",
        "date_obj": date(2026, 3, 31),
        "time": "10:30 AM",
        "address": "1093 Cleveland Ave, Atlanta, GA 30334",
        "phone": "404-768-2218",
        "fax": "404-768-2138",
        "notes": "First follow-up post-discharge. Bring medication list. CRITICAL — do not miss.",
        "urgent": True,
    },
]

DARRIAN_PHARMACY = {
    "name": "CVS/pharmacy #4178",
    "address": "895 Ralph Abernathy Blvd SW, Atlanta, GA 30310",
    "phone": "404-755-1511",
    "pickup_list": ["atomoxetine (Strattera) 40 mg", "mirtazapine (Remeron) 15 mg",
                    "OLANZapine (Zyprexa) 10 mg", "OXcarbazepine (Trileptal) 150 mg"],
}

DARRIAN_MYCHART = {
    "url": "https://www.tannermychart.org/MyChart/",
    "activation_code": "SB3FK-4FC3Q-NSTVF",
    "expires": "4/22/2026",
    "mrn": "3913971",
}

# Georgia Crisis Lines (from discharge resources)
GEORGIA_CRISIS_LINES = [
    ("988 Suicide & Crisis Lifeline", "Call or text 988", "24/7"),
    ("Crisis Text Line", "Text HOME to 741741", "24/7"),
    ("GCAL — Georgia Crisis & Access Line", "1-800-715-4225", "24/7 — mygcal.com"),
    ("Tanner Willowbrooke Psychiatry", "770-812-3266", "Your treatment team"),
    ("CARES Warm Line (recovery support)", "1-844-326-5400", "Call/Text 8:30AM–11PM daily"),
    ("Peer2Peer Warm Line", "888-945-1414", "24/7 peer support"),
    ("NAMI Georgia", "www.nami.org", "Free online resources"),
]

# Revolutionary Figures + Inspirational Figures (from Darrian's handwritten list)
FIRE_QUOTES = [
    # Malcolm X
    ("Malcolm X", "A man who stands for nothing will fall for anything."),
    ("Malcolm X", "Education is the passport to the future, for tomorrow belongs to those who prepare for it today."),
    ("Malcolm X", "We didn't land on Plymouth Rock. Plymouth Rock landed on us."),
    ("Malcolm X", "If you have no critics you'll likely have no success."),
    # Assata Shakur
    ("Assata Shakur", "Nobody in the world, nobody in history, has ever gotten their freedom by appealing to the moral sense of the people who were oppressing them."),
    ("Assata Shakur", "It is our duty to fight for our freedom. It is our duty to win. We must love each other and support each other. We have nothing to lose but our chains."),
    ("Assata Shakur", "I am a Black revolutionary woman. Deal with it."),
    # Huey P Newton
    ("Huey P Newton", "You can jail a revolutionary, but you can't jail the revolution."),
    ("Huey P Newton", "Any unarmed people are slaves, or are subject to slavery at any given moment."),
    ("Huey P Newton", "Power is the ability to define phenomena, and make it act in a desired manner."),
    # Bobby Seale
    ("Bobby Seale", "You fight racism with solidarity. We don't fight racism with racism."),
    ("Bobby Seale", "Power to the people. All power to all the people."),
    # Marcus Garvey
    ("Marcus Garvey", "Up, you mighty race. You can accomplish what you will."),
    ("Marcus Garvey", "A people without the knowledge of their past history, origin, and culture is like a tree without roots."),
    # WEB DuBois
    ("W.E.B. DuBois", "Either America will destroy ignorance or ignorance will destroy the United States."),
    ("W.E.B. DuBois", "The cost of liberty is less than the price of repression."),
    # Ubuntu
    ("Ubuntu Philosophy", "I am because we are. (Umuntu ngumuntu ngabantu)"),
    ("Ubuntu Philosophy", "A person is a person through other persons."),
    # One Piece / Luffy
    ("Monkey D. Luffy (One Piece)", "I don't want to conquer anything. I just think the guy with the most freedom in the whole ocean is the Pirate King!"),
    ("Monkey D. Luffy (One Piece)", "Power isn't determined by your size, but the size of your heart and dreams."),
    ("Monkey D. Luffy (One Piece)", "If you don't take risks, you can't create a future!"),
    ("Monkey D. Luffy (One Piece)", "Forgetting is like a wound. The wound may heal, but it has already left a scar."),
    ("Roronoa Zoro (One Piece)", "Nothing happened. (scar from fighting Mihawk — survived it anyway)"),
    ("Eiichiro Oda", "What keeps me going is not the readers or the anime — it's the fact that the story still has so much to tell."),
    # J Cole / Kendrick / artists
    ("J Cole", "One thing about a winner, they always want the ball."),
    ("J Cole", "There's beauty in the struggle, ugliness in the success."),
    ("Kendrick Lamar", "Be humble. Sit down."),
    ("Kendrick Lamar", "I got a bird's eye view — I can see everything moving."),
    ("Brent Faiyaz", "The only way out is through."),
    ("Donald Glover", "The most disrespected thing in America is the Black imagination."),
    ("Viola Davis", "You cannot win an Emmy for roles that aren't written."),
    # DBT-inspired
    ("Marsha Linehan (DBT)", "You have to accept reality as it is — then you can change it."),
    ("Marsha Linehan (DBT)", "Radical acceptance is not approval. It's acknowledging what is."),
    # Darrian's own words from therapy
    ("Darrian Belcher (3/26/26)", "Mindfulness is so key. Every time I feel mania, check yourself in if you need to."),
    ("Darrian Belcher (3/26/26)", "Just having a tool is not useful. You need to know how to use it."),
    ("Darrian Belcher (3/26/26)", "Taking your mind off present rumination and putting your mind on your physical self — your body will feel it before your brain registers it."),
]

# DBT Skills Reference
DBT_WHAT_SKILLS = ["Observe", "Describe", "Participate", "Wordless Watching", "Dropping Into Pauses"]
DBT_HOW_SKILLS  = ["Nonjudgmentally", "One-Mindfully", "Effectively"]
DBT_IMPROVE     = ["Imagery", "Meaning", "Prayer/Meditation", "Relaxation", "One Thing in the Moment",
                   "Vacation (brief)", "Self-Encouragement", "Rethink the Situation"]
DBT_TIPP        = ["Temperature (cold water/ice)", "Intense Exercise", "Paced Breathing", "Paired Muscle Relaxation"]
DBT_STOP        = ["Stop", "Take a breath", "Observe what's happening", "Proceed mindfully"]
DBT_WISE_MIND   = ["Stone on the Lake", "Walking the Spiral Staircase", "Breathing 'Wise In / Mind Out'",
                   "Asking Wise Mind a Question", "Dropping Into the Pause"]
COPING_POSITIVE = ["Walk / Run", "Gym", "Breathing exercises", "Meditation / Off-grid time", "Cycling",
                   "Stretching / Yoga", "Sleeping (restorative)", "Eating well", "Gaming (brief)",
                   "Talking with family", "Cold shower / ice", "Journaling / Writing", "Coding",
                   "Making tea or coffee", "Reading", "Music", "Basketball",
                   # From the coping wheel (Tanner Willowbrooke, March 2026)
                   "Word search / Crossword puzzle", "Paint or draw", "Write a short story or song",
                   "Cook or bake with family", "Dance", "Play a board game", "Volunteer your time",
                   "Watch a favorite movie", "Rearrange or clean your room", "Deep breathing",
                   "Face your problem (Opposite Action)", "Spend time with family", "Go for a hike",
                   "Listen to calming music", "Use positive self-talk", "Eat a healthy meal",
                   "Stretching / yoga", "Make something (art, jewelry, music)", "Ask for a hug"]
COPING_NEGATIVE = ["Smoking weed", "Alcohol", "Not eating properly", "Not sleeping enough",
                   "Isolating (long-term)", "Yelling", "Talking too fast", "Blocking the trigger (avoidance)",
                   "Doom scrolling", "Impulsive spending"]
MIND_STATES = ["🔥 Emotion Mind (ruled by feelings — hot, mood-dependent)",
               "🧊 Reasonable Mind (ruled by logic — cool, task-focused)",
               "🌊 Wise Mind (integration — the middle path, inner wisdom)"]
EFFECTIVENESS = {1: "❌ Not effective", 2: "😐 Somewhat", 3: "✅ Effective", 4: "🔥 Very effective", 5: "⚡ Transformative"}

# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()

    # Daily Wise Mind state check-in
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS wm_state_log (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            log_date        DATE NOT NULL,
            log_time        TEXT,
            mind_state      TEXT,
            mind_score      INTEGER,
            emotion_present TEXT,
            body_sensation  TEXT,
            one_mindfully   TEXT,
            notes           TEXT,
            wise_mind_tool  TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # DBT skills practice log
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS wm_skill_log (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            log_date        DATE NOT NULL,
            skill_category  TEXT NOT NULL,
            skill_name      TEXT NOT NULL,
            situation       TEXT,
            effectiveness   INTEGER,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Coping skills tracker
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS wm_coping_log (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            log_date        DATE NOT NULL,
            coping_type     TEXT NOT NULL,
            skills_used     TEXT,
            trigger         TEXT,
            outcome         TEXT,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Trigger + coping plan log
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS wm_trigger_log (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            log_date        DATE NOT NULL,
            trigger_event   TEXT,
            emotion_before  TEXT,
            intensity_before INTEGER,
            action_taken    TEXT,
            dbt_skill_used  TEXT,
            emotion_after   TEXT,
            intensity_after INTEGER,
            lesson          TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ubuntu / Community reflection
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS wm_ubuntu_log (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            log_date        DATE NOT NULL,
            gave_to_who     TEXT,
            what_i_gave     TEXT,
            what_i_received TEXT,
            community_vision TEXT,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Medication adherence log
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS wm_med_log (
            id              {AUTO},
            user_id         INTEGER NOT NULL DEFAULT 1,
            log_date        DATE NOT NULL,
            med_name        TEXT NOT NULL,
            taken           INTEGER DEFAULT 0,
            time_taken      TEXT,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

_ensure_tables()


# ── Helper Functions ───────────────────────────────────────────────────────────
def _uid():
    return st.session_state.get("user_id", 1)

def _today_state():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        f"SELECT * FROM wm_state_log WHERE user_id={PH} AND log_date={PH} ORDER BY created_at DESC LIMIT 1",
        (_uid(), date.today().isoformat())
    )
    row  = cur.fetchone()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return dict(zip(cols, row)) if row else None

def _skill_logs(days=30):
    conn = get_conn()
    cur  = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(
        f"SELECT * FROM wm_skill_log WHERE user_id={PH} AND log_date>={PH} ORDER BY log_date DESC, created_at DESC",
        (_uid(), since)
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _coping_logs(days=30):
    conn = get_conn()
    cur  = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(
        f"SELECT * FROM wm_coping_log WHERE user_id={PH} AND log_date>={PH} ORDER BY log_date DESC",
        (_uid(), since)
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _trigger_logs(days=30):
    conn = get_conn()
    cur  = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(
        f"SELECT * FROM wm_trigger_log WHERE user_id={PH} AND log_date>={PH} ORDER BY log_date DESC",
        (_uid(), since)
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _ubuntu_logs(days=30):
    conn = get_conn()
    cur  = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(
        f"SELECT * FROM wm_ubuntu_log WHERE user_id={PH} AND log_date>={PH} ORDER BY log_date DESC",
        (_uid(), since)
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _get_wise_mind_coaching(mind_state, emotion, body, one_thing, notes):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No API key. Add one in Settings to get personalized coaching."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            system="""You are Darrian Belcher's DBT-informed mental wellness coach. Darrian is a 22-year-old Black man,
ADHD-inattentive, Mood-Related, Generalized Anxiety. He recently completed 5 days in a voluntary mental health facility
where he engaged deeply with DBT skills. He is inspired by Malcolm X, Assata Shakur, Bobby Seale, Huey P Newton,
Ubuntu philosophy, and One Piece (Monkey D. Luffy's freedom philosophy). He is a builder — TPM at Visa, homelab owner,
entrepreneur. He is strong, self-aware, and ready to grow.

Your style:
- Speak directly, authentically — not clinical, not preachy
- Reference his actual DBT skills when relevant (Wise Mind, IMPROVE, TIPP, STOP)
- Occasional reference to his inspirational figures or One Piece when genuinely fitting
- Short, scannable, actionable — no walls of text
- NEVER minimize what he's feeling
- Always end with ONE specific action he can take in the next 5 minutes""",
            messages=[{
                "role": "user",
                "content": f"""Current check-in:
- Mind state: {mind_state}
- Emotion present: {emotion}
- Body sensation: {body}
- One thing I'm focused on right now: {one_thing}
- Notes: {notes}
- Date/time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}

Give me:
1. What this state is telling me (pattern recognition)
2. The one DBT skill most suited for RIGHT NOW
3. A 5-minute grounding action
4. A one-sentence fire to carry into the day"""
            }]
        )
        return msg.content[0].text
    except Exception as e:
        return f"❌ Coaching error: {e}"


# ── PAGE HEADER ────────────────────────────────────────────────────────────────
# Daily fire quote — new one each day (seeded by date so it's stable for the day)
random.seed(int(date.today().strftime("%Y%m%d")))
daily_quote = random.choice(FIRE_QUOTES)

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
    border-left: 4px solid #4ade80;
    padding: 20px 24px;
    border-radius: 12px;
    margin-bottom: 16px;
">
    <h1 style="color: #4ade80; margin: 0 0 8px 0; font-size: 1.8rem;">🌊 Wise Mind Daily</h1>
    <p style="color: #94a3b8; margin: 0 0 12px 0; font-size: 0.9rem;">DBT Practice · Grounding · Strengths · Community · The Will of D</p>
    <p style="color: #e2e8f0; font-style: italic; margin: 0; font-size: 1rem;">
        "<span style="color:#fbbf24;">{daily_quote[1]}</span>"
    </p>
    <p style="color: #64748b; margin: 4px 0 0 0; font-size: 0.85rem;">— {daily_quote[0]}</p>
</div>
""", unsafe_allow_html=True)

# Today's quick summary bar
today_state = _today_state()
if today_state:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today's Mind State", today_state.get("mind_state", "—")[:20] if today_state.get("mind_state") else "—")
    col2.metric("Wise Mind Score", f"{today_state.get('mind_score', '—')}/5")
    col3.metric("One-Mindfully Focus", today_state.get("one_mindfully", "—")[:25] if today_state.get("one_mindfully") else "—")
    col4.metric("Wise Mind Tool Used", today_state.get("wise_mind_tool", "—")[:25] if today_state.get("wise_mind_tool") else "—")
else:
    st.info("🌅 No check-in logged today. Start with **Today's State** below — takes 2 minutes.")

# ── Appointment Alert Banner ───────────────────────────────────────────────────
_today = date.today()
for appt in DARRIAN_APPOINTMENTS:
    days_until = (appt["date_obj"] - _today).days
    if 0 <= days_until <= 7:
        if days_until == 0:
            badge = "🚨 TODAY"
            color = "#ef4444"
        elif days_until == 1:
            badge = "⚠️ TOMORROW"
            color = "#f59e0b"
        else:
            badge = f"📅 IN {days_until} DAYS"
            color = "#3b82f6"
        st.markdown(f"""
<div style="background: #1a0a00; border: 2px solid {color}; border-radius: 10px; padding: 14px 18px; margin: 8px 0;">
<span style="color:{color}; font-weight:bold; font-size:1rem;">{badge} — {appt['title']}</span>
<span style="color:#94a3b8; font-size:0.9rem; margin-left:12px;">{appt['type']}</span><br>
<span style="color:#e2e8f0; font-size:1rem; font-weight:bold;">🕙 {appt['time']} on {appt['date_str']}</span>
<span style="color:#64748b; font-size:0.85rem; margin-left:12px;">📍 {appt['address']}  📞 {appt['phone']}</span><br>
<span style="color:#fbbf24; font-size:0.85rem;">💡 {appt['notes']}</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── TABS ───────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🧘 Today's State",
    "🛠️ DBT Skills",
    "⚡ Triggers & Plan",
    "💪 Strengths Mirror",
    "🌍 Ubuntu",
    "⛵ The Will of D",
    "📊 Trends",
    "💊 Meds & Care",
])


# ══════════════════════════════════════════════════════════════════════
# TAB 0: TODAY'S STATE — Wise Mind check-in
# ══════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("🧘 Today's Wise Mind State Check")
    st.caption(date.today().strftime("%A, %B %d, %Y"))

    if today_state:
        st.success("✅ You've checked in today. Log another if your state has shifted.")
        with st.expander("View today's entry"):
            st.write(today_state)

    col_l, col_r = st.columns([1, 1])

    with col_l:
        with st.form("wise_mind_checkin"):
            st.markdown("#### Which state am I in right now?")
            st.markdown("""
| 🔥 Emotion Mind | 🧊 Reasonable Mind | 🌊 Wise Mind |
|---|---|---|
| Feelings rule. Hot, reactive. | Logic rules. Cold, task-focused. | The middle path. Inner wisdom. |
""")
            mind_state = st.radio(
                "Current state:",
                MIND_STATES,
                index=2,
                label_visibility="collapsed"
            )
            mind_score = st.slider("How centered in Wise Mind am I? (1=not at all, 5=fully centered)", 1, 5, 3)

            st.markdown("---")
            emotion_present = st.text_input(
                "What emotion is present right now?",
                placeholder="e.g. Frustration, calm, anxiety, hopeful, overwhelmed..."
            )
            body_sensation = st.text_input(
                "What does my body feel?",
                placeholder="e.g. Tight chest, heavy shoulders, calm belly, restless legs..."
            )
            one_mindfully = st.text_input(
                "🎯 ONE THING to focus on right now (One-Mindfully):",
                placeholder="e.g. 'Finish the morning report' or 'Just breathe for 5 minutes'"
            )
            wise_mind_tool = st.selectbox(
                "Wise Mind tool I'll use today:",
                ["(pick one)"] + DBT_WISE_MIND
            )
            notes = st.text_area("Any notes / what's on my mind?", height=80, placeholder="Raw. Honest. No judgment.")

            get_coaching = st.checkbox("🤖 Get AI coaching on this state", value=True)

            submitted = st.form_submit_button("💾 Log My State", type="primary", use_container_width=True)
            if submitted:
                conn = get_conn()
                db_exec(conn, f"""
                    INSERT INTO wm_state_log
                        (user_id, log_date, log_time, mind_state, mind_score, emotion_present,
                         body_sensation, one_mindfully, notes, wise_mind_tool)
                    VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                """, (
                    _uid(), date.today().isoformat(),
                    datetime.now().strftime("%H:%M"),
                    mind_state, mind_score, emotion_present,
                    body_sensation, one_mindfully, notes,
                    wise_mind_tool if wise_mind_tool != "(pick one)" else ""
                ))
                conn.commit()
                conn.close()
                st.success("✅ State logged!")

                if get_coaching and (emotion_present or notes):
                    with st.spinner("🤖 Getting coaching..."):
                        coaching = _get_wise_mind_coaching(mind_state, emotion_present, body_sensation, one_mindfully, notes)
                    st.markdown("---")
                    st.markdown("### 🤖 Wise Mind Coaching")
                    st.markdown(coaching)
                st.rerun()

    with col_r:
        st.markdown("### 🌀 Grounding Toolkit")
        st.caption("Use these when you're in Emotion Mind and need to come back.")

        with st.expander("🪨 Stone on the Lake (Wise Mind)"):
            st.markdown("""
1. Imagine a clear blue lake on a beautiful sunny day
2. You are a small flake of stone — flat, light
3. You've been tossed onto the lake and are **gently floating down** through calm, clear water
4. Slowly drifting toward the smooth, sandy bottom
5. Notice what you see, what you feel as you float down
6. As you reach the center of yourself, **settle your attention there**
7. Notice the serenity. Notice the quiet deep within.

*This is Wise Mind. It's always there. You just go down to find it.*
""")

        with st.expander("🌀 Walking the Spiral Staircase"):
            st.markdown("""
1. Imagine that within you is a spiral staircase winding down to your very center
2. Starting at the top, **walk very slowly downward** — deeper and deeper within yourself
3. Notice sensations. Rest on a step. Turn on lights as you go.
4. Do not force yourself further than you want to go
5. Notice the quiet
6. As you reach the center of yourself, **settle there — in your gut or abdomen**

*This is the walk Darrian wrote about in the facility. It calms the nervous system.*
""")

        with st.expander("🌬️ Breathing 'Wise In / Mind Out'"):
            st.markdown("""
1. Breathe in slowly — say to yourself: **"Wise"**
2. Breathe out slowly — say to yourself: **"Mind"**
3. Focus your entire attention on the word "Wise" on the inhale
4. Focus your entire attention on the word "Mind" on the exhale
5. Continue until you sense you've settled into Wise Mind
6. If a thought comes — observe it. Don't grab it. Let it pass.
""")

        with st.expander("🧲 5-4-3-2-1 Grounding (Panic / Dissociation)"):
            st.markdown("""
- **5** things you can **SEE** right now
- **4** things you can **TOUCH / FEEL**
- **3** things you can **HEAR**
- **2** things you can **SMELL**
- **1** thing you can **TASTE**

*Brings you back to the present moment. Works in under 2 minutes.*
""")

        with st.expander("⚡ TIPP — When Emotions Are OFF THE CHARTS"):
            st.markdown("""
**T — Temperature:** Splash cold water on your face. Hold ice. Cold shower.
Activates the dive reflex → slows heart rate fast.

**I — Intense Exercise:** 20 jumping jacks. Sprint in place for 60 seconds.
Burns off the adrenaline your body released.

**P — Paced Breathing:** Exhale longer than inhale. Try 4 in, 8 out.
Activates parasympathetic nervous system (calm mode).

**P — Paired Muscle Relaxation:** Tense muscle group → hold 5 sec → release.
Teaches the body the difference between tense and relaxed.
""")

        with st.expander("🛑 STOP Skill"):
            st.markdown("""
**S — Stop.** Don't react yet. Freeze.
**T — Take a breath.** One deep breath. Nose in, mouth out.
**O — Observe.** What am I feeling? What's actually happening?
**P — Proceed mindfully.** Now move — from Wise Mind, not Emotion Mind.
""")


# ══════════════════════════════════════════════════════════════════════
# TAB 1: DBT SKILLS — Log which skills you practiced today
# ══════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("🛠️ DBT Skills Practice Log")
    st.caption("Track which skills you actually used. Consistency builds the muscle.")

    col_form, col_ref = st.columns([1, 1])

    with col_form:
        st.markdown("#### Log a Skill Practice")
        with st.form("skill_log_form", clear_on_submit=True):
            skill_date = st.date_input("Date", value=date.today())
            skill_category = st.selectbox("Skill Category", [
                "Mindfulness — WHAT skills",
                "Mindfulness — HOW skills",
                "Mindfulness — Wise Mind",
                "Distress Tolerance — IMPROVE",
                "Distress Tolerance — TIPP",
                "Distress Tolerance — STOP",
                "Distress Tolerance — Sensory Awareness",
                "Emotion Regulation — PLEASE",
                "Emotion Regulation — Opposite Action",
                "Interpersonal Effectiveness — DEAR MAN",
                "Walking the Middle Path",
                "Other"
            ])

            # Dynamic skill options based on category
            skill_options_map = {
                "Mindfulness — WHAT skills": DBT_WHAT_SKILLS,
                "Mindfulness — HOW skills": DBT_HOW_SKILLS,
                "Mindfulness — Wise Mind": DBT_WISE_MIND,
                "Distress Tolerance — IMPROVE": DBT_IMPROVE,
                "Distress Tolerance — TIPP": DBT_TIPP,
                "Distress Tolerance — STOP": DBT_STOP,
                "Distress Tolerance — Sensory Awareness": ["30-question sensory scan", "Body scan", "Custom"],
                "Emotion Regulation — PLEASE": ["Physical illness treatment", "Eating balanced", "Avoid mood-altering substances", "Sleep hygiene", "Exercise"],
                "Emotion Regulation — Opposite Action": ["Acted opposite to fear", "Acted opposite to shame", "Acted opposite to anger", "Acted opposite to sadness"],
                "Interpersonal Effectiveness — DEAR MAN": ["Describe", "Express", "Assert", "Reinforce", "Mindful", "Appear confident", "Negotiate"],
                "Walking the Middle Path": ["Balanced reasonable/emotion mind", "Radical acceptance", "Self-denial vs self-indulgence"],
                "Other": ["Custom skill"],
            }
            skill_name_options = skill_options_map.get(skill_category, ["Custom"])
            skill_name = st.selectbox("Skill Used", skill_name_options)
            skill_situation = st.text_area("What situation triggered the need for this skill?", height=60,
                                           placeholder="Brief description — no judgment")
            effectiveness = st.select_slider("How effective was it?",
                                              options=list(EFFECTIVENESS.keys()),
                                              value=3,
                                              format_func=lambda x: EFFECTIVENESS[x])
            skill_notes = st.text_area("Notes / what I noticed:", height=60,
                                       placeholder="What worked? What didn't? What would I do differently?")

            if st.form_submit_button("💾 Log Skill", type="primary", use_container_width=True):
                conn = get_conn()
                db_exec(conn, f"""
                    INSERT INTO wm_skill_log
                        (user_id, log_date, skill_category, skill_name, situation, effectiveness, notes)
                    VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH})
                """, (_uid(), skill_date.isoformat(), skill_category, skill_name,
                      skill_situation, effectiveness, skill_notes))
                conn.commit()
                conn.close()
                st.success(f"✅ Logged: {skill_name}")
                st.rerun()

    with col_ref:
        st.markdown("#### 📚 Skills Quick Reference")

        with st.expander("🎯 IMPROVE — Distress Tolerance", expanded=True):
            st.markdown("""
**I** — **Imagery** — Imagine a safe place, or emotions draining out like water
**M** — **Meaning** — Find purpose or meaning in the painful situation
**P** — **Prayer / Meditation** — Open your heart. Turn it over.
**R** — **Relaxation** — Hot bath, deep breathing, yoga, massage
**O** — **One thing in the moment** — Focus ONLY on what you're doing right now
**V** — **Vacation (brief)** — 1-hour break from responsibility. Pull the covers up.
**E** — **Self-Encouragement** — "This too shall pass." "I will make it out of this."
""")

        with st.expander("🧘 Mindfulness WHAT + HOW"):
            st.markdown("""
**WHAT skills:**
- **Observe** — Notice without grabbing or pushing away
- **Describe** — Label what you observe in words
- **Participate** — Throw yourself into the activity fully

**HOW skills:**
- **Nonjudgmentally** — See facts, not evaluations. "Not good or bad — just what is."
- **One-Mindfully** — Do ONE thing at a time. When eating, eat. When walking, walk.
- **Effectively** — Do what works. Don't let emotion mind sacrifice wise mind goals.
""")

        with st.expander("📅 Recent Skills (Last 7 Days)"):
            recent_skills = _skill_logs(7)
            if not recent_skills:
                st.info("No skills logged yet. Practice = progress.")
            else:
                for s in recent_skills[:10]:
                    eff_label = EFFECTIVENESS.get(s.get("effectiveness", 3), "")
                    st.markdown(f"**{s.get('log_date','')}** · {s.get('skill_name','')} · {eff_label}")

    # Coping Skills Log section
    st.markdown("---")
    st.markdown("### 🎭 Coping Skills Tracker")
    st.caption("Named from your own notes: which tools did you reach for today?")

    c1, c2 = st.columns([1, 1])
    with c1:
        with st.form("coping_form", clear_on_submit=True):
            c_date = st.date_input("Date", value=date.today(), key="cope_date")
            c_type = st.radio("Coping type used:", ["✅ Positive Coping", "⚠️ Negative Coping", "Both (honest)"])
            pos_skills = st.multiselect("Positive coping skills used:", COPING_POSITIVE)
            neg_skills = st.multiselect("Negative coping skills used (be honest — no judgment):", COPING_NEGATIVE)
            c_trigger = st.text_input("What triggered the need to cope?", placeholder="Situation, feeling, person...")
            c_outcome = st.text_area("How did it go?", height=60, placeholder="What happened? What would you do differently?")

            if st.form_submit_button("💾 Log Coping", type="primary", use_container_width=True):
                all_positive = json.dumps(pos_skills)
                all_negative = json.dumps(neg_skills)
                conn = get_conn()
                db_exec(conn, f"""
                    INSERT INTO wm_coping_log
                        (user_id, log_date, coping_type, skills_used, trigger, outcome, notes)
                    VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH})
                """, (_uid(), c_date.isoformat(), c_type,
                      json.dumps({"positive": pos_skills, "negative": neg_skills}),
                      c_trigger, c_outcome, ""))
                conn.commit()
                conn.close()
                st.success("✅ Coping log saved. Awareness is the first step.")
                st.rerun()

    with c2:
        st.markdown("#### 📊 Recent Coping Patterns")
        recent_coping = _coping_logs(14)
        if recent_coping:
            pos_count = sum(1 for c in recent_coping if "Positive" in (c.get("coping_type") or ""))
            neg_count = sum(1 for c in recent_coping if "Negative" in (c.get("coping_type") or ""))
            both_count = sum(1 for c in recent_coping if "Both" in (c.get("coping_type") or ""))
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("✅ Positive", pos_count)
            col_b.metric("⚠️ Negative", neg_count)
            col_c.metric("🔄 Both", both_count)

            st.markdown("**Recent entries:**")
            for c in recent_coping[:5]:
                icon = "✅" if "Positive" in (c.get("coping_type") or "") else ("⚠️" if "Negative" in (c.get("coping_type") or "") else "🔄")
                st.markdown(f"{icon} **{c.get('log_date','')}** — {c.get('trigger','')[:50]}")
        else:
            st.info("Log your coping to see patterns. Negative coping is data, not failure.")


# ══════════════════════════════════════════════════════════════════════
# TAB 2: TRIGGERS & PLAN
# ══════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("⚡ Trigger Log & Coping Plan")
    st.caption("From your notes: Slowing down, gaming, talking with family are your core emergency plan. Let's build on that.")

    col_trig, col_plan = st.columns([1, 1])

    with col_trig:
        st.markdown("#### Log a Trigger Event")
        with st.form("trigger_form", clear_on_submit=True):
            t_date = st.date_input("Date", value=date.today(), key="trig_date")
            t_event = st.text_area("What happened? (the trigger)", height=70,
                                    placeholder="Situation, person, thought, memory, feeling...")
            t_emotion_before = st.text_input("Emotion BEFORE coping:", placeholder="e.g. Rage, panic, shame, despair")
            t_intensity_before = st.slider("Intensity before (1=mild, 10=overwhelming)", 1, 10, 7)
            t_action = st.text_area("What did I do?", height=60,
                                     placeholder="What action or skill did I use?")
            t_skill = st.selectbox("DBT skill I used:", ["(none / reacted)"] + DBT_WHAT_SKILLS + DBT_HOW_SKILLS + DBT_IMPROVE + DBT_TIPP + DBT_STOP)
            t_emotion_after = st.text_input("Emotion AFTER coping:", placeholder="e.g. Calmer, still upset, neutral")
            t_intensity_after = st.slider("Intensity after (1=mild, 10=overwhelming)", 1, 10, 5)
            t_lesson = st.text_area("What did I learn?", height=60,
                                     placeholder="What would I do differently? What worked?")

            if st.form_submit_button("💾 Log Trigger", type="primary", use_container_width=True):
                conn = get_conn()
                db_exec(conn, f"""
                    INSERT INTO wm_trigger_log
                        (user_id, log_date, trigger_event, emotion_before, intensity_before,
                         action_taken, dbt_skill_used, emotion_after, intensity_after, lesson)
                    VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
                """, (
                    _uid(), t_date.isoformat(), t_event, t_emotion_before, t_intensity_before,
                    t_action, t_skill if t_skill != "(none / reacted)" else "",
                    t_emotion_after, t_intensity_after, t_lesson
                ))
                conn.commit()
                conn.close()
                st.success("✅ Trigger logged. This is data, not failure.")
                st.rerun()

    with col_plan:
        st.markdown("#### 🆘 Your Emergency Coping Plan")
        st.markdown("""
<div style="background: #0f172a; border-radius: 10px; padding: 16px; border: 1px solid #334155;">
<h4 style="color: #4ade80; margin-top: 0;">Darrian's Core Plan (Written in the facility)</h4>

<p style="color: #cbd5e1; margin: 4px 0;"><strong style="color:#fbbf24;">Level 1 — Slow Down</strong><br>
Pause. Don't react. Take 3 deep breaths. STOP skill. Remove yourself from the room if needed.</p>

<p style="color: #cbd5e1; margin: 4px 0;"><strong style="color:#fbbf24;">Level 2 — Ground Your Body</strong><br>
Walk. Run. Gym. Cold shower. Stretch. Cycling. Basketball. Your body will feel it before your brain registers it.</p>

<p style="color: #cbd5e1; margin: 4px 0;"><strong style="color:#fbbf24;">Level 3 — Connect</strong><br>
Talk with family. Call someone real. Not social media — a real human voice.</p>

<p style="color: #cbd5e1; margin: 4px 0;"><strong style="color:#fbbf24;">Level 4 — IMPROVE</strong><br>
Imagery, Meaning, Prayer, Relaxation, One thing, Vacation, Encouragement.</p>

<p style="color: #cbd5e1; margin: 4px 0;"><strong style="color:#fbbf24;">Level 5 — Seek Support</strong><br>
Therapist → Psychiatrist → Hospital if needed. Checking yourself in is strength, not weakness. You did it. It worked.</p>

<hr style="border-color: #334155;">
<p style="color: #64748b; font-size: 0.85rem; margin: 0;">
📞 Crisis Line: 988 | Crisis Text: HOME → 741741
</p>
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📊 Trigger History (Intensity Reduction)")
        t_logs = _trigger_logs(14)
        if t_logs:
            import pandas as pd
            df = pd.DataFrame(t_logs)
            if "intensity_before" in df.columns and "intensity_after" in df.columns:
                df["reduction"] = df["intensity_before"] - df["intensity_after"]
                df["date_short"] = df["log_date"].apply(lambda x: str(x)[:10])
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df["date_short"], y=df["intensity_before"],
                                     name="Before", marker_color="#ef4444", opacity=0.8))
                fig.add_trace(go.Bar(x=df["date_short"], y=df["intensity_after"],
                                     name="After Coping", marker_color="#4ade80", opacity=0.8))
                fig.update_layout(barmode="group", height=250, margin=dict(t=20, b=20),
                                  legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
                avg_reduction = df["reduction"].mean()
                if avg_reduction > 0:
                    st.success(f"📉 Your coping skills reduce intensity by **{avg_reduction:.1f} points** on average. They're working.")
        else:
            st.info("Log triggers to see your coping effectiveness over time.")


# ══════════════════════════════════════════════════════════════════════
# TAB 3: STRENGTHS MIRROR
# ══════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("💪 Strengths Mirror")
    st.caption("Written by you, for you. Read this when the negative self-talk gets loud.")

    st.markdown("""
<div style="background: #0a1628; border-left: 4px solid #fbbf24; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
<p style="color: #fbbf24; font-style: italic; margin: 0;">
"I am because we are. But right now, let's be clear about who 'I' is." — Ubuntu + Darrian
</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("### ✅ Your Strengths (Self-Identified — March 2026, Voluntary Hospitalization)")
    st.caption("These aren't compliments. These are observations YOU made about yourself when no one was watching.")

    # Show all strengths in a grid
    for i in range(0, len(DARRIAN_STRENGTHS), 2):
        c1, c2 = st.columns(2)
        with c1:
            name, desc = DARRIAN_STRENGTHS[i]
            st.markdown(f"""
<div style="background: #0f2027; border: 1px solid #1e3a5f; border-radius: 10px; padding: 14px; margin-bottom: 10px; min-height: 90px;">
<h4 style="color: #4ade80; margin: 0 0 6px 0;">{name}</h4>
<p style="color: #94a3b8; margin: 0; font-size: 0.9rem;">{desc}</p>
</div>
""", unsafe_allow_html=True)
        if i + 1 < len(DARRIAN_STRENGTHS):
            with c2:
                name2, desc2 = DARRIAN_STRENGTHS[i + 1]
                st.markdown(f"""
<div style="background: #0f2027; border: 1px solid #1e3a5f; border-radius: 10px; padding: 14px; margin-bottom: 10px; min-height: 90px;">
<h4 style="color: #4ade80; margin: 0 0 6px 0;">{name2}</h4>
<p style="color: #94a3b8; margin: 0; font-size: 0.9rem;">{desc2}</p>
</div>
""", unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🌱 Growth Edges (Honest — Not Flaws)")
    st.caption("These are neurological realities + patterns you identified. They're workable. They don't define you.")

    for name, desc in DARRIAN_GROWTH_EDGES:
        st.markdown(f"""
<div style="background: #1a0a00; border: 1px solid #3d2000; border-radius: 10px; padding: 12px; margin-bottom: 8px;">
<strong style="color: #fbbf24;">{name}</strong>
<p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 0.9rem;">{desc}</p>
</div>
""", unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🎯 Daily Affirmation — Personalized")
    random.seed(int(datetime.now().strftime("%Y%m%d%H")) // 3)  # Changes 8x/day
    daily_strength = random.choice(DARRIAN_STRENGTHS)
    daily_edge = random.choice(DARRIAN_GROWTH_EDGES)
    st.markdown(f"""
<div style="background: linear-gradient(135deg, #0a2040, #0f2a10); border-radius: 12px; padding: 20px; text-align: center;">
<p style="color: #4ade80; font-size: 1.1rem; margin: 0 0 8px 0;">
<strong>Today's Strength to Lean On:</strong> {daily_strength[0]}
</p>
<p style="color: #94a3b8; margin: 0 0 16px 0; font-size: 0.9rem;">{daily_strength[1]}</p>
<p style="color: #fbbf24; font-size: 1.0rem; margin: 0 0 6px 0;">
<strong>Today's Edge to Work With:</strong> {daily_edge[0]}
</p>
<p style="color: #94a3b8; margin: 0; font-size: 0.9rem;">{daily_edge[1]}</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 4: UBUNTU — Community Reflection
# ══════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🌍 Ubuntu — I Am Because We Are")
    st.caption("The revolutionary figures you love all said the same thing: freedom is collective.")

    st.markdown("""
<div style="background: #0a1628; border-left: 4px solid #7c3aed; padding: 16px 20px; border-radius: 8px; margin-bottom: 20px;">
<p style="color: #c4b5fd; font-size: 1.05rem; font-style: italic; margin: 0 0 8px 0;">
"It is our duty to fight for our freedom. It is our duty to win.<br>
We must love each other and support each other.<br>
We have nothing to lose but our chains."
</p>
<p style="color: #6d28d9; margin: 0; font-size: 0.9rem;">— Assata Shakur</p>
</div>
""", unsafe_allow_html=True)

    col_form, col_log = st.columns([1, 1])

    with col_form:
        st.markdown("#### Daily Community Reflection")
        st.caption("From your notes: Sikh kitchens, free gatherings, speaking to youth, building in VA + ATL.")
        with st.form("ubuntu_form", clear_on_submit=True):
            u_date = st.date_input("Date", value=date.today(), key="ubuntu_date")
            u_gave_to = st.text_input("Who did I give to or think about today?",
                                       placeholder="e.g. My mom, a stranger, my community, college students...")
            u_gave_what = st.text_area("What did I give? (time, knowledge, energy, presence, code)", height=60,
                                        placeholder="Even a text message counts. Even thinking about someone counts.")
            u_received = st.text_input("What did I receive from my community today?",
                                        placeholder="Support, inspiration, a laugh, wisdom...")
            u_vision = st.text_area("Community Vision — what am I building toward?", height=80,
                                     placeholder="Sikh kitchens, ATL community, College Confused, the village...")
            u_notes = st.text_area("Other Ubuntu thoughts:", height=60)

            if st.form_submit_button("💾 Save Reflection", type="primary", use_container_width=True):
                conn = get_conn()
                db_exec(conn, f"""
                    INSERT INTO wm_ubuntu_log
                        (user_id, log_date, gave_to_who, what_i_gave, what_i_received, community_vision, notes)
                    VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH})
                """, (_uid(), u_date.isoformat(), u_gave_to, u_gave_what, u_received, u_vision, u_notes))
                conn.commit()
                conn.close()
                st.success("✅ Ubuntu reflection saved. The village thanks you.")
                st.rerun()

    with col_log:
        st.markdown("#### 🌐 Community Vision Board")
        st.markdown("""
<div style="background: #1a0a3d; border-radius: 10px; padding: 16px;">
<h4 style="color: #c4b5fd; margin-top: 0;">What Darrian Is Building (from the notes)</h4>
<ul style="color: #94a3b8; line-height: 2;">
<li>🍊 <strong style="color: #fbbf24;">Peach State Savings</strong> — AI finance tools for people banks ignore</li>
<li>🎓 <strong style="color: #fbbf24;">College Confused</strong> — Free. No paywall. For first-gen kids everywhere.</li>
<li>🤖 <strong style="color: #fbbf24;">SoleOps</strong> — Economic empowerment for independent resellers</li>
<li>🏘️ <strong style="color: #fbbf24;">ATL Community</strong> — Real friendships, genuine connection, go outside</li>
<li>🙏 <strong style="color: #fbbf24;">Sikh Kitchen Concept</strong> — Free gatherings with resources. No means test.</li>
<li>🌱 <strong style="color: #fbbf24;">Family Systems</strong> — Mom's dashboard first, then sisters</li>
<li>🎙️ <strong style="color: #fbbf24;">Speak to Youth</strong> — Schools, summer camps, social media</li>
<li>🌿 <strong style="color: #fbbf24;">Long-term</strong> — Self-sustainability, off-grid, renewable energy</li>
</ul>
</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📖 Recent Ubuntu Reflections")
        u_logs = _ubuntu_logs(14)
        if u_logs:
            for log in u_logs[:5]:
                with st.container(border=True):
                    st.caption(str(log.get("log_date", ""))[:10])
                    if log.get("gave_to_who"):
                        st.markdown(f"**Gave to:** {log['gave_to_who']}")
                    if log.get("what_i_gave"):
                        st.markdown(f"**Gave:** {log['what_i_gave']}")
                    if log.get("community_vision"):
                        st.markdown(f"🌍 *{log['community_vision']}*")
        else:
            st.info("Start reflecting on how you're contributing to your community.")


# ══════════════════════════════════════════════════════════════════════
# TAB 5: THE WILL OF D — Quotes + Philosophy
# ══════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("⛵ The Will of D — Fire Every Day")
    st.caption("Malcolm. Assata. Bobby. Huey. Marcus. WEB. Luffy. Oda. J Cole. Kendrick. These are your nakama.")

    st.markdown("""
<div style="background: linear-gradient(135deg, #0a0a0a, #1a0a00); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #7c3aed;">
<h3 style="color: #fbbf24; margin-top: 0;">The Will of D (One Piece)</h3>
<p style="color: #e2e8f0; font-size: 1rem; line-height: 1.7;">
In One Piece, the people who carry the initial 'D' in their name are born to shake the world.
They laugh in the face of death. They fight for freedom. They protect their nakama (chosen family).
They don't conquer — they <em>liberate</em>. Luffy never wanted a throne. He wanted <strong>freedom</strong>.
</p>
<p style="color: #e2e8f0; font-size: 1rem; line-height: 1.7;">
Darrian, you carry this energy. The people you named — Malcolm, Assata, Bobby, Huey, Marcus —
they all had the Will of D. They didn't wait for permission to build a free world.
</p>
<p style="color: #fbbf24; font-style: italic; font-size: 1.05rem;">
"I don't want to conquer anything. I just think the guy with the most freedom in the whole ocean is the Pirate King!"
<br><span style="color: #64748b;">— Monkey D. Luffy</span>
</p>
<p style="color: #94a3b8; font-size: 0.9rem;">
Oda's philosophy: You don't have to be the smartest or the strongest.
You just have to be the one who never gives up on what matters.
And your nakama — your crew, your village — carries you the rest of the way.
</p>
</div>
""", unsafe_allow_html=True)

    # Quote explorer
    st.markdown("### 🔥 Quote Library")
    col_filter, _ = st.columns([1, 2])
    with col_filter:
        filter_person = st.selectbox(
            "Filter by:",
            ["All Figures"] + sorted(list(set(q[0] for q in FIRE_QUOTES)))
        )

    filtered_quotes = [q for q in FIRE_QUOTES if filter_person == "All Figures" or q[0] == filter_person]

    for person, quote in filtered_quotes:
        st.markdown(f"""
<div style="background: #0f0f1a; border-left: 3px solid #7c3aed; padding: 12px 16px; margin-bottom: 8px; border-radius: 6px;">
<p style="color: #e2e8f0; font-style: italic; margin: 0 0 4px 0;">"{quote}"</p>
<p style="color: #7c3aed; margin: 0; font-size: 0.85rem;">— {person}</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # Random quote button
    if "random_quote_idx" not in st.session_state:
        st.session_state.random_quote_idx = 0

    if st.button("⚡ Give Me Fire (Random Quote)", use_container_width=True):
        st.session_state.random_quote_idx = random.randint(0, len(FIRE_QUOTES) - 1)
        st.rerun()

    rq = FIRE_QUOTES[st.session_state.random_quote_idx]
    st.markdown(f"""
<div style="background: linear-gradient(135deg, #1a0040, #000820); border-radius: 12px; padding: 24px; text-align: center; border: 2px solid #fbbf24;">
<p style="color: #fbbf24; font-size: 1.2rem; font-style: italic; margin: 0 0 12px 0;">"{rq[1]}"</p>
<p style="color: #94a3b8; margin: 0; font-size: 1rem;">— {rq[0]}</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# TAB 6: TRENDS
# ══════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("📊 DBT Practice Trends — 30 Days")

    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    skills_30 = _skill_logs(30)
    coping_30 = _coping_logs(30)
    trigger_30 = _trigger_logs(30)

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Skills Practiced", len(skills_30))
    col_b.metric("Coping Logs", len(coping_30))
    col_c.metric("Triggers Processed", len(trigger_30))
    col_d.metric("Streak Days", len(set(s.get("log_date","")[:10] for s in skills_30 + coping_30)))

    st.divider()

    if skills_30:
        df_s = pd.DataFrame(skills_30)

        # Skills by category
        cat_counts = df_s["skill_category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        fig = px.bar(cat_counts, x="Category", y="Count",
                     title="DBT Skills by Category (30 days)",
                     color="Count", color_continuous_scale="Teal")
        fig.update_layout(height=300, margin=dict(t=40, b=80), xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

        # Effectiveness over time
        if "effectiveness" in df_s.columns:
            df_s["date_short"] = df_s["log_date"].apply(lambda x: str(x)[:10])
            df_eff = df_s.groupby("date_short")["effectiveness"].mean().reset_index()
            fig2 = px.line(df_eff, x="date_short", y="effectiveness",
                           title="Average Skill Effectiveness Over Time",
                           markers=True, color_discrete_sequence=["#4ade80"])
            fig2.add_hline(y=3, line_dash="dash", line_color="gray", annotation_text="Effective threshold")
            fig2.update_layout(height=260, margin=dict(t=40, b=20), yaxis=dict(range=[0, 6]))
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Log DBT skills to see trends. The graph builds as you build the habit.")

    if trigger_30:
        df_t = pd.DataFrame(trigger_30)
        if "intensity_before" in df_t.columns and "intensity_after" in df_t.columns:
            df_t["date_short"] = df_t["log_date"].apply(lambda x: str(x)[:10])
            df_t["reduction"] = df_t["intensity_before"] - df_t["intensity_after"]
            avg_before = df_t["intensity_before"].mean()
            avg_after  = df_t["intensity_after"].mean()
            avg_reduce = df_t["reduction"].mean()
            col1, col2, col3 = st.columns(3)
            col1.metric("Avg Intensity (Before)", f"{avg_before:.1f}/10")
            col2.metric("Avg Intensity (After)", f"{avg_after:.1f}/10")
            col3.metric("Avg Reduction", f"{avg_reduce:.1f} pts", delta=f"{'↓' if avg_reduce > 0 else '↑'} intensity")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — 💊 MEDS & CARE
# ─────────────────────────────────────────────────────────────────────────────
with tabs[7]:
    st.markdown("## 💊 Meds & Care")
    st.caption("Your personal medication schedule, appointments, pharmacy, and crisis lines — all in one place.")

    # ── STOPPED MED WARNING ──────────────────────────────────────────────────
    st.error(
        "🚫 **STOP — DO NOT TAKE:** " +
        " · ".join(f"**{m['name']}** ({m['reason']})" for m in DARRIAN_STOPPED_MEDS),
        icon="⛔"
    )

    st.divider()

    # ── DAILY MEDICATION SCHEDULE ─────────────────────────────────────────────
    st.markdown("### 📅 Daily Schedule")

    col_am, col_pm, col_night = st.columns(3)

    def _med_card(col, time_label, emoji):
        # schedule values: "AM + PM", "NIGHT", "DAILY"
        def _matches(sched, label):
            s = sched.upper()
            if label == "AM":
                return "AM" in s or "DAILY" in s
            if label == "PM":
                return "PM" in s
            if label == "NIGHT":
                return "NIGHT" in s
            return False
        meds_for_time = [m for m in DARRIAN_MEDS if _matches(m["schedule"], time_label)]
        col.markdown(f"**{emoji} {time_label}**")
        if meds_for_time:
            for m in meds_for_time:
                col.markdown(f"- **{m['name']}** {m['dose']}  \n  _{m['schedule_detail']}_")
        else:
            col.markdown("_No meds at this time_")

    _med_card(col_am,    "AM",    "🌅")
    _med_card(col_pm,    "PM",    "🌇")
    _med_card(col_night, "NIGHT", "🌙")

    st.divider()

    # ── MED ADHERENCE TRACKER ────────────────────────────────────────────────
    st.markdown("### ✅ Log Today's Meds")
    today_str = date.today().isoformat()

    # Load today's logs
    conn = get_conn()
    rows = []
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT med_name, taken, time_taken, notes FROM wm_med_log WHERE user_id={PH} AND log_date={PH}",
            (st.session_state.get("user_id", 1), today_str)
        )
        rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    except Exception:
        pass
    conn.close()

    taken_names = {r["med_name"] for r in rows if r["taken"]}

    with st.form("med_log_form"):
        st.markdown(f"**Date: {today_str}**")
        med_checks = {}
        med_notes  = {}
        for m in DARRIAN_MEDS:
            c1, c2 = st.columns([1, 2])
            med_checks[m["name"]] = c1.checkbox(
                f"{m['name']} {m['dose']}",
                value=(m["name"] in taken_names)
            )
            med_notes[m["name"]] = c2.text_input(
                "Notes (optional)",
                key=f"med_note_{m['name']}",
                label_visibility="collapsed",
                placeholder=f"e.g. took with food — {m['name']}"
            )
        submitted = st.form_submit_button("💾 Save Med Log", use_container_width=True)

    if submitted:
        conn = get_conn()
        uid = st.session_state.get("user_id", 1)
        now_time = datetime.now().strftime("%H:%M")
        for m in DARRIAN_MEDS:
            # Upsert: delete existing then insert
            try:
                db_exec(conn, "DELETE FROM wm_med_log WHERE user_id=? AND log_date=? AND med_name=?",
                        (uid, today_str, m["name"]))
                db_exec(conn, """INSERT INTO wm_med_log (user_id, log_date, med_name, taken, time_taken, notes)
                                  VALUES (?, ?, ?, ?, ?, ?)""",
                        (uid, today_str, m["name"],
                         1 if med_checks[m["name"]] else 0,
                         now_time if med_checks[m["name"]] else None,
                         med_notes[m["name"]] or None))
            except Exception as e:
                st.error(f"DB error: {e}")
        conn.commit()
        conn.close()
        taken_count = sum(1 for v in med_checks.values() if v)
        st.success(f"✅ Saved! {taken_count}/{len(DARRIAN_MEDS)} medications logged as taken today.")
        st.rerun()

    # ── ADHERENCE STREAK ─────────────────────────────────────────────────────
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT log_date, COUNT(*) as cnt FROM wm_med_log WHERE user_id={PH} AND taken=1 GROUP BY log_date ORDER BY log_date DESC LIMIT 30",
            (st.session_state.get("user_id", 1),)
        )
        streak_rows = cur.fetchall()
    except Exception:
        streak_rows = []
    conn.close()

    if streak_rows:
        st.divider()
        st.markdown("### 📈 Adherence (Last 30 Days)")
        streak_dates = [r[0] for r in streak_rows]
        streak_days  = len(streak_dates)
        st.metric("Days with at least 1 med logged", f"{streak_days} days")

    st.divider()

    # ── UPCOMING APPOINTMENTS ────────────────────────────────────────────────
    st.markdown("### 📍 Upcoming Appointments")
    for appt in DARRIAN_APPOINTMENTS:
        with st.container(border=True):
            st.markdown(f"**{appt['title']}** — {appt['type']}  \n"
                        f"📅 {appt['date_str']} at {appt['time']}  \n"
                        f"📌 {appt['address']}  \n"
                        f"📞 [{appt['phone']}](tel:{appt['phone'].replace('-','')})")
            st.markdown(f"💡 _{appt['notes']}_")
            st.markdown(
                f"[🗺️ Get Directions](https://maps.apple.com/?q={appt['address'].replace(' ','+')})",
                unsafe_allow_html=False
            )

    st.divider()

    # ── PHARMACY ─────────────────────────────────────────────────────────────
    st.markdown("### 💊 Pharmacy")
    with st.container(border=True):
        st.markdown(
            f"**{DARRIAN_PHARMACY['name']}**  \n"
            f"📌 {DARRIAN_PHARMACY['address']}  \n"
            f"📞 [{DARRIAN_PHARMACY['phone']}](tel:{DARRIAN_PHARMACY['phone'].replace('-','')})"
        )
        st.markdown("**Prescriptions to pick up:**")
        for rx in DARRIAN_PHARMACY["pickup_list"]:
            st.markdown(f"- {rx}")

    st.divider()

    # ── MYCHART ──────────────────────────────────────────────────────────────
    st.markdown("### 🏥 Tanner MyChart")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.markdown(
            f"**Portal:** [{DARRIAN_MYCHART['url']}]({DARRIAN_MYCHART['url']})  \n"
            f"**MRN:** `{DARRIAN_MYCHART['mrn']}`"
        )
        c2.markdown(
            f"**Activation Code:**  \n"
            f"```\n{DARRIAN_MYCHART['activation_code']}\n```  \n"
            f"_Expires: {DARRIAN_MYCHART['expires']}_"
        )
        st.info("💡 Use the activation code on the MyChart portal to set up your account and view discharge records.")

    st.divider()

    # ── CRISIS LINES ─────────────────────────────────────────────────────────
    st.markdown("### 🆘 Crisis & Warm Lines")
    st.caption("You are never alone. These lines are available 24/7 or during extended hours.")
    for line in GEORGIA_CRISIS_LINES:
        c1, c2, c3 = st.columns([2, 2, 3])
        c1.markdown(f"**{line[0]}**")
        c2.markdown(f"`{line[1]}`")
        c3.markdown(f"_{line[2]}_")

    st.divider()

    # ── MED WARNINGS (EXPANDABLE) ────────────────────────────────────────────
    with st.expander("⚠️ Medication Warnings & Notes"):
        for m in DARRIAN_MEDS:
            warnings = m.get("warnings", [])
            if warnings:
                st.warning(f"**{m['name']}** ({m['dose']})\n\n" + "\n".join(f"- {w}" for w in warnings))
        st.error(
            "🚫 **STOPPED MEDICATIONS — DO NOT TAKE:**\n\n" +
            "\n".join(f"- **{m['name']}** {m['dose']}: {m['reason']}" for m in DARRIAN_STOPPED_MEDS)
        )
