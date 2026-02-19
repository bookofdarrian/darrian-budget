import os
import sqlite3

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
            status TEXT DEFAULT \'inventory\',
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
            source TEXT DEFAULT \'manual\',
            notes TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            month TEXT NOT NULL,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            receipt_type TEXT DEFAULT \'expense\',
            filename TEXT,
            image_data BYTEA,
            notes TEXT,
            created_at TEXT DEFAULT (to_char(now(), \'YYYY-MM-DD HH24:MI:SS\'))
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
            notes TEXT DEFAULT \'\',
            updated_at TEXT DEFAULT (to_char(now(), \'YYYY-MM-DD HH24:MI:SS\'))
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS financial_goals (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT \'\',
            goal_type TEXT DEFAULT \'savings\',
            target_amount REAL DEFAULT 0,
            current_amount REAL DEFAULT 0,
            target_date TEXT,
            period TEXT DEFAULT \'yearly\',
            category TEXT DEFAULT \'\',
            status TEXT DEFAULT \'active\',
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (to_char(now(), \'YYYY-MM-DD HH24:MI:SS\'))
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
    else:
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

    # ── Migrations: add columns to existing tables if missing ────────────────
    if USE_POSTGRES:
        # Check if is_debit column exists in bank_transactions
        c.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='bank_transactions' AND column_name='is_debit'
        """)
        if not c.fetchone():
            c.execute("ALTER TABLE bank_transactions ADD COLUMN is_debit INTEGER DEFAULT 1")
    else:
        # SQLite: check PRAGMA table_info
        c.execute("PRAGMA table_info(bank_transactions)")
        cols = [row[1] for row in c.fetchall()]
        if 'is_debit' not in cols:
            c.execute("ALTER TABLE bank_transactions ADD COLUMN is_debit INTEGER DEFAULT 1")

    conn.commit()
    conn.close()


# ── App settings helpers (key/value store) ───────────────────────────────────
def _ensure_settings_table(conn):
    if USE_POSTGRES:
        conn.cursor().execute('''CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
    else:
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
        # psycopg2 returns a tuple; use cursor description for keys
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

    categories = [
        ("Housing", "Mortgage / Rent", 2645),
        ("Housing", "Phone", 50),
        ("Housing", "Electricity", 120),
        ("Housing", "Gas", 60),
        ("Housing", "Water and Sewer", 30),
        ("Housing", "Cable / WiFi", 75),
        ("Housing", "Waste Removal", 25),
        ("Housing", "Maintenance / Repairs", 23),
        ("Housing", "Supplies", 0),
        ("Transportation", "Vehicle Payment", 0),
        ("Transportation", "Insurance", 100),
        ("Transportation", "Fuel", 80),
        ("Transportation", "Maintenance", 75),
        ("Insurance", "Renters", 100),
        ("Insurance", "Health", 0),
        ("Insurance", "Pet", 25),
        ("Food", "Groceries", 400),
        ("Food", "Dining Out", 200),
        ("Pets", "Food", 50),
        ("Pets", "Medical", 50),
        ("Pets", "Grooming", 0),
        ("Personal Care", "Medical", 50),
        ("Personal Care", "Hair / Nails", 140),
        ("Entertainment", "Night Out", 200),
        ("Entertainment", "Music Platforms", 0),
        ("Entertainment", "Movies", 112),
        ("Entertainment", "Subscriptions", 75),
        ("Loans", "Credit Card", 100),
        ("Savings / Investments", "Roth IRA", 300),
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
        (month, "Visa Salary — Paycheck 1 (Post-Tax)", 2142, "Bi-weekly take-home"),
        (month, "Visa Salary — Paycheck 2 (Post-Tax)", 2142, "Bi-weekly take-home"),
        (month, "404 Sole Archive", 0, "Update from resale tracker"),
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
