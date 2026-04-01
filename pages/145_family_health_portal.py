"""
Family Health Portal — Page 145
Read-only, family-facing wellness view for Darrian Belcher.
No full login required — uses a simple family access PIN.
Shows: mood trends, episode warnings, daily status, and family guidance.
Designed for mom/family to check in on Darrian's wellness.
"""
import streamlit as st
import os
import sys
import json
from datetime import date, timedelta

st.set_page_config(
    page_title="💚 Darrian's Health — Family Portal",
    page_icon="💚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, init_db, get_setting, set_setting
from utils.auth import inject_css

init_db()
inject_css()

PH = "%s" if USE_POSTGRES else "?"
AUTO = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

MOOD_SCALE = {
    1: ("😢", "Depressed", "🔵"),
    2: ("😔", "Low", "🔵"),
    3: ("😐", "Neutral", "⚪"),
    4: ("🙂", "Good", "🟢"),
    5: ("😄", "Great", "🟢"),
    6: ("⚡", "Elevated", "🟡"),
    7: ("🔥", "Manic High", "🔴"),
}

DEFAULT_PIN = "2025"  # Family can change this in settings

# ── Tables ─────────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS hh_daily_checkin (
            id                {AUTO},
            user_id           INTEGER NOT NULL DEFAULT 1,
            checkin_date      DATE NOT NULL,
            mood_score        INTEGER,
            anxiety_score     INTEGER,
            energy_score      INTEGER,
            sleep_hours       REAL,
            sleep_quality     TEXT,
            primary_emotion   TEXT,
            family_visible    INTEGER DEFAULT 0,
            family_note       TEXT,
            overall_day_score INTEGER,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

_ensure_tables()

# ── Data loaders ───────────────────────────────────────────────────────────────
def _load_family_checkins(days=30):
    conn = get_conn()
    cur = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(f"""
        SELECT checkin_date, mood_score, energy_score, anxiety_score,
               sleep_hours, sleep_quality, primary_emotion,
               family_note, family_visible, overall_day_score
        FROM hh_daily_checkin
        WHERE user_id=1 AND family_visible > 0 AND checkin_date >= {PH}
        ORDER BY checkin_date DESC
    """, (since,))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _load_all_recent(days=7):
    """Load all recent check-ins for episode detection (not shown to family directly)."""
    conn = get_conn()
    cur = conn.cursor()
    since = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(f"""
        SELECT checkin_date, mood_score, sleep_hours, anxiety_score, energy_score
        FROM hh_daily_checkin
        WHERE user_id=1 AND checkin_date >= {PH}
        ORDER BY checkin_date DESC
    """, (since,))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def _get_episode_status(checkins):
    """Return (status_level, status_msg, color) based on recent check-ins."""
    if not checkins:
        return "unknown", "No recent data available.", "gray"

    moods = [c["mood_score"] for c in checkins if c.get("mood_score")]
    sleeps = [c["sleep_hours"] for c in checkins if c.get("sleep_hours")]
    anxieties = [c["anxiety_score"] for c in checkins if c.get("anxiety_score") is not None]

    if not moods:
        return "unknown", "No mood data logged yet this week.", "gray"

    avg_mood = sum(moods) / len(moods)
    avg_sleep = sum(sleeps) / len(sleeps) if sleeps else 7

    # Red flags
    if avg_mood >= 6.0 and avg_sleep < 5.5:
        return "alert", "⚠️ Mood has been elevated AND sleep has been low. This can be an early sign of a mood episode. Please reach out to check in.", "red"
    if avg_mood >= 5.8:
        return "watch", "🟡 Mood has been on the higher side this week. Keep an eye out — offer calm, low-key support.", "orange"
    if avg_mood <= 2.0:
        return "watch", "🔵 Darrian has been in a low mood this week. Gentle presence and support are most helpful right now.", "blue"
    if avg_sleep < 5.5:
        return "watch", "😴 Sleep has been below average this week. Sleep is important for mood stability — a check-in may help.", "orange"
    if anxieties and sum(anxieties) / len(anxieties) >= 2.5:
        return "watch", "😰 Anxiety has been consistently moderate to high. Calm, low-pressure check-ins are ideal.", "orange"

    return "stable", "✅ Things look stable this week. No major mood, sleep, or anxiety concerns detected.", "green"

def _get_latest_checkin():
    checkins = _load_family_checkins(7)
    return checkins[0] if checkins else None

# ── PIN Auth ───────────────────────────────────────────────────────────────────
def _check_pin() -> bool:
    """Simple family PIN check — no account needed."""
    if st.session_state.get("family_portal_unlocked"):
        return True

    stored_pin = get_setting("family_portal_pin") or DEFAULT_PIN

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f49a.png",
                 width=60)
        st.markdown("## 💚 Darrian's Health Portal")
        st.markdown("*Family access — enter your PIN to view*")
        st.markdown("")
        pin_input = st.text_input("Family PIN", type="password", placeholder="Enter PIN",
                                   max_chars=10, key="family_pin_input",
                                   label_visibility="collapsed")
        if st.button("Unlock Portal 🔓", type="primary", use_container_width=True):
            if pin_input == stored_pin:
                st.session_state.family_portal_unlocked = True
                st.rerun()
            else:
                st.error("Incorrect PIN. Ask Darrian for the family access PIN.")

        st.markdown("")
        st.caption("💬 This portal shows Darrian's shared wellness check-ins so family can stay informed and support him.")
    return False

# ── Main portal ────────────────────────────────────────────────────────────────
def render_portal():
    # Header
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 0.5rem 0;'>
        <h1 style='font-size:2rem; margin-bottom:0;'>💚 Darrian's Wellness Portal</h1>
        <p style='color:#888; font-size:0.95rem; margin-top:0;'>Family View — Updated daily by Darrian</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Current Status Banner ──────────────────────────────────────────────────
    all_recent = _load_all_recent(7)
    status_level, status_msg, status_color = _get_episode_status(all_recent)

    color_map = {
        "green": "#1a7a1a", "orange": "#cc6600", "red": "#cc0000",
        "blue": "#1a4a9a", "gray": "#555"
    }
    bg_map = {
        "green": "#e8f5e9", "orange": "#fff3e0", "red": "#ffebee",
        "blue": "#e3f2fd", "gray": "#f5f5f5"
    }

    st.markdown(f"""
    <div style='background:{bg_map.get(status_color,"#f5f5f5")};
                border-left:5px solid {color_map.get(status_color,"#888")};
                padding: 1rem 1.2rem; border-radius: 8px; margin-bottom: 1.5rem;'>
        <strong style='color:{color_map.get(status_color,"#333")}; font-size:1rem;'>
            This Week's Status</strong><br>
        <span style='font-size:0.95rem;'>{status_msg}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Latest check-in ────────────────────────────────────────────────────────
    latest = _get_latest_checkin()
    family_checkins = _load_family_checkins(14)

    if latest:
        st.markdown("### 📅 Most Recent Update")
        date_str = str(latest.get("checkin_date", ""))[:10]
        mood = latest.get("mood_score", 3) or 3
        emoji, label, dot = MOOD_SCALE.get(mood, ("😐", "Neutral", "⚪"))
        sleep = latest.get("sleep_hours")
        emotion = latest.get("primary_emotion", "")
        family_note = latest.get("family_note", "")
        day_score = latest.get("overall_day_score")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mood", f"{dot} {label}")
        c2.metric("Sleep", f"{sleep:.1f} hrs" if sleep else "—")
        c3.metric("Feeling", emotion or "—")
        c4.metric("Day Score", f"{day_score}/10" if day_score else "—")

        if family_note:
            st.info(f"💬 **Darrian's note for family:** _{family_note}_")

        st.caption(f"Last updated: {date_str}")
    else:
        st.info("📭 No shared check-ins yet. Darrian hasn't marked any entries as visible to family yet.")

    st.divider()

    # ── Mood timeline ──────────────────────────────────────────────────────────
    if family_checkins:
        st.markdown("### 📊 Mood Timeline (Last 2 Weeks)")
        st.caption("Only entries Darrian chose to share are shown.")

        try:
            import pandas as pd
            import plotly.graph_objects as go

            df = pd.DataFrame(family_checkins).sort_values("checkin_date")

            fig = go.Figure()
            mood_colors = []
            for m in df.get("mood_score", []):
                if m is None:
                    mood_colors.append("#888")
                elif m >= 6:
                    mood_colors.append("#FF9800")
                elif m <= 2:
                    mood_colors.append("#2196F3")
                elif 3 <= m <= 5:
                    mood_colors.append("#4CAF50")
                else:
                    mood_colors.append("#888")

            fig.add_trace(go.Scatter(
                x=df["checkin_date"],
                y=df["mood_score"],
                mode="lines+markers",
                name="Mood",
                line=dict(color="#4CAF50", width=2),
                marker=dict(size=10, color=mood_colors),
                hovertemplate="%{x}<br>Mood: %{y}/7<extra></extra>"
            ))

            # Comfort zones
            fig.add_hrect(y0=3, y1=5, fillcolor="rgba(76,175,80,0.08)",
                          line_width=0, annotation_text="Stable range",
                          annotation_position="top right")
            fig.add_hline(y=5.5, line_dash="dash", line_color="orange",
                          line_width=1, annotation_text="Watch zone")
            fig.add_hline(y=2.5, line_dash="dash", line_color="#2196F3",
                          line_width=1, annotation_text="Low zone")

            fig.update_layout(
                height=280,
                yaxis=dict(range=[0, 8], tickvals=[1,2,3,4,5,6,7],
                           ticktext=["😢 Depressed","😔 Low","😐 Neutral",
                                     "🙂 Good","😄 Great","⚡ Elevated","🔥 High"]),
                xaxis_title="Date",
                margin=dict(t=20, b=20, l=10, r=10),
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            # Fallback: simple table
            for ci in family_checkins[:7]:
                mood = ci.get("mood_score", 3) or 3
                emoji, label, dot = MOOD_SCALE.get(mood, ("😐", "Neutral", "⚪"))
                st.markdown(f"**{str(ci.get('checkin_date',''))[:10]}** — {dot} {label}")

    st.divider()

    # ── Family guide ──────────────────────────────────────────────────────────
    st.markdown("### 💬 How to Support Darrian")

    with st.container(border=True):
        st.markdown("""
**🟢 When mood is 3–5 (Stable — Good)**
He's doing well. A simple "proud of you" or normal conversation is perfect.
No need to check on health — just be present.

**🟡 When mood is 6–7 (Elevated)**
He may seem energized, talkative, or ambitious.
→ Don't add stimulation — keep conversation calm and grounded
→ Gently ask if he's been sleeping well
→ Don't argue or confront — stay warm and present
→ If it's been 3+ days like this with less sleep, call him

**🔵 When mood is 1–2 (Low)**
He's in a low period. He may seem withdrawn or quiet.
→ Don't give advice — just show up and be present
→ "I love you and I'm here" goes further than any solution
→ Offer to do something low-key together (watch something, food)
→ Don't take silence personally

**😴 Sleep is the #1 early warning sign**
If Darrian tells you he's barely sleeping but has lots of energy, that's the clearest
sign to gently encourage rest and possibly reach out to his doctor.

**If he mentions self-harm thoughts:**
→ Stay calm — don't panic or react dramatically
→ Ask: "Are you safe right now?"
→ Encourage him to call/text his therapist
→ Crisis line: **988** (call or text) | Crisis text: **HOME to 741741**
→ You can also call 988 yourself for guidance on how to help him
""")

    st.divider()

    # ── Quick reference ───────────────────────────────────────────────────────
    st.markdown("### 📋 Darrian's Health at a Glance")
    with st.expander("What you should know (click to expand)"):
        st.markdown("""
**Diagnoses (confirmed by evaluation):**
- **Mood Regulation Disorder** — mood cycles between highs and lows; had a manic episode at 17
- **ADHD (Inattentive type)** — difficulty with focus and attention, not hyperactivity
- **Generalized Anxiety Disorder** — persistent worry; physically feels anxiety strongly

**Current medications:**
- **Atomoxetine (Strattera)** — for ADHD focus
- **Quetiapine (Seroquel)** — for mood stability
- **Mirtazapine 15mg** — for sleep and mood support

**What helps most:**
- Consistent sleep schedule
- Low-stimulation environment at home
- Exercise (especially basketball)
- Regular tele-therapy sessions
- Feeling supported without pressure

**What doesn't help:**
- High-conflict or stressful conversations during elevated moods
- Pressure to "just push through it" — it's neurological, not willpower
- Dismissing his anxiety as overthinking
""")

    st.divider()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center; color:#888; font-size:0.8rem; padding:1rem 0;'>
        💚 Darrian built this portal so his family can stay connected to his wellness.<br>
        Only entries he chooses to share appear here. Updated daily when he logs a check-in.
    </div>
    """, unsafe_allow_html=True)

    # Admin: allow pin change at bottom
    with st.expander("⚙️ Family Settings (PIN management)"):
        st.caption("Change the family access PIN below.")
        current_pin = get_setting("family_portal_pin") or DEFAULT_PIN
        new_pin = st.text_input("New Family PIN (share with family members)",
                                 value=current_pin, type="password", key="new_family_pin")
        if st.button("Save PIN", key="save_family_pin"):
            set_setting("family_portal_pin", new_pin)
            st.success("✅ Family PIN updated!")

# ── Entry point ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container { max-width: 800px; padding-top: 2rem; }
    [data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

if _check_pin():
    render_portal()
