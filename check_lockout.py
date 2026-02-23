import sqlite3, time, os

now = time.time()
WINDOW = 15 * 60   # 15 min
MAX_ATTEMPTS = 10

for db_name, db_path in [
    ("budget.db",    "data/budget.db"),
    ("budget_qa.db", "data/budget_qa.db"),
]:
    if not os.path.exists(db_path):
        print(f"{db_name}: NOT FOUND")
        continue

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Check if login_attempts table exists
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "login_attempts" not in tables:
        print(f"{db_name}: no login_attempts table")
        conn.close()
        continue

    rows = conn.execute(
        "SELECT email, success, attempted_at FROM login_attempts ORDER BY attempted_at DESC LIMIT 30"
    ).fetchall()

    print(f"\n=== {db_name} — login_attempts (last 30) ===")
    if not rows:
        print("  (empty)")
    for r in rows:
        age_s = now - r["attempted_at"]
        age_str = f"{age_s/60:.1f} min ago"
        status = "SUCCESS" if r["success"] else "FAIL"
        print(f"  {status:7s}  {r['email']}  {age_str}")

    # Lockout check for dbelcher003@gmail.com
    email = "dbelcher003@gmail.com"
    cutoff = now - WINDOW
    fails = conn.execute(
        "SELECT attempted_at FROM login_attempts WHERE email=? AND success=0 AND attempted_at>? ORDER BY attempted_at DESC",
        (email, cutoff)
    ).fetchall()
    print(f"\n  Lockout check for {email}:")
    print(f"    Failures in last 15 min: {len(fails)} / {MAX_ATTEMPTS}")
    if len(fails) >= MAX_ATTEMPTS:
        most_recent = fails[0]["attempted_at"]
        remaining = int(900 - (now - most_recent))
        print(f"    *** LOCKED OUT — {max(remaining,0)//60}m {max(remaining,0)%60}s remaining ***")
    else:
        print(f"    Not locked out")

    conn.close()
