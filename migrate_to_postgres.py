"""
One-time migration: copies local SQLite data → Railway PostgreSQL.
Run with: python migrate_to_postgres.py

This script:
  1. Creates all tables in PostgreSQL (if not already present)
  2. Migrates every table from the local SQLite budget.db
  3. Handles the is_debit column in bank_transactions
  4. Migrates app_settings (including the saved Anthropic API key)
  5. Migrates investment_context, financial_goals, goal_checklist
"""
import sqlite3
import psycopg2
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'budget.db')

# Use DATABASE_URL from env if available, otherwise fall back to the hardcoded URL
PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:jlYIqFpzBulCfWCxhZKoYrTWtscgAxRg@mainline.proxy.rlwy.net:51582/railway")
# Railway sometimes emits postgres:// — fix it
if PG_URL.startswith("postgres://"):
    PG_URL = PG_URL.replace("postgres://", "postgresql://", 1)

print(f"SQLite source: {SQLITE_PATH}")
print("Connecting to SQLite...")
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

print("Connecting to PostgreSQL...")
pg_conn = psycopg2.connect(PG_URL)
pg = pg_conn.cursor()

# ── Create / ensure all tables exist in PostgreSQL ────────────────────────────
print("Creating tables (if not exist)...")

pg.execute('''CREATE TABLE IF NOT EXISTS income (
    id SERIAL PRIMARY KEY, month TEXT NOT NULL, source TEXT NOT NULL,
    amount REAL NOT NULL, notes TEXT)''')

pg.execute('''CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY, month TEXT NOT NULL, category TEXT NOT NULL,
    subcategory TEXT NOT NULL, projected REAL DEFAULT 0, actual REAL DEFAULT 0, notes TEXT)''')

pg.execute('''CREATE TABLE IF NOT EXISTS sole_archive (
    id SERIAL PRIMARY KEY, date TEXT NOT NULL, item TEXT NOT NULL, size TEXT,
    buy_price REAL NOT NULL, sell_price REAL DEFAULT 0, platform TEXT,
    fees REAL DEFAULT 0, shipping REAL DEFAULT 0, status TEXT DEFAULT 'inventory', notes TEXT)''')

pg.execute('''CREATE TABLE IF NOT EXISTS recurring_templates (
    id SERIAL PRIMARY KEY, category TEXT NOT NULL, subcategory TEXT NOT NULL,
    projected REAL DEFAULT 0, active INTEGER DEFAULT 1)''')

pg.execute('''CREATE TABLE IF NOT EXISTS bank_transactions (
    id SERIAL PRIMARY KEY, month TEXT NOT NULL, date TEXT NOT NULL,
    description TEXT NOT NULL, amount REAL NOT NULL,
    is_debit INTEGER DEFAULT 1,
    category TEXT, subcategory TEXT,
    matched_expense_id INTEGER, source TEXT DEFAULT 'manual', notes TEXT)''')

pg.execute('''CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY, month TEXT NOT NULL, date TEXT NOT NULL,
    merchant TEXT NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL,
    receipt_type TEXT DEFAULT 'expense', filename TEXT, image_data BYTEA,
    notes TEXT, created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')))''')

pg.execute('''CREATE TABLE IF NOT EXISTS investment_context (
    id SERIAL PRIMARY KEY,
    bal_401k REAL DEFAULT 0, contrib_401k_ytd REAL DEFAULT 0, match_401k_ytd REAL DEFAULT 0,
    bal_roth REAL DEFAULT 0, contrib_roth_ytd REAL DEFAULT 0,
    bal_hsa REAL DEFAULT 0, contrib_hsa_ytd REAL DEFAULT 0,
    bal_brokerage REAL DEFAULT 0, notes TEXT DEFAULT '',
    updated_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')))''')

pg.execute('''CREATE TABLE IF NOT EXISTS financial_goals (
    id SERIAL PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
    goal_type TEXT DEFAULT 'savings', target_amount REAL DEFAULT 0,
    current_amount REAL DEFAULT 0, target_date TEXT, period TEXT DEFAULT 'yearly',
    category TEXT DEFAULT '', status TEXT DEFAULT 'active', sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')))''')

pg.execute('''CREATE TABLE IF NOT EXISTS goal_checklist (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER REFERENCES financial_goals(id) ON DELETE CASCADE,
    item TEXT NOT NULL, completed INTEGER DEFAULT 0, sort_order INTEGER DEFAULT 0)''')

pg.execute('''CREATE TABLE IF NOT EXISTS users (
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

pg.execute('''CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY, value TEXT)''')

pg_conn.commit()

# ── Ensure is_debit column exists (for existing PG databases) ─────────────────
pg.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='bank_transactions' AND column_name='is_debit'
""")
if not pg.fetchone():
    print("  Adding missing is_debit column to bank_transactions...")
    pg.execute("ALTER TABLE bank_transactions ADD COLUMN is_debit INTEGER DEFAULT 1")
    pg_conn.commit()

# ── Helper: check if a table exists in SQLite ─────────────────────────────────
def sqlite_table_exists(table: str) -> bool:
    row = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None

def sqlite_has_column(table: str, column: str) -> bool:
    rows = sqlite_conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)

# ── Migrate each table ────────────────────────────────────────────────────────
# Format: table_name → tuple of columns to migrate (excluding auto id)
tables = {
    'income': (
        'month', 'source', 'amount', 'notes'
    ),
    'expenses': (
        'month', 'category', 'subcategory', 'projected', 'actual', 'notes'
    ),
    'sole_archive': (
        'date', 'item', 'size', 'buy_price', 'sell_price', 'platform',
        'fees', 'shipping', 'status', 'notes'
    ),
    'recurring_templates': (
        'category', 'subcategory', 'projected', 'active'
    ),
    'receipts': (
        'month', 'date', 'merchant', 'amount', 'category', 'receipt_type',
        'filename', 'image_data', 'notes', 'created_at'
    ),
    'investment_context': (
        'bal_401k', 'contrib_401k_ytd', 'match_401k_ytd',
        'bal_roth', 'contrib_roth_ytd',
        'bal_hsa', 'contrib_hsa_ytd',
        'bal_brokerage', 'notes', 'updated_at'
    ),
    'financial_goals': (
        'title', 'description', 'goal_type', 'target_amount', 'current_amount',
        'target_date', 'period', 'category', 'status', 'sort_order', 'created_at'
    ),
    'goal_checklist': (
        'goal_id', 'item', 'completed', 'sort_order'
    ),
    'users': (
        'email', 'password_hash', 'salt', 'plan', 'stripe_customer_id',
        'stripe_subscription_id', 'subscription_status', 'created_at', 'last_login'
    ),
    'app_settings': (
        'key', 'value'
    ),
}

# bank_transactions needs special handling for is_debit
def migrate_bank_transactions():
    if not sqlite_table_exists('bank_transactions'):
        print("  bank_transactions: table not found in SQLite (skipping)")
        return

    has_is_debit = sqlite_has_column('bank_transactions', 'is_debit')
    if has_is_debit:
        cols = ('month', 'date', 'description', 'amount', 'is_debit',
                'category', 'subcategory', 'matched_expense_id', 'source', 'notes')
    else:
        cols = ('month', 'date', 'description', 'amount',
                'category', 'subcategory', 'matched_expense_id', 'source', 'notes')

    rows = sqlite_conn.execute(f"SELECT {', '.join(cols)} FROM bank_transactions").fetchall()
    if not rows:
        print("  bank_transactions: 0 rows (skipping)")
        return

    pg.execute("DELETE FROM bank_transactions")
    for row in rows:
        row_dict = dict(zip(cols, tuple(row)))
        # Default is_debit=1 if column didn't exist in SQLite
        if 'is_debit' not in row_dict:
            row_dict['is_debit'] = 1
        insert_cols = ('month', 'date', 'description', 'amount', 'is_debit',
                       'category', 'subcategory', 'matched_expense_id', 'source', 'notes')
        vals = tuple(row_dict.get(c) for c in insert_cols)
        placeholders = ', '.join(['%s'] * len(insert_cols))
        pg.execute(
            f"INSERT INTO bank_transactions ({', '.join(insert_cols)}) VALUES ({placeholders})",
            vals
        )
    pg_conn.commit()
    print(f"  bank_transactions: {len(rows)} rows migrated ✅")

for table, cols in tables.items():
    if not sqlite_table_exists(table):
        print(f"  {table}: table not found in SQLite (skipping)")
        continue

    # Only select columns that actually exist in the SQLite table
    existing_cols = [c for c in cols if sqlite_has_column(table, c)]
    if not existing_cols:
        print(f"  {table}: no matching columns found (skipping)")
        continue

    rows = sqlite_conn.execute(f"SELECT {', '.join(existing_cols)} FROM {table}").fetchall()
    if not rows:
        print(f"  {table}: 0 rows (skipping)")
        continue

    placeholders = ', '.join(['%s'] * len(existing_cols))
    col_str = ', '.join(existing_cols)

    # app_settings uses upsert to avoid duplicate key errors
    if table == 'app_settings':
        for row in rows:
            pg.execute(
                f"INSERT INTO app_settings ({col_str}) VALUES ({placeholders}) "
                f"ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                tuple(row)
            )
    else:
        pg.execute(f"DELETE FROM {table}")
        for row in rows:
            pg.execute(f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})", tuple(row))

    pg_conn.commit()
    print(f"  {table}: {len(rows)} rows migrated ✅")

migrate_bank_transactions()

# ── Reset sequences so new inserts don't collide with migrated IDs ────────────
print("\nResetting PostgreSQL sequences...")
seq_tables = [
    'income', 'expenses', 'sole_archive', 'recurring_templates',
    'bank_transactions', 'receipts', 'investment_context',
    'financial_goals', 'goal_checklist'
]
for table in seq_tables:
    try:
        pg.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}")
        pg_conn.commit()
        print(f"  {table}: sequence reset ✅")
    except Exception as e:
        pg_conn.rollback()
        print(f"  {table}: sequence reset skipped ({e})")

sqlite_conn.close()
pg_conn.close()
print("\n✅ Migration complete! Your Railway PostgreSQL now has all your local data.")
print("\nNext steps:")
print("  1. Make sure ANTHROPIC_API_KEY is set in Railway environment variables")
print("  2. Make sure DATABASE_URL is set in Railway environment variables")
print("  3. Optionally set APP_PASSWORD in Railway environment variables")
