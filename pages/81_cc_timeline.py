"""
College Confused — My Application Timeline Dashboard (Page 81)
==============================================================
Personalized college application timeline generator with:
  - One-time student profile setup wizard
  - Auto-generated milestone timeline based on grade/year
  - Progress tracking with completion checkboxes
  - Automation helpers (quick-action links)
  - Custom milestone builder
  - College list tracker (Safety / Likely / Reach)
  - Plain-language tips panel
"""

import streamlit as st
from datetime import datetime, date, timedelta
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="My Application Timeline — College Confused",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════════════════════
# ── DB Setup ──────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_student_profile (
        id {ai},
        user_email TEXT NOT NULL,
        grad_year INTEGER,
        current_grade TEXT,
        state TEXT,
        gpa REAL,
        sat_score INTEGER,
        act_score INTEGER,
        intended_major TEXT,
        first_gen INTEGER DEFAULT 0,
        hbcu_interest INTEGER DEFAULT 0,
        financial_need INTEGER DEFAULT 0,
        created_at TEXT {ts},
        updated_at TEXT {ts}
    )""")

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_timeline_milestones (
        id {ai},
        user_email TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        category TEXT DEFAULT 'general',
        due_date TEXT,
        completed INTEGER DEFAULT 0,
        priority TEXT DEFAULT 'normal',
        resource_link TEXT DEFAULT '',
        automation_type TEXT DEFAULT '',
        completed_at TEXT,
        created_at TEXT {ts}
    )""")

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_college_list (
        id {ai},
        user_email TEXT NOT NULL,
        college_name TEXT NOT NULL,
        college_type TEXT DEFAULT 'reach',
        applied INTEGER DEFAULT 0,
        accepted INTEGER DEFAULT 0,
        deadline TEXT,
        notes TEXT DEFAULT '',
        net_price REAL,
        created_at TEXT {ts}
    )""")

    conn.commit()
    conn.close()


_ensure_tables()


# ══════════════════════════════════════════════════════════════════════════════
# ── Data helpers ──────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _get_profile(user_email: str) -> dict | None:
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM cc_student_profile WHERE user_email = ? ORDER BY id DESC LIMIT 1", (user_email,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    if USE_POSTGRES:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    return dict(row)


def _save_profile(user_email: str, data: dict):
    conn = get_conn()
    # Delete old profile first (one per user)
    db_exec(conn, "DELETE FROM cc_student_profile WHERE user_email = ?", (user_email,))
    if USE_POSTGRES:
        db_exec(conn, """INSERT INTO cc_student_profile
            (user_email, grad_year, current_grade, state, gpa, sat_score, act_score,
             intended_major, first_gen, hbcu_interest, financial_need)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (user_email, data["grad_year"], data["current_grade"], data["state"],
             data["gpa"], data.get("sat_score"), data.get("act_score"),
             data["intended_major"], data["first_gen"], data["hbcu_interest"],
             data["financial_need"]))
    else:
        db_exec(conn, """INSERT INTO cc_student_profile
            (user_email, grad_year, current_grade, state, gpa, sat_score, act_score,
             intended_major, first_gen, hbcu_interest, financial_need)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_email, data["grad_year"], data["current_grade"], data["state"],
             data["gpa"], data.get("sat_score"), data.get("act_score"),
             data["intended_major"], data["first_gen"], data["hbcu_interest"],
             data["financial_need"]))
    conn.commit()
    conn.close()


def _get_milestones(user_email: str) -> list[dict]:
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM cc_timeline_milestones WHERE user_email = ? ORDER BY due_date ASC, id ASC", (user_email,))
    rows = cur.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in cur.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _toggle_milestone(milestone_id: int, completed: int):
    conn = get_conn()
    if completed:
        if USE_POSTGRES:
            db_exec(conn, "UPDATE cc_timeline_milestones SET completed=1, completed_at=to_char(now(),'YYYY-MM-DD HH24:MI:SS') WHERE id=%s", (milestone_id,))
        else:
            db_exec(conn, "UPDATE cc_timeline_milestones SET completed=1, completed_at=datetime('now') WHERE id=?", (milestone_id,))
    else:
        db_exec(conn, "UPDATE cc_timeline_milestones SET completed=0, completed_at=NULL WHERE id=?", (milestone_id,))
    conn.commit()
    conn.close()


def _delete_milestone(milestone_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM cc_timeline_milestones WHERE id=?", (milestone_id,))
    conn.commit()
    conn.close()


def _add_milestone(user_email: str, title: str, description: str, category: str,
                   due_date: str, priority: str, resource_link: str, automation_type: str = ""):
    conn = get_conn()
    db_exec(conn, """INSERT INTO cc_timeline_milestones
        (user_email, title, description, category, due_date, priority, resource_link, automation_type)
        VALUES (?,?,?,?,?,?,?,?)""",
        (user_email, title, description, category, due_date, priority, resource_link, automation_type))
    conn.commit()
    conn.close()


def _get_college_list(user_email: str) -> list[dict]:
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM cc_college_list WHERE user_email = ? ORDER BY college_type, college_name", (user_email,))
    rows = cur.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in cur.description]
        result = [dict(zip(cols, r)) for r in rows]
    else:
        result = [dict(r) for r in rows]
    conn.close()
    return result


def _add_college(user_email: str, college_name: str, college_type: str, deadline: str, notes: str):
    conn = get_conn()
    db_exec(conn, """INSERT INTO cc_college_list (user_email, college_name, college_type, deadline, notes)
        VALUES (?,?,?,?,?)""",
        (user_email, college_name, college_type, deadline, notes))
    conn.commit()
    conn.close()


def _update_college(college_id: int, applied: int, accepted: int, notes: str):
    conn = get_conn()
    db_exec(conn, "UPDATE cc_college_list SET applied=?, accepted=?, notes=? WHERE id=?",
            (applied, accepted, notes, college_id))
    conn.commit()
    conn.close()


def _delete_college(college_id: int):
    conn = get_conn()
    db_exec(conn, "DELETE FROM cc_college_list WHERE id=?", (college_id,))
    conn.commit()
    conn.close()


def _clear_milestones(user_email: str):
    conn = get_conn()
    db_exec(conn, "DELETE FROM cc_timeline_milestones WHERE user_email=?", (user_email,))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ── Timeline Generator ────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _date_str(year: int, month: int, day: int = 1) -> str:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return date(year, month, 28).isoformat()


def _generate_timeline(user_email: str, profile: dict):
    """Generate all milestones based on student grade/year. Clears existing first."""
    _clear_milestones(user_email)

    grade = profile.get("current_grade", "12th")
    gy    = profile.get("grad_year", date.today().year + 1)  # graduation year
    sy    = gy - 1  # senior year = grad_year - 1

    milestones = []

    # ── 9th / 10th Grade Early Planning ───────────────────────────────────────
    if grade in ("9th", "10th"):
        milestones += [
            ("Research what college is — Why go to college?",
             "Explore careers, earning potential, and what a college degree means for your future. "
             "Talk to family members who went to college, or watch videos on YouTube about college life.",
             "general", _date_str(sy - 2, 9), "high", "", ""),
            ("Create a free College Board Big Future account",
             "Go to bigfuture.collegeboard.org and create a free account. "
             "You can explore colleges, careers, and scholarships all in one place.",
             "general", _date_str(sy - 2, 9), "high",
             "https://bigfuture.collegeboard.org/", "bigfuture"),
            ("Start a college interest list",
             "Write down 5–10 colleges that interest you. Don't worry about being realistic yet — "
             "just dream big! You can narrow it down later. Use Big Future to explore.",
             "applications", _date_str(sy - 2, 10), "normal", "", ""),
            ("Focus on your GPA — most important thing you can do right now!",
             "Your GPA (grade point average) is the #1 thing colleges look at. "
             "Study hard, ask teachers for help early, and don't let your grades slip. "
             "A strong GPA opens doors to scholarships and better colleges.",
             "general", _date_str(sy - 2, 9), "high", "", ""),
            ("Join at least 1–2 extracurricular activities",
             "Colleges want to see you're involved outside of class. "
             "Join a club, sport, band, volunteer group, student government — anything you enjoy! "
             "Doing something consistently for years looks better than quitting after a month.",
             "general", _date_str(sy - 2, 10), "normal", "", ""),
            ("Take the PSAT in October (practice SAT)",
             "The PSAT is a practice version of the SAT — it's free or low-cost at your school. "
             "Signing up early helps you practice for the real SAT later. Ask your school counselor how to register.",
             "testing", _date_str(sy - 2, 10), "normal", "", ""),
        ]

    # ── 11th Grade ────────────────────────────────────────────────────────────
    if grade in ("9th", "10th", "11th"):
        yr11 = sy - 1
        milestones += [
            ("Register for the PSAT (October of 11th grade)",
             "The 11th-grade PSAT is the most important one — it's used for the National Merit Scholarship! "
             "High scorers can win up to $2,500. Register through your school counselor.",
             "testing", _date_str(yr11, 9), "high", "", ""),
            ("Start researching colleges seriously",
             "Go deeper on your college list. Look at: acceptance rates, average GPA/SAT, "
             "cost of attendance, financial aid, location, programs offered. Use College Board Big Future.",
             "applications", _date_str(yr11, 10), "normal",
             "https://bigfuture.collegeboard.org/", "bigfuture"),
            ("Visit college websites or attend virtual tours",
             "Most colleges have free virtual tours on their websites or on YouTube. "
             "Some also do free in-person visits. Get a feel for each school's campus culture.",
             "applications", _date_str(yr11, 11), "normal", "", ""),
            ("Begin narrowing down your college list to 10–20 schools",
             "By spring of 11th grade, you should have a list of about 10–20 colleges. "
             "Include: 3–4 Safety schools (you'll definitely get in), 5–8 Likely schools, "
             "and 3–5 Reach schools (dream schools). Balance is key!",
             "applications", _date_str(yr11, 12), "normal", "", ""),
            ("Register for the SAT (spring of 11th grade)",
             "The SAT is one of two main standardized tests for college admission (the other is the ACT). "
             "Register at collegeboard.org. Spring SAT dates are usually March, May, and June. "
             "You can take it multiple times — colleges usually take your best score!",
             "testing", _date_str(yr11, 2), "high",
             "https://www.collegeboard.org/", "sat"),
            ("Register for the ACT (spring of 11th grade)",
             "The ACT is the other main standardized test. Some students do better on the ACT than SAT — "
             "try both! Register at act.org. ACT dates are usually Feb, April, June, July, Sept.",
             "testing", _date_str(yr11, 2), "high",
             "http://www.act.org/", "act"),
            ("Start studying for SAT/ACT — Khan Academy is FREE!",
             "Khan Academy has free, official SAT prep made with College Board. "
             "Start studying 2–3 months before your test date. Even 20 minutes a day adds up. "
             "Go to khanacademy.org/SAT to create your free study plan.",
             "testing", _date_str(yr11, 1), "high",
             "https://www.khanacademy.org/SAT", "khan"),
            ("Ask teachers for letters of recommendation (give 1 month notice!)",
             "Most college applications require 2–3 letters of recommendation from teachers or counselors. "
             "Ask teachers who know you well and in subjects related to your major. "
             "IMPORTANT: Ask at least 1 full month before you need the letter — teachers are busy!",
             "applications", _date_str(yr11, 4), "high", "", ""),
            ("Begin thinking about your Common App personal essay topic",
             "The Common App personal essay is 650 words about YOU. Start brainstorming topics now. "
             "Great essays are personal, specific, and show who you are. "
             "Possible topics: a challenge you overcame, a passion, a person who influenced you.",
             "essays", _date_str(yr11, 5), "normal", "", ""),
        ]

    # ── Summer Before Senior Year ──────────────────────────────────────────────
    if grade in ("9th", "10th", "11th", "12th"):
        summer = sy  # summer before senior year is the same calendar year as senior year
        milestones += [
            ("Finalize college list (10–20 schools)",
             "By August, your college list should be finalized. Make sure you have a good mix: "
             "Safety (schools you're confident about), Likely (good match), and Reach (dream schools). "
             "Having 3–5 of each type is a solid strategy.",
             "applications", _date_str(summer, 7), "high", "", ""),
            ("Create your Common App account at commonapp.org",
             "The Common App opens August 1 every year. Create your account early so you're ready. "
             "The Common App lets you apply to 1,000+ colleges with ONE application. "
             "Most colleges use it — this is the most important application tool you have.",
             "applications", _date_str(summer, 8, 1), "high",
             "https://www.commonapp.org/", "commonapp"),
            ("Draft your Common App personal essay",
             "Start drafting your 650-word personal essay this summer. Write multiple drafts. "
             "Get feedback from a teacher, counselor, or trusted adult. "
             "Your essay should be YOUR voice — don't let someone else write it for you!",
             "essays", _date_str(summer, 8), "high", "", ""),
            ("Request official transcripts from your school counselor",
             "Colleges need your official transcripts (your complete grade history). "
             "Ask your school counselor to send transcripts to each college on your list. "
             "Some schools charge a small fee. Start this process early — counselors get busy in fall!",
             "applications", _date_str(summer, 8), "high", "", ""),
            ("Research scholarships you'll apply to — make a list!",
             "Scholarships are FREE money for college that you don't have to pay back. "
             "Search for local scholarships (from your community, church, employer), "
             "national scholarships, and college-specific scholarships. "
             "Write down the name, deadline, and requirements for each one.",
             "financial_aid", _date_str(summer, 8), "high", "", ""),
            ("FAFSA prep — gather parent/guardian financial documents",
             "The FAFSA (Free Application for Federal Student Aid) is how you apply for federal financial aid. "
             "To complete it, you'll need: Social Security numbers, tax returns from last year, "
             "bank account balances, and investment info. Gather these documents now — "
             "the FAFSA opens October 1 and you want to submit it ASAP!",
             "financial_aid", _date_str(summer, 9), "high",
             "https://studentaid.gov/h/apply-for-aid/fafsa", "fafsa"),
        ]

    # ── Senior Year Fall ───────────────────────────────────────────────────────
    if grade in ("11th", "12th"):
        milestones += [
            ("Finalize and submit Early Action applications (Nov 1–15 deadlines)",
             "Early Action (EA) means you apply early (usually November 1 or 15) and hear back in December. "
             "It's non-binding — you don't have to go if accepted. It gives you more time to compare offers. "
             "Highly recommended if your grades and scores are ready!",
             "applications", _date_str(sy, 11, 1), "high", "", ""),
            ("Complete and submit the FAFSA — opens October 1, do this ASAP!",
             "The FAFSA opens October 1. Submit it as SOON as possible — "
             "financial aid is first-come, first-served at many schools. "
             "The FAFSA determines your eligibility for Pell Grants, federal loans, and work-study. "
             "Go to studentaid.gov — it takes about 30–60 minutes to complete.",
             "financial_aid", _date_str(sy, 10, 1), "high",
             "https://studentaid.gov/h/apply-for-aid/fafsa", "fafsa"),
            ("Send official SAT/ACT scores to colleges",
             "Colleges need your official scores sent directly from College Board (SAT) or ACT. "
             "This is different from self-reported scores on your application. "
             "Check each college's requirements and send scores before application deadlines.",
             "testing", _date_str(sy, 10), "high",
             "https://www.collegeboard.org/", "sat"),
            ("Follow up on teacher recommendations",
             "Remind your teachers (politely!) about your recommendation letters. "
             "Give them a reminder email or note with: your application deadlines, "
             "list of colleges you're applying to, and a brief note about your goals.",
             "applications", _date_str(sy, 10), "normal", "", ""),
            ("Apply to all scholarships with fall deadlines",
             "Check your scholarship list and submit all applications with October or November deadlines. "
             "For each scholarship, you'll need: transcript, essay(s), sometimes letters of recommendation. "
             "Don't skip any — even $500 adds up!",
             "financial_aid", _date_str(sy, 11), "high", "", ""),
            ("Write supplemental essays for each college",
             "Many colleges (especially selective ones) require extra essays beyond the Common App essay. "
             "These are called 'supplemental essays.' Common prompts: 'Why our school?' 'Why your major?' "
             "Research each college and write specific, genuine answers.",
             "essays", _date_str(sy, 10), "high", "", ""),
        ]

    # ── Senior Year Winter ──────────────────────────────────────────────────────
    if grade == "12th":
        milestones += [
            ("Check application portals for missing documents",
             "After submitting applications, check each college's applicant portal. "
             "Many schools will email you if something is missing (transcript, test scores, recs). "
             "Missing documents can delay or hurt your application — check portals weekly in December!",
             "applications", _date_str(sy, 12), "high", "", ""),
            ("Apply to Regular Decision colleges (Jan–Feb deadlines)",
             "Regular Decision (RD) deadlines are usually January 1–February 1. "
             "Submit all your Regular Decision applications before their deadlines. "
             "Double-check that all supporting documents (transcript, recs, scores) have been sent.",
             "applications", _date_str(gy, 1, 15), "high", "", ""),
            ("Apply to scholarships with winter deadlines (December–February)",
             "Continue applying for scholarships! Many have December, January, and February deadlines. "
             "Local community scholarships often have smaller pools of applicants — higher odds of winning!",
             "financial_aid", _date_str(gy, 1), "normal", "", ""),
            ("Review financial aid offers as acceptance letters arrive",
             "Early Action acceptances arrive in December. Financial aid award letters come separately. "
             "When you get an award letter, look for: grants (free money), loans (must repay), and work-study. "
             "Calculate your net price = tuition + room/board - grants/scholarships.",
             "financial_aid", _date_str(gy, 1), "normal", "", ""),
            ("Complete CSS Profile if required",
             "The CSS Profile is a more detailed financial aid form used by private colleges. "
             "Check if any of your colleges require it (usually private schools and some HBCUs). "
             "It costs $25 for the first school, $16 for each additional. Fee waivers available!",
             "financial_aid", _date_str(sy, 12), "normal",
             "https://bigfuture.collegeboard.org/", "bigfuture"),
        ]

    # ── Senior Year Spring ─────────────────────────────────────────────────────
    if grade == "12th":
        milestones += [
            ("Compare financial aid award letters from accepted schools",
             "By March, you should have acceptance letters and financial aid offers from most schools. "
             "Compare them side by side. Look at the NET PRICE (after all aid), not just the sticker price. "
             "A school that costs more might give you more aid — making it actually cheaper!",
             "financial_aid", _date_str(gy, 3), "high", "", ""),
            ("Make your final college decision by May 1 (National Decision Day)",
             "May 1 is National Decision Day — the deadline to commit to one school. "
             "You'll submit a deposit (usually $200–$500) to hold your spot. "
             "Before deciding: compare net price, visit if possible, trust your gut!",
             "applications", _date_str(gy, 5, 1), "high", "", ""),
            ("Submit your enrollment deposit to your chosen college",
             "Once you've decided, submit your enrollment deposit to secure your spot in the class. "
             "Make sure to decline all other offers politely — other students are on waitlists waiting!",
             "applications", _date_str(gy, 5, 1), "high", "", ""),
            ("Apply for on-campus housing",
             "Many colleges open housing applications in spring. Apply ASAP — "
             "popular dorms fill up fast! First-year students usually must live on campus anyway.",
             "applications", _date_str(gy, 4), "normal", "", ""),
            ("Fill out any remaining scholarship applications",
             "Some scholarships have April or May deadlines. Keep applying! "
             "Even a $250 scholarship reduces what you need to borrow in loans.",
             "financial_aid", _date_str(gy, 4), "normal", "", ""),
            ("🎉 Celebrate! You did it! Congrats, future college student!",
             "You've worked SO hard to get here. Take a moment to celebrate! "
             "Tell your family. Thank your teachers and counselors. "
             "Then start getting excited — college is going to be amazing!",
             "general", _date_str(gy, 5, 15), "normal", "", ""),
        ]

    # ── Insert all milestones ──────────────────────────────────────────────────
    for title, desc, category, due_date, priority, resource_link, automation_type in milestones:
        _add_milestone(user_email, title, desc, category, due_date, priority, resource_link, automation_type)


# ══════════════════════════════════════════════════════════════════════════════
# ── Page Header ───────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

user       = st.session_state.get("user", {})
user_email = user.get("email", "")

st.title("📅 My Application Timeline")
st.caption("Your personalized college application roadmap — everything you need to do, in order.")

profile = _get_profile(user_email)

# ══════════════════════════════════════════════════════════════════════════════
# ── FEATURE 1: STUDENT PROFILE SETUP WIZARD ──────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

if profile is None:
    st.markdown("---")
    st.markdown("## 👋 Let's Set Up Your Dashboard!")
    st.info(
        "Answer a few quick questions so we can build your **personalized college application timeline**. "
        "This only takes 2 minutes!"
    )

    with st.form("profile_setup_form"):
        col1, col2 = st.columns(2)
        with col1:
            current_grade = st.selectbox(
                "What grade are you in right now? *",
                ["9th", "10th", "11th", "12th", "College"],
                help="Select your current grade level"
            )
            current_year = date.today().year
            grad_year_options = list(range(current_year, current_year + 6))
            grad_year = st.selectbox(
                "What year will you graduate high school? *",
                grad_year_options,
                help="The year you walk across the stage!"
            )
            state = st.text_input(
                "What state do you live in?",
                placeholder="e.g. Georgia, California, Texas",
                help="Some scholarships and programs are state-specific"
            )
            intended_major = st.text_input(
                "What do you want to study in college?",
                placeholder="e.g. Computer Science, Nursing, Business, Undecided",
                help="You can always change this later!"
            )
        with col2:
            gpa = st.number_input(
                "Current GPA (0.0 – 4.0)",
                min_value=0.0, max_value=5.0, value=3.0, step=0.1,
                help="Your current unweighted or weighted GPA"
            )
            sat_score = st.number_input(
                "SAT Score (optional, 400–1600)",
                min_value=0, max_value=1600, value=0, step=10,
                help="Leave as 0 if you haven't taken it yet"
            )
            act_score = st.number_input(
                "ACT Score (optional, 1–36)",
                min_value=0, max_value=36, value=0, step=1,
                help="Leave as 0 if you haven't taken it yet"
            )
            first_gen = st.radio(
                "Are you a first-generation college student?",
                ["No", "Yes"],
                help="First-gen means neither of your parents/guardians attended a 4-year college"
            )
            hbcu_interest = st.radio(
                "Interested in Historically Black Colleges and Universities (HBCUs)?",
                ["No", "Yes"],
                help="HBCUs are colleges founded for African-American students — many have amazing programs and scholarships!"
            )
            financial_need = st.radio(
                "Do you have financial need for college?",
                ["No", "Yes"],
                help="If your family has limited income, you may qualify for need-based aid like Pell Grants"
            )

        st.markdown("---")
        submitted = st.form_submit_button("🚀 Build My Timeline!", type="primary", use_container_width=True)

        if submitted:
            if not current_grade:
                st.error("Please select your current grade.")
            else:
                profile_data = {
                    "grad_year":     grad_year,
                    "current_grade": current_grade,
                    "state":         state.strip(),
                    "gpa":           gpa,
                    "sat_score":     sat_score if sat_score > 0 else None,
                    "act_score":     act_score if act_score > 0 else None,
                    "intended_major": intended_major.strip(),
                    "first_gen":     1 if first_gen == "Yes" else 0,
                    "hbcu_interest": 1 if hbcu_interest == "Yes" else 0,
                    "financial_need": 1 if financial_need == "Yes" else 0,
                }
                _save_profile(user_email, profile_data)
                _generate_timeline(user_email, profile_data)
                st.success("✅ Your personalized timeline has been created! Scroll down to see your milestones.")
                st.rerun()

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# ── Profile loaded — show dashboard ──────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

milestones = _get_milestones(user_email)
total      = len(milestones)
completed  = sum(1 for m in milestones if m["completed"])
pct        = int((completed / total * 100)) if total > 0 else 0

today_str  = date.today().isoformat()
in30_str   = (date.today() + timedelta(days=30)).isoformat()
upcoming   = sum(1 for m in milestones if not m["completed"] and m.get("due_date") and today_str <= m["due_date"] <= in30_str)
overdue    = sum(1 for m in milestones if not m["completed"] and m.get("due_date") and m["due_date"] < today_str)


# ── Profile banner ─────────────────────────────────────────────────────────────
with st.expander("👤 My Profile", expanded=False):
    pc1, pc2, pc3, pc4 = st.columns(4)
    pc1.metric("Grade", profile.get("current_grade", "—"))
    pc2.metric("Graduating", profile.get("grad_year", "—"))
    pc3.metric("GPA", f"{profile.get('gpa', 0):.1f}")
    pc4.metric("Major", profile.get("intended_major", "Undecided") or "Undecided")

    flags = []
    if profile.get("first_gen"):
        flags.append("🎓 First-Generation Student")
    if profile.get("hbcu_interest"):
        flags.append("🏫 Interested in HBCUs")
    if profile.get("financial_need"):
        flags.append("💵 Financial Need")
    if profile.get("sat_score"):
        flags.append(f"📝 SAT: {profile['sat_score']}")
    if profile.get("act_score"):
        flags.append(f"📋 ACT: {profile['act_score']}")
    if flags:
        st.markdown("  ·  ".join(flags))

    st.markdown("---")
    col_reset1, col_reset2 = st.columns([3, 1])
    with col_reset2:
        if st.button("🔄 Reset Profile & Timeline", help="Delete your profile and start over"):
            _clear_milestones(user_email)
            conn = get_conn()
            db_exec(conn, "DELETE FROM cc_student_profile WHERE user_email=?", (user_email,))
            conn.commit()
            conn.close()
            st.rerun()
    with col_reset1:
        if st.button("🔁 Regenerate Timeline (keeps profile)", help="Re-create all auto milestones from scratch"):
            _generate_timeline(user_email, profile)
            st.success("Timeline regenerated!")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ── FEATURE 2: DASHBOARD VIEW ─────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.subheader("📊 Your Progress")

k1, k2, k3, k4 = st.columns(4)
k1.metric("📋 Total Milestones", total)
k2.metric("✅ Completed",        completed)
k3.metric("📅 Upcoming (30d)",   upcoming)
k4.metric("⚠️ Overdue",          overdue, delta_color="inverse" if overdue > 0 else "normal")

st.progress(pct / 100, text=f"{pct}% Complete — {completed} of {total} milestones done")

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_timeline, tab_add, tab_colleges, tab_tips = st.tabs([
    "📅 My Timeline",
    "➕ Add Milestone",
    "🏫 College List",
    "💡 Tips & Glossary",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Timeline / Milestone Dashboard
# ══════════════════════════════════════════════════════════════════════════════
with tab_timeline:
    # ── Category filter ────────────────────────────────────────────────────────
    CATEGORIES = ["All", "Applications", "Testing", "Financial Aid", "Scholarships", "Essays", "General"]
    cat_filter = st.selectbox("Filter by category:", CATEGORIES, key="cat_filter")
    show_completed = st.checkbox("Show completed milestones", value=False, key="show_completed")

    cat_map = {
        "Applications":  "applications",
        "Testing":       "testing",
        "Financial Aid": "financial_aid",
        "Scholarships":  "scholarships",
        "Essays":        "essays",
        "General":       "general",
    }

    filtered = milestones
    if cat_filter != "All":
        filtered = [m for m in milestones if m.get("category") == cat_map.get(cat_filter, cat_filter.lower())]
    if not show_completed:
        filtered = [m for m in filtered if not m["completed"]]

    if not filtered:
        if show_completed or cat_filter == "All":
            st.success("🎉 All milestones in this category are done! Amazing work!")
        else:
            st.info("No milestones to show. Try enabling 'Show completed milestones' or selecting a different category.")
    else:
        # ── Group by section ───────────────────────────────────────────────────
        overdue_list   = [m for m in filtered if not m["completed"] and m.get("due_date") and m["due_date"] < today_str]
        upcoming_list  = [m for m in filtered if not m["completed"] and m.get("due_date") and today_str <= m["due_date"] <= in30_str]
        future_list    = [m for m in filtered if not m["completed"] and (not m.get("due_date") or m["due_date"] > in30_str)]
        done_list      = [m for m in filtered if m["completed"]]

        AUTOMATION_LINKS = {
            "sat":        ("📝 Register for SAT",         "https://www.collegeboard.org/"),
            "act":        ("📋 Register for ACT",          "http://www.act.org/"),
            "commonapp":  ("📄 Create Common App Account", "https://www.commonapp.org/"),
            "fafsa":      ("💵 Start FAFSA",               "https://studentaid.gov/h/apply-for-aid/fafsa"),
            "khan":       ("📚 Khan Academy SAT Prep",     "https://www.khanacademy.org/SAT"),
            "bigfuture":  ("🌐 College Board Big Future",  "https://bigfuture.collegeboard.org/"),
        }

        CATEGORY_EMOJI = {
            "applications": "📋",
            "testing":       "📝",
            "financial_aid": "💰",
            "scholarships":  "🎓",
            "essays":        "✍️",
            "general":       "⭐",
        }

        def _render_milestone_card(m: dict, section_key: str):
            mid      = m["id"]
            done     = bool(m["completed"])
            due_raw  = m.get("due_date", "")
            cat_em   = CATEGORY_EMOJI.get(m.get("category", "general"), "⭐")
            priority_badge = "🔴 High Priority" if m.get("priority") == "high" else ""

            # Due date color
            due_color = "#8892a4"
            due_label = ""
            if due_raw:
                try:
                    due_dt = datetime.strptime(due_raw, "%Y-%m-%d").date()
                    if not done and due_dt < date.today():
                        due_color = "#ef4444"
                        due_label = f"⚠️ Overdue — {due_dt.strftime('%b %d, %Y')}"
                    elif not done and due_dt <= date.today() + timedelta(days=7):
                        due_color = "#f97316"
                        due_label = f"🔔 Due soon — {due_dt.strftime('%b %d, %Y')}"
                    else:
                        due_label = f"📅 Due {due_dt.strftime('%b %d, %Y')}"
                except Exception:
                    due_label = f"📅 {due_raw}"

            with st.container():
                cc1, cc2 = st.columns([11, 1])
                with cc1:
                    title_style = "text-decoration: line-through; opacity: 0.5;" if done else ""
                    st.markdown(
                        f"<div style='{title_style}'>"
                        f"<strong>{cat_em} {m['title']}</strong>"
                        + (f" &nbsp; <span style='color:#ef4444; font-size:0.78rem;'>{priority_badge}</span>" if priority_badge and not done else "")
                        + "</div>",
                        unsafe_allow_html=True
                    )
                    if due_label:
                        st.markdown(
                            f"<div style='color:{due_color}; font-size:0.82rem; margin-top:2px;'>{due_label}</div>",
                            unsafe_allow_html=True
                        )
                    if m.get("description"):
                        with st.expander("ℹ️ More info", expanded=False):
                            st.markdown(m["description"])

                    # Automation quick-action buttons
                    auto_type = m.get("automation_type", "")
                    if auto_type and auto_type in AUTOMATION_LINKS:
                        label, url = AUTOMATION_LINKS[auto_type]
                        st.link_button(f"🚀 Quick Action: {label}", url)
                    elif m.get("resource_link"):
                        st.link_button("🔗 Open Resource", m["resource_link"])

                with cc2:
                    checkbox_val = st.checkbox(
                        "Done",
                        value=done,
                        key=f"ms_check_{section_key}_{mid}",
                        label_visibility="collapsed"
                    )
                    if checkbox_val != done:
                        _toggle_milestone(mid, 1 if checkbox_val else 0)
                        st.rerun()
                    if st.button("🗑️", key=f"ms_del_{section_key}_{mid}", help="Delete milestone"):
                        _delete_milestone(mid)
                        st.rerun()
            st.divider()

        # ── Overdue section ────────────────────────────────────────────────────
        if overdue_list:
            st.markdown("### ⚠️ Overdue")
            for m in overdue_list:
                _render_milestone_card(m, "overdue")

        # ── Upcoming section ───────────────────────────────────────────────────
        if upcoming_list:
            st.markdown("### 🔔 Due in the Next 30 Days")
            for m in upcoming_list:
                _render_milestone_card(m, "upcoming")

        # ── Future section ─────────────────────────────────────────────────────
        if future_list:
            st.markdown("### 📋 All Other Milestones")
            for m in future_list:
                _render_milestone_card(m, "future")

        # ── Completed section ──────────────────────────────────────────────────
        if done_list and show_completed:
            st.markdown("### ✅ Completed")
            for m in done_list:
                _render_milestone_card(m, "done")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Add Custom Milestone
# ══════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.subheader("➕ Add a Custom Milestone")
    st.caption("Add anything not already on your timeline — a campus visit, a specific scholarship, an interview, etc.")

    with st.form("add_milestone_form"):
        am_col1, am_col2 = st.columns(2)
        with am_col1:
            ms_title = st.text_input("Milestone Title *", placeholder="e.g. Apply to XYZ Scholarship")
            ms_category = st.selectbox(
                "Category *",
                ["general", "applications", "testing", "financial_aid", "scholarships", "essays"],
                format_func=lambda x: {
                    "general": "⭐ General",
                    "applications": "📋 Applications",
                    "testing": "📝 Testing",
                    "financial_aid": "💰 Financial Aid",
                    "scholarships": "🎓 Scholarships",
                    "essays": "✍️ Essays",
                }[x]
            )
            ms_priority = st.selectbox("Priority", ["normal", "high"], format_func=lambda x: "🔴 High" if x == "high" else "⚪ Normal")
        with am_col2:
            ms_due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30))
            ms_resource = st.text_input("Resource Link (optional)", placeholder="https://...")
            ms_desc = st.text_area("Description (optional)", placeholder="Notes about this milestone...", height=100)

        add_sub = st.form_submit_button("➕ Add Milestone", type="primary", use_container_width=True)
        if add_sub:
            if not ms_title.strip():
                st.error("Please enter a title for your milestone.")
            else:
                resource_link = ms_resource.strip() if ms_resource.strip().startswith("http") else ""
                _add_milestone(
                    user_email,
                    ms_title.strip(),
                    ms_desc.strip(),
                    ms_category,
                    ms_due_date.isoformat(),
                    ms_priority,
                    resource_link,
                )
                st.success(f"✅ Added: '{ms_title.strip()}'")
                st.rerun()

    # ── Quick-action resource links ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🚀 Quick Access — Important Links")
    st.caption("Bookmark these — you'll use them a lot during your college search!")

    qa_col1, qa_col2, qa_col3 = st.columns(3)
    with qa_col1:
        st.link_button("📝 Register for SAT (College Board)", "https://www.collegeboard.org/", use_container_width=True)
        st.link_button("📚 Khan Academy SAT Prep (FREE)", "https://www.khanacademy.org/SAT", use_container_width=True)
    with qa_col2:
        st.link_button("📋 Register for ACT", "http://www.act.org/", use_container_width=True)
        st.link_button("💵 Start FAFSA (studentaid.gov)", "https://studentaid.gov/h/apply-for-aid/fafsa", use_container_width=True)
    with qa_col3:
        st.link_button("📄 Create Common App Account", "https://www.commonapp.org/", use_container_width=True)
        st.link_button("🌐 College Board Big Future", "https://bigfuture.collegeboard.org/", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — College List Tracker
# ══════════════════════════════════════════════════════════════════════════════
with tab_colleges:
    st.subheader("🏫 My College List")
    st.caption("Track every school on your list. Color coded: 🟢 Safety · 🟡 Likely · 🔴 Reach")

    college_list = _get_college_list(user_email)

    # ── Summary stats ──────────────────────────────────────────────────────────
    if college_list:
        safety_count  = sum(1 for c in college_list if c["college_type"] == "safety")
        likely_count  = sum(1 for c in college_list if c["college_type"] == "likely")
        reach_count   = sum(1 for c in college_list if c["college_type"] == "reach")
        applied_count = sum(1 for c in college_list if c["applied"])
        accepted_count= sum(1 for c in college_list if c["accepted"])

        cs1, cs2, cs3, cs4, cs5 = st.columns(5)
        cs1.metric("🟢 Safety",  safety_count)
        cs2.metric("🟡 Likely",  likely_count)
        cs3.metric("🔴 Reach",   reach_count)
        cs4.metric("✅ Applied", applied_count)
        cs5.metric("🎉 Accepted", accepted_count)

        # ── Recommendation box ───────────────────────────────────────────────
        total_colleges = len(college_list)
        if total_colleges > 0:
            if safety_count == 0:
                st.warning("⚠️ You have no Safety schools! Add at least 2–3 schools where you're confident you'll be accepted.")
            elif likely_count == 0:
                st.warning("⚠️ You have no Likely schools! Add some schools that are a good match for your stats.")
            elif reach_count == 0:
                st.info("💡 Consider adding 1–2 Reach schools — dream big! You might surprise yourself.")
            elif safety_count >= 2 and likely_count >= 3 and reach_count >= 2:
                st.success(f"✅ Great balance! {total_colleges} schools total with a healthy mix of Safety, Likely, and Reach.")

        st.markdown("---")

        # ── College cards ──────────────────────────────────────────────────────
        TYPE_COLORS = {"safety": "#22c55e", "likely": "#eab308", "reach": "#ef4444"}
        TYPE_LABELS = {"safety": "🟢 Safety", "likely": "🟡 Likely", "reach": "🔴 Reach"}

        for college in college_list:
            cid        = college["id"]
            ctype      = college.get("college_type", "reach")
            color      = TYPE_COLORS.get(ctype, "#888")
            type_label = TYPE_LABELS.get(ctype, "🔴 Reach")

            with st.container():
                cl1, cl2, cl3, cl4, cl5 = st.columns([4, 2, 1, 1, 1])
                with cl1:
                    st.markdown(
                        f"<div style='font-size:1rem; font-weight:700;'>"
                        f"<span style='color:{color};'>{type_label}</span>  "
                        f"{college['college_name']}</div>",
                        unsafe_allow_html=True
                    )
                    if college.get("deadline"):
                        st.caption(f"Deadline: {college['deadline']}")
                    if college.get("notes"):
                        st.caption(college["notes"])
                with cl2:
                    st.caption("Status")
                    applied_new  = st.checkbox("Applied",  value=bool(college["applied"]),  key=f"applied_{cid}")
                    accepted_new = st.checkbox("Accepted", value=bool(college["accepted"]), key=f"accepted_{cid}")
                    if applied_new != bool(college["applied"]) or accepted_new != bool(college["accepted"]):
                        _update_college(cid, 1 if applied_new else 0, 1 if accepted_new else 0, college.get("notes",""))
                        st.rerun()
                with cl3:
                    if college.get("net_price"):
                        st.metric("Net Price", f"${college['net_price']:,.0f}")
                with cl4:
                    st.write("")
                    st.write("")
                    if st.button("🗑️", key=f"del_college_{cid}", help="Remove from list"):
                        _delete_college(cid)
                        st.rerun()
                with cl5:
                    pass
            st.divider()

    else:
        st.info("No colleges added yet. Use the form below to start building your list!")

    # ── Add college form ────────────────────────────────────────────────────────
    st.markdown("### ➕ Add a College")
    with st.form("add_college_form"):
        cf1, cf2 = st.columns(2)
        with cf1:
            new_college_name = st.text_input("College Name *", placeholder="e.g. Spelman College")
            new_college_type = st.selectbox(
                "Type *",
                ["safety", "likely", "reach"],
                format_func=lambda x: {
                    "safety": "🟢 Safety (I'm confident I'll get in)",
                    "likely": "🟡 Likely (Good match for my stats)",
                    "reach": "🔴 Reach (Dream school / selective)",
                }[x]
            )
        with cf2:
            new_deadline = st.text_input("Application Deadline", placeholder="e.g. January 1, 2026")
            new_notes    = st.text_input("Notes", placeholder="e.g. HBCU, requires CSS Profile")

        add_col_sub = st.form_submit_button("➕ Add College", type="primary", use_container_width=True)
        if add_col_sub:
            if not new_college_name.strip():
                st.error("Please enter a college name.")
            else:
                _add_college(user_email, new_college_name.strip(), new_college_type, new_deadline.strip(), new_notes.strip())
                st.success(f"✅ Added {new_college_name.strip()} to your list!")
                st.rerun()

    # ── Tips for building a college list ──────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💡 Tips for Building Your College List")
    st.markdown("""
**How many colleges should I apply to?**
Most counselors recommend applying to **10–15 colleges** total. More than 20 is usually too many to manage well.

**What is a Safety school?**
A Safety school is one where your GPA and test scores are **above** their average — you're very likely to get in. Always apply to 2–3 safeties!

**What is a Likely school?**
A Likely school is one where your stats are **right in the middle** of their accepted students. These are your best-match schools.

**What is a Reach school?**
A Reach school is one where your stats are **below** their average — but you still have a shot. Dream big! Apply to 2–3 reaches.
""")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Tips & Glossary
# ══════════════════════════════════════════════════════════════════════════════
with tab_tips:
    st.subheader("💡 College Application Tips & Plain-Language Guide")
    st.caption("Never heard these terms before? No problem — here's what everything means.")

    st.markdown("---")

    # ── What is Early Action? ─────────────────────────────────────────────────
    with st.expander("📅 What is Early Action (EA)?", expanded=True):
        st.markdown("""
**Early Action** means you apply to a college *early* — usually with a deadline of **November 1 or November 15** — 
and you get your decision back in **December**, way before most applicants.

**The best part?** Early Action is **non-binding** — that means if you get in, you don't *have* to go there. 
You can still compare it with other offers before making your final decision by May 1.

**Why apply Early Action?**
- You find out earlier if you got in (less stress!)
- Some schools give priority financial aid to EA applicants
- You have more time to compare your options

**Early Action vs. Early Decision:** Early Decision (ED) is *binding* — if you get in, you must attend and withdraw all other applications. 
Only apply ED if you are 100% sure that school is your #1 choice AND you've discussed finances with your family.

**Bottom line:** Early Action = apply early, get decision early, stay flexible. It's usually a great strategy!
""")

    # ── What is FAFSA? ────────────────────────────────────────────────────────
    with st.expander("💵 What is FAFSA?", expanded=True):
        st.markdown("""
**FAFSA** stands for **Free Application for Federal Student Aid**. It's the form the U.S. government uses to figure out 
how much financial help you can get for college.

**FAFSA can get you:**
- 🎁 **Pell Grants** — FREE money you don't pay back (up to $7,395/year if you qualify)
- 🏦 **Federal Loans** — money you borrow at low interest rates
- 👷 **Work-Study** — a part-time job on campus to help pay for college

**Who should fill out the FAFSA?**
*Everyone!* Even if you think your family makes too much — you might still get some aid or qualify for scholarships that use FAFSA data.

**When is the FAFSA due?**
The FAFSA opens **October 1** each year. Submit it AS SOON AS POSSIBLE — financial aid is often first-come, first-served. Some states run out of money!

**What do you need to fill it out?**
- Your Social Security Number (and your parent/guardian's)
- Your parent/guardian's tax return from last year
- Bank account balances
- Investment/savings information

**Where do I do it?** → [studentaid.gov](https://studentaid.gov/h/apply-for-aid/fafsa) — it's 100% free to fill out!

**Pro tip:** If your family's financial situation changed recently (job loss, medical bills, divorce), you can request a special circumstances review after submitting.
""")

    # ── What is the Common App? ────────────────────────────────────────────────
    with st.expander("📄 What is the Common App?", expanded=True):
        st.markdown("""
**The Common Application** (Common App) is a single online application platform that lets you apply to **over 1,000 colleges** at once.

Instead of filling out a separate application for every single school, you fill out your info ONCE — 
and then you can send it to as many participating schools as you want.

**What's in the Common App?**
- Basic personal info (name, address, family background)
- High school courses and grades (transcript)
- Extracurricular activities (up to 10)
- A personal essay (650 words — the most important writing you'll do)
- Teacher and counselor recommendations
- School-specific supplemental questions

**When does it open?** August 1 every year — create your account early!

**Which schools use it?** Most 4-year colleges use the Common App, including many HBCUs, Ivy League schools, and state universities.

**How much does it cost?** The Common App itself is free. Most colleges charge an application fee of $50–$90. 
Fee waivers are available if you qualify based on financial need — look for the "Common App Fee Waiver" option!

**Where do I sign up?** → [commonapp.org](https://www.commonapp.org/)
""")

    # ── More tips ─────────────────────────────────────────────────────────────
    with st.expander("🎓 What is a First-Generation College Student?", expanded=False):
        st.markdown("""
A **first-generation college student** (first-gen) is someone whose parents or guardians did not complete a 4-year college degree.

**Why does it matter?**
- Many scholarships are specifically for first-gen students
- Colleges often have special support programs (tutoring, mentoring, financial aid) just for first-gen students
- You're a trailblazer in your family — that's something to be proud of!

**Resources for first-gen students:**
- First Gen Foundation
- QuestBridge (for low-income, high-achieving students)
- Many HBCUs have strong first-gen support communities
""")

    with st.expander("🏫 What is an HBCU?", expanded=False):
        st.markdown("""
**HBCU** stands for **Historically Black College or University**. These are colleges and universities 
founded before 1964 to serve African-American students who were excluded from other institutions.

**Famous HBCUs include:**
- Howard University (Washington D.C.)
- Spelman College (Atlanta, GA)
- Morehouse College (Atlanta, GA)
- Hampton University (Hampton, VA)
- Florida A&M University (Tallahassee, FL)
- North Carolina A&T State University

**Why consider an HBCU?**
- Strong sense of community and cultural belonging
- Many have generous financial aid and HBCU-specific scholarships
- Strong alumni networks
- High graduation rates for Black students
- Many top employers actively recruit from HBCUs

**Great resource:** Use [thinkHBCU](https://www.thinkhbcu.org/) or College Board's Big Future to explore HBCU options.
""")

    with st.expander("💰 What is a Pell Grant?", expanded=False):
        st.markdown("""
A **Pell Grant** is FREE money from the federal government to help low- and moderate-income students pay for college.

**Key facts:**
- You can receive up to **$7,395 per year** (2023–24 award year)
- It's based on financial need (determined by your FAFSA)
- You do NOT have to pay it back — it's a grant, not a loan!
- You can use it at any accredited college or trade school
- You can receive Pell Grants for up to 12 semesters (6 years)

**How do I get it?** Fill out the FAFSA as early as possible after October 1. If you qualify, the money goes directly to your college to cover tuition and fees.

**Bottom line:** Pell Grants are some of the best financial aid out there. Always fill out the FAFSA to see if you qualify!
""")

    with st.expander("📝 What is a Supplemental Essay?", expanded=False):
        st.markdown("""
A **supplemental essay** is an additional writing piece that some colleges require beyond the main Common App personal essay.

**Common prompts include:**
- "Why do you want to attend [college name]?" — This is the most common. Research the school deeply and be specific!
- "Why are you interested in [your major]?"
- "Describe a challenge you've overcome."
- "Tell us about a community you belong to."

**How long are they?** Usually 150–650 words, depending on the school.

**Are they important?** YES — especially at selective schools. A generic, copy-pasted "Why us?" essay can hurt your application.

**Tips for great supplemental essays:**
- Research the school's specific programs, professors, clubs, and values
- Be specific — mention real programs, not just "great reputation"
- Show genuine enthusiasm — colleges can tell when you're faking it
- Have a teacher or counselor review each one before submitting
""")

    st.markdown("---")
    st.markdown("### 📞 More Help")
    st.markdown("""
**Free Resources:**
- 🌐 [College Board Big Future](https://bigfuture.collegeboard.org/) — Explore colleges, scholarships, and financial aid
- 📚 [Khan Academy SAT Prep](https://www.khanacademy.org/SAT) — Free, official SAT prep
- 💵 [Federal Student Aid](https://studentaid.gov/) — Everything about FAFSA and federal aid
- 📄 [Common App](https://www.commonapp.org/) — Start your college applications
- 🏫 [ThinkHBCU](https://www.thinkhbcu.org/) — HBCU exploration and resources

**Talk to someone:**
- Your **school counselor** — they do this every day and are there to help you!
- **College access programs** like Gear Up, Upward Bound, or College Advising Corps (many are free)
- **College fairs** — free events where you can meet representatives from dozens of schools at once
""")
