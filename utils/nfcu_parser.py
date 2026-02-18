"""
Navy Federal Credit Union PDF Statement Parser
Extracts transactions from NFCU statement PDFs.
"""
import re
import io
import pdfplumber


# Matches lines like:
#   10-27 POS Debit- Debit Card 3453 10-26-25 Chevron 0306168 Atlanta GA   2.79-   3,009.19
#   10-30 Deposit - ACH Paid From Visa Technology Payroll 01Afd9   2,041.90   4,808.72
#   11-04 Paid To - The Vivian 4980 Rent Chk 12400005   1,710.32-   2,574.88
TXN_RE = re.compile(
    r'^(\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2}-?)\s+([\d,]+\.\d{2})$'
)

SKIP_KEYWORDS = [
    'beginning balance', 'ending balance', 'dividend', 'atm rebate',
    'items paid', 'average daily balance', 'your account earned',
    'no transactions', 'continued from', 'joint owner',
]

# Lines that are credits (deposits) — keep them but mark as non-expense
CREDIT_KEYWORDS = [
    'deposit', 'paid from', 'credit adjustment', 'atm rebate', 'dividend',
]


def _parse_amount(raw: str):
    """Return (float_amount, is_debit)."""
    is_debit = raw.endswith('-')
    return float(raw.rstrip('-').replace(',', '')), is_debit


def _clean_description(desc: str) -> str:
    """Strip card/date noise from NFCU transaction descriptions."""
    # Remove "POS Debit- Debit Card XXXX [Transaction] MM-DD-YY " prefix (handles broken spacing)
    desc = re.sub(r'POS\s+Deb\s*it\s*-?\s*Debit\s+C\s*ard\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    desc = re.sub(r'POS\s+Debit\s*-?\s*Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    desc = re.sub(r'PO\s+S\s+Debit\s*-?\s*Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    # Remove "POS Credit Adjustment XXXX Transaction MM-DD-YY " prefix
    desc = re.sub(r'POS\s+Credit\s+Adjustment\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    # Remove leftover "POS Debi t-" or similar broken prefixes
    desc = re.sub(r'^POS\s+Deb\w*\s*t?\s*-?\s*Debit\s+Card\s+\d+\s*\d{2}-\d{2}-\d{2}\s*', '', desc)
    # Normalise whitespace (collapse internal spaces from PDF line-break artifacts)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc


def parse_nfcu_pdf(pdf_file) -> list[dict]:
    """
    Parse a Navy Federal PDF statement.

    Args:
        pdf_file: file-like object (bytes or BytesIO) of the PDF

    Returns:
        List of dicts with keys:
            date        – "YYYY-MM-DD"
            description – cleaned merchant/description string
            amount      – positive float
            is_debit    – True = money out (expense), False = money in (credit)
            account     – account name string
    """
    if isinstance(pdf_file, bytes):
        pdf_file = io.BytesIO(pdf_file)

    transactions = []
    current_year = None
    current_account = None

    with pdfplumber.open(pdf_file) as pdf:
        full_text = "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )

    # ── Detect statement year ────────────────────────────────────────────────
    period_match = re.search(
        r'\d{2}/\d{2}/(\d{2})\s*-\s*\d{2}/\d{2}/(\d{2})', full_text
    )
    if period_match:
        # Use the end-date year (right side of the period)
        current_year = "20" + period_match.group(2)

    # ── Walk lines ───────────────────────────────────────────────────────────
    for line in full_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Detect account section headers
        if re.search(r'Campus Checking', line, re.I):
            current_account = 'Campus Checking'
        elif re.search(r'e-Checking', line, re.I):
            current_account = 'e-Checking'
        elif re.search(r'Membership Savings', line, re.I):
            current_account = 'Membership Savings'

        m = TXN_RE.match(line)
        if not m or not current_year or not current_account:
            continue

        date_str, raw_desc, amt_raw, _bal = m.groups()

        # Skip non-transaction summary lines
        if any(k in raw_desc.lower() for k in SKIP_KEYWORDS):
            continue

        amount, is_debit = _parse_amount(amt_raw)
        desc = _clean_description(raw_desc)

        # Build full date
        month, day = date_str.split('-')
        full_date = f"{current_year}-{month}-{day}"

        transactions.append({
            'date':        full_date,
            'description': desc,
            'amount':      amount,
            'is_debit':    is_debit,
            'account':     current_account,
        })

    return transactions
