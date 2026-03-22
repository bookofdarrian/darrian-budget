"""
pages/146_immich_setup.py
─────────────────────────────────────────────────────────────────────────────
Immich Photo Setup Wizard
Owner: Darrian Belcher | Peach State Savings

PURPOSE
───────
One-stop page to get real photos showing in all carousels on PSS, SoleOps,
and College Confused.

STEP 1 — Save Immich server URL (default: http://100.95.125.112:2283)
STEP 2 — Create / paste API key  (saved to app_settings in the production DB)
STEP 3 — Run AI Photo Index      (CLIP searches + Claude classification)
STEP 4 — Preview                 (see your real photos in test carousels)
"""

import threading
import time

import streamlit as st

from utils.auth import inject_css, render_sidebar_brand, render_sidebar_user_widget, require_login
from utils.db import get_setting, init_db, set_setting

st.set_page_config(
    page_title="Immich Setup · Darrian Budget",
    page_icon="📸",
    layout="wide",
)

init_db()
inject_css()
require_login()

# ─── Sidebar ─────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                           label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                 label="Todo",               icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",    label="Creator",            icon="🎬")
st.sidebar.page_link("pages/25_notes.py",                label="Notes",              icon="📝")
st.sidebar.page_link("pages/26_media_library.py",        label="Media Library",      icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",   label="Personal Assistant", icon="🤖")
st.sidebar.page_link("pages/147_proactive_ai_engine.py", label="Proactive AI",       icon="🧠")
st.sidebar.page_link("pages/146_immich_setup.py",        label="Immich Setup",       icon="📸")
render_sidebar_user_widget()

# ─── Header ──────────────────────────────────────────────────────────────────
st.title("📸 Immich Photo Setup Wizard")
st.caption(
    "Get real photos showing in your PSS, SoleOps, and College Confused carousels. "
    "Complete all 4 steps below — takes about 2 minutes."
)
st.divider()

# ─── Live status bar ─────────────────────────────────────────────────────────
def _status_row() -> dict:
    from utils.immich_photos import has_api_key, is_immich_available, _load_catalog_from_db
    server = get_setting("immich_server") or "http://100.95.125.112:2283"
    up = is_immich_available()
    key = has_api_key()
    total_indexed = 0
    for cat in ("shoe", "fashion", "nature", "lifestyle", "headshot"):
        photos = _load_catalog_from_db(cat)
        if photos:
            total_indexed += len(photos)
    return {"server": server, "up": up, "key": key, "indexed": total_indexed}

status = _status_row()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Immich Server", "🟢 UP" if status["up"] else "🔴 DOWN", status["server"].replace("http://", ""))
c2.metric("API Key", "🟢 Set" if status["key"] else "🔴 Missing", "Stored in DB" if status["key"] else "Needs setup")
c3.metric("Photos Indexed", status["indexed"], "carousel-ready" if status["indexed"] > 0 else "run index below")
c4.metric("Carousels", "🟢 Real Photos" if status["indexed"] > 0 else "⚠️ Emoji Fallback",
          "All 3 sites" if status["indexed"] > 0 else "No catalog yet")

st.divider()

# ─── STEP 1: Server URL ───────────────────────────────────────────────────────
with st.expander("**Step 1 — Immich Server URL**", expanded=not status["up"]):
    st.markdown("Confirm the address where Immich is running on your homelab.")
    current_server = get_setting("immich_server") or "http://100.95.125.112:2283"
    new_server = st.text_input("Immich Server URL", value=current_server, key="server_url_input")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("💾 Save Server URL", use_container_width=True):
            set_setting("immich_server", new_server.rstrip("/"))
            st.success(f"✅ Server saved: {new_server}")
            st.rerun()
    with col2:
        if st.button("🔍 Ping Server", use_container_width=True):
            try:
                import requests
                r = requests.get(f"{new_server.rstrip('/')}/api/server/ping", timeout=4)
                if r.status_code == 200:
                    st.success("✅ Immich is reachable!")
                else:
                    st.error(f"❌ Server returned HTTP {r.status_code}")
            except Exception as e:
                st.error(f"❌ Can't reach server: {e}")

# ─── STEP 2: API Key ──────────────────────────────────────────────────────────
with st.expander("**Step 2 — API Key**", expanded=status["up"] and not status["key"]):
    st.markdown(
        "Two ways to get your API key:\n"
        "- **Option A** — Enter your Immich email & password and we'll create one automatically.\n"
        "- **Option B** — Paste an existing key (from Immich UI → Account Settings → API Keys)."
    )
    tab_a, tab_b = st.tabs(["Option A: Auto-create from credentials", "Option B: Paste existing key"])

    with tab_a:
        col1, col2 = st.columns(2)
        email = col1.text_input("Immich Email", placeholder="admin@immich.local", key="im_email")
        password = col2.text_input("Immich Password", type="password", key="im_password")
        if st.button("🔑 Create API Key", key="create_key_btn", use_container_width=True):
            if not email or not password:
                st.warning("Enter both email and password.")
            else:
                with st.spinner("Authenticating with Immich..."):
                    from utils.immich_photos import create_api_key
                    key = create_api_key(email, password)
                if key:
                    st.success(f"✅ API key created and saved to DB! (starts with: {key[:8]}...)")
                    st.rerun()
                else:
                    st.error("❌ Failed to create API key. Check email/password and server URL.")

    with tab_b:
        paste_key = st.text_input("Paste API Key", type="password", placeholder="immich_api_key_...", key="paste_key")
        if st.button("💾 Save API Key", key="save_paste_key", use_container_width=True):
            if paste_key.strip():
                set_setting("immich_api_key", paste_key.strip())
                st.success("✅ API key saved to DB!")
                st.rerun()
            else:
                st.warning("Paste a key first.")

# ─── STEP 3: AI Photo Index ───────────────────────────────────────────────────
with st.expander("**Step 3 — Run AI Photo Index**", expanded=status["up"] and status["key"] and status["indexed"] == 0):
    st.markdown(
        "This step runs CLIP semantic searches against your Immich library and uses Claude AI "
        "to classify each photo (shoe, fashion, nature, lifestyle, headshot) and assign it to "
        "the right site (PSS/SoleOps/CC). Results are cached for 6 hours."
    )

    n_photos = st.slider("Max photos to index", min_value=20, max_value=200, value=80, step=10,
                         help="More photos = better carousels but takes longer. 80 is a good start.")

    if not status["key"]:
        st.warning("⚠️ Complete Step 2 (API key) first.")
    elif not status["up"]:
        st.warning("⚠️ Immich server is not reachable. Check Step 1.")
    else:
        api_key_ok = bool(get_setting("anthropic_api_key"))
        if not api_key_ok:
            st.warning(
                "⚠️ No Anthropic API key found in DB. "
                "The index will use CLIP search results only (no Claude classification). "
                "Set `anthropic_api_key` in Settings to enable full AI routing."
            )

        if st.button("🚀 Start AI Index Now", use_container_width=True, type="primary"):
            status_box = st.empty()
            progress = st.progress(0, text="Starting...")

            def _run_index():
                try:
                    from utils.immich_photos import (
                        CAROUSEL_SEARCH_QUERIES,
                        ai_classify_photo,
                        has_api_key,
                        is_immich_available,
                        run_full_ai_index,
                        search_photos_clip,
                        _save_catalog_to_db,
                        get_setting as _gs,
                    )
                    catalog = run_full_ai_index(max_photos=n_photos)
                    total = sum(len(v) for v in catalog.values())
                    st.session_state["_index_result"] = f"✅ Indexed {total} photos across {len(catalog)} categories."
                except Exception as e:
                    st.session_state["_index_result"] = f"❌ Index failed: {e}"

            with st.spinner(f"Indexing up to {n_photos} photos... (this takes 1-3 minutes)"):
                # Run in the same thread so spinner shows
                from utils.immich_photos import run_full_ai_index as _rfi
                try:
                    catalog = _rfi(max_photos=n_photos)
                    total = sum(len(v) for v in catalog.values())
                    progress.progress(100, text="Done!")
                    st.success(f"✅ Indexed **{total} photos** across {len(catalog)} categories. Carousels will now show real photos!")
                    # Clear process-level carousel cache so new photos render immediately
                    try:
                        import utils.carousel as _car
                        _car._CAROUSEL_HTML_CACHE.clear()
                    except Exception:
                        pass
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Indexing failed: {e}")

    # Quick re-index (force refresh)
    if status["indexed"] > 0:
        st.markdown("---")
        st.caption(f"Already indexed {status['indexed']} photos. Re-index to refresh after adding new photos to Immich.")
        if st.button("🔄 Re-index Photos", use_container_width=True):
            # Expire the catalog cache by clearing the DB keys
            from utils.immich_photos import CAROUSEL_SEARCH_QUERIES, CACHE_KEY_PREFIX
            from utils.db import set_setting as _ss
            for cat in CAROUSEL_SEARCH_QUERIES:
                _ss(f"{CACHE_KEY_PREFIX}{cat}", "")
            try:
                import utils.carousel as _car
                _car._CAROUSEL_HTML_CACHE.clear()
            except Exception:
                pass
            st.success("Cache cleared. Scroll up and click 'Start AI Index Now' to re-index.")
            st.rerun()

# ─── STEP 4: Preview ──────────────────────────────────────────────────────────
with st.expander("**Step 4 — Preview Carousels**", expanded=status["indexed"] > 0):
    if status["indexed"] == 0:
        st.info("Complete Step 3 to index photos, then come back here to preview.")
    else:
        from utils.carousel import (
            CAROUSEL_BASE_CSS,
            carousel_theme_css,
            render_nature_inspiration_carousel,
            render_shoe_product_carousel,
            render_story_band_html,
        )
        from utils.immich_photos import _load_catalog_from_db

        st.markdown(f"**{status['indexed']} photos indexed.** Here's a live preview of your carousels:")

        # Show catalog breakdown
        cats = {}
        for cat in ("shoe", "fashion", "nature", "lifestyle", "headshot"):
            photos = _load_catalog_from_db(cat)
            cats[cat] = len(photos) if photos else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("👟 Shoe", cats["shoe"])
        c2.metric("🧥 Fashion", cats["fashion"])
        c3.metric("🌅 Nature", cats["nature"])
        c4.metric("💻 Lifestyle", cats["lifestyle"])
        c5.metric("📸 Headshot", cats["headshot"])

        st.markdown("---")
        st.markdown("### Shoe Carousel (SoleOps)")
        st.components.v1.html(
            carousel_theme_css("cyan") + CAROUSEL_BASE_CSS + render_shoe_product_carousel("cyan"),
            height=340, scrolling=False,
        )

        st.markdown("### Nature Carousel (PSS / CC)")
        st.components.v1.html(
            carousel_theme_css("green") + CAROUSEL_BASE_CSS + render_nature_inspiration_carousel("green"),
            height=340, scrolling=False,
        )

        st.markdown("### Story Band")
        st.components.v1.html(
            CAROUSEL_BASE_CSS + render_story_band_html(
                "Built from Hampton to Atlanta — every photo tells a story of purpose.",
                "Darrian Belcher", "#22D47E"
            ),
            height=140, scrolling=False,
        )

# ─── Troubleshooting ─────────────────────────────────────────────────────────
with st.expander("🔧 Troubleshooting"):
    st.markdown("""
**Still seeing emoji placeholders after indexing?**
1. Verify the Immich server URL is accessible from the production server (not just your Mac):
   - The Streamlit app runs on CT100 @ 100.95.125.112 → it calls `http://100.95.125.112:2283`
   - Both are on the same LAN so this should work
2. Check there are actually photos in Immich: `Immich UI → Photos`
3. Make sure Immich's CLIP AI model is enabled: `Admin → Settings → Machine Learning → CLIP`
4. After indexing, clear the Streamlit cache with the Re-index button above or restart the app

**API key lost after restart?**
- Keys are stored in `data/budget.db` in the `app_settings` table
- Run: `sqlite3 data/budget.db "SELECT key, substr(value,1,20) FROM app_settings WHERE key LIKE 'immich%';"`

**Run index manually from CLI (on CT100):**
```bash
cd /path/to/darrian-budget
source venv/bin/activate
python3 utils/immich_photos.py --ping    # check connection
python3 utils/immich_photos.py --index   # run full index
```
""")
