import os
import sqlite3
import hashlib
import secrets
import re
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Detect environment ────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Some Postgres hosts emit postgres:// but psycopg2 requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import sql as pgsql

# SQLite fallback path (local dev)
DB_PATH    = os.path.join(os.path.dirname(__file__), '..', 'data', 'budget.db')
DB_PATH_QA = os.path.join(os.path.dirname(__file__), '..', 'data', 'budget_qa.db')

# QA / sandbox accounts that get their own isolated SQLite database
_QA_EMAILS = {"dbelcher003@gmail.com"}

# Module-level override: set by auth after login so get_conn() can route correctly
_active_db_path: str | None = None


def set_active_db(email: str | None):
    """
    Call this right after a user logs in (or logs out).
    Routes each user to their own isolated SQLite DB under data/users/.
    QA accounts get budget_qa.db.
    Only has effect in SQLite mode (local dev / self-hosted).
    """
    global _active_db_path
    if email is None:
        _active_db_path = None
        return
    email_clean = email.strip().lower()
    if email_clean in _QA_EMAILS:
        _active_db_path = DB_PATH_QA
        return
    # ── Per-user isolated database ───────────────────────────────────────────
    user_hash   = hashlib.sha256(email_clean.encode()).hexdigest()[:24]
    user_db_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'users')
    os.makedirs(user_db_dir, exist_ok=True)
    _active_db_path = os.path.join(user_db_dir, f'user_{user_hash}.db')


def _get_db_path() -> str:
    """Return the correct SQLite path for the current session."""
    return _active_db_path if _active_db_path else DB_PATH


# ── Connection factory ────────────────────────────────────────────────────────
def get_conn():
    """Return a connection to the current user's data DB (per-user isolated)."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(_get_db_path())
        conn.row_factory = sqlite3.Row
        return conn


def get_auth_conn():
    """
    Always return a connection to the SHARED auth DB (budget.db).
    Used for users table, app_settings, login_attempts — never per-user data.
    """
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Portable execute helper ───────────────────────────────────────────────────
def _execute(conn, query: str, params=None):
    """Execute a query, translating ? placeholders to %s for PostgreSQL."""
    if USE_POSTGRES:
        query = query.replace("?", "%s")
    c = conn.cursor()
    if params:
        c.execute(query, params)
    else:
        c.execute(query)
    return c


def execute(conn, query: str, params=None):
    """Public portable execute — translates ? to %s for PostgreSQL, returns cursor."""
    if USE_POSTGRES:
        query = query.replace("?", "%s")
    c = conn.cursor()
    if params is not None:
        c.execute(query, params)
    else:
        c.execute(query)
    return c


def fetchone(conn, query: str, params=None):
    """Execute a query and return one row."""
    c = execute(conn, query, params)
    return c.fetchone()


# ── Portable read_sql replacement ────────────────────────────────────────────
def read_sql(query: str, conn, params=None):
    """Return a pandas DataFrame from a SQL query, works with both backends."""
    import pandas as pd
    if USE_POSTGRES:
        query = query.replace("?", "%s")
        return pd.read_sql(query, conn, params=params)
    else:
        if params:
            return pd.read_sql(query, conn, params=params)
        return pd.read_sql(query, conn)


# ── Schema init ───────────────────────────────────────────────────────────────
def init_db():
    """
    Initialize both the shared auth DB and the current user's data DB.
    - Auth DB (budget.db): users, app_settings, waitlist, login_attempts
    - Data DB (per-user): all financial tables (expenses, income, bank_transactions, etc.)
    Safe to call multiple times (all CREATE TABLE IF NOT EXISTS).
    """
    # ── 1. Init auth tables in the shared budget.db ───────────────────────────
    auth_conn = get_auth_conn()
    auth_c    = auth_conn.cursor()
    if USE_POSTGRES:
        # users, waitlist, app_settings, login_attempts, pa_* in shared DB
        auth_c.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, salt TEXT NOT NULL,
            plan TEXT DEFAULT 'free', stripe_customer_id TEXT DEFAULT '',
            stripe_subscription_id TEXT DEFAULT '', subscription_status TEXT DEFAULT 'none',
            created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')), last_login TEXT
        )''')
        auth_c.execute('''CREATE TABLE IF NOT EXISTS waitlist (
            id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '', source TEXT DEFAULT '',
            created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
        )''')
        auth_c.execute('''CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)''')
        auth_c.execute('''CREATE TABLE IF NOT EXISTS login_attempts (
            id SERIAL PRIMARY KEY, email TEXT NOT NULL,
            attempted_at REAL NOT NULL, success INTEGER DEFAULT 0
        )''')
    else:
        auth_c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, salt TEXT NOT NULL,
            plan TEXT DEFAULT 'free', stripe_customer_id TEXT DEFAULT '',
            stripe_subscription_id TEXT DEFAULT '', subscription_status TEXT DEFAULT 'none',
            created_at TEXT DEFAULT (datetime('now')), last_login TEXT
        )''')
        auth_c.execute('''CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '', source TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )''')
        auth_c.execute('''CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)''')
        auth_c.execute('''CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL,
            attempted_at REAL NOT NULL, success INTEGER DEFAULT 0
        )''')
    auth_conn.commit()
    auth_conn.close()

    # ── 2. Init financial data tables in the user's isolated DB ──────────────
    conn = get_conn()
    c    = conn.cursor()
    if USE_POSTGRES:
        _init_postgres(c)
    else:
        _init_sqlite(c)

    # ── Migrations ────────────────────────────────────────────────────────────
    if USE_POSTGRES:
        c.execute("""SELECT column_name FROM information_schema.columns
                     WHERE table_name='bank_transactions' AND column_name='is_debit'""")
        if not c.fetchone():
            c.execute("ALTER TABLE bank_transactions ADD COLUMN is_debit INTEGER DEFAULT 1")
        c.execute("""SELECT column_name FROM information_schema.columns
                     WHERE table_name='recurring_templates' AND column_name='due_day'""")
        if not c.fetchone():
            c.execute("ALTER TABLE recurring_templates ADD COLUMN due_day INTEGER DEFAULT NULL")
    else:
        c.execute("PRAGMA table_info(bank_transactions)")
        if 'is_debit' not in [row[1] for row in c.fetchall()]:
            c.execute("ALTER TABLE bank_transactions ADD COLUMN is_debit INTEGER DEFAULT 1")
        c.execute("PRAGMA table_info(recurring_templates)")
        if 'due_day' not in [row[1] for row in c.fetchall()]:
            c.execute("ALTER TABLE recurring_templates ADD COLUMN due_day INTEGER DEFAULT NULL")

    # Migration: add user_id to all financial data tables
    for tbl in ['expenses','income','bank_transactions','recurring_templates',
                'financial_goals','goal_checklist','net_worth_snapshots',
                'investment_context','receipts','sole_archive']:
        try:
            if USE_POSTGRES:
                c.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name='user_id'", (tbl,))
                if not c.fetchone():
                    c.execute(f"ALTER TABLE {tbl} ADD COLUMN user_id INTEGER DEFAULT NULL")
            else:
                c.execute(f"PRAGMA table_info({tbl})")
                if 'user_id' not in [row[1] for row in c.fetchall()]:
                    c.execute(f"ALTER TABLE {tbl} ADD COLUMN user_id INTEGER DEFAULT NULL")
        except Exception:
            pass

    conn.commit()
    conn.close()


def _init_postgres(c):
    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id SERIAL PRIMARY KEY,
        month TEXT NOT NULL,
        source TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id SERIAL PRIMARY KEY,
        month TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        projected REAL DEFAULT 0,
        actual REAL DEFAULT 0,
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sole_archive (
        id SERIAL PRIMARY KEY,
        date TEXT NOT NULL,
        item TEXT NOT NULL,
        size TEXT,
        buy_price REAL NOT NULL,
        sell_price REAL DEFAULT 0,
        platform TEXT,
        fees REAL DEFAULT 0,
        shipping REAL DEFAULT 0,
        status TEXT DEFAULT 'inventory',
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS recurring_templates (
        id SERIAL PRIMARY KEY,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        projected REAL DEFAULT 0,
        active INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bank_transactions (
        id SERIAL PRIMARY KEY,
        month TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        is_debit INTEGER DEFAULT 1,
        category TEXT,
        subcategory TEXT,
        matched_expense_id INTEGER,
        source TEXT DEFAULT 'manual',
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS receipts (
        id SERIAL PRIMARY KEY,
        month TEXT NOT NULL,
        date TEXT NOT NULL,
        merchant TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        receipt_type TEXT DEFAULT 'expense',
        filename TEXT,
        image_data BYTEA,
        notes TEXT,
        created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS investment_context (
        id SERIAL PRIMARY KEY,
        bal_401k REAL DEFAULT 0,
        contrib_401k_ytd REAL DEFAULT 0,
        match_401k_ytd REAL DEFAULT 0,
        bal_roth REAL DEFAULT 0,
        contrib_roth_ytd REAL DEFAULT 0,
        bal_hsa REAL DEFAULT 0,
        contrib_hsa_ytd REAL DEFAULT 0,
        bal_brokerage REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        updated_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS financial_goals (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        goal_type TEXT DEFAULT 'savings',
        target_amount REAL DEFAULT 0,
        current_amount REAL DEFAULT 0,
        target_date TEXT,
        period TEXT DEFAULT 'yearly',
        category TEXT DEFAULT '',
        status TEXT DEFAULT 'active',
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS goal_checklist (
        id SERIAL PRIMARY KEY,
        goal_id INTEGER REFERENCES financial_goals(id) ON DELETE CASCADE,
        item TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS net_worth_snapshots (
        id SERIAL PRIMARY KEY,
        snapshot_date TEXT NOT NULL,
        label TEXT DEFAULT '',
        checking REAL DEFAULT 0,
        savings REAL DEFAULT 0,
        cash_other REAL DEFAULT 0,
        bal_401k REAL DEFAULT 0,
        bal_roth REAL DEFAULT 0,
        bal_hsa REAL DEFAULT 0,
        bal_brokerage REAL DEFAULT 0,
        home_value REAL DEFAULT 0,
        vehicle_value REAL DEFAULT 0,
        other_assets REAL DEFAULT 0,
        credit_card_debt REAL DEFAULT 0,
        student_loans REAL DEFAULT 0,
        car_loan REAL DEFAULT 0,
        other_liabilities REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        plan TEXT DEFAULT 'free',
        stripe_customer_id TEXT DEFAULT '',
        stripe_subscription_id TEXT DEFAULT '',
        subscription_status TEXT DEFAULT 'none',
        created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
        last_login TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS waitlist (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT DEFAULT '',
        source TEXT DEFAULT '',
        created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # ── Personal Assistant tables ─────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS pa_emails (
        id SERIAL PRIMARY KEY,
        gmail_id TEXT UNIQUE NOT NULL,
        thread_id TEXT DEFAULT '',
        date TEXT NOT NULL,
        date_iso TEXT NOT NULL,
        subject TEXT NOT NULL,
        sender TEXT NOT NULL,
        snippet TEXT DEFAULT '',
        email_type TEXT DEFAULT 'unknown',
        is_purchase INTEGER DEFAULT 0,
        is_notification INTEGER DEFAULT 0,
        is_task INTEGER DEFAULT 0,
        is_newsletter INTEGER DEFAULT 0,
        extracted_amount REAL DEFAULT NULL,
        extracted_merchant TEXT DEFAULT NULL,
        suggested_category TEXT DEFAULT NULL,
        suggested_subcategory TEXT DEFAULT NULL,
        purchase_description TEXT DEFAULT NULL,
        priority TEXT DEFAULT 'normal',
        confidence REAL DEFAULT 0,
        llm_parsed INTEGER DEFAULT 0,
        expense_logged INTEGER DEFAULT 0,
        task_created INTEGER DEFAULT 0,
        is_unread INTEGER DEFAULT 1,
        fetched_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS pa_tasks (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        due_date TEXT DEFAULT NULL,
        priority TEXT DEFAULT 'normal',
        status TEXT DEFAULT 'open',
        source TEXT DEFAULT 'manual',
        source_email_id TEXT DEFAULT NULL,
        source_email_subject TEXT DEFAULT NULL,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
        completed_at TEXT DEFAULT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS pa_notification_rules (
        id SERIAL PRIMARY KEY,
        rule_name TEXT NOT NULL,
        match_type TEXT DEFAULT 'sender',
        match_value TEXT NOT NULL,
        action TEXT DEFAULT 'label',
        action_value TEXT DEFAULT '',
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
    )''')


def _init_sqlite(c):
    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        source TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        projected REAL DEFAULT 0,
        actual REAL DEFAULT 0,
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sole_archive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        item TEXT NOT NULL,
        size TEXT,
        buy_price REAL NOT NULL,
        sell_price REAL DEFAULT 0,
        platform TEXT,
        fees REAL DEFAULT 0,
        shipping REAL DEFAULT 0,
        status TEXT DEFAULT 'inventory',
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS recurring_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        projected REAL DEFAULT 0,
        active INTEGER DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bank_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        is_debit INTEGER DEFAULT 1,
        category TEXT,
        subcategory TEXT,
        matched_expense_id INTEGER,
        source TEXT DEFAULT 'manual',
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        date TEXT NOT NULL,
        merchant TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        receipt_type TEXT DEFAULT 'expense',
        filename TEXT,
        image_data BLOB,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS investment_context (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bal_401k REAL DEFAULT 0,
        contrib_401k_ytd REAL DEFAULT 0,
        match_401k_ytd REAL DEFAULT 0,
        bal_roth REAL DEFAULT 0,
        contrib_roth_ytd REAL DEFAULT 0,
        bal_hsa REAL DEFAULT 0,
        contrib_hsa_ytd REAL DEFAULT 0,
        bal_brokerage REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        updated_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS financial_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        goal_type TEXT DEFAULT 'savings',
        target_amount REAL DEFAULT 0,
        current_amount REAL DEFAULT 0,
        target_date TEXT,
        period TEXT DEFAULT 'yearly',
        category TEXT DEFAULT '',
        status TEXT DEFAULT 'active',
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS goal_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER REFERENCES financial_goals(id),
        item TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS net_worth_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date TEXT NOT NULL,
        label TEXT DEFAULT '',
        checking REAL DEFAULT 0,
        savings REAL DEFAULT 0,
        cash_other REAL DEFAULT 0,
        bal_401k REAL DEFAULT 0,
        bal_roth REAL DEFAULT 0,
        bal_hsa REAL DEFAULT 0,
        bal_brokerage REAL DEFAULT 0,
        home_value REAL DEFAULT 0,
        vehicle_value REAL DEFAULT 0,
        other_assets REAL DEFAULT 0,
        credit_card_debt REAL DEFAULT 0,
        student_loans REAL DEFAULT 0,
        car_loan REAL DEFAULT 0,
        other_liabilities REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        plan TEXT DEFAULT 'free',
        stripe_customer_id TEXT DEFAULT '',
        stripe_subscription_id TEXT DEFAULT '',
        subscription_status TEXT DEFAULT 'none',
        created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS waitlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT DEFAULT '',
        source TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # ── Personal Assistant tables ─────────────────────────────────────────────
    c.execute('''CREATE TABLE IF NOT EXISTS pa_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gmail_id TEXT UNIQUE NOT NULL,
        thread_id TEXT DEFAULT '',
        date TEXT NOT NULL,
        date_iso TEXT NOT NULL,
        subject TEXT NOT NULL,
        sender TEXT NOT NULL,
        snippet TEXT DEFAULT '',
        email_type TEXT DEFAULT 'unknown',
        is_purchase INTEGER DEFAULT 0,
        is_notification INTEGER DEFAULT 0,
        is_task INTEGER DEFAULT 0,
        is_newsletter INTEGER DEFAULT 0,
        extracted_amount REAL DEFAULT NULL,
        extracted_merchant TEXT DEFAULT NULL,
        suggested_category TEXT DEFAULT NULL,
        suggested_subcategory TEXT DEFAULT NULL,
        purchase_description TEXT DEFAULT NULL,
        priority TEXT DEFAULT 'normal',
        confidence REAL DEFAULT 0,
        llm_parsed INTEGER DEFAULT 0,
        expense_logged INTEGER DEFAULT 0,
        task_created INTEGER DEFAULT 0,
        is_unread INTEGER DEFAULT 1,
        fetched_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS pa_tasks (
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
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS pa_notification_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_name TEXT NOT NULL,
        match_type TEXT DEFAULT 'sender',
        match_value TEXT NOT NULL,
        action TEXT DEFAULT 'label',
        action_value TEXT DEFAULT '',
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )''')


# ── App settings helpers (key/value store — stored in shared auth DB) ─────────
def _ensure_settings_table(conn):
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()


def get_setting(key: str, default: str = "") -> str:
    """Retrieve a single app setting by key (reads from shared auth DB)."""
    conn = get_auth_conn()
    _ensure_settings_table(conn)
    c = execute(conn, "SELECT value FROM app_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return default
    return row[0] if row[0] is not None else default


def set_setting(key: str, value: str):
    """Upsert a single app setting (writes to shared auth DB)."""
    conn = get_auth_conn()
    _ensure_settings_table(conn)
    if USE_POSTGRES:
        execute(conn,
            "INSERT INTO app_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (key, value)
        )
    else:
        execute(conn,
            "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
    conn.commit()
    conn.close()


# ── Input validation helpers ──────────────────────────────────────────────────
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def validate_email(email: str) -> bool:
    """Return True if email looks valid (RFC-ish, max 254 chars)."""
    if not email or len(email) > 254:
        return False
    return bool(_EMAIL_RE.match(email.strip()))


def validate_password(password: str) -> tuple[bool, str]:
    """
    Enforce password policy. Returns (ok, error_message).
    Policy: 8+ chars, at least one letter, at least one digit.
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password) > 128:
        return False, "Password must be under 128 characters."
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    return True, ""


# ── Login attempt tracking (brute-force protection) ───────────────────────────
_MAX_ATTEMPTS   = 10          # lock after this many failures
_LOCKOUT_SECS   = 15 * 60    # 15-minute lockout window
_WINDOW_SECS    = 15 * 60    # count failures within this window


def _ensure_login_attempts_table(conn):
    if USE_POSTGRES:
        conn.cursor().execute('''CREATE TABLE IF NOT EXISTS login_attempts (
            id SERIAL PRIMARY KEY, email TEXT NOT NULL,
            attempted_at REAL NOT NULL, success INTEGER DEFAULT 0
        )''')
    else:
        conn.cursor().execute('''CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL,
            attempted_at REAL NOT NULL, success INTEGER DEFAULT 0
        )''')
    conn.commit()


def _record_login_attempt(email: str, success: bool):
    conn = get_auth_conn()   # always log to shared auth DB
    _ensure_login_attempts_table(conn)
    execute(conn,
        "INSERT INTO login_attempts (email, attempted_at, success) VALUES (?, ?, ?)",
        (email.lower(), time.time(), 1 if success else 0)
    )
    conn.commit()
    conn.close()


def is_account_locked(email: str) -> tuple[bool, int]:
    """
    Returns (locked, seconds_remaining).
    Locked if >= _MAX_ATTEMPTS failures in the last _WINDOW_SECS.
    Reads from shared auth DB (login_attempts is global, not per-user).
    """
    conn = get_auth_conn()   # always read from shared auth DB
    _ensure_login_attempts_table(conn)
    cutoff = time.time() - _WINDOW_SECS
    c = execute(conn,
        "SELECT attempted_at FROM login_attempts WHERE email=? AND success=0 AND attempted_at > ? ORDER BY attempted_at DESC",
        (email.lower(), cutoff)
    )
    rows = c.fetchall()
    conn.close()
    if len(rows) < _MAX_ATTEMPTS:
        return False, 0
    most_recent = rows[0][0]
    remaining = int(_LOCKOUT_SECS - (time.time() - most_recent))
    return True, max(remaining, 0)


# ── Password hashing (bcrypt with SHA-256 fallback for existing accounts) ─────
def _hash_password_bcrypt(password: str) -> str:
    """Hash with bcrypt (work factor 12). Returns the full bcrypt hash string."""
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _verify_password_bcrypt(password: str, stored_hash: str) -> bool:
    """Verify a bcrypt hash."""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False


def _hash_password_legacy(password: str, salt: str) -> str:
    """Legacy SHA-256 hash — only used to verify old accounts during migration."""
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def create_user(email: str, password: str) -> dict | None:
    """
    Create a new user. Writes to the shared auth DB (budget.db).
    Returns the user dict on success, None if email already exists or validation fails.
    """
    email = email.strip().lower()
    if not validate_email(email):
        return None
    ok, _ = validate_password(password)
    if not ok:
        return None

    pw_hash = _hash_password_bcrypt(password)
    salt    = "bcrypt"
    conn    = get_auth_conn()   # users table is in shared auth DB
    try:
        if USE_POSTGRES:
            c = execute(conn,
                """INSERT INTO users (email, password_hash, salt, plan, subscription_status)
                   VALUES (%s, %s, %s, 'free', 'none') RETURNING id, email, plan, subscription_status""",
                (email, pw_hash, salt)
            )
            row = c.fetchone()
            conn.commit()
            conn.close()
            return {"id": row[0], "email": row[1], "plan": row[2], "subscription_status": row[3]}
        else:
            c = execute(conn,
                "INSERT INTO users (email, password_hash, salt, plan, subscription_status) VALUES (?, ?, ?, 'free', 'none')",
                (email, pw_hash, salt)
            )
            user_id = c.lastrowid
            conn.commit()
            conn.close()
            return {"id": user_id, "email": email, "plan": "free", "subscription_status": "none"}
    except Exception:
        conn.close()
        return None


def authenticate_user(email: str, password: str) -> dict | None:
    """
    Verify email + password. Reads from the shared auth DB (budget.db).
    - Checks account lockout before attempting verification.
    - Records every attempt (success or failure).
    - Supports both bcrypt (new) and legacy SHA-256 accounts.
    Returns user dict on success, None on failure.
    """
    email = email.strip().lower()

    locked, remaining = is_account_locked(email)
    if locked:
        _record_login_attempt(email, False)
        return None

    conn = get_auth_conn()   # users table is in shared auth DB
    c = execute(conn, "SELECT * FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if row is None:
        conn.close()
        import bcrypt
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4)))
        _record_login_attempt(email, False)
        return None

    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        user = dict(zip(cols, row))
    else:
        user = dict(row)

    stored_hash = user["password_hash"]
    salt        = user.get("salt", "")

    verified = False
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        verified = _verify_password_bcrypt(password, stored_hash)
    else:
        legacy_hash = _hash_password_legacy(password, salt)
        if secrets.compare_digest(legacy_hash, stored_hash):
            verified = True
            new_hash = _hash_password_bcrypt(password)
            execute(conn, "UPDATE users SET password_hash=?, salt='bcrypt' WHERE id=?",
                    (new_hash, user["id"]))
            conn.commit()

    if not verified:
        conn.close()
        _record_login_attempt(email, False)
        return None

    if USE_POSTGRES:
        execute(conn, "UPDATE users SET last_login = to_char(now(), 'YYYY-MM-DD HH24:MI:SS') WHERE id = %s",
                (user["id"],))
    else:
        execute(conn, "UPDATE users SET last_login = datetime('now') WHERE id = ?", (user["id"],))
    conn.commit()
    conn.close()
    _record_login_attempt(email, True)
    user.pop("password_hash", None)
    user.pop("salt", None)
    return user


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by ID from the shared auth DB."""
    conn = get_auth_conn()
    c = execute(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return None
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return dict(zip(cols, row))
    return dict(row)


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user by email from the shared auth DB."""
    email = email.strip().lower()
    conn  = get_auth_conn()
    c = execute(conn, "SELECT * FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return None
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return dict(zip(cols, row))
    return dict(row)


def update_user_subscription(user_id: int, plan: str, stripe_customer_id: str,
                              stripe_subscription_id: str, subscription_status: str):
    """Update a user's subscription details. Writes to shared auth DB."""
    conn = get_auth_conn()
    execute(conn,
        "UPDATE users SET plan=?, stripe_customer_id=?, stripe_subscription_id=?, subscription_status=? WHERE id=?",
        (plan, stripe_customer_id, stripe_subscription_id, subscription_status, user_id)
    )
    conn.commit()
    conn.close()


# ── Owner / dev accounts — always Pro regardless of subscription ──────────────
# All compared lowercase (is_pro_user lowercases before checking)
_OWNER_EMAILS = {
    "darrianbelcher@gmail.com",    # primary
    "darrianebelcher@gmail.com",   # registered account (lowercase)
}

# ── Sandbox/QA accounts — NEVER granted Pro via owner/admin shortcuts ─────────
# These accounts must go through real (test) Stripe checkout to get Pro.
_SANDBOX_EMAILS = {
    "dbelcher003@gmail.com",       # QA / payment testing account
}

def is_cc_ai_allowed(user_email: str) -> bool:
    """CC AI features are owner-only until a dedicated CC key is configured.
    Set cc_ai_owner_only=0 in app_settings to open AI to all CC users."""
    email = (user_email or "").strip().lower()
    try:
        owner_only = get_setting("cc_ai_owner_only", "1")
    except Exception:
        owner_only = "1"
    if str(owner_only) == "0":
        return True  # AI open to everyone
    return email in _OWNER_EMAILS


def is_pro_user(user: dict) -> bool:
    """Return True if the user has an active Pro subscription."""
    if not user:
        return False
    email = user.get("email", "").strip().lower()
    # Sandbox accounts are NEVER auto-granted Pro — must pay via Stripe test checkout
    if email in _SANDBOX_EMAILS:
        plan = user.get("plan", "free")
        status = user.get("subscription_status", "none")
        return plan == "pro" and status in ("active", "trialing")
    # Owner accounts are always Pro
    if email in _OWNER_EMAILS:
        return True
    # Admin override via ADMIN_EMAILS env var (comma-separated)
    admin_emails = os.environ.get("ADMIN_EMAILS", "").split(",")
    if email in [e.strip().lower() for e in admin_emails if e.strip()]:
        return True
    plan = user.get("plan", "free")
    status = user.get("subscription_status", "none")
    return plan == "pro" and status in ("active", "trialing")


# ── Token usage tracking ──────────────────────────────────────────────────────
def _ensure_token_usage_table():
    """Create token_usage table in the shared auth DB if it doesn't exist."""
    conn = get_auth_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute('''CREATE TABLE IF NOT EXISTS token_usage (
            id SERIAL PRIMARY KEY,
            user_email TEXT NOT NULL,
            site TEXT NOT NULL DEFAULT 'pss',
            page TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            used_byok INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
        )''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            site TEXT NOT NULL DEFAULT 'pss',
            page TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            used_byok INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )''')
    conn.commit()
    conn.close()


def log_token_usage(user_email: str, page: str, model: str,
                    input_tokens: int, output_tokens: int,
                    site: str = "pss", used_byok: bool = False):
    """
    Record a single AI API call's token consumption in the shared auth DB.
    Call this after every successful Anthropic response.
    """
    _ensure_token_usage_table()
    conn = get_auth_conn()
    total = input_tokens + output_tokens
    execute(conn,
        "INSERT INTO token_usage (user_email, site, page, model, input_tokens, output_tokens, total_tokens, used_byok) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_email.strip().lower(), site, page, model,
         input_tokens, output_tokens, total, 1 if used_byok else 0)
    )
    conn.commit()
    conn.close()


def get_token_usage_summary() -> list:
    """Return per-user token usage totals from the shared auth DB."""
    _ensure_token_usage_table()
    conn = get_auth_conn()
    c = execute(conn,
        """SELECT user_email, site,
                  COUNT(*) as calls,
                  SUM(input_tokens) as total_input,
                  SUM(output_tokens) as total_output,
                  SUM(total_tokens) as total_tokens,
                  SUM(used_byok) as byok_calls,
                  MAX(created_at) as last_call
           FROM token_usage
           GROUP BY user_email, site
           ORDER BY total_tokens DESC"""
    )
    rows = c.fetchall()
    conn.close()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


def get_token_usage_detail(user_email: str = None, limit: int = 200) -> list:
    """Return raw token usage rows, optionally filtered by user."""
    _ensure_token_usage_table()
    conn = get_auth_conn()
    if user_email:
        c = execute(conn,
            "SELECT * FROM token_usage WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
            (user_email.strip().lower(), limit)
        )
    else:
        c = execute(conn,
            "SELECT * FROM token_usage ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
    rows = c.fetchall()
    conn.close()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


def add_to_waitlist(email: str, name: str = "", source: str = "") -> bool:
    """Add an email to the waitlist (shared auth DB)."""
    email = email.strip().lower()
    conn  = get_auth_conn()
    try:
        execute(conn, "INSERT INTO waitlist (email, name, source) VALUES (?, ?, ?)",
                (email, name.strip(), source.strip()))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_waitlist_count() -> int:
    """Return total waitlist signups from shared auth DB."""
    conn  = get_auth_conn()
    c     = execute(conn, "SELECT COUNT(*) FROM waitlist")
    count = c.fetchone()[0]
    conn.close()
    return int(count)


# ── Investment context helpers ────────────────────────────────────────────────
_INV_FIELDS = [
    "bal_401k", "contrib_401k_ytd", "match_401k_ytd",
    "bal_roth", "contrib_roth_ytd",
    "bal_hsa", "contrib_hsa_ytd",
    "bal_brokerage", "notes",
]

_INV_DEFAULTS = {f: 0.0 for f in _INV_FIELDS}
_INV_DEFAULTS["notes"] = ""


def load_investment_context() -> dict:
    """Return the saved investment context row as a dict, or defaults if none exists."""
    conn = get_conn()
    c = execute(conn, "SELECT * FROM investment_context ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row is None:
        return dict(_INV_DEFAULTS)
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        return dict(zip(cols, row))
    else:
        return dict(row)


def save_investment_context(data: dict):
    """Upsert the single investment context row (delete-then-insert)."""
    conn = get_conn()
    execute(conn, "DELETE FROM investment_context")
    if USE_POSTGRES:
        execute(conn,
            """INSERT INTO investment_context
               (bal_401k, contrib_401k_ytd, match_401k_ytd,
                bal_roth, contrib_roth_ytd,
                bal_hsa, contrib_hsa_ytd,
                bal_brokerage, notes,
                updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, to_char(now(),'YYYY-MM-DD HH24:MI:SS'))""",
            (
                data.get("bal_401k", 0), data.get("contrib_401k_ytd", 0), data.get("match_401k_ytd", 0),
                data.get("bal_roth", 0), data.get("contrib_roth_ytd", 0),
                data.get("bal_hsa", 0), data.get("contrib_hsa_ytd", 0),
                data.get("bal_brokerage", 0), data.get("notes", ""),
            )
        )
    else:
        execute(conn,
            """INSERT INTO investment_context
               (bal_401k, contrib_401k_ytd, match_401k_ytd,
                bal_roth, contrib_roth_ytd,
                bal_hsa, contrib_hsa_ytd,
                bal_brokerage, notes,
                updated_at)
               VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))""",
            (
                data.get("bal_401k", 0), data.get("contrib_401k_ytd", 0), data.get("match_401k_ytd", 0),
                data.get("bal_roth", 0), data.get("contrib_roth_ytd", 0),
                data.get("bal_hsa", 0), data.get("contrib_hsa_ytd", 0),
                data.get("bal_brokerage", 0), data.get("notes", ""),
            )
        )
    conn.commit()
    conn.close()


# ── Seed helpers ──────────────────────────────────────────────────────────────
def seed_budget(month: str, user_id: int = 0):
    conn = get_conn()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("SELECT COUNT(*) FROM expenses WHERE month = %s AND user_id = %s", (month, user_id))
    else:
        c.execute("SELECT COUNT(*) FROM expenses WHERE month = ? AND user_id = ?", (month, user_id))

    if c.fetchone()[0] > 0:
        conn.close()
        return

    # Default projected amounts are 0 for all new users.
    # (Owner's personal values are already seeded in their own DB.)
    categories = [
        ("Housing", "Mortgage / Rent", 0),
        ("Housing", "Phone", 0),
        ("Housing", "Electricity", 0),
        ("Housing", "Gas", 0),
        ("Housing", "Water and Sewer", 0),
        ("Housing", "Cable / WiFi", 0),
        ("Housing", "Waste Removal", 0),
        ("Housing", "Maintenance / Repairs", 0),
        ("Housing", "Supplies", 0),
        ("Transportation", "Vehicle Payment", 0),
        ("Transportation", "Insurance", 0),
        ("Transportation", "Fuel", 0),
        ("Transportation", "Maintenance", 0),
        ("Insurance", "Renters", 0),
        ("Insurance", "Health", 0),
        ("Insurance", "Pet", 0),
        ("Food", "Groceries", 0),
        ("Food", "Dining Out", 0),
        ("Pets", "Food", 0),
        ("Pets", "Medical", 0),
        ("Pets", "Grooming", 0),
        ("Personal Care", "Medical", 0),
        ("Personal Care", "Hair / Nails", 0),
        ("Entertainment", "Night Out", 0),
        ("Entertainment", "Music Platforms", 0),
        ("Entertainment", "Movies", 0),
        ("Entertainment", "Subscriptions", 0),
        ("Loans", "Credit Card", 0),
        ("Savings / Investments", "Roth IRA", 0),
        ("Savings / Investments", "Retirement Account", 0),
    ]

    if USE_POSTGRES:
        for cat, sub, proj in categories:
            c.execute(
                "INSERT INTO expenses (month, category, subcategory, projected, actual, user_id) VALUES (%s, %s, %s, %s, 0, %s)",
                (month, cat, sub, proj, user_id)
            )
    else:
        c.executemany(
            "INSERT INTO expenses (month, category, subcategory, projected, actual, user_id) VALUES (?, ?, ?, ?, 0, ?)",
            [(month, cat, sub, proj, user_id) for cat, sub, proj in categories]
        )

    conn.commit()
    conn.close()


def seed_income(month: str, user_id: int = 0):
    conn = get_conn()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("SELECT COUNT(*) FROM income WHERE month = %s AND user_id = %s", (month, user_id))
    else:
        c.execute("SELECT COUNT(*) FROM income WHERE month = ? AND user_id = ?", (month, user_id))

    if c.fetchone()[0] > 0:
        conn.close()
        return

    rows = [
        (month, "Salary — Paycheck 1 (Post-Tax)", 0, "Bi-weekly take-home", user_id),
        (month, "Salary — Paycheck 2 (Post-Tax)", 0, "Bi-weekly take-home", user_id),
        (month, "Business Income", 0, "Side hustle / resale / freelance", user_id),
    ]

    if USE_POSTGRES:
        for row in rows:
            c.execute(
                "INSERT INTO income (month, source, amount, notes, user_id) VALUES (%s, %s, %s, %s, %s)",
                row
            )
    else:
        c.executemany(
            "INSERT INTO income (month, source, amount, notes, user_id) VALUES (?, ?, ?, ?, ?)",
            rows
        )

    conn.commit()
    conn.close()
