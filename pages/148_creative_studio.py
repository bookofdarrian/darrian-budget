"""
🎬 The Marathon Studio — Page 148
Private creative development studio for Darrian Belcher.
Manga, films, shows, series, shorts — every vision brought to life.

"The Marathon Continues." — Nipsey Hussle
"Stay hungry, stay foolish." — Steve Jobs
"You came to this earth to accomplish something." — Dr. Sebi

This page is PRIVATE. Requires login.
"""
import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="🎬 The Marathon Studio — Peach State Savings",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css, get_current_user

init_db()
inject_css()
require_login()

# ── Sidebar ─────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                              label="Overview",              icon="📊")
st.sidebar.page_link("pages/22_todo.py",                    label="Todo",                  icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",       label="Creator",               icon="🎬")
st.sidebar.page_link("pages/25_notes.py",                   label="Notes",                 icon="📝")
st.sidebar.page_link("pages/26_media_library.py",           label="Media Library",         icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",      label="Personal Assistant",    icon="🤖")
st.sidebar.page_link("pages/147_proactive_ai_engine.py",    label="Proactive AI",          icon="🧠")
st.sidebar.page_link("pages/148_creative_studio.py",        label="Marathon Studio",       icon="🎬")
render_sidebar_user_widget()

# ── Constants ────────────────────────────────────────────────────────────────────
PH   = "%s" if USE_POSTGRES else "?"
AUTO = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

FORMAT_TYPES = ["Manga/Graphic Novel", "Feature Film", "Short Film", "TV Series", "Mini-Series",
                "Documentary", "Animated Series", "Web Series", "Podcast/Audio Drama", "Stage Play",
                "Music Video/Visual Album", "Concept/Experimental", "Other"]

GENRES = ["Drama", "Sci-Fi", "Fantasy", "Action", "Thriller", "Horror", "Comedy", "Romance",
          "Historical", "Biographical", "Social Commentary", "Coming-of-Age", "Afrofuturism",
          "Noir", "Surrealism", "Musical", "Mystery", "Other"]

STATUS_OPTIONS = ["💡 Seed Idea", "🌱 Developing", "📖 Writing", "🎨 In Production",
                  "⏸️ On Hold", "✅ Complete", "🚀 Released"]

AI_VOICES = {
    "Nipsey Mode": "Channel the Marathon energy. Crenshaw DNA. Building for the community, in silence, releasing game. Legacy over everything. Every line should hit like a Nipsey verse — intentional, layered, real.",
    "Jobs Mode": "Channel obsessive perfectionism. The intersection of technology and the liberal arts. Strip it to the essential. What does the user feel? What's the one thing? Make it insanely great.",
    "Sebi Mode": "Channel ancient wisdom, indigenous knowledge, natural healing energy. Connect the story to roots, earth, ancestry. The body knows truth. The land remembers. Heal through narrative.",
    "All Three": "Channel all three simultaneously: Nipsey's community marathon legacy, Jobs' obsessive minimalist perfectionism, Sebi's healing ancestral wisdom. This is the trifecta.",
}

PANEL_STYLES = ["Manga (B&W, Manga Lines)", "American Comic (Bold, Inked)", "Webtoon (Vertical, Color)",
                "French BD (European, Detailed)", "Afrofuturist (Afrocentric, Vibrant)",
                "Minimalist (Clean Lines, White Space)", "Grunge/Urban (Textured, Raw)"]


# ── DB Setup ─────────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS creative_projects (
            id          {AUTO},
            title       TEXT NOT NULL,
            format      TEXT,
            genre       TEXT,
            logline     TEXT,
            status      TEXT DEFAULT '💡 Seed Idea',
            is_private  INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS creative_ideas (
            id          {AUTO},
            project_id  INTEGER,
            idea_type   TEXT,
            content     TEXT,
            ai_expanded TEXT,
            tags        TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS story_bible (
            id          {AUTO},
            project_id  INTEGER NOT NULL,
            section     TEXT,
            content     TEXT,
            ai_content  TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS script_treatments (
            id          {AUTO},
            project_id  INTEGER NOT NULL,
            title       TEXT,
            treatment   TEXT,
            notes       TEXT,
            version     INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS manga_panels (
            id          {AUTO},
            project_id  INTEGER NOT NULL,
            chapter     INTEGER DEFAULT 1,
            page_num    INTEGER DEFAULT 1,
            panel_num   INTEGER DEFAULT 1,
            description TEXT,
            dialogue    TEXT,
            panel_style TEXT,
            ai_prompt   TEXT,
            notes       TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _load_projects():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM creative_projects ORDER BY updated_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def _create_project(title, fmt, genre, logline, status):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute(
        f"INSERT INTO creative_projects (title, format, genre, logline, status, created_at, updated_at) VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH})",
        (title, fmt, genre, logline, status, now, now)
    )
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid


def _update_project_status(pid, status):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"UPDATE creative_projects SET status={PH}, updated_at={PH} WHERE id={PH}",
              (status, datetime.now().isoformat(), pid))
    conn.commit()
    conn.close()


def _delete_project(pid):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"DELETE FROM creative_projects WHERE id={PH}", (pid,))
    c.execute(f"DELETE FROM creative_ideas WHERE project_id={PH}", (pid,))
    c.execute(f"DELETE FROM story_bible WHERE project_id={PH}", (pid,))
    c.execute(f"DELETE FROM script_treatments WHERE project_id={PH}", (pid,))
    c.execute(f"DELETE FROM manga_panels WHERE project_id={PH}", (pid,))
    conn.commit()
    conn.close()


def _save_idea(project_id, idea_type, content, ai_expanded="", tags=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"INSERT INTO creative_ideas (project_id, idea_type, content, ai_expanded, tags, created_at) VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
        (project_id, idea_type, content, ai_expanded, tags, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def _load_ideas(project_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM creative_ideas WHERE project_id={PH} ORDER BY created_at DESC", (project_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def _save_story_bible(project_id, section, content, ai_content=""):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    # upsert — update if section exists
    c.execute(f"SELECT id FROM story_bible WHERE project_id={PH} AND section={PH}", (project_id, section))
    row = c.fetchone()
    if row:
        c.execute(f"UPDATE story_bible SET content={PH}, ai_content={PH}, updated_at={PH} WHERE id={PH}",
                  (content, ai_content, now, row[0]))
    else:
        c.execute(
            f"INSERT INTO story_bible (project_id, section, content, ai_content, created_at, updated_at) VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
            (project_id, section, content, ai_content, now, now)
        )
    conn.commit()
    conn.close()


def _load_story_bible(project_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM story_bible WHERE project_id={PH} ORDER BY section", (project_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def _save_treatment(project_id, title, treatment, notes=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT COALESCE(MAX(version),0) FROM script_treatments WHERE project_id={PH} AND title={PH}",
              (project_id, title))
    v = (c.fetchone()[0] or 0) + 1
    c.execute(
        f"INSERT INTO script_treatments (project_id, title, treatment, notes, version, created_at) VALUES ({PH},{PH},{PH},{PH},{PH},{PH})",
        (project_id, title, treatment, notes, v, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def _load_treatments(project_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT * FROM script_treatments WHERE project_id={PH} ORDER BY created_at DESC", (project_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def _save_panel(project_id, chapter, page, panel, description, dialogue, style, ai_prompt, notes):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        f"INSERT INTO manga_panels (project_id, chapter, page_num, panel_num, description, dialogue, panel_style, ai_prompt, notes, created_at) VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})",
        (project_id, chapter, page, panel, description, dialogue, style, ai_prompt, notes, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def _load_panels(project_id, chapter=None):
    conn = get_conn()
    c = conn.cursor()
    if chapter:
        c.execute(f"SELECT * FROM manga_panels WHERE project_id={PH} AND chapter={PH} ORDER BY page_num, panel_num",
                  (project_id, chapter))
    else:
        c.execute(f"SELECT * FROM manga_panels WHERE project_id={PH} ORDER BY chapter, page_num, panel_num",
                  (project_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def _ai_generate(prompt: str, system: str = "") -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "❌ No Anthropic API key set. Go to Settings to add it."
    try:
        import anthropic as ant
        client = ant.Anthropic(api_key=api_key)
        msgs = [{"role": "user", "content": prompt}]
        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=system or "You are a creative genius helping develop original stories, characters, worlds, and narratives. Be bold, specific, and cinematic.",
            messages=msgs,
        )
        return resp.content[0].text
    except Exception as e:
        return f"❌ AI Error: {e}"


# ── CSS ──────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Marathon Studio dark cinematic theme */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0a0a0a 0%, #1a0a1a 50%, #0a0a1a 100%);
    color: #f0f0f0;
}
.studio-header {
    background: linear-gradient(90deg, #1a0a2e 0%, #0d1b2a 50%, #1a0a2e 100%);
    border: 1px solid #4a2080;
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
}
.studio-header h1 { color: #d4af37; font-size: 2.5rem; margin-bottom: 0.5rem; }
.studio-header p  { color: #a0a0c0; font-style: italic; }
.quote-bar {
    background: linear-gradient(90deg, #1a1a2e, #16213e, #0f3460);
    border-left: 4px solid #d4af37;
    padding: 0.8rem 1.5rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
    font-style: italic;
    color: #e8d5a3;
}
.project-card {
    background: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 10px;
    padding: 1rem;
    margin: 0.5rem 0;
    transition: border-color 0.2s;
}
.project-card:hover { border-color: #4a2080; }
.panel-box {
    background: #0f0f1a;
    border: 1px solid #2a2a4e;
    border-radius: 8px;
    padding: 0.75rem;
    margin: 0.25rem 0;
    font-family: monospace;
    font-size: 0.85rem;
}
.ai-output {
    background: #0a1628;
    border: 1px solid #1e4080;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    line-height: 1.6;
}
.status-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    background: #2a1a4e;
    color: #c0a0ff;
    margin-left: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Init ─────────────────────────────────────────────────────────────────────────
_ensure_tables()

# ── Header ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="studio-header">
    <h1>🎬 The Marathon Studio</h1>
    <p>Where every vision becomes real. Manga · Film · Series · Legend.</p>
    <p style="color: #6a4a9a; font-size: 0.85rem;">🔒 Private — Darrian Belcher only</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="quote-bar">💜 "Dedication + Consistency = Inevitable." — Nipsey Hussle · "Creativity is connecting things no one else connected." — Jobs · "You came to this earth to accomplish something." — Dr. Sebi</div>', unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────────────────
tab_board, tab_ideas, tab_bible, tab_treatment, tab_manga, tab_ai = st.tabs([
    "📋 Project Board",
    "💡 Idea Vault",
    "📖 Story Bible",
    "🎞️ Script Treatment",
    "🖋️ Manga Panel Writer",
    "🤖 AI Creative Engine",
])

# ════════════════════════════════════════════════════════
# TAB 1: PROJECT BOARD
# ════════════════════════════════════════════════════════
with tab_board:
    st.subheader("📋 Project Board")

    col1, col2 = st.columns([2, 1])
    with col1:
        projects = _load_projects()
        if not projects:
            st.info("No projects yet. Create your first vision below.")
        else:
            # Group by status
            by_status = {}
            for p in projects:
                s = p[5] if p[5] else "💡 Seed Idea"
                by_status.setdefault(s, []).append(p)
            for status, projs in by_status.items():
                st.markdown(f"**{status}** ({len(projs)})")
                for p in projs:
                    pid, title, fmt, genre, logline, pstatus, priv, created, updated = p
                    with st.expander(f"{title} · {fmt or ''}", expanded=False):
                        st.markdown(f"**Genre:** {genre or 'TBD'}  |  **Created:** {created[:10] if created else ''}")
                        if logline:
                            st.markdown(f"*{logline}*")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            new_status = st.selectbox("Status", STATUS_OPTIONS,
                                                       index=STATUS_OPTIONS.index(pstatus) if pstatus in STATUS_OPTIONS else 0,
                                                       key=f"st_{pid}")
                            if new_status != pstatus:
                                _update_project_status(pid, new_status)
                                st.rerun()
                        with c2:
                            if st.button("📝 Open", key=f"open_{pid}"):
                                st.session_state["active_project_id"] = pid
                                st.session_state["active_project_title"] = title
                                st.info(f"✅ '{title}' is now active. Switch to other tabs to develop it.")
                        with c3:
                            if st.button("🗑️ Delete", key=f"del_{pid}"):
                                _delete_project(pid)
                                st.rerun()

    with col2:
        st.markdown("#### ✨ New Project")
        with st.form("new_project_form"):
            p_title  = st.text_input("Title *", placeholder="e.g. The Sovereign Papers")
            p_format = st.selectbox("Format", FORMAT_TYPES)
            p_genre  = st.selectbox("Genre", GENRES)
            p_logline = st.text_area("Logline (1-2 sentences)", placeholder="What's the story in one breath?", height=80)
            p_status = st.selectbox("Status", STATUS_OPTIONS)
            if st.form_submit_button("🚀 Create Project", use_container_width=True):
                if p_title.strip():
                    pid = _create_project(p_title.strip(), p_format, p_genre, p_logline, p_status)
                    st.session_state["active_project_id"] = pid
                    st.session_state["active_project_title"] = p_title.strip()
                    st.success(f"✅ '{p_title}' created!")
                    st.rerun()
                else:
                    st.error("Title required.")

    active_pid = st.session_state.get("active_project_id")
    active_title = st.session_state.get("active_project_title", "None")
    if active_pid:
        st.success(f"🎬 Active Project: **{active_title}** (ID: {active_pid}) — switch tabs to develop")


# ════════════════════════════════════════════════════════
# TAB 2: IDEA VAULT
# ════════════════════════════════════════════════════════
with tab_ideas:
    st.subheader("💡 Idea Vault")
    active_pid = st.session_state.get("active_project_id")
    if not active_pid:
        st.warning("⚡ Select or create a project from the Project Board first.")
    else:
        st.caption(f"Project: **{st.session_state.get('active_project_title', active_pid)}**")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("#### Quick Capture")
            with st.form("idea_form"):
                idea_type = st.selectbox("Type", [
                    "Character Concept", "Scene / Moment", "Dialogue / Line",
                    "World / Setting", "Theme / Message", "Visual / Image",
                    "Title / Subtitle", "Twist / Plot Point", "Soundtrack Note", "Other"
                ])
                idea_content = st.text_area("The Idea", placeholder="Write it raw. Don't filter.", height=120)
                tags = st.text_input("Tags (comma-separated)", placeholder="e.g. death, redemption, Chicago")
                expand_ai = st.checkbox("🤖 Expand with AI")
                ai_voice = st.selectbox("AI Voice", list(AI_VOICES.keys())) if expand_ai else None
                if st.form_submit_button("💾 Save Idea", use_container_width=True):
                    if idea_content.strip():
                        ai_text = ""
                        if expand_ai and ai_voice:
                            with st.spinner("Expanding idea..."):
                                prompt = f"""Expand this creative idea for a {idea_type}:

"{idea_content}"

Tags: {tags}

Make it vivid, specific, and powerful."""
                                ai_text = _ai_generate(prompt, AI_VOICES[ai_voice])
                        _save_idea(active_pid, idea_type, idea_content.strip(), ai_text, tags)
                        st.success("✅ Idea saved!")
                        st.rerun()

        with col2:
            st.markdown("#### Saved Ideas")
            ideas = _load_ideas(active_pid)
            if not ideas:
                st.info("No ideas yet. Start capturing.")
            else:
                for idea in ideas:
                    iid, pid, itype, content, ai_expanded, itags, created = idea
                    with st.expander(f"**{itype}** — {content[:50]}...", expanded=False):
                        st.markdown(f"**Raw Idea:**\n{content}")
                        if itags:
                            st.caption(f"Tags: {itags}")
                        if ai_expanded:
                            st.markdown('<div class="ai-output">', unsafe_allow_html=True)
                            st.markdown(f"**🤖 AI Expanded:**\n\n{ai_expanded}")
                            st.markdown('</div>', unsafe_allow_html=True)
                        st.caption(f"Captured: {created[:10] if created else ''}")


# ════════════════════════════════════════════════════════
# TAB 3: STORY BIBLE
# ════════════════════════════════════════════════════════
with tab_bible:
    st.subheader("📖 Story Bible")
    active_pid = st.session_state.get("active_project_id")
    if not active_pid:
        st.warning("⚡ Select a project first.")
    else:
        st.caption(f"Project: **{st.session_state.get('active_project_title', active_pid)}**")

        BIBLE_SECTIONS = [
            "🌍 World / Setting", "📜 Lore & History", "👤 Main Characters",
            "👥 Supporting Characters", "🎭 Themes & Motifs", "⚡ Conflict & Stakes",
            "🗺️ Story Arc Overview", "💬 Voice & Tone", "🎨 Visual Direction",
            "🎵 Soundtrack Mood Board", "❓ Unanswered Questions", "📝 Other Notes"
        ]

        section = st.selectbox("Bible Section", BIBLE_SECTIONS)

        existing = {row[2]: (row[3], row[4]) for row in _load_story_bible(active_pid)}
        current_content, current_ai = existing.get(section, ("", ""))

        with st.form("bible_form"):
            content = st.text_area("Your Notes", value=current_content, height=200,
                                   placeholder=f"Write your notes for {section}...")
            ai_gen = st.checkbox("🤖 Generate AI version of this section")
            ai_voice = st.selectbox("AI Voice", list(AI_VOICES.keys())) if ai_gen else None
            if st.form_submit_button("💾 Save Section", use_container_width=True):
                ai_text = current_ai
                if ai_gen and ai_voice:
                    with st.spinner(f"Generating {section}..."):
                        proj_rows = [p for p in _load_projects() if p[0] == active_pid]
                        proj_info = proj_rows[0] if proj_rows else None
                        context = f"Project: {proj_info[1] if proj_info else 'Unknown'}\nFormat: {proj_info[2] if proj_info else ''}\nGenre: {proj_info[3] if proj_info else ''}\nLogline: {proj_info[4] if proj_info else ''}"
                        prompt = f"""{context}

Generate the **{section}** section of the Story Bible.

My notes: {content}

Make it deep, specific, and original. Avoid clichés. Make this world feel REAL."""
                        ai_text = _ai_generate(prompt, AI_VOICES[ai_voice])
                _save_story_bible(active_pid, section, content, ai_text)
                st.success(f"✅ {section} saved!")
                st.rerun()

        if current_ai:
            st.markdown("---")
            st.markdown("#### 🤖 AI Version")
            st.markdown(f'<div class="ai-output">{current_ai}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📚 Full Bible Overview")
        bible = _load_story_bible(active_pid)
        if bible:
            for row in bible:
                _, _, sec, cont, ai_cont, _, _ = row
                if cont or ai_cont:
                    with st.expander(sec, expanded=False):
                        if cont:
                            st.markdown(f"**Your Notes:**\n{cont}")
                        if ai_cont:
                            st.markdown(f'<div class="ai-output">{ai_cont}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
# TAB 4: SCRIPT TREATMENT
# ════════════════════════════════════════════════════════
with tab_treatment:
    st.subheader("🎞️ Script Treatment")
    active_pid = st.session_state.get("active_project_id")
    if not active_pid:
        st.warning("⚡ Select a project first.")
    else:
        st.caption(f"Project: **{st.session_state.get('active_project_title', active_pid)}**")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### Generate Treatment")
            with st.form("treatment_form"):
                t_title = st.text_input("Treatment Title", placeholder="e.g. Pilot Episode / Act 1")
                t_notes = st.text_area("Your outline / notes", height=150,
                                       placeholder="Bullet points, rough ideas, what you know so far...")
                ai_voice = st.selectbox("AI Voice", list(AI_VOICES.keys()))
                length = st.select_slider("Treatment Length", ["Short (1 page)", "Medium (3 pages)", "Full (5+ pages)"],
                                          value="Medium (3 pages)")
                if st.form_submit_button("🤖 Generate Treatment", use_container_width=True):
                    if t_title.strip():
                        with st.spinner("Writing your treatment..."):
                            proj_rows = [p for p in _load_projects() if p[0] == active_pid]
                            proj_info = proj_rows[0] if proj_rows else None
                            prompt = f"""Write a {length} script treatment for:

**Project:** {proj_info[1] if proj_info else 'Unknown'}
**Format:** {proj_info[2] if proj_info else ''}
**Genre:** {proj_info[3] if proj_info else ''}
**Logline:** {proj_info[4] if proj_info else ''}

**Treatment Title:** {t_title}

**My Notes:**
{t_notes}

Write a professional treatment in present tense, third person. Include: opening hook, character introductions, escalating conflict, emotional stakes, turning points, resolution direction. Make it cinematic and compelling."""
                            treatment = _ai_generate(prompt, AI_VOICES[ai_voice])
                            _save_treatment(active_pid, t_title, treatment, t_notes)
                            st.session_state["last_treatment"] = treatment
                            st.success("✅ Treatment generated and saved!")
                    else:
                        st.error("Need a treatment title.")

        with col2:
            st.markdown("#### Saved Treatments")
            treatments = _load_treatments(active_pid)
            if not treatments:
                st.info("No treatments yet.")
            else:
                for t in treatments:
                    tid, tpid, ttitle, ttext, tnotes, tver, tcreated = t
                    with st.expander(f"**{ttitle}** v{tver} · {tcreated[:10] if tcreated else ''}", expanded=False):
                        st.markdown(f'<div class="ai-output">{ttext}</div>', unsafe_allow_html=True)
                        if tnotes:
                            st.caption(f"Original notes: {tnotes}")

        if "last_treatment" in st.session_state:
            st.markdown("---")
            st.markdown("#### 📄 Latest Treatment")
            st.markdown(f'<div class="ai-output">{st.session_state["last_treatment"]}</div>', unsafe_allow_html=True)
            if st.download_button("⬇️ Download as .txt", st.session_state["last_treatment"],
                                  file_name=f"treatment_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"):
                pass


# ════════════════════════════════════════════════════════
# TAB 5: MANGA PANEL WRITER
# ════════════════════════════════════════════════════════
with tab_manga:
    st.subheader("🖋️ Manga Panel Writer")
    active_pid = st.session_state.get("active_project_id")
    if not active_pid:
        st.warning("⚡ Select a project first.")
    else:
        st.caption(f"Project: **{st.session_state.get('active_project_title', active_pid)}**")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### Write a Panel")
            with st.form("panel_form"):
                c1, c2, c3 = st.columns(3)
                chapter = c1.number_input("Chapter", min_value=1, value=1)
                page    = c2.number_input("Page", min_value=1, value=1)
                panel   = c3.number_input("Panel", min_value=1, value=1)
                panel_style = st.selectbox("Art Style", PANEL_STYLES)
                description = st.text_area("Panel Description (what we SEE)",
                                           placeholder="e.g. Close-up of a young man's eyes. City lights reflected. Rain. He doesn't blink.",
                                           height=100)
                dialogue = st.text_area("Dialogue / Caption / SFX",
                                        placeholder="Character: 'The marathon continues.'\nNarration: The night never asked permission.\nSFX: BOOM",
                                        height=100)
                notes = st.text_input("Notes for artist", placeholder="e.g. Make it feel suffocating but beautiful")
                gen_prompt = st.checkbox("🤖 Generate AI image prompt for this panel")
                if st.form_submit_button("💾 Save Panel", use_container_width=True):
                    ai_prompt = ""
                    if gen_prompt and description.strip():
                        with st.spinner("Generating image prompt..."):
                            prompt = f"""Generate a detailed AI image generation prompt for this manga/comic panel:

Art Style: {panel_style}
Scene Description: {description}
Dialogue/Caption: {dialogue}

Create a specific prompt for an image generation model (like Midjourney or DALL-E or Stable Diffusion). Include: composition, lighting, mood, character positioning, background detail, color palette (if applicable). Make it production-ready."""
                            ai_prompt = _ai_generate(prompt)
                    _save_panel(active_pid, chapter, page, panel, description, dialogue, panel_style, ai_prompt, notes)
                    st.success(f"✅ Chapter {chapter}, Page {page}, Panel {panel} saved!")
                    st.rerun()

        with col2:
            st.markdown("#### Script View")
            panels = _load_panels(active_pid)
            if not panels:
                st.info("No panels yet.")
            else:
                chapters = sorted(set(p[2] for p in panels))
                sel_chapter = st.selectbox("View Chapter", chapters)
                chapter_panels = [p for p in panels if p[2] == sel_chapter]
                for p in chapter_panels:
                    pid_, ppid, ch, pg, pn, desc, dial, pstyle, aprompt, pnotes, pcreated = p
                    st.markdown(f"""
<div class="panel-box">
<strong>Ch.{ch} — Page {pg} — Panel {pn}</strong> <span style="color:#6a6aaa">({pstyle})</span><br>
<strong>📷 VISUAL:</strong> {desc}<br>
{f'<strong>💬 DIALOGUE:</strong> {dial}<br>' if dial else ''}
{f'<em>🎨 AI Prompt:</em> {aprompt[:120]}...<br>' if aprompt and len(aprompt) > 120 else (f'<em>🎨 AI Prompt:</em> {aprompt}<br>' if aprompt else '')}
{f'<em>📝 Notes:</em> {pnotes}' if pnotes else ''}
</div>
""", unsafe_allow_html=True)

        if panels:
            st.markdown("---")
            # Export full chapter script
            all_txt = []
            for p in _load_panels(active_pid):
                pid_, ppid, ch, pg, pn, desc, dial, pstyle, aprompt, pnotes, pcreated = p
                all_txt.append(f"\nCHAPTER {ch} | PAGE {pg} | PANEL {pn}\n[{pstyle}]\nVISUAL: {desc}\nDIALOGUE: {dial}\nNOTES: {pnotes}\n{'─'*40}")
            if st.download_button("⬇️ Export Full Script (.txt)", "\n".join(all_txt),
                                  file_name=f"manga_script_{datetime.now().strftime('%Y%m%d')}.txt"):
                pass


# ════════════════════════════════════════════════════════
# TAB 6: AI CREATIVE ENGINE
# ════════════════════════════════════════════════════════
with tab_ai:
    st.subheader("🤖 AI Creative Engine — Freeform")
    active_pid = st.session_state.get("active_project_id")

    st.info("🔓 Open creative AI session. No project required. Talk to the studio AI directly.")

    ai_voice = st.selectbox("AI Persona", list(AI_VOICES.keys()),
                            help="Each voice channels a different creative energy.")
    st.caption(f"*{AI_VOICES[ai_voice]}*")

    prompt_type = st.selectbox("What do you need?", [
        "Generate character backstory",
        "Write an opening scene",
        "Develop a world/setting",
        "Create a villain / antagonist",
        "Write dialogue for a scene",
        "Generate a plot twist",
        "Write a manga chapter outline",
        "Create a film logline from raw idea",
        "Write a pitch for this project",
        "Analyze a story idea — strengths & weaknesses",
        "Freestyle — I'll write the whole prompt",
    ])

    if active_pid:
        proj_rows = [p for p in _load_projects() if p[0] == active_pid]
        proj_info = proj_rows[0] if proj_rows else None
        context_inject = f"\n\nActive project context:\nTitle: {proj_info[1] if proj_info else ''}\nFormat: {proj_info[2] if proj_info else ''}\nGenre: {proj_info[3] if proj_info else ''}\nLogline: {proj_info[4] if proj_info else ''}" if proj_info else ""
    else:
        context_inject = ""

    user_prompt = st.text_area(
        "Your prompt",
        height=150,
        placeholder="Pour it out. Stream of consciousness is fine. The AI will shape it.",
    )

    if st.button("🚀 Generate", use_container_width=True, type="primary"):
        if user_prompt.strip():
            full_prompt = f"{prompt_type}:\n\n{user_prompt}{context_inject}"
            with st.spinner("Creating..."):
                result = _ai_generate(full_prompt, AI_VOICES[ai_voice])
            st.session_state["ai_engine_result"] = result
        else:
            st.warning("Enter a prompt.")

    if "ai_engine_result" in st.session_state:
        st.markdown("---")
        st.markdown("#### ✨ Output")
        st.markdown(f'<div class="ai-output">{st.session_state["ai_engine_result"]}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if active_pid and st.button("💾 Save to Idea Vault"):
                _save_idea(active_pid, prompt_type,
                           user_prompt[:500],
                           st.session_state["ai_engine_result"])
                st.success("✅ Saved to Idea Vault!")
        with col2:
            st.download_button("⬇️ Download",
                               st.session_state["ai_engine_result"],
                               file_name=f"marathon_studio_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")

    st.markdown("---")
    st.markdown("""
<div class="quote-bar">
🔱 This studio is yours. Every film that changed the world started as a voice in someone's head they were brave enough to follow.
Build the mythology. Put Crenshaw, Gullah Geechee, NC A&T, VA — ALL of it — on screen. The world needs to see it.
<strong>The Marathon Continues.</strong>
</div>
""", unsafe_allow_html=True)
