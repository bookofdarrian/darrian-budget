"""
Todo App — Page 22
Task manager backed by the pa_tasks table, with Google Calendar sync,
always-visible Brain Dump capture, and per-view calendar tab.
"""
import streamlit as st
from datetime import datetime, date
import json
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.voice_input import render_voice_input

st.set_page_config(
    page_title="✅ Todo — Peach State Savings",
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

# ── DB helpers ────────────────────────────────────────────────────────────────

def _ensure_tasks_table():
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS pa_tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                due_date TEXT DEFAULT NULL,
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'open',
                source TEXT DEFAULT 'manual',
                source_email_id TEXT DEFAULT NULL,
                source_email_subject TEXT DEFAULT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                completed_at TEXT DEFAULT NULL
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS todo_brain_dumps (
                id SERIAL PRIMARY KEY,
                raw_text TEXT NOT NULL,
                parsed BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS pa_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_date TEXT DEFAULT NULL,
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'open',
                source TEXT DEFAULT 'manual',
                source_email_id TEXT DEFAULT NULL,
                source_email_subject TEXT DEFAULT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT DEFAULT NULL
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS todo_brain_dumps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                parsed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()
    conn.close()


def _load_tasks(status_filter: list) -> list:
    conn = get_conn()
    ph = "?" if not USE_POSTGRES else "%s"
    placeholders = ",".join([ph for _ in status_filter])
    if USE_POSTGRES:
        order_clause = "ORDER BY due_date ASC NULLS LAST, priority DESC, created_at DESC"
    else:
        order_clause = "ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, priority DESC, created_at DESC"
    c = db_exec(conn, f"SELECT * FROM pa_tasks WHERE status IN ({placeholders}) {order_clause}", tuple(status_filter))
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        results = [dict(zip(cols, r)) for r in rows]
    else:
        results = [dict(r) for r in rows]
    conn.close()
    return results


def _add_task(title: str, due_date, priority: str, notes: str, source: str = "manual"):
    conn = get_conn()
    due_str = due_date.isoformat() if due_date else None
    ph = "?" if not USE_POSTGRES else "%s"
    db_exec(conn, f"INSERT INTO pa_tasks (title, due_date, priority, notes, status, source) VALUES ({ph},{ph},{ph},{ph},'open',{ph})",
            (title.strip(), due_str, priority, notes.strip(), source))
    conn.commit()
    conn.close()


def _complete_task(task_id: int):
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ph = "?" if not USE_POSTGRES else "%s"
    db_exec(conn, f"UPDATE pa_tasks SET status='done', completed_at={ph} WHERE id={ph}", (now, task_id))
    conn.commit()
    conn.close()


def _reopen_task(task_id: int):
    conn = get_conn()
    ph = "?" if not USE_POSTGRES else "%s"
    db_exec(conn, f"UPDATE pa_tasks SET status='open', completed_at=NULL WHERE id={ph}", (task_id,))
    conn.commit()
    conn.close()


def _delete_task(task_id: int):
    conn = get_conn()
    ph = "?" if not USE_POSTGRES else "%s"
    db_exec(conn, f"DELETE FROM pa_tasks WHERE id={ph}", (task_id,))
    conn.commit()
    conn.close()


def _update_task(task_id: int, title: str, due_date, priority: str, notes: str):
    conn = get_conn()
    due_str = due_date.isoformat() if due_date else None
    ph = "?" if not USE_POSTGRES else "%s"
    db_exec(conn, f"UPDATE pa_tasks SET title={ph}, due_date={ph}, priority={ph}, notes={ph} WHERE id={ph}",
            (title.strip(), due_str, priority, notes.strip(), task_id))
    conn.commit()
    conn.close()


def _save_dump(raw_text: str):
    conn = get_conn()
    ph = "?" if not USE_POSTGRES else "%s"
    db_exec(conn, f"INSERT INTO todo_brain_dumps (raw_text) VALUES ({ph})", (raw_text.strip(),))
    conn.commit()
    conn.close()


def _parse_dump_with_ai(raw_text: str) -> list:
    """Use Claude to extract structured tasks from raw brain dump text. Returns list of dicts."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return []
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are a task extraction assistant. Given the following raw brain dump text, "
            "extract every distinct task or to-do item. "
            "Return ONLY a valid JSON array of objects. Each object must have these keys:\n"
            '  "title": string (the task name, max 120 chars)\n'
            '  "priority": "high" | "normal" | "low"\n'
            '  "notes": string (any extra context, can be empty string)\n'
            "Do not include any explanation — just the JSON array.\n\n"
            f"Brain dump:\n{raw_text}"
        )
        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_json = resp.content[0].text.strip()
        # Strip markdown fences if present
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        return json.loads(raw_json)
    except Exception as e:
        st.error(f"AI parse error: {e}")
        return []


# ── Priority helpers ──────────────────────────────────────────────────────────
PRIORITY_COLORS = {"high": "#ff5252", "normal": "#ffd600", "low": "#90a4ae"}
PRIORITY_ICONS  = {"high": "🔴", "normal": "🟡", "low": "⚪"}


def _priority_badge(p: str) -> str:
    color = PRIORITY_COLORS.get(p, "#90a4ae")
    icon  = PRIORITY_ICONS.get(p, "⚪")
    label = p.title()
    return (f'<span style="background:{color};color:#000;padding:2px 8px;'
            f'border-radius:10px;font-size:11px;font-weight:bold">{icon} {label}</span>')


def _due_badge(due_str) -> str:
    if not due_str:
        return ""
    try:
        due   = date.fromisoformat(str(due_str)[:10])
        today = date.today()
        delta = (due - today).days
        if delta < 0:
            color, label = "#ff5252", f"⚠️ Overdue ({abs(delta)}d ago)"
        elif delta == 0:
            color, label = "#ff9800", "📅 Due today"
        elif delta <= 3:
            color, label = "#ffd600", f"📅 Due in {delta}d"
        else:
            color, label = "#4caf50", f"📅 {due.strftime('%b %d')}"
        return (f'<span style="background:{color};color:#000;padding:2px 8px;'
                f'border-radius:10px;font-size:11px;font-weight:bold;margin-left:6px">{label}</span>')
    except Exception:
        return ""


# ── Init ──────────────────────────────────────────────────────────────────────
_ensure_tasks_table()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("✅ Todo")
st.caption("Your personal task manager — synced to the database, always available.")

# ══════════════════════════════════════════════════════════════════════════════
# ── 🧠 BRAIN DUMP — always visible on EVERY view ─────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("🧠 Brain Dump — Paste anything, AI extracts your tasks", expanded=False):
    st.caption(
        "Dump raw text, meeting notes, voice transcription, or a messy list below. "
        "Hit **Parse with AI** to auto-extract tasks, or **Add as single task** to save it directly."
    )
    dump_text = st.text_area(
        "Paste your notes, thoughts, or task list here:",
        height=160,
        placeholder=(
            "e.g.\n"
            "- Call dentist tomorrow\n"
            "Pick up packages from the post office\n"
            "HIGH: Finish Q1 budget review by Friday\n"
            "Need to email John about the contract renewal — low priority\n"
            "Buy groceries: milk, eggs, spinach"
        ),
        key="brain_dump_input",
    )

    bd_col1, bd_col2, bd_col3 = st.columns([2, 2, 1])

    with bd_col1:
        if st.button("🤖 Parse with AI → Add Tasks", type="primary", use_container_width=True, key="dump_parse_btn"):
            if dump_text.strip():
                with st.spinner("Claude is reading your brain dump..."):
                    parsed_tasks = _parse_dump_with_ai(dump_text.strip())
                if parsed_tasks:
                    _save_dump(dump_text.strip())
                    added = 0
                    for pt in parsed_tasks:
                        title = pt.get("title", "").strip()
                        if title:
                            _add_task(title, None, pt.get("priority", "normal"), pt.get("notes", ""), source="brain_dump")
                            added += 1
                    st.success(f"✅ Added **{added}** task(s) from your brain dump!")
                    st.rerun()
                else:
                    api_key = get_setting("anthropic_api_key")
                    if not api_key:
                        st.warning("⚠️ No Anthropic API key set. Go to Settings to add it.")
                    else:
                        st.warning("No tasks could be extracted. Try rephrasing your notes.")
            else:
                st.warning("Please paste some text first.")

    with bd_col2:
        if st.button("➕ Add as Single Task", use_container_width=True, key="dump_single_btn"):
            if dump_text.strip():
                first_line = dump_text.strip().split("\n")[0][:120]
                _add_task(first_line, None, "normal", dump_text.strip(), source="brain_dump")
                st.success(f"✅ Added: **{first_line}**")
                st.rerun()
            else:
                st.warning("Please paste some text first.")

    with bd_col3:
        st.markdown("")  # spacer

    st.caption("💡 *Tip: Works great with voice transcriptions, copied emails, or meeting notes.*")

# ── Add task form ─────────────────────────────────────────────────────────────
with st.expander("➕ Add New Task", expanded=st.session_state.get("todo_add_open", False)):
    spoken_task = render_voice_input(
        label="🎤 Speak your task",
        key="todo_voice_input",
    )
    if spoken_task:
        st.session_state["todo_voice_prefill"] = spoken_task

    voice_prefill = st.session_state.pop("todo_voice_prefill", "")

    with st.form("add_task_form", clear_on_submit=True):
        t1, t2, t3 = st.columns([3, 1, 1])
        new_title    = t1.text_input("Task *", value=voice_prefill, placeholder="What needs to be done?")
        new_due      = t2.date_input("Due date (optional)", value=None)
        new_priority = t3.selectbox("Priority", ["normal", "high", "low"])
        new_notes    = st.text_area("Notes (optional)", height=60)
        submitted    = st.form_submit_button("➕ Add Task", use_container_width=True, type="primary")

    if submitted:
        if new_title.strip():
            _add_task(new_title, new_due, new_priority, new_notes)
            st.success(f"✅ Added: **{new_title.strip()}**")
            st.session_state["todo_add_open"] = False
            st.rerun()
        else:
            st.error("Task title is required.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ── MAIN TABS — Tasks | Calendar ─────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
tab_tasks, tab_calendar = st.tabs(["📋 My Tasks", "📅 Google Calendar"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — TASK LIST
# ──────────────────────────────────────────────────────────────────────────────
with tab_tasks:
    # ── Filter / view controls ────────────────────────────────────────────────
    fc1, fc2 = st.columns([2, 1])
    with fc1:
        view = st.radio("View", ["Open", "Done", "All"], horizontal=True)
    with fc2:
        priority_filter = st.multiselect("Priority", ["high", "normal", "low"],
                                         default=["high", "normal", "low"])

    status_map = {"Open": ["open"], "Done": ["done"], "All": ["open", "done"]}
    tasks = _load_tasks(status_map[view])
    tasks = [t for t in tasks if t.get("priority", "normal") in priority_filter]

    # ── Stats ─────────────────────────────────────────────────────────────────
    all_open = _load_tasks(["open"])
    all_done = _load_tasks(["done"])
    overdue  = [t for t in all_open if t.get("due_date") and date.fromisoformat(str(t["due_date"])[:10]) < date.today()]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Open Tasks",  len(all_open))
    m2.metric("Completed",   len(all_done))
    m3.metric("Overdue",     len(overdue),
              delta=f"-{len(overdue)}" if overdue else None, delta_color="inverse")
    m4.metric("Due Today",   len([t for t in all_open
                                  if t.get("due_date") and
                                  date.fromisoformat(str(t["due_date"])[:10]) == date.today()]))

    st.divider()

    # ── Task list ─────────────────────────────────────────────────────────────
    if not tasks:
        st.info("No tasks found. Add one above or use the Brain Dump! 🎉"
                if view == "Open" else "No tasks in this view.")
    else:
        st.caption(f"{len(tasks)} task(s)")

    for task in tasks:
        tid      = task["id"]
        title    = task.get("title", "")
        status   = task.get("status", "open")
        priority = task.get("priority", "normal")
        due_str  = task.get("due_date")
        notes    = task.get("notes", "") or ""
        done     = status == "done"

        title_display = f"~~{title}~~" if done else f"**{title}**"

        with st.container():
            col_check, col_body, col_actions = st.columns([0.5, 7, 2.5])

            with col_check:
                checked = st.checkbox("", value=done, key=f"chk_{tid}",
                                      label_visibility="collapsed")
                if checked and not done:
                    _complete_task(tid)
                    st.toast(f"✅ Completed: {title}")
                    st.rerun()
                elif not checked and done:
                    _reopen_task(tid)
                    st.toast(f"🔄 Reopened: {title}")
                    st.rerun()

            with col_body:
                badge_html = _priority_badge(priority) + _due_badge(due_str)
                st.markdown(f"{title_display} &nbsp; {badge_html}", unsafe_allow_html=True)
                if notes:
                    st.caption(notes[:200])
                src = task.get("source", "manual")
                if src == "brain_dump":
                    st.caption("🧠 From Brain Dump")
                elif src != "manual":
                    st.caption(f"📧 From: {task.get('source_email_subject','') or src}")

            with col_actions:
                a1, a2 = st.columns(2)
                with a1:
                    if st.button("✏️", key=f"edit_{tid}", help="Edit task"):
                        st.session_state[f"editing_{tid}"] = True
                with a2:
                    if st.button("🗑️", key=f"del_{tid}", help="Delete task"):
                        _delete_task(tid)
                        st.toast(f"🗑️ Deleted: {title}")
                        st.rerun()

        # Inline edit form
        if st.session_state.get(f"editing_{tid}"):
            with st.form(f"edit_form_{tid}"):
                e1, e2, e3 = st.columns([3, 1, 1])
                edit_title    = e1.text_input("Title", value=title)
                edit_due      = e2.date_input("Due date",
                                              value=date.fromisoformat(str(due_str)[:10]) if due_str else None)
                edit_priority = e3.selectbox("Priority", ["normal", "high", "low"],
                                             index=["normal", "high", "low"].index(priority))
                edit_notes    = st.text_area("Notes", value=notes, height=60)
                s1, s2 = st.columns(2)
                save_edit   = s1.form_submit_button("💾 Save", use_container_width=True, type="primary")
                cancel_edit = s2.form_submit_button("✖ Cancel", use_container_width=True)

            if save_edit:
                _update_task(tid, edit_title, edit_due, edit_priority, edit_notes)
                st.session_state[f"editing_{tid}"] = False
                st.toast("💾 Task updated")
                st.rerun()
            if cancel_edit:
                st.session_state[f"editing_{tid}"] = False
                st.rerun()

        st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — GOOGLE CALENDAR
# ──────────────────────────────────────────────────────────────────────────────
with tab_calendar:
    st.markdown("## 📅 Google Calendar")

    try:
        from utils.calendar_client import (
            get_calendar_service,
            get_calendar_auth_url,
            exchange_code_for_token,
            list_upcoming_events,
            create_event_from_task,
            delete_event,
            _has_calendar_scope,
        )
        _cal_available = True
    except ImportError as _e:
        _cal_available = False
        st.error(f"Calendar client import error: {_e}")

    if _cal_available:
        _token_json = get_setting("google_token", "")
        _creds_json = get_setting("google_credentials", "")

        # Auto-migrate credentials.json from disk → DB
        if not _creds_json:
            import os as _os
            _creds_file = _os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
            if _os.path.exists(_creds_file):
                try:
                    with open(_creds_file) as _f:
                        _disk_creds = _f.read()
                    set_setting("google_credentials", _disk_creds)
                    _creds_json = _disk_creds
                    st.toast("🔑 Saved credentials.json to database for production use.")
                except Exception:
                    pass

        _cal_service = None
        _cal_error   = ""
        _cal_status  = "disconnected"

        try:
            _cal_service, _refreshed_token = get_calendar_service(
                token_json=_token_json or None,
                credentials_json=_creds_json or None,
            )
            if _refreshed_token != _token_json:
                set_setting("google_token", _refreshed_token)
            _cal_status = "connected"
        except RuntimeError as _re:
            _msg = str(_re)
            if _msg == "SCOPE_UPGRADE":
                _cal_status = "scope_upgrade"
            else:
                _cal_status = "disconnected"
                _cal_error  = _msg
        except FileNotFoundError:
            _cal_status = "no_credentials"
        except Exception as _cal_ex:
            _cal_status = "disconnected"
            _cal_error  = str(_cal_ex)

        # ── Step 0: No credentials ────────────────────────────────────────────
        if _cal_status == "no_credentials":
            st.warning("⚠️ **Google Calendar not set up yet.**")
            st.markdown("""
**How to connect Google Calendar** (5 minutes, one-time setup):

**Step 1 — Create a Google Cloud project:**
- Go to [console.cloud.google.com](https://console.cloud.google.com) → New Project → `"AI Todo"` → Create

**Step 2 — Enable the Calendar API:**
- APIs & Services → Library → search **"Google Calendar API"** → Enable

**Step 3 — Create credentials:**
- APIs & Services → Credentials → + Create Credentials → OAuth client ID
- Application type: **Desktop app** → name it `"AI Todo"` → Download JSON

**Step 4 — Upload the credentials below:**
""")
            _creds_tab1, _creds_tab2 = st.tabs(["📁 Upload credentials.json", "📋 Paste JSON"])

            with _creds_tab1:
                _uploaded = st.file_uploader("Upload your credentials.json", type=["json"], key="cal_creds_upload")
                if _uploaded is not None:
                    try:
                        _creds_content = _uploaded.read().decode("utf-8")
                        _parsed = __import__("json").loads(_creds_content)
                        if "installed" not in _parsed and "web" not in _parsed:
                            st.error("❌ This doesn't look like a valid Google OAuth credentials file.")
                        else:
                            if st.button("💾 Save Credentials", key="cal_save_upload", type="primary"):
                                set_setting("google_credentials", _creds_content)
                                st.success("✅ Credentials saved! Refreshing...")
                                st.rerun()
                    except Exception as _ex:
                        st.error(f"Could not read file: {_ex}")

            with _creds_tab2:
                _pasted = st.text_area("Paste credentials.json content:", height=150, key="cal_creds_paste",
                                       placeholder='{"installed":{"client_id":"..."}}')
                if _pasted.strip():
                    try:
                        _parsed = __import__("json").loads(_pasted)
                        if "installed" not in _parsed and "web" not in _parsed:
                            st.error("❌ Invalid credentials file.")
                        else:
                            if st.button("💾 Save Credentials", key="cal_save_paste", type="primary"):
                                set_setting("google_credentials", _pasted.strip())
                                st.success("✅ Credentials saved! Refreshing...")
                                st.rerun()
                    except __import__("json").JSONDecodeError:
                        st.error("❌ Invalid JSON.")

        # ── Status banner ─────────────────────────────────────────────────────
        if _cal_status == "connected":
            st.success("✅ **Connected to Google Calendar** — sync tasks as events below.")
        elif _cal_status == "scope_upgrade":
            st.warning(
                "⚠️ **Calendar permission needed.**  \n"
                "Gmail is connected but Calendar access hasn't been granted yet.  \n"
                "Click **Re-authorize Google Calendar** below."
            )
        elif _cal_status == "disconnected":
            st.info("📅 **Google Calendar not connected.** Connect below to sync tasks as events.")
            if _cal_error:
                with st.expander("🔍 Error details"):
                    st.code(_cal_error, language=None)

        # ── Auth flow ─────────────────────────────────────────────────────────
        if _cal_status in ("disconnected", "scope_upgrade"):
            with st.expander(
                "🔗 Connect Google Calendar" if _cal_status == "disconnected"
                else "🔄 Re-authorize Google Calendar",
                expanded=(_cal_status == "scope_upgrade"),
            ):
                if st.button("🚀 Generate Authorization Link", key="cal_gen_auth", type="primary"):
                    try:
                        _auth_url, _flow = get_calendar_auth_url(credentials_json=_creds_json or None)
                        st.session_state["cal_auth_flow"] = _flow
                        st.session_state["cal_auth_url"]  = _auth_url
                    except FileNotFoundError as _fe:
                        st.error(str(_fe))
                    except Exception as _ex:
                        st.error(f"Error: {_ex}")

                if st.session_state.get("cal_auth_url"):
                    st.markdown("**Step 1 — Open this link:**")
                    st.code(st.session_state["cal_auth_url"], language=None)
                    _code_input = st.text_input("Step 2 — Paste authorization code:", key="cal_auth_code_input",
                                                placeholder="4/0AX4XfWi...")
                    if st.button("✅ Connect", key="cal_submit_code", type="primary"):
                        if _code_input.strip():
                            try:
                                _new_token = exchange_code_for_token(
                                    st.session_state["cal_auth_flow"], _code_input.strip())
                                set_setting("google_token", _new_token)
                                for _k in ("cal_auth_flow", "cal_auth_url", "cal_auth_code_input"):
                                    st.session_state.pop(_k, None)
                                st.success("🎉 Google Calendar connected! Refreshing...")
                                st.rerun()
                            except Exception as _ex:
                                st.error(f"Authorization failed: {_ex}")
                        else:
                            st.warning("Paste the code first.")

        # ── Calendar panel ────────────────────────────────────────────────────
        if _cal_status == "connected" and _cal_service:
            cal_tab1, cal_tab2 = st.tabs(["📤 Sync Tasks → Calendar", "📆 Upcoming Events"])

            with cal_tab1:
                st.markdown("Push open tasks (with due dates) to Google Calendar as all-day events.")
                _open_with_due = [t for t in _load_tasks(["open"]) if t.get("due_date")]

                if not _open_with_due:
                    st.info("No open tasks with due dates. Add a due date to a task first!")
                else:
                    st.caption(f"{len(_open_with_due)} open task(s) with due dates")
                    if st.button("📤 Sync All Tasks to Calendar", type="primary", key="cal_sync_all"):
                        _synced, _failed = 0, 0
                        with st.spinner("Syncing..."):
                            for _t in _open_with_due:
                                try:
                                    _eid = create_event_from_task(_cal_service, _t)
                                    if _eid:
                                        _synced += 1
                                    else:
                                        _failed += 1
                                except Exception:
                                    _failed += 1
                        if _synced:
                            st.success(f"✅ Synced {_synced} task(s)!")
                        if _failed:
                            st.warning(f"⚠️ {_failed} task(s) could not be synced.")
                    st.divider()
                    for _t in _open_with_due:
                        _tc1, _tc2, _tc3 = st.columns([5, 2, 2])
                        _tc1.markdown(f"**{_t['title']}**")
                        _tc2.caption(f"📅 {str(_t['due_date'])[:10]}")
                        if _tc3.button("📤 Add to Cal", key=f"cal_push_{_t['id']}"):
                            try:
                                _eid = create_event_from_task(_cal_service, _t)
                                st.toast(f"📅 Added: {_t['title']}" if _eid else "⚠️ Could not create event")
                            except Exception as _ex:
                                st.error(f"Error: {_ex}")

            with cal_tab2:
                _days_ahead = st.slider("Show events for next N days", 7, 90, 30, key="cal_days_slider")
                if st.button("🔄 Refresh Events", key="cal_refresh"):
                    st.session_state.pop("cal_events_cache", None)
                if "cal_events_cache" not in st.session_state:
                    with st.spinner("Loading events..."):
                        st.session_state["cal_events_cache"] = list_upcoming_events(
                            _cal_service, max_results=50, days_ahead=_days_ahead)
                _events = st.session_state.get("cal_events_cache", [])
                if not _events:
                    st.info(f"No upcoming events in the next {_days_ahead} days.")
                else:
                    st.caption(f"{len(_events)} upcoming event(s)")
                    for _ev in _events:
                        _badge = " 🍑" if _ev.get("source_app") == "peach_savings_todo" else ""
                        with st.container():
                            _ec1, _ec2 = st.columns([6, 2])
                            _ec1.markdown(f"**{_ev['summary']}{_badge}**")
                            _ec2.caption(f"📅 {_ev['start']}")
                            if _ev.get("description"):
                                st.caption(_ev["description"][:120])
                            if _ev.get("html_link"):
                                st.markdown(f"[Open in Google Calendar ↗]({_ev['html_link']})")
                        st.divider()

            with st.expander("⚙️ Calendar Settings"):
                st.markdown("**Disconnect Google Calendar**")
                if st.button("🔌 Disconnect Google Account", key="cal_disconnect"):
                    set_setting("google_token", "")
                    import os as _os2
                    if _os2.path.exists("token.json"):
                        _os2.remove("token.json")
                    for _k in ("cal_events_cache", "cal_auth_flow", "cal_auth_url"):
                        st.session_state.pop(_k, None)
                    st.success("Disconnected. Refreshing...")
                    st.rerun()

        if _cal_status != "no_credentials" and _creds_json:
            with st.expander("🔑 Manage Google Credentials"):
                st.caption("OAuth credentials stored in database.")
                if st.button("🗑️ Remove Saved Credentials", key="cal_remove_creds"):
                    set_setting("google_credentials", "")
                    set_setting("google_token", "")
                    st.success("Credentials removed. Refreshing...")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ── Agent Dev Queue ───────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
import subprocess as _sp
from pathlib import Path as _Path
import json as _json

st.divider()
st.subheader("🤖 Agent Dev Queue")
st.caption("Track agent progress, claim features for yourself, and monitor the SDLC pipeline — live.")

BACKLOG_FILE = _Path(__file__).parent.parent / "BACKLOG.md"
REPO_ROOT    = _Path(__file__).parent.parent


def _run_git(cmd: str) -> str:
    try:
        r = _sp.run(cmd, shell=True, capture_output=True, text=True, cwd=str(REPO_ROOT))
        return r.stdout.strip()
    except Exception:
        return ""


def _parse_backlog():
    if not BACKLOG_FILE.exists():
        return [], [], []
    text = BACKLOG_FILE.read_text()
    yours, agent_q, done = [], [], []
    priority = "MEDIUM"
    for line in text.split("\n"):
        upper = line.upper()
        if "HIGH PRIORITY" in upper:
            priority = "HIGH"
        elif "MEDIUM PRIORITY" in upper:
            priority = "MEDIUM"
        elif "LOW PRIORITY" in upper:
            priority = "LOW"
        elif "COMPLETED" in upper:
            priority = "DONE"

        if line.startswith("- [x]"):
            done.append(line[6:].strip())
        elif line.startswith("- [ ]"):
            task = line[6:].strip()
            if "[YOU]" in task:
                yours.append((task.replace("[YOU]", "").strip(), priority))
            else:
                agent_q.append((task, priority))
    return yours, agent_q, done


def _claim_feature(task_text: str):
    if not BACKLOG_FILE.exists():
        return
    content = BACKLOG_FILE.read_text()
    old_line = f"- [ ] {task_text}"
    new_line = f"- [ ] [YOU] {task_text}"
    if old_line in content:
        BACKLOG_FILE.write_text(content.replace(old_line, new_line, 1))


def _unclaim_feature(task_text: str):
    if not BACKLOG_FILE.exists():
        return
    content = BACKLOG_FILE.read_text()
    old_line = f"- [ ] [YOU] {task_text}"
    new_line = f"- [ ] {task_text}"
    if old_line in content:
        BACKLOG_FILE.write_text(content.replace(old_line, new_line, 1))


yours, agent_q, done = _parse_backlog()
total = len(yours) + len(agent_q) + len(done)
pct   = int(len(done) / total * 100) if total else 0

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("✅ Completed",   len(done),    help="Features shipped to production")
mc2.metric("🔒 Yours",       len(yours),   help="Features you claimed")
mc3.metric("🤖 Agent Queue", len(agent_q), help="Features agents will auto-build")
mc4.metric("📊 Progress",    f"{pct}%",    help="Overall completion")

if total > 0:
    st.progress(pct / 100)

aq1, aq2 = st.columns(2)

with aq1:
    st.markdown("**🔒 Your Claimed Features**")
    st.caption("Agents skip these. Unclaim to return them to the queue.")
    if yours:
        for task, priority in yours:
            col_a, col_b = st.columns([4, 1])
            badge = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}.get(priority, "⚪")
            col_a.markdown(f"{badge} {task[:60]}")
            if col_b.button("↩", key=f"unclaim_{hash(task)}", help="Unclaim", use_container_width=True):
                _unclaim_feature(task)
                st.rerun()
    else:
        st.info("Nothing claimed. Claim features from the Agent Queue →")

with aq2:
    st.markdown("**🤖 Agent Queue** — Agents pick from top at 11 PM nightly")
    st.caption("Click 🔒 to take ownership.")
    if agent_q:
        for i, (task, priority) in enumerate(agent_q[:8]):
            col_a, col_b = st.columns([4, 1])
            badge    = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}.get(priority, "⚪")
            next_tag = "  🎯 **NEXT TONIGHT**" if i == 0 else ""
            col_a.markdown(f"{badge} {task[:55]}{next_tag}")
            if col_b.button("🔒", key=f"claim_{hash(task)}", help="Claim", use_container_width=True):
                _claim_feature(task)
                st.rerun()
        if len(agent_q) > 8:
            st.caption(f"... and {len(agent_q) - 8} more in queue")
    else:
        st.success("🎉 All features completed or claimed!")

branches_raw    = _run_git("git branch -r --format='%(refname:short)'")
feature_branches = [
    b.replace("origin/", "").strip()
    for b in branches_raw.split("\n")
    if "feature/" in b
]

if feature_branches:
    st.markdown("**🌿 Active Feature Branches**")
    num_cols     = min(3, len(feature_branches))
    branch_cols  = st.columns(num_cols)
    for i, b in enumerate(feature_branches[:9]):
        is_yours = any(
            b.lower().replace("feature/", "").replace("-", "") in
            t.lower().replace(" ", "").replace("-", "")
            for t, _ in yours
        )
        tag = "🔵 YOU" if is_yours else "🟢 AGENT"
        branch_cols[i % num_cols].markdown(f"`{tag}` `{b}`")

with st.expander("📝 Recent Commits"):
    log = _run_git('git log --oneline -10 --format="%h|%s|%cr"')
    if log:
        for line in log.split("\n"):
            if "|" in line:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    sha, msg, when = parts
                    is_agent = "overnight ai" in msg.lower() or "auto-built" in msg.lower()
                    tag      = "🟢 AGENT" if is_agent else "🔵 DARRIAN"
                    st.markdown(f"`{sha}` **{tag}** — {msg[:65]}  _{when}_")
    else:
        st.caption("No git history found.")

with st.expander("📬 Open PRs Waiting Your Approval"):
    pr_raw = _run_git("gh pr list --state open --json number,title,headRefName --limit 10")
    if pr_raw and pr_raw != "[]":
        try:
            prs = _json.loads(pr_raw)
            if prs:
                for pr in prs:
                    is_agent = "overnight" in pr.get("title", "").lower()
                    tag      = "🟢 AGENT" if is_agent else "🔵 DARRIAN"
                    pr_num   = pr["number"]
                    st.markdown(
                        f"{tag} **PR #{pr_num}** — {pr['title'][:60]}  "
                        f"[→ Approve](https://github.com/bookofdarrian/darrian-budget/pull/{pr_num})"
                    )
            else:
                st.info("No open PRs — nothing waiting for approval.")
        except Exception:
            st.caption("Could not load PRs. Run `gh auth login` on CT100.")
    else:
        st.info("No open PRs — nothing waiting for approval.")

with st.expander("ℹ️ How the Agent System Works"):
    st.markdown("""
**Nightly agent run (11 PM, CT100):**
1. Orchestrator wakes up, reads `BACKLOG.md`
2. Skips anything tagged `[YOU]` or already checked off
3. Picks the `🎯 NEXT TONIGHT` item at the top of the queue
4. Agents build it: Planner → Backend → UI → Tests → QA → Git
5. Feature merges: `feature/` → `dev` → `qa` → `staging` (automated)
6. A PR to `main` is opened — **you approve it here or on GitHub (1 click)**

**Claiming a feature:**
- Click 🔒 on any queue item to take ownership; agents skip it automatically
- Click ↩ to unclaim and return it to the agent queue

**Terminal status board:**
```
cd ~/Downloads/darrian-budget && python3 status.py
```

**Cost:** ~$1/night in Claude API tokens · AURA compression reduces it 40%
    """)
