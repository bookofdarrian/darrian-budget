"""
Check bank transactions - find payroll deposits and month distribution
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

import psycopg2
conn = psycopg2.connect(DATABASE_URL)
c = conn.cursor()

print("=== MONTHS IN BANK TRANSACTIONS ===")
c.execute("SELECT month, COUNT(*), SUM(amount) FROM bank_transactions GROUP BY month ORDER BY month")
for r in c.fetchall():
    print(f"  month={r[0]}, count={r[1]}, total=${r[2]:,.2f}")

print("\n=== ALL VISA PAYROLL DEPOSITS (any month) ===")
c.execute("""
    SELECT id, month, date, description, amount, is_debit
    FROM bank_transactions
    WHERE LOWER(description) LIKE '%visa%' OR LOWER(description) LIKE '%payroll%' OR LOWER(description) LIKE '%deposit%'
    ORDER BY date
""")
for r in c.fetchall():
    label = "CREDIT" if r[5] == 0 else "DEBIT"
    print(f"  [{label}] month={r[1]}, date={r[2]}, desc='{r[3]}', amount=${r[4]:,.2f}")

print("\n=== FEBRUARY 2026 TRANSACTIONS (by date field) ===")
c.execute("""
    SELECT id, month, date, description, amount, is_debit
    FROM bank_transactions
    WHERE date LIKE '2026-02%'
    ORDER BY date
    LIMIT 30
""")
rows = c.fetchall()
for r in rows:
    label = "CREDIT" if r[5] == 0 else "DEBIT"
    print(f"  [{label}] month={r[1]}, date={r[2]}, desc='{r[3][:50]}', amount=${r[4]:,.2f}")
print(f"  Total rows with date in 2026-02: {len(rows)}")

conn.close()
