"""
Tests for pages/00_landing.py business licensing section.
Verifies: import, color constants, For-Business tier content strings, pricing values.
"""
import importlib
import importlib.util
import sys
import types
import unittest


# ---------------------------------------------------------------------------
# Minimal Streamlit stub so the page module can be imported without a running
# Streamlit server.
# ---------------------------------------------------------------------------
def _build_streamlit_stub():
    """Return a minimal module-level stub for streamlit."""
    st = types.ModuleType("streamlit")

    # No-op callables for every st.* call in the landing page
    for attr in (
        "set_page_config", "markdown", "button", "columns",
        "switch_page", "write", "error", "info", "success",
        "title", "header", "subheader", "caption",
    ):
        setattr(st, attr, lambda *a, **kw: None)

    # columns() must return context managers
    class _FakeCol:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        # Support attribute access for widget calls inside `with col:`
        def __getattr__(self, _):
            return lambda *a, **kw: None

    st.columns = lambda *a, **kw: [_FakeCol() for _ in range(3)]
    return st


class TestLandingPageImport(unittest.TestCase):
    """The landing page module must import cleanly under a Streamlit stub."""

    @classmethod
    def setUpClass(cls):
        # Inject stub before importing the page
        sys.modules["streamlit"] = _build_streamlit_stub()
        spec = importlib.util.spec_from_file_location(
            "landing_page",
            "pages/00_landing.py",
        )
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_module_loads(self):
        """Page imports without raising exceptions."""
        self.assertIsNotNone(self.mod)

    def test_color_constants_defined(self):
        """Core color constants must be present and start with '#'."""
        for const in ("PEACH", "PEACH_LIGHT", "PEACH_DARK", "BG_MAIN", "BG_CARD",
                      "TEXT_MAIN", "TEXT_MUTED", "SUCCESS"):
            with self.subTest(const=const):
                val = getattr(self.mod, const)
                self.assertTrue(
                    val.startswith("#"),
                    f"{const}={val!r} should be a hex color",
                )

    def test_peach_glow_rgba(self):
        """PEACH_GLOW must be an rgba() value."""
        self.assertTrue(
            self.mod.PEACH_GLOW.startswith("rgba("),
            f"PEACH_GLOW={self.mod.PEACH_GLOW!r}",
        )

    def test_business_tier_prices(self):
        """
        The source code must contain the three business-tier price strings
        as rendered in the For-Business section.
        """
        import inspect
        source = inspect.getsource(self.mod)
        for price_str in ("$19", "$79", "$249"):
            with self.subTest(price=price_str):
                self.assertIn(
                    price_str,
                    source,
                    f"Expected business tier price {price_str!r} in landing page source",
                )

    def test_for_business_section_anchor(self):
        """The 'for-business' anchor must appear in the page source."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn(
            "for-business",
            source,
            "Expected id='for-business' section in landing page",
        )

    def test_agency_white_label_mentioned(self):
        """Agency / white-label copy must appear in source."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn(
            "White-Label",
            source,
            "Expected Agency White-Label content in landing page",
        )

    def test_download_self_host_mentioned(self):
        """Download & Self-Host option must appear in source."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn(
            "Self-Host",
            source,
            "Expected Download & Self-Host content in landing page",
        )

    def test_nav_for_business_link(self):
        """Nav must contain the 'For Business' link anchor."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn(
            "#for-business",
            source,
            "Expected #for-business nav link in landing page",
        )

    def test_pricing_free_plan(self):
        """Free plan ($0) must still appear in pricing section."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn("Free Plan", source)

    def test_pricing_pro_plan(self):
        """Pro plan ($4.99) must still appear in pricing section."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn("4.99", source)

    def test_json_ld_present(self):
        """JSON-LD structured data script tag must be present."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn("application/ld+json", source)

    def test_faq_section_present(self):
        """FAQ section must be present."""
        import inspect
        source = inspect.getsource(self.mod)
        self.assertIn("id=\"faq\"", source)


if __name__ == "__main__":
    unittest.main()
