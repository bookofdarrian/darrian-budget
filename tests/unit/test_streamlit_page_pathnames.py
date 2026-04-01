import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES_DIR = os.path.join(ROOT, "pages")


def _page_slug(filename: str) -> str:
    stem = filename[:-3]
    return re.sub(r"^\d+_", "", stem)


def test_streamlit_page_pathnames_are_unique():
    page_files = [name for name in os.listdir(PAGES_DIR) if name.endswith(".py")]
    slug_map = {}

    for filename in page_files:
        slug_map.setdefault(_page_slug(filename), []).append(filename)

    collisions = {slug: files for slug, files in slug_map.items() if len(files) > 1}
    assert not collisions, f"Duplicate Streamlit pathnames found: {collisions}"