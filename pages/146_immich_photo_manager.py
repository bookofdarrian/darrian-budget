"""
pages/146_immich_photo_manager.py
─────────────────────────────────────────────────────────────────────────────
Immich AI Photo Manager
Owner: Darrian Belcher | Peach State Savings

PURPOSE
───────
This page is the command center for managing how your Immich photo library
powers the carousels on peachstatesavings.com, soleops, and College Confused.

FEATURES
────────
- Connect to Immich with email/password → auto-generate & save API key
- Live status: Immich server ping, API key status, total photos
- View your Immich albums and pick which ones map to which carousel
- Run AI Photo Index: Claude + Immich CLIP classifies every photo →
  routes each one to the right site + carousel slot + SEO alt text
- Preview carousels in-app before they go live
- Manual override: drag photos between categories
- Auto-refresh schedule: index runs nightly at 2 AM via cron
"""

import json
import time
from datetime import datetime

import streamlit as st

from utils.auth import inject_css, render_sidebar_brand, render_sidebar_user_widget, require_login
from utils.db import get_conn, get_setting, init_db, set_setting
from utils.immich_photos import (
    CAROUSEL_SEARCH_QUERIES,
    SITE_CATEGORY_MAP,
    ai_classify_photo,
    create_api_key,
    get_album_assets,
    get_albums,
    get_all_assets,
    get_carousel_photos,
    has_api_key,
    is_immich_available,
    run_full_ai_index,
    search_photos_clip,
    thumbnail_url,
)

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Immich Photo Manager | PSS",
    page_icon="📸",
    layout="wide",
)

init_db()
inject_css()
require_login()

# ─── Sidebar ──────────────────────────────────────────────────────────────────

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
st.sidebar.page_link("pages/146_immich_photo_manager.py", label="📸 Photo Manager", icon="📸")
render_sidebar_user_widget()

# ─── DB table ─────────────────────────────────────────────────────────────────


def _ensure_tables() -> None:
    conn = get_conn()
    try:
        import os
        USE_POSTGRES = os.getenv("DATABASE_URL", "").startswith("postgres")
        ph = "%s" if USE_POSTGRES else "?"
        with conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS immich_photo_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    sites TEXT NOT NULL DEFAULT 'all',
                    seo_alt_text TEXT,
                    caption TEXT,
                    priority INTEGER DEFAULT 5,
                    reasoning TEXT,
                    thumbnail_url TEXT,
                    manually_overridden INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
    finally:
        conn.close()


_ensure_tables()

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _save_classified_photo(photo: dict) -> None:
    conn = get_conn()
    try:
        with conn:
            conn.execute("""
                INSERT INTO immich_photo_catalog
                    (asset_id, category, sites, seo_alt_text, caption, priority,
                     reasoning, thumbnail_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(asset_id) DO UPDATE SET
                    category = excluded.category,
                    sites = excluded.sites,
                    seo_alt_text = excluded.seo_alt_text,
                    caption = excluded.caption,
                    priority = excluded.priority,
                    reasoning = excluded.reasoning,
                    thumbnail_url = excluded.thumbnail_url,
                    updated_at = datetime('now')
                WHERE manually_overridden = 0
            """, (
                photo.get("asset_id"),
                photo.get("category", "lifestyle"),
                json.dumps(photo.get("sites", ["all"])),
                photo.get("seo_alt_text", ""),
                photo.get("caption", ""),
                photo.get("priority", 5),
                photo.get("reasoning", ""),
                photo.get("thumbnail_url", ""),
            ))
    finally:
        conn.close()


def _load_catalog(category: str = None, site: str = None) -> list[dict]:
    conn = get_conn()
    try:
        query = "SELECT * FROM immich_photo_catalog"
        params = []
        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY priority DESC, updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        cols = [d[0] for d in conn.execute(query, params).description] if rows else []
        # Re-run with description
        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def _update_photo_override(asset_id: str, category: str, sites: list, priority: int, caption: str) -> None:
    conn = get_conn()
    try:
        with conn:
            conn.execute("""
                UPDATE immich_photo_catalog
                SET category = ?, sites = ?, priority = ?, caption = ?,
                    manually_overridden = 1, updated_at = datetime('now')
                WHERE asset_id = ?
            """, (category, json.dumps(sites), priority, caption, asset_id))
    finally:
        conn.close()


# ─── Main UI ──────────────────────────────────────────────────────────────────

st.title("📸 Immich AI Photo Manager")
st.markdown(
    "Connect your Immich library → AI routes every photo to the right carousel, "
    "site, and SEO position automatically."
)

# ─── Section 1: Connection Status ────────────────────────────────────────────

st.markdown("## 🔌 Connection Status")

col_ping, col_key, col_photos = st.columns(3)

immich_up = is_immich_available()
api_key_set = has_api_key()

with col_ping:
    if immich_up:
        st.success("✅ Immich Server: **Online**\n\nhttp://100.95.125.112:2283")
    else:
        st.error("❌ Immich Server: **Offline**\n\nCheck VPN / Tailscale")

with col_key:
    if api_key_set:
        stored_key = get_setting("immich_api_key") or ""
        st.success(f"✅ API Key: **Configured**\n\n`{stored_key[:8]}...`")
    else:
        st.warning("⚠️ API Key: **Not Set**\n\nUse the form below to connect")

with col_photos:
    if immich_up and api_key_set:
        # Quick count — cached
        count_key = "immich_total_count"
        cached_count = get_setting(count_key)
        if not cached_count:
            try:
                import requests
                r = requests.get(
                    f"http://100.95.125.112:2283/api/assets/statistics",
                    headers={"x-api-key": get_setting("immich_api_key") or ""},
                    timeout=5,
                )
                if r.status_code == 200:
                    total = r.json().get("total", "?")
                    set_setting(count_key, str(total))
                    cached_count = str(total)
            except Exception:
                cached_count = "?"
        st.info(f"📷 **{cached_count}** photos in your library")
    else:
        st.info("📷 Connect to count photos")

st.markdown("---")

# ─── Section 2: Connect / Generate API Key ───────────────────────────────────

with st.expander("🔑 Connect Immich — Enter Credentials to Generate API Key", expanded=not api_key_set):
    st.markdown("""
    Enter your Immich login (same email/password you use at http://100.95.125.112:2283).
    This will auto-generate and save an API key so the app can access your photos.
    **Your password is NOT stored** — only the API key is saved.
    """)
    col_e, col_p = st.columns(2)
    with col_e:
        immich_email = st.text_input("Immich Email", placeholder="darrian@example.com")
    with col_p:
        immich_password = st.text_input("Immich Password", type="password")

    col_btn, col_manual = st.columns(2)
    with col_btn:
        if st.button("🔑 Generate API Key", type="primary"):
            if not immich_email or not immich_password:
                st.error("Enter both email and password")
            else:
                with st.spinner("Connecting to Immich..."):
                    key = create_api_key(immich_email, immich_password)
                if key:
                    st.success(f"✅ API key created and saved: `{key[:8]}...`")
                    st.rerun()
                else:
                    st.error("❌ Failed. Check email/password and make sure Immich is running.")

    with col_manual:
        st.markdown("**Or paste an existing API key:**")
        manual_key = st.text_input("API Key", placeholder="Paste key from Immich → Account → API Keys")
        if st.button("💾 Save API Key"):
            if manual_key:
                set_setting("immich_api_key", manual_key.strip())
                st.success("✅ API key saved!")
                st.rerun()

st.markdown("---")

# ─── Section 3: Albums ───────────────────────────────────────────────────────

if immich_up and api_key_set:
    st.markdown("## 📁 Your Immich Albums")
    st.markdown("Create albums in Immich to group photos by type (e.g. 'SoleOps', 'Brand Photos', 'Street Style').")

    albums = get_albums()
    if albums:
        album_cols = st.columns(min(4, len(albums)))
        for i, album in enumerate(albums):
            with album_cols[i % 4]:
                count = album.get("assetCount", 0)
                name = album.get("albumName", "Unnamed")
                st.metric(f"📁 {name}", f"{count} photos")

        st.markdown("### Map Albums to Carousels")
        col_al, col_cat = st.columns(2)
        with col_al:
            selected_album = st.selectbox(
                "Select Album",
                [a.get("albumName") for a in albums],
            )
        with col_cat:
            target_category = st.selectbox(
                "Assign to Category",
                list(CAROUSEL_SEARCH_QUERIES.keys()),
            )
        target_sites = st.multiselect(
            "Show on Sites",
            ["soleops", "pss", "cc"],
            default=["pss"],
        )
        if st.button("📌 Assign Album to Carousel"):
            album_obj = next((a for a in albums if a.get("albumName") == selected_album), None)
            if album_obj:
                assets = get_album_assets(album_obj["id"])
                count = 0
                for asset in assets:
                    photo = {
                        "asset_id": asset["id"],
                        "category": target_category,
                        "sites": target_sites,
                        "seo_alt_text": f"Darrian Belcher {target_category} - {asset.get('originalFileName', '')}",
                        "caption": "",
                        "priority": 7,
                        "reasoning": f"Manually assigned from album '{selected_album}'",
                        "thumbnail_url": thumbnail_url(asset["id"]),
                    }
                    _save_classified_photo(photo)
                    count += 1
                st.success(f"✅ {count} photos from '{selected_album}' assigned to {target_category} carousel")
                st.rerun()
    else:
        st.info("No albums found. Create albums in Immich to organize your photos by type.")

    st.markdown("---")

    # ─── Section 4: AI Photo Index ───────────────────────────────────────────

    st.markdown("## 🤖 AI Photo Indexing")
    st.markdown("""
    **How it works:**
    1. Immich CLIP AI semantically searches your library for each category
    2. Claude analyzes each photo (filename, EXIF, location) and decides:
       - Which carousel slot: shoe / fashion / nature / lifestyle / headshot
       - Which sites: SoleOps / PSS / College Confused
       - SEO alt text optimized for your brand
       - Priority score (1-10) for placement above/below fold
    3. Results cached in DB, refreshed hourly
    """)

    col_run, col_count = st.columns(2)
    with col_run:
        max_photos = st.slider("Max photos to index", 10, 200, 50, step=10)
        if st.button("🚀 Run AI Photo Index", type="primary"):
            if not get_setting("anthropic_api_key"):
                st.error("❌ No Anthropic API key. Add it in app settings first.")
            else:
                progress = st.progress(0, text="Starting AI index...")
                with st.spinner("Running CLIP searches + Claude classification..."):
                    catalog = run_full_ai_index(max_photos=max_photos)
                    total = sum(len(v) for v in catalog.values())
                    for cat, photos in catalog.items():
                        for photo in photos:
                            _save_classified_photo(photo)
                progress.progress(1.0, text=f"✅ Indexed {total} photos across {len(catalog)} categories")
                st.success(f"✅ Done! {total} photos indexed and ready for carousels.")
                st.rerun()

    with col_count:
        catalog_rows = _load_catalog()
        if catalog_rows:
            cats = {}
            for row in catalog_rows:
                c = row.get("category", "?")
                cats[c] = cats.get(c, 0) + 1
            for cat, n in sorted(cats.items()):
                st.metric(f"{cat.title()}", f"{n} photos")
        else:
            st.info("No photos indexed yet. Run the AI index above.")

    st.markdown("---")

    # ─── Section 5: CLIP Semantic Search ─────────────────────────────────────

    st.markdown("## 🔍 Test CLIP Semantic Search")
    st.markdown("Search your Immich library with natural language — same AI Immich uses internally.")

    clip_query = st.text_input(
        "Search query",
        placeholder='Try: "sneakers product shot" or "street fashion Atlanta" or "professional headshot"',
    )
    clip_limit = st.slider("Results", 4, 20, 8, key="clip_limit")

    if st.button("🔍 Search") and clip_query:
        with st.spinner(f"Searching for '{clip_query}'..."):
            results = search_photos_clip(clip_query, limit=clip_limit)

        if results:
            st.success(f"Found {len(results)} photos")
            cols = st.columns(4)
            for i, asset in enumerate(results):
                with cols[i % 4]:
                    img_url = thumbnail_url(asset.get("id", ""), size="thumbnail")
                    st.image(img_url, caption=asset.get("originalFileName", ""), use_container_width=True)
                    if st.button(f"📌 Classify with AI", key=f"classify_{i}"):
                        api_key = get_setting("anthropic_api_key") or ""
                        if api_key:
                            classified = ai_classify_photo(asset, api_key)
                            _save_classified_photo(classified)
                            st.success(f"Saved as **{classified['category']}** for **{classified['sites']}**")
        else:
            st.warning("No results. Try a different search query or check your API key.")

    st.markdown("---")

    # ─── Section 6: Carousel Preview ─────────────────────────────────────────

    st.markdown("## 👁️ Carousel Preview")
    st.markdown("Preview what photos will appear in each carousel on your sites.")

    col_prev_cat, col_prev_site = st.columns(2)
    with col_prev_cat:
        preview_cat = st.selectbox("Category", list(CAROUSEL_SEARCH_QUERIES.keys()), key="prev_cat")
    with col_prev_site:
        preview_site = st.selectbox("Site", ["all", "soleops", "pss", "cc"], key="prev_site")

    # Load from DB catalog
    preview_photos = _load_catalog(category=preview_cat)
    if preview_site != "all":
        preview_photos = [
            p for p in preview_photos
            if preview_site in json.loads(p.get("sites", '["all"]'))
            or "all" in json.loads(p.get("sites", '["all"]'))
        ]

    if preview_photos:
        st.info(f"Showing {len(preview_photos)} photos for **{preview_cat}** on **{preview_site}**")
        cols = st.columns(4)
        for i, photo in enumerate(preview_photos[:16]):
            with cols[i % 4]:
                img_url = photo.get("thumbnail_url", "")
                try:
                    st.image(img_url, use_container_width=True)
                except Exception:
                    st.markdown(f"🖼️ `{photo.get('asset_id', '')[:8]}...`")
                st.caption(f"**P:{photo.get('priority')}** | {photo.get('seo_alt_text', '')[:40]}")

                # Override controls
                with st.expander("Edit", expanded=False):
                    new_cat = st.selectbox(
                        "Category", list(CAROUSEL_SEARCH_QUERIES.keys()),
                        index=list(CAROUSEL_SEARCH_QUERIES.keys()).index(photo.get("category", "lifestyle")),
                        key=f"cat_{photo['asset_id']}",
                    )
                    new_sites = st.multiselect(
                        "Sites",
                        ["soleops", "pss", "cc"],
                        default=json.loads(photo.get("sites", '["pss"]')),
                        key=f"sites_{photo['asset_id']}",
                    )
                    new_priority = st.slider("Priority", 1, 10, photo.get("priority", 5), key=f"pri_{photo['asset_id']}")
                    new_caption = st.text_input("Caption", photo.get("caption", ""), key=f"cap_{photo['asset_id']}")
                    if st.button("💾 Save Override", key=f"save_{photo['asset_id']}"):
                        _update_photo_override(photo["asset_id"], new_cat, new_sites, new_priority, new_caption)
                        st.success("Saved!")
                        st.rerun()
    else:
        st.info(f"No photos indexed for {preview_cat} yet. Run the AI index or assign an album above.")

    st.markdown("---")

    # ─── Section 7: SEO Report ────────────────────────────────────────────────

    st.markdown("## 🔎 SEO Photo Report")
    st.markdown("Review AI-generated alt text and captions for all indexed photos.")

    all_photos = _load_catalog()
    if all_photos:
        for photo in all_photos[:50]:
            with st.expander(
                f"{'🔴' if not photo.get('seo_alt_text') else '🟢'} "
                f"{photo.get('category', '?').upper()} | P:{photo.get('priority')} | "
                f"{photo.get('asset_id', '')[:12]}..."
            ):
                col_img, col_meta = st.columns([1, 3])
                with col_img:
                    try:
                        st.image(photo.get("thumbnail_url", ""), width=120)
                    except Exception:
                        st.markdown("🖼️")
                with col_meta:
                    st.markdown(f"**Sites:** {photo.get('sites')}")
                    st.markdown(f"**Alt text:** {photo.get('seo_alt_text', '—')}")
                    st.markdown(f"**Caption:** {photo.get('caption', '—')}")
                    st.markdown(f"**AI reasoning:** {photo.get('reasoning', '—')}")
                    st.markdown(f"**Manual override:** {'Yes' if photo.get('manually_overridden') else 'No'}")
    else:
        st.info("No photos indexed yet.")

else:
    st.info("👆 Connect to Immich above to get started.")

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#666;font-size:12px'>"
    "📸 Immich AI Photo Manager | Darrian Belcher | Peach State Savings"
    "</p>",
    unsafe_allow_html=True,
)
