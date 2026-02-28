"""
Todo App — Page 22
Task manager backed by the pa_tasks table, with Google Calendar sync.
"""
import streamlit as st
from datetime import datetime, date
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

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
st.sidebar.page_link("pages/18_real_estate_bot.py",     label="🏠 Real Estate Bot",  icon="🏠")
st.sidebar.page_link("pages/1_expenses.py",             label="Expenses",            icon="📋")
st.sidebar.page_link("pages/2_income.py",               label="Income",              icon="💵")
st.sidebar.page_link("pages/4_trends.py",               label="Monthly Trends",      icon="📈")
st.sidebar.page_link("pages/8_goals.py",                label="Financial Goals",     icon="🎯")
st.sidebar.page_link("pages/15_bills.py",               label="Bill Calendar",       icon="📅")
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
    conn.commit()
    conn.close()


def _load_tasks(status_filter: list[str]) -> list[dict]:
    conn = get_conn()
    placeholders = ",".join(["?" for _ in status_filter])
    # NULLS LAST is PostgreSQL-only; use CASE for SQLite compatibility
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


def _add_task(title: str, due_date, priority: str, notes: str):
    conn = get_conn()
    due_str = due_date.isoformat() if due_date else None
    db_exec(conn, "INSERT INTO pa_tasks (title, due_date, priority, notes, status, source) VALUES (?,?,?,?,'open','manual')",
            (title.strip(), due_str, priority, notes.strip()))
    conn.commit()
    conn.close()


def _complete_task(task_id: int):
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_exec(conn, "UPDATE pa_tasks SET status='done', completed_at=? WHERE id=?", (now, task_id))
    conn.commit()
    conn.close()


def _reopen_task(task_id: int):
    conn = get_conn()
    db_exec(conn, "UPDATE pa_tasks SET status='open', completed_at=NULL WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def _delete_task(task_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM pa_tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def _update_task(task_id: int, title: str, due_date, priority: str, notes: str):
    conn = get_conn()
    due_str = due_date.isoformat() if due_date else None
    db_exec(conn, "UPDATE pa_tasks SET title=?, due_date=?, priority=?, notes=? WHERE id=?",
            (title.strip(), due_str, priority, notes.strip(), task_id))
    conn.commit()
    conn.close()


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
        due = date.fromisoformat(str(due_str)[:10])
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

# ── Add task form ─────────────────────────────────────────────────────────────
with st.expander("➕ Add New Task", expanded=st.session_state.get("todo_add_open", False)):
    with st.form("add_task_form", clear_on_submit=True):
        t1, t2, t3 = st.columns([3, 1, 1])
        new_title    = t1.text_input("Task *", placeholder="What needs to be done?")
        new_due      = t2.date_input("Due date (optional)", value=None)
        new_priority = t3.selectbox("Priority", ["normal", "high", "low"])
        new_notes    = st.text_area("Notes (optional)", height=60)
        submitted = st.form_submit_button("➕ Add Task", use_container_width=True, type="primary")

    if submitted:
        if new_title.strip():
            _add_task(new_title, new_due, new_priority, new_notes)
            st.success(f"✅ Added: **{new_title.strip()}**")
            st.session_state["todo_add_open"] = False
            st.rerun()
        else:
            st.error("Task title is required.")

st.divider()

# ── Filter / view controls ────────────────────────────────────────────────────
fc1, fc2 = st.columns([2, 1])
with fc1:
    view = st.radio("View", ["Open", "Done", "All"], horizontal=True)
with fc2:
    priority_filter = st.multiselect("Priority", ["high", "normal", "low"],
                                     default=["high", "normal", "low"])

status_map = {"Open": ["open"], "Done": ["done"], "All": ["open", "done"]}
tasks = _load_tasks(status_map[view])

# Apply priority filter
tasks = [t for t in tasks if t.get("priority", "normal") in priority_filter]

# ── Stats ─────────────────────────────────────────────────────────────────────
all_open = _load_tasks(["open"])
all_done = _load_tasks(["done"])
overdue  = [t for t in all_open if t.get("due_date") and date.fromisoformat(str(t["due_date"])[:10]) < date.today()]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Open Tasks",    len(all_open))
m2.metric("Completed",     len(all_done))
m3.metric("Overdue",       len(overdue),  delta=f"-{len(overdue)}" if overdue else None, delta_color="inverse")
m4.metric("Due Today",     len([t for t in all_open if t.get("due_date") and date.fromisoformat(str(t["due_date"])[:10]) == date.today()]))

st.divider()

# ── Task list ─────────────────────────────────────────────────────────────────
if not tasks:
    st.info("No tasks found. Add one above! 🎉" if view == "Open" else "No tasks in this view.")
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
            st.markdown(
                f"{title_display} &nbsp; {badge_html}",
                unsafe_allow_html=True,
            )
            if notes:
                st.caption(notes)
            src = task.get("source", "manual")
            if src != "manual":
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
            edit_due      = e2.date_input("Due date", value=date.fromisoformat(str(due_str)[:10]) if due_str else None)
            edit_priority = e3.selectbox("Priority", ["normal", "high", "low"],
                                         index=["normal", "high", "low"].index(priority))
            edit_notes = st.text_area("Notes", value=notes, height=60)
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

# ══════════════════════════════════════════════════════════════════════════════
# ── Google Calendar Integration ───────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("## 📅 Google Calendar")

# ── Load calendar client ──────────────────────────────────────────────────────
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
    # ── Try to connect ────────────────────────────────────────────────────────
    _token_json = get_setting("google_token", "")
    _cal_service = None
    _cal_status  = "disconnected"   # disconnected | scope_upgrade | connected

    try:
        _cal_service, _refreshed_token = get_calendar_service(_token_json or None)
        if _refreshed_token != _token_json:
            set_setting("google_token", _refreshed_token)
        _cal_status = "connected"
    except RuntimeError as _re:
        _msg = str(_re)
        if _msg == "SCOPE_UPGRADE":
            _cal_status = "scope_upgrade"
        else:
            _cal_status = "disconnected"
    except FileNotFoundError:
        _cal_status = "no_credentials"
    except Exception:
        _cal_status = "disconnected"

    # ── Status banner ─────────────────────────────────────────────────────────
    if _cal_status == "connected":
        st.success("✅ **Connected to Google Calendar** — your tasks can be synced as events.")

    elif _cal_status == "scope_upgrade":
        st.warning(
            "⚠️ **Google Calendar permission needed.**  \n"
            "Your existing Google account is connected (Gmail), but Calendar access hasn't been granted yet.  \n"
            "Click **Connect Google Calendar** below to re-authorize with Calendar permission added."
        )

    elif _cal_status == "no_credentials":
        st.error(
            "❌ **credentials.json not found.**  \n"
            "1. Go to [console.cloud.google.com](https://console.cloud.google.com)  \n"
            "2. Enable the **Google Calendar API** on your project  \n"
            "3. Download your OAuth credentials JSON and save it as `credentials.json` in the project root"
        )

    else:
        st.info(
            "📅 **Google Calendar not connected.**  \n"
            "Connect your Google account to sync todo tasks as calendar events."
        )

    # ── Auth / Re-auth flow ───────────────────────────────────────────────────
    if _cal_status in ("disconnected", "scope_upgrade", "no_credentials") and _cal_status != "no_credentials":
        with st.expander(
            "🔗 Connect Google Calendar" if _cal_status == "disconnected" else "🔄 Re-authorize Google Calendar (add Calendar permission)",
            expanded=(_cal_status == "scope_upgrade"),
        ):
            if _cal_status == "scope_upgrade":
                st.markdown(
                    "**Why re-authorize?**  \n"
                    "Your token was created for Gmail only. We need to add `Google Calendar` to the same authorization "
                    "so tasks can be synced as events. Your Gmail access will continue working normally."
                )

            if st.button("🚀 Generate Authorization Link", key="cal_gen_auth", type="primary"):
                try:
                    _auth_url, _flow = get_calendar_auth_url()
                    st.session_state["cal_auth_flow"] = _flow
                    st.session_state["cal_auth_url"]  = _auth_url
                except FileNotFoundError as _fe:
                    st.error(str(_fe))
                except Exception as _ex:
                    st.error(f"Error generating auth URL: {_ex}")

            if st.session_state.get("cal_auth_url"):
                st.markdown("**Step 1 — Open this link in your browser:**")
                st.code(st.session_state["cal_auth_url"], language=None)
                st.markdown(
                    "**Step 2 — Sign in with Google, approve both Gmail and Calendar permissions, "
                    "then copy the authorization code shown.**"
                )
                _code_input = st.text_input(
                    "Step 3 — Paste the authorization code here:",
                    key="cal_auth_code_input",
                    placeholder="4/0AX4XfWi...",
                )
                if st.button("✅ Connect", key="cal_submit_code", type="primary"):
                    if _code_input.strip():
                        try:
                            _new_token = exchange_code_for_token(
                                st.session_state["cal_auth_flow"],
                                _code_input.strip(),
                            )
                            set_setting("google_token", _new_token)
                            # Clear session state
                            for _k in ("cal_auth_flow", "cal_auth_url", "cal_auth_code_input"):
                                st.session_state.pop(_k, None)
                            st.success("🎉 Google Calendar connected! Refreshing...")
                            st.rerun()
                        except Exception as _ex:
                            st.error(f"Authorization failed: {_ex}")
                    else:
                        st.warning("Please paste the authorization code first.")

    # ── Calendar panel (only when connected) ─────────────────────────────────
    if _cal_status == "connected" and _cal_service:

        cal_tab1, cal_tab2 = st.tabs(["📤 Sync Tasks → Calendar", "📆 Upcoming Events"])

        # ── Tab 1: Sync tasks ─────────────────────────────────────────────────
        with cal_tab1:
            st.markdown("Push your open tasks (with due dates) to Google Calendar as all-day events.")

            _open_with_due = [t for t in _load_tasks(["open"]) if t.get("due_date")]

            if not _open_with_due:
                st.info("No open tasks with due dates to sync. Add a due date to a task first!")
            else:
                st.caption(f"{len(_open_with_due)} open task(s) with due dates")

                # Sync all button
                if st.button("📤 Sync All Tasks to Calendar", type="primary", key="cal_sync_all"):
                    _synced = 0
                    _failed = 0
                    with st.spinner("Syncing tasks to Google Calendar..."):
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
                        st.success(f"✅ Synced {_synced} task(s) to Google Calendar!")
                    if _failed:
                        st.warning(f"⚠️ {_failed} task(s) could not be synced.")

                st.divider()

                # Per-task sync
                for _t in _open_with_due:
                    _tc1, _tc2, _tc3 = st.columns([5, 2, 2])
                    _tc1.markdown(f"**{_t['title']}**")
                    _tc2.caption(f"📅 {str(_t['due_date'])[:10]}")
                    if _tc3.button("📤 Add to Cal", key=f"cal_push_{_t['id']}", help="Add this task to Google Calendar"):
                        try:
                            _eid = create_event_from_task(_cal_service, _t)
                            if _eid:
                                st.toast(f"📅 Added to calendar: {_t['title']}")
                            else:
                                st.toast("⚠️ Could not create event (no due date?)")
                        except Exception as _ex:
                            st.error(f"Error: {_ex}")

        # ── Tab 2: Upcoming events ────────────────────────────────────────────
        with cal_tab2:
            _days_ahead = st.slider("Show events for next N days", 7, 90, 30, key="cal_days_slider")

            if st.button("🔄 Refresh Events", key="cal_refresh"):
                st.session_state.pop("cal_events_cache", None)

            if "cal_events_cache" not in st.session_state:
                with st.spinner("Loading calendar events..."):
                    st.session_state["cal_events_cache"] = list_upcoming_events(
                        _cal_service, max_results=50, days_ahead=_days_ahead
                    )

            _events = st.session_state.get("cal_events_cache", [])

            if not _events:
                st.info(f"No upcoming events in the next {_days_ahead} days.")
            else:
                st.caption(f"{len(_events)} upcoming event(s)")
                for _ev in _events:
                    _is_task_event = _ev.get("source_app") == "peach_savings_todo"
                    _badge = " 🍑" if _is_task_event else ""
                    with st.container():
                        _ec1, _ec2 = st.columns([6, 2])
                        _ec1.markdown(f"**{_ev['summary']}{_badge}**")
                        _ec2.caption(f"📅 {_ev['start']}")
                        if _ev.get("description"):
                            st.caption(_ev["description"][:120])
                        if _ev.get("html_link"):
                            st.markdown(f"[Open in Google Calendar ↗]({_ev['html_link']})", unsafe_allow_html=False)
                    st.divider()

        # ── Disconnect button ─────────────────────────────────────────────────
        with st.expander("⚙️ Calendar Settings"):
            st.markdown("**Disconnect Google Calendar**")
            st.caption("This removes the stored token. You can reconnect at any time.")
            if st.button("🔌 Disconnect Google Account", key="cal_disconnect"):
                set_setting("google_token", "")
                import os as _os
                _tok = "token.json"
                if _os.path.exists(_tok):
                    _os.remove(_tok)
                for _k in ("cal_events_cache", "cal_auth_flow", "cal_auth_url"):
                    st.session_state.pop(_k, None)
                st.success("Disconnected. Refreshing...")
                st.rerun()
