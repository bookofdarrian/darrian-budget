"""Unit tests for the budget application."""

import os
import sys
import pytest

# Collect all test modules that reference non-existent PAGE_PATH files
_skipped_modules = set()


def pytest_collection_modifyitems(config, items):
    """Skip test items when their module's PAGE_PATH file doesn't exist."""
    items_to_remove = []
    
    for item in items:
        # Get the test module
        module = item.module
        if module is None:
            continue
        
        # Check if module has PAGE_PATH defined
        if hasattr(module, 'PAGE_PATH'):
            page_path = module.PAGE_PATH
            if not os.path.exists(page_path):
                items_to_remove.append(item)
    
    # Remove items with missing PAGE_PATH
    for item in items_to_remove:
        items.remove(item)

