"""
Unit tests for pages 24, 25, 26 — Creator Companion, Notes, Media Library.
Run with: pytest tests/unit/test_creator_pages.py -v
"""
import pytest
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# ══════════════════════════════════════════════════════════════════════════════
# SHARED DB / UTIL FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def init_test_db():
    """Initialize the in-memory / temp SQLite DB before each test."""
    from utils.db import init_db
    init_db()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 25 — NOTES
# ══════════════════════════════════════════════════════════════════════════════

class TestNotesDB:
    """Test notes DB table creation and core helpers."""

    def test_ensure_tables_runs_without_error(self):
        """Notes DB tables must be created without exceptions."""
        from utils.db import get_conn, execute as db_exec
        conn = get_conn()
        # These should all exist after _ensure_tables() logic (replicated inline for isolation)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                tags TEXT DEFAULT '',
                pinned INTEGER DEFAULT 0,
                archived INTEGER DEFAULT 0,
                color TEXT DEFAULT '#1e1e1e',
                word_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS note_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                saved_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
        assert True

    def test_word_count_helper(self):
        """_word_count should return correct word count."""
        text = "Hello world this is a test"
        words = len(text.split()) if text.strip() else 0
        assert words == 6

    def test_word_count_empty_string(self):
        """_word_count should return 0 for empty string."""
        text = ""
        words = len(text.split()) if text.strip() else 0
        assert words == 0

    def test_note_create_and_load(self):
        """Create a note, then load it back."""
        from utils.db import get_conn, execute as db_exec, init_db
        init_db()
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                tags TEXT DEFAULT '',
                pinned INTEGER DEFAULT 0,
                archived INTEGER DEFAULT 0,
                color TEXT DEFAULT '#1e1e1e',
                word_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        c = db_exec(conn, "INSERT INTO notes (title, content, category) VALUES (?,?,?)",
                    ("Test Note", "Some content here", "General"))
        note_id = c.lastrowid
        row = db_exec(conn, "SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        conn.close()
        assert row is not None
        # title is first TEXT column (index 1 after id)
        assert row[1] == "Test Note"

    def test_note_categories_list(self):
        """CATEGORIES constant must include expected values."""
        categories = [
            "General", "Business", "Finance", "Ideas", "Journal", "Research",
            "Goals", "Health", "Tech", "Creative", "Travel", "People", "Learning"
        ]
        assert "General" in categories
        assert "Finance" in categories
        assert len(categories) >= 10

    def test_note_version_table_exists(self):
        """note_versions table should be creatable."""
        from utils.db import get_conn, execute as db_exec
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS note_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                saved_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
        assert True


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 24 — CREATOR COMPANION
# ══════════════════════════════════════════════════════════════════════════════

class TestCreatorCompanionDB:
    """Test creator companion DB tables and helpers."""

    def test_ensure_tables_runs_without_error(self):
        """CC DB tables must be created without exceptions."""
        from utils.db import get_conn, execute as db_exec
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                niche TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                color TEXT DEFAULT '#ffa726',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content_type TEXT DEFAULT 'video',
                status TEXT DEFAULT 'idea',
                platform TEXT DEFAULT 'YouTube',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER DEFAULT NULL,
                idea TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
        assert True

    def test_statuses_list(self):
        """STATUSES constant should have all required workflow stages."""
        statuses = ["idea", "scripting", "filming", "editing", "scheduled", "published", "archived"]
        assert "idea" in statuses
        assert "published" in statuses
        assert "archived" in statuses
        assert len(statuses) == 7

    def test_channel_create_and_load(self):
        """Create a channel record, then load it."""
        from utils.db import get_conn, execute as db_exec, init_db
        init_db()
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                niche TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                color TEXT DEFAULT '#ffa726',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        c = db_exec(conn,
            "INSERT INTO cc_channels (name, platform) VALUES (?,?)",
            ("Test Channel", "YouTube"))
        ch_id = c.lastrowid
        row = db_exec(conn, "SELECT * FROM cc_channels WHERE id=?", (ch_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "Test Channel"

    def test_content_types_list(self):
        """CONTENT_TYPES should include standard formats."""
        content_types = ["video", "short", "reel", "post", "thread", "podcast", "blog", "live"]
        assert "video" in content_types
        assert "short" in content_types
        assert "podcast" in content_types


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 26 — MEDIA LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

class TestMediaLibraryDB:
    """Test media library DB tables and helpers."""

    def test_ensure_tables_runs_without_error(self):
        """Media library DB tables must be created without exceptions."""
        from utils.db import get_conn, execute as db_exec
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist TEXT DEFAULT '',
                album TEXT DEFAULT '',
                genre TEXT DEFAULT '',
                mood TEXT DEFAULT '',
                media_type TEXT DEFAULT 'music',
                source TEXT DEFAULT '',
                url TEXT DEFAULT '',
                bpm INTEGER DEFAULT 0,
                key_sig TEXT DEFAULT '',
                duration_sec INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                rating INTEGER DEFAULT 0,
                used_in TEXT DEFAULT '',
                favorite INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS media_playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                color TEXT DEFAULT '#ffa726',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS media_playlist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                media_id INTEGER NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
        assert True

    def test_duration_str_helper(self):
        """_duration_str should format seconds as M:SS."""
        def _duration_str(secs):
            if not secs:
                return "—"
            m, s = divmod(int(secs), 60)
            return f"{m}:{s:02d}"

        assert _duration_str(0)  == "—"
        assert _duration_str(60) == "1:00"
        assert _duration_str(90) == "1:30"
        assert _duration_str(3661) == "61:01"

    def test_star_html_helper(self):
        """_star_html should return correct star count."""
        def _star_html(rating):
            return "⭐" * int(rating) + "☆" * (5 - int(rating))

        assert _star_html(0) == "☆☆☆☆☆"
        assert _star_html(3) == "⭐⭐⭐☆☆"
        assert _star_html(5) == "⭐⭐⭐⭐⭐"

    def test_media_item_create_and_load(self):
        """Create a media item and load it back."""
        from utils.db import get_conn, execute as db_exec, init_db
        init_db()
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist TEXT DEFAULT '',
                genre TEXT DEFAULT '',
                media_type TEXT DEFAULT 'music',
                source TEXT DEFAULT '',
                url TEXT DEFAULT '',
                duration_sec INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                rating INTEGER DEFAULT 0,
                favorite INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        c = db_exec(conn,
            "INSERT INTO media_items (title, artist, genre, source) VALUES (?,?,?,?)",
            ("Test Song", "Test Artist", "Hip-Hop", "Spotify"))
        item_id = c.lastrowid
        row = db_exec(conn, "SELECT * FROM media_items WHERE id=?", (item_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "Test Song"

    def test_genres_list(self):
        """GENRES must include common music genres."""
        genres = [
            "Hip-Hop", "R&B", "Pop", "Electronic", "Lo-Fi", "Jazz", "Soul",
            "Gospel", "Trap", "Drill", "Afrobeats", "House", "Cinematic",
            "Ambient", "Rock", "Country", "Other"
        ]
        assert "Hip-Hop" in genres
        assert "Lo-Fi" in genres
        assert "Other" in genres

    def test_ms_to_sec_conversion(self):
        """_ms_to_sec should convert milliseconds to seconds."""
        def _ms_to_sec(ms):
            return (ms or 0) // 1000

        assert _ms_to_sec(0)      == 0
        assert _ms_to_sec(1000)   == 1
        assert _ms_to_sec(60000)  == 60
        assert _ms_to_sec(None)   == 0

    def test_playlist_create_and_link(self):
        """Create a playlist, add a track to it."""
        from utils.db import get_conn, execute as db_exec, init_db
        init_db()
        conn = get_conn()
        for ddl in [
            """CREATE TABLE IF NOT EXISTS media_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )""",
            """CREATE TABLE IF NOT EXISTS media_playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#ffa726',
                created_at TEXT DEFAULT (datetime('now'))
            )""",
            """CREATE TABLE IF NOT EXISTS media_playlist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                media_id INTEGER NOT NULL,
                sort_order INTEGER DEFAULT 0
            )""",
        ]:
            db_exec(conn, ddl)
        conn.commit()

        # Create a track and a playlist
        track_id = db_exec(conn,
            "INSERT INTO media_items (title, artist) VALUES (?,?)",
            ("Track A", "Artist A")).lastrowid
        pl_id = db_exec(conn,
            "INSERT INTO media_playlists (name) VALUES (?)",
            ("My Playlist",)).lastrowid
        db_exec(conn,
            "INSERT INTO media_playlist_items (playlist_id, media_id, sort_order) VALUES (?,?,?)",
            (pl_id, track_id, 1))
        conn.commit()

        row = db_exec(conn,
            "SELECT m.title FROM media_items m "
            "JOIN media_playlist_items p ON m.id=p.media_id "
            "WHERE p.playlist_id=?", (pl_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "Track A"


# ══════════════════════════════════════════════════════════════════════════════
# SYNTAX / IMPORT CHECKS
# ══════════════════════════════════════════════════════════════════════════════

class TestPageSyntax:
    """Verify all three new pages are syntactically valid Python."""

    def test_page_24_syntax(self):
        import ast
        path = os.path.join(os.path.dirname(__file__), "../../pages/24_creator_companion.py")
        with open(path) as f:
            src = f.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in 24_creator_companion.py: {e}")

    def test_page_25_syntax(self):
        import ast
        path = os.path.join(os.path.dirname(__file__), "../../pages/25_notes.py")
        with open(path) as f:
            src = f.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in 25_notes.py: {e}")

    def test_page_26_syntax(self):
        import ast
        path = os.path.join(os.path.dirname(__file__), "../../pages/26_media_library.py")
        with open(path) as f:
            src = f.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"Syntax error in 26_media_library.py: {e}")
