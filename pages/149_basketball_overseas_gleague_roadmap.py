import streamlit as st
st.set_page_config(page_title="Basketball Roadmap", page_icon="🏀", layout="wide")
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                           label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                 label="Todo",               icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",    label="Creator",            icon="🎬")
st.sidebar.page_link("pages/25_notes.py",                label="Notes",              icon="📝")
st.sidebar.page_link("pages/26_media_library.py",        label="Media Library",      icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",   label="Personal Assistant", icon="🤖")
st.sidebar.page_link("pages/147_proactive_ai_engine.py", label="Proactive AI",       icon="🧠")
render_sidebar_user_widget()

# ── Mobile-optimized CSS ──
st.markdown("""
<style>
    /* Mobile-first responsive tweaks */
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        h1 { font-size: 1.5rem !important; }
        h2, h3 { font-size: 1.2rem !important; }
        [data-testid="metric-container"] { padding: 0.5rem !important; }
        [data-testid="stMetricValue"] { font-size: 1rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    }
    .phase-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem;
        border-left: 4px solid #e94560;
    }
    .phase-card h4 { color: #e94560; margin-top: 0; }
    .kpi-tag {
        display: inline-block; background: #0f3460; color: #fff;
        padding: 0.25rem 0.6rem; border-radius: 20px; font-size: 0.8rem;
        margin: 0.15rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Title ──
st.title("🏀 Overseas → G League Roadmap")
st.caption("Darrian Belcher · 5'8\" · 140 lbs · 35\"+ vert · Left-hand discovery · Age 22 · Aug 25 birthday")

# ── Baseline ──
st.subheader("📊 Current Baseline")
c1, c2, c3 = st.columns(3)
c1.metric("Height / Weight", "5'8\" / 140 lbs")
c2.metric("Vertical", "35\"+ (est. 37\"+)")
c3.metric("Dominant Hand", "Left (new)")

c4, c5, c6 = st.columns(3)
c4.metric("Age / DOB", "22 / Aug 25")
c5.metric("Experience", "On-and-off since kid")
c6.metric("Target", "Overseas → G League")

# ── Priority Stack ──
st.subheader("🎯 Priority Stack")
st.markdown("""
1. **Overseas contract** (Europe lower-tier, Asia, Latin America) — realistic 6-month target
2. **G League roster spot** — 12-18 month target after overseas tape
3. **NBA** — aspirational, requires G League breakout season + viral moments
""")

# ── 12-Month Phases ──
st.subheader("🗓️ 12-Month Blueprint")

# Phase 1
st.markdown("""<div class="phase-card">
<h4>Phase 1: Foundation (Months 1–3 · Apr–Jun 2026)</h4>
<b>Focus:</b> Body transformation, left-hand integration, film library, agent outreach<br>
<b>Body:</b> 140 → 155 lbs lean · 3,200–3,600 kcal/day · 1.8g protein/lb · Creatine + whey<br>
<b>Skill:</b> 200 shots/day · Left-hand finishing drills 30 min/day · Ball-handling circuits<br>
<b>Film:</b> Record 2 full games + 1 highlight reel (30s/60s/2min cuts)<br>
<b>Exposure:</b> 10–15 outreach emails/week to agents + overseas coaches<br>
<span class="kpi-tag">+15 lbs</span>
<span class="kpi-tag">37\"+ vert</span>
<span class="kpi-tag">35% 3PT</span>
<span class="kpi-tag">2.5 AST/TO</span>
<span class="kpi-tag">20+ leads</span>
</div>""", unsafe_allow_html=True)

# Phase 2
st.markdown("""<div class="phase-card">
<h4>Phase 2: Exposure & Overseas (Months 4–6 · Jul–Sep 2026)</h4>
<b>Focus:</b> Camps, showcases, agent signings, contract negotiations<br>
<b>Camps:</b> 3–5 pro/AAU camps (Drew League, CP3 camp, local pro-ams)<br>
<b>Agents:</b> Sign with 1 boutique agent specializing in overseas placements<br>
<b>Leagues:</b> Target Germany (ProB), France (NM1), Japan (B2), Argentina (LNB), Mexico (LNBP)<br>
<span class="kpi-tag">3 camp invites</span>
<span class="kpi-tag">1 agent signed</span>
<span class="kpi-tag">1 overseas offer</span>
</div>""", unsafe_allow_html=True)

# Phase 3
st.markdown("""<div class="phase-card">
<h4>Phase 3: Overseas Season (Months 7–9 · Oct–Dec 2026)</h4>
<b>Focus:</b> Dominate overseas league, build pro stats, continue bulking<br>
<b>Stats target:</b> 15+ PPG · 5+ APG · 2+ STL · sub-2.0 TO · 40%+ 3PT<br>
<b>Body:</b> 155 → 170 lbs · Maintain 38\"+ vert · 3.5s lane agility<br>
<b>Film:</b> Weekly highlight cuts for social + agent distribution<br>
<span class="kpi-tag">15+ PPG</span>
<span class="kpi-tag">5+ APG</span>
<span class="kpi-tag">170 lbs</span>
<span class="kpi-tag">40%+ 3PT</span>
</div>""", unsafe_allow_html=True)

# Phase 4
st.markdown("""<div class="phase-card">
<h4>Phase 4: G League Push (Months 10–12 · Jan–Mar 2027)</h4>
<b>Focus:</b> G League tryouts, NBA showcases, viral film package<br>
<b>Tryouts:</b> G League open tryouts + Showcase Cup invites<br>
<b>Body:</b> 170 → 180 lbs · 40\"+ vert · Elite conditioning<br>
<b>Film:</b> Full-season highlight reel + advanced stat package for scouts<br>
<span class="kpi-tag">G League invite</span>
<span class="kpi-tag">180 lbs</span>
<span class="kpi-tag">40\"+ vert</span>
<span class="kpi-tag">Scout package</span>
</div>""", unsafe_allow_html=True)

# ── Weekly Template ──
st.subheader("📅 Weekly Template")
st.markdown("""
| Day | Skill (2h) | Strength (1h) | Film (1h) | Outreach (30m) |
|-----|-----------|---------------|-----------|----------------|
| **Mon** | Shooting + left-hand | Push day | Watch film | Email agents |
| **Tue** | Ball-handling | Pull day | Break down plays | Social posts |
| **Wed** | Game IQ + reads | Legs + plyo | Self-film review | Follow-ups |
| **Thu** | Shooting + off-dribble | Push day | Opponent scout | Camp research |
| **Fri** | Full scrimmage | Pull day | Highlight edits | Network calls |
| **Sat** | **3h game/camp** | — | — | — |
| **Sun** | **Recovery + review** | Mobility | Weekly KPI check | Plan next week |
""")

# ── Nutrition Protocol ──
st.subheader("🍗 Bulking Nutrition Protocol")
st.markdown("""
**Daily targets (Phase 1–2):** 3,200–3,600 kcal · 250–280g protein · 400–500g carbs · 80–100g fat

| Meal | Example | Macros |
|------|---------|--------|
| **Breakfast** | 4 eggs, oats, banana, PB | 600 kcal / 40g P |
| **Snack 1** | Whey shake + granola | 400 kcal / 40g P |
| **Lunch** | Chicken, rice, veggies | 700 kcal / 50g P |
| **Pre-workout** | PB&J + banana | 400 kcal / 15g P |
| **Post-workout** | Whey + dextrose + creatine | 350 kcal / 40g P |
| **Dinner** | Salmon, sweet potato, salad | 700 kcal / 45g P |
| **Before bed** | Casein shake + almonds | 450 kcal / 40g P |

**Supplements:** Creatine monohydrate 5g/day · Whey isolate · Omega-3 · Vitamin D3 · Magnesium
""")

# ── Left-Hand Development ──
st.subheader("🤚 Left-Hand Development Plan")
st.markdown("""
Since you just discovered you may be naturally left-handed, this is a **massive competitive advantage** if developed properly:

1. **Daily life:** Use left hand for eating, writing, phone — rewire motor patterns
2. **Dribbling:** 15 min/day left-only cone drills, crossovers, behind-back
3. **Finishing:** 50 left-hand layups/day (both sides of rim, floaters, reverse)
4. **Shooting:** Start with form shooting 5ft, progress to 3PT over 8 weeks
5. **Game integration:** By Month 3, use left hand as primary in scrimmages
""")

# ── Exposure Playbook ──
st.subheader("📢 Exposure & Agent Playbook")
st.markdown("""
**Film Package (build by end of Month 2):**
- 2 full unedited games (shows coaches your real game)
- 30-second sizzle reel (social media / DMs)
- 60-second highlight reel (agent pitches)
- 2-minute full highlight (league applications)

**Target Leagues (realistic for 5'8\" guard with elite athleticism):**
- 🇩🇪 Germany ProB / ProA — good development, decent pay
- 🇫🇷 France NM1 / NM2 — competitive, scouts watch
- 🇯🇵 Japan B2 / B3 — values athleticism, good lifestyle
- 🇦🇷 Argentina LNB — competitive, affordable living
- 🇲🇽 Mexico LNBP — close to home, growing league

**Agent Outreach Template:**
> Subject: 5'8\" PG | 37\"+ Vert | Film Attached | Seeking Overseas
>
> Hi [Agent], I'm a 22-year-old point guard (5'8\", 155 lbs, 37\"+ vertical)
> looking for overseas opportunities. I've attached my highlight reel and
> full game film. I'm a high-IQ, athletic guard with elite finishing ability
> and a developing left hand. Available immediately. Would love to discuss.

**Weekly Outreach Cadence:** 10–15 emails/week · 5 LinkedIn messages · 3 Instagram DMs to overseas coaches
""")

# ── Risk Mitigation ──
st.subheader("⚠️ Risk Mitigation")
st.markdown("""
- **Injury:** Prehab daily (ankle/knee bands, hip mobility), sleep 8+ hrs, deload every 4th week
- **Burnout:** 1 full rest day/week, mental health check-ins, maintain hobbies outside ball
- **Financial:** Budget for camps ($200–500 each), travel, agent fees (typically 10% of contract)
- **No offers by Month 6:** Pivot to semi-pro leagues (TBL, ABA) for film + stats, re-approach in fall
""")

# ── Next Steps ──
st.subheader("🚀 Immediate Next Steps")
st.markdown("""
1. ✅ **Upload 2 full games + 1 highlight** to Immich or share links/files
2. ✅ **Send recent stats** in format: MIN / PTS / REB / AST / STL / TO / FG% / 3PT% / FT%
3. ✅ **Confirm weekly schedule** — hours/day available, gym access, trainer access
4. ✅ **Pick 3 target leagues** from the list above for Phase 2 outreach
5. ✅ **Start left-hand daily life switch** today — eat, write, brush teeth with left hand
6. ✅ **Begin nutrition protocol** — hit 3,200 kcal minimum starting tomorrow
""")

st.markdown("---")
st.caption("Built for Darrian Belcher · Overseas first, G League next, NBA dream · Updated April 2026")
