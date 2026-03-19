"""
College Confused — Standalone Streamlit Entry Point
Port: 8503 | Domain: collegeconfused.org
Run: streamlit run cc_app.py --server.port=8503 --server.address=0.0.0.0

Public landing page shown to unauthenticated visitors (Googlebot-indexable).
Authenticated users see the full dashboard.
"""

import streamlit as st
from utils.db import init_db
from utils.auth import (
    inject_cc_css,
    render_sidebar_brand,
    render_sidebar_user_widget,
    get_current_user,
)

st.set_page_config(
    page_title="College Confused — Free AI College Prep for Every Student",
    page_icon="🎓",
    layout="wide",
)

init_db()
inject_cc_css()

user = get_current_user()

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC LANDING PAGE — shown to unauthenticated visitors + Googlebot
# ═══════════════════════════════════════════════════════════════════════════════
if not user:

    # Hide sidebar completely for the public landing page
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    .block-container { padding-top: 2rem; max-width: 960px; margin: 0 auto; }

    .cc-hero {
        background: linear-gradient(135deg, #12102A 0%, #1E1A4A 60%, #2A1F6A 100%);
        border-radius: 16px;
        padding: 4rem 3rem;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #3D35A0;
    }
    .cc-hero h1 {
        font-size: 3rem;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: 1rem;
        line-height: 1.2;
    }
    .cc-hero p {
        font-size: 1.25rem;
        color: #C4B8FF;
        max-width: 600px;
        margin: 0 auto 2rem;
        line-height: 1.6;
    }
    .cc-badge {
        display: inline-block;
        background: #2A1F6A;
        border: 1px solid #9B8EFF;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.85rem;
        color: #9B8EFF;
        margin-bottom: 1.5rem;
        letter-spacing: 0.5px;
    }

    .feature-card {
        background: #1A1738;
        border: 1px solid #2E2860;
        border-radius: 12px;
        padding: 1.5rem;
        height: 100%;
        transition: border-color 0.2s;
    }
    .feature-card:hover { border-color: #9B8EFF; }
    .feature-card h3 { color: #FFFFFF; font-size: 1.1rem; margin-bottom: 0.5rem; }
    .feature-card p { color: #A89FD0; font-size: 0.95rem; line-height: 1.5; margin: 0; }

    .stat-row {
        background: #12102A;
        border: 1px solid #2E2860;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        text-align: center;
    }
    .stat-num { font-size: 2rem; font-weight: 800; color: #9B8EFF; }
    .stat-label { font-size: 0.9rem; color: #A89FD0; }

    .cc-quote {
        background: #1A1738;
        border-left: 4px solid #9B8EFF;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        margin: 0.5rem 0;
    }
    .cc-quote p { color: #C4B8FF; font-style: italic; margin: 0 0 0.5rem 0; }
    .cc-quote span { color: #7B6FBF; font-size: 0.85rem; }

    .footer-bar {
        text-align: center;
        padding: 2rem 0 1rem;
        color: #5A5080;
        font-size: 0.85rem;
        border-top: 1px solid #2E2860;
        margin-top: 3rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero Section ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="cc-hero">
        <div class="cc-badge">🆓 100% Free — No Credit Card Required</div>
        <h1>Stop Being Confused.<br>Start Getting In.</h1>
        <p>College Confused is the AI-powered college prep platform built for students who want
        real guidance — not generic advice. Track deadlines, find scholarships, write better essays,
        and build your college list — all in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── CTA Buttons ───────────────────────────────────────────────────────────
    cta1, cta2, cta3 = st.columns([2, 1, 2])
    with cta2:
        if st.button("🎓 Get Started Free", type="primary", use_container_width=True):
            st.switch_page("app.py")
    st.markdown("<div style='text-align:center; color:#7B6FBF; font-size:0.85rem; margin-top:-0.5rem;'>Already have an account? <a href='#' style='color:#9B8EFF;'>Sign in</a></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Stats Bar ─────────────────────────────────────────────────────────────
    st.subheader("Built for the college application journey")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown('<div class="stat-row"><div class="stat-num">7</div><div class="stat-label">AI-powered tools</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown('<div class="stat-row"><div class="stat-num">100%</div><div class="stat-label">Free forever</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown('<div class="stat-row"><div class="stat-num">∞</div><div class="stat-label">Essay drafts</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown('<div class="stat-row"><div class="stat-num">24/7</div><div class="stat-label">AI guidance</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Features Grid ─────────────────────────────────────────────────────────
    st.subheader("Everything you need. Nothing you don't.")

    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("""
        <div class="feature-card">
            <h3>📅 Application Timeline</h3>
            <p>Every deadline — Common App, Early Decision, FAFSA, scholarships — tracked in one dashboard.
            Get reminded before things are due, not after.</p>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="feature-card">
            <h3>💰 Scholarship Finder</h3>
            <p>Discover scholarships you actually qualify for based on your GPA, major, state, and background.
            Track applications and deadlines in one place.</p>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="feature-card">
            <h3>✍️ AI Essay Station</h3>
            <p>Claude AI helps you brainstorm, draft, and polish your Common App personal statement and
            school-specific supplements. Your story, told better.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    f4, f5, f6 = st.columns(3)
    with f4:
        st.markdown("""
        <div class="feature-card">
            <h3>🏫 College List Builder</h3>
            <p>Build a balanced list of reach, match, and safety schools. Research notes, admission stats,
            and financial aid data all in one place.</p>
        </div>
        """, unsafe_allow_html=True)
    with f5:
        st.markdown("""
        <div class="feature-card">
            <h3>📚 SAT/ACT Prep</h3>
            <p>Practice questions, score tracking, and AI-generated study plans built around your target
            schools' score ranges. Study smarter, not harder.</p>
        </div>
        """, unsafe_allow_html=True)
    with f6:
        st.markdown("""
        <div class="feature-card">
            <h3>📋 FAFSA Guide</h3>
            <p>Step-by-step walkthrough of the Free Application for Federal Student Aid. Know exactly
            what you need, when to submit, and what to expect.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Testimonials ──────────────────────────────────────────────────────────
    st.subheader("What students say")

    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown("""
        <div class="cc-quote">
            <p>"I was so lost with the Common App until I found College Confused.
            The timeline feature alone saved me from missing 3 deadlines."</p>
            <span>— Aaliyah T., accepted to Georgia Tech 🎉</span>
        </div>
        """, unsafe_allow_html=True)
    with t2:
        st.markdown("""
        <div class="cc-quote">
            <p>"The AI essay station helped me find my story. My counselor said it was
            the best personal statement draft she'd read all year."</p>
            <span>— Marcus J., accepted to Howard University 🎉</span>
        </div>
        """, unsafe_allow_html=True)
    with t3:
        st.markdown("""
        <div class="cc-quote">
            <p>"Found $12,000 in scholarships I never would have found on my own.
            The scholarship tracker made it actually manageable."</p>
            <span>— Priya K., accepted to University of Florida 🎉</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Final CTA ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="cc-hero" style="padding: 3rem 2rem;">
        <h1 style="font-size:2rem;">Your college journey starts here.</h1>
        <p>Free. AI-powered. Built for students who deserve better than confusing advice.</p>
    </div>
    """, unsafe_allow_html=True)

    cta4, cta5, cta6 = st.columns([2, 1, 2])
    with cta5:
        if st.button("🎓 Create Free Account", type="primary", use_container_width=True, key="cta_bottom"):
            st.switch_page("app.py")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="footer-bar">
        <strong>College Confused</strong> · Free AI-powered college prep · collegeconfused.org<br>
        Built with ❤️ for first-gen students, underfunded schools, and everyone who deserves a fair shot.
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATED DASHBOARD — shown to logged-in users
# ═══════════════════════════════════════════════════════════════════════════════
username = user.get("username", "Student")

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

st.title("🎓 College Confused")
st.markdown(f"Welcome back, **{username}** — let's get you into college.")
st.markdown("---")

st.subheader("📍 Where are you in your journey?")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 📅 My Timeline")
    st.markdown("Every deadline, every milestone — tracked so nothing slips.")
    if st.button("View My Timeline →", key="btn_timeline"):
        st.switch_page("pages/81_cc_timeline.py")

with c2:
    st.markdown("#### 🏫 College List")
    st.markdown("Reach, match, and safety schools with research notes.")
    if st.button("View College List →", key="btn_list"):
        st.switch_page("pages/87_cc_college_list.py")

with c3:
    st.markdown("#### 💰 Scholarships")
    st.markdown("Discover and track scholarships you qualify for.")
    if st.button("Find Scholarships →", key="btn_scholarships"):
        st.switch_page("pages/82_cc_scholarships.py")

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("#### ✍️ Essay Station")
    st.markdown("AI-powered brainstorming, drafting, and review.")
    if st.button("Open Essay Station →", key="btn_essay"):
        st.switch_page("pages/83_cc_essay_station.py")

with c5:
    st.markdown("#### 📚 SAT/ACT Prep")
    st.markdown("Practice questions, score tracking, AI study plans.")
    if st.button("Start Test Prep →", key="btn_testprep"):
        st.switch_page("pages/84_cc_test_prep.py")

with c6:
    st.markdown("#### 📋 FAFSA Guide")
    st.markdown("Step-by-step FAFSA walkthrough, know what to expect.")
    if st.button("Open FAFSA Guide →", key="btn_fafsa"):
        st.switch_page("pages/88_cc_fafsa_guide.py")

st.markdown("---")
st.info(
    "💡 **Tip:** Start with your **Timeline** to see all upcoming deadlines, "
    "then visit **Essay Station** to get ahead on your personal statement.",
    icon="🎯",
)
st.caption("College Confused — Free AI-powered college prep for every student | collegeconfused.org")
