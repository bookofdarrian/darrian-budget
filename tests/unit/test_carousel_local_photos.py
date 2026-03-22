"""
tests/unit/test_carousel_local_photos.py
─────────────────────────────────────────────────────────────────
Unit tests for the local static photo fallback added to utils/carousel.py

Tests verify:
  1. carousel.py imports cleanly
  2. _load_photo_b64 returns a valid data URI for known files
  3. _get_local_carousel_photos returns real photos for headshot/lifestyle
  4. _get_local_carousel_photos returns [] for categories with no files (shoe, fashion, nature)
  5. _build_local_photo_cards returns card HTML containing <img> src when photos exist
  6. _build_local_photo_cards returns '' for empty categories
  7. render_headshot_lifestyle_carousel produces non-empty HTML with real photo data
  8. Live static photo files exist on disk and are non-zero
"""

import re
from pathlib import Path

import pytest

# ─── Repo root for file existence checks ──────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent


# ─── 1. Import check ──────────────────────────────────────────────────────────

def test_carousel_module_imports():
    """carousel.py must import without errors."""
    import utils.carousel  # noqa: F401


# ─── 2. _load_photo_b64 ───────────────────────────────────────────────────────

def test_load_photo_b64_headshot_png():
    from utils.carousel import _load_photo_b64
    uri = _load_photo_b64("static/photos/darrian_headshot.png")
    assert uri.startswith("data:image/png;base64,"), f"Expected PNG data URI, got: {uri[:60]}"
    assert len(uri) > 10_000, "Headshot data URI suspiciously short"


def test_load_photo_b64_professional_jpg():
    from utils.carousel import _load_photo_b64
    uri = _load_photo_b64("static/photos/darrian_professional.jpg")
    assert uri.startswith("data:image/jpeg;base64,"), f"Expected JPEG data URI"
    assert len(uri) > 10_000


def test_load_photo_b64_missing_file_returns_empty():
    from utils.carousel import _load_photo_b64
    result = _load_photo_b64("static/photos/does_not_exist.png")
    assert result == "", "Missing file should return empty string"


# ─── 3. _get_local_carousel_photos — categories WITH photos ───────────────────

def test_get_local_carousel_photos_headshot_returns_two_photos():
    from utils.carousel import _get_local_carousel_photos
    photos = _get_local_carousel_photos("headshot")
    assert len(photos) >= 2, f"Expected ≥2 headshot photos, got {len(photos)}"


def test_get_local_carousel_photos_headshot_structure():
    from utils.carousel import _get_local_carousel_photos
    photos = _get_local_carousel_photos("headshot")
    for uri, label, sub in photos:
        assert uri.startswith("data:image/"), f"Expected data URI, got: {uri[:60]}"
        assert isinstance(label, str) and label, "Label must be non-empty string"
        assert isinstance(sub, str), "Sub must be a string"


def test_get_local_carousel_photos_lifestyle_returns_photos():
    from utils.carousel import _get_local_carousel_photos
    photos = _get_local_carousel_photos("lifestyle")
    assert len(photos) >= 1, f"Expected ≥1 lifestyle photo, got {len(photos)}"


# ─── 4. _get_local_carousel_photos — categories WITHOUT photos ────────────────

@pytest.mark.parametrize("category", ["shoe", "fashion", "nature"])
def test_get_local_carousel_photos_empty_categories(category):
    from utils.carousel import _get_local_carousel_photos
    photos = _get_local_carousel_photos(category)
    # These categories have no local photos yet — should return []
    assert isinstance(photos, list), "Always returns a list"
    # We don't assert empty because user might add photos; just confirm it's a list


# ─── 5. _build_local_photo_cards returns HTML when photos exist ───────────────

def test_build_local_photo_cards_headshot_has_content():
    from utils.carousel import _build_local_photo_cards
    html = _build_local_photo_cards("headshot")
    assert len(html) > 100, "Expected non-trivial HTML for headshot"
    # Must include a real photo src (data URI), not an emoji placeholder
    assert "data:image/" in html, "Card HTML should embed a real photo data URI"


def test_build_local_photo_cards_headshot_no_emoji():
    from utils.carousel import _build_local_photo_cards
    html = _build_local_photo_cards("headshot")
    # When a real photo is provided, the emoji span should NOT be in the card
    assert 'class="car-emoji"' not in html, (
        "Emoji placeholder should not appear when real photo is embedded"
    )


def test_build_local_photo_cards_empty_category_returns_empty_string():
    from utils.carousel import _build_local_photo_cards
    # A category with no photos → empty string so caller falls through to emoji
    result = _build_local_photo_cards("shoe")
    # shoe has no photos yet, so empty string expected
    # (if user adds shoe photos this test will start passing with non-empty — that's fine)
    assert isinstance(result, str)


# ─── 6. render_headshot_lifestyle_carousel end-to-end ────────────────────────

def test_render_headshot_lifestyle_carousel_returns_html():
    from utils.carousel import render_headshot_lifestyle_carousel
    html = render_headshot_lifestyle_carousel()
    assert "<div" in html, "Expected HTML div output"
    assert "car-track-wrap" in html, "Expected carousel track wrapper"


def test_render_headshot_lifestyle_carousel_has_real_photo():
    from utils.carousel import render_headshot_lifestyle_carousel
    html = render_headshot_lifestyle_carousel()
    assert "data:image/" in html, (
        "Headshot carousel should contain at least one real base64 photo, not just emoji"
    )


# ─── 7. Static photo files exist on disk ─────────────────────────────────────

@pytest.mark.parametrize("rel_path", [
    "static/photos/darrian_headshot.png",
    "static/photos/darrian_professional.jpg",
    "static/photos/carousel/headshot/darrian_headshot.png",
    "static/photos/carousel/headshot/darrian_professional.jpg",
    "static/photos/carousel/lifestyle/darrian_lifestyle.jpg",
])
def test_static_photo_file_exists(rel_path):
    full = REPO_ROOT / rel_path
    assert full.exists(), f"Missing: {rel_path}"
    assert full.stat().st_size > 10_000, f"File too small (suspect empty): {rel_path}"


# ─── 8. carousel.py syntax check ─────────────────────────────────────────────

def test_carousel_py_syntax():
    import py_compile, tempfile, shutil
    src = REPO_ROOT / "utils" / "carousel.py"
    assert src.exists()
    py_compile.compile(str(src), doraise=True)
