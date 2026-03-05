"""
AI-Powered Notes — Page 25
A unified, intelligent notes system to replace Apple Notes, Google Docs,
Microsoft Word, and Notion. Full search, AI summarization, tags, rich text,
Notebooks, Templates, Apple Notes XML import, and export.
"""
import streamlit as st
from datetime import datetime
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.voice_input import render_voice_input

st.set_page_config(
    page_title="📝 Notes — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",            icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",             icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",          icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",            icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",    icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",  icon="🤖")
render_sidebar_user_widget()

# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS notes (
            id {ai},
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            category TEXT DEFAULT 'General',
            tags TEXT DEFAULT '',
            pinned INTEGER DEFAULT 0,
            archived INTEGER DEFAULT 0,
            color TEXT DEFAULT '#1e1e1e',
            word_count INTEGER DEFAULT 0,
            created_at TEXT {ts},
            updated_at TEXT {ts}
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS note_versions (
            id {ai},
            note_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            saved_at TEXT {ts}
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS notebooks (
            id {ai},
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            icon TEXT DEFAULT '📓',
            color TEXT DEFAULT '#1565c0',
            created_at TEXT {ts}
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS note_templates (
            id {ai},
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'General',
            content TEXT DEFAULT '',
            icon TEXT DEFAULT '📄',
            created_at TEXT {ts}
        )
    """)
    # Add notebook_id column to notes if missing (migration-safe)
    try:
        db_exec(conn, "ALTER TABLE notes ADD COLUMN notebook_id INTEGER DEFAULT NULL")
        conn.commit()
    except Exception:
        pass  # Column already exists
    conn.commit()
    conn.close()

_ensure_tables()

# ── Constants ──────────────────────────────────────────────────────────────────
CATEGORIES = [
    "General", "Business", "Finance", "Ideas", "Journal", "Research",
    "Goals", "Health", "Tech", "Creative", "Travel", "People", "Learning"
]
NOTE_COLORS = {
    "Default": "#1e1e1e",
    "Peach":   "#ff8a65",
    "Blue":    "#1565c0",
    "Green":   "#2e7d32",
    "Purple":  "#6a1b9a",
    "Red":     "#b71c1c",
    "Gold":    "#f57f17",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0

def _load_notes(search="", category=None, pinned_only=False, archived=False, tag=None):
    conn = get_conn()
    where, params = ["archived=?"], [1 if archived else 0]
    if pinned_only:
        where.append("pinned=1")
    if category and category != "All":
        where.append("category=?"); params.append(category)
    if tag:
        where.append("tags LIKE ?"); params.append(f"%{tag}%")
    clause = "WHERE " + " AND ".join(where)
    c = db_exec(conn,
        f"SELECT * FROM notes {clause} ORDER BY pinned DESC, updated_at DESC",
        tuple(params))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    results = [dict(zip(cols, r)) for r in rows]
    if search:
        sl = search.lower()
        results = [n for n in results
                   if sl in n.get("title","").lower()
                   or sl in n.get("content","").lower()
                   or sl in n.get("tags","").lower()]
    return results

def _get_note(note_id: int):
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM notes WHERE id=?", (note_id,))
    row = c.fetchone()
    cols = [d[0] for d in c.description]
    conn.close()
    return dict(zip(cols, row)) if row else None

def _save_note(note_id: int, title: str, content: str, category: str, tags: str, color: str):
    wc  = _word_count(content)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    # Save version snapshot before update
    old = _get_note(note_id)
    if old and old.get("content"):
        db_exec(conn, "INSERT INTO note_versions (note_id, content, saved_at) VALUES (?,?,?)",
                (note_id, old["content"], now))
    db_exec(conn,
        "UPDATE notes SET title=?,content=?,category=?,tags=?,color=?,word_count=?,updated_at=? WHERE id=?",
        (title.strip(), content, category, tags.strip(), color, wc, now, note_id))
    conn.commit(); conn.close()

def _create_note(title: str, content: str, category: str, tags: str, color: str) -> int:
    wc = _word_count(content)
    conn = get_conn()
    c = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        c.execute(
            f"INSERT INTO notes (title,content,category,tags,color,word_count) VALUES ({ph},{ph},{ph},{ph},{ph},{ph}) RETURNING id",
            (title.strip(), content, category, tags.strip(), color, wc))
        note_id = c.fetchone()[0]
    else:
        c.execute(
            f"INSERT INTO notes (title,content,category,tags,color,word_count) VALUES ({ph},{ph},{ph},{ph},{ph},{ph})",
            (title.strip(), content, category, tags.strip(), color, wc))
        note_id = c.lastrowid
    conn.commit(); conn.close()
    return note_id

def _delete_note(note_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM note_versions WHERE note_id=?", (note_id,))
    db_exec(conn, "DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit(); conn.close()

def _toggle_pin(note_id: int, current: int):
    conn = get_conn()
    db_exec(conn, "UPDATE notes SET pinned=? WHERE id=?", (0 if current else 1, note_id))
    conn.commit(); conn.close()

def _toggle_archive(note_id: int, current: int):
    conn = get_conn()
    db_exec(conn, "UPDATE notes SET archived=? WHERE id=?", (0 if current else 1, note_id))
    conn.commit(); conn.close()

def _ask_ai(prompt: str) -> str:
    api_key = get_setting("anthropic_api_key", "")
    if not api_key:
        api_key = st.session_state.get("anthropic_api_key", "")
    if not api_key:
        return "No Anthropic API key found. Add it in the AI Insights page settings."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI Error: {e}"

def _get_all_tags():
    conn = get_conn()
    c = db_exec(conn, "SELECT tags FROM notes WHERE tags != '' AND archived=0")
    rows = c.fetchall()
    conn.close()
    tags = set()
    for row in rows:
        t = row[0] if not isinstance(row, dict) else row["tags"]
        for tag in t.split(","):
            tag = tag.strip()
            if tag:
                tags.add(tag)
    return sorted(tags)

# ── Notebook Helpers ───────────────────────────────────────────────────────────
def _load_notebooks():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM notebooks ORDER BY name ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _create_notebook(name: str, description: str, icon: str, color: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        c.execute(
            f"INSERT INTO notebooks (name, description, icon, color) VALUES ({ph},{ph},{ph},{ph}) RETURNING id",
            (name.strip(), description.strip(), icon, color))
        nb_id = c.fetchone()[0]
    else:
        c.execute(
            f"INSERT INTO notebooks (name, description, icon, color) VALUES ({ph},{ph},{ph},{ph})",
            (name.strip(), description.strip(), icon, color))
        nb_id = c.lastrowid
    conn.commit(); conn.close()
    return nb_id

def _delete_notebook(nb_id: int):
    conn = get_conn()
    # Unassign notes from this notebook
    db_exec(conn, "UPDATE notes SET notebook_id=NULL WHERE notebook_id=?", (nb_id,))
    db_exec(conn, "DELETE FROM notebooks WHERE id=?", (nb_id,))
    conn.commit(); conn.close()

def _assign_note_to_notebook(note_id: int, notebook_id):
    conn = get_conn()
    db_exec(conn, "UPDATE notes SET notebook_id=? WHERE id=?", (notebook_id, note_id))
    conn.commit(); conn.close()

def _load_notes_in_notebook(notebook_id: int):
    conn = get_conn()
    c = db_exec(conn,
        "SELECT * FROM notes WHERE notebook_id=? AND archived=0 ORDER BY updated_at DESC",
        (notebook_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

# ── Template Helpers ───────────────────────────────────────────────────────────
BUILTIN_TEMPLATES = [
    {
        "name": "Meeting Notes",
        "description": "Structure for capturing meeting decisions and action items",
        "category": "Business",
        "icon": "🤝",
        "content": (
            "# Meeting Notes\n\n"
            "**Date:** \n"
            "**Attendees:** \n"
            "**Purpose:** \n\n"
            "---\n\n"
            "## Agenda\n"
            "1. \n"
            "2. \n\n"
            "## Discussion\n\n\n"
            "## Decisions Made\n"
            "- \n\n"
            "## Action Items\n"
            "- [ ] \n"
            "- [ ] \n\n"
            "## Next Meeting\n"
            "**Date:** \n"
        ),
    },
    {
        "name": "Daily Journal",
        "description": "Daily reflection and gratitude journaling",
        "category": "Journal",
        "icon": "📔",
        "content": (
            "# Daily Journal — {date}\n\n"
            "## Morning Intentions\n"
            "Today I intend to...\n\n"
            "## Gratitude\n"
            "1. \n"
            "2. \n"
            "3. \n\n"
            "## Top 3 Priorities\n"
            "1. [ ] \n"
            "2. [ ] \n"
            "3. [ ] \n\n"
            "## Notes & Thoughts\n\n\n"
            "## Evening Reflection\n"
            "What went well today?\n\n"
            "What could be improved?\n\n"
            "Energy level: /10\n"
        ),
    },
    {
        "name": "Project Plan",
        "description": "Project overview with goals, tasks, and timeline",
        "category": "Business",
        "icon": "📋",
        "content": (
            "# Project: \n\n"
            "**Owner:** \n"
            "**Start Date:** \n"
            "**Target Date:** \n"
            "**Status:** Planning\n\n"
            "---\n\n"
            "## Objective\n\n\n"
            "## Key Results / Success Metrics\n"
            "- \n\n"
            "## Tasks\n"
            "- [ ] \n"
            "- [ ] \n"
            "- [ ] \n\n"
            "## Resources Needed\n"
            "- \n\n"
            "## Risks & Blockers\n"
            "- \n\n"
            "## Notes\n\n"
        ),
    },
    {
        "name": "Idea Capture",
        "description": "Quick idea exploration and brainstorm",
        "category": "Ideas",
        "icon": "💡",
        "content": (
            "# Idea: \n\n"
            "**Captured:** {date}\n\n"
            "## The Core Idea\n\n\n"
            "## Why This Matters\n\n\n"
            "## Potential Use Cases\n"
            "- \n\n"
            "## Next Steps to Explore\n"
            "- [ ] \n\n"
            "## Related Ideas / Resources\n"
            "- \n"
        ),
    },
    {
        "name": "Research Notes",
        "description": "Structured research and learning notes",
        "category": "Research",
        "icon": "🔬",
        "content": (
            "# Research: \n\n"
            "**Topic:** \n"
            "**Date:** {date}\n"
            "**Sources:** \n\n"
            "---\n\n"
            "## Key Findings\n\n\n"
            "## Important Quotes\n"
            "> \n\n"
            "## My Analysis\n\n\n"
            "## Questions Still Unanswered\n"
            "- \n\n"
            "## References\n"
            "1. \n"
        ),
    },
    {
        "name": "Goal Setting",
        "description": "SMART goal planning template",
        "category": "Goals",
        "icon": "🎯",
        "content": (
            "# Goal: \n\n"
            "**Timeframe:** \n"
            "**Category:** \n\n"
            "## SMART Definition\n"
            "- **Specific:** \n"
            "- **Measurable:** \n"
            "- **Achievable:** \n"
            "- **Relevant:** \n"
            "- **Time-bound:** \n\n"
            "## Why This Goal Matters\n\n\n"
            "## Milestones\n"
            "- [ ] \n"
            "- [ ] \n"
            "- [ ] \n\n"
            "## Potential Obstacles\n"
            "- \n\n"
            "## Progress Notes\n\n"
        ),
    },
]

def _load_templates():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM note_templates ORDER BY name ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _create_template(name: str, description: str, category: str, content: str, icon: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        c.execute(
            f"INSERT INTO note_templates (name, description, category, content, icon) VALUES ({ph},{ph},{ph},{ph},{ph}) RETURNING id",
            (name.strip(), description.strip(), category, content, icon))
        t_id = c.fetchone()[0]
    else:
        c.execute(
            f"INSERT INTO note_templates (name, description, category, content, icon) VALUES ({ph},{ph},{ph},{ph},{ph})",
            (name.strip(), description.strip(), category, content, icon))
        t_id = c.lastrowid
    conn.commit(); conn.close()
    return t_id

def _delete_template(t_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM note_templates WHERE id=?", (t_id,))
    conn.commit(); conn.close()

# ── Import Helpers ─────────────────────────────────────────────────────────────
def _import_apple_notes_xml(xml_bytes: bytes) -> list:
    """Parse an Apple Notes / iTunes XML export (plist format) and return a list of note dicts."""
    import plistlib
    try:
        plist = plistlib.loads(xml_bytes)
    except Exception as e:
        return [], f"Failed to parse plist: {e}"

    notes = []
    # Apple Notes exports as a flat plist dict; handle both array and dict structures
    if isinstance(plist, list):
        items = plist
    elif isinstance(plist, dict):
        # Try common keys
        items = plist.get("notes", plist.get("Notes", [plist]))
    else:
        items = []

    for item in items:
        if not isinstance(item, dict):
            continue
        title   = item.get("title", item.get("Title", item.get("ZTitle", "Imported Note")))
        body    = item.get("body",  item.get("Body",  item.get("ZText", item.get("content", ""))))
        created = item.get("creation date", item.get("ZCreationDate", ""))
        notes.append({
            "title":   str(title).strip() or "Imported Note",
            "content": str(body).strip(),
            "created": str(created)[:10] if created else "",
        })
    return notes, None

def _export_notes_markdown(notes: list) -> str:
    """Export a list of note dicts as a combined Markdown string."""
    lines = []
    for n in notes:
        lines.append(f"# {n.get('title','Untitled')}")
        lines.append(f"*Category: {n.get('category','General')} | Tags: {n.get('tags','')} | Updated: {str(n.get('updated_at',''))[:10]}*")
        lines.append("")
        lines.append(n.get("content",""))
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("📝 Notes")
st.caption("Your AI-powered second brain — smarter than Apple Notes, more personal than Notion.")

all_notes = _load_notes()
pinned    = [n for n in all_notes if n.get("pinned")]
total_wc  = sum(n.get("word_count", 0) for n in all_notes)
all_tags  = _get_all_tags()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Notes",  len(all_notes))
m2.metric("Pinned",       len(pinned))
m3.metric("Total Words",  f"{total_wc:,}")
m4.metric("Tags",         len(all_tags))

st.divider()

# ── Main tabs ──────────────────────────────────────────────────────────────────
tab_browse, tab_editor, tab_ai, tab_notebooks, tab_templates, tab_import = st.tabs([
    "📚 All Notes", "✍️ Editor", "🤖 AI Tools",
    "📓 Notebooks", "📄 Templates", "📥 Import / Export"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — BROWSE
# ══════════════════════════════════════════════════════════════════════════════
with tab_browse:
    # ── Toolbar ────────────────────────────────────────────────────────────────
    tcol1, tcol2, tcol3, tcol4 = st.columns([3, 2, 2, 1])
    with tcol1:
        search_q = st.text_input("🔍 Search notes", placeholder="Title, content, or tag...", label_visibility="collapsed")
    with tcol2:
        cat_filter = st.selectbox("Category", ["All"] + CATEGORIES, label_visibility="collapsed")
    with tcol3:
        tag_filter = st.selectbox("Tag", ["All"] + all_tags, label_visibility="collapsed") if all_tags else "All"
    with tcol4:
        show_archived = st.checkbox("Archived", value=False)

    if st.button("➕ New Note", type="primary"):
        st.session_state["editing_note_id"] = "new"
        st.session_state["active_tab"] = "editor"

    st.divider()

    # If user just created/selected a note, jump to editor
    if st.session_state.get("active_tab") == "editor":
        st.info("Switch to the **✍️ Editor** tab to write your note.")

    tag_arg = tag_filter if (tag_filter and tag_filter != "All") else None
    notes = _load_notes(
        search=search_q,
        category=cat_filter if cat_filter != "All" else None,
        archived=show_archived,
        tag=tag_arg,
    )

    if not notes:
        st.info("No notes found. Create one with ➕ New Note above!")
    else:
        st.caption(f"{len(notes)} note(s)")
        # Grid layout: 3 columns
        cols = st.columns(3)
        for idx, note in enumerate(notes):
            with cols[idx % 3]:
                ncolor = note.get("color", "#1e1e1e")
                pin_icon = "📌 " if note.get("pinned") else ""
                preview = note.get("content", "")[:200].replace("\n", " ")
                wc = note.get("word_count", 0)
                upd = str(note.get("updated_at", ""))[:10]
                tags_list = [t.strip() for t in note.get("tags","").split(",") if t.strip()]
                tag_html = " ".join(
                    f'<span style="background:#333;color:#aaa;padding:1px 6px;border-radius:8px;font-size:10px">{t}</span>'
                    for t in tags_list[:4]
                )
                st.markdown(
                    f'<div style="border:1px solid #333;border-left:4px solid {ncolor};'
                    f'border-radius:8px;padding:12px;margin-bottom:4px;background:#111">'
                    f'<b style="font-size:14px">{pin_icon}{note["title"]}</b><br>'
                    f'<span style="color:#aaa;font-size:11px">{note.get("category","General")} · {wc} words · {upd}</span><br>'
                    f'<span style="color:#888;font-size:12px">{preview[:150]}{"…" if len(preview)>150 else ""}</span><br>'
                    f'{tag_html}</div>',
                    unsafe_allow_html=True
                )
                ba, bb, bc = st.columns(3)
                if ba.button("✏️ Edit", key=f"edit_note_{note['id']}"):
                    st.session_state["editing_note_id"] = note["id"]
                if bb.button("📌" if not note.get("pinned") else "📍", key=f"pin_{note['id']}"):
                    _toggle_pin(note["id"], note.get("pinned", 0))
                    st.rerun()
                if bc.button("🗑️", key=f"del_n_{note['id']}"):
                    _delete_note(note["id"])
                    st.toast("Note deleted.")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EDITOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_editor:
    editing_id = st.session_state.get("editing_note_id")

    # ── Note selector ──────────────────────────────────────────────────────────
    note_options = [(n["id"], n["title"]) for n in _load_notes()]
    note_select_options = [("new", "✨ New Note")] + note_options
    current_idx = 0
    if editing_id and editing_id != "new":
        ids = [x[0] for x in note_select_options]
        if editing_id in ids:
            current_idx = ids.index(editing_id)

    selected = st.selectbox(
        "Note",
        options=[x[0] for x in note_select_options],
        format_func=lambda x: "✨ New Note" if x == "new" else dict(note_options).get(x, "Unknown"),
        index=current_idx,
        label_visibility="collapsed",
    )
    st.session_state["editing_note_id"] = selected

    # ── Load existing or blank ─────────────────────────────────────────────────
    if selected == "new":
        existing = {"title": "", "content": "", "category": "General", "tags": "", "color": "#1e1e1e"}
    else:
        existing = _get_note(selected) or {"title": "", "content": "", "category": "General", "tags": "", "color": "#1e1e1e"}

    # ── Editor form ────────────────────────────────────────────────────────────
    ef1, ef2, ef3 = st.columns([4, 2, 2])
    edit_title    = ef1.text_input("Title", value=existing.get("title",""), placeholder="Note title...")
    edit_category = ef2.selectbox("Category", CATEGORIES,
                                  index=CATEGORIES.index(existing.get("category","General"))
                                  if existing.get("category","General") in CATEGORIES else 0)
    color_name    = ef3.selectbox("Color", list(NOTE_COLORS.keys()))
    edit_color    = NOTE_COLORS[color_name]
    edit_tags     = st.text_input("Tags", value=existing.get("tags",""),
                                  placeholder="ideas, business, finance (comma separated)")

    # ── Rich text area ─────────────────────────────────────────────────────────
    edit_content = st.text_area(
        "Content",
        value=existing.get("content",""),
        height=450,
        placeholder=(
            "Start writing...\n\n"
            "Supports Markdown: **bold**, *italic*, # headings, - bullet lists, "
            "> blockquotes, `code`, and more."
        ),
        label_visibility="collapsed",
    )
    wc_live = _word_count(edit_content)
    st.caption(f"📝 {wc_live} words · {len(edit_content)} characters")

    # ── Preview toggle ─────────────────────────────────────────────────────────
    if st.checkbox("👁️ Preview (Markdown rendered)", value=False):
        st.markdown("---")
        st.markdown(edit_content)
        st.markdown("---")

    # ── Action buttons ─────────────────────────────────────────────────────────
    sa, sb, sc, sd = st.columns(4)
    if sa.button("💾 Save", type="primary", use_container_width=True):
        if edit_title.strip():
            if selected == "new":
                new_id = _create_note(edit_title, edit_content, edit_category, edit_tags, edit_color)
                st.session_state["editing_note_id"] = new_id
                st.success("✅ Note created!")
            else:
                _save_note(selected, edit_title, edit_content, edit_category, edit_tags, edit_color)
                st.success("✅ Saved!")
            st.rerun()
        else:
            st.error("Title is required.")

    if sb.button("📋 Copy", use_container_width=True):
        st.session_state["clipboard"] = edit_content
        st.toast("Content copied to clipboard session!")

    if sc.button("🗃️ Archive", use_container_width=True) and selected != "new":
        _toggle_archive(selected, existing.get("archived", 0))
        st.toast("Archived!" if not existing.get("archived") else "Unarchived!")
        st.session_state["editing_note_id"] = "new"
        st.rerun()

    if sd.button("🗑️ Delete", use_container_width=True) and selected != "new":
        _delete_note(selected)
        st.toast("Note deleted.")
        st.session_state["editing_note_id"] = "new"
        st.rerun()

    # ── Version history ────────────────────────────────────────────────────────
    if selected != "new":
        with st.expander("🕐 Version History"):
            conn = get_conn()
            c = db_exec(conn, "SELECT * FROM note_versions WHERE note_id=? ORDER BY saved_at DESC LIMIT 10", (selected,))
            rows = c.fetchall()
            cols_v = [d[0] for d in c.description]
            conn.close()
            versions = [dict(zip(cols_v, r)) for r in rows]
            if not versions:
                st.caption("No previous versions saved yet.")
            else:
                for v in versions:
                    with st.container():
                        st.caption(f"📅 {v.get('saved_at','')[:16]}")
                        st.text(v.get("content","")[:300] + "…" if len(v.get("content","")) > 300 else v.get("content",""))
                        if st.button("↩️ Restore this version", key=f"restore_{v['id']}"):
                            _save_note(selected, edit_title, v["content"], edit_category, edit_tags, edit_color)
                            st.success("Version restored!")
                            st.rerun()
                    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI TOOLS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("### 🤖 AI Note Tools")
    st.caption("Use Claude to summarize, expand, reformat, or analyze any note.")

    # Pick a note to work on
    ai_note_options = [(n["id"], n["title"]) for n in _load_notes()]
    if not ai_note_options:
        st.info("Create some notes first, then come back to use AI tools!")
    else:
        ai_note_id = st.selectbox("Select a note to work on",
                                  [x[0] for x in ai_note_options],
                                  format_func=lambda x: dict(ai_note_options).get(x, "?"))
        ai_note = _get_note(ai_note_id)
        if ai_note:
            st.caption(f"**{ai_note['title']}** — {ai_note.get('word_count',0)} words")
            content_preview = ai_note.get("content","")[:500]
            if len(ai_note.get("content","")) > 500:
                content_preview += "…"
            with st.expander("Preview note content"):
                st.text(content_preview)

        ai_action = st.selectbox("What should AI do?", [
            "Summarize this note",
            "Expand and enrich this note",
            "Extract key action items / tasks",
            "Reformat as bullet points",
            "Reformat as a structured document",
            "Find connections to other notes",
            "Generate questions from this note",
            "Improve writing clarity",
            "Custom instruction",
        ])

        custom_instr = ""
        if ai_action == "Custom instruction":
            custom_instr = st.text_area("Your instruction", height=100)

        if st.button("✨ Run AI", type="primary") and ai_note:
            note_content = ai_note.get("content","")
            note_title   = ai_note.get("title","")

            action_prompts = {
                "Summarize this note": f"Summarize the following note titled '{note_title}' in 3-5 sentences:\n\n{note_content}",
                "Expand and enrich this note": f"Expand and enrich this note titled '{note_title}'. Add detail, context, and depth while preserving the original voice:\n\n{note_content}",
                "Extract key action items / tasks": f"Extract all action items, tasks, and next steps from this note titled '{note_title}':\n\n{note_content}",
                "Reformat as bullet points": f"Reformat this note titled '{note_title}' as a clean, organized bullet point list:\n\n{note_content}",
                "Reformat as a structured document": f"Reformat this note titled '{note_title}' as a structured document with clear headings, sections, and formatting:\n\n{note_content}",
                "Find connections to other notes": f"This is a note titled '{note_title}':\n\n{note_content}\n\nSuggest connections, related topics, themes, and how this relates to broader ideas in life, work, and creativity.",
                "Generate questions from this note": f"Generate 10 thoughtful questions to explore the ideas further from this note titled '{note_title}':\n\n{note_content}",
                "Improve writing clarity": f"Improve the clarity, flow, and readability of this note titled '{note_title}' while preserving the core meaning:\n\n{note_content}",
                "Custom instruction": f"{custom_instr}\n\nNote titled '{note_title}':\n\n{note_content}",
            }

            prompt = action_prompts.get(ai_action, f"Help with this note:\n\n{note_content}")
            with st.spinner("AI is thinking..."):
                result = _ask_ai(prompt)

            st.markdown("#### AI Result")
            st.markdown(result)

            # Option to save AI result as a new note
            if st.button("💾 Save AI output as new note"):
                new_title = f"[AI] {ai_action} — {note_title}"
                new_id = _create_note(new_title, result, "General", "ai-generated", "#6a1b9a")
                st.success(f"✅ Saved as new note: '{new_title}'")
                st.session_state["editing_note_id"] = new_id

    # ── Quick capture ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### ⚡ Quick Capture")
    st.caption("Capture a thought fast — speak it or type it.")

    # Voice capture
    voice_text = render_voice_input(
        label="🎤 Speak your note",
        key="notes_quick_voice",
    )
    if voice_text and "notes_voice_prefill" not in st.session_state:
        st.session_state["notes_voice_prefill"] = voice_text

    voice_prefill = st.session_state.pop("notes_voice_prefill", "")

    with st.form("quick_capture", clear_on_submit=True):
        qc_text = st.text_area(
            "What's on your mind?",
            value=voice_prefill,
            height=120,
            placeholder="Brain dump here... or use the mic above.",
        )
        qc_title = st.text_input("Title (optional)", placeholder="Auto-generated if blank")
        qc_cat   = st.selectbox("Category", CATEGORIES, index=0)
        if st.form_submit_button("⚡ Capture", type="primary", use_container_width=True):
            if qc_text.strip():
                title = qc_title.strip() or f"Quick Note — {datetime.now().strftime('%b %d %Y %H:%M')}"
                _create_note(title, qc_text.strip(), qc_cat, "quick-capture", "#1e1e1e")
                st.success(f"✅ Captured: '{title}'")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NOTEBOOKS
# ══════════════════════════════════════════════════════════════════════════════
with tab_notebooks:
    st.markdown("### 📓 Notebooks")
    st.caption("Organize notes into notebooks — like folders in Apple Notes or spaces in Notion.")

    notebooks = _load_notebooks()
    nb_col1, nb_col2 = st.columns([2, 1])

    with nb_col2:
        st.markdown("#### ➕ New Notebook")
        with st.form("new_notebook_form", clear_on_submit=True):
            nb_name  = st.text_input("Notebook Name", placeholder="e.g. Work, Personal, Ideas…")
            nb_desc  = st.text_input("Description (optional)")
            nb_icon  = st.selectbox("Icon", ["📓", "📒", "📔", "📕", "📗", "📘", "📙", "🗂️", "📁", "🏠", "💼", "🎯"])
            nb_color = st.selectbox("Color", list(NOTE_COLORS.keys()))
            if st.form_submit_button("Create Notebook", type="primary"):
                if nb_name.strip():
                    _create_notebook(nb_name, nb_desc, nb_icon, NOTE_COLORS[nb_color])
                    st.success(f"✅ Notebook '{nb_name}' created!")
                    st.rerun()
                else:
                    st.error("Name is required.")

    with nb_col1:
        if not notebooks:
            st.info("No notebooks yet. Create one to organize your notes.")
        else:
            for nb in notebooks:
                nb_notes = _load_notes_in_notebook(nb["id"])
                with st.expander(
                    f"{nb.get('icon','📓')} **{nb['name']}** — {len(nb_notes)} notes",
                    expanded=False
                ):
                    st.caption(nb.get("description",""))
                    if nb_notes:
                        for nn in nb_notes:
                            nc1, nc2 = st.columns([4, 1])
                            nc1.markdown(f"**{nn['title']}** · *{nn.get('category','')}* · {str(nn.get('updated_at',''))[:10]}")
                            if nc2.button("✏️", key=f"nb_edit_{nn['id']}"):
                                st.session_state["editing_note_id"] = nn["id"]
                                st.info("Switch to the **✍️ Editor** tab to edit.")
                    else:
                        st.caption("No notes in this notebook yet.")

                    # Assign a note to this notebook
                    all_unassigned = [n for n in _load_notes() if not n.get("notebook_id")]
                    if all_unassigned:
                        st.markdown("---")
                        assign_options = {n["id"]: n["title"] for n in all_unassigned}
                        assign_id = st.selectbox(
                            "Add a note to this notebook",
                            options=list(assign_options.keys()),
                            format_func=lambda x: assign_options[x],
                            key=f"assign_sel_{nb['id']}",
                        )
                        if st.button("➕ Add to Notebook", key=f"assign_btn_{nb['id']}"):
                            _assign_note_to_notebook(assign_id, nb["id"])
                            st.success("Note added!")
                            st.rerun()

                    if st.button("🗑️ Delete Notebook", key=f"del_nb_{nb['id']}"):
                        _delete_notebook(nb["id"])
                        st.toast(f"Notebook '{nb['name']}' deleted.")
                        st.rerun()

    # ── Unassigned notes ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 📄 Notes Without a Notebook")
    unassigned = [n for n in _load_notes() if not n.get("notebook_id")]
    if unassigned:
        st.caption(f"{len(unassigned)} unassigned note(s)")
        for un in unassigned[:10]:
            uc1, uc2 = st.columns([5, 1])
            uc1.markdown(f"**{un['title']}** · *{un.get('category','')}* · {str(un.get('updated_at',''))[:10]}")
            if uc2.button("✏️ Edit", key=f"unedit_{un['id']}"):
                st.session_state["editing_note_id"] = un["id"]
    else:
        st.info("All notes are assigned to notebooks!")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════
with tab_templates:
    st.markdown("### 📄 Note Templates")
    st.caption("Start a new note from a pre-built or custom template.")

    today_str = datetime.now().strftime("%B %d, %Y")

    # ── Built-in templates ─────────────────────────────────────────────────────
    st.markdown("#### 🏗️ Built-in Templates")
    bt_cols = st.columns(3)
    for bi, tmpl in enumerate(BUILTIN_TEMPLATES):
        with bt_cols[bi % 3]:
            st.markdown(
                f'<div style="border:1px solid #333;border-radius:8px;padding:12px;margin-bottom:8px;background:#111">'
                f'<b>{tmpl["icon"]} {tmpl["name"]}</b><br>'
                f'<span style="color:#aaa;font-size:12px">{tmpl["category"]}</span><br>'
                f'<span style="color:#888;font-size:11px">{tmpl["description"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"Use Template", key=f"use_builtin_{bi}"):
                # Replace {date} placeholder
                filled = tmpl["content"].replace("{date}", today_str)
                st.session_state["template_prefill"] = {
                    "title": tmpl["name"],
                    "content": filled,
                    "category": tmpl["category"],
                }
                st.session_state["editing_note_id"] = "new"
                st.success(f"✅ Template loaded! Go to the **✍️ Editor** tab.")

    # Apply prefill from template if set
    if "template_prefill" in st.session_state:
        pf = st.session_state.pop("template_prefill")
        st.info(
            f"Template **{pf['title']}** is ready in the Editor tab with pre-filled content."
        )

    st.divider()

    # ── Custom templates (saved to DB) ─────────────────────────────────────────
    st.markdown("#### 📝 My Custom Templates")
    custom_templates = _load_templates()

    if not custom_templates:
        st.info("No custom templates yet. Create one below!")
    else:
        ct_cols = st.columns(3)
        for ci, ct in enumerate(custom_templates):
            with ct_cols[ci % 3]:
                st.markdown(
                    f'<div style="border:1px solid #444;border-radius:8px;padding:12px;margin-bottom:8px;background:#111">'
                    f'<b>{ct.get("icon","📄")} {ct["name"]}</b><br>'
                    f'<span style="color:#aaa;font-size:12px">{ct.get("category","General")}</span><br>'
                    f'<span style="color:#888;font-size:11px">{ct.get("description","")}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                cu1, cu2 = st.columns(2)
                if cu1.button("Use", key=f"use_custom_{ct['id']}"):
                    filled = ct["content"].replace("{date}", today_str)
                    st.session_state["editing_note_id"] = "new"
                    st.session_state["template_prefill"] = {
                        "title": ct["name"],
                        "content": filled,
                        "category": ct.get("category","General"),
                    }
                    st.success("Template loaded! Go to the **✍️ Editor** tab.")
                if cu2.button("🗑️", key=f"del_tmpl_{ct['id']}"):
                    _delete_template(ct["id"])
                    st.toast("Template deleted.")
                    st.rerun()

    st.divider()
    st.markdown("#### ➕ Save Current Note as Template")
    with st.form("save_as_template_form", clear_on_submit=True):
        tmpl_name = st.text_input("Template Name", placeholder="e.g. Weekly Review")
        tmpl_desc = st.text_input("Description")
        tmpl_cat  = st.selectbox("Category", CATEGORIES)
        tmpl_icon = st.selectbox("Icon", ["📄", "📝", "🤝", "📔", "📋", "💡", "🔬", "🎯", "📊", "🗒️"])
        tmpl_body = st.text_area("Template Content", height=200,
                                  placeholder="Write your template here. Use {date} for today's date.")
        if st.form_submit_button("💾 Save as Template", type="primary"):
            if tmpl_name.strip() and tmpl_body.strip():
                _create_template(tmpl_name, tmpl_desc, tmpl_cat, tmpl_body, tmpl_icon)
                st.success(f"✅ Template '{tmpl_name}' saved!")
                st.rerun()
            else:
                st.error("Name and content are required.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — IMPORT / EXPORT
# ══════════════════════════════════════════════════════════════════════════════
with tab_import:
    st.markdown("### 📥 Import / Export Notes")

    imp_col, exp_col = st.columns(2)

    # ── IMPORT ─────────────────────────────────────────────────────────────────
    with imp_col:
        st.markdown("#### 📥 Import")

        import_mode = st.radio(
            "Import from",
            ["Apple Notes XML (plist)", "Plain Text / Markdown file"],
            horizontal=True,
        )

        if import_mode == "Apple Notes XML (plist)":
            st.caption(
                "**How to export from Apple Notes:**\n"
                "Open Notes app → File → Export as PDF won't work; instead, "
                "use **File → Export to XML** if available, or use a third-party "
                "tool to export your notes library to plist/XML format, then upload it here."
            )
            uploaded_xml = st.file_uploader(
                "Upload Apple Notes .xml / .plist file",
                type=["xml", "plist"],
                key="apple_notes_upload",
            )
            if uploaded_xml:
                xml_bytes = uploaded_xml.read()
                parsed, err = _import_apple_notes_xml(xml_bytes)
                if err:
                    st.error(f"Parse error: {err}")
                elif not parsed:
                    st.warning("No notes found in the file. Check that it's a valid Apple Notes export.")
                else:
                    st.success(f"Found {len(parsed)} note(s) to import.")
                    import_cat = st.selectbox("Assign Category", CATEGORIES, key="import_cat_xml")
                    if st.button("⬇️ Import All Notes", type="primary", key="do_import_xml"):
                        for pn in parsed:
                            title   = pn["title"] or "Imported Note"
                            content = pn["content"]
                            tags    = "apple-notes,imported"
                            _create_note(title, content, import_cat, tags, "#1565c0")
                        st.success(f"✅ Imported {len(parsed)} notes!")
                        st.rerun()

        else:  # Plain text / Markdown
            st.caption(
                "Upload a `.txt` or `.md` file. Each file becomes one note. "
                "The filename (without extension) will be used as the note title."
            )
            uploaded_txt = st.file_uploader(
                "Upload .txt or .md file(s)",
                type=["txt", "md"],
                accept_multiple_files=True,
                key="plain_text_upload",
            )
            if uploaded_txt:
                txt_cat = st.selectbox("Category for imported notes", CATEGORIES, key="import_cat_txt")
                if st.button("⬇️ Import Files", type="primary", key="do_import_txt"):
                    count = 0
                    for f in uploaded_txt:
                        try:
                            content = f.read().decode("utf-8", errors="replace")
                            title   = f.name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
                            _create_note(title, content, txt_cat, "imported,text", "#1e1e1e")
                            count += 1
                        except Exception as ex:
                            st.warning(f"Skipped {f.name}: {ex}")
                    st.success(f"✅ Imported {count} file(s) as notes!")
                    st.rerun()

    # ── EXPORT ─────────────────────────────────────────────────────────────────
    with exp_col:
        st.markdown("#### 📤 Export")

        export_scope = st.radio(
            "Export scope",
            ["All notes", "By category", "By tag"],
            horizontal=True,
        )

        export_notes_list = []
        if export_scope == "All notes":
            export_notes_list = _load_notes()
        elif export_scope == "By category":
            exp_cat = st.selectbox("Select category", CATEGORIES, key="exp_cat")
            export_notes_list = _load_notes(category=exp_cat)
        else:
            exp_tag = st.text_input("Tag to export", placeholder="e.g. work")
            if exp_tag.strip():
                export_notes_list = _load_notes(tag=exp_tag.strip())

        st.caption(f"{len(export_notes_list)} note(s) selected for export.")

        export_fmt = st.radio("Export format", ["Markdown (.md)", "Plain text (.txt)"], horizontal=True)

        if st.button("📤 Generate Export", type="primary", key="do_export") and export_notes_list:
            md_content = _export_notes_markdown(export_notes_list)
            ext = "md" if "Markdown" in export_fmt else "txt"
            fname = f"notes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            st.download_button(
                label=f"⬇️ Download {fname}",
                data=md_content.encode("utf-8"),
                file_name=fname,
                mime="text/plain",
                key="download_export",
            )
        elif not export_notes_list:
            st.info("No notes match the selected scope.")
