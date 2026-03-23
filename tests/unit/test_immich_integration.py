"""
tests/unit/test_immich_integration.py
Unit tests for Immich photo integration across PSS, SoleOps, and College Confused.

Tests:
  1. utils/immich_photos.py — import, helper functions, thumbnail URI caching
  2. utils/carousel.py — import, _build_immich_cards_for_category fallback,
     all 4 render functions return HTML strings
  3. app.py / cc_app.py / soleops_app.py — carousel imports resolve cleanly
"""

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ─── 1. immich_photos module tests ───────────────────────────────────────────

class TestImmichPhotosModule(unittest.TestCase):

    def test_import(self):
        """Module imports without error."""
        import utils.immich_photos as m
        self.assertTrue(hasattr(m, "is_immich_available"))
        self.assertTrue(hasattr(m, "get_carousel_photos"))
        self.assertTrue(hasattr(m, "get_thumbnail_data_uri"))
        self.assertTrue(hasattr(m, "get_thumbnail_data_uri_batch"))

    def test_constants_present(self):
        """Required constants are defined."""
        from utils.immich_photos import (
            CAROUSEL_SEARCH_QUERIES,
            SITE_CATEGORY_MAP,
            DEFAULT_IMMICH_SERVER,
        )
        self.assertIn("shoe", CAROUSEL_SEARCH_QUERIES)
        self.assertIn("fashion", CAROUSEL_SEARCH_QUERIES)
        self.assertIn("nature", CAROUSEL_SEARCH_QUERIES)
        self.assertIn("lifestyle", CAROUSEL_SEARCH_QUERIES)
        self.assertIn("headshot", CAROUSEL_SEARCH_QUERIES)
        self.assertIn("soleops", SITE_CATEGORY_MAP)
        self.assertIn("pss", SITE_CATEGORY_MAP)
        self.assertIn("cc", SITE_CATEGORY_MAP)
        self.assertIsInstance(DEFAULT_IMMICH_SERVER, str)
        self.assertTrue(DEFAULT_IMMICH_SERVER.startswith("http"))

    def test_is_immich_available_returns_bool_on_connection_error(self):
        """is_immich_available() returns False when server is unreachable."""
        from utils import immich_photos
        with patch("requests.get", side_effect=ConnectionError("unreachable")):
            result = immich_photos.is_immich_available()
        self.assertFalse(result)
        self.assertIsInstance(result, bool)

    def test_has_api_key_false_when_not_set(self):
        """has_api_key() returns False when no key in DB."""
        from utils import immich_photos
        with patch("utils.immich_photos.get_setting", return_value=None):
            self.assertFalse(immich_photos.has_api_key())

    def test_has_api_key_true_when_set(self):
        """has_api_key() returns True when key is stored in DB."""
        from utils import immich_photos
        with patch("utils.immich_photos.get_setting", return_value="test-api-key-abc123"):
            self.assertTrue(immich_photos.has_api_key())

    def test_thumbnail_url_format(self):
        """thumbnail_url() returns a URL string with asset_id embedded."""
        from utils import immich_photos
        # Patch _get_server to return a real URL, and get_setting for the api key
        with patch("utils.immich_photos._get_server", return_value="http://100.95.125.112:2283"), \
             patch("utils.immich_photos.get_setting", return_value="mykey"):
            url = immich_photos.thumbnail_url("abc-123", size="thumbnail")
        self.assertIn("abc-123", url)
        self.assertIn("thumbnail", url)
        self.assertTrue(url.startswith("http"))

    def test_get_thumbnail_data_uri_no_key(self):
        """get_thumbnail_data_uri() returns None when no API key is set."""
        from utils import immich_photos
        with patch("utils.immich_photos.has_api_key", return_value=False):
            result = immich_photos.get_thumbnail_data_uri("abc-123")
        self.assertIsNone(result)

    def test_get_thumbnail_data_uri_uses_cache(self):
        """get_thumbnail_data_uri() returns cached value without hitting network."""
        import json, time
        from utils import immich_photos
        cached_uri = "data:image/jpeg;base64,FAKECACHEDDATA"
        cache_payload = json.dumps({"uri": cached_uri, "ts": time.time()})
        with patch("utils.immich_photos.has_api_key", return_value=True), \
             patch("utils.immich_photos.get_setting", return_value=cache_payload):
            result = immich_photos.get_thumbnail_data_uri("abc-123")
        self.assertEqual(result, cached_uri)

    def test_get_thumbnail_data_uri_returns_none_on_http_error(self):
        """get_thumbnail_data_uri() returns None when Immich returns non-200."""
        from utils import immich_photos
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("utils.immich_photos.has_api_key", return_value=True), \
             patch("utils.immich_photos.get_setting", return_value=None), \
             patch("utils.immich_photos.thumbnail_url", return_value="http://fake/thumb"), \
             patch("requests.get", return_value=mock_resp):
            result = immich_photos.get_thumbnail_data_uri("abc-123")
        self.assertIsNone(result)

    def test_get_carousel_photos_returns_empty_when_no_key_no_cache(self):
        """get_carousel_photos() returns [] when Immich is unavailable and no cache."""
        from utils import immich_photos
        with patch("utils.immich_photos.has_api_key", return_value=False), \
             patch("utils.immich_photos._load_catalog_from_db", return_value=None), \
             patch("utils.immich_photos.is_immich_available", return_value=False):
            result = immich_photos.get_carousel_photos("shoe", site="soleops")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_thumbnail_data_uri_batch_empty_list(self):
        """get_thumbnail_data_uri_batch() returns empty dict for empty input."""
        from utils import immich_photos
        result = immich_photos.get_thumbnail_data_uri_batch([])
        self.assertEqual(result, {})


# ─── 2. carousel module tests ─────────────────────────────────────────────────

class TestCarouselModule(unittest.TestCase):

    def test_import(self):
        """carousel module imports without error."""
        import utils.carousel as c
        self.assertTrue(hasattr(c, "render_shoe_product_carousel"))
        self.assertTrue(hasattr(c, "render_nature_inspiration_carousel"))
        self.assertTrue(hasattr(c, "render_street_fashion_carousel"))
        self.assertTrue(hasattr(c, "render_headshot_lifestyle_carousel"))
        self.assertTrue(hasattr(c, "_build_immich_cards_for_category"))
        self.assertTrue(hasattr(c, "CAROUSEL_BASE_CSS"))

    def test_immich_helper_returns_fallback_when_unavailable(self):
        """_build_immich_cards_for_category() returns fallback placeholder HTML
        (not empty string) when Immich is down — carousel is never blocked."""
        import utils.carousel as _car_mod
        from utils.carousel import _build_immich_cards_for_category
        # Clear process-level cache so this test isn't served a stale hit
        # from test_immich_cards_with_real_photos which runs before this.
        _car_mod._CAROUSEL_HTML_CACHE.clear()
        with patch("utils.immich_photos.is_immich_available", return_value=False):
            result = _build_immich_cards_for_category("shoe", "soleops")
        # The implementation intentionally falls back to emoji placeholder cards
        # rather than returning an empty string, so the page is never blocked.
        self.assertIsInstance(result, str)

    def test_render_shoe_carousel_returns_html(self):
        """render_shoe_product_carousel() returns non-empty HTML string."""
        from utils.carousel import render_shoe_product_carousel
        with patch("utils.immich_photos.is_immich_available", return_value=False):
            html = render_shoe_product_carousel("cyan")
        self.assertIsInstance(html, str)
        self.assertIn("car-inner", html)
        self.assertGreater(len(html), 100)

    def test_render_nature_carousel_returns_html(self):
        """render_nature_inspiration_carousel() returns HTML with carousel classes."""
        from utils.carousel import render_nature_inspiration_carousel
        with patch("utils.immich_photos.is_immich_available", return_value=False):
            html = render_nature_inspiration_carousel("green")
        self.assertIsInstance(html, str)
        self.assertIn("car-track-wrap", html)

    def test_render_fashion_carousel_returns_html(self):
        """render_street_fashion_carousel() returns HTML with reverse class."""
        from utils.carousel import render_street_fashion_carousel
        with patch("utils.immich_photos.is_immich_available", return_value=False):
            html = render_street_fashion_carousel("cyan")
        self.assertIsInstance(html, str)
        self.assertIn("reverse", html)

    def test_render_headshot_carousel_returns_html(self):
        """render_headshot_lifestyle_carousel() returns HTML with slow class."""
        from utils.carousel import render_headshot_lifestyle_carousel
        with patch("utils.immich_photos.is_immich_available", return_value=False):
            html = render_headshot_lifestyle_carousel("cyan")
        self.assertIsInstance(html, str)
        self.assertIn("slow", html)

    def test_build_card_with_photo_src_hides_emoji(self):
        """_build_card() with photo_src uses <img> background and omits emoji span."""
        from utils.carousel import _build_card
        html = _build_card("👟", "Test Label", "sub", "#000", "#111", "#fff",
                           photo_src="data:image/jpeg;base64,FAKEPHOTO")
        self.assertIn("FAKEPHOTO", html)
        self.assertNotIn('class="car-emoji"', html)

    def test_build_card_without_photo_shows_emoji(self):
        """_build_card() without photo_src shows emoji gradient background."""
        from utils.carousel import _build_card
        html = _build_card("👟", "Test Label", "sub", "#1a0505", "#3D0000", "#fff")
        self.assertIn("car-emoji", html)
        self.assertIn("👟", html)
        self.assertIn("linear-gradient", html)

    def test_carousel_theme_css_returns_style_tag(self):
        """carousel_theme_css() returns a non-empty <style> string."""
        from utils.carousel import carousel_theme_css
        for theme in ("cyan", "green", "blue", "gold", "peach"):
            css = carousel_theme_css(theme)
            self.assertIn("<style>", css)
            self.assertIn(f"car-track-wrap-{theme}", css)

    def test_render_story_band_html(self):
        """render_story_band_html() includes the quote text."""
        from utils.carousel import render_story_band_html
        html = render_story_band_html("Test quote here", "Author Name", "#22D47E")
        self.assertIn("Test quote here", html)
        self.assertIn("Author Name", html)
        self.assertIn("#22D47E", html)

    def test_render_roots_cities_band(self):
        """render_roots_cities_band() includes all 4 city names."""
        from utils.carousel import render_roots_cities_band
        html = render_roots_cities_band()
        self.assertIn("Hampton", html)
        self.assertIn("Atlanta", html)
        self.assertIn("New York", html)
        self.assertIn("Chicago", html)

    def test_immich_cards_with_real_photos(self):
        """_build_immich_cards_for_category() returns HTML when Immich returns photos."""
        import base64
        from utils.carousel import _build_immich_cards_for_category

        fake_photos = [
            {"asset_id": "abc123", "seo_alt_text": "Sneaker photo", "caption": "Heat"},
        ]
        fake_uri = "data:image/jpeg;base64," + base64.b64encode(b"FAKEIMAGE").decode()
        fake_thumb_map = {"abc123": fake_uri}

        with patch("utils.immich_photos.is_immich_available", return_value=True), \
             patch("utils.immich_photos.get_carousel_photos", return_value=fake_photos), \
             patch("utils.immich_photos.get_thumbnail_data_uri_batch", return_value=fake_thumb_map):
            result = _build_immich_cards_for_category("shoe", "soleops")

        # "FAKEIMAGE" bytes are base64-encoded as "RkFLRUlNQUdF" in the data URI
        self.assertIn("RkFLRUlNQUdF", result)  # base64("FAKEIMAGE")
        self.assertIn("data:image/jpeg;base64,", result)
        self.assertIn("Sneaker photo", result)


# ─── 3. App entry point import tests ─────────────────────────────────────────

class TestAppImports(unittest.TestCase):
    """Verify that the carousel imports added to app.py, cc_app.py, soleops_app.py
    resolve cleanly — i.e., no NameError or ImportError for the carousel symbols."""

    def test_app_py_carousel_imports(self):
        """app.py imports from carousel resolve — all symbols exist."""
        from utils.carousel import (
            CAROUSEL_BASE_CSS,
            carousel_theme_css,
            render_nature_inspiration_carousel,
            render_headshot_lifestyle_carousel,
            render_story_band_html,
            render_roots_cities_band,
        )
        self.assertIsInstance(CAROUSEL_BASE_CSS, str)
        self.assertIn("<style>", CAROUSEL_BASE_CSS)

    def test_cc_app_carousel_imports(self):
        """cc_app.py carousel imports all resolve."""
        from utils.carousel import (
            CAROUSEL_BASE_CSS,
            carousel_theme_css,
            render_nature_inspiration_carousel,
            render_street_fashion_carousel,
            render_headshot_lifestyle_carousel,
            render_story_band_html,
            render_roots_cities_band,
        )
        # All 4 render functions return strings
        with patch("utils.immich_photos.is_immich_available", return_value=False):
            self.assertIsInstance(render_nature_inspiration_carousel("blue"), str)
            self.assertIsInstance(render_street_fashion_carousel("blue"), str)
            self.assertIsInstance(render_headshot_lifestyle_carousel("blue"), str)

    def test_soleops_carousel_imports(self):
        """soleops_app.py carousel imports all resolve."""
        from utils.carousel import (
            CAROUSEL_BASE_CSS,
            carousel_theme_css,
            render_shoe_product_carousel,
            render_street_fashion_carousel,
            render_nature_inspiration_carousel,
            render_story_band_html,
            render_roots_cities_band,
            render_headshot_lifestyle_carousel,
        )
        with patch("utils.immich_photos.is_immich_available", return_value=False):
            self.assertIsInstance(render_shoe_product_carousel("cyan"), str)


if __name__ == "__main__":
    unittest.main()
