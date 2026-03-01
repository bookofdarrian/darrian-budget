"""
Unit tests for the budget application.
Run with: pytest tests/unit/ -v
"""

import sys
import types
import pytest


def _stub_streamlit():
    """Minimal streamlit stub so auth/util modules can be imported in tests."""
    mod = types.ModuleType("streamlit")
    mod.set_page_config = lambda **k: None
    mod.markdown = lambda *a, **k: None
    mod.title = lambda *a, **k: None
    mod.write = lambda *a, **k: None
    mod.sidebar = types.SimpleNamespace(
        markdown=lambda *a, **k: None,
        page_link=lambda *a, **k: None,
    )
    mod.session_state = {}
    mod.rerun = lambda: None
    mod.stop = lambda: None
    sys.modules["streamlit"] = mod
    return mod


class TestBudgetApp:
    """Test cases for the main budget app."""

    def test_app_imports(self):
        """Verify core imports work (streamlit stubbed for test env)."""
        _stub_streamlit()
        try:
            import pandas  # noqa: F401
            from utils.db import init_db  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_database_connection(self):
        """Verify database can be initialized."""
        try:
            from utils.db import init_db
            init_db()
            assert True
        except Exception as e:
            pytest.fail(f"Database initialization failed: {e}")

    @pytest.mark.unit
    def test_auth_module(self):
        """Test authentication utilities (streamlit stubbed for test env)."""
        _stub_streamlit()
        try:
            # Force reload after stubbing streamlit
            if "utils.auth" in sys.modules:
                del sys.modules["utils.auth"]
            from utils.auth import require_login  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Auth import failed: {e}")
