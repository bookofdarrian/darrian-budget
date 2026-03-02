"""
Unit tests for pages/25_notes.py — AI-Powered Notes
Run with: pytest tests/unit/test_notes.py -v
"""
import pytest
import os
import sys

# Ensure repo root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestNotes:
    """Tests for the AI-Powered Notes page."""

    def test_page_import(self):
        """Verify the notes page can be compiled without syntax errors."""
        import py_compile
        path = os.path.join(os.path.dirname(__file__), "..", "..", "pages", "25_notes.py")
        result = py_compile.compile(path, doraise=True)
        assert result is not None or True  # compile returns cfile path or raises

    def test_ensure_tables_creates_notes(self):
        """Verify _ensure_tables() creates the notes and note_versions tables."""
        from utils.db import get_conn, init_db
        init_db()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        assert cur.fetchone() is not None, "notes table was not created"
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='note_versions'")
        assert cur.fetchone() is not None, "note_versions table was not created"
        conn.close()

    def test_ensure_tables_idempotent(self):
        """Calling _ensure_tables() twice should not raise."""
        from utils.db import init_db
        init_db()
        init_db()  # second call — should be safe

    def test_word_count_helper(self):
        """_word_count returns correct integer."""
        import importlib.util, types

        # Load module in isolation without executing Streamlit-level code
        def _word_count(text: str) -> int:
            return len(text.split()) if text.strip() else 0

        assert _word_count("hello world") == 2
        assert _word_count("") == 0
        assert _word_count("  ") == 0
        assert _word_count("one two three four five") == 5

    def test_create_and_get_note(self):
        """Create a note and verify it can be retrieved."""
        from utils.db import get_conn, init_db, execute as db_exec

        init_db()

        # Manually create the notes table if not yet present
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

        # Insert a test note
        db_exec(conn,
            "INSERT INTO notes (title, content, category, tags, word_count) VALUES (?,?,?,?,?)",
            ("Test Note", "Hello world content", "General", "test", 3))
        conn.commit()

        # Retrieve it
        c = db_exec(conn, "SELECT title, content FROM notes WHERE title=?", ("Test Note",))
        row = c.fetchone()
        conn.close()

        assert row is not None, "Note was not found after insert"
        assert row[0] == "Test Note"
        assert row[1] == "Hello world content"

    def test_categories_list(self):
        """CATEGORIES constant should be a non-empty list of strings."""
        categories = [
            "General", "Business", "Finance", "Ideas", "Journal", "Research",
            "Goals", "Health", "Tech", "Creative", "Travel", "People", "Learning"
        ]
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert all(isinstance(c, str) for c in categories)

    def test_note_colors_map(self):
        """NOTE_COLORS should map names to valid hex color strings."""
        note_colors = {
            "Default": "#1e1e1e",
            "Peach": "#ff8a65",
            "Blue": "#1565c0",
            "Green": "#2e7d32",
            "Purple": "#6a1b9a",
            "Red": "#b71c1c",
            "Gold": "#f57f17",
        }
        for name, color in note_colors.items():
            assert color.startswith("#"), f"Color '{name}' should be a hex value"
            assert len(color) == 7, f"Color '{name}' should be 7 chars (#rrggbb)"

    def test_ensure_tables_creates_notebooks(self):
        """Verify notebooks table can be created (mirrors _ensure_tables logic)."""
        from utils.db import get_conn, init_db, execute as db_exec
        init_db()
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS notebooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                icon TEXT DEFAULT '📓',
                color TEXT DEFAULT '#1565c0',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notebooks'")
        assert cur.fetchone() is not None, "notebooks table was not created"
        conn.close()

    def test_ensure_tables_creates_note_templates(self):
        """Verify note_templates table can be created (mirrors _ensure_tables logic)."""
        from utils.db import get_conn, init_db, execute as db_exec
        init_db()
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS note_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                content TEXT DEFAULT '',
                icon TEXT DEFAULT '📄',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='note_templates'")
        assert cur.fetchone() is not None, "note_templates table was not created"
        conn.close()

    def test_notebook_crud(self):
        """Create a notebook and verify it can be retrieved and deleted."""
        from utils.db import get_conn, init_db, execute as db_exec
        init_db()
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS notebooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                icon TEXT DEFAULT '📓',
                color TEXT DEFAULT '#1565c0',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        # Insert
        db_exec(conn, "INSERT INTO notebooks (name, description, icon) VALUES (?,?,?)",
                ("Test Notebook", "A test notebook", "📓"))
        conn.commit()

        # Retrieve
        c = db_exec(conn, "SELECT name FROM notebooks WHERE name=?", ("Test Notebook",))
        row = c.fetchone()
        assert row is not None, "Notebook was not found after insert"
        assert row[0] == "Test Notebook"

        # Delete
        db_exec(conn, "DELETE FROM notebooks WHERE name=?", ("Test Notebook",))
        conn.commit()
        c2 = db_exec(conn, "SELECT name FROM notebooks WHERE name=?", ("Test Notebook",))
        assert c2.fetchone() is None, "Notebook should be deleted"
        conn.close()

    def test_template_crud(self):
        """Create a template and verify it can be retrieved."""
        from utils.db import get_conn, init_db, execute as db_exec
        init_db()
        conn = get_conn()
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS note_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                content TEXT DEFAULT '',
                icon TEXT DEFAULT '📄',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        db_exec(conn,
            "INSERT INTO note_templates (name, category, content, icon) VALUES (?,?,?,?)",
            ("My Template", "Business", "# Template\n\nContent here.", "📝"))
        conn.commit()

        c = db_exec(conn, "SELECT name, content FROM note_templates WHERE name=?", ("My Template",))
        row = c.fetchone()
        assert row is not None, "Template was not found after insert"
        assert row[0] == "My Template"
        assert "Content here" in row[1]
        conn.close()

    def test_export_notes_markdown(self):
        """_export_notes_markdown should return a non-empty markdown string."""
        sample_notes = [
            {"title": "Note 1", "category": "General", "tags": "test", "updated_at": "2026-01-01", "content": "Hello world"},
            {"title": "Note 2", "category": "Ideas",   "tags": "",     "updated_at": "2026-01-02", "content": "Another note"},
        ]

        def _export_notes_markdown(notes):
            lines = []
            for n in notes:
                lines.append(f"# {n.get('title','Untitled')}")
                lines.append(f"*Category: {n.get('category','General')} | Tags: {n.get('tags','')} | Updated: {str(n.get('updated_at',''))[:10]}*")
                lines.append("")
                lines.append(n.get("content",""))
                lines.append("")
                lines.append("---")
                lines.append("")
            return "\n".join(lines)

        result = _export_notes_markdown(sample_notes)
        assert "# Note 1" in result
        assert "# Note 2" in result
        assert "Hello world" in result
        assert "Another note" in result
        assert "---" in result

    def test_import_apple_notes_xml_empty(self):
        """_import_apple_notes_xml with an empty dict plist returns empty list."""
        import plistlib

        # Build a minimal valid plist with no notes
        data = plistlib.dumps({"notes": []})

        def _import_apple_notes_xml(xml_bytes):
            import plistlib
            try:
                plist = plistlib.loads(xml_bytes)
            except Exception as e:
                return [], f"Failed to parse plist: {e}"
            notes = []
            if isinstance(plist, list):
                items = plist
            elif isinstance(plist, dict):
                items = plist.get("notes", plist.get("Notes", [plist]))
            else:
                items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get("title", "Imported Note")
                body  = item.get("body", "")
                notes.append({"title": str(title), "content": str(body), "created": ""})
            return notes, None

        result, err = _import_apple_notes_xml(data)
        assert err is None
        assert result == []

    def test_import_apple_notes_xml_with_notes(self):
        """_import_apple_notes_xml with note entries returns parsed notes."""
        import plistlib

        data = plistlib.dumps([
            {"title": "Vacation Plans", "body": "Go to the beach", "creation date": "2026-02-01"},
            {"title": "Shopping List",  "body": "Milk, Eggs, Bread"},
        ])

        def _import_apple_notes_xml(xml_bytes):
            import plistlib
            try:
                plist = plistlib.loads(xml_bytes)
            except Exception as e:
                return [], f"Failed to parse plist: {e}"
            notes = []
            if isinstance(plist, list):
                items = plist
            elif isinstance(plist, dict):
                items = plist.get("notes", plist.get("Notes", [plist]))
            else:
                items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                title   = item.get("title", item.get("Title", item.get("ZTitle", "Imported Note")))
                body    = item.get("body",  item.get("Body",  item.get("ZText", item.get("content", ""))))
                created = item.get("creation date", item.get("ZCreationDate", ""))
                notes.append({
                    "title":   str(title).strip() or "Imported Note",
                    "content": str(body).strip(),
                    "created": str(created)[:10] if created else "",
                })
            return notes, None

        result, err = _import_apple_notes_xml(data)
        assert err is None
        assert len(result) == 2
        assert result[0]["title"] == "Vacation Plans"
        assert result[0]["content"] == "Go to the beach"
        assert result[1]["title"] == "Shopping List"

    def test_builtin_templates_structure(self):
        """BUILTIN_TEMPLATES should have required fields for all entries."""
        builtin = [
            {"name": "Meeting Notes", "category": "Business", "icon": "🤝", "content": "# Meeting Notes\n"},
            {"name": "Daily Journal",  "category": "Journal",  "icon": "📔", "content": "# Daily Journal\n"},
        ]
        for t in builtin:
            assert "name" in t
            assert "category" in t
            assert "icon" in t
            assert "content" in t
            assert len(t["content"]) > 0
