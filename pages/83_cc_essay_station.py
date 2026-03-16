"""
College Confused — Essay Development Station (Page 83)
AI-powered essay writing & coaching, trained on Darrian Belcher's winning essay style.
"""

import os
import streamlit as st
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting, is_cc_ai_allowed

st.set_page_config(
    page_title="Essay Station — College Confused",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()

from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_cc_css

inject_cc_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Confused")
st.sidebar.page_link("pages/80_cc_home.py",           label="🏠 Home",              icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py",       label="📅 My Timeline",       icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",   label="💰 Scholarships",      icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",  label="✍️ Essay Station",     icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",      label="📚 SAT/ACT Prep",      icon="📚")
st.sidebar.markdown("---")
render_sidebar_user_widget()

# ── Constants ─────────────────────────────────────────────────────────────────

DARRIAN_ESSAY_CONTEXT = """
DARRIAN BELCHER'S COLLEGE ESSAY STYLE & WINNING APPROACH:

BACKGROUND: Darrian Belcher is the founder of College Confused. He applied to 30+ colleges his senior year, received 25 acceptances, 10+ full rides, and $1M+ in scholarships. He won the VISA Black Scholars program ($20,000/year), Trajectory Foundation Scholarship ($5,000/year), and multiple full rides including VCU, Virginia State, Alabama A&M, Fisk, Xavier University of Louisiana, Bethune Cookman, and William & Mary.

WRITING STYLE CHARACTERISTICS:
1. Opens with a vivid, cinematic scene that pulls the reader in immediately (e.g., "Apron? Check. Work hat? Check. Slip-resistant shoes? Check.")
2. Uses personal, authentic voice — writes like he's talking to a trusted friend
3. Connects personal challenges to larger purpose and goals
4. Shows growth and resilience without being overly dramatic
5. Weaves in specific details (real names, places, numbers) to make stories real
6. Links personal story to career goals and community impact
7. Ends with forward-looking purpose statement
8. Themes: Technology passion, family sacrifice, low-income background, resilience after adversity (house fire, parents' divorce), wanting to give back
9. Tone: Optimistic, determined, grateful, community-focused
10. NEVER sounds like bragging — focuses on growth and impact on others

KEY ESSAY THEMES FROM HIS ESSAYS:
- The house fire in 2019 that destroyed everything — taught him what truly matters (family)
- Working at McDonald's to help support his family
- Parents' divorce and moving to a new city
- Using Chromebooks to discover passion for technology
- Flipping sneakers to earn money, connecting to technology interest
- Being accepted to Governor's School of Science and Technology
- Creating College Confused website during GSST fellowship
- Volunteering at Virginia Peninsula Food Bank
- Track team — learning discipline, teamwork, overcoming setbacks

STRUCTURAL APPROACH:
1. Hook (cinematic opening or surprising statement)
2. Context (what was happening/situation)
3. Challenge/Conflict (what made it hard)
4. Action (what he did about it)
5. Growth (what he learned)
6. Connection to Future (how this shapes his goals)
7. Closing Vision (where he's headed)

WHAT MAKES HIS ESSAYS STAND OUT:
- Specific over general: "I applied to 40 scholarships and won 9" not "I applied to many scholarships"
- Vulnerability + strength: Shows struggle while showing he overcame it
- Purpose-driven: Every story connects back to wanting to help others
- Authentic voice: Doesn't try to sound like someone else
- No clichés: Avoids "ever since I was little" and "in today's society"
"""

ESSAY_TYPES = [
    "Common App Personal Statement",
    "Supplemental Essay",
    "Scholarship Essay",
    "Why This College",
]

STATUS_OPTIONS = ["Draft", "In Progress", "Final", "Submitted"]

COMMON_APP_PROMPTS = [
    {
        "number": 1,
        "prompt": "Some students have a background, identity, interest, or talent that is so meaningful they believe their application would be incomplete without it. If this sounds like you, then please share your story.",
        "what_asking": "Tell us something central to who you are — a defining part of your identity, passion, or background.",
        "great_response": "Pick ONE thing (not everything). Go deep, not wide. Show how it shapes how you see the world.",
        "avoid": "Listing accomplishments. Being vague. Saying 'I've always been passionate about...'",
        "hook_idea": "Start in the middle of a moment — mid-practice, mid-experiment, mid-game. Drop us in.",
    },
    {
        "number": 2,
        "prompt": "The lessons we take from obstacles we encounter can be fundamental to later success. Recount a time when you faced a challenge, setback, or failure. How did it affect you, and what did you learn from the experience?",
        "what_asking": "Show us how you handle hard things. Admissions wants to see resilience and self-awareness.",
        "great_response": "Be honest and vulnerable. The lesson must be specific, not generic ('I learned to persevere').",
        "avoid": "Picking a minor challenge. Skipping the lesson. Making it sound like you have everything figured out.",
        "hook_idea": "Open at the worst moment — the phone call, the grade, the loss. Put us right there with you.",
    },
    {
        "number": 3,
        "prompt": "Reflect on a time when you questioned or challenged a belief or idea. What prompted your thinking? What was the outcome?",
        "what_asking": "Demonstrate critical thinking and intellectual courage. Show you can think for yourself.",
        "great_response": "Pick a genuine belief you changed your mind about. Be honest about why you believed what you did before.",
        "avoid": "Picking something safe or cliché. Not showing your actual thought process. Being preachy.",
        "hook_idea": "Start with the old belief stated confidently — then the moment everything shifted.",
    },
    {
        "number": 4,
        "prompt": "Reflect on something that someone has done for you that has made you happy or thankful in a surprising way. How has this gratitude affected or motivated you?",
        "what_asking": "Show your capacity for gratitude, humility, and how relationships shape you.",
        "great_response": "Make it about a specific person and a specific moment. Surprise is key — unexpected kindness hits hardest.",
        "avoid": "Generic thank-you to parents. Vague gratitude. Not connecting it to your life going forward.",
        "hook_idea": "Describe the exact moment — the person's face, their words, where you were standing.",
    },
    {
        "number": 5,
        "prompt": "Discuss an accomplishment, event, or realization that sparked a period of personal growth and a new understanding of yourself or others.",
        "what_asking": "Show self-awareness and growth. Admissions wants to see you evolve through an experience.",
        "great_response": "Focus more on the 'new understanding' than the accomplishment itself. The growth is the story.",
        "avoid": "Turning it into a brag. Not explaining what actually changed inside you.",
        "hook_idea": "Start after the accomplishment — in the quiet moment of reflection, or the surprising emotion you felt.",
    },
    {
        "number": 6,
        "prompt": "Describe a topic, idea, or concept you find so engaging that it makes you lose all track of time. Why does it captivate you? What or who do you turn to when you want to learn more?",
        "what_asking": "Show intellectual passion and curiosity. What drives you to learn?",
        "great_response": "Get specific — name the exact topic, the exact resource, the exact rabbit hole. Show the obsession.",
        "avoid": "Picking something generic. Not showing WHY it captivates you personally.",
        "hook_idea": "Open at 2am, deep in research, losing track of time — show us the obsession in action.",
    },
    {
        "number": 7,
        "prompt": "Share an essay on any topic of your choice.",
        "what_asking": "Total creative freedom — tell us something meaningful about you that no other prompt captures.",
        "great_response": "This is your chance to be bold. Pick the story that only YOU can tell.",
        "avoid": "Picking a 'safe' topic because you have freedom. This is the prompt to take the biggest swing.",
        "hook_idea": "Open with your most unexpected, memorable, or surprising sentence — something they've never read before.",
    },
]

# ── DB helpers ────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_essays (
        id {ai},
        user_email TEXT NOT NULL,
        title TEXT NOT NULL,
        prompt TEXT DEFAULT '',
        content TEXT DEFAULT '',
        essay_type TEXT DEFAULT 'common_app',
        word_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Draft',
        ai_feedback TEXT DEFAULT '',
        version INTEGER DEFAULT 1,
        created_at TEXT {ts},
        updated_at TEXT {ts}
    )""")

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_essay_versions (
        id {ai},
        essay_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        saved_at TEXT {ts}
    )""")

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_student_story (
        id {ai},
        user_email TEXT NOT NULL,
        background TEXT DEFAULT '',
        challenges TEXT DEFAULT '',
        achievements TEXT DEFAULT '',
        extracurriculars TEXT DEFAULT '',
        career_goals TEXT DEFAULT '',
        why_college TEXT DEFAULT '',
        unique_qualities TEXT DEFAULT '',
        updated_at TEXT {ts}
    )""")

    conn.commit()
    conn.close()


def _get_essays(user_email: str) -> list:
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"
    c = db_exec(conn, f"SELECT * FROM cc_essays WHERE user_email = {p} ORDER BY updated_at DESC", (user_email,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return []
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


def _get_essay(essay_id: int) -> dict | None:
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"
    c = db_exec(conn, f"SELECT * FROM cc_essays WHERE id = {p}", (essay_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return dict(zip(cols, row))
    return dict(row)


def _save_essay(user_email: str, title: str, prompt: str, content: str,
                essay_type: str, status: str, essay_id: int | None = None) -> int:
    word_count = len(content.split()) if content.strip() else 0
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"

    if essay_id:
        # Get current version
        c = db_exec(conn, f"SELECT version, content FROM cc_essays WHERE id = {p}", (essay_id,))
        row = c.fetchone()
        if row:
            old_version = row[0] if USE_POSTGRES else row["version"]
            old_content = row[1] if USE_POSTGRES else row["content"]
            new_version = old_version + 1
            # Save version history
            db_exec(conn, f"""INSERT INTO cc_essay_versions (essay_id, content, version)
                              VALUES ({p}, {p}, {p})""", (essay_id, old_content, old_version))

        if USE_POSTGRES:
            db_exec(conn, """UPDATE cc_essays SET title=%s, prompt=%s, content=%s,
                             essay_type=%s, word_count=%s, status=%s, version=%s,
                             updated_at=to_char(now(),'YYYY-MM-DD HH24:MI:SS')
                             WHERE id=%s""",
                    (title, prompt, content, essay_type, word_count, status, new_version, essay_id))
        else:
            db_exec(conn, """UPDATE cc_essays SET title=?, prompt=?, content=?,
                             essay_type=?, word_count=?, status=?, version=?,
                             updated_at=datetime('now')
                             WHERE id=?""",
                    (title, prompt, content, essay_type, word_count, status, new_version, essay_id))
        conn.commit()
        conn.close()
        return essay_id
    else:
        if USE_POSTGRES:
            c = db_exec(conn, """INSERT INTO cc_essays (user_email, title, prompt, content,
                                 essay_type, word_count, status)
                                 VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (user_email, title, prompt, content, essay_type, word_count, status))
            new_id = c.fetchone()[0]
        else:
            c = db_exec(conn, """INSERT INTO cc_essays (user_email, title, prompt, content,
                                 essay_type, word_count, status)
                                 VALUES (?,?,?,?,?,?,?)""",
                        (user_email, title, prompt, content, essay_type, word_count, status))
            new_id = c.lastrowid
        conn.commit()
        conn.close()
        return new_id


def _save_ai_feedback(essay_id: int, feedback: str):
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        db_exec(conn, f"UPDATE cc_essays SET ai_feedback={p}, updated_at=to_char(now(),'YYYY-MM-DD HH24:MI:SS') WHERE id={p}",
                (feedback, essay_id))
    else:
        db_exec(conn, f"UPDATE cc_essays SET ai_feedback={p}, updated_at=datetime('now') WHERE id={p}",
                (feedback, essay_id))
    conn.commit()
    conn.close()


def _delete_essay(essay_id: int):
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"DELETE FROM cc_essay_versions WHERE essay_id = {p}", (essay_id,))
    db_exec(conn, f"DELETE FROM cc_essays WHERE id = {p}", (essay_id,))
    conn.commit()
    conn.close()


def _get_essay_versions(essay_id: int) -> list:
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"
    c = db_exec(conn, f"SELECT * FROM cc_essay_versions WHERE essay_id = {p} ORDER BY version DESC", (essay_id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return []
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


def _get_story(user_email: str) -> dict:
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"
    c = db_exec(conn, f"SELECT * FROM cc_student_story WHERE user_email = {p} ORDER BY id DESC LIMIT 1", (user_email,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {}
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return dict(zip(cols, row))
    return dict(row)


def _save_story(user_email: str, background: str, challenges: str, achievements: str,
                extracurriculars: str, career_goals: str, why_college: str, unique_qualities: str):
    conn = get_conn()
    p = "%s" if USE_POSTGRES else "?"
    # Check if existing record
    c = db_exec(conn, f"SELECT id FROM cc_student_story WHERE user_email = {p}", (user_email,))
    row = c.fetchone()
    if row:
        existing_id = row[0] if USE_POSTGRES else row["id"]
        if USE_POSTGRES:
            db_exec(conn, """UPDATE cc_student_story SET background=%s, challenges=%s, achievements=%s,
                             extracurriculars=%s, career_goals=%s, why_college=%s, unique_qualities=%s,
                             updated_at=to_char(now(),'YYYY-MM-DD HH24:MI:SS') WHERE id=%s""",
                    (background, challenges, achievements, extracurriculars,
                     career_goals, why_college, unique_qualities, existing_id))
        else:
            db_exec(conn, """UPDATE cc_student_story SET background=?, challenges=?, achievements=?,
                             extracurriculars=?, career_goals=?, why_college=?, unique_qualities=?,
                             updated_at=datetime('now') WHERE id=?""",
                    (background, challenges, achievements, extracurriculars,
                     career_goals, why_college, unique_qualities, existing_id))
    else:
        if USE_POSTGRES:
            db_exec(conn, """INSERT INTO cc_student_story (user_email, background, challenges, achievements,
                             extracurriculars, career_goals, why_college, unique_qualities)
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (user_email, background, challenges, achievements, extracurriculars,
                     career_goals, why_college, unique_qualities))
        else:
            db_exec(conn, """INSERT INTO cc_student_story (user_email, background, challenges, achievements,
                             extracurriculars, career_goals, why_college, unique_qualities)
                             VALUES (?,?,?,?,?,?,?,?)""",
                    (user_email, background, challenges, achievements, extracurriculars,
                     career_goals, why_college, unique_qualities))
    conn.commit()
    conn.close()


# ── AI helpers ────────────────────────────────────────────────────────────────

def _generate_essay_draft(prompt_text: str, essay_type: str, story: dict, darrian_style: bool, user_email: str = "") -> str:
    if not is_cc_ai_allowed(user_email):
        return "🚀 AI Essay Builder is coming soon to College Confused! Check the **Examples & Tips** tab for essay strategies and tips from Darrian's real winning essays."
    api_key = os.environ.get("CC_ANTHROPIC_API_KEY") or get_setting("cc_anthropic_api_key", "")
    if not api_key:
        return "⚠️ No API key configured. Please ask an admin to configure the Anthropic API key in Settings."

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        style_section = f"\n\n{DARRIAN_ESSAY_CONTEXT}\n\nUse Darrian's writing style and approach as your model." if darrian_style else ""

        story_section = f"""
Student's Background Information:
- Background/Who they are: {story.get('background', 'Not provided')}
- Challenges they've overcome: {story.get('challenges', 'Not provided')}
- Achievements and proud moments: {story.get('achievements', 'Not provided')}
- Extracurricular activities: {story.get('extracurriculars', 'Not provided')}
- Career goals: {story.get('career_goals', 'Not provided')}
- Why they want to go to college: {story.get('why_college', 'Not provided')}
- What makes them unique: {story.get('unique_qualities', 'Not provided')}
""" if story else ""

        word_limits = {
            "Common App Personal Statement": "650",
            "Supplemental Essay": "250-650",
            "Scholarship Essay": "500",
            "Why This College": "300-500",
        }
        word_limit = word_limits.get(essay_type, "650")

        system_prompt = f"""You are an expert college essay coach who has helped hundreds of students get into their dream schools and win scholarships.{style_section}

Your goal is to help students write authentic, compelling essays that tell THEIR story in THEIR voice.

Essay Type: {essay_type}
Word Limit: {word_limit} words

{story_section}

Essay Prompt: {prompt_text}

Write a compelling draft essay that:
1. Opens with a vivid hook (specific scene, not a generic statement)
2. Uses authentic, personal voice
3. Tells a specific story with real details
4. Shows growth and learning
5. Connects to future goals
6. Stays within word limit
7. Does NOT sound generic or AI-written
8. Uses the student's real background information provided above

After the essay, provide 3 specific suggestions for how to make it even more personal and authentic."""

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": system_prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI Error: {e}"


def _get_essay_feedback(essay_text: str, prompt_text: str, essay_type: str, user_email: str = "") -> str:
    if not is_cc_ai_allowed(user_email):
        return "🚀 AI Feedback is coming soon! In the meantime, use the **7 Things That Make Essays Great** in the Examples & Tips tab to self-review your essay."
    api_key = os.environ.get("CC_ANTHROPIC_API_KEY") or get_setting("cc_anthropic_api_key", "")
    if not api_key:
        return "⚠️ No API key configured. Please ask an admin to configure the Anthropic API key in Settings."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""You are an expert college essay reviewer. Review this {essay_type} essay and provide specific, actionable feedback.

Essay Prompt: {prompt_text}

Essay:
{essay_text}

{DARRIAN_ESSAY_CONTEXT}

Provide feedback in this format:
## Overall Assessment (2-3 sentences)

## What's Working Well ✅
(3-5 specific strengths)

## Areas to Improve 🔧
(3-5 specific, actionable suggestions with examples)

## Opening Hook Analysis
(Is it strong enough? How could it be stronger?)

## Authenticity Check
(Does it sound like a real person? What feels generic?)

## Closing Strength
(Is the ending memorable? Suggestions to make it stronger)

## One Sentence to Add
(Write one powerful sentence they could add to strengthen the essay)

Keep feedback encouraging and constructive. This student worked hard on this."""

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"Error: {e}"


# ── Session state helpers ─────────────────────────────────────────────────────

def _init_session():
    defaults = {
        "cc_essay_editing_id": None,
        "cc_essay_draft_result": "",
        "cc_feedback_result": "",
        "cc_essay_saved_msg": "",
        "cc_builder_saved_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Page render ───────────────────────────────────────────────────────────────

_ensure_tables()
_init_session()

user = st.session_state.get("user", {})
user_email = user.get("email", "anonymous")

# Header
st.markdown("""
<div style="margin-bottom: 8px;">
    <h1 style="margin-bottom: 4px;">✍️ Essay Development Station</h1>
    <p style="color: #8892a4; font-size: 1.05rem; margin: 0;">
        Write your best story. AI trained on real winning essays will help you every step of the way.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📝 My Essays",
    "🤖 AI Essay Builder",
    "📖 Examples & Tips",
    "🗂️ My Story Profile",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: MY ESSAYS
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    essays = _get_essays(user_email)

    col_header, col_new = st.columns([3, 1])
    with col_header:
        st.markdown("### 📝 My Essays")
        st.caption(f"You have **{len(essays)}** essay{'s' if len(essays) != 1 else ''} saved.")
    with col_new:
        if st.button("➕ New Essay", type="primary", use_container_width=True, key="new_essay_btn"):
            st.session_state["cc_essay_editing_id"] = "new"

    st.markdown("")

    # ── Essay list ────────────────────────────────────────────────────────────
    if essays and st.session_state["cc_essay_editing_id"] is None:
        status_colors = {
            "Draft": "#8892a4",
            "In Progress": "#FFAB76",
            "Final": "#5bc67e",
            "Submitted": "#4a9eff",
        }
        for essay in essays:
            with st.expander(
                f"{'📄' if essay['status'] == 'Draft' else '✏️' if essay['status'] == 'In Progress' else '✅' if essay['status'] == 'Final' else '🎓'} "
                f"**{essay['title']}** — {essay['essay_type']} · {essay['word_count']} words",
                expanded=False,
            ):
                col_info, col_actions = st.columns([3, 1])
                with col_info:
                    status_color = status_colors.get(essay["status"], "#8892a4")
                    st.markdown(
                        f"**Status:** <span style='color:{status_color}; font-weight:600;'>{essay['status']}</span> &nbsp;|&nbsp; "
                        f"**Version:** {essay['version']} &nbsp;|&nbsp; "
                        f"**Updated:** {str(essay['updated_at'])[:16]}",
                        unsafe_allow_html=True,
                    )
                    if essay.get("prompt"):
                        st.caption(f"📋 Prompt: {essay['prompt'][:120]}{'...' if len(essay['prompt']) > 120 else ''}")
                    if essay.get("content"):
                        preview = essay["content"][:300].strip()
                        st.markdown(f"> {preview}{'...' if len(essay['content']) > 300 else ''}")
                with col_actions:
                    if st.button("✏️ Edit", key=f"edit_{essay['id']}", use_container_width=True):
                        st.session_state["cc_essay_editing_id"] = essay["id"]
                        st.rerun()
                    if st.button("🗑️ Delete", key=f"del_{essay['id']}", use_container_width=True):
                        _delete_essay(essay["id"])
                        st.success("Essay deleted.")
                        st.rerun()

                # AI feedback if available
                if essay.get("ai_feedback"):
                    with st.expander("🤖 Last AI Feedback", expanded=False):
                        st.markdown(essay["ai_feedback"])

    elif not essays and st.session_state["cc_essay_editing_id"] is None:
        st.info("No essays yet. Click **➕ New Essay** to start writing, or use the **AI Essay Builder** tab to generate a draft.")

    # ── Essay editor ──────────────────────────────────────────────────────────
    if st.session_state["cc_essay_editing_id"] is not None:
        editing_id = st.session_state["cc_essay_editing_id"]
        is_new = editing_id == "new"

        existing = None if is_new else _get_essay(editing_id)

        st.markdown("---")
        col_back, col_title_header = st.columns([1, 5])
        with col_back:
            if st.button("← Back", key="back_to_list"):
                st.session_state["cc_essay_editing_id"] = None
                st.session_state["cc_feedback_result"] = ""
                st.rerun()
        with col_title_header:
            st.markdown(f"### {'✨ New Essay' if is_new else '✏️ Edit Essay'}")

        with st.form("essay_editor_form", clear_on_submit=False):
            col_left, col_right = st.columns([3, 1])
            with col_left:
                title = st.text_input(
                    "Essay Title",
                    value="" if is_new else (existing or {}).get("title", ""),
                    placeholder="e.g., Common App Personal Statement — Draft 1",
                    max_chars=200,
                )
            with col_right:
                essay_type = st.selectbox(
                    "Essay Type",
                    ESSAY_TYPES,
                    index=0 if is_new else (
                        ESSAY_TYPES.index((existing or {}).get("essay_type", "Common App Personal Statement"))
                        if (existing or {}).get("essay_type") in ESSAY_TYPES else 0
                    ),
                )

            prompt_text = st.text_area(
                "Essay Prompt (paste the prompt you're responding to)",
                value="" if is_new else (existing or {}).get("prompt", ""),
                placeholder="Paste the exact essay prompt here...",
                height=80,
            )

            content = st.text_area(
                "Your Essay",
                value="" if is_new else (existing or {}).get("content", ""),
                placeholder="Start writing your essay here...\n\nTip: Don't try to be perfect on the first draft. Just get your story down!",
                height=380,
            )

            word_count_live = len(content.split()) if content.strip() else 0
            wc_color = "#5bc67e" if word_count_live <= 650 else "#ff6b6b"
            st.markdown(
                f"<div style='text-align:right; font-size:0.85rem; color:{wc_color}; margin-top:-8px;'>"
                f"Word count: <strong>{word_count_live}</strong></div>",
                unsafe_allow_html=True,
            )

            col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
            with col_s1:
                status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index((existing or {}).get("status", "Draft"))
                    if (existing or {}).get("status") in STATUS_OPTIONS else 0,
                )
            with col_s2:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)

            col_save, col_feedback, col_spacer = st.columns([1, 1, 2])
            with col_save:
                save_clicked = st.form_submit_button("💾 Save Essay", type="primary", use_container_width=True)
            with col_feedback:
                feedback_clicked = st.form_submit_button("🤖 Get AI Feedback", use_container_width=True)

            if save_clicked:
                if not title.strip():
                    st.error("Please give your essay a title.")
                else:
                    saved_id = _save_essay(
                        user_email=user_email,
                        title=title.strip(),
                        prompt=prompt_text.strip(),
                        content=content,
                        essay_type=essay_type,
                        status=status,
                        essay_id=None if is_new else editing_id,
                    )
                    st.session_state["cc_essay_editing_id"] = saved_id
                    st.success(f"✅ Essay saved! (Version updated, {word_count_live} words)")
                    st.rerun()

            if feedback_clicked:
                if not content.strip():
                    st.error("Please write something first before getting feedback.")
                else:
                    with st.spinner("🤖 AI is reading your essay..."):
                        feedback = _get_essay_feedback(content, prompt_text, essay_type, user_email)
                    if not is_new and editing_id:
                        _save_ai_feedback(editing_id, feedback)
                    st.session_state["cc_feedback_result"] = feedback

        # Show feedback outside the form
        if st.session_state.get("cc_feedback_result"):
            st.markdown("---")
            st.markdown("### 🤖 AI Essay Feedback")
            st.markdown(
                "<div style='background:#12151c; border:1px solid #1e2330; border-radius:12px; padding:20px; margin-top:8px;'>"
                + st.session_state["cc_feedback_result"].replace("\n", "<br>")
                + "</div>",
                unsafe_allow_html=True,
            )
            if st.button("Clear Feedback", key="clear_feedback"):
                st.session_state["cc_feedback_result"] = ""
                st.rerun()

        # Version history
        if not is_new and editing_id and editing_id != "new":
            versions = _get_essay_versions(editing_id)
            if versions:
                with st.expander(f"🕐 Version History ({len(versions)} saved versions)", expanded=False):
                    for v in versions:
                        v_wc = len(v["content"].split()) if v["content"].strip() else 0
                        st.markdown(
                            f"**Version {v['version']}** — {v_wc} words — saved {str(v['saved_at'])[:16]}"
                        )
                        st.markdown(
                            f"> {v['content'][:200].strip()}{'...' if len(v['content']) > 200 else ''}"
                        )
                        st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: AI ESSAY BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🤖 AI Essay Builder")
    st.markdown(
        "This AI is trained on Darrian Belcher's winning essay style — "
        "he won **$1M+ in scholarships** and **10+ full rides**. "
        "Let it help you write and improve your essays."
    )

    story = _get_story(user_email)
    has_story = any([
        story.get("background"), story.get("challenges"), story.get("achievements"),
        story.get("extracurriculars"), story.get("career_goals"),
    ])

    if not has_story:
        st.warning(
            "💡 **Tip:** Fill out your **My Story Profile** (Tab 4) first so the AI can personalize your essay "
            "with YOUR details. Without it, the AI will write a more generic draft."
        )

    builder_mode = st.radio(
        "What do you want to do?",
        ["✨ Build a New Essay Draft", "🔧 Improve My Existing Essay"],
        horizontal=True,
    )

    st.markdown("---")

    # ── Mode A: Build from Story ──────────────────────────────────────────────
    if builder_mode == "✨ Build a New Essay Draft":
        st.markdown("#### ✨ Build a Draft from Your Story")
        st.caption("The AI will use your story profile and Darrian's writing style to generate a first draft.")

        col_a1, col_a2 = st.columns([1, 1])
        with col_a1:
            build_essay_type = st.selectbox("Essay Type", ESSAY_TYPES, key="build_type")
        with col_a2:
            darrian_style = st.checkbox(
                "🏆 Use Darrian's writing style as model",
                value=True,
                help="When checked, the AI will model your essay after Darrian Belcher's award-winning writing style.",
            )

        build_prompt = st.text_area(
            "Paste the Essay Prompt",
            placeholder="Paste the full essay prompt here. The more specific the prompt, the better the draft.",
            height=100,
            key="build_prompt_input",
        )

        if has_story:
            with st.expander("📋 Your Story Profile (used by AI)", expanded=False):
                if story.get("background"):
                    st.markdown(f"**Background:** {story['background']}")
                if story.get("challenges"):
                    st.markdown(f"**Challenges:** {story['challenges']}")
                if story.get("achievements"):
                    st.markdown(f"**Achievements:** {story['achievements']}")
                if story.get("extracurriculars"):
                    st.markdown(f"**Extracurriculars:** {story['extracurriculars']}")
                if story.get("career_goals"):
                    st.markdown(f"**Career Goals:** {story['career_goals']}")
                if story.get("why_college"):
                    st.markdown(f"**Why College:** {story['why_college']}")
                if story.get("unique_qualities"):
                    st.markdown(f"**Unique Qualities:** {story['unique_qualities']}")

        col_gen, col_spacer = st.columns([1, 3])
        with col_gen:
            gen_clicked = st.button(
                "🚀 Generate Essay Draft",
                type="primary",
                use_container_width=True,
                key="generate_draft_btn",
            )

        if gen_clicked:
            if not build_prompt.strip():
                st.error("Please paste an essay prompt first.")
            else:
                with st.spinner("✍️ Writing your essay draft... (this takes 15-30 seconds)"):
                    result = _generate_essay_draft(
                        prompt_text=build_prompt,
                        essay_type=build_essay_type,
                        story=story,
                        darrian_style=darrian_style,
                        user_email=user_email,
                    )
                st.session_state["cc_essay_draft_result"] = result
                st.session_state["cc_builder_saved_id"] = None

        if st.session_state.get("cc_essay_draft_result"):
            st.markdown("---")
            st.markdown("#### 📄 Generated Draft")
            st.markdown(
                "<div style='background:#12151c; border:1px solid #1e2330; border-radius:12px; "
                "padding:20px; margin-top:8px; white-space:pre-wrap;'>"
                + st.session_state["cc_essay_draft_result"]
                + "</div>",
                unsafe_allow_html=True,
            )

            draft_wc = len(st.session_state["cc_essay_draft_result"].split())
            st.caption(f"~{draft_wc} words in generated output (includes suggestions)")

            st.markdown("##### 💾 Save this draft to My Essays?")
            save_col1, save_col2 = st.columns([2, 1])
            with save_col1:
                draft_save_title = st.text_input(
                    "Essay title",
                    value=f"{build_essay_type} — AI Draft",
                    key="draft_save_title",
                    max_chars=200,
                )
            with save_col2:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("💾 Save to My Essays", key="save_draft_to_essays", type="primary"):
                    if st.session_state.get("cc_builder_saved_id"):
                        st.info("Already saved! Go to **📝 My Essays** tab to edit it.")
                    else:
                        saved_id = _save_essay(
                            user_email=user_email,
                            title=draft_save_title.strip() or f"{build_essay_type} — AI Draft",
                            prompt=build_prompt.strip(),
                            content=st.session_state["cc_essay_draft_result"],
                            essay_type=build_essay_type,
                            status="Draft",
                        )
                        st.session_state["cc_builder_saved_id"] = saved_id
                        st.success(f"✅ Saved! Go to **📝 My Essays** to edit and refine it.")

            if st.button("🗑️ Clear Draft", key="clear_draft_btn"):
                st.session_state["cc_essay_draft_result"] = ""
                st.session_state["cc_builder_saved_id"] = None
                st.rerun()

    # ── Mode B: Improve My Essay ──────────────────────────────────────────────
    else:
        st.markdown("#### 🔧 Improve My Existing Essay")
        st.caption("Paste your essay below and the AI will give you detailed, specific feedback.")

        col_b1, col_b2 = st.columns([1, 1])
        with col_b1:
            improve_type = st.selectbox("Essay Type", ESSAY_TYPES, key="improve_type")

        improve_prompt = st.text_area(
            "Essay Prompt (optional but recommended)",
            placeholder="Paste the prompt your essay is responding to...",
            height=70,
            key="improve_prompt_input",
        )

        improve_essay = st.text_area(
            "Your Essay",
            placeholder="Paste your full essay here...",
            height=300,
            key="improve_essay_input",
        )

        if improve_essay.strip():
            wc = len(improve_essay.split())
            wc_color = "#5bc67e" if wc <= 650 else "#ff6b6b"
            st.markdown(
                f"<div style='text-align:right; font-size:0.85rem; color:{wc_color};'>"
                f"Word count: <strong>{wc}</strong></div>",
                unsafe_allow_html=True,
            )

        col_fb, col_sp = st.columns([1, 3])
        with col_fb:
            fb_clicked = st.button(
                "🤖 Get AI Feedback",
                type="primary",
                use_container_width=True,
                key="get_feedback_btn_b",
            )

        if fb_clicked:
            if not improve_essay.strip():
                st.error("Please paste your essay first.")
            else:
                with st.spinner("🤖 Reading and analyzing your essay..."):
                    fb_result = _get_essay_feedback(improve_essay, improve_prompt, improve_type, user_email)
                st.session_state["cc_feedback_result_b"] = fb_result

        if st.session_state.get("cc_feedback_result_b"):
            st.markdown("---")
            st.markdown("### 🤖 AI Essay Feedback")
            st.markdown(
                "<div style='background:#12151c; border:1px solid #1e2330; border-radius:12px; "
                "padding:20px; margin-top:8px;'>"
                + st.session_state["cc_feedback_result_b"]
                + "</div>",
                unsafe_allow_html=True,
            )
            if st.button("Clear Feedback", key="clear_feedback_b"):
                st.session_state["cc_feedback_result_b"] = ""
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: ESSAY EXAMPLES & TIPS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📖 Essay Examples & Tips")

    section = st.radio(
        "What do you want to explore?",
        ["📋 Common App Prompts (2024–2025)", "🏆 7 Things That Make Essays Great", "❌ 5 Common Mistakes", "🔍 How to Find Your Topic"],
        horizontal=True,
    )

    st.markdown("---")

    if section == "📋 Common App Prompts (2024–2025)":
        st.markdown("#### 📋 Common App Essay Prompts — 2024–2025")
        st.caption(
            "650-word limit. Choose the prompt that lets you tell the story only YOU can tell. "
            "All prompts are equally good — pick the one that excites you most."
        )

        for p in COMMON_APP_PROMPTS:
            with st.expander(f"**Prompt #{p['number']}** — {p['prompt'][:70]}...", expanded=False):
                st.markdown(f"**📋 Full Prompt:**\n\n> {p['prompt']}")
                st.markdown("---")

                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown("**🎯 What They're Really Asking:**")
                    st.info(p["what_asking"])

                    st.markdown("**✅ What Makes a Great Response:**")
                    st.success(p["great_response"])

                with col_r:
                    st.markdown("**⚠️ What to Avoid:**")
                    st.warning(p["avoid"])

                    st.markdown("**💡 Hook Idea (Darrian's Style):**")
                    st.markdown(
                        f"<div style='background:#1a2a1a; border-left:3px solid #5bc67e; "
                        f"padding:12px 16px; border-radius:4px; font-style:italic;'>"
                        f"\"{p['hook_idea']}\"</div>",
                        unsafe_allow_html=True,
                    )

    elif section == "🏆 7 Things That Make Essays Great":
        st.markdown("#### 🏆 The 7 Things That Make an Essay GREAT")
        st.caption("Inspired by real winning essays — including Darrian's $1M+ in scholarships.")

        tips = [
            {
                "number": "1",
                "title": "A Cinematic Opening Hook",
                "icon": "🎬",
                "description": "Start mid-scene. Not 'I've always loved basketball,' but 'The ball left my hands at the buzzer. I didn't look up.'",
                "darrian_example": "Darrian's McDonald's essay opens: 'Apron? Check. Work hat? Check. Slip-resistant shoes? Check.' — You're there before you even know what's happening.",
                "action": "Rewrite your first sentence to put the reader IN the moment, not before it.",
            },
            {
                "number": "2",
                "title": "Specific, Real Details",
                "icon": "🔍",
                "description": "The difference between memorable and forgettable is specificity. Real names. Real places. Real numbers.",
                "darrian_example": "Not 'I applied to many scholarships' — but 'I applied to 40 scholarships my senior year and won 9.' Which hits harder?",
                "action": "Replace every vague word with the actual specific detail.",
            },
            {
                "number": "3",
                "title": "Authentic Voice",
                "icon": "🗣️",
                "description": "Write like you talk to your best friend, not like you're writing a term paper. Admissions officers read thousands of essays — yours needs to sound like a real person.",
                "darrian_example": "Darrian's essays sound like him. If you read them and met him, you'd recognize the voice immediately.",
                "action": "Read your essay out loud. If it doesn't sound like you, rewrite those sentences.",
            },
            {
                "number": "4",
                "title": "Vulnerability + Strength",
                "icon": "💪",
                "description": "Show the hard part. Then show what you did. The vulnerability makes the strength believable.",
                "darrian_example": "The house fire essay shows genuine loss — and then genuine resilience. You feel both the pain and the growth.",
                "action": "Find the part of your essay where you glossed over the hard part — go deeper there.",
            },
            {
                "number": "5",
                "title": "A Clear Lesson",
                "icon": "📚",
                "description": "Every story needs a 'so what.' What did you learn? How did it change you? Be specific — not 'I learned to persevere' but WHAT you now do differently.",
                "darrian_example": "After the house fire: the lesson wasn't just 'family matters' — it was a shift in how he prioritized everything after that.",
                "action": "Ask yourself: what would I do differently now because of this experience? THAT is your lesson.",
            },
            {
                "number": "6",
                "title": "Connection to Your Future",
                "icon": "🔭",
                "description": "Your past experience should explain WHY you're heading where you're going. The story and the goal should feel inevitable together.",
                "darrian_example": "Technology passion → helping underserved communities → College Confused. Each step flows into the next.",
                "action": "End your essay with a sentence that connects your story to where you're headed.",
            },
            {
                "number": "7",
                "title": "Zero Clichés",
                "icon": "🚫",
                "description": "If you've read the phrase before, don't write it. 'Ever since I was little,' 'in today's society,' 'hard work pays off' — these are autopilot words that disconnect the reader.",
                "darrian_example": "Every sentence in a great essay could only have been written by that one person about that one experience.",
                "action": "Search your essay for clichés and replace each one with something only you would say.",
            },
        ]

        for tip in tips:
            with st.expander(f"{tip['icon']} **{tip['number']}. {tip['title']}**", expanded=False):
                st.markdown(f"**{tip['description']}**")
                st.markdown("")
                st.markdown(
                    f"<div style='background:#1a2030; border-left:3px solid #FFAB76; padding:12px 16px; border-radius:4px; margin:8px 0;'>"
                    f"🏆 <strong>Darrian's Approach:</strong> {tip['darrian_example']}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='background:#1a2a1a; border-left:3px solid #5bc67e; padding:12px 16px; border-radius:4px;'>"
                    f"✅ <strong>Your Action Step:</strong> {tip['action']}</div>",
                    unsafe_allow_html=True,
                )

    elif section == "❌ 5 Common Mistakes":
        st.markdown("#### ❌ 5 Common Essay Mistakes (And How to Fix Them)")

        mistakes = [
            {
                "mistake": "Summarizing Your Resume",
                "icon": "📄",
                "problem": "Listing your achievements instead of telling a story. Admissions officers already have your activities list — they don't need you to repeat it.",
                "fix": "Pick ONE moment that illustrates who you are. Go deep into that one thing instead of wide across everything.",
                "example_bad": "I have been in track, NHS, student council, and I volunteer at the food bank every month...",
                "example_good": "The starting gun fired. My legs weren't ready, but my mind was — because this race was three years of early mornings made real.",
            },
            {
                "mistake": "The 'Humble Brag' Trap",
                "icon": "😬",
                "problem": "Framing everything as an accomplishment, even your hardships. It makes you sound like you're performing humility rather than being genuine.",
                "fix": "Show real vulnerability. What actually scared you? What did you doubt? What failed before it worked?",
                "example_bad": "Even though the experience was challenging, I rose to the occasion and demonstrated strong leadership...",
                "example_good": "I had no idea what I was doing. The other students seemed confident. I wrote three drafts and deleted all of them.",
            },
            {
                "mistake": "Generic Opening Lines",
                "icon": "😴",
                "problem": "Starting with a dictionary definition, a famous quote, or a generic statement. These signal to admissions officers that the essay is about to be forgettable.",
                "fix": "Open mid-scene. Put the reader inside a specific moment — sensory details, action, dialogue.",
                "example_bad": "Webster's Dictionary defines leadership as 'the action of leading a group of people...'",
                "example_good": "The kitchen smelled like burnt rice and something else I couldn't name. It was 11pm. My mom was still at her second job.",
            },
            {
                "mistake": "Not Connecting to the Future",
                "icon": "🔭",
                "problem": "Telling a good story but forgetting to answer 'so what?' Admissions wants to know: how does this shape who you'll be in college and beyond?",
                "fix": "Your last paragraph should show where you're going, not just where you've been. Forward-looking = memorable.",
                "example_bad": "...and that's why that summer changed me. I will never forget the lessons I learned.",
                "example_good": "...that summer is why I'm studying computer science at your school. I want to build the tool that a 17-year-old version of me would have actually used.",
            },
            {
                "mistake": "Trying to Sound Impressive",
                "icon": "🎭",
                "problem": "Using big vocabulary, complex sentence structures, or formal tone to sound 'college-level.' It backfires — your voice disappears.",
                "fix": "Write simply. The most powerful essays use short sentences at key moments. Punch. Don't decorate.",
                "example_bad": "Through the juxtaposition of my socioeconomic circumstances and academic aspirations, I have cultivated a profound understanding...",
                "example_good": "We didn't have much. But I had a Chromebook and an internet connection. That was enough.",
            },
        ]

        for m in mistakes:
            with st.expander(f"{m['icon']} **Mistake: {m['mistake']}**", expanded=False):
                st.markdown(f"**❌ The Problem:** {m['problem']}")
                st.markdown(f"**✅ The Fix:** {m['fix']}")
                col_bad, col_good = st.columns(2)
                with col_bad:
                    st.markdown("**Before (weak):**")
                    st.markdown(
                        f"<div style='background:#2a1a1a; border-left:3px solid #ff6b6b; padding:12px; border-radius:4px; font-style:italic;'>"
                        f"\"{m['example_bad']}\"</div>",
                        unsafe_allow_html=True,
                    )
                with col_good:
                    st.markdown("**After (strong):**")
                    st.markdown(
                        f"<div style='background:#1a2a1a; border-left:3px solid #5bc67e; padding:12px; border-radius:4px; font-style:italic;'>"
                        f"\"{m['example_good']}\"</div>",
                        unsafe_allow_html=True,
                    )

    else:  # Find Your Topic
        st.markdown("#### 🔍 How to Find Your Essay Topic")
        st.markdown(
            "The hardest part of essay writing isn't the writing — it's finding THE story. "
            "Here's a process that works."
        )

        st.markdown("---")

        steps = [
            {
                "step": "Step 1: Make a List of 10 Moments",
                "icon": "📝",
                "content": """Think about moments in your life that were meaningful — not necessarily dramatic.
                
**Prompts to get you started:**
- A moment when you changed your mind about something
- A time you were proud of yourself that nobody else saw
- Something you do that others find strange or confusing
- A time you failed and what happened next
- The moment you realized something about who you are
- A conversation that stuck with you for months
- A skill or interest that people always ask you about
- Something about your family, culture, or background that shaped you

Write 10 bullet points — just the moment, not the whole story.""",
            },
            {
                "step": "Step 2: Find the Story With a Lesson",
                "icon": "🎯",
                "content": """For each moment on your list, ask: **What did I learn from this?**

If you can't answer that question easily, it might not be essay material. 

The essay prompt is almost always asking: *How did this experience change you?*

Pick the 3 moments where you have the clearest answer to that question.""",
            },
            {
                "step": "Step 3: The '10-Minute Test'",
                "icon": "⏱️",
                "content": """For your top 3 moments, set a timer for 10 minutes and free-write each one.

Don't edit. Don't think about college admissions. Just write the story like you're telling a close friend.

After 10 minutes, read what you wrote. **Which one surprised you? Which one felt most real?**

That's usually your essay.""",
            },
            {
                "step": "Step 4: The 'Only You' Filter",
                "icon": "👆",
                "content": """Ask yourself: **Could anyone else write this essay?**

If 100 other students could write the same essay with slightly different names and places — it's not specific enough.

Your essay should be SO specific to your experience that it could only come from you. The specificity IS the power.""",
            },
            {
                "step": "Step 5: Start With the AI Builder",
                "icon": "🤖",
                "content": """Once you have your topic, head to the **AI Essay Builder** tab. 

Fill out your **My Story Profile** first — the more details you give about your background, the more personalized your draft will be.

Then use **Build a New Essay Draft** with your topic as the prompt. Use the draft as a starting point — your job is to make it sound MORE like you, not less.""",
            },
        ]

        for s in steps:
            with st.expander(f"{s['icon']} **{s['step']}**", expanded=False):
                st.markdown(s["content"])

        st.markdown("---")
        st.markdown("#### 💬 Darrian's Advice")
        st.markdown(
            "<div style='background:#1a2030; border-left:4px solid #FFAB76; padding:16px 20px; border-radius:8px;'>"
            "<strong style='color:#FFAB76;'>From Darrian:</strong><br><br>"
            "\"The essay that got me into William &amp; Mary with a full ride wasn't about my GPA or my awards. "
            "It was about the night our house caught fire and what I was thinking as I watched everything burn. "
            "I cried writing it. That's how I knew it was the right essay.<br><br>"
            "The best essays make the reader feel something. Don't protect yourself. "
            "The more honest you are about the hard parts, the more real the good parts become.\""
            "</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: MY STORY PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🗂️ My Story Profile")
    st.markdown(
        "This is your personal information vault. The more you fill out here, "
        "the better the AI can personalize your essay drafts with YOUR real story."
    )

    story = _get_story(user_email)

    with st.form("story_profile_form"):
        st.markdown("#### 👤 About You")

        background = st.text_area(
            "Who are you? (Background, family, where you're from)",
            value=story.get("background", ""),
            placeholder="Tell us about yourself. Where did you grow up? What's your family like? "
                        "What's your cultural background? What makes your upbringing unique?\n\n"
                        "Example: 'I grew up in Hampton, VA with my mom and younger brother. "
                        "My parents divorced when I was 14 and we moved to a new city. "
                        "I'm Black, first-generation college student on my dad's side...'",
            height=130,
        )

        challenges = st.text_area(
            "What challenges have you overcome?",
            value=story.get("challenges", ""),
            placeholder="What hard things have you been through? What tested you?\n\n"
                        "Example: 'Our house caught fire in 2019 and we lost everything. "
                        "I had to switch schools twice in one year. Money was really tight — "
                        "I worked at McDonald's to help with groceries...'",
            height=120,
        )

        achievements = st.text_area(
            "What are you most proud of? (Achievements, wins, proud moments)",
            value=story.get("achievements", ""),
            placeholder="What have you accomplished? Big or small. Official or unofficial.\n\n"
                        "Example: 'Got into Governor's School of Science and Technology. "
                        "Won $5,000 Trajectory scholarship. Started a website called College Confused. "
                        "Made varsity track team. Got straight A's in AP classes despite working part-time...'",
            height=120,
        )

        extracurriculars = st.text_area(
            "What activities do you do outside of school?",
            value=story.get("extracurriculars", ""),
            placeholder="Clubs, sports, jobs, hobbies, side projects, volunteering...\n\n"
                        "Example: 'Track and field (400m). McDonald's part-time. "
                        "Sneaker resale business (buy/sell on StockX). Volunteer at Virginia Peninsula Food Bank. "
                        "Building College Confused website...'",
            height=110,
        )

        st.markdown("#### 🎓 Your College Goals")

        career_goals = st.text_area(
            "What do you want to study and why?",
            value=story.get("career_goals", ""),
            placeholder="What major are you interested in? What career do you want? Why?\n\n"
                        "Example: 'I want to study Computer Science. I want to build "
                        "technology tools that help low-income students navigate college applications. "
                        "Long-term goal is to start a tech company focused on education equity...'",
            height=110,
        )

        why_college = st.text_area(
            "Why do you want to go to college?",
            value=story.get("why_college", ""),
            placeholder="What does college mean to you personally? What do you want to get from it?\n\n"
                        "Example: 'I want to be the first in my family to graduate from a 4-year university. "
                        "I want to get the technical skills to build real products. "
                        "I also want to prove to other kids from my neighborhood that it's possible...'",
            height=110,
        )

        unique_qualities = st.text_area(
            "What makes you unique? What would you bring to a college campus?",
            value=story.get("unique_qualities", ""),
            placeholder="What's different or special about you? What perspective do you have "
                        "that others might not?\n\n"
                        "Example: 'I've experienced poverty, loss, and instability — and I've "
                        "turned those experiences into a platform that helps thousands of students. "
                        "I have an entrepreneurial mindset and a genuine obsession with "
                        "helping people who look like me...'",
            height=110,
        )

        col_save_story, col_sp = st.columns([1, 3])
        with col_save_story:
            save_story = st.form_submit_button("💾 Save Story Profile", type="primary", use_container_width=True)

        if save_story:
            _save_story(
                user_email=user_email,
                background=background.strip(),
                challenges=challenges.strip(),
                achievements=achievements.strip(),
                extracurriculars=extracurriculars.strip(),
                career_goals=career_goals.strip(),
                why_college=why_college.strip(),
                unique_qualities=unique_qualities.strip(),
            )
            st.success("✅ Story profile saved! The AI will now use this to personalize your essay drafts.")

    # Profile completeness
    st.markdown("---")
    st.markdown("#### 📊 Profile Completeness")
    fields = [
        ("Background", story.get("background", "")),
        ("Challenges", story.get("challenges", "")),
        ("Achievements", story.get("achievements", "")),
        ("Extracurriculars", story.get("extracurriculars", "")),
        ("Career Goals", story.get("career_goals", "")),
        ("Why College", story.get("why_college", "")),
        ("Unique Qualities", story.get("unique_qualities", "")),
    ]
    filled = sum(1 for _, v in fields if v.strip())
    total = len(fields)
    pct = int((filled / total) * 100)
    bar_color = "#5bc67e" if pct >= 80 else "#FFAB76" if pct >= 40 else "#ff6b6b"

    st.markdown(
        f"<div style='font-size:1.1rem; font-weight:700; color:{bar_color};'>{pct}% Complete ({filled}/{total} sections)</div>",
        unsafe_allow_html=True,
    )
    st.progress(pct / 100)

    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        bg_done = "✅" if story.get("background", "").strip() else "⬜"
        st.markdown(f"{bg_done} Background")
    with col_stat2:
        ch_done = "✅" if story.get("challenges", "").strip() else "⬜"
        st.markdown(f"{ch_done} Challenges")
    with col_stat3:
        ac_done = "✅" if story.get("achievements", "").strip() else "⬜"
        st.markdown(f"{ac_done} Achievements")
    with col_stat4:
        ex_done = "✅" if story.get("extracurriculars", "").strip() else "⬜"
        st.markdown(f"{ex_done} Extracurriculars")

    col_stat5, col_stat6, col_stat7, col_stat8 = st.columns(4)
    with col_stat5:
        cg_done = "✅" if story.get("career_goals", "").strip() else "⬜"
        st.markdown(f"{cg_done} Career Goals")
    with col_stat6:
        wc_done = "✅" if story.get("why_college", "").strip() else "⬜"
        st.markdown(f"{wc_done} Why College")
    with col_stat7:
        uq_done = "✅" if story.get("unique_qualities", "").strip() else "⬜"
        st.markdown(f"{uq_done} Unique Qualities")
    with col_stat8:
        st.markdown("")

    if pct < 100:
        missing = [name for name, val in fields if not val.strip()]
        st.info(
            f"💡 Fill in these sections for better AI essays: **{', '.join(missing)}**"
        )
    else:
        st.success("🎉 Profile complete! The AI has everything it needs to write a highly personalized essay for you.")

    st.markdown("---")
    st.markdown(
        "<div style='background:#1a2030; border-left:4px solid #FFAB76; padding:16px 20px; border-radius:8px;'>"
        "<strong style='color:#FFAB76;'>🔒 Privacy Note:</strong><br>"
        "Your story profile is private and only visible to you. "
        "It is never shared with colleges, scholarship committees, or anyone else. "
        "It is only used to power your AI essay drafts on this platform."
        "</div>",
        unsafe_allow_html=True,
    )
