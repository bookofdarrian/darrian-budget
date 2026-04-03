"""
College Confused — SAT/ACT Test Prep (Page 84)
Free resources, practice questions, score tracker, and AI study coach
to help students score higher and unlock scholarship opportunities.
"""
import os
import streamlit as st
from datetime import date
import json

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting, is_cc_ai_allowed
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_cc_css

st.set_page_config(
    page_title="SAT/ACT Prep — College Confused",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_cc_css()
require_login()

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

# ── Percentile Tables ──────────────────────────────────────────────────────────
SAT_PERCENTILES = {
    400: 1, 500: 1, 600: 3, 700: 7, 800: 13, 900: 23, 1000: 35,
    1100: 50, 1200: 64, 1300: 78, 1400: 89, 1500: 96, 1600: 99
}
ACT_PERCENTILES = {
    1: 1, 10: 1, 14: 5, 16: 9, 18: 16, 19: 20, 20: 27, 21: 33,
    22: 40, 23: 47, 24: 54, 25: 61, 26: 68, 27: 74, 28: 80,
    29: 85, 30: 89, 31: 92, 32: 95, 33: 97, 34: 98, 35: 99, 36: 99
}

# ── Practice Question Banks ────────────────────────────────────────────────────
SAT_MATH_QUESTIONS = [
    {
        "question": "If 3x + 7 = 22, what is the value of x?",
        "choices": ["3", "5", "7", "9"],
        "answer": "5",
        "explanation": "Subtract 7 from both sides: 3x = 15. Then divide by 3: x = 5. Always check your answer by plugging back in: 3(5) + 7 = 22 ✓",
        "difficulty": "easy",
        "topic": "Linear Equations"
    },
    {
        "question": "A store sells pencils for $0.25 each and pens for $1.50 each. If Sara buys 4 pencils and 3 pens, how much does she spend in total?",
        "choices": ["$4.50", "$5.00", "$5.50", "$6.00"],
        "answer": "$5.50",
        "explanation": "4 pencils × $0.25 = $1.00. 3 pens × $1.50 = $4.50. Total = $1.00 + $4.50 = $5.50",
        "difficulty": "easy",
        "topic": "Word Problems"
    },
    {
        "question": "What is 15% of 80?",
        "choices": ["8", "10", "12", "15"],
        "answer": "12",
        "explanation": "15% means 15/100. So 15/100 × 80 = 1200/100 = 12. Or multiply 0.15 × 80 = 12",
        "difficulty": "easy",
        "topic": "Percentages"
    },
    {
        "question": "If f(x) = 2x² - 3x + 1, what is f(3)?",
        "choices": ["7", "10", "13", "16"],
        "answer": "10",
        "explanation": "Substitute x=3: f(3) = 2(3²) - 3(3) + 1 = 2(9) - 9 + 1 = 18 - 9 + 1 = 10",
        "difficulty": "medium",
        "topic": "Functions"
    },
    {
        "question": "A triangle has sides of length 5, 12, and 13. What type of triangle is this?",
        "choices": ["Acute", "Right", "Obtuse", "Equilateral"],
        "answer": "Right",
        "explanation": "Check using Pythagorean theorem: 5² + 12² = 25 + 144 = 169 = 13². Since a² + b² = c², this is a right triangle! (5-12-13 is a Pythagorean triple)",
        "difficulty": "medium",
        "topic": "Geometry"
    },
    {
        "question": "What is the slope of the line passing through (2, 3) and (6, 11)?",
        "choices": ["1", "2", "3", "4"],
        "answer": "2",
        "explanation": "Slope = (y₂ - y₁) / (x₂ - x₁) = (11 - 3) / (6 - 2) = 8 / 4 = 2",
        "difficulty": "easy",
        "topic": "Linear Equations"
    },
    {
        "question": "If x² - 5x + 6 = 0, what are the values of x?",
        "choices": ["x = 2 and x = 3", "x = -2 and x = -3", "x = 1 and x = 6", "x = -1 and x = -6"],
        "answer": "x = 2 and x = 3",
        "explanation": "Factor: (x - 2)(x - 3) = 0. So x = 2 or x = 3. Check: 2² - 5(2) + 6 = 4 - 10 + 6 = 0 ✓",
        "difficulty": "medium",
        "topic": "Quadratics"
    },
    {
        "question": "A circle has a radius of 5. What is its area? (Use π ≈ 3.14)",
        "choices": ["15.7", "31.4", "78.5", "314"],
        "answer": "78.5",
        "explanation": "Area = πr² = 3.14 × 5² = 3.14 × 25 = 78.5",
        "difficulty": "easy",
        "topic": "Geometry"
    },
    {
        "question": "If 2^x = 32, what is the value of x?",
        "choices": ["3", "4", "5", "6"],
        "answer": "5",
        "explanation": "2^1=2, 2^2=4, 2^3=8, 2^4=16, 2^5=32. So x = 5. You can also write 32 = 2^5.",
        "difficulty": "medium",
        "topic": "Exponents"
    },
    {
        "question": "In a class of 30 students, 18 play basketball and 12 play soccer. 6 students play both. How many play at least one sport?",
        "choices": ["18", "20", "24", "30"],
        "answer": "24",
        "explanation": "Use the inclusion-exclusion principle: |B ∪ S| = |B| + |S| - |B ∩ S| = 18 + 12 - 6 = 24",
        "difficulty": "medium",
        "topic": "Counting & Probability"
    },
]

SAT_READING_QUESTIONS = [
    {
        "passage": "The college application process can feel overwhelming. With hundreds of schools, dozens of deadlines, and countless requirements, students often don't know where to start. However, breaking the process into manageable steps can make it much more achievable.",
        "question": "Based on the passage, what is the author's main point about the college application process?",
        "choices": [
            "It is impossible for most students to complete",
            "Breaking it into steps makes it more manageable",
            "There are too many schools to choose from",
            "Students should not apply to college"
        ],
        "answer": "Breaking it into steps makes it more manageable",
        "explanation": "The passage says 'breaking the process into manageable steps can make it much more achievable.' This directly states the main point.",
        "difficulty": "easy",
        "topic": "Main Idea"
    },
    {
        "passage": "Scholarships represent one of the most underutilized resources in college funding. Each year, billions of dollars go unclaimed simply because students do not apply. Many students assume they are not qualified, but scholarships exist for nearly every background, interest, and achievement level.",
        "question": "The word 'underutilized' in the passage most nearly means:",
        "choices": ["overused", "not used enough", "difficult to understand", "very expensive"],
        "answer": "not used enough",
        "explanation": "'Underutilized' comes from 'under' (not enough) + 'utilized' (used). The passage supports this — scholarships go unclaimed because students don't apply.",
        "difficulty": "easy",
        "topic": "Vocabulary in Context"
    },
    {
        "passage": "First-generation college students — those whose parents did not attend college — face unique challenges. They must navigate a system that their families have little experience with, often without a roadmap. Yet research consistently shows that first-gen students who receive mentorship and support graduate at similar rates to their peers.",
        "question": "The author's primary purpose in this passage is to:",
        "choices": [
            "Criticize colleges for not supporting first-gen students",
            "Acknowledge challenges while highlighting the power of support",
            "Argue that first-gen students should not attend college",
            "Compare first-gen students unfavorably to other students"
        ],
        "answer": "Acknowledge challenges while highlighting the power of support",
        "explanation": "The passage recognizes challenges ('face unique challenges') but ends on a positive, empowering note about mentorship and support.",
        "difficulty": "medium",
        "topic": "Author's Purpose"
    },
    {
        "passage": "Khan Academy's free SAT prep program has helped millions of students improve their scores. Studies show that students who use the program for 20 hours see an average score increase of 115 points. The program adapts to each student's weak areas, making practice more efficient.",
        "question": "According to the passage, Khan Academy's program is effective primarily because it:",
        "choices": [
            "Costs less than other test prep programs",
            "Is only available online",
            "Adapts to target each student's weak areas",
            "Requires 20 hours of practice"
        ],
        "answer": "Adapts to target each student's weak areas",
        "explanation": "The passage explicitly states the program 'adapts to each student's weak areas, making practice more efficient.'",
        "difficulty": "easy",
        "topic": "Evidence-Based Reading"
    },
    {
        "passage": "The FAFSA — Free Application for Federal Student Aid — opens on October 1st each year. Despite its importance, millions of eligible students never complete it. A study found that 1 in 5 students who qualified for federal aid simply did not apply, leaving an estimated $24 billion unclaimed annually.",
        "question": "What inference can best be made from this passage?",
        "choices": [
            "The FAFSA is too complicated for most students",
            "Federal student aid is running out of money",
            "Many students miss out on financial aid they could receive",
            "Only October applicants receive FAFSA funding"
        ],
        "answer": "Many students miss out on financial aid they could receive",
        "explanation": "The passage says students 'never complete' the FAFSA and '$24 billion' goes unclaimed. This supports the inference that many miss aid they qualify for.",
        "difficulty": "medium",
        "topic": "Inference"
    },
]

ACT_ENGLISH_QUESTIONS = [
    {
        "sentence": "The students _____ studying hard for the exam.",
        "question": "Which word correctly completes the sentence?",
        "choices": ["was", "were", "is", "be"],
        "answer": "were",
        "explanation": "'Students' is plural, so we need the plural verb 'were.' Rule: singular subjects use singular verbs (is/was), plural subjects use plural verbs (are/were).",
        "difficulty": "easy",
        "topic": "Subject-Verb Agreement"
    },
    {
        "sentence": "I want to go to college; _____ I need to save money.",
        "question": "Which conjunction correctly connects these two ideas?",
        "choices": ["however", "therefore", "although", "but"],
        "answer": "therefore",
        "explanation": "'Therefore' shows cause and effect — wanting to go to college CAUSES the need to save money. 'However' would show contrast, which doesn't make sense here.",
        "difficulty": "medium",
        "topic": "Conjunctions and Transitions"
    },
    {
        "sentence": "My sister, who is a doctor, _____ always giving me health advice.",
        "question": "Which verb form is correct?",
        "choices": ["is", "are", "were", "be"],
        "answer": "is",
        "explanation": "The subject is 'My sister' (singular), not 'who is a doctor' (a relative clause). Always identify the true subject. 'Sister' = singular → 'is'.",
        "difficulty": "medium",
        "topic": "Subject-Verb Agreement"
    },
    {
        "sentence": "The college application _____ due on January 1.",
        "question": "Which is correct?",
        "choices": ["is", "are", "were", "will being"],
        "answer": "is",
        "explanation": "'Application' is singular, so we use 'is.' 'Will being' is never correct in English.",
        "difficulty": "easy",
        "topic": "Verb Tense"
    },
    {
        "sentence": "Running to class every morning, _____ was exhausted by 9 AM.",
        "question": "Which word makes this a grammatically correct sentence?",
        "choices": ["the student", "which", "it", "they"],
        "answer": "the student",
        "explanation": "A participial phrase at the start ('Running to class...') must be followed immediately by the noun doing the running. 'The student' is the one running.",
        "difficulty": "hard",
        "topic": "Dangling Modifiers"
    },
]

ACT_SCIENCE_QUESTIONS = [
    {
        "question": "A scientist measures the temperature of a solution every 5 minutes. At 0 min: 20°C, 5 min: 35°C, 10 min: 50°C, 15 min: 65°C. If the pattern continues, what will the temperature be at 20 minutes?",
        "choices": ["70°C", "75°C", "80°C", "85°C"],
        "answer": "80°C",
        "explanation": "The temperature increases by 15°C every 5 minutes. At 15 min it's 65°C, so at 20 min it will be 65 + 15 = 80°C. Always look for the pattern in data questions!",
        "difficulty": "easy",
        "topic": "Data Analysis"
    },
    {
        "question": "An experiment tests whether plant growth is affected by light color. Group A receives red light, Group B receives blue light, Group C receives no light. What is the control group?",
        "choices": ["Group A", "Group B", "Group C", "All three groups"],
        "answer": "Group C",
        "explanation": "The control group is the one that doesn't receive the variable being tested (light color). Group C with no light is the control — it shows what happens without the treatment.",
        "difficulty": "easy",
        "topic": "Experimental Design"
    },
    {
        "question": "A graph shows that as altitude increases, air pressure decreases. This relationship is best described as:",
        "choices": ["Positive correlation", "Negative correlation", "No correlation", "Causation without correlation"],
        "answer": "Negative correlation",
        "explanation": "When one variable increases and the other decreases, that's a NEGATIVE correlation. Positive = both go up. Negative = one goes up, other goes down.",
        "difficulty": "easy",
        "topic": "Data Interpretation"
    },
    {
        "question": "A study finds that students who sleep 8+ hours score 15% higher on tests. A student concludes that sleeping more CAUSES higher test scores. What is the flaw in this reasoning?",
        "choices": [
            "The sample size might be too small",
            "Correlation does not prove causation",
            "The study should have used animals",
            "Test scores are not reliable"
        ],
        "answer": "Correlation does not prove causation",
        "explanation": "This is a classic ACT Science trap! A correlation (relationship between two things) does NOT mean one causes the other. Both sleep and scores could be caused by a third factor (like good study habits).",
        "difficulty": "medium",
        "topic": "Scientific Reasoning"
    },
    {
        "question": "In an experiment, a variable that is deliberately changed by the scientist is called the:",
        "choices": ["Dependent variable", "Independent variable", "Control variable", "Confounding variable"],
        "answer": "Independent variable",
        "explanation": "The INDEPENDENT variable is what the scientist changes on purpose. The DEPENDENT variable is what changes as a result. The control variable stays the same.",
        "difficulty": "easy",
        "topic": "Experimental Design"
    },
]

QUESTION_BANKS = {
    "SAT Math": SAT_MATH_QUESTIONS,
    "SAT Reading": SAT_READING_QUESTIONS,
    "ACT English": ACT_ENGLISH_QUESTIONS,
    "ACT Science": ACT_SCIENCE_QUESTIONS,
}


# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_test_scores (
        id {ai},
        user_email TEXT NOT NULL,
        test_type TEXT NOT NULL,
        score INTEGER NOT NULL,
        test_date TEXT,
        section_scores TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT {ts}
    )""")

    db_exec(conn, f"""CREATE TABLE IF NOT EXISTS cc_practice_results (
        id {ai},
        user_email TEXT NOT NULL,
        test_type TEXT NOT NULL,
        section TEXT NOT NULL,
        questions_total INTEGER DEFAULT 0,
        questions_correct INTEGER DEFAULT 0,
        time_taken INTEGER DEFAULT 0,
        difficulty TEXT DEFAULT 'medium',
        created_at TEXT {ts}
    )""")
    conn.commit()
    conn.close()


_ensure_tables()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get_user_email() -> str:
    user = st.session_state.get("user", {})
    return user.get("email", "guest@cc.app")


def _get_percentile(score: int, test_type: str) -> int:
    if test_type == "SAT":
        table = SAT_PERCENTILES
    elif test_type == "ACT":
        table = ACT_PERCENTILES
    else:
        return 0
    closest = min(table.keys(), key=lambda x: abs(x - score))
    return table[closest]


def _load_scores(user_email: str) -> list:
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM cc_test_scores WHERE user_email = ? ORDER BY test_date DESC", (user_email,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return []
    if USE_POSTGRES:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


def _save_score(user_email: str, test_type: str, score: int, test_date: str,
                section_scores: str, notes: str):
    conn = get_conn()
    db_exec(conn,
        "INSERT INTO cc_test_scores (user_email, test_type, score, test_date, section_scores, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (user_email, test_type, score, test_date, section_scores, notes)
    )
    conn.commit()
    conn.close()


def _save_practice_result(user_email: str, test_type: str, section: str,
                           total: int, correct: int):
    conn = get_conn()
    db_exec(conn,
        "INSERT INTO cc_practice_results (user_email, test_type, section, questions_total, questions_correct) VALUES (?, ?, ?, ?, ?)",
        (user_email, test_type, section, total, correct)
    )
    conn.commit()
    conn.close()


def _load_practice_history(user_email: str) -> list:
    conn = get_conn()
    cur = db_exec(conn,
        "SELECT * FROM cc_practice_results WHERE user_email = ? ORDER BY created_at DESC LIMIT 20",
        (user_email,)
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return []
    if USE_POSTGRES:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    return [dict(r) for r in rows]


# ── AI Study Coach ─────────────────────────────────────────────────────────────
def _ai_study_coach(test_type: str, weak_areas: list, scores_history: list, user_email: str = "") -> str:
    if not is_cc_ai_allowed(user_email):
        return "🚀 AI Study Coach is coming soon to College Confused! In the meantime, use the Quick Study Tips on the right and [Khan Academy](https://www.khanacademy.org/SAT) (free + official) for personalized SAT/ACT prep."
    api_key = os.environ.get("CC_ANTHROPIC_API_KEY") or get_setting("cc_anthropic_api_key", "")
    if not api_key:
        return "Please configure Anthropic API key in Settings."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        scores_summary = "\n".join([
            f"- {s.get('test_date', 'Unknown')}: {s.get('score', 'N/A')} ({s.get('test_type', 'N/A')})"
            for s in scores_history[-5:]
        ])
        weak_str = ", ".join(weak_areas) if weak_areas else "Not specified"

        prompt = f"""You are a friendly, encouraging SAT/ACT tutor helping a student improve their score.

Test Focus: {test_type}
Recent Scores:
{scores_summary if scores_summary else "No scores recorded yet"}
Weak Areas: {weak_str}

Please provide:
1. A personalized 2-week study plan (specific daily tasks, each 30-60 minutes)
2. The most important concepts to focus on for {test_type}
3. 3 specific tips to improve in their weak areas
4. Words of encouragement

Keep it simple, specific, and encouraging. This student is working hard. Write as if you're talking directly to them."""

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"Error: {e}"


# ── Page Header ────────────────────────────────────────────────────────────────
st.title("📚 SAT/ACT Test Prep")
st.markdown("**Free resources to help you score higher and unlock scholarship opportunities**")
st.info(
    "💡 **The best free SAT prep in the world is Khan Academy — we'll point you there AND give you extra tools.** "
    "A 1200 SAT or 25 ACT makes you competitive at most schools. Don't panic if you're not there yet — you can always take it again!"
)

user_email = _get_user_email()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 My Scores",
    "📖 Study Resources",
    "🧪 Practice Questions",
    "🤖 AI Study Coach",
    "ℹ️ What's on the Test?"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MY SCORES
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 My Test Score Tracker")

    col_form, col_stats = st.columns([1, 1])

    with col_form:
        st.markdown("**➕ Add a Test Score**")
        with st.form("add_score_form"):
            test_type_sel = st.selectbox("Test Type", ["SAT", "ACT", "PSAT"])
            if test_type_sel == "SAT":
                score_val = st.number_input("Total Score (400–1600)", min_value=400, max_value=1600, value=1000, step=10)
                st.markdown("**Section Scores (optional)**")
                sc_rw = st.number_input("Reading & Writing (200–800)", min_value=200, max_value=800, value=500, step=10)
                sc_math = st.number_input("Math (200–800)", min_value=200, max_value=800, value=500, step=10)
                section_str = f"RW:{sc_rw},Math:{sc_math}"
            elif test_type_sel == "ACT":
                score_val = st.number_input("Composite Score (1–36)", min_value=1, max_value=36, value=20)
                st.markdown("**Section Scores (optional)**")
                sc_eng = st.number_input("English (1–36)", min_value=1, max_value=36, value=20)
                sc_math = st.number_input("Math (1–36)", min_value=1, max_value=36, value=20)
                sc_read = st.number_input("Reading (1–36)", min_value=1, max_value=36, value=20)
                sc_sci = st.number_input("Science (1–36)", min_value=1, max_value=36, value=20)
                section_str = f"Eng:{sc_eng},Math:{sc_math},Read:{sc_read},Sci:{sc_sci}"
            else:  # PSAT
                score_val = st.number_input("Total Score (320–1520)", min_value=320, max_value=1520, value=1000, step=10)
                section_str = ""

            test_date_val = st.date_input("Test Date", value=date.today())
            notes_val = st.text_area("Notes (optional)", placeholder="How did it go? What to improve?", height=80)
            submitted = st.form_submit_button("✅ Save Score", use_container_width=True, type="primary")

            if submitted:
                _save_score(
                    user_email, test_type_sel, int(score_val),
                    str(test_date_val), section_str, notes_val
                )
                st.success(f"✅ {test_type_sel} score of {score_val} saved!")
                st.rerun()

    with col_stats:
        st.markdown("**🎯 Goal Score**")
        goal_test = st.selectbox("Goal test type", ["SAT", "ACT"], key="goal_test")
        if goal_test == "SAT":
            goal_score = st.slider("My SAT goal score", 400, 1600, 1200, step=10)
        else:
            goal_score = st.slider("My ACT goal score", 1, 36, 25)

        percentile = _get_percentile(goal_score, goal_test)
        st.metric(f"Estimated Percentile at {goal_score}", f"Top {100 - percentile}%")

        if goal_test == "SAT":
            if goal_score >= 1400:
                st.success("🔥 That's a highly competitive score — excellent target!")
            elif goal_score >= 1200:
                st.success("✅ A 1200+ makes you competitive at most schools!")
            elif goal_score >= 1000:
                st.info("📈 Good starting target — keep studying and you'll get there!")
            else:
                st.info("🌱 Every journey starts somewhere. Keep working at it!")
        else:
            if goal_score >= 30:
                st.success("🔥 A 30+ ACT is highly competitive — great goal!")
            elif goal_score >= 25:
                st.success("✅ A 25+ ACT makes you competitive at most schools!")
            elif goal_score >= 20:
                st.info("📈 Above average — a solid foundation to build on!")
            else:
                st.info("🌱 Every journey starts somewhere. Keep working at it!")

    # ── Score History ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📈 Score History")
    scores = _load_scores(user_email)

    if not scores:
        st.info("No scores recorded yet. Add your first score above!")
    else:
        # Summary metrics
        sat_scores = [s for s in scores if s.get("test_type") == "SAT"]
        act_scores = [s for s in scores if s.get("test_type") == "ACT"]

        m1, m2, m3, m4 = st.columns(4)
        if sat_scores:
            best_sat = max(sat_scores, key=lambda x: x.get("score", 0))
            m1.metric("Best SAT", best_sat["score"])
            m2.metric("SAT Attempts", len(sat_scores))
        if act_scores:
            best_act = max(act_scores, key=lambda x: x.get("score", 0))
            m3.metric("Best ACT", best_act["score"])
            m4.metric("ACT Attempts", len(act_scores))

        # Chart: score progression
        if len(scores) >= 2:
            import pandas as pd
            df = pd.DataFrame(scores)
            df["test_date"] = pd.to_datetime(df["test_date"])
            df = df.sort_values("test_date")

            sat_df = df[df["test_type"] == "SAT"]
            act_df = df[df["test_type"] == "ACT"]

            if not sat_df.empty:
                st.markdown("**SAT Score Progression**")
                st.line_chart(sat_df.set_index("test_date")[["score"]])
            if not act_df.empty:
                st.markdown("**ACT Score Progression**")
                st.line_chart(act_df.set_index("test_date")[["score"]])

        # Score table
        st.markdown("**All Scores**")
        for s in scores:
            pct = _get_percentile(s.get("score", 0), s.get("test_type", "SAT"))
            with st.expander(f"📝 {s.get('test_type')} — {s.get('score')} ({s.get('test_date', 'N/A')}) — {pct}th percentile"):
                if s.get("section_scores"):
                    st.write(f"**Sections:** {s.get('section_scores')}")
                if s.get("notes"):
                    st.write(f"**Notes:** {s.get('notes')}")

    st.markdown("---")
    st.markdown(
        "💬 **Remember:** A 1200 SAT or 25 ACT makes you competitive at most schools. "
        "Don't panic if you're not there yet — you can always take it again!"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — STUDY RESOURCES
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📖 Free Study Resources")
    st.markdown("Everything here is **100% free**. No credit card required.")

    col_sat, col_act = st.columns(2)

    with col_sat:
        st.markdown("### 🔵 Free SAT Resources")

        resources_sat = [
            ("⭐ Khan Academy Official SAT Prep", "https://www.khanacademy.org/SAT",
             "The #1 free SAT resource. Personalized practice, linked to College Board data. Start here!"),
            ("📝 College Board Official Practice Tests", "https://satsuite.collegeboard.org/sat/practice-preparation",
             "8 full-length free practice tests from the actual test makers. The real deal."),
            ("❓ College Board Question of the Day", "https://www.collegeboard.org/",
             "Quick daily practice to stay sharp between study sessions."),
            ("📚 PrepScholar SAT Study Guide", "https://blog.prepscholar.com/the-ultimate-sat-study-guide-for-sat-prep",
             "Comprehensive free guide covering every section. Great strategy tips."),
            ("🎓 Magoosh Free SAT Resources", "https://magoosh.com/hs/sat/",
             "Free blog, video lessons, and practice questions from Magoosh."),
        ]

        for name, url, desc in resources_sat:
            with st.container():
                st.markdown(f"**[{name}]({url})**")
                st.caption(desc)
                st.markdown("")

    with col_act:
        st.markdown("### 🔴 Free ACT Resources")

        resources_act = [
            ("⭐ ACT Academy (Official)", "https://academy.act.org/",
             "The official free ACT prep platform. Personalized practice from the test makers. Start here!"),
            ("📝 Official ACT Sample Questions", "http://www.act.org/content/act/en/products-and-services/the-act/test-preparation/free-act-test-prep.html",
             "Free sample questions and tips from the ACT organization itself."),
            ("📚 PrepScholar ACT Guide", "https://blog.prepscholar.com/topic/act-strategies",
             "Expert ACT strategies, section guides, and study plans. All free."),
        ]

        for name, url, desc in resources_act:
            with st.container():
                st.markdown(f"**[{name}]({url})**")
                st.caption(desc)
                st.markdown("")

    # ── Study Plans ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Free Study Plans")

    with st.expander("📗 30-Day SAT Study Plan — For students with 1 month to prepare"):
        st.markdown("""
**Week 1 — Diagnostic & Foundation**
- Day 1: Take a full practice SAT (timed) to establish your baseline score
- Day 2: Review your results — identify your 3 weakest areas
- Day 3: Khan Academy — complete all Reading & Writing lessons for your weak topics
- Day 4: Khan Academy — complete all Math lessons for your weak topics
- Day 5: Practice 20 Reading & Writing questions on Khan Academy
- Day 6: Practice 20 Math questions on Khan Academy
- Day 7: Rest! Your brain needs recovery time

**Week 2 — Skill Building**
- Day 8: Work through PrepScholar SAT Math guide
- Day 9: 30-minute timed Reading passage practice
- Day 10: Khan Academy full section practice — Math No Calculator
- Day 11: Khan Academy full section practice — Math Calculator
- Day 12: Vocabulary in context practice (10 words/day)
- Day 13: Full SAT Reading section (timed)
- Day 14: Review all mistakes from this week

**Week 3 — Practice Tests & Strategy**
- Day 15: Take Practice Test 2 (College Board)
- Day 16: Thorough review of Practice Test 2 mistakes
- Day 17: Focus session on your #1 weak area
- Day 18: Focus session on your #2 weak area
- Day 19: Timed practice — hardest question types for you
- Day 20: Strategy review — read PrepScholar tips
- Day 21: Rest!

**Week 4 — Final Prep**
- Day 22: Take Practice Test 3 (College Board)
- Day 23: Review mistakes — note any recurring patterns
- Day 24: Light review of key formulas (Math)
- Day 25: Light review of grammar rules (Writing)
- Day 26: Final Khan Academy practice — target your weak areas
- Day 27: Review your notes — light study only
- Day 28: REST. Get 9 hours of sleep. You've got this!
""")

    with st.expander("📘 60-Day ACT Study Plan — For students with 2 months to prepare"):
        st.markdown("""
**Month 1 — Build Your Foundation**
- Week 1: Take a full ACT practice test. Review results. Start ACT Academy.
- Week 2: Focus on English section — grammar, punctuation, style (45 min/day)
- Week 3: Focus on Math section — algebra, geometry, trig (45 min/day)
- Week 4: Take Practice Test 2. Review all mistakes.

**Month 2 — Target Weak Areas & Peak Performance**
- Week 5: Focus on Reading — 4 passages per session (timed, 35 min)
- Week 6: Focus on Science — data interpretation & experimental design (45 min/day)
- Week 7: Take Practice Test 3. Review & adjust strategy.
- Week 8 (Final):
  - Days 1-4: Light review of all sections
  - Day 5: Final practice test
  - Day 6: Review notes only
  - Day 7: **REST. Sleep 9 hours. Eat well. You're ready!**

**Daily habits that help:**
- 📱 Do 15-minute Khan Academy or ACT Academy sessions even on off days
- 📖 Read newspapers/books to build reading speed
- ✏️ Memorize ACT Math formulas (they're not provided!)
""")

    with st.expander("⚡ Weekend Warrior Plan — For busy students (6-8 hours/week)"):
        st.markdown("""
**This plan is for students with jobs, sports, or other commitments.**
You CAN still improve significantly with consistent weekend work!

**Every Saturday (3-4 hours):**
- Hour 1: Full timed practice section (English, Math, Reading, or Science)
- Hour 2: Review every single mistake — understand WHY you got it wrong
- Hour 3: Khan Academy or ACT Academy focused on your weak areas
- Hour 4 (optional): Second section practice

**Every Sunday (1-2 hours):**
- 30 minutes: Review flashcards / key formulas
- 30 minutes: 15-20 focused practice questions
- 30 minutes (optional): Watch a Khan Academy lesson on a tough topic

**Weekday micro-sessions (15 min/day):**
- Use Khan Academy's app on your phone
- 5 questions during lunch = 25 questions/week = significant improvement!

**Timeline expectation:**
- 4 weeks: +30–50 points SAT / +1–2 points ACT
- 8 weeks: +60–100 points SAT / +2–4 points ACT
- 12 weeks: +100–150 points SAT / +3–6 points ACT
""")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRACTICE QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🧪 Practice Questions")
    st.markdown("Answer real SAT/ACT-style questions with instant explanations!")

    # Session state for quiz
    if "quiz_question_idx" not in st.session_state:
        st.session_state["quiz_question_idx"] = 0
    if "quiz_answers" not in st.session_state:
        st.session_state["quiz_answers"] = {}
    if "quiz_submitted" not in st.session_state:
        st.session_state["quiz_submitted"] = False
    if "quiz_bank" not in st.session_state:
        st.session_state["quiz_bank"] = "SAT Math"

    col_select, col_info = st.columns([2, 1])
    with col_select:
        bank_choice = st.selectbox(
            "Choose a question set:",
            list(QUESTION_BANKS.keys()),
            key="bank_selector"
        )

    with col_info:
        bank_size = len(QUESTION_BANKS[bank_choice])
        st.metric("Questions Available", bank_size)

    # Reset quiz if bank changed
    if bank_choice != st.session_state.get("quiz_bank"):
        st.session_state["quiz_bank"] = bank_choice
        st.session_state["quiz_question_idx"] = 0
        st.session_state["quiz_answers"] = {}
        st.session_state["quiz_submitted"] = False

    questions = QUESTION_BANKS[bank_choice]
    q_idx = st.session_state["quiz_question_idx"]

    if not st.session_state["quiz_submitted"] and q_idx < len(questions):
        q = questions[q_idx]
        st.markdown(f"---")
        st.markdown(f"**Question {q_idx + 1} of {len(questions)}** — *{q.get('topic', '')}* ({q.get('difficulty', 'medium').title()})")

        # Show passage for reading questions
        if "passage" in q:
            st.markdown(f"""
<div style="background:#1a1f2e; border-left:4px solid #4a9eff; padding:16px; border-radius:8px; margin:12px 0; font-style:italic; color:#c0cfe0;">
{q['passage']}
</div>
""", unsafe_allow_html=True)
        elif "sentence" in q:
            st.markdown(f"""
<div style="background:#1a1f2e; border-left:4px solid #ffab76; padding:16px; border-radius:8px; margin:12px 0; font-style:italic; color:#c0cfe0;">
{q['sentence']}
</div>
""", unsafe_allow_html=True)

        st.markdown(f"**{q['question']}**")

        answer_key = f"quiz_q_{q_idx}"
        selected = st.radio(
            "Select your answer:",
            q["choices"],
            key=answer_key,
            index=None
        )

        col_sub, col_skip = st.columns([1, 1])
        with col_sub:
            if st.button("✅ Submit Answer", use_container_width=True, type="primary", disabled=(selected is None)):
                st.session_state["quiz_answers"][q_idx] = selected
                # Show feedback immediately
                if selected == q["answer"]:
                    st.success(f"✅ **Correct!** Well done!")
                else:
                    st.error(f"❌ **Incorrect.** The correct answer is: **{q['answer']}**")
                st.info(f"💡 **Explanation:** {q['explanation']}")

                # Move to next or finish
                if q_idx + 1 < len(questions):
                    if st.button("Next Question →", use_container_width=True):
                        st.session_state["quiz_question_idx"] += 1
                        st.rerun()
                else:
                    st.session_state["quiz_submitted"] = True
                    # Save results
                    total = len(questions)
                    correct = sum(
                        1 for i, q2 in enumerate(questions)
                        if st.session_state["quiz_answers"].get(i) == q2["answer"]
                    )
                    # Add current answer
                    if selected == q["answer"]:
                        correct += 1
                    _save_practice_result(user_email, bank_choice.split()[0], bank_choice, total, correct)
                    st.rerun()

        with col_skip:
            if st.button("Skip →", use_container_width=True):
                st.session_state["quiz_answers"][q_idx] = None
                if q_idx + 1 < len(questions):
                    st.session_state["quiz_question_idx"] += 1
                else:
                    st.session_state["quiz_submitted"] = True
                st.rerun()

        # Progress bar
        progress = (q_idx) / len(questions)
        st.progress(progress, text=f"Progress: {q_idx}/{len(questions)} questions")

    elif st.session_state["quiz_submitted"] or q_idx >= len(questions):
        # ── Quiz Results ───────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🏆 Quiz Complete!")

        total = len(questions)
        correct = sum(
            1 for i, q2 in enumerate(questions)
            if st.session_state["quiz_answers"].get(i) == q2["answer"]
        )
        pct = (correct / total * 100) if total > 0 else 0

        r1, r2, r3 = st.columns(3)
        r1.metric("Correct", f"{correct}/{total}")
        r2.metric("Score", f"{pct:.0f}%")
        r3.metric("Section", bank_choice)

        if pct >= 90:
            st.success("🔥 Outstanding! You're mastering this section!")
        elif pct >= 70:
            st.success("✅ Great work! A few more practice sessions and you'll ace it.")
        elif pct >= 50:
            st.warning("📈 Good effort! Review the explanations and try again.")
        else:
            st.info("💪 Keep practicing! Every attempt makes you stronger. Review the answers below.")

        # Review answers
        st.markdown("**📋 Answer Review**")
        for i, q2 in enumerate(questions):
            user_ans = st.session_state["quiz_answers"].get(i)
            is_correct = user_ans == q2["answer"]
            icon = "✅" if is_correct else "❌"
            with st.expander(f"{icon} Q{i+1}: {q2['question'][:60]}..."):
                if "passage" in q2:
                    st.markdown(f"*Passage:* {q2['passage'][:200]}...")
                st.write(f"**Your answer:** {user_ans or 'Skipped'}")
                st.write(f"**Correct answer:** {q2['answer']}")
                st.info(f"💡 {q2['explanation']}")

        if st.button("🔄 Try Again", use_container_width=True, type="primary"):
            st.session_state["quiz_question_idx"] = 0
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_submitted"] = False
            st.rerun()

    # ── Practice History ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 My Practice History")
    history = _load_practice_history(user_email)
    if not history:
        st.info("Complete your first quiz above to see your history!")
    else:
        import pandas as pd
        hist_df = pd.DataFrame(history)
        hist_df["accuracy"] = (hist_df["questions_correct"] / hist_df["questions_total"] * 100).round(1)
        st.dataframe(
            hist_df[["created_at", "section", "questions_correct", "questions_total", "accuracy"]].rename(columns={
                "created_at": "Date",
                "section": "Section",
                "questions_correct": "Correct",
                "questions_total": "Total",
                "accuracy": "Accuracy %"
            }),
            use_container_width=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI STUDY COACH
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🤖 AI Study Coach — Powered by Claude")
    st.markdown("Get a **personalized 2-week study plan** based on your scores and weak areas.")

    col_coach, col_tips = st.columns([1, 1])

    with col_coach:
        st.markdown("**Tell me about your goals:**")
        coach_test = st.selectbox("Which test are you preparing for?", ["SAT", "ACT", "Both SAT and ACT"])
        weak_areas_opts = {
            "SAT": ["Math – Algebra", "Math – Geometry", "Math – Data Analysis", "Math – Advanced Topics",
                    "Reading – Main Idea", "Reading – Vocabulary", "Reading – Inference",
                    "Writing – Grammar", "Writing – Punctuation", "Writing – Essay Structure"],
            "ACT": ["English – Grammar", "English – Punctuation", "English – Style",
                    "Math – Algebra", "Math – Geometry", "Math – Trig",
                    "Reading – Comprehension", "Reading – Speed",
                    "Science – Data Analysis", "Science – Experimental Design"],
            "Both SAT and ACT": ["Math", "Reading", "Grammar", "Writing", "Science"]
        }
        test_key = coach_test if coach_test in weak_areas_opts else "SAT"
        weak_areas_sel = st.multiselect(
            "Select your weak areas (choose all that apply):",
            weak_areas_opts[test_key],
            max_selections=5
        )

        scores_hist = _load_scores(user_email)
        if scores_hist:
            st.markdown(f"✅ Found **{len(scores_hist)} score(s)** in your history — the AI will use these for personalization.")
        else:
            st.info("💡 No scores saved yet. Add scores in the 'My Scores' tab for better personalization.")

        if st.button("🤖 Get My Personalized Study Plan", use_container_width=True, type="primary"):
            with st.spinner("Creating your personalized 2-week study plan..."):
                plan = _ai_study_coach(coach_test, weak_areas_sel, scores_hist, _get_user_email())

            st.markdown("---")
            st.markdown("### 📋 Your Personalized Study Plan")
            st.markdown(plan)

            api_key = os.environ.get("CC_ANTHROPIC_API_KEY") or get_setting("cc_anthropic_api_key", "")
            if not api_key:
                st.warning("⚙️ To unlock AI features, add your Anthropic API key in the Settings page.")

    with col_tips:
        st.markdown("**💡 Quick Study Tips**")
        st.markdown("""
**For SAT:**
- 📌 Khan Academy is free AND official — 20 hours = +115 points average
- 🎯 Focus on your weak areas, not what you're already good at
- ⏰ Always practice with a timer — the SAT is a speed test too
- 📖 Read newspaper editorials to build reading speed
- 🔢 Memorize these SAT formulas: Pythagorean theorem, linear equations, percent change

**For ACT:**
- 📌 ACT Academy is the official free platform — start there
- ⚡ ACT Science is NOT about science knowledge — it's about reading data
- 🏃 ACT is faster-paced — practice skipping and coming back
- 📝 ACT English grammar rules are predictable — memorize them
- 🎯 Wrong answer = no penalty, so NEVER leave a blank

**General Advice:**
- 😴 Sleep 8+ hours before the test — proven to boost scores
- 🥗 Eat a real breakfast on test day
- 📅 Take the test multiple times — most students improve on their 2nd attempt
- 💬 Talk to your school counselor about fee waivers (they're free if you qualify!)
""")

        st.markdown("**📞 Need More Help?**")
        st.markdown("""
- Your school's college counselor can help you register for free
- Many public libraries offer free prep books — ask your librarian!
- [Khan Academy](https://www.khanacademy.org/SAT) — free, forever
- [ACT Academy](https://academy.act.org/) — free, forever
""")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WHAT'S ON THE TEST?
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("ℹ️ What's on the SAT and ACT?")
    st.markdown("A simple guide to understanding both tests.")

    col_sat_info, col_act_info = st.columns(2)

    with col_sat_info:
        st.markdown("### 🔵 SAT Structure")
        import pandas as pd
        sat_table = pd.DataFrame([
            ["Reading & Writing", "54", "64 min", "Reading, vocabulary, grammar"],
            ["Math (no calculator)", "22", "35 min", "Algebra, basic concepts"],
            ["Math (with calculator)", "38", "55 min", "Complex math, data analysis"],
            ["**TOTAL**", "**1600 score**", "**~3 hours**", "**College readiness**"],
        ], columns=["Section", "Questions", "Time", "What It Tests"])
        st.dataframe(sat_table, use_container_width=True, hide_index=True)

        st.markdown("""
**SAT Scoring:**
- Total score: 400–1600
- Two section scores: Reading & Writing (200–800) + Math (200–800)
- No penalty for wrong answers — always guess!
- Digital test on a computer (as of 2024)

**SAT Key Facts:**
- Offered 7 times/year (Aug, Oct, Nov, Dec, Mar, May, Jun)
- Cost: ~$60 (free waivers available — ask your counselor!)
- Results available in ~2 weeks
- Linked to Khan Academy for free personalized prep
""")

    with col_act_info:
        st.markdown("### 🔴 ACT Structure")
        act_table = pd.DataFrame([
            ["English", "75", "45 min", "Grammar, punctuation, style"],
            ["Math", "60", "60 min", "Algebra through trigonometry"],
            ["Reading", "40", "35 min", "Reading comprehension"],
            ["Science", "40", "35 min", "Data analysis, experiments"],
            ["Writing (optional)", "1 essay", "40 min", "Argumentative writing"],
            ["**TOTAL**", "**36 score**", "**~3 hrs**", "**College readiness**"],
        ], columns=["Section", "Questions", "Time", "What It Tests"])
        st.dataframe(act_table, use_container_width=True, hide_index=True)

        st.markdown("""
**ACT Scoring:**
- Total (composite) score: 1–36
- Average of four section scores
- No penalty for wrong answers — always guess!
- Paper test (traditional format)

**ACT Key Facts:**
- Offered 7 times/year
- Cost: ~$67 ($93 with Writing) — fee waivers available!
- Results available in ~3 weeks
- ACT Science is reading data, NOT science knowledge
""")

    # ── FAQ Section ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("❓ Frequently Asked Questions")

    faqs = [
        (
            "Which should I take — SAT or ACT?",
            """**Take both!** Most students do better on one than the other, but you won't know which until you try.
            
Here's a simple guide:
- **Better at math?** → Both tests are math-heavy, but the ACT math is more straightforward
- **Better at reading?** → SAT rewards careful reading; ACT is faster-paced
- **Good at science?** → ACT has a Science section (it's really data reading)
- **Better test-taker under pressure?** → ACT moves faster; SAT gives more time per question

**Action:** Take a full free practice test for each and compare your results!"""
        ),
        (
            "How many times can I take it?",
            """**As many times as you want!** Most colleges look at your BEST score (called "superscoring"):
            
- **SAT Superscore:** Colleges take the best Math AND best Reading/Writing from different test dates
- **ACT Superscore:** Colleges take the best score from each section across all attempts

**Strategy:** Take it once in spring of 11th grade, then again in fall of 12th grade if you want to improve.
Most students improve by 100+ points on their second SAT attempt."""
        ),
        (
            "Can I get a fee waiver?",
            """**Yes! And you should ask about it!** Fee waivers are FREE and cover the full test cost.

**Who qualifies:**
- Students receiving free/reduced lunch
- Students from low-income families (income thresholds vary)
- Foster youth and homeless youth automatically qualify
- Many other situations — just ask!

**How to get one:**
1. Ask your school counselor — they have the waiver forms
2. Your counselor can provide up to 4 SAT fee waivers and 2 ACT waivers per student
3. The waiver also covers score sends to colleges (usually $13 each!)

**Important:** Don't skip the test because of cost. ASK FIRST."""
        ),
        (
            "When should I start studying?",
            """**The earlier, the better — but it's never too late!**

**Ideal timeline:**
- **9th-10th grade:** Take the PSAT (great practice, no pressure)
- **Early 11th grade:** Start Khan Academy/ACT Academy, take a practice test
- **Spring 11th grade:** Take your first real SAT or ACT
- **Fall 12th grade:** Retake if you want to improve (many do!)

**Don't stress if you're already in 12th grade** — you still have time! Many students improve significantly in just 4-8 weeks of focused study."""
        ),
        (
            "Is a prep course worth it?",
            """**Free resources are just as effective as paid courses!**

Studies by College Board and ACT found that:
- Students using Khan Academy for 20 hours improved SAT scores by **115 points** on average
- This is better than most paid prep courses that cost $500–$2,000

**Free options that work:**
- Khan Academy Official SAT Prep (linked to your PSAT scores!)
- ACT Academy (official, personalized, free)
- Official practice tests from College Board/ACT website
- YouTube channels like "PrepScholar" for free video lessons

**Bottom line:** Spend 1–2 hours per day consistently for 2–3 months. That's worth more than any prep course."""
        ),
    ]

    for question, answer in faqs:
        with st.expander(f"❓ {question}"):
            st.markdown(answer)

    # ── Score comparison chart ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Score Comparison: What Different Scores Mean")
    st.markdown("Use this to understand what your score means for college admissions:")

    import pandas as pd
    comparison_data = pd.DataFrame([
        ["400–800", "1–12", "1st–5th", "Keep studying! Every student improves with practice."],
        ["800–1000", "12–18", "5th–16th", "Below average. 2–3 months of focused study can make a big difference."],
        ["1000–1100", "18–22", "16th–40th", "Average range. Competitive at many community colleges and state schools."],
        ["1100–1200", "22–25", "40th–61st", "Good score! Competitive at most 4-year universities."],
        ["1200–1350", "25–28", "61st–80th", "Strong score! Opens doors to most selective schools."],
        ["1350–1500", "28–32", "80th–95th", "Excellent! Very competitive at selective and highly selective schools."],
        ["1500–1600", "32–36", "95th–99th", "Outstanding! Competitive at elite schools (Harvard, MIT, etc.)"],
    ], columns=["SAT Score", "ACT Equivalent", "Percentile", "What It Means"])

    st.dataframe(comparison_data, use_container_width=True, hide_index=True)

    st.markdown("""
> 💬 **Remember:** Your test score is ONE part of your application. 
> Grades, essays, activities, and recommendations all matter too. 
> A 1200 SAT student with a great essay and strong GPA can beat a 1450 SAT student with nothing else to offer!
""")
