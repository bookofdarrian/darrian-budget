"""
Unit tests for Google Calendar DB-credentials feature.

Covers:
  - _load_credentials_config() with DB string
  - _load_credentials_config() raises FileNotFoundError when nothing available
  - _has_calendar_scope() returns correct bool
  - gmail_client._load_credentials_config() same contract
"""
import json
import os
import pytest
import tempfile


# ── calendar_client tests ─────────────────────────────────────────────────────

class TestCalendarLoadCredentials:
    """Test _load_credentials_config() in utils/calendar_client."""

    def _make_fake_creds(self, app_type: str = "installed") -> dict:
        return {
            app_type: {
                "client_id": "fake-client-id.apps.googleusercontent.com",
                "client_secret": "fake-secret",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    def test_load_from_json_string_installed(self):
        """Credentials passed as JSON string (installed app) are parsed correctly."""
        from utils.calendar_client import _load_credentials_config
        creds = self._make_fake_creds("installed")
        result = _load_credentials_config(json.dumps(creds))
        assert result["installed"]["client_id"] == "fake-client-id.apps.googleusercontent.com"

    def test_load_from_json_string_web(self):
        """Credentials passed as JSON string (web app) are parsed correctly."""
        from utils.calendar_client import _load_credentials_config
        creds = self._make_fake_creds("web")
        result = _load_credentials_config(json.dumps(creds))
        assert "web" in result

    def test_raises_file_not_found_when_no_source(self, tmp_path, monkeypatch):
        """Raises FileNotFoundError when neither DB string nor file is available."""
        from utils.calendar_client import _load_credentials_config
        # Patch CREDENTIALS_FILE to a non-existent path
        monkeypatch.setattr("utils.calendar_client.CREDENTIALS_FILE",
                            str(tmp_path / "nonexistent.json"))
        with pytest.raises(FileNotFoundError, match="Google credentials not found"):
            _load_credentials_config(None)

    def test_raises_value_error_on_invalid_json(self):
        """Raises ValueError when credentials_json_str is invalid JSON."""
        from utils.calendar_client import _load_credentials_config
        with pytest.raises((ValueError, json.JSONDecodeError)):
            _load_credentials_config("not-valid-json{{{")

    def test_load_from_file_fallback(self, tmp_path, monkeypatch):
        """Falls back to credentials.json file when no string provided."""
        from utils.calendar_client import _load_credentials_config
        creds = self._make_fake_creds("installed")
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps(creds))
        monkeypatch.setattr("utils.calendar_client.CREDENTIALS_FILE", str(creds_file))
        result = _load_credentials_config(None)
        assert result["installed"]["client_secret"] == "fake-secret"

    def test_db_string_takes_priority_over_file(self, tmp_path, monkeypatch):
        """DB credentials string takes priority over file."""
        from utils.calendar_client import _load_credentials_config
        # Put different data in the file vs string
        file_creds = {"installed": {"client_id": "FILE-CLIENT-ID", "client_secret": "file-secret",
                                     "redirect_uris": [], "auth_uri": "", "token_uri": ""}}
        db_creds   = {"installed": {"client_id": "DB-CLIENT-ID",   "client_secret": "db-secret",
                                     "redirect_uris": [], "auth_uri": "", "token_uri": ""}}
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps(file_creds))
        monkeypatch.setattr("utils.calendar_client.CREDENTIALS_FILE", str(creds_file))
        result = _load_credentials_config(json.dumps(db_creds))
        assert result["installed"]["client_id"] == "DB-CLIENT-ID"


class TestHasCalendarScope:
    """Test _has_calendar_scope() helper."""

    def test_returns_true_when_scope_present(self):
        from utils.calendar_client import _has_calendar_scope, CALENDAR_SCOPE
        token = json.dumps({"scopes": [CALENDAR_SCOPE, "https://www.googleapis.com/auth/gmail.readonly"]})
        assert _has_calendar_scope(token) is True

    def test_returns_false_when_scope_missing(self):
        from utils.calendar_client import _has_calendar_scope
        token = json.dumps({"scopes": ["https://www.googleapis.com/auth/gmail.readonly"]})
        assert _has_calendar_scope(token) is False

    def test_returns_false_on_empty_string(self):
        from utils.calendar_client import _has_calendar_scope
        assert _has_calendar_scope("") is False

    def test_returns_false_on_invalid_json(self):
        from utils.calendar_client import _has_calendar_scope
        assert _has_calendar_scope("{bad json}") is False


# ── gmail_client tests ────────────────────────────────────────────────────────

class TestGmailLoadCredentials:
    """Test _load_credentials_config() in utils/gmail_client (same contract)."""

    def _make_fake_creds(self) -> dict:
        return {
            "installed": {
                "client_id": "gmail-fake-id.apps.googleusercontent.com",
                "client_secret": "gmail-fake-secret",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    def test_load_from_json_string(self):
        from utils.gmail_client import _load_credentials_config
        creds = self._make_fake_creds()
        result = _load_credentials_config(json.dumps(creds))
        assert result["installed"]["client_id"] == "gmail-fake-id.apps.googleusercontent.com"

    def test_raises_when_no_source(self, tmp_path, monkeypatch):
        from utils.gmail_client import _load_credentials_config
        monkeypatch.setattr("utils.gmail_client.CREDENTIALS_FILE",
                            str(tmp_path / "nonexistent.json"))
        with pytest.raises(FileNotFoundError, match="Google credentials not found"):
            _load_credentials_config(None)

    def test_load_from_file_fallback(self, tmp_path, monkeypatch):
        from utils.gmail_client import _load_credentials_config
        creds = self._make_fake_creds()
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps(creds))
        monkeypatch.setattr("utils.gmail_client.CREDENTIALS_FILE", str(creds_file))
        result = _load_credentials_config(None)
        assert result["installed"]["client_secret"] == "gmail-fake-secret"


# ── Todo page calendar section import test ────────────────────────────────────

class TestTodoPageImport:
    """Verify pages/22_todo.py compiles without errors."""

    def test_module_compiles(self):
        import py_compile
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "pages", "22_todo.py")
        path = os.path.normpath(path)
        result = py_compile.compile(path, doraise=True)
        assert result is not None or True  # compile() returns bytecode path or raises
