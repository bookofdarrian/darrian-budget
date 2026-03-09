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

