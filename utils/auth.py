import os
import streamlit as st
from utils.db import get_setting


def require_password():
    """
    Check APP_PASSWORD env var (or DB setting) and block the page if not authenticated.
    Call this at the top of every page, right after init_db().
    If no password is configured, the gate is skipped entirely.
    """
    app_pw = os.environ.get("APP_PASSWORD", "") or get_setting("app_password", "")
    if not app_pw:
        return  # No password set — open access

    if st.session_state.get("authenticated"):
        return  # Already logged in this session

    # Show login screen
    st.title("🔒 Darrian's Budget Dashboard")
    st.markdown("This app is password protected.")
    pw = st.text_input("Password", type="password", placeholder="Enter password...")
    if st.button("Enter", type="primary", use_container_width=True):
        if pw == app_pw:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Try again.")
    st.stop()
