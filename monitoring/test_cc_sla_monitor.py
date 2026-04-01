#!/usr/bin/env python3
"""
Test CC SLA Monitor without waiting for cron
=============================================
Manually trigger a test run of the SLA monitor script.

Usage:
  python3 test_cc_sla_monitor.py
  python3 test_cc_sla_monitor.py --create-test-data    # Create test breaches in DB
  python3 test_cc_sla_monitor.py --clear-test-data      # Clean up test data

Useful for:
  • Testing Telegram alert delivery during setup
  • Verifying the script runs correctly
  • Debugging SLA logic without waiting 10 minutes
"""

import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent dir to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_conn, execute as db_exec, get_setting, USE_POSTGRES, init_db


def create_test_data(conn):
    """
    Create test SLA breaches in the database.
    Creates real cc_student_inquiries and cc_mentors entries.
    """
    print("[TEST] Creating test data for SLA breaches...")
    
    init_db()
    
    # Create mentors first
    ph = "%s" if USE_POSTGRES else "?"
    
    # Insert test mentor
    mentor_query = f"""
    INSERT INTO cc_mentors (name, email, timezone, active)
    VALUES ({ph}, {ph}, {ph}, {ph})
    ON CONFLICT (email) DO NOTHING
    RETURNING id
    """ if USE_POSTGRES else f"""
    INSERT OR IGNORE INTO cc_mentors (name, email, timezone, active)
    VALUES ({ph}, {ph}, {ph}, {ph})
    """
    
    try:
        db_exec(conn, mentor_query, ("Test Mentor", "test.mentor@example.com", "UTC", True))
        conn.commit()
        print("  ✓ Test mentor created")
    except Exception as e:
        print(f"  ! Mentor may already exist: {e}")
        conn.rollback()
    
    # Get mentor ID or create if needed
    mentor_id_query = "SELECT id FROM cc_mentors WHERE email = ?"
    mentor_id_query = "SELECT id FROM cc_mentors WHERE email = %s" if USE_POSTGRES else mentor_id_query
    mentor_result = db_exec(conn, mentor_id_query, ("test.mentor@example.com",))
    mentor_id = mentor_result.fetchone()[0] if mentor_result else 1
    
    # Create test inquiries with breached timestamps
    now_utc = datetime.now(timezone.utc)
    
    # Response SLA breach: submitted 10 minutes ago, not routed
    response_breach_time = (now_utc - timedelta(minutes=10)).isoformat()
    
    # Mentor Response SLA breach: submitted 25 hours ago, routed but not responded
    mentor_breach_time = (now_utc - timedelta(hours=25)).isoformat()
    
    # Insert test inquiries
    inquiry_query = f"""
    INSERT INTO cc_student_inquiries 
    (email, name, grade_level, goal, status, routed_to_mentor_id, created_at)
    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    ON CONFLICT (email) DO NOTHING
    """ if USE_POSTGRES else f"""
    INSERT OR IGNORE INTO cc_student_inquiries 
    (email, name, grade_level, goal, status, routed_to_mentor_id, created_at)
    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """
    
    # Test inquiry 1: Response SLA breach
    try:
        db_exec(conn, inquiry_query, (
            "test.breach.response@example.com",
            "Test Response Breach",
            "12",
            "college_list",
            "new",
            None,  # Not routed yet
            response_breach_time
        ))
        conn.commit()
        print("  ✓ Test inquiry (response SLA breach) created")
    except Exception as e:
        print(f"  ! Inquiry 1 may already exist: {e}")
        conn.rollback()
    
    # Test inquiry 2: Mentor Response SLA breach
    try:
        db_exec(conn, inquiry_query, (
            "test.breach.mentor@example.com",
            "Test Mentor Breach",
            "college",
            "fafsa",
            "new",
            mentor_id,  # Routed to mentor
            mentor_breach_time
        ))
        conn.commit()
        print("  ✓ Test inquiry (mentor response SLA breach) created")
    except Exception as e:
        print(f"  ! Inquiry 2 may already exist: {e}")
        conn.rollback()
    
    print("\n[TEST] ✓ Test data created. Run the monitor to see alerts:")
    print("  python3 monitoring/cc_sla_monitor.py")


def clear_test_data(conn):
    """Clean up test data from the database."""
    print("[TEST] Cleaning up test data...")
    
    test_emails = [
        "test.breach.response@example.com",
        "test.breach.mentor@example.com"
    ]
    
    for email in test_emails:
        ph = "%s" if USE_POSTGRES else "?"
        query = f"DELETE FROM cc_student_inquiries WHERE email = {ph}"
        try:
            db_exec(conn, query, (email,))
            conn.commit()
            print(f"  ✓ Deleted {email}")
        except Exception as e:
            print(f"  ! Failed to delete {email}: {e}")
            conn.rollback()
    
    # Clean up test mentor
    try:
        ph = "%s" if USE_POSTGRES else "?"
        query = f"DELETE FROM cc_mentors WHERE email = {ph}"
        db_exec(conn, query, ("test.mentor@example.com",))
        conn.commit()
        print("  ✓ Deleted test mentor")
    except Exception as e:
        print(f"  ! Failed to delete test mentor: {e}")
        conn.rollback()
    
    print("\n[TEST] ✓ Test data cleaned up")


def main():
    parser = argparse.ArgumentParser(
        description="Test CC SLA Monitor script",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--create-test-data", action="store_true", 
                       help="Create test SLA breaches in the database")
    parser.add_argument("--clear-test-data", action="store_true",
                       help="Delete test data from the database")
    args = parser.parse_args()
    
    conn = get_conn()
    
    if args.create_test_data:
        create_test_data(conn)
    elif args.clear_test_data:
        clear_test_data(conn)
    else:
        # Default: just run the monitor
        print("[TEST] Running SLA monitor...")
        import cc_sla_monitor
        return cc_sla_monitor.main()
    
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
