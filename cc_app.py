"""
College Confused — Standalone Streamlit Entry Point
Port: 8503 | Domain: collegeconfused.org
Run: streamlit run cc_app.py --server.port=8503 --server.address=0.0.0.0
"""

import streamlit as st
from utils.db import init_db
from utils.auth import (
    require_login,
    inject_cc_css,
    render_sidebar_brand,
    render_sidebar_user_widget,
    get_current_user,
)

st.set_page_config(
    page_title="College Confused — AI College Prep",
    page_icon="🎓",
    layout="wide",
)

init_db()
inject_cc_css()
require_login()

# ── Sidebar ──────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("cc_app.py",                       label="🏠 Home",            icon="🏠")
st.sidebar.page_link("pages/80_cc_home.py",             label="🎓 Dashboard",       icon="🎓")
st.sidebar.page_link("pages/81_cc_timeline.py",         label="📅 My Timeline",     icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",     label="💰 Scholarships",    icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",    label="✍️ Essay Station",   icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",        label="📚 SAT/ACT Prep",    icon="📚")
st.sidebar.page_link("pages/87_cc_college_list.py",     label="🏫 College List",    icon="🏫")
st.sidebar.page_link("pages/88_cc_fafsa_guide.py",      label="📋 FAFSA Guide",     icon="📋")
render_sidebar_user_widget()

# ── Main Landing ──────────────────────────────────────────────────────────────
user = get_current_user()
username = user.get("username", "Student") if user else "Student"

st.title("🎓 College Confused")
st.markdown(f"Welcome back, **{username}** — let's get you into college.")
st.markdown("---")

# ── Hero Cards ────────────────────────────────────────────────────────────────
st.subheader("📍 Where are you in your journey?")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 📅 My Timeline")
    st.markdown("Every deadline, every milestone — organized and tracked so nothing slips through the cracks.")
    if st.button("View My Timeline →", key="btn_timeline"):
        st.switch_page("pages/81_cc_timeline.py")

with c2:
    st.markdown("#### 🏫 College List")
    st.markdown("Build and manage your college list. Reach, match, and safety schools with research notes.")
    if st.button("View College List →", key="btn_list"):
        st.switch_page("pages/87_cc_college_list.py")

with c3:
    st.markdown("#### 💰 Scholarships")
    st.markdown("Discover scholarships you actually qualify for. Track applications and deadlines.")
    if st.button("Find Scholarships →", key="btn_scholarships"):
        st.switch_page("pages/82_cc_scholarships.py")

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("#### ✍️ Essay Station")
    st.markdown("AI-powered essay brainstorming, drafting, and review. CommonApp, supplements, and more.")
    if st.button("Open Essay Station →", key="btn_essay"):
        st.switch_page("pages/83_cc_essay_station.py")

with c5:
    st.markdown("#### 📚 SAT/ACT Prep")
    st.markdown("Practice questions, score tracking, and AI study plans tailored to your target scores.")
    if st.button("Start Test Prep →", key="btn_testprep"):
        st.switch_page("pages/84_cc_test_prep.py")

with c6:
    st.markdown("#### 📋 FAFSA Guide")
    st.markdown("Step-by-step FAFSA walkthrough. Know what to gather, what to expect, and when to submit.")
    if st.button("Open FAFSA Guide →", key="btn_fafsa"):
        st.switch_page("pages/88_cc_fafsa_guide.py")

st.markdown("---")

# ── Motivational footer ───────────────────────────────────────────────────────
st.info(
    "💡 **Tip:** Start with your **Timeline** to see all upcoming deadlines, "
    "then visit **Essay Station** to get ahead on your personal statement.",
    icon="🎯",
)
st.caption("College Confused — Free AI-powered college prep for every student | collegeconfused.org")
