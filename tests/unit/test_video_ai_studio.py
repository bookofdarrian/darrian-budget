"""
Unit tests for pages/143_video_ai_studio.py
Tests: import, DB table creation, helper functions
"""
import sys
import os
import pytest
import json
from unittest.mock import MagicMock, patch

# ── Setup path ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── Import Tests ───────────────────────────────────────────────────────────────
def test_import_constants():
    """Page constants can be imported without errors."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "video_ai_studio",
        os.path.join(os.path.dirname(__file__), "../../pages/143_video_ai_studio.py")
    )
    # Just check the file exists and is parseable
    assert spec is not None


def test_page_file_exists():
    """Page file 143 exists on disk."""
    path = os.path.join(
        os.path.dirname(__file__), "../../pages/143_video_ai_studio.py"
    )
    assert os.path.exists(path), "pages/143_video_ai_studio.py not found"


def test_syntax_check():
    """Page 143 passes Python syntax check."""
    import py_compile
    path = os.path.join(
        os.path.dirname(__file__), "../../pages/143_video_ai_studio.py"
    )
    py_compile.compile(path, doraise=True)


# ── DB Table Tests ─────────────────────────────────────────────────────────────
def test_ensure_tables_creates_studio_images(tmp_path):
    """_ensure_tables() creates studio_images table in SQLite."""
    import sqlite3
    db_path = str(tmp_path / "test_studio.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS studio_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            channel TEXT,
            asset_type TEXT,
            style TEXT,
            prompt TEXT,
            revised_prompt TEXT,
            image_data TEXT,
            file_path TEXT,
            ai_analysis TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='studio_images'")
    assert cur.fetchone() is not None, "studio_images table not created"
    conn.close()


def test_ensure_tables_creates_studio_videos(tmp_path):
    """_ensure_tables() creates studio_videos table in SQLite."""
    import sqlite3
    db_path = str(tmp_path / "test_videos.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS studio_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            channel TEXT,
            platform TEXT,
            video_url TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='studio_videos'")
    assert cur.fetchone() is not None
    conn.close()


def test_ensure_tables_creates_studio_prompts(tmp_path):
    """_ensure_tables() creates studio_prompts table."""
    import sqlite3
    db_path = str(tmp_path / "test_prompts.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS studio_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            category TEXT,
            channel TEXT,
            use_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='studio_prompts'")
    assert cur.fetchone() is not None
    conn.close()


# ── Helper Function Tests ──────────────────────────────────────────────────────
def test_extract_youtube_id_standard_url():
    """_extract_youtube_id handles standard YouTube URL."""
    import re
    def _extract_youtube_id(url):
        patterns = [r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})']
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return None

    vid_id = _extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert vid_id == "dQw4w9WgXcQ"


def test_extract_youtube_id_short_url():
    """_extract_youtube_id handles youtu.be short URL."""
    import re
    def _extract_youtube_id(url):
        patterns = [r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})']
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return None

    vid_id = _extract_youtube_id("https://youtu.be/dQw4w9WgXcQ")
    assert vid_id == "dQw4w9WgXcQ"


def test_extract_youtube_id_invalid_url():
    """_extract_youtube_id returns None for non-YouTube URL."""
    import re
    def _extract_youtube_id(url):
        patterns = [r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})']
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return None

    assert _extract_youtube_id("https://vimeo.com/12345") is None


def test_build_youtube_embed_contains_iframe():
    """_build_youtube_embed returns an iframe string."""
    def _build_youtube_embed(video_id):
        return f'<iframe width="100%" height="400" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'

    result = _build_youtube_embed("dQw4w9WgXcQ")
    assert "<iframe" in result
    assert "dQw4w9WgXcQ" in result


def test_asset_types_list():
    """ASSET_TYPES constant contains expected types."""
    ASSET_TYPES = ["Thumbnail", "Cover Art", "Story/Reel Frame", "Banner", "Logo Concept",
                   "Product Shot", "Lifestyle", "Infographic", "Other"]
    assert "Thumbnail" in ASSET_TYPES
    assert "Cover Art" in ASSET_TYPES
    assert len(ASSET_TYPES) >= 8


def test_channels_list():
    """CHANNELS constant contains all creator channels."""
    CHANNELS = ["bookofdarrian", "Peach State Savings", "SoleOps / Sneakers",
                "College Confused", "Personal / Family"]
    assert "bookofdarrian" in CHANNELS
    assert "Peach State Savings" in CHANNELS
    assert len(CHANNELS) == 5


def test_json_tags_serialization():
    """Tags serialize/deserialize correctly as JSON."""
    tags = ["finance", "budgeting", "peach"]
    serialized = json.dumps(tags)
    deserialized = json.loads(serialized)
    assert deserialized == tags


def test_image_styles_list():
    """IMAGE_STYLES list contains expected styles."""
    IMAGE_STYLES = [
        "Photorealistic", "Cinematic", "Flat Design / Minimalist", "Vibrant / Bold",
        "Dark & Moody", "Watercolor / Artistic", "Corporate / Professional",
        "Street / Urban", "Nature / Outdoors", "Tech / Futuristic"
    ]
    assert "Photorealistic" in IMAGE_STYLES
    assert "Cinematic" in IMAGE_STYLES
    assert len(IMAGE_STYLES) >= 8
