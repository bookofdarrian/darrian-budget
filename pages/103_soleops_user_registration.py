"""
SoleOps User Registration & Sign In
Branded signup/login page for getsoleops.com visitors.
Uses the same users table as PSS so get_current_user() works on soleops_app.py.
"""
import streamlit as st

st.set_page_config(
    page_title="SoleOps — Create Your Free Account",
    page_icon="👟",
    layout="wide",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.auth import (
    inject_soleops_css,
    get_current_user,
)

init_db()
inject_soleops_css()

# ── If already logged in, go straight to the dashboard ───────────────────────
user = get_current_user()
if user:
    st.switch_page("soleops_app.py")

# ── Import internal auth helpers (non-public API — import carefully) ─────────
try:
    from utils.auth import (
        create_user,
        authenticate_user,
        validate_email,
        validate_password,
        is_account_locked,
        set_active_db,
    )
    _AUTH_OK = True
except ImportError:
    _AUTH_OK = False


def _ensure_waitlist_table():
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, """
        CREATE TABLE IF NOT EXISTS soleops_waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            source TEXT DEFAULT 'registration_page',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.close()


_ensure_waitlist_table()

# ── Hide sidebar ──────────────────────────────────────────────────────────────
st.html("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
</style>
""")

# ── Page CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
  --cyan: #00D4FF;
  --bg-main: #06080F;
  --bg-card: #0E1022;
  --bg-border: #181C38;
  --text-main: #F0F4FF;
  --text-muted: #7A80A0;
  --grad-text: linear-gradient(135deg, #00D4FF, #B06AFF);
}
body, .stApp { background: var(--bg-main) !important; color: var(--text-main); }
.stApp { background: var(--bg-main) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { max-width: 480px !important; padding: 3rem 1.5rem 5rem !important; margin: 0 auto; }
div[data-testid="stTextInput"] input {
  background: var(--bg-card) !important;
  border: 1px solid var(--bg-border) !important;
  color: var(--text-main) !important;
  border-radius: 8px !important;
}
div[data-testid="stTextInput"] input:focus {
  border-color: var(--cyan) !important;
  box-shadow: 0 0 0 2px rgba(0,212,255,0.15) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #00D4FF, #7B2FBE) !important;
  color: #fff !important;
  border: none !important;
  font-weight: 800 !important;
  border-radius: 10px !important;
  min-height: 48px !important;
}
.stButton > button:not([kind="primary"]) {
  background: transparent !important;
  border: 1px solid var(--bg-border) !important;
  color: var(--text-muted) !important;
  border-radius: 10px !important;
}
div[data-testid="stTabs"] button {
  color: var(--text-muted) !important;
  font-weight: 600;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--cyan) !important;
  border-bottom-color: var(--cyan) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 32px 0 24px 0;">
  <div style="font-size:2.2rem; font-weight:900; background: linear-gradient(135deg,#00D4FF,#B06AFF);
              -webkit-background-clip:text; -webkit-text-fill-color:transparent;
              background-clip:text; letter-spacing:-0.04em; line-height:1.1;">
    👟 SoleOps
  </div>
  <div style="color:#7A80A0; font-size:0.9rem; margin-top:8px;">
    The all-in-one platform for serious sneaker resellers
  </div>
</div>
""", unsafe_allow_html=True)

if not _AUTH_OK:
    st.error("Auth system not available. Check utils/auth.py imports.")
    st.stop()

# ── Tabs: Sign In / Create Account ───────────────────────────────────────────
tab_login, tab_register = st.tabs(["Sign In", "Create Free Account"])

# ── SIGN IN ───────────────────────────────────────────────────────────────────
with tab_login:
    st.markdown("#### Welcome back")
    st.caption("Sign in to access your inventory, P&L, and AI tools.")

    login_email = st.text_input("Email", key="so_login_email",
                                 placeholder="you@email.com", max_chars=254)
    login_pw    = st.text_input("Password", type="password", key="so_login_pw",
                                 placeholder="••••••••", max_chars=128)

    if st.button("Sign In →", type="primary", use_container_width=True, key="so_btn_login"):
        email_clean = (login_email or "").strip().lower()
        if not email_clean or not login_pw:
            st.error("Please enter your email and password.")
        elif not validate_email(email_clean):
            st.error("Please enter a valid email address.")
        else:
            locked, remaining = is_account_locked(email_clean)
            if locked:
                mins = max(1, remaining // 60)
                st.error(f"🔒 Too many failed attempts. Try again in {mins} min.")
            else:
                user_obj = authenticate_user(email_clean, login_pw)
                if user_obj:
                    set_active_db(user_obj.get("email"))
                    st.session_state["user"] = user_obj
                    st.session_state["authenticated"] = True
                    st.success("Signed in! Redirecting to your dashboard…")
                    st.switch_page("soleops_app.py")
                else:
                    st.error("Invalid email or password.")

# ── CREATE ACCOUNT ────────────────────────────────────────────────────────────
with tab_register:
    st.markdown("#### Create your free account")
    st.caption("Free plan: 5 inventory items, manual price lookup, basic P&L. No credit card.")

    reg_email = st.text_input("Email", key="so_reg_email",
                               placeholder="you@email.com", max_chars=254)
    reg_pw    = st.text_input("Password", type="password", key="so_reg_pw",
                               placeholder="8+ chars, letters and numbers", max_chars=128)
    reg_pw2   = st.text_input("Confirm Password", type="password", key="so_reg_pw2",
                               placeholder="Repeat password", max_chars=128)

    if reg_pw:
        ok, msg = validate_password(reg_pw)
        if not ok:
            st.caption(f"⚠️ {msg}")
        else:
            st.caption("✅ Password looks good")

    if st.button("Create Free Account →", type="primary",
                  use_container_width=True, key="so_btn_register"):
        email_clean = (reg_email or "").strip().lower()
        if not email_clean or not reg_pw:
            st.error("Email and password are required.")
        elif not validate_email(email_clean):
            st.error("Please enter a valid email address.")
        else:
            ok, pw_msg = validate_password(reg_pw)
            if not ok:
                st.error(pw_msg)
            elif reg_pw != reg_pw2:
                st.error("Passwords don't match.")
            else:
                user_obj = create_user(email_clean, reg_pw)
                if user_obj:
                    set_active_db(user_obj.get("email"))
                    st.session_state["user"] = user_obj
                    st.session_state["authenticated"] = True
                    # Also save to waitlist
                    try:
                        conn = get_conn()
                        ph = "%s" if USE_POSTGRES else "?"
                        db_exec(conn, f"""
                            INSERT OR IGNORE INTO soleops_waitlist (email, source)
                            VALUES ({ph}, {ph})
                        """, (email_clean, "registration"))
                        conn.close()
                    except Exception:
                        pass
                    st.success("Account created! Welcome to SoleOps 👟")
                    st.switch_page("soleops_app.py")
                else:
                    st.error("An account with that email already exists. Try signing in instead.")

# ── Back link ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; margin-top:24px; color:#7A80A0; font-size:0.8rem;">
  <a href="/" style="color:#00D4FF; text-decoration:none;">← Back to SoleOps</a>
  &nbsp;·&nbsp;
  <span>Your data is encrypted and never shared.</span>
</div>
""", unsafe_allow_html=True)
