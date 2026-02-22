"""
Peach State Savings — Authentication & Authorization

Supports two modes:
  1. MULTI_USER mode (default):
     - Email + password registration/login with bcrypt hashing
     - Brute-force lockout (10 failures → 15-min lockout)
     - Free vs Pro tier gating via Stripe
  2. LEGACY mode (APP_PASSWORD env var set, MULTI_USER=false):
     - Single shared password (backward-compatible for beta testers)

Call require_login() at the top of every page.
Call require_pro() on pages that need a paid subscription.
"""

import os
import math
import streamlit as st
from utils.db import (
    init_db, authenticate_user, create_user, get_user_by_id,
    is_pro_user, get_setting, validate_email, validate_password,
    is_account_locked
)

# ── Brand ─────────────────────────────────────────────────────────────────────
APP_NAME    = "Peach State Savings"
APP_EMOJI   = "🍑"

PEACH       = "#FFAB76"
PEACH_DARK  = "#e8924f"
PEACH_GLOW  = "#3d2010"
BG_MAIN     = "#0e1117"
BG_CARD     = "#12151c"
BG_BORDER   = "#1e2330"
TEXT_MUTED  = "#8892a4"
TEXT_MAIN   = "#fafafa"

GLOBAL_CSS = f"""
<style>
/* ── Peach State Savings global styles ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {BG_MAIN} 0%, #12151c 100%);
    border-right: 1px solid {BG_BORDER};
}}
[data-testid="stSidebar"] .stMarkdown p {{
    color: {TEXT_MUTED};
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.brand-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 12px 0;
    border-bottom: 1px solid {BG_BORDER};
    margin-bottom: 8px;
}}
.brand-name {{
    font-size: 1.15rem;
    font-weight: 700;
    color: {PEACH};
    letter-spacing: -0.02em;
    line-height: 1.2;
}}
.brand-tagline {{
    font-size: 0.68rem;
    color: {TEXT_MUTED};
    margin-top: -1px;
}}
.pro-badge {{
    display: inline-block;
    background: linear-gradient(135deg, {PEACH}, {PEACH_DARK});
    color: #000;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    vertical-align: middle;
    margin-left: 6px;
}}
.free-badge {{
    display: inline-block;
    background: {BG_BORDER};
    color: {TEXT_MUTED};
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    vertical-align: middle;
    margin-left: 6px;
}}
[data-testid="metric-container"] {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 10px;
    padding: 14px 18px;
}}
.paywall-card {{
    background: linear-gradient(135deg, {PEACH_GLOW} 0%, {BG_CARD} 100%);
    border: 1px solid {PEACH};
    border-radius: 14px;
    padding: 32px;
    text-align: center;
    margin: 24px 0;
}}
.paywall-card h2 {{ color: {PEACH}; margin-bottom: 8px; }}
.paywall-card p  {{ color: {TEXT_MUTED}; margin-bottom: 20px; }}
.price-card {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 14px;
    padding: 28px;
    height: 100%;
}}
.price-card.featured {{
    border-color: {PEACH};
    background: linear-gradient(135deg, {PEACH_GLOW} 0%, {BG_CARD} 100%);
}}
.price-amount {{
    font-size: 2.5rem;
    font-weight: 800;
    color: {TEXT_MAIN};
    line-height: 1;
}}
.price-period {{ color: {TEXT_MUTED}; font-size: 0.85rem; }}
.feature-list {{ list-style: none; padding: 0; margin: 16px 0; }}
.feature-list li {{ padding: 5px 0; color: #c8d0dc; font-size: 0.9rem; }}
.feature-list li::before {{ content: "✓ "; color: {PEACH}; font-weight: 700; }}
.feature-list li.locked {{ color: {TEXT_MUTED}; }}
.feature-list li.locked::before {{ content: "🔒 "; }}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {PEACH}, {PEACH_DARK}) !important;
    color: #000 !important;
    border: none !important;
    font-weight: 700 !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: {PEACH_DARK} !important;
    color: #000 !important;
}}
</style>
"""


def inject_css():
    """Inject global CSS once per session."""
    if not st.session_state.get("_css_injected"):
        st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
        st.session_state["_css_injected"] = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_lockout(seconds: int) -> str:
    mins = math.ceil(seconds / 60)
    return f"{mins} minute{'s' if mins != 1 else ''}"


# ── Auth pages ────────────────────────────────────────────────────────────────

def _legacy_password_check():
    """Single-password gate for beta / personal use."""
    app_pw = os.environ.get("APP_PASSWORD", "") or get_setting("app_password", "")
    if not app_pw:
        return
    if st.session_state.get("authenticated"):
        return

    inject_css()
    st.markdown(f"""
    <div style="text-align:center; padding:60px 0 24px 0;">
        <div style="font-size:2.4rem; font-weight:800; color:{PEACH}; letter-spacing:-0.03em;">
            {APP_EMOJI} {APP_NAME}
        </div>
        <div style="color:{TEXT_MUTED}; font-size:0.9rem; margin-top:6px;">
            Your personal finance dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pw = st.text_input("Password", type="password", placeholder="Enter password...")
        if st.button("Enter", type="primary", use_container_width=True):
            if pw == app_pw:
                st.session_state["authenticated"] = True
                st.session_state["user"] = {
                    "email": "owner", "plan": "pro",
                    "subscription_status": "active", "id": 0
                }
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()


def _show_auth_page():
    """Full register/login UI with security hardening."""
    inject_css()

    st.markdown(f"""
    <div style="text-align:center; padding: 48px 0 24px 0;">
        <div style="font-size:2.4rem; font-weight:800; color:{PEACH}; letter-spacing:-0.03em;">
            {APP_EMOJI} {APP_NAME}
        </div>
        <div style="color:{TEXT_MUTED}; font-size:0.95rem; margin-top:8px;">
            AI-powered personal finance — built different
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── Sign In ───────────────────────────────────────────────────────────
        with tab_login:
            st.markdown("#### Welcome back")
            email    = st.text_input("Email", key="login_email",
                                     placeholder="you@email.com",
                                     max_chars=254)
            password = st.text_input("Password", type="password", key="login_pw",
                                     placeholder="••••••••",
                                     max_chars=128)

            if st.button("Sign In", type="primary", use_container_width=True,
                         key="btn_login"):
                email_clean = (email or "").strip().lower()

                # Input validation
                if not email_clean or not password:
                    st.error("Please enter your email and password.")
                elif not validate_email(email_clean):
                    st.error("Please enter a valid email address.")
                else:
                    # Check lockout BEFORE hitting the DB
                    locked, remaining = is_account_locked(email_clean)
                    if locked:
                        st.error(
                            f"🔒 Too many failed attempts. "
                            f"Please wait {_fmt_lockout(remaining)} before trying again."
                        )
                    else:
                        user = authenticate_user(email_clean, password)
                        if user:
                            st.session_state["user"] = user
                            st.session_state["authenticated"] = True
                            st.rerun()
                        else:
                            # Check again after the failed attempt to show updated count
                            locked2, remaining2 = is_account_locked(email_clean)
                            if locked2:
                                st.error(
                                    f"🔒 Account temporarily locked after too many failed attempts. "
                                    f"Try again in {_fmt_lockout(remaining2)}."
                                )
                            else:
                                st.error("Invalid email or password.")

        # ── Register ──────────────────────────────────────────────────────────
        with tab_register:
            st.markdown("#### Create your free account")
            st.caption(
                "Free plan: budgeting, expenses, income tracking, bank import. "
                "No credit card required."
            )
            reg_email = st.text_input("Email", key="reg_email",
                                      placeholder="you@email.com",
                                      max_chars=254)
            reg_pw    = st.text_input("Password", type="password", key="reg_pw",
                                      placeholder="8+ chars, letters and numbers",
                                      max_chars=128)
            reg_pw2   = st.text_input("Confirm Password", type="password",
                                      key="reg_pw2",
                                      placeholder="Repeat password",
                                      max_chars=128)

            # Live password strength hint
            if reg_pw:
                ok, msg = validate_password(reg_pw)
                if not ok:
                    st.caption(f"⚠️ {msg}")
                else:
                    st.caption("✅ Password looks good")

            if st.button("Create Account", type="primary",
                         use_container_width=True, key="btn_register"):
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
                        user = create_user(email_clean, reg_pw)
                        if user:
                            st.session_state["user"] = user
                            st.session_state["authenticated"] = True
                            st.success(f"Account created! Welcome to {APP_NAME} {APP_EMOJI}")
                            st.rerun()
                        else:
                            st.error(
                                "An account with that email already exists. "
                                "Try signing in instead."
                            )

        st.markdown(
            f"<div style='text-align:center; margin-top:20px; color:{TEXT_MUTED}; "
            f"font-size:0.75rem;'>"
            "Your financial data is encrypted and never shared.</div>",
            unsafe_allow_html=True
        )

    st.stop()


# ── Public API ────────────────────────────────────────────────────────────────

def require_login():
    """
    Gate: user must be logged in to proceed.
    Handles both legacy (APP_PASSWORD) and multi-user modes.
    Always call this at the top of every page after set_page_config.
    """
    inject_css()
    init_db()

    app_pw     = os.environ.get("APP_PASSWORD", "") or get_setting("app_password", "")
    multi_user = os.environ.get("MULTI_USER", "true").lower() not in ("false", "0", "no")

    if app_pw and not multi_user:
        _legacy_password_check()
        return

    if st.session_state.get("authenticated") and st.session_state.get("user"):
        user = st.session_state["user"]
        # Refresh from DB every page load to pick up subscription changes
        if user.get("id", 0) != 0:
            fresh = get_user_by_id(user["id"])
            if fresh:
                # Strip sensitive fields just in case
                fresh.pop("password_hash", None)
                fresh.pop("salt", None)
                st.session_state["user"] = fresh
        return

    _show_auth_page()


def require_password():
    """Alias for require_login() — keeps old page imports working."""
    require_login()


def get_current_user() -> dict | None:
    """Return the currently logged-in user dict, or None."""
    return st.session_state.get("user")


def current_user_is_pro() -> bool:
    """Return True if the current session user has an active Pro plan."""
    return is_pro_user(get_current_user())


def require_pro(feature_name: str = "this feature"):
    """
    Gate: show a paywall if the user is not on Pro.
    Call after require_login(). Stops page execution if not Pro.
    """
    if current_user_is_pro():
        return

    inject_css()
    user  = get_current_user()
    email = user.get("email", "") if user else ""

    st.markdown(f"""
    <div class="paywall-card">
        <h2>🔒 Pro Feature</h2>
        <p>
            <strong>{feature_name}</strong> is available on the
            <strong>{APP_NAME} Pro</strong> plan.<br>
            Upgrade for $9/month to unlock AI insights, trends analysis,
            and net worth tracking.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Upgrade to Pro — $9/month", type="primary",
                     use_container_width=True, key="paywall_upgrade_btn"):
            from utils.stripe_utils import create_checkout_session, STRIPE_ENABLED
            if STRIPE_ENABLED and user and user.get("id", 0) != 0:
                url = create_checkout_session(email, user["id"])
                if url:
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url={url}">',
                        unsafe_allow_html=True
                    )
                    st.markdown(f"[Click here if not redirected]({url})")
                else:
                    st.error("Could not create checkout session. Please try again.")
            else:
                st.switch_page("pages/0_pricing.py")

        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.8rem; margin-top:8px;'>"
            "Cancel anytime · Secure payment via Stripe</div>",
            unsafe_allow_html=True
        )

    st.stop()


def render_sidebar_brand():
    """Render the Peach State Savings brand header in the sidebar."""
    inject_css()
    st.sidebar.markdown(f"""
    <div class="brand-header">
        <div>
            <div class="brand-name">{APP_EMOJI} {APP_NAME}</div>
            <div class="brand-tagline">AI-powered budgeting</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_user_widget():
    """
    Render the user account widget at the bottom of the sidebar.
    Shows email, plan badge, upgrade button, and logout.
    """
    user = get_current_user()
    if not user:
        return

    email = user.get("email", "")
    pro   = is_pro_user(user)
    badge = (f'<span class="pro-badge">PRO</span>'
             if pro else f'<span class="free-badge">FREE</span>')

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<div style='font-size:0.78rem; color:{TEXT_MUTED};'>Signed in as</div>"
        f"<div style='font-size:0.82rem; color:{TEXT_MAIN}; font-weight:600; "
        f"word-break:break-all;'>{email} {badge}</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if not pro:
            if st.button("⬆️ Upgrade", use_container_width=True,
                         key="sidebar_upgrade"):
                st.switch_page("pages/0_pricing.py")
    with col2:
        if st.button("Sign Out", use_container_width=True, key="sidebar_logout"):
            for key in ["user", "authenticated", "api_key",
                        "inv_loaded_from_db", "_css_injected"]:
                st.session_state.pop(key, None)
            st.rerun()
