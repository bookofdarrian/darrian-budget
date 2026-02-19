"""
Navy Federal Credit Union PDF Statement Parser
Handles two statement formats:
  1. Deposit account statements (Checking / Savings)
  2. Visa credit card statements
"""
import re
import io
import pdfplumber


# ── Checking/Savings parser ───────────────────────────────────────────────────
#
# Transaction line formats:
#   Format A (debit, amount- attached):
#     07-24 POS Debit- Debit Card 3453 07-23-25 Amazon Mktpl*s27Iw WA   29.48-   8,159.32
#   Format B (credit, no dash):
#     07-24 Deposit - ACH Paid From Visa Technology Direct Dep   2,194.81   8,198.99
#   Format C (debit, space before dash):
#     07-28 POS Debit - Debit Card 3453 Transaction 07-27-25 7-Eleven NY   3.09 -   6,233.23
#
# Capture groups: (MM-DD) (description) (amount) (dash or empty) (balance)
_DEP_TXN_RE = re.compile(
    r'^(\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s*(-?)\s+([\d,]+\.\d{2})$'
)

_DEP_SKIP = [
    'beginning balance', 'ending balance', 'dividend', 'atm rebate',
    'items paid', 'average daily balance', 'your account earned',
    'no transactions', 'continued from', 'joint owner',
]

_DEP_ACCOUNT_HEADERS = [
    (r'Campus Checking',    'Campus Checking'),
    (r'e-Checking',         'e-Checking'),
    (r'Membership Savings', 'Membership Savings'),
]


def _normalize_dep_line(line: str) -> str:
    """Fix common PDF text-extraction artifacts in deposit statements."""
    line = re.sub(r'(\d{2}-\d{2})\s+-(\d{2})', r'\1-\2', line)       # "12-02 -25" → "12-02-25"
    line = re.sub(r'(\d{3}-\d{3})\s+-(\d{4})', r'\1-\2', line)       # phone numbers
    line = re.sub(r'Deb\s*i\s*t\s*-', 'Debit-', line)
    line = re.sub(r'C\s+ard\b', 'Card', line)
    line = re.sub(r'\b([A-Z])\s+([A-Z])\b', r'\1\2', line)
    return line


def _clean_dep_description(desc: str) -> str:
    """Strip card/date noise from deposit-account transaction descriptions."""
    desc = re.sub(r'\b(\d)\s+(\d)-(\d{2})-(\d{2})\b', r'\1\2-\3-\4', desc)
    desc = re.sub(r'POS\s+Debit\s*-?\s*Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    desc = re.sub(r'POS\s+Credit\s+Adjustment\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    desc = re.sub(r'POS\s+Debit\s+-\s+Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc


def _parse_deposit_statement(full_text: str, year: str, end_month: int = 0) -> list[dict]:
    """Parse a checking/savings deposit account statement.

    year      – the statement end year (e.g. "2025")
    end_month – the statement end month as int (1-12). Used to detect
                year-boundary transactions: if a transaction month is
                greater than end_month, it belongs to year-1 (e.g. a
                December transaction on a January statement).
    """
    transactions = []
    current_account = None
    year_int = int(year)

    for raw_line in full_text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        # Detect account section headers
        for pattern, acct_name in _DEP_ACCOUNT_HEADERS:
            if re.search(pattern, line, re.I):
                current_account = acct_name
                break

        line = _normalize_dep_line(line)
        m = _DEP_TXN_RE.match(line)
        if not m or not current_account:
            continue

        date_str, raw_desc, amt_str, dash, _bal = m.groups()

        if any(k in raw_desc.lower() for k in _DEP_SKIP):
            continue

        amount = float(amt_str.replace(',', ''))
        is_debit = dash == '-'
        desc = _clean_dep_description(raw_desc)
        month_str, day = date_str.split('-')
        txn_month = int(month_str)

        # Year-boundary fix: if the statement ends in month M and this
        # transaction is in month > M, it must be from the prior year.
        # e.g. a January statement (end_month=1) with a txn in month 12
        # → that's December of the previous year.
        if end_month > 0 and txn_month > end_month:
            txn_year = year_int - 1
        else:
            txn_year = year_int

        full_date = f"{txn_year}-{month_str}-{day}"

        transactions.append({
            'date':        full_date,
            'description': desc,
            'amount':      amount,
            'is_debit':    is_debit,
            'account':     current_account,
        })

    return transactions


# ── Credit card parser ────────────────────────────────────────────────────────
#
# The NFCU Visa statement has a tabular layout. pdfplumber extracts it as
# lines that look like one of:
#
#   "01/02/26 01/05/26 24692166002102839952326 TST*TON TON RAMEN & YAKI Atlanta GA $18.22"
#   "01/20/26 01/20/26 99999999999999999999999 NFCU ONLINE CASH ADVANCE VIENNA VA $130.00"
#   "01/06/26 01/06/26 74060956006065270100003 NFO PAYMENT RECEIVED xxxx xxxx xxxx 2045 $300.00"
#
# We match on: MM/DD/YY  MM/DD/YY  <ref>  <description>  <amount>
# Trans date is group 1, description is group 3, amount is group 4.
#
# Payments ("NFO PAYMENT RECEIVED") are credits — we mark is_debit=False.
# Cash advances are debits.
# All other charges are debits.

_CC_TXN_RE = re.compile(
    r'^(\d{2}/\d{2}/\d{2})\s+'          # trans date MM/DD/YY
    r'\d{2}/\d{2}/\d{2}\s+'             # post date (ignored)
    r'\d{10,}\s+'                        # reference number (10+ digits)
    r'(.+?)\s+'                          # description (non-greedy)
    r'\$?([\d,]+\.\d{2})$'              # amount
)

# Lines to skip in CC statements
_CC_SKIP = [
    'total payments', 'total new activity', 'interest charge',
    'total interest', 'balance subject', 'annual percentage',
    'type of balance', 'purchases', 'bal trf', 'cash advances',
    'submitted by', 'trans date', 'description', 'amount',
    'payments and credits', 'transactions',
]

# Payments from checking to credit card — these are transfers, not expenses
_CC_PAYMENT_KEYWORDS = [
    'nfo payment received',
    'payment received',
    'online payment',
]


def _parse_cc_year(date_str: str) -> str:
    """Convert MM/DD/YY to YYYY-MM-DD."""
    parts = date_str.split('/')
    month, day, yr = parts[0], parts[1], parts[2]
    return f"20{yr}-{month}-{day}"


def _parse_credit_card_statement(full_text: str) -> list[dict]:
    """Parse an NFCU Visa credit card statement."""
    transactions = []

    for raw_line in full_text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        # Skip header/summary lines
        if any(k in line.lower() for k in _CC_SKIP):
            continue

        m = _CC_TXN_RE.match(line)
        if not m:
            continue

        trans_date_str, raw_desc, amt_str = m.group(1), m.group(2), m.group(3)
        full_date = _parse_cc_year(trans_date_str)
        amount = float(amt_str.replace(',', ''))
        desc = re.sub(r'\s+', ' ', raw_desc).strip()

        # Payments received are credits (money in to CC = transfer from checking)
        desc_lower = desc.lower()
        is_payment = any(k in desc_lower for k in _CC_PAYMENT_KEYWORDS)
        is_debit = not is_payment  # charges are debits, payments are credits

        transactions.append({
            'date':        full_date,
            'description': desc,
            'amount':      amount,
            'is_debit':    is_debit,
            'account':     'Visa Credit Card',
        })

    return transactions


# ── Statement type detection ──────────────────────────────────────────────────

def _is_credit_card_statement(full_text: str) -> bool:
    """Return True if this looks like an NFCU Visa credit card statement."""
    indicators = [
        'summary of account activity',
        'nfo payment received',
        'statement closing date',
        'minimum payment due',
        'credit limit',
        'cash limit',
    ]
    text_lower = full_text.lower()
    matches = sum(1 for ind in indicators if ind in text_lower)
    return matches >= 3


# ── Public API ────────────────────────────────────────────────────────────────

def parse_nfcu_pdf(pdf_file) -> list[dict]:
    """
    Parse a Navy Federal PDF statement (checking/savings OR credit card).

    Args:
        pdf_file: file-like object (bytes or BytesIO) of the PDF

    Returns:
        List of dicts with keys:
            date        – "YYYY-MM-DD"
            description – cleaned merchant/description string
            amount      – positive float
            is_debit    – True = money out (expense/charge), False = money in (credit/payment)
            account     – account name string
    """
    if isinstance(pdf_file, bytes):
        pdf_file = io.BytesIO(pdf_file)

    with pdfplumber.open(pdf_file) as pdf:
        full_text = "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )

    # ── Route to correct parser ──────────────────────────────────────────────
    if _is_credit_card_statement(full_text):
        return _parse_credit_card_statement(full_text)

    # Deposit account — detect statement period from header
    # Format: "MM/DD/YY - MM/DD/YY"  (start - end)
    period_match = re.search(
        r'(\d{2})/(\d{2})/(\d{2})\s*-\s*(\d{2})/(\d{2})/(\d{2})', full_text
    )
    if period_match:
        end_month = int(period_match.group(4))   # end MM
        year      = "20" + period_match.group(6) # end YY → YYYY
    else:
        # Fallback: look for any 4-digit year
        yr_match  = re.search(r'\b(20\d{2})\b', full_text)
        year      = yr_match.group(1) if yr_match else "2025"
        end_month = 0  # unknown — no year-boundary correction

    return _parse_deposit_statement(full_text, year, end_month)
