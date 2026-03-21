"""
Tests: landing page image assets
- static/photos/darrian_headshot.png   (builder section)
- static/dashboard_screenshot.png     (hero mockup)
Verifies files exist, are non-empty, are valid images,
and that _load_b64() returns a proper data URI.
"""
import base64
import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
HEADSHOT  = REPO_ROOT / "static" / "photos" / "darrian_headshot.png"
HERO_IMG  = REPO_ROOT / "static" / "dashboard_screenshot.png"


def _load_b64(path: str, mime: str = "image/jpeg") -> str:
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{data}"
    except Exception:
        return ""


class TestHeadshotImage:
    def test_headshot_file_exists(self):
        assert HEADSHOT.exists(), f"Missing: {HEADSHOT}"

    def test_headshot_is_nonempty(self):
        assert HEADSHOT.stat().st_size > 0

    def test_headshot_minimum_size(self):
        assert HEADSHOT.stat().st_size / 1024 >= 10

    def test_headshot_png_magic_bytes(self):
        with open(HEADSHOT, "rb") as f:
            header = f.read(4)
        assert header == b"\x89PNG"

    def test_headshot_loads_as_base64_data_uri(self):
        uri = _load_b64(str(HEADSHOT), "image/png")
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 100

    def test_headshot_base64_is_valid(self):
        uri = _load_b64(str(HEADSHOT), "image/png")
        decoded = base64.b64decode(uri.split(",", 1)[1])
        assert len(decoded) == HEADSHOT.stat().st_size


class TestHeroScreenshot:
    def test_hero_file_exists(self):
        assert HERO_IMG.exists(), f"Missing: {HERO_IMG}"

    def test_hero_is_nonempty(self):
        assert HERO_IMG.stat().st_size > 0

    def test_hero_minimum_size(self):
        assert HERO_IMG.stat().st_size / 1024 >= 10

    def test_hero_png_magic_bytes(self):
        """PNG must start with 89 50 4E 47."""
        with open(HERO_IMG, "rb") as f:
            header = f.read(4)
        assert header == b"\x89PNG", f"dashboard_screenshot.png does not have PNG header: {header!r}"

    def test_hero_loads_as_base64_data_uri(self):
        uri = _load_b64(str(HERO_IMG), "image/png")
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 100

    def test_hero_base64_is_valid(self):
        uri = _load_b64(str(HERO_IMG), "image/png")
        decoded = base64.b64decode(uri.split(",", 1)[1])
        assert len(decoded) == HERO_IMG.stat().st_size


class TestLandingPageImageReferences:
    def test_landing_references_headshot_path(self):
        content = (REPO_ROOT / "pages" / "00_landing.py").read_text()
        assert "static/photos/darrian_headshot.png" in content

    def test_landing_references_dashboard_screenshot(self):
        content = (REPO_ROOT / "pages" / "00_landing.py").read_text()
        assert "static/dashboard_screenshot.png" in content

    def test_landing_uses_load_b64(self):
        content = (REPO_ROOT / "pages" / "00_landing.py").read_text()
        assert "_load_b64" in content

    def test_landing_hero_mockup_uses_hero_img_src(self):
        content = (REPO_ROOT / "pages" / "00_landing.py").read_text()
        assert "{_HERO_IMG_SRC}" in content

    def test_landing_builder_uses_headshot(self):
        content = (REPO_ROOT / "pages" / "00_landing.py").read_text()
        assert "{_HEADSHOT}" in content
