"""
Mom's Command Center — Page 150
A complete life-management system built with love for a mother of three.
Christian-centered. Trauma-informed. ADHD-friendly. Grace-based — not shame-based.
Inspired by the kind of care grandparents give: firm, warm, full of love and wisdom.

"She is clothed with strength and dignity, and she laughs without fear of the future."
— Proverbs 31:25
"""
import streamlit as st
import json
from datetime import datetime, date, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="✝️ Mom's Command Center — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                               label="Overview",            icon="📊")
st.sidebar.page_link("pages/22_todo.py",                     label="Todo",                icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",        label="Creator",             icon="🎬")
st.sidebar.page_link("pages/25_notes.py",                    label="Notes",               icon="📝")
st.sidebar.page_link("pages/57_social_media_manager.py",     label="Social Media",        icon="📱")
st.sidebar.page_link("pages/17_personal_assistant.py",       label="Personal Assistant",  icon="🤖")
st.sidebar.page_link("pages/147_proactive_ai_engine.py",     label="Proactive AI",        icon="🧠")
st.sidebar.page_link("pages/150_moms_command_center.py",     label="Mom's Command Center", icon="✝️")
render_sidebar_user_widget()

# ── Custom warm CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Nunito:wght@400;600;700;800&display=swap');

.mcc-header {
    background: linear-gradient(135deg, #3b1f5e 0%, #1a3a5c 50%, #0d2b3e 100%);
    border-radius: 18px;
    padding: 32px 36px;
    margin-bottom: 24px;
    border: 1px solid rgba(255,200,100,0.2);
    position: relative;
    overflow: hidden;
}
.mcc-header::before {
    content: '✝';
    position: absolute;
    right: 32px; top: 16px;
    font-size: 5rem;
    color: rgba(255,200,100,0.08);
    pointer-events: none;
}
.mcc-title {
    font-family: 'Nunito', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #fff;
    margin: 0 0 6px 0;
}
.mcc-verse {
    font-family: 'Lora', serif;
    font-style: italic;
    color: rgba(255,200,100,0.85);
    font-size: 1rem;
    line-height: 1.7;
}

/* Grace cards */
.grace-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 16px;
    padding: 22px 24px;
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 12px;
    position: relative;
}
.grace-card.gold { border-color: rgba(255,200,80,0.3); }
.grace-card.rose { border-color: rgba(255,120,120,0.3); }
.grace-card.teal { border-color: rgba(80,200,180,0.3); }
.grace-card.purple { border-color: rgba(160,100,255,0.3); }
.grace-card.green { border-color: rgba(80,200,120,0.3); }

.grace-label {
    font-family: 'Nunito', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: rgba(255,200,100,0.7);
    margin-bottom: 6px;
}
.grace-value {
    font-size: 1.6rem;
    font-weight: 800;
    color: #fff;
    font-family: 'Nunito', sans-serif;
}
.grace-sub { font-size: 0.82rem; color: rgba(255,255,255,0.5); margin-top: 4px; }

/* Scripture callout */
.scripture-box {
    background: linear-gradient(135deg, rgba(255,200,80,0.08) 0%, rgba(60,30,100,0.3) 100%);
    border-left: 4px solid rgba(255,200,80,0.7);
    border-radius: 0 12px 12px 0;
    padding: 18px 22px;
    margin: 16px 0;
}
.scripture-text {
    font-family: 'Lora', serif;
    font-style: italic;
    color: rgba(255,220,140,0.95);
    font-size: 1rem;
    line-height: 1.75;
}
.scripture-ref {
    font-family: 'Nunito', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    color: rgba(255,200,80,0.6);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 10px;
}

/* Habit ring */
.habit-ring {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 54px; height: 54px;
    border-radius: 50%;
    border: 3px solid rgba(80,200,150,0.4);
    font-size: 1.4rem;
    background: rgba(80,200,150,0.08);
    margin-bottom: 6px;
    cursor: pointer;
    transition: all 0.2s;
}
.habit-ring.done {
    border-color: #50c896;
    background: rgba(80,200,150,0.2);
    box-shadow: 0 0 16px rgba(80,200,150,0.3);
}

/* Kid card */
.kid-card {
    background: #16213e;
    border-radius: 14px;
    padding: 20px 22px;
    border: 1px solid rgba(255,255,255,0.07);
    height: 100%;
}
.kid-name {
    font-family: 'Nunito', sans-serif;
    font-weight: 800;
    font-size: 1.1rem;
    color: #fff;
    margin-bottom: 4px;
}
.kid-age { font-size: 0.78rem; color: rgba(255,255,255,0.45); }

/* Post card */
.post-card {
    background: #1a1a2e;
    border-radius: 14px;
    padding: 18px 20px;
    border: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 10px;
}

/* Affirmation pill */
.affirm-pill {
    display: inline-block;
    background: rgba(255,200,80,0.12);
    border: 1px solid rgba(255,200,80,0.3);
    color: rgba(255,220,140,0.9);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 0.82rem;
    font-family: 'Lora', serif;
    font-style: italic;
    margin: 3px 3px;
}

/* Grandma wisdom box */
.grandma-box {
    background: linear-gradient(135deg, rgba(255,200,80,0.07) 0%, rgba(60,30,100,0.2) 100%);
    border: 1px solid rgba(255,200,80,0.2);
    border-radius: 16px;
    padding: 22px 26px;
    margin: 16px 0;
}
.grandma-box p {
    font-family: 'Lora', serif;
    font-style: italic;
    color: rgba(255,220,140,0.85);
    font-size: 0.93rem;
    line-height: 1.85;
    margin: 0;
}
</style>
""", unsafe_allow_html=True)

# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    # Daily check-in / devotional log
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_daily_log (
            id {ai},
            log_date TEXT NOT NULL,
            mood INTEGER DEFAULT 5,
            anxiety INTEGER DEFAULT 5,
            energy INTEGER DEFAULT 5,
            gratitude TEXT DEFAULT '',
            prayer_request TEXT DEFAULT '',
            morning_intention TEXT DEFAULT '',
            evening_reflection TEXT DEFAULT '',
            scripture_for_day TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Kids
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_kids (
            id {ai},
            name TEXT NOT NULL,
            age INTEGER DEFAULT 0,
            grade TEXT DEFAULT '',
            school TEXT DEFAULT '',
            color TEXT DEFAULT '#7c6af7',
            notes TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Kid events / calendar
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_kid_events (
            id {ai},
            kid_id INTEGER DEFAULT 0,
            kid_name TEXT DEFAULT '',
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT DEFAULT '',
            event_type TEXT DEFAULT 'general',
            location TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            completed INTEGER DEFAULT 0,
            created_at TEXT {ts}
        )
    """)

    # Habits
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_habits (
            id {ai},
            name TEXT NOT NULL,
            icon TEXT DEFAULT '🌟',
            category TEXT DEFAULT 'self-care',
            scripture TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT {ts}
        )
    """)

    # Habit completions
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_habit_log (
            id {ai},
            habit_id INTEGER NOT NULL,
            log_date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Social media posts (Christian-toned)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_social_posts (
            id {ai},
            title TEXT DEFAULT '',
            caption TEXT DEFAULT '',
            platform TEXT DEFAULT 'Instagram',
            post_type TEXT DEFAULT 'post',
            status TEXT DEFAULT 'draft',
            theme TEXT DEFAULT 'faith',
            scheduled_date TEXT DEFAULT NULL,
            posted_date TEXT DEFAULT NULL,
            media_note TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Simple budget
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_budget (
            id {ai},
            budget_month TEXT NOT NULL,
            category TEXT NOT NULL,
            item TEXT NOT NULL,
            projected REAL DEFAULT 0,
            actual REAL DEFAULT 0,
            due_date TEXT DEFAULT '',
            paid INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Affirmations / scripture bank
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS mcc_affirmations (
            id {ai},
            text TEXT NOT NULL,
            scripture_ref TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            created_at TEXT {ts}
        )
    """)

    conn.commit()
    conn.close()

_ensure_tables()

# ── Seed default habits ────────────────────────────────────────────────────────
def _seed_defaults():
    conn = get_conn()
    c = db_exec(conn, "SELECT COUNT(*) FROM mcc_habits")
    if c.fetchone()[0] == 0:
        default_habits = [
            ("Morning Prayer", "🙏", "faith", "Before I formed you in the womb I knew you. — Jeremiah 1:5"),
            ("Read Scripture", "📖", "faith", "Your word is a lamp to my feet. — Psalm 119:105"),
            ("Drink Water", "💧", "health", "Whoever drinks the water I give them will never thirst. — John 4:14"),
            ("Move My Body", "🚶‍♀️", "health", "Do you not know that your body is a temple? — 1 Corinthians 6:19"),
            ("One Kind Act", "💛", "community", "Love one another as I have loved you. — John 15:12"),
            ("Gratitude Journal", "✍️", "mindset", "Give thanks in all circumstances. — 1 Thessalonians 5:18"),
            ("Connect with Kids", "👨‍👩‍👧‍👦", "family", "Train up a child in the way they should go. — Proverbs 22:6"),
            ("Rest & Breathe", "🌿", "health", "Come to me, all you who are weary. — Matthew 11:28"),
        ]
        for name, icon, cat, scripture in default_habits:
            db_exec(conn, "INSERT INTO mcc_habits (name, icon, category, scripture) VALUES (?,?,?,?)",
                    (name, icon, cat, scripture))

    c = db_exec(conn, "SELECT COUNT(*) FROM mcc_affirmations")
    if c.fetchone()[0] == 0:
        affirmations = [
            ("I am not my past. I am who God says I am.", "Isaiah 43:18-19", "healing"),
            ("Today I choose peace over anxiety.", "Philippians 4:6-7", "anxiety"),
            ("I am a strong, capable mother. God chose me for my children.", "Psalm 139:14", "motherhood"),
            ("My worth is not defined by what I have or don't have.", "Proverbs 31:10", "poverty"),
            ("I am healing. Slowly but surely.", "Jeremiah 30:17", "trauma"),
            ("My children are blessed because their mother fights for them.", "Joshua 1:9", "motherhood"),
            ("I don't have to have it all together to be a good mom.", "Romans 8:28", "grace"),
            ("Rest is not laziness. Rest is God's design.", "Psalm 23:2", "adhd"),
            ("I am more than my diagnosis.", "2 Timothy 1:7", "adhd"),
            ("God turned my divorce into a doorway, not a dead end.", "Romans 8:28", "divorce"),
            ("I am learning to forgive — myself and others.", "Colossians 3:13", "healing"),
            ("Even on hard days, God is working things out for me.", "Romans 8:28", "faith"),
        ]
        for text, ref, cat in affirmations:
            db_exec(conn, "INSERT INTO mcc_affirmations (text, scripture_ref, category) VALUES (?,?,?)",
                    (text, ref, cat))

    conn.commit()
    conn.close()

_seed_defaults()

# ── Constants ──────────────────────────────────────────────────────────────────
TODAY = date.today()
TODAY_STR = TODAY.isoformat()
MONTH_STR = TODAY.strftime("%Y-%m")

DAILY_SCRIPTURES = [
    ("She is clothed with strength and dignity, and she laughs without fear of the future.", "Proverbs 31:25"),
    ("I can do all things through Christ who strengthens me.", "Philippians 4:13"),
    ("Cast all your anxiety on Him because He cares for you.", "1 Peter 5:7"),
    ("For I know the plans I have for you — plans to prosper you and not to harm you.", "Jeremiah 29:11"),
    ("God is within her, she will not fall.", "Psalm 46:5"),
    ("The Lord your God is with you, the Mighty Warrior who saves.", "Zephaniah 3:17"),
    ("Come to me, all you who are weary and burdened, and I will give you rest.", "Matthew 11:28"),
]

THEMES = ["faith", "family", "testimony", "encouragement", "motherhood", "healing", "gratitude", "wisdom"]
PLATFORMS = ["Instagram", "Facebook", "TikTok", "Twitter/X", "YouTube"]

EVENT_TYPES = ["school", "appointment", "activity", "church", "therapy", "sports", "birthday", "other"]
EVENT_COLORS = {
    "school": "#4fc3f7",
    "appointment": "#ef9a9a",
    "activity": "#a5d6a7",
    "church": "#ffcc80",
    "therapy": "#ce93d8",
    "sports": "#80cbc4",
    "birthday": "#f48fb1",
    "other": "#b0bec5",
}

BUDGET_CATEGORIES = [
    "Housing", "Utilities", "Food", "Transportation", "Kids",
    "Healthcare", "Phone", "Clothing", "Personal Care", "Church/Tithe",
    "Debt", "Savings", "Miscellaneous"
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def _load_kids():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM mcc_kids ORDER BY age DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_today_log():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM mcc_daily_log WHERE log_date=?", (TODAY_STR,))
    row = c.fetchone()
    conn.close()
    if row:
        cols = ["id","log_date","mood","anxiety","energy","gratitude","prayer_request","morning_intention","evening_reflection","scripture_for_day","created_at"]
        return dict(zip(cols, row))
    return None

def _save_daily_log(mood, anxiety, energy, gratitude, prayer, intention, reflection, scripture):
    conn = get_conn()
    existing = _load_today_log()
    if existing:
        db_exec(conn, """UPDATE mcc_daily_log SET mood=?,anxiety=?,energy=?,gratitude=?,
                          prayer_request=?,morning_intention=?,evening_reflection=?,scripture_for_day=? 
                          WHERE log_date=?""",
                (mood, anxiety, energy, gratitude, prayer, intention, reflection, scripture, TODAY_STR))
    else:
        db_exec(conn, """INSERT INTO mcc_daily_log 
                         (log_date,mood,anxiety,energy,gratitude,prayer_request,morning_intention,evening_reflection,scripture_for_day)
                         VALUES (?,?,?,?,?,?,?,?,?)""",
                (TODAY_STR, mood, anxiety, energy, gratitude, prayer, intention, reflection, scripture))
    conn.commit()
    conn.close()

def _load_habits():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM mcc_habits WHERE active=1 ORDER BY category ASC, name ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _get_habit_done(habit_id: int, for_date: str) -> bool:
    conn = get_conn()
    c = db_exec(conn, "SELECT completed FROM mcc_habit_log WHERE habit_id=? AND log_date=?",
                (habit_id, for_date))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0])

def _toggle_habit(habit_id: int, for_date: str):
    conn = get_conn()
    c = db_exec(conn, "SELECT id, completed FROM mcc_habit_log WHERE habit_id=? AND log_date=?",
                (habit_id, for_date))
    row = c.fetchone()
    if row:
        new_val = 0 if row[1] else 1
        db_exec(conn, "UPDATE mcc_habit_log SET completed=? WHERE id=?", (new_val, row[0]))
    else:
        db_exec(conn, "INSERT INTO mcc_habit_log (habit_id, log_date, completed) VALUES (?,?,1)",
                (habit_id, for_date))
    conn.commit()
    conn.close()

def _habit_streak(habit_id: int) -> int:
    conn = get_conn()
    c = db_exec(conn, """SELECT log_date FROM mcc_habit_log 
                         WHERE habit_id=? AND completed=1 
                         ORDER BY log_date DESC LIMIT 30""", (habit_id,))
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    if not rows:
        return 0
    streak = 0
    check = date.today()
    for row_date in rows:
        try:
            d = date.fromisoformat(str(row_date)[:10])
        except Exception:
            break
        if d == check or d == check - timedelta(days=1):
            streak += 1
            check = d - timedelta(days=1)
        else:
            break
    return streak

def _load_kid_events(start: date, end: date):
    conn = get_conn()
    c = db_exec(conn, """SELECT * FROM mcc_kid_events 
                         WHERE event_date >= ? AND event_date <= ?
                         ORDER BY event_date ASC, event_time ASC""",
                (start.isoformat(), end.isoformat()))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_posts(status=None):
    conn = get_conn()
    where = "" if not status else f"WHERE status='{status}'"
    c = db_exec(conn, f"SELECT * FROM mcc_social_posts {where} ORDER BY created_at DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_budget(month: str):
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM mcc_budget WHERE budget_month=? ORDER BY category ASC, item ASC",
                (month,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_affirmations(category=None):
    conn = get_conn()
    if category:
        c = db_exec(conn, "SELECT * FROM mcc_affirmations WHERE category=? ORDER BY RANDOM() LIMIT 5",
                    (category,))
    else:
        c = db_exec(conn, "SELECT * FROM mcc_affirmations ORDER BY RANDOM() LIMIT 5")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _ask_ai(system_prompt: str, user_prompt: str) -> str:
    api_key = get_setting("anthropic_api_key", "")
    if not api_key:
        api_key = st.session_state.get("anthropic_api_key", "")
    if not api_key:
        return "No Anthropic API key found. Add it in Settings > AI Insights."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI Error: {e}"

# ── AI context for mom ─────────────────────────────────────────────────────────
MOM_CONTEXT = """
You are a warm, wise, and deeply loving AI life coach and social media strategist 
for a Christian single mother of three children. 

Her story:
- She is navigating single motherhood, financial hardship, divorce recovery, and personal trauma
- She has ADHD and struggles with anxiety and depression
- She is a woman of deep faith who wants to grow in her walk with God
- She wants to build a social media presence that uplifts others and shares her testimony
- She is rebuilding her life with grace, not shame

Your voice is:
- Like the wisest, most loving grandparent — firm but gentle, never harsh
- Christian-centered without being preachy or judgmental
- Trauma-informed: you NEVER shame her for struggling
- ADHD-aware: you give clear, simple steps, not overwhelming lists
- Grace-based: you always point back to God's love and redemption
- Encouraging, warm, real — not corporate or robotic

For social media content:
- Christian but relatable and authentic — not churchy or fake
- Centered on real life: motherhood, healing, faith in hard times, small wins
- Uplifting without toxic positivity
- Honest about the hard stuff while still pointing to hope

Start with encouragement before advice. Always remind her she is enough.
"""

# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
# Daily scripture rotation
scripture_idx = TODAY.timetuple().tm_yday % len(DAILY_SCRIPTURES)
todays_scripture, scripture_ref = DAILY_SCRIPTURES[scripture_idx]

st.markdown(f"""
<div class="mcc-header">
    <div style="font-family:'Nunito',sans-serif;font-size:0.75rem;font-weight:700;
                color:rgba(255,200,100,0.7);text-transform:uppercase;letter-spacing:0.12em;
                margin-bottom:8px;">✝️ Mom's Command Center</div>
    <div class="mcc-title">Good Morning, Beautiful. 🌸</div>
    <div style="font-family:'Nunito',sans-serif;color:rgba(255,255,255,0.6);
                font-size:0.85rem;margin:4px 0 16px;">
        {TODAY.strftime("%A, %B %d, %Y")}
    </div>
    <div class="mcc-verse">"{todays_scripture}"</div>
    <div style="font-family:'Nunito',sans-serif;font-size:0.72rem;font-weight:700;
                color:rgba(255,200,100,0.5);text-transform:uppercase;letter-spacing:0.1em;margin-top:8px;">
        — {scripture_ref}
    </div>
</div>
""", unsafe_allow_html=True)

# Today's check-in quick metrics
today_log = _load_today_log()
habits = _load_habits()
done_today = sum(1 for h in habits if _get_habit_done(h["id"], TODAY_STR))

m1, m2, m3, m4 = st.columns(4)
with m1:
    mood_val = today_log["mood"] if today_log else "—"
    st.markdown(f"""<div class="grace-card gold">
        <div class="grace-label">Mood Today</div>
        <div class="grace-value">{mood_val}/10</div>
        <div class="grace-sub">How are you feeling?</div>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""<div class="grace-card teal">
        <div class="grace-label">Habits Done</div>
        <div class="grace-value">{done_today}/{len(habits)}</div>
        <div class="grace-sub">Grace over perfection ✨</div>
    </div>""", unsafe_allow_html=True)
with m3:
    upcoming_events = _load_kid_events(TODAY, TODAY + timedelta(days=7))
    st.markdown(f"""<div class="grace-card purple">
        <div class="grace-label">Kid Events (7d)</div>
        <div class="grace-value">{len(upcoming_events)}</div>
        <div class="grace-sub">This week</div>
    </div>""", unsafe_allow_html=True)
with m4:
    posts = _load_posts("draft")
    st.markdown(f"""<div class="grace-card rose">
        <div class="grace-label">Posts Ready</div>
        <div class="grace-value">{len(posts)}</div>
        <div class="grace-sub">Drafts to review</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Main tabs ──────────────────────────────────────────────────────────────────
tab_anchor, tab_habits, tab_family, tab_smm, tab_budget, tab_coach, tab_setup = st.tabs([
    "🙏 Daily Anchor",
    "🌟 Habits",
    "👨‍👩‍👧 Family Hub",
    "📱 Social Media",
    "💵 Budget",
    "💛 Life Coach",
    "⚙️ Setup",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DAILY ANCHOR (Morning Check-In + Devotional)
# ══════════════════════════════════════════════════════════════════════════════
with tab_anchor:
    st.markdown("### 🙏 Daily Anchor")
    st.caption("Start your day grounded in grace. No pressure — just a moment to breathe and connect.")

    # Affirmation of the day
    affirmations = _load_affirmations()
    if affirmations:
        af = affirmations[0]
        st.markdown(f"""
        <div class="grandma-box">
            <p>"{af['text']}"</p>
            <div style="font-family:'Nunito',sans-serif;font-size:0.72rem;font-weight:700;
                        color:rgba(255,200,100,0.5);text-transform:uppercase;letter-spacing:0.1em;margin-top:10px;">
                — {af['scripture_ref']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    col_morning, col_evening = st.columns(2)

    with col_morning:
        st.markdown("#### ☀️ Morning Check-In")
        st.caption("Takes 2 minutes. Worth it every time.")

        with st.form("morning_form"):
            mood = st.slider("💛 Mood (1 = rough, 10 = thriving)", 1, 10,
                             today_log["mood"] if today_log else 5)
            anxiety = st.slider("🌊 Anxiety Level (1 = calm, 10 = overwhelmed)", 1, 10,
                                today_log["anxiety"] if today_log else 5)
            energy = st.slider("⚡ Energy (1 = empty, 10 = full)", 1, 10,
                               today_log["energy"] if today_log else 5)

            st.markdown("**Three things I'm grateful for today:**")
            gratitude = st.text_area("Gratitude",
                                     value=today_log["gratitude"] if today_log else "",
                                     placeholder="Even small things count. A warm cup of coffee. The kids laughing. A roof over your head.",
                                     height=80,
                                     label_visibility="collapsed")

            intention = st.text_input("☀️ One intention for today:",
                                       value=today_log["morning_intention"] if today_log else "",
                                       placeholder="e.g. 'I will be patient with myself and the kids.'")

            prayer = st.text_area("🙏 Prayer request (just for you):",
                                  value=today_log["prayer_request"] if today_log else "",
                                  placeholder="What are you laying at God's feet today?",
                                  height=70,
                                  label_visibility="collapsed")

            scripture_choice = st.text_input("📖 Scripture I'm holding today (optional):",
                                              value=today_log["scripture_for_day"] if today_log else todays_scripture,
                                              placeholder="Type a verse or use today's scripture above")

            if st.form_submit_button("💛 Save My Morning Check-In", type="primary", use_container_width=True):
                reflection = today_log["evening_reflection"] if today_log else ""
                _save_daily_log(mood, anxiety, energy, gratitude, prayer, intention, reflection, scripture_choice)
                st.success("✅ Beautiful. You showed up for yourself today. That matters.")
                st.rerun()

    with col_evening:
        st.markdown("#### 🌙 Evening Reflection")
        st.caption("End the day with grace. What happened? How are you?")

        with st.form("evening_form"):
            reflection = st.text_area("Tonight I'm reflecting on...",
                                      value=today_log["evening_reflection"] if today_log else "",
                                      placeholder=(
                                          "What went well today — even one tiny thing?\n"
                                          "What was hard? (No judgment. Just honesty.)\n"
                                          "What are you releasing before you sleep?"
                                      ),
                                      height=200,
                                      label_visibility="collapsed")

            if st.form_submit_button("🌙 Save Evening Reflection", type="primary", use_container_width=True):
                if today_log:
                    _save_daily_log(
                        today_log["mood"], today_log["anxiety"], today_log["energy"],
                        today_log["gratitude"], today_log["prayer_request"],
                        today_log["morning_intention"], reflection,
                        today_log["scripture_for_day"]
                    )
                else:
                    _save_daily_log(5, 5, 5, "", "", "", reflection, todays_scripture)
                st.success("🌙 Rest, beautiful. Tomorrow is a new mercy. Lamentations 3:22-23")
                st.rerun()

        # Grandma wisdom
        st.markdown("""
        <div class="grandma-box" style="margin-top:20px;">
            <p>
            Baby, some days you're going to do everything right and it's still going to be hard.
            That's not failure — that's life. You put one foot in front of the other.
            You ask God for strength you don't have yet. You trust that He's working
            even when you can't see it. That's enough. <em>You</em> are enough.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 📖 This Week's Scriptures")
    scripture_cols = st.columns(3)
    for i, (verse, ref) in enumerate(DAILY_SCRIPTURES[:6]):
        with scripture_cols[i % 3]:
            st.markdown(f"""
            <div class="scripture-box">
                <div class="scripture-text">"{verse}"</div>
                <div class="scripture-ref">— {ref}</div>
            </div>
            """, unsafe_allow_html=True)

    # Affirmation wall
    st.divider()
    st.markdown("#### 💛 Your Affirmations")
    all_affirm = _load_affirmations()
    affirm_html = " ".join([f'<span class="affirm-pill">{a["text"][:60]}...</span>'
                             if len(a["text"]) > 60
                             else f'<span class="affirm-pill">{a["text"]}</span>'
                             for a in all_affirm])
    st.markdown(f'<div style="line-height:2;">{affirm_html}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HABITS (ADHD-Friendly, Grace-Based)
# ══════════════════════════════════════════════════════════════════════════════
with tab_habits:
    st.markdown("### 🌟 Habit Tracker")

    st.markdown("""
    <div class="grandma-box">
        <p>
        Sweetheart, we're not going for perfect. We're going for <em>present</em>.
        If you get one thing done today — <em>one</em> — that's a win.
        These habits aren't rules. They're seeds you're planting for yourself and your babies.
        No shame if you miss. Just start again tomorrow. That's grace.
        </p>
    </div>
    """, unsafe_allow_html=True)

    habits = _load_habits()
    if not habits:
        st.info("Add habits in ⚙️ Setup to get started!")
    else:
        # Date selector
        hab_date = st.date_input("Track habits for:", value=TODAY, key="habit_date")
        hab_date_str = hab_date.isoformat()

        done_count = sum(1 for h in habits if _get_habit_done(h["id"], hab_date_str))
        pct = int((done_count / len(habits)) * 100) if habits else 0

        # Progress bar
        bar_color = "#50c896" if pct >= 75 else "#ffc850" if pct >= 40 else "#ef9a9a"
        st.markdown(f"""
        <div style="margin:16px 0">
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;
                        color:rgba(255,255,255,0.5);margin-bottom:6px;">
                <span>Today's Grace Meter</span>
                <span>{done_count}/{len(habits)} — {pct}%</span>
            </div>
            <div style="background:#1a1a2e;border-radius:100px;height:10px;overflow:hidden">
                <div style="background:{bar_color};width:{pct}%;height:100%;
                            border-radius:100px;transition:width 0.5s ease"></div>
            </div>
            <div style="text-align:center;margin-top:8px;font-size:0.82rem;
                        color:rgba(255,255,255,0.4);font-style:italic;">
                {'🎉 Amazing! You showed UP today!' if pct == 100
                 else '💛 Every habit checked is a seed planted.' if pct >= 50
                 else '🙏 Be gentle with yourself. Even one check matters.'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Habit grid
        cats = list(dict.fromkeys([h["category"] for h in habits]))
        for cat in cats:
            cat_habits = [h for h in habits if h["category"] == cat]
            cat_labels = {"faith": "✝️ Faith", "health": "💪 Health", "family": "👨‍👩‍👧 Family",
                          "community": "💛 Community", "mindset": "🧠 Mindset", "self-care": "🌸 Self-Care"}
            st.markdown(f"**{cat_labels.get(cat, cat.title())}**")
            habit_cols = st.columns(min(len(cat_habits), 4))
            for idx, habit in enumerate(cat_habits):
                with habit_cols[idx % 4]:
                    is_done = _get_habit_done(habit["id"], hab_date_str)
                    streak = _habit_streak(habit["id"])
                    ring_cls = "habit-ring done" if is_done else "habit-ring"
                    st.markdown(
                        f'<div style="text-align:center">'
                        f'<div class="{ring_cls}">{habit["icon"]}</div>'
                        f'<div style="font-size:0.78rem;color:#fff;font-weight:600">{habit["name"]}</div>'
                        f'<div style="font-size:0.7rem;color:rgba(255,255,255,0.4)">'
                        f'{"🔥 " + str(streak) + " day streak" if streak > 0 else "—"}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    btn_label = "✅ Done!" if not is_done else "↩️ Undo"
                    if st.button(btn_label, key=f"hab_{habit['id']}_{hab_date_str}",
                                 use_container_width=True,
                                 type="primary" if not is_done else "secondary"):
                        _toggle_habit(habit["id"], hab_date_str)
                        st.rerun()
                    if habit.get("scripture"):
                        st.caption(f'*"{habit["scripture"][:60]}..."*')

    st.divider()

    # 7-Day overview
    st.markdown("#### 📅 Last 7 Days")
    if habits:
        dates_7 = [TODAY - timedelta(days=i) for i in range(6, -1, -1)]
        header_row = ["Habit"] + [d.strftime("%a %m/%d") for d in dates_7]
        table_rows = []
        for h in habits:
            row = [f"{h['icon']} {h['name']}"]
            for d in dates_7:
                done = _get_habit_done(h["id"], d.isoformat())
                row.append("✅" if done else "⬜")
            table_rows.append(row)

        # Simple HTML table
        thead = "".join(f"<th style='padding:6px 10px;color:rgba(255,255,255,0.4);font-size:0.72rem;text-align:center'>{h}</th>"
                        for h in header_row)
        tbody = ""
        for row in table_rows:
            tds = "".join(f"<td style='padding:6px 10px;text-align:center;font-size:0.8rem'>{cell}</td>"
                          for cell in row)
            tbody += f"<tr>{tds}</tr>"
        st.markdown(f"""
        <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;background:#1a1a2e;border-radius:12px;overflow:hidden">
            <thead><tr style="border-bottom:1px solid rgba(255,255,255,0.08)">{thead}</tr></thead>
            <tbody>{tbody}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FAMILY HUB (3 Kids + Calendar)
# ══════════════════════════════════════════════════════════════════════════════
with tab_family:
    st.markdown("### 👨‍👩‍👧 Family Hub")
    st.caption("Keep up with your three beautiful babies — schedules, events, and everything in between.")

    kids = _load_kids()

    if not kids:
        st.info("Add your children in ⚙️ Setup to get started!")
    else:
        # Kid cards
        kid_cols = st.columns(len(kids))
        kid_colors = ["#7c6af7", "#f7936a", "#50c896"]
        for idx, (col, kid) in enumerate(zip(kid_cols, kids)):
            color = kid.get("color", kid_colors[idx % 3])
            with col:
                st.markdown(f"""
                <div class="kid-card" style="border-top:3px solid {color}">
                    <div style="font-size:2rem;margin-bottom:6px">
                        {'👦' if idx % 2 == 0 else '👧'}
                    </div>
                    <div class="kid-name">{kid['name']}</div>
                    <div class="kid-age">Age {kid.get('age','?')} · {kid.get('grade','')}</div>
                    <div style="font-size:0.78rem;color:rgba(255,255,255,0.35);margin-top:6px">
                        {kid.get('school','')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # Upcoming events
    st.markdown("#### 📅 Upcoming 2 Weeks")
    events = _load_kid_events(TODAY, TODAY + timedelta(days=14))
    if not events:
        st.info("No events yet — add them below!")
    else:
        for evt in events:
            evt_date = str(evt.get("event_date",""))[:10]
            try:
                d = date.fromisoformat(evt_date)
                days_away = (d - TODAY).days
                due_label = "TODAY" if days_away == 0 else "Tomorrow" if days_away == 1 else f"in {days_away}d"
            except Exception:
                due_label = ""
            etype = evt.get("event_type","general")
            ecolor = EVENT_COLORS.get(etype, "#b0bec5")
            kid_name = evt.get("kid_name","")
            ec1, ec2 = st.columns([5, 1])
            loc_html = f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.35);margin-top:4px">📍 {evt["location"]}</div>' if evt.get("location") else ""
            ec1.markdown(
                f'<div class="post-card" style="border-left:4px solid {ecolor}">'
                f'<div style="font-weight:700;color:#fff;font-size:0.92rem">{evt["title"]}</div>'
                f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.45);margin-top:3px">'
                f'{kid_name} · {evt_date} {evt.get("event_time","")} · '
                f'<span style="color:{ecolor}">{etype.upper()}</span> · '
                f'<span style="color:#ffc850">{due_label}</span></div>'
                f'{loc_html}'
                f'</div>',
                unsafe_allow_html=True
            )
            if ec2.button("✅ Done", key=f"evt_done_{evt['id']}"):
                conn = get_conn()
                db_exec(conn, "UPDATE mcc_kid_events SET completed=1 WHERE id=?", (evt["id"],))
                conn.commit(); conn.close()
                st.rerun()

    st.divider()
    st.markdown("#### ➕ Add Event")
    with st.form("add_event_form", clear_on_submit=True):
        ef1, ef2, ef3 = st.columns(3)
        evt_title = ef1.text_input("Event Name *", placeholder="e.g., Science Fair")
        evt_date_inp = ef2.date_input("Date", value=TODAY)
        evt_time_inp = ef3.text_input("Time", placeholder="3:30 PM")

        ef4, ef5, ef6 = st.columns(3)
        evt_kid = ef4.selectbox("Which Child", [k["name"] for k in kids] if kids else ["No kids added"])
        evt_type = ef5.selectbox("Event Type", EVENT_TYPES)
        evt_location = ef6.text_input("Location (optional)")

        evt_notes = st.text_area("Notes (optional)", height=60, placeholder="Anything to remember for this event...")

        if st.form_submit_button("💛 Add Event", type="primary", use_container_width=True):
            if evt_title.strip():
                kid_obj = next((k for k in kids if k["name"] == evt_kid), None)
                kid_id = kid_obj["id"] if kid_obj else 0
                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO mcc_kid_events (kid_id, kid_name, title, event_date, event_time, event_type, location, notes) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (kid_id, evt_kid, evt_title.strip(), evt_date_inp.isoformat(),
                     evt_time_inp.strip(), evt_type, evt_location.strip(), evt_notes.strip()))
                conn.commit(); conn.close()
                st.success(f"✅ Added: {evt_title.strip()} for {evt_kid}!")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SOCIAL MEDIA MANAGER (Christian-Centered)
# ══════════════════════════════════════════════════════════════════════════════
with tab_smm:
    st.markdown("### 📱 Social Media Manager")

    st.markdown("""
    <div class="grandma-box">
        <p>
        Your story is your ministry. The struggles you survived, the grace you walk in every day —
        that is exactly what someone scrolling at 2am needs to see. You don't need a perfect life
        to have an impactful page. You need an <em>honest</em> one.
        Post from the heart. God will handle the reach.
        </p>
    </div>
    """, unsafe_allow_html=True)

    smm_compose, smm_queue, smm_ai = st.tabs(["✍️ Compose", "📋 My Posts", "🤖 AI Caption Writer"])

    with smm_compose:
        st.markdown("#### ✍️ Create New Post")
        with st.form("smm_compose", clear_on_submit=True):
            p1, p2 = st.columns(2)
            post_title = p1.text_input("Post Title / Idea", placeholder="e.g., My healing season testimony")
            post_platform = p2.multiselect("Platforms", PLATFORMS, default=["Instagram", "Facebook"])
            post_theme = st.selectbox("Content Theme",
                                      THEMES,
                                      format_func=lambda x: {
                                          "faith": "✝️ Faith & Scripture",
                                          "family": "👨‍👩‍👧 Mom Life & Family",
                                          "testimony": "💛 My Testimony & Healing",
                                          "encouragement": "🌟 Encouragement for Others",
                                          "motherhood": "🤱 Real Motherhood Moments",
                                          "healing": "🌱 Healing Journey",
                                          "gratitude": "🙏 Gratitude & Blessings",
                                          "wisdom": "📖 Wisdom & Lessons Learned"
                                      }.get(x, x.title()))
            post_caption = st.text_area("Caption", height=180,
                                        placeholder=(
                                            "Write your caption here. Be real. Be you.\n\n"
                                            "Tip: Start with something honest — a struggle, a win, a moment with the kids.\n"
                                            "End with an encouragement or scripture.\n"
                                            "Ask a question to invite your community in."
                                        ))
            p3, p4 = st.columns(2)
            post_status = p3.selectbox("Status", ["draft", "ready", "scheduled", "posted"])
            post_schedule = p4.date_input("Schedule Date (optional)", value=None)
            media_note = st.text_input("Media Note", placeholder="e.g., Use the photo from Sunday morning, or the reel with the kids")

            if st.form_submit_button("💛 Save Post", type="primary", use_container_width=True):
                if post_title.strip():
                    conn = get_conn()
                    db_exec(conn,
                        "INSERT INTO mcc_social_posts (title, caption, platform, theme, status, scheduled_date, media_note) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (post_title.strip(), post_caption.strip(),
                         ",".join(post_platform), post_theme,
                         post_status,
                         post_schedule.isoformat() if post_schedule else None,
                         media_note.strip()))
                    conn.commit(); conn.close()
                    st.success("✅ Post saved! Your story is worth telling.")
                    st.rerun()

    with smm_queue:
        st.markdown("#### 📋 Your Post Queue")
        smm_status_filter = st.selectbox("Filter", ["all", "draft", "ready", "scheduled", "posted"],
                                          key="smm_filter")
        posts = _load_posts(None if smm_status_filter == "all" else smm_status_filter)
        if not posts:
            st.info("No posts yet — create your first one in ✍️ Compose!")
        else:
            for post in posts:
                status_colors = {
                    "draft": "#607d8b", "ready": "#ffc850",
                    "scheduled": "#4fc3f7", "posted": "#50c896"
                }
                sc = status_colors.get(post.get("status","draft"), "#607d8b")
                theme_icons = {
                    "faith": "✝️", "family": "👨‍👩‍👧", "testimony": "💛",
                    "encouragement": "🌟", "motherhood": "🤱", "healing": "🌱",
                    "gratitude": "🙏", "wisdom": "📖"
                }
                ticon = theme_icons.get(post.get("theme","faith"), "📱")
                with st.container():
                    pc1, pc2 = st.columns([5, 1])
                    pc1.markdown(
                        f'<div class="post-card" style="border-left:4px solid {sc}">'
                        f'<div style="font-weight:700;color:#fff">{ticon} {post["title"]}</div>'
                        f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.4);margin-top:3px">'
                        f'{post.get("platform","")} · '
                        f'<span style="color:{sc}">{post.get("status","draft").upper()}</span>'
                        f'{"  ·  📅 " + str(post["scheduled_date"])[:10] if post.get("scheduled_date") else ""}</div>'
                        f'<div style="font-size:0.84rem;color:rgba(255,255,255,0.65);margin-top:8px">'
                        f'{post.get("caption","")[:200]}{"..." if len(post.get("caption","")) > 200 else ""}'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )
                    with pc2:
                        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                        new_status = st.selectbox("Status",
                                                   ["draft","ready","scheduled","posted"],
                                                   index=["draft","ready","scheduled","posted"].index(
                                                       post.get("status","draft")),
                                                   key=f"smm_st_{post['id']}")
                        if new_status != post.get("status"):
                            conn = get_conn()
                            db_exec(conn, "UPDATE mcc_social_posts SET status=? WHERE id=?",
                                    (new_status, post["id"]))
                            conn.commit(); conn.close()
                            st.rerun()
                        if st.button("🗑️", key=f"smm_del_{post['id']}"):
                            conn = get_conn()
                            db_exec(conn, "DELETE FROM mcc_social_posts WHERE id=?", (post["id"],))
                            conn.commit(); conn.close()
                            st.rerun()

    with smm_ai:
        st.markdown("#### 🤖 AI Caption Writer — Rooted in Grace")
        st.caption("Tell me what's on your heart. I'll help you find the words.")

        ai_task = st.selectbox("What do you need?", [
            "Write a caption from my heart",
            "Turn my testimony into a post",
            "Write a scripture encouragement post",
            "Mama life — real and relatable",
            "Healing journey update",
            "Gratitude + faith post",
            "Content ideas for my page (30 days)",
            "Make my draft caption better",
            "Write a caption for a hard day",
        ])

        if ai_task == "Write a caption from my heart":
            topic = st.text_area("What's on your heart today?", height=100,
                                 placeholder="Just talk to me like I'm your best friend...")
            platform = st.selectbox("Platform", PLATFORMS, key="ai_plat_1")
            if st.button("💛 Write My Caption", type="primary") and topic.strip():
                with st.spinner("Writing from a place of grace..."):
                    result = _ask_ai(MOM_CONTEXT,
                        f"Platform: {platform}\n\nShe wants to post about: {topic}\n\n"
                        f"Write a heartfelt, authentic caption. Start with something real. "
                        f"Weave in faith naturally. End with a question that invites community. "
                        f"Add 10-15 relevant hashtags at the bottom.")
                st.markdown("**Your Caption:**")
                st.text_area("Copy this:", value=result, height=300, key="ai_result_1")

        elif ai_task == "Turn my testimony into a post":
            testimony = st.text_area("Share a piece of your testimony:", height=120,
                                     placeholder="What did you go through? What did God do? What do you want others to know?")
            if st.button("✝️ Write My Testimony Post", type="primary") and testimony.strip():
                with st.spinner("Turning your story into ministry..."):
                    result = _ask_ai(MOM_CONTEXT,
                        f"She wants to share this part of her testimony: {testimony}\n\n"
                        f"Write a powerful but gentle Instagram/Facebook caption. "
                        f"Honor the pain she went through. Point to God's faithfulness. "
                        f"Make it relatable for other women who've been through hard times. "
                        f"Add a short scripture that fits. End with an invitation to comment or share.")
                st.text_area("Your Testimony Post:", value=result, height=300, key="ai_result_2")

        elif ai_task == "Write a scripture encouragement post":
            topic_area = st.selectbox("Who are you speaking to?",
                                      ["Single moms", "Women healing from divorce", "Moms with ADHD/anxiety",
                                       "People going through hard times", "Young moms", "Anyone who needs hope"])
            scripture = st.text_input("Scripture (optional — I'll choose one if you leave blank)")
            if st.button("📖 Write Encouragement Post", type="primary"):
                with st.spinner("Writing words that will minister..."):
                    result = _ask_ai(MOM_CONTEXT,
                        f"Write a scripture-based encouragement post for: {topic_area}\n"
                        f"{'Use this scripture: ' + scripture if scripture.strip() else 'Choose a fitting scripture.'}\n\n"
                        f"Make it warm, real, and faith-forward. Not preachy — like a friend sharing truth. "
                        f"3-4 short paragraphs. Add hashtags.")
                st.text_area("Your Encouragement Post:", value=result, height=300, key="ai_result_3")

        elif ai_task == "Content ideas for my page (30 days)":
            page_vibe = st.text_input("Describe your page in one sentence:",
                                       placeholder="e.g., Christian single mom sharing faith, healing, and real life")
            if st.button("📅 Build My 30-Day Plan", type="primary") and page_vibe.strip():
                with st.spinner("Building your content calendar..."):
                    result = _ask_ai(MOM_CONTEXT,
                        f"Her page: {page_vibe}\n\n"
                        f"Create a 30-day social media content calendar for a Christian single mom. "
                        f"Mix of: faith posts, real motherhood moments, testimony/healing, encouragement, "
                        f"scripture of the day, and life updates. "
                        f"Format: Day | Theme | Post Idea | Hook sentence. "
                        f"Keep it simple enough for someone with ADHD — clear, not overwhelming. "
                        f"Batching-friendly (can create 3-4 posts at once).")
                st.text_area("Your 30-Day Plan:", value=result, height=400, key="ai_result_4")

        elif ai_task == "Write a caption for a hard day":
            st.markdown("""
            <div class="scripture-box">
                <div class="scripture-text">"The Lord is close to the brokenhearted and saves those who are crushed in spirit."</div>
                <div class="scripture-ref">— Psalm 34:18</div>
            </div>
            """, unsafe_allow_html=True)
            hard_day = st.text_area("What's been hard today? (You don't have to share everything — just enough for context)",
                                     height=100, placeholder="It's okay. You're safe here.")
            if st.button("💛 Write My Hard Day Post", type="primary") and hard_day.strip():
                with st.spinner("Writing from the messy middle..."):
                    result = _ask_ai(MOM_CONTEXT,
                        f"She's having a hard day: {hard_day}\n\n"
                        f"Write an authentic, raw, but hopeful social media caption for a hard day. "
                        f"It's okay to be real about the struggle. Don't bypass the pain. "
                        f"But end with a thread of hope — not toxic positivity, but real faith. "
                        f"Let it be the post that makes another struggling mom feel seen. "
                        f"Include a gentle scripture. Keep it under 300 words.")
                st.text_area("Your Caption:", value=result, height=300, key="ai_result_5")

        else:
            custom_ask = st.text_area("What do you need?", height=100,
                                       placeholder="Ask anything — I'm here to help you show up with grace.")
            if st.button("💛 Ask AI", type="primary") and custom_ask.strip():
                with st.spinner("Thinking with love..."):
                    result = _ask_ai(MOM_CONTEXT, custom_ask)
                st.text_area("AI Response:", value=result, height=300, key="ai_result_custom")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — BUDGET (Simple, Dignity-First)
# ══════════════════════════════════════════════════════════════════════════════
with tab_budget:
    st.markdown("### 💵 Family Budget")

    st.markdown("""
    <div class="grandma-box">
        <p>
        Baby, money is tight — and that doesn't mean you're failing.
        Managing a small budget with three kids takes <em>skill</em> and <em>sacrifice</em> most people can't imagine.
        This isn't about judgment. It's about helping you see your money clearly so it can work harder for you.
        Every dollar accounted for is a step forward. We're going to work with what we have — and trust God for the rest.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Month selector
    bud_month = st.selectbox("Month",
                              [TODAY.strftime("%Y-%m"),
                               (TODAY.replace(day=1) - timedelta(days=1)).strftime("%Y-%m"),
                               (TODAY.replace(day=28) + timedelta(days=4)).strftime("%Y-%m")],
                              key="bud_month")

    budget_items = _load_budget(bud_month)

    # Totals
    total_projected = sum(b.get("projected", 0) or 0 for b in budget_items)
    total_actual = sum(b.get("actual", 0) or 0 for b in budget_items)
    income_items = [b for b in budget_items if b.get("category") == "Income"]
    total_income = sum(b.get("actual", 0) or 0 for b in income_items)
    total_bills = total_actual
    remaining = total_income - total_bills

    bm1, bm2, bm3, bm4 = st.columns(4)
    bm1.metric("Total Income", f"${total_income:,.0f}")
    bm2.metric("Total Bills/Expenses", f"${total_bills:,.0f}")
    color_ind = "normal" if remaining >= 0 else "inverse"
    bm3.metric("Remaining", f"${remaining:,.0f}", delta=f"${remaining:,.0f}", delta_color=color_ind)
    paid_count = len([b for b in budget_items if b.get("paid")])
    bm4.metric("Bills Paid", f"{paid_count}/{len(budget_items)}")

    st.divider()

    # Add income / expense
    with st.expander("➕ Add Income or Expense"):
        with st.form("add_budget_item", clear_on_submit=True):
            bi1, bi2, bi3 = st.columns(3)
            bi_cat = bi1.selectbox("Category", ["Income"] + BUDGET_CATEGORIES)
            bi_item = bi2.text_input("Item Name *", placeholder="e.g., Rent, Groceries, Child support")
            bi_projected = bi3.number_input("Expected Amount ($)", min_value=0.0, step=10.0)
            bi4, bi5, bi6 = st.columns(3)
            bi_actual = bi4.number_input("Actual Amount ($)", min_value=0.0, step=10.0)
            bi_due = bi5.text_input("Due Date", placeholder="e.g., 1st, 15th, or date")
            bi_paid = bi6.checkbox("Already Paid?")
            bi_notes = st.text_input("Notes (optional)")
            if st.form_submit_button("💵 Add", type="primary", use_container_width=True) and bi_item.strip():
                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO mcc_budget (budget_month, category, item, projected, actual, due_date, paid, notes) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (bud_month, bi_cat, bi_item.strip(), bi_projected, bi_actual,
                     bi_due.strip(), 1 if bi_paid else 0, bi_notes.strip()))
                conn.commit(); conn.close()
                st.success("✅ Added!")
                st.rerun()

    # Budget table by category
    if not budget_items:
        st.info("No budget items yet — add income and bills above to get started!")
    else:
        cats_present = list(dict.fromkeys([b["category"] for b in budget_items]))
        for cat in cats_present:
            cat_items = [b for b in budget_items if b["category"] == cat]
            cat_total = sum(b.get("actual",0) or 0 for b in cat_items)
            with st.expander(f"{'💰' if cat == 'Income' else '📋'} {cat} — ${cat_total:,.0f}",
                             expanded=(cat == "Income")):
                for item in cat_items:
                    ic1, ic2, ic3, ic4, ic5 = st.columns([3, 1.5, 1.5, 1, 1])
                    ic1.markdown(f"**{item['item']}**" +
                                 (f" · *{item['due_date']}*" if item.get('due_date') else ""))
                    ic2.markdown(f"Projected: ${item.get('projected',0):,.0f}")
                    ic3.markdown(f"Actual: ${item.get('actual',0):,.0f}")
                    paid_display = "✅ PAID" if item.get("paid") else "⏳ Pending"
                    ic4.markdown(paid_display)
                    if not item.get("paid"):
                        if ic5.button("✅ Pay", key=f"pay_{item['id']}"):
                            conn = get_conn()
                            db_exec(conn, "UPDATE mcc_budget SET paid=1 WHERE id=?", (item["id"],))
                            conn.commit(); conn.close()
                            st.rerun()
                    else:
                        if ic5.button("↩️", key=f"unpay_{item['id']}"):
                            conn = get_conn()
                            db_exec(conn, "UPDATE mcc_budget SET paid=0 WHERE id=?", (item["id"],))
                            conn.commit(); conn.close()
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — LIFE COACH (AI, Christian-Centered, Grandma Energy)
# ══════════════════════════════════════════════════════════════════════════════
with tab_coach:
    st.markdown("### 💛 Life Coach")

    st.markdown("""
    <div class="grandma-box">
        <p>
        I'm here, baby. Ask me anything. I'm not here to judge you —
        I'm here to help you get through it, one step at a time.
        Whether it's a hard conversation with the kids, a rough mental health day,
        figuring out how to make the money stretch, or just needing someone to say
        <em>you're doing better than you think</em> — I'm here.
        </p>
    </div>
    """, unsafe_allow_html=True)

    coach_topic = st.selectbox("What do you need help with today?", [
        "I just need encouragement",
        "ADHD — I can't focus today",
        "Anxiety is bad today",
        "Depression — feeling really low",
        "Parenting — tough situation with one of the kids",
        "Money stress",
        "Healing from my divorce / past relationship",
        "I'm angry and I need to process it",
        "I need help setting priorities for today",
        "Social media — I'm feeling insecure about posting",
        "I'm questioning my faith today",
        "Ask your own question",
    ])

    if coach_topic == "I just need encouragement":
        if st.button("💛 Encourage Me", type="primary", use_container_width=True):
            with st.spinner("Speaking life over you..."):
                result = _ask_ai(MOM_CONTEXT,
                    "She just needs encouragement today. No specific problem — she just needs to hear something that will lift her up. "
                    "Make it personal. Make it warm. Reference the specific challenges she faces: single motherhood, ADHD, healing from trauma. "
                    "Speak to her like a wise grandmother who sees how hard she's fighting and wants her to know it's noticed by God. "
                    "End with a scripture that feels like a hug.")
            st.markdown("---")
            st.markdown(result)

    elif coach_topic == "ADHD — I can't focus today":
        context_add = st.text_area("What do you need to get done today?",
                                    placeholder="List 1-5 things. Don't worry about how — just what.",
                                    height=100)
        if st.button("🧠 Help Me Focus", type="primary") and context_add.strip():
            with st.spinner("Breaking it down gently..."):
                result = _ask_ai(MOM_CONTEXT,
                    f"She has ADHD and is struggling to focus today. She needs to get these things done: {context_add}\n\n"
                    f"Break these into the smallest possible steps. Start with the easiest win to build momentum. "
                    f"Use the body doubling technique if helpful. Give her a 'first 15 minutes' plan. "
                    f"Remind her of God's grace for neurodivergent minds. Keep it encouraging, not overwhelming.")
            st.markdown(result)

    elif coach_topic == "Anxiety is bad today":
        anxiety_note = st.text_area("What's making the anxiety worse right now?",
                                     placeholder="You don't have to explain it all — just what's at the surface.",
                                     height=80)
        if st.button("🌊 Help Me Breathe", type="primary"):
            with st.spinner("Bringing calm..."):
                anxiety_ctx = anxiety_note if anxiety_note and anxiety_note.strip() else "she shared she is feeling anxious"
                result = _ask_ai(MOM_CONTEXT,
                    f"She's struggling with anxiety today. Context: {anxiety_ctx}\n\n"
                    "Start with a grounding technique (biblical if possible). Then speak to her anxiety with compassion. "
                    "Remind her of Philippians 4:6-7. Give her 3 practical things she can do RIGHT NOW. "
                    "Keep it gentle — like a grandmother holding her hands and speaking truth over her.")
            st.markdown(result)

    elif coach_topic == "Depression — feeling really low":
        st.markdown("""
        <div class="scripture-box">
            <div class="scripture-text">"He heals the brokenhearted and binds up their wounds."</div>
            <div class="scripture-ref">— Psalm 147:3</div>
        </div>
        """, unsafe_allow_html=True)
        depr_note = st.text_area("Tell me what's going on. I'm listening.",
                                  placeholder="No judgment. No fixing. Just share.",
                                  height=100)
        if st.button("💛 Talk to Me", type="primary"):
            with st.spinner("Listening with love..."):
                result = _ask_ai(MOM_CONTEXT,
                    f"She's experiencing depression today. What she shared: {depr_note or 'she is feeling low'}\n\n"
                    f"First and most important: validate her feelings completely. Do NOT rush to fix. "
                    f"Acknowledge that depression is real, it's hard, and it doesn't mean she's weak or faithless. "
                    f"Gently remind her of God's love for the depressed (point to scriptures where God met people in their lowest). "
                    f"Give her ONE small, doable thing. Ask her to check in with her doctor if it's been ongoing. "
                    f"Be warm, slow, and full of grace.")
            st.markdown(result)
            st.warning("💛 If you're in crisis, please reach out to the 988 Suicide & Crisis Lifeline (call or text 988). You matter.")

    elif coach_topic == "Parenting — tough situation with one of the kids":
        parenting_q = st.text_area("What's going on with your child?",
                                    placeholder="What happened? How are you feeling about it? What's your goal?",
                                    height=100)
        if st.button("👨‍👩‍👧 Help Me Parent Well", type="primary") and parenting_q.strip():
            with st.spinner("Offering wise counsel..."):
                result = _ask_ai(MOM_CONTEXT,
                    f"She's dealing with a parenting challenge: {parenting_q}\n\n"
                    f"Offer practical, loving, biblically-grounded parenting guidance. "
                    f"Remember she's a single mom with ADHD managing this alone — no co-parent to lean on. "
                    f"Be honest but encouraging. If discipline is needed, frame it with love not shame. "
                    f"If she needs to set a boundary, help her find the words. "
                    f"Reference Proverbs 22:6 and related scriptures naturally.")
            st.markdown(result)

    elif coach_topic == "Ask your own question":
        custom_q = st.text_area("What's on your heart?", height=120,
                                  placeholder="Ask me anything. I'm here.")
        if st.button("💛 Ask", type="primary") and custom_q.strip():
            with st.spinner("Responding with love..."):
                result = _ask_ai(MOM_CONTEXT, custom_q)
            st.markdown(result)

    else:
        topic_prompts = {
            "Money stress": "She's stressed about money. She's a single mom of three living on a tight budget. Give her practical next steps, emotional validation, and a faith perspective. Remind her of Matthew 6:25-34. Be practical — not dismissive.",
            "Healing from my divorce / past relationship": "She's healing from her divorce and past relationship trauma. Offer gentle wisdom. Validate her pain. Point her to God's faithfulness in restoration. Remind her that her story isn't over — it's a new chapter. Reference Isaiah 43:18-19.",
            "I'm angry and I need to process it": "She's feeling angry. Help her process anger in a healthy way. Validate the anger first — it's often protective. Talk about Ephesians 4:26 'be angry but do not sin'. Give her 3 healthy outlets. Help her see what the anger might be protecting.",
            "I need help setting priorities for today": "She needs to figure out her priorities for today. She's a single mom with ADHD so simplicity is key. Help her identify the top 3 most important things and give her a simple order to tackle them. Encourage her to start with the smallest win.",
            "Social media — I'm feeling insecure about posting": "She's feeling insecure about posting on social media. Remind her that her story matters. Help her see that she doesn't need to be polished — she needs to be honest. Give her 3 reasons why her voice is needed. Remind her that God can use an imperfect post more than no post at all.",
            "I'm questioning my faith today": "She's questioning her faith. This is sacred ground — meet her with total grace and no judgment. Remind her that doubt is not the opposite of faith. Share Habakkuk, Thomas, Job — examples of believers who wrestled with God. Give her permission to bring her questions to God directly. He can handle it.",
        }
        prompt_to_use = topic_prompts.get(coach_topic, f"She needs help with: {coach_topic}")
        if st.button("💛 Help Me", type="primary", use_container_width=True):
            with st.spinner("Speaking truth in love..."):
                result = _ask_ai(MOM_CONTEXT, prompt_to_use)
            st.markdown(result)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — SETUP (Kids + Habits)
# ══════════════════════════════════════════════════════════════════════════════
with tab_setup:
    st.markdown("### ⚙️ Setup Your Command Center")

    setup_kids, setup_habits = st.tabs(["👨‍👩‍👧 My Children", "🌟 My Habits"])

    with setup_kids:
        st.markdown("#### Add Your Children")
        st.caption("Enter each child's info to personalize the Family Hub.")

        kids = _load_kids()
        if kids:
            st.markdown("**Current children:**")
            for kid in kids:
                kc1, kc2 = st.columns([4, 1])
                kc1.markdown(f"**{kid['name']}** · Age {kid.get('age','')} · {kid.get('grade','')} · {kid.get('school','')}")
                if kc2.button("🗑️", key=f"del_kid_{kid['id']}"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM mcc_kids WHERE id=?", (kid["id"],))
                    conn.commit(); conn.close()
                    st.rerun()
            st.divider()

        if len(kids) < 5:
            with st.form("add_kid_form", clear_on_submit=True):
                k1, k2 = st.columns(2)
                kid_name = k1.text_input("Child's Name *")
                kid_age = k2.number_input("Age", min_value=0, max_value=25, step=1)
                k3, k4 = st.columns(2)
                kid_grade = k3.text_input("Grade", placeholder="e.g., 3rd Grade, Kindergarten")
                kid_school = k4.text_input("School Name")
                kid_notes = st.text_area("Notes (allergies, special needs, anything important)", height=60)
                kid_color = st.color_picker("Color (for calendar display)", "#7c6af7")
                if st.form_submit_button("💛 Add Child", type="primary") and kid_name.strip():
                    conn = get_conn()
                    db_exec(conn,
                        "INSERT INTO mcc_kids (name, age, grade, school, color, notes) VALUES (?,?,?,?,?,?)",
                        (kid_name.strip(), kid_age, kid_grade.strip(), kid_school.strip(),
                         kid_color, kid_notes.strip()))
                    conn.commit(); conn.close()
                    st.success(f"✅ {kid_name.strip()} added! 💛")
                    st.rerun()
        else:
            st.info("You can have up to 5 children registered.")

    with setup_habits:
        st.markdown("#### Customize Your Habits")
        st.caption("Add, remove, or adjust your daily habits. Start small — even 3 habits is powerful.")

        habits = _load_habits()
        if habits:
            for habit in habits:
                hc1, hc2 = st.columns([4, 1])
                hc1.markdown(f"{habit['icon']} **{habit['name']}** · *{habit['category']}*")
                if habit.get("scripture"):
                    hc1.caption(f'*"{habit["scripture"][:80]}"*')
                if hc2.button("🗑️", key=f"del_hab_{habit['id']}"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM mcc_habits WHERE id=?", (habit["id"],))
                    conn.commit(); conn.close()
                    st.rerun()
            st.divider()

        with st.form("add_habit_form", clear_on_submit=True):
            h1, h2 = st.columns(2)
            hab_name = h1.text_input("Habit Name *", placeholder="e.g., Evening Prayer")
            hab_icon = h2.text_input("Icon (emoji)", placeholder="🙏", value="🌟")
            h3, h4 = st.columns(2)
            hab_cat = h3.selectbox("Category", ["faith", "health", "family", "mindset", "community", "self-care"])
            hab_scripture = h4.text_input("Linked Scripture (optional)",
                                           placeholder="e.g., Psalm 46:5")
            if st.form_submit_button("➕ Add Habit", type="primary") and hab_name.strip():
                conn = get_conn()
                db_exec(conn, "INSERT INTO mcc_habits (name, icon, category, scripture) VALUES (?,?,?,?)",
                        (hab_name.strip(), hab_icon.strip() or "🌟", hab_cat, hab_scripture.strip()))
                conn.commit(); conn.close()
                st.success(f"✅ '{hab_name}' added!")
                st.rerun()

        st.divider()
        st.markdown("#### 💛 A Note on Habits & ADHD")
        st.markdown("""
        <div class="grandma-box">
            <p>
            Honey, you don't need 20 habits. You need 3-5 that feel doable even on your worst day.
            Start with: morning prayer, drink water, and connect with your kids.
            That's it. Build from there. Every day you show up — even imperfectly — is a seed planted.
            "She opens her hand to the poor and reaches out her hands to the needy." — Proverbs 31:20.
            That starts with you being gentle with <em>yourself</em>.
            </p>
        </div>
        """, unsafe_allow_html=True)
