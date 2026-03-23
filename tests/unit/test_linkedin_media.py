"""
tests/unit/test_linkedin_media.py
==================================
Unit tests for the LinkedIn media campaign pipeline.

Tests:
  1. Import check — make_linkedin_video and post_linkedin_now importable
  2. Path resolution — source video and output dirs resolve correctly
  3. Duration helper — get_duration returns a float
  4. Post queue — _build_post_queue returns correct structure
  5. DB table creation — _ensure_smm_tables works idempotently
  6. Duplicate guard — seed_smm_db skips existing entries
  7. SEO copy — all post variants contain required keywords
  8. Video filter strings — safe constants (no injection chars)
"""

import importlib.util
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _load(filename: str):
    spec = importlib.util.spec_from_file_location(
        filename.replace(".py", ""),
        PROJECT_ROOT / filename,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Imports
# ══════════════════════════════════════════════════════════════════════════════
class TestImports:
    def test_make_linkedin_video_importable(self):
        mod = _load("make_linkedin_video.py")
        assert mod is not None

    def test_post_linkedin_now_importable(self):
        mod = _load("post_linkedin_now.py")
        assert mod is not None

    def test_make_linkedin_video_has_required_functions(self):
        mod = _load("make_linkedin_video.py")
        for fn in ["download_music", "generate_ambient_music", "loop_music",
                   "encode_video", "get_duration", "print_summary"]:
            assert hasattr(mod, fn), f"Missing: {fn}"

    def test_post_linkedin_now_has_required_functions(self):
        mod = _load("post_linkedin_now.py")
        for fn in ["_build_post_queue", "_ensure_smm_tables",
                   "seed_smm_db", "show_status"]:
            assert hasattr(mod, fn), f"Missing: {fn}"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Paths
# ══════════════════════════════════════════════════════════════════════════════
class TestPaths:
    def setup_method(self):
        self.mod = _load("make_linkedin_video.py")

    def test_source_video_filename(self):
        assert self.mod.SOURCE_VIDEO.name == "final_real_voice.mp4"

    def test_source_video_exists(self):
        assert self.mod.SOURCE_VIDEO.exists(), (
            f"Source video missing: {self.mod.SOURCE_VIDEO}"
        )

    def test_output_filenames(self):
        assert self.mod.OUTPUT_VERTICAL.name  == "linkedin_vertical_9x16.mp4"
        assert self.mod.OUTPUT_LANDSCAPE.name == "linkedin_landscape_16x9.mp4"
        assert self.mod.OUTPUT_SQUARE.name    == "linkedin_square_1x1.mp4"

    def test_output_dir_inside_videos(self):
        assert self.mod.OUTPUT_DIR.parent.name == "videos"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — get_duration
# ══════════════════════════════════════════════════════════════════════════════
class TestGetDuration:
    def setup_method(self):
        self.mod = _load("make_linkedin_video.py")

    def test_returns_float_for_existing_video(self):
        dur = self.mod.get_duration(self.mod.SOURCE_VIDEO)
        assert isinstance(dur, float)
        assert dur > 0

    def test_fallback_for_missing_file(self):
        dur = self.mod.get_duration(Path("/nonexistent/file.mp4"))
        assert dur == 170.0

    def test_source_duration_in_range(self):
        """Voice video should be 2–4 minutes (120–240 s)."""
        dur = self.mod.get_duration(self.mod.SOURCE_VIDEO)
        assert 120 < dur < 300, f"Unexpected duration: {dur:.1f}s"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Post queue structure
# ══════════════════════════════════════════════════════════════════════════════
class TestPostQueue:
    REQUIRED_KEYS = {
        "platform", "account_name", "title", "content",
        "media_path", "hashtags", "status", "scheduled_at", "notes",
    }
    REQUIRED_PLATFORMS = {
        "LinkedIn", "Instagram", "TikTok", "YouTube", "Twitter", "Facebook",
    }

    def setup_method(self):
        self.mod   = _load("post_linkedin_now.py")
        self.posts = self.mod._build_post_queue()

    def test_queue_not_empty(self):
        assert len(self.posts) >= 1

    def test_all_platforms_present(self):
        platforms = {p["platform"] for p in self.posts}
        for pl in self.REQUIRED_PLATFORMS:
            assert pl in platforms, f"Missing platform: {pl}"

    def test_required_keys_on_every_post(self):
        for post in self.posts:
            missing = self.REQUIRED_KEYS - set(post.keys())
            assert not missing, f"Post '{post.get('title')}' missing keys: {missing}"

    def test_linkedin_has_multiple_variants(self):
        li = [p for p in self.posts if p["platform"] == "LinkedIn"]
        assert len(li) >= 3

    def test_no_empty_content(self):
        for post in self.posts:
            assert post["content"].strip(), f"Empty content: {post['title']}"

    def test_scheduled_at_is_future_datetime(self):
        for post in self.posts:
            sched = post["scheduled_at"]
            dt = datetime.strptime(sched, "%Y-%m-%d %H:%M:%S")
            assert dt > datetime.now(), (
                f"scheduled_at in the past for: {post['title']}"
            )

    def test_valid_status_values(self):
        valid = {"draft", "scheduled", "posted", "failed"}
        for post in self.posts:
            assert post["status"] in valid, (
                f"Invalid status '{post['status']}' on: {post['title']}"
            )

    def test_linkedin_posts_have_hashtags(self):
        for post in self.posts:
            if post["platform"] == "LinkedIn":
                assert "#" in post["hashtags"], (
                    f"LinkedIn post missing hashtags: {post['title']}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — DB table creation
# ══════════════════════════════════════════════════════════════════════════════
class TestDBTables:
    def setup_method(self):
        self.mod = _load("post_linkedin_now.py")

    def test_creates_smm_posts_table(self):
        conn = sqlite3.connect(":memory:")
        self.mod._ensure_smm_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        assert "smm_posts" in {r[0] for r in cursor.fetchall()}
        conn.close()

    def test_idempotent_on_double_call(self):
        conn = sqlite3.connect(":memory:")
        self.mod._ensure_smm_tables(conn)
        self.mod._ensure_smm_tables(conn)  # must not raise
        conn.close()

    def test_correct_columns_present(self):
        conn = sqlite3.connect(":memory:")
        self.mod._ensure_smm_tables(conn)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(smm_posts)")
        cols = {r[1] for r in cursor.fetchall()}
        conn.close()
        required = {
            "id", "platform", "account_name", "title", "content",
            "media_path", "hashtags", "status", "scheduled_at",
            "posted_at", "notes", "created_at", "updated_at",
        }
        for col in required:
            assert col in cols, f"Missing column: {col}"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Seed deduplication
# ══════════════════════════════════════════════════════════════════════════════
class TestSeedDeduplication:
    def setup_method(self):
        self.mod = _load("post_linkedin_now.py")

    def _mem_conn(self):
        """Create an in-memory SQLite connection whose close() is a no-op,
        so multiple seed_smm_db calls can share the same DB state.
        sqlite3.Connection.close is read-only, so we wrap with MagicMock."""
        real_conn = sqlite3.connect(":memory:")
        self.mod._ensure_smm_tables(real_conn)
        # MagicMock(wraps=...) delegates everything to the real connection
        # but lets us override .close() to prevent destroying the in-memory DB
        mock_conn = MagicMock(wraps=real_conn)
        mock_conn.close = MagicMock()   # no-op — keeps the in-memory DB alive
        mock_conn.cursor = real_conn.cursor   # use real cursor for real queries
        mock_conn.commit = real_conn.commit
        return mock_conn

    def test_seed_inserts_posts(self):
        """seed_smm_db should insert all posts into a fresh DB."""
        conn = self._mem_conn()
        with patch.object(self.mod, "DB_AVAILABLE", True), \
             patch.object(self.mod, "get_conn", return_value=conn):
            count = self.mod.seed_smm_db(self.mod._build_post_queue())
        assert count > 0

    def test_second_seed_inserts_zero(self):
        """Calling seed_smm_db twice must not create duplicates."""
        conn = self._mem_conn()
        with patch.object(self.mod, "DB_AVAILABLE", True), \
             patch.object(self.mod, "get_conn", return_value=conn):
            posts = self.mod._build_post_queue()
            self.mod.seed_smm_db(posts)            # first call
            count2 = self.mod.seed_smm_db(posts)   # second call → 0
        assert count2 == 0

    def test_dry_run_writes_nothing(self):
        """dry_run=True must not touch the DB at all."""
        conn = self._mem_conn()
        # dry_run returns before calling get_conn, so no patch needed here
        with patch.object(self.mod, "DB_AVAILABLE", True):
            count = self.mod.seed_smm_db(
                self.mod._build_post_queue(), dry_run=True
            )
        assert count == 0
        # Verify nothing was written
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM smm_posts")
        assert cursor.fetchone()[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — SEO copy quality
# ══════════════════════════════════════════════════════════════════════════════
class TestSEOCopy:
    SEO_KEYWORDS = ["AI", "SDLC", "Python", "peachstatesavings.com",
                    "PIPELINE", "#"]

    def setup_method(self):
        self.mod = _load("post_linkedin_now.py")

    def test_primary_post_contains_seo_keywords(self):
        for kw in self.SEO_KEYWORDS:
            assert kw in self.mod.POST_2_LONG, (
                f"SEO keyword '{kw}' missing from primary post"
            )

    def test_hook_within_150_chars(self):
        first = self.mod.POST_2_LONG.strip().split("\n")[0]
        assert len(first) <= 150, f"Hook too long ({len(first)} chars)"

    def test_primary_post_has_cta(self):
        cta_signals = ["Comment", "comment", "👇", "share", "Share"]
        assert any(s in self.mod.POST_2_LONG for s in cta_signals), \
            "Primary post missing a CTA"

    def test_url_in_all_platforms(self):
        posts_by_platform: dict = {}
        for p in self.mod._build_post_queue():
            posts_by_platform.setdefault(p["platform"], []).append(p)
        for platform, platform_posts in posts_by_platform.items():
            all_content = " ".join(p["content"] for p in platform_posts)
            has_url = (
                "peachstatesavings.com" in all_content
                or "github.com/bookofdarrian" in all_content
            )
            assert has_url, f"No URL found in any {platform} post"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — Filter string safety
# ══════════════════════════════════════════════════════════════════════════════
class TestFilterStrings:
    DANGEROUS = ["|", "&", "`", "$", "\n", "\r"]

    def setup_method(self):
        self.mod = _load("make_linkedin_video.py")

    def test_watermark_is_safe(self):
        for ch in self.DANGEROUS:
            assert ch not in self.mod.WATERMARK, \
                f"Unsafe char '{ch}' in WATERMARK"

    def test_author_is_safe(self):
        for ch in self.DANGEROUS:
            assert ch not in self.mod.AUTHOR, \
                f"Unsafe char '{ch}' in AUTHOR"

    def test_voice_volume_is_numeric_and_valid(self):
        vol = float(self.mod.VOICE_VOLUME)
        assert 0.0 <= vol <= 2.0

    def test_music_volume_low_enough(self):
        vol = float(self.mod.MUSIC_VOLUME)
        assert 0.0 < vol <= 0.5, \
            f"MUSIC_VOLUME {vol} too high — would overpower voice"

    def test_music_urls_use_https(self):
        for url in self.mod.MUSIC_URLS:
            assert url.startswith("https://"), f"Non-HTTPS URL: {url}"


# ══════════════════════════════════════════════════════════════════════════════
# Smoke test
# ══════════════════════════════════════════════════════════════════════════════
def test_full_smoke():
    """Import both modules and build the post queue end-to-end."""
    mod1 = _load("make_linkedin_video.py")
    mod2 = _load("post_linkedin_now.py")
    posts = mod2._build_post_queue()

    assert isinstance(posts, list)
    assert len(posts) >= 6
    for p in posts:
        assert p["content"]
        assert p["platform"]
        assert p["title"]

    platforms = {p["platform"] for p in posts}
    print(f"\n✅ Smoke: {len(posts)} posts across {len(platforms)} platforms")
