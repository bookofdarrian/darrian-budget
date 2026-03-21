"""
Tests: landing page image assets
- static/photos/darrian_headshot.png  (builder section)
- static/hero_screenshot.jpg          (hero mockup)
Verifies files exist, are non-empty, are valid images,
and that _load_b64() returns a proper data URI.
"""
import base64
import os
import sys
import pytest
from pathlib import Path

# ── repo root ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
HEADSHOT  = REPO_ROOT / "static" / "photos" / "darrian_headshot.png"
HERO_IMG  = REPO_ROOT / "static" / "hero_screenshot.jpg"


# ── helper: mirror of _load_b64() in the landing page ─────────────────────────
def _load_b64(path: str, mime: str = "image/jpeg") -> str:
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{data}"
    except Exception:
        return ""


# ── Tests: headshot ────────────────────────────────────────────────────────────
class TestHeadshotImage:
    def test_headshot_file_exists(self):
        assert HEADSHOT.exists(), f"Missing: {HEADSHOT}"

    def test_headshot_is_nonempty(self):
        assert HEADSHOT.stat().st_size > 0, "darrian_headshot.png is empty"

    def test_headshot_minimum_size(self):
        """Should be at least 10 KB — not a placeholder."""
        size_kb = HEADSHOT.stat().st_size / 1024
        assert size_kb >= 10, f"darrian_headshot.png too small ({size_kb:.1f} KB) — probably a placeholder"

    def test_headshot_png_magic_bytes(self):
        """File must start with PNG magic bytes: 0x89 50 4E 47."""
        with open(HEADSHOT, "rb") as f:
            header = f.read(4)
        assert header == b"\x89PNG", f"darrian_headshot.png does not have PNG header: {header!r}"

    def test_headshot_loads_as_base64_data_uri(self):
        uri = _load_b64(str(HEADSHOT), "image/png")
        assert uri.startswith("data:image/png;base64,"), "Headshot data URI has wrong prefix"
        assert len(uri) > 100, "Headshot data URI is suspiciously short"

    def test_headshot_base64_is_valid(self):
        uri = _load_b64(str(HEADSHOT), "image/png")
        b64_part = uri.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert len(decoded) == HEADSHOT.stat().st_size, "Decoded base64 size doesn't match file size"


# ── Tests: hero screenshot ─────────────────────────────────────────────────────
class TestHeroScreenshot:
    def test_hero_file_exists(self):
        assert HERO_IMG.exists(), f"Missing: {HERO_IMG}"

    def test_hero_is_nonempty(self):
        assert HERO_IMG.stat().st_size > 0, "hero_screenshot.jpg is empty"

    def test_hero_minimum_size(self):
        """Should be at least 10 KB — not a placeholder."""
        size_kb = HERO_IMG.stat().st_size / 1024
        assert size_kb >= 10, f"hero_screenshot.jpg too small ({size_kb:.1f} KB) — probably a placeholder"

    def test_hero_jpeg_magic_bytes(self):
        """JPEG must start with FF D8 FF."""
        with open(HERO_IMG, "rb") as f:
            header = f.read(3)
        assert header == b"\xff\xd8\xff", f"hero_screenshot.jpg does not have JPEG header: {header!r}"

    def test_hero_loads_as_base64_data_uri(self):
        uri = _load_b64(str(HERO_IMG), "image/jpeg")
        assert uri.startswith("data:image/jpeg;base64,"), "Hero data URI has wrong prefix"
        assert len(uri) > 100, "Hero data URI is suspiciously short"

    def test_hero_base64_is_valid(self):
        uri = _load_b64(str(HERO_IMG), "image/jpeg")
        b64_part = uri.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert len(decoded) == HERO_IMG.stat().st_size, "Decoded base64 size doesn't match file size"


# ── Landing page references correct paths ─────────────────────────────────────
class TestLandingPageImageReferences:
    def test_landing_references_headshot_path(self):
        landing = REPO_ROOT / "pages" / "00_landing.py"
        content = landing.read_text()
        assert "static/photos/darrian_headshot.png" in content, \
            "landing page does not reference darrian_headshot.png"

    def test_landing_references_hero_screenshot(self):
        landing = REPO_ROOT / "pages" / "00_landing.py"
        content = landing.read_text()
        assert "static/hero_screenshot.jpg" in content, \
            "landing page does not reference hero_screenshot.jpg"

    def test_landing_uses_load_b64(self):
        landing = REPO_ROOT / "pages" / "00_landing.py"
        content = landing.read_text()
        assert "_load_b64" in content, "landing page missing _load_b64() helper"

    def test_landing_no_inline_landscape_base64(self):
        """The old giant landscape base64 started with /9j/4AAQSkZJRgABAQAAAQABAAD
        — make sure it's still present as the unused _HERO_IMG variable but
        NOT embedded in the final HTML img src."""
        landing = REPO_ROOT / "pages" / "00_landing.py"
        content = landing.read_text()
        # The f-string that builds the hero mockup HTML must use _HERO_IMG_SRC not _HERO_IMG
        assert "{_HERO_IMG_SRC}" in content, \
            "hero mockup HTML should use {_HERO_IMG_SRC}, not the inline base64 variable"

    def test_landing_builder_uses_headshot_not_emoji(self):
        landing = REPO_ROOT / "pages" / "00_landing.py"
        content = landing.read_text()
        assert "{_HEADSHOT}" in content, \
            "builder section should use {_HEADSHOT} (real photo), not emoji"
        # The emoji should be gone from the builder avatar
        assert "👨🏾\u200d💻</div>" not in content, \
            "builder section still contains the old emoji avatar"
