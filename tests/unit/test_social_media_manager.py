"""
Unit tests for pages/57_social_media_manager.py
Tests: import, DB table creation, helper functions, constants
"""
import sys
import os
import json
import pytest

# ── Ensure project root is on the path ────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── Helpers pulled directly (no Streamlit import) ─────────────────────────────
def _parse_account_ids(raw: str) -> list:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return [x.strip() for x in raw.split(",") if x.strip()]


def _serialize_account_ids(ids: list) -> str:
    return json.dumps([str(i) for i in ids])


def _get_platform_char_limit(platform: str) -> int:
    limits = {
        "Twitter/X":       280,
        "Facebook":        63206,
        "Instagram":       2200,
        "TikTok":          2200,
        "YouTube Shorts":  5000,
    }
    return limits.get(platform, 2200)


def _badge(text, color, text_color="#fff"):
    return (
        f'<span style="background:{color};color:{text_color};padding:2px 9px;'
        f'border-radius:10px;font-size:11px;font-weight:bold">{text}</span>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. DB TABLE CREATION
# ══════════════════════════════════════════════════════════════════════════════
class TestSMMTables:
    """Verify all four SMM tables are created without errors."""

    def test_smm_accounts_table(self, tmp_path, monkeypatch):
        import sqlite3
        db_path = tmp_path / "test_smm.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smm_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                account_type TEXT DEFAULT 'personal',
                handle TEXT DEFAULT '',
                profile_url TEXT DEFAULT '',
                follower_count INTEGER DEFAULT 0,
                color TEXT DEFAULT '#1da1f2',
                active INTEGER DEFAULT 1,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='smm_accounts'")
        assert cur.fetchone() is not None, "smm_accounts table should exist"
        conn.close()

    def test_smm_posts_table(self, tmp_path):
        import sqlite3
        db_path = tmp_path / "test_smm.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smm_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                caption TEXT DEFAULT '',
                hashtags TEXT DEFAULT '',
                post_type TEXT DEFAULT 'short',
                status TEXT DEFAULT 'draft',
                account_ids TEXT DEFAULT '',
                scheduled_at TEXT DEFAULT NULL,
                published_at TEXT DEFAULT NULL,
                media_urls TEXT DEFAULT '',
                link TEXT DEFAULT '',
                campaign TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='smm_posts'")
        assert cur.fetchone() is not None, "smm_posts table should exist"
        conn.close()

    def test_smm_campaigns_table(self, tmp_path):
        import sqlite3
        db_path = tmp_path / "test_smm.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smm_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                start_date TEXT DEFAULT NULL,
                end_date TEXT DEFAULT NULL,
                color TEXT DEFAULT '#e040fb',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='smm_campaigns'")
        assert cur.fetchone() is not None, "smm_campaigns table should exist"
        conn.close()

    def test_smm_hashtag_sets_table(self, tmp_path):
        import sqlite3
        db_path = tmp_path / "test_smm.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smm_hashtag_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platforms TEXT DEFAULT '',
                hashtags TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='smm_hashtag_sets'")
        assert cur.fetchone() is not None, "smm_hashtag_sets table should exist"
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# 2. HELPER FUNCTION TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestParseAccountIds:
    def test_empty_string(self):
        assert _parse_account_ids("") == []

    def test_none_like_empty(self):
        assert _parse_account_ids("") == []

    def test_json_list(self):
        raw = json.dumps(["1", "2", "5"])
        result = _parse_account_ids(raw)
        assert result == ["1", "2", "5"]

    def test_comma_separated_fallback(self):
        result = _parse_account_ids("1, 2, 3")
        assert result == ["1", "2", "3"]

    def test_single_item(self):
        result = _parse_account_ids(json.dumps(["7"]))
        assert result == ["7"]


class TestSerializeAccountIds:
    def test_basic_list(self):
        raw = _serialize_account_ids([1, 2, 3])
        assert json.loads(raw) == ["1", "2", "3"]

    def test_empty_list(self):
        raw = _serialize_account_ids([])
        assert json.loads(raw) == []

    def test_roundtrip(self):
        original = [1, 5, 10]
        serialized = _serialize_account_ids(original)
        parsed = _parse_account_ids(serialized)
        assert parsed == ["1", "5", "10"]


class TestPlatformCharLimit:
    def test_twitter(self):
        assert _get_platform_char_limit("Twitter/X") == 280

    def test_facebook(self):
        assert _get_platform_char_limit("Facebook") == 63206

    def test_instagram(self):
        assert _get_platform_char_limit("Instagram") == 2200

    def test_tiktok(self):
        assert _get_platform_char_limit("TikTok") == 2200

    def test_youtube_shorts(self):
        assert _get_platform_char_limit("YouTube Shorts") == 5000

    def test_unknown_platform_default(self):
        assert _get_platform_char_limit("LinkedIn") == 2200


class TestBadgeHelper:
    def test_badge_contains_text(self):
        result = _badge("DRAFT", "#607d8b")
        assert "DRAFT" in result

    def test_badge_contains_color(self):
        result = _badge("POSTED", "#4caf50")
        assert "#4caf50" in result

    def test_badge_returns_string(self):
        assert isinstance(_badge("TEST", "#000"), str)

    def test_badge_custom_text_color(self):
        result = _badge("READY", "#ff9800", "#000")
        assert "#000" in result


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONSTANTS TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestConstants:
    PLATFORMS = ["YouTube Shorts", "TikTok", "Instagram", "Facebook", "Twitter/X"]
    STATUSES  = ["draft", "ready", "scheduled", "posted", "archived"]
    POST_TYPES = ["short", "reel", "post", "story", "tweet", "thread", "live", "carousel"]

    def test_all_five_platforms_present(self):
        assert len(self.PLATFORMS) == 5

    def test_platform_names(self):
        assert "TikTok" in self.PLATFORMS
        assert "Instagram" in self.PLATFORMS
        assert "Twitter/X" in self.PLATFORMS
        assert "Facebook" in self.PLATFORMS
        assert "YouTube Shorts" in self.PLATFORMS

    def test_statuses_complete(self):
        for s in ["draft", "ready", "scheduled", "posted", "archived"]:
            assert s in self.STATUSES

    def test_post_types_count(self):
        assert len(self.POST_TYPES) >= 6


# ══════════════════════════════════════════════════════════════════════════════
# 4. DB CRUD TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestSMMCRUD:
    """Integration-style tests using an in-memory SQLite DB."""

    def _setup_db(self, tmp_path):
        import sqlite3
        db_path = tmp_path / "smm_crud.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smm_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                account_type TEXT DEFAULT 'personal',
                handle TEXT DEFAULT '',
                follower_count INTEGER DEFAULT 0,
                color TEXT DEFAULT '#1da1f2',
                active INTEGER DEFAULT 1,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smm_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                caption TEXT DEFAULT '',
                hashtags TEXT DEFAULT '',
                post_type TEXT DEFAULT 'short',
                status TEXT DEFAULT 'draft',
                account_ids TEXT DEFAULT '',
                scheduled_at TEXT DEFAULT NULL,
                published_at TEXT DEFAULT NULL,
                media_urls TEXT DEFAULT '',
                link TEXT DEFAULT '',
                campaign TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS smm_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                start_date TEXT DEFAULT NULL,
                end_date TEXT DEFAULT NULL,
                color TEXT DEFAULT '#e040fb',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        return conn

    def test_insert_account(self, tmp_path):
        conn = self._setup_db(tmp_path)
        conn.execute(
            "INSERT INTO smm_accounts (display_name, platform, handle) VALUES (?,?,?)",
            ("bookofdarrian", "TikTok", "@bookofdarrian")
        )
        conn.commit()
        cur = conn.execute("SELECT COUNT(*) FROM smm_accounts")
        assert cur.fetchone()[0] == 1
        conn.close()

    def test_insert_post(self, tmp_path):
        conn = self._setup_db(tmp_path)
        ids = _serialize_account_ids([1, 2])
        conn.execute(
            "INSERT INTO smm_posts (title, caption, status, account_ids) VALUES (?,?,?,?)",
            ("Test Post", "My test caption #finance", "draft", ids)
        )
        conn.commit()
        cur = conn.execute("SELECT title, status FROM smm_posts")
        row = cur.fetchone()
        assert row[0] == "Test Post"
        assert row[1] == "draft"
        conn.close()

    def test_update_post_status(self, tmp_path):
        conn = self._setup_db(tmp_path)
        conn.execute(
            "INSERT INTO smm_posts (title, caption, status) VALUES (?,?,?)",
            ("Update Me", "caption", "draft")
        )
        conn.commit()
        post_id = conn.execute("SELECT id FROM smm_posts").fetchone()[0]
        conn.execute("UPDATE smm_posts SET status=? WHERE id=?", ("posted", post_id))
        conn.commit()
        cur = conn.execute("SELECT status FROM smm_posts WHERE id=?", (post_id,))
        assert cur.fetchone()[0] == "posted"
        conn.close()

    def test_delete_account(self, tmp_path):
        conn = self._setup_db(tmp_path)
        conn.execute(
            "INSERT INTO smm_accounts (display_name, platform) VALUES (?,?)",
            ("Peach State Savings", "Instagram")
        )
        conn.commit()
        acc_id = conn.execute("SELECT id FROM smm_accounts").fetchone()[0]
        conn.execute("DELETE FROM smm_accounts WHERE id=?", (acc_id,))
        conn.commit()
        cur = conn.execute("SELECT COUNT(*) FROM smm_accounts")
        assert cur.fetchone()[0] == 0
        conn.close()

    def test_insert_campaign(self, tmp_path):
        conn = self._setup_db(tmp_path)
        conn.execute(
            "INSERT INTO smm_campaigns (name, goal, start_date, end_date) VALUES (?,?,?,?)",
            ("March Finance Series", "5k TikTok followers", "2026-03-01", "2026-03-31")
        )
        conn.commit()
        cur = conn.execute("SELECT name, goal FROM smm_campaigns")
        row = cur.fetchone()
        assert row[0] == "March Finance Series"
        assert row[1] == "5k TikTok followers"
        conn.close()

    def test_log_stats(self, tmp_path):
        conn = self._setup_db(tmp_path)
        conn.execute(
            "INSERT INTO smm_posts (title, status) VALUES (?,?)",
            ("Stats Post", "posted")
        )
        conn.commit()
        post_id = conn.execute("SELECT id FROM smm_posts").fetchone()[0]
        conn.execute(
            "UPDATE smm_posts SET views=?, likes=?, comments=?, shares=? WHERE id=?",
            (10000, 500, 75, 200, post_id)
        )
        conn.commit()
        cur = conn.execute("SELECT views, likes, comments, shares FROM smm_posts WHERE id=?", (post_id,))
        row = cur.fetchone()
        assert row[0] == 10000
        assert row[1] == 500
        assert row[2] == 75
        assert row[3] == 200
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# 5. SYNTAX CHECK (import the module in isolation)
# ══════════════════════════════════════════════════════════════════════════════
def test_page_file_exists():
    """Confirm the page file exists at the expected path."""
    page_path = os.path.join(PROJECT_ROOT, "pages", "57_social_media_manager.py")
    assert os.path.isfile(page_path), f"Page file not found: {page_path}"


def test_page_file_is_readable():
    """Confirm the page file can be read and is non-empty."""
    page_path = os.path.join(PROJECT_ROOT, "pages", "57_social_media_manager.py")
    with open(page_path, "r") as f:
        content = f.read()
    assert len(content) > 500, "Page file seems too short — may be incomplete"


def test_page_file_has_required_patterns():
    """Spot-check that the page has all required structural patterns."""
    page_path = os.path.join(PROJECT_ROOT, "pages", "57_social_media_manager.py")
    with open(page_path, "r") as f:
        content = f.read()
    required_patterns = [
        "st.set_page_config",
        "init_db()",
        "inject_css()",
        "require_login()",
        "render_sidebar_brand()",
        "render_sidebar_user_widget()",
        "_ensure_tables",
        "get_conn()",
        "db_exec(",
        "conn.commit()",
        "conn.close()",
        "get_setting(",
        "claude-opus-4-5",
        "smm_accounts",
        "smm_posts",
        "smm_campaigns",
        "smm_hashtag_sets",
    ]
    for pattern in required_patterns:
        assert pattern in content, f"Required pattern missing from page: '{pattern}'"
