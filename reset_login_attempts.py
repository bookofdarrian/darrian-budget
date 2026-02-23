import sqlite3, os

dbs = [
    ("budget.db",    "data/budget.db"),
    ("budget_qa.db", "data/budget_qa.db"),
]

for db_name, db_path in dbs:
    if not os.path.exists(db_path):
        print(f"{db_name}: NOT FOUND — skipping")
        continue
    conn = sqlite3.connect(db_path)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "login_attempts" in tables:
        before = conn.execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0]
        conn.execute("DELETE FROM login_attempts")
        conn.commit()
        print(f"{db_name}: cleared {before} login_attempt row(s) ✅")
    else:
        print(f"{db_name}: no login_attempts table — nothing to clear")
    conn.close()

print("\nDone. All login attempt records wiped — no accounts are locked.")
