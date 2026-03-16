"""Global pytest configuration and hooks."""

import os
import pytest


def pytest_collection_modifyitems(config, items):
    """Remove test items for pages that don't exist."""
    items_to_remove = []
    for item in items:
        # Try to get the module
        try:
            module = item.module
            if module and hasattr(module, 'PAGE_PATH'):
                page_path = getattr(module, 'PAGE_PATH')
                if page_path and not os.path.exists(page_path):
                    items_to_remove.append(item)
        except Exception:
            pass
    
    # Remove in reverse to avoid index issues
    for item in reversed(items_to_remove):
        items.remove(item)


@pytest.fixture(autouse=True)
def _isolate_db_state(monkeypatch):
    """
    Reset utils.db._active_db_path to None before every test.

    Prevents cross-test DB-path pollution when tests in other files
    (e.g. test_sandbox_and_scheduled_agents.py) monkeypatch db_mod.get_conn
    to a fake while run_scheduled_agents is imported, leaving a stale
    module-level reference that confuses later tests.

    Each test that needs a specific DB path must set it via its own
    fixture (e.g. the local tmp_db fixture in each test file).
    """
    try:
        import utils.db as db_mod
        monkeypatch.setattr(db_mod, "_active_db_path", None)
    except Exception:
        pass
    yield
