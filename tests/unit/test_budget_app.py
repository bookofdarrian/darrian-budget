"""
Unit tests for the budget application.
Run with: pytest tests/unit/ -v
"""

import pytest


class TestBudgetApp:
    """Test cases for the main budget app."""

    def test_app_imports(self):
        """Verify core imports work."""
        try:
            import streamlit  # noqa: F401
            import pandas  # noqa: F401
            from utils.db import init_db  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_database_connection(self):
        """Verify database can be initialized."""
        try:
            from utils.db import init_db
            # This should not raise an exception
            init_db()
            assert True
        except Exception as e:
            pytest.fail(f"Database initialization failed: {e}")

    @pytest.mark.unit
    def test_auth_module(self):
        """Test authentication utilities."""
        try:
            from utils.auth import require_login  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Auth import failed: {e}")
