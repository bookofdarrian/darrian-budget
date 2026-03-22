# BUGFIX_PATTERNS.md — Known Bugs, Patterns & Fixes
**Last Updated: 2026-03-22**
**Maintained by: Darrian Belcher / Peach State Savings**

> This document captures recurring bugs that have burned us in production, the root cause,
> how to detect them, and the exact fix pattern. Claude agents MUST read this file before
> writing any database or authentication code.

---

## 🔴 BUG #1 — `conn.execute()` Crashes on PostgreSQL

### Status: FIXED (2026-03-22) — 9 pages patched
### Files Fixed: 146, 143, 144, 66, 70, 84, 73, 29

### The Error
```
AttributeError: 'psycopg2.extensions.connection' object has no attribute 'execute'
Traceback:
  File "pages/146_immich_photo_manager.py", line 83, in _ensure_tables
    conn.execute(f"""
```

### Root Cause
`conn.execute()` is a **SQLite-only convenience shortcut**. In SQLite (`sqlite3` module),
`connection.execute()` works because SQLite wraps cursor creation internally.

In PostgreSQL (`psycopg2`), **connections do NOT have an `.execute()` method** — only cursors do.
So `conn.execute(...)` raises `AttributeError` immediately on any PostgreSQL environment.

### Why It Passes Dev But Fails Prod
- Dev runs SQLite → `conn.execute()` works fine → no error
- Prod runs PostgreSQL (`USE_POSTGRES=True`, `DATABASE_URL` set) → crashes instantly

### The Fix (Always Use This Pattern)

**❌ NEVER DO THIS:**
```python
conn.execute("CREATE TABLE IF NOT EXISTS ...")
conn.execute("INSERT INTO ...", (val1, val2))
rows = conn.execute("SELECT * FROM ...").fetchall()
```

**✅ ALWAYS DO THIS:**
```python
from utils.db import get_conn, execute as db_exec

db_exec(conn, "CREATE TABLE IF NOT EXISTS ...")
db_exec(conn, "INSERT INTO ...", (val1, val2))
rows = db_exec(conn, "SELECT * FROM ...").fetchall()
```

### The `db_exec` / `execute` Function (from `utils/db.py`)
```python
def execute(conn, query: str, params=None):
    """Portable execute — translates ? to %s for PostgreSQL, returns cursor."""
    if USE_POSTGRES:
        query = query.replace("?", "%s")
    c = conn.cursor()
    if params is not None:
        c.execute(query, params)
    else:
        c.execute(query)
    return c
```
- ✅ Works with **both** SQLite and PostgreSQL
- ✅ Auto-translates `?` placeholders to `%s` for psycopg2
- ✅ Returns the cursor so `.fetchall()`, `.fetchone()`, `.lastrowid` all work

### Import Pattern (Required in Every Page)
```python
from utils.db import get_conn, execute as db_exec, init_db, get_setting, set_setting
```

### Detection Script
To scan for this bug in any page:
```bash
grep -rn "conn\.execute(" pages/ --include="*.py"
```
Any output means the bug exists in that file. Output should be empty.

### Pre-Commit Check (Add to CI)
```bash
# Fail if any page still uses conn.execute() directly
if grep -rn "conn\.execute(" pages/ --include="*.py"; then
    echo "ERROR: conn.execute() found — use db_exec(conn, ...) instead"
    exit 1
fi
```

---

## 🔴 BUG #2 — Missing `conn.commit()` After Writes

### Status: Watch for this pattern

### The Error
Data appears to be saved (no exception thrown) but disappears on page refresh.

### Root Cause
`db_exec()` does NOT auto-commit. Writes (INSERT, UPDATE, DELETE, CREATE TABLE) require
an explicit `conn.commit()` after the execute.

### The Fix
```python
conn = get_conn()
try:
    db_exec(conn, "INSERT INTO ...", (val1, val2))
    conn.commit()
finally:
    conn.close()
```

---

## 🔴 BUG #3 — SQLite Placeholder `?` vs PostgreSQL `%s`

### Status: Handled by `db_exec` — but watch for raw cursor usage

### The Error (PostgreSQL only)
```
TypeError: not all arguments converted during string formatting
# or
ProgrammingError: syntax error at or near "?"
```

### Root Cause
SQLite uses `?` as the parameter placeholder. PostgreSQL (psycopg2) uses `%s`.
If you bypass `db_exec()` and use raw cursor calls, you must handle this yourself.

### The Fix
Always use `db_exec(conn, query, params)` — it auto-translates `?` → `%s` when
`USE_POSTGRES=True`. Never write raw cursor code unless you handle the translation:

```python
# If you MUST use raw cursor (avoid this):
if USE_POSTGRES:
    query = query.replace("?", "%s")
cur = conn.cursor()
cur.execute(query, params)
```

---

## 🔴 BUG #4 — `conn.executescript()` is SQLite-Only

### Status: Active risk — any file with executescript() will break on PostgreSQL

### The Error (PostgreSQL only)
```
AttributeError: 'psycopg2.extensions.connection' object has no attribute 'executescript'
```

### Root Cause
`conn.executescript()` is SQLite-only. It runs multiple SQL statements separated by `;`.
psycopg2 has no equivalent.

### The Fix
Split the script into individual statements and run each with `db_exec()`:
```python
# ❌ NEVER:
conn.executescript("""
    CREATE TABLE a (...);
    CREATE TABLE b (...);
""")

# ✅ ALWAYS (separate db_exec calls, one per statement):
db_exec(conn, "CREATE TABLE IF NOT EXISTS a (...)")
db_exec(conn, "CREATE TABLE IF NOT EXISTS b (...)")
conn.commit()
```

### Detection
```bash
grep -rn "conn\.executescript(" pages/ --include="*.py"
```

---

## 🟡 BUG #5 — `st.experimental_rerun()` Deprecated

### Status: Use `st.rerun()` instead

### The Error
```
AttributeError: module 'streamlit' has no attribute 'experimental_rerun'
# or a deprecation warning that breaks some Streamlit versions
```

### The Fix
```python
# ❌ Old:
st.experimental_rerun()

# ✅ New:
st.rerun()
```

---

## 🟡 BUG #6 — Hardcoded API Keys in Page Files

### Status: Security policy violation — all keys must use get_setting()

### The Fix
```python
# ❌ NEVER:
api_key = "sk-ant-abc123..."

# ✅ ALWAYS:
api_key = get_setting("anthropic_api_key")
if not api_key:
    st.error("Anthropic API key not configured. Go to Settings.")
    st.stop()
```

---

## 🟡 BUG #7 — Row Access by Column Name Fails on PostgreSQL

### Status: Active risk when not using db_exec properly

### The Error
```
TypeError: tuple indices must be integers or slices, not str
```

### Root Cause
- SQLite with `conn.row_factory = sqlite3.Row` returns dict-like rows accessible by column name
- PostgreSQL psycopg2 returns plain tuples by default — `row["column_name"]` fails

### The Fix
Use `psycopg2.extras.RealDictCursor` or access rows by index. Better: use `db_exec`
which works consistently, and then access columns by index or zip with cursor.description:

```python
cur = db_exec(conn, "SELECT id, name, value FROM settings WHERE id = ?", (setting_id,))
row = cur.fetchone()
if row:
    # Access by index (works everywhere):
    setting_id, name, value = row[0], row[1], row[2]
    # OR zip with description for dict access:
    cols = [d[0] for d in cur.description]
    data = dict(zip(cols, row))
```

---

## 📋 PRE-FLIGHT CHECKLIST FOR EVERY NEW PAGE

Before committing any new page, verify:

```bash
# 1. No direct conn.execute() calls
grep -n "conn\.execute(" pages/NEW_PAGE.py  # should return nothing

# 2. No executescript() calls
grep -n "conn\.executescript(" pages/NEW_PAGE.py  # should return nothing

# 3. No hardcoded API keys
grep -n "sk-ant-\|sk-\|Bearer " pages/NEW_PAGE.py  # should return nothing

# 4. Syntax check passes
python3 -m py_compile pages/NEW_PAGE.py && echo "OK"

# 5. db_exec imported
grep "execute as db_exec" pages/NEW_PAGE.py  # should show the import line
```

---

---

## 🔴 BUG #8 — CC Landing Page Hero Text Invisible (`-webkit-text-fill-color` CSS Conflict)

### Status: FIXED (2026-03-22) — collegeconfused.org landing page
### Files Fixed: `/opt/college-confused/app.py`, `/opt/college-confused/cc_global_css.py`

### The Bug
The entire hero section on collegeconfused.org was invisible:
- `.cc-eyebrow` (eyebrow badge) — invisible
- `.cc-h1` (headline "Stop Being Confused") — invisible
- `.cc-hero-sub` (subtitle paragraph) — invisible

### Root Cause — Two Layers

**Layer 1 — Global CSS aggressive override (`cc_global_css.py`)**
```css
/* ❌ THIS WAS THE OLD RULE — REMOVED */
h1, h2, h3, h4, h5, h6, p, li, span, div, label,
.stMarkdown, .stText, [class*="css"] { color: #f0f0ff !important; }
```
Setting `color: #f0f0ff` on `div` and `span` in global CSS doesn't make things visible when
`-webkit-text-fill-color` is also set — because in CSS/WebKit, `-webkit-text-fill-color`
**overrides `color`** entirely. So `color: white` is meaningless if `text-fill-color: transparent`.

**Layer 2 — `inject_cc_css()` in `utils/auth.py` sets all h1 transparent**
```css
/* This runs first, before any page CSS */
h1 {
  background: linear-gradient(90deg, var(--cc-primary), var(--cc-coral)) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;  ← makes ALL h1 invisible
  background-clip: text !important;
}
.cc-hero h1 { /* same — transparent fill for gradient */ }
```
This is correct for CC dashboard pages where h1 IS a gradient. But on the public landing page,
`.cc-h1` sets `color: var(--text-main)` in the master CSS — however, `color` doesn't override
`-webkit-text-fill-color`. The text stayed transparent.

### Why `cc_global_css.py` Fix Alone Wasn't Enough
`cc_global_css.py` is only imported by sub-pages via their `inject_cc_css()` path.
The landing `app.py` does NOT import `cc_global_css.py` — only `inject_cc_css()` from `utils/auth.py`.
So the `cc_global_css.py` fix only helps the dashboard pages, not the landing page.

### The Full Fix

**Fix 1 — `cc_global_css.py`: Remove aggressive universal color rule**
```css
/* ❌ REMOVED: */
h1, h2, h3, h4, h5, h6, p, li, span, div, label,
.stMarkdown, .stText, [class*="css"] { color: #f0f0ff !important; }

/* ✅ REPLACED WITH: target only Streamlit elements, add explicit .cc-* overrides */
.stMarkdown > div, .stText, [data-testid="stMarkdownContainer"] { color: #f0f0ff; }
.cc-eyebrow { color: #C4B8FF !important; -webkit-text-fill-color: #C4B8FF !important; ... }
.cc-h1 { color: #F2F0FF !important; -webkit-text-fill-color: #F2F0FF !important; ... }
.cc-hero-sub { color: #8A84B0 !important; -webkit-text-fill-color: #8A84B0 !important; ... }
```

**Fix 2 — `app.py` master CSS: Add `-webkit-text-fill-color` to all hero classes**
```css
/* ✅ Added to each hero class in the inline master CSS: */
.cc-eyebrow {
  color: var(--violet-light);
  -webkit-text-fill-color: #C4B8FF !important;  /* ← added */
  ...
}
.cc-h1 {
  color: var(--text-main);
  -webkit-text-fill-color: #F2F0FF !important;  /* ← added */
  ...
}
.cc-hero-sub {
  color: var(--text-muted);
  -webkit-text-fill-color: #8A84B0 !important;  /* ← added */
  ...
}
/* .cc-h1 span STAYS transparent for gradient — intentional */
.cc-h1 span {
  background: var(--grad-violet);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;  /* ← keep for gradient */
}
```

### The CSS Rule You Must Know
> **`-webkit-text-fill-color` OVERRIDES `color` in WebKit/Blink browsers.**
> Setting `color: white !important` does NOTHING if `-webkit-text-fill-color: transparent` is active.
> You MUST explicitly set `-webkit-text-fill-color: <visible-color>` to make text visible.

### When This Happens
Any time you have:
1. A global theme CSS that sets `-webkit-text-fill-color` on broad selectors (e.g., `h1`, `p`, `span`)
2. A page-specific CSS that sets `color` on a custom class
3. The global rule runs first → page rule overrides `color` but NOT `text-fill-color`
→ Text is invisible

### Detection
```bash
# Find pages that set color but not -webkit-text-fill-color on the same selector
grep -n "color: var(" /opt/college-confused/app.py | head -20
# Then check if inject_cc_css() sets -webkit-text-fill-color on those same element types
grep -n "webkit-text-fill-color" /opt/college-confused/utils/auth.py
```

### Prevention Rule
**When writing custom `.cc-*` or `.pss-*` CSS classes for elements that `inject_cc_css()`
touches (h1, h2, p, span), ALWAYS set both:**
```css
.your-class {
  color: #FFFFFF;
  -webkit-text-fill-color: #FFFFFF !important;  /* required — overrides global theme */
}
```

---

## 🔍 FULL CODEBASE SCAN COMMANDS

```bash
# Find all conn.execute() bugs
grep -rn "conn\.execute(" pages/ --include="*.py"

# Find all executescript() bugs  
grep -rn "conn\.executescript(" pages/ --include="*.py"

# Find experimental_ APIs
grep -rn "experimental_" pages/ --include="*.py"

# Find hardcoded API keys
grep -rn "sk-ant-\|Bearer [a-zA-Z0-9]" pages/ --include="*.py"
```

---

## 📚 CORRECT DB PATTERNS QUICK REFERENCE

```python
# === STANDARD PAGE TEMPLATE ===
from utils.db import get_conn, execute as db_exec, init_db, get_setting, set_setting

def _ensure_tables():
    conn = get_conn()
    db_exec(conn, """
        CREATE TABLE IF NOT EXISTS my_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def _load_data(user_id: str) -> list:
    conn = get_conn()
    rows = db_exec(conn, "SELECT * FROM my_table WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return rows

def _create_record(user_id: str, value: str):
    conn = get_conn()
    db_exec(conn, "INSERT INTO my_table (user_id, value) VALUES (?, ?)", (user_id, value))
    conn.commit()
    conn.close()

def _delete_record(record_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM my_table WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
```
