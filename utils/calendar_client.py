"""
Google Calendar Client
======================
Handles all Google Calendar API interactions for the Todo integration.

Capabilities:
  - OAuth2 authentication (shared credentials.json, token stored in DB/disk)
  - List upcoming events from Google Calendar
  - Create calendar events from todo tasks
  - Delete / update calendar events
  - Sync todo tasks → Google Calendar (push tasks with due dates as all-day events)

Scopes:
  This module uses COMBINED_SCOPES which includes both Gmail and Calendar.
  If the existing token only has Gmail scopes, the user must re-authorize.

Setup (same project as Gmail):
  1. Go to console.cloud.google.com → your existing project
  2. Enable Google Calendar API
  3. The same credentials.json works — just re-authorize with the new scope
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE       = os.environ.get("GMAIL_TOKEN_FILE", "token.json")

# Combined scopes — Gmail + Calendar
COMBINED_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


def _has_calendar_scope(token_json: str) -> bool:
    """Check if a token JSON string includes the Calendar scope."""
    try:
        data = json.loads(token_json)
        scopes = data.get("scopes", [])
        return CALENDAR_SCOPE in scopes
    except Exception:
        return False


def get_calendar_service(token_json: Optional[str] = None):
    """
    Build and return an authenticated Google Calendar API service object.

    token_json: JSON string of the stored OAuth token (from DB or disk).

    Returns (service, token_json_str) where token_json_str is the
    (possibly refreshed) token to save back to the DB.

    Raises:
        FileNotFoundError  — credentials.json not found
        RuntimeError("AUTH_REQUIRED")   — first-time setup needed
        RuntimeError("SCOPE_UPGRADE")   — token exists but lacks Calendar scope
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Google API libraries not installed. Run:\n"
            "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )

    creds = None

    # 1. Try token from DB (passed in as JSON string)
    if token_json:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), COMBINED_SCOPES)
        except Exception as e:
            logger.warning(f"Could not load token from DB: {e}")
            creds = None

    # 2. Fallback: try token.json on disk
    if not creds and os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, COMBINED_SCOPES)
            token_json = open(TOKEN_FILE).read()
        except Exception:
            creds = None

    # 3. Check if Calendar scope is present
    if creds and token_json and not _has_calendar_scope(token_json):
        raise RuntimeError("SCOPE_UPGRADE")

    # 4. Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            creds = None

    # 5. If still no valid creds, we need the auth flow
    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"credentials.json not found at '{CREDENTIALS_FILE}'. "
                "Download it from Google Cloud Console → APIs & Services → Credentials."
            )
        raise RuntimeError("AUTH_REQUIRED")

    token_str = creds.to_json()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service, token_str


def get_calendar_auth_url(state: str = "") -> tuple[str, object]:
    """
    Generate the OAuth2 authorization URL for Calendar + Gmail combined scopes.
    Returns (auth_url, flow) — store flow in session_state to exchange code later.
    """
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        raise ImportError("Run: pip install google-auth-oauthlib")

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"credentials.json not found at '{CREDENTIALS_FILE}'. "
            "Download it from Google Cloud Console."
        )

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=COMBINED_SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="false",   # request all scopes fresh
        prompt="consent",
        state=state,
    )
    return auth_url, flow


def exchange_code_for_token(flow, code: str) -> str:
    """
    Exchange the authorization code for a token.
    Returns the token as a JSON string to store in the DB.
    """
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_str = creds.to_json()
    # Save to disk as fallback (overwrites old Gmail-only token)
    with open(TOKEN_FILE, "w") as f:
        f.write(token_str)
    return token_str


# ── Calendar event helpers ────────────────────────────────────────────────────

def list_upcoming_events(service, max_results: int = 20, days_ahead: int = 30) -> list[dict]:
    """
    Fetch upcoming events from the primary Google Calendar.
    Returns list of event dicts.
    """
    try:
        now = datetime.utcnow().isoformat() + "Z"
        end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

        result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=end,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = result.get("items", [])
        parsed = []
        for ev in events:
            start = ev.get("start", {})
            end_ev = ev.get("end", {})
            start_str = start.get("date") or start.get("dateTime", "")[:10]
            end_str   = end_ev.get("date") or end_ev.get("dateTime", "")[:10]
            parsed.append({
                "id":          ev.get("id", ""),
                "summary":     ev.get("summary", "(no title)"),
                "description": ev.get("description", ""),
                "start":       start_str,
                "end":         end_str,
                "all_day":     "date" in start,
                "html_link":   ev.get("htmlLink", ""),
                "status":      ev.get("status", "confirmed"),
                "source_app":  ev.get("extendedProperties", {}).get("private", {}).get("source_app", ""),
                "task_id":     ev.get("extendedProperties", {}).get("private", {}).get("task_id", ""),
            })
        return parsed
    except Exception as e:
        logger.error(f"Failed to list calendar events: {e}")
        return []


def create_event_from_task(service, task: dict) -> Optional[str]:
    """
    Create a Google Calendar all-day event from a todo task.
    Returns the event ID on success, None on failure.

    task dict keys: title, due_date (YYYY-MM-DD), priority, notes, id
    """
    try:
        due = task.get("due_date")
        if not due:
            return None

        due_str = str(due)[:10]
        # All-day event: end date is the day after
        try:
            end_date = (date.fromisoformat(due_str) + timedelta(days=1)).isoformat()
        except Exception:
            end_date = due_str

        priority_emoji = {"high": "🔴", "normal": "🟡", "low": "⚪"}.get(task.get("priority", "normal"), "🟡")
        summary = f"{priority_emoji} {task.get('title', 'Task')}"

        description_parts = []
        if task.get("notes"):
            description_parts.append(task["notes"])
        description_parts.append(f"Priority: {task.get('priority', 'normal').title()}")
        description_parts.append("📱 Added from Peach State Savings Todo")

        event_body = {
            "summary": summary,
            "description": "\n".join(description_parts),
            "start": {"date": due_str},
            "end":   {"date": end_date},
            "extendedProperties": {
                "private": {
                    "source_app": "peach_savings_todo",
                    "task_id":    str(task.get("id", "")),
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 480},   # 8 hours before (morning of)
                ],
            },
        }

        created = service.events().insert(calendarId="primary", body=event_body).execute()
        return created.get("id")
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return None


def delete_event(service, event_id: str) -> bool:
    """Delete a Google Calendar event by ID. Returns True on success."""
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete calendar event {event_id}: {e}")
        return False


def update_event_from_task(service, event_id: str, task: dict) -> bool:
    """Update an existing calendar event to match the current task state."""
    try:
        due = task.get("due_date")
        if not due:
            return False

        due_str = str(due)[:10]
        end_date = (date.fromisoformat(due_str) + timedelta(days=1)).isoformat()

        priority_emoji = {"high": "🔴", "normal": "🟡", "low": "⚪"}.get(task.get("priority", "normal"), "🟡")
        summary = f"{priority_emoji} {task.get('title', 'Task')}"
        if task.get("status") == "done":
            summary = f"✅ {task.get('title', 'Task')}"

        description_parts = []
        if task.get("notes"):
            description_parts.append(task["notes"])
        description_parts.append(f"Priority: {task.get('priority', 'normal').title()}")
        description_parts.append("📱 Added from Peach State Savings Todo")

        event_body = {
            "summary": summary,
            "description": "\n".join(description_parts),
            "start": {"date": due_str},
            "end":   {"date": end_date},
        }

        service.events().patch(calendarId="primary", eventId=event_id, body=event_body).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update calendar event {event_id}: {e}")
        return False


def find_task_event(service, task_id: str) -> Optional[str]:
    """
    Search for an existing calendar event created from a specific task ID.
    Returns the event ID if found, None otherwise.
    """
    try:
        result = service.events().list(
            calendarId="primary",
            privateExtendedProperty=f"task_id={task_id}",
            maxResults=5,
        ).execute()
        items = result.get("items", [])
        if items:
            return items[0].get("id")
        return None
    except Exception as e:
        logger.error(f"Failed to search for task event: {e}")
        return None
