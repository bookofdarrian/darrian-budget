"""
One-time migration: copies local SQLite data → Railway PostgreSQL.
Run with: python migrate_to_postgres.py
"""
import sqlite3
import psycopg2
import os

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'budget.db')
PG_URL = "postgresql://postgres:jlYIqFpzBulCfWCxhZKoYrTWtscgAxRg@mainline.proxy.rlwy.net:51582/railway"

print("Connecting to SQLite...")
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

print("Connecting to PostgreSQL...")
pg_conn = psycopg2.connect(PG_URL)
pg = pg_conn.cursor()

# ── Create tables in PostgreSQL ───────────────────────────────────────────────
print("Creating tables...")
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
    description TEXT NOT NULL, amount REAL NOT NULL, category TEXT, subcategory TEXT,
    matched_expense_id INTEGER, source TEXT DEFAULT 'manual', notes TEXT)''')

pg.execute('''CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY, month TEXT NOT NULL, date TEXT NOT NULL,
    merchant TEXT NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL,
    receipt_type TEXT DEFAULT 'expense', filename TEXT, image_data BYTEA,
    notes TEXT, created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')))''')

pg_conn.commit()

# ── Migrate each table ────────────────────────────────────────────────────────
tables = {
    'income':               ('month', 'source', 'amount', 'notes'),
    'expenses':             ('month', 'category', 'subcategory', 'projected', 'actual', 'notes'),
    'sole_archive':         ('date', 'item', 'size', 'buy_price', 'sell_price', 'platform', 'fees', 'shipping', 'status', 'notes'),
    'recurring_templates':  ('category', 'subcategory', 'projected', 'active'),
    'bank_transactions':    ('month', 'date', 'description', 'amount', 'category', 'subcategory', 'matched_expense_id', 'source', 'notes'),
    'receipts':             ('month', 'date', 'merchant', 'amount', 'category', 'receipt_type', 'filename', 'image_data', 'notes', 'created_at'),
}

for table, cols in tables.items():
    rows = sqlite_conn.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
    if not rows:
        print(f"  {table}: 0 rows (skipping)")
        continue
    placeholders = ', '.join(['%s'] * len(cols))
    col_str = ', '.join(cols)
    # Clear existing data first to avoid duplicates on re-run
    pg.execute(f"DELETE FROM {table}")
    for row in rows:
        pg.execute(f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})", tuple(row))
    pg_conn.commit()
    print(f"  {table}: {len(rows)} rows migrated ✅")

sqlite_conn.close()
pg_conn.close()
print("\n✅ Migration complete! Your Railway PostgreSQL now has all your local data.")
