"""
College Confused — Scholarship Dashboard (Page 82)
Helps students find, filter, save, and track scholarship opportunities.
"""

import os
import streamlit as st
from datetime import datetime
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting, is_cc_ai_allowed
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_cc_css

st.set_page_config(
    page_title="Scholarship Dashboard — College Confused",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_cc_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Confused")
st.sidebar.page_link("pages/80_cc_home.py",           label="🏠 Home",              icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py",       label="📅 My Timeline",       icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",   label="💰 Scholarships",      icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",  label="✍️ Essay Station",     icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",      label="📚 SAT/ACT Prep",      icon="📚")
st.sidebar.markdown("---")
render_sidebar_user_widget()

# ── Current user ──────────────────────────────────────────────────────────────
_user = st.session_state.get("user", {})
_user_email = _user.get("email", "anonymous")


# ══════════════════════════════════════════════════════════════════════════════
# DB SETUP
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_scholarships (
        id {ai},
        name TEXT NOT NULL,
        provider TEXT NOT NULL,
        amount_min REAL DEFAULT 0,
        amount_max REAL DEFAULT 0,
        amount_display TEXT DEFAULT '',
        deadline TEXT DEFAULT '',
        deadline_month INTEGER DEFAULT 12,
        url TEXT DEFAULT '',
        description TEXT DEFAULT '',
        eligibility TEXT DEFAULT '',
        category TEXT DEFAULT 'national',
        state TEXT DEFAULT '',
        hbcu_only INTEGER DEFAULT 0,
        minority_focus INTEGER DEFAULT 0,
        stem_focus INTEGER DEFAULT 0,
        first_gen_focus INTEGER DEFAULT 0,
        need_based INTEGER DEFAULT 0,
        merit_based INTEGER DEFAULT 0,
        essay_required INTEGER DEFAULT 0,
        gpa_min REAL DEFAULT 0,
        renewable INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 1,
        created_at TEXT {ts}
    )""")

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_scholarship_saved (
        id {ai},
        user_email TEXT NOT NULL,
        scholarship_id INTEGER NOT NULL,
        status TEXT DEFAULT 'saved',
        notes TEXT DEFAULT '',
        applied_date TEXT,
        created_at TEXT {ts}
    )""")
    conn.commit()
    conn.close()


def _seed_scholarships():
    conn = get_conn()
    c = db_exec(conn, "SELECT COUNT(*) FROM cc_scholarships")
    count = c.fetchone()[0]
    conn.close()
    if count > 0:
        return

    scholarships = [
        # NATIONAL SCHOLARSHIPS
        ("College Board Opportunity Scholarships", "College Board", 500, 40000, "Up to $40,000", "Rolling", 12, "https://opportunity.collegeboard.org/", "Complete college application tasks to earn scholarship entries. Tasks include creating a college list, SAT practice, FAFSA completion, and applying to college.", "High school students applying to college", "national", "", 0, 0, 0, 0, 1, 1, 0, 0.0, 0),
        ("Gates Scholarship", "Bill & Melinda Gates Foundation", 0, 0, "Full Cost of Attendance", "September 15", 9, "https://www.thegatesscholarship.org/", "For exceptional, Pell-eligible, minority high school seniors in the United States.", "Pell-eligible minority students, 3.3+ GPA", "national", "", 1, 0, 0, 1, 1, 1, 1, 3.3, 1),
        ("Jack Kent Cooke Foundation Scholarship", "Jack Kent Cooke Foundation", 0, 55000, "Up to $55,000/year", "November", 11, "https://www.jkcf.org/our-scholarships/", "For high-achieving students with financial need transitioning from high school to college.", "High academic achievement, financial need", "national", "", 0, 0, 0, 0, 1, 1, 1, 3.5, 1),
        ("Coca-Cola Scholars Program", "Coca-Cola Scholars Foundation", 20000, 20000, "$20,000", "October 31", 10, "https://www.coca-colascholarsfoundation.org/", "Merit-based scholarship for high school seniors who demonstrate leadership and service.", "High school seniors, leadership, service", "national", "", 0, 0, 0, 0, 0, 1, 1, 3.0, 0),
        ("Dell Scholars Program", "Michael & Susan Dell Foundation", 20000, 20000, "$20,000", "December 1", 12, "https://www.dellscholars.org/", "For hardworking students who need support to achieve their college dreams. Includes laptop, textbooks, and ongoing support.", "2.4+ GPA, Pell-eligible, college prep program participant", "national", "", 0, 0, 0, 1, 1, 0, 0, 2.4, 0),
        ("Ron Brown Scholar Program", "Ron Brown Scholar Program", 10000, 10000, "$10,000/year", "January 9", 1, "https://www.ronbrown.org/", "For academically talented, community-involved African American high school seniors.", "African American high school seniors, academic achievement", "national", "", 1, 0, 0, 0, 0, 1, 1, 3.0, 1),
        ("QuestBridge National College Match", "QuestBridge", 0, 0, "Full 4-Year Scholarship", "September 27", 9, "https://www.questbridge.org/", "Connects high-achieving, low-income students with full scholarships to top colleges.", "High-achieving low-income students", "national", "", 0, 0, 0, 1, 1, 1, 1, 3.5, 1),
        ("Elks National Foundation Most Valuable Student", "Elks National Foundation", 1000, 50000, "$1,000 - $50,000", "November 1", 11, "https://www.elks.org/enf/scholars/mvs.cfm", "Merit-based scholarship for graduating high school seniors who demonstrate scholarship, leadership, and financial need.", "US citizens, leadership, academic achievement", "national", "", 0, 0, 0, 0, 1, 1, 1, 0.0, 1),
        ("Sallie Mae Scholarship", "Sallie Mae", 1000, 5000, "Up to $5,000", "March 31", 3, "https://www.salliemae.com/college-planning/scholarship-search/", "Various scholarships for students pursuing higher education.", "High school and college students", "national", "", 0, 0, 0, 0, 0, 1, 0, 0.0, 0),
        ("UNCF Scholarships", "United Negro College Fund", 500, 0, "Varies", "Rolling", 12, "https://uncf.org/scholarships", "UNCF awards over $100 million in scholarships annually to students at more than 1,100 schools.", "African American students, financial need", "national", "", 1, 0, 0, 0, 1, 1, 1, 2.5, 0),
        # HBCU-SPECIFIC
        ("Thurgood Marshall College Fund Scholarship", "Thurgood Marshall College Fund", 3000, 3000, "$3,000", "February 15", 2, "https://tmcf.org/students-alumni/scholarship/tmcf-scholarships/", "Merit and need-based scholarships for students attending TMCF member HBCUs.", "Students attending TMCF member HBCUs, 3.0+ GPA", "hbcu", "", 1, 0, 0, 0, 1, 1, 1, 3.0, 0),
        ("HBCU Week Foundation Scholarship", "HBCU Week Foundation", 1000, 10000, "$1,000 - $10,000", "February 15", 2, "https://www.hbcuweek.org/scholarships-and-internships/", "Scholarships for students planning to attend HBCUs. Partners include NFL, Capital One, DuPont.", "Students planning to attend HBCUs", "hbcu", "", 1, 0, 0, 0, 0, 1, 0, 0.0, 0),
        ("UNCF/Koch Scholars Program", "UNCF and Charles Koch Foundation", 5000, 5000, "$5,000", "February 28", 2, "https://uncf.org/scholarships", "For students at UNCF member HBCUs studying business, economics, or social sciences.", "UNCF member HBCU students, specific majors", "hbcu", "", 1, 0, 0, 0, 0, 1, 1, 2.5, 0),
        ("NAFEO Scholarship", "National Association for Equal Opportunity", 2500, 2500, "$2,500", "March 1", 3, "https://nafeo.org/", "For students attending HBCUs and Predominantly Black Institutions.", "HBCU and PBI students", "hbcu", "", 1, 0, 0, 0, 1, 1, 0, 2.5, 0),
        # STEM SCHOLARSHIPS
        ("NSBE Scholarship", "National Society of Black Engineers", 1000, 5000, "$1,000 - $5,000", "January 31", 1, "https://www.nsbe.org/Programs/Scholarships", "For African American students pursuing STEM degrees.", "African American STEM students, NSBE member", "national", "", 1, 1, 1, 0, 0, 1, 1, 2.5, 0),
        ("SHPE Scholarship", "Society of Hispanic Professional Engineers", 1000, 7000, "$1,000 - $7,000", "April 1", 4, "https://shpe.org/resources/scholarships/", "For Hispanic students in engineering and STEM fields.", "Hispanic STEM students", "national", "", 0, 1, 1, 0, 0, 1, 1, 3.0, 0),
        ("Google Generation Scholarship", "Google", 10000, 10000, "$10,000", "December 1", 12, "https://buildyourfuture.withgoogle.com/scholarships", "For students underrepresented in computer science pursuing technology degrees.", "Underrepresented CS students", "national", "", 0, 1, 1, 0, 0, 1, 1, 3.2, 0),
        ("Microsoft Scholarship", "Microsoft", 0, 0, "Varies", "February 1", 2, "https://careers.microsoft.com/students/us/en/usscholarshipprogram", "For underrepresented students pursuing computer science or related technical degrees.", "Underrepresented CS/tech students", "national", "", 0, 1, 1, 0, 0, 1, 0, 3.0, 0),
        # FIRST-GEN / NEED-BASED
        ("Horatio Alger Scholarship", "Horatio Alger Association", 6000, 25000, "$6,000 - $25,000", "October 25", 10, "https://scholars.horatioalger.org/scholarships/about-our-scholarship-programs/", "For students who have overcome adversity and demonstrated financial need.", "Financial need, adversity overcome, 2.0+ GPA", "national", "", 0, 0, 0, 1, 1, 0, 1, 2.0, 1),
        ("Raise.me Micro-Scholarships", "Raise.me", 100, 2000, "$100 - $2,000", "Rolling", 12, "https://www.raise.me/", "Earn scholarship money from colleges for achievements throughout high school.", "High school students, any grade", "national", "", 0, 0, 0, 0, 1, 1, 0, 0.0, 0),
        ("Fastweb Scholarships", "Fastweb", 1000, 0, "Varies (1.5M+ scholarships)", "Rolling", 12, "https://www.fastweb.com/", "Free scholarship search engine matching students with over 1.5 million scholarship opportunities.", "All students", "national", "", 0, 0, 0, 0, 0, 1, 0, 0.0, 0),
        ("Scholarships.com Database", "Scholarships.com", 500, 0, "Varies ($19B+ tracked)", "Rolling", 12, "https://www.scholarships.com/", "Free search engine tracking over $19 billion in scholarships. Create profile for personalized matches.", "All students", "national", "", 0, 0, 0, 0, 0, 1, 0, 0.0, 0),
        ("Niche Scholarships", "Niche", 500, 25000, "Varies", "Monthly", 12, "https://www.niche.com/colleges/scholarships/", "Scholarship search and matching service. Niche also offers its own no-essay scholarships.", "All students", "national", "", 0, 0, 0, 0, 0, 1, 0, 0.0, 0),
        # COMMUNITY / LOCAL FINDING
        ("Local Community Foundation", "Your Local Community Foundation", 500, 5000, "$500 - $5,000", "Varies", 3, "https://www.cof.org/page/community-foundation-locator", "Community foundations in most cities offer local scholarships. Search for your city's foundation.", "Local residents, varies by foundation", "local", "", 0, 0, 0, 0, 1, 1, 0, 0.0, 0),
        ("Rotary Club Scholarship", "Local Rotary Club", 500, 3000, "Varies by club", "Varies", 2, "https://www.rotary.org/en/our-programs/scholarships", "Most local Rotary Clubs offer scholarships for community members. Ask your school counselor!", "Community involvement, leadership", "local", "", 0, 0, 0, 0, 0, 1, 1, 0.0, 0),
        ("Elks Lodge Scholarship", "Local Elks Lodge", 1000, 4000, "Varies", "November 1", 11, "https://www.elks.org/", "Most Elks Lodges offer local scholarships. Check with the lodge nearest you.", "US citizens, local community member", "local", "", 0, 0, 0, 0, 1, 1, 0, 0.0, 0),
        # INTERNATIONAL/DIVERSE
        ("Hispanic Scholarship Fund", "Hispanic Scholarship Fund", 500, 5000, "$500 - $5,000", "February 15", 2, "https://www.hsf.net/scholarship", "Supports Hispanic and Latino students pursuing higher education.", "Hispanic/Latino students, 3.0+ GPA", "national", "", 0, 1, 0, 0, 1, 1, 1, 3.0, 0),
        ("Asian & Pacific Islander Scholarship", "Asian & Pacific Islander American Scholarship Fund", 2500, 20000, "$2,500 - $20,000", "January 19", 1, "https://www.apiasf.org/", "For students who identify as Asian and/or Pacific Islander American.", "Asian/Pacific Islander students, financial need", "national", "", 0, 1, 0, 0, 1, 1, 0, 2.7, 1),
        ("American Indian College Fund", "American Indian College Fund", 200, 0, "Varies", "May 31", 5, "https://collegefund.org/", "Supports American Indian and Alaska Native students at tribal colleges and universities.", "American Indian/Alaska Native students", "national", "", 0, 1, 0, 0, 1, 0, 0, 0.0, 0),
    ]

    conn = get_conn()
    for s in scholarships:
        (name, provider, amount_min, amount_max, amount_display, deadline, deadline_month,
         url, description, eligibility, category, state, hbcu_only, minority_focus, stem_focus,
         first_gen_focus, need_based, merit_based, essay_required, gpa_min, renewable) = s
        db_exec(conn, """INSERT INTO cc_scholarships
            (name, provider, amount_min, amount_max, amount_display, deadline, deadline_month,
             url, description, eligibility, category, state, hbcu_only, minority_focus, stem_focus,
             first_gen_focus, need_based, merit_based, essay_required, gpa_min, renewable)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, provider, amount_min, amount_max, amount_display, deadline, deadline_month,
             url, description, eligibility, category, state, hbcu_only, minority_focus, stem_focus,
             first_gen_focus, need_based, merit_based, essay_required, gpa_min, renewable))
    conn.commit()
    conn.close()


# ── AI Matcher ────────────────────────────────────────────────────────────────

def _ai_match_scholarships(profile: dict, scholarships: list, user_email: str = "") -> str:
    if not is_cc_ai_allowed(user_email):
        return "🚀 AI Matching is coming soon to College Confused! In the meantime, use the filters in the Browse tab to find scholarships that match your profile."
    api_key = os.environ.get("CC_ANTHROPIC_API_KEY") or get_setting("cc_anthropic_api_key", "")
    if not api_key:
        return "No AI key configured. Please set your Anthropic API key in Settings."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        schol_summary = "\n".join([
            f"- {s['name']} ({s['provider']}): {s['amount_display']}, Deadline: {s['deadline']}, "
            f"HBCU: {bool(s['hbcu_only'])}, Minority: {bool(s['minority_focus'])}, "
            f"STEM: {bool(s['stem_focus'])}, Need-Based: {bool(s['need_based'])}"
            for s in scholarships[:30]
        ])
        prompt = f"""You are a college counselor helping a student find the best scholarships.

Student Profile:
- Grade: {profile.get('current_grade', 'Senior')}
- GPA: {profile.get('gpa', 'N/A')}
- State: {profile.get('state', 'Unknown')}
- Intended Major: {profile.get('intended_major', 'Undecided')}
- First-Generation: {bool(profile.get('first_gen', 0))}
- HBCU Interest: {bool(profile.get('hbcu_interest', 0))}
- Financial Need: {bool(profile.get('financial_need', 0))}
- SAT Score: {profile.get('sat_score', 'Not taken')}
- ACT Score: {profile.get('act_score', 'Not taken')}

Available Scholarships:
{schol_summary}

Please recommend the TOP 5-8 scholarships that best match this student's profile. For each:
1. Name the scholarship
2. Explain in simple language (1-2 sentences) why it's a great fit for THIS specific student
3. Give one actionable next step

Keep language simple and encouraging. This student may be the first in their family to go to college."""

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"AI Error: {e}"


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_all_scholarships() -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, "SELECT * FROM cc_scholarships ORDER BY deadline_month, name")
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _get_saved_scholarships(user_email: str) -> list[dict]:
    conn = get_conn()
    c = db_exec(conn, """
        SELECT s.*, ss.status as save_status, ss.notes as save_notes,
               ss.applied_date, ss.id as saved_id
        FROM cc_scholarships s
        JOIN cc_scholarship_saved ss ON s.id = ss.scholarship_id
        WHERE ss.user_email = ?
        ORDER BY ss.created_at DESC
    """, (user_email,))
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _get_saved_ids(user_email: str) -> set:
    conn = get_conn()
    c = db_exec(conn, "SELECT scholarship_id FROM cc_scholarship_saved WHERE user_email = ?", (user_email,))
    rows = c.fetchall()
    conn.close()
    return {r[0] for r in rows}


def _save_scholarship(user_email: str, scholarship_id: int):
    conn = get_conn()
    # Check if already saved
    c = db_exec(conn, "SELECT id FROM cc_scholarship_saved WHERE user_email = ? AND scholarship_id = ?",
                (user_email, scholarship_id))
    if c.fetchone():
        conn.close()
        return False  # already saved
    db_exec(conn, """INSERT INTO cc_scholarship_saved (user_email, scholarship_id, status, notes)
                     VALUES (?, ?, 'saved', '')""", (user_email, scholarship_id))
    conn.commit()
    conn.close()
    return True


def _update_saved_scholarship(saved_id: int, status: str, notes: str, applied_date: str):
    conn = get_conn()
    db_exec(conn, """UPDATE cc_scholarship_saved
                     SET status = ?, notes = ?, applied_date = ?
                     WHERE id = ?""",
            (status, notes, applied_date, saved_id))
    conn.commit()
    conn.close()


def _remove_saved_scholarship(saved_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM cc_scholarship_saved WHERE id = ?", (saved_id,))
    conn.commit()
    conn.close()


def _get_student_profile(user_email: str) -> dict:
    """Try to load student profile from cc_student_profile table if it exists."""
    try:
        conn = get_conn()
        c = db_exec(conn, "SELECT * FROM cc_student_profile WHERE user_email = ? LIMIT 1", (user_email,))
        row = c.fetchone()
        if row is None:
            conn.close()
            return {}
        if USE_POSTGRES:
            cols = [d[0] for d in c.description]
            result = dict(zip(cols, row))
        else:
            result = dict(row)
        conn.close()
        return result
    except Exception:
        return {}


# ── Styling helpers ───────────────────────────────────────────────────────────

CC_CSS = """
<style>
.schol-card {
    background: #12151c;
    border: 1px solid #1e2330;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
    position: relative;
}
.schol-card:hover {
    border-color: #4CAF50;
    transition: border-color 0.2s;
}
.schol-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: #fafafa;
    margin-bottom: 2px;
}
.schol-provider {
    font-size: 0.82rem;
    color: #8892a4;
    margin-bottom: 8px;
}
.schol-amount {
    display: inline-block;
    background: #1a3a1a;
    color: #4CAF50;
    font-weight: 700;
    font-size: 0.88rem;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid #2a5a2a;
    margin-right: 6px;
    margin-bottom: 6px;
}
.schol-deadline {
    display: inline-block;
    background: #2a1a1a;
    color: #f87171;
    font-size: 0.82rem;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid #5a2a2a;
    margin-right: 6px;
    margin-bottom: 6px;
}
.schol-deadline-ok {
    display: inline-block;
    background: #1a1a2a;
    color: #8892a4;
    font-size: 0.82rem;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid #2a2a4a;
    margin-right: 6px;
    margin-bottom: 6px;
}
.badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    margin-right: 4px;
    margin-bottom: 4px;
}
.badge-hbcu   { background: #2d1b69; color: #c4b5fd; border: 1px solid #5b21b6; }
.badge-stem   { background: #0c2340; color: #60a5fa; border: 1px solid #1e3a5f; }
.badge-min    { background: #2d1b3d; color: #e879f9; border: 1px solid #5b21b6; }
.badge-fg     { background: #1a2d1a; color: #86efac; border: 1px solid #166534; }
.badge-need   { background: #2d1a1a; color: #fca5a5; border: 1px solid #7f1d1d; }
.badge-merit  { background: #2d2a1a; color: #fcd34d; border: 1px solid #78350f; }
.badge-essay  { background: #1a2530; color: #93c5fd; border: 1px solid #1e3a5f; }
.badge-renew  { background: #1a2d25; color: #6ee7b7; border: 1px solid #065f46; }
.badge-local  { background: #2d2520; color: #fdba74; border: 1px solid #7c2d12; }
.schol-desc {
    font-size: 0.87rem;
    color: #c8d0dc;
    line-height: 1.5;
    margin: 8px 0 6px 0;
}
.schol-elig {
    font-size: 0.8rem;
    color: #8892a4;
    margin-bottom: 10px;
}
.tip-box {
    background: #0c1f0c;
    border: 1px solid #1a4a1a;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 12px 0;
}
.tip-box h4 { color: #4CAF50; margin-bottom: 8px; }
.tip-box li { color: #c8d0dc; font-size: 0.88rem; line-height: 1.7; }
.warning-box {
    background: #2d1a00;
    border: 1px solid #7c4a00;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 12px 0;
    color: #fbbf24;
    font-size: 0.88rem;
}
.info-box {
    background: #0c1a2d;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 12px 0;
    color: #93c5fd;
    font-size: 0.88rem;
}
.stats-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}
.stat-pill {
    background: #12151c;
    border: 1px solid #1e2330;
    border-radius: 10px;
    padding: 10px 16px;
    text-align: center;
    flex: 1;
    min-width: 120px;
}
.stat-pill .val {
    font-size: 1.5rem;
    font-weight: 800;
    color: #4CAF50;
    line-height: 1;
}
.stat-pill .lbl {
    font-size: 0.72rem;
    color: #8892a4;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.saved-card {
    background: #12151c;
    border: 1px solid #1e2330;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
</style>
"""

st.markdown(CC_CSS, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# INITIALIZE
# ══════════════════════════════════════════════════════════════════════════════

_ensure_tables()
_seed_scholarships()

all_scholarships = _get_all_scholarships()
saved_ids = _get_saved_ids(_user_email)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 💰 Scholarship Dashboard")
st.markdown("**Billions of dollars in scholarships go unclaimed every year. Find yours here.**")

st.markdown("""
<div class="warning-box">
⚠️ <strong>WARNING:</strong> Avoid any scholarship that asks you to pay a fee upfront — those are <strong>scams</strong>.
All scholarships listed here are <strong>100% free to apply</strong>.
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STATS BAR
# ══════════════════════════════════════════════════════════════════════════════

total_schols = len(all_scholarships)
hbcu_count = sum(1 for s in all_scholarships if s.get("hbcu_only") or s.get("category") == "hbcu")
saved_count = len(saved_ids)

# Compute total funding (sum of amount_max, or amount_min if max is 0)
total_funding = 0
for s in all_scholarships:
    amt = s.get("amount_max") or s.get("amount_min") or 0
    total_funding += amt

if total_funding >= 1_000_000:
    funding_display = f"${total_funding/1_000_000:.1f}M+"
elif total_funding >= 1_000:
    funding_display = f"${total_funding/1_000:.0f}K+"
else:
    funding_display = f"${total_funding:,.0f}"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📋 Scholarships in Database", total_schols)
with col2:
    st.metric("💵 Total Funding Tracked", funding_display)
with col3:
    st.metric("🏫 HBCU-Specific", hbcu_count)
with col4:
    st.metric("💾 My Saved Scholarships", saved_count)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_browse, tab_saved, tab_local, tab_tips, tab_ai = st.tabs([
    "🔍 Browse Scholarships",
    "💾 My Saved List",
    "📍 Find Local Scholarships",
    "💡 Tips & Advice",
    "🤖 AI Matcher",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: BROWSE SCHOLARSHIPS
# ══════════════════════════════════════════════════════════════════════════════

with tab_browse:
    st.markdown("### 🔍 Filter Scholarships")

    # ── Filter row ────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        search_q = st.text_input("🔎 Search by name or provider", placeholder="e.g. Gates, HBCU, STEM...")
    with fc2:
        cat_opts = ["All", "National", "HBCU-Specific", "STEM", "Local"]
        cat_filter = st.selectbox("📂 Category", cat_opts)
    with fc3:
        gpa_opts = ["Any GPA", "2.0+ GPA", "2.5+ GPA", "3.0+ GPA", "3.5+ GPA"]
        gpa_filter = st.selectbox("📊 GPA Requirement", gpa_opts)

    fc4, fc5, fc6, fc7 = st.columns([2, 2, 2, 2])
    with fc4:
        focus_opts = ["All", "HBCU Only", "Minority Focus", "First-Generation", "Need-Based", "Merit-Based"]
        focus_filter = st.selectbox("🎯 Focus Area", focus_opts)
    with fc5:
        essay_opts = ["Any", "Essay Required", "No Essay"]
        essay_filter = st.selectbox("✍️ Essay", essay_opts)
    with fc6:
        renew_opts = ["Any", "Renewable", "One-Time"]
        renew_filter = st.selectbox("🔄 Renewable?", renew_opts)
    with fc7:
        month_names = ["Any Month", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        deadline_filter = st.selectbox("📅 Deadline Month", month_names)

    min_amount = st.slider("💵 Minimum Amount ($)", 0, 50000, 0, step=500,
                           help="Filter scholarships with a maximum award at or above this amount")

    st.markdown("---")

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = all_scholarships[:]

    if search_q.strip():
        q = search_q.strip().lower()
        filtered = [s for s in filtered if q in s["name"].lower() or q in s["provider"].lower()]

    if cat_filter == "National":
        filtered = [s for s in filtered if s["category"] == "national"]
    elif cat_filter == "HBCU-Specific":
        filtered = [s for s in filtered if s["category"] == "hbcu" or s.get("hbcu_only")]
    elif cat_filter == "STEM":
        filtered = [s for s in filtered if s.get("stem_focus")]
    elif cat_filter == "Local":
        filtered = [s for s in filtered if s["category"] == "local"]

    if focus_filter == "HBCU Only":
        filtered = [s for s in filtered if s.get("hbcu_only")]
    elif focus_filter == "Minority Focus":
        filtered = [s for s in filtered if s.get("minority_focus")]
    elif focus_filter == "First-Generation":
        filtered = [s for s in filtered if s.get("first_gen_focus")]
    elif focus_filter == "Need-Based":
        filtered = [s for s in filtered if s.get("need_based")]
    elif focus_filter == "Merit-Based":
        filtered = [s for s in filtered if s.get("merit_based")]

    if gpa_filter != "Any GPA":
        gpa_map = {"2.0+ GPA": 2.0, "2.5+ GPA": 2.5, "3.0+ GPA": 3.0, "3.5+ GPA": 3.5}
        max_gpa = gpa_map[gpa_filter]
        filtered = [s for s in filtered if s.get("gpa_min", 0) <= max_gpa]

    if essay_filter == "Essay Required":
        filtered = [s for s in filtered if s.get("essay_required")]
    elif essay_filter == "No Essay":
        filtered = [s for s in filtered if not s.get("essay_required")]

    if renew_filter == "Renewable":
        filtered = [s for s in filtered if s.get("renewable")]
    elif renew_filter == "One-Time":
        filtered = [s for s in filtered if not s.get("renewable")]

    if deadline_filter != "Any Month":
        month_idx = month_names.index(deadline_filter)
        filtered = [s for s in filtered if s.get("deadline_month") == month_idx]

    if min_amount > 0:
        filtered = [s for s in filtered
                    if (s.get("amount_max") or s.get("amount_min") or 0) >= min_amount]

    st.markdown(f"**Showing {len(filtered)} scholarship(s)**")

    if not filtered:
        st.info("No scholarships match your filters. Try broadening your search!")
    else:
        current_month = datetime.now().month

        for s in filtered:
            schol_id = s["id"]
            is_saved = schol_id in saved_ids

            # Deadline urgency
            dlm = s.get("deadline_month", 12)
            months_away = (dlm - current_month) % 12
            if months_away <= 2 and s.get("deadline", "Rolling") not in ("Rolling", "Varies", "Monthly"):
                deadline_cls = "schol-deadline"
                deadline_icon = "🔴"
            else:
                deadline_cls = "schol-deadline-ok"
                deadline_icon = "📅"

            # Build badge HTML
            badges_html = ""
            if s.get("hbcu_only") or s.get("category") == "hbcu":
                badges_html += '<span class="badge badge-hbcu">🏫 HBCU</span>'
            if s.get("stem_focus"):
                badges_html += '<span class="badge badge-stem">🔬 STEM</span>'
            if s.get("minority_focus"):
                badges_html += '<span class="badge badge-min">🌍 Minority</span>'
            if s.get("first_gen_focus"):
                badges_html += '<span class="badge badge-fg">🥇 First-Gen</span>'
            if s.get("need_based"):
                badges_html += '<span class="badge badge-need">❤️ Need-Based</span>'
            if s.get("merit_based"):
                badges_html += '<span class="badge badge-merit">⭐ Merit</span>'
            if s.get("essay_required"):
                badges_html += '<span class="badge badge-essay">✍️ Essay</span>'
            if s.get("renewable"):
                badges_html += '<span class="badge badge-renew">🔄 Renewable</span>'
            if s.get("category") == "local":
                badges_html += '<span class="badge badge-local">📍 Local</span>'

            gpa_text = ""
            if s.get("gpa_min", 0) > 0:
                gpa_text = f" · Min GPA: {s['gpa_min']}"

            st.markdown(f"""
<div class="schol-card">
    <div class="schol-name">{s['name']}</div>
    <div class="schol-provider">{s['provider']}</div>
    <span class="schol-amount">💰 {s['amount_display']}</span>
    <span class="{deadline_cls}">{deadline_icon} Deadline: {s['deadline']}</span>
    <div style="margin: 6px 0;">{badges_html}</div>
    <div class="schol-desc">{s['description']}</div>
    <div class="schol-elig">✅ Eligibility: {s['eligibility']}{gpa_text}</div>
</div>
""", unsafe_allow_html=True)

            btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
            with btn_col1:
                if s.get("url"):
                    st.link_button("🔗 Apply Now", s["url"], use_container_width=True)
            with btn_col2:
                if is_saved:
                    st.button("✅ Saved", key=f"saved_indicator_{schol_id}",
                              disabled=True, use_container_width=True)
                else:
                    if st.button("💾 Save", key=f"save_btn_{schol_id}",
                                 use_container_width=True):
                        result = _save_scholarship(_user_email, schol_id)
                        if result:
                            st.success(f"Saved '{s['name']}'!")
                            st.rerun()
                        else:
                            st.info("Already in your saved list.")
            with btn_col3:
                st.caption(f"#{schol_id}")

            st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: MY SAVED SCHOLARSHIPS
# ══════════════════════════════════════════════════════════════════════════════

with tab_saved:
    st.markdown("### 💾 My Saved Scholarships")
    st.caption("Track the scholarships you're researching, applying to, or have won!")

    saved_list = _get_saved_scholarships(_user_email)

    if not saved_list:
        st.markdown("""
<div class="info-box">
You haven't saved any scholarships yet! Head to the <strong>Browse Scholarships</strong> tab
and click <strong>💾 Save</strong> on any scholarship that looks like a good fit.
</div>
""", unsafe_allow_html=True)
    else:
        status_opts = ["saved", "researching", "applied", "won", "passed"]
        status_labels = {
            "saved": "📌 Saved",
            "researching": "🔍 Researching",
            "applied": "📤 Applied",
            "won": "🏆 Won!",
            "passed": "❌ Passed",
        }
        status_colors = {
            "saved": "#8892a4",
            "researching": "#60a5fa",
            "applied": "#fcd34d",
            "won": "#4CAF50",
            "passed": "#f87171",
        }

        # Summary stats
        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        counts = {s: 0 for s in status_opts}
        for sv in saved_list:
            counts[sv.get("save_status", "saved")] += 1
        sc1.metric("📌 Saved", counts["saved"])
        sc2.metric("🔍 Researching", counts["researching"])
        sc3.metric("📤 Applied", counts["applied"])
        sc4.metric("🏆 Won", counts["won"])
        sc5.metric("❌ Passed", counts["passed"])

        st.markdown("---")

        for sv in saved_list:
            saved_id = sv.get("saved_id") or sv.get("id")
            sv_status = sv.get("save_status", "saved")
            color = status_colors.get(sv_status, "#8892a4")
            label = status_labels.get(sv_status, sv_status.title())

            st.markdown(f"""
<div class="saved-card">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
        <div>
            <div class="schol-name">{sv['name']}</div>
            <div class="schol-provider">{sv['provider']}</div>
        </div>
        <div style="text-align:right;">
            <span class="schol-amount">💰 {sv['amount_display']}</span><br>
            <span style="color:{color}; font-size:0.82rem; font-weight:600;">{label}</span>
        </div>
    </div>
    <div class="schol-elig" style="margin-top:6px;">📅 Deadline: {sv['deadline']}</div>
</div>
""", unsafe_allow_html=True)

            exp_key = f"edit_saved_{saved_id}"
            with st.expander("Edit / Update", expanded=False):
                ecol1, ecol2 = st.columns([2, 2])
                with ecol1:
                    new_status_idx = status_opts.index(sv_status) if sv_status in status_opts else 0
                    new_status = st.selectbox(
                        "Status",
                        status_opts,
                        index=new_status_idx,
                        format_func=lambda x: status_labels.get(x, x.title()),
                        key=f"status_{saved_id}"
                    )
                    new_date = st.text_input(
                        "Applied Date (YYYY-MM-DD)",
                        value=sv.get("applied_date") or "",
                        key=f"date_{saved_id}",
                        placeholder="2025-01-15"
                    )
                with ecol2:
                    new_notes = st.text_area(
                        "Notes",
                        value=sv.get("save_notes") or "",
                        key=f"notes_{saved_id}",
                        placeholder="Add notes about your application, requirements, etc.",
                        height=100
                    )

                btn_a, btn_b, btn_c = st.columns([2, 1, 1])
                with btn_a:
                    if st.button("💾 Save Changes", key=f"update_{saved_id}", use_container_width=True):
                        _update_saved_scholarship(saved_id, new_status, new_notes, new_date)
                        st.success("Updated!")
                        st.rerun()
                with btn_b:
                    if sv.get("url"):
                        st.link_button("🔗 Apply", sv["url"], use_container_width=True)
                with btn_c:
                    if st.button("🗑️ Remove", key=f"remove_{saved_id}", use_container_width=True):
                        _remove_saved_scholarship(saved_id)
                        st.rerun()

        # Export summary
        st.markdown("---")
        st.markdown("#### 📊 Quick Export (Copy-Paste Spreadsheet)")
        rows_txt = "Name\tProvider\tAmount\tDeadline\tStatus\tNotes\n"
        for sv in saved_list:
            rows_txt += f"{sv['name']}\t{sv['provider']}\t{sv['amount_display']}\t{sv['deadline']}\t{sv.get('save_status','saved')}\t{sv.get('save_notes','')}\n"
        st.text_area("Copy this into Excel or Google Sheets:", rows_txt, height=180)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: HOW TO FIND LOCAL SCHOLARSHIPS
# ══════════════════════════════════════════════════════════════════════════════

with tab_local:
    st.markdown("### 📍 How to Find Local Scholarships")
    st.markdown("""
Local scholarships are often the **EASIEST to win** because fewer people apply.
A scholarship with 10 applicants is way better odds than one with 10,000!
Here's exactly how to find them:
""")

    st.markdown("""
<div class="tip-box">
<h4>Step-by-Step Guide to Finding Local Scholarships</h4>
<ol style="color: #c8d0dc; font-size: 0.88rem; line-height: 2;">
    <li><strong>Ask your school counselor</strong> — They usually have a list of local scholarships. Walk in and ask: "Do you have a list of scholarships for students from [your city]?"</li>
    <li><strong>Search Google</strong> — Try: "[Your City] scholarships for high school seniors" or "[Your County] college scholarships"</li>
    <li><strong>Check social media</strong> — Follow local businesses on Instagram and Twitter. Many post scholarship announcements there first!</li>
    <li><strong>Ask your parents' employers</strong> — Many large companies offer scholarships for employees' children. Your parent should check their HR portal or ask HR directly.</li>
    <li><strong>Check local community organizations</strong>:
        <ul>
            <li>Local church or religious organization</li>
            <li>NAACP local chapter</li>
            <li>Urban League chapter</li>
            <li>Local credit union (many offer scholarships to members)</li>
            <li>Parent-Teacher Association (PTA)</li>
        </ul>
    </li>
    <li><strong>Contact your community foundation</strong> — Most cities have one. Find yours at <a href="https://www.cof.org/page/community-foundation-locator" target="_blank" style="color:#60a5fa;">cof.org/community-foundation-locator</a></li>
    <li><strong>Local Rotary, Elks, Kiwanis clubs</strong> — These civic organizations almost always offer local scholarships. Search "[Your City] Rotary scholarship"</li>
    <li><strong>Your state's higher education commission</strong> — Every state has one. Search "[Your State] state scholarships for college"</li>
    <li><strong>Credit unions</strong> — If your family is a member of a credit union, check if they offer scholarships to members' children</li>
    <li><strong>Local hospitals and healthcare systems</strong> — Great for students interested in nursing, medicine, or healthcare careers</li>
</ol>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 🗺️ State-Level Resources")
    state_resources = {
        "Georgia": ("HOPE Scholarship", "https://www.gafutures.org/hope-state-aid-programs/hope-zell-miller-scholarships/", "Free tuition at GA public colleges for students with 3.0+ GPA"),
        "Florida": ("Florida Bright Futures", "https://www.floridastudentfinancialaidsg.org/SAPHome/SAPHome", "Merit-based scholarship for FL students attending FL colleges"),
        "Texas": ("Texas Grant", "https://www.collegeforalltexans.com/apps/financialaid/tofa2.cfm?ID=B401", "Need-based grant for Texas students attending Texas schools"),
        "California": ("Cal Grant", "https://www.csac.ca.gov/cal-grants", "State-funded grants for California students"),
        "New York": ("Excelsior Scholarship", "https://www.hesc.ny.gov/repay-your-loans/repaying-your-loans/excelsior-scholarship.html", "Free tuition at NY public colleges for families earning under $125K/year"),
        "Illinois": ("Illinois Monetary Award Program", "https://isac.org/students/during-college/financial-aid-and-scholarships/monetary-award-program/", "Need-based grants for Illinois students"),
        "North Carolina": ("NC Need-Based Scholarship", "https://www.cfnc.org/pay-for-college/nc-financial-aid/nc-need-based-scholarship/", "Financial assistance for NC students"),
        "Alabama": ("Alabama Student Grant", "https://ache.edu/student-information/financial-aid/", "Aid for students attending private Alabama colleges"),
        "Mississippi": ("Mississippi Eminent Scholars Grant", "https://www.mississippi.edu/ihl/financialaid.asp", "For high-achieving Mississippi students"),
        "Louisiana": ("TOPS Scholarship", "https://mylosfa.la.gov/students-parents/scholarships-grants/tops/", "Tuition payment for Louisiana students"),
    }

    sel_state = st.selectbox("Find resources for your state:", ["Select your state..."] + sorted(state_resources.keys()))
    if sel_state and sel_state != "Select your state...":
        prog_name, prog_url, prog_desc = state_resources[sel_state]
        st.markdown(f"""
<div class="info-box">
<strong>🎓 {prog_name}</strong><br>
{prog_desc}<br><br>
<a href="{prog_url}" target="_blank" style="color:#60a5fa;">→ Learn More & Apply</a>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="info-box">
<strong>💡 Pro Tip:</strong> Even if your state isn't listed above, every state has financial aid programs.
Search Google for "<strong>[Your State] state scholarship program</strong>" or visit your state's higher education agency website.
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: TIPS & ADVICE
# ══════════════════════════════════════════════════════════════════════════════

with tab_tips:
    st.markdown("### 💡 Scholarship Tips from Real Experience")

    st.markdown("""
<div class="tip-box">
<h4>🏆 Top Tips for Winning Scholarships</h4>
<ul>
    <li><strong>"Apply to as many as you can — Darrian applied to 40 and won 9."</strong> Volume matters. The more you apply, the more you win.</li>
    <li><strong>Don't get discouraged</strong> — even small amounts add up. $500 here, $1,000 there... that's textbooks, housing, or a semester!</li>
    <li><strong>Keep a spreadsheet</strong> with deadlines, requirements, essay prompts, and your application status. Organization = winning.</li>
    <li><strong>Many scholarships have very few applicants</strong> — especially local ones. A $2,000 local scholarship might only have 5 applicants. Those are great odds!</li>
    <li><strong>Start applying sophomore year</strong> — don't wait until senior year. Some scholarships are open to 9th-12th graders.</li>
    <li><strong>Reuse and recycle your essays</strong> — many prompts are similar. Write one great essay about your story and adapt it for different applications.</li>
    <li><strong>Get your letters of recommendation EARLY</strong> — ask teachers in September, not October. Give them 6+ weeks.</li>
    <li><strong>Submit before the deadline</strong> — never on the last day. Technical issues happen. Submit 3-5 days early.</li>
</ul>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 📋 Your Scholarship Checklist")
    st.markdown("Use this checklist to stay organized during scholarship season:")

    checklist_items = [
        ("📁 Create a dedicated folder", "Keep all scholarship documents, essays, and letters in one Google Drive or folder"),
        ("📊 Build a tracking spreadsheet", "Columns: Scholarship Name | Amount | Deadline | Requirements | Status | Notes"),
        ("✍️ Write your core essay", "Write one 500-word essay about your story, goals, and why you deserve a scholarship"),
        ("📸 Gather your documents", "Transcript, test scores, financial info (FAFSA), activities list, awards"),
        ("👨‍🏫 Ask for recommendation letters", "Ask at least 3 teachers/counselors — give them plenty of lead time"),
        ("🎯 Apply to at least 10 national scholarships", "Use the database above to find ones that match your profile"),
        ("🏘️ Apply to at least 5 local scholarships", "Ask your counselor and search your city/county"),
        ("📧 Set deadline reminders", "Add all deadlines to your phone calendar with reminders 1 week before"),
        ("✅ Follow up after applying", "Keep a record of what you submitted and check for confirmation emails"),
        ("🙏 Write thank-you notes", "If you win, always send a thank-you letter to the scholarship provider"),
    ]

    for i, (title, desc) in enumerate(checklist_items):
        with st.container():
            chk = st.checkbox(f"**{title}**", key=f"checklist_{i}")
            st.caption(f"   {desc}")

    st.markdown("---")

    st.markdown("### 🚨 Red Flags — Scholarship SCAMS to Avoid")
    st.markdown("""
<div class="warning-box">
<strong>⚠️ NEVER apply to a scholarship that:</strong><br><br>
• <strong>Charges you a fee</strong> to apply or to receive your award<br>
• Promises you a scholarship you "definitely qualify for" without you applying<br>
• Asks for your <strong>bank account or Social Security Number</strong> in the application<br>
• Sends you a check and asks you to send some back<br>
• Has a website with no contact information or a suspicious email address<br>
• Says you "won" a scholarship you never applied to<br><br>
<strong>Real scholarships are always FREE to apply and never ask for payment.</strong>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📅 Scholarship Season Timeline")

    timeline_data = [
        ("🏫 Freshman & Sophomore Year", "Start building your resume: clubs, volunteering, sports, jobs. Many scholarships look at all 4 years."),
        ("📚 Junior Year — Fall", "Take PSAT (qualifies for National Merit). Research scholarships. Start drafting your personal statement."),
        ("📝 Junior Year — Spring", "Apply to junior-year scholarships. Take SAT/ACT. Ask teachers about recommendation letters."),
        ("☀️ Summer Before Senior Year", "Write your core essay. Build your scholarship spreadsheet. Research local opportunities."),
        ("🍂 Senior Year — September/October", "Apply to early deadlines: Gates, QuestBridge, Coca-Cola. Most major scholarships open."),
        ("❄️ Senior Year — November/December", "FAFSA opens October 1 — complete it ASAP! Apply to remaining scholarships."),
        ("🌸 Senior Year — January/February", "More deadlines. Keep applying. Follow up on applications. HBCU scholarship deadlines."),
        ("🌱 Senior Year — March/April", "Award notifications start arriving. Apply to rolling scholarships. Spring deadlines."),
        ("🎓 May/June", "Commit to college! Thank scholarship providers. Prepare for college."),
    ]

    for period, desc in timeline_data:
        with st.expander(period, expanded=False):
            st.write(desc)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: AI SCHOLARSHIP MATCHER
# ══════════════════════════════════════════════════════════════════════════════

with tab_ai:
    st.markdown("### 🤖 AI Scholarship Matcher")
    st.markdown("""
Tell me about yourself and I'll analyze all scholarships in our database to find
your **best matches** — with specific reasons why each one fits YOU.
""")

    st.markdown("""
<div class="info-box">
💡 The more information you provide, the better your matches will be.
All info stays private and is only used for matching.
</div>
""", unsafe_allow_html=True)

    # Try to load existing profile
    existing_profile = _get_student_profile(_user_email)

    st.markdown("#### 📝 Your Profile")
    ai_col1, ai_col2 = st.columns(2)
    with ai_col1:
        ai_grade = st.selectbox("Current Grade", ["9th", "10th", "11th", "12th", "College Freshman"],
                                index=3,
                                help="What grade are you in?")
        ai_gpa = st.number_input("GPA (0.0 - 4.0)", min_value=0.0, max_value=4.0, value=3.0, step=0.1,
                                 help="Your current GPA")
        ai_state = st.text_input("Your State", value=existing_profile.get("state", ""),
                                 placeholder="e.g. Georgia")
        ai_major = st.text_input("Intended Major / Career Interest",
                                 value=existing_profile.get("intended_major", ""),
                                 placeholder="e.g. Computer Science, Nursing, Business")

    with ai_col2:
        ai_first_gen = st.checkbox("First-Generation College Student",
                                   value=bool(existing_profile.get("first_gen", False)),
                                   help="Would you be the first in your family to attend college?")
        ai_hbcu = st.checkbox("Interested in HBCUs",
                              value=bool(existing_profile.get("hbcu_interest", False)),
                              help="Are you considering attending an HBCU?")
        ai_need = st.checkbox("Financial Need",
                              value=bool(existing_profile.get("financial_need", False)),
                              help="Do you qualify for financial aid based on income?")
        ai_sat = st.text_input("SAT Score (optional)",
                               value=str(existing_profile.get("sat_score", "")) if existing_profile.get("sat_score") else "",
                               placeholder="e.g. 1200")
        ai_act = st.text_input("ACT Score (optional)",
                               value=str(existing_profile.get("act_score", "")) if existing_profile.get("act_score") else "",
                               placeholder="e.g. 24")

    ai_extra = st.text_area(
        "Anything else about yourself? (activities, background, special circumstances)",
        placeholder="e.g. I'm in band, I volunteer at a food bank, I'm a first-generation immigrant, I want to study medicine...",
        height=100
    )

    st.markdown("---")

    if "ai_scholarship_result" not in st.session_state:
        st.session_state["ai_scholarship_result"] = ""

    if st.button("🤖 Find My Best Scholarships", type="primary", use_container_width=True):
        profile_dict = {
            "current_grade": ai_grade,
            "gpa": ai_gpa,
            "state": ai_state,
            "intended_major": ai_major,
            "first_gen": int(ai_first_gen),
            "hbcu_interest": int(ai_hbcu),
            "financial_need": int(ai_need),
            "sat_score": ai_sat or None,
            "act_score": ai_act or None,
            "extra_info": ai_extra,
        }

        with st.spinner("🔍 Analyzing your profile against our scholarship database..."):
            result = _ai_match_scholarships(profile_dict, all_scholarships, _user_email)
            st.session_state["ai_scholarship_result"] = result

    if st.session_state.get("ai_scholarship_result"):
        st.markdown("---")
        st.markdown("#### 🎯 Your Personalized Scholarship Matches")
        st.markdown(st.session_state["ai_scholarship_result"])
        st.markdown("---")
        st.info("💡 After reviewing your matches, go to the **Browse Scholarships** tab to find these scholarships and click **💾 Save** to track them!")

    st.markdown("---")
    st.markdown("""
<div class="tip-box">
<h4>🔑 No AI Key? No Problem!</h4>
<p style="color:#c8d0dc; font-size:0.88rem;">
Even without the AI matcher, you can use the <strong>Browse Scholarships</strong> tab filters to find scholarships that match your profile:
</p>
<ul>
<li>Filter by <strong>Focus Area</strong> (HBCU, First-Gen, Need-Based, etc.)</li>
<li>Set your <strong>GPA requirement</strong> so you only see scholarships you qualify for</li>
<li>Filter by <strong>Category</strong> to see HBCU-specific or STEM scholarships</li>
<li>Use <strong>No Essay</strong> filter to find quick-apply opportunities</li>
</ul>
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#8892a4; font-size:0.78rem; padding:16px 0;">
💰 College Confused Scholarship Dashboard · All scholarships listed are free to apply<br>
Scholarship information is verified but deadlines change — always check the official website<br>
<strong>Remember: Billions in scholarships go unclaimed each year. Apply early, apply often.</strong>
</div>
""", unsafe_allow_html=True)
