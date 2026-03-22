import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sys
import os
import json
import io

st.set_page_config(
    page_title="Health & Wellness AI Hub | Peach State Savings",
    page_icon="🍑",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────
MOOD_OPTIONS    = ["😄 Great", "🙂 Good", "😐 Neutral", "😔 Low", "😢 Bad"]
ENERGY_OPTIONS  = ["⚡ Very High", "🔋 High", "😐 Medium", "😴 Low", "💤 Exhausted"]
SLEEP_OPTIONS   = list(range(0, 13))
WORKOUT_TYPES   = ["Running", "Lifting", "HIIT", "Yoga", "Cycling", "Swimming", "Walking", "Basketball", "Other"]
FREQUENCY_OPTS  = ["Daily", "Every 4 hours", "Every 6 hours", "Every 8 hours", "Every 12 hours", "As needed", "Weekly"]
VACCINE_LIST    = ["COVID-19", "Flu", "Tdap", "MMR", "Hepatitis B", "HPV", "Shingles", "Pneumococcal", "Other"]


# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    auto = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS hw_mood_logs (
            id          {auto},
            log_date    DATE NOT NULL,
            mood        TEXT,
            energy      TEXT,
            sleep_hours REAL,
            notes       TEXT,
            medications_taken TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS hw_workouts (
            id          {auto},
            workout_date DATE NOT NULL,
            type        TEXT,
            duration_min INTEGER,
            exercises   TEXT,
            notes       TEXT,
            calories_burned INTEGER,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS hw_medications (
            id          {auto},
            name        TEXT NOT NULL,
            dosage      TEXT,
            frequency   TEXT,
            start_date  DATE,
            refill_date DATE,
            notes       TEXT,
            active      INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS hw_health_goals (
            id          {auto},
            goal        TEXT NOT NULL,
            target_date DATE,
            progress    TEXT,
            completed   INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS hw_doctor_visits (
            id          {auto},
            visit_date  DATE NOT NULL,
            doctor_type TEXT,
            doctor_name TEXT,
            notes       TEXT,
            next_visit  DATE,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS hw_vaccines (
            id          {auto},
            vaccine     TEXT NOT NULL,
            date_given  DATE,
            next_due    DATE,
            notes       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


_ensure_tables()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _load_mood_logs(days: int = 30):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    since = (date.today() - timedelta(days=days)).isoformat()
    cur = db_exec(conn, f"SELECT * FROM hw_mood_logs WHERE log_date >= {ph} ORDER BY log_date DESC", (since,))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _load_workouts(days: int = 90):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    since = (date.today() - timedelta(days=days)).isoformat()
    cur = db_exec(conn, f"SELECT * FROM hw_workouts WHERE workout_date >= {ph} ORDER BY workout_date DESC", (since,))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _load_medications():
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM hw_medications WHERE active = 1 ORDER BY name")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _load_doctor_visits():
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM hw_doctor_visits ORDER BY visit_date DESC")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _load_vaccines():
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM hw_vaccines ORDER BY date_given DESC")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _load_goals():
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM hw_health_goals ORDER BY completed, target_date")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _log_mood(log_date, mood, energy, sleep_hours, notes, meds_taken):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, 
        f"INSERT INTO hw_mood_logs (log_date, mood, energy, sleep_hours, notes, medications_taken) VALUES ({ph},{ph},{ph},{ph},{ph},{ph})",
        (log_date, mood, energy, sleep_hours, notes, meds_taken)
    )
    conn.commit()
    conn.close()


def _log_workout(workout_date, wtype, duration, exercises, notes, calories):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, 
        f"INSERT INTO hw_workouts (workout_date, type, duration_min, exercises, notes, calories_burned) VALUES ({ph},{ph},{ph},{ph},{ph},{ph})",
        (workout_date, wtype, duration, exercises, notes, calories)
    )
    conn.commit()
    conn.close()


def _add_medication(name, dosage, frequency, start_date, refill_date, notes):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, 
        f"INSERT INTO hw_medications (name, dosage, frequency, start_date, refill_date, notes) VALUES ({ph},{ph},{ph},{ph},{ph},{ph})",
        (name, dosage, frequency, start_date, refill_date, notes)
    )
    conn.commit()
    conn.close()


def _deactivate_medication(med_id):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"UPDATE hw_medications SET active = 0 WHERE id = {ph}", (med_id,))
    conn.commit()
    conn.close()


def _add_doctor_visit(visit_date, doctor_type, doctor_name, notes, next_visit):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, 
        f"INSERT INTO hw_doctor_visits (visit_date, doctor_type, doctor_name, notes, next_visit) VALUES ({ph},{ph},{ph},{ph},{ph})",
        (visit_date, doctor_type, doctor_name, notes, next_visit)
    )
    conn.commit()
    conn.close()


def _add_vaccine(vaccine, date_given, next_due, notes):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, 
        f"INSERT INTO hw_vaccines (vaccine, date_given, next_due, notes) VALUES ({ph},{ph},{ph},{ph})",
        (vaccine, date_given, next_due, notes)
    )
    conn.commit()
    conn.close()


def _add_goal(goal, target_date, progress):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, 
        f"INSERT INTO hw_health_goals (goal, target_date, progress) VALUES ({ph},{ph},{ph})",
        (goal, target_date, progress)
    )
    conn.commit()
    conn.close()


def _complete_goal(goal_id):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"UPDATE hw_health_goals SET completed = 1 WHERE id = {ph}", (goal_id,))
    conn.commit()
    conn.close()


# ── AI Helper ──────────────────────────────────────────────────────────────────
def _ai_health_analysis(prompt_text: str) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ No Anthropic API key configured. Add it in Settings."
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt_text}]
    )
    return msg.content[0].text


# ── Page Header ────────────────────────────────────────────────────────────────
st.title("🏥 Health & Wellness AI Hub")
st.markdown("*Your personal health command center — mood, workouts, medications, and AI insights.*")

# ── KPI Bar ────────────────────────────────────────────────────────────────────
mood_df     = _load_mood_logs(7)
workout_df  = _load_workouts(7)
med_df      = _load_medications()
vaccines_df = _load_vaccines()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Check-ins (7d)",    len(mood_df))
k2.metric("Workouts (7d)",     len(workout_df))
k3.metric("Active Meds",       len(med_df))
k4.metric("Vaccines Logged",   len(vaccines_df))

# Refill alerts
if not med_df.empty:
    refill_soon = med_df[med_df["refill_date"].notna()].copy()
    if not refill_soon.empty:
        refill_soon["refill_date"] = pd.to_datetime(refill_soon["refill_date"])
        upcoming = refill_soon[refill_soon["refill_date"] <= pd.Timestamp(date.today() + timedelta(days=7))]
        k5.metric("Refills Due (7d)", len(upcoming), delta=None)
    else:
        k5.metric("Refills Due (7d)", 0)
else:
    k5.metric("Refills Due (7d)", 0)

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Daily Check-In",
    "💪 Workout Tracker",
    "💊 Medications",
    "🏥 Doctor & Vaccines",
    "🤖 AI Health Insights",
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Daily Check-In
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📋 Daily Health Check-In")

    col_form, col_history = st.columns([1, 1])

    with col_form:
        st.markdown("**Log Today's Check-In**")
        with st.form("checkin_form"):
            ci_date     = st.date_input("Date", value=date.today())
            ci_mood     = st.selectbox("Mood", MOOD_OPTIONS)
            ci_energy   = st.selectbox("Energy Level", ENERGY_OPTIONS)
            ci_sleep    = st.slider("Hours of Sleep", 0, 12, 7)
            ci_notes    = st.text_area("Journal Notes", placeholder="How are you feeling today?", height=100)

            # Active medications checkbox list
            meds_loaded = _load_medications()
            med_names = meds_loaded["name"].tolist() if not meds_loaded.empty else []
            ci_meds_taken = st.multiselect("Medications Taken Today", med_names)

            submitted = st.form_submit_button("✅ Log Check-In", use_container_width=True)
            if submitted:
                _log_mood(ci_date, ci_mood, ci_energy, float(ci_sleep),
                          ci_notes, ", ".join(ci_meds_taken))
                st.success(f"Check-in logged for {ci_date}!")
                st.rerun()

    with col_history:
        st.markdown("**Recent Check-Ins (Last 7 Days)**")
        recent = _load_mood_logs(7)
        if recent.empty:
            st.info("No check-ins yet. Log your first one!")
        else:
            for _, row in recent.iterrows():
                with st.expander(f"{row['log_date']} — {row['mood']}"):
                    st.write(f"**Energy:** {row['energy']}")
                    st.write(f"**Sleep:** {row['sleep_hours']} hrs")
                    if row['notes']:
                        st.write(f"**Notes:** {row['notes']}")
                    if row['medications_taken']:
                        st.write(f"**Meds Taken:** {row['medications_taken']}")

    st.markdown("---")
    st.subheader("📈 Mood & Sleep Trends (30 Days)")
    trend_df = _load_mood_logs(30)
    if not trend_df.empty:
        # Numeric mood mapping
        mood_map = {"😄 Great": 5, "🙂 Good": 4, "😐 Neutral": 3, "😔 Low": 2, "😢 Bad": 1}
        trend_df["mood_score"] = trend_df["mood"].map(mood_map).fillna(3)
        trend_df["log_date"]   = pd.to_datetime(trend_df["log_date"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_df["log_date"], y=trend_df["mood_score"],
            name="Mood Score", mode="lines+markers",
            line=dict(color="#FF6B6B", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=trend_df["log_date"], y=trend_df["sleep_hours"],
            name="Sleep Hours", mode="lines+markers",
            line=dict(color="#4ECDC4", width=2), yaxis="y2"
        ))
        fig.update_layout(
            title="Mood Score vs Sleep Hours",
            yaxis=dict(title="Mood (1–5)", range=[0, 6]),
            yaxis2=dict(title="Sleep Hours", overlaying="y", side="right", range=[0, 13]),
            legend=dict(x=0, y=1),
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)

        # Apple Health CSV import
        st.markdown("**📱 Import from Apple Health Export**")
        uploaded = st.file_uploader("Upload Apple Health CSV export", type=["csv"])
        if uploaded:
            try:
                df_apple = pd.read_csv(uploaded)
                st.dataframe(df_apple.head(20))
                st.info("Preview shown above. Map columns manually to log entries.")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
    else:
        st.info("Log at least one check-in to see trends.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Workout Tracker
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("💪 Workout Tracker")

    col_wlog, col_wplan = st.columns([1, 1])

    with col_wlog:
        st.markdown("**Log a Workout**")
        with st.form("workout_form"):
            w_date      = st.date_input("Date", value=date.today(), key="w_date")
            w_type      = st.selectbox("Workout Type", WORKOUT_TYPES)
            w_duration  = st.number_input("Duration (minutes)", min_value=5, max_value=300, value=45)
            w_exercises = st.text_area("Exercises / Notes", placeholder="e.g. 3x10 bench press, 20 min run...")
            w_calories  = st.number_input("Calories Burned (est.)", min_value=0, max_value=3000, value=200)
            w_notes     = st.text_input("Additional Notes")
            w_submit    = st.form_submit_button("💪 Log Workout", use_container_width=True)
            if w_submit:
                _log_workout(w_date, w_type, int(w_duration), w_exercises, w_notes, int(w_calories))
                st.success("Workout logged!")
                st.rerun()

    with col_wplan:
        st.markdown("**🤖 AI Workout Plan Generator**")
        with st.form("workout_ai_form"):
            wp_goal      = st.selectbox("Goal", ["Lose Weight", "Build Muscle", "Endurance", "General Fitness", "Flexibility"])
            wp_level     = st.selectbox("Fitness Level", ["Beginner", "Intermediate", "Advanced"])
            wp_days      = st.slider("Days/Week Available", 1, 7, 4)
            wp_equipment = st.multiselect("Available Equipment", ["None/Bodyweight", "Dumbbells", "Barbell", "Cables", "Full Gym", "Resistance Bands"])
            wp_body      = st.selectbox("Body Type / Focus", ["Ectomorph (lean)", "Mesomorph (athletic)", "Endomorph (stocky)", "General"])
            wp_gen       = st.form_submit_button("🤖 Generate Plan", use_container_width=True)

        if wp_gen:
            eq_str = ", ".join(wp_equipment) if wp_equipment else "bodyweight only"
            prompt = f"""
Create a detailed {wp_days}-day/week workout plan for someone who wants to {wp_goal.lower()}.
Fitness level: {wp_level}
Body type: {wp_body}
Equipment: {eq_str}

Provide:
1. Weekly schedule with specific days
2. 3-5 exercises per session with sets/reps
3. Warm-up and cool-down suggestions
4. Progressive overload tips
5. Estimated calorie burn per session

Keep it practical and motivating.
"""
            with st.spinner("Generating your personalized plan..."):
                result = _ai_health_analysis(prompt)
            st.markdown(result)

    st.markdown("---")
    st.subheader("📊 Workout History")
    w_df = _load_workouts(90)
    if not w_df.empty:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            type_counts = w_df["type"].value_counts().reset_index()
            type_counts.columns = ["type", "count"]
            fig_type = px.pie(type_counts, values="count", names="type",
                              title="Workouts by Type (90 Days)")
            st.plotly_chart(fig_type, use_container_width=True)

        with col_c2:
            w_df["workout_date"] = pd.to_datetime(w_df["workout_date"])
            weekly = w_df.resample("W", on="workout_date")["duration_min"].sum().reset_index()
            fig_week = px.bar(weekly, x="workout_date", y="duration_min",
                              title="Weekly Workout Minutes", labels={"duration_min": "Minutes"})
            st.plotly_chart(fig_week, use_container_width=True)

        st.dataframe(
            w_df[["workout_date", "type", "duration_min", "calories_burned", "exercises"]].head(20),
            use_container_width=True
        )
    else:
        st.info("No workouts logged yet. Start tracking your fitness!")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — Medications
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("💊 Medication Tracker")

    col_madd, col_mlist = st.columns([1, 1])

    with col_madd:
        st.markdown("**Add Medication**")
        with st.form("med_form"):
            m_name      = st.text_input("Medication Name *", placeholder="e.g. Adderall 20mg")
            m_dosage    = st.text_input("Dosage", placeholder="e.g. 20mg")
            m_freq      = st.selectbox("Frequency", FREQUENCY_OPTS)
            m_start     = st.date_input("Start Date", value=date.today(), key="m_start")
            m_refill    = st.date_input("Next Refill Date", value=date.today() + timedelta(days=30), key="m_refill")
            m_notes     = st.text_area("Notes", placeholder="Side effects, instructions, etc.")
            m_submit    = st.form_submit_button("💊 Add Medication", use_container_width=True)
            if m_submit:
                if not m_name:
                    st.error("Medication name is required.")
                else:
                    _add_medication(m_name, m_dosage, m_freq, m_start, m_refill, m_notes)
                    st.success(f"{m_name} added!")
                    st.rerun()

    with col_mlist:
        st.markdown("**Active Medications**")
        meds = _load_medications()
        if meds.empty:
            st.info("No medications tracked. Add one on the left.")
        else:
            for _, row in meds.iterrows():
                refill_str = ""
                if row["refill_date"]:
                    rd = pd.to_datetime(row["refill_date"]).date()
                    days_left = (rd - date.today()).days
                    if days_left <= 7:
                        refill_str = f" ⚠️ Refill in {days_left}d"
                    else:
                        refill_str = f" (Refill: {rd})"

                with st.expander(f"💊 {row['name']} — {row['dosage']} {row['frequency']}{refill_str}"):
                    st.write(f"**Start Date:** {row['start_date']}")
                    if row["notes"]:
                        st.write(f"**Notes:** {row['notes']}")
                    if st.button(f"Discontinue {row['name']}", key=f"disc_{row['id']}"):
                        _deactivate_medication(row["id"])
                        st.rerun()

    st.markdown("---")
    st.subheader("📅 Refill Calendar")
    all_meds_df = meds
    if not all_meds_df.empty:
        refill_df = all_meds_df[all_meds_df["refill_date"].notna()].copy()
        if not refill_df.empty:
            refill_df["refill_date"] = pd.to_datetime(refill_df["refill_date"])
            refill_df["days_until"]  = (refill_df["refill_date"] - pd.Timestamp(date.today())).dt.days
            refill_df = refill_df.sort_values("days_until")
            st.dataframe(
                refill_df[["name", "dosage", "frequency", "refill_date", "days_until"]].rename(
                    columns={"days_until": "Days Until Refill"}
                ),
                use_container_width=True
            )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — Doctor Visits & Vaccines
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("🏥 Doctor Visits & Vaccine Tracker")

    col_dv, col_vacc = st.columns([1, 1])

    with col_dv:
        st.markdown("**Log Doctor Visit**")
        with st.form("doctor_form"):
            dv_date   = st.date_input("Visit Date", value=date.today(), key="dv_date")
            dv_type   = st.selectbox("Doctor Type", ["Primary Care", "Dentist", "Eye Doctor", "Dermatologist",
                                                      "Psychiatrist", "Therapist", "Cardiologist", "Other"])
            dv_name   = st.text_input("Doctor Name")
            dv_notes  = st.text_area("Notes / Diagnosis", height=80)
            dv_next   = st.date_input("Next Scheduled Visit", value=date.today() + timedelta(days=180), key="dv_next")
            dv_sub    = st.form_submit_button("🏥 Log Visit", use_container_width=True)
            if dv_sub:
                _add_doctor_visit(dv_date, dv_type, dv_name, dv_notes, dv_next)
                st.success("Visit logged!")
                st.rerun()

        st.markdown("**Past Visits**")
        dv_df = _load_doctor_visits()
        if dv_df.empty:
            st.info("No visits logged yet.")
        else:
            st.dataframe(
                dv_df[["visit_date", "doctor_type", "doctor_name", "notes", "next_visit"]].head(10),
                use_container_width=True
            )

    with col_vacc:
        st.markdown("**Vaccine Tracker**")
        with st.form("vaccine_form"):
            v_name  = st.selectbox("Vaccine", VACCINE_LIST)
            v_given = st.date_input("Date Given", value=date.today(), key="v_given")
            v_due   = st.date_input("Next Dose Due", value=date.today() + timedelta(days=365), key="v_due")
            v_notes = st.text_input("Notes")
            v_sub   = st.form_submit_button("💉 Log Vaccine", use_container_width=True)
            if v_sub:
                _add_vaccine(v_name, v_given, v_due, v_notes)
                st.success(f"{v_name} logged!")
                st.rerun()

        st.markdown("**Vaccine History**")
        vacc_df = _load_vaccines()
        if vacc_df.empty:
            st.info("No vaccines logged yet.")
        else:
            vacc_df["next_due"]   = pd.to_datetime(vacc_df["next_due"])
            vacc_df["days_until"] = (vacc_df["next_due"] - pd.Timestamp(date.today())).dt.days
            st.dataframe(
                vacc_df[["vaccine", "date_given", "next_due", "days_until", "notes"]].rename(
                    columns={"days_until": "Days Until Next"}
                ),
                use_container_width=True
            )

    # Upcoming reminders
    st.markdown("---")
    st.subheader("🔔 Upcoming Health Reminders")
    reminders = []
    dv_df2 = _load_doctor_visits()
    if not dv_df2.empty:
        upcoming_visits = dv_df2[dv_df2["next_visit"].notna()].copy()
        upcoming_visits["next_visit"] = pd.to_datetime(upcoming_visits["next_visit"])
        upcoming_visits = upcoming_visits[upcoming_visits["next_visit"] >= pd.Timestamp(date.today())]
        for _, r in upcoming_visits.iterrows():
            days = (r["next_visit"].date() - date.today()).days
            reminders.append(f"🏥 **{r['doctor_type']}** ({r['doctor_name']}) — in {days} days ({r['next_visit'].date()})")

    vacc_df2 = _load_vaccines()
    if not vacc_df2.empty:
        upcoming_vacc = vacc_df2[vacc_df2["next_due"].notna()].copy()
        upcoming_vacc["next_due"] = pd.to_datetime(upcoming_vacc["next_due"])
        upcoming_vacc = upcoming_vacc[upcoming_vacc["next_due"] >= pd.Timestamp(date.today())]
        for _, r in upcoming_vacc.iterrows():
            days = (r["next_due"].date() - date.today()).days
            reminders.append(f"💉 **{r['vaccine']} vaccine** — due in {days} days ({r['next_due'].date()})")

    if reminders:
        for rem in sorted(reminders):
            st.markdown(f"- {rem}")
    else:
        st.info("No upcoming health reminders.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — AI Health Insights
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("🤖 AI Health Insights — Powered by Claude")

    insight_type = st.selectbox("Choose Insight Type", [
        "Mood Pattern Analysis (30 days)",
        "Workout Progress & Recommendations",
        "Medication Management Review",
        "Preventative Health Checklist",
        "Mental Health & Wellness Tips",
        "Custom Health Question",
    ])

    custom_q = ""
    if insight_type == "Custom Health Question":
        custom_q = st.text_area("Your question:", placeholder="Ask anything about your health data...", height=100)

    # File upload for psych eval / family history
    with st.expander("📎 Upload Health Documents (Optional — for richer AI analysis)"):
        doc_file = st.file_uploader("Upload PDF / Text (psych eval, family history, lab results)", type=["txt", "pdf"])
        doc_text = ""
        if doc_file:
            if doc_file.type == "text/plain":
                doc_text = doc_file.read().decode("utf-8", errors="ignore")[:3000]
                st.success(f"Loaded {len(doc_text)} chars from {doc_file.name}")
            else:
                st.info("PDF uploaded. Text extraction requires pdfplumber — showing file name only.")
                doc_text = f"[User uploaded PDF: {doc_file.name}]"

    # Health goals
    with st.expander("🎯 Health Goals"):
        col_g1, col_g2 = st.columns([1, 1])
        with col_g1:
            with st.form("goal_form"):
                g_goal   = st.text_input("New Goal", placeholder="e.g. Run 5K, lose 10 lbs, meditate daily")
                g_target = st.date_input("Target Date", value=date.today() + timedelta(days=90), key="g_target")
                g_prog   = st.text_input("Current Progress", placeholder="e.g. Can run 2K, down 3 lbs")
                g_sub    = st.form_submit_button("Add Goal")
                if g_sub and g_goal:
                    _add_goal(g_goal, g_target, g_prog)
                    st.success("Goal added!")
                    st.rerun()

        with col_g2:
            goals_df = _load_goals()
            if not goals_df.empty:
                active_goals = goals_df[goals_df["completed"] == 0]
                for _, g in active_goals.iterrows():
                    col_gc, col_gd = st.columns([3, 1])
                    col_gc.write(f"🎯 **{g['goal']}** (by {g['target_date']})")
                    if col_gd.button("✅ Done", key=f"g_{g['id']}"):
                        _complete_goal(g["id"])
                        st.rerun()

    if st.button("🤖 Generate AI Health Insight", use_container_width=True, type="primary"):
        # Build context from DB
        mood_ctx    = _load_mood_logs(30).to_string(index=False) if not _load_mood_logs(30).empty else "No mood data"
        workout_ctx = _load_workouts(30).to_string(index=False) if not _load_workouts(30).empty else "No workout data"
        med_ctx     = _load_medications().to_string(index=False) if not _load_medications().empty else "No medications"
        goals_ctx   = _load_goals().to_string(index=False) if not _load_goals().empty else "No goals set"

        if insight_type == "Mood Pattern Analysis (30 days)":
            prompt = f"""
Analyze this 30-day mood and health log data and provide insights:

MOOD DATA:
{mood_ctx}

MEDICATIONS:
{med_ctx}

{f'HEALTH DOCUMENTS:{chr(10)}{doc_text}' if doc_text else ''}

Please provide:
1. Mood trend analysis (improving, declining, or stable?)
2. Sleep quality patterns
3. Medication adherence observations
4. Potential triggers for mood changes
5. 3 specific actionable recommendations
6. Mental health check-in questions to reflect on

Keep the tone supportive and non-clinical.
"""
        elif insight_type == "Workout Progress & Recommendations":
            prompt = f"""
Analyze this workout history and provide coaching insights:

WORKOUT DATA:
{workout_ctx}

HEALTH GOALS:
{goals_ctx}

Please provide:
1. Workout consistency analysis
2. Most common workout types and if they align with goals
3. Signs of overtraining or undertraining
4. 3 specific improvements to the current routine
5. Next milestone to work toward
6. Recovery recommendations

Be specific, data-driven, and motivating.
"""
        elif insight_type == "Medication Management Review":
            prompt = f"""
Review this medication regimen and provide management tips:

MEDICATIONS:
{med_ctx}

MOOD DATA (for side effect context):
{mood_ctx}

Please provide:
1. General medication management best practices
2. Timing optimization suggestions (based on frequency)
3. Potential interactions to discuss with doctor (general guidance)
4. Side effect monitoring tips
5. Refill planning reminders
6. Questions to ask at the next doctor visit

Note: This is general wellness guidance, not medical advice. Always consult a physician.
"""
        elif insight_type == "Preventative Health Checklist":
            prompt = f"""
Create a personalized preventative health checklist based on this data:

DOCTOR VISITS:
Recent doctor visit history from user's health hub.

VACCINES:
{_load_vaccines().to_string(index=False) if not _load_vaccines().empty else 'No vaccines logged'}

MEDICATIONS:
{med_ctx}

{f'HEALTH DOCUMENTS:{chr(10)}{doc_text}' if doc_text else ''}

Please provide:
1. Annual screenings to schedule (blood work, dental, vision, etc.)
2. Vaccine boosters to consider
3. Lifestyle risk factors to address
4. Mental health check-ins recommended frequency
5. Specific tests/checkups for someone in their late 20s–30s

Keep it actionable with specific timeframes.
"""
        elif insight_type == "Mental Health & Wellness Tips":
            prompt = f"""
Provide personalized mental health and wellness guidance based on:

RECENT MOOD DATA:
{mood_ctx}

MEDICATIONS:
{med_ctx}

HEALTH GOALS:
{goals_ctx}

{f'HEALTH DOCUMENTS:{chr(10)}{doc_text}' if doc_text else ''}

Please provide:
1. Evidence-based mental health practices for the observed patterns
2. Stress management techniques
3. Sleep hygiene recommendations (based on sleep data)
4. Mindfulness/meditation suggestions
5. Social wellness tips
6. Warning signs to watch for and when to seek professional support

Be empathetic, practical, and non-judgmental.
"""
        else:
            prompt = f"""
The user has the following health data:

MOOD (30 days): {mood_ctx[:500]}
WORKOUTS: {workout_ctx[:500]}
MEDICATIONS: {med_ctx[:300]}
GOALS: {goals_ctx[:300]}

Their question: {custom_q}

Please answer thoroughly with practical, actionable advice. Always recommend consulting healthcare professionals for medical decisions.
"""

        with st.spinner("Analyzing your health data..."):
            result = _ai_health_analysis(prompt)

        st.markdown("### 🤖 AI Health Insights")
        st.markdown(result)
        st.caption("*This is AI-generated wellness guidance, not medical advice. Always consult qualified healthcare professionals.*")
