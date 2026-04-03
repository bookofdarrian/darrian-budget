"""
College Confused — College List Builder (page 87)
Search/filter colleges by major, location, cost, acceptance rate, HBCU;
save to personal list; compare side-by-side; AI advisor.
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
    page_title="College List Builder — College Confused",
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
st.sidebar.page_link("pages/80_cc_home.py",                      label="Home",               icon="🏠")
st.sidebar.page_link("pages/81_cc_timeline.py",                  label="My Timeline",         icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",              label="Scholarships",        icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",             label="Essay Station",       icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",                 label="SAT/ACT Prep",        icon="📚")
st.sidebar.page_link("pages/87_cc_college_list.py",              label="College List",        icon="🏫")
st.sidebar.page_link("pages/88_cc_fafsa_guide.py",               label="FAFSA Guide",         icon="📋")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/93_cc_application_tracker.py",       label="Applications",        icon="📝")
st.sidebar.page_link("pages/97_cc_admissions_decision_tracker.py", label="Decisions",          icon="📬")
st.sidebar.page_link("pages/94_cc_recommendation_letter_tracker.py", label="Rec Letters",      icon="📨")
st.sidebar.page_link("pages/95_cc_interview_prep_ai.py",         label="Interview Prep",      icon="🎤")
st.sidebar.page_link("pages/96_cc_financial_aid_appeal_generator.py", label="Aid Appeals",     icon="💸")
st.sidebar.page_link("pages/98_cc_test_score_tracker.py",        label="Score Tracker",       icon="📊")
st.sidebar.page_link("pages/99_cc_campus_visit_planner.py",      label="Campus Visits",       icon="🗺️")
st.sidebar.page_link("pages/89_cc_student_inquiry_form.py",      label="Get Help",            icon="🙋")
render_sidebar_user_widget()

# ── College seed data ─────────────────────────────────────────────────────────
# fmt: (name, state, city, type, hbcu, accept_pct, tuition, avg_sat, avg_act, setting, size, majors, website, notes)
_COLLEGE_SEEDS = [
    # ── HBCUs ────────────────────────────────────────────────────────────────
    ("Howard University",               "DC","Washington","Private",1,38,28888,1150,24,"Urban","Medium",
     "Business,Engineering,Nursing,Law,Communications,Pre-Med,Political Science",
     "https://howard.edu","Prestigious HBCU in DC. 'The Mecca.' Strong alumni network, excellent medical/law pipeline."),
    ("Morehouse College",               "GA","Atlanta",  "Private",1,52,29000,1180,25,"Urban","Small",
     "Business,Pre-Med,Political Science,Computer Science,Psychology",
     "https://morehouse.edu","All-male HBCU. Dr. King's alma mater. Exceptional leadership development."),
    ("Spelman College",                 "GA","Atlanta",  "Private",1,42,29000,1190,26,"Urban","Small",
     "Biology,Computer Science,Psychology,English,Political Science",
     "https://spelman.edu","All-female HBCU. Top STEM pipeline for Black women. Strong Ivy transfer/grad admissions."),
    ("Florida A&M University",          "FL","Tallahassee","Public",1,35,5,700,1030,21,"Suburban","Large",
     "Business,Pharmacy,Engineering,Journalism,Agriculture,Nursing",
     "https://famu.edu","Florida's only public HBCU. #1 HBCU by US News. Rattler pride. Low in-state tuition."),
    ("Hampton University",              "VA","Hampton",  "Private",1,55,28000,1080,22,"Suburban","Medium",
     "Business,Nursing,Education,Aviation,Sciences",
     "https://hamptonu.edu","One of the oldest HBCUs. Strong nursing, aviation, and business programs."),
    ("North Carolina A&T State Univ.",  "NC","Greensboro","Public",1,62,7500,1020,20,"Suburban","Large",
     "Engineering,Agriculture,Business,Communications,Computer Science",
     "https://ncat.edu","Largest HBCU. #1 for Black engineering graduates. Strong research programs."),
    ("Prairie View A&M University",     "TX","Prairie View","Public",1,60,9500,960,18,"Suburban","Medium",
     "Engineering,Education,Nursing,Business,Agriculture",
     "https://pvamu.edu","Texas HBCU in the A&M system. Affordable. Strong STEM and nursing pathways."),
    ("Tennessee State University",      "TN","Nashville","Public",1,70,8200,980,19,"Urban","Medium",
     "Agriculture,Engineering,Nursing,Business,Education",
     "https://tnstate.edu","Nashville HBCU. Music city connections. Affordable in-state option."),
    ("Tuskegee University",             "AL","Tuskegee", "Private",1,36,24000,1050,22,"Rural","Small",
     "Engineering,Veterinary Medicine,Architecture,Nursing,Agriculture",
     "https://tuskegee.edu","Booker T. Washington's legacy. Only HBCU with vet medicine and architecture."),
    ("Morgan State University",         "MD","Baltimore","Public",1,67,7900,1010,20,"Urban","Medium",
     "Business,Engineering,Architecture,Public Health,Education",
     "https://morgan.edu","Maryland's Preeminent Public Urban Research University. Close to DC jobs."),

    # ── Ivy League ────────────────────────────────────────────────────────────
    ("Harvard University",              "MA","Cambridge","Private",0,4,57000,1510,35,"Urban","Large",
     "Pre-Law,Economics,Computer Science,Biology,Political Science,History",
     "https://harvard.edu","#1 university in the world. Need-based aid meets 100% of demonstrated need."),
    ("Yale University",                 "CT","New Haven","Private",0,5,61000,1510,35,"Urban","Medium",
     "Law,Medicine,Political Science,History,Environmental Science,Drama",
     "https://yale.edu","Incredible residential college system. Best law school in the US."),
    ("Princeton University",            "NJ","Princeton","Private",0,4,55000,1510,35,"Suburban","Medium",
     "Economics,Engineering,Computer Science,Public Policy,Mathematics",
     "https://princeton.edu","Only Ivy with no graduate professional schools. All-aid, no loans."),
    ("Columbia University",             "NY","New York", "Private",0,4,63000,1510,35,"Urban","Large",
     "Journalism,Business,Engineering,Pre-Law,Political Science,Film",
     "https://columbia.edu","In the heart of New York City. Core Curriculum. Top journalism + business programs."),
    ("University of Pennsylvania",      "PA","Philadelphia","Private",0,7,59000,1500,34,"Urban","Large",
     "Business,Nursing,Engineering,Economics,Pre-Med,Social Work",
     "https://upenn.edu","Wharton School = #1 undergrad business. Nursing, engineering, liberal arts."),

    # ── Top Private Universities ───────────────────────────────────────────────
    ("MIT",                             "MA","Cambridge","Private",0,4,57000,1540,36,"Urban","Medium",
     "Engineering,Computer Science,Mathematics,Physics,Economics,Architecture",
     "https://mit.edu","Best STEM school. 70%+ receive aid. Research-heavy. Nobel laureate faculty."),
    ("Stanford University",             "CA","Stanford", "Private",0,4,56000,1510,35,"Suburban","Large",
     "Computer Science,Engineering,Business,Biology,Psychology,Economics",
     "https://stanford.edu","Silicon Valley. #1 entrepreneurship ecosystem. Meets 100% of need."),
    ("Duke University",                 "NC","Durham",   "Private",0,6,58000,1480,34,"Suburban","Medium",
     "Pre-Med,Engineering,Public Policy,Business,Biology,Computer Science",
     "https://duke.edu","Top 10 overall. Phenomenal pre-med. Duke Chapel. Rivalry with UNC."),
    ("Emory University",                "GA","Atlanta",  "Private",0,19,54000,1420,33,"Suburban","Medium",
     "Pre-Med,Business,Psychology,Biology,Public Health,Law",
     "https://emory.edu","Top medical school pipeline in the Southeast. CDC connection. Atlanta location."),
    ("Vanderbilt University",           "TN","Nashville","Private",0,7,56000,1500,34,"Urban","Medium",
     "Engineering,Education,Business,Pre-Med,Music,Psychology",
     "https://vanderbilt.edu","Nashville. Debt-free pledge for low-income students. Top-15 overall."),
    ("Georgetown University",           "DC","Washington","Private",0,12,56000,1450,33,"Urban","Medium",
     "Pre-Law,International Relations,Business,Nursing,Political Science",
     "https://georgetown.edu","DC's premier university. Best for government, law, diplomacy careers."),
    ("Rice University",                 "TX","Houston",  "Private",0,9,52000,1510,35,"Urban","Medium",
     "Engineering,Computer Science,Architecture,Music,Economics,Natural Sciences",
     "https://rice.edu","Top-15. Lowest tuition among elite privates. Houston's energy sector access."),
    ("Carnegie Mellon University",      "PA","Pittsburgh","Private",0,11,58000,1490,34,"Urban","Large",
     "Computer Science,Engineering,Drama,Music,Business,Architecture",
     "https://cmu.edu","#1 CS undergrad. School of Drama is world-class. Robotics Institute."),

    # ── Strong Public Universities ────────────────────────────────────────────
    ("Georgia Institute of Technology", "GA","Atlanta",  "Public", 0,21,12000,1440,33,"Urban","Large",
     "Engineering,Computer Science,Business,Architecture,Sciences,Cybersecurity",
     "https://gatech.edu","#1 public engineering school. Affordable in-state. Top CS/ECE program."),
    ("University of Georgia",           "GA","Athens",   "Public", 0,45,12000,1290,30,"College Town","Large",
     "Business,Education,Journalism,Agriculture,Pre-Law,Psychology",
     "https://uga.edu","Flagship Georgia university. HOPE Scholarship eligible. Beautiful campus."),
    ("University of Florida",           "FL","Gainesville","Public",0,31,6400,1350,31,"College Town","Large",
     "Engineering,Business,Agriculture,Pre-Med,Law,Nursing",
     "https://ufl.edu","Top-5 public university. Incredibly affordable in-state. Bright Futures eligible."),
    ("Florida State University",        "FL","Tallahassee","Public",0,36,6500,1270,29,"College Town","Large",
     "Business,Film,Criminology,Education,Social Work,Nursing",
     "https://fsu.edu","Top film school. Affordable. Bright Futures eligible. Next to FAMU."),
    ("University of Texas at Austin",   "TX","Austin",   "Public", 0,31,11000,1340,31,"Urban","Large",
     "Business,Engineering,Computer Science,Communications,Law,Natural Sciences",
     "https://utexas.edu","Top-15 public. Austin tech scene. Flagship UT system. Hook 'Em Horns."),
    ("University of Michigan",          "MI","Ann Arbor","Public", 0,17,16000,1440,33,"College Town","Large",
     "Business,Engineering,Pre-Med,Law,Social Work,Education",
     "https://umich.edu","Top-5 public. Ross School of Business #1 BBA. Go Blue!"),
    ("Virginia Tech",                   "VA","Blacksburg","Public",0,60,13000,1280,29,"College Town","Large",
     "Engineering,Computer Science,Architecture,Agriculture,Business",
     "https://vt.edu","Excellent engineering value. Ut Prosim ('That I May Serve')."),
    ("UNC Chapel Hill",                 "NC","Chapel Hill","Public",0,19,9000,1370,32,"College Town","Large",
     "Business,Journalism,Pre-Med,Public Policy,Biology,Education",
     "https://unc.edu","Top-5 public. Kenan-Flagler Business School. Carolina blue."),
    ("University of Maryland",          "MD","College Park","Public",0,44,10000,1380,32,"Suburban","Large",
     "Engineering,Computer Science,Business,Journalism,Agriculture",
     "https://umd.edu","Close to DC. Strong CS pipeline to federal agencies. ACC athletics."),
    ("North Carolina State University", "NC","Raleigh",  "Public", 0,45,9000,1260,28,"Urban","Large",
     "Engineering,Computer Science,Agriculture,Design,Business,Education",
     "https://ncsu.edu","Research Triangle Park access. Wolfpack. Affordable NC option."),
    ("Georgia State University",        "GA","Atlanta",  "Public", 0,55,9000,1100,22,"Urban","Large",
     "Business,Law,Film,Public Health,Computer Science,Education",
     "https://gsu.edu","Atlanta's urban public university. HSI + MSI. Top completion rates for diverse students."),

    # ── Strong Liberal Arts / Mid-Tier ────────────────────────────────────────
    ("Morehouse School of Medicine",    "GA","Atlanta",  "Private",1,5,35000,1300,30,"Urban","Small",
     "Medicine,Pre-Med,Public Health",
     "https://msm.edu","HBCU medical school. Mission to serve underserved communities."),
    ("Clark Atlanta University",        "GA","Atlanta",  "Private",1,56,25000,1010,20,"Urban","Medium",
     "Business,Communications,Social Work,Computer Science,Education",
     "https://cau.edu","Part of Atlanta University Center. Adjacent to Morehouse and Spelman."),
    ("Xavier University of Louisiana",  "LA","New Orleans","Private",1,66,26000,1050,22,"Urban","Small",
     "Pre-Med,Pharmacy,Biology,Chemistry,Education",
     "https://xula.edu","#1 HBCU for producing Black doctors. Pre-health pipeline is unmatched."),
    ("Bethune-Cookman University",      "FL","Daytona Beach","Private",1,55,17000,940,18,"Suburban","Small",
     "Business,Nursing,Education,Communications,Criminal Justice",
     "https://cookman.edu","Mary McLeod Bethune's legacy. Affordable HBCU in Florida."),
    ("Dillard University",              "LA","New Orleans","Private",1,44,20000,1000,20,"Urban","Small",
     "Business,Nursing,Biology,Psychology,Urban Studies",
     "https://dillard.edu","Liberal arts HBCU in New Orleans. Diverse academic programs."),
    ("Wake Forest University",          "NC","Winston-Salem","Private",0,27,57000,1430,33,"Suburban","Medium",
     "Business,Pre-Med,Law,Psychology,Communications",
     "https://wfu.edu","Test-optional pioneer. Strong pre-med. Excellent business school."),
    ("University of Notre Dame",        "IN","Notre Dame","Private",0,13,57000,1480,34,"Suburban","Medium",
     "Business,Engineering,Pre-Law,Political Science,Film,Theology",
     "https://nd.edu","Catholic. Top 20 overall. Fighting Irish. Strong alumni loyalty."),
]

# ── DB Tables ─────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    ai  = "SERIAL PRIMARY KEY"    if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    ts  = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))" if USE_POSTGRES else "DEFAULT (datetime('now'))"

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_colleges (
        id {ai},
        name TEXT NOT NULL UNIQUE,
        state TEXT NOT NULL,
        city TEXT NOT NULL,
        type TEXT NOT NULL,
        hbcu INTEGER DEFAULT 0,
        acceptance_rate INTEGER DEFAULT 50,
        tuition INTEGER DEFAULT 30000,
        avg_sat INTEGER DEFAULT 1200,
        avg_act INTEGER DEFAULT 26,
        setting TEXT DEFAULT 'Suburban',
        size TEXT DEFAULT 'Medium',
        majors TEXT DEFAULT '',
        website TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        seeded INTEGER DEFAULT 1
    )""")

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_user_college_list (
        id {ai},
        user_email TEXT NOT NULL,
        college_name TEXT NOT NULL,
        college_type TEXT DEFAULT 'target',
        notes TEXT DEFAULT '',
        added_at TEXT {ts},
        UNIQUE(user_email, college_name)
    )""")

    conn.commit()
    conn.close()


def _seed_colleges():
    """Seed the college database if empty."""
    conn = get_conn()
    c = db_exec(conn, "SELECT COUNT(*) FROM cc_colleges")
    count = c.fetchone()[0]
    if count > 0:
        conn.close()
        return
    ph = "%s" if USE_POSTGRES else "?"
    for row in _COLLEGE_SEEDS:
        try:
            db_exec(conn, f"""
                INSERT OR IGNORE INTO cc_colleges
                (name,state,city,type,hbcu,acceptance_rate,tuition,avg_sat,avg_act,setting,size,majors,website,notes)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
            """, row)
        except Exception:
            pass
    conn.commit()
    conn.close()


def _load_colleges(
    search: str = "",
    state: str = "All",
    school_type: str = "All",
    hbcu_only: bool = False,
    max_tuition: int = 70000,
    max_accept: int = 100,
    min_accept: int = 0,
    major_filter: str = "",
    size_filter: str = "All",
) -> list[dict]:
    conn = get_conn()
    q = "SELECT * FROM cc_colleges WHERE 1=1"
    params = []
    ph = "%s" if USE_POSTGRES else "?"
    if search:
        q += f" AND (LOWER(name) LIKE {ph} OR LOWER(city) LIKE {ph} OR LOWER(majors) LIKE {ph})"
        s = f"%{search.lower()}%"
        params += [s, s, s]
    if state != "All":
        q += f" AND state = {ph}"
        params.append(state)
    if school_type != "All":
        q += f" AND type = {ph}"
        params.append(school_type)
    if hbcu_only:
        q += f" AND hbcu = {ph}"
        params.append(1)
    if max_tuition < 70000:
        q += f" AND tuition <= {ph}"
        params.append(max_tuition)
    if max_accept < 100:
        q += f" AND acceptance_rate <= {ph}"
        params.append(max_accept)
    if min_accept > 0:
        q += f" AND acceptance_rate >= {ph}"
        params.append(min_accept)
    if major_filter:
        q += f" AND LOWER(majors) LIKE {ph}"
        params.append(f"%{major_filter.lower()}%")
    if size_filter != "All":
        q += f" AND size = {ph}"
        params.append(size_filter)
    q += " ORDER BY hbcu DESC, acceptance_rate ASC"

    c = db_exec(conn, q, params if params else None)
    rows = c.fetchall()
    conn.close()
    if rows and hasattr(rows[0], "keys"):
        return [dict(r) for r in rows]
    cols = [d[0] for d in c.description] if hasattr(c, "description") else []
    return [dict(zip(cols, r)) for r in rows]


def _load_user_list(user_email: str) -> list[dict]:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    c = db_exec(conn, f"""
        SELECT ul.*, col.state, col.hbcu, col.acceptance_rate, col.tuition,
               col.avg_sat, col.type, col.setting, col.website
        FROM cc_user_college_list ul
        LEFT JOIN cc_colleges col ON ul.college_name = col.name
        WHERE ul.user_email = {ph}
        ORDER BY ul.college_type, ul.added_at
    """, (user_email,))
    rows = c.fetchall()
    conn.close()
    if rows and hasattr(rows[0], "keys"):
        return [dict(r) for r in rows]
    return []


def _add_to_list(user_email: str, college_name: str, college_type: str = "target", notes: str = "") -> bool:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    try:
        db_exec(conn, f"""
            INSERT INTO cc_user_college_list (user_email, college_name, college_type, notes)
            VALUES ({ph},{ph},{ph},{ph})
        """, (user_email, college_name, college_type, notes))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def _remove_from_list(entry_id: int) -> None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"DELETE FROM cc_user_college_list WHERE id = {ph}", (entry_id,))
    conn.commit()
    conn.close()


def _get_college_detail(name: str) -> dict | None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    c = db_exec(conn, f"SELECT * FROM cc_colleges WHERE name = {ph}", (name,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row) if hasattr(row, "keys") else dict(zip([d[0] for d in c.description], row))


try:
    _ensure_tables()
    _seed_colleges()
except Exception as _e:
    st.warning(f"⚠️ Could not initialize College List tables: {_e}")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --cc-primary:#6C63FF; --cc-accent:#FF6B6B; --cc-success:#51CF66;
    --cc-bg-card:#1a1a2e; --cc-text-muted:#8892a4; --cc-border:#2a2a4a;
}
.cc-college-card {
    background:#1a1a2e; border:1px solid #2a2a4a; border-radius:14px;
    padding:20px 22px; margin-bottom:14px;
    transition:border-color 0.2s,box-shadow 0.2s;
}
.cc-college-card:hover { border-color:#6C63FF; box-shadow:0 8px 24px rgba(108,99,255,0.15); }
.cc-college-name { font-size:1.1rem; font-weight:700; color:#fafafa; margin-bottom:4px; }
.cc-college-meta { font-size:0.85rem; color:#8892a4; margin-bottom:8px; }
.cc-hbcu-badge {
    display:inline-block; background:linear-gradient(135deg,#FF6B6B,#ff8e53);
    color:#fff; font-size:0.72rem; font-weight:700; padding:2px 10px;
    border-radius:20px; margin-left:8px; vertical-align:middle;
}
.cc-accept-badge {
    display:inline-block; padding:2px 10px; border-radius:20px;
    font-size:0.72rem; font-weight:700;
}
.accept-low  { background:#2d1b1b; color:#FF6B6B; }
.accept-mid  { background:#2d261b; color:#FFA94D; }
.accept-high { background:#1b2d1b; color:#51CF66; }
.cc-tag {
    display:inline-block; background:#2a2a4a; color:#8892a4;
    font-size:0.72rem; padding:2px 8px; border-radius:6px; margin:2px 2px 0 0;
}
.cc-section-title { font-size:1.7rem; font-weight:800; color:#fafafa; margin-bottom:6px; }
.cc-section-sub { font-size:0.95rem; color:#8892a4; margin-bottom:20px; }
.cc-compare-col {
    background:#1a1a2e; border:1px solid #2a2a4a; border-radius:14px;
    padding:20px; height:100%;
}
.cc-compare-name { font-size:1.05rem; font-weight:700; color:#fafafa; margin-bottom:12px; text-align:center; }
.cc-compare-stat { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #2a2a4a; }
.cc-compare-label { font-size:0.85rem; color:#8892a4; }
.cc-compare-value { font-size:0.85rem; color:#fafafa; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="cc-section-title">🏫 College List Builder</div>
<div class="cc-section-sub">
    Search thousands of colleges, filter by what matters to you, save schools
    to your personal list, and compare them side-by-side. Built with HBCUs front and center.
</div>
""", unsafe_allow_html=True)

user_email = st.session_state.get("email", st.session_state.get("username", "guest"))

tab_find, tab_list, tab_compare, tab_ai = st.tabs([
    "🔍 Find Colleges", "💾 My List", "⚖️ Compare", "🤖 AI Advisor"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — FIND COLLEGES
# ══════════════════════════════════════════════════════════════════════════════
with tab_find:
    st.markdown("#### 🔍 Search & Filter")

    # Filters row
    fcol1, fcol2, fcol3, fcol4 = st.columns([2, 1, 1, 1])
    search_q  = fcol1.text_input("Search by name, city, or major", placeholder="e.g. engineering, Atlanta, Howard…")
    state_opt = fcol2.selectbox("State", ["All","AL","CA","CT","DC","FL","GA","IL","IN","LA","MA","MD","MI","NC","NJ","NY","OH","PA","TN","TX","VA","WA","WI"])
    type_opt  = fcol3.selectbox("Type", ["All", "Public", "Private"])
    size_opt  = fcol4.selectbox("Size", ["All", "Small", "Medium", "Large"])

    fcol5, fcol6, fcol7, fcol8 = st.columns([1, 1, 1, 1])
    hbcu_only    = fcol5.checkbox("🏆 HBCUs Only")
    max_tuition  = fcol6.select_slider("Max Tuition ($)", options=[5000,10000,15000,20000,25000,30000,40000,50000,60000,70000], value=70000)
    accept_range = fcol7.slider("Acceptance Rate (%)", 0, 100, (0, 100))
    major_q      = fcol8.text_input("Major / Focus", placeholder="e.g. nursing, CS…")

    colleges = _load_colleges(
        search=search_q, state=state_opt, school_type=type_opt,
        hbcu_only=hbcu_only, max_tuition=max_tuition,
        max_accept=accept_range[1], min_accept=accept_range[0],
        major_filter=major_q, size_filter=size_opt,
    )

    st.markdown(f"**{len(colleges)} colleges found**")

    if not colleges:
        st.info("No colleges match your filters. Try broadening your search.")
    else:
        for col in colleges:
            accept = col.get("acceptance_rate", 50)
            if accept <= 15:
                ab_cls, ab_txt = "accept-low", f"{accept}% 🔥 Reach"
            elif accept <= 40:
                ab_cls, ab_txt = "accept-mid", f"{accept}% 🎯 Target"
            else:
                ab_cls, ab_txt = "accept-high", f"{accept}% ✅ Likely"

            hbcu_badge = '<span class="cc-hbcu-badge">HBCU</span>' if col.get("hbcu") else ""
            majors_html = "".join(f'<span class="cc-tag">{m.strip()}</span>' for m in col.get("majors", "").split(",")[:5] if m.strip())
            tuition_k = col.get("tuition", 0) // 1000

            with st.container():
                st.markdown(f"""
                <div class="cc-college-card">
                    <div class="cc-college-name">
                        {col['name']}{hbcu_badge}
                        <span class="cc-accept-badge {ab_cls}">{ab_txt}</span>
                    </div>
                    <div class="cc-college-meta">
                        {col.get('city','')}, {col.get('state','')} &nbsp;·&nbsp;
                        {col.get('type','')} &nbsp;·&nbsp;
                        {col.get('setting','')} &nbsp;·&nbsp;
                        {col.get('size','')} &nbsp;·&nbsp;
                        <strong style="color:#6C63FF;">${tuition_k}k/yr</strong> &nbsp;·&nbsp;
                        SAT avg {col.get('avg_sat','N/A')} &nbsp;·&nbsp;
                        ACT avg {col.get('avg_act','N/A')}
                    </div>
                    <div style="font-size:0.88rem;color:#c8d0dc;margin-bottom:8px;">{col.get('notes','')}</div>
                    <div>{majors_html}</div>
                </div>
                """, unsafe_allow_html=True)

                btn_col1, btn_col2, btn_col3, _ = st.columns([1, 1, 1, 4])
                if btn_col1.button("⭐ Reach", key=f"reach_{col['name']}", use_container_width=True):
                    if _add_to_list(user_email, col["name"], "reach"):
                        st.success(f"Added {col['name']} to Reach list!")
                        st.rerun()
                if btn_col2.button("🎯 Target", key=f"target_{col['name']}", use_container_width=True):
                    if _add_to_list(user_email, col["name"], "target"):
                        st.success(f"Added {col['name']} to Target list!")
                        st.rerun()
                if btn_col3.button("✅ Safety", key=f"safety_{col['name']}", use_container_width=True):
                    if _add_to_list(user_email, col["name"], "safety"):
                        st.success(f"Added {col['name']} to Safety list!")
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MY LIST
# ══════════════════════════════════════════════════════════════════════════════
with tab_list:
    my_list = _load_user_list(user_email)

    if not my_list:
        st.info("Your college list is empty. Go to **Find Colleges** and add schools to get started!")
    else:
        reach   = [c for c in my_list if c.get("college_type") == "reach"]
        targets = [c for c in my_list if c.get("college_type") == "target"]
        safety  = [c for c in my_list if c.get("college_type") == "safety"]

        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("⭐ Reach Schools", len(reach))
        lc2.metric("🎯 Target Schools", len(targets))
        lc3.metric("✅ Safety Schools", len(safety))

        st.markdown("---")

        def _render_list_group(label: str, icon: str, schools: list, color: str):
            if not schools:
                return
            st.markdown(f"### {icon} {label} Schools")
            for s in schools:
                hbcu = "🏆 HBCU · " if s.get("hbcu") else ""
                accept = s.get("acceptance_rate", "?")
                tuition = s.get("tuition", 0)
                sc1, sc2, sc3 = st.columns([4, 1, 1])
                sc1.markdown(
                    f"**{s['college_name']}**  \n"
                    f"<span style='font-size:0.85rem;color:#8892a4;'>"
                    f"{hbcu}{s.get('state','?')} · {s.get('type','?')} · "
                    f"Accept: {accept}% · ${tuition//1000}k/yr</span>",
                    unsafe_allow_html=True,
                )
                new_type = sc2.selectbox(
                    "Type", ["reach","target","safety"],
                    index=["reach","target","safety"].index(s.get("college_type","target")),
                    key=f"type_{s['id']}",
                    label_visibility="collapsed",
                )
                if new_type != s.get("college_type"):
                    conn = get_conn()
                    ph = "%s" if USE_POSTGRES else "?"
                    db_exec(conn, f"UPDATE cc_user_college_list SET college_type={ph} WHERE id={ph}", (new_type, s["id"]))
                    conn.commit()
                    conn.close()
                    st.rerun()
                if sc3.button("🗑️", key=f"del_{s['id']}", use_container_width=True):
                    _remove_from_list(s["id"])
                    st.rerun()
            st.markdown("---")

        _render_list_group("Reach", "⭐", reach,   "#FF6B6B")
        _render_list_group("Target", "🎯", targets, "#FFA94D")
        _render_list_group("Safety", "✅", safety,  "#51CF66")

        # College strategy tip
        if len(reach) + len(targets) + len(safety) > 0:
            st.info(
                "📌 **Darrian's College List Formula:**  \n"
                "Apply to **2–3 reach** schools (accept rate < 20%), "
                "**5–6 target** schools (accept rate 20–60%), and "
                "**2–3 safety** schools (accept rate > 60% and you have stats above average).  \n"
                "**10–12 total applications** is the sweet spot for most students."
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("#### ⚖️ Compare Colleges Side-by-Side")

    all_names = [r[0] for r in _COLLEGE_SEEDS]
    sel_col1, sel_col2, sel_col3 = st.columns(3)
    pick_a = sel_col1.selectbox("School 1", ["(select)"] + all_names, key="cmp_a")
    pick_b = sel_col2.selectbox("School 2", ["(select)"] + all_names, key="cmp_b")
    pick_c = sel_col3.selectbox("School 3 (optional)", ["(none)"] + all_names, key="cmp_c")

    picks = [p for p in [pick_a, pick_b, pick_c] if p not in ("(select)", "(none)")]

    if len(picks) < 2:
        st.info("Select at least 2 colleges above to compare them.")
    else:
        details = [_get_college_detail(p) for p in picks]
        details = [d for d in details if d]

        cols = st.columns(len(details))
        fields = [
            ("State", "state"), ("City", "city"), ("Type", "type"),
            ("HBCU", "hbcu"), ("Acceptance Rate", "acceptance_rate"),
            ("Tuition / yr", "tuition"), ("Avg SAT", "avg_sat"),
            ("Avg ACT", "avg_act"), ("Setting", "setting"), ("Size", "size"),
        ]
        for i, (col, det) in enumerate(zip(cols, details)):
            with col:
                hbcu_badge = ' <span class="cc-hbcu-badge">HBCU</span>' if det.get("hbcu") else ""
                st.markdown(f"""
                <div class="cc-compare-col">
                    <div class="cc-compare-name">{det['name']}{hbcu_badge}</div>
                    {"".join(
                        f'<div class="cc-compare-stat"><span class="cc-compare-label">{lbl}</span>'
                        f'<span class="cc-compare-value">'
                        f'{"✅ Yes" if key == "hbcu" and det.get(key) else ("$" + f"{det.get(key,0):,}" if key == "tuition" else (str(det.get(key, "N/A")) + ("%" if key == "acceptance_rate" else "")))}'
                        f'</span></div>'
                        for lbl, key in fields
                    )}
                </div>
                """, unsafe_allow_html=True)

        # College notes
        st.markdown("---")
        for det in details:
            with st.expander(f"📝 About {det['name']}"):
                st.write(det.get("notes", "No additional info available."))
                if det.get("website"):
                    st.markdown(f"🌐 [Visit Website]({det['website']})", unsafe_allow_html=True)
                st.write(f"**Top Majors:** {det.get('majors','N/A')}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI ADVISOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown("#### 🤖 AI College Advisor")
    st.caption("Claude AI reviews your list and gives personalized college strategy advice.")

    if not is_cc_ai_allowed(user_email):
        st.warning("🔒 AI features are currently owner-only during beta. Check back soon!")
    else:
        api_key = get_setting("anthropic_api_key")
        if not api_key:
            st.error("⚙️ Anthropic API key not configured. Add it in Settings → API Keys.")
        else:
            my_list_for_ai = _load_user_list(user_email)

            if not my_list_for_ai:
                st.info("Add schools to your college list first (Find Colleges tab), then come back here for AI advice.")
            else:
                # Student profile inputs for better advice
                st.markdown("**Tell Claude a bit about you (optional — better advice):**")
                ai_c1, ai_c2, ai_c3 = st.columns(3)
                ai_gpa    = ai_c1.number_input("GPA (out of 4.0)", 0.0, 4.0, 3.5, 0.1)
                ai_sat    = ai_c2.number_input("SAT Score (0 if N/A)", 0, 1600, 1200, 10)
                ai_major  = ai_c3.text_input("Intended Major", placeholder="e.g. Computer Science")
                ai_prompt = st.text_area(
                    "Ask Claude anything about your list",
                    value="Review my college list and give me a realistic assessment. Which schools are best fits? Am I applying to enough HBCUs? Any concerns or advice?",
                    height=100,
                )

                if st.button("🤖 Get AI College Advice", type="primary", use_container_width=True):
                    list_summary = "\n".join([
                        f"- {c['college_name']} ({c.get('college_type','target').upper()}) | "
                        f"{c.get('state','?')} | Accept {c.get('acceptance_rate','?')}% | "
                        f"{'HBCU' if c.get('hbcu') else 'Non-HBCU'}"
                        for c in my_list_for_ai
                    ])
                    prompt = f"""You are a college admissions advisor reviewing a student's college list.

STUDENT PROFILE:
- GPA: {ai_gpa}
- SAT: {ai_sat if ai_sat > 0 else 'Not provided'}
- Intended Major: {ai_major if ai_major else 'Undecided'}

COLLEGE LIST:
{list_summary}

STUDENT QUESTION: {ai_prompt}

Provide honest, encouraging, and actionable college counseling advice. 
- Comment on reach/target/safety balance
- Highlight any HBCU opportunities they shouldn't miss
- Note financial aid considerations  
- Suggest 1-2 schools to add if their list is weak in any area
- Keep it to 3-4 paragraphs, plain language"""

                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=api_key)
                        with st.spinner("Claude is reviewing your college list…"):
                            response = client.messages.create(
                                model="claude-opus-4-5",
                                max_tokens=800,
                                messages=[{"role": "user", "content": prompt}],
                            )
                        st.markdown("---")
                        st.markdown("**🤖 Claude's College Advice:**")
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
