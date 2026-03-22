"""
Social Media Manager — Page 57
Ultimate all-in-one hub: draft, schedule, cross-post, and track performance
across YouTube Shorts, TikTok, Instagram Reels, Facebook, and Twitter/X
for every personal and business account.
"""
import streamlit as st
import json
from datetime import datetime, date, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="📱 Social Media Manager — Peach State Savings",
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
st.sidebar.page_link("pages/57_social_media_manager.py", label="📱 Social Media",    icon="📱")
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

    # Social accounts (personal & business profiles per platform)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS smm_accounts (
            id {ai},
            display_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_type TEXT DEFAULT 'personal',
            handle TEXT DEFAULT '',
            profile_url TEXT DEFAULT '',
            follower_count INTEGER DEFAULT 0,
            color TEXT DEFAULT '#1da1f2',
            active INTEGER DEFAULT 1,
            notes TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    # Posts / drafts / scheduled content
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS smm_posts (
            id {ai},
            title TEXT NOT NULL DEFAULT '',
            caption TEXT DEFAULT '',
            hashtags TEXT DEFAULT '',
            post_type TEXT DEFAULT 'short',
            status TEXT DEFAULT 'draft',
            account_ids TEXT DEFAULT '',
            scheduled_at TEXT DEFAULT NULL,
            published_at TEXT DEFAULT NULL,
            media_urls TEXT DEFAULT '',
            link TEXT DEFAULT '',
            campaign TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            created_at TEXT {ts}
        )
    """)

    # Campaigns / series groupings
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS smm_campaigns (
            id {ai},
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            goal TEXT DEFAULT '',
            start_date TEXT DEFAULT NULL,
            end_date TEXT DEFAULT NULL,
            color TEXT DEFAULT '#e040fb',
            active INTEGER DEFAULT 1,
            created_at TEXT {ts}
        )
    """)

    # Hashtag sets / templates
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS smm_hashtag_sets (
            id {ai},
            name TEXT NOT NULL,
            platforms TEXT DEFAULT '',
            hashtags TEXT DEFAULT '',
            created_at TEXT {ts}
        )
    """)

    conn.commit()
    conn.close()

_ensure_tables()

# ── Seed default accounts ──────────────────────────────────────────────────────
def _seed_accounts():
    conn = get_conn()
    c = db_exec(conn, "SELECT COUNT(*) FROM smm_accounts")
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        defaults = [
            ("bookofdarrian", "YouTube Shorts", "personal", "@bookofdarrian", "#ff0000"),
            ("bookofdarrian", "TikTok",         "personal", "@bookofdarrian", "#000000"),
            ("bookofdarrian", "Instagram",      "personal", "@bookofdarrian", "#e1306c"),
            ("bookofdarrian", "Twitter/X",      "personal", "@bookofdarrian", "#1da1f2"),
            ("bookofdarrian", "Facebook",       "personal", "bookofdarrian",  "#1877f2"),
            ("Peach State Savings", "YouTube Shorts", "business", "@peachstatesavings", "#ff0000"),
            ("Peach State Savings", "TikTok",         "business", "@peachstatesavings", "#000000"),
            ("Peach State Savings", "Instagram",      "business", "@peachstatesavings", "#e1306c"),
            ("Peach State Savings", "Twitter/X",      "business", "@pss_finance",       "#1da1f2"),
            ("Peach State Savings", "Facebook",       "business", "PeachStateSavings",  "#1877f2"),
        ]
        conn = get_conn()
        for dname, plat, atype, handle, color in defaults:
            db_exec(conn,
                "INSERT INTO smm_accounts (display_name, platform, account_type, handle, color) VALUES (?,?,?,?,?)",
                (dname, plat, atype, handle, color))
        conn.commit()
        conn.close()

_seed_accounts()

# ── Seed default hashtag sets ──────────────────────────────────────────────────
def _seed_hashtag_sets():
    conn = get_conn()
    c = db_exec(conn, "SELECT COUNT(*) FROM smm_hashtag_sets")
    count = c.fetchone()[0]
    conn.close()
    if count == 0:
        sets = [
            ("Personal Finance", "TikTok,Instagram,YouTube Shorts",
             "#personalfinance #budgeting #moneytips #savingmoney #financialfreedom #moneyadvice #investing #wealth #frugalliving #debtfree"),
            ("Atlanta / ATL", "TikTok,Instagram,Facebook",
             "#atlanta #atl #atlinfluencer #georgia #atlcreator #atlbusiness #atllife"),
            ("Content Creator", "TikTok,Instagram,YouTube Shorts",
             "#contentcreator #creatortips #socialmediatips #ugccreator #youtuber #tiktokgrowth"),
            ("Business / Entrepreneurship", "TikTok,Instagram,Twitter/X,LinkedIn",
             "#entrepreneur #business #smallbusiness #startup #businesstips #sidehustle #passiveincome"),
        ]
        conn = get_conn()
        for name, plats, tags in sets:
            db_exec(conn, "INSERT INTO smm_hashtag_sets (name, platforms, hashtags) VALUES (?,?,?)",
                    (name, plats, tags))
        conn.commit()
        conn.close()

_seed_hashtag_sets()

# ── Constants ──────────────────────────────────────────────────────────────────
PLATFORMS = ["YouTube Shorts", "TikTok", "Instagram", "Facebook", "Twitter/X"]

PLATFORM_ICONS = {
    "YouTube Shorts": "▶️",
    "TikTok":         "🎵",
    "Instagram":      "📸",
    "Facebook":       "📘",
    "Twitter/X":      "🐦",
}

PLATFORM_COLORS = {
    "YouTube Shorts": "#ff0000",
    "TikTok":         "#010101",
    "Instagram":      "#e1306c",
    "Facebook":       "#1877f2",
    "Twitter/X":      "#1da1f2",
}

POST_TYPES = ["short", "reel", "post", "story", "tweet", "thread", "live", "carousel"]

STATUSES = ["draft", "ready", "scheduled", "posted", "archived"]

STATUS_COLORS = {
    "draft":     "#607d8b",
    "ready":     "#ff9800",
    "scheduled": "#2196f3",
    "posted":    "#4caf50",
    "archived":  "#78909c",
}

ACCOUNT_TYPES = ["personal", "business"]

# ── Helpers ────────────────────────────────────────────────────────────────────
def _badge(text, color, text_color="#fff"):
    return (f'<span style="background:{color};color:{text_color};padding:2px 9px;'
            f'border-radius:10px;font-size:11px;font-weight:bold">{text}</span>')

def _platform_pill(platform):
    color = PLATFORM_COLORS.get(platform, "#607d8b")
    icon  = PLATFORM_ICONS.get(platform, "📱")
    return _badge(f"{icon} {platform}", color)

def _load_accounts(active_only=True):
    conn = get_conn()
    clause = "WHERE active=1" if active_only else ""
    c = db_exec(conn, f"SELECT * FROM smm_accounts {clause} ORDER BY account_type ASC, display_name ASC, platform ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_posts(status=None, account_id=None, campaign=None):
    conn = get_conn()
    where, params = [], []
    if status and status != "all":
        where.append("status=?"); params.append(status)
    if campaign and campaign != "all":
        where.append("campaign=?"); params.append(campaign)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    c = db_exec(conn,
        f"SELECT * FROM smm_posts {clause} ORDER BY scheduled_at ASC, created_at DESC",
        tuple(params))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    posts = [dict(zip(cols, r)) for r in rows]
    # Filter by account_id if given (stored as JSON list in account_ids)
    if account_id:
        sid = str(account_id)
        posts = [p for p in posts if sid in (p.get("account_ids") or "")]
    return posts

def _load_campaigns():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM smm_campaigns ORDER BY start_date ASC, name ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_hashtag_sets():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM smm_hashtag_sets ORDER BY name ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _ask_ai(prompt: str) -> str:
    api_key = get_setting("anthropic_api_key", "")
    if not api_key:
        api_key = st.session_state.get("anthropic_api_key", "")
    if not api_key:
        return "⚠️ No Anthropic API key found. Add it in Settings."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI Error: {e}"

def _parse_account_ids(raw: str) -> list:
    """Parse account_ids stored as comma-separated or JSON list string."""
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return [x.strip() for x in raw.split(",") if x.strip()]

def _serialize_account_ids(ids: list) -> str:
    return json.dumps([str(i) for i in ids])

def _get_platform_char_limit(platform: str) -> int:
    limits = {
        "Twitter/X":       280,
        "Facebook":        63206,
        "Instagram":       2200,
        "TikTok":          2200,
        "YouTube Shorts":  5000,
    }
    return limits.get(platform, 2200)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("📱 Social Media Manager")
st.caption("Draft once, post everywhere — YouTube Shorts, TikTok, Instagram Reels, Facebook & Twitter/X.")

accounts     = _load_accounts()
account_map  = {acc["id"]: acc for acc in accounts}
campaigns    = _load_campaigns()
campaign_map = {c["id"]: c for c in campaigns}
all_posts    = _load_posts()

# ── Quick stats ────────────────────────────────────────────────────────────────
drafts_ct    = len([p for p in all_posts if p["status"] == "draft"])
ready_ct     = len([p for p in all_posts if p["status"] == "ready"])
scheduled_ct = len([p for p in all_posts if p["status"] == "scheduled"])
posted_ct    = len([p for p in all_posts if p["status"] == "posted"])

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Accounts",  len(accounts))
m2.metric("Drafts",    drafts_ct)
m3.metric("Ready",     ready_ct)
m4.metric("Scheduled", scheduled_ct)
m5.metric("Posted",    posted_ct)
m6.metric("Campaigns", len(campaigns))

st.divider()

tab_compose, tab_queue, tab_calendar, tab_analytics, tab_ai, tab_accounts, tab_campaigns, tab_hashtags = st.tabs([
    "✍️ Compose",
    "📋 Queue",
    "🗓️ Calendar",
    "📈 Analytics",
    "🤖 AI Studio",
    "👤 Accounts",
    "🎯 Campaigns",
    "🏷️ Hashtags",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — COMPOSE
# ══════════════════════════════════════════════════════════════════════════════
with tab_compose:
    st.markdown("### ✍️ Compose New Post")
    st.caption("Create one post and choose which accounts & platforms to publish it to.")

    # Group accounts by brand for easy multi-select
    personal_accs = [a for a in accounts if a.get("account_type") == "personal"]
    business_accs = [a for a in accounts if a.get("account_type") == "business"]

    with st.form("compose_form", clear_on_submit=True):
        post_title = st.text_input("Post Title / Reference *", placeholder="e.g., 'March Finance Tips Short'")

        st.markdown("**Select Target Accounts**")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**Personal Accounts**")
            sel_personal = []
            for acc in personal_accs:
                icon = PLATFORM_ICONS.get(acc["platform"], "📱")
                if st.checkbox(f"{icon} {acc['platform']} ({acc['handle']})",
                               key=f"comp_acc_{acc['id']}"):
                    sel_personal.append(acc["id"])
        with sc2:
            st.markdown("**Business Accounts**")
            sel_business = []
            for acc in business_accs:
                icon = PLATFORM_ICONS.get(acc["platform"], "📱")
                if st.checkbox(f"{icon} {acc['platform']} — {acc['display_name']} ({acc['handle']})",
                               key=f"comp_bacc_{acc['id']}"):
                    sel_business.append(acc["id"])

        selected_ids = sel_personal + sel_business

        cf1, cf2, cf3 = st.columns(3)
        post_type  = cf1.selectbox("Post Type",  POST_TYPES)
        post_status = cf2.selectbox("Status",    STATUSES)
        campaign_names = ["(none)"] + [c["name"] for c in campaigns]
        post_campaign   = cf3.selectbox("Campaign", campaign_names)

        caption_text = st.text_area(
            "Caption / Content *",
            height=150,
            placeholder="Write your caption here. Use {{HASHTAGS}} to auto-insert your hashtag set.",
        )

        hashtag_sets = _load_hashtag_sets()
        ht1, ht2 = st.columns(2)
        sel_ht_set = ht1.selectbox("Append Hashtag Set",
                                   ["(none)"] + [h["name"] for h in hashtag_sets],
                                   key="comp_ht_set")
        custom_tags = ht2.text_input("Or custom hashtags", placeholder="#finance #atl")

        post_link   = st.text_input("Link (optional)", placeholder="https://...")
        media_input = st.text_input("Media URL / File path (optional)", placeholder="https://... or /path/to/video.mp4")
        post_notes  = st.text_area("Internal Notes", height=60, placeholder="Reminder notes, editing instructions, etc.")

        sched_col, _ = st.columns([2, 3])
        schedule_it  = sched_col.checkbox("Schedule for a specific date & time")
        scheduled_dt = None
        if schedule_it:
            sd1, sd2 = st.columns(2)
            sched_date = sd1.date_input("Date", min_value=date.today())
            sched_time = sd2.time_input("Time")
            scheduled_dt = datetime.combine(sched_date, sched_time).strftime("%Y-%m-%d %H:%M")

        if st.form_submit_button("📤 Save Post", type="primary", use_container_width=True):
            if not post_title.strip():
                st.error("Post title is required.")
            elif not caption_text.strip():
                st.error("Caption is required.")
            elif not selected_ids:
                st.error("Select at least one account to post to.")
            else:
                # Build final caption with hashtags
                final_caption = caption_text.strip()
                tags_to_append = ""
                if sel_ht_set != "(none)":
                    ht_obj = next((h for h in hashtag_sets if h["name"] == sel_ht_set), None)
                    if ht_obj:
                        tags_to_append = ht_obj["hashtags"]
                if custom_tags.strip():
                    tags_to_append = (tags_to_append + " " + custom_tags.strip()).strip()
                if "{{HASHTAGS}}" in final_caption:
                    final_caption = final_caption.replace("{{HASHTAGS}}", tags_to_append)
                else:
                    final_caption = final_caption + ("\n\n" + tags_to_append if tags_to_append else "")

                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO smm_posts "
                    "(title, caption, hashtags, post_type, status, account_ids, "
                    " scheduled_at, media_urls, link, campaign, notes) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        post_title.strip(),
                        final_caption,
                        tags_to_append,
                        post_type,
                        "scheduled" if scheduled_dt else post_status,
                        _serialize_account_ids(selected_ids),
                        scheduled_dt,
                        media_input.strip(),
                        post_link.strip(),
                        post_campaign if post_campaign != "(none)" else "",
                        post_notes.strip(),
                    ))
                conn.commit()
                conn.close()

                plat_list = ", ".join([account_map[i]["platform"] for i in selected_ids if i in account_map])
                st.success(f"✅ Post saved for: {plat_list}")
                st.rerun()

    # Cross-post quick helper
    st.divider()
    st.markdown("#### 🔁 Quick Cross-Post")
    st.caption("Adapt an existing post caption to fit a different platform's character limits and tone.")
    qc1, qc2 = st.columns(2)
    existing_posts = [p for p in all_posts if p["status"] in ("draft", "ready")]
    if existing_posts:
        sel_post_id = qc1.selectbox("Source post",
                                    [p["id"] for p in existing_posts],
                                    format_func=lambda x: next(p["title"] for p in existing_posts if p["id"] == x))
        target_plat = qc2.selectbox("Adapt for platform", PLATFORMS)
        if st.button("🔄 Adapt Caption with AI"):
            src_post = next((p for p in existing_posts if p["id"] == sel_post_id), None)
            if src_post:
                limit = _get_platform_char_limit(target_plat)
                with st.spinner("Adapting..."):
                    prompt = (
                        f"Adapt this social media caption for {target_plat} "
                        f"(max {limit} chars). Keep the core message, adjust tone and format to fit the platform. "
                        f"For Twitter/X, split into a thread if needed.\n\n"
                        f"Original caption:\n{src_post['caption']}"
                    )
                    result = _ask_ai(prompt)
                st.markdown(f"**Adapted for {target_plat}:**")
                st.text_area("Result (copy & paste)", value=result, height=200, key="adapt_result")
    else:
        st.info("No draft/ready posts available to adapt.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — QUEUE
# ══════════════════════════════════════════════════════════════════════════════
with tab_queue:
    st.markdown("### 📋 Post Queue")

    qf1, qf2, qf3 = st.columns(3)
    q_status   = qf1.selectbox("Filter by Status", ["all"] + STATUSES, key="q_st")
    q_platform = qf2.selectbox("Filter by Platform", ["all"] + PLATFORMS, key="q_plat")
    q_type     = qf3.selectbox("Filter by Type", ["all"] + POST_TYPES, key="q_type")

    posts = _load_posts(status=q_status)

    # Filter by platform (account_ids contains an account on that platform)
    if q_platform != "all":
        plat_acc_ids = {str(a["id"]) for a in accounts if a["platform"] == q_platform}
        posts = [p for p in posts if any(
            aid in plat_acc_ids
            for aid in _parse_account_ids(p.get("account_ids", ""))
        )]

    if q_type != "all":
        posts = [p for p in posts if p.get("post_type") == q_type]

    if not posts:
        st.info("No posts found with the current filters.")
    else:
        st.caption(f"{len(posts)} post(s)")
        for post in posts:
            acc_ids = _parse_account_ids(post.get("account_ids", ""))
            accs    = [account_map[int(aid)] for aid in acc_ids if int(aid) in account_map]
            plats   = list(dict.fromkeys([a["platform"] for a in accs]))  # dedupe, preserve order
            st_col  = STATUS_COLORS.get(post.get("status", "draft"), "#607d8b")

            with st.container():
                hdr1, hdr2 = st.columns([5, 3])
                platform_pills = " ".join([_platform_pill(p) for p in plats])
                hdr1.markdown(
                    f"**{post['title']}**  \n"
                    + platform_pills + " "
                    + _badge(post.get("status", "draft").upper(), st_col),
                    unsafe_allow_html=True,
                )
                sched = post.get("scheduled_at") or "Unscheduled"
                if sched and sched != "Unscheduled":
                    sched = str(sched)[:16]
                hdr2.caption(f"📅 {sched}  |  🎞️ {post.get('post_type','').title()}")
                if post.get("campaign"):
                    hdr2.caption(f"🎯 {post['campaign']}")

                with st.expander("View caption & details"):
                    st.text_area("Caption", value=post.get("caption", ""), height=120, key=f"cap_{post['id']}", disabled=True)
                    if post.get("link"):
                        st.caption(f"🔗 {post['link']}")
                    if post.get("notes"):
                        st.caption(f"📝 {post['notes']}")

                    target_accs_text = ", ".join([f"{a['display_name']} ({a['platform']})" for a in accs])
                    st.caption(f"📤 Posting to: {target_accs_text}")

                    ea1, ea2, ea3, ea4 = st.columns(4)
                    cur_st = STATUSES.index(post.get("status", "draft")) if post.get("status") in STATUSES else 0
                    new_st = ea1.selectbox("Update Status", STATUSES, index=cur_st, key=f"qst_{post['id']}")
                    if new_st != post.get("status"):
                        conn = get_conn()
                        pub_dt = datetime.now().strftime("%Y-%m-%d %H:%M") if new_st == "posted" else post.get("published_at")
                        db_exec(conn, "UPDATE smm_posts SET status=?, published_at=? WHERE id=?",
                                (new_st, pub_dt, post["id"]))
                        conn.commit(); conn.close()
                        st.rerun()
                    if ea4.button("🗑️ Delete", key=f"del_p_{post['id']}"):
                        conn = get_conn()
                        db_exec(conn, "DELETE FROM smm_posts WHERE id=?", (post["id"],))
                        conn.commit(); conn.close()
                        st.rerun()

            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_calendar:
    st.markdown("### 🗓️ Content Calendar")

    cal_weeks = st.slider("Show next N weeks", 1, 8, 4, key="cal_weeks")
    today = date.today()
    end_date = today + timedelta(weeks=cal_weeks)

    sched_posts = [p for p in all_posts if p.get("status") in ("scheduled", "posted") and p.get("scheduled_at")]

    # Build day-by-day view
    days_range = [(today + timedelta(days=i)) for i in range((end_date - today).days + 1)]

    # Group by week
    from itertools import groupby
    def week_num(d):
        return d.isocalendar()[1]

    weeks = {}
    for d in days_range:
        wk = d.isocalendar()[1]
        if wk not in weeks:
            weeks[wk] = []
        weeks[wk].append(d)

    for wk, days in weeks.items():
        wk_start = days[0].strftime("%b %d")
        wk_end   = days[-1].strftime("%b %d")
        st.markdown(f"#### 📅 Week {wk} — {wk_start} to {wk_end}")
        day_cols = st.columns(min(7, len(days)))
        for idx, day in enumerate(days):
            day_str  = day.strftime("%Y-%m-%d")
            day_name = day.strftime("%a %m/%d")
            day_posts = []
            for p in sched_posts:
                sched_str = str(p.get("scheduled_at", ""))[:10]
                if sched_str == day_str:
                    day_posts.append(p)

            with day_cols[idx % 7]:
                is_today = (day == today)
                header_style = "font-weight:bold;color:#ffa726" if is_today else "color:#aaa"
                st.markdown(f'<div style="{header_style}">{day_name}{"  📍" if is_today else ""}</div>',
                            unsafe_allow_html=True)
                if not day_posts:
                    st.markdown('<div style="color:#555;font-size:11px">—</div>', unsafe_allow_html=True)
                for p in day_posts:
                    acc_ids = _parse_account_ids(p.get("account_ids", ""))
                    plats   = list(dict.fromkeys(
                        [account_map[int(a)]["platform"] for a in acc_ids if int(a) in account_map]
                    ))
                    icons = "".join([PLATFORM_ICONS.get(pl, "📱") for pl in plats])
                    st_col = STATUS_COLORS.get(p.get("status", "draft"), "#607d8b")
                    st.markdown(
                        f'<div style="background:{st_col}22;border-left:3px solid {st_col};'
                        f'padding:3px 6px;border-radius:4px;margin:2px 0;font-size:11px">'
                        f'{icons} <b>{p["title"][:25]}</b></div>',
                        unsafe_allow_html=True,
                    )
        st.divider()

    # Upcoming list view
    st.markdown("#### 📋 Upcoming Scheduled Posts")
    upcoming = []
    for p in sched_posts:
        try:
            d = date.fromisoformat(str(p.get("scheduled_at", ""))[:10])
            if today <= d <= end_date:
                upcoming.append((d, p))
        except Exception:
            pass
    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        st.info("No upcoming scheduled posts. Head to Compose to create and schedule some!")
    else:
        for d, p in upcoming:
            delta = (d - today).days
            due_label = "Today!" if delta == 0 else ("Tomorrow!" if delta == 1 else f"in {delta}d")
            acc_ids = _parse_account_ids(p.get("account_ids", ""))
            plats   = list(dict.fromkeys(
                [account_map[int(a)]["platform"] for a in acc_ids if int(a) in account_map]
            ))
            icons  = " ".join([PLATFORM_ICONS.get(pl, "📱") for pl in plats])
            uc1, uc2, uc3 = st.columns([4, 2, 2])
            uc1.markdown(f"**{p['title']}**  \n{icons} {' · '.join(plats)}")
            uc2.caption(f"📅 {str(p['scheduled_at'])[:16]} ({due_label})")
            uc3.caption(f"🎞️ {p.get('post_type','').title()}")
            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    st.markdown("### 📈 Performance Analytics")
    st.caption("Track engagement metrics on your posted content. Log stats manually or via API integrations.")

    posted_posts = [p for p in all_posts if p.get("status") == "posted"]

    if not posted_posts:
        st.info("No posted content yet. Once you start posting and marking posts as 'posted', stats will appear here.")
    else:
        # Summary metrics across all posts
        total_views    = sum(p.get("views", 0) or 0    for p in posted_posts)
        total_likes    = sum(p.get("likes", 0) or 0    for p in posted_posts)
        total_comments = sum(p.get("comments", 0) or 0 for p in posted_posts)
        total_shares   = sum(p.get("shares", 0) or 0   for p in posted_posts)

        am1, am2, am3, am4 = st.columns(4)
        am1.metric("Total Views",    f"{total_views:,}")
        am2.metric("Total Likes",    f"{total_likes:,}")
        am3.metric("Total Comments", f"{total_comments:,}")
        am4.metric("Total Shares",   f"{total_shares:,}")
        st.divider()

        # Per-platform breakdown
        st.markdown("#### Platform Breakdown")
        plat_stats = {}
        for p in posted_posts:
            acc_ids = _parse_account_ids(p.get("account_ids", ""))
            plats   = list(dict.fromkeys(
                [account_map[int(a)]["platform"] for a in acc_ids if int(a) in account_map]
            ))
            for pl in plats:
                if pl not in plat_stats:
                    plat_stats[pl] = {"posts": 0, "views": 0, "likes": 0, "comments": 0, "shares": 0}
                plat_stats[pl]["posts"]    += 1
                plat_stats[pl]["views"]    += p.get("views", 0) or 0
                plat_stats[pl]["likes"]    += p.get("likes", 0) or 0
                plat_stats[pl]["comments"] += p.get("comments", 0) or 0
                plat_stats[pl]["shares"]   += p.get("shares", 0) or 0

        ps_cols = st.columns(len(plat_stats) or 1)
        for idx, (plat, stats) in enumerate(plat_stats.items()):
            icon  = PLATFORM_ICONS.get(plat, "📱")
            color = PLATFORM_COLORS.get(plat, "#607d8b")
            with ps_cols[idx % len(ps_cols)]:
                st.markdown(
                    f'<div style="border-left:4px solid {color};padding-left:10px">'
                    f'<b>{icon} {plat}</b></div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"{stats['posts']} posts | {stats['views']:,} views | {stats['likes']:,} likes")
        st.divider()

        # Top posts
        st.markdown("#### 🏆 Top Posts by Views")
        top_posts = sorted(posted_posts, key=lambda x: x.get("views", 0) or 0, reverse=True)[:10]
        for p in top_posts:
            acc_ids = _parse_account_ids(p.get("account_ids", ""))
            plats   = list(dict.fromkeys(
                [account_map[int(a)]["platform"] for a in acc_ids if int(a) in account_map]
            ))
            icons  = " ".join([PLATFORM_ICONS.get(pl, "📱") for pl in plats])
            ta1, ta2, ta3, ta4, ta5 = st.columns([3, 1, 1, 1, 2])
            ta1.markdown(f"**{p['title']}** {icons}")
            ta2.metric("Views",    p.get("views", 0) or 0)
            ta3.metric("Likes",    p.get("likes", 0) or 0)
            ta4.metric("Comments", p.get("comments", 0) or 0)
            pub_dt = str(p.get("published_at", ""))[:10] or "—"
            ta5.caption(f"📅 {pub_dt}")
            st.divider()

        # Log stats
        st.markdown("#### 📝 Log Stats for a Post")
        with st.form("log_stats_form"):
            lp_id = st.selectbox("Select Post",
                                 [p["id"] for p in posted_posts],
                                 format_func=lambda x: next(p["title"] for p in posted_posts if p["id"] == x))
            ls1, ls2, ls3, ls4 = st.columns(4)
            lv = ls1.number_input("Views",    min_value=0, step=1)
            ll = ls2.number_input("Likes",    min_value=0, step=1)
            lc = ls3.number_input("Comments", min_value=0, step=1)
            lsh = ls4.number_input("Shares",  min_value=0, step=1)
            if st.form_submit_button("💾 Save Stats", type="primary"):
                conn = get_conn()
                db_exec(conn,
                    "UPDATE smm_posts SET views=?, likes=?, comments=?, shares=? WHERE id=?",
                    (lv, ll, lc, lsh, lp_id))
                conn.commit(); conn.close()
                st.success("✅ Stats updated!")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — AI STUDIO
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("### 🤖 AI Content Studio")
    st.caption("Let Claude write captions, generate hooks, build calendars, suggest hashtags, and more.")

    ai_task = st.selectbox("What do you want AI to help with?", [
        "Write captions for all 5 platforms",
        "Generate viral hook ideas",
        "Build a 30-day content calendar",
        "Suggest hashtag strategy",
        "Write a TikTok/Reel script",
        "Generate post ideas from a topic",
        "Repurpose a long-form idea into shorts",
        "Write an Instagram carousel script",
        "Craft a Twitter/X thread",
        "Analyze what's working (based on stats)",
        "Custom prompt",
    ])

    context_base = (
        "You are a social media strategist helping Darrian Belcher grow his personal brand "
        "(bookofdarrian) and his business brand (Peach State Savings — personal finance & budgeting). "
        "He posts on YouTube Shorts, TikTok, Instagram Reels, Facebook, and Twitter/X. "
        "His niche: personal finance, budgeting, Atlanta lifestyle, content creation, and entrepreneurship."
    )

    if ai_task == "Write captions for all 5 platforms":
        ai_topic = st.text_input("What is the post about? *", placeholder="e.g., How I saved $500 in one month")
        ai_brand = st.selectbox("Brand / Account", ["bookofdarrian (personal)", "Peach State Savings (business)"])
        if st.button("✨ Generate All 5 Captions", type="primary") and ai_topic:
            with st.spinner("Generating captions for all platforms..."):
                prompt = (
                    f"{context_base}\n\nBrand: {ai_brand}\nTopic: {ai_topic}\n\n"
                    f"Write optimized captions for ALL 5 platforms:\n"
                    f"1. YouTube Shorts (max 5000 chars — detailed, with chapters if needed)\n"
                    f"2. TikTok (max 2200 chars — casual, trendy, use hooks)\n"
                    f"3. Instagram Reels (max 2200 chars — story-driven, CTA)\n"
                    f"4. Facebook (conversational, community-focused, ask a question)\n"
                    f"5. Twitter/X (max 280 chars — punchy; OR a 5-tweet thread)\n\n"
                    f"Label each clearly. Include relevant hashtags for each platform."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Generate viral hook ideas":
        ai_topic  = st.text_input("Topic or niche")
        ai_count  = st.slider("How many hooks?", 5, 20, 10)
        ai_style  = st.multiselect("Hook styles", ["Story", "Controversy", "Shocking stat", "Curiosity gap", "Relatability", "Challenge", "How-to"], default=["Story", "Curiosity gap"])
        if st.button("🎣 Generate Hooks", type="primary") and ai_topic:
            with st.spinner("Generating hooks..."):
                prompt = (
                    f"{context_base}\nTopic: {ai_topic}\n\n"
                    f"Generate {ai_count} viral social media hooks using styles: {', '.join(ai_style)}. "
                    f"Each hook should be under 15 seconds when spoken aloud (~35 words max). "
                    f"Make them immediately scroll-stopping. Label the style used."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Build a 30-day content calendar":
        freq_map = st.selectbox("Posting frequency", ["Daily (all platforms)", "5x/week", "3x/week", "1x/week per platform"])
        acct_sel = st.multiselect("For accounts", ["bookofdarrian (personal)", "Peach State Savings (business)"],
                                  default=["Peach State Savings (business)"])
        themes   = st.text_input("Recurring themes/series", placeholder="e.g., Money Monday, Story Time, Tips Tuesday")
        if st.button("📅 Build Calendar", type="primary"):
            with st.spinner("Building 30-day calendar..."):
                prompt = (
                    f"{context_base}\nAccounts: {', '.join(acct_sel)}\n\n"
                    f"Build a 30-day social media content calendar posting {freq_map}. "
                    f"{'Include themes: ' + themes if themes else ''} "
                    f"Platforms: YouTube Shorts, TikTok, Instagram Reels, Facebook, Twitter/X. "
                    f"Format as a table: Day | Date | Platform | Title | Post Type | Caption Hook. "
                    f"Mix educational, entertaining, and personal content."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Suggest hashtag strategy":
        hs_plat  = st.selectbox("Platform", PLATFORMS)
        hs_niche = st.text_input("Niche / topic", placeholder="e.g., personal finance, Atlanta, sneakers")
        hs_size  = st.selectbox("Account size", ["Under 1k", "1k-10k", "10k-100k", "100k+"])
        if st.button("🏷️ Generate Hashtag Strategy", type="primary") and hs_niche:
            with st.spinner("Building hashtag strategy..."):
                prompt = (
                    f"{context_base}\n\n"
                    f"Build a {hs_plat} hashtag strategy for niche: {hs_niche} (account size: {hs_size}).\n"
                    f"Include:\n1. 5 mega hashtags (1M+ posts) — for reach\n"
                    f"2. 10 mid-tier hashtags (100k-1M) — for discovery\n"
                    f"3. 10 micro hashtags (under 100k) — for community\n"
                    f"4. A ready-to-copy set of 25-30 hashtags\n"
                    f"5. Tips specific to {hs_plat}'s algorithm."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Write a TikTok/Reel script":
        tk_topic = st.text_input("Video topic *")
        tk_len   = st.selectbox("Target length", ["15 sec", "30 sec", "60 sec", "3 min"])
        tk_brand = st.selectbox("Brand", ["bookofdarrian (personal)", "Peach State Savings (business)"])
        if st.button("🎬 Write Script", type="primary") and tk_topic:
            with st.spinner("Writing script..."):
                prompt = (
                    f"{context_base}\nBrand: {tk_brand}\n\n"
                    f"Write a {tk_len} TikTok/Instagram Reel script about: {tk_topic}.\n"
                    f"Format:\n- Hook (first 3 seconds — spoken + visual direction)\n"
                    f"- Main content (bullet points with visual cues)\n"
                    f"- CTA (last 3-5 seconds)\n"
                    f"Include on-screen text suggestions and any trending audio notes."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Generate post ideas from a topic":
        gi_topic = st.text_input("Topic / keyword")
        gi_count = st.slider("Number of ideas", 5, 30, 15)
        gi_plats = st.multiselect("Platforms to target", PLATFORMS, default=PLATFORMS)
        if st.button("💡 Generate Ideas", type="primary") and gi_topic:
            with st.spinner("Generating..."):
                prompt = (
                    f"{context_base}\n\nTopic: {gi_topic}\nPlatforms: {', '.join(gi_plats)}\n\n"
                    f"Generate {gi_count} social media post ideas. For each include:\n"
                    f"- Platform\n- Format (short, reel, carousel, thread, etc.)\n"
                    f"- Title / hook\n- Brief description\n- Why it would perform well."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Repurpose a long-form idea into shorts":
        lf_topic = st.text_area("Paste your long-form content, video script, or blog post idea", height=150)
        if st.button("✂️ Repurpose into Shorts", type="primary") and lf_topic:
            with st.spinner("Repurposing..."):
                prompt = (
                    f"{context_base}\n\n"
                    f"Take this long-form content and repurpose it into short-form content for ALL platforms:\n\n"
                    f"Long-form content:\n{lf_topic}\n\n"
                    f"Create:\n1. 3 TikTok/Reel hooks (15-30 sec each)\n"
                    f"2. 5 Twitter/X posts or a thread\n"
                    f"3. 1 Instagram carousel (10 slides with text for each slide)\n"
                    f"4. 1 Facebook post (community angle)\n"
                    f"5. 1 YouTube Shorts concept"
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Write an Instagram carousel script":
        ic_topic = st.text_input("Carousel topic *")
        ic_slides = st.slider("Number of slides", 3, 15, 7)
        ic_brand  = st.selectbox("Brand", ["bookofdarrian (personal)", "Peach State Savings (business)"])
        if st.button("📊 Write Carousel", type="primary") and ic_topic:
            with st.spinner("Writing carousel script..."):
                prompt = (
                    f"{context_base}\nBrand: {ic_brand}\n\n"
                    f"Write a {ic_slides}-slide Instagram carousel about: {ic_topic}.\n"
                    f"For each slide:\n- Slide number + headline (max 8 words)\n"
                    f"- Body text (max 50 words)\n- Visual suggestion\n\n"
                    f"Slide 1 = scroll-stopping cover. Last slide = CTA. Make it save-worthy."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Craft a Twitter/X thread":
        tt_topic  = st.text_input("Thread topic *")
        tt_tweets = st.slider("Number of tweets", 5, 20, 10)
        if st.button("🧵 Write Thread", type="primary") and tt_topic:
            with st.spinner("Writing thread..."):
                prompt = (
                    f"{context_base}\n\n"
                    f"Write a {tt_tweets}-tweet Twitter/X thread about: {tt_topic}.\n"
                    f"Tweet 1: Hook — bold claim or question (max 280 chars)\n"
                    f"Tweets 2-{tt_tweets-1}: Value-packed points (each under 280 chars)\n"
                    f"Last tweet: CTA — follow, comment, or share.\n"
                    f"Number each tweet. Make it viral-worthy."
                )
                res = _ask_ai(prompt)
            st.markdown(res)

    elif ai_task == "Analyze what's working (based on stats)":
        if not posted_posts:
            st.info("No posted content with stats yet.")
        else:
            top_n = sorted(posted_posts, key=lambda x: x.get("views", 0) or 0, reverse=True)[:10]
            stats_summary = "\n".join([
                f"- '{p['title']}': {p.get('views',0)} views, {p.get('likes',0)} likes, "
                f"{p.get('comments',0)} comments, type={p.get('post_type')}"
                for p in top_n
            ])
            if st.button("📊 Analyze Performance", type="primary"):
                with st.spinner("Analyzing..."):
                    prompt = (
                        f"{context_base}\n\n"
                        f"Analyze this social media performance data and give actionable insights:\n\n"
                        f"{stats_summary}\n\n"
                        f"Tell me:\n1. What content types are performing best\n"
                        f"2. What patterns you see in top performers\n"
                        f"3. What I should do more of\n"
                        f"4. What to stop or change\n"
                        f"5. 5 specific post ideas based on what's working"
                    )
                    res = _ask_ai(prompt)
                st.markdown(res)

    else:
        custom_prompt = st.text_area("Your prompt", height=150,
                                     placeholder="Ask AI anything about social media strategy...")
        if st.button("✨ Ask AI", type="primary") and custom_prompt:
            with st.spinner("Thinking..."):
                res = _ask_ai(f"{context_base}\n\n{custom_prompt}")
            st.markdown(res)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_accounts:
    st.markdown("### 👤 Manage Accounts")
    st.caption("Add and manage your personal and business accounts across all platforms.")

    with st.expander("➕ Add New Account"):
        with st.form("add_account_form", clear_on_submit=True):
            aa1, aa2, aa3 = st.columns(3)
            acc_name    = aa1.text_input("Display Name *", placeholder="bookofdarrian")
            acc_platform = aa2.selectbox("Platform", PLATFORMS)
            acc_type    = aa3.selectbox("Account Type", ACCOUNT_TYPES)
            ab1, ab2, ab3 = st.columns(3)
            acc_handle  = ab1.text_input("Handle / Username", placeholder="@bookofdarrian")
            acc_url     = ab2.text_input("Profile URL", placeholder="https://tiktok.com/@...")
            acc_followers = ab3.number_input("Follower Count", min_value=0, step=100)
            acc_color   = st.color_picker("Brand Color", PLATFORM_COLORS.get(acc_platform, "#1da1f2"))
            acc_notes   = st.text_area("Notes", height=60)
            if st.form_submit_button("➕ Add Account", type="primary") and acc_name.strip():
                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO smm_accounts "
                    "(display_name, platform, account_type, handle, profile_url, follower_count, color, notes) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (acc_name.strip(), acc_platform, acc_type, acc_handle.strip(),
                     acc_url.strip(), acc_followers, acc_color, acc_notes.strip()))
                conn.commit(); conn.close()
                st.success(f"✅ Added: {acc_name.strip()} on {acc_platform}")
                st.rerun()

    # Group by account type
    for acc_type_group in ["personal", "business"]:
        group_accs = [a for a in accounts if a.get("account_type") == acc_type_group]
        if not group_accs:
            continue
        st.markdown(f"#### {'👤 Personal' if acc_type_group == 'personal' else '🏢 Business'} Accounts")

        # Group further by display_name
        names = list(dict.fromkeys([a["display_name"] for a in group_accs]))
        for dname in names:
            name_accs = [a for a in group_accs if a["display_name"] == dname]
            st.markdown(f"**{dname}**")
            acol_count = min(len(name_accs), 5)
            acc_cols = st.columns(acol_count)
            for idx, acc in enumerate(name_accs):
                color = acc.get("color", "#607d8b")
                icon  = PLATFORM_ICONS.get(acc["platform"], "📱")
                with acc_cols[idx % acol_count]:
                    st.markdown(
                        f'<div style="border:1px solid {color};border-radius:8px;padding:10px;text-align:center">'
                        f'<div style="font-size:24px">{icon}</div>'
                        f'<div style="font-weight:bold;color:{color}">{acc["platform"]}</div>'
                        f'<div style="color:#aaa;font-size:11px">{acc.get("handle","")}</div>'
                        f'<div style="font-size:11px">{(acc.get("follower_count") or 0):,} followers</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("🗑️", key=f"del_acc_{acc['id']}"):
                        conn = get_conn()
                        db_exec(conn, "DELETE FROM smm_accounts WHERE id=?", (acc["id"],))
                        conn.commit(); conn.close()
                        st.rerun()
            st.divider()

    # Update follower counts
    with st.expander("📊 Update Follower Counts"):
        with st.form("update_followers_form"):
            uf_id = st.selectbox("Account",
                                 [a["id"] for a in accounts],
                                 format_func=lambda x: f"{account_map[x]['display_name']} — {account_map[x]['platform']} ({account_map[x]['handle']})")
            uf_count = st.number_input("New Follower Count", min_value=0, step=1)
            if st.form_submit_button("💾 Update", type="primary"):
                conn = get_conn()
                db_exec(conn, "UPDATE smm_accounts SET follower_count=? WHERE id=?", (uf_count, uf_id))
                conn.commit(); conn.close()
                st.success("✅ Updated!")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — CAMPAIGNS
# ══════════════════════════════════════════════════════════════════════════════
with tab_campaigns:
    st.markdown("### 🎯 Campaigns & Series")
    st.caption("Group related posts into campaigns or content series for tracking and planning.")

    with st.expander("➕ Create New Campaign"):
        with st.form("add_campaign_form", clear_on_submit=True):
            ca1, ca2 = st.columns(2)
            camp_name  = ca1.text_input("Campaign Name *", placeholder="March Finance Tips Series")
            camp_goal  = ca2.text_input("Goal", placeholder="Grow to 5k followers on TikTok")
            camp_desc  = st.text_area("Description", height=60)
            cd1, cd2, cd3 = st.columns(3)
            camp_start = cd1.date_input("Start Date", value=date.today())
            camp_end   = cd2.date_input("End Date",   value=date.today() + timedelta(days=30))
            camp_color = cd3.color_picker("Color", "#e040fb")
            if st.form_submit_button("➕ Create Campaign", type="primary") and camp_name.strip():
                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO smm_campaigns (name, description, goal, start_date, end_date, color) "
                    "VALUES (?,?,?,?,?,?)",
                    (camp_name.strip(), camp_desc.strip(), camp_goal.strip(),
                     camp_start.isoformat(), camp_end.isoformat(), camp_color))
                conn.commit(); conn.close()
                st.success(f"✅ Campaign created: {camp_name.strip()}")
                st.rerun()

    if not campaigns:
        st.info("No campaigns yet. Create one above!")
    else:
        for camp in campaigns:
            color = camp.get("color", "#e040fb")
            camp_posts = [p for p in all_posts if p.get("campaign") == camp["name"]]
            posted_in  = len([p for p in camp_posts if p.get("status") == "posted"])
            sched_in   = len([p for p in camp_posts if p.get("status") == "scheduled"])
            draft_in   = len([p for p in camp_posts if p.get("status") == "draft"])

            st.markdown(
                f'<div style="border-left:4px solid {color};padding-left:12px">'
                f'<b style="font-size:15px">{camp["name"]}</b></div>',
                unsafe_allow_html=True,
            )
            if camp.get("description"):
                st.caption(camp["description"])
            if camp.get("goal"):
                st.caption(f"🎯 Goal: {camp['goal']}")
            sd = str(camp.get("start_date",""))[:10] or "—"
            ed = str(camp.get("end_date",""))[:10] or "—"
            st.caption(f"📅 {sd} → {ed}")

            cm1, cm2, cm3, cm4 = st.columns(4)
            cm1.metric("Total Posts", len(camp_posts))
            cm2.metric("Posted",      posted_in)
            cm3.metric("Scheduled",   sched_in)
            cm4.metric("Drafts",      draft_in)

            if st.button("🗑️ Delete Campaign", key=f"del_camp_{camp['id']}"):
                conn = get_conn()
                db_exec(conn, "DELETE FROM smm_campaigns WHERE id=?", (camp["id"],))
                conn.commit(); conn.close()
                st.rerun()
            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — HASHTAGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_hashtags:
    st.markdown("### 🏷️ Hashtag Sets")
    st.caption("Save ready-to-use hashtag sets per niche/platform. Use {{HASHTAGS}} in captions to auto-insert.")

    with st.expander("➕ Create New Hashtag Set"):
        with st.form("add_hashtag_form", clear_on_submit=True):
            hf1, hf2 = st.columns(2)
            hs_name  = hf1.text_input("Set Name *", placeholder="Personal Finance")
            hs_plats = hf2.multiselect("Platforms", PLATFORMS)
            hs_tags  = st.text_area("Hashtags *", height=100,
                                    placeholder="#personalfinance #budgeting #moneytips ...")
            if st.form_submit_button("💾 Save Set", type="primary") and hs_name.strip() and hs_tags.strip():
                conn = get_conn()
                db_exec(conn, "INSERT INTO smm_hashtag_sets (name, platforms, hashtags) VALUES (?,?,?)",
                        (hs_name.strip(), ",".join(hs_plats), hs_tags.strip()))
                conn.commit(); conn.close()
                st.success(f"✅ Saved: {hs_name.strip()}")
                st.rerun()

    ht_sets = _load_hashtag_sets()
    if not ht_sets:
        st.info("No hashtag sets yet.")
    else:
        for ht in ht_sets:
            ht1, ht2 = st.columns([4, 1])
            ht1.markdown(f"**{ht['name']}**")
            if ht.get("platforms"):
                ht1.caption(f"Platforms: {ht['platforms']}")
            tag_count = len(ht.get("hashtags","").split()) if ht.get("hashtags") else 0
            ht2.caption(f"{tag_count} tags")
            st.text_area("Tags (copy-ready)", value=ht.get("hashtags",""), height=80,
                         key=f"ht_view_{ht['id']}", disabled=False)
            if st.button("🗑️ Delete", key=f"del_ht_{ht['id']}"):
                conn = get_conn()
                db_exec(conn, "DELETE FROM smm_hashtag_sets WHERE id=?", (ht["id"],))
                conn.commit(); conn.close()
                st.rerun()
            st.divider()

    # Platform character limits reference
    st.markdown("#### 📏 Platform Character Limits")
    lim_data = {
        "Platform": ["Twitter/X", "Instagram", "TikTok", "Facebook", "YouTube Shorts"],
        "Caption Limit": ["280 chars", "2,200 chars", "2,200 chars", "63,206 chars", "5,000 chars"],
        "Hashtag Sweet Spot": ["2-3", "5-11", "3-5", "1-2", "none needed"],
        "Best Posting Time": ["8-10am, 7-9pm", "6-9am, 7-9pm", "7am, 7pm", "1-4pm", "anytime"],
    }
    st.dataframe(lim_data, use_container_width=True)
