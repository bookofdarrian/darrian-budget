"""
Life Experience & Travel Model — Page 67
Peach State Savings — peachstatesavings.com

Travel advisor on steroids:
  - Trip Planner (budget tracking, past trips)
  - Travel Journal (memories, notes, photo uploads)
  - Life Milestones Timeline (plotly chart)
  - AI Travel Advisor (Claude recommendations)
  - Flights & Hotels (manual cost log)
  - Google Calendar integration (graceful fallback)
  - iTunes Search API for destination music vibes
"""

import os
import json
import urllib.request
import urllib.parse
import datetime
from datetime import date

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="✈️ Life & Travel — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                         label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",               label="✅ Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",  label="🎬 Creator",         icon="🎬")
st.sidebar.page_link("pages/25_notes.py",              label="📝 Notes",           icon="📝")
st.sidebar.page_link("pages/26_media_library.py",      label="🎵 Media Library",   icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


# ── DB Table Bootstrap ────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
        td = "DEFAULT (to_char(now(), 'YYYY-MM-DD'))"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"
        td = "DEFAULT (date('now'))"

    # Trips
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS trips (
            id {ai},
            destination TEXT NOT NULL,
            country TEXT DEFAULT '',
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            trip_type TEXT DEFAULT 'leisure',
            total_budget REAL DEFAULT 0,
            total_spent REAL DEFAULT 0,
            status TEXT DEFAULT 'planned',
            companions TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            rating INTEGER DEFAULT 0,
            cover_photo BLOB,
            created_at TEXT {ts}
        )
    """)

    # Flights
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS flights (
            id {ai},
            trip_id INTEGER DEFAULT NULL,
            flight_date TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            airline TEXT DEFAULT '',
            flight_number TEXT DEFAULT '',
            departure_time TEXT DEFAULT '',
            arrival_time TEXT DEFAULT '',
            seat_class TEXT DEFAULT 'economy',
            cost REAL DEFAULT 0,
            miles_earned INTEGER DEFAULT 0,
            booking_ref TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Hotels
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS hotels (
            id {ai},
            trip_id INTEGER DEFAULT NULL,
            hotel_name TEXT NOT NULL,
            city TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            room_type TEXT DEFAULT '',
            nightly_rate REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            rating INTEGER DEFAULT 0,
            booking_platform TEXT DEFAULT '',
            confirmation_num TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Ubers / Rideshare
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS ubers (
            id {ai},
            trip_id INTEGER DEFAULT NULL,
            ride_date TEXT NOT NULL,
            pickup TEXT DEFAULT '',
            dropoff TEXT DEFAULT '',
            service TEXT DEFAULT 'Uber',
            cost REAL DEFAULT 0,
            city TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Memories / Travel Journal
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS memories (
            id {ai},
            trip_id INTEGER NOT NULL,
            memory_date TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            mood TEXT DEFAULT 'happy',
            tags TEXT DEFAULT '',
            photo BLOB,
            photo_filename TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Life Milestones
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS life_milestones (
            id {ai},
            milestone_date TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'life',
            description TEXT DEFAULT '',
            impact TEXT DEFAULT 'positive',
            emoji TEXT DEFAULT '🌟',
            created_at TEXT {ts}
        )
    """)

    conn.commit()
    conn.close()


_ensure_tables()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    key = st.session_state.get("api_key", "")
    if not key:
        key = get_setting("anthropic_api_key", "")
        if key:
            st.session_state["api_key"] = key
    return key


def _ask_claude(prompt: str, max_tokens: int = 1500) -> str:
    api_key = _get_api_key()
    if not api_key:
        return "⚠️ No Claude API key configured. Add it in AI Insights → Settings."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        return f"❌ AI error: {e}"


def _load_trips() -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM trips ORDER BY start_date DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _load_flights(trip_id=None) -> list[dict]:
    conn = get_conn()
    if trip_id:
        c = db_exec(conn, "SELECT * FROM flights WHERE trip_id=? ORDER BY flight_date DESC", (trip_id,))
    else:
        c = db_exec(conn, "SELECT * FROM flights ORDER BY flight_date DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _load_hotels(trip_id=None) -> list[dict]:
    conn = get_conn()
    if trip_id:
        c = db_exec(conn, "SELECT * FROM hotels WHERE trip_id=? ORDER BY check_in DESC", (trip_id,))
    else:
        c = db_exec(conn, "SELECT * FROM hotels ORDER BY check_in DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _load_memories(trip_id: int) -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM memories WHERE trip_id=? ORDER BY memory_date ASC", (trip_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _load_milestones() -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM life_milestones ORDER BY milestone_date ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _load_ubers(trip_id=None) -> list[dict]:
    conn = get_conn()
    if trip_id:
        c = db_exec(conn, "SELECT * FROM ubers WHERE trip_id=? ORDER BY ride_date DESC", (trip_id,))
    else:
        c = db_exec(conn, "SELECT * FROM ubers ORDER BY ride_date DESC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _stars(n: int) -> str:
    n = max(0, min(5, int(n or 0)))
    return "⭐" * n + "☆" * (5 - n)


def _trip_options(trips: list[dict]) -> dict:
    """Return {id: label} mapping for selectbox."""
    return {t["id"]: f"{t['destination']} ({t['start_date'][:10]})" for t in trips}


def _itunes_search(query: str, limit: int = 6) -> list[dict]:
    """Search iTunes Search API. Returns list of result dicts."""
    try:
        params = urllib.parse.urlencode({
            "term": query,
            "entity": "song",
            "limit": limit,
            "media": "music",
        })
        url = f"https://itunes.apple.com/search?{params}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
        return data.get("results", [])
    except Exception:
        return []


# ── Google Calendar helpers (graceful fallback) ───────────────────────────────

def _get_gcal_token() -> str:
    return get_setting("google_calendar_token", "")


def _get_gcal_credentials() -> str:
    return get_setting("google_credentials", "")


def _gcal_connected() -> bool:
    return bool(_get_gcal_token())


def _get_calendar_service():
    """Return (service, token_str) or raise. Uses calendar_client.py."""
    try:
        from utils.calendar_client import get_calendar_service
        svc, new_token = get_calendar_service(
            token_json=_get_gcal_token(),
            credentials_json=_get_gcal_credentials(),
        )
        if new_token != _get_gcal_token():
            set_setting("google_calendar_token", new_token)
        return svc
    except Exception as e:
        raise e


def _find_free_windows(days_ahead: int = 60) -> list[dict]:
    """
    Query Google Calendar and identify free weekends.
    Returns list of {start, end, label} dicts.
    Graceful fallback: returns [] if calendar not connected.
    """
    if not _gcal_connected():
        return []
    try:
        svc = _get_calendar_service()
        now = datetime.datetime.utcnow()
        end_range = now + datetime.timedelta(days=days_ahead)

        result = svc.events().list(
            calendarId="primary",
            timeMin=now.isoformat() + "Z",
            timeMax=end_range.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])

        # Build set of busy weekend days
        busy_dates = set()
        for ev in events:
            start_raw = ev.get("start", {}).get("date") or ev.get("start", {}).get("dateTime", "")
            end_raw   = ev.get("end", {}).get("date") or ev.get("end", {}).get("dateTime", "")
            if start_raw:
                try:
                    s = date.fromisoformat(start_raw[:10])
                    e = date.fromisoformat(end_raw[:10]) if end_raw else s
                    cur = s
                    while cur <= e:
                        busy_dates.add(cur)
                        cur += datetime.timedelta(days=1)
                except Exception:
                    pass

        # Find free weekends (Fri–Sun)
        free_windows = []
        check = now.date()
        count = 0
        while check < end_range.date() and count < 8:
            if check.weekday() == 4:  # Friday
                fri = check
                sat = fri + datetime.timedelta(days=1)
                sun = fri + datetime.timedelta(days=2)
                if fri not in busy_dates and sat not in busy_dates and sun not in busy_dates:
                    free_windows.append({
                        "start": fri.isoformat(),
                        "end":   sun.isoformat(),
                        "label": f"{fri.strftime('%b %d')} – {sun.strftime('%b %d, %Y')} (Fri–Sun)",
                    })
                    count += 1
            check += datetime.timedelta(days=1)
        return free_windows
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("✈️ Life Experience & Travel")
st.caption("Your personal travel advisor, memory keeper, and life milestone tracker.")

trips = _load_trips()
flights = _load_flights()
hotels = _load_hotels()
ubers = _load_ubers()
milestones = _load_milestones()

# KPI strip
total_trips = len(trips)
countries = len(set(t.get("country", t.get("destination", "")) for t in trips if t.get("country") or t.get("destination")))
total_flight_cost = sum(f.get("cost", 0) for f in flights)
total_hotel_cost = sum(h.get("total_cost", 0) for h in hotels)
total_travel_spend = sum(t.get("total_spent", 0) for t in trips)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("✈️ Trips", total_trips)
k2.metric("🌍 Destinations", countries)
k3.metric("🛫 Flights Logged", len(flights))
k4.metric("🏨 Hotel Stays", len(hotels))
k5.metric("💰 Total Travel Spend", f"${total_travel_spend:,.0f}")

st.divider()

# ── Main Tabs ─────────────────────────────────────────────────────────────────
tab_plan, tab_journal, tab_milestones, tab_ai, tab_flights = st.tabs([
    "🗺️ Trip Planner",
    "📖 Travel Journal",
    "🌟 Life Milestones",
    "🤖 AI Travel Advisor",
    "✈️ Flights & Hotels",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TRIP PLANNER
# ══════════════════════════════════════════════════════════════════════════════
with tab_plan:
    st.markdown("### 🗺️ Trip Planner")

    col_add, col_list = st.columns([1, 2])

    with col_add:
        with st.expander("➕ Add New Trip", expanded=not trips):
            with st.form("add_trip_form", clear_on_submit=True):
                dest   = st.text_input("Destination *", placeholder="Tokyo, Japan")
                country = st.text_input("Country", placeholder="Japan")
                c1, c2 = st.columns(2)
                start_d = c1.date_input("Start Date", value=date.today())
                end_d   = c2.date_input("End Date", value=date.today() + datetime.timedelta(days=7))
                trip_type = st.selectbox("Trip Type", [
                    "leisure", "business", "adventure", "cultural",
                    "beach", "road trip", "family", "solo", "other"
                ])
                c3, c4 = st.columns(2)
                budget = c3.number_input("Total Budget ($)", min_value=0.0, value=1000.0, format="%.2f")
                spent  = c4.number_input("Amount Spent ($)", min_value=0.0, value=0.0, format="%.2f")
                companions = st.text_input("Travel Companions", placeholder="Solo, with partner, friends...")
                status = st.selectbox("Status", ["planned", "booked", "in progress", "completed", "cancelled"])
                rating = st.slider("Rating (if completed)", 0, 5, 0)
                notes  = st.text_area("Notes", height=80, placeholder="Trip notes, highlights...")
                cover  = st.file_uploader("Cover Photo (optional)", type=["jpg", "jpeg", "png"])
                cover_bytes = cover.read() if cover else None

                if st.form_submit_button("✈️ Save Trip", type="primary", use_container_width=True):
                    if dest.strip():
                        conn = get_conn()
                        db_exec(conn,
                            "INSERT INTO trips (destination, country, start_date, end_date, trip_type, "
                            "total_budget, total_spent, status, companions, notes, rating, cover_photo) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (dest.strip(), country.strip(), start_d.isoformat(), end_d.isoformat(),
                             trip_type, budget, spent, status, companions.strip(),
                             notes.strip(), rating, cover_bytes)
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Trip to {dest.strip()} saved!")
                        st.rerun()
                    else:
                        st.error("Destination is required.")

    with col_list:
        if not trips:
            st.info("No trips yet. Add your first trip using the form on the left!")
        else:
            # Filter controls
            f1, f2, f3 = st.columns(3)
            ft_status = f1.selectbox("Filter Status", ["All", "planned", "booked", "in progress", "completed", "cancelled"], key="tp_status")
            ft_type   = f2.selectbox("Filter Type",   ["All", "leisure", "business", "adventure", "cultural", "beach", "road trip", "family", "solo", "other"], key="tp_type")
            ft_sort   = f3.selectbox("Sort By", ["Newest First", "Oldest First", "Budget High→Low", "Rating High→Low"], key="tp_sort")

            filtered = [t for t in trips if
                (ft_status == "All" or t.get("status") == ft_status) and
                (ft_type   == "All" or t.get("trip_type") == ft_type)
            ]
            if ft_sort == "Oldest First":
                filtered = sorted(filtered, key=lambda x: x.get("start_date", ""))
            elif ft_sort == "Budget High→Low":
                filtered = sorted(filtered, key=lambda x: x.get("total_budget", 0), reverse=True)
            elif ft_sort == "Rating High→Low":
                filtered = sorted(filtered, key=lambda x: x.get("rating", 0), reverse=True)

            st.caption(f"{len(filtered)} trip(s)")

            for t in filtered:
                nights = 0
                try:
                    s = date.fromisoformat(t["start_date"][:10])
                    e = date.fromisoformat(t["end_date"][:10])
                    nights = (e - s).days
                except Exception:
                    pass

                budget_pct = min(100, int((t.get("total_spent", 0) / t.get("total_budget", 1)) * 100)) if t.get("total_budget") else 0
                status_colors = {
                    "planned": "#4a9eff", "booked": "#ffab76", "in progress": "#ffd700",
                    "completed": "#4caf50", "cancelled": "#e57373"
                }
                sc = status_colors.get(t.get("status", "planned"), "#aaa")

                with st.expander(
                    f"**{t['destination']}**  ·  {t['start_date'][:10]}  ·  "
                    f"{t.get('trip_type', '').title()}  ·  {_stars(t.get('rating', 0))}",
                    expanded=False
                ):
                    st.markdown(
                        f"<span style='background:{sc};color:#000;padding:2px 8px;"
                        f"border-radius:10px;font-size:11px;font-weight:700'>"
                        f"{t.get('status','').upper()}</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown("")

                    ic1, ic2, ic3 = st.columns(3)
                    ic1.metric("Duration", f"{nights} nights")
                    ic2.metric("Budget", f"${t.get('total_budget', 0):,.0f}")
                    ic3.metric("Spent", f"${t.get('total_spent', 0):,.0f}")

                    if t.get("total_budget", 0) > 0:
                        over = t.get("total_spent", 0) > t.get("total_budget", 0)
                        st.progress(min(1.0, budget_pct / 100.0))
                        if over:
                            st.caption(f"⚠️ Over budget by ${t['total_spent'] - t['total_budget']:,.0f}")
                        else:
                            remaining = t.get("total_budget", 0) - t.get("total_spent", 0)
                            st.caption(f"${remaining:,.0f} remaining ({100 - budget_pct}%)")

                    if t.get("companions"):
                        st.caption(f"👥 {t['companions']}")
                    if t.get("notes"):
                        st.caption(t["notes"][:200])

                    # Edit form
                    with st.form(f"edit_trip_{t['id']}"):
                        ec1, ec2 = st.columns(2)
                        new_spent  = ec1.number_input("Update Spent ($)", value=float(t.get("total_spent", 0)), format="%.2f", key=f"esp_{t['id']}")
                        new_status = ec2.selectbox("Update Status",
                            ["planned", "booked", "in progress", "completed", "cancelled"],
                            index=["planned", "booked", "in progress", "completed", "cancelled"].index(t.get("status", "planned")),
                            key=f"ests_{t['id']}"
                        )
                        new_rating = st.slider("Rating", 0, 5, int(t.get("rating", 0)), key=f"ert_{t['id']}")
                        new_notes  = st.text_area("Notes", value=t.get("notes", ""), height=60, key=f"en_{t['id']}")
                        ec_save, ec_del = st.columns(2)
                        if ec_save.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                            conn = get_conn()
                            db_exec(conn,
                                "UPDATE trips SET total_spent=?, status=?, rating=?, notes=? WHERE id=?",
                                (new_spent, new_status, new_rating, new_notes, t["id"])
                            )
                            conn.commit()
                            conn.close()
                            st.success("Saved!")
                            st.rerun()
                        if ec_del.form_submit_button("🗑️ Delete Trip", use_container_width=True):
                            conn = get_conn()
                            db_exec(conn, "DELETE FROM trips WHERE id=?", (t["id"],))
                            conn.commit()
                            conn.close()
                            st.rerun()

    # ── Trip Map / Summary Chart ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Trip Analytics")
    if trips:
        ac1, ac2 = st.columns(2)
        with ac1:
            type_counts = {}
            for t in trips:
                typ = t.get("trip_type", "other")
                type_counts[typ] = type_counts.get(typ, 0) + 1
            fig_types = px.pie(
                values=list(type_counts.values()),
                names=list(type_counts.keys()),
                title="Trips by Type",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_types.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#fafafa")
            st.plotly_chart(fig_types, use_container_width=True)
        with ac2:
            completed = [t for t in trips if t.get("status") == "completed"]
            if completed:
                df_spend = pd.DataFrame([{
                    "Destination": t["destination"],
                    "Budget": t.get("total_budget", 0),
                    "Spent": t.get("total_spent", 0),
                } for t in completed])
                fig_spend = px.bar(df_spend, x="Destination", y=["Budget", "Spent"],
                                   barmode="group", title="Budget vs Spent (Completed Trips)",
                                   color_discrete_sequence=["#4a9eff", "#ffab76"])
                fig_spend.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#fafafa")
                st.plotly_chart(fig_spend, use_container_width=True)
            else:
                st.info("Complete some trips to see budget analytics.")
    else:
        st.info("Add trips to see analytics.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TRAVEL JOURNAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_journal:
    st.markdown("### 📖 Travel Journal")
    st.caption("Capture memories, notes, and photos for each trip.")

    if not trips:
        st.info("Add a trip first in the **Trip Planner** tab to start journaling.")
    else:
        trip_opts = _trip_options(trips)
        sel_trip_id = st.selectbox(
            "Select Trip",
            options=list(trip_opts.keys()),
            format_func=lambda x: trip_opts[x],
            key="journal_trip_sel"
        )

        sel_trip = next((t for t in trips if t["id"] == sel_trip_id), None)
        if sel_trip:
            st.markdown(
                f"**{sel_trip['destination']}** · "
                f"{sel_trip['start_date'][:10]} to {sel_trip['end_date'][:10]} · "
                f"{_stars(sel_trip.get('rating', 0))}"
            )

        # Add memory form
        with st.expander("➕ Add Memory / Journal Entry", expanded=False):
            with st.form("add_memory_form", clear_on_submit=True):
                mc1, mc2 = st.columns(2)
                mem_title = mc1.text_input("Title *", placeholder="First day in Tokyo...")
                mem_date  = mc2.date_input("Date", value=date.today())
                mem_mood  = st.selectbox("Mood", ["happy", "excited", "relaxed", "nostalgic", "adventurous", "tired", "overwhelmed", "peaceful", "grateful", "other"])
                mem_content = st.text_area("Journal Entry", height=150,
                    placeholder="Write about this moment — what you saw, felt, ate, experienced...")
                mem_tags  = st.text_input("Tags", placeholder="food, culture, temple, sunset (comma-separated)")
                mem_photo = st.file_uploader("Photo", type=["jpg", "jpeg", "png", "gif"])
                photo_bytes    = mem_photo.read() if mem_photo else None
                photo_filename = mem_photo.name if mem_photo else ""

                if st.form_submit_button("📝 Save Memory", type="primary", use_container_width=True):
                    if mem_title.strip():
                        conn = get_conn()
                        db_exec(conn,
                            "INSERT INTO memories (trip_id, memory_date, title, content, mood, tags, photo, photo_filename) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            (sel_trip_id, mem_date.isoformat(), mem_title.strip(),
                             mem_content.strip(), mem_mood, mem_tags.strip(),
                             photo_bytes, photo_filename)
                        )
                        conn.commit()
                        conn.close()
                        st.success("Memory saved! 📸")
                        st.rerun()
                    else:
                        st.error("Title is required.")

        # Display memories
        memories = _load_memories(sel_trip_id)
        if not memories:
            st.info("No journal entries yet for this trip. Add your first memory above!")
        else:
            st.markdown(f"#### 📸 {len(memories)} Memory(-ies)")
            mood_emojis = {
                "happy": "😊", "excited": "🤩", "relaxed": "😌", "nostalgic": "🥺",
                "adventurous": "🏔️", "tired": "😴", "overwhelmed": "😵",
                "peaceful": "🕊️", "grateful": "🙏", "other": "💭"
            }

            for mem in memories:
                mood_em = mood_emojis.get(mem.get("mood", "other"), "💭")
                with st.expander(
                    f"{mood_em} **{mem['title']}** · {mem['memory_date'][:10]}",
                    expanded=False
                ):
                    if mem.get("photo"):
                        try:
                            st.image(mem["photo"], caption=mem.get("photo_filename", ""), use_column_width=True)
                        except Exception:
                            pass

                    st.markdown(mem.get("content", ""))

                    if mem.get("tags"):
                        tag_list = [tg.strip() for tg in mem["tags"].split(",") if tg.strip()]
                        tag_html = " ".join(
                            f'<span style="background:#333;color:#aaa;padding:2px 8px;'
                            f'border-radius:12px;font-size:11px">{tg}</span>'
                            for tg in tag_list
                        )
                        st.markdown(tag_html, unsafe_allow_html=True)

                    dc1, dc2 = st.columns([4, 1])
                    with dc2:
                        if st.button("🗑️ Delete", key=f"del_mem_{mem['id']}"):
                            conn = get_conn()
                            db_exec(conn, "DELETE FROM memories WHERE id=?", (mem["id"],))
                            conn.commit()
                            conn.close()
                            st.rerun()

        # ── Music Vibe for Destination ─────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🎵 Destination Music Vibes")
        st.caption("Find the soundtrack for your trip using iTunes Search API.")

        dest_query = st.text_input(
            "Search music for destination",
            value=sel_trip["destination"] if sel_trip else "",
            placeholder="Tokyo lofi, Paris jazz, Jamaica reggae...",
            key="music_vibe_query"
        )
        if st.button("🎵 Find Destination Music", key="find_music_btn"):
            results = _itunes_search(dest_query, limit=8)
            if results:
                st.session_state["music_vibe_results"] = results
            else:
                st.warning("No results found. Try a different search term.")

        if st.session_state.get("music_vibe_results"):
            st.markdown(f"**{len(st.session_state['music_vibe_results'])} tracks found:**")
            for r in st.session_state["music_vibe_results"]:
                t_name  = r.get("trackName") or r.get("collectionName", "")
                a_name  = r.get("artistName", "")
                al_name = r.get("collectionName", "")
                genre   = r.get("primaryGenreName", "")
                dur_ms  = r.get("trackTimeMillis", 0)
                preview = r.get("previewUrl", "")
                it_url  = r.get("trackViewUrl", "")
                dur_s   = int(dur_ms or 0) // 1000
                mins, secs = divmod(dur_s, 60)

                vc1, vc2 = st.columns([4, 2])
                vc1.markdown(
                    f"**{t_name}** — {a_name}  \n"
                    f"<span style='color:#aaa;font-size:11px'>{al_name} · {genre} · {mins}:{secs:02d}</span>",
                    unsafe_allow_html=True
                )
                if preview:
                    vc2.audio(preview)
                if it_url:
                    vc2.markdown(f"[🍎 Apple Music]({it_url})")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LIFE MILESTONES
# ══════════════════════════════════════════════════════════════════════════════
with tab_milestones:
    st.markdown("### 🌟 Life Milestones Timeline")
    st.caption("Your personal life story — major events, achievements, and turning points.")

    # Add milestone form
    with st.expander("➕ Add Life Milestone", expanded=not milestones):
        with st.form("add_milestone_form", clear_on_submit=True):
            ml1, ml2 = st.columns(2)
            ml_title = ml1.text_input("Title *", placeholder="Graduated from college, First home, New job...")
            ml_date  = ml2.date_input("Date", value=date.today())
            ml3, ml4, ml5 = st.columns(3)
            ml_category = ml3.selectbox("Category", [
                "life", "career", "travel", "finance", "health", "relationship",
                "education", "family", "achievement", "other"
            ])
            ml_impact = ml4.selectbox("Impact", ["positive", "negative", "neutral", "transformative"])
            ml_emoji  = ml5.text_input("Emoji", value="🌟", max_chars=4)
            ml_desc   = st.text_area("Description", height=100,
                placeholder="Tell the story of this milestone...")

            if st.form_submit_button("🌟 Save Milestone", type="primary", use_container_width=True):
                if ml_title.strip():
                    conn = get_conn()
                    db_exec(conn,
                        "INSERT INTO life_milestones (milestone_date, title, category, description, impact, emoji) "
                        "VALUES (?,?,?,?,?,?)",
                        (ml_date.isoformat(), ml_title.strip(), ml_category,
                         ml_desc.strip(), ml_impact, ml_emoji.strip() or "🌟")
                    )
                    conn.commit()
                    conn.close()
                    st.success("Milestone saved!")
                    st.rerun()
                else:
                    st.error("Title is required.")

    # Timeline chart
    milestones = _load_milestones()
    if milestones:
        st.markdown("#### 📅 Timeline")

        # Build plotly timeline
        impact_colors = {
            "positive": "#4caf50",
            "negative": "#e57373",
            "neutral": "#90a4ae",
            "transformative": "#ffab76",
        }
        category_y = {cat: i for i, cat in enumerate(
            ["life", "career", "travel", "finance", "health",
             "relationship", "education", "family", "achievement", "other"]
        )}

        fig = go.Figure()

        for m in milestones:
            try:
                ms_date = m["milestone_date"][:10]
                y_val = category_y.get(m.get("category", "other"), 0)
                color = impact_colors.get(m.get("impact", "positive"), "#4caf50")
                fig.add_trace(go.Scatter(
                    x=[ms_date],
                    y=[y_val],
                    mode="markers+text",
                    marker=dict(size=18, color=color, line=dict(width=2, color="#fff")),
                    text=[m.get("emoji", "🌟")],
                    textposition="top center",
                    textfont=dict(size=16),
                    hovertemplate=(
                        f"<b>{m['title']}</b><br>"
                        f"Date: {ms_date}<br>"
                        f"Category: {m.get('category', '')}<br>"
                        f"Impact: {m.get('impact', '')}<br>"
                        f"{m.get('description', '')[:100]}"
                        "<extra></extra>"
                    ),
                    name=m["title"],
                    showlegend=False,
                ))
            except Exception:
                pass
        
        # Add connecting line
        if len(milestones) > 1:
            sorted_ms = sorted(milestones, key=lambda x: x["milestone_date"])
            fig.add_trace(go.Scatter(
                x=[m["milestone_date"][:10] for m in sorted_ms],
                y=[category_y.get(m.get("category", "other"), 0) for m in sorted_ms],
                mode="lines",
                line=dict(color="#333", width=1, dash="dot"),
                showlegend=False,
                hoverinfo="skip",
            ))

        cat_labels = ["Life", "Career", "Travel", "Finance", "Health",
                      "Relationship", "Education", "Family", "Achievement", "Other"]
        fig.update_layout(
            title="Life Milestones Timeline",
            xaxis_title="Date",
            yaxis=dict(
                tickvals=list(range(len(cat_labels))),
                ticktext=cat_labels,
                title="Category",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(14,17,23,1)",
            font_color="#fafafa",
            height=450,
            showlegend=False,
            xaxis=dict(gridcolor="#1e2330"),
            yaxis_gridcolor="#1e2330",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Category breakdown
        st.markdown("#### 📊 Milestones by Category")
        cat_counts = {}
        for m in milestones:
            cat = m.get("category", "other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        fig_cats = px.bar(
            x=list(cat_counts.keys()),
            y=list(cat_counts.values()),
            labels={"x": "Category", "y": "Count"},
            color=list(cat_counts.keys()),
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_cats.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(14,17,23,1)",
                               font_color="#fafafa", showlegend=False, height=300)
        st.plotly_chart(fig_cats, use_container_width=True)

        # Milestone list
        st.markdown("---")
        st.markdown("#### 📋 All Milestones")
        filter_cat = st.selectbox("Filter Category", ["All", "life", "career", "travel", "finance", "health",
                                                        "relationship", "education", "family", "achievement", "other"],
                                  key="ms_cat_filter")
        display_ms = [m for m in reversed(milestones) if filter_cat == "All" or m.get("category") == filter_cat]

        for m in display_ms:
            impact_icon = {"positive": "✅", "negative": "⚠️", "neutral": "➡️", "transformative": "🔥"}.get(m.get("impact", "positive"), "✅")
            with st.expander(f"{m.get('emoji', '🌟')} **{m['title']}** · {m['milestone_date'][:10]} · {impact_icon}"):
                st.markdown(m.get("description", ""))
                st.caption(f"Category: {m.get('category', '')} · Impact: {m.get('impact', '')}")
                if st.button("🗑️ Delete", key=f"del_ms_{m['id']}"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM life_milestones WHERE id=?", (m["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()
    else:
        st.info("No milestones yet. Add your first life milestone using the form above!")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI TRAVEL ADVISOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("### 🤖 AI Travel Advisor")
    st.caption("Claude-powered destination recommendations, weekend trips, and travel insights.")

    # API key check
    api_key = _get_api_key()
    if not api_key:
        with st.expander("⚙️ Add Claude API Key", expanded=True):
            new_key = st.text_input("Claude API Key", type="password", placeholder="sk-ant-api03-...", key="travel_api_key_input")
            if new_key and new_key.startswith("sk-ant-"):
                st.session_state["api_key"] = new_key
                set_setting("anthropic_api_key", new_key)
                st.success("API key saved!")
                st.rerun()
            st.info("Get your API key at console.anthropic.com")

    # Build travel history summary for context
    completed_trips = [t for t in trips if t.get("status") == "completed"]
    travel_history = ""
    if completed_trips:
        history_lines = [
            f"- {t['destination']} ({t['start_date'][:10]}): {t.get('trip_type', 'leisure')}, "
            f"${t.get('total_spent', 0):,.0f} spent, rated {t.get('rating', 0)}/5"
            for t in completed_trips[:10]
        ]
        travel_history = "Past trips:\n" + "\n".join(history_lines)
    else:
        travel_history = "No past trips logged yet."

    ai_mode = st.selectbox("What do you need?", [
        "🌍 Weekend Trip Recommendations",
        "✈️ Full Trip Planning",
        "🏖️ Destination Deep Dive",
        "💰 Budget Optimization",
        "📊 Analyze My Travel Patterns",
        "🗺️ Itinerary Builder",
        "💬 Custom Travel Question",
    ], key="ai_travel_mode")

    st.divider()

    # ── Google Calendar Free Windows ──────────────────────────────────────────
    st.markdown("#### 📅 Available Travel Windows")
    if _gcal_connected():
        free_windows = _find_free_windows(days_ahead=60)
        if free_windows:
            st.success(f"🟢 Found {len(free_windows)} free weekend(s) in the next 60 days via Google Calendar:")
            for w in free_windows:
                st.markdown(f"  • 🗓️ {w['label']}")
        else:
            st.info("No completely free weekends found in the next 60 days (or calendar is busy).")
    else:
        st.info("💡 Connect Google Calendar (in the Todo page) to see your available travel windows automatically.")
        free_windows = []

    st.divider()

    if ai_mode == "🌍 Weekend Trip Recommendations":
        st.markdown("#### 🌍 Weekend Trip Recommendations")
        c1, c2, c3 = st.columns(3)
        home_city    = c1.text_input("Home City", value="Atlanta, GA", key="ai_home_city")
        weekend_budget = c2.number_input("Weekend Budget ($)", min_value=100, value=500, step=50, key="ai_wk_budget")
        travel_style = c3.multiselect("Travel Style", ["beach", "city", "nature", "culture", "food", "adventure", "budget", "luxury"], default=["culture", "food"], key="ai_style")

        preferred_month = st.selectbox("Preferred Month", ["Any"] + [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ], key="ai_month")

        if st.button("🤖 Get Weekend Trip Ideas", type="primary", key="ai_weekend_btn"):
            free_window_text = ""
            if free_windows:
                free_window_text = f"\nAvailable free weekends from Google Calendar:\n" + \
                    "\n".join(f"  - {w['label']}" for w in free_windows[:4])

            prompt = f"""You are an expert travel advisor. The user lives in {home_city} and wants weekend trip recommendations.

{travel_history}

Budget: ${weekend_budget} for the weekend (flights + hotel + activities)
Travel style preferences: {', '.join(travel_style)}
Preferred time: {preferred_month}
{free_window_text}

Give 5 specific weekend trip recommendations. For each include:
1. **Destination** (city, state/country)
2. **Why it fits** (based on their past trips and style preferences)
3. **Getting there** (flight time + rough cost, or drivable distance)
4. **Where to stay** (hotel recommendation + price range)
5. **Top 3 activities**
6. **Best food spots**
7. **Estimated total cost breakdown**
8. **Best time to book**

Make recommendations specific, actionable, and budget-conscious. Reference their past travel history when relevant."""

            with st.spinner("Finding your perfect weekend getaways..."):
                result = _ask_claude(prompt, max_tokens=2000)
            st.session_state["ai_travel_result"] = result

    elif ai_mode == "✈️ Full Trip Planning":
        st.markdown("#### ✈️ Full Trip Planner")
        c1, c2 = st.columns(2)
        dest_in   = c1.text_input("Destination", placeholder="Japan, Costa Rica, Italy...", key="ai_dest_full")
        duration  = c2.number_input("Trip Duration (days)", min_value=2, max_value=30, value=7, key="ai_dur")
        c3, c4 = st.columns(2)
        dep_city  = c3.text_input("Departing From", value="Atlanta, GA", key="ai_dep_city")
        full_budget = c4.number_input("Total Budget ($)", min_value=500, value=3000, step=100, key="ai_full_budget")
        group_size = st.number_input("Group Size", min_value=1, max_value=10, value=1, key="ai_group")
        interests  = st.text_area("Interests / Must-Haves", height=80,
            placeholder="Sushi, temples, street markets, ryokan, bullet train...", key="ai_interests")

        if st.button("🤖 Plan My Trip", type="primary", key="ai_full_btn"):
            if dest_in.strip():
                prompt = f"""You are a master travel planner. Plan a detailed {duration}-day trip to {dest_in} for {group_size} person(s).

Traveler profile:
{travel_history}

Trip details:
- Departing from: {dep_city}
- Duration: {duration} days
- Total budget: ${full_budget} (for {group_size} person(s))
- Interests: {interests}

Create a comprehensive trip plan including:
1. **Overview & Best Time to Visit**
2. **Flight Strategy** (best airlines, booking tips, estimated cost)
3. **Accommodation** (3 hotel options at different price points with neighborhoods)
4. **Day-by-Day Itinerary** (all {duration} days)
5. **Top Restaurants** (breakfast, lunch, dinner spots)
6. **Hidden Gems** (off-the-beaten-path spots a local would recommend)
7. **Detailed Budget Breakdown** (flights, hotel, food, activities, transport)
8. **Practical Tips** (visa, currency, transport, cultural notes)
9. **Packing List Highlights**

Be specific with names, prices, and neighborhoods. Reference their travel history for personalization."""

                with st.spinner(f"Planning your {duration}-day trip to {dest_in}..."):
                    result = _ask_claude(prompt, max_tokens=3000)
                st.session_state["ai_travel_result"] = result
            else:
                st.error("Please enter a destination.")

    elif ai_mode == "🏖️ Destination Deep Dive":
        dest_dive = st.text_input("Destination to deep dive", placeholder="Bali, Thailand, Barcelona...", key="ai_dive_dest")
        focus_area = st.multiselect("Focus On", ["food scene", "nightlife", "culture", "nature", "shopping", "beaches", "day trips", "hidden gems"], default=["culture", "food scene"], key="ai_dive_focus")

        if st.button("🤖 Deep Dive", type="primary", key="ai_dive_btn"):
            if dest_dive.strip():
                prompt = f"""Give me a deep-dive insider guide to {dest_dive} focusing on: {', '.join(focus_area)}.

My travel background: {travel_history}

I want hyper-specific recommendations that go beyond tourist traps:
1. **The neighborhoods nobody talks about** (and why you should go)
2. **Food: where locals actually eat** (specific restaurant names + dishes)
3. **Hidden experiences** that most tourists miss
4. **{focus_area[0] if focus_area else 'Culture'} deep dive** — what makes {dest_dive} unique
5. **The real cost** — honest budget breakdown, what's worth splurging on vs saving
6. **When NOT to go** and what to avoid
7. **One perfect day itinerary** as a local would spend it
8. **Phrases / cultural tips** that will change your experience

Be opinionated. Tell me what's actually worth it."""

                with st.spinner(f"Deep diving into {dest_dive}..."):
                    result = _ask_claude(prompt, max_tokens=2000)
                st.session_state["ai_travel_result"] = result

    elif ai_mode == "💰 Budget Optimization":
        bo_dest = st.text_input("Destination", placeholder="Europe, Southeast Asia...", key="ai_bo_dest")
        bo_budget = st.number_input("Total Budget ($)", min_value=200, value=2000, step=100, key="ai_bo_budget")
        bo_dur = st.number_input("Days", min_value=1, max_value=30, value=10, key="ai_bo_dur")
        bo_non_neg = st.text_input("Non-negotiables", placeholder="Private room, no hostels, good wifi...", key="ai_bo_nn")

        if st.button("🤖 Optimize My Budget", type="primary", key="ai_bo_btn"):
            if bo_dest.strip():
                prompt = f"""I want to travel to {bo_dest} for {bo_dur} days on a ${bo_budget} total budget.

My non-negotiables: {bo_non_neg}
My travel history: {travel_history}

Help me maximize value within this budget:
1. **Is this budget realistic?** What can I actually afford?
2. **Flight hacks** — cheapest booking strategies, which airports, which days to fly
3. **Accommodation strategy** — where to stay to save vs where to splurge
4. **Daily budget breakdown** — what to spend per day on food, transport, activities
5. **Free activities** that are actually great (not just "wander around")
6. **Budget mistakes to avoid** — tourist traps and overpriced spots
7. **Money-saving apps and tools** for this destination
8. **Total cost estimate** with best/worst case scenarios

Be honest if the budget is too tight — suggest alternatives if needed."""

                with st.spinner("Optimizing your travel budget..."):
                    result = _ask_claude(prompt, max_tokens=2000)
                st.session_state["ai_travel_result"] = result

    elif ai_mode == "📊 Analyze My Travel Patterns":
        if not completed_trips:
            st.info("Complete some trips to analyze your travel patterns!")
        else:
            if st.button("🤖 Analyze My Travel DNA", type="primary", key="ai_analyze_btn"):
                all_memories_text = ""
                for t in completed_trips[:5]:
                    mems = _load_memories(t["id"])
                    if mems:
                        mem_excerpts = "\n".join(f"  - {m['title']}: {m['content'][:100]}" for m in mems[:3])
                        all_memories_text += f"\n{t['destination']} memories:\n{mem_excerpts}"

                prompt = f"""Analyze this person's travel history and give deep insights about their travel style, preferences, and patterns.

{travel_history}

Milestones related to travel:
{chr(10).join(f"- {m['title']} ({m['milestone_date'][:10]})" for m in milestones if m.get('category') == 'travel')}

Journal excerpts:
{all_memories_text}

Provide:
1. **Your Travel Personality** — what type of traveler you are based on the data
2. **Pattern Analysis** — when you travel, how much you spend, what you prioritize
3. **Destination Patterns** — what your past choices reveal about your preferences
4. **Budget Patterns** — are you a budget traveler, mid-range, or splurger?
5. **What you're missing** — types of travel you haven't tried that you'd probably love
6. **Your next 3 ideal destinations** — specifically matched to your patterns
7. **Travel goals to set** — what would make your travel life more fulfilling
8. **Your travel year in review** — a narrative summary of your travel life

Make it personal, specific, and insightful."""

                with st.spinner("Analyzing your travel patterns..."):
                    result = _ask_claude(prompt, max_tokens=2000)
                st.session_state["ai_travel_result"] = result

    elif ai_mode == "🗺️ Itinerary Builder":
        it_dest = st.text_input("Destination", placeholder="New York City, Tokyo...", key="ai_it_dest")
        it_days = st.number_input("Number of Days", min_value=1, max_value=21, value=5, key="ai_it_days")
        it_style = st.selectbox("Pace", ["packed (see everything)", "balanced", "relaxed (quality over quantity)"], key="ai_it_style")
        it_prefs = st.text_area("What you love", height=80, placeholder="Art museums, street food, rooftop bars, morning walks, live music...", key="ai_it_prefs")
        it_mobility = st.selectbox("Mobility", ["no restrictions", "prefer minimal walking", "traveling with kids", "traveling with seniors"], key="ai_it_mob")

        if st.button("🤖 Build My Itinerary", type="primary", key="ai_it_btn"):
            if it_dest.strip():
                prompt = f"""Build a detailed {it_days}-day itinerary for {it_dest}.

Style: {it_style}
Preferences: {it_prefs}
Mobility: {it_mobility}
Travel history for context: {travel_history}

Create a hour-by-hour itinerary for each day with:
- **Morning** (8am-12pm): Specific activities with names, addresses
- **Afternoon** (12pm-6pm): Sights + lunch recommendation
- **Evening** (6pm+): Dinner + evening activity
- **Pro tip** for each day
- **Transportation** between stops
- **Estimated cost** for the day

Format each day as:
**Day X: [Theme]**
[Schedule]

Include backup options if something is closed. Be specific — actual restaurant names, museum names, neighborhoods."""

                with st.spinner(f"Building your {it_days}-day {it_dest} itinerary..."):
                    result = _ask_claude(prompt, max_tokens=3000)
                st.session_state["ai_travel_result"] = result

    else:  # Custom question
        custom_q = st.text_area("Your travel question", height=120,
            placeholder="Ask anything: best time to visit X, visa requirements, packing list for Y, travel insurance advice...",
            key="ai_custom_q")
        if st.button("🤖 Ask AI", type="primary", key="ai_custom_btn"):
            if custom_q.strip():
                context = f"Travel background: {travel_history}\n\n"
                with st.spinner("Thinking..."):
                    result = _ask_claude(context + custom_q, max_tokens=1500)
                st.session_state["ai_travel_result"] = result

    # Display result
    if st.session_state.get("ai_travel_result"):
        st.markdown("---")
        st.markdown(st.session_state["ai_travel_result"])
        col_clear, col_copy = st.columns([1, 4])
        if col_clear.button("🗑️ Clear", key="clear_ai_result"):
            st.session_state.pop("ai_travel_result", None)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — FLIGHTS & HOTELS
# ══════════════════════════════════════════════════════════════════════════════
with tab_flights:
    st.markdown("### ✈️ Flights, Hotels & Rides")
    st.caption("Log all travel bookings with cost tracking.")

    fh_tab1, fh_tab2, fh_tab3 = st.tabs(["✈️ Flights", "🏨 Hotels", "🚗 Rideshare"])

    # ── Flights Sub-tab ────────────────────────────────────────────────────────
    with fh_tab1:
        st.markdown("#### ✈️ Flight Log")

        with st.expander("➕ Log New Flight", expanded=False):
            with st.form("add_flight_form", clear_on_submit=True):
                if trips:
                    trip_opts_f = {"none": "No trip / standalone"} | _trip_options(trips)
                    fl_trip = st.selectbox("Link to Trip (optional)",
                                           options=list(trip_opts_f.keys()),
                                           format_func=lambda x: trip_opts_f[x],
                                           key="fl_trip_sel")
                    fl_trip_id = None if fl_trip == "none" else fl_trip
                else:
                    fl_trip_id = None

                fc1, fc2 = st.columns(2)
                fl_date = fc1.date_input("Flight Date", value=date.today(), key="fl_date")
                fl_airline = fc2.text_input("Airline", placeholder="Delta, United, Southwest...", key="fl_airline")
                fc3, fc4 = st.columns(2)
                fl_origin = fc3.text_input("From *", placeholder="ATL", key="fl_origin")
                fl_dest   = fc4.text_input("To *", placeholder="JFK", key="fl_dest_inp")
                fc5, fc6 = st.columns(2)
                fl_num   = fc5.text_input("Flight #", placeholder="DL 1234", key="fl_num")
                fl_class = fc6.selectbox("Class", ["economy", "premium economy", "business", "first"], key="fl_class")
                fc7, fc8, fc9 = st.columns(3)
                fl_dep = fc7.text_input("Departure Time", placeholder="8:30 AM", key="fl_dep")
                fl_arr = fc8.text_input("Arrival Time", placeholder="11:45 AM", key="fl_arr")
                fl_cost  = fc9.number_input("Cost ($)", min_value=0.0, value=0.0, format="%.2f", key="fl_cost")
                fc10, fc11 = st.columns(2)
                fl_miles = fc10.number_input("Miles Earned", min_value=0, value=0, key="fl_miles")
                fl_ref   = fc11.text_input("Booking Reference", placeholder="ABC123", key="fl_ref")
                fl_notes = st.text_area("Notes", height=60, key="fl_notes")

                if st.form_submit_button("✈️ Save Flight", type="primary", use_container_width=True):
                    if fl_origin.strip() and fl_dest.strip():
                        conn = get_conn()
                        db_exec(conn,
                            "INSERT INTO flights (trip_id, flight_date, origin, destination, airline, "
                            "flight_number, departure_time, arrival_time, seat_class, cost, miles_earned, "
                            "booking_ref, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (fl_trip_id, fl_date.isoformat(), fl_origin.strip().upper(),
                             fl_dest.strip().upper(), fl_airline.strip(), fl_num.strip(),
                             fl_dep.strip(), fl_arr.strip(), fl_class, fl_cost,
                             fl_miles, fl_ref.strip(), fl_notes.strip())
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Flight {fl_origin.strip().upper()} → {fl_dest.strip().upper()} saved!")
                        st.rerun()
                    else:
                        st.error("Origin and destination are required.")

        # Display flights
        all_flights = _load_flights()
        if not all_flights:
            st.info("No flights logged yet.")
        else:
            total_miles = sum(f.get("miles_earned", 0) for f in all_flights)
            total_fcost = sum(f.get("cost", 0) for f in all_flights)
            fm1, fm2, fm3 = st.columns(3)
            fm1.metric("Total Flights", len(all_flights))
            fm2.metric("Total Flight Cost", f"${total_fcost:,.0f}")
            fm3.metric("Total Miles Earned", f"{total_miles:,}")

            df_flights = pd.DataFrame([{
                "Date": f["flight_date"][:10],
                "Route": f"{f['origin']} → {f['destination']}",
                "Airline": f.get("airline", ""),
                "Flight #": f.get("flight_number", ""),
                "Class": f.get("seat_class", ""),
                "Cost": f"${f.get('cost', 0):,.2f}",
                "Miles": f.get("miles_earned", 0),
                "Ref": f.get("booking_ref", ""),
            } for f in all_flights])
            st.dataframe(df_flights, use_container_width=True, hide_index=True)

            # Delete individual flights
            st.markdown("#### Manage Flights")
            for f in all_flights[:10]:
                fc1, fc2 = st.columns([5, 1])
                fc1.markdown(f"**{f['flight_date'][:10]}** · {f['origin']} → {f['destination']} · "
                            f"{f.get('airline', '')} · ${f.get('cost', 0):,.0f}")
                if fc2.button("🗑️", key=f"del_flight_{f['id']}"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM flights WHERE id=?", (f["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    # ── Hotels Sub-tab ─────────────────────────────────────────────────────────
    with fh_tab2:
        st.markdown("#### 🏨 Hotel Stays")

        with st.expander("➕ Log Hotel Stay", expanded=False):
            with st.form("add_hotel_form", clear_on_submit=True):
                if trips:
                    trip_opts_h = {"none": "No trip / standalone"} | _trip_options(trips)
                    ht_trip = st.selectbox("Link to Trip (optional)",
                                           options=list(trip_opts_h.keys()),
                                           format_func=lambda x: trip_opts_h[x],
                                           key="ht_trip_sel")
                    ht_trip_id = None if ht_trip == "none" else ht_trip
                else:
                    ht_trip_id = None

                hc1, hc2 = st.columns(2)
                ht_name = hc1.text_input("Hotel Name *", placeholder="Marriott, Airbnb, Hostel...", key="ht_name")
                ht_city = hc2.text_input("City *", placeholder="New York, Paris...", key="ht_city")
                hc3, hc4 = st.columns(2)
                ht_checkin  = hc3.date_input("Check-in", value=date.today(), key="ht_checkin")
                ht_checkout = hc4.date_input("Check-out", value=date.today() + datetime.timedelta(days=1), key="ht_checkout")
                hc5, hc6 = st.columns(2)
                ht_room    = hc5.text_input("Room Type", placeholder="King, Suite, Double...", key="ht_room")
                ht_rate    = hc6.number_input("Nightly Rate ($)", min_value=0.0, value=0.0, format="%.2f", key="ht_rate")
                hc7, hc8, hc9 = st.columns(3)
                ht_platform = hc7.selectbox("Booked Via", ["Direct", "Booking.com", "Hotels.com", "Airbnb", "Expedia", "VRBO", "Hopper", "Other"], key="ht_platform")
                ht_rating  = hc8.slider("Rating", 0, 5, 0, key="ht_rating")
                ht_conf    = hc9.text_input("Confirmation #", placeholder="ABC123", key="ht_conf")

                # Auto-calculate total
                try:
                    nights = max(1, (ht_checkout - ht_checkin).days)
                    auto_total = ht_rate * nights
                except Exception:
                    nights = 1
                    auto_total = 0.0
                ht_total = st.number_input(
                    f"Total Cost ($) — {nights} night(s) × ${ht_rate:,.2f} = ${auto_total:,.2f}",
                    min_value=0.0, value=auto_total, format="%.2f", key="ht_total"
                )
                ht_notes = st.text_area("Notes", height=60, key="ht_notes")

                if st.form_submit_button("🏨 Save Hotel Stay", type="primary", use_container_width=True):
                    if ht_name.strip() and ht_city.strip():
                        conn = get_conn()
                        db_exec(conn,
                            "INSERT INTO hotels (trip_id, hotel_name, city, check_in, check_out, room_type, "
                            "nightly_rate, total_cost, rating, booking_platform, confirmation_num, notes) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (ht_trip_id, ht_name.strip(), ht_city.strip(),
                             ht_checkin.isoformat(), ht_checkout.isoformat(),
                             ht_room.strip(), ht_rate, ht_total, ht_rating,
                             ht_platform, ht_conf.strip(), ht_notes.strip())
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {ht_name.strip()} in {ht_city.strip()} saved!")
                        st.rerun()
                    else:
                        st.error("Hotel name and city are required.")

        # Display hotels
        all_hotels = _load_hotels()
        if not all_hotels:
            st.info("No hotel stays logged yet.")
        else:
            total_hcost = sum(h.get("total_cost", 0) for h in all_hotels)
            total_hnights = sum(
                max(0, (date.fromisoformat(h["check_out"][:10]) - date.fromisoformat(h["check_in"][:10])).days)
                for h in all_hotels
            )
            hm1, hm2, hm3 = st.columns(3)
            hm1.metric("Total Hotel Stays", len(all_hotels))
            hm2.metric("Total Hotel Cost", f"${total_hcost:,.0f}")
            hm3.metric("Total Nights", total_hnights)

            df_hotels = pd.DataFrame([{
                "Hotel": h["hotel_name"],
                "City": h["city"],
                "Check-in": h["check_in"][:10],
                "Check-out": h["check_out"][:10],
                "Room": h.get("room_type", ""),
                "Nightly": f"${h.get('nightly_rate', 0):,.0f}",
                "Total": f"${h.get('total_cost', 0):,.2f}",
                "Rating": _stars(h.get("rating", 0)),
                "Platform": h.get("booking_platform", ""),
            } for h in all_hotels])
            st.dataframe(df_hotels, use_container_width=True, hide_index=True)

            # Delete hotels
            st.markdown("#### Manage Hotels")
            for h in all_hotels[:10]:
                hc1, hc2 = st.columns([5, 1])
                hc1.markdown(f"**{h['hotel_name']}** · {h['city']} · "
                             f"{h['check_in'][:10]} → {h['check_out'][:10]} · "
                             f"${h.get('total_cost', 0):,.0f}")
                if hc2.button("🗑️", key=f"del_hotel_{h['id']}"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM hotels WHERE id=?", (h["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    # ── Rideshare Sub-tab ──────────────────────────────────────────────────────
    with fh_tab3:
        st.markdown("#### 🚗 Rideshare / Uber Log")

        with st.expander("➕ Log Ride", expanded=False):
            with st.form("add_uber_form", clear_on_submit=True):
                if trips:
                    trip_opts_u = {"none": "No trip / standalone"} | _trip_options(trips)
                    ub_trip = st.selectbox("Link to Trip (optional)",
                                           options=list(trip_opts_u.keys()),
                                           format_func=lambda x: trip_opts_u[x],
                                           key="ub_trip_sel")
                    ub_trip_id = None if ub_trip == "none" else ub_trip
                else:
                    ub_trip_id = None

                uc1, uc2 = st.columns(2)
                ub_date    = uc1.date_input("Ride Date", value=date.today(), key="ub_date")
                ub_service = uc2.selectbox("Service", ["Uber", "Lyft", "Taxi", "Grab", "Bolt", "Other"], key="ub_service")
                uc3, uc4 = st.columns(2)
                ub_pickup  = uc3.text_input("Pickup", placeholder="Hotel, Airport...", key="ub_pickup")
                ub_dropoff = uc4.text_input("Drop-off", placeholder="Restaurant, Museum...", key="ub_dropoff")
                uc5, uc6 = st.columns(2)
                ub_city = uc5.text_input("City", placeholder="New York, Tokyo...", key="ub_city")
                ub_cost = uc6.number_input("Cost ($)", min_value=0.0, value=0.0, format="%.2f", key="ub_cost")
                ub_notes = st.text_area("Notes", height=60, key="ub_notes")

                if st.form_submit_button("🚗 Save Ride", type="primary", use_container_width=True):
                    conn = get_conn()
                    db_exec(conn,
                        "INSERT INTO ubers (trip_id, ride_date, pickup, dropoff, service, cost, city, notes) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (ub_trip_id, ub_date.isoformat(), ub_pickup.strip(),
                         ub_dropoff.strip(), ub_service, ub_cost, ub_city.strip(), ub_notes.strip())
                    )
                    conn.commit()
                    conn.close()
                    st.success("🚗 Ride saved!")
                    st.rerun()

        # Display rides
        all_ubers = _load_ubers()
        if not all_ubers:
            st.info("No rides logged yet.")
        else:
            total_uber_cost = sum(u.get("cost", 0) for u in all_ubers)
            um1, um2 = st.columns(2)
            um1.metric("Total Rides", len(all_ubers))
            um2.metric("Total Ride Spend", f"${total_uber_cost:,.2f}")

            df_ubers = pd.DataFrame([{
                "Date": u["ride_date"][:10],
                "Service": u.get("service", "Uber"),
                "From": u.get("pickup", ""),
                "To": u.get("dropoff", ""),
                "City": u.get("city", ""),
                "Cost": f"${u.get('cost', 0):,.2f}",
            } for u in all_ubers])
            st.dataframe(df_ubers, use_container_width=True, hide_index=True)

            # Spend by service
            if len(all_ubers) >= 3:
                service_spend = {}
                for u in all_ubers:
                    s = u.get("service", "Other")
                    service_spend[s] = service_spend.get(s, 0) + u.get("cost", 0)
                fig_uber = px.pie(
                    values=list(service_spend.values()),
                    names=list(service_spend.keys()),
                    title="Rideshare Spend by Service",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )
                fig_uber.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#fafafa", height=300)
                st.plotly_chart(fig_uber, use_container_width=True)

            # Delete rides
            st.markdown("#### Manage Rides")
            for u in all_ubers[:10]:
                rc1, rc2 = st.columns([5, 1])
                rc1.markdown(f"**{u['ride_date'][:10]}** · {u.get('service', '')} · "
                             f"{u.get('pickup', '')} → {u.get('dropoff', '')} · "
                             f"${u.get('cost', 0):,.2f}")
                if rc2.button("🗑️", key=f"del_uber_{u['id']}"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM ubers WHERE id=?", (u["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    # ── Overall Cost Summary ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💰 Travel Cost Breakdown")
    all_ubers_summary = _load_ubers()
    total_uber_all = sum(u.get("cost", 0) for u in all_ubers_summary)
    total_flight_all = sum(f.get("cost", 0) for f in _load_flights())
    total_hotel_all = sum(h.get("total_cost", 0) for h in _load_hotels())
    total_trip_other = sum(t.get("total_spent", 0) for t in trips) - total_flight_all - total_hotel_all - total_uber_all

    cost_data = {
        "Flights": total_flight_all,
        "Hotels": total_hotel_all,
        "Rideshare": total_uber_all,
        "Other": max(0, total_trip_other),
    }
    cost_data = {k: v for k, v in cost_data.items() if v > 0}

    if cost_data:
        fig_cost = px.pie(
            values=list(cost_data.values()),
            names=list(cost_data.keys()),
            title=f"Total Travel Spend: ${sum(cost_data.values()):,.0f}",
            color_discrete_sequence=["#4a9eff", "#ffab76", "#4caf50", "#e57373"],
        )
        fig_cost.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#fafafa", height=350)
        st.plotly_chart(fig_cost, use_container_width=True)
    else:
        st.info("Log flights, hotels, and rides to see your travel cost breakdown.")
