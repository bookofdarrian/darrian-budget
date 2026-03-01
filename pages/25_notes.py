"""
AI-Powered Notes — Page 25
A unified, intelligent notes system to replace Apple Notes, Google Docs,
Microsoft Word, and Notion. Full search, AI summarization, tags, and rich text.
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
    c = db_exec(conn,
        "INSERT INTO notes (title,content,category,tags,color,word_count) VALUES (?,?,?,?,?,?)",
        (title.strip(), content, category, tags.strip(), color, wc))
    if USE_POSTGRES:
        note_id = c.fetchone()[0]
    else:
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
tab_browse, tab_editor, tab_ai = st.tabs(["📚 All Notes", "✍️ Editor", "🤖 AI Tools"])

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
