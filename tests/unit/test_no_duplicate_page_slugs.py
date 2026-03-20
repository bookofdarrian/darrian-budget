"""
test_no_duplicate_page_slugs.py
================================
Prevents the recurring StreamlitAPIException:
  "Multiple Pages specified with URL pathname X. URL pathnames must be unique."

Streamlit derives a page's URL slug from the filename (after stripping the
leading number prefix and .py extension).  If two files share the same slug,
the app crashes on startup for EVERY user.

This test runs on every CI push and blocks any commit that introduces a
duplicate slug in the pages/ directory.
"""
import os
import re
import collections
import pytest

PAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "pages")


def _get_slug_map():
    """Return {slug: [filename, ...]} for all .py files in pages/."""
    pages_dir = os.path.abspath(PAGES_DIR)
    slug_map = collections.defaultdict(list)
    for fname in sorted(os.listdir(pages_dir)):
        if fname.endswith(".py"):
            # Streamlit strips leading digits+underscore to form the slug
            slug = re.sub(r"^\d+_", "", fname[:-3])
            slug_map[slug].append(fname)
    return slug_map


def test_no_duplicate_page_slugs():
    """All pages/ filenames must have unique URL slugs.

    If this test fails, two or more page files share the same slug and
    will crash the Streamlit app on startup.  Remove or rename the
    duplicate file(s) before merging.
    """
    slug_map = _get_slug_map()
    dupes = {slug: files for slug, files in slug_map.items() if len(files) > 1}

    if dupes:
        lines = ["\nDuplicate Streamlit page slugs detected — app will crash!\n"]
        for slug, files in sorted(dupes.items()):
            lines.append(f"  slug '{slug}':")
            for f in sorted(files):
                lines.append(f"    pages/{f}")
        lines.append("\nFix: remove or rename the older duplicate file(s).")
        pytest.fail("\n".join(lines))


def test_pages_dir_exists():
    """Sanity-check that the pages directory is reachable from this test."""
    assert os.path.isdir(os.path.abspath(PAGES_DIR)), \
        f"pages/ directory not found at {os.path.abspath(PAGES_DIR)}"


def test_page_count_reasonable():
    """Sanity-check: we expect at least 10 pages and fewer than 500."""
    slug_map = _get_slug_map()
    count = len(slug_map)
    assert count >= 10, f"Too few pages ({count}) — is pages/ empty?"
    assert count < 500, f"Unreasonably many pages ({count}) — check for runaway generation"
