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

# Railway (and some other hosts) emit postgres:// but psycopg2 requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import sql as pgsql

# SQLite fallback path (local dev)
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'budget.db')


# ── Connection factory ────────────────────────────────────────────────────────
def get_conn():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
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
    conn = get_conn()
    c = conn.cursor()

    if USE_POSTGRES:
        _init_postgres(c)
    else:
        _init_sqlite(c)

    # ── Migrations: add columns to existing tables if missing ────────────────
    if USE_POSTGRES:
        c.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='bank_transactions' AND column_name='is_debit'
        """)
        if not c.fetchone():
            c.execute("ALTER TABLE bank_transactions ADD COLUMN is_debit INTEGER DEFAULT 1")
    else:
        c.execute("PRAGMA table_info(bank_transactions)")
        cols = [row[1] for row in c.fetchall()]
        if 'is_debit' not in cols:
            c.execute("ALTER TABLE bank_transactions ADD COLUMN is_debit INTEGER DEFAULT 1")

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


# ── App settings helpers (key/value store) ───────────────────────────────────
def _ensure_settings_table(conn):
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    conn.commit()


def get_setting(key: str, default: str = "") -> str:
    """Retrieve a single app setting by key."""
    conn = get_conn()
    _ensure_settings_table(conn)
    c = execute(conn, "SELECT value FROM app_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return default
    return row[0] if row[0] is not None else default


def set_setting(key: str, value: str):
    """Upsert a single app setting."""
    conn = get_conn()
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
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            attempted_at REAL NOT NULL,
            success INTEGER DEFAULT 0
        )''')
    else:
        conn.cursor().execute('''CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            attempted_at REAL NOT NULL,
            success INTEGER DEFAULT 0
        )''')
    conn.commit()


def _record_login_attempt(email: str, success: bool):
    conn = get_conn()
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
    """
    conn = get_conn()
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
    # Locked — compute remaining time from the most recent failure
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
    Create a new user with bcrypt password hashing.
    Returns the user dict on success, None if email already exists or validation fails.
    """
    email = email.strip().lower()
    if not validate_email(email):
        return None
    ok, _ = validate_password(password)
    if not ok:
        return None

    pw_hash = _hash_password_bcrypt(password)
    # salt column kept for schema compatibility but unused for new accounts
    salt = "bcrypt"
    conn = get_conn()
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
    Verify email + password with brute-force protection.
    - Checks account lockout before attempting verification.
    - Records every attempt (success or failure).
    - Supports both bcrypt (new) and legacy SHA-256 accounts.
    - On successful legacy login, upgrades hash to bcrypt transparently.
    Returns user dict on success, None on failure.
    """
    email = email.strip().lower()

    # ── Brute-force check ─────────────────────────────────────────────────────
    locked, remaining = is_account_locked(email)
    if locked:
        # Record this attempt too (counts against them)
        _record_login_attempt(email, False)
        return None

    conn = get_conn()
    c = execute(conn, "SELECT * FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if row is None:
        conn.close()
        # Constant-time dummy work to prevent user enumeration via timing
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

    # ── Verify password ───────────────────────────────────────────────────────
    verified = False
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        # bcrypt hash
        verified = _verify_password_bcrypt(password, stored_hash)
    else:
        # Legacy SHA-256 — verify then upgrade to bcrypt
        legacy_hash = _hash_password_legacy(password, salt)
        if secrets.compare_digest(legacy_hash, stored_hash):
            verified = True
            # Upgrade to bcrypt in-place
            new_hash = _hash_password_bcrypt(password)
            execute(conn,
                "UPDATE users SET password_hash=?, salt='bcrypt' WHERE id=?",
                (new_hash, user["id"])
            )
            conn.commit()

    if not verified:
        conn.close()
        _record_login_attempt(email, False)
        return None

    # ── Success ───────────────────────────────────────────────────────────────
    if USE_POSTGRES:
        execute(conn,
            "UPDATE users SET last_login = to_char(now(), 'YYYY-MM-DD HH24:MI:SS') WHERE id = %s",
            (user["id"],)
        )
    else:
        execute(conn,
            "UPDATE users SET last_login = datetime('now') WHERE id = ?",
            (user["id"],)
        )
    conn.commit()
    conn.close()
    _record_login_attempt(email, True)
    # Strip sensitive fields before returning
    user.pop("password_hash", None)
    user.pop("salt", None)
    return user


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by ID."""
    conn = get_conn()
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
    """Fetch a user by email."""
    email = email.strip().lower()
    conn = get_conn()
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
    """Update a user's subscription details after a Stripe event."""
    conn = get_conn()
    execute(conn,
        """UPDATE users SET plan=?, stripe_customer_id=?, stripe_subscription_id=?,
           subscription_status=? WHERE id=?""",
        (plan, stripe_customer_id, stripe_subscription_id, subscription_status, user_id)
    )
    conn.commit()
    conn.close()


# ── Owner / dev accounts — always Pro regardless of subscription ──────────────
_OWNER_EMAILS = {
    "darrianbelcher@gmail.com",   # primary dev account
}

def is_pro_user(user: dict) -> bool:
    """Return True if the user has an active Pro subscription."""
    if not user:
        return False
    email = user.get("email", "").strip().lower()
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


def add_to_waitlist(email: str, name: str = "", source: str = "") -> bool:
    """Add an email to the waitlist. Returns True on success, False if already exists."""
    email = email.strip().lower()
    conn = get_conn()
    try:
        execute(conn,
            "INSERT INTO waitlist (email, name, source) VALUES (?, ?, ?)",
            (email, name.strip(), source.strip())
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_waitlist_count() -> int:
    """Return total waitlist signups."""
    conn = get_conn()
    c = execute(conn, "SELECT COUNT(*) FROM waitlist")
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
def seed_budget(month: str):
    conn = get_conn()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("SELECT COUNT(*) FROM expenses WHERE month = %s", (month,))
    else:
        c.execute("SELECT COUNT(*) FROM expenses WHERE month = ?", (month,))

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
                "INSERT INTO expenses (month, category, subcategory, projected, actual) VALUES (%s, %s, %s, %s, 0)",
                (month, cat, sub, proj)
            )
    else:
        c.executemany(
            "INSERT INTO expenses (month, category, subcategory, projected, actual) VALUES (?, ?, ?, ?, 0)",
            [(month, cat, sub, proj) for cat, sub, proj in categories]
        )

    conn.commit()
    conn.close()


def seed_income(month: str):
    conn = get_conn()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("SELECT COUNT(*) FROM income WHERE month = %s", (month,))
    else:
        c.execute("SELECT COUNT(*) FROM income WHERE month = ?", (month,))

    if c.fetchone()[0] > 0:
        conn.close()
        return

    rows = [
        (month, "Salary — Paycheck 1 (Post-Tax)", 0, "Bi-weekly take-home"),
        (month, "Salary — Paycheck 2 (Post-Tax)", 0, "Bi-weekly take-home"),
        (month, "Business Income", 0, "Side hustle / resale / freelance"),
    ]

    if USE_POSTGRES:
        for row in rows:
            c.execute(
                "INSERT INTO income (month, source, amount, notes) VALUES (%s, %s, %s, %s)",
                row
            )
    else:
        c.executemany(
            "INSERT INTO income (month, source, amount, notes) VALUES (?, ?, ?, ?)",
            rows
        )

    conn.commit()
    conn.close()
