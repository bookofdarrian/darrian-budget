"""
Page 149 — FAFSA & Financial Aid Tracker
NC A&T grad. HBCU community. Build the tool you needed.
"""

import streamlit as st
from datetime import date, datetime
import json

from utils.db import init_db, get_conn, execute as db_exec
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css, get_setting

st.set_page_config(
    page_title="FAFSA & Financial Aid Tracker — Peach State Savings",
    page_icon="🎓",
    layout="wide",
)

init_db()
inject_css()
require_login()

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
CURRENT_YEAR = date.today().year
FAFSA_YEAR = f"{CURRENT_YEAR}-{CURRENT_YEAR + 1}"

AID_TYPES = ["Pell Grant", "Institutional Grant", "State Grant", "Merit Scholarship",
             "Need-Based Scholarship", "Work-Study", "Subsidized Loan",
             "Unsubsidized Loan", "PLUS Loan", "Private Loan", "Other"]

LOAN_TYPES = ["Subsidized Loan", "Unsubsidized Loan", "PLUS Loan", "Private Loan"]

STATE_DEADLINES = {
    "Alabama": "February 15",
    "Alaska": "April 15",
    "Arizona": "No state deadline",
    "Arkansas": "June 1",
    "California": "March 2",
    "Colorado": "No state deadline",
    "Connecticut": "February 15",
    "Delaware": "April 15",
    "Florida": "May 15",
    "Georgia": "July 1",
    "Hawaii": "No state deadline",
    "Idaho": "March 1",
    "Illinois": "October 1 (prior year)",
    "Indiana": "April 15",
    "Iowa": "July 1",
    "Kansas": "April 1",
    "Kentucky": "February 15",
    "Louisiana": "July 1",
    "Maine": "May 1",
    "Maryland": "March 1",
    "Massachusetts": "May 1",
    "Michigan": "March 1",
    "Minnesota": "30 days after admission",
    "Mississippi": "March 31",
    "Missouri": "February 1",
    "Montana": "March 1",
    "Nebraska": "No state deadline",
    "Nevada": "February 1",
    "New Hampshire": "No state deadline",
    "New Jersey": "June 1 (fall); October 1 (spring)",
    "New Mexico": "March 1",
    "New York": "May 1",
    "North Carolina": "March 1",
    "North Dakota": "April 15",
    "Ohio": "October 1",
    "Oklahoma": "March 1",
    "Oregon": "March 1",
    "Pennsylvania": "May 1",
    "Rhode Island": "March 1",
    "South Carolina": "June 30",
    "South Dakota": "No state deadline",
    "Tennessee": "February 1",
    "Texas": "January 15",
    "Utah": "March 31",
    "Vermont": "March 1",
    "Virginia": "July 31",
    "Washington": "February 28",
    "West Virginia": "April 15",
    "Wisconsin": "No state deadline",
    "Wyoming": "No state deadline",
    "Washington D.C.": "May 1",
}

HBCU_LIST = [
    "NC A&T State University", "Howard University", "Spelman College",
    "Morehouse College", "Hampton University", "Tuskegee University",
    "Morgan State University", "Tennessee State University",
    "Florida A&M University", "Bethune-Cookman University",
    "Clark Atlanta University", "Xavier University of Louisiana",
    "Grambling State University", "Jackson State University",
    "North Carolina Central University", "Southern University",
    "Delaware State University", "Bowie State University",
    "Virginia State University", "Elizabeth City State University",
    "Fayetteville State University", "Winston-Salem State University",
    "Alcorn State University", "Alabama A&M University",
    "Alabama State University", "Other HBCU", "Other University",
]


# ─────────────────────────────────────────────
# DB SETUP
# ─────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    db_exec(conn, """
        CREATE TABLE IF NOT EXISTS fafsa_schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            school_name TEXT NOT NULL,
            is_hbcu INTEGER DEFAULT 0,
            applied INTEGER DEFAULT 0,
            accepted INTEGER DEFAULT 0,
            deadline TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, """
        CREATE TABLE IF NOT EXISTS fafsa_aid_awards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            school_id INTEGER,
            school_name TEXT NOT NULL,
            aid_type TEXT NOT NULL,
            amount REAL NOT NULL,
            per_year INTEGER DEFAULT 1,
            renewable INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, """
        CREATE TABLE IF NOT EXISTS fafsa_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            family_income REAL DEFAULT 0,
            household_size INTEGER DEFAULT 1,
            dependents INTEGER DEFAULT 0,
            state TEXT DEFAULT '',
            fafsa_filed INTEGER DEFAULT 0,
            fafsa_filed_date TEXT,
            efc REAL DEFAULT 0,
            aid_year TEXT DEFAULT '',
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.close()


_ensure_tables()


# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────
def _get_user_id():
    return st.session_state.get("user_id", 1)


def _load_profile():
    conn = get_conn()
    uid = _get_user_id()
    cur = db_exec(conn, "SELECT * FROM fafsa_profile WHERE user_id = ?", (uid,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def _save_profile(income, household, dependents, state, filed, filed_date, efc, notes):
    conn = get_conn()
    uid = _get_user_id()
    db_exec(conn, """
        INSERT INTO fafsa_profile (user_id, family_income, household_size, dependents, state,
            fafsa_filed, fafsa_filed_date, efc, aid_year, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            family_income=excluded.family_income,
            household_size=excluded.household_size,
            dependents=excluded.dependents,
            state=excluded.state,
            fafsa_filed=excluded.fafsa_filed,
            fafsa_filed_date=excluded.fafsa_filed_date,
            efc=excluded.efc,
            aid_year=excluded.aid_year,
            notes=excluded.notes,
            updated_at=CURRENT_TIMESTAMP
    """, (uid, income, household, dependents, state,
          1 if filed else 0, str(filed_date) if filed else None,
          efc, FAFSA_YEAR, notes))
    conn.close()


def _load_schools():
    conn = get_conn()
    uid = _get_user_id()
    cur = db_exec(conn, 
        "SELECT * FROM fafsa_schools WHERE user_id = ? ORDER BY school_name", (uid,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _add_school(name, is_hbcu, applied, accepted, deadline, notes):
    conn = get_conn()
    uid = _get_user_id()
    db_exec(conn, """
        INSERT INTO fafsa_schools (user_id, school_name, is_hbcu, applied, accepted, deadline, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (uid, name, 1 if is_hbcu else 0, 1 if applied else 0,
          1 if accepted else 0, deadline, notes))
    conn.close()


def _delete_school(school_id):
    conn = get_conn()
    db_exec(conn, "DELETE FROM fafsa_schools WHERE id = ?", (school_id,))
    db_exec(conn, "DELETE FROM fafsa_aid_awards WHERE school_id = ?", (school_id,))
    conn.close()


def _load_awards():
    conn = get_conn()
    uid = _get_user_id()
    cur = db_exec(conn, 
        "SELECT * FROM fafsa_aid_awards WHERE user_id = ? ORDER BY school_name, aid_type", (uid,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _add_award(school_id, school_name, aid_type, amount, per_year, renewable, notes):
    conn = get_conn()
    uid = _get_user_id()
    db_exec(conn, """
        INSERT INTO fafsa_aid_awards (user_id, school_id, school_name, aid_type, amount, per_year, renewable, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (uid, school_id, school_name, aid_type, amount,
          1 if per_year else 0, 1 if renewable else 0, notes))
    conn.close()


def _delete_award(award_id):
    conn = get_conn()
    db_exec(conn, "DELETE FROM fafsa_aid_awards WHERE id = ?", (award_id,))
    conn.close()


def _estimate_efc(income, household_size, dependents):
    """Rough EFC estimate — NOT official. Use studentaid.gov for real numbers."""
    if income <= 0:
        return 0
    base_rate = 0.22
    if income < 30000:
        efc = max(0, income * 0.0)
    elif income < 50000:
        efc = income * 0.06
    elif income < 75000:
        efc = income * 0.12
    elif income < 100000:
        efc = income * 0.18
    else:
        efc = income * base_rate
    # Adjust for household size
    if household_size > 3:
        efc *= max(0.5, 1 - (household_size - 3) * 0.08)
    # Dependent adjustment
    if dependents > 1:
        efc *= max(0.6, 1 - (dependents - 1) * 0.05)
    return round(efc, 2)


def _get_pell_estimate(efc):
    """Estimate Pell Grant. Max Pell 2024-25: $7,395. Phase out around EFC $6,206."""
    MAX_PELL = 7395
    if efc <= 0:
        return MAX_PELL
    if efc >= 6206:
        return 0
    pct = max(0, 1 - (efc / 6206))
    return round(MAX_PELL * pct, 0)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                           label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                 label="Todo",               icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",    label="Creator",            icon="🎬")
st.sidebar.page_link("pages/25_notes.py",                label="Notes",              icon="📝")
st.sidebar.page_link("pages/26_media_library.py",        label="Media Library",      icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",   label="Personal Assistant", icon="🤖")
st.sidebar.page_link("pages/147_proactive_ai_engine.py", label="Proactive AI",       icon="🧠")
st.sidebar.page_link("pages/149_fafsa_tracker.py",       label="FAFSA Tracker",      icon="🎓")
render_sidebar_user_widget()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.title("🎓 FAFSA & Financial Aid Tracker")
st.caption(f"Aid Year: {FAFSA_YEAR} · FAFSA opens October 1 · studentaid.gov")

st.info(
    "⚠️ **EFC estimates on this page are approximate.** For your official EFC/SAI, "
    "complete your FAFSA at [studentaid.gov](https://studentaid.gov). "
    "This tool helps you **organize, compare, and plan** — not replace official sources.",
    icon="ℹ️"
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 My Profile", "🏫 Schools", "💰 Aid Awards", "📊 Compare Schools", "📅 Deadlines"
])

# ─────────────────────────────────────────────
# TAB 1 — MY PROFILE
# ─────────────────────────────────────────────
with tab1:
    st.subheader("Your FAFSA Profile")
    profile = _load_profile()

    col1, col2 = st.columns(2)
    with col1:
        income = st.number_input(
            "Household AGI (Adjusted Gross Income) $",
            min_value=0.0, value=float(profile.get("family_income", 0)),
            step=1000.0, format="%.0f",
            help="From your (or your parents') most recent tax return"
        )
        household = st.number_input(
            "Household Size",
            min_value=1, value=int(profile.get("household_size", 1)), step=1
        )
        dependents = st.number_input(
            "Number of Dependents in College",
            min_value=0, value=int(profile.get("dependents", 0)), step=1,
            help="Other family members attending college at same time lowers EFC"
        )
        state = st.selectbox(
            "Home State",
            options=[""] + sorted(STATE_DEADLINES.keys()),
            index=0 if not profile.get("state") else
                  (list(STATE_DEADLINES.keys()).index(profile.get("state")) + 1
                   if profile.get("state") in STATE_DEADLINES else 0)
        )

    with col2:
        filed = st.checkbox("FAFSA Filed ✅", value=bool(profile.get("fafsa_filed", False)))
        filed_date = st.date_input(
            "Date Filed",
            value=date.today() if not profile.get("fafsa_filed_date") else
                  datetime.strptime(profile["fafsa_filed_date"], "%Y-%m-%d").date()
        ) if filed else None

        manual_efc = st.number_input(
            "EFC / SAI (if known from FAFSA) $",
            min_value=0.0,
            value=float(profile.get("efc", 0)),
            step=100.0, format="%.0f",
            help="Leave 0 to use our estimate. Enter your official number once you have it."
        )
        notes = st.text_area("Notes", value=profile.get("notes", ""), height=80)

    # Estimates
    estimated_efc = _estimate_efc(income, household, dependents)
    display_efc = manual_efc if manual_efc > 0 else estimated_efc
    pell = _get_pell_estimate(display_efc)

    st.markdown("---")
    st.subheader("📊 Estimated Aid Eligibility")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Household Income", f"${income:,.0f}")
    m2.metric(
        "EFC / SAI",
        f"${display_efc:,.0f}",
        delta="Official" if manual_efc > 0 else "Estimate ⚠️",
        delta_color="off"
    )
    m3.metric("Est. Pell Grant", f"${pell:,.0f}/yr", help="Max Pell 2024-25: $7,395")
    m4.metric("Dependents in College", str(dependents))

    if pell > 0:
        st.success(f"🎉 Based on your income, you may qualify for up to **${pell:,.0f}/year** in Pell Grants — this is FREE money, no repayment required.")
    elif display_efc >= 6206:
        st.warning("Your EFC may be too high for Pell Grant eligibility, but you can still qualify for institutional grants, merit aid, and subsidized loans.")

    if st.button("💾 Save Profile", type="primary"):
        _save_profile(income, household, dependents, state, filed, filed_date, display_efc, notes)
        st.success("Profile saved!")
        st.rerun()

    # State deadline reminder
    if state and state in STATE_DEADLINES:
        st.info(f"📅 **{state} state aid deadline:** {STATE_DEADLINES[state]}")


# ─────────────────────────────────────────────
# TAB 2 — SCHOOLS
# ─────────────────────────────────────────────
with tab2:
    st.subheader("Schools You're Applying To / Considering")

    schools = _load_schools()

    with st.expander("➕ Add a School", expanded=len(schools) == 0):
        sc1, sc2, sc3 = st.columns([2, 1, 1])
        with sc1:
            school_search = st.text_input("School Name (or select HBCU)", placeholder="Start typing...")
            school_name = school_search if school_search else ""
            hbcu_pick = st.selectbox("...or pick from HBCU list", [""] + HBCU_LIST)
            final_name = hbcu_pick if hbcu_pick else school_name
        with sc2:
            is_hbcu = st.checkbox("HBCU? 🐾", value=(hbcu_pick and hbcu_pick != "Other University"))
            s_applied = st.checkbox("Applied?")
            s_accepted = st.checkbox("Accepted?")
        with sc3:
            s_deadline = st.text_input("School Aid Deadline", placeholder="e.g. March 1")
            s_notes = st.text_area("Notes", height=80)

        if st.button("Add School", type="primary"):
            if final_name:
                _add_school(final_name, is_hbcu, s_applied, s_accepted, s_deadline, s_notes)
                st.success(f"Added {final_name}!")
                st.rerun()
            else:
                st.error("Please enter a school name.")

    st.markdown("---")
    if not schools:
        st.info("No schools added yet. Add your first school above!")
    else:
        for school in schools:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
                c1.markdown(f"**{school['school_name']}** {'🐾' if school['is_hbcu'] else ''}")
                c2.write("✅ Applied" if school["applied"] else "⏳ Pending")
                c3.write("🎉 Accepted" if school["accepted"] else "—")
                c4.write(school["deadline"] or "—")
                if c5.button("🗑️", key=f"del_school_{school['id']}"):
                    _delete_school(school["id"])
                    st.rerun()
                if school["notes"]:
                    st.caption(school["notes"])
                st.markdown("---")


# ─────────────────────────────────────────────
# TAB 3 — AID AWARDS
# ─────────────────────────────────────────────
with tab3:
    st.subheader("Award Letters — Track Every Dollar")
    st.caption("Enter each aid item from your award letters. Compare apples to apples.")

    schools = _load_schools()
    awards = _load_awards()

    with st.expander("➕ Add Aid Award", expanded=len(awards) == 0):
        a1, a2, a3 = st.columns(3)
        with a1:
            if schools:
                school_options = {s["school_name"]: s["id"] for s in schools}
                a_school_name = st.selectbox("School", list(school_options.keys()))
                a_school_id = school_options[a_school_name]
            else:
                a_school_name = st.text_input("School Name")
                a_school_id = None
            a_type = st.selectbox("Aid Type", AID_TYPES)
        with a2:
            a_amount = st.number_input("Amount per Year $", min_value=0.0, step=100.0, format="%.0f")
            a_per_year = st.checkbox("Annual (renewable)", value=True)
            a_renewable = st.checkbox("Multi-year renewable", value=True)
        with a3:
            a_notes = st.text_area("Notes / Conditions", height=100,
                                   placeholder="e.g. maintain 3.0 GPA, full-time enrollment")

        if st.button("Add Award", type="primary"):
            if a_school_name and a_amount > 0:
                _add_award(a_school_id, a_school_name, a_type, a_amount, a_per_year, a_renewable, a_notes)
                st.success("Award added!")
                st.rerun()
            else:
                st.error("School and amount required.")

    st.markdown("---")

    if not awards:
        st.info("No awards entered yet. Add award letters from your schools above.")
    else:
        # Group by school
        from collections import defaultdict
        by_school = defaultdict(list)
        for aw in awards:
            by_school[aw["school_name"]].append(aw)

        for school_name, school_awards in by_school.items():
            total_grants = sum(a["amount"] for a in school_awards if a["aid_type"] not in LOAN_TYPES)
            total_loans = sum(a["amount"] for a in school_awards if a["aid_type"] in LOAN_TYPES)
            total_all = total_grants + total_loans

            st.markdown(f"### 🏫 {school_name}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Free Money (Grants/Scholarships)", f"${total_grants:,.0f}")
            c2.metric("Loans (must repay)", f"${total_loans:,.0f}")
            c3.metric("Total Package", f"${total_all:,.0f}")

            for aw in school_awards:
                ac1, ac2, ac3, ac4, ac5 = st.columns([2, 1, 1, 1, 1])
                is_loan = aw["aid_type"] in LOAN_TYPES
                ac1.write(f"{'💸' if is_loan else '🎁'} {aw['aid_type']}")
                ac2.write(f"${aw['amount']:,.0f}/yr")
                ac3.write("🔁 Renewable" if aw["renewable"] else "1x Only")
                if aw["notes"]:
                    ac4.caption(aw["notes"])
                if ac5.button("🗑️", key=f"del_award_{aw['id']}"):
                    _delete_award(aw["id"])
                    st.rerun()
            st.markdown("---")


# ─────────────────────────────────────────────
# TAB 4 — COMPARE SCHOOLS
# ─────────────────────────────────────────────
with tab4:
    st.subheader("📊 Side-by-Side Award Comparison")
    st.caption("Net cost = Total Cost of Attendance - Free Money (grants/scholarships)")

    awards = _load_awards()

    if not awards:
        st.info("Add award letters in the 'Aid Awards' tab to compare schools here.")
    else:
        from collections import defaultdict
        by_school = defaultdict(list)
        for aw in awards:
            by_school[aw["school_name"]].append(aw)

        # Build comparison table
        rows = []
        for sname, saws in by_school.items():
            total_free = sum(a["amount"] for a in saws if a["aid_type"] not in LOAN_TYPES)
            total_loans = sum(a["amount"] for a in saws if a["aid_type"] in LOAN_TYPES)
            pell_in_pkg = sum(a["amount"] for a in saws if a["aid_type"] == "Pell Grant")
            inst_grant = sum(a["amount"] for a in saws
                             if a["aid_type"] in ["Institutional Grant", "Merit Scholarship",
                                                   "Need-Based Scholarship", "State Grant"])
            rows.append({
                "School": sname,
                "Free Money": f"${total_free:,.0f}",
                "Pell Grant": f"${pell_in_pkg:,.0f}",
                "Institutional Aid": f"${inst_grant:,.0f}",
                "Loans": f"${total_loans:,.0f}",
                "Total Package": f"${total_free + total_loans:,.0f}",
            })

        import pandas as pd
        df = pd.DataFrame(rows).set_index("School")
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.subheader("💡 Award Letter Reading Guide")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
**🎁 Free Money (you KEEP this):**
- Pell Grant
- Institutional Grants
- Merit Scholarships
- State Grants
- Work-Study (earned, not borrowed)

**Always maximize free money first.**
            """)
        with col2:
            st.markdown("""
**💸 Loans (you REPAY this + interest):**
- Subsidized Loan: no interest while enrolled
- Unsubsidized Loan: interest accrues immediately
- PLUS Loan: parents borrow; higher interest rate
- Private Loan: worst terms; use as last resort

**Never borrow more than your expected first-year salary.**
            """)

        st.info(
            "🔑 **Rule of thumb:** Total student loan debt should be ≤ your expected starting salary. "
            "If NC A&T Computer Science grads start at ~$65K, don't borrow more than $65K total.",
            icon="💡"
        )


# ─────────────────────────────────────────────
# TAB 5 — DEADLINES
# ─────────────────────────────────────────────
with tab5:
    st.subheader("📅 State FAFSA Deadlines")
    st.caption("File EARLY — many states award aid first-come, first-served and run out of funds.")

    profile = _load_profile()
    user_state = profile.get("state", "")

    # Highlight user's state
    if user_state and user_state in STATE_DEADLINES:
        st.success(f"📍 Your state: **{user_state}** — Deadline: **{STATE_DEADLINES[user_state]}**")

    st.markdown("---")

    # Key federal dates
    st.subheader("🏛️ Federal FAFSA Key Dates")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
| Event | Date |
|-------|------|
| FAFSA Opens | October 1, {CURRENT_YEAR} |
| Aid Year | {FAFSA_YEAR} |
| Federal Deadline | June 30, {CURRENT_YEAR + 1} |
        """)
    with col2:
        st.markdown(f"""
**⚡ Pro tips:**
- File October 1 if possible — state money runs out
- You use **{CURRENT_YEAR - 1}** tax returns for {FAFSA_YEAR} FAFSA
- Update FAFSA if income changed significantly
- Check studentaid.gov for official dates
        """)

    st.markdown("---")
    st.subheader("All State Deadlines")

    # Search/filter
    state_search = st.text_input("🔍 Filter by state", placeholder="Type a state name...")

    states_to_show = {
        k: v for k, v in sorted(STATE_DEADLINES.items())
        if state_search.lower() in k.lower()
    } if state_search else STATE_DEADLINES

    # Display in 3 columns
    state_items = list(states_to_show.items())
    cols = st.columns(3)
    for i, (state_name, deadline) in enumerate(state_items):
        is_user = (state_name == user_state)
        with cols[i % 3]:
            if is_user:
                st.markdown(f"**📍 {state_name}:** {deadline}")
            else:
                st.write(f"**{state_name}:** {deadline}")

    st.markdown("---")
    st.markdown("""
### 📚 Resources
| Resource | Link |
|----------|------|
| File your FAFSA | [studentaid.gov/h/apply-for-aid/fafsa](https://studentaid.gov/h/apply-for-aid/fafsa) |
| EFC/SAI Calculator | [studentaid.gov/aid-estimator](https://studentaid.gov/aid-estimator) |
| HBCU Aid Info | [thehbcupage.com](https://thehbcupage.com) |
| College Scorecard | [collegescorecard.ed.gov](https://collegescorecard.ed.gov) |
| NC A&T Financial Aid | [ncat.edu/financial-aid](https://www.ncat.edu/cost-aid/financial-aid/index.php) |
| Khan Academy FAFSA Guide | [khanacademy.org/college-careers-more/financial-aid](https://www.khanacademy.org/college-careers-more/financial-aid) |
    """)
