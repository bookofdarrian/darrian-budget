"""
Video & AI Image Studio — Page 143
Generate AI images (Claude vision + DALL-E style prompts), upload/manage videos,
embed YouTube/local videos, and build content asset libraries for all channels.
"""
import streamlit as st
import os
import json
import base64
import hashlib
from datetime import datetime, date
from pathlib import Path
import anthropic

st.set_page_config(
    page_title="🎥 Video & AI Image Studio — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                              label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                    label="Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",       label="Creator",         icon="🎬")
st.sidebar.page_link("pages/25_notes.py",                   label="Notes",           icon="📝")
st.sidebar.page_link("pages/26_media_library.py",           label="Media Library",   icon="🎵")
st.sidebar.page_link("pages/143_video_ai_studio.py",        label="🎥 Video & AI Image",icon="🎥")
st.sidebar.page_link("pages/17_personal_assistant.py",      label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────
PAGE_TITLE = "🎥 Video & AI Image Studio"
CHANNELS   = ["bookofdarrian", "Peach State Savings", "SoleOps / Sneakers", "College Confused", "Personal / Family"]
ASSET_TYPES = ["Thumbnail", "Cover Art", "Story/Reel Frame", "Banner", "Logo Concept", "Product Shot", "Lifestyle", "Infographic", "Other"]
VIDEO_PLATFORMS = ["YouTube", "Instagram Reel", "TikTok", "Facebook", "Twitter/X", "LinkedIn", "Local Upload", "Other"]
IMAGE_STYLES = [
    "Photorealistic", "Cinematic", "Flat Design / Minimalist", "Vibrant / Bold",
    "Dark & Moody", "Watercolor / Artistic", "Corporate / Professional",
    "Street / Urban", "Nature / Outdoors", "Tech / Futuristic"
]
STATIC_DIR = Path("static/studio")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

PH = "%s" if USE_POSTGRES else "?"
AUTO = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS studio_images (
            id           {AUTO},
            user_id      INTEGER NOT NULL DEFAULT 1,
            title        TEXT NOT NULL,
            channel      TEXT,
            asset_type   TEXT,
            style        TEXT,
            prompt       TEXT,
            revised_prompt TEXT,
            image_data   TEXT,
            file_path    TEXT,
            ai_analysis  TEXT,
            tags         TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS studio_videos (
            id           {AUTO},
            user_id      INTEGER NOT NULL DEFAULT 1,
            title        TEXT NOT NULL,
            channel      TEXT,
            platform     TEXT,
            video_url    TEXT,
            embed_code   TEXT,
            thumbnail_id INTEGER,
            description  TEXT,
            duration_sec INTEGER,
            tags         TEXT,
            status       TEXT DEFAULT 'draft',
            publish_date DATE,
            views        INTEGER DEFAULT 0,
            notes        TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS studio_prompts (
            id           {AUTO},
            user_id      INTEGER NOT NULL DEFAULT 1,
            title        TEXT NOT NULL,
            prompt_text  TEXT NOT NULL,
            category     TEXT,
            channel      TEXT,
            use_count    INTEGER DEFAULT 0,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

_ensure_tables()

# ── Helper Functions ───────────────────────────────────────────────────────────
def _get_user_id():
    return st.session_state.get("user_id", 1)

def _save_image_record(title, channel, asset_type, style, prompt, revised_prompt, image_data, file_path, ai_analysis, tags):
    conn = get_conn()
    db_exec(conn, f"""
        INSERT INTO studio_images
            (user_id, title, channel, asset_type, style, prompt, revised_prompt, image_data, file_path, ai_analysis, tags)
        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
    """, (_get_user_id(), title, channel, asset_type, style, prompt, revised_prompt,
           image_data, file_path, ai_analysis, json.dumps(tags)))
    conn.commit()
    conn.close()

def _load_images(channel=None):
    conn = get_conn()
    cur = conn.cursor()
    if channel and channel != "All Channels":
        cur.execute(f"SELECT * FROM studio_images WHERE user_id={PH} AND channel={PH} ORDER BY created_at DESC",
                    (_get_user_id(), channel))
    else:
        cur.execute(f"SELECT * FROM studio_images WHERE user_id={PH} ORDER BY created_at DESC",
                    (_get_user_id(),))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _save_video(title, channel, platform, video_url, embed_code, description, tags, status, publish_date, notes):
    conn = get_conn()
    db_exec(conn, f"""
        INSERT INTO studio_videos
            (user_id, title, channel, platform, video_url, embed_code, description, tags, status, publish_date, notes)
        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
    """, (_get_user_id(), title, channel, platform, video_url, embed_code, description,
           json.dumps(tags), status, publish_date, notes))
    conn.commit()
    conn.close()

def _load_videos(channel=None):
    conn = get_conn()
    cur = conn.cursor()
    if channel and channel != "All Channels":
        cur.execute(f"SELECT * FROM studio_videos WHERE user_id={PH} AND channel={PH} ORDER BY created_at DESC",
                    (_get_user_id(), channel))
    else:
        cur.execute(f"SELECT * FROM studio_videos WHERE user_id={PH} ORDER BY created_at DESC",
                    (_get_user_id(),))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _save_prompt(title, prompt_text, category, channel):
    conn = get_conn()
    db_exec(conn, f"""
        INSERT INTO studio_prompts (user_id, title, prompt_text, category, channel)
        VALUES ({PH},{PH},{PH},{PH},{PH})
    """, (_get_user_id(), title, prompt_text, category, channel))
    conn.commit()
    conn.close()

def _load_prompts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM studio_prompts WHERE user_id={PH} ORDER BY use_count DESC, created_at DESC",
                (_get_user_id(),))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _extract_youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def _build_youtube_embed(video_id: str) -> str:
    return f'<iframe width="100%" height="400" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

def _analyze_image_with_claude(image_bytes: bytes, filename: str, analysis_goal: str) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key set. Go to Settings to add one."
    try:
        client = anthropic.Anthropic(api_key=api_key)
        ext = Path(filename).suffix.lower()
        media_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                          ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
        media_type = media_type_map.get(ext, "image/jpeg")
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": f"""You are a creative director and content strategist for Darrian Belcher's brand.

Analysis Goal: {analysis_goal}

Please analyze this image and provide:
1. **Visual Description** — What you see in the image
2. **Brand Fit Assessment** — How well it fits the channel/brand
3. **Strengths** — What works well visually
4. **Improvement Suggestions** — Specific actionable tweaks
5. **Content Ideas** — 3 content ideas this image could inspire
6. **Caption Suggestions** — 2 social media captions ready to post

Keep it practical, energetic, and creator-focused."""}
                ]
            }]
        )
        return msg.content[0].text
    except Exception as e:
        return f"❌ AI analysis error: {e}"

def _generate_image_prompt_with_claude(concept: str, channel: str, asset_type: str, style: str) -> dict:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return {"prompt": "", "error": "No API key"}
    try:
        client = anthropic.Anthropic(api_key=api_key)
        channel_context = {
            "bookofdarrian": "lifestyle, street culture, Black excellence, personal growth, Atlanta culture",
            "Peach State Savings": "personal finance, wealth building, modern professional, Georgia-based",
            "SoleOps / Sneakers": "sneaker culture, resale business, streetwear, limited editions",
            "College Confused": "college prep, student life, academic success, young adults",
            "Personal / Family": "family, community, personal milestones"
        }.get(channel, "modern lifestyle")

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": f"""You are an expert AI image prompt engineer for content creators.

Channel: {channel} ({channel_context})
Asset Type: {asset_type}
Visual Style: {style}
Concept: {concept}

Write a detailed, optimized image generation prompt (150-200 words) that:
1. Opens with the subject and composition
2. Specifies lighting, colors, and mood
3. Mentions the style ({style})
4. Includes technical quality descriptors (8K, cinematic, professional, etc.)
5. Ends with negative prompt suggestions

Format as JSON:
{{
  "prompt": "the main generation prompt",
  "negative_prompt": "what to avoid",
  "tips": "1-2 sentences on best AI tool to use for this"
}}"""
            }]
        )
        return json.loads(msg.content[0].text)
    except json.JSONDecodeError:
        text = msg.content[0].text if 'msg' in dir() else ""
        return {"prompt": text, "negative_prompt": "", "tips": ""}
    except Exception as e:
        return {"prompt": "", "error": str(e)}

def _generate_video_script_with_claude(video_title: str, channel: str, duration: str, key_points: str) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No API key set."
    try:
        client = anthropic.Anthropic(api_key=api_key)
        channel_context = {
            "bookofdarrian": "Darrian Belcher's personal brand — lifestyle, Black excellence, Atlanta culture, personal growth, authentic storytelling",
            "Peach State Savings": "personal finance app and brand — budgeting, investing, wealth building, fintech, modern money management",
            "SoleOps / Sneakers": "sneaker resale business — buying, selling, authenticating sneakers, market trends, profit strategies",
            "College Confused": "college prep platform — applications, scholarships, FAFSA, campus visits, student success",
            "Personal / Family": "personal life and family content"
        }.get(channel, "lifestyle and personal brand")

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""You are a professional YouTube/Instagram video scriptwriter for Darrian Belcher.

Channel: {channel} — {channel_context}
Video Title: {video_title}
Target Duration: {duration}
Key Points to Cover: {key_points}

Write a complete video script with:
**HOOK** (first 5-10 seconds — attention grabber)
**INTRO** (brief channel/topic intro)
**MAIN CONTENT** (structured sections with timestamps)
**CTA** (call to action — subscribe, follow, comment)
**OUTRO** (sign-off)

Make it conversational, energetic, and authentic to Darrian's voice. Include B-roll suggestions in [brackets]."""
            }]
        )
        return msg.content[0].text
    except Exception as e:
        return f"❌ Error: {e}"

# ── UI ─────────────────────────────────────────────────────────────────────────
st.title(PAGE_TITLE)
st.caption("AI-powered image generation, video management, and content asset library for all your creator channels.")

tabs = st.tabs([
    "🖼️ AI Image Generator",
    "🎥 Video Library",
    "📹 Video Embed & Manage",
    "📝 Prompt Library",
    "🔍 Image Analyzer",
    "🎬 Script Writer"
])

# ── TAB 1: AI Image Generator ──────────────────────────────────────────────────
with tabs[0]:
    st.subheader("🖼️ AI Image Prompt Generator")
    st.info("Claude generates optimized prompts you can paste into **DALL-E 3**, **Midjourney**, **Stable Diffusion**, **Adobe Firefly**, or **Ideogram**. Upload generated images back here to save them.")

    col1, col2 = st.columns([1, 1])
    with col1:
        channel = st.selectbox("Channel", CHANNELS, key="ig_channel")
        asset_type = st.selectbox("Asset Type", ASSET_TYPES, key="ig_asset")
        style = st.selectbox("Visual Style", IMAGE_STYLES, key="ig_style")
        concept = st.text_area("Concept / Description",
            placeholder="e.g. 'A young Black man counting money in an Atlanta penthouse at sunset, celebrating financial freedom'",
            height=100, key="ig_concept")
        gen_btn = st.button("🤖 Generate AI Prompt", type="primary", use_container_width=True)

    with col2:
        if gen_btn and concept:
            with st.spinner("Generating optimized prompt with Claude..."):
                result = _generate_image_prompt_with_claude(concept, channel, asset_type, style)
            if "error" in result and result["error"]:
                st.error(result["error"])
            else:
                st.success("✅ Prompt generated!")
                st.markdown("**📋 Main Prompt** (copy this):")
                st.code(result.get("prompt", ""), language=None)
                if result.get("negative_prompt"):
                    st.markdown("**🚫 Negative Prompt:**")
                    st.code(result.get("negative_prompt", ""), language=None)
                if result.get("tips"):
                    st.info(f"💡 **Tool Tip:** {result.get('tips', '')}")

                # Save prompt to library
                if st.button("💾 Save to Prompt Library"):
                    title = f"{asset_type} — {channel} — {datetime.now().strftime('%b %d')}"
                    _save_prompt(title, result.get("prompt", ""), asset_type, channel)
                    st.success("Saved to Prompt Library!")
                    st.rerun()
        elif gen_btn:
            st.warning("Please enter a concept/description first.")

    st.divider()
    st.subheader("📤 Upload Generated Image")
    st.caption("After generating in Midjourney/DALL-E/etc., upload here to save to your library.")

    ucol1, ucol2 = st.columns([1, 1])
    with ucol1:
        up_title = st.text_input("Image Title", key="up_title")
        up_channel = st.selectbox("Channel", CHANNELS, key="up_channel")
        up_asset_type = st.selectbox("Asset Type", ASSET_TYPES, key="up_asset_type")
        up_style = st.selectbox("Style Used", IMAGE_STYLES, key="up_style")
        up_prompt = st.text_area("Prompt Used (optional)", height=80, key="up_prompt")
        up_tags = st.text_input("Tags (comma-separated)", key="up_tags")
        uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp", "gif"])
        analyze_on_upload = st.checkbox("🤖 AI Analyze on Upload", value=True)

    with ucol2:
        if uploaded_file and up_title:
            img_bytes = uploaded_file.read()
            b64_data = base64.standard_b64encode(img_bytes).decode()
            st.image(img_bytes, caption=up_title, use_container_width=True)

            if st.button("💾 Save Image to Library", type="primary"):
                # Save file
                safe_name = hashlib.md5(img_bytes).hexdigest()[:12]
                ext = Path(uploaded_file.name).suffix
                file_path = str(STATIC_DIR / f"{safe_name}{ext}")
                with open(file_path, "wb") as f:
                    f.write(img_bytes)

                ai_analysis = ""
                if analyze_on_upload:
                    with st.spinner("Analyzing with Claude..."):
                        ai_analysis = _analyze_image_with_claude(img_bytes, uploaded_file.name,
                            f"Analyze as a {up_asset_type} for {up_channel}")

                tags = [t.strip() for t in up_tags.split(",") if t.strip()]
                _save_image_record(up_title, up_channel, up_asset_type, up_style,
                                   up_prompt, "", b64_data, file_path, ai_analysis, tags)
                st.success("✅ Image saved to library!")
                if ai_analysis:
                    with st.expander("🤖 AI Analysis", expanded=True):
                        st.markdown(ai_analysis)
                st.rerun()

    st.divider()
    st.subheader("📚 Image Library")
    filter_channel = st.selectbox("Filter by Channel", ["All Channels"] + CHANNELS, key="lib_filter")
    images = _load_images(filter_channel)

    if not images:
        st.info("No images saved yet. Generate and upload your first image above!")
    else:
        st.caption(f"{len(images)} image(s) in library")
        # Display in grid (3 columns)
        cols = st.columns(3)
        for i, img in enumerate(images):
            with cols[i % 3]:
                with st.container(border=True):
                    if img.get("image_data"):
                        try:
                            img_bytes = base64.standard_b64decode(img["image_data"])
                            st.image(img_bytes, use_container_width=True)
                        except Exception:
                            st.markdown("🖼️ *Image data unavailable*")
                    st.markdown(f"**{img['title']}**")
                    st.caption(f"📺 {img.get('channel','')} | 🎨 {img.get('asset_type','')} | {img.get('created_at','')[:10]}")
                    if img.get("tags"):
                        try:
                            tags = json.loads(img["tags"])
                            if tags:
                                st.caption(" ".join([f"`{t}`" for t in tags]))
                        except Exception:
                            pass
                    with st.expander("🤖 AI Analysis"):
                        st.markdown(img.get("ai_analysis") or "*No analysis available*")
                    with st.expander("📋 Prompt"):
                        st.code(img.get("prompt") or "*No prompt saved*", language=None)

# ── TAB 2: Video Library ───────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("🎥 Video Library")
    filter_ch = st.selectbox("Filter by Channel", ["All Channels"] + CHANNELS, key="vlib_filter")
    videos = _load_videos(filter_ch)

    if not videos:
        st.info("No videos saved yet. Add your first video in the 'Video Embed & Manage' tab!")
    else:
        # KPI strip
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Videos", len(videos))
        k2.metric("Published", sum(1 for v in videos if v.get("status") == "published"))
        k3.metric("Drafts", sum(1 for v in videos if v.get("status") == "draft"))
        k4.metric("Total Views", f"{sum(v.get('views',0) for v in videos):,}")
        st.divider()

        for v in videos:
            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"### {v['title']}")
                    st.caption(f"📺 {v.get('channel','')} | 📱 {v.get('platform','')} | 📅 {str(v.get('publish_date',''))[:10]}")
                    if v.get("description"):
                        st.markdown(v["description"][:200] + ("..." if len(v.get("description","")) > 200 else ""))
                    status_color = {"published": "🟢", "draft": "🟡", "scheduled": "🔵", "archived": "🔴"}.get(v.get("status",""), "⚪")
                    st.caption(f"{status_color} {v.get('status','').title()} | 👁️ {v.get('views',0):,} views")
                with col2:
                    if v.get("video_url"):
                        vid_id = _extract_youtube_id(v["video_url"])
                        if vid_id:
                            st.markdown(f'<img src="https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" style="width:100%;border-radius:8px;">', unsafe_allow_html=True)
                    if v.get("notes"):
                        st.caption(f"📝 {v['notes'][:100]}")

# ── TAB 3: Video Embed & Manage ───────────────────────────────────────────────
with tabs[2]:
    st.subheader("📹 Add & Embed Video")

    sub_tabs = st.tabs(["➕ Add Video", "▶️ Embed Viewer"])
    with sub_tabs[0]:
        col1, col2 = st.columns([1, 1])
        with col1:
            v_title = st.text_input("Video Title *", key="v_title")
            v_channel = st.selectbox("Channel", CHANNELS, key="v_channel")
            v_platform = st.selectbox("Platform", VIDEO_PLATFORMS, key="v_platform")
            v_url = st.text_input("Video URL (YouTube, etc.)", key="v_url")
            v_description = st.text_area("Description", height=100, key="v_desc")
            v_tags = st.text_input("Tags (comma-separated)", key="v_tags")

        with col2:
            v_status = st.selectbox("Status", ["draft", "scheduled", "published", "archived"], key="v_status")
            v_publish_date = st.date_input("Publish Date", value=date.today(), key="v_pub_date")
            v_notes = st.text_area("Notes / Ideas", height=80, key="v_notes")

            # Preview embed
            if v_url:
                vid_id = _extract_youtube_id(v_url)
                if vid_id:
                    st.markdown("**Preview:**")
                    st.markdown(_build_youtube_embed(vid_id), unsafe_allow_html=True)

        if st.button("💾 Save Video", type="primary", use_container_width=True):
            if v_title:
                embed_code = ""
                if v_url:
                    vid_id = _extract_youtube_id(v_url)
                    if vid_id:
                        embed_code = _build_youtube_embed(vid_id)
                tags = [t.strip() for t in v_tags.split(",") if t.strip()]
                _save_video(v_title, v_channel, v_platform, v_url, embed_code,
                           v_description, tags, v_status, v_publish_date, v_notes)
                st.success("✅ Video saved!")
                st.rerun()
            else:
                st.warning("Please enter a video title.")

    with sub_tabs[1]:
        st.subheader("▶️ Quick Embed Viewer")
        embed_url = st.text_input("Paste any YouTube URL to preview", key="embed_viewer_url")
        if embed_url:
            vid_id = _extract_youtube_id(embed_url)
            if vid_id:
                st.markdown(_build_youtube_embed(vid_id), unsafe_allow_html=True)
                st.code(f"https://youtu.be/{vid_id}", language=None)
            else:
                st.warning("Could not extract YouTube video ID. Make sure it's a YouTube URL.")

        st.divider()
        st.subheader("📤 Embed Saved Videos")
        videos = _load_videos()
        if videos:
            selected = st.selectbox("Select a saved video to embed",
                                     [f"{v['title']} ({v.get('platform','')})" for v in videos],
                                     key="embed_select")
            idx = [f"{v['title']} ({v.get('platform','')})" for v in videos].index(selected)
            v = videos[idx]
            if v.get("video_url"):
                vid_id = _extract_youtube_id(v["video_url"])
                if vid_id:
                    st.markdown(_build_youtube_embed(vid_id), unsafe_allow_html=True)
            elif v.get("embed_code"):
                st.markdown(v["embed_code"], unsafe_allow_html=True)

# ── TAB 4: Prompt Library ─────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("📝 Saved Prompt Library")
    col1, col2 = st.columns([2, 1])
    with col1:
        prompts = _load_prompts()
        if not prompts:
            st.info("No saved prompts yet. Generate prompts in the AI Image Generator tab to save them here.")
        else:
            for p in prompts:
                with st.expander(f"**{p['title']}** — {p.get('channel','')} | {p.get('category','')} | Used {p.get('use_count',0)}x"):
                    st.code(p["prompt_text"], language=None)
                    st.caption(f"Saved {str(p.get('created_at',''))[:10]}")

    with col2:
        st.subheader("➕ Add Prompt Manually")
        mp_title = st.text_input("Title", key="mp_title")
        mp_channel = st.selectbox("Channel", CHANNELS, key="mp_channel")
        mp_category = st.selectbox("Category", ASSET_TYPES, key="mp_cat")
        mp_text = st.text_area("Prompt Text", height=120, key="mp_text")
        if st.button("💾 Save Prompt", use_container_width=True):
            if mp_title and mp_text:
                _save_prompt(mp_title, mp_text, mp_category, mp_channel)
                st.success("Saved!")
                st.rerun()

# ── TAB 5: Image Analyzer ─────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("🔍 AI Image Analyzer (Claude Vision)")
    st.caption("Upload any image and Claude will analyze it for brand fit, visual quality, content ideas, and caption suggestions.")

    ia_col1, ia_col2 = st.columns([1, 1])
    with ia_col1:
        ia_channel = st.selectbox("Channel Context", CHANNELS, key="ia_channel")
        ia_goal = st.text_input("Analysis Goal",
            value="Analyze this image for content marketing and social media use",
            key="ia_goal")
        ia_file = st.file_uploader("Upload Image to Analyze", type=["png","jpg","jpeg","webp"],
                                    key="ia_uploader")
        if ia_file:
            st.image(ia_file, use_container_width=True)

    with ia_col2:
        if ia_file:
            if st.button("🤖 Analyze with Claude", type="primary", use_container_width=True):
                img_bytes = ia_file.read()
                with st.spinner("Claude is analyzing your image..."):
                    analysis = _analyze_image_with_claude(img_bytes, ia_file.name,
                                                           f"{ia_goal} (Channel: {ia_channel})")
                st.markdown("### 🎯 AI Analysis")
                st.markdown(analysis)

# ── TAB 6: Script Writer ──────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("🎬 AI Video Script Writer")
    st.caption("Claude writes complete video scripts tailored to your channel, style, and duration.")

    sc_col1, sc_col2 = st.columns([1, 1])
    with sc_col1:
        sc_channel = st.selectbox("Channel", CHANNELS, key="sc_channel")
        sc_title = st.text_input("Video Title / Topic", key="sc_title",
                                  placeholder="e.g. 'How I Built a Budget App That Makes $500/mo'")
        sc_duration = st.selectbox("Target Duration", ["30 seconds", "1 minute", "3 minutes",
                                                        "5 minutes", "8-10 minutes", "15+ minutes"])
        sc_points = st.text_area("Key Points to Cover",
                                  placeholder="- My budgeting journey\n- The app features\n- How viewers can try it",
                                  height=120, key="sc_points")
        sc_btn = st.button("🤖 Generate Script", type="primary", use_container_width=True)

    with sc_col2:
        if sc_btn:
            if sc_title and sc_points:
                with st.spinner("Writing your script with Claude..."):
                    script = _generate_video_script_with_claude(sc_title, sc_channel, sc_duration, sc_points)
                st.markdown("### 📄 Generated Script")
                st.markdown(script)
                st.download_button("⬇️ Download Script",
                                   data=script,
                                   file_name=f"script_{sc_title[:30].replace(' ','_')}.md",
                                   mime="text/markdown")
            else:
                st.warning("Please fill in the video title and key points.")
