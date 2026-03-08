"""
Sandbox / Privacy Mode — Page 73
Peach State Savings

Allows specific users (granted by admin) to run the app in a fully
isolated mode where all their data lives in a per-user SQLite file
on the server — completely separate from the shared production DB.

Key properties:
  • Each sandbox user gets data/sandbox_{user_id}.db (SQLite only)
  • Production DB only stores sandbox grants + metadata (no financial data)
  • Users can download their sandbox DB file at any time
  • Auto-expires after SANDBOX_TTL_DAYS days of inactivity
  • Admin can view all sandboxes, their sizes, last activity, and wipe them
  • Works even when USE_POSTGRES=True (sandbox DBs are always SQLite)
"""

import os
import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.auth import (
    require_login,
    render_sidebar_brand,
    render_sidebar_user_widget,
    inject_css,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🔒 Sandbox Mode — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
st.sidebar.page_link("pages/73_sandbox_mode.py",        label="🔒 Sandbox Mode",   icon="🔒")
render_sidebar_user_widget()

# ── Constants ─────────────────────────────────────────────────────────────────
SANDBOX_TTL_DAYS: int = 7          # inactive sandbox auto-expires after this many days
DATA_DIR: Path = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SANDBOX_TABLES: list[str] = [
    "expenses", "income", "goals", "investments",
    "bills", "net_worth", "pa_tasks", "todo_brain_dumps",
]


# ══════════════════════════════════════════════════════════════════════════════
# ── DB helpers (production DB — grants/metadata only) ────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_tables() -> None:
    """Create sandbox metadata tables in the production DB."""
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS sandbox_grants (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                granted_by TEXT NOT NULL,
                granted_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                expires_at TEXT,
                last_accessed TEXT,
                db_size_bytes INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                active BOOLEAN DEFAULT TRUE
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS sandbox_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                granted_by TEXT NOT NULL,
                granted_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT,
                last_accessed TEXT,
                db_size_bytes INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                active INTEGER DEFAULT 1
            )
        """)
    conn.close()


def _get_grant(username: str) -> dict | None:
    """Return the sandbox grant row for a username, or None."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    row = conn.execute(
        f"SELECT * FROM sandbox_grants WHERE username = {ph} AND active = {1 if not USE_POSTGRES else 'TRUE'}",
        (username,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def _list_grants() -> list[dict]:
    """Return all active sandbox grants."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM sandbox_grants ORDER BY granted_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _grant_sandbox(username: str, granted_by: str, notes: str = "") -> None:
    """Grant sandbox access to a user."""
    conn = get_conn()
    expires = (datetime.now() + timedelta(days=SANDBOX_TTL_DAYS * 10)).strftime("%Y-%m-%d")
    ph = "%s" if USE_POSTGRES else "?"
    if USE_POSTGRES:
        db_exec(conn, f"""
            INSERT INTO sandbox_grants (username, granted_by, expires_at, notes, active)
            VALUES ({ph}, {ph}, {ph}, {ph}, TRUE)
            ON CONFLICT (username) DO UPDATE SET active = TRUE, granted_by = EXCLUDED.granted_by,
            notes = EXCLUDED.notes, expires_at = EXCLUDED.expires_at
        """, (username, granted_by, expires, notes))
    else:
        db_exec(conn, f"""
            INSERT OR REPLACE INTO sandbox_grants (username, granted_by, expires_at, notes, active)
            VALUES ({ph}, {ph}, {ph}, {ph}, 1)
        """, (username, granted_by, expires, notes))
    conn.commit()
    conn.close()


def _revoke_sandbox(username: str) -> None:
    """Revoke sandbox access."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"UPDATE sandbox_grants SET active = {0 if not USE_POSTGRES else 'FALSE'} WHERE username = {ph}", (username,))
    conn.commit()
    conn.close()


def _update_last_accessed(username: str) -> None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_exec(conn, f"UPDATE sandbox_grants SET last_accessed = {ph} WHERE username = {ph}", (now, username))
    conn.commit()
    conn.close()


def _update_db_size(username: str) -> None:
    db_path = _sandbox_db_path(username)
    size = db_path.stat().st_size if db_path.exists() else 0
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"UPDATE sandbox_grants SET db_size_bytes = {ph} WHERE username = {ph}", (size, username))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ── Sandbox SQLite DB helpers (per-user isolated DB) ─────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _sandbox_db_path(username: str) -> Path:
    safe = "".join(c for c in username if c.isalnum() or c in "-_")
    return DATA_DIR / f"sandbox_{safe}.db"


def _get_sandbox_conn(username: str) -> sqlite3.Connection:
    """Return a connection to this user's isolated sandbox SQLite DB."""
    path = _sandbox_db_path(username)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_sandbox_db(username: str) -> None:
    """Create all the standard tables in the user's sandbox DB."""
    conn = _get_sandbox_conn(username)
    # Expenses
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, category TEXT, description TEXT,
            amount REAL DEFAULT 0.0, user_id INTEGER DEFAULT 1
        )
    """)
    # Income
    conn.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, source TEXT, description TEXT,
            amount REAL DEFAULT 0.0, user_id INTEGER DEFAULT 1
        )
    """)
    # Goals
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, target_amount REAL DEFAULT 0.0,
            current_amount REAL DEFAULT 0.0, deadline TEXT,
            status TEXT DEFAULT 'active', user_id INTEGER DEFAULT 1
        )
    """)
    # Net worth snapshots
    conn.execute("""
        CREATE TABLE IF NOT EXISTS net_worth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT, assets REAL DEFAULT 0.0,
            liabilities REAL DEFAULT 0.0,
            net_worth REAL GENERATED ALWAYS AS (assets - liabilities) STORED,
            user_id INTEGER DEFAULT 1
        )
    """)
    # Bills
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, amount REAL DEFAULT 0.0,
            due_day INTEGER DEFAULT 1, category TEXT DEFAULT '',
            status TEXT DEFAULT 'active', user_id INTEGER DEFAULT 1
        )
    """)
    # Todo tasks
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pa_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT, priority TEXT DEFAULT 'normal',
            notes TEXT DEFAULT '', status TEXT DEFAULT 'open',
            source TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        )
    """)
    # Sandbox-specific: sandbox_meta
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sandbox_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO sandbox_meta (key, value) VALUES ('created_at', ?)",
        (datetime.now().isoformat(),),
    )
    conn.commit()
    conn.close()


def _sandbox_summary(username: str) -> dict:
    """Return row counts for all sandbox tables."""
    conn = _get_sandbox_conn(username)
    result: dict = {}
    for tbl in SANDBOX_TABLES:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            result[tbl] = n
        except Exception:
            result[tbl] = 0
    conn.close()
    return result


def _export_sandbox_as_json(username: str) -> str:
    """Export all sandbox data as a pretty JSON string."""
    conn = _get_sandbox_conn(username)
    export: dict = {"exported_at": datetime.now().isoformat(), "tables": {}}
    for tbl in SANDBOX_TABLES:
        try:
            rows = conn.execute(f"SELECT * FROM {tbl}").fetchall()
            export["tables"][tbl] = [dict(r) for r in rows]
        except Exception:
            export["tables"][tbl] = []
    conn.close()
    return json.dumps(export, indent=2, default=str)


def _wipe_sandbox_db(username: str) -> None:
    """Delete the user's sandbox SQLite file."""
    path = _sandbox_db_path(username)
    if path.exists():
        path.unlink()


def _expire_old_sandboxes() -> list[str]:
    """
    Check all grants for inactivity. If a user hasn't accessed their sandbox
    in SANDBOX_TTL_DAYS, wipe the DB file and mark the grant expired.
    Returns list of expired usernames.
    """
    grants = _list_grants()
    expired: list[str] = []
    cutoff = datetime.now() - timedelta(days=SANDBOX_TTL_DAYS)
    for g in grants:
        last = g.get("last_accessed")
        if last:
            try:
                last_dt = datetime.strptime(last[:19], "%Y-%m-%d %H:%M:%S")
                if last_dt < cutoff:
                    _wipe_sandbox_db(g["username"])
                    _revoke_sandbox(g["username"])
                    expired.append(g["username"])
            except Exception:
                pass
    return expired


# ══════════════════════════════════════════════════════════════════════════════
# ── UI helpers ────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    elif n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.2f} MB"


def _is_admin() -> bool:
    user = st.session_state.get("username", "")
    return user == get_setting("admin_username", "darrian")


# ══════════════════════════════════════════════════════════════════════════════
# ── Main UI ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

_ensure_tables()

username: str = st.session_state.get("username", "")
is_admin: bool = _is_admin()

st.title("🔒 Sandbox / Privacy Mode")
st.caption("Test the full app with your data — without storing anything on the shared server.")

# Expire stale sandboxes silently in background
_expire_old_sandboxes()

# ── Tab routing ───────────────────────────────────────────────────────────────
if is_admin:
    tabs = st.tabs(["🧑 My Sandbox", "🛠️ Admin — Manage Sandboxes", "ℹ️ How It Works"])
    tab_mine, tab_admin, tab_info = tabs
else:
    tabs = st.tabs(["🧑 My Sandbox", "ℹ️ How It Works"])
    tab_mine, tab_info = tabs
    tab_admin = None  # type: ignore[assignment]

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — My Sandbox
# ─────────────────────────────────────────────────────────────────────────────
with tab_mine:
    grant = _get_grant(username)

    if grant is None:
        st.info("🔒 You don't have sandbox access yet. Ask the admin to grant it.", icon="🔒")
        st.markdown("""
        **What is Sandbox Mode?**
        - Your financial data stays in an isolated database just for you
        - It is completely separate from the shared production database
        - You can delete all your data with one click at any time
        - Data auto-expires after **{} days of inactivity**
        - You can export everything as JSON before it expires
        """.format(SANDBOX_TTL_DAYS))
    else:
        _update_last_accessed(username)
        _init_sandbox_db(username)
        _update_db_size(username)
        grant = _get_grant(username)  # refresh after size update

        db_path = _sandbox_db_path(username)
        size_str = _fmt_bytes(grant.get("db_size_bytes", 0))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Status", "🟢 Active")
        col2.metric("DB Size", size_str)
        col3.metric("Granted By", grant.get("granted_by", "—"))
        col4.metric("Expires", grant.get("expires_at", "—")[:10] if grant.get("expires_at") else "—")

        st.success(
            f"✅ Your sandbox is active. All data entered here is stored in "
            f"`data/sandbox_{username}.db` — **not** in the shared database.",
            icon="🔒",
        )
        st.markdown("---")

        # ── Summary ──────────────────────────────────────────────────────────
        st.subheader("📊 Your Sandbox Data Summary")
        summary = _sandbox_summary(username)
        s_cols = st.columns(len(SANDBOX_TABLES))
        for i, tbl in enumerate(SANDBOX_TABLES):
            s_cols[i].metric(tbl.replace("_", " ").title(), summary[tbl])

        st.markdown("---")

        # ── Actions ──────────────────────────────────────────────────────────
        st.subheader("⚙️ Actions")
        act1, act2, act3 = st.columns(3)

        with act1:
            st.markdown("**📥 Export Your Data**")
            st.caption("Download everything as JSON before it expires.")
            if st.button("⬇️ Export as JSON", use_container_width=True, key="sb_export"):
                json_str = _export_sandbox_as_json(username)
                st.download_button(
                    label="💾 Download sandbox_export.json",
                    data=json_str,
                    file_name=f"sandbox_{username}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="sb_export_dl",
                )

        with act2:
            st.markdown("**📂 Download Raw SQLite DB**")
            st.caption("Take a full copy of your SQLite database file.")
            if db_path.exists() and st.button("⬇️ Download .db File", use_container_width=True, key="sb_dl_db"):
                with open(db_path, "rb") as f:
                    st.download_button(
                        label=f"💾 sandbox_{username}.db",
                        data=f.read(),
                        file_name=f"sandbox_{username}.db",
                        mime="application/octet-stream",
                        use_container_width=True,
                        key="sb_db_dl",
                    )

        with act3:
            st.markdown("**🗑️ Wipe My Sandbox**")
            st.caption("Permanently delete all your sandbox data right now.")
            confirm = st.checkbox("I understand this is irreversible", key="sb_wipe_confirm")
            if confirm and st.button("🗑️ Delete My Sandbox Data", use_container_width=True, type="primary", key="sb_wipe"):
                _wipe_sandbox_db(username)
                _revoke_sandbox(username)
                st.success("✅ Your sandbox data has been permanently deleted.")
                st.rerun()

        st.markdown("---")
        st.markdown("""
        **Privacy Guarantees:**
        - 🗄️ Your data lives in `data/sandbox_{}.db` — never touches the shared DB
        - 🔒 Only you and the admin can access this file
        - ⏰ Auto-wipes after **{} days** of inactivity
        - 📥 Export at any time before expiry
        - 🗑️ Delete instantly with the button above
        """.format(username, SANDBOX_TTL_DAYS))


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Admin Panel
# ─────────────────────────────────────────────────────────────────────────────
if tab_admin is not None:
    with tab_admin:
        if not is_admin:
            st.error("🔒 Admin access required.")
        else:
            st.subheader("🛠️ Sandbox Grant Management")

            # ── Grant new access ──────────────────────────────────────────────
            with st.expander("➕ Grant Sandbox Access to a User", expanded=False):
                g1, g2, g3 = st.columns([2, 2, 3])
                new_user = g1.text_input("Username", placeholder="darrian", key="adm_new_user")
                new_notes = g3.text_area("Notes (optional)", height=70, key="adm_notes")
                if g2.button("✅ Grant Access", key="adm_grant", use_container_width=True):
                    if new_user.strip():
                        _grant_sandbox(new_user.strip(), username, new_notes.strip())
                        _init_sandbox_db(new_user.strip())
                        st.success(f"✅ Sandbox access granted to **{new_user.strip()}**")
                        st.rerun()
                    else:
                        st.error("Username is required.")

            st.markdown("---")

            # ── Current grants table ──────────────────────────────────────────
            grants = _list_grants()
            if not grants:
                st.info("No sandbox grants yet.")
            else:
                st.markdown(f"**{len(grants)} sandbox account(s)**")
                for g in grants:
                    uname = g["username"]
                    db_path = _sandbox_db_path(uname)
                    size_bytes = db_path.stat().st_size if db_path.exists() else 0
                    active_badge = "🟢 Active" if g.get("active") else "🔴 Revoked"

                    with st.container():
                        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 2, 1, 1])
                        c1.markdown(f"**{uname}** — {active_badge}")
                        c2.metric("Size", _fmt_bytes(size_bytes))
                        c3.metric("Granted By", g.get("granted_by", "—"))
                        c4.metric("Last Access", (g.get("last_accessed") or "Never")[:10])
                        if c5.button("🗑️ Wipe DB", key=f"adm_wipe_{uname}", use_container_width=True):
                            _wipe_sandbox_db(uname)
                            st.success(f"Wiped sandbox DB for {uname}")
                            st.rerun()
                        if g.get("active"):
                            if c6.button("❌ Revoke", key=f"adm_revoke_{uname}", use_container_width=True):
                                _revoke_sandbox(uname)
                                st.success(f"Revoked access for {uname}")
                                st.rerun()
                        else:
                            if c6.button("✅ Re-grant", key=f"adm_regrant_{uname}", use_container_width=True):
                                _grant_sandbox(uname, username)
                                st.rerun()
                        st.divider()

            st.markdown("---")
            # ── Expire stale sandboxes button ─────────────────────────────────
            if st.button("🧹 Run Expiration Cleanup Now", key="adm_expire"):
                expired = _expire_old_sandboxes()
                if expired:
                    st.success(f"Expired and wiped: {', '.join(expired)}")
                else:
                    st.info("No stale sandboxes to expire.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — How It Works
# ─────────────────────────────────────────────────────────────────────────────
with tab_info:
    st.subheader("ℹ️ How Sandbox Mode Works")
    st.markdown(f"""
    ### The Privacy Problem
    When you try out a personal finance app, you're being asked to trust a stranger
    with your most sensitive data — bank accounts, income, spending, net worth.
    That's a real barrier.

    ### Our Solution: Per-User Isolated SQLite
    Instead of storing your trial data in our shared production database,
    Sandbox Mode gives every approved user their **own isolated SQLite file**:

    ```
    data/
    ├── budget.db          ← shared production DB (no sandbox data here)
    ├── sandbox_alice.db   ← Alice's completely private data
    └── sandbox_bob.db     ← Bob's completely private data
    ```

    ### Guarantees
    | Property | Detail |
    |---|---|
    | **Isolation** | Your data never touches the shared DB |
    | **Self-service deletion** | Wipe your DB instantly from the UI |
    | **Auto-expiry** | Idle sandboxes auto-delete after **{SANDBOX_TTL_DAYS} days** |
    | **Export first** | Download as JSON or raw `.db` before deletion |
    | **Admin visibility** | Admin can see sandbox sizes/activity but not your data content |

    ### Better Alternatives (Future Work)
    | Option | Privacy Level | Complexity |
    |---|---|---|
    | Current: per-user SQLite on server | ⭐⭐⭐ High | Low |
    | Self-hosted Docker (your own machine) | ⭐⭐⭐⭐⭐ Max | Medium |
    | Browser-local via Pyodide (no server) | ⭐⭐⭐⭐⭐ Max | Very High |

    For now, the per-user SQLite approach is the best balance of privacy and
    simplicity. The self-hosted Docker option is documented in `Dockerfile`.

    ### Getting Access
    Contact the admin (`{get_setting("admin_username", "darrian")}`) to be added to the sandbox allowlist.
    """)
