"""
budget_importer.py
──────────────────
Parses the Microsoft "Personal Monthly Budget" Excel template (and similar
layouts) into structured income + expense dicts that can be inserted into
the app's database.

Supports:
  • The exact Microsoft template attached by the user
  • Generic flat tables (description | projected | actual)
  • AI-assisted categorisation via Claude when the layout is ambiguous
"""

from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd


# ── Known category mappings from the Microsoft template ──────────────────────
# Maps common label strings (lowercased) → (category, subcategory)
_KNOWN_LABELS: dict[str, tuple[str, str]] = {
    # Housing
    "mortgage or rent":        ("Housing", "Mortgage / Rent"),
    "mortgage":                ("Housing", "Mortgage / Rent"),
    "rent":                    ("Housing", "Mortgage / Rent"),
    "phone":                   ("Housing", "Phone"),
    "electricity":             ("Housing", "Electricity"),
    "gas":                     ("Housing", "Gas"),
    "water and sewer":         ("Housing", "Water and Sewer"),
    "water":                   ("Housing", "Water and Sewer"),
    "cable / wifi":            ("Housing", "Cable / WiFi"),
    "cable/wifi":              ("Housing", "Cable / WiFi"),
    "internet":                ("Housing", "Cable / WiFi"),
    "wifi":                    ("Housing", "Cable / WiFi"),
    "waste removal":           ("Housing", "Waste Removal"),
    "trash":                   ("Housing", "Waste Removal"),
    "maintenance or repairs":  ("Housing", "Maintenance / Repairs"),
    "maintenance":             ("Housing", "Maintenance / Repairs"),
    "repairs":                 ("Housing", "Maintenance / Repairs"),
    "supplies":                ("Housing", "Supplies"),
    # Transportation
    "vehicle payment":         ("Transportation", "Vehicle Payment"),
    "car payment":             ("Transportation", "Vehicle Payment"),
    "bus/taxi fare":           ("Transportation", "Bus / Taxi"),
    "bus":                     ("Transportation", "Bus / Taxi"),
    "taxi":                    ("Transportation", "Bus / Taxi"),
    "uber":                    ("Transportation", "Bus / Taxi"),
    "lyft":                    ("Transportation", "Bus / Taxi"),
    "insurance":               ("Transportation", "Insurance"),
    "auto insurance":          ("Transportation", "Insurance"),
    "car insurance":           ("Transportation", "Insurance"),
    "licensing":               ("Transportation", "Licensing"),
    "fuel":                    ("Transportation", "Fuel"),
    "gas (fuel)":              ("Transportation", "Fuel"),
    # Insurance
    "renters":                 ("Insurance", "Renters"),
    "renters insurance":       ("Insurance", "Renters"),
    "health":                  ("Insurance", "Health"),
    "health insurance":        ("Insurance", "Health"),
    "life":                    ("Insurance", "Life"),
    "life insurance":          ("Insurance", "Life"),
    # Food
    "groceries":               ("Food", "Groceries"),
    "grocery":                 ("Food", "Groceries"),
    "dining out":              ("Food", "Dining Out"),
    "restaurants":             ("Food", "Dining Out"),
    "eating out":              ("Food", "Dining Out"),
    # Pets
    "pet food":                ("Pets", "Food"),
    "pet medical":             ("Pets", "Medical"),
    "grooming":                ("Pets", "Grooming"),
    "pet grooming":            ("Pets", "Grooming"),
    "toys":                    ("Pets", "Toys"),
    # Personal Care
    "medical":                 ("Personal Care", "Medical"),
    "doctor":                  ("Personal Care", "Medical"),
    "hair/nails":              ("Personal Care", "Hair / Nails"),
    "hair":                    ("Personal Care", "Hair / Nails"),
    "nails":                   ("Personal Care", "Hair / Nails"),
    "clothing":                ("Personal Care", "Clothing"),
    "clothes":                 ("Personal Care", "Clothing"),
    "dry cleaning":            ("Personal Care", "Dry Cleaning"),
    "health club":             ("Personal Care", "Health Club"),
    "gym":                     ("Personal Care", "Health Club"),
    "fitness":                 ("Personal Care", "Health Club"),
    # Entertainment
    "night out":               ("Entertainment", "Night Out"),
    "music platforms":         ("Entertainment", "Music Platforms"),
    "spotify":                 ("Entertainment", "Music Platforms"),
    "apple music":             ("Entertainment", "Music Platforms"),
    "movies":                  ("Entertainment", "Movies"),
    "concerts":                ("Entertainment", "Concerts"),
    "sporting events":         ("Entertainment", "Sporting Events"),
    "live theater":            ("Entertainment", "Live Theater"),
    "subscriptions":           ("Entertainment", "Subscriptions"),
    "netflix":                 ("Entertainment", "Subscriptions"),
    "hulu":                    ("Entertainment", "Subscriptions"),
    "disney+":                 ("Entertainment", "Subscriptions"),
    # Loans
    "personal":                ("Loans", "Personal Loan"),
    "personal loan":           ("Loans", "Personal Loan"),
    "student":                 ("Loans", "Student Loan"),
    "student loan":            ("Loans", "Student Loan"),
    "credit card":             ("Loans", "Credit Card"),
    # Taxes
    "federal":                 ("Taxes", "Federal"),
    "state":                   ("Taxes", "State"),
    "local":                   ("Taxes", "Local"),
    # Savings / Investments
    "retirement account":      ("Savings / Investments", "Retirement Account"),
    "401k":                    ("Savings / Investments", "Retirement Account"),
    "401(k)":                  ("Savings / Investments", "Retirement Account"),
    "investment account":      ("Savings / Investments", "Investment Account"),
    "roth ira":                ("Savings / Investments", "Roth IRA"),
    "roth":                    ("Savings / Investments", "Roth IRA"),
    # Gifts & Donations
    "charity":                 ("Gifts & Donations", "Charity"),
    "charity 1":               ("Gifts & Donations", "Charity 1"),
    "charity 2":               ("Gifts & Donations", "Charity 2"),
    "charity 3":               ("Gifts & Donations", "Charity 3"),
    "donations":               ("Gifts & Donations", "Donations"),
    # Legal
    "attorney":                ("Legal", "Attorney"),
    "alimony":                 ("Legal", "Alimony"),
    "payments on lien or judgment": ("Legal", "Lien / Judgment"),
}

# Section headers in the Microsoft template — skip these rows
_SECTION_HEADERS = {
    "housing", "transportation", "insurance", "food", "pets",
    "personal care", "entertainment", "loans", "taxes",
    "savings or investments", "savings / investments",
    "gifts and donations", "legal",
    "subtotal", "total monthly income", "total projected cost",
    "total actual cost", "total difference",
    "projected monthly income", "actual monthly income",
    "projected balance", "actual balance", "difference",
    "income 1", "extra income",
}

# Columns that look like "projected cost" / "actual cost"
_PROJ_PATTERNS = re.compile(r"projected", re.I)
_ACT_PATTERNS  = re.compile(r"actual",    re.I)


def _is_numeric(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return True
    try:
        float(str(val).replace(",", "").replace("$", "").strip())
        return True
    except (ValueError, TypeError):
        return False


def _to_float(val: Any) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _clean_label(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _lookup_category(label: str) -> tuple[str, str] | None:
    """Return (category, subcategory) from the known-labels map, or None."""
    key = label.lower().strip()
    if key in _KNOWN_LABELS:
        return _KNOWN_LABELS[key]
    # Partial match — check if any known key is contained in the label
    for k, v in _KNOWN_LABELS.items():
        if k in key or key in k:
            return v
    return None


# ── Microsoft template parser ─────────────────────────────────────────────────

def parse_microsoft_template(df: pd.DataFrame) -> dict:
    """
    Parse the Microsoft 'PERSONAL MONTHLY BUDGET' sheet layout.

    The sheet has two side-by-side tables (columns B-E and G-J).
    Returns:
        {
          "income": [{"source": str, "amount": float, "notes": str}],
          "expenses": [{"category": str, "subcategory": str,
                        "projected": float, "actual": float}],
          "raw_rows": int,
          "unmatched": [str],   # labels we couldn't categorise
        }
    """
    income: list[dict] = []
    expenses: list[dict] = []
    unmatched: list[str] = []
    raw_rows = 0

    # Flatten all cell values into a searchable list of (row_idx, col_idx, value)
    cells: list[tuple[int, int, Any]] = []
    for r_idx, row in df.iterrows():
        for c_idx, val in enumerate(row):
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                cells.append((int(r_idx), c_idx, val))

    # ── Extract income ────────────────────────────────────────────────────────
    # Look for rows where a cell contains "Income 1" or "Extra income" near a number
    for r_idx, row in df.iterrows():
        row_vals = [v for v in row if v is not None and not (isinstance(v, float) and pd.isna(v))]
        row_str  = " ".join(str(v).lower() for v in row_vals)

        if "income 1" in row_str or "income1" in row_str:
            nums = [_to_float(v) for v in row_vals if _is_numeric(v)]
            if nums:
                income.append({"source": "Income 1 (Salary)", "amount": max(nums), "notes": "Imported from Excel"})

        elif "extra income" in row_str:
            nums = [_to_float(v) for v in row_vals if _is_numeric(v)]
            if nums:
                income.append({"source": "Extra Income", "amount": max(nums), "notes": "Imported from Excel"})

    # ── Extract expenses ──────────────────────────────────────────────────────
    # Walk every row; for each text cell that looks like an expense label,
    # grab the nearest numeric values to the right as projected / actual.
    current_section = "Other"

    for r_idx, row in df.iterrows():
        row_list = list(row)
        for c_idx, val in enumerate(row_list):
            label = _clean_label(val)
            if not label or _is_numeric(val):
                continue

            label_lower = label.lower()

            # Detect section headers to track current category context
            if label_lower in _section_headers_set():
                current_section = label.title()
                continue

            # Skip formula strings and other noise
            if label.startswith("[Formula") or label.startswith("="):
                continue

            # Skip very long strings (instructions / descriptions)
            if len(label) > 60:
                continue

            # Skip if it's a known section-level label
            if label_lower in _SECTION_HEADERS:
                continue

            # Try to find projected + actual values to the right of this cell
            right_nums: list[float] = []
            for look_ahead in range(1, 6):
                if c_idx + look_ahead < len(row_list):
                    candidate = row_list[c_idx + look_ahead]
                    if _is_numeric(candidate):
                        right_nums.append(_to_float(candidate))

            if not right_nums:
                continue  # no numbers → not an expense row

            raw_rows += 1
            projected = right_nums[0] if len(right_nums) >= 1 else 0.0
            actual    = right_nums[1] if len(right_nums) >= 2 else 0.0

            # Look up category
            mapping = _lookup_category(label)
            if mapping:
                cat, sub = mapping
            else:
                # Use current section as category, label as subcategory
                cat = current_section if current_section != "Other" else "Other"
                sub = label.title()
                unmatched.append(label)

            # Avoid duplicates (same cat+sub already added)
            existing = next((e for e in expenses if e["category"] == cat and e["subcategory"] == sub), None)
            if existing:
                # Keep the higher values (in case the template has duplicate rows)
                existing["projected"] = max(existing["projected"], projected)
                existing["actual"]    = max(existing["actual"],    actual)
            else:
                expenses.append({
                    "category":   cat,
                    "subcategory": sub,
                    "projected":  projected,
                    "actual":     actual,
                })

    return {
        "income":   income,
        "expenses": expenses,
        "raw_rows": raw_rows,
        "unmatched": list(set(unmatched)),
    }


def _section_headers_set() -> set[str]:
    return _SECTION_HEADERS


# ── Generic flat-table parser ─────────────────────────────────────────────────

def parse_generic_table(df: pd.DataFrame) -> dict:
    """
    Attempt to parse a generic flat table with columns like:
      Description | Projected | Actual   (or similar names)

    Returns same structure as parse_microsoft_template.
    """
    income: list[dict] = []
    expenses: list[dict] = []
    unmatched: list[str] = []

    # Normalise column names
    df.columns = [str(c).strip() for c in df.columns]
    col_lower  = [c.lower() for c in df.columns]

    # Find description column
    desc_col = None
    for i, c in enumerate(col_lower):
        if any(kw in c for kw in ["description", "item", "name", "category", "expense", "label"]):
            desc_col = df.columns[i]
            break
    if desc_col is None and len(df.columns) >= 1:
        desc_col = df.columns[0]

    # Find projected / actual columns
    proj_col = next((df.columns[i] for i, c in enumerate(col_lower) if _PROJ_PATTERNS.search(c)), None)
    act_col  = next((df.columns[i] for i, c in enumerate(col_lower) if _ACT_PATTERNS.search(c)),  None)

    # Fallback: use 2nd and 3rd numeric columns
    num_cols = [df.columns[i] for i, c in enumerate(col_lower)
                if df[df.columns[i]].apply(_is_numeric).sum() > len(df) * 0.3]
    if proj_col is None and len(num_cols) >= 1:
        proj_col = num_cols[0]
    if act_col is None and len(num_cols) >= 2:
        act_col = num_cols[1]

    for _, row in df.iterrows():
        label = _clean_label(row.get(desc_col, "")) if desc_col else ""
        if not label or label.lower() in _SECTION_HEADERS:
            continue
        if label.startswith("[Formula") or len(label) > 80:
            continue

        projected = _to_float(row.get(proj_col, 0)) if proj_col else 0.0
        actual    = _to_float(row.get(act_col,  0)) if act_col  else 0.0

        if projected == 0 and actual == 0:
            continue

        # Income detection
        label_lower = label.lower()
        if any(kw in label_lower for kw in ["income", "salary", "paycheck", "wage", "revenue", "earnings"]):
            income.append({
                "source": label.title(),
                "amount": actual if actual > 0 else projected,
                "notes":  "Imported from Excel",
            })
            continue

        mapping = _lookup_category(label)
        if mapping:
            cat, sub = mapping
        else:
            cat = "Other"
            sub = label.title()
            unmatched.append(label)

        expenses.append({
            "category":   cat,
            "subcategory": sub,
            "projected":  projected,
            "actual":     actual,
        })

    return {
        "income":    income,
        "expenses":  expenses,
        "raw_rows":  len(df),
        "unmatched": list(set(unmatched)),
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def parse_budget_excel(file_bytes: bytes | io.BytesIO) -> dict:
    """
    Auto-detect the Excel layout and return parsed budget data.

    Returns:
        {
          "income":    list[dict],   # {source, amount, notes}
          "expenses":  list[dict],   # {category, subcategory, projected, actual}
          "raw_rows":  int,
          "unmatched": list[str],    # labels that couldn't be auto-categorised
          "sheet":     str,          # sheet name used
          "layout":    str,          # "microsoft_template" | "generic"
        }
    """
    if isinstance(file_bytes, bytes):
        file_bytes = io.BytesIO(file_bytes)

    xl = pd.ExcelFile(file_bytes, engine="openpyxl")
    sheet_names = xl.sheet_names

    # Prefer the "PERSONAL MONTHLY BUDGET" sheet if present
    target_sheet = None
    for name in sheet_names:
        if "budget" in name.lower() and "personal" in name.lower():
            target_sheet = name
            break
    if target_sheet is None:
        for name in sheet_names:
            if "budget" in name.lower():
                target_sheet = name
                break
    if target_sheet is None:
        target_sheet = sheet_names[0]

    df = xl.parse(target_sheet, header=None)

    # Detect layout: Microsoft template has no proper header row
    # (first row is usually a label like "PERSONAL MONTHLY BUDGET")
    first_row_str = " ".join(str(v).lower() for v in df.iloc[0] if v is not None and not (isinstance(v, float) and pd.isna(v)))
    is_ms_template = (
        "personal monthly budget" in first_row_str
        or "projected monthly income" in " ".join(str(v).lower() for v in df.values.flatten() if v is not None and not (isinstance(v, float) and pd.isna(v)))[:500]
    )

    if is_ms_template:
        result = parse_microsoft_template(df)
        result["sheet"]  = target_sheet
        result["layout"] = "microsoft_template"
    else:
        # Try with header row
        df_with_header = xl.parse(target_sheet)
        result = parse_generic_table(df_with_header)
        result["sheet"]  = target_sheet
        result["layout"] = "generic"

    return result


# ── AI-assisted categorisation helper ────────────────────────────────────────

def build_ai_categorise_prompt(unmatched_labels: list[str], existing_categories: list[tuple[str, str]]) -> str:
    """
    Build a prompt for Claude to categorise unmatched expense labels.
    existing_categories: list of (category, subcategory) tuples already in the DB.
    """
    cat_list = "\n".join(f"  - {cat} › {sub}" for cat, sub in existing_categories)
    label_list = "\n".join(f"  - {lbl}" for lbl in unmatched_labels)
    return (
        "I'm importing a personal budget spreadsheet and have these expense labels "
        "that I couldn't automatically categorise:\n"
        f"{label_list}\n\n"
        "My existing budget categories are:\n"
        f"{cat_list}\n\n"
        "For each label, suggest the best matching category and subcategory from my list, "
        "OR suggest a new category/subcategory if none fit. "
        "Reply in this exact format (one line per label):\n"
        "LABEL: <original label> → CATEGORY: <category> › SUBCATEGORY: <subcategory>\n"
        "Only output those lines, nothing else."
    )


def parse_ai_categorise_response(response: str, unmatched_labels: list[str]) -> dict[str, tuple[str, str]]:
    """
    Parse Claude's categorisation response.
    Returns {original_label: (category, subcategory)}.
    """
    result: dict[str, tuple[str, str]] = {}
    pattern = re.compile(
        r"LABEL:\s*(.+?)\s*→\s*CATEGORY:\s*(.+?)\s*›\s*SUBCATEGORY:\s*(.+)",
        re.IGNORECASE
    )
    for line in response.strip().split("\n"):
        m = pattern.match(line.strip())
        if m:
            label = m.group(1).strip()
            cat   = m.group(2).strip()
            sub   = m.group(3).strip()
            result[label] = (cat, sub)
    return result
