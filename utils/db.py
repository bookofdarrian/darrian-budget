import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'budget.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Income sources
    c.execute('''CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        source TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT
    )''')

    # Expenses
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        projected REAL DEFAULT 0,
        actual REAL DEFAULT 0,
        notes TEXT
    )''')

    # 404 Sole Archive transactions
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
        status TEXT DEFAULT 'inventory',  -- inventory, sold
        notes TEXT
    )''')

    # Recurring expense templates
    c.execute('''CREATE TABLE IF NOT EXISTS recurring_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        projected REAL DEFAULT 0,
        active INTEGER DEFAULT 1
    )''')

    # Bank-imported transactions (from CSV or manual entry)
    c.execute('''CREATE TABLE IF NOT EXISTS bank_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        subcategory TEXT,
        matched_expense_id INTEGER,
        source TEXT DEFAULT 'manual',
        notes TEXT
    )''')

    # Receipts (expense receipts + HSA receipts)
    c.execute('''CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,
        date TEXT NOT NULL,
        merchant TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        receipt_type TEXT DEFAULT 'expense',  -- expense, hsa
        filename TEXT,
        image_data BLOB,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    conn.commit()
    conn.close()

def seed_budget(month: str):
    """Seed a month with Darrian's actual budget categories and projected amounts from his spreadsheet."""
    conn = get_conn()
    c = conn.cursor()

    # Check if month already seeded
    c.execute("SELECT COUNT(*) FROM expenses WHERE month = ?", (month,))
    if c.fetchone()[0] > 0:
        conn.close()
        return

    categories = [
        # (category, subcategory, projected)
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

    c.executemany(
        "INSERT INTO expenses (month, category, subcategory, projected, actual) VALUES (?, ?, ?, ?, 0)",
        [(month, cat, sub, proj) for cat, sub, proj in categories]
    )
    conn.commit()
    conn.close()

# Seed income for a month
def seed_income(month: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM income WHERE month = ?", (month,))
    if c.fetchone()[0] > 0:
        conn.close()
        return
    c.executemany(
        "INSERT INTO income (month, source, amount, notes) VALUES (?, ?, ?, ?)",
        [
            (month, "Visa Salary (Post-Tax)", 2142, "Bi-weekly take-home"),
            (month, "404 Sole Archive", 0, "Update from resale tracker"),
        ]
    )
    conn.commit()
    conn.close()
