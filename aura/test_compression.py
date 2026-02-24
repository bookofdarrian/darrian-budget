"""Quick standalone test of the AURA compression engine (no server needed)."""
import sys
sys.path.insert(0, '.')

# Import the compression functions directly from server.py
from server import compress, _estimate_tokens

SAMPLE = """Budget data for February 2026:
  Total Income: $5,000.00
  Total Projected Expenses: $4,200.00
  Total Actual Expenses: $3,850.00
  Savings: $1,150.00
  Savings Rate: 23.0%

Expense breakdown (Category | Subcategory | Projected | Actual | Difference):
  Housing | Mortgage / Rent | $1,500.00 | $1,500.00 | under by $0.00
  Housing | Phone | $80.00 | $85.00 | OVER by $5.00
  Food | Groceries | $400.00 | $380.00 | under by $20.00
  Food | Dining Out | $200.00 | $310.00 | OVER by $110.00
  Transportation | Fuel | $150.00 | $142.00 | under by $8.00
  Entertainment | Subscriptions | $50.00 | $50.00 | under by $0.00

Individual transactions this month (description | amount):
  CHEVRON #1234 | $45.00
  PUBLIX SUPER MARKETS | $127.50
  CHICK-FIL-A | $23.40
  NETFLIX | $15.49
  SPOTIFY | $9.99

Investment & Retirement Accounts (Fidelity / external):
  Total Investment Portfolio Value: $42,500.00
  401(k) Balance: $28,000.00
    -> YTD Employee Contributions: $2,350.00 (2025 limit: $23,500)
    -> YTD Employer Match Received: $940.00
  Roth IRA Balance: $12,000.00
    -> YTD Contributions: $1,500.00 (2025 limit: $7,000 -- $5,500.00 remaining)
  HSA Balance: $2,500.00
    -> YTD Contributions: $500.00 (2025 individual limit: $4,300 -- $3,800.00 remaining)"""

print("=" * 60)
print("AURA COMPRESSION ENGINE TEST")
print("=" * 60)
print(f"\nOriginal text: {len(SAMPLE)} chars, ~{_estimate_tokens(SAMPLE)} tokens")
print()

for mode in ["toon", "c-ipa", "uccs", "auto"]:
    result = compress(SAMPLE, mode=mode)
    savings = (1 - result["compression_ratio"]) * 100
    print(f"Mode: {result['mode_used']:8s} | "
          f"{result['original_tokens']:4d} → {result['compressed_tokens']:4d} tokens | "
          f"{savings:5.1f}% saved | "
          f"{result['processing_ms']:.1f}ms")

print()
print("--- UCCS compressed output ---")
uccs = compress(SAMPLE, mode="uccs")
print(uccs["compressed"])
print()
print("--- C-IPA compressed output ---")
cipa = compress(SAMPLE, mode="c-ipa")
print(cipa["compressed"])
