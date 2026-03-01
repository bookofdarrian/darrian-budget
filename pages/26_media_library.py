"""
Media Library — Page 26
Track, organize and discover music, sounds, and media assets for content creation.
"""
import streamlit as st
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="🎵 Media Library — Peach State Savings",
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
        CREATE TABLE IF NOT EXISTS media_items (
            id {ai},
            title TEXT NOT NULL,
            artist TEXT DEFAULT '',
            album TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            mood TEXT DEFAULT '',
            media_type TEXT DEFAULT 'music',
            source TEXT DEFAULT '',
            url TEXT DEFAULT '',
            bpm INTEGER DEFAULT 0,
            key_sig TEXT DEFAULT '',
            duration_sec INTEGER DEFAULT 0,
            tags TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            rating INTEGER DEFAULT 0,
            used_in TEXT DEFAULT '',
            favorite INTEGER DEFAULT 0,
            created_at TEXT {ts}
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS media_playlists (
            id {ai},
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#ffa726',
            created_at TEXT {ts}
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS media_playlist_items (
            id {ai},
            playlist_id INTEGER NOT NULL,
            media_id INTEGER NOT NULL,
            sort_order INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

_ensure_tables()

# ── Constants ──────────────────────────────────────────────────────────────────
MEDIA_TYPES = ["music", "sound effect", "voiceover", "podcast", "sample", "ambient", "other"]
GENRES = [
    "Hip-Hop", "R&B", "Pop", "Electronic", "Lo-Fi", "Jazz", "Soul",
    "Gospel", "Trap", "Drill", "Afrobeats", "House", "Cinematic",
    "Ambient", "Rock", "Country", "Other"
]
MOODS = [
    "Energetic", "Chill", "Motivational", "Sad", "Happy", "Dark",
    "Uplifting", "Romantic", "Aggressive", "Peaceful", "Mysterious", "Other"
]
SOURCES = ["YouTube", "Spotify", "SoundCloud", "Epidemic Sound", "Artlist",
           "Pixabay", "Free Music Archive", "Owned / Original", "Other"]
RATINGS = [0, 1, 2, 3, 4, 5]


# ── Helpers ────────────────────────────────────────────────────────────────────
def _load_items(search="", media_type=None, genre=None, mood=None,
                favorites_only=False, tag=None):
    conn = get_conn()
    where, params = [], []
    if favorites_only:
        where.append("favorite=1")
    if media_type and media_type != "All":
        where.append("media_type=?")
        params.append(media_type)
    if genre and genre != "All":
        where.append("genre=?")
        params.append(genre)
    if mood and mood != "All":
        where.append("mood=?")
        params.append(mood)
    if tag:
        where.append("tags LIKE ?")
        params.append(f"%{tag}%")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    c = db_exec(conn,
        f"SELECT * FROM media_items {clause} ORDER BY favorite DESC, rating DESC, created_at DESC",
        tuple(params))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    results = [dict(zip(cols, r)) for r in rows]
    if search:
        sl = search.lower()
        results = [r for r in results
                   if sl in r.get("title", "").lower()
                   or sl in r.get("artist", "").lower()
                   or sl in r.get("tags", "").lower()
                   or sl in r.get("notes", "").lower()]
    return results


def _load_playlists():
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM media_playlists ORDER BY name ASC")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _playlist_items(playlist_id):
    conn = get_conn()
    c = db_exec(conn,
        "SELECT m.* FROM media_items m "
        "JOIN media_playlist_items p ON m.id=p.media_id "
        "WHERE p.playlist_id=? ORDER BY p.sort_order ASC",
        (playlist_id,))
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def _star_html(rating):
    return "⭐" * int(rating) + "☆" * (5 - int(rating))


def _duration_str(secs):
    if not secs:
        return "—"
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"


def _all_tags():
    conn = get_conn()
    c = db_exec(conn, "SELECT tags FROM media_items WHERE tags != ''")
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
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI Error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("🎵 Media Library")
st.caption("Your personal music & sound catalog for content creation — organized, searchable, AI-powered.")

all_items = _load_items()
favorites = [i for i in all_items if i.get("favorite")]
playlists = _load_playlists()
all_tags  = _all_tags()
total_dur = sum(i.get("duration_sec", 0) for i in all_items)
total_min = total_dur // 60

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Tracks",  len(all_items))
m2.metric("Favorites",     len(favorites))
m3.metric("Playlists",     len(playlists))
m4.metric("Total Runtime", f"{total_min} min")
m5.metric("Tags",          len(all_tags))

st.divider()

tab_library, tab_add, tab_playlists, tab_ai, tab_spotify, tab_apple = st.tabs([
    "📚 Library", "➕ Add Track", "🎧 Playlists", "🤖 AI Music Tools", "🎵 Spotify", "🍎 Apple Music"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
with tab_library:
    f1, f2, f3, f4, f5 = st.columns([3, 2, 2, 2, 1])
    with f1:
        search_q = st.text_input("Search", placeholder="Title, artist, tag...",
                                  label_visibility="collapsed")
    with f2:
        ft_type = st.selectbox("Type", ["All"] + MEDIA_TYPES, label_visibility="collapsed")
    with f3:
        ft_genre = st.selectbox("Genre", ["All"] + GENRES, label_visibility="collapsed")
    with f4:
        ft_mood = st.selectbox("Mood", ["All"] + MOODS, label_visibility="collapsed")
    with f5:
        favs_only = st.checkbox("⭐ Favs", value=False)

    items = _load_items(
        search=search_q,
        media_type=ft_type if ft_type != "All" else None,
        genre=ft_genre if ft_genre != "All" else None,
        mood=ft_mood if ft_mood != "All" else None,
        favorites_only=favs_only,
    )

    st.caption(f"{len(items)} track(s)")

    if not items:
        st.info("No tracks found. Add some in the ➕ Add Track tab!")
    else:
        for item in items:
            with st.container():
                c1, c2, c3, c4 = st.columns([5, 3, 2, 2])
                fav_icon = "⭐" if item.get("favorite") else "☆"
                c1.markdown(
                    f"**{fav_icon} {item['title']}**  \n"
                    f"<span style='color:#aaa;font-size:12px'>"
                    f"{item.get('artist', 'Unknown Artist')} · "
                    f"{item.get('album', '') or item.get('source', '')} · "
                    f"{item.get('media_type', '').title()}</span>",
                    unsafe_allow_html=True
                )
                if item.get("notes"):
                    c1.caption(item["notes"][:80])

                bpm_str = f"🥁 {item['bpm']} BPM" if item.get("bpm") else ""
                key_str = f"🎵 {item['key_sig']}" if item.get("key_sig") else ""
                c2.markdown(
                    f"<span style='color:#aaa;font-size:12px'>"
                    f"🎸 {item.get('genre', '—')} &nbsp; 😌 {item.get('mood', '—')}<br>"
                    f"⏱️ {_duration_str(item.get('duration_sec', 0))} &nbsp; {bpm_str} &nbsp; {key_str}"
                    f"</span>",
                    unsafe_allow_html=True
                )
                if item.get("tags"):
                    tag_list = [t.strip() for t in item["tags"].split(",") if t.strip()]
                    tag_html = " ".join(
                        f'<span style="background:#333;color:#aaa;padding:1px 5px;'
                        f'border-radius:6px;font-size:10px">{t}</span>'
                        for t in tag_list[:5]
                    )
                    c2.markdown(tag_html, unsafe_allow_html=True)

                c3.markdown(_star_html(item.get("rating", 0)))
                if item.get("url"):
                    c3.markdown(f"[🔗 Open]({item['url']})")
                if item.get("used_in"):
                    c3.caption(f"📹 {item['used_in'][:40]}")

                with c4:
                    fav_label = "★ Unfav" if item.get("favorite") else "☆ Fav"
                    if st.button(fav_label, key=f"fav_{item['id']}"):
                        conn = get_conn()
                        db_exec(conn, "UPDATE media_items SET favorite=? WHERE id=?",
                                (0 if item.get("favorite") else 1, item["id"]))
                        conn.commit()
                        conn.close()
                        st.rerun()

                    new_rating = st.selectbox(
                        "", RATINGS,
                        index=item.get("rating", 0),
                        key=f"rate_{item['id']}",
                        label_visibility="collapsed",
                        format_func=lambda x: "⭐" * x if x else "No rating"
                    )
                    if new_rating != item.get("rating", 0):
                        conn = get_conn()
                        db_exec(conn, "UPDATE media_items SET rating=? WHERE id=?",
                                (new_rating, item["id"]))
                        conn.commit()
                        conn.close()
                        st.rerun()

                    if st.button("🗑️", key=f"del_{item['id']}"):
                        conn = get_conn()
                        db_exec(conn, "DELETE FROM media_items WHERE id=?", (item["id"],))
                        conn.commit()
                        conn.close()
                        st.rerun()

            st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ADD TRACK
# ══════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.markdown("### ➕ Add Track to Library")
    with st.form("add_track_form", clear_on_submit=True):
        a1, a2 = st.columns(2)
        new_title  = a1.text_input("Title *", placeholder="Song / sound name")
        new_artist = a2.text_input("Artist / Creator", placeholder="Artist name")

        b1, b2, b3 = st.columns(3)
        new_type  = b1.selectbox("Media Type", MEDIA_TYPES)
        new_genre = b2.selectbox("Genre", GENRES)
        new_mood  = b3.selectbox("Mood", MOODS)

        c1, c2, c3, c4 = st.columns(4)
        new_bpm      = c1.number_input("BPM", min_value=0, max_value=300, value=0)
        new_key      = c2.text_input("Key", placeholder="e.g. C Major")
        new_duration = c3.number_input("Duration (seconds)", min_value=0, value=0)
        new_rating   = c4.selectbox("Rating", RATINGS,
                                     format_func=lambda x: "⭐" * x if x else "Unrated")

        d1, d2 = st.columns(2)
        new_source = d1.selectbox("Source", SOURCES)
        new_album  = d2.text_input("Album / EP", placeholder="Album name (optional)")

        new_url   = st.text_input("URL / Link", placeholder="YouTube, Spotify, SoundCloud link...")
        new_tags  = st.text_input("Tags", placeholder="chill, vlog, study, intro (comma separated)")
        new_used  = st.text_input("Used In", placeholder="Which video/project?")
        new_notes = st.text_area("Notes", height=80, placeholder="Any notes about this track...")
        new_fav   = st.checkbox("⭐ Mark as Favorite")

        if st.form_submit_button("💾 Add to Library", type="primary", use_container_width=True):
            if new_title.strip():
                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO media_items "
                    "(title,artist,album,genre,mood,media_type,source,url,bpm,key_sig,"
                    "duration_sec,tags,notes,rating,used_in,favorite) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (new_title.strip(), new_artist.strip(), new_album.strip(),
                     new_genre, new_mood, new_type, new_source, new_url.strip(),
                     new_bpm, new_key.strip(), new_duration, new_tags.strip(),
                     new_notes.strip(), new_rating, new_used.strip(),
                     1 if new_fav else 0))
                conn.commit()
                conn.close()
                st.success(f"✅ Added: {new_title.strip()}")
                st.rerun()
            else:
                st.error("Title is required.")

    st.divider()
    st.markdown("### 🔗 Quick Add from URL")
    st.caption("Paste a link and tag it fast.")
    with st.form("quick_add_form", clear_on_submit=True):
        q_url    = st.text_input("URL *", placeholder="https://youtube.com/watch?v=...")
        q_title  = st.text_input("Title *", placeholder="Track name")
        q_artist = st.text_input("Artist")
        q1, q2, q3 = st.columns(3)
        q_genre = q1.selectbox("Genre", GENRES, key="q_genre")
        q_mood  = q2.selectbox("Mood",  MOODS,  key="q_mood")
        q_type  = q3.selectbox("Type",  MEDIA_TYPES, key="q_type")
        q_tags  = st.text_input("Tags", placeholder="vlog, background, energetic")

        if st.form_submit_button("⚡ Quick Add", type="primary", use_container_width=True):
            if q_url.strip() and q_title.strip():
                conn = get_conn()
                db_exec(conn,
                    "INSERT INTO media_items "
                    "(title,artist,genre,mood,media_type,url,tags,source) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (q_title.strip(), q_artist.strip(), q_genre, q_mood,
                     q_type, q_url.strip(), q_tags.strip(), "URL Import"))
                conn.commit()
                conn.close()
                st.success(f"✅ Quick added: {q_title.strip()}")
                st.rerun()
            else:
                st.error("URL and Title are required.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PLAYLISTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_playlists:
    st.markdown("### 🎧 Playlists")

    with st.expander("➕ Create New Playlist"):
        with st.form("create_playlist_form", clear_on_submit=True):
            p1, p2 = st.columns([4, 2])
            pl_name  = p1.text_input("Playlist Name *",
                                      placeholder="e.g., Vlog Beats, Intros, Study Music")
            pl_color = p2.color_picker("Color", "#ffa726")
            pl_desc  = st.text_area("Description", height=60,
                                     placeholder="What is this playlist for?")
            if st.form_submit_button("✅ Create Playlist", type="primary"):
                if pl_name.strip():
                    conn = get_conn()
                    db_exec(conn,
                        "INSERT INTO media_playlists (name, description, color) VALUES (?,?,?)",
                        (pl_name.strip(), pl_desc.strip(), pl_color))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Created: {pl_name}")
                    st.rerun()

    playlists = _load_playlists()
    if not playlists:
        st.info("No playlists yet. Create one above!")
    else:
        for pl in playlists:
            color     = pl.get("color", "#ffa726")
            pl_tracks = _playlist_items(pl["id"])
            pl_min    = sum(t.get("duration_sec", 0) for t in pl_tracks) // 60

            with st.expander(
                f"**{pl['name']}** — {len(pl_tracks)} tracks · {pl_min} min",
                expanded=False
            ):
                st.markdown(
                    f'<div style="border-left:3px solid {color};padding-left:10px">'
                    f'{pl.get("description", "")}</div>',
                    unsafe_allow_html=True
                )
                st.markdown("")

                all_ids = [(i["id"], i["title"]) for i in all_items]
                if all_ids:
                    with st.form(f"add_to_pl_{pl['id']}", clear_on_submit=True):
                        sel_track = st.selectbox(
                            "Add track",
                            [x[0] for x in all_ids],
                            format_func=lambda x: dict(all_ids).get(x, "?"),
                            key=f"sel_pl_{pl['id']}"
                        )
                        if st.form_submit_button("➕ Add to Playlist", use_container_width=True):
                            conn = get_conn()
                            existing = db_exec(conn,
                                "SELECT id FROM media_playlist_items "
                                "WHERE playlist_id=? AND media_id=?",
                                (pl["id"], sel_track)).fetchone()
                            if not existing:
                                db_exec(conn,
                                    "INSERT INTO media_playlist_items "
                                    "(playlist_id, media_id, sort_order) VALUES (?,?,?)",
                                    (pl["id"], sel_track, len(pl_tracks) + 1))
                                conn.commit()
                            conn.close()
                            st.rerun()

                if not pl_tracks:
                    st.caption("No tracks yet. Add some above!")
                else:
                    for idx, track in enumerate(pl_tracks, 1):
                        tc1, tc2, tc3 = st.columns([5, 3, 1])
                        tc1.markdown(
                            f"**{idx}. {track['title']}** · {track.get('artist', '')}"
                        )
                        tc2.caption(
                            f"{track.get('genre', '—')} · "
                            f"{_duration_str(track.get('duration_sec', 0))}"
                        )
                        if tc3.button("✕", key=f"rm_pl_{pl['id']}_{track['id']}"):
                            conn = get_conn()
                            db_exec(conn,
                                "DELETE FROM media_playlist_items "
                                "WHERE playlist_id=? AND media_id=?",
                                (pl["id"], track["id"]))
                            conn.commit()
                            conn.close()
                            st.rerun()

                st.markdown("")
                if st.button("🗑️ Delete Playlist", key=f"del_pl_{pl['id']}"):
                    conn = get_conn()
                    db_exec(conn,
                        "DELETE FROM media_playlist_items WHERE playlist_id=?", (pl["id"],))
                    db_exec(conn, "DELETE FROM media_playlists WHERE id=?", (pl["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI MUSIC TOOLS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("### 🤖 AI Music & Sound Tools")
    st.caption("Use Claude to find music recommendations, write briefs, and curate vibes for your content.")

    ai_task = st.selectbox("What do you need?", [
        "Recommend music for a specific vibe / content type",
        "Suggest tracks from my library for a video",
        "Build a content soundtrack strategy",
        "Write a music brief for a video editor",
        "Find royalty-free music sources for my niche",
        "Suggest sound design ideas for a scene",
        "Custom prompt",
    ])

    lib_summary = (
        f"The user has {len(all_items)} tracks in their media library. "
        f"Genres: {', '.join(set(i.get('genre','') for i in all_items if i.get('genre'))) or 'various'}. "
        f"Moods: {', '.join(set(i.get('mood','') for i in all_items if i.get('mood'))) or 'various'}. "
        f"Top tracks: {', '.join(i['title'] for i in all_items[:5])}."
    )
    creator_ctx = (
        "The user is Darrian Belcher, a content creator with three channels: "
        "bookofdarrian (lifestyle/culture/finance), Peach State Savings (personal finance), "
        "and a productivity app (To-Do). They make YouTube videos and short-form content."
    )

    if ai_task == "Recommend music for a specific vibe / content type":
        vibe_in    = st.text_input("Describe the vibe or content type",
                                    placeholder="e.g., motivational finance video, chill study vlog")
        content_in = st.selectbox("Content format",
                                   ["YouTube video", "YouTube Short", "TikTok",
                                    "Instagram Reel", "Podcast", "Intro / Outro", "Background music"])
        if st.button("🎵 Get Recommendations", type="primary") and vibe_in:
            with st.spinner("Finding the perfect sound..."):
                prompt = (
                    f"{creator_ctx}\n{lib_summary}\n\n"
                    f"Recommend 8-10 specific songs, artists, or tracks for a {content_in} "
                    f"with this vibe: {vibe_in}. "
                    f"Include: track name, artist, why it fits, where to find it. "
                    f"Mix mainstream tracks and royalty-free options."
                )
                result = _ask_ai(prompt)
            st.markdown(result)

    elif ai_task == "Suggest tracks from my library for a video":
        video_desc = st.text_area("Describe your video", height=100,
                                   placeholder="e.g., 10-minute YouTube video about budgeting for millennials...")
        if st.button("🔍 Match Tracks", type="primary") and video_desc:
            if not all_items:
                st.info("Add some tracks to your library first!")
            else:
                with st.spinner("Matching your library..."):
                    track_list = "\n".join(
                        f"- {i['title']} by {i.get('artist','?')} | "
                        f"{i.get('genre','?')} | {i.get('mood','?')} | "
                        f"{_duration_str(i.get('duration_sec',0))}"
                        for i in all_items[:50]
                    )
                    prompt = (
                        f"{creator_ctx}\n\nMedia library:\n{track_list}\n\n"
                        f"Suggest the best 3-5 tracks for this video:\n{video_desc}\n\n"
                        f"Explain why each fits and where to use it "
                        f"(intro, background, outro, transition)."
                    )
                    result = _ask_ai(prompt)
                st.markdown(result)

    elif ai_task == "Build a content soundtrack strategy":
        channel = st.selectbox("Which channel?",
                                ["bookofdarrian", "Peach State Savings", "To-Do App", "All Channels"])
        if st.button("🗺️ Build Strategy", type="primary"):
            with st.spinner("Building your soundtrack strategy..."):
                prompt = (
                    f"{creator_ctx}\n\n"
                    f"Build a music and sound strategy for the '{channel}' channel. Include:\n"
                    f"1. Signature sound/vibe for this channel\n"
                    f"2. Recommended genres and moods for different video types\n"
                    f"3. Intro/outro music approach\n"
                    f"4. Background music rules (volume levels, energy matching)\n"
                    f"5. 10 specific artist recommendations that fit the brand\n"
                    f"6. Where to legally source music (free + paid options)"
                )
                result = _ask_ai(prompt)
            st.markdown(result)

    elif ai_task == "Write a music brief for a video editor":
        brief_title   = st.text_input("Video title / topic")
        brief_len     = st.selectbox("Video length",
                                      ["1-3 min (Short)", "5-10 min", "10-20 min", "20+ min"])
        brief_tone    = st.text_input("Tone / vibe",
                                       placeholder="e.g., informative but energetic, chill conversational")
        brief_moments = st.text_area("Key moments that need music", height=80,
                                      placeholder="e.g., 0:00 - hype intro, 2:30 - emotional section")
        if st.button("📋 Write Brief", type="primary") and brief_title:
            with st.spinner("Writing music brief..."):
                prompt = (
                    f"{creator_ctx}\n\n"
                    f"Write a detailed music brief for a video editor:\n"
                    f"Title: {brief_title}\nLength: {brief_len}\nTone: {brief_tone}\n"
                    f"Key moments:\n{brief_moments}\n\n"
                    f"Include: overall music direction, track recommendations per section, "
                    f"tempo/energy guidance, volume ducking notes, and transition suggestions. "
                    f"Format as a professional brief."
                )
                result = _ask_ai(prompt)
            st.markdown(result)

    elif ai_task == "Find royalty-free music sources for my niche":
        niche_in = st.text_input("Your content niche",
                                  value="Personal finance / lifestyle / culture")
        budget   = st.selectbox("Budget",
                                  ["Free only", "Under $10/month", "Under $20/month", "No limit"])
        if st.button("🔍 Find Sources", type="primary"):
            with st.spinner("Researching sources..."):
                prompt = (
                    f"{creator_ctx}\n\n"
                    f"Find the best royalty-free music sources for a creator in the "
                    f"'{niche_in}' niche with a budget of '{budget}'. Include:\n"
                    f"1. Top 5-8 platforms with pros, cons, and cost\n"
                    f"2. Best free options with good quality\n"
                    f"3. Specific artists or playlists to bookmark\n"
                    f"4. YouTube-safe vs. full commercial license details\n"
                    f"5. Tips for avoiding copyright strikes"
                )
                result = _ask_ai(prompt)
            st.markdown(result)

    elif ai_task == "Suggest sound design ideas for a scene":
        scene_desc = st.text_area("Describe the scene or moment", height=100,
                                   placeholder="e.g., The big reveal moment where I show my net worth grew by $10k")
        if st.button("🎬 Get Sound Ideas", type="primary") and scene_desc:
            with st.spinner("Thinking about sound design..."):
                prompt = (
                    f"{creator_ctx}\n\n"
                    f"Suggest creative sound design ideas for this scene:\n{scene_desc}\n\n"
                    f"Include: music, sound effects, transition sounds, and audio editing techniques "
                    f"(risers, drops, silence, voice effects) to make this moment hit harder. "
                    f"Be specific and creative."
                )
                result = _ask_ai(prompt)
            st.markdown(result)

    else:
        custom_p = st.text_area("Your prompt", height=150,
                                 placeholder="Ask AI anything about music, sound, content audio...")
        if st.button("✨ Ask AI", type="primary") and custom_p:
            with st.spinner("Thinking..."):
                result = _ask_ai(f"{creator_ctx}\n\n{lib_summary}\n\n{custom_p}")
            st.markdown(result)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — SPOTIFY INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_spotify:
    st.markdown("### 🎵 Spotify Integration")
    st.caption("Import your Spotify playlists and search Spotify tracks — saved directly to your Media Library.")

    # ── Spotify credentials setup ──────────────────────────────────────────────
    from utils.db import set_setting as _set_setting

    sp_client_id     = get_setting("spotify_client_id", "")
    sp_client_secret = get_setting("spotify_client_secret", "")
    sp_redirect_uri  = get_setting("spotify_redirect_uri", "http://127.0.0.1:8501")

    with st.expander("⚙️ Spotify API Setup" + (" ✅" if sp_client_id else " — required first"), expanded=not sp_client_id):
        st.markdown(
            "**How to get your Spotify API credentials (free, 5 minutes):**\n\n"
            "1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)\n"
            "2. Click **Create App** → fill in any name/description\n"
            "3. Set **Redirect URI** to `http://localhost:8501` (for local) or your Railway URL\n"
            "4. Copy your **Client ID** and **Client Secret** below\n"
            "5. Under App Settings → **Redirect URIs**, add the same URL you enter below"
        )
        with st.form("spotify_creds_form"):
            f_id     = st.text_input("Client ID",     value=sp_client_id,     type="default")
            f_secret = st.text_input("Client Secret", value=sp_client_secret, type="password")
            f_redir  = st.text_input("Redirect URI",  value=sp_redirect_uri,
                                      help="Must match exactly what you set in the Spotify Developer Dashboard")
            if st.form_submit_button("💾 Save Credentials", type="primary"):
                _set_setting("spotify_client_id",     f_id.strip())
                _set_setting("spotify_client_secret", f_secret.strip())
                _set_setting("spotify_redirect_uri",  f_redir.strip())
                st.success("✅ Credentials saved!")
                st.rerun()

    if not sp_client_id or not sp_client_secret:
        st.warning("Add your Spotify API credentials above to get started.")
        st.stop()

    # ── Spotify helper functions ───────────────────────────────────────────────
    def _get_spotify_cc():
        """Client Credentials — for search (no user login needed)."""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials
            return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=sp_client_id,
                client_secret=sp_client_secret
            ))
        except Exception as e:
            return None

    def _get_spotify_oauth():
        """Authorization Code — for user's playlists."""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            return SpotifyOAuth(
                client_id=sp_client_id,
                client_secret=sp_client_secret,
                redirect_uri=sp_redirect_uri,
                scope="playlist-read-private playlist-read-collaborative user-library-read",
                cache_path=".spotify_token_cache",
                open_browser=False,
            )
        except Exception as e:
            return None

    def _get_authenticated_spotify():
        """Get an authenticated spotipy client using cached token or OAuth flow."""
        import spotipy
        oauth = _get_spotify_oauth()
        if oauth is None:
            return None
        token_info = oauth.get_cached_token()
        if token_info:
            return spotipy.Spotify(auth=token_info["access_token"])
        return None

    def _ms_to_sec(ms):
        return (ms or 0) // 1000

    def _save_track_to_library(track: dict, extra_tags: str = "spotify") -> bool:
        """Save a Spotify track dict to the local media_items table. Returns True if new."""
        title    = track.get("name", "")
        artists  = ", ".join(a["name"] for a in track.get("artists", []))
        album    = track.get("album", {}).get("name", "") if isinstance(track.get("album"), dict) else ""
        duration = _ms_to_sec(track.get("duration_ms", 0))
        spotify_url = track.get("external_urls", {}).get("spotify", "")
        track_id    = track.get("id", "")
        tags     = f"spotify,{extra_tags}".strip(",")

        conn = get_conn()
        # Avoid duplicates by checking URL or title+artist combo
        existing = db_exec(conn,
            "SELECT id FROM media_items WHERE url=? OR (title=? AND artist=?)",
            (spotify_url, title, artists)).fetchone()
        if existing:
            conn.close()
            return False
        db_exec(conn,
            "INSERT INTO media_items "
            "(title,artist,album,media_type,source,url,duration_sec,tags) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (title, artists, album, "music", "Spotify", spotify_url, duration, tags))
        conn.commit()
        conn.close()
        return True

    def _save_playlist_to_library(pl_name: str, tracks: list, pl_color: str = "#1db954") -> tuple:
        """Create a local playlist and populate it with the given Spotify tracks."""
        conn = get_conn()
        # Create or reuse local playlist with same name
        existing_pl = db_exec(conn, "SELECT id FROM media_playlists WHERE name=?", (pl_name,)).fetchone()
        if existing_pl:
            pl_id = existing_pl[0]
        else:
            c = db_exec(conn,
                "INSERT INTO media_playlists (name, description, color) VALUES (?,?,?)",
                (pl_name, f"Imported from Spotify", pl_color))
            pl_id = c.lastrowid if not USE_POSTGRES else c.fetchone()[0]
        conn.commit()
        conn.close()

        new_tracks, dupes = 0, 0
        for idx, track in enumerate(tracks):
            is_new = _save_track_to_library(track, extra_tags=f"spotify,{pl_name.lower()}")
            if is_new:
                new_tracks += 1
            # Link track to playlist
            conn = get_conn()
            track_url = track.get("external_urls", {}).get("spotify", "")
            track_row = db_exec(conn,
                "SELECT id FROM media_items WHERE url=?", (track_url,)).fetchone()
            if track_row:
                media_id = track_row[0]
                existing_link = db_exec(conn,
                    "SELECT id FROM media_playlist_items WHERE playlist_id=? AND media_id=?",
                    (pl_id, media_id)).fetchone()
                if not existing_link:
                    db_exec(conn,
                        "INSERT INTO media_playlist_items (playlist_id,media_id,sort_order) VALUES (?,?,?)",
                        (pl_id, media_id, idx + 1))
                    conn.commit()
                else:
                    dupes += 1
            conn.close()
        return new_tracks, dupes

    # ── Mode selector ──────────────────────────────────────────────────────────
    sp_mode = st.radio("What do you want to do?",
                        ["🔍 Search Spotify (no login)", "📋 Import My Playlists (login required)"],
                        horizontal=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MODE 1 — SEARCH (Client Credentials, no user login)
    # ══════════════════════════════════════════════════════════════════════════
    if sp_mode == "🔍 Search Spotify (no login)":
        st.markdown("#### 🔍 Search Spotify")
        st.caption("Find any track on Spotify and add it to your library instantly.")

        with st.form("spotify_search_form"):
            sq_query  = st.text_input("Search", placeholder="Artist name, song title, album...")
            sq_limit  = st.slider("Results", 5, 20, 10)
            sq_submit = st.form_submit_button("🔍 Search Spotify", type="primary", use_container_width=True)

        if sq_submit and sq_query.strip():
            sp = _get_spotify_cc()
            if not sp:
                st.error("Could not connect to Spotify. Check your Client ID and Secret.")
            else:
                with st.spinner("Searching Spotify..."):
                    try:
                        results = sp.search(q=sq_query.strip(), type="track", limit=sq_limit)
                        tracks  = results.get("tracks", {}).get("items", [])
                    except Exception as e:
                        st.error(f"Spotify error: {e}")
                        tracks = []

                if not tracks:
                    st.info("No results found. Try a different search.")
                else:
                    st.caption(f"{len(tracks)} results from Spotify")
                    for track in tracks:
                        title   = track.get("name", "")
                        artists = ", ".join(a["name"] for a in track.get("artists", []))
                        album   = track.get("album", {}).get("name", "")
                        dur_sec = _ms_to_sec(track.get("duration_ms", 0))
                        sp_url  = track.get("external_urls", {}).get("spotify", "")
                        pop     = track.get("popularity", 0)

                        rc1, rc2, rc3 = st.columns([5, 3, 2])
                        rc1.markdown(
                            f"**{title}**  \n"
                            f"<span style='color:#aaa;font-size:12px'>{artists} · {album}</span>",
                            unsafe_allow_html=True
                        )
                        rc2.caption(
                            f"⏱️ {_duration_str(dur_sec)} · "
                            f"🔥 {pop}% popularity"
                        )
                        if sp_url:
                            rc2.markdown(f"[▶ Open in Spotify]({sp_url})")
                        with rc3:
                            if st.button("➕ Add to Library", key=f"sp_add_{track.get('id','')}"):
                                is_new = _save_track_to_library(track)
                                if is_new:
                                    st.success(f"✅ Added: {title}")
                                else:
                                    st.info("Already in library.")
                                st.rerun()
                        st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MODE 2 — IMPORT MY PLAYLISTS (OAuth)
    # ══════════════════════════════════════════════════════════════════════════
    else:
        st.markdown("#### 📋 Import Your Spotify Playlists")
        st.caption(
            "This imports your actual Spotify playlists and all their tracks into the Media Library. "
            "Requires a one-time Spotify login."
        )

        oauth = _get_spotify_oauth()
        sp_authed = _get_authenticated_spotify()

        if sp_authed is None:
            # Step 1: Show auth URL
            if oauth:
                auth_url = oauth.get_authorize_url()
                st.markdown(
                    f"**Step 1:** Click the link below to log in with Spotify:\n\n"
                    f"🔐 [**Log in with Spotify**]({auth_url})\n\n"
                    f"After logging in, Spotify will redirect you to a URL that starts with "
                    f"`{sp_redirect_uri}?code=...`\n\n"
                    f"**Step 2:** Copy the **entire redirect URL** from your browser's address bar "
                    f"(even if it shows an error page — that's expected) and paste it below:"
                )
                redirect_response = st.text_input("Paste the full redirect URL here",
                                                   placeholder=f"{sp_redirect_uri}?code=AQA...")
                if st.button("🔑 Authenticate", type="primary") and redirect_response.strip():
                    try:
                        token_info = oauth.parse_response_code(redirect_response.strip())
                        full_token = oauth.get_access_token(token_info, as_dict=True)
                        st.success("✅ Authenticated with Spotify! Refresh the page to import playlists.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {e}\n\nMake sure you copied the full URL.")
            else:
                st.error("Could not initialize Spotify OAuth. Check your credentials.")
        else:
            # Authenticated — show playlists
            import spotipy

            try:
                user_info = sp_authed.current_user()
                st.success(
                    f"✅ Connected as **{user_info.get('display_name', user_info.get('id', '?'))}** "
                    f"({user_info.get('email', '')})"
                )
            except Exception:
                user_info = {}

            if st.button("🔓 Disconnect Spotify"):
                import os
                if os.path.exists(".spotify_token_cache"):
                    os.remove(".spotify_token_cache")
                st.rerun()

            st.divider()

            # Load user's playlists
            with st.spinner("Loading your Spotify playlists..."):
                try:
                    pl_results = sp_authed.current_user_playlists(limit=50)
                    sp_playlists = pl_results.get("items", [])
                except Exception as e:
                    sp_playlists = []
                    st.error(f"Could not load playlists: {e}")

            if not sp_playlists:
                st.info("No playlists found on your Spotify account.")
            else:
                st.caption(f"{len(sp_playlists)} playlist(s) on your Spotify account")

                # Import all playlists at once
                if st.button("⬇️ Import ALL Playlists", type="primary"):
                    total_new, total_dupes = 0, 0
                    prog = st.progress(0.0, text="Importing playlists...")
                    for idx, pl in enumerate(sp_playlists):
                        pl_name = pl.get("name", "Untitled")
                        pl_id   = pl.get("id", "")
                        prog.progress((idx + 1) / len(sp_playlists), text=f"Importing: {pl_name}")
                        try:
                            track_results = sp_authed.playlist_tracks(pl_id, limit=100)
                            tracks = [
                                item["track"] for item in track_results.get("items", [])
                                if item.get("track") and item["track"].get("id")
                            ]
                            n, d = _save_playlist_to_library(pl_name, tracks)
                            total_new += n
                            total_dupes += d
                        except Exception:
                            pass
                    prog.empty()
                    st.success(
                        f"✅ Import complete! {total_new} new tracks added · "
                        f"{total_dupes} already in library."
                    )
                    st.rerun()

                st.divider()

                # Per-playlist import
                for pl in sp_playlists:
                    pl_name   = pl.get("name", "Untitled")
                    pl_count  = pl.get("tracks", {}).get("total", 0)
                    pl_owner  = pl.get("owner", {}).get("display_name", "")
                    pl_img    = (pl.get("images") or [{}])[0].get("url", "")

                    with st.container():
                        pc1, pc2, pc3 = st.columns([5, 3, 2])
                        pc1.markdown(
                            f"**{pl_name}**  \n"
                            f"<span style='color:#aaa;font-size:12px'>"
                            f"{pl_count} tracks · by {pl_owner}</span>",
                            unsafe_allow_html=True
                        )
                        if pl.get("external_urls", {}).get("spotify"):
                            pc2.markdown(f"[▶ Open in Spotify]({pl['external_urls']['spotify']})")
                        with pc3:
                            if st.button(f"⬇️ Import", key=f"import_pl_{pl.get('id','')}"):
                                with st.spinner(f"Importing '{pl_name}'..."):
                                    try:
                                        track_results = sp_authed.playlist_tracks(
                                            pl.get("id"), limit=100)
                                        tracks = [
                                            item["track"]
                                            for item in track_results.get("items", [])
                                            if item.get("track") and item["track"].get("id")
                                        ]
                                        new_t, dupe_t = _save_playlist_to_library(pl_name, tracks)
                                        st.success(
                                            f"✅ Imported '{pl_name}': "
                                            f"{new_t} new · {dupe_t} already existed"
                                        )
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Import failed: {e}")
                    st.divider()

            # Liked Songs import
            st.markdown("#### ❤️ Import Liked Songs")
            liked_limit = st.slider("How many liked songs?", 20, 200, 50, step=10)
            if st.button("⬇️ Import Liked Songs"):
                with st.spinner(f"Importing your top {liked_limit} liked songs..."):
                    try:
                        liked = sp_authed.current_user_saved_tracks(limit=liked_limit)
                        tracks = [
                            item["track"] for item in liked.get("items", [])
                            if item.get("track") and item["track"].get("id")
                        ]
                        new_t, dupe_t = _save_playlist_to_library("❤️ Liked Songs", tracks)
                        st.success(f"✅ {new_t} new liked songs added · {dupe_t} already in library.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not import liked songs: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — APPLE MUSIC
# ══════════════════════════════════════════════════════════════════════════════
with tab_apple:
    st.markdown("### 🍎 Apple Music")
    st.caption(
        "Apple Music doesn't offer a public Python API — but you have two great options: "
        "**iTunes Search** (search 200M+ tracks instantly, no account needed) and "
        "**Library XML Import** (export your playlists from Music.app and import them here)."
    )

    apple_mode = st.radio(
        "Choose a method",
        ["🔍 iTunes Search (no login)", "📂 Import from Music.app XML"],
        horizontal=True
    )
    st.divider()

    # ── HELPERS ────────────────────────────────────────────────────────────────
    def _save_apple_track(title, artist, album, genre, duration_ms, preview_url,
                          itunes_url, tags="apple-music"):
        """Save an iTunes/Apple Music track to the local library. Returns True if new."""
        dur_sec = int(duration_ms or 0) // 1000
        conn = get_conn()
        existing = db_exec(conn,
            "SELECT id FROM media_items WHERE url=? OR (title=? AND artist=?)",
            (itunes_url, title, artist)).fetchone()
        if existing:
            conn.close()
            return False
        db_exec(conn,
            "INSERT INTO media_items "
            "(title,artist,album,genre,media_type,source,url,duration_sec,tags) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (title, artist, album, genre or "Other", "music",
             "Apple Music", itunes_url, dur_sec, tags))
        conn.commit()
        conn.close()
        return True

    def _save_apple_playlist(pl_name: str, tracks: list) -> tuple:
        """Create a local playlist and populate with Apple Music tracks."""
        conn = get_conn()
        existing_pl = db_exec(conn, "SELECT id FROM media_playlists WHERE name=?",
                               (pl_name,)).fetchone()
        if existing_pl:
            pl_id = existing_pl[0]
        else:
            c = db_exec(conn,
                "INSERT INTO media_playlists (name, description, color) VALUES (?,?,?)",
                (pl_name, "Imported from Apple Music / Music.app", "#fc3c44"))
            pl_id = c.lastrowid if not USE_POSTGRES else c.fetchone()[0]
        conn.commit()
        conn.close()

        new_t, dupes = 0, 0
        for idx, t in enumerate(tracks):
            is_new = _save_apple_track(
                t.get("title", ""), t.get("artist", ""), t.get("album", ""),
                t.get("genre", ""), t.get("duration_ms", 0),
                t.get("preview_url", ""), t.get("url", ""),
                tags=f"apple-music,{pl_name.lower()}"
            )
            if is_new:
                new_t += 1
            conn = get_conn()
            track_row = db_exec(conn,
                "SELECT id FROM media_items WHERE url=?",
                (t.get("url", ""),)).fetchone()
            if track_row:
                media_id = track_row[0]
                link = db_exec(conn,
                    "SELECT id FROM media_playlist_items WHERE playlist_id=? AND media_id=?",
                    (pl_id, media_id)).fetchone()
                if not link:
                    db_exec(conn,
                        "INSERT INTO media_playlist_items (playlist_id,media_id,sort_order) VALUES (?,?,?)",
                        (pl_id, media_id, idx + 1))
                    conn.commit()
                else:
                    dupes += 1
            conn.close()
        return new_t, dupes

    # ══════════════════════════════════════════════════════════════════════════
    # MODE 1 — ITUNES SEARCH
    # ══════════════════════════════════════════════════════════════════════════
    if apple_mode == "🔍 iTunes Search (no login)":
        st.markdown("#### 🔍 iTunes / Apple Music Search")
        st.caption(
            "Uses Apple's free **iTunes Search API** — searches the same 200M+ track catalog "
            "as Apple Music. No account or API key needed."
        )

        with st.form("itunes_search_form"):
            iq1, iq2, iq3 = st.columns([4, 2, 2])
            it_query  = iq1.text_input("Search", placeholder="Song, artist, or album...")
            it_entity = iq2.selectbox("Search type", ["song", "album", "artist", "musicTrack"])
            it_limit  = iq3.slider("Results", 5, 25, 10)
            it_submit = st.form_submit_button("🔍 Search Apple Music", type="primary",
                                              use_container_width=True)

        if it_submit and it_query.strip():
            import urllib.request
            import urllib.parse
            import json as _json

            params = urllib.parse.urlencode({
                "term": it_query.strip(),
                "entity": it_entity,
                "limit": it_limit,
                "media": "music",
            })
            url = f"https://itunes.apple.com/search?{params}"

            with st.spinner("Searching iTunes..."):
                try:
                    with urllib.request.urlopen(url, timeout=10) as resp:
                        data = _json.loads(resp.read())
                    results = data.get("results", [])
                except Exception as e:
                    st.error(f"iTunes search failed: {e}")
                    results = []

            if not results:
                st.info("No results found. Try a different search.")
            else:
                st.caption(f"{len(results)} results from iTunes")
                for r in results:
                    t_name    = r.get("trackName") or r.get("collectionName", "")
                    a_name    = r.get("artistName", "")
                    al_name   = r.get("collectionName", "")
                    genre     = r.get("primaryGenreName", "")
                    dur_ms    = r.get("trackTimeMillis", 0)
                    preview   = r.get("previewUrl", "")
                    itunes_u  = r.get("trackViewUrl") or r.get("collectionViewUrl", "")
                    artwork   = r.get("artworkUrl60", "")
                    dur_s     = int(dur_ms or 0) // 1000

                    rc1, rc2, rc3 = st.columns([5, 3, 2])
                    rc1.markdown(
                        f"**{t_name}**  \n"
                        f"<span style='color:#aaa;font-size:12px'>"
                        f"{a_name} · {al_name} · {genre}</span>",
                        unsafe_allow_html=True
                    )
                    rc2.caption(f"⏱️ {_duration_str(dur_s)}")
                    if preview:
                        rc2.audio(preview)
                    if itunes_u:
                        rc2.markdown(f"[🍎 Open in Apple Music]({itunes_u})")
                    with rc3:
                        track_key = itunes_u or f"{t_name}_{a_name}"
                        if st.button("➕ Add to Library",
                                     key=f"am_add_{hash(track_key) % 999999}"):
                            is_new = _save_apple_track(
                                t_name, a_name, al_name, genre,
                                dur_ms, preview, itunes_u
                            )
                            if is_new:
                                st.success(f"✅ Added: {t_name}")
                            else:
                                st.info("Already in library.")
                            st.rerun()
                    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MODE 2 — XML IMPORT
    # ══════════════════════════════════════════════════════════════════════════
    else:
        st.markdown("#### 📂 Import from Music.app (XML)")
        st.markdown(
            "**How to export your Apple Music library:**\n\n"
            "1. Open **Music.app** on your Mac\n"
            "2. In the menu bar: **File → Library → Export Library...**\n"
            "3. Save the file (e.g., `Library.xml`)\n"
            "4. Upload it below\n\n"
            "To export a **single playlist**: right-click the playlist → "
            "**Export Playlist...** → choose XML format"
        )

        xml_file = st.file_uploader(
            "Upload your Music.app Library.xml or playlist .xml",
            type=["xml"],
            help="Export from Music.app: File → Library → Export Library → .xml"
        )

        if xml_file is not None:
            import plistlib

            with st.spinner("Parsing your Apple Music library..."):
                try:
                    data = plistlib.loads(xml_file.read())
                except Exception as e:
                    st.error(f"Could not parse XML file: {e}")
                    data = {}

            if data:
                tracks_dict = data.get("Tracks", {})
                playlists_raw = data.get("Playlists", [])

                st.success(
                    f"✅ Library parsed: **{len(tracks_dict)} tracks**, "
                    f"**{len(playlists_raw)} playlists**"
                )

                # Build track lookup by track ID
                def _itunes_track_to_dict(t):
                    dur_ms = t.get("Total Time", 0)
                    return {
                        "title":       t.get("Name", ""),
                        "artist":      t.get("Artist", ""),
                        "album":       t.get("Album", ""),
                        "genre":       t.get("Genre", ""),
                        "duration_ms": dur_ms,
                        "preview_url": "",
                        "url":         t.get("Location", ""),
                    }

                track_lookup = {
                    str(tid): _itunes_track_to_dict(t)
                    for tid, t in tracks_dict.items()
                }

                # Show playlist list with import buttons
                importable_pls = [
                    pl for pl in playlists_raw
                    if pl.get("Name") and pl.get("Name") not in
                       ("Library", "Music", "Downloaded Music", "Recently Added",
                        "Recently Played", "Top 25 Most Played")
                    and pl.get("Playlist Items")
                ]

                if not importable_pls:
                    st.info(
                        "No importable playlists found. "
                        "Try exporting a specific playlist instead of the full library."
                    )
                else:
                    st.markdown(f"**{len(importable_pls)} importable playlist(s) found:**")

                    # Import all button
                    if st.button("⬇️ Import ALL Playlists from XML", type="primary"):
                        total_new, total_dupes = 0, 0
                        prog = st.progress(0.0, text="Importing from Apple Music XML...")
                        for idx, pl in enumerate(importable_pls):
                            pl_name  = pl.get("Name", "Untitled")
                            pl_items = pl.get("Playlist Items", [])
                            tracks   = [
                                track_lookup[str(item["Track ID"])]
                                for item in pl_items
                                if str(item.get("Track ID", "")) in track_lookup
                            ]
                            prog.progress(
                                (idx + 1) / len(importable_pls),
                                text=f"Importing: {pl_name}"
                            )
                            n, d = _save_apple_playlist(pl_name, tracks)
                            total_new += n
                            total_dupes += d
                        prog.empty()
                        st.success(
                            f"✅ Import complete! {total_new} new tracks · "
                            f"{total_dupes} already existed."
                        )
                        st.rerun()

                    st.divider()

                    # Per-playlist import
                    for pl in importable_pls:
                        pl_name  = pl.get("Name", "Untitled")
                        pl_items = pl.get("Playlist Items", [])
                        tracks   = [
                            track_lookup[str(item["Track ID"])]
                            for item in pl_items
                            if str(item.get("Track ID", "")) in track_lookup
                        ]

                        pc1, pc2 = st.columns([6, 2])
                        pc1.markdown(f"**{pl_name}** — {len(tracks)} tracks")
                        with pc2:
                            if st.button("⬇️ Import", key=f"xml_pl_{pl_name}"):
                                with st.spinner(f"Importing '{pl_name}'..."):
                                    new_t, dupe_t = _save_apple_playlist(pl_name, tracks)
                                st.success(
                                    f"✅ '{pl_name}': {new_t} new · {dupe_t} existed"
                                )
                                st.rerun()
                        st.divider()

                # Bulk import ALL tracks (not just playlists)
                st.markdown("#### 📦 Import All Tracks (no playlists)")
                st.caption(
                    f"Import every track in your library ({len(track_lookup)} tracks) "
                    "as individual entries, without playlist grouping."
                )
                if st.button("⬇️ Import All Tracks"):
                    with st.spinner(f"Importing {len(track_lookup)} tracks..."):
                        new_t, skip_t = 0, 0
                        for t in track_lookup.values():
                            if t.get("title"):
                                is_new = _save_apple_track(
                                    t["title"], t["artist"], t["album"],
                                    t["genre"], t["duration_ms"],
                                    t["preview_url"], t["url"],
                                    tags="apple-music,library"
                                )
                                if is_new:
                                    new_t += 1
                                else:
                                    skip_t += 1
                    st.success(
                        f"✅ {new_t} new tracks added · {skip_t} already existed."
                    )
                    st.rerun()
