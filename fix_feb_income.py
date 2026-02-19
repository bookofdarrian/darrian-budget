"""
One-time fix: Add missing second paycheck to February 2026 income
and rename the existing single paycheck entry to "Paycheck 1".
Run with: railway run python fix_feb_income.py
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
else:
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'budget.db')
    conn = sqlite3.connect(DB_PATH)

c = conn.cursor()
MONTH = "2026-02"

# Show current state
if USE_POSTGRES:
    c.execute("SELECT id, source, amount, notes FROM income WHERE month = %s ORDER BY id", (MONTH,))
else:
    c.execute("SELECT id, source, amount, notes FROM income WHERE month = ? ORDER BY id", (MONTH,))

rows = c.fetchall()
print(f"\nCurrent income rows for {MONTH}:")
for r in rows:
    print(f"  id={r[0]}, source='{r[1]}', amount={r[2]}")

# Find the single "Visa Salary" entry and rename it to Paycheck 1
visa_rows = [r for r in rows if "Visa Salary" in r[1] and "Paycheck 2" not in r[1]]
paycheck2_exists = any("Paycheck 2" in r[1] for r in rows)

if visa_rows and not paycheck2_exists:
    old_id = visa_rows[0][0]
    # Rename existing entry to Paycheck 1
    if USE_POSTGRES:
        c.execute(
            "UPDATE income SET source = %s, notes = %s WHERE id = %s",
            ("Visa Salary — Paycheck 1 (Post-Tax)", "Bi-weekly take-home", old_id)
        )
        # Insert Paycheck 2
        c.execute(
            "INSERT INTO income (month, source, amount, notes) VALUES (%s, %s, %s, %s)",
            (MONTH, "Visa Salary — Paycheck 2 (Post-Tax)", 2142, "Bi-weekly take-home")
        )
    else:
        c.execute(
            "UPDATE income SET source = ?, notes = ? WHERE id = ?",
            ("Visa Salary — Paycheck 1 (Post-Tax)", "Bi-weekly take-home", old_id)
        )
        c.execute(
            "INSERT INTO income (month, source, amount, notes) VALUES (?, ?, ?, ?)",
            (MONTH, "Visa Salary — Paycheck 2 (Post-Tax)", 2142, "Bi-weekly take-home")
        )
    conn.commit()
    print(f"\n✅ Fixed! Renamed id={old_id} to Paycheck 1 and added Paycheck 2 ($2,142)")
elif paycheck2_exists:
    print("\n✅ Paycheck 2 already exists — no changes needed.")
else:
    print("\n⚠️  No Visa Salary entry found — check income data manually.")

# Show final state
if USE_POSTGRES:
    c.execute("SELECT id, source, amount FROM income WHERE month = %s ORDER BY id", (MONTH,))
else:
    c.execute("SELECT id, source, amount FROM income WHERE month = ? ORDER BY id", (MONTH,))

print(f"\nFinal income rows for {MONTH}:")
total = 0
for r in c.fetchall():
    print(f"  id={r[0]}, source='{r[1]}', amount=${r[2]:,.2f}")
    total += r[2]
print(f"\n  TOTAL INCOME: ${total:,.2f}")

conn.close()
