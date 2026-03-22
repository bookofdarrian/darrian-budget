# ── College Confused — Homepage / Landing Page (page 80) ──────────────────────
import streamlit as st
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_cc_css
st.set_page_config(
    page_title="College Confused — Simplify Your College Journey",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_cc_css()
require_login()

# ── DB Tables ─────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_support_emails (
        id {ai},
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at TEXT {ts}
    )""")
    conn.commit()
    conn.close()


try:
    _ensure_tables()
except Exception as _e:
    st.warning(f"⚠️ Could not initialize College Confused tables: {_e}")

# ── Sidebar ───────────────────────────────────────────────────────────────────

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Confused")
st.sidebar.page_link("pages/80_cc_home.py",           label="🏠 Home",              icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py",       label="📅 My Timeline",       icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",   label="💰 Scholarships",      icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",  label="✍️ Essay Station",     icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",      label="📚 SAT/ACT Prep",      icon="📚")
st.sidebar.page_link("pages/87_cc_college_list.py",   label="🏫 College List",      icon="🏫")
st.sidebar.page_link("pages/88_cc_fafsa_guide.py",    label="📋 FAFSA Guide",       icon="📋")
st.sidebar.markdown("---")
render_sidebar_user_widget()

# ── SEO Meta ──────────────────────────────────────────────────────────────────

st.markdown("""
<meta name="description" content="College Confused helps students, families, and supporters navigate the college application process with free guides, AI tools, scholarship search, essay help, and SAT/ACT prep.">
<meta name="keywords" content="college application, scholarships, FAFSA, SAT prep, ACT prep, college essays, HBCU scholarships, first generation college student">
<meta property="og:title" content="College Confused — Simplify Your College Journey">
<meta property="og:description" content="Free college application guides, scholarship search, AI essay help, and SAT/ACT prep for all students.">
""", unsafe_allow_html=True)

# ── Custom CSS ────────────────────────────────────────────────────────────────

CC_CSS = """
<style>
/* ── College Confused color palette ── */
:root {
    --cc-primary:    #6C63FF;
    --cc-accent:     #FF6B6B;
    --cc-success:    #51CF66;
    --cc-bg-card:    #1a1a2e;
    --cc-text-muted: #8892a4;
    --cc-border:     #2a2a4a;
    --cc-bg-dark:    #0f0f23;
}

/* ── Hero section ── */
.cc-hero {
    background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 40%, #16213e 70%, #0f3460 100%);
    border: 1px solid #2a2a5a;
    border-radius: 20px;
    padding: 60px 40px;
    text-align: center;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.cc-hero::before {
    content: '';
    position: absolute;
    top: -60px; left: -60px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(108,99,255,0.18) 0%, transparent 70%);
    pointer-events: none;
}
.cc-hero::after {
    content: '';
    position: absolute;
    bottom: -60px; right: -60px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(255,107,107,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.cc-hero-brand {
    font-size: 3.2rem;
    font-weight: 900;
    color: #6C63FF;
    letter-spacing: -0.04em;
    line-height: 1.1;
    margin-bottom: 12px;
}
.cc-hero-tagline {
    font-size: 1.8rem;
    font-weight: 700;
    color: #fafafa;
    margin-bottom: 14px;
    line-height: 1.25;
}
.cc-hero-sub {
    font-size: 1.1rem;
    color: #8892a4;
    max-width: 640px;
    margin: 0 auto 32px auto;
    line-height: 1.6;
}

/* ── Feature / info cards ── */
.cc-card {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 14px;
    padding: 28px 24px;
    height: 100%;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    cursor: default;
}
.cc-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(108,99,255,0.18);
    border-color: #6C63FF;
}
.cc-card-icon {
    font-size: 2.2rem;
    margin-bottom: 12px;
    display: block;
}
.cc-card-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #fafafa;
    margin-bottom: 8px;
}
.cc-card-body {
    font-size: 0.92rem;
    color: #8892a4;
    line-height: 1.55;
}

/* ── Step / how-it-works cards ── */
.cc-step-card {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 14px;
    padding: 28px 22px;
    text-align: center;
    position: relative;
    height: 100%;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.cc-step-card:hover {
    border-color: #6C63FF;
    box-shadow: 0 8px 24px rgba(108,99,255,0.15);
}
.cc-step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #6C63FF, #9b55ff);
    color: #fff;
    font-size: 1rem;
    font-weight: 800;
    border-radius: 50%;
    margin-bottom: 14px;
}
.cc-step-icon {
    font-size: 2rem;
    margin-bottom: 10px;
    display: block;
}
.cc-step-title {
    font-size: 1rem;
    font-weight: 700;
    color: #fafafa;
    margin-bottom: 8px;
}
.cc-step-body {
    font-size: 0.88rem;
    color: #8892a4;
    line-height: 1.5;
}

/* ── Stat numbers ── */
.cc-stat {
    text-align: center;
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 14px;
    padding: 24px 16px;
}
.cc-stat-number {
    font-size: 2.4rem;
    font-weight: 900;
    color: #6C63FF;
    line-height: 1;
    margin-bottom: 8px;
}
.cc-stat-label {
    font-size: 0.85rem;
    color: #8892a4;
    line-height: 1.4;
}

/* ── Section headers ── */
.cc-section-title {
    font-size: 1.7rem;
    font-weight: 800;
    color: #fafafa;
    margin-bottom: 6px;
    letter-spacing: -0.02em;
}
.cc-section-sub {
    font-size: 0.95rem;
    color: #8892a4;
    margin-bottom: 24px;
    line-height: 1.5;
}

/* ── Mission / promise blocks ── */
.cc-mission-block {
    background: linear-gradient(135deg, #1a1a2e 0%, #12122e 100%);
    border: 1px solid #2a2a4a;
    border-left: 4px solid #6C63FF;
    border-radius: 12px;
    padding: 28px 28px;
    margin-bottom: 16px;
}
.cc-promise-block {
    background: linear-gradient(135deg, #1a2e1a 0%, #122e12 100%);
    border: 1px solid #2a4a2a;
    border-left: 4px solid #51CF66;
    border-radius: 12px;
    padding: 28px 28px;
    margin-bottom: 16px;
}
.cc-promise-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #51CF66;
    margin-bottom: 10px;
}
.cc-mission-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #6C63FF;
    margin-bottom: 10px;
}

/* ── Who we help audience chips ── */
.cc-audience-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 12px;
}
.cc-audience-chip {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 40px;
    padding: 10px 20px;
    font-size: 0.92rem;
    color: #c8d0dc;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    transition: border-color 0.2s;
}
.cc-audience-chip:hover {
    border-color: #6C63FF;
    color: #fafafa;
}

/* ── Contact section ── */
.cc-contact-block {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 14px;
    padding: 32px 28px;
}

/* ── Footer email helper ── */
.cc-support-note {
    text-align: center;
    font-size: 0.88rem;
    color: #8892a4;
    margin-top: 20px;
    padding: 14px;
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 10px;
}
.cc-support-note a {
    color: #6C63FF;
    text-decoration: none;
}

/* ── Responsive tweaks ── */
@media (max-width: 768px) {
    .cc-hero { padding: 36px 20px; }
    .cc-hero-brand { font-size: 2rem; }
    .cc-hero-tagline { font-size: 1.3rem; }
    .cc-stat-number { font-size: 1.8rem; }
    .cc-section-title { font-size: 1.3rem; }
}
</style>
"""

st.markdown(CC_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-hero">
    <div class="cc-hero-brand">🎓 College Confused</div>
    <div class="cc-hero-tagline">Simplify the College Application Process</div>
    <div class="cc-hero-sub">
        Free guides, tools, and AI-powered resources for every student, family,
        and supporter — no matter your background.
    </div>
</div>
""", unsafe_allow_html=True)

# Hero CTA buttons
hero_col1, hero_col2, hero_col3, hero_col4, hero_col5, hero_col6 = st.columns(6)
with hero_col1:
    st.page_link("pages/81_cc_timeline.py", label="📅 Build My Timeline", use_container_width=True)
with hero_col2:
    st.page_link("pages/82_cc_scholarships.py", label="💰 Find Scholarships", use_container_width=True)
with hero_col3:
    st.page_link("pages/83_cc_essay_station.py", label="✍️ Write My Essays", use_container_width=True)
with hero_col4:
    st.page_link("pages/84_cc_test_prep.py", label="📚 SAT/ACT Prep", use_container_width=True)
with hero_col5:
    st.page_link("pages/87_cc_college_list.py", label="🏫 My College List", use_container_width=True)
with hero_col6:
    st.page_link("pages/88_cc_fafsa_guide.py", label="📋 FAFSA Guide", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# QUICK STATS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-section-title">📊 Why It Matters</div>
<div class="cc-section-sub">The numbers that drove us to build College Confused.</div>
""", unsafe_allow_html=True)

stat1, stat2, stat3, stat4 = st.columns(4)
with stat1:
    st.markdown("""
    <div class="cc-stat">
        <div class="cc-stat-number">$100B+</div>
        <div class="cc-stat-label">In scholarships go unclaimed every year in the US</div>
    </div>
    """, unsafe_allow_html=True)
with stat2:
    st.markdown("""
    <div class="cc-stat">
        <div class="cc-stat-number">25+</div>
        <div class="cc-stat-label">College acceptances won by our founder in a single cycle</div>
    </div>
    """, unsafe_allow_html=True)
with stat3:
    st.markdown("""
    <div class="cc-stat">
        <div class="cc-stat-number">$1.5M+</div>
        <div class="cc-stat-label">In merit-based scholarships earned by our founder — now sharing the playbook</div>
    </div>
    """, unsafe_allow_html=True)
with stat4:
    st.markdown("""
    <div class="cc-stat">
        <div class="cc-stat-number">10+</div>
        <div class="cc-stat-label">Full-ride scholarship offers received — all documented strategies shared here</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# WHAT IS COLLEGE CONFUSED — MISSION
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-section-title">🏫 What Is College Confused?</div>
<div class="cc-section-sub">A nonprofit born from real struggle — and real success.</div>
""", unsafe_allow_html=True)

mission_col, founder_col = st.columns([3, 2], gap="large")

with mission_col:
    st.markdown("""
    <div class="cc-mission-block">
        <div class="cc-mission-title">Our Mission</div>
        <p style="color:#c8d0dc; font-size:1rem; line-height:1.7; margin:0 0 14px 0;">
            <strong>College Confused</strong> is a nonprofit organization founded by
            <strong>Darrian Belcher</strong> during his senior year fellowship at the
            <strong>Governor's School for Science &amp; Technology (GSST)</strong>.
        </p>
        <p style="color:#c8d0dc; font-size:1rem; line-height:1.7; margin:0 0 14px 0;">
            As a <strong>low-income student</strong>, Darrian navigated
            the college process largely on his own — figuring out FAFSA, scholarship essays,
            test prep, and application timelines with almost no guidance. That confusion turned
            into a superpower: <strong>25+ college acceptances, 10+ full rides, and over $1.5M+
            in merit-based scholarships earned.</strong>
        </p>
        <p style="color:#c8d0dc; font-size:1rem; line-height:1.7; margin:0;">
            Now, College Confused exists to make sure <em>no student goes through that alone</em>.
            We give every student — regardless of zip code, income, or background — the same
            tools, guides, and knowledge that helped Darrian win.
            <strong>Completely free. No gatekeeping. Ever.</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

with founder_col:
    st.markdown("""
    <div class="cc-card" style="border-left: 4px solid #FF6B6B;">
        <span class="cc-card-icon">🧑🏾‍🎓</span>
        <div class="cc-card-title">Meet the Founder</div>
        <div class="cc-card-body">
            <strong style="color:#fafafa;">Darrian Belcher</strong> is a GSST senior fellow and the founder of College Confused.<br><br>
            He applied to college the hard way — no college counselor, no prep courses,
            no roadmap. But through relentless research and trial-and-error, he built a
            system that worked.<br><br>
            <strong style="color:#FF6B6B;">25+ acceptances. 10+ full rides. $1.5M+ in merit-based scholarships.</strong><br><br>
            Now he's teaching everyone else how to do it.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HOW IT WORKS — 4-STEP PROCESS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-section-title">⚙️ How It Works</div>
<div class="cc-section-sub">
    Four simple steps — start anywhere, go at your own pace.
    Everything is free. Everything is designed for regular people.
</div>
""", unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4, gap="medium")

with s1:
    st.markdown("""
    <div class="cc-step-card">
        <div class="cc-step-badge">1</div>
        <span class="cc-step-icon">📅</span>
        <div class="cc-step-title">Set Up Your Timeline</div>
        <div class="cc-step-body">
            One click to generate your personalized college application timeline.
            Know exactly what to do — and when — from junior year all the way to Decision Day.
        </div>
    </div>
    """, unsafe_allow_html=True)

with s2:
    st.markdown("""
    <div class="cc-step-card">
        <div class="cc-step-badge">2</div>
        <span class="cc-step-icon">💰</span>
        <div class="cc-step-title">Find Scholarships</div>
        <div class="cc-step-body">
            Search national, international, and local scholarships filtered just for you.
            No more Googling for hours — we surface the money that's already waiting for you.
        </div>
    </div>
    """, unsafe_allow_html=True)

with s3:
    st.markdown("""
    <div class="cc-step-card">
        <div class="cc-step-badge">3</div>
        <span class="cc-step-icon">✍️</span>
        <div class="cc-step-title">Write Your Essays</div>
        <div class="cc-step-body">
            AI-powered essay station trained on real winning essays. Get prompts,
            outlines, feedback, and examples so your story lands — every time.
        </div>
    </div>
    """, unsafe_allow_html=True)

with s4:
    st.markdown("""
    <div class="cc-step-card">
        <div class="cc-step-badge">4</div>
        <span class="cc-step-icon">📚</span>
        <div class="cc-step-title">Prep for Tests</div>
        <div class="cc-step-body">
            SAT/ACT practice exams and AI study insights — no tutor needed.
            Learn which sections to focus on and track your score improvements over time.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE CARDS — 5 major sections
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-section-title">🚀 Explore the Tools</div>
<div class="cc-section-sub">
    Every tool is built for clarity. No jargon. No paywalls. Just results.
</div>
""", unsafe_allow_html=True)

fc1, fc2, fc3 = st.columns(3, gap="medium")
fc4, fc5, _   = st.columns(3, gap="medium")

with fc1:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">🏠</span>
        <div class="cc-card-title">College Confused Home</div>
        <div class="cc-card-body">
            Your starting point. Understand the process, meet the founder,
            and get pointed in the right direction — no matter where you're starting from.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/80_cc_home.py", label="You're here! ↩", use_container_width=True)

with fc2:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">📅</span>
        <div class="cc-card-title">My Timeline</div>
        <div class="cc-card-body">
            Generate a week-by-week college application timeline customized to your
            grade level, goals, and target schools. Never miss a deadline again.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/81_cc_timeline.py", label="📅 Open Timeline →", use_container_width=True)

with fc3:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">💰</span>
        <div class="cc-card-title">Scholarships</div>
        <div class="cc-card-body">
            Search thousands of scholarships — local, national, HBCU-specific,
            first-gen, STEM, arts, and more. Filter by eligibility. Apply with confidence.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/82_cc_scholarships.py", label="💰 Find Scholarships →", use_container_width=True)

with fc4:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">✍️</span>
        <div class="cc-card-title">Essay Station</div>
        <div class="cc-card-body">
            AI-powered essay writing tools trained on real winning college essays.
            Get prompts, outlines, AI feedback, and examples for Common App, supplementals,
            and scholarship essays.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/83_cc_essay_station.py", label="✍️ Open Essay Station →", use_container_width=True)

with fc5:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">📚</span>
        <div class="cc-card-title">SAT/ACT Prep</div>
        <div class="cc-card-body">
            Full-length SAT and ACT practice tests, section drills, score tracking,
            and AI-generated study plans. No expensive tutors required.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/84_cc_test_prep.py", label="📚 Start Prepping →", use_container_width=True)

# Second row of feature cards
fc6, fc7, _ = st.columns(3, gap="medium")

with fc6:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">🏫</span>
        <div class="cc-card-title">My College List</div>
        <div class="cc-card-body">
            Build and manage your college list with safety, target, and reach schools.
            Track deadlines, application status, financial aid offers, and decisions
            — all in one place.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/87_cc_college_list.py", label="🏫 Build My College List →", use_container_width=True)

with fc7:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">📋</span>
        <div class="cc-card-title">FAFSA Guide</div>
        <div class="cc-card-body">
            Step-by-step FAFSA walkthrough written in plain English — for students,
            parents, and grandparents. Covers every section, every document you need,
            and how to avoid the most common mistakes.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/88_cc_fafsa_guide.py", label="📋 Open FAFSA Guide →", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# WHO WE HELP
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-section-title">🤝 Who We Help</div>
<div class="cc-section-sub">
    College Confused is not just for students. We built this for everyone who
    plays a role in a young person's college journey.
</div>
""", unsafe_allow_html=True)

audience_left, audience_right = st.columns([3, 2], gap="large")

with audience_left:
    st.markdown("""
    <div class="cc-audience-grid">
        <div class="cc-audience-chip">🧑‍🎓 Students (middle school → college)</div>
        <div class="cc-audience-chip">👩‍👧 Parents &amp; guardians</div>
        <div class="cc-audience-chip">👴 Grandparents &amp; elderly family members</div>
        <div class="cc-audience-chip">🍎 Teachers &amp; school counselors</div>
        <div class="cc-audience-chip">🌍 Community mentors &amp; coaches</div>
        <div class="cc-audience-chip">🏘️ Youth program leaders</div>
        <div class="cc-audience-chip">⛪ Church &amp; faith community supporters</div>
        <div class="cc-audience-chip">🏫 First-generation students</div>
        <div class="cc-audience-chip">💚 Low-income families</div>
        <div class="cc-audience-chip">🏆 High-achievers ready to maximize aid</div>
    </div>
    """, unsafe_allow_html=True)

with audience_right:
    st.markdown("""
    <div class="cc-card" style="border-left: 4px solid #51CF66;">
        <span class="cc-card-icon">💬</span>
        <div class="cc-card-title" style="color:#51CF66;">No Experience Needed</div>
        <div class="cc-card-body">
            Never applied to college yourself? No problem.<br><br>
            Our guides are written so that <strong>anyone</strong> — a grandparent,
            a first-time parent, or a 7th grader — can follow along and actually
            help their student succeed.<br><br>
            We don't assume you know what FAFSA, CSS Profile, Early Decision,
            or demonstrated interest mean. We explain everything from scratch,
            every time.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE LANGUAGE PROMISE
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-promise-block">
    <div class="cc-promise-title">✅ Our Simple Language Promise</div>
    <p style="color:#c8d0dc; font-size:1.05rem; line-height:1.7; margin:0 0 10px 0;">
        <strong>We write every guide so that anyone — 8 years old or 80 years old — can follow along.</strong>
    </p>
    <p style="color:#8892a4; font-size:0.95rem; line-height:1.65; margin:0;">
        No jargon. No gatekeeping. No assuming you already know how things work.
        Just clear steps, plain English, and real examples drawn from real students
        who won — including our founder. If something on this site is confusing,
        that's <em>our</em> fault — and we want to fix it.
        Email us at <a href="mailto:support@collegeconfused.org" style="color:#51CF66;">support@collegeconfused.org</a>
        and we'll make it clearer.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONTACT / SUPPORT FORM
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-section-title">📬 Get in Touch</div>
<div class="cc-section-sub">
    Have a question? Need help with something specific? We read every message
    and respond within 24–48 hours — for real.
</div>
""", unsafe_allow_html=True)

contact_col, faq_col = st.columns([3, 2], gap="large")

with contact_col:
    st.markdown('<div class="cc-contact-block">', unsafe_allow_html=True)

    with st.form("support_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name  = col1.text_input("Your Name", placeholder="E.g. Maya Johnson")
        email = col2.text_input("Your Email", placeholder="maya@example.com")
        subject = st.selectbox(
            "Subject",
            [
                "General Question",
                "Scholarship Help",
                "Essay Help",
                "SAT/ACT Help",
                "Timeline Help",
                "Technical Issue",
                "Partnership Inquiry",
                "Other",
            ],
        )
        message = st.text_area(
            "Your Message",
            height=120,
            placeholder="Tell us what's on your mind. We're here to help.",
        )
        submitted = st.form_submit_button(
            "Send Message 📨",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if name and email and message:
                try:
                    conn = get_conn()
                    db_exec(
                        conn,
                        "INSERT INTO cc_support_emails (name, email, subject, message) VALUES (?, ?, ?, ?)",
                        (name.strip(), email.strip(), subject, message.strip()),
                    )
                    conn.commit()
                    conn.close()
                    st.success(
                        "✅ Message sent! We'll get back to you within 24–48 hours. "
                        "Keep an eye on your inbox."
                    )
                except Exception as e:
                    st.error(f"❌ Something went wrong while sending your message. Please try again. ({e})")
            else:
                st.error("⚠️ Please fill in your name, email, and message before sending.")

    st.markdown("</div>", unsafe_allow_html=True)

with faq_col:
    st.markdown("""
    <div class="cc-card">
        <span class="cc-card-icon">❓</span>
        <div class="cc-card-title">Common Questions</div>
        <div class="cc-card-body">
            <strong style="color:#fafafa;">Is everything really free?</strong><br>
            Yes. College Confused is a nonprofit. There are no paywalls, subscriptions,
            or hidden fees — ever.<br><br>

            <strong style="color:#fafafa;">Do I need to create an account?</strong><br>
            You're already logged in! Your timeline and progress are saved to your account.<br><br>

            <strong style="color:#fafafa;">I'm a parent, not a student. Can I use this?</strong><br>
            Absolutely. Everything is written for parents and supporters too — no college
            experience required.<br><br>

            <strong style="color:#fafafa;">What if my school doesn't have a counselor?</strong><br>
            This site <em>is</em> your counselor. We cover everything a good college
            counselor would — for free.<br><br>

            <strong style="color:#fafafa;">How do I contact you?</strong><br>
            Fill out the form, or email
            <a href="mailto:support@collegeconfused.org" style="color:#6C63FF;">
            support@collegeconfused.org</a> directly.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ACCESSIBILITY NOTE
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="cc-support-note">
    🙋 <strong>Need help understanding any of this?</strong>
    Email us at
    <a href="mailto:support@collegeconfused.org">support@collegeconfused.org</a>
    and we will walk you through it step by step — no question is too basic.
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<hr style="border-color:#2a2a4a; margin: 8px 0 20px 0;">
<div style="text-align:center; color:#8892a4; font-size:0.82rem; line-height:1.8;">
    🎓 <strong style="color:#6C63FF;">College Confused</strong> — A nonprofit by Darrian Belcher
    &nbsp;|&nbsp;
    Founded at GSST Senior Year Fellowship
    &nbsp;|&nbsp;
    <a href="mailto:support@collegeconfused.org" style="color:#6C63FF; text-decoration:none;">
        support@collegeconfused.org
    </a>
    <br>
    <span style="font-size:0.75rem; color:#555f70;">
        Free college application resources for every student, family, and supporter.
        No paywalls. No gatekeeping. Ever.
    </span>
</div>
""", unsafe_allow_html=True)
