"""Regression tests for NFCU PDF parser edge cases seen in live statements."""

import io

import pytest

from utils.nfcu_parser import _normalize_dep_line, _parse_deposit_statement
from utils import nfcu_parser


def test_normalize_dep_line_fixes_split_amount_fragments():
    """Parser should normalize OCR/word-split amount artifacts."""
    raw = "03-06 Deposit - ACH Paid From Payroll 2,1 55.03 11,405.11"
    norm = _normalize_dep_line(raw)
    assert "2,155.03" in norm


def test_parse_deposit_statement_accepts_no_balance_rows():
    """Rows missing running-balance column should still parse."""
    lines = [
        "Campus Checking - 0000000000",
        "03-10 Transfer To Credit Card 300.00-",
    ]
    txns = _parse_deposit_statement(lines, year="2026", end_month=3)
    assert len(txns) == 1
    t = txns[0]
    assert t["date"] == "2026-03-10"
    assert t["amount"] == 300.00
    assert t["is_debit"] is True
    assert t["account"] == "Campus Checking"


def test_parse_deposit_statement_handles_unicode_minus():
    """Unicode minus glyphs from PDFs should be treated as debit markers."""
    lines = [
        "Campus Checking - 0000000000",
        "03-10 Zelle Transfer 24.00− 6,631.11",
    ]
    txns = _parse_deposit_statement(lines, year="2026", end_month=3)
    assert len(txns) == 1
    assert txns[0]["is_debit"] is True
    assert txns[0]["amount"] == 24.00


def test_parse_nfcu_pdf_raises_clear_error_when_pdfplumber_missing(monkeypatch):
    """Missing pdfplumber should raise actionable RuntimeError instead of import crash."""
    monkeypatch.setattr(nfcu_parser, "pdfplumber", None)
    with pytest.raises(RuntimeError, match="Missing dependency: 'pdfplumber'"):
        nfcu_parser.parse_nfcu_pdf(io.BytesIO(b"%PDF-1.4 fake"))
