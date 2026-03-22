"""
utils/immich_photos.py
─────────────────────────────────────────────────────────────────────────────
AI-Powered Immich Photo Connector
Owner: Darrian Belcher | Peach State Savings / SoleOps / College Confused

HOW IT WORKS
────────────
1.  Immich is already running at http://100.95.125.112:2283 with CLIP AI
2.  We call the Immich API to do semantic CLIP searches ("sneakers", "headshot",
    "street fashion", "nature Atlanta", etc.)
3.  Claude analyzes each result's filename + EXIF description + Immich tags
    to decide which carousel slot it belongs to (shoe, fashion, nature,
    lifestyle, headshot) and which SITE it best serves (soleops, pss, cc, all)
4.  Results are cached in app_settings (DB) and refreshed nightly
5.  Carousel engine calls get_carousel_photos(category, site) → list of
    Immich thumbnail URLs ready to drop into HTML <img> tags

IMMICH API KEY
─────────────
Store in DB: set_setting("immich_api_key", "<your key>")
Get from Immich UI → Account Settings → API Keys → New API Key
Or run: utils/immich_photos.py --create-key from the homelab

IMMICH SERVER
─────────────
Store in DB: set_setting("immich_server", "http://100.95.125.112:2283")
Default falls back to that address automatically.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import requests

from utils.db import get_conn, get_setting, set_setting

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

DEFAULT_IMMICH_SERVER = "http://100.95.125.112:2283"
CACHE_KEY_PREFIX = "immich_cache_"
CACHE_TTL_SECONDS = 3600  # 1 hour — refresh hourly

# ─── Carousel slot → CLIP search queries ─────────────────────────────────────
# These are the AI semantic searches we run against YOUR Immich library.
# Immich's CLIP model understands natural language so be descriptive.

CAROUSEL_SEARCH_QUERIES: dict[str, list[str]] = {
    "shoe": [
        "sneakers shoes close up product",
        "Air Jordan Nike Adidas shoe",
        "sneaker collection flatlay",
        "shoe resale product photo",
    ],
    "fashion": [
        "street fashion outfit full body",
        "urban style streetwear",
        "lifestyle fashion portrait outdoors",
        "black man street style fashion",
    ],
    "nature": [
        "nature outdoor landscape sunrise sunset",
        "Atlanta Georgia city skyline",
        "Hampton Virginia beach waterfront",
        "Chicago skyline architecture",
        "New York City NYC skyline",
        "trees forest greenery peaceful",
    ],
    "lifestyle": [
        "headshot professional portrait",
        "laptop work desk setup",
        "lifestyle candid everyday moment",
        "professional business portrait",
    ],
    "headshot": [
        "headshot close up portrait professional",
        "face portrait confident smile",
        "personal brand photo",
    ],
}

# ─── Site routing rules ───────────────────────────────────────────────────────
# AI assigns photos to sites based on content. Override logic below.

SITE_CATEGORY_MAP: dict[str, list[str]] = {
    "soleops": ["shoe", "fashion"],
    "pss": ["nature", "lifestyle", "headshot"],
    "cc": ["nature", "lifestyle"],
    "all": ["fashion", "lifestyle", "headshot"],
}

# ─── Immich API helpers ───────────────────────────────────────────────────────


def _get_headers() -> dict[str, str]:
    """Return Immich API headers using stored API key."""
    api_key = get_setting("immich_api_key") or ""
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_server() -> str:
    return (get_setting("immich_server") or DEFAULT_IMMICH_SERVER).rstrip("/")


def is_immich_available() -> bool:
    """Quick health check — returns True if Immich server is reachable."""
    try:
        r = requests.get(
            f"{_get_server()}/api/server/ping", timeout=3
        )
        return r.status_code == 200
    except Exception:
        return False


def has_api_key() -> bool:
    """Returns True if an API key is configured."""
    return bool(get_setting("immich_api_key"))


# ─── Login / API Key creation ─────────────────────────────────────────────────


def login_and_get_token(email: str, password: str) -> str | None:
    """
    Authenticate with Immich using email+password.
    Returns user access token (NOT an API key — use for one-time calls).
    """
    try:
        r = requests.post(
            f"{_get_server()}/api/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if r.status_code == 201:
            return r.json().get("accessToken")
    except Exception as e:
        logger.error("Immich login failed: %s", e)
    return None


def create_api_key(email: str, password: str, key_name: str = "darrian-budget-app") -> str | None:
    """
    Log in with email/password, create a named API key, save it to DB.
    Returns the API key string or None on failure.
    """
    token = login_and_get_token(email, password)
    if not token:
        return None
    try:
        r = requests.post(
            f"{_get_server()}/api/api-keys",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"name": key_name},
            timeout=10,
        )
        if r.status_code in (200, 201):
            secret = r.json().get("secret")
            if secret:
                set_setting("immich_api_key", secret)
                set_setting("immich_server", _get_server())
                logger.info("Immich API key created and saved: %s", key_name)
                return secret
    except Exception as e:
        logger.error("Failed to create Immich API key: %s", e)
    return None


# ─── Photo search ─────────────────────────────────────────────────────────────


def search_photos_clip(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Use Immich CLIP semantic search to find photos matching a natural-language
    query. Returns list of Immich asset dicts.
    """
    if not has_api_key():
        return []
    try:
        r = requests.post(
            f"{_get_server()}/api/search/smart",
            headers=_get_headers(),
            json={"query": query, "type": "IMAGE", "withExif": True},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            assets = data.get("assets", {}).get("items", [])
            return assets[:limit]
    except Exception as e:
        logger.error("Immich CLIP search failed for '%s': %s", query, e)
    return []


def get_all_assets(limit: int = 500) -> list[dict[str, Any]]:
    """Fetch all assets from Immich (paged, up to limit)."""
    if not has_api_key():
        return []
    assets: list[dict[str, Any]] = []
    page = 1
    while len(assets) < limit:
        try:
            r = requests.get(
                f"{_get_server()}/api/assets",
                headers=_get_headers(),
                params={"page": page, "size": 100},
                timeout=15,
            )
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            assets.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        except Exception as e:
            logger.error("Immich asset fetch failed page %d: %s", page, e)
            break
    return assets[:limit]


def get_albums() -> list[dict[str, Any]]:
    """List all albums in Immich."""
    if not has_api_key():
        return []
    try:
        r = requests.get(
            f"{_get_server()}/api/albums",
            headers=_get_headers(),
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error("Failed to fetch Immich albums: %s", e)
    return []


def get_album_assets(album_id: str) -> list[dict[str, Any]]:
    """Get all assets in a specific Immich album."""
    if not has_api_key():
        return []
    try:
        r = requests.get(
            f"{_get_server()}/api/albums/{album_id}",
            headers=_get_headers(),
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("assets", [])
    except Exception as e:
        logger.error("Failed to fetch album %s: %s", album_id, e)
    return []


# ─── Thumbnail URL builder ────────────────────────────────────────────────────


def thumbnail_url(asset_id: str, size: str = "preview") -> str:
    """
    Return the public thumbnail URL for an Immich asset.
    size: "thumbnail" (small square) | "preview" (medium web-ready)
    These URLs work in <img> tags if the browser can reach the Immich server.
    For public sites, proxy through the Streamlit app instead.
    """
    server = _get_server()
    api_key = get_setting("immich_api_key") or ""
    return f"{server}/api/assets/{asset_id}/thumbnail?size={size}&key={api_key}"


def proxy_thumbnail_url(asset_id: str, size: str = "preview") -> str:
    """
    Return a local proxy URL (served by Streamlit's static file handler).
    Preferred for production — hides internal server address.
    Format: /api/photos/{asset_id}?size={size}
    Handled by pages/146_immich_photo_manager.py
    """
    return f"/api/photos/{asset_id}?size={size}"


# ─── AI Photo Routing via Claude ─────────────────────────────────────────────


def ai_classify_photo(asset: dict[str, Any], anthropic_api_key: str) -> dict[str, Any]:
    """
    Use Claude to classify a single Immich asset into:
    - category: shoe | fashion | nature | lifestyle | headshot
    - sites: list of ["soleops", "pss", "cc"]
    - seo_alt_text: SEO-optimized alt text
    - caption: short inspiring caption
    - priority: 1-10 (10 = most prominent placement)

    Input: Immich asset dict with originalFileName, exifInfo, description, etc.
    """
    try:
        import anthropic  # type: ignore

        client = anthropic.Anthropic(api_key=anthropic_api_key)

        filename = asset.get("originalFileName", "")
        description = asset.get("exifInfo", {}).get("description", "") or ""
        created_at = asset.get("fileCreatedAt", "")
        city = asset.get("exifInfo", {}).get("city", "") or ""
        state = asset.get("exifInfo", {}).get("state", "") or ""
        country = asset.get("exifInfo", {}).get("country", "") or ""

        prompt = f"""You are classifying a photo for Darrian Belcher's personal brand websites.
Darrian is a Black man from Hampton VA (raised), with family roots in Chicago and Atlanta.
Mom did an internship in NYC. Darrian is a Sikh-influenced Black Panther ideologist — middle son,
two sisters, divorced parents. His brands: SoleOps (sneaker reselling), Peach State Savings
(personal finance), College Confused (college prep for first-gen students).

Photo info:
- Filename: {filename}
- Description: {description}
- Created: {created_at}
- Location: {city}, {state}, {country}

Classify this photo and return ONLY a JSON object (no markdown, no explanation):
{{
  "category": "<shoe|fashion|nature|lifestyle|headshot>",
  "sites": ["<soleops|pss|cc>"],
  "seo_alt_text": "<SEO alt text for image, 10-15 words>",
  "caption": "<inspiring 1-line caption that fits Darrian's brand voice>",
  "priority": <1-10>,
  "reasoning": "<one sentence why you chose this category>"
}}

Rules:
- shoe: sneakers, shoe products, shoe collection photos
- fashion: outfits, streetwear, full-body lifestyle fashion
- nature: outdoors, city skylines, landscapes, Hampton/ATL/Chicago/NYC vibes
- lifestyle: desk setups, candid moments, daily life
- headshot: portrait, face-focused, professional/personal brand
- Priority 8-10 = hero/above-fold carousel placement
- Priority 5-7 = mid-page carousel
- Priority 1-4 = story band / footer area
"""

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # strip any accidental markdown
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)
        result["asset_id"] = asset.get("id", "")
        result["thumbnail_url"] = thumbnail_url(asset.get("id", ""))
        return result
    except Exception as e:
        logger.error("AI classification failed for %s: %s", asset.get("id"), e)
        return {
            "asset_id": asset.get("id", ""),
            "category": "lifestyle",
            "sites": ["all"],
            "seo_alt_text": "Darrian Belcher personal brand photo",
            "caption": "",
            "priority": 5,
            "reasoning": "fallback classification",
            "thumbnail_url": thumbnail_url(asset.get("id", "")),
        }


# ─── Bulk AI Indexing ─────────────────────────────────────────────────────────


def run_full_ai_index(max_photos: int = 100) -> dict[str, list[dict]]:
    """
    Main indexing function:
    1. Run CLIP semantic searches for each carousel category
    2. Deduplicate results
    3. AI-classify each photo with Claude
    4. Cache results in DB
    Returns: dict keyed by category with list of classified photo dicts
    """
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        logger.error("No Anthropic API key — AI classification skipped")
        return {}

    seen_ids: set[str] = set()
    catalog: dict[str, list[dict]] = {cat: [] for cat in CAROUSEL_SEARCH_QUERIES}

    for category, queries in CAROUSEL_SEARCH_QUERIES.items():
        for query in queries:
            if len(catalog[category]) >= (max_photos // len(CAROUSEL_SEARCH_QUERIES)):
                break
            results = search_photos_clip(query, limit=10)
            for asset in results:
                asset_id = asset.get("id", "")
                if asset_id and asset_id not in seen_ids:
                    seen_ids.add(asset_id)
                    classified = ai_classify_photo(asset, api_key)
                    # Route to the category that matches best
                    best_cat = classified.get("category", category)
                    catalog[best_cat].append(classified)
                    time.sleep(0.2)  # rate limit

    # Sort each category by priority (desc)
    for cat in catalog:
        catalog[cat].sort(key=lambda x: x.get("priority", 5), reverse=True)

    # Cache in DB
    _save_catalog_to_db(catalog)
    return catalog


def _save_catalog_to_db(catalog: dict[str, list[dict]]) -> None:
    """Persist the photo catalog to app_settings as JSON."""
    conn = get_conn()
    try:
        for category, photos in catalog.items():
            key = f"{CACHE_KEY_PREFIX}{category}"
            value = json.dumps({"photos": photos, "cached_at": time.time()})
            set_setting(key, value)
    except Exception as e:
        logger.error("Failed to save catalog to DB: %s", e)
    finally:
        conn.close()


def _load_catalog_from_db(category: str) -> list[dict] | None:
    """Load cached photo catalog from DB. Returns None if stale or missing."""
    raw = get_setting(f"{CACHE_KEY_PREFIX}{category}")
    if not raw:
        return None
    try:
        data = json.loads(raw)
        cached_at = data.get("cached_at", 0)
        if time.time() - cached_at > CACHE_TTL_SECONDS:
            return None  # stale
        return data.get("photos", [])
    except Exception:
        return None


# ─── Main public API ──────────────────────────────────────────────────────────


def get_carousel_photos(
    category: str,
    site: str = "all",
    limit: int = 12,
    fallback_to_cache: bool = True,
) -> list[dict[str, Any]]:
    """
    PRIMARY FUNCTION called by carousel.py and page templates.

    Args:
        category: "shoe" | "fashion" | "nature" | "lifestyle" | "headshot"
        site: "soleops" | "pss" | "cc" | "all"
        limit: max photos to return
        fallback_to_cache: use cached results if Immich is unreachable

    Returns:
        List of dicts with keys:
            asset_id, thumbnail_url, seo_alt_text, caption, priority
    """
    # Try cache first (fast path)
    if fallback_to_cache:
        cached = _load_catalog_from_db(category)
        if cached:
            filtered = [
                p for p in cached
                if site == "all" or site in p.get("sites", []) or "all" in p.get("sites", [])
            ]
            return filtered[:limit]

    # If no cache and Immich is up, do a quick search without full AI classification
    if is_immich_available() and has_api_key():
        queries = CAROUSEL_SEARCH_QUERIES.get(category, [category])
        results = []
        for q in queries[:2]:  # limit to 2 queries for speed
            assets = search_photos_clip(q, limit=limit)
            for a in assets:
                asset_id = a.get("id", "")
                results.append({
                    "asset_id": asset_id,
                    "thumbnail_url": thumbnail_url(asset_id),
                    "seo_alt_text": f"Darrian Belcher {category} photo",
                    "caption": "",
                    "priority": 7,
                    "sites": ["all"],
                })
        return results[:limit]

    return []


def get_photos_by_album_name(
    album_name: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Get photos from a specific Immich album by name.
    Good for curated sets: "Brand Photos", "SoleOps Inventory", etc.
    """
    albums = get_albums()
    for album in albums:
        if album.get("albumName", "").lower() == album_name.lower():
            assets = get_album_assets(album["id"])
            return [
                {
                    "asset_id": a["id"],
                    "thumbnail_url": thumbnail_url(a["id"]),
                    "seo_alt_text": a.get("originalFileName", "Darrian Belcher photo"),
                    "caption": "",
                    "priority": 7,
                    "album": album_name,
                }
                for a in assets[:limit]
            ]
    return []


# ─── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if "--ping" in sys.argv:
        up = is_immich_available()
        print(f"Immich: {'UP ✓' if up else 'DOWN ✗'} | API key: {'SET ✓' if has_api_key() else 'MISSING ✗'}")

    elif "--index" in sys.argv:
        print("Running full AI photo index...")
        catalog = run_full_ai_index(max_photos=50)
        for cat, photos in catalog.items():
            print(f"  {cat}: {len(photos)} photos")
        print("Done. Cached in DB.")

    elif "--albums" in sys.argv:
        albums = get_albums()
        for a in albums:
            print(f"  {a.get('albumName')} — {a.get('assetCount', '?')} photos")

    elif "--create-key" in sys.argv:
        email = input("Immich email: ")
        password = input("Immich password: ")
        key = create_api_key(email, password)
        print(f"API key created and saved: {key[:8]}..." if key else "Failed")

    else:
        print(__doc__)
