"""
One-time script: seeds the 6 Connect Everything Quick Wins
into the pa_tasks table (Todo page 22).
Safe to run multiple times — skips duplicates by title.
"""
import sqlite3
import sys
import os
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "budget.db")

QUICK_WINS = [
    (
        "🔌 Link Echo Dot to Apple Home (Apple Home skill)",
        "high",
        "Alexa app → More → Skills & Games → search Apple → enable Apple Home skill → sign in with Apple ID → say 'Alexa, discover devices'. Unlocks cross-platform control: Siri controls Echo devices, Alexa controls HomeKit devices.",
    ),
    (
        "⚡ Create Alexa Morning Routine ('Alexa, good morning')",
        "high",
        "Alexa app → More → Routines → + → Voice: 'good morning' → Actions: Flash Briefing + turn on lights 40% + play morning playlist on Spotify. Takes ~5 min.",
    ),
    (
        "🌙 Create Alexa Goodnight Routine ('Alexa, goodnight')",
        "high",
        "Alexa app → More → Routines → + → Voice: 'goodnight' → Actions: turn off all lights + Do Not Disturb ON + set alarm for tomorrow. Takes ~5 min.",
    ),
    (
        "🌅 Create HomePod Morning Scene ('Hey Siri, good morning')",
        "normal",
        "Home app → + → Add Scene → name it Morning → set lights warm white 30%. Then Automations → + → Time of Day → 7:00 AM weekdays → activate Morning scene. Takes ~10 min.",
    ),
    (
        "📍 Enable iPhone presence automations (auto leave/arrive)",
        "normal",
        "Home app → Automations → + → People Arrive → turn on entry light. People Leave → turn off ALL lights. Alexa app → Routines → Location trigger → same actions. Fully automatic after setup.",
    ),
    (
        "📢 Set up HomePod Intercom + announcements",
        "low",
        "Home app → house icon → Intercom → add HomePod to a room. Then say 'Hey Siri, intercom: [message]' to broadcast to all HomePods. Bonus: 'Hey Siri, wake me at 7am with [playlist]' for music alarm.",
    ),
]


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found at {DB_PATH}")
        print("   Start the Streamlit app once to create the DB, then re-run this script.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Ensure table exists (mirrors pages/22_todo.py)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pa_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT DEFAULT NULL,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'open',
            source TEXT DEFAULT 'manual',
            source_email_id TEXT DEFAULT NULL,
            source_email_subject TEXT DEFAULT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT DEFAULT NULL
        )
    """)

    today = date.today().isoformat()
    added = 0
    skipped = 0

    for title, priority, notes in QUICK_WINS:
        # Check for duplicate
        existing = conn.execute(
            "SELECT id FROM pa_tasks WHERE title = ?", (title,)
        ).fetchone()

        if existing:
            print(f"  ⏭  Skipped (already exists): {title[:60]}")
            skipped += 1
            continue

        conn.execute(
            """
            INSERT INTO pa_tasks (title, due_date, priority, notes, status, source)
            VALUES (?, ?, ?, ?, 'open', 'smart_home_wizard')
            """,
            (title, today, priority, notes),
        )
        print(f"  ✅ Added: {title[:70]}")
        added += 1

    conn.commit()
    conn.close()

    print(f"\nDone — {added} task(s) added, {skipped} skipped.")
    if added:
        print("👉  Open page 22 (Todo) to see your Smart Home Quick Wins!")


if __name__ == "__main__":
    main()
