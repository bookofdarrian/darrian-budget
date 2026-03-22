"""cc_global_css.py — shared global CSS + mobile nav for College Confused."""

GLOBAL_CSS = """
<style>
/* ═══ VIEWPORT / META ═══════════════════════════════════════════════════════ */
html, body { overflow-x: hidden; }

/* ═══ HIDE TOP WHITE BAR / TOOLBAR ═══════════════════════════════════════════ */
header[data-testid="stHeader"],
.stAppToolbar,
#MainMenu,
footer { display: none !important; }

/* ═══ APP BACKGROUND ════════════════════════════════════════════════════════ */
.stApp, .main, .block-container { background: #0d0d1a !important; }

/* ═══ TEXT — only target Streamlit-native elements, NOT custom .cc-* classes ═══
   Removing the old aggressive rule:
     h1,h2,...,div,span { color:#f0f0ff !important }
   which was overriding -webkit-text-fill-color on gradient text elements,
   making hero eyebrow/h1/subtitle invisible.
═══════════════════════════════════════════════════════════════════════════════ */
.stMarkdown > div,
.stText,
[data-testid="stMarkdownContainer"] { color: #f0f0ff; }

/* ═══ FORCE CC HERO ELEMENTS VISIBLE — hardcoded fallbacks ═════════════════ */
.cc-eyebrow {
  color: #C4B8FF !important;
  -webkit-text-fill-color: #C4B8FF !important;
  background: rgba(155,142,255,0.12) !important;
  -webkit-background-clip: unset !important;
  background-clip: unset !important;
}
.cc-h1 {
  color: #F2F0FF !important;
  -webkit-text-fill-color: #F2F0FF !important;
  background: none !important;
  -webkit-background-clip: unset !important;
  background-clip: unset !important;
}
.cc-h1 span {
  background: linear-gradient(135deg, #9B8EFF, #C4B8FF) !important;
  -webkit-background-clip: text !important;
  background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  color: transparent !important;
}
.cc-hero-sub {
  color: #8A84B0 !important;
  -webkit-text-fill-color: #8A84B0 !important;
  background: none !important;
  -webkit-background-clip: unset !important;
}
.cc-nav-brand {
  background: linear-gradient(135deg, #9B8EFF, #C4B8FF) !important;
  -webkit-background-clip: text !important;
  background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
}
.cc-nav-link {
  color: #8A84B0 !important;
  -webkit-text-fill-color: #8A84B0 !important;
}
.cc-stat-num {
  color: #9B8EFF !important;
  -webkit-text-fill-color: #9B8EFF !important;
}
.cc-stat-label, .cc-stat-num + div {
  color: #8A84B0 !important;
  -webkit-text-fill-color: #8A84B0 !important;
}
.cc-feat-title, .cc-step-title, .cc-section-title {
  color: #F2F0FF !important;
  -webkit-text-fill-color: #F2F0FF !important;
}
.cc-feat-desc, .cc-step-desc, .cc-section-sub {
  color: #8A84B0 !important;
  -webkit-text-fill-color: #8A84B0 !important;
}
.cc-trust-item {
  color: #8A84B0 !important;
  -webkit-text-fill-color: #8A84B0 !important;
}
.cc-trust-check {
  color: #9B8EFF !important;
  -webkit-text-fill-color: #9B8EFF !important;
}

/* ═══ SIDEBAR ═══════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
    background: linear-gradient(180deg, #0f0f23 0%, #12122a 100%) !important;
    border-right: 1px solid #2a2a4a;
}
section[data-testid="stSidebarNav"] { display: none !important; }

/* Keep sidebar toggle button visible on mobile */
button[data-testid="baseButton-header"],
button[kind="header"] {
    display: block !important;
    visibility: visible !important;
    color: #f0f0ff !important;
    background: #1a1a2e !important;
    border-radius: 8px !important;
}

/* ═══ FORM INPUTS — DARK BACKGROUND ════════════════════════════════════════ */
[data-baseweb="select"] > div,
[data-baseweb="select"] [data-baseweb="popover"],
.stSelectbox > div > div {
    background: #1a1a2e !important;
    border-color: #3d3d6a !important;
    color: #f0f0ff !important;
}
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="base-input"],
input, textarea {
    background: #1a1a2e !important;
    color: #f0f0ff !important;
    border-color: #3d3d6a !important;
}
input::placeholder, textarea::placeholder { color: #6b7280 !important; }
.stTextInput > div > div,
.stNumberInput > div > div > div,
.stDateInput > div > div,
.stTextArea > div > div {
    background: #1a1a2e !important;
    border-color: #3d3d6a !important;
}

/* ═══ LABELS ═══════════════════════════════════════════════════════════════ */
.stSelectbox label, .stTextInput label, .stNumberInput label,
.stDateInput label, .stTextArea label, .stSlider label,
.stRadio label, .stCheckbox label,
[data-testid="stWidgetLabel"] { color: #c9d1d9 !important; font-weight: 600; }

/* ═══ DROPDOWN MENU ═════════════════════════════════════════════════════════ */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"] { background: #1a1a2e !important; border: 1px solid #3d3d6a !important; }
[role="option"]:hover { background: #2a2a4a !important; }
[aria-selected="true"] { background: #6C63FF !important; }

/* ═══ NUMBER INPUT BUTTONS ══════════════════════════════════════════════════ */
.stNumberInput button {
    background: #2a2a4a !important; color: #f0f0ff !important; border-color: #3d3d6a !important;
}

/* ═══ TABS ══════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] { background: #1a1a2e !important; border-bottom: 2px solid #2a2a4a !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #9ba3b4 !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: #6C63FF !important; border-bottom: 2px solid #6C63FF !important; }

/* ═══ BUTTONS ═══════════════════════════════════════════════════════════════ */
.stButton > button {
    background: linear-gradient(135deg, #6C63FF, #9b55ff) !important;
    color: #fff !important; border: none !important; font-weight: 700 !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

/* ═══ ALERTS / EXPANDERS ════════════════════════════════════════════════════ */
.stAlert { background: #1a1a2e !important; border-color: #3d3d6a !important; }
.streamlit-expanderHeader { background: #1a1a2e !important; color: #f0f0ff !important; }

/* ═══ LINKS ══════════════════════════════════════════════════════════════════ */
a { color: #6C63FF !important; }
a:hover { color: #9b55ff !important; }

/* ═══ METRICS / DATAFRAMES ══════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: #1a1a2e !important; border: 1px solid #2a2a4a !important;
    border-radius: 10px; padding: 12px !important;
}
.stDataFrame, [data-testid="stTable"] { background: #1a1a2e !important; color: #f0f0ff !important; }

/* ═══ MOBILE BOTTOM NAV (shown only on small screens) ═══════════════════════ */
.cc-mobile-nav {
    display: none;
    position: fixed;
    bottom: 0; left: 0; right: 0;
    background: #0f0f23;
    border-top: 2px solid #3d3d6a;
    z-index: 9999;
    padding: 8px 0 max(8px, env(safe-area-inset-bottom));
}
.cc-mobile-nav-inner {
    display: flex;
    justify-content: space-around;
    align-items: center;
    max-width: 480px;
    margin: 0 auto;
}
.cc-mobile-nav a {
    display: flex !important;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    text-decoration: none !important;
    color: #9ba3b4 !important;
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    padding: 4px 8px;
    border-radius: 10px;
    transition: color 0.15s;
    min-width: 52px;
}
.cc-mobile-nav a:hover, .cc-mobile-nav a.active {
    color: #6C63FF !important;
    background: rgba(108,99,255,0.12);
}
.cc-mobile-nav a .nav-icon { font-size: 1.35rem; line-height: 1; }
.cc-mobile-nav a .nav-label { font-size: 0.58rem; text-transform: uppercase; }

/* Add bottom padding on mobile so content is not hidden behind nav bar */
@media (max-width: 768px) {
    .cc-mobile-nav { display: block; }
    .block-container { padding-bottom: 80px !important; }
    .cc-title { font-size: 2rem !important; }
    .cc-subtitle { font-size: 1.1rem !important; }
    .cc-stats { gap: 16px !important; flex-wrap: wrap; }
    .cc-stat-num { font-size: 1.4rem !important; }
    .cc-banner { flex-direction: column; gap: 12px; text-align: center; }
}
</style>
"""

# NOTE: hrefs use Streamlit's actual URL slugs (strips numeric prefix from filename)
# 80_cc_home.py → /cc_home, 81_cc_timeline.py → /cc_timeline, etc.
MOBILE_NAV_HTML = """
<nav class="cc-mobile-nav" role="navigation" aria-label="Main navigation">
  <div class="cc-mobile-nav-inner">
    <a href="/" aria-label="Home">
      <span class="nav-icon">🏠</span>
      <span class="nav-label">Home</span>
    </a>
    <a href="/cc_timeline" aria-label="My Timeline">
      <span class="nav-icon">📅</span>
      <span class="nav-label">Timeline</span>
    </a>
    <a href="/cc_scholarships" aria-label="Scholarships">
      <span class="nav-icon">💰</span>
      <span class="nav-label">Scholarships</span>
    </a>
    <a href="/cc_essay_station" aria-label="Essay Station">
      <span class="nav-icon">✍️</span>
      <span class="nav-label">Essays</span>
    </a>
    <a href="/cc_test_prep" aria-label="SAT/ACT Prep">
      <span class="nav-icon">📚</span>
      <span class="nav-label">SAT/ACT</span>
    </a>
  </div>
</nav>
"""
