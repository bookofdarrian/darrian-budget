"""
College Confused Speed to Lead backend system.

Handles student inquiry qualification, mentor routing, email generation, and tracking.
All functions are database-agnostic (SQLite + PostgreSQL support via utils.db.execute).
No Streamlit imports — pure functions only.
"""
import json
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any

import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, get_setting, set_setting


# ─── Constants ────────────────────────────────────────────────────────────────

QUALIFIED_GRADE_LEVELS = {"9", "10", "11", "12", "college"}
QUALIFIED_GOALS = {"college_list", "essays", "fafsa", "sat_act"}
SUSPICIOUS_EMAIL_PATTERNS = {"test@", "@test.", "dummy", "fake", "sample", "example@example"}
SUSPICIOUS_NAMES = {"john doe", "jane doe", "test", "admin"}


# ─── Schema Initialization ────────────────────────────────────────────────────

def _ensure_cc_stl_tables(conn):
    """
    Initialize all College Confused Speed to Lead tables.
    
    - Creates 4 tables: inquiries, mentors, metrics, response_emails
    - Idempotent: safe to call multiple times
    - Works with SQLite and PostgreSQL
    
    Args:
        conn: Database connection from get_conn()
    """
    if USE_POSTGRES:
        # PostgreSQL: SERIAL, TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_student_inquiries (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                name TEXT NOT NULL,
                grade_level TEXT CHECK(grade_level IN ('9', '10', '11', '12', 'college', 'other')),
                goal TEXT CHECK(goal IN ('college_list', 'essays', 'fafsa', 'sat_act', 'general', 'other')),
                region TEXT,
                major_interest TEXT,
                ip_address TEXT,
                qualified_at TIMESTAMP,
                qualification_status TEXT DEFAULT 'pending' CHECK(qualification_status IN ('qualified', 'unqualified', 'pending_review')),
                qualification_confidence TEXT DEFAULT 'low' CHECK(qualification_confidence IN ('high', 'medium', 'low')),
                qualification_reason JSONB,
                routed_to_mentor_id INTEGER REFERENCES cc_mentors(id),
                status TEXT DEFAULT 'new' CHECK(status IN ('new', 'responded', 'mentor_engaged', 'conversion_completed')),
                mentor_response_sent_at TIMESTAMP,
                student_first_reply_at TIMESTAMP,
                student_booked_call BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_inquiries_email ON cc_student_inquiries(email)")
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_inquiries_status ON cc_student_inquiries(status)")
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_inquiries_mentor ON cc_student_inquiries(routed_to_mentor_id)")
        
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_mentors (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                timezone TEXT DEFAULT 'UTC',
                bio TEXT,
                specialties JSONB DEFAULT '[]'::jsonb,
                regions_covered JSONB DEFAULT '[]'::jsonb,
                max_students_per_month INTEGER DEFAULT 10,
                current_month_load INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_mentors_active ON cc_mentors(active)")
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_mentors_load ON cc_mentors(current_month_load)")
        
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_inquiry_metrics (
                id SERIAL PRIMARY KEY,
                inquiry_id INTEGER NOT NULL UNIQUE REFERENCES cc_student_inquiries(id),
                time_to_qualify_ms INTEGER,
                time_to_route_ms INTEGER,
                time_to_email_ms INTEGER,
                total_response_time_ms INTEGER,
                mentor_response_sent_at TIMESTAMP,
                student_first_reply_at TIMESTAMP,
                student_booked_call BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_metrics_inquiry ON cc_inquiry_metrics(inquiry_id)")
        
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_response_emails (
                id SERIAL PRIMARY KEY,
                inquiry_id INTEGER NOT NULL REFERENCES cc_student_inquiries(id),
                mentor_id INTEGER NOT NULL REFERENCES cc_mentors(id),
                claude_prompt TEXT,
                claude_response TEXT,
                claude_tokens_used INTEGER,
                email_subject TEXT,
                email_body_html TEXT,
                email_sent_at TIMESTAMP,
                email_status TEXT DEFAULT 'pending' CHECK(email_status IN ('pending', 'sent', 'bounced', 'opened', 'clicked')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_response_emails_inquiry ON cc_response_emails(inquiry_id)")
        
    else:
        # SQLite: INTEGER PRIMARY KEY AUTOINCREMENT, DATETIME DEFAULT CURRENT_TIMESTAMP
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_student_inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                name TEXT NOT NULL,
                grade_level TEXT CHECK(grade_level IN ('9', '10', '11', '12', 'college', 'other')),
                goal TEXT CHECK(goal IN ('college_list', 'essays', 'fafsa', 'sat_act', 'general', 'other')),
                region TEXT,
                major_interest TEXT,
                ip_address TEXT,
                qualified_at DATETIME,
                qualification_status TEXT DEFAULT 'pending' CHECK(qualification_status IN ('qualified', 'unqualified', 'pending_review')),
                qualification_confidence TEXT DEFAULT 'low' CHECK(qualification_confidence IN ('high', 'medium', 'low')),
                qualification_reason JSON,
                routed_to_mentor_id INTEGER,
                status TEXT DEFAULT 'new' CHECK(status IN ('new', 'responded', 'mentor_engaged', 'conversion_completed')),
                mentor_response_sent_at DATETIME,
                student_first_reply_at DATETIME,
                student_booked_call BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(routed_to_mentor_id) REFERENCES cc_mentors(id)
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_inquiries_email ON cc_student_inquiries(email)")
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_inquiries_status ON cc_student_inquiries(status)")
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_inquiries_mentor ON cc_student_inquiries(routed_to_mentor_id)")
        
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_mentors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                timezone TEXT DEFAULT 'UTC',
                bio TEXT,
                specialties JSON DEFAULT '[]',
                regions_covered JSON DEFAULT '[]',
                max_students_per_month INTEGER DEFAULT 10,
                current_month_load INTEGER DEFAULT 0,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_mentors_active ON cc_mentors(active)")
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_mentors_load ON cc_mentors(current_month_load)")
        
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_inquiry_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inquiry_id INTEGER NOT NULL UNIQUE,
                time_to_qualify_ms INTEGER,
                time_to_route_ms INTEGER,
                time_to_email_ms INTEGER,
                total_response_time_ms INTEGER,
                mentor_response_sent_at DATETIME,
                student_first_reply_at DATETIME,
                student_booked_call BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(inquiry_id) REFERENCES cc_student_inquiries(id)
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_metrics_inquiry ON cc_inquiry_metrics(inquiry_id)")
        
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS cc_response_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inquiry_id INTEGER NOT NULL,
                mentor_id INTEGER NOT NULL,
                claude_prompt TEXT,
                claude_response TEXT,
                claude_tokens_used INTEGER,
                email_subject TEXT,
                email_body_html TEXT,
                email_sent_at DATETIME,
                email_status TEXT DEFAULT 'pending' CHECK(email_status IN ('pending', 'sent', 'bounced', 'opened', 'clicked')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(inquiry_id) REFERENCES cc_student_inquiries(id),
                FOREIGN KEY(mentor_id) REFERENCES cc_mentors(id)
            )
        """)
        db_exec(conn, "CREATE INDEX IF NOT EXISTS idx_cc_response_emails_inquiry ON cc_response_emails(inquiry_id)")
    
    conn.commit()


# ─── Qualification Logic ──────────────────────────────────────────────────────

def qualify_inquiry(inquiry_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Qualify a student inquiry based on grade level, goal, name, and email patterns.
    
    Qualification rules:
    - Grade 9-12 + valid email = qualified (high confidence)
    - College + valid email = qualified (high confidence)
    - Empty goal or blank name = unqualified (low confidence)
    - Goal in ['college_list', 'essays', 'fafsa', 'sat_act'] = qualified (high)
    - Goal in ['general', 'other'] = qualified (medium confidence)
    - Suspicious email/name patterns = unqualified (low confidence)
    
    Args:
        inquiry_data (dict): {email, name, grade_level, goal, region, major_interest, ip_address}
    
    Returns:
        dict: {
            is_qualified: bool,
            confidence: str ('high', 'medium', 'low'),
            reason: {
                passed: list[str],
                failed: list[str],
                notes: str
            }
        }
    """
    passed = []
    failed = []
    notes = ""
    confidence = "low"
    is_qualified = False
    
    email = inquiry_data.get("email", "").strip().lower()
    name = inquiry_data.get("name", "").strip()
    grade_level = inquiry_data.get("grade_level", "").strip()
    goal = inquiry_data.get("goal", "").strip()
    
    # ── Rule 1: Name validation ───────────────────────────────────────────────
    if not name or len(name) < 2:
        failed.append("name_empty_or_too_short")
    elif name.lower() in SUSPICIOUS_NAMES:
        failed.append("name_suspicious")
    else:
        passed.append("name_valid")
    
    # ── Rule 2: Email validation ──────────────────────────────────────────────
    if not email or "@" not in email:
        failed.append("email_invalid_format")
    elif any(pattern in email for pattern in SUSPICIOUS_EMAIL_PATTERNS):
        failed.append("email_suspicious_pattern")
    else:
        passed.append("email_valid")
    
    # ── Rule 3: Grade level validation ────────────────────────────────────────
    if grade_level not in QUALIFIED_GRADE_LEVELS:
        if grade_level:
            failed.append(f"grade_level_not_qualified (got {grade_level})")
        else:
            failed.append("grade_level_missing")
    else:
        passed.append(f"grade_level_qualified ({grade_level})")
    
    # ── Rule 4: Goal validation ───────────────────────────────────────────────
    if not goal:
        failed.append("goal_missing")
    elif goal in QUALIFIED_GOALS:
        passed.append(f"goal_high_value ({goal})")
    elif goal in {"general", "other"}:
        passed.append(f"goal_medium_value ({goal})")
    else:
        failed.append(f"goal_unrecognized ({goal})")
    
    # ── Final decision ────────────────────────────────────────────────────────
    if len(failed) == 0 and len(passed) >= 3:
        is_qualified = True
        if goal in QUALIFIED_GOALS:
            confidence = "high"
            notes = "Grade level + qualified goal + valid email."
        else:
            confidence = "medium"
            notes = "Grade level + general goal + valid email."
    elif len(failed) <= 1 and "name_valid" in passed and "email_valid" in passed:
        is_qualified = True
        confidence = "medium"
        notes = "Valid name + email, but missing or unrecognized goal."
    else:
        is_qualified = False
        confidence = "low"
        notes = "Failed multiple checks or suspicious patterns detected."
    
    return {
        "is_qualified": is_qualified,
        "confidence": confidence,
        "reason": {
            "passed": passed,
            "failed": failed,
            "notes": notes
        }
    }


# ─── Mentor Routing ───────────────────────────────────────────────────────────

def route_inquiry_to_mentor(
    inquiry_id: int,
    grade_level: str,
    goal: str,
    region: Optional[str],
    conn
) -> Optional[int]:
    """
    Route an inquiry to the least-loaded active mentor matching goal + region coverage.
    
    Algorithm:
    1. Find active mentors with goal in their specialties
    2. Filter by region coverage (if region specified)
    3. Return mentor with lowest current_month_load (and room to expand)
    4. Increment mentor.current_month_load +1
    5. Update inquiry.routed_to_mentor_id
    
    Args:
        inquiry_id (int): ID of student inquiry
        grade_level (str): Student grade level
        goal (str): Student goal (college_list, essays, etc.)
        region (str): Geographic region
        conn: Database connection
    
    Returns:
        int|None: Mentor ID if routed successfully, None if no mentor available
    """
    # Find active mentors with this goal in specialties
    ph = "%s" if USE_POSTGRES else "?"
    mentor_rows = db_exec(conn, f"""
        SELECT id, name, email, specialties, regions_covered, current_month_load, max_students_per_month
        FROM cc_mentors
        WHERE active = {1 if USE_POSTGRES else 1}
        ORDER BY current_month_load ASC
        LIMIT 50
    """).fetchall()
    
    if not mentor_rows:
        return None
    
    # Filter by goal specialty and region coverage
    best_mentor = None
    for row in mentor_rows:
        mentor_id = row[0]
        specialties = json.loads(row[3] or "[]")
        regions = json.loads(row[4] or "[]")
        current_load = row[5]
        max_load = row[6]
        
        # Check if mentor has room
        if current_load >= max_load:
            continue
        
        # Check specialties match
        if goal not in specialties and "general" not in specialties:
            continue
        
        # Check region match (if region specified)
        if region and regions and region not in regions:
            continue
        
        best_mentor = (mentor_id, current_load)
        break
    
    if not best_mentor:
        return None
    
    mentor_id, _ = best_mentor
    
    # Increment mentor load
    db_exec(conn, f"""
        UPDATE cc_mentors
        SET current_month_load = current_month_load + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph}
    """, (mentor_id,))
    
    # Update inquiry routing
    db_exec(conn, f"""
        UPDATE cc_student_inquiries
        SET routed_to_mentor_id = {ph},
            updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph}
    """, (mentor_id, inquiry_id))
    
    conn.commit()
    return mentor_id


# ─── Claude Email Generation ─────────────────────────────────────────────────

def generate_first_response_email(
    student_name: str,
    goal: str,
    grade_level: str,
    mentor_name: str,
    region: Optional[str] = None,
    major_interest: Optional[str] = None,
    mentor_specialty: Optional[str] = None
) -> Tuple[str, str, int]:
    """
    Generate a warm first-touch email using Claude.
    
    Args:
        student_name (str): Student's name (for greeting)
        goal (str): Student's goal (college_list, essays, etc.)
        grade_level (str): Grade level (9-12, college)
        mentor_name (str): Mentor's name (for signature)
        region (str): Geographic region (optional)
        major_interest (str): Student's major interest (optional)
        mentor_specialty (str): Mentor's specialty (optional)
    
    Returns:
        tuple: (email_subject, email_body_html, tokens_used)
        - email_subject: e.g., "Let's chat about your college goals"
        - email_body_html: Plain text email (no HTML yet)
        - tokens_used: Total tokens from Claude API
    """
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return ("ERROR", "API key not configured", 0)
    
    # Build context for Claude
    region_context = f"\n- Region: {region}" if region else ""
    major_context = f"\n- Major Interest: {major_interest}" if major_interest else ""
    specialty_context = f"\n- Specialty: {mentor_specialty}" if mentor_specialty else ""
    
    prompt = f"""You are a mentor at College Confused, a nonprofit college prep platform founded by Darrian Belcher.
Your job is to send warm, authentic, first-touch emails to students who've submitted inquiries.

**Student Information:**
- Name: {student_name}
- Grade Level: {grade_level}
- Goal: {goal}{region_context}{major_context}

**Your Mentor Info:**
- Name: {mentor_name}{specialty_context}

**Email Requirements:**
1. 120-150 words (no longer)
2. Thank them for reaching out
3. Acknowledge their specific goal ({goal}) with one sentence of validation
4. Ask ONE clarifying question based on their grade level (e.g., if 12th grade: "What's your timeline for applications?")
5. Give them your email {mentor_name.lower().replace(" ", ".")}@collegeconfused.org + link to book a call (https://calendly.com/collegeconfused/mentorship)
6. Sign with your name — no title, no corporate language
7. Voice: Warm, authentic, community-first. Like Darrian Belcher wrote it — raw, real, not stuffy.
8. NO exclamation marks overuse. NO cheesy closing like "Excited to help!" — make it genuine.

**Template for subject line:** Short, personal, actionable (e.g., "Let's talk about your college list")

Generate ONLY the email body in this format:
SUBJECT: [short subject line here]
BODY:
[email body starting with "Hi {student_name},"]

NO preamble. Start immediately with SUBJECT:"""
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        # Parse subject and body from response
        lines = response_text.strip().split("\n")
        subject = ""
        body_lines = []
        in_body = False
        
        for line in lines:
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                in_body = True
            elif in_body:
                body_lines.append(line)
        
        body = "\n".join(body_lines).strip()
        
        # Fallback if parsing fails
        if not subject or not body:
            subject = f"Let's talk about your {goal}"
            body = response_text
        
        return (subject, body, tokens_used)
    
    except Exception as e:
        return (
            "Error generating email",
            f"Failed to generate email: {str(e)}",
            0
        )


# ─── Student Inquiry Creation ─────────────────────────────────────────────────

def create_student_inquiry(
    email: str,
    phone: Optional[str],
    name: str,
    grade_level: str,
    goal: str,
    region: Optional[str],
    major_interest: Optional[str],
    ip_address: Optional[str],
    conn
) -> int:
    """
    Create a new student inquiry with qualification and routing.
    
    Workflow:
    1. Qualify the inquiry using qualify_inquiry()
    2. Insert into cc_student_inquiries with qualification status
    3. Route to mentor using route_inquiry_to_mentor()
    4. Create metrics record
    
    Args:
        email, phone, name, grade_level, goal, region, major_interest, ip_address
        conn: Database connection
    
    Returns:
        int: Inquiry ID
    
    Raises:
        Exception: If email already exists or DB error occurs
    """
    phone = phone or ""
    region = region or ""
    major_interest = major_interest or ""
    ip_address = ip_address or ""
    
    # ── Qualify ───────────────────────────────────────────────────────────────
    t_start = time.time()
    qual_result = qualify_inquiry({
        "email": email,
        "name": name,
        "grade_level": grade_level,
        "goal": goal,
        "region": region,
        "major_interest": major_interest,
        "ip_address": ip_address
    })
    time_to_qualify_ms = int((time.time() - t_start) * 1000)
    
    is_qualified = qual_result["is_qualified"]
    confidence = qual_result["confidence"]
    reason = json.dumps(qual_result["reason"])
    
    # ── Insert inquiry ────────────────────────────────────────────────────────
    ph = "%s" if USE_POSTGRES else "?"
    qualified_at = datetime.utcnow().isoformat() if is_qualified else None
    
    cursor = db_exec(conn, f"""
        INSERT INTO cc_student_inquiries (
            email, phone, name, grade_level, goal, region, major_interest, ip_address,
            qualification_status, qualification_confidence, qualification_reason, qualified_at
        ) VALUES (
            {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph},
            {ph}, {ph}, {ph}, {ph}
        )
    """, (
        email, phone, name, grade_level, goal, region, major_interest, ip_address,
        "qualified" if is_qualified else "unqualified",
        confidence,
        reason,
        qualified_at
    ))
    
    inquiry_id = cursor.lastrowid
    
    # ── Route if qualified ────────────────────────────────────────────────────
    mentor_id = None
    if is_qualified:
        t_route_start = time.time()
        mentor_id = route_inquiry_to_mentor(inquiry_id, grade_level, goal, region, conn)
        time_to_route_ms = int((time.time() - t_route_start) * 1000)
    else:
        time_to_route_ms = 0
    
    # ── Create metrics record ─────────────────────────────────────────────────
    db_exec(conn, f"""
        INSERT INTO cc_inquiry_metrics (inquiry_id, time_to_qualify_ms, time_to_route_ms)
        VALUES ({ph}, {ph}, {ph})
    """, (inquiry_id, time_to_qualify_ms, time_to_route_ms))
    
    conn.commit()
    return inquiry_id


# ─── Email Sending (Sendgrid Integration) ───────────────────────────────────

def send_email_to_student(
    inquiry_id: int,
    mentor_id: int,
    email_subject: str,
    email_body: str,
    conn
) -> bool:
    """
    Send welcome email to student via Sendgrid.
    
    Workflow:
    1. Fetch student email from inquiry
    2. Fetch mentor email + info
    3. Call Sendgrid API with Sendgrid API key from settings
    4. Log email in cc_response_emails table
    5. Update cc_student_inquiries.mentor_response_sent_at
    
    Args:
        inquiry_id (int): Student inquiry ID
        mentor_id (int): Mentor ID
        email_subject (str): Email subject line
        email_body (str): Email body (plain text or HTML)
        conn: Database connection
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    # ── Fetch student email ───────────────────────────────────────────────────
    ph = "%s" if USE_POSTGRES else "?"
    inquiry_row = db_exec(conn, f"SELECT email, name FROM cc_student_inquiries WHERE id = {ph}", (inquiry_id,)).fetchone()
    
    if not inquiry_row:
        print(f"Inquiry {inquiry_id} not found")
        return False
    
    student_email = inquiry_row[0]
    student_name = inquiry_row[1]
    
    # ── Fetch mentor info ─────────────────────────────────────────────────────
    mentor_row = db_exec(conn, f"SELECT email, name FROM cc_mentors WHERE id = {ph}", (mentor_id,)).fetchone()
    
    if not mentor_row:
        print(f"Mentor {mentor_id} not found")
        return False
    
    mentor_email = mentor_row[0]
    mentor_name = mentor_row[1]
    
    # ── Call Sendgrid API ─────────────────────────────────────────────────────
    sendgrid_api_key = get_setting("cc_sendgrid_api_key")
    if not sendgrid_api_key:
        print("Sendgrid API key not configured")
        # Log as pending (will retry later)
        db_exec(conn, f"""
            INSERT INTO cc_response_emails (
                inquiry_id, mentor_id, email_subject, email_body_html, email_status
            ) VALUES ({ph}, {ph}, {ph}, {ph}, 'pending')
        """, (inquiry_id, mentor_id, email_subject, email_body))
        conn.commit()
        return False
    
    try:
        import requests
        
        sendgrid_url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {sendgrid_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "personalizations": [
                {
                    "to": [{"email": student_email, "name": student_name}],
                    "subject": email_subject
                }
            ],
            "from": {"email": mentor_email, "name": mentor_name},
            "content": [
                {
                    "type": "text/plain",
                    "value": email_body
                }
            ],
            "reply_to": {"email": mentor_email},
            "tracking_settings": {
                "open": {"enable": True},
                "click": {"enable": True}
            }
        }
        
        response = requests.post(sendgrid_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201, 202]:
            # ── Log successful send ───────────────────────────────────────────
            send_time = datetime.utcnow().isoformat()
            db_exec(conn, f"""
                INSERT INTO cc_response_emails (
                    inquiry_id, mentor_id, email_subject, email_body_html, email_status, email_sent_at
                ) VALUES ({ph}, {ph}, {ph}, {ph}, 'sent', {ph})
            """, (inquiry_id, mentor_id, email_subject, email_body, send_time))
            
            db_exec(conn, f"""
                UPDATE cc_student_inquiries
                SET mentor_response_sent_at = {ph}, status = 'responded', updated_at = CURRENT_TIMESTAMP
                WHERE id = {ph}
            """, (send_time, inquiry_id))
            
            conn.commit()
            return True
        else:
            print(f"Sendgrid API error: {response.status_code} - {response.text}")
            # Log as failed
            db_exec(conn, f"""
                INSERT INTO cc_response_emails (
                    inquiry_id, mentor_id, email_subject, email_body_html, email_status
                ) VALUES ({ph}, {ph}, {ph}, {ph}, 'bounced')
            """, (inquiry_id, mentor_id, email_subject, email_body))
            conn.commit()
            return False
    
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        # Log as pending (will retry)
        db_exec(conn, f"""
            INSERT INTO cc_response_emails (
                inquiry_id, mentor_id, email_subject, email_body_html, email_status
            ) VALUES ({ph}, {ph}, {ph}, {ph}, 'pending')
        """, (inquiry_id, mentor_id, email_subject, email_body))
        conn.commit()
        return False


# ─── Mentor Dashboard Helpers ─────────────────────────────────────────────────

def get_mentor_inquiries(
    mentor_id: int,
    conn,
    status: str = "new"
) -> List[Dict[str, Any]]:
    """
    Get all unresponded inquiries routed to a mentor.
    
    Args:
        mentor_id (int): Mentor ID
        conn: Database connection
        status (str): Filter by inquiry status (default: 'new')
    
    Returns:
        list[dict]: Inquiries with columns:
            - id, name, email, grade_level, goal, region, created_at, time_since_inquiry_min
    """
    ph = "%s" if USE_POSTGRES else "?"
    
    rows = db_exec(conn, f"""
        SELECT 
            id, name, email, grade_level, goal, region, created_at,
            CAST ((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) as time_since_inquiry_min
        FROM cc_student_inquiries
        WHERE routed_to_mentor_id = {ph} AND status = {ph}
        ORDER BY created_at DESC
    """, (mentor_id, status)).fetchall()
    
    results = []
    for row in rows:
        results.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "grade_level": row[3],
            "goal": row[4],
            "region": row[5],
            "created_at": row[6],
            "time_since_inquiry_min": row[7]
        })
    
    return results


def mentor_draft_response(
    inquiry_id: int,
    mentor_id: int,
    conn
) -> Dict[str, Any]:
    """
    Pre-fetch student inquiry data and generate a draft email response.
    
    Returns a draft that mentors can edit before sending.
    
    Args:
        inquiry_id (int): Student inquiry ID
        mentor_id (int): Mentor ID (for verification)
        conn: Database connection
    
    Returns:
        dict: {
            inquiry_id, student_name, goal, grade_level, region, major_interest,
            email_subject, email_body_html, ready_to_send: bool
        }
    """
    ph = "%s" if USE_POSTGRES else "?"
    
    # Fetch inquiry
    inquiry_row = db_exec(conn, f"""
        SELECT id, name, goal, grade_level, region, major_interest
        FROM cc_student_inquiries
        WHERE id = {ph} AND routed_to_mentor_id = {ph}
    """, (inquiry_id, mentor_id)).fetchone()
    
    if not inquiry_row:
        return {
            "error": "Inquiry not found or not routed to this mentor",
            "ready_to_send": False
        }
    
    student_id, student_name, goal, grade_level, region, major_interest = inquiry_row
    
    # Fetch mentor info
    mentor_row = db_exec(conn, f"""
        SELECT name, specialties
        FROM cc_mentors
        WHERE id = {ph}
    """, (mentor_id,)).fetchone()
    
    mentor_name = mentor_row[0]
    specialties = json.loads(mentor_row[1] or "[]")
    mentor_specialty = specialties[0] if specialties else None
    
    # Generate email
    email_subject, email_body, tokens = generate_first_response_email(
        student_name=student_name,
        goal=goal,
        grade_level=grade_level,
        mentor_name=mentor_name,
        region=region,
        major_interest=major_interest,
        mentor_specialty=mentor_specialty
    )
    
    return {
        "inquiry_id": inquiry_id,
        "student_name": student_name,
        "goal": goal,
        "grade_level": grade_level,
        "region": region,
        "major_interest": major_interest,
        "email_subject": email_subject,
        "email_body_html": email_body,
        "ready_to_send": "Error" not in email_subject,
        "mentor_id": mentor_id
    }
