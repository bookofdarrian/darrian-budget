#!/usr/bin/env python3
"""
update_app_passwords.py
Generates cryptographically strong passwords, updates bcrypt hashes in the app DBs,
and saves a secure copy to ~/Documents/PSS_APP_PASSWORDS.txt (outside git repo).

Run: python3 update_app_passwords.py
"""
import secrets
import string
import sqlite3
import os
import bcrypt
from datetime import datetime

# ── Generate strong 24-char passwords ─────────────────────────────────────────
def strong_pw(length=24):
    """Generate a cryptographically secure password guaranteed to have:
    2+ uppercase, 2+ lowercase, 2+ digits, 2+ symbols."""
    lower  = string.ascii_lowercase
    upper  = string.ascii_uppercase
    digits = string.digits
    syms   = "!@%-_=+?."
    pool   = lower + upper + digits + syms
    while True:
        pw = "".join(secrets.choice(pool) for _ in range(length))
        if (sum(1 for c in pw if c in upper)  >= 2 and
            sum(1 for c in pw if c in lower)  >= 2 and
            sum(1 for c in pw if c in digits) >= 2 and
            sum(1 for c in pw if c in syms)   >= 2):
            return pw

def hash_pw(pw):
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

# ── Generate ───────────────────────────────────────────────────────────────────
pw_pro  = strong_pw(24)   # darrianebelcher@gmail.com — MAIN (Pro account)
pw_free = strong_pw(24)   # dbelcher003@gmail.com — secondary

print()
print("Generated passwords:")
print(f"  PRO  darrianebelcher@gmail.com  →  {pw_pro}")
print(f"  FREE dbelcher003@gmail.com      →  {pw_free}")

# ── Hash ───────────────────────────────────────────────────────────────────────
print("\nHashing (bcrypt rounds=12, this takes a few seconds)...")
hash_pro  = hash_pw(pw_pro)
hash_free = hash_pw(pw_free)
print("  Done.")

# ── Update budget.db ───────────────────────────────────────────────────────────
db_prod = "data/budget.db"
if os.path.exists(db_prod):
    conn = sqlite3.connect(db_prod)
    conn.execute("UPDATE users SET password_hash=?, salt='bcrypt' WHERE email=?",
                 (hash_pro, "darrianebelcher@gmail.com"))
    conn.execute("UPDATE users SET password_hash=?, salt='bcrypt' WHERE email=?",
                 (hash_free, "dbelcher003@gmail.com"))
    conn.commit()
    conn.close()
    print(f"  ✅ Updated {db_prod}")

# ── Update budget_qa.db ────────────────────────────────────────────────────────
db_qa = "data/budget_qa.db"
if os.path.exists(db_qa):
    conn = sqlite3.connect(db_qa)
    conn.execute("UPDATE users SET password_hash=?, salt='bcrypt' WHERE email=?",
                 (hash_free, "dbelcher003@gmail.com"))
    conn.commit()
    conn.close()
    print(f"  ✅ Updated {db_qa}")

# ── Save to secure file OUTSIDE git repo ──────────────────────────────────────
ts        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
save_path = os.path.expanduser("~/Documents/PSS_APP_PASSWORDS.txt")

lines = [
    "╔══════════════════════════════════════════════════════════════════╗",
    "║   PEACH STATE SAVINGS — APP LOGIN CREDENTIALS                   ║",
    f"║   Generated: {ts}                             ║",
    "║   KEEP PRIVATE — NOT in git repo — safe to store here           ║",
    "╚══════════════════════════════════════════════════════════════════╝",
    "",
    "━━━ MAIN ACCOUNT (Pro) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "  Works on:  peachstatesavings.com",
    "             getsoleops.com",
    "             collegeconfused.org",
    "  Email:     darrianebelcher@gmail.com",
    f"  Password:  {pw_pro}",
    "  Plan:      PRO (active)",
    "",
    "━━━ SECONDARY ACCOUNT (Free) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "  Email:     dbelcher003@gmail.com",
    f"  Password:  {pw_free}",
    "  Plan:      Free",
    "",
    "━━━ ADD TO iPHONE (iCloud Keychain) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "  iPhone → Settings → Passwords → + (top right)",
    "  Website:   peachstatesavings.com",
    "  Username:  darrianebelcher@gmail.com",
    f"  Password:  {pw_pro}",
    "  Tap Save → it syncs to your Mac automatically",
    "",
    "━━━ STORAGE INFO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    f"  This file: ~/Documents/PSS_APP_PASSWORDS.txt",
    "  Hashing:   bcrypt rounds=12 in data/budget.db",
    "  Git:       data/ is NOT committed — passwords never leave server",
    "",
    f"  Generated: {ts}",
]

with open(save_path, "w") as f:
    f.write("\n".join(lines) + "\n")

os.chmod(save_path, 0o600)  # owner read/write only

print()
print("=" * 60)
print("  ✅ PASSWORDS UPDATED")
print("=" * 60)
print()
print("  ━━━ SCREENSHOT THIS FOR YOUR PHONE ━━━")
print()
print("  MAIN LOGIN (all 3 sites):")
print(f"  Email:    darrianebelcher@gmail.com")
print(f"  Password: {pw_pro}")
print()
print("  Sites:")
print("  → peachstatesavings.com")
print("  → getsoleops.com")
print("  → collegeconfused.org")
print()
print(f"  Saved to: {save_path}")
print("  (chmod 600 — only you can read it)")
print()
print("  To add to iPhone Keychain:")
print("  Settings → Passwords → + → peachstatesavings.com")
print(f"  Username: darrianebelcher@gmail.com")
print(f"  Password: {pw_pro}")
print()
