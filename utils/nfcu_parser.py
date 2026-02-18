"""
Navy Federal Credit Union PDF Statement Parser
Extracts transactions from NFCU statement PDFs.
"""
import re
import io
import pdfplumber


# Matches transaction lines in two formats:
#
# Format A (amount- attached):
#   11-26 POS Debit- Debit Card 3453 11-25-25 AMC 9640 Online KS   47.70-   5,469.29
#
# Format B (amount space- separated):
#   11-28 POS Debit- Debit Card 3453 11-27-25 Cc* Crumbl UT   13.07 -   7,387.20
#
# Capture groups: (date) (description) (amount with optional space-dash) (balance)
TXN_RE = re.compile(
    r'^(\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s*(-?)\s+([\d,]+\.\d{2})$'
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


def _parse_amount(amount_str: str, dash: str):
    """Return (float_amount, is_debit).
    
    dash is the captured '-' group (may be empty string for credits).
    is_debit=True means money out (expense), False means money in (credit/deposit).
    """
    amount = float(amount_str.replace(',', ''))
    is_debit = dash == '-'
    return amount, is_debit


def _normalize_line(line: str) -> str:
    """Fix PDF artifacts: collapse broken spaces inside words/numbers.
    
    The NFCU PDF renderer sometimes inserts spaces mid-word or mid-number:
      'Debit C ard'  -> 'Debit Card'
      '107 7 2'      -> '1077 2'  (can't fully fix merchant names)
      '9.32 -'       -> handled by regex
      '12-02 -25'    -> '12-02-25'
    
    We focus on fixing the date patterns and obvious artifacts.
    """
    # Fix broken transaction dates like "12-02 -25" -> "12-02-25"
    line = re.sub(r'(\d{2}-\d{2})\s+-(\d{2})', r'\1-\2', line)
    # Fix broken phone-like numbers in descriptions like "757-856 -5083" -> "757-856-5083"
    line = re.sub(r'(\d{3}-\d{3})\s+-(\d{4})', r'\1-\2', line)
    # Fix "Deb it-" / "Debi t-" -> "Debit-"  (space injected before 't')
    line = re.sub(r'Deb\s*i\s*t\s*-', 'Debit-', line)
    # Fix "C ard" -> "Card"
    line = re.sub(r'C\s+ard\b', 'Card', line)
    # Fix "V A" at end of state abbreviations -> "VA"
    line = re.sub(r'\b([A-Z])\s+([A-Z])\b', r'\1\2', line)
    return line


def _clean_description(desc: str) -> str:
    """Strip card/date noise from NFCU transaction descriptions."""
    # First fix broken dates inside descriptions like "1 2-11-25" -> "12-11-25"
    desc = re.sub(r'\b(\d)\s+(\d)-(\d{2})-(\d{2})\b', r'\1\2-\3-\4', desc)
    # Remove "POS Debit- Debit Card XXXX [Transaction] MM-DD-YY " prefix (all spacing variants)
    desc = re.sub(r'POS\s+Debit\s*-?\s*Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    # Remove "POS Credit Adjustment XXXX Transaction MM-DD-YY " prefix
    desc = re.sub(r'POS\s+Credit\s+Adjustment\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    # Remove "POS Debit - Debit Card XXXX Transaction MM-DD-YY " (space before dash variant)
    desc = re.sub(r'POS\s+Debit\s+-\s+Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    # Normalise whitespace
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
    for raw_line in full_text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        # Detect account section headers
        if re.search(r'Campus Checking', line, re.I):
            current_account = 'Campus Checking'
        elif re.search(r'e-Checking', line, re.I):
            current_account = 'e-Checking'
        elif re.search(r'Membership Savings', line, re.I):
            current_account = 'Membership Savings'

        # Normalize PDF artifacts before matching
        line = _normalize_line(line)

        m = TXN_RE.match(line)
        if not m or not current_year or not current_account:
            continue

        date_str, raw_desc, amt_str, dash, _bal = m.groups()

        # Skip non-transaction summary lines
        if any(k in raw_desc.lower() for k in SKIP_KEYWORDS):
            continue

        amount, is_debit = _parse_amount(amt_str, dash)
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
