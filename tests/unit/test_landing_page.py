"""
Unit tests for pages/00_landing.py — Public Landing Page
"""

import importlib.util
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def test_landing_page_file_exists():
    """Landing page file exists at the expected path."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "pages", "00_landing.py"
    )
    assert os.path.exists(path), "pages/00_landing.py not found"


def test_landing_page_importable():
    """Landing page can be loaded as a module spec without errors."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "pages", "00_landing.py"
    )
    spec = importlib.util.spec_from_file_location("landing", path)
    assert spec is not None, "Could not create module spec for 00_landing.py"


def test_landing_page_has_no_require_login():
    """
    Landing page must NOT call require_login() — it is a public page.
    Visitors who are not logged in must be able to see it.
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "pages", "00_landing.py"
    )
    with open(path, "r") as f:
        content = f.read()
    assert "require_login()" not in content, (
        "Landing page must NOT call require_login() — it is public-facing"
    )


def test_landing_page_has_no_hardcoded_keys():
    """Landing page must not contain hardcoded API keys or secrets."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "pages", "00_landing.py"
    )
    with open(path, "r") as f:
        content = f.read()
    # Check for common secret patterns
    assert "sk-ant-" not in content, "Anthropic key detected in landing page"
    assert "sk_live_" not in content, "Stripe live key detected in landing page"
    assert "APP_PASSWORD" not in content, "APP_PASSWORD referenced in landing page"


def test_landing_page_has_cta_buttons():
    """Landing page contains at least one call-to-action referencing app.py."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "pages", "00_landing.py"
    )
    with open(path, "r") as f:
        content = f.read()
    assert "app.py" in content, "Landing page should link to app.py for sign-up/sign-in"
    assert "switch_page" in content, "Landing page should use st.switch_page() for CTA navigation"


def test_landing_page_has_set_page_config():
    """Landing page calls st.set_page_config at the top."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "pages", "00_landing.py"
    )
    with open(path, "r") as f:
        content = f.read()
    assert "st.set_page_config" in content, "Landing page must call st.set_page_config"


def test_landing_page_mentions_brand():
    """Landing page mentions the Peach State Savings brand."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "pages", "00_landing.py"
    )
    with open(path, "r") as f:
        content = f.read()
    assert "Peach State Savings" in content, "Brand name not found in landing page"
    assert "🍑" in content, "Brand emoji not found in landing page"


def test_auth_page_links_to_landing():
    """auth.py _show_auth_page must link to the landing page via /landing URL."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "utils", "auth.py"
    )
    with open(path, "r") as f:
        content = f.read()
    # Streamlit strips numeric prefix: 00_landing.py → /landing URL
    assert "'/landing'" in content or '"/landing"' in content, (
        "auth.py login page should link to /landing (Streamlit strips 00_ prefix)"
    )
