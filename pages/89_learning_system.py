"""
Page 89 — Learning System
Tina Huang's 5-Step Learning Framework + Neuroscience Tips
ADHD/Bipolar-Adapted for Darrian Belcher
"""

import streamlit as st
import json
import datetime
from utils.db import init_db, get_conn, execute as db_exec, get_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="Learning System — Peach State Savings",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="auto",
)

init_db()
inject_css()
require_login()

# ─── Sidebar ─────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
st.sidebar.page_link("pages/89_learning_system.py",     label="🧠 Learning System",icon="🧠")
st.sidebar.page_link("pages/90_ai_workflow_hub.py",     label="⚡ AI Workflow",    icon="⚡")
render_sidebar_user_widget()

# ─── DB Setup ────────────────────────────────────────────────────────────────

USE_POSTGRES = get_setting("use_postgres") == "true"
PH = "%s" if USE_POSTGRES else "?"


def _ensure_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"""
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
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS learning_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER REFERENCES learning_goals(id) ON DELETE CASCADE,
            resource_type TEXT,
            title TEXT,
            url TEXT,
            format TEXT DEFAULT 'video',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS learning_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER REFERENCES learning_goals(id) ON DELETE CASCADE,
            session_date DATE DEFAULT CURRENT_DATE,
            energy_level TEXT,
            duration_minutes INTEGER,
            stage_worked TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS interleave_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week TEXT,
            goal_id INTEGER REFERENCES learning_goals(id) ON DELETE CASCADE,
            duration_minutes INTEGER DEFAULT 60,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _load_goals():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM learning_goals ORDER BY priority DESC, created_at DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _load_active_goals():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM learning_goals WHERE completed_at IS NULL ORDER BY priority DESC, created_at DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _create_goal(title, goal_statement, priority, energy_level, notes):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"INSERT INTO learning_goals (title, goal_statement, priority, energy_level, notes) VALUES ({PH},{PH},{PH},{PH},{PH})",
        (title, goal_statement, priority, energy_level, notes)
    )
    conn.commit()
    conn.close()


def _update_goal_stage(goal_id, stage):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"UPDATE learning_goals SET stage={PH}, updated_at=CURRENT_TIMESTAMP WHERE id={PH}",
        (stage, goal_id)
    )
    conn.commit()
    conn.close()


def _complete_goal(goal_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"UPDATE learning_goals SET completed_at=CURRENT_TIMESTAMP, stage='done', updated_at=CURRENT_TIMESTAMP WHERE id={PH}",
        (goal_id,)
    )
    conn.commit()
    conn.close()


def _delete_goal(goal_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM learning_goals WHERE id={PH}", (goal_id,))
    conn.commit()
    conn.close()


def _add_resource(goal_id, resource_type, title, url, fmt, notes):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"INSERT INTO learning_resources (goal_id, resource_type, title, url, format, notes) VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
        (goal_id, resource_type, title, url, fmt, notes)
    )
    conn.commit()
    conn.close()


def _load_resources(goal_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM learning_resources WHERE goal_id={PH} ORDER BY created_at", (goal_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _log_session(goal_id, energy, duration, stage, notes):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"INSERT INTO learning_sessions (goal_id, energy_level, duration_minutes, stage_worked, notes) VALUES ({PH},{PH},{PH},{PH},{PH})",
        (goal_id, energy, duration, stage, notes)
    )
    conn.commit()
    conn.close()


def _load_sessions(goal_id=None):
    conn = get_conn()
    c = conn.cursor()
    if goal_id:
        c.execute(
            f"SELECT ls.*, lg.title as goal_title FROM learning_sessions ls JOIN learning_goals lg ON ls.goal_id=lg.id WHERE ls.goal_id={PH} ORDER BY ls.created_at DESC LIMIT 20",
            (goal_id,)
        )
    else:
        c.execute(
            "SELECT ls.*, lg.title as goal_title FROM learning_sessions ls JOIN learning_goals lg ON ls.goal_id=lg.id ORDER BY ls.created_at DESC LIMIT 30"
        )
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _ai_learn_coach(topic, goal, stage, adhd_mode):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key set. Go to Settings to add it."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        adhd_note = ""
        if adhd_mode:
            adhd_note = """
IMPORTANT CONTEXT: Darrian has ADHD and Bipolar Disorder. 
- Keep responses SHORT and PUNCHY — max 5 bullet points per section
- Use bold headers to create visual breaks
- Give ONE concrete action to do right now, not a list of 10
- Avoid overwhelming with options — pick the BEST one and say why
- Use high-energy, encouraging tone that matches ADHD brain
- Break big tasks into micro-steps (15-25 min chunks)
- Acknowledge that motivation isn't always there — give strategies for low-energy days
"""
        prompt = f"""You are Darrian's personal learning coach, using Tina Huang's 5-step framework (Goal, Research, Priming, Comprehension, Implementation) adapted for neuroscience-based rapid learning.

{adhd_note}

Topic to learn: {topic}
Stated goal: {goal}
Current stage: {stage}

Provide:
1. A specific, actionable plan for THIS stage only
2. The best AI tool to use for this stage (from: Perplexity, NotebookLM, Google AI Studio, ChatGPT audio, Claude)
3. Time estimate (be realistic)
4. One neuroscience hack that applies here (e.g., spaced repetition, interleaving, priming effect)
5. ADHD-friendly tip for this specific stage

Be blunt, direct, and practical. Skip generic advice."""

        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"❌ AI error: {e}"


def _ai_priming_quiz(topic, resources_text):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key set."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""Create a PRIMING quiz for the topic: {topic}

Context/resources: {resources_text}

Generate 5 multiple-choice questions that:
1. Cover the MOST IMPORTANT concepts a learner will encounter
2. Are designed to be taken BEFORE studying (priming effect — research shows this improves retention 10-20%)
3. Include a brief explanation of why each answer matters after the options

Format each question as:
**Q1. [Question]**
a) Option A
b) Option B  
c) Option C
d) Option D

*(You won't know this yet — that's the point! Note what surprises you.)*

Keep questions focused on definitions, key concepts, and real-world applications."""

        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"❌ AI error: {e}"


def _ai_interleave_schedule(goals):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key set."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        goals_text = "\n".join([f"- {g['title']} (priority: {g['priority']}, energy needed: {g['energy_level']})" for g in goals])
        prompt = f"""Create a weekly interleaved study schedule for Darrian (ADHD + Bipolar, software engineer with full-time job at Visa).

Active learning goals:
{goals_text}

Rules:
- Interleaving = mixing multiple subjects in ONE day (proven to improve retention vs. blocked learning)
- Never more than 90 minutes on any single topic per day
- Respect energy levels: high-energy topics in morning, low-energy in evening
- Monday-Friday: max 2 hours total learning (he has a job)
- Saturday/Sunday: up to 3 hours total
- Leave buffer days — ADHD brains need recovery

Output a clean weekly schedule table showing:
Day | Topic | Duration | When (morning/afternoon/evening) | Energy Level

Then add 3 ADHD-specific tips for sticking to this schedule."""

        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"❌ AI error: {e}"


# ─── Main App ─────────────────────────────────────────────────────────────────
_ensure_tables()

st.title("🧠 Learning System")
st.markdown("""
> **Tina Huang's 5-Step Framework** adapted for ADHD + Bipolar brains.  
> *Goal → Research → Priming → Comprehension → Implementation*  
> Cut learning time by 60–70% using the right AI tools at each stage.
""")

# Energy banner
today_energy = st.selectbox(
    "⚡ Today's Energy Level (this determines WHAT you should work on)",
    ["🔥 High — Morning fresh, ready to tackle hard stuff",
     "⚡ Medium — Afternoon mode, can focus with effort",
     "😴 Low — Evening/crash, light review only",
     "🚫 Burnout — Rest day, do NOT study today"],
    key="today_energy"
)
if "Burnout" in today_energy:
    st.warning("🛑 **Rest day activated.** ADHD and Bipolar brains need recovery. Don't push it — review tomorrow's goals in BACKLOG, then close this tab.")
elif "Low" in today_energy:
    st.info("😴 **Low energy mode.** Stick to: reviewing notes, light priming quizzes, or listening to an audio podcast at 1x speed. No new concepts today.")

st.markdown("---")

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 My Goals",
    "🔬 Stage Toolkit",
    "📅 Interleave Schedule",
    "📓 Log Session",
    "🧠 Framework Guide"
])

# ── TAB 1: Goals ──────────────────────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns([2, 1])

    with col_right:
        st.subheader("➕ New Learning Goal")
        with st.form("new_goal_form", clear_on_submit=True):
            g_title = st.text_input("What are you learning?", placeholder="e.g. AI Agent Development")
            g_goal = st.text_area(
                "Specific goal (be exact!)",
                placeholder="e.g. Build a working multi-agent system that monitors my eBay prices autonomously",
                help="Tina's #1 tip: define the END RESULT, not the topic. 'Learn AI agents' is vague. 'Build X that does Y' is a goal."
            )
            g_priority = st.selectbox("Priority", ["high", "medium", "low"])
            g_energy = st.selectbox(
                "Energy level needed",
                ["high", "medium", "low"],
                help="Match this to your energy calendar. High-energy topics = morning. Low-energy = evening review."
            )
            g_notes = st.text_area("Notes / Context", placeholder="Why do you need this? What's the deadline?")
            if st.form_submit_button("🎯 Create Goal", type="primary"):
                if g_title and g_goal:
                    _create_goal(g_title, g_goal, g_priority, g_energy, g_notes)
                    st.success(f"✅ Goal '{g_title}' created!")
                    st.rerun()
                else:
                    st.error("Title and goal statement required.")

    with col_left:
        st.subheader("🎯 Active Goals")
        active_goals = _load_active_goals()
        STAGES = ["goal", "research", "priming", "comprehension", "implementation", "done"]
        STAGE_ICONS = {"goal": "🎯", "research": "🔍", "priming": "⚡", "comprehension": "📚", "implementation": "🛠️", "done": "✅"}
        STAGE_COLORS = {"goal": "blue", "research": "orange", "priming": "violet", "comprehension": "green", "implementation": "red", "done": "gray"}

        if not active_goals:
            st.info("No active goals. Create your first learning goal →")
        else:
            for g in active_goals:
                with st.expander(f"{STAGE_ICONS.get(g['stage'], '📋')} **{g['title']}** — Stage: `{g['stage'].upper()}`", expanded=False):
                    st.markdown(f"**Goal:** {g['goal_statement']}")
                    if g['notes']:
                        st.markdown(f"**Notes:** {g['notes']}")
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("Priority", g['priority'].upper())
                    with col_b:
                        st.metric("Energy Needed", g['energy_level'].upper())
                    with col_c:
                        curr_idx = STAGES.index(g['stage']) if g['stage'] in STAGES else 0
                        new_stage = st.selectbox(
                            "Advance Stage",
                            STAGES,
                            index=curr_idx,
                            key=f"stage_{g['id']}"
                        )
                        if new_stage != g['stage']:
                            if st.button("Update", key=f"upd_{g['id']}"):
                                _update_goal_stage(g['id'], new_stage)
                                st.rerun()
                    with col_d:
                        if st.button("✅ Complete", key=f"done_{g['id']}"):
                            _complete_goal(g['id'])
                            st.success(f"🎉 '{g['title']}' completed!")
                            st.rerun()
                        if st.button("🗑️ Delete", key=f"del_{g['id']}"):
                            _delete_goal(g['id'])
                            st.rerun()

                    # Resources
                    resources = _load_resources(g['id'])
                    if resources:
                        st.markdown("**📎 Resources:**")
                        for r in resources:
                            icon = "🎥" if r['format'] == 'video' else "📄" if r['format'] == 'text' else "🎧" if r['format'] == 'audio' else "🔗"
                            st.markdown(f"  {icon} [{r['title']}]({r['url']}) — {r['resource_type']}")

                    # Add resource
                    with st.form(f"resource_form_{g['id']}", clear_on_submit=True):
                        st.markdown("**Add Resource:**")
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            r_title = st.text_input("Resource Name", key=f"rt_{g['id']}")
                            r_url = st.text_input("URL", key=f"ru_{g['id']}")
                        with rc2:
                            r_type = st.selectbox("Type", ["Course", "Book", "Video", "Article", "Podcast", "GitHub", "Docs"], key=f"rtype_{g['id']}")
                            r_fmt = st.selectbox("Format", ["video", "audio", "text", "interactive"], key=f"rfmt_{g['id']}")
                        r_notes = st.text_input("Notes", key=f"rn_{g['id']}")
                        if st.form_submit_button("Add Resource"):
                            _add_resource(g['id'], r_type, r_title, r_url, r_fmt, r_notes)
                            st.rerun()

        st.markdown("---")
        st.subheader("✅ Completed Goals")
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM learning_goals WHERE completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 10")
        rows = c.fetchall()
        cols_d = [d[0] for d in c.description]
        conn.close()
        completed = [dict(zip(cols_d, r)) for r in rows]
        if completed:
            for g in completed:
                st.markdown(f"✅ **{g['title']}** — Completed {str(g['completed_at'])[:10]}")
        else:
            st.info("No completed goals yet.")

# ── TAB 2: Stage Toolkit ──────────────────────────────────────────────────────
with tab2:
    st.subheader("🔬 Stage-by-Stage AI Toolkit")
    st.markdown("Pick a goal and stage to get the exact AI tools + workflow to use.")

    goals = _load_active_goals()
    if not goals:
        st.warning("Create a learning goal in the Goals tab first.")
    else:
        selected_goal = st.selectbox(
            "Select Goal",
            options=[g['title'] for g in goals],
            key="toolkit_goal"
        )
        goal_obj = next((g for g in goals if g['title'] == selected_goal), None)

        stage = st.selectbox(
            "Which stage are you working on?",
            ["goal", "research", "priming", "comprehension", "implementation"],
            format_func=lambda x: {
                "goal": "🎯 Goal — Define what success looks like",
                "research": "🔍 Research — Find the best resources (Perplexity)",
                "priming": "⚡ Priming — Pre-learn before you learn (NotebookLM)",
                "comprehension": "📚 Comprehension — Actually learn it (layered approach)",
                "implementation": "🛠️ Implementation — Build/apply it"
            }[x],
            key="toolkit_stage"
        )

        adhd_mode = st.toggle("🧠 ADHD/Bipolar Mode (shorter, punchier guidance)", value=True)

        # Static stage guides
        STAGE_GUIDES = {
            "goal": {
                "title": "🎯 Stage 1: Goal Definition",
                "time_pct": "0–5% of total time",
                "ai_tool": "ChatGPT or Claude",
                "description": "Before anything else, write ONE sentence: *What does success look like when I'm done?*",
                "adhd_tip": "ADHD brains need a VIVID end state to stay motivated. Don't say 'learn Python' — say 'build a script that texts me when my eBay listing sells.' The more concrete, the more your brain cares.",
                "neuroscience": "Goal-setting activates the prefrontal cortex's reward anticipation loop. Specific goals = more dopamine = more motivation.",
                "checklist": [
                    "Write goal as: 'I want to [ACTION] that [DOES SPECIFIC THING] so that [OUTCOME]'",
                    "Is this goal testable? Can you demo it to someone?",
                    "Assign energy level: high/medium/low",
                    "Set a realistic deadline (not 'someday')"
                ]
            },
            "research": {
                "title": "🔍 Stage 2: Resource Research",
                "time_pct": "0–10% of total time",
                "ai_tool": "**Perplexity AI** (search Reddit + course aggregators)",
                "description": "Don't guess — use Perplexity to find how OTHER people learned this, and which resources they rated best.",
                "adhd_tip": "Set a TIMER for research. ADHD = rabbit hole risk. 20 minutes max on Perplexity, then pick 2-3 resources and STOP. More resources ≠ better learning.",
                "neuroscience": "Choice overload (too many resources) activates decision fatigue and kills motivation. Constraint = focus.",
                "checklist": [
                    "Search Perplexity: 'how to learn [TOPIC] reddit 2025'",
                    "Ask: 'What are the top 3 courses/resources for [TOPIC] for [YOUR GOAL]?'",
                    "Filter by YOUR format preference: video/audio/text",
                    "Pick max 2-3 primary resources. Add them to the goal.",
                    "Note: use Deep Research mode for complex topics"
                ],
                "prompt": "Search Perplexity for: 'how did people learn [TOPIC] fast reddit site:reddit.com' — look for threads with 50+ upvotes"
            },
            "priming": {
                "title": "⚡ Stage 3: Priming",
                "time_pct": "2–5% of total time (saves 10–20% retention!)",
                "ai_tool": "**NotebookLM** (upload resources → generate study guide + quiz)",
                "description": "Skim everything first. Take a quiz BEFORE you know the answers. This primes your brain subconsciously — you'll absorb more when you actually study.",
                "adhd_tip": "Priming is PERFECT for ADHD. It's fast, low-stakes, and creates natural curiosity. When you hit the topic during actual study, your brain goes 'oh I remember seeing this' — dopamine hit.",
                "neuroscience": "Priming effect: exposure to material (even without understanding it) improves subsequent learning by 10-20%. Pre-testing improves retention vs. studying first.",
                "checklist": [
                    "Upload your resources to NotebookLM",
                    "Ask NotebookLM: 'Generate a study guide with key topics'",
                    "Ask NotebookLM: 'Generate a quiz I should take BEFORE studying'",
                    "Take the quiz — don't Google answers. Note what surprises you.",
                    "Skim course titles/headers — 15-20 minutes max",
                    "For coding: look at the starter code/final product first"
                ]
            },
            "comprehension": {
                "title": "📚 Stage 4: Comprehension (Layered Learning)",
                "time_pct": "40–60% of total time",
                "ai_tool": "**ChatGPT Audio Mode** + **NotebookLM** + **Google AI Studio**",
                "description": "Learn in LAYERS, not deep-dives. Pass 1: concepts only. Pass 2: examples. Pass 3: deep details.",
                "adhd_tip": "Never go deep on ONE thing until you've covered ALL things at a surface level. ADHD brains hyper-focus — resist the urge to master one concept before moving on. The layer approach keeps novelty high.",
                "neuroscience": "Spaced repetition + interleaving. Mixing topics across sessions improves long-term retention vs. blocked studying.",
                "checklist": [
                    "**Pass 1 (2x speed):** Only note definitions, major concepts, full examples",
                    "**Pass 2:** Go through material at normal speed, fill in gaps",
                    "**Pass 3:** Deep dive into areas where you're weak",
                    "Convert boring formats: text → audio (Google AI Studio), video → text (NotebookLM)",
                    "Use ChatGPT Audio Mode to talk through confusing concepts out loud",
                    "Ask Claude to generate an interactive dashboard from your notes",
                    "Interleave: don't study this topic >90 min in one sitting"
                ],
                "format_tips": {
                    "Audio Learner (like Tina)": "Google AI Studio → 'Transform this text into a single-person podcast script with only definitions, concepts, and examples. No commentary.'",
                    "Visual Learner": "Ask Claude/Sonnet to build an interactive diagram or dashboard",
                    "Text Learner": "NotebookLM → transform video/audio to structured textbook format"
                }
            },
            "implementation": {
                "title": "🛠️ Stage 5: Implementation",
                "time_pct": "20–40% of total time",
                "ai_tool": "**Claude Code** or **Windsurf** for coding; **Manus/Gamma** for slides/reports",
                "description": "Apply what you learned. This is where it sticks. Build something real.",
                "adhd_tip": "Start with the SMALLEST possible version (MVP). ADHD brains love completion. Ship something tiny first, then iterate. A working small thing beats a perfect thing that never gets done.",
                "neuroscience": "Active recall + practice is 10x more effective than passive review. Building = the best form of retrieval practice.",
                "checklist": [
                    "Define the smallest version that proves you learned it",
                    "For code: use Claude/Cline/Windsurf to build the MVP",
                    "For essays/reports: outline in NotebookLM, write in ChatGPT",
                    "For slides: use Gamma or Manus",
                    "For data analysis: give raw data to Claude → interactive dashboard",
                    "Test your implementation against your original goal statement",
                    "Ship it — even if imperfect"
                ]
            }
        }

        guide = STAGE_GUIDES[stage]
        st.markdown(f"### {guide['title']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Time", guide['time_pct'])
        with col2:
            st.metric("🤖 Best AI Tool", guide['ai_tool'].replace("**", ""))
        with col3:
            st.metric("🧠 ADHD Friendly", "✅ High" if stage in ["priming", "goal"] else "⚡ Medium")

        st.markdown(f"**What to do:** {guide['description']}")

        if adhd_mode:
            st.info(f"🧠 **ADHD/Bipolar Tip:** {guide['adhd_tip']}")

        st.markdown(f"🔬 **Neuroscience:** {guide['neuroscience']}")

        st.markdown("**✅ Checklist:**")
        for item in guide['checklist']:
            st.markdown(f"  - {item}")

        if 'format_tips' in guide:
            st.markdown("**🎯 Format Conversion Tips:**")
            for learner_type, tip in guide['format_tips'].items():
                st.markdown(f"  **{learner_type}:** {tip}")

        st.markdown("---")

        # AI Coach
        st.subheader("🤖 AI Learning Coach")
        if st.button("💡 Get Personalized Plan for This Stage", type="primary"):
            if goal_obj:
                with st.spinner("Thinking like Tina Huang..."):
                    result = _ai_learn_coach(
                        selected_goal,
                        goal_obj.get('goal_statement', ''),
                        stage,
                        adhd_mode
                    )
                st.markdown(result)

        # Priming Quiz Generator
        if stage == "priming":
            st.markdown("---")
            st.subheader("📝 Generate Priming Quiz")
            resources = _load_resources(goal_obj['id']) if goal_obj else []
            resource_text = ", ".join([r['title'] for r in resources]) if resources else selected_goal
            if st.button("🎯 Generate Pre-Learning Quiz", type="secondary"):
                with st.spinner("Generating priming quiz..."):
                    quiz = _ai_priming_quiz(selected_goal, resource_text)
                st.markdown(quiz)
                st.info("💡 Take this quiz WITHOUT Googling. The point is NOT to get answers right — it's to prime your brain for what's coming.")

# ── TAB 3: Interleave Schedule ────────────────────────────────────────────────
with tab3:
    st.subheader("📅 Interleaved Study Schedule")
    st.markdown("""
    > **Interleaving** = studying multiple different topics in the same day.  
    > Research shows this **outperforms** blocking (one topic per day) for long-term retention.  
    > For ADHD brains: interleaving also keeps novelty high = more dopamine = more focus.
    """)

    goals = _load_active_goals()
    if len(goals) < 2:
        st.info("Add at least 2 active learning goals to generate an interleaved schedule.")
    else:
        if st.button("🗓️ Generate My Interleaved Schedule", type="primary"):
            with st.spinner("Building your ADHD-optimized study schedule..."):
                schedule = _ai_interleave_schedule(goals)
            st.markdown(schedule)

    st.markdown("---")
    st.subheader("⚡ Energy Map")
    st.markdown("""
    Match your study sessions to your energy, not your calendar.

    | Time of Day | Energy Level | What to Study |
    |-------------|-------------|---------------|
    | Morning (pre-work, 6-8am) | 🔥 High | Complex new concepts, implementation, coding |
    | Lunch (12-1pm) | ⚡ Medium | Comprehension pass 2, examples, practice |
    | After work (6-7pm) | 😴 Low | Priming, note review, light audio at 1x |
    | Night (8pm+) | 🚫 Very Low | Log to BACKLOG. Do NOT study. |

    **ADHD Rule:** Never schedule a study session you know you'll skip. A 20-minute session at high energy beats a 2-hour planned session that never happens.

    **Bipolar Note:** On high days, cap sessions at 90 minutes total — hyperfocus can burn you out. On low days, even 15 minutes of light priming counts.
    """)

    # Recent sessions
    st.markdown("---")
    st.subheader("📊 Recent Study Sessions")
    sessions = _load_sessions()
    if sessions:
        for s in sessions[:10]:
            emoji = "🔥" if s['energy_level'] == "high" else "⚡" if s['energy_level'] == "medium" else "😴"
            st.markdown(f"{emoji} **{s['goal_title']}** | {s['stage_worked']} | {s['duration_minutes']}min | {str(s['session_date'])[:10]}")
    else:
        st.info("No sessions logged yet.")

# ── TAB 4: Log Session ────────────────────────────────────────────────────────
with tab4:
    st.subheader("📓 Log a Study Session")
    st.markdown("Track your sessions to build data on when you learn best.")

    goals = _load_active_goals()
    if not goals:
        st.warning("No active goals. Create a goal first.")
    else:
        with st.form("log_session_form", clear_on_submit=True):
            ls_goal = st.selectbox("Goal", [g['title'] for g in goals])
            ls_energy = st.selectbox("Energy Level During Session", ["high", "medium", "low"])
            ls_duration = st.slider("Duration (minutes)", 15, 180, 60, 15)
            ls_stage = st.selectbox("Stage Worked On", ["goal", "research", "priming", "comprehension", "implementation"])
            ls_notes = st.text_area("What did you cover? Any insights?")

            if st.form_submit_button("📝 Log Session", type="primary"):
                goal_id = next((g['id'] for g in goals if g['title'] == ls_goal), None)
                if goal_id:
                    _log_session(goal_id, ls_energy, ls_duration, ls_stage, ls_notes)
                    st.success(f"✅ Session logged! {ls_duration} minutes on '{ls_goal}'")
                    st.rerun()

# ── TAB 5: Framework Guide ────────────────────────────────────────────────────
with tab5:
    st.subheader("🧠 Tina Huang's Framework — Full Reference")
    st.markdown("""
    ## The Jigsaw Puzzle Analogy
    Learning is like assembling a puzzle:
    - **Goal** = picking WHICH puzzle to solve
    - **Research** = finding the missing pieces
    - **Priming** = sorting pieces by color/shape before assembly
    - **Comprehension** = actually assembling it, layer by layer
    - **Implementation** = connecting the final patches into a complete picture

    ---

    ## Time Allocation (Without AI)
    | Stage | % of Time |
    |-------|-----------|
    | Goal | 0–5% |
    | Research | 0–10% |
    | Priming | 2–5% |
    | Comprehension | 40–60% |
    | Implementation | 20–40% |

    ## Time Allocation (With AI — saves ~20 hours per 30-hour learning goal)
    | Stage | AI Tool | Time Saved |
    |-------|---------|-----------|
    | Research | Perplexity Deep Research | ~3 hours |
    | Priming | NotebookLM study guide + quiz | ~1 hour |
    | Comprehension | Format conversion + ChatGPT Audio | ~7 hours |
    | Implementation | Claude Code / Manus / Gamma | ~6 hours |

    ---

    ## AI Tool Quick Reference
    | Tool | Best For |
    |------|---------|
    | **Perplexity** | Finding resources, Reddit research, course comparison |
    | **NotebookLM** | Uploading docs, study guides, quizzes, format conversion |
    | **Google AI Studio** | Text → audio podcast script (for audio learners) |
    | **ChatGPT Audio Mode** | Talk through confusion out loud |
    | **Claude Opus** | Interactive dashboards from notes, code |
    | **Gamma/Manus** | Slide decks |
    | **Cline + Claude** | Building hyper-specific apps |

    ---

    ## ADHD/Bipolar Learning Rules (Darrian-Specific)
    1. **Energy first, time second.** Never schedule based on available time. Schedule based on energy.
    2. **Interleave.** 3 topics × 1 hour beats 1 topic × 3 hours. Keeps novelty high.
    3. **Priming is your best friend.** Low-stakes, fast, and creates natural curiosity.
    4. **25-minute caps on hard topics.** Pomodoro for deep work. ADHD hyperfocus = burnout.
    5. **Convert formats.** If a textbook is killing you, turn it into audio. Format matters more for ADHD.
    6. **Log every session.** Data on when you learn best = priceless for ADHD brains.
    7. **On bipolar high days:** Cap at 90 min total. Hyperfocus now = crash later.
    8. **On bipolar low days:** Even 15 minutes of priming counts. Show up anyway.
    9. **Implementation starts small.** MVP > perfect. Completion dopamine is real.
    10. **Rest is part of learning.** Sleep consolidates memories. Don't skip it.

    ---

    ## The Tina Huang Speed Multipliers
    - **2-3x speed** for initial comprehension pass (audio/video)
    - **Pre-testing** before studying (priming quiz) = +10-20% retention
    - **Layer 1 = definitions + major concepts + full examples only**
    - **Audio conversion** = absorb a 30-page report in 30 minutes
    - **Talk to AI** (ChatGPT Audio) = explain your confusion out loud
    - **Note organization** → NotebookLM → Claude interactive dashboard

    ---

    ## For College Confused Users
    These same principles apply to college prep:
    - **Goal:** Acceptance to X school / $Y in scholarships
    - **Research:** Perplexity for school requirements, scholarship databases
    - **Priming:** Skim essay prompts + common app before writing
    - **Comprehension:** Study test content in layers (concepts → practice → deep)
    - **Implementation:** Write drafts, apply, submit

    The CC pages (80-88) already implement many of these steps.
    """)
