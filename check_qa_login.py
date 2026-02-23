import bcrypt

pw = b'AamirAmunRa2026!!!'

hashes = {
    'budget.db   | id=1 | dbelcher003@gmail.com':     b'$2b$12$QjLIhy2y9mSQRdyzP9Yfa.70Q8lY19zL0ff9cMcXsPmIvLLGj0n.K',
    'budget.db   | id=2 | darrianebelcher@gmail.com': b'$2b$12$wQOEnz0Q37Ihk0gyU7dWJOn7AQhUJKbI/UMeDNhhUaUQqiig6bdhO',
    'budget_qa.db| id=1 | dbelcher003@gmail.com':     b'$2b$12$OP6KdtcHnWmFkX1LHtx0zui1tLzhOLXhhjqbZQl99CT8bgh.4ZIem',
}

print("=== Password check: 'AamirAmunRa2026!!!' ===")
for label, h in hashes.items():
    try:
        result = bcrypt.checkpw(pw, h)
        status = "✅ MATCH" if result else "❌ NO MATCH"
    except Exception as e:
        status = f"ERROR: {e}"
    print(f"  {status}  |  {label}")
