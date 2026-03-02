"""
Navy Federal Credit Union PDF Statement Parser
Handles two statement formats:
  1. Deposit account statements (Checking / Savings)
  2. Visa credit card statements

Uses word-position-based extraction (pdfplumber extract_words) to
correctly reconstruct columnar layouts — descriptions (left column)
and amounts (right column) that share the same visual row are joined
into a single text line before regex matching.
"""
import re
import io
from collections import defaultdict
import pdfplumber


# ── Layout-aware text extraction ──────────────────────────────────────────────

def _extract_layout_lines(pdf_file) -> list[str]:
    """
    Extract lines from every page of a PDF using word positions.

    pdfplumber's default extract_text() can separate visually-adjacent
    columns into different text blocks.  By grouping extracted *words*
    by their vertical (top) coordinate we reconstruct true visual rows,
    so a description in column A and its amount in column B end up on
    the same line.

    Returns a flat list of strings, one per visual row across all pages.
    """
    if isinstance(pdf_file, (bytes, bytearray)):
        pdf_file = io.BytesIO(pdf_file)
    if hasattr(pdf_file, 'seek'):
        pdf_file.seek(0)

    all_lines: list[str] = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            words = page.extract_words(
                x_tolerance=6,
                y_tolerance=4,
                keep_blank_chars=False,
                use_text_flow=False,
            )
            if not words:
                continue

            # Group words by rounded top coordinate (2-px buckets)
            rows: dict[int, list] = defaultdict(list)
            for w in words:
                y_key = round(w['top'] / 2) * 2
                rows[y_key].append(w)

            # Sort rows top→bottom, words left→right; join with a space
            for y in sorted(rows):
                row_words = sorted(rows[y], key=lambda w: w['x0'])
                all_lines.append(' '.join(w['text'] for w in row_words))

    return all_lines


def _extract_raw_text(pdf_file) -> str:
    """
    Extract plain text using pdfplumber's extract_text() (no layout magic).
    Used ONLY for statement-type detection — keyword presence checks.
    Font-split artifacts don't matter since we just look for substrings.
    """
    if isinstance(pdf_file, (bytes, bytearray)):
        pdf_file = io.BytesIO(pdf_file)
    if hasattr(pdf_file, 'seek'):
        pdf_file.seek(0)
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


# ── Checking/Savings (deposit) parser ────────────────────────────────────────
#
# Visual row format after layout reconstruction:
#   MM-DD  <description>  <amount>[−]  <balance>
#
# Debit:  01-27 POS Debit- Debit Card 3453 01-25-25 Alex Panjwani GA  19.59-  758.70
# Credit: 02-06 Deposit - ACH Paid From Visa Technology Direct Dep     996.97  1,159.84
# Debit (space before dash):  01-28 McDonald's GA  14.95 -  216.15

_DEP_TXN_RE = re.compile(
    r'^(\d{2}-\d{2})\s+(.+?)\s+([\d,]+\.\d{2})\s*(-?)\s*([\d,]+\.\d{2})$'
)

_DEP_SKIP = [
    'beginning balance', 'ending balance', 'dividend', 'atm rebate',
    'items paid', 'average daily balance', 'your account earned',
    'no transactions', 'continued from', 'joint owner',
    'statement of account', 'statement period', 'access no',
]

_DEP_ACCOUNT_HEADERS = [
    (r'Campus Checking',    'Campus Checking'),
    (r'EveryDay Checking',  'EveryDay Checking'),
    (r'e-Checking',         'e-Checking'),
    (r'Membership Savings', 'Membership Savings'),
]


def _normalize_dep_line(line: str) -> str:
    """Fix common PDF text-extraction artifacts in deposit statements."""
    # "12-02 -25" artifact from date ranges in descriptions
    line = re.sub(r'(\d{2}-\d{2})\s+-(\d{2})', r'\1-\2', line)
    line = re.sub(r'(\d{3}-\d{3})\s+-(\d{4})', r'\1-\2', line)
    line = re.sub(r'Deb\s*i\s*t\s*-', 'Debit-', line)
    line = re.sub(r'C\s+ard\b', 'Card', line)
    line = re.sub(r'\b([A-Z])\s+([A-Z])\b', r'\1\2', line)
    # Normalise trailing "amount -" → "amount-" so regex group 4 captures dash
    line = re.sub(r'([\d,]+\.\d{2})\s+-\s+([\d,]+\.\d{2})$', r'\1- \2', line)
    return line


def _clean_dep_description(desc: str) -> str:
    """Strip card/date noise from deposit-account transaction descriptions."""
    desc = re.sub(r'\b(\d)\s+(\d)-(\d{2})-(\d{2})\b', r'\1\2-\3-\4', desc)
    desc = re.sub(r'POS\s+Debit\s*-?\s*Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    desc = re.sub(r'POS\s+Credit\s+Adjustment\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    desc = re.sub(r'POS\s+Debit\s+-\s+Debit\s+Card\s+\d+\s*(?:Transaction\s*)?\d{2}-\d{2}-\d{2}\s*', '', desc)
    # Wipe trailing "Paid To -" prefix (keep merchant name)
    desc = re.sub(r'^Paid\s+To\s+-\s*', '', desc, flags=re.I)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc


def _parse_deposit_statement(lines: list[str], year: str, end_month: int = 0) -> list[dict]:
    """Parse a checking/savings deposit account statement from reconstructed lines."""
    transactions = []
    current_account = None
    year_int = int(year)

    for raw_line in lines:
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
# The NFCU Visa CC statement can produce lines in two formats depending
# on how pdfplumber reconstructs the table:
#
# FORMAT A (single line, proper spacing):
#   "01/02/26 01/05/26 24692166002102839952326 TST*TON TON RAMEN GA $18.22"
#
# FORMAT B (date+ref on one line, desc+amount on next):
#   "01/02/26 01/05/26 24692166002102839952326"
#   "TST*TON TON RAMEN & YAKI Atlanta GA $18.22"
#
# FORMAT C (no spaces, glued fields — seen in payment section):
#   "01/06/2601/06/2674060956006065270100003NFO PAYMENT RECEIVEDxxxx 2045$300.00"
#
# We handle all three by trying single-line first, then joining pairs.

_CC_TXN_RE = re.compile(
    r'(?:^|\s)(\d{2}/\d{2}/\d{2})'      # trans date MM/DD/YY (may be glued)
    r'[\s/\d]{8,}'                        # post-date + optional ref number start
    r'(\d{10,})\s*'                        # reference number (10+ digits)
    r'(.+?)\s+'                            # description (non-greedy)
    r'\$?([\d,]+\.\d{2})$',               # amount
    re.S
)

# Single-line CC transaction — reference number is OPTIONAL (some rows
# omit it when there is a long merchant name that wraps the ref off-screen)
_CC_CLEAN_RE = re.compile(
    r'^(\d{2}/\d{2}/\d{2})\s+'          # trans date MM/DD/YY
    r'\d{2}/\d{2}/\d{2}\s+'             # post date
    r'(?:\d{10,}\s+)?'                   # reference number (OPTIONAL)
    r'(.+?)\s+'                          # description
    r'\$\s*([\d,][,\d\s]*\.\d{2})$'     # amount — allow "$ 18.22" and "90 0.00"
)

# Lines to skip in CC statements
_CC_SKIP = [
    'total payments', 'total new activity', 'interest charge',
    'total interest', 'balance subject', 'annual percentage',
    'type of balance', 'purchases', 'bal trf', 'cash advances',
    'submitted by', 'trans date', 'description', 'amount',
    'payments and credits', 'transactions', 'darrian belcher',
    'total fees', 'total interest', '2026 totals', 'rewards',
]

_CC_PAYMENT_KEYWORDS = [
    'nfo payment received',
    'payment received',
    'online payment',
]

_CC_DATE_LINE_RE = re.compile(
    r'^(\d{2}/\d{2}/\d{2})[\s/]'
)
_CC_AMOUNT_RE = re.compile(r'\$?([\d,]+\.\d{2})$')


def _parse_cc_year(date_str: str) -> str:
    """Convert MM/DD/YY to YYYY-MM-DD."""
    parts = date_str.split('/')
    month, day, yr = parts[0], parts[1], parts[2]
    return f"20{yr}-{month}-{day}"


def _try_parse_cc_line(line: str) -> dict | None:
    """
    Try to parse a single (possibly joined) line as a CC transaction.
    Returns a transaction dict or None.
    """
    line = line.strip()
    if not line:
        return None
    if any(k in line.lower() for k in _CC_SKIP):
        return None

    # Try clean single-line format (ref number optional, not captured)
    m = _CC_CLEAN_RE.match(line)
    if m:
        trans_date_str, raw_desc, amt_str = m.groups()
        return _make_cc_txn(trans_date_str, raw_desc, amt_str)

    # Try glued format (no spaces between date fields)
    # e.g. "01/06/2601/06/2674060956006065270100003NFO PAYMENT RECEIVED...2045$300.00"
    glued = re.match(
        r'^(\d{2}/\d{2}/\d{2})\d{2}/\d{2}/\d{2}(?:\d{10,})?\s*(.+?)\s*\$\s*([\d,][,\d\s]*\.\d{2})$',
        line
    )
    if glued:
        trans_date_str, raw_desc, amt_str = glued.groups()
        return _make_cc_txn(trans_date_str, raw_desc, amt_str)

    return None


def _make_cc_txn(trans_date_str: str, raw_desc: str, amt_str: str) -> dict:
    full_date = _parse_cc_year(trans_date_str)
    # Normalize amount: remove spaces ("90 0.00" → "900.00", "18 .22" → "18.22")
    amount = float(re.sub(r'\s', '', amt_str).replace(',', ''))
    desc = re.sub(r'\s+', ' ', raw_desc).strip()
    # Strip "xxxx xxxx xxxx NNNN" account-number suffix
    desc = re.sub(r'\s+xxxx[\s\w]+$', '', desc, flags=re.I).strip()
    desc_lower = desc.lower()
    is_payment = any(k in desc_lower for k in _CC_PAYMENT_KEYWORDS)
    return {
        'date':        full_date,
        'description': desc,
        'amount':      amount,
        'is_debit':    not is_payment,
        'account':     'Visa Credit Card',
    }


def _parse_credit_card_statement(lines: list[str]) -> list[dict]:
    """
    Parse an NFCU Visa credit card statement from reconstructed layout lines.
    Handles both single-line and multi-line (date+ref / desc+amount) formats.
    """
    transactions = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip blanks and known header/summary lines
        if not line or any(k in line.lower() for k in _CC_SKIP):
            i += 1
            continue

        # Attempt single-line parse first
        txn = _try_parse_cc_line(line)
        if txn:
            transactions.append(txn)
            i += 1
            continue

        # If this line looks like a date header (MM/DD/YY ...) but has no amount,
        # try joining with subsequent lines (up to 3) to get the full transaction
        if _CC_DATE_LINE_RE.match(line):
            combined = line
            for j in range(1, 4):
                if i + j >= len(lines):
                    break
                next_line = lines[i + j].strip()
                if not next_line:
                    break
                combined = combined + ' ' + next_line
                txn = _try_parse_cc_line(combined)
                if txn:
                    transactions.append(txn)
                    i += j  # extra lines consumed
                    break

        i += 1

    return transactions


# ── Statement type detection ──────────────────────────────────────────────────

def _is_credit_card_statement(text: str) -> bool:
    """Return True if this looks like an NFCU Visa credit card statement."""
    indicators = [
        'summary of account activity',
        'nfo payment received',
        'statement closing date',
        'minimum payment due',
        'credit limit',
        'cash limit',
    ]
    text_lower = text.lower()
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
            is_debit    – True = money out, False = money in
            account     – account name string
    """
    if isinstance(pdf_file, bytes):
        pdf_file = io.BytesIO(pdf_file)
    if hasattr(pdf_file, 'seek'):
        pdf_file.seek(0)

    # ── Detect statement type using raw text (more reliable for keywords) ────
    raw_text = _extract_raw_text(pdf_file)
    if hasattr(pdf_file, 'seek'):
        pdf_file.seek(0)

    # ── Extract layout-aware lines for actual parsing ────────────────────────
    lines = _extract_layout_lines(pdf_file)
    if hasattr(pdf_file, 'seek'):
        pdf_file.seek(0)

    # ── Route to correct parser ──────────────────────────────────────────────
    if _is_credit_card_statement(raw_text):
        return _parse_credit_card_statement(lines)

    full_text = '\n'.join(lines)

    # ── Deposit account — detect statement period ────────────────────────────
    period_match = re.search(
        r'(\d{2})/(\d{2})/(\d{2})\s*-\s*(\d{2})/(\d{2})/(\d{2})', full_text
    )
    if period_match:
        end_month = int(period_match.group(4))
        year      = "20" + period_match.group(6)
    else:
        yr_match  = re.search(r'\b(20\d{2})\b', full_text)
        year      = yr_match.group(1) if yr_match else "2025"
        end_month = 0

    return _parse_deposit_statement(lines, year, end_month)
