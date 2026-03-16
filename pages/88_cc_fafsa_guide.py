"""
College Confused — FAFSA Guide + EFC/SAI Calculator (page 88)
Step-by-step FAFSA walkthrough, EFC/SAI calculator,
dependency status guide, and state deadline tracker.
"""
import streamlit as st
from utils.db import (
    get_conn, USE_POSTGRES, execute as db_exec, init_db,
    get_setting, is_cc_ai_allowed,
)
from utils.auth import (
    require_login, render_sidebar_brand,
    render_sidebar_user_widget, inject_css,
)

st.set_page_config(
    page_title="FAFSA Guide — College Confused",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_cc_css()
require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎓 College Confused")
st.sidebar.page_link("pages/80_cc_home.py",           label="🏠 Home",             icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py",       label="📅 My Timeline",      icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",   label="💰 Scholarships",     icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",  label="✍️ Essay Station",    icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",      label="📚 SAT/ACT Prep",     icon="📚")
st.sidebar.page_link("pages/87_cc_college_list.py",   label="🏫 College List",     icon="🏫")
st.sidebar.page_link("pages/88_cc_fafsa_guide.py",    label="💸 FAFSA Guide",      icon="💸")
st.sidebar.markdown("---")
render_sidebar_user_widget()

# ── State FAFSA deadlines ─────────────────────────────────────────────────────
# (state, priority_deadline, notes, has_state_aid)
_STATE_DEADLINES = [
    ("Alabama",        "Feb 15",  "Early deadline. Apply ASAP after Oct 1.",     True),
    ("Alaska",         "Apr 15",  "Alaska Education Grant — submit early.",       True),
    ("Arizona",        "Mar 1",   "AZ Grants — many have Feb priority dates.",    True),
    ("Arkansas",       "Jun 1",   "Governor's Scholars Program — Apr 1.",         True),
    ("California",     "Mar 2",   "Cal Grant — hardest deadline in the US!",      True),
    ("Colorado",       "Mar 1",   "Colorado Student Grant — early is critical.",  True),
    ("Connecticut",    "Feb 15",  "CT Aid — submit by Feb 15 for priority.",      True),
    ("Delaware",       "Apr 15",  "DE Scholarship — apply early for max aid.",    True),
    ("Florida",        "May 15",  "Bright Futures + Florida Student Aid.",        True),
    ("Georgia",        "Jun 1",   "HOPE Scholarship — no FAFSA deadline but file.",True),
    ("Hawaii",         "Mar 1",   "Hawaii B+ Scholarship — Mar 1 priority.",      True),
    ("Idaho",          "Mar 1",   "Opportunity Scholarship — Feb 15 for priority.",True),
    ("Illinois",       "As soon as possible", "MAP Grant runs out fast — file Oct 1!",True),
    ("Indiana",        "Apr 15",  "Frank O'Bannon Grant — Apr 15.",               True),
    ("Iowa",           "Jul 1",   "Iowa Grant — first come, first served.",       True),
    ("Kansas",         "Apr 1",   "KS Career Tech Grant — Apr 1.",                True),
    ("Kentucky",       "Feb 15",  "KY Educational Excellence — KEES deadline.",   True),
    ("Louisiana",      "Jul 1",   "GO Grant + TOPS — file by Jul 1.",             True),
    ("Maine",          "May 1",   "Maine State Grant — May 1.",                   True),
    ("Maryland",       "Mar 1",   "Howard P. Rawlings Grant — Mar 1!",            True),
    ("Massachusetts",  "May 1",   "MASSGrant Plus — file early!",                True),
    ("Michigan",       "Mar 1",   "Michigan Competitive Scholarship — Mar 1.",    True),
    ("Minnesota",      "30 days after enrollment", "MN State Grant — rolling.",  True),
    ("Mississippi",    "Apr 1",   "MS Eminent Scholars — Mar 31.",               True),
    ("Missouri",       "Feb 1",   "Access Missouri — CRITICAL early deadline!",  True),
    ("Montana",        "Mar 1",   "Montana University System Aid.",               True),
    ("Nebraska",       "May 1",   "Nebraska Opportunity Grant — rolling.",        True),
    ("Nevada",         "Feb 1",   "Silver State Opportunity Grant — Feb 1.",      True),
    ("New Hampshire",  "May 1",   "NH Incentive Program.",                        True),
    ("New Jersey",     "Jun 1",   "NJ TAG — Jun 1 for returning, Apr for new.",   True),
    ("New Mexico",     "Mar 1",   "Legislative Lottery + NM Student Incentive.",  True),
    ("New York",       "May 1",   "TAP — Apply by May 1 for fall.",               True),
    ("North Carolina", "Mar 1",   "NC Need-Based Scholarship — Mar 1.",           True),
    ("North Dakota",   "Apr 15",  "ND State Student Financial Aid.",              True),
    ("Ohio",           "Oct 1",   "Ohio College Opportunity Grant — ASAP!",       True),
    ("Oklahoma",       "Apr 15",  "Oklahoma Tuition Aid Grant — rolling.",        True),
    ("Oregon",         "Mar 1",   "Oregon Opportunity Grant — Mar 1.",            True),
    ("Pennsylvania",   "May 1",   "PA State Grant — May 1.",                      True),
    ("Rhode Island",   "Mar 1",   "RI State Grant — ASAP after Oct 1.",           True),
    ("South Carolina", "Jun 30",  "SC Need-Based Grant — rolling.",               True),
    ("South Dakota",   "N/A",     "No state need-based aid program.",            False),
    ("Tennessee",      "Feb 1",   "TN Student Assistance Corp — Feb 1!",          True),
    ("Texas",          "Jan 15",  "TEXAS Grant — Jan 15. Very early deadline!",   True),
    ("Utah",           "Apr 1",   "Utah Centennial Scholarship — Apr 1.",         True),
    ("Vermont",        "Mar 1",   "Vermont Incentive Grant — Mar 1.",             True),
    ("Virginia",       "Mar 31",  "Virginia Guaranteed Assistance Program.",      True),
    ("Washington",     "Feb 15",  "WA College Grant — Feb 15 priority!",          True),
    ("Washington DC",  "May 31",  "DC Tuition Assistance Grant (DCTAG).",         True),
    ("West Virginia",  "Apr 15",  "PROMISE Scholarship — Apr 15.",                True),
    ("Wisconsin",      "Oct 1",   "WI Higher Education Grant — file ASAP!",       True),
    ("Wyoming",        "N/A",     "No state-funded grant program.",              False),
]

# ── DB Tables ─────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    ai = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    ts = "DEFAULT (to_char(now(),'YYYY-MM-DD HH24:MI:SS'))" if USE_POSTGRES else "DEFAULT (datetime('now'))"

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_fafsa_checklist (
        id {ai},
        user_email TEXT NOT NULL,
        item_key TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        updated_at TEXT {ts},
        UNIQUE(user_email, item_key)
    )""")

    conn.commit()
    conn.close()


def _load_checklist(user_email: str) -> dict:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    c = db_exec(conn, f"SELECT item_key, completed FROM cc_fafsa_checklist WHERE user_email={ph}", (user_email,))
    rows = c.fetchall()
    conn.close()
    return {r[0]: bool(r[1]) for r in rows}


def _toggle_checklist(user_email: str, item_key: str, done: bool) -> None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    try:
        db_exec(conn, f"""
            INSERT INTO cc_fafsa_checklist (user_email, item_key, completed)
            VALUES ({ph},{ph},{ph})
        """, (user_email, item_key, 1 if done else 0))
    except Exception:
        db_exec(conn, f"""
            UPDATE cc_fafsa_checklist SET completed={ph} WHERE user_email={ph} AND item_key={ph}
        """, (1 if done else 0, user_email, item_key))
    conn.commit()
    conn.close()


def _calc_efc(
    parent_agi: float, parent_assets: float, parent_num_in_college: int,
    student_income: float, student_assets: float,
    family_size: int, num_in_college: int,
) -> dict:
    """
    Simplified SAI/EFC estimate.
    Based on FAFSA simplified formula (federal methodology approximation).
    This is an ESTIMATE only — actual amounts vary.
    """
    # Income protection allowance (approx 2024 values)
    ipa_table = {1:18580, 2:23330, 3:29080, 4:35960, 5:42450, 6:49540}
    ipa = ipa_table.get(min(family_size, 6), 49540 + (family_size - 6) * 3000)

    # Parent income contribution
    available_income = max(0, parent_agi - ipa)
    if available_income <= 0:
        parent_income_contrib = 0
    elif available_income <= 14400:
        parent_income_contrib = available_income * 0.22
    elif available_income <= 18000:
        parent_income_contrib = available_income * 0.25
    elif available_income <= 21600:
        parent_income_contrib = available_income * 0.29
    elif available_income <= 25200:
        parent_income_contrib = available_income * 0.34
    elif available_income <= 28800:
        parent_income_contrib = available_income * 0.40
    else:
        parent_income_contrib = available_income * 0.47

    # Parent asset contribution (5.64% of assets above allowance)
    asset_protection = max(0, 5000)  # simplified asset protection allowance
    parent_asset_contrib = max(0, (parent_assets - asset_protection)) * 0.0564

    # Divide by number in college
    total_parent_contrib = (parent_income_contrib + parent_asset_contrib)
    if num_in_college > 1:
        total_parent_contrib = total_parent_contrib / num_in_college

    # Student income contribution (50% of income above $7600 allowance)
    student_income_contrib = max(0, student_income - 7600) * 0.50

    # Student asset contribution (20% of student assets)
    student_asset_contrib = student_assets * 0.20

    efc = max(0, total_parent_contrib + student_income_contrib + student_asset_contrib)

    return {
        "efc": round(efc),
        "parent_income_contrib": round(parent_income_contrib),
        "parent_asset_contrib": round(parent_asset_contrib),
        "student_income_contrib": round(student_income_contrib),
        "student_asset_contrib": round(student_asset_contrib),
        "total_parent_contrib": round(total_parent_contrib),
    }


try:
    _ensure_tables()
except Exception as _e:
    st.warning(f"⚠️ Could not initialize FAFSA tables: {_e}")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.cc-section-title { font-size:1.7rem; font-weight:800; color:#fafafa; margin-bottom:6px; }
.cc-section-sub { font-size:0.95rem; color:#8892a4; margin-bottom:20px; }
.cc-step-block {
    background:#1a1a2e; border:1px solid #2a2a4a; border-left:4px solid #6C63FF;
    border-radius:12px; padding:22px 24px; margin-bottom:14px;
}
.cc-step-num {
    display:inline-flex; align-items:center; justify-content:center;
    width:34px; height:34px; background:linear-gradient(135deg,#6C63FF,#9b55ff);
    color:#fff; font-weight:800; border-radius:50%; margin-right:12px;
    font-size:0.95rem; vertical-align:middle;
}
.cc-step-title { font-size:1.05rem; font-weight:700; color:#fafafa; display:inline; }
.cc-step-body { font-size:0.9rem; color:#c8d0dc; line-height:1.65; margin-top:10px; }
.cc-warn-block {
    background:#2d1b1b; border:1px solid #5a2a2a; border-left:4px solid #FF6B6B;
    border-radius:10px; padding:16px 20px; margin-bottom:14px;
}
.cc-tip-block {
    background:#1b2d1b; border:1px solid #2a5a2a; border-left:4px solid #51CF66;
    border-radius:10px; padding:16px 20px; margin-bottom:14px;
}
.cc-efc-card {
    background:#1a1a2e; border:1px solid #2a2a4a; border-radius:14px;
    padding:24px; text-align:center;
}
.cc-efc-number { font-size:2.8rem; font-weight:900; color:#6C63FF; }
.cc-efc-label { font-size:0.9rem; color:#8892a4; margin-top:4px; }
.cc-deadline-urgent { color:#FF6B6B; font-weight:700; }
.cc-deadline-ok { color:#51CF66; }
.cc-deadline-none { color:#8892a4; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cc-section-title">💸 FAFSA Guide + EFC Calculator</div>
<div class="cc-section-sub">
    Plain-English FAFSA walkthrough, your estimated family contribution (EFC/SAI),
    state-specific deadlines, and dependency status guide.
    No experience required.
</div>
""", unsafe_allow_html=True)

user_email = st.session_state.get("email", st.session_state.get("username", "guest"))
checklist  = _load_checklist(user_email)

tab_guide, tab_efc, tab_deadlines, tab_dependency, tab_ai = st.tabs([
    "📋 FAFSA Step-by-Step", "💰 EFC/SAI Calculator",
    "📅 State Deadlines", "👨‍👩‍👧 Dependency Status", "🤖 AI FAFSA Advisor"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FAFSA STEP-BY-STEP
# ══════════════════════════════════════════════════════════════════════════════
with tab_guide:
    st.markdown("#### 📋 How to Complete the FAFSA — Plain English, Step by Step")

    checklist_items = [
        ("get_fsaid",      "Get your FSA ID (studentaid.gov)",       "fsa_id"),
        ("gather_taxes",   "Gather tax documents (IRS Data Retrieval Tool)", "taxes"),
        ("gather_ssn",     "Have Social Security Numbers ready",      "ssn"),
        ("open_fafsa",     "Open FAFSA at studentaid.gov",            "open"),
        ("section1",       "Complete Section 1: Student Info",        "s1"),
        ("section2",       "Complete Section 2: School Selection",    "s2"),
        ("section3",       "Complete Section 3: Dependency",          "s3"),
        ("section4",       "Complete Section 4: Parent Info",         "s4"),
        ("section5",       "Complete Section 5: Financial Info",      "s5"),
        ("sign_submit",    "Sign & Submit",                            "sign"),
        ("sar_review",     "Review your SAR (Student Aid Report)",    "sar"),
        ("award_letters",  "Compare Financial Aid Award Letters",     "awards"),
    ]

    completed_count = sum(1 for key, _, _ in checklist_items if checklist.get(key, False))
    total_count = len(checklist_items)
    progress_pct = completed_count / total_count if total_count > 0 else 0

    st.progress(progress_pct, text=f"FAFSA Checklist: {completed_count}/{total_count} steps completed")
    st.markdown("<br>", unsafe_allow_html=True)

    STEPS = [
        {
            "key": "get_fsaid",
            "num": 1,
            "title": "Create Your FSA ID",
            "body": """
Your FSA ID is your username and password for the Federal Student Aid website.
<strong>Both you AND one parent need separate FSA IDs.</strong><br><br>
🌐 Go to: <a href="https://fsaid.ed.gov" target="_blank" style="color:#6C63FF;">fsaid.ed.gov</a><br>
📋 You'll need: Social Security Number, date of birth, email address.<br>
⚠️ <strong>Important:</strong> Each person needs their OWN email address.
A parent cannot use the student's email. Create the FSA ID at least 3 days before you want to file.
            """,
        },
        {
            "key": "gather_taxes",
            "num": 2,
            "title": "Gather Your Documents",
            "body": """
Before you start, have these ready:<br><br>
<strong>Student needs:</strong><br>
• Social Security Number (or Alien Registration Number)<br>
• Driver's license (optional, but helpful)<br>
• Prior-prior year tax return (e.g., for 2025–26 FAFSA, you need 2023 taxes)<br>
• Bank account balances as of today<br>
• Records of untaxed income (child support, VA benefits, etc.)<br><br>
<strong>Parent needs:</strong><br>
• Social Security Number<br>
• Same prior-prior year tax return<br>
• Investment and bank account balances<br>
• Business/farm records (if applicable)<br><br>
💡 <strong>Tip:</strong> Use the IRS Data Retrieval Tool (DRT) in FAFSA — it auto-fills your tax info and prevents errors.
            """,
        },
        {
            "key": "open_fafsa",
            "num": 3,
            "title": "Open the FAFSA at studentaid.gov",
            "body": """
🌐 Go to: <a href="https://studentaid.gov/h/apply-for-aid/fafsa" target="_blank" style="color:#6C63FF;">studentaid.gov/fafsa</a><br><br>
The FAFSA opens <strong>October 1st every year</strong> for the following school year.
Always file as soon as it opens — many state grants run out of money on a first-come, first-served basis.<br><br>
📌 <strong>Sign in with your FSA ID</strong>, then click "Start a New FAFSA."
Choose the correct school year. (Filing for fall 2026 = 2026–27 FAFSA)
            """,
        },
        {
            "key": "section1",
            "num": 4,
            "title": "Section 1: Student Information",
            "body": """
Fill in your basic personal information:<br>
• Legal name (exactly as it appears on your Social Security card)<br>
• Social Security Number<br>
• Date of birth<br>
• Mailing address and email<br>
• Citizenship status<br>
• Selective Service registration (males 18–25 — register at <a href="https://sss.gov" target="_blank" style="color:#6C63FF;">sss.gov</a> if you haven't)<br><br>
⚠️ <strong>Name MUST match Social Security records exactly</strong> — a mismatch will delay or reject your FAFSA.
            """,
        },
        {
            "key": "section2",
            "num": 5,
            "title": "Section 2: School Selection",
            "body": """
Add the colleges you want to receive your FAFSA information.<br><br>
• You can add up to <strong>20 schools</strong><br>
• Search by school name or use the Federal School Code<br>
• Include <strong>all schools you're applying to</strong> — you can always remove them later<br>
• Put your most affordable school first if you're worried about privacy<br><br>
💡 <strong>HBCU Tip:</strong> HBCUs often have additional institutional grants on top of FAFSA aid.
Always add HBCUs to your school list.
            """,
        },
        {
            "key": "section3",
            "num": 6,
            "title": "Section 3: Dependency Status",
            "body": """
FAFSA asks whether you are a "dependent" or "independent" student.<br><br>
<strong>Most traditional students are DEPENDENT</strong> — meaning you must report parent financial info.<br>
You're independent if you answer YES to any of these:<br>
• Are you 24 or older?<br>
• Are you married?<br>
• Are you a veteran or active duty military?<br>
• Do you have dependents of your own?<br>
• Were you in foster care or a ward of the court after age 13?<br>
• Are you an emancipated minor?<br><br>
⚠️ If you're dependent but your parents won't provide info, see "Dependency Override."
Go to the <strong>Dependency Status tab</strong> for the full guide.
            """,
        },
        {
            "key": "section4",
            "num": 7,
            "title": "Section 4: Parent Financial Information",
            "body": """
You'll report your parent's (or step-parent's) financial information.<br><br>
<strong>Whose info to report:</strong><br>
• If parents are married: both parents' combined info<br>
• If divorced/separated: report the parent you lived with MORE in the past 12 months<br>
• If that parent remarried: include step-parent's info too<br><br>
<strong>Use the IRS Data Retrieval Tool (DRT)</strong> to automatically import tax data — much faster and error-free.<br><br>
💡 <strong>Tip for high-income families:</strong> Don't assume you won't qualify. Many families with $100k+ income still receive some aid, especially from HBCUs with strong institutional funds.
            """,
        },
        {
            "key": "section5",
            "num": 8,
            "title": "Section 5: Financial Information & Assets",
            "body": """
Report current account balances (as of the day you file):<br>
• Checking and savings accounts<br>
• Investment accounts (stocks, bonds — NOT retirement accounts)<br>
• 529 College Savings Plans (parent-owned)<br>
• Business and farm value (if applicable)<br><br>
⚠️ <strong>Do NOT include retirement accounts</strong> (401k, IRA, pension) — these are not counted!<br><br>
Student assets are counted MORE heavily (20%) than parent assets (5.64%), so it's better to have savings in parent accounts.
            """,
        },
        {
            "key": "sign_submit",
            "num": 9,
            "title": "Sign & Submit",
            "body": """
Both the student AND one parent must sign electronically using FSA IDs.<br><br>
After signing:<br>
• You'll receive a confirmation email within minutes<br>
• Your SAR (Student Aid Report) is generated within 3–5 days<br>
• Schools receive your info automatically<br><br>
📌 <strong>Save your confirmation number!</strong> Screenshot the confirmation page.
            """,
        },
        {
            "key": "sar_review",
            "num": 10,
            "title": "Review Your SAR (Student Aid Report)",
            "body": """
Your SAR summarizes your FAFSA data and shows your <strong>EFC / Student Aid Index (SAI)</strong>.<br><br>
• <strong>EFC = 0:</strong> Maximum Pell Grant eligibility (~$7,395 for 2024-25)<br>
• <strong>EFC = $5,000:</strong> Reduced Pell Grant<br>
• <strong>EFC > $6,000:</strong> Typically no federal Pell Grant, but still eligible for loans and institutional aid<br><br>
⚠️ If anything looks wrong, log into studentaid.gov and make corrections immediately.
            """,
        },
        {
            "key": "award_letters",
            "num": 11,
            "title": "Compare Financial Aid Award Letters",
            "body": """
After admissions decisions, each school sends a <strong>Financial Aid Award Letter</strong>.<br><br>
<strong>What to look for:</strong><br>
• Grants/scholarships (FREE money — accept all of it)<br>
• Work-Study (earned income — usually a good option)<br>
• Loans (money you have to pay back — minimize this)<br><br>
⚠️ <strong>Don't confuse "Cost of Attendance" with "Out of Pocket."</strong><br>
Out of Pocket = COA − All grants − Scholarships<br><br>
💡 If a school's aid offer is disappointing, you can appeal! See the Financial Aid Appeal guide (coming soon).
            """,
        },
    ]

    for step in STEPS:
        key = step["key"]
        is_done = checklist.get(key, False)
        border_color = "#51CF66" if is_done else "#6C63FF"
        check_icon = "✅" if is_done else ""

        st.markdown(f"""
        <div class="cc-step-block" style="border-left-color:{border_color};">
            <span class="cc-step-num">{step['num']}</span>
            <span class="cc-step-title">{step['title']} {check_icon}</span>
            <div class="cc-step-body">{step['body']}</div>
        </div>
        """, unsafe_allow_html=True)

        col_check, _ = st.columns([1, 6])
        done_toggle = col_check.checkbox(
            "Mark complete", value=is_done, key=f"chk_{key}"
        )
        if done_toggle != is_done:
            _toggle_checklist(user_email, key, done_toggle)
            st.rerun()

    # Key FAFSA tips
    st.markdown("---")
    st.markdown("""
    <div class="cc-tip-block">
        <strong style="color:#51CF66;">✅ Darrian's #1 FAFSA Rule</strong><br>
        <span style="color:#c8d0dc;">
        File on October 1st. Don't wait. Many states run out of grant money by December.
        Students who file in October get more aid than students who file in February — for the same financial situation.
        Set a reminder right now.
        </span>
    </div>
    <div class="cc-warn-block">
        <strong style="color:#FF6B6B;">⚠️ Biggest FAFSA Mistakes</strong><br>
        <span style="color:#c8d0dc;">
        1. Filing late (state aid runs out!) &nbsp;|&nbsp;
        2. Listing parents incorrectly after divorce &nbsp;|&nbsp;
        3. Forgetting to report untaxed income &nbsp;|&nbsp;
        4. Name mismatch with SSA records &nbsp;|&nbsp;
        5. Not appealing a low offer
        </span>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EFC / SAI CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_efc:
    st.markdown("#### 💰 EFC / SAI Calculator")
    st.info(
        "This is an **estimate only** based on a simplified version of the federal need analysis formula. "
        "Your actual SAI may differ. Use this to plan, not to predict exactly."
    )

    st.markdown("##### 👨‍👩‍👧 Household Info")
    hc1, hc2, hc3 = st.columns(3)
    family_size       = hc1.number_input("Family Size (total people in household)", 1, 15, 4)
    num_in_college    = hc2.number_input("Number in College Simultaneously", 1, 5, 1)
    dependency_status = hc3.selectbox("Student Type", ["Dependent (has parental support)", "Independent (no parental support)"])

    is_dependent = "Dependent" in dependency_status

    st.markdown("##### 💼 Parent Financial Info")
    if is_dependent:
        pc1, pc2 = st.columns(2)
        parent_agi    = pc1.number_input("Parent Adjusted Gross Income (AGI, line 11 of 1040)", 0, 1000000, 60000, 1000)
        parent_assets = pc2.number_input("Parent Net Assets (checking + savings + investments, NOT retirement)", 0, 2000000, 10000, 500)
    else:
        parent_agi, parent_assets = 0.0, 0.0
        st.info("Independent students skip the parent section.")

    st.markdown("##### 🎒 Student Financial Info")
    sc1, sc2 = st.columns(2)
    student_income = sc1.number_input("Student Income (last year, from job or work)", 0, 100000, 0, 500)
    student_assets = sc2.number_input("Student Assets (checking + savings in YOUR name)", 0, 500000, 500, 100)

    if st.button("📊 Calculate My EFC / SAI", type="primary", use_container_width=True):
        result = _calc_efc(
            parent_agi=float(parent_agi), parent_assets=float(parent_assets),
            parent_num_in_college=num_in_college, student_income=float(student_income),
            student_assets=float(student_assets), family_size=int(family_size),
            num_in_college=int(num_in_college),
        )
        efc = result["efc"]

        st.markdown("---")
        ec1, ec2, ec3 = st.columns(3)

        with ec1:
            st.markdown(f"""
            <div class="cc-efc-card">
                <div class="cc-efc-number">${efc:,}</div>
                <div class="cc-efc-label">Estimated EFC / SAI</div>
            </div>
            """, unsafe_allow_html=True)

        with ec2:
            pell = max(0, 7395 - (efc * 7395 // 6500)) if efc < 6500 else 0
            st.markdown(f"""
            <div class="cc-efc-card">
                <div class="cc-efc-number" style="color:#51CF66;">${pell:,}</div>
                <div class="cc-efc-label">Est. Annual Pell Grant</div>
            </div>
            """, unsafe_allow_html=True)

        with ec3:
            max_loan = 5500
            st.markdown(f"""
            <div class="cc-efc-card">
                <div class="cc-efc-number" style="color:#FFA94D;">${max_loan:,}</div>
                <div class="cc-efc-label">Max Direct Loan (Year 1)</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### 📊 Breakdown")

        breakdown = [
            ("Parent income contribution", result["parent_income_contrib"]),
            ("Parent asset contribution", result["parent_asset_contrib"]),
            ("Student income contribution", result["student_income_contrib"]),
            ("Student asset contribution", result["student_asset_contrib"]),
        ]
        for label, amount in breakdown:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #2a2a4a;">
                <span style="color:#8892a4;font-size:0.9rem;">{label}</span>
                <span style="color:#fafafa;font-weight:600;">${amount:,}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Interpretation
        if efc == 0:
            st.success("🎉 **EFC = $0** — You qualify for maximum Pell Grant (~$7,395/yr). Apply to schools with strong institutional aid for near-zero cost!")
        elif efc < 3000:
            st.success(f"✅ **Low EFC** — You should receive a substantial Pell Grant. Look for schools with generous need-based packages.")
        elif efc < 10000:
            st.info(f"📌 **Moderate EFC** — You may receive partial Pell Grant. HBCUs and strong need-based schools like Vanderbilt, Princeton, and UChicago often meet 100% of demonstrated need.")
        else:
            st.warning(f"⚠️ **Higher EFC** — Limited Pell Grant eligibility. Focus on merit scholarships and schools with strong merit aid programs. Don't stop applying — your EFC estimate ≠ what you'll actually pay.")

        st.caption("⚠️ This calculator uses a simplified approximation of the federal need analysis formula. Your actual SAI from FAFSA may differ. Consult your school's financial aid office for your actual package.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — STATE DEADLINES
# ══════════════════════════════════════════════════════════════════════════════
with tab_deadlines:
    st.markdown("#### 📅 State FAFSA Priority Deadlines")
    st.warning(
        "**File FAFSA on October 1st every year** — before any state deadline. "
        "State grants are often first-come, first-served and run out of money!"
    )

    search_state = st.text_input("🔍 Search your state", placeholder="e.g. Georgia, Texas…")
    show_aid_only = st.checkbox("Show only states with aid programs", value=True)

    filtered = [
        s for s in _STATE_DEADLINES
        if (not search_state or search_state.lower() in s[0].lower())
        and (not show_aid_only or s[3])
    ]

    dl_c1, dl_c2 = st.columns(2)
    for i, (state, deadline, notes, has_aid) in enumerate(filtered):
        target_col = dl_c1 if i % 2 == 0 else dl_c2
        urgent = any(m in deadline.lower() for m in ["jan", "feb", "oct", "asap"])
        cls = "cc-deadline-urgent" if urgent else ("cc-deadline-ok" if has_aid else "cc-deadline-none")
        icon = "🔴" if urgent else ("🟢" if has_aid else "⚫")

        with target_col:
            st.markdown(f"""
            <div style="background:#1a1a2e;border:1px solid #2a2a4a;border-radius:10px;padding:14px 18px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:700;color:#fafafa;">{icon} {state}</span>
                    <span class="{cls}">{deadline}</span>
                </div>
                <div style="font-size:0.83rem;color:#8892a4;margin-top:6px;">{notes}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.info(
        "🔴 Red = Early/urgent deadline (Jan–Feb or October).  "
        "🟢 Green = Later deadline but still file early.  "
        "⚫ No state need-based aid program.\n\n"
        "**Always verify deadlines directly with your state's higher education agency** — they change yearly."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DEPENDENCY STATUS
# ══════════════════════════════════════════════════════════════════════════════
with tab_dependency:
    st.markdown("#### 👨‍👩‍👧 Are You Dependent or Independent?")
    st.markdown("""
    <div style="background:#1a1a2e;border:1px solid #2a2a4a;border-radius:14px;padding:22px 24px;margin-bottom:20px;">
        <p style="color:#c8d0dc;font-size:1rem;line-height:1.7;margin:0 0 10px 0;">
            FAFSA uses your <strong style="color:#fafafa;">dependency status</strong> to determine
            whether your parents' financial information is required.
        </p>
        <p style="color:#c8d0dc;font-size:1rem;line-height:1.7;margin:0;">
            Most traditional college students are <strong style="color:#6C63FF;">dependent</strong>.
            If you're dependent, your parents must provide their financial info — even if you don't live
            with them, even if they don't support you financially.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### ✅ You are INDEPENDENT if ANY of the following apply:")
    ind_criteria = [
        ("🎂", "Age 24+",              "Were you born before January 1, 2001? (for 2025–26 FAFSA)"),
        ("💍", "Married",              "Are you legally married (or separated, but not divorced)?"),
        ("🎖️","Military/Veteran",     "Are you a veteran or currently on active duty for a purpose other than training?"),
        ("👶", "Have Dependents",      "Do you have children or other dependents you support (more than half their income)?"),
        ("🏠", "Homeless/At Risk",     "Are you unaccompanied, self-supporting, and/or homeless?"),
        ("🏛️", "Foster Care/Ward",    "Were you in foster care or a ward of the court at any point after age 13?"),
        ("⚖️", "Emancipated Minor",   "Are you currently a legal emancipated minor as determined by a court?"),
        ("🎓", "Working on Master's+","Are you currently enrolled in a graduate or professional program?"),
    ]
    for icon, title, description in ind_criteria:
        col_a, col_b = st.columns([1, 8])
        col_a.markdown(f"<div style='font-size:1.8rem;text-align:center;'>{icon}</div>", unsafe_allow_html=True)
        col_b.markdown(f"**{title}**  \n{description}")

    st.markdown("---")
    st.markdown("##### ⚠️ My Parents Won't Cooperate — What Do I Do?")
    st.markdown("""
    <div style="background:#2d1b1b;border:1px solid #5a2a2a;border-left:4px solid #FF6B6B;border-radius:10px;padding:18px 22px;margin-bottom:16px;">
        <strong style="color:#FF6B6B;">This is one of the most common FAFSA problems for low-income and first-gen students.</strong>
        <div style="color:#c8d0dc;font-size:0.9rem;line-height:1.65;margin-top:10px;">
            <strong>Option 1: Dependency Override</strong> — You can request a dependency override from your
            school's financial aid office. This requires documented proof of an "unusual circumstance"
            (abuse, abandonment, incarceration of parents, etc.). It's a formal process but it works.<br><br>
            <strong>Option 2: Parent Refuses (not an override situation)</strong> — Unfortunately, if your
            parents are technically required to provide info but simply refuse, FAFSA cannot be completed
            without it. In this case: focus on <strong>merit-based scholarships</strong> that don't
            require FAFSA, and talk to the financial aid office — many schools have institutional processes.<br><br>
            <strong>Option 3: File as Independent</strong> — If you genuinely meet an independence criterion
            above, document it and check the correct box. Don't lie — but if it's true, use it.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#1b2d1b;border:1px solid #2a5a2a;border-left:4px solid #51CF66;border-radius:10px;padding:18px 22px;">
        <strong style="color:#51CF66;">💡 Darrian's Advice for First-Gen Students</strong>
        <div style="color:#c8d0dc;font-size:0.9rem;line-height:1.65;margin-top:10px;">
            If your parents have never done taxes or don't have a Social Security Number (undocumented),
            <strong>you can still file FAFSA</strong> — put all zeros for their income and assets,
            and explain the situation to the financial aid office directly. Don't let this stop you.
            Many HBCUs and need-focused schools have special processes for exactly this situation.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — AI FAFSA ADVISOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("#### 🤖 AI FAFSA Advisor")
    st.caption("Ask Claude any FAFSA question in plain English. No jargon. No judgment.")

    if not is_cc_ai_allowed(user_email):
        st.warning("🔒 AI features are currently owner-only during beta. Check back soon!")
    else:
        api_key = get_setting("anthropic_api_key")
        if not api_key:
            st.error("⚙️ Anthropic API key not configured.")
        else:
            fafsa_q = st.text_area(
                "What's your FAFSA question?",
                placeholder=(
                    "Examples:\n"
                    "• My parents are divorced — whose info do I use?\n"
                    "• My parents won't give me their tax info. What do I do?\n"
                    "• I got a $12,000 EFC. Will I still get any aid?\n"
                    "• I have a 529 plan. How does that affect my aid?"
                ),
                height=120,
            )

            if st.button("🤖 Ask Claude", type="primary", use_container_width=True):
                if not fafsa_q.strip():
                    st.error("Please type your question first.")
                else:
                    prompt = f"""You are a college financial aid expert helping a student with FAFSA questions.
The student may be first-generation, low-income, or have complicated family situations.
Speak in plain English. Be warm, encouraging, and direct. Never use jargon without explaining it.
Always tell them what to DO next, not just what the rules are.

Student's question: {fafsa_q}

Answer in 2-3 paragraphs. End with one actionable next step."""
                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=api_key)
                        with st.spinner("Claude is answering your FAFSA question…"):
                            response = client.messages.create(
                                model="claude-opus-4-5",
                                max_tokens=600,
                                messages=[{"role": "user", "content": prompt}],
                            )
                        st.markdown("---")
                        st.markdown("**🤖 Claude's Answer:**")
                        st.markdown(response.content[0].text)
                    except Exception as e:
                        st.error(f"AI error: {e}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<hr style="border-color:#2a2a4a; margin:20px 0 12px 0;">
<div style="text-align:center; color:#8892a4; font-size:0.82rem;">
    🎓 <strong style="color:#6C63FF;">College Confused</strong> — Free college guidance for every student.
    &nbsp;|&nbsp;
    <a href="mailto:support@collegeconfused.org" style="color:#6C63FF; text-decoration:none;">
        support@collegeconfused.org
    </a>
</div>
""", unsafe_allow_html=True)
