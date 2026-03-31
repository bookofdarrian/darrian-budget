"""
seed_march2026_upgrades.py
──────────────────────────
Seeds Darrian's March/April 2026 life upgrades into the budget DB:

  1. MacBook M5 Pro 16" — one-time Tech expense (March 2026)
  2. iPhone Dual SIM + 5G Hotspot Line — new recurring phone bill
  3. New Home Internet — new recurring housing bill
  4. 765 Swamp Creek Dr — new property (closing April 30, 2026)

Run from the project root:
    source venv/bin/activate
    python3 seed_march2026_upgrades.py
"""

import sqlite3
import hashlib
import os
import sys

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
AUTH_DB    = os.path.join(BASE_DIR, "data", "budget.db")
USERS_DIR  = os.path.join(BASE_DIR, "data", "users")

MONTH      = "2026-03"          # expense month for one-time purchase
CLOSE_DATE = "2026-04-30"       # 765 Swamp Creek Dr closing date

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_user_db(email: str) -> str:
    user_hash = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:24]
    return os.path.join(USERS_DIR, f"user_{user_hash}.db")


def conn_for(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def get_first_user(auth_path: str):
    """Return the first owner-level user from budget.db."""
    c = conn_for(auth_path)
    row = c.execute(
        "SELECT id, email FROM users ORDER BY id LIMIT 1"
    ).fetchone()
    c.close()
    return (row["id"], row["email"]) if row else (1, None)


# ── Main seeding logic ────────────────────────────────────────────────────────

def seed(user_db: str, user_id: int):
    c = conn_for(user_db)

    # ── Ensure recurring_templates has due_day column (migration safety) ──────
    cols = [r[1] for r in c.execute("PRAGMA table_info(recurring_templates)").fetchall()]
    if "due_day" not in cols:
        c.execute("ALTER TABLE recurring_templates ADD COLUMN due_day INTEGER DEFAULT NULL")
        print("  ✅ Migrated recurring_templates: added due_day column")

    if "user_id" not in cols:
        c.execute("ALTER TABLE recurring_templates ADD COLUMN user_id INTEGER DEFAULT NULL")

    # ── Ensure properties table exists (from 74_home_equity_dashboard.py) ────
    c.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            zillow_id TEXT,
            purchase_price REAL,
            purchase_date TEXT,
            property_type TEXT DEFAULT 'Single Family',
            bedrooms INTEGER,
            bathrooms REAL,
            sqft INTEGER,
            lot_size INTEGER,
            year_built INTEGER,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================================================================
    # 1. MacBook M5 Pro 16" — one-time expense March 2026
    # =========================================================================
    # Check if already seeded
    existing = c.execute(
        "SELECT id FROM expenses WHERE month=? AND subcategory=? AND user_id=?",
        (MONTH, "MacBook M5 Pro 16\"", user_id)
    ).fetchone()

    if existing:
        print("  ⚠️  MacBook expense already exists — skipping")
    else:
        c.execute(
            """INSERT INTO expenses
               (month, category, subcategory, projected, actual, notes, user_id)
               VALUES (?,?,?,?,?,?,?)""",
            (MONTH, "Tech / Equipment", 'MacBook M5 Pro 16"',
             2499.00,   # projected — update to actual purchase price in the app
             2499.00,   # actual    — update to actual purchase price in the app
             "New M5 MacBook Pro 16\" — primary dev machine (March 2026). UPDATE ACTUAL PRICE.",
             user_id)
        )
        print('  ✅ Added expense: MacBook M5 Pro 16" — $2,499.00 (update price to actual)')

    # =========================================================================
    # 2. iPhone Dual SIM + 5G Hotspot Line — recurring bill
    # =========================================================================
    existing_rt = c.execute(
        "SELECT id FROM recurring_templates WHERE subcategory=? AND user_id=?",
        ("iPhone — Dual SIM + 5G Hotspot", user_id)
    ).fetchone()

    if existing_rt:
        print("  ⚠️  iPhone line recurring template already exists — skipping")
    else:
        c.execute(
            """INSERT INTO recurring_templates
               (category, subcategory, projected, active, due_day, user_id)
               VALUES (?,?,?,1,?,?)""",
            ("Housing", "iPhone — Dual SIM + 5G Hotspot",
             85.00,   # placeholder — update to actual monthly cost in the app
             1,       # due_day = 1st of month (update if different)
             user_id)
        )
        print("  ✅ Added recurring template: iPhone — Dual SIM + 5G Hotspot — $85.00/mo (update price)")

    # Also add to March 2026 expenses (first month)
    existing_exp = c.execute(
        "SELECT id FROM expenses WHERE month=? AND subcategory=? AND user_id=?",
        (MONTH, "iPhone — Dual SIM + 5G Hotspot", user_id)
    ).fetchone()

    if not existing_exp:
        c.execute(
            """INSERT INTO expenses
               (month, category, subcategory, projected, actual, notes, user_id)
               VALUES (?,?,?,?,?,?,?)""",
            (MONTH, "Housing", "iPhone — Dual SIM + 5G Hotspot",
             85.00, 85.00,
             "New line — dual SIM + 5G hotspot (replaces Pixel). UPDATE ACTUAL COST.",
             user_id)
        )
        print("  ✅ Added March 2026 expense: iPhone — Dual SIM + 5G Hotspot")

    # =========================================================================
    # 3. New Home Internet — recurring bill
    # =========================================================================
    existing_inet = c.execute(
        "SELECT id FROM recurring_templates WHERE subcategory=? AND user_id=?",
        ("Home Internet — 765 Swamp Creek", user_id)
    ).fetchone()

    if existing_inet:
        print("  ⚠️  Home Internet recurring template already exists — skipping")
    else:
        c.execute(
            """INSERT INTO recurring_templates
               (category, subcategory, projected, active, due_day, user_id)
               VALUES (?,?,?,1,?,?)""",
            ("Housing", "Home Internet — 765 Swamp Creek",
             80.00,   # placeholder — update to actual monthly cost
             1,       # due_day placeholder
             user_id)
        )
        print("  ✅ Added recurring template: Home Internet — 765 Swamp Creek — $80.00/mo (update price)")

    # Add to April 2026 expenses (first month at new house)
    inet_month = "2026-04"
    existing_inet_exp = c.execute(
        "SELECT id FROM expenses WHERE month=? AND subcategory=? AND user_id=?",
        (inet_month, "Home Internet — 765 Swamp Creek", user_id)
    ).fetchone()

    if not existing_inet_exp:
        c.execute(
            """INSERT INTO expenses
               (month, category, subcategory, projected, actual, notes, user_id)
               VALUES (?,?,?,?,?,?,?)""",
            (inet_month, "Housing", "Home Internet — 765 Swamp Creek",
             80.00, 0.00,
             "New home internet at 765 Swamp Creek Dr. First bill May (closing Apr 30). UPDATE PRICE.",
             user_id)
        )
        print("  ✅ Added April 2026 expense: Home Internet — 765 Swamp Creek")

    # =========================================================================
    # 4. 765 Swamp Creek Dr — new property (closing April 30, 2026)
    # =========================================================================
    existing_prop = c.execute(
        "SELECT id FROM properties WHERE address LIKE ? AND user_id=?",
        ("%Swamp Creek%", user_id)
    ).fetchone()

    if existing_prop:
        print("  ⚠️  765 Swamp Creek Dr property already exists — skipping")
    else:
        c.execute(
            """INSERT INTO properties
               (user_id, address, city, state, zip_code,
                purchase_price, purchase_date, property_type, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                user_id,
                "765 Swamp Creek Dr",
                "",           # update city in Home Equity Dashboard
                "GA",         # assumed Georgia — update if different
                "",           # update zip code in Home Equity Dashboard
                0.00,         # UPDATE with actual purchase price in Home Equity Dashboard
                CLOSE_DATE,   # closing date April 30, 2026
                "Single Family",
                "🏠 NEW HOME — Closing April 30, 2026. Inspected & under contract. "
                "UPDATE: purchase price, city, zip, bedrooms, bathrooms, sqft in Home Equity Dashboard."
            )
        )
        print("  ✅ Added property: 765 Swamp Creek Dr (closing April 30, 2026)")
        print("     ⚡ Go to Home Equity Dashboard to add your mortgage details!")

    # ── Also add mortgage/housing expense to April 2026 ──────────────────────
    mortgage_month = "2026-04"
    existing_mtg = c.execute(
        "SELECT id FROM expenses WHERE month=? AND subcategory LIKE ? AND user_id=?",
        (mortgage_month, "%Swamp Creek%", user_id)
    ).fetchone()

    if not existing_mtg:
        c.execute(
            """INSERT INTO expenses
               (month, category, subcategory, projected, actual, notes, user_id)
               VALUES (?,?,?,?,?,?,?)""",
            (mortgage_month, "Housing", "Mortgage — 765 Swamp Creek Dr",
             0.00, 0.00,
             "First mortgage payment — 765 Swamp Creek Dr. Closing April 30, 2026. UPDATE AMOUNT.",
             user_id)
        )
        print("  ✅ Added April 2026 mortgage expense placeholder: 765 Swamp Creek Dr")

    c.commit()
    c.close()


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🍑 Peach State Savings — March/April 2026 Life Upgrade Seed Script")
    print("=" * 65)

    if not os.path.exists(AUTH_DB):
        print(f"❌ Auth DB not found: {AUTH_DB}")
        sys.exit(1)

    # ── Target the Pro owner account (darrianebelcher@gmail.com, ID=2) ────────
    OWNER_EMAIL = "darrianebelcher@gmail.com"
    OWNER_ID    = 2

    user_db = get_user_db(OWNER_EMAIL)
    print(f"  👤 User: {OWNER_EMAIL} (ID: {OWNER_ID})")

    if not os.path.exists(user_db):
        print(f"  ⚠️  Per-user DB not found: {user_db}")
        print(f"  ↩️  Falling back to shared budget.db")
        user_db = AUTH_DB

    print(f"  💾 Target DB: {user_db}")
    print()

    seed(user_db, OWNER_ID)

    print()
    print("=" * 65)
    print("✅ Done! Here's what to update in the app UI:")
    print()
    print('  📱 MacBook M5 Pro 16"')
    print("     → Expenses > March 2026 > Tech / Equipment")
    print("     → Update projected & actual to your real purchase price")
    print()
    print("  📱 iPhone — Dual SIM + 5G Hotspot")
    print("     → Bills > Manage Recurring > update monthly cost & due date")
    print()
    print("  🌐 Home Internet — 765 Swamp Creek")
    print("     → Bills > Manage Recurring > update monthly cost & due date")
    print()
    print("  🏠 765 Swamp Creek Dr")
    print("     → Home Equity Dashboard > Properties tab > edit property")
    print("     → Add: purchase price, city, zip, beds/baths, sqft")
    print("     → Add Mortgage tab: lender, loan amount, rate, term")
    print()
    print("  🎉 Congrats on the new house! Closing April 30, 2026 🏡")
    print()
