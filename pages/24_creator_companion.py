"""
Creator Companion — Page 24
Plan, schedule, and post content for all channels with AI-powered ideation.
Channels: bookofdarrian, Peach State Savings, To-Do App, and more.
"""
import streamlit as st
from datetime import datetime, date, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="🎬 Creator Companion — Peach State Savings",
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
st.sidebar.page_link("pages/22_todo.py",                label="Todo",             icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",          icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",            icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",    icon="🎵")
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
        CREATE TABLE IF NOT EXISTS cc_channels (
            id {ai},
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            niche TEXT DEFAULT '',
            goal TEXT DEFAULT '',
            color TEXT DEFAULT '#ffa726',
            active INTEGER DEFAULT 1,
            created_at TEXT {ts}
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS cc_content (
            id {ai},
            channel_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content_type TEXT DEFAULT 'video',
            status TEXT DEFAULT 'idea',
            platform TEXT DEFAULT 'YouTube',
            scheduled_date TEXT DEFAULT NULL,
            published_date TEXT DEFAULT NULL,
            description TEXT DEFAULT '',
            script TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            created_at TEXT {ts}
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS cc_ideas (
            id {ai},
            channel_id INTEGER DEFAULT NULL,
            idea TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            used INTEGER DEFAULT 0,
            created_at TEXT {ts}
        )
    """)
    conn.commit()
    conn.close()

_ensure_tables()

# ── Seed default channels if none exist ───────────────────────────────────────
def _seed_channels():
    conn = get_conn()
    c = db_exec(conn, "SELECT COUNT(*) FROM cc_channels")
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        defaults = [
            ("bookofdarrian", "YouTube", "Lifestyle / Culture / Finance",
             "Get back to consistent posting — 1 video/week by EOY", "#ffa726"),
            ("Peach State Savings", "YouTube / TikTok", "Personal Finance",
             "Educate audience on budgeting, investing, and building wealth in Atlanta", "#ef5350"),
            ("To-Do App", "Product / Social", "SaaS / Productivity",
             "Build audience for the productivity app launch", "#42a5f5"),
        ]
        conn = get_conn()
        for name, platform, niche, goal, color in defaults:
            db_exec(conn,
                "INSERT INTO cc_channels (name, platform, niche, goal, color) VALUES (?,?,?,?,?)",
                (name, platform, niche, goal, color))
        conn.commit()
        conn.close()

_seed_channels()

# ── Constants ──────────────────────────────────────────────────────────────────
STATUSES      = ["idea", "scripting", "filming", "editing", "scheduled", "published", "archived"]
STATUS_COLORS = {
    "idea": "#607d8b", "scripting": "#9c27b0", "filming": "#e91e63",
    "editing": "#ff9800", "scheduled": "#2196f3", "published": "#4caf50", "archived": "#78909c"
}
CONTENT_TYPES = ["video", "short", "reel", "post", "thread", "podcast", "blog", "live"]
PLATFORMS     = ["YouTube", "TikTok", "Instagram", "Twitter/X", "LinkedIn", "Substack", "Multiple"]

# ── Helpers ────────────────────────────────────────────────────────────────────
def _badge(text, color, text_color="#fff"):
    return (f'<span style="background:{color};color:{text_color};padding:2px 9px;'
            f'border-radius:10px;font-size:11px;font-weight:bold">{text}</span>')

def _load_channels():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM cc_channels ORDER BY name ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_content(channel_id=None, status=None):
    conn = get_conn()
    where, params = [], []
    if channel_id:
        where.append("channel_id=?"); params.append(channel_id)
    if status:
        where.append("status=?"); params.append(status)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    c = db_exec(conn,
        f"SELECT * FROM cc_content {clause} ORDER BY scheduled_date ASC, created_at DESC",
        tuple(params))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_ideas(channel_id=None, used=0):
    conn = get_conn()
    if channel_id:
        c = db_exec(conn,
            "SELECT * FROM cc_ideas WHERE channel_id=? AND used=? ORDER BY created_at DESC",
            (channel_id, used))
    else:
        c = db_exec(conn,
            "SELECT * FROM cc_ideas WHERE used=? ORDER BY created_at DESC",
            (used,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

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

# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("🎬 Creator Companion")
st.caption("Plan, schedule & publish content across all your channels — powered by AI.")

channels    = _load_channels()
channel_map = {ch["id"]: ch for ch in channels}

# ── Quick stats ────────────────────────────────────────────────────────────────
all_content  = _load_content()
published    = [c for c in all_content if c["status"] == "published"]
scheduled_ct = [c for c in all_content if c["status"] == "scheduled"]
in_progress  = [c for c in all_content if c["status"] in ("scripting", "filming", "editing")]
ideas_count  = len(_load_ideas())

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Channels",    len(channels))
m2.metric("Published",   len(published))
m3.metric("Scheduled",   len(scheduled_ct))
m4.metric("In Progress", len(in_progress))
m5.metric("Idea Bank",   ideas_count)

st.divider()

tab_dash, tab_board, tab_ideas, tab_ai, tab_channels = st.tabs([
    "📊 Dashboard", "📋 Content Board", "💡 Idea Bank", "🤖 AI Studio", "⚙️ Channels"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown("### 🗓️ Upcoming Scheduled Content")
    today = date.today()
    window_end = today + timedelta(days=30)
    upcoming = []
    for item in scheduled_ct:
        ds = item.get("scheduled_date")
        if ds:
            try:
                d = date.fromisoformat(str(ds)[:10])
                if today <= d <= window_end:
                    upcoming.append(item)
            except Exception:
                pass
    upcoming.sort(key=lambda x: x["scheduled_date"])

    if not upcoming:
        st.info("Nothing scheduled in the next 30 days. Head to the Content Board to schedule posts!")
    else:
        for item in upcoming:
            ch   = channel_map.get(item["channel_id"], {})
            color = ch.get("color", "#ffa726")
            sched = str(item["scheduled_date"])[:10]
            delta = (date.fromisoformat(sched) - today).days
            due   = "Today!" if delta == 0 else f"in {delta}d"
            c1, c2, c3 = st.columns([4, 2, 2])
            c1.markdown(
                f"**{item['title']}**  \n"
                + _badge(ch.get('name', '?'), color, "#000"),
                unsafe_allow_html=True
            )
            c2.caption(f"📅 {sched} ({due})")
            c3.caption(f"🎥 {item['content_type'].title()} · {item['platform']}")
            st.divider()

    st.markdown("### 📈 Channel Overview")
    for ch in channels:
        if not ch.get("active"):
            continue
        ch_items = _load_content(channel_id=ch["id"])
        pub  = len([c for c in ch_items if c["status"] == "published"])
        scd  = len([c for c in ch_items if c["status"] == "scheduled"])
        wip  = len([c for c in ch_items if c["status"] in ("scripting", "filming", "editing")])
        col  = ch.get("color", "#ffa726")
        st.markdown(
            f'<div style="border-left:4px solid {col};padding-left:12px;margin:4px 0">'
            f'<b style="font-size:16px">{ch["name"]}</b> '
            f'<span style="color:#aaa;font-size:12px">· {ch["platform"]}</span></div>',
            unsafe_allow_html=True
        )
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Published",   pub)
        mc2.metric("Scheduled",   scd)
        mc3.metric("In Progress", wip)
        goal_text = ch.get("goal", "—")
        mc4.metric("Goal", (goal_text[:38] + "…") if len(goal_text) > 38 else goal_text)
        st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CONTENT BOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_board:
    col_f, col_a = st.columns([3, 1])
    with col_f:
        filter_ch = st.selectbox(
            "Channel",
            options=[0] + [ch["id"] for ch in channels],
            format_func=lambda x: "All Channels" if x == 0 else channel_map[x]["name"],
            key="board_filter_ch"
        )
        filter_st = st.multiselect("Status", STATUSES, default=STATUSES[:6], key="board_filter_st")
    with col_a:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ New Content", type="primary", use_container_width=True, key="btn_new_content"):
            st.session_state["show_add_content"] = not st.session_state.get("show_add_content", False)

    if st.session_state.get("show_add_content"):
        with st.form("add_content_form", clear_on_submit=True):
            af1, af2 = st.columns(2)
            new_title   = af1.text_input("Title *", placeholder="Video / Post title")
            new_ch_id   = af2.selectbox("Channel *",
                                        [ch["id"] for ch in channels],
                                        format_func=lambda x: channel_map[x]["name"])
            af3, af4, af5 = st.columns(3)
            new_type    = af3.selectbox("Type",     CONTENT_TYPES)
            new_status  = af4.selectbox("Status",   STATUSES)
            new_plat    = af5.selectbox("Platform", PLATFORMS)
            new_sched   = st.date_input("Scheduled Date (optional)", value=None)
            new_desc    = st.text_area("Description / Concept", height=80)
            new_tags    = st.text_input("Tags", placeholder="finance, budgeting, tips")
            if st.form_submit_button("➕ Add", type="primary", use_container_width=True):
                if new_title.strip():
                    conn = get_conn()
                    db_exec(conn,
                        "INSERT INTO cc_content "
                        "(channel_id,title,content_type,status,platform,scheduled_date,description,tags) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (new_ch_id, new_title.strip(), new_type, new_status, new_plat,
                         new_sched.isoformat() if new_sched else None,
                         new_desc.strip(), new_tags.strip()))
                    conn.commit(); conn.close()
                    st.success(f"✅ Added: {new_title.strip()}")
                    st.session_state["show_add_content"] = False
                    st.rerun()
                else:
                    st.error("Title is required.")

    items = _load_content(channel_id=filter_ch if filter_ch != 0 else None)
    items = [i for i in items if i["status"] in filter_st]

    if not items:
        st.info("No content found. Add some above!")
    else:
        st.caption(f"{len(items)} item(s)")
        for item in items:
            ch    = channel_map.get(item["channel_id"], {})
            col   = ch.get("color", "#ffa726")
            cname = ch.get("name", "?")
            st_color = STATUS_COLORS.get(item["status"], "#607d8b")
            with st.container():
                b1, b2, b3 = st.columns([5, 3, 2])
                b1.markdown(
                    f"**{item['title']}**  \n"
                    + _badge(cname, col, "#000") + " "
                    + _badge(item["status"].upper(), st_color)
                    + f' <span style="color:#aaa;font-size:11px">{item["content_type"].title()} · {item["platform"]}</span>',
                    unsafe_allow_html=True
                )
                if item.get("description"):
                    b1.caption(item["description"][:120])
                sd = str(item["scheduled_date"])[:10] if item.get("scheduled_date") else "Unscheduled"
                b2.caption(f"📅 {sd}")
                if item.get("tags"):
                    b2.caption(f"🏷️ {item['tags'][:60]}")
                with b3:
                    cur_idx = STATUSES.index(item["status"]) if item["status"] in STATUSES else 0
                    new_st = st.selectbox("", STATUSES, index=cur_idx,
                                          key=f"st_{item['id']}", label_visibility="collapsed")
                    if new_st != item["status"]:
                        conn = get_conn()
                        pub_dt = datetime.now().strftime("%Y-%m-%d") if new_st == "published" else item.get("published_date")
                        db_exec(conn, "UPDATE cc_content SET status=?,published_date=? WHERE id=?",
                                (new_st, pub_dt, item["id"]))
                        conn.commit(); conn.close()
                        st.rerun()
                    if st.button("🗑️", key=f"del_c_{item['id']}"):
                        conn = get_conn()
                        db_exec(conn, "DELETE FROM cc_content WHERE id=?", (item["id"],))
                        conn.commit(); conn.close()
                        st.rerun()
            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — IDEA BANK
# ══════════════════════════════════════════════════════════════════════════════
with tab_ideas:
    st.markdown("### 💡 Idea Bank")
    with st.form("add_idea_form", clear_on_submit=True):
        ii1, ii2 = st.columns([4, 2])
        idea_text = ii1.text_input("New Idea *", placeholder="What should you create next?")
        idea_ch   = ii2.selectbox("Channel",
                                  [0] + [ch["id"] for ch in channels],
                                  format_func=lambda x: "Any / Undecided" if x == 0 else channel_map[x]["name"])
        if st.form_submit_button("💡 Save Idea", type="primary"):
            if idea_text.strip():
                conn = get_conn()
                db_exec(conn, "INSERT INTO cc_ideas (channel_id,idea,source) VALUES (?,?,?)",
                        (idea_ch if idea_ch != 0 else None, idea_text.strip(), "manual"))
                conn.commit(); conn.close()
                st.success("💡 Idea saved!")
                st.rerun()

    ideas = _load_ideas()
    if not ideas:
        st.info("No ideas yet. Add some above or use the AI Studio tab to generate ideas!")
    else:
        st.caption(f"{len(ideas)} idea(s) in the bank")
        for idea in ideas:
            ch    = channel_map.get(idea.get("channel_id")) or {}
            cname = ch.get("name", "Any Channel")
            ccolor = ch.get("color", "#607d8b")
            ic1, ic2, ic3 = st.columns([6, 2, 2])
            ic1.markdown(f"💡 {idea['idea']}")
            ic2.markdown(_badge(cname, ccolor, "#000"), unsafe_allow_html=True)
            with ic3:
                if st.button("➡️ Use", key=f"use_{idea['id']}"):
                    conn = get_conn()
                    db_exec(conn, "UPDATE cc_ideas SET used=1 WHERE id=?", (idea["id"],))
                    conn.commit(); conn.close()
                    st.toast("Idea marked as used! Add it to the Content Board.")
                    st.rerun()
                if st.button("🗑️", key=f"del_i_{idea['id']}"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM cc_ideas WHERE id=?", (idea["id"],))
                    conn.commit(); conn.close()
                    st.rerun()
            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI STUDIO
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("### 🤖 AI Content Studio")
    st.caption("Use Claude AI to generate ideas, write scripts, build calendars, and craft titles.")

    ai_task = st.selectbox("What do you want AI to help with?", [
        "Generate video ideas",
        "Write a script outline",
        "Craft 5 viral title variations",
        "Build a 4-week content calendar",
        "Write a video description + tags",
        "Generate a content strategy",
        "Write a hook / intro",
        "Custom prompt",
    ])
    ai_ch_id = st.selectbox("For which channel?",
                             [ch["id"] for ch in channels],
                             format_func=lambda x: channel_map[x]["name"],
                             key="ai_ch_sel")
    sel_ch = channel_map.get(ai_ch_id, {})
    ctx = (f"You are helping Darrian Belcher, a content creator.\n"
           f"Channel: {sel_ch.get('name','')}\n"
           f"Platform: {sel_ch.get('platform','')}\n"
           f"Niche: {sel_ch.get('niche','')}\n"
           f"Goal: {sel_ch.get('goal','')}")

    if ai_task == "Generate video ideas":
        count  = st.slider("How many ideas?", 5, 20, 10)
        angle  = st.text_input("Specific angle or theme?", placeholder="e.g., beginner finance, Atlanta culture")
        if st.button("✨ Generate Ideas", type="primary"):
            with st.spinner("Generating..."):
                p = (f"{ctx}\n\nGenerate {count} compelling video ideas for this channel. "
                     f"Each should have: a punchy title, one-sentence description, and why it performs well. "
                     f"{'Angle: ' + angle if angle else ''}")
                res = _ask_ai(p)
            st.markdown(res)

    elif ai_task == "Write a script outline":
        vid_title = st.text_input("Video title / topic")
        vid_len   = st.selectbox("Target length", ["5 min", "10 min", "15 min", "20+ min"])
        if st.button("✍️ Write Outline", type="primary") and vid_title:
            with st.spinner("Writing outline..."):
                p = (f"{ctx}\n\nWrite a detailed script outline for a {vid_len} video titled: '{vid_title}'. "
                     f"Include: Hook, Intro, 3-5 main sections with talking points, CTA, and outro. "
                     f"Keep it conversational and authentic to Darrian's voice.")
                res = _ask_ai(p)
            st.markdown(res)

    elif ai_task == "Craft 5 viral title variations":
        topic = st.text_input("What is the video about?")
        if st.button("🔥 Generate Titles", type="primary") and topic:
            with st.spinner("Crafting titles..."):
                p = (f"{ctx}\n\nCreate 5 viral title variations for a video about: {topic}. "
                     f"Mix styles: curiosity gap, listicle, personal story, bold claim, how-to. "
                     f"Each title under 60 characters, optimized for clicks and SEO.")
                res = _ask_ai(p)
            st.markdown(res)

    elif ai_task == "Build a 4-week content calendar":
        freq   = st.selectbox("Posting frequency", ["1x/week", "2x/week", "3x/week", "Daily"])
        series = st.text_input("Recurring themes or series?", placeholder="e.g., Money Monday, Story Time Friday")
        if st.button("📅 Build Calendar", type="primary"):
            with st.spinner("Building calendar..."):
                p = (f"{ctx}\n\nBuild a 4-week content calendar posting {freq}. "
                     f"{'Include these series: ' + series if series else ''} "
                     f"Format as a table: Week | Day | Title | Type | Platform. Make it varied and realistic.")
                res = _ask_ai(p)
            st.markdown(res)

    elif ai_task == "Write a video description + tags":
        vt = st.text_input("Video title")
        vs = st.text_area("Brief summary of what the video covers", height=80)
        if st.button("📝 Generate", type="primary") and vt:
            with st.spinner("Writing..."):
                p = (f"{ctx}\n\nWrite a YouTube description and tag list for:\nTitle: {vt}\nTopic: {vs}\n\n"
                     f"Format: Hook paragraph, 3-4 body paragraphs, timestamps placeholder, subscribe CTA, "
                     f"then 15-20 SEO tags as a comma-separated list.")
                res = _ask_ai(p)
            st.markdown(res)

    elif ai_task == "Generate a content strategy":
        timeframe = st.selectbox("Timeframe", ["1 month", "3 months", "6 months", "1 year"])
        goal_inp  = st.text_input("Primary goal?", placeholder="e.g., grow to 10k subs, launch a product")
        if st.button("🗺️ Generate Strategy", type="primary") and goal_inp:
            with st.spinner("Building strategy..."):
                p = (f"{ctx}\n\nCreate a {timeframe} content strategy. Goal: {goal_inp}. "
                     f"Include: content pillars, posting cadence, growth tactics, monetization opportunities, "
                     f"collaboration ideas, and key milestones. Be specific and actionable.")
                res = _ask_ai(p)
            st.markdown(res)

    elif ai_task == "Write a hook / intro":
        h_topic = st.text_input("Video topic / title")
        h_style = st.selectbox("Hook style", ["Story", "Shocking stat", "Bold claim", "Question", "Relatable problem"])
        if st.button("🎣 Write Hook", type="primary") and h_topic:
            with st.spinner("Writing hook..."):
                p = (f"{ctx}\n\nWrite a {h_style}-style YouTube hook/intro (first 30 seconds) for a video about: {h_topic}. "
                     f"Immediately grab attention, establish credibility, and preview the value. Under 150 words.")
                res = _ask_ai(p)
            st.markdown(res)

    else:
        custom = st.text_area("Your prompt", height=150, placeholder="Ask AI anything about content creation...")
        if st.button("✨ Ask AI", type="primary") and custom:
            with st.spinner("Thinking..."):
                res = _ask_ai(f"{ctx}\n\n{custom}")
            st.markdown(res)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CHANNELS
# ══════════════════════════════════════════════════════════════════════════════
with tab_channels:
    st.markdown("### ⚙️ Manage Channels")
    with st.expander("➕ Add New Channel"):
        with st.form("add_ch_form", clear_on_submit=True):
            nc1, nc2 = st.columns(2)
            ch_name  = nc1.text_input("Channel Name *")
            ch_plat  = nc2.text_input("Platform(s) *", placeholder="YouTube, TikTok, Instagram...")
            ch_niche = st.text_input("Niche / Topic")
            ch_goal  = st.text_area("Goal", height=60, placeholder="What do you want to achieve with this channel?")
            ch_color = st.color_picker("Brand Color", "#ffa726")
            if st.form_submit_button("➕ Add Channel", type="primary") and ch_name.strip():
                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO cc_channels (name,platform,niche,goal,color) VALUES (?,?,?,?,?)",
                    (ch_name.strip(), ch_plat.strip(), ch_niche.strip(), ch_goal.strip(), ch_color))
                conn.commit(); conn.close()
                st.success(f"✅ Added: {ch_name}")
                st.rerun()

    for ch in channels:
        color = ch.get("color", "#ffa726")
        st.markdown(
            f'<div style="border-left:4px solid {color};padding-left:12px">'
            f'<b style="font-size:15px">{ch["name"]}</b> — '
            f'<span style="color:#aaa">{ch["platform"]}</span></div>',
            unsafe_allow_html=True
        )
        st.caption(f"Niche: {ch.get('niche','—')}  |  Goal: {ch.get('goal','—')[:100]}")
        if st.button("🗑️ Delete", key=f"del_ch_{ch['id']}"):
            conn = get_conn()
            db_exec(conn, "DELETE FROM cc_channels WHERE id=?", (ch["id"],))
            conn.commit(); conn.close()
            st.rerun()
        st.divider()
