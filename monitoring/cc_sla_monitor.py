#!/usr/bin/env python3
"""
CC Speed to Lead SLA Monitoring Cron
====================================
Checks for unresponded inquiries and sends Telegram alerts to Darrian.

Run every 10 minutes:
  */10 * * * * /opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py >> /var/log/cc_sla_monitor.log 2>&1

SLA Rules:
  1. Response SLA (5 minutes): Inquiry submitted but not routed to mentor
  2. Mentor Response SLA (24 hours): Routed to mentor but mentor hasn't responded yet

On breach, sends Telegram alert with inquiry details.
"""

import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent dir (darrian-budget) to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_conn, execute as db_exec, get_setting, USE_POSTGRES


def _send_telegram_alert(title: str, lines: list[str]) -> bool:
    """
    Send Telegram alert to Darrian.
    Returns True on success, False on failure.
    """
    token = get_setting("telegram_bot_token")
    chat_id = get_setting("telegram_chat_id")
    
    if not token or not chat_id:
        print(f"[ERROR] Telegram credentials not configured. Skipping alert.", file=sys.stderr)
        return False
    
    message = title + "\n" + "\n".join(lines)
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        if response.status_code == 200:
            return True
        else:
            print(f"[ERROR] Telegram API error {response.status_code}: {response.text[:200]}", file=sys.stderr)
            return False
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No internet connection — cannot send Telegram alert", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram alert: {e}", file=sys.stderr)
        return False


def _check_response_sla(conn, minutes: int = 5) -> list[dict]:
    """
    Check inquiries not routed/responded within N minutes.
    
    Returns list of dicts with:
      - id, name, email, created_at, routed_to_mentor_id
      - age_minutes: how long ago submitted
    """
    # Threshold: submissions older than N minutes that haven't been routed yet
    threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    
    ph = "%s" if USE_POSTGRES else "?"
    query = f"""
    SELECT id, name, email, created_at, routed_to_mentor_id
    FROM cc_student_inquiries
    WHERE status = 'new'
    AND created_at < {ph}
    AND routed_to_mentor_id IS NULL
    ORDER BY created_at ASC
    """
    
    try:
        result = db_exec(conn, query, (threshold.isoformat(),))
        rows = result.fetchall() if result else []
        
        # Convert to dicts and add age_minutes
        inquiries = []
        for row in rows:
            if isinstance(row, dict):
                inquiry = dict(row)
            else:
                # Handle tuple rows from PostgreSQL
                inquiry = {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'created_at': row[3],
                    'routed_to_mentor_id': row[4]
                }
            
            # Parse created_at and calculate age
            created = datetime.fromisoformat(inquiry['created_at'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age_seconds = (now - created).total_seconds()
            inquiry['age_minutes'] = int(age_seconds / 60)
            inquiries.append(inquiry)
        
        return inquiries
    except Exception as e:
        print(f"[ERROR] Failed to check response SLA: {e}", file=sys.stderr)
        return []


def _check_mentor_response_sla(conn, hours: int = 24) -> list[dict]:
    """
    Check routed inquiries mentor hasn't responded to in N hours.
    
    Returns list of dicts with:
      - id, name, email, routed_to_mentor_id, mentor_name, created_at
      - age_hours: how long ago submitted
    """
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    ph = "%s" if USE_POSTGRES else "?"
    query = f"""
    SELECT 
        i.id, i.name, i.email, i.routed_to_mentor_id, 
        m.name as mentor_name, i.created_at
    FROM cc_student_inquiries i
    LEFT JOIN cc_mentors m ON i.routed_to_mentor_id = m.id
    WHERE i.status = 'new'
    AND i.routed_to_mentor_id IS NOT NULL
    AND i.mentor_response_sent_at IS NULL
    AND i.created_at < {ph}
    ORDER BY i.created_at ASC
    """
    
    try:
        result = db_exec(conn, query, (threshold.isoformat(),))
        rows = result.fetchall() if result else []
        
        # Convert to dicts and add age_hours
        inquiries = []
        for row in rows:
            if isinstance(row, dict):
                inquiry = dict(row)
            else:
                # Handle tuple rows from PostgreSQL
                inquiry = {
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'routed_to_mentor_id': row[3],
                    'mentor_name': row[4],
                    'created_at': row[5]
                }
            
            # Parse created_at and calculate age
            created = datetime.fromisoformat(inquiry['created_at'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age_seconds = (now - created).total_seconds()
            inquiry['age_hours'] = int(age_seconds / 3600)
            inquiries.append(inquiry)
        
        return inquiries
    except Exception as e:
        print(f"[ERROR] Failed to check mentor response SLA: {e}", file=sys.stderr)
        return []


def _alert_response_sla(inquiries: list[dict]) -> None:
    """Send alert for response SLA breaches."""
    if not inquiries:
        return
    
    count = len(inquiries)
    title = f"🚨 <b>CC SLA BREACH: Response</b>\n{count} inquiry(ies) not responded in 5+ minutes"
    lines = []
    
    for inquiry in inquiries[:5]:  # Show first 5
        name = inquiry['name'][:20]  # Truncate long names
        email = inquiry['email']
        age = inquiry['age_minutes']
        lines.append(f"  • {name} ({email}) — {age}m ago")
    
    if count > 5:
        lines.append(f"  ... and {count - 5} more")
    
    success = _send_telegram_alert(title, lines)
    if success:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ✓ Response SLA alert sent ({count} breaches)")
    else:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ✗ Failed to send response SLA alert", file=sys.stderr)


def _alert_mentor_sla(inquiries: list[dict]) -> None:
    """Send alert for mentor response SLA breaches."""
    if not inquiries:
        return
    
    count = len(inquiries)
    title = f"🚨 <b>CC SLA BREACH: Mentor Response</b>\n{count} inquiry(ies) mentor hasn't responded in 24+ hours"
    lines = []
    
    for inquiry in inquiries[:5]:  # Show first 5
        name = inquiry['name'][:20]  # Truncate long names
        mentor = (inquiry['mentor_name'] or "Unknown")[:20]
        age = inquiry['age_hours']
        lines.append(f"  • {name} → {mentor} — {age}h ago")
    
    if count > 5:
        lines.append(f"  ... and {count - 5} more")
    
    success = _send_telegram_alert(title, lines)
    if success:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ✓ Mentor SLA alert sent ({count} breaches)")
    else:
        print(f"[{datetime.now(timezone.utc).isoformat()}] ✗ Failed to send mentor SLA alert", file=sys.stderr)


def main():
    """Main monitoring loop."""
    try:
        conn = get_conn()
        
        # Check Response SLA (5 min)
        response_breaches = _check_response_sla(conn, minutes=5)
        if response_breaches:
            _alert_response_sla(response_breaches)
        
        # Check Mentor Response SLA (24 hours)
        mentor_breaches = _check_mentor_response_sla(conn, hours=24)
        if mentor_breaches:
            _alert_mentor_sla(mentor_breaches)
        
        # Status message if no breaches
        if not response_breaches and not mentor_breaches:
            print(f"[{datetime.now(timezone.utc).isoformat()}] ✓ All SLAs met — no breaches detected")
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] [FATAL ERROR] SLA monitoring failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
