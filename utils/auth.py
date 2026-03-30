"""
Peach State Savings — Authentication & Authorization

Supports two modes:
  1. MULTI_USER mode (default):
     - Email + password registration/login with bcrypt hashing
     - Brute-force lockout (10 failures → 15-min lockout)
     - Free vs Pro tier gating via Stripe
  2. LEGACY mode (APP_PASSWORD env var set, MULTI_USER=false):
     - Single shared password (backward-compatible for beta testers)

Call require_login() at the top of every page.
Call require_pro() on pages that need a paid subscription.
"""

import os
import math
import streamlit as st
from utils.db import (
    init_db, authenticate_user, create_user, get_user_by_id,
    is_pro_user, get_setting, validate_email, validate_password,
    is_account_locked, set_active_db
)

# ── Brand ─────────────────────────────────────────────────────────────────────
APP_NAME    = "Peach State Savings"
APP_EMOJI   = "🍑"

# PSS 2.0 palette — warm peach-orange on near-black with navy + emerald accents
PEACH       = "#FF6B35"   # primary — warm peach-orange
PEACH_DARK  = "#d9541e"   # primary hover
PEACH_GLOW  = "#2d1206"   # primary bg tint for cards/glow
BG_MAIN     = "#0D1117"   # near-black background
BG_CARD     = "#161B22"   # card background
BG_BORDER   = "#30363D"   # border / divider
TEXT_MUTED  = "#8B949E"   # muted text
TEXT_MAIN   = "#E6EDF3"   # primary text
PSS_ACCENT  = "#1A936F"   # emerald green — money / growth / success
PSS_NAVY    = "#004E89"   # deep navy — trust / secondary
PSS_AMBER   = "#F18F01"   # amber — warnings / highlights

GLOBAL_CSS = f"""
<style>
/* ── Hide Streamlit's auto-generated page nav (we use our own) ── */
[data-testid="stSidebarNav"] {{ display: none !important; }}

/* ── Peach State Savings global styles ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {BG_MAIN} 0%, #12151c 100%);
    border-right: 1px solid {BG_BORDER};
}}
[data-testid="stSidebar"] .stMarkdown p {{
    color: {TEXT_MUTED};
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.brand-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 12px 0;
    border-bottom: 1px solid {BG_BORDER};
    margin-bottom: 8px;
}}
.brand-name {{
    font-size: 1.15rem;
    font-weight: 700;
    color: {PEACH};
    letter-spacing: -0.02em;
    line-height: 1.2;
}}
.brand-tagline {{
    font-size: 0.68rem;
    color: {TEXT_MUTED};
    margin-top: -1px;
}}
.pro-badge {{
    display: inline-block;
    background: linear-gradient(135deg, {PEACH}, {PEACH_DARK});
    color: #000;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    vertical-align: middle;
    margin-left: 6px;
}}
.free-badge {{
    display: inline-block;
    background: {BG_BORDER};
    color: {TEXT_MUTED};
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    vertical-align: middle;
    margin-left: 6px;
}}
[data-testid="metric-container"] {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 10px;
    padding: 14px 18px;
}}
.paywall-card {{
    background: linear-gradient(135deg, {PEACH_GLOW} 0%, {BG_CARD} 100%);
    border: 1px solid {PEACH};
    border-radius: 14px;
    padding: 32px;
    text-align: center;
    margin: 24px 0;
}}
.paywall-card h2 {{ color: {PEACH}; margin-bottom: 8px; }}
.paywall-card p  {{ color: {TEXT_MUTED}; margin-bottom: 20px; }}
.price-card {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 14px;
    padding: 28px;
    height: 100%;
}}
.price-card.featured {{
    border-color: {PEACH};
    background: linear-gradient(135deg, {PEACH_GLOW} 0%, {BG_CARD} 100%);
}}
.price-amount {{
    font-size: 2.5rem;
    font-weight: 800;
    color: {TEXT_MAIN};
    line-height: 1;
}}
.price-period {{ color: {TEXT_MUTED}; font-size: 0.85rem; }}
.feature-list {{ list-style: none; padding: 0; margin: 16px 0; }}
.feature-list li {{ padding: 5px 0; color: #c8d0dc; font-size: 0.9rem; }}
.feature-list li::before {{ content: "✓ "; color: {PEACH}; font-weight: 700; }}
.feature-list li.locked {{ color: {TEXT_MUTED}; }}
.feature-list li.locked::before {{ content: "🔒 "; }}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {PEACH}, {PEACH_DARK}) !important;
    color: #000 !important;
    border: none !important;
    font-weight: 700 !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: {PEACH_DARK} !important;
    color: #000 !important;
}}

/* ── PSS 2.0 Enhancements ──────────────────────────────────────────────────── */

/* App background */
.stApp {{ background-color: {BG_MAIN}; color: {TEXT_MAIN}; }}

/* ── Top header/toolbar bar — force dark ── */
[data-testid="stHeader"] {{
    background-color: {BG_MAIN} !important;
    border-bottom: 1px solid {BG_BORDER} !important;
    backdrop-filter: none !important;
}}
/* Streamlit v1.40+ renamed the header container */
header[data-testid="stHeader"],
.stAppHeader,
[data-testid="stAppHeader"] {{
    background-color: {BG_MAIN} !important;
    border-bottom: 1px solid {BG_BORDER} !important;
}}
/* The toolbar icon buttons inside the header (menu, deploy, etc.) */
[data-testid="stHeader"] button,
[data-testid="stToolbar"] {{
    color: {TEXT_MUTED} !important;
}}
/* Nuke any white/light background on the main top bar iframe layer */
.stApp > header {{
    background-color: {BG_MAIN} !important;
    border-bottom: 1px solid {BG_BORDER} !important;
}}

/* Page headers */
h1 {{ color: {PEACH}; font-weight: 700; letter-spacing: -0.02em; }}
h2 {{ color: {TEXT_MAIN}; font-weight: 600; }}
h3 {{ color: {TEXT_MUTED}; font-weight: 500; }}

/* All regular buttons — lift on hover */
.stButton > button {{
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    border-radius: 8px !important;
}}
.stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(255,107,53,0.25) !important;
}}

/* Input fields */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {{
    background: {BG_CARD} !important;
    border: 1px solid {BG_BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT_MAIN} !important;
}}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {{
    border-color: {PEACH} !important;
    box-shadow: 0 0 0 2px rgba(255,107,53,0.2) !important;
}}

/* Selectbox */
.stSelectbox [data-baseweb="select"] > div {{
    background: {BG_CARD} !important;
    border-color: {BG_BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT_MAIN} !important;
}}

/* Tabs — primary color active indicator */
[data-testid="stTabs"] [data-baseweb="tab"] {{
    color: {TEXT_MUTED};
    font-weight: 500;
    border-bottom: 2px solid transparent;
    transition: color 0.15s ease;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: {PEACH} !important;
    border-bottom-color: {PEACH} !important;
    font-weight: 600 !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {{
    color: {TEXT_MAIN} !important;
}}

/* Success / info / warning / error alerts */
.stSuccess, [data-testid="stAlert"][kind="success"] {{
    background: rgba(26,147,111,0.12) !important;
    border: 1px solid {PSS_ACCENT} !important;
    border-radius: 8px !important;
    color: #7dd3b8 !important;
}}
.stInfo, [data-testid="stAlert"][kind="info"] {{
    background: rgba(0,78,137,0.15) !important;
    border: 1px solid {PSS_NAVY} !important;
    border-radius: 8px !important;
}}
.stWarning, [data-testid="stAlert"][kind="warning"] {{
    background: rgba(241,143,1,0.12) !important;
    border: 1px solid {PSS_AMBER} !important;
    border-radius: 8px !important;
}}
.stError, [data-testid="stAlert"][kind="error"] {{
    background: rgba(255,69,58,0.12) !important;
    border: 1px solid #FF453A !important;
    border-radius: 8px !important;
}}

/* Expanders */
[data-testid="stExpander"] {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 10px;
}}
[data-testid="stExpander"] summary {{
    color: {TEXT_MAIN};
    font-weight: 500;
}}

/* Metric delta positive/negative */
[data-testid="stMetricDelta"] svg {{ display: none; }}
[data-testid="stMetricDelta"][data-direction="up"] span {{ color: {PSS_ACCENT} !important; }}
[data-testid="stMetricDelta"][data-direction="down"] span {{ color: #FF453A !important; }}

/* Dataframe */
[data-testid="stDataFrame"] {{
    border: 1px solid {BG_BORDER};
    border-radius: 8px;
    overflow: hidden;
}}

/* Progress bar — peach fill */
[data-testid="stProgressBar"] > div > div {{
    background: linear-gradient(90deg, {PEACH}, {PSS_ACCENT}) !important;
}}

/* Mobile Responsiveness ─────────────────────────────────────────────────── */
@media (max-width: 768px) {{

    /* ── Main content padding ── */
    .main .block-container {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
        max-width: 100% !important;
    }}

    /* ── Sidebar: collapse by default on mobile, full-width when open ── */
    [data-testid="stSidebar"] {{
        min-width: 85vw !important;
        max-width: 85vw !important;
    }}

    /* ── Sidebar toggle button: bigger tap target ── */
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="collapsedControl"] button {{
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
    }}

    /* ── Page title sizing ── */
    h1 {{ font-size: 1.5rem !important; line-height: 1.3 !important; }}
    h2 {{ font-size: 1.25rem !important; }}
    h3 {{ font-size: 1.1rem !important; }}

    /* ── Metric cards: stack 2-per-row on mobile ── */
    [data-testid="metric-container"] {{
        padding: 10px 12px !important;
        min-width: 0 !important;
    }}
    [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        font-size: 1.2rem !important;
    }}
    [data-testid="metric-container"] [data-testid="stMetricLabel"] {{
        font-size: 0.72rem !important;
    }}

    /* ── Column layouts: force single column on very small screens ── */
    [data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.5rem !important;
    }}
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
        min-width: calc(50% - 0.5rem) !important;
        flex: 1 1 calc(50% - 0.5rem) !important;
    }}

    /* ── 4-column KPI rows: 2x2 grid ── */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)) > [data-testid="stColumn"] {{
        min-width: calc(50% - 0.5rem) !important;
        flex: 1 1 calc(50% - 0.5rem) !important;
    }}

    /* ── Buttons: full width, bigger tap targets ── */
    .stButton > button {{
        min-height: 44px !important;
        font-size: 0.9rem !important;
        padding: 10px 16px !important;
        width: 100% !important;
    }}

    /* ── Tabs: scrollable on mobile ── */
    [data-testid="stTabs"] [role="tablist"] {{
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
        scrollbar-width: none !important;
    }}
    [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {{
        display: none !important;
    }}
    [data-testid="stTabs"] [role="tab"] {{
        white-space: nowrap !important;
        min-width: fit-content !important;
        padding: 8px 12px !important;
        font-size: 0.82rem !important;
    }}

    /* ── Data tables: horizontal scroll ── */
    [data-testid="stDataFrame"] {{
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }}
    [data-testid="stDataFrame"] > div {{
        min-width: 0 !important;
    }}

    /* ── Charts: full width ── */
    [data-testid="stArrowVegaLiteChart"],
    [data-testid="stVegaLiteChart"] {{
        width: 100% !important;
        overflow-x: auto !important;
    }}

    /* ── Text inputs & selects: bigger touch targets ── */
    input[type="text"],
    input[type="email"],
    input[type="password"],
    input[type="number"],
    textarea,
    select {{
        font-size: 16px !important;  /* prevents iOS zoom on focus */
        min-height: 44px !important;
    }}
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea {{
        font-size: 16px !important;
        min-height: 44px !important;
    }}

    /* ── Selectbox ── */
    [data-testid="stSelectbox"] > div > div {{
        min-height: 44px !important;
        font-size: 0.9rem !important;
    }}

    /* ── Expanders ── */
    [data-testid="stExpander"] summary {{
        padding: 12px 16px !important;
        font-size: 0.9rem !important;
    }}

    /* ── Progress bars ── */
    [data-testid="stProgressBar"] {{
        height: 8px !important;
    }}

    /* ── Auth page: remove side padding on login form ── */
    .auth-center-col {{
        padding: 0 !important;
    }}

    /* ── Paywall card: tighter padding ── */
    .paywall-card {{
        padding: 20px 16px !important;
    }}

    /* ── Price cards: full width stacked ── */
    .price-card {{
        padding: 20px 16px !important;
        margin-bottom: 16px !important;
    }}
    .price-amount {{
        font-size: 2rem !important;
    }}

    /* ── Brand header in sidebar ── */
    .brand-name {{
        font-size: 1rem !important;
    }}

    /* ── Sidebar nav links: bigger tap targets ── */
    [data-testid="stSidebar"] a {{
        padding: 8px 4px !important;
        display: block !important;
        min-height: 40px !important;
        line-height: 40px !important;
    }}

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {{
        padding: 16px !important;
    }}
    [data-testid="stFileUploader"] label {{
        font-size: 0.9rem !important;
    }}

    /* ── Toast notifications ── */
    [data-testid="stToast"] {{
        max-width: 90vw !important;
        font-size: 0.85rem !important;
    }}

    /* ── Download button ── */
    [data-testid="stDownloadButton"] button {{
        width: 100% !important;
        min-height: 44px !important;
    }}

    /* ── Checkbox: bigger tap target ── */
    [data-testid="stCheckbox"] label {{
        min-height: 36px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }}

    /* ── Form submit buttons ── */
    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button {{
        min-height: 44px !important;
        width: 100% !important;
    }}

    /* ── Hide wide-layout padding ── */
    .appview-container .main {{
        padding: 0 !important;
    }}

    /* ── Reduce top header bar height ── */
    [data-testid="stHeader"] {{
        height: 3rem !important;
    }}
}}

/* ── Extra small screens (phones < 480px) ── */
@media (max-width: 480px) {{
    .main .block-container {{
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }}

    h1 {{ font-size: 1.3rem !important; }}

    /* ── Single column on very small screens for 4-col layouts ── */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"] {{
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }}

    [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        font-size: 1.05rem !important;
    }}

    /* ── Tabs: even smaller text ── */
    [data-testid="stTabs"] [role="tab"] {{
        font-size: 0.75rem !important;
        padding: 6px 8px !important;
    }}
}}
</style>
"""


def inject_css():
    """Inject global CSS + favicon meta tags once per session."""
    if not st.session_state.get("_css_injected"):
        st.html(GLOBAL_CSS)
        # Inject apple-touch-icon and favicon for iPhone "Add to Home Screen"
        st.html("""
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍑</text></svg>">
<link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍑</text></svg>">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Peach State">
<meta name="theme-color" content="#FF6B35">
""")
        st.session_state["_css_injected"] = True


def inject_soleops_css():
    """Inject SoleOps design system v2 — WCAG 2.1 AA, Inter font, contemporary SaaS + sneaker culture."""
    inject_css()
    if not st.session_state.get("_soleops_css_injected"):
        st.html("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   SOLEOPS DESIGN SYSTEM v2.0
   Contemporary SaaS + Sneaker Culture + WCAG 2.1 AA Accessible
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── CSS Custom Properties (Design Tokens) ──────────────────────────────── */
:root {
  --so-bg-primary:    #0A0B0F;
  --so-bg-secondary:  #111318;
  --so-bg-elevated:   #1A1D27;
  --so-bg-border:     #252836;

  --so-accent:        #00D4FF;
  --so-accent-2:      #7C3AED;
  --so-accent-warm:   #FF6B35;
  --so-success:       #22C55E;
  --so-danger:        #EF4444;
  --so-warning:       #F59E0B;

  --so-text-primary:  #F1F5F9;
  --so-text-secondary:#94A3B8;
  --so-text-muted:    #64748B;

  --so-radius-sm:     6px;
  --so-radius-md:     12px;
  --so-radius-lg:     16px;
  --so-radius-xl:     24px;
  --so-radius-full:   9999px;

  --so-shadow-md:     0 4px 16px rgba(0,0,0,0.5);
  --so-shadow-glow:   0 0 32px rgba(0,212,255,0.15);
  --so-transition:    0.2s cubic-bezier(0.4,0,0.2,1);

  /* Legacy compat vars */
  --sole-primary: #00D4FF;
  --sole-profit:  #22C55E;
  --sole-loss:    #EF4444;
  --sole-muted:   #94A3B8;
  --sole-card:    #111318;
  --sole-card2:   #1A1D27;
  --sole-border:  #252836;
}

/* ── ACCESSIBILITY: Skip Navigation ─────────────────────────────────────── */
.skip-nav {
  position: absolute; top: -40px; left: 16px;
  background: var(--so-accent); color: var(--so-bg-primary);
  padding: 8px 16px; border-radius: var(--so-radius-md);
  font-weight: 700; font-size: 0.9rem; z-index: 10000;
  text-decoration: none; transition: top var(--so-transition);
}
.skip-nav:focus { top: 8px; outline: 3px solid var(--so-accent); outline-offset: 2px; }

/* ── ACCESSIBILITY: Focus Styles (WCAG 2.4.7) ───────────────────────────── */
*:focus-visible {
  outline: 2px solid var(--so-accent) !important;
  outline-offset: 2px !important;
  border-radius: var(--so-radius-sm) !important;
}
*:focus:not(:focus-visible) { outline: none !important; }

/* ── Base App Styles ─────────────────────────────────────────────────────── */
.stApp, html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main, .main, .block-container, .appview-container {
  background-color: var(--so-bg-primary) !important;
  color: var(--so-text-primary) !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  font-size: 16px !important;
  line-height: 1.6 !important;
  -webkit-font-smoothing: antialiased;
}

/* ── Typography ──────────────────────────────────────────────────────────── */
h1 {
  font-size: clamp(1.75rem, 4vw, 2.5rem) !important;
  font-weight: 800 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.15 !important;
  background: linear-gradient(135deg, var(--so-accent), var(--so-accent-2)) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  background-clip: text !important;
}
h2 {
  font-size: clamp(1.25rem, 3vw, 1.75rem) !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
  color: var(--so-text-primary) !important;
  -webkit-text-fill-color: var(--so-text-primary) !important;
  background: none !important;
  line-height: 1.25 !important;
}
h3, h4 {
  font-size: 1.1rem !important;
  font-weight: 600 !important;
  color: var(--so-text-secondary) !important;
  -webkit-text-fill-color: var(--so-text-secondary) !important;
  background: none !important;
}
p, .stMarkdown p { color: var(--so-text-secondary) !important; line-height: 1.7 !important; }
span, li, label { color: var(--so-text-primary) !important; }
td, th { color: var(--so-text-primary) !important; }
hr { border-color: var(--so-bg-border) !important; }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"], [data-testid="stSidebar"]>div {
  background: linear-gradient(180deg, var(--so-bg-secondary) 0%, var(--so-bg-primary) 100%) !important;
  border-right: 1px solid var(--so-bg-border) !important;
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: var(--so-text-secondary) !important; font-size: 0.875rem !important; }
[data-testid="stSidebar"] a { color: var(--so-accent) !important; }
[data-testid="stHeader"] { background: var(--so-bg-primary) !important; border-bottom: 1px solid var(--so-bg-border) !important; }

/* ── Metric Cards ────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
  background: var(--so-bg-secondary) !important;
  border: 1px solid var(--so-bg-border) !important;
  border-radius: var(--so-radius-lg) !important;
  box-shadow: var(--so-shadow-md) !important;
  transition: transform var(--so-transition), box-shadow var(--so-transition), border-color var(--so-transition) !important;
}
[data-testid="metric-container"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: var(--so-shadow-glow) !important;
  border-color: rgba(0,212,255,0.3) !important;
}
[data-testid="stMetricValue"] { color: var(--so-accent) !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] { color: var(--so-text-muted) !important; font-size: 0.8rem !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }
[data-testid="stMetricDelta"][data-direction="up"] span { color: #4ADE80 !important; }
[data-testid="stMetricDelta"][data-direction="down"] span { color: #F87171 !important; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton>button {
  font-family: 'Inter', sans-serif !important;
  font-weight: 700 !important;
  border-radius: var(--so-radius-full) !important;
  font-size: 0.9rem !important;
  padding: 10px 24px !important;
  min-height: 44px !important;
  transition: all var(--so-transition) !important;
  letter-spacing: 0.01em !important;
}
.stButton>button[kind="primary"] {
  background: linear-gradient(135deg, var(--so-accent) 0%, #0099CC 100%) !important;
  color: var(--so-bg-primary) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(0,212,255,0.3) !important;
}
.stButton>button[kind="primary"]:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 16px rgba(0,212,255,0.4) !important;
  filter: brightness(1.05) !important;
}
.stButton>button:not([kind="primary"]) {
  background: transparent !important;
  color: var(--so-text-primary) !important;
  border: 1.5px solid var(--so-bg-border) !important;
  box-shadow: none !important;
}
.stButton>button:not([kind="primary"]):hover {
  border-color: var(--so-accent) !important;
  color: var(--so-accent) !important;
  box-shadow: 0 0 12px rgba(0,212,255,0.15) !important;
}
.stButton>button:focus-visible {
  outline: 2px solid var(--so-accent) !important;
  outline-offset: 3px !important;
}

/* ── Form Inputs ─────────────────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  background-color: var(--so-bg-elevated) !important;
  border: 1.5px solid var(--so-bg-border) !important;
  border-radius: var(--so-radius-md) !important;
  color: var(--so-text-primary) !important;
  font-size: 0.95rem !important;
  padding: 10px 14px !important;
  min-height: 44px !important;
  transition: border-color var(--so-transition), box-shadow var(--so-transition) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
  border-color: var(--so-accent) !important;
  box-shadow: 0 0 0 3px rgba(0,212,255,0.15) !important;
  outline: none !important;
}
.stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label {
  color: var(--so-text-secondary) !important;
  font-size: 0.875rem !important;
  font-weight: 600 !important;
}
.stSelectbox [data-baseweb="select"]>div {
  background: var(--so-bg-elevated) !important;
  border: 1.5px solid var(--so-bg-border) !important;
  border-radius: var(--so-radius-md) !important;
  color: var(--so-text-primary) !important;
  min-height: 44px !important;
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"], [data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--so-bg-secondary) !important;
  border-radius: var(--so-radius-lg) !important;
  padding: 4px !important;
  border: 1px solid var(--so-bg-border) !important;
}
.stTabs [data-baseweb="tab"], [data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: var(--so-radius-md) !important;
  color: var(--so-text-muted) !important;
  font-weight: 500 !important;
  font-size: 0.875rem !important;
  min-height: 38px !important;
  border: none !important;
  transition: all var(--so-transition) !important;
}
.stTabs [aria-selected="true"], [data-testid="stTabs"] [aria-selected="true"] {
  background: var(--so-bg-elevated) !important;
  color: var(--so-accent) !important;
  font-weight: 700 !important;
  box-shadow: var(--so-shadow-md) !important;
  border-bottom: 2px solid var(--so-accent) !important;
}

/* ── Data Tables ─────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: var(--so-radius-lg) !important; overflow: hidden !important; border: 1px solid var(--so-bg-border) !important; }
[data-testid="stDataFrame"], thead, tbody, tr { background: var(--so-bg-secondary) !important; color: var(--so-text-primary) !important; }
th { color: var(--so-accent) !important; font-weight: 700 !important; background: var(--so-bg-elevated) !important; border-color: var(--so-bg-border) !important; }
td { border-color: var(--so-bg-border) !important; }

/* ── Progress ────────────────────────────────────────────────────────────── */
[data-testid="stProgressBar"]>div>div { background: linear-gradient(90deg, var(--so-accent), var(--so-accent-2)) !important; border-radius: var(--so-radius-full) !important; }
[data-testid="stProgressBar"]>div { background: var(--so-bg-border) !important; border-radius: var(--so-radius-full) !important; }

/* ── Alerts ──────────────────────────────────────────────────────────────── */
.stSuccess { background: rgba(34,197,94,0.1) !important; border-color: rgba(34,197,94,0.4) !important; color: #BBF7D0 !important; border-radius: var(--so-radius-md) !important; }
.stError   { background: rgba(239,68,68,0.1) !important; border-color: rgba(239,68,68,0.4) !important; color: #FECACA !important; border-radius: var(--so-radius-md) !important; }
.stWarning { background: rgba(245,158,11,0.1) !important; border-color: rgba(245,158,11,0.4) !important; color: #FDE68A !important; border-radius: var(--so-radius-md) !important; }
.stInfo    { background: rgba(0,212,255,0.08) !important; border-color: rgba(0,212,255,0.3) !important; color: #BAE6FD !important; border-radius: var(--so-radius-md) !important; }

/* ── Expanders ───────────────────────────────────────────────────────────── */
.streamlit-expanderHeader, [data-testid="stExpander"] {
  background: var(--so-bg-secondary) !important;
  border: 1px solid var(--so-bg-border) !important;
  border-radius: var(--so-radius-md) !important;
  color: var(--so-text-primary) !important;
  font-weight: 600 !important;
}
.streamlit-expanderHeader:hover { border-color: var(--so-accent) !important; }

/* ── Legacy sole-* utility classes (backward compat) ────────────────────── */
.sole-signal-buy { background: rgba(34,197,94,0.08) !important; border: 1px solid var(--so-success) !important; border-radius: var(--so-radius-md) !important; padding: 12px 16px !important; color: #4ADE80 !important; }
.sole-signal-hold { background: rgba(239,68,68,0.08) !important; border: 1px solid var(--so-danger) !important; border-radius: var(--so-radius-md) !important; padding: 12px 16px !important; color: #F87171 !important; }
.sole-pnl-positive { color: #4ADE80 !important; font-weight: 700 !important; }
.sole-pnl-negative { color: #F87171 !important; font-weight: 700 !important; }
.sole-card, .so-card {
  background: var(--so-bg-secondary) !important;
  border: 1px solid var(--so-bg-border) !important;
  border-radius: var(--so-radius-lg) !important;
  padding: 1.5rem !important;
  margin-bottom: 1rem !important;
  transition: transform var(--so-transition), box-shadow var(--so-transition), border-color var(--so-transition) !important;
  position: relative; overflow: hidden;
}
.sole-card:hover, .so-card:hover {
  transform: translateY(-2px) !important;
  box-shadow: var(--so-shadow-glow) !important;
  border-color: rgba(0,212,255,0.3) !important;
}

/* ── Status Badges ───────────────────────────────────────────────────────── */
.so-badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: var(--so-radius-full); font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.so-badge-success { background: rgba(34,197,94,0.15); color: #4ADE80; }
.so-badge-danger  { background: rgba(239,68,68,0.15); color: #F87171; }
.so-badge-warning { background: rgba(245,158,11,0.15); color: #FCD34D; }
.so-badge-info    { background: rgba(0,212,255,0.15); color: #67E8F9; }

/* ── Live Ticker ─────────────────────────────────────────────────────────── */
.so-ticker { display: flex; align-items: center; gap: 6px; background: rgba(0,212,255,0.08); border: 1px solid rgba(0,212,255,0.2); border-radius: var(--so-radius-full); padding: 6px 14px; font-size: 0.8rem; font-weight: 600; color: var(--so-accent); }
.so-ticker-dot { width: 6px; height: 6px; background: var(--so-success); border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(0.8); } }

/* ── Pricing Cards ───────────────────────────────────────────────────────── */
.so-pricing-card { background: var(--so-bg-secondary); border: 1px solid var(--so-bg-border); border-radius: var(--so-radius-xl); padding: 32px 28px; text-align: center; transition: all var(--so-transition); position: relative; overflow: hidden; }
.so-pricing-card.featured { border-color: var(--so-accent); box-shadow: var(--so-shadow-glow); }
.so-pricing-card.featured::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--so-accent), var(--so-accent-2)); }
.so-price-amount { font-size: 3rem; font-weight: 900; color: var(--so-text-primary); letter-spacing: -0.04em; line-height: 1; }
.so-price-period { color: var(--so-text-muted); font-size: 0.875rem; }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--so-bg-primary); }
::-webkit-scrollbar-thumb { background: var(--so-bg-border); border-radius: var(--so-radius-full); }
::-webkit-scrollbar-thumb:hover { background: var(--so-text-muted); }

/* ── Reduced Motion ──────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}

/* ── Mobile ──────────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  h1 { font-size: 1.75rem !important; }
  .so-pricing-card { padding: 24px 20px; }
  .so-price-amount { font-size: 2.5rem; }
}

/* ── Print ───────────────────────────────────────────────────────────────── */
@media print {
  .stSidebar, .stButton, .so-ticker { display: none !important; }
  .stApp { background: white !important; color: black !important; }
  h1, h2, h3 { color: black !important; -webkit-text-fill-color: black !important; }
}
</style>
""")
        st.session_state["_soleops_css_injected"] = True


def inject_cc_css():
    """Inject College Confused brand CSS — dark midnight-purple theme.
    Dark-over-dark swap is 100% reliable in Streamlit.
    Palette: midnight purple bg + bright lavender headings + coral + teal."""
    inject_css()
    if not st.session_state.get("_cc_css_injected"):
        st.html("""
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ── CC Palette ── */
:root{--cc-bg:#12102A;--cc-card:#1C1A3A;--cc-card2:#252248;--cc-border:#3A3560;--cc-primary:#9B8EFF;--cc-coral:#FF7A5C;--cc-teal:#4ECDC4;--cc-gold:#FFD166;--cc-text:#F0EEFF;--cc-muted:#8B7FD4;--cc-sidebar:#16143A;}
/* ── Base layer ── */
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],section.main,.main,.block-container,.appview-container{background-color:var(--cc-bg)!important;color:var(--cc-text)!important;font-family:'Plus Jakarta Sans',-apple-system,sans-serif!important;}
/* ── Headings ── */
h1{background:linear-gradient(90deg,var(--cc-primary) 0%,var(--cc-coral) 100%)!important;-webkit-background-clip:text!important;-webkit-text-fill-color:transparent!important;background-clip:text!important;font-weight:800!important;}
h2{color:var(--cc-text)!important;-webkit-text-fill-color:var(--cc-text)!important;background:none!important;font-weight:700!important;}
h3,h4{color:var(--cc-muted)!important;-webkit-text-fill-color:var(--cc-muted)!important;background:none!important;}
p,span,li,td,th,label{color:var(--cc-text)!important;}
/* ── Sidebar ── */
[data-testid="stSidebar"],[data-testid="stSidebar"]>div{background:linear-gradient(180deg,#0E0C24 0%,var(--cc-sidebar) 100%)!important;border-right:1px solid var(--cc-border)!important;}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label{color:var(--cc-muted)!important;}
[data-testid="stSidebar"] a{color:var(--cc-primary)!important;}
[data-testid="stHeader"]{background:var(--cc-bg)!important;border-bottom:1px solid var(--cc-border)!important;}
/* ── Metric cards ── */
[data-testid="metric-container"]{background:var(--cc-card)!important;border:1px solid rgba(155,142,255,0.2)!important;border-radius:16px!important;box-shadow:0 4px 24px rgba(155,142,255,0.08)!important;transition:all 0.2s ease!important;}
[data-testid="metric-container"]:hover{border-color:rgba(155,142,255,0.4)!important;box-shadow:0 8px 32px rgba(155,142,255,0.15)!important;transform:translateY(-2px)!important;}
[data-testid="stMetricValue"]{color:var(--cc-primary)!important;font-weight:700!important;}
[data-testid="stMetricLabel"]{color:var(--cc-muted)!important;}
[data-testid="stMetricDelta"][data-direction="up"] span{color:var(--cc-teal)!important;}
[data-testid="stMetricDelta"][data-direction="down"] span{color:var(--cc-coral)!important;}
/* ── Buttons ── */
.stButton>button{font-family:'Plus Jakarta Sans',sans-serif!important;border-radius:50px!important;font-weight:700!important;transition:all 0.2s ease!important;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,var(--cc-primary) 0%,#C084FC 100%)!important;color:#0E0C24!important;border:none!important;box-shadow:0 4px 16px rgba(155,142,255,0.3)!important;}
.stButton>button[kind="primary"]:hover{transform:translateY(-2px)!important;box-shadow:0 8px 28px rgba(155,142,255,0.45)!important;}
.stButton>button:not([kind="primary"]){background:var(--cc-card2)!important;color:var(--cc-primary)!important;border:1px solid rgba(155,142,255,0.35)!important;}
/* ── Inputs ── */
.stTextInput input,.stNumberInput input,.stTextArea textarea{background:var(--cc-card)!important;border:1px solid var(--cc-border)!important;border-radius:12px!important;color:var(--cc-text)!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{border-color:var(--cc-primary)!important;box-shadow:0 0 0 3px rgba(155,142,255,0.15)!important;}
.stSelectbox [data-baseweb="select"]>div{background:var(--cc-card)!important;border:1px solid var(--cc-border)!important;border-radius:12px!important;color:var(--cc-text)!important;}
/* ── Tables ── */
[data-testid="stDataFrame"],thead,tbody,tr{background:var(--cc-card)!important;color:var(--cc-text)!important;}
td,th{border-color:var(--cc-border)!important;color:var(--cc-text)!important;}
th{color:var(--cc-primary)!important;font-weight:700!important;background:var(--cc-card2)!important;}
/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:var(--cc-card)!important;border-bottom:1px solid var(--cc-border)!important;border-radius:12px 12px 0 0!important;}
[data-testid="stTabs"] [data-baseweb="tab"]{color:var(--cc-muted)!important;font-weight:500!important;}
[data-testid="stTabs"] [aria-selected="true"]{color:var(--cc-primary)!important;border-bottom:3px solid var(--cc-primary)!important;font-weight:700!important;}
/* ── Progress ── */
[data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,var(--cc-primary),var(--cc-teal))!important;border-radius:8px!important;}
[data-testid="stProgressBar"]>div{background:var(--cc-border)!important;border-radius:8px!important;}
/* ── Expanders ── */
[data-testid="stExpander"]{background:var(--cc-card)!important;border:1px solid var(--cc-border)!important;border-radius:12px!important;}
hr{border-color:var(--cc-border)!important;}
/* ── CC utility classes ── */
.cc-hero{background:linear-gradient(135deg,#1C1048 0%,#2A1060 50%,#1A2A4A 100%)!important;border:1px solid rgba(155,142,255,0.25)!important;border-radius:20px!important;padding:2.5rem!important;text-align:center!important;margin-bottom:2rem!important;box-shadow:0 8px 40px rgba(155,142,255,0.15)!important;}
.cc-hero h1{background:linear-gradient(90deg,var(--cc-primary),var(--cc-coral))!important;-webkit-background-clip:text!important;-webkit-text-fill-color:transparent!important;background-clip:text!important;}
.cc-card{background:var(--cc-card)!important;border:1px solid rgba(155,142,255,0.15)!important;border-radius:16px!important;padding:1.5rem!important;margin-bottom:1rem!important;transition:all 0.2s ease!important;box-shadow:0 4px 20px rgba(0,0,0,0.3)!important;}
.cc-card:hover{border-color:rgba(155,142,255,0.35)!important;box-shadow:0 8px 32px rgba(155,142,255,0.12)!important;transform:translateY(-2px)!important;}
.cc-stat{text-align:center!important;padding:1.5rem!important;background:var(--cc-card)!important;border-radius:16px!important;border:1px solid rgba(155,142,255,0.15)!important;}
.cc-stat .number{font-size:2.5rem!important;font-weight:800!important;color:var(--cc-primary)!important;}
.cc-stat .label{color:var(--cc-muted)!important;font-size:0.9rem!important;}
.cc-badge{display:inline-block!important;background:linear-gradient(135deg,var(--cc-gold),#F4A261)!important;color:#1A0A00!important;border-radius:50px!important;padding:0.25rem 0.85rem!important;font-weight:700!important;font-size:0.8rem!important;}
.cc-badge-purple{display:inline-block!important;background:rgba(155,142,255,0.15)!important;color:var(--cc-primary)!important;border:1px solid rgba(155,142,255,0.4)!important;border-radius:50px!important;padding:0.25rem 0.85rem!important;font-weight:600!important;font-size:0.8rem!important;}
.cc-scholarship-amount{color:var(--cc-teal)!important;font-size:1.6rem!important;font-weight:800!important;}
.cc-timeline-step{border-left:3px solid var(--cc-primary)!important;padding-left:1.25rem!important;margin-bottom:1.25rem!important;}
.cc-timeline-step.done{border-color:var(--cc-teal)!important;}
.cc-timeline-step.upcoming{border-color:var(--cc-coral)!important;}
</style>
""")
        st.session_state["_cc_css_injected"] = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_lockout(seconds: int) -> str:
    mins = math.ceil(seconds / 60)
    return f"{mins} minute{'s' if mins != 1 else ''}"


# ── Auth pages ────────────────────────────────────────────────────────────────

def _legacy_password_check():
    """Single-password gate for beta / personal use."""
    app_pw = os.environ.get("APP_PASSWORD", "") or get_setting("app_password", "")
    if not app_pw:
        return
    if st.session_state.get("authenticated"):
        return

    inject_css()
    st.markdown(f"""
    <div style="text-align:center; padding:60px 0 24px 0;">
        <div style="font-size:2.4rem; font-weight:800; color:{PEACH}; letter-spacing:-0.03em;">
            {APP_EMOJI} {APP_NAME}
        </div>
        <div style="color:{TEXT_MUTED}; font-size:0.9rem; margin-top:6px;">
            Your personal finance dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pw = st.text_input("Password", type="password", placeholder="Enter password...")
        if st.button("Enter", type="primary", use_container_width=True):
            if pw == app_pw:
                st.session_state["authenticated"] = True
                st.session_state["user"] = {
                    "email": "owner", "plan": "pro",
                    "subscription_status": "active", "id": 0
                }
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()


def _show_auth_page():
    """Full register/login UI with security hardening."""
    inject_css()

    # Hide sidebar entirely on login page — unauthenticated visitors
    # should not see the full page list
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    button[kind="header"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:center; padding: 48px 0 24px 0;">
        <div style="font-size:2.4rem; font-weight:800; color:{PEACH}; letter-spacing:-0.03em;">
            {APP_EMOJI} {APP_NAME}
        </div>
        <div style="color:{TEXT_MUTED}; font-size:0.95rem; margin-top:8px;">
            AI-powered personal finance
        </div>
    </div>
    <style>
    /* On mobile, make the auth form full-width */
    @media (max-width: 768px) {{
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {{
            display: none !important;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {{
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── Sign In ───────────────────────────────────────────────────────────
        with tab_login:
            st.markdown("#### Welcome back")
            email    = st.text_input("Email", key="login_email",
                                     placeholder="you@email.com",
                                     max_chars=254)
            password = st.text_input("Password", type="password", key="login_pw",
                                     placeholder="••••••••",
                                     max_chars=128)

            if st.button("Sign In", type="primary", use_container_width=True,
                         key="btn_login"):
                email_clean = (email or "").strip().lower()

                # Input validation
                if not email_clean or not password:
                    st.error("Please enter your email and password.")
                elif not validate_email(email_clean):
                    st.error("Please enter a valid email address.")
                else:
                    # Check lockout BEFORE hitting the DB
                    locked, remaining = is_account_locked(email_clean)
                    if locked:
                        st.error(
                            f"🔒 Too many failed attempts. "
                            f"Please wait {_fmt_lockout(remaining)} before trying again."
                        )
                    else:
                        user = authenticate_user(email_clean, password)
                        if user:
                            set_active_db(user.get("email"))
                            st.session_state["user"] = user
                            st.session_state["authenticated"] = True
                            st.rerun()
                        else:
                            # Check again after the failed attempt to show updated count
                            locked2, remaining2 = is_account_locked(email_clean)
                            if locked2:
                                st.error(
                                    f"🔒 Account temporarily locked after too many failed attempts. "
                                    f"Try again in {_fmt_lockout(remaining2)}."
                                )
                            else:
                                st.error("Invalid email or password.")

        # ── Register ──────────────────────────────────────────────────────────
        with tab_register:
            st.markdown("#### Create your free account")
            st.caption(
                "Free plan: budgeting, expenses, income tracking, bank import. "
                "No credit card required."
            )
            reg_email = st.text_input("Email", key="reg_email",
                                      placeholder="you@email.com",
                                      max_chars=254)
            reg_pw    = st.text_input("Password", type="password", key="reg_pw",
                                      placeholder="8+ chars, letters and numbers",
                                      max_chars=128)
            reg_pw2   = st.text_input("Confirm Password", type="password",
                                      key="reg_pw2",
                                      placeholder="Repeat password",
                                      max_chars=128)

            # Live password strength hint
            if reg_pw:
                ok, msg = validate_password(reg_pw)
                if not ok:
                    st.caption(f"⚠️ {msg}")
                else:
                    st.caption("✅ Password looks good")

            if st.button("Create Account", type="primary",
                         use_container_width=True, key="btn_register"):
                email_clean = (reg_email or "").strip().lower()

                if not email_clean or not reg_pw:
                    st.error("Email and password are required.")
                elif not validate_email(email_clean):
                    st.error("Please enter a valid email address.")
                else:
                    ok, pw_msg = validate_password(reg_pw)
                    if not ok:
                        st.error(pw_msg)
                    elif reg_pw != reg_pw2:
                        st.error("Passwords don't match.")
                    else:
                        user = create_user(email_clean, reg_pw)
                        if user:
                            st.session_state["user"] = user
                            st.session_state["authenticated"] = True
                            _send_welcome_email(email_clean)  # fire-and-forget
                            st.success(f"Account created! Welcome to {APP_NAME} {APP_EMOJI}")
                            st.rerun()
                        else:
                            st.error(
                                "An account with that email already exists. "
                                "Try signing in instead."
                            )

    st.markdown(
        f"<div style='text-align:center; margin-top:20px; color:{TEXT_MUTED}; "
        f"font-size:0.75rem;'>"
        "Your financial data is encrypted and never shared.</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<div style='text-align:center; margin-top:12px;'>"
        f"<a href='/landing' target='_self' style='color:{PEACH}; "
        f"font-size:0.82rem; text-decoration:none;'>"
        "← What is Peach State Savings?</a></div>",
        unsafe_allow_html=True
    )

    st.stop()


# ── Welcome Email ─────────────────────────────────────────────────────────────

def _send_welcome_email(email: str):
    """
    Send a welcome email to new registrants via Gmail SMTP.
    Fire-and-forget — runs in a background thread, never blocks the UI.
    Silently skips if gmail credentials aren't configured.
    """
    import threading

    def _send():
        try:
            gmail_user = get_setting("gmail_user")
            gmail_pass = get_setting("gmail_app_password")
            if not gmail_user or not gmail_pass:
                return
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText as _MIMEText

            app_url = os.environ.get("APP_URL", "https://peachstatesavings.com")

            html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#0e1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:40px 24px;">

    <!-- Header -->
    <div style="text-align:center;padding:32px 0 24px;">
      <div style="font-size:2.5rem;">🍑</div>
      <h1 style="color:#FFAB76;font-size:1.8rem;font-weight:800;margin:8px 0 4px;letter-spacing:-0.02em;">
        Welcome to Peach State Savings
      </h1>
      <p style="color:#8892a4;font-size:0.95rem;margin:0;">
        Your AI-powered personal finance dashboard is ready.
      </p>
    </div>

    <!-- Main Card -->
    <div style="background:#12151c;border:1px solid #1e2330;border-radius:16px;padding:32px;margin-bottom:24px;">
      <p style="color:#fafafa;font-size:1rem;margin:0 0 20px;">
        Hey there 👋 — your <strong style="color:#FFAB76;">free account</strong> is all set.
        Here's what you can do right now:
      </p>

      <div style="margin-bottom:24px;">
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="color:#FFAB76;font-weight:700;margin-right:8px;flex-shrink:0;">✓</span>
          <span style="color:#c8d0dc;font-size:0.9rem;"><strong style="color:#fafafa;">Budget Tracking</strong> — Log expenses, income, and see where your money goes</span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="color:#FFAB76;font-weight:700;margin-right:8px;flex-shrink:0;">✓</span>
          <span style="color:#c8d0dc;font-size:0.9rem;"><strong style="color:#fafafa;">Bank Import</strong> — Upload CSV statements to auto-categorize transactions</span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="color:#FFAB76;font-weight:700;margin-right:8px;flex-shrink:0;">✓</span>
          <span style="color:#c8d0dc;font-size:0.9rem;"><strong style="color:#fafafa;">Financial Goals</strong> — Set and track savings targets</span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="color:#FFAB76;font-weight:700;margin-right:8px;flex-shrink:0;">✓</span>
          <span style="color:#c8d0dc;font-size:0.9rem;"><strong style="color:#fafafa;">Bill Calendar</strong> — Never miss a bill payment again</span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="color:#FFAB76;font-weight:700;margin-right:8px;flex-shrink:0;">✓</span>
          <span style="color:#c8d0dc;font-size:0.9rem;"><strong style="color:#fafafa;">Paycheck Calculator</strong> — See your exact take-home after taxes</span>
        </div>
        <div style="display:flex;align-items:flex-start;">
          <span style="color:#FFAB76;font-weight:700;margin-right:8px;flex-shrink:0;">✓</span>
          <span style="color:#c8d0dc;font-size:0.9rem;"><strong style="color:#fafafa;">SoleOps Reseller Tools</strong> — Sneaker inventory, P&amp;L, arbitrage scanner</span>
        </div>
      </div>

      <!-- CTA Button -->
      <div style="text-align:center;margin-top:28px;">
        <a href="{app_url}"
           style="display:inline-block;background:linear-gradient(135deg,#FFAB76,#e8924f);
                  color:#000;font-weight:700;font-size:1rem;padding:14px 36px;
                  border-radius:10px;text-decoration:none;letter-spacing:-0.01em;">
          Open My Dashboard →
        </a>
      </div>
    </div>

    <!-- Pro Upsell -->
    <div style="background:linear-gradient(135deg,#3d2010 0%,#12151c 100%);
                border:1px solid #FFAB76;border-radius:12px;padding:24px;margin-bottom:24px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
        <span style="font-size:1.2rem;">⭐</span>
        <strong style="color:#FFAB76;font-size:1rem;">Unlock the full platform for $4.99/mo</strong>
      </div>
      <p style="color:#8892a4;font-size:0.85rem;margin:0 0 12px;">
        Pro adds AI insights, net worth tracking, RSU/ESPP tools, portfolio analytics,
        monthly financial reports, and 60+ advanced features.
      </p>
      <a href="{app_url}/pricing"
         style="color:#FFAB76;font-size:0.85rem;font-weight:600;text-decoration:none;">
        View Pro features →
      </a>
    </div>

    <!-- Footer -->
    <div style="text-align:center;color:#4a5568;font-size:0.78rem;padding-top:16px;">
      <p style="margin:0 0 4px;">Peach State Savings · Atlanta, GA</p>
      <p style="margin:0;">Questions? Reply to this email or visit
        <a href="{app_url}" style="color:#FFAB76;">peachstatesavings.com</a>
      </p>
    </div>

  </div>
</body>
</html>"""

            # Plain text fallback
            text = f"""Welcome to Peach State Savings! 🍑

Your free account is ready. Here's what you can do:

✓ Budget Tracking — Log expenses, income, and see where your money goes
✓ Bank Import — Upload CSV statements to auto-categorize transactions
✓ Financial Goals — Set and track savings targets
✓ Bill Calendar — Never miss a bill payment again
✓ Paycheck Calculator — See your exact take-home after taxes
✓ SoleOps Reseller Tools — Sneaker inventory, P&L, arbitrage scanner

Open your dashboard: {app_url}

Want more? Upgrade to Pro for $4.99/mo — AI insights, net worth tracking,
RSU/ESPP tools, 60+ advanced features.

— The Peach State Savings Team
"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = "🍑 Welcome to Peach State Savings!"
            msg["From"]    = f"Peach State Savings <{gmail_user}>"
            msg["To"]      = email

            msg.attach(_MIMEText(text, "plain"))
            msg.attach(_MIMEText(html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_pass)
                server.send_message(msg)

        except Exception:
            pass  # Email is best-effort — never block signup

    threading.Thread(target=_send, daemon=True).start()


# ── Public API ────────────────────────────────────────────────────────────────

def require_login():
    """
    Gate: user must be logged in to proceed.
    Handles both legacy (APP_PASSWORD) and multi-user modes.
    Always call this at the top of every page after set_page_config.
    """
    inject_css()
    init_db()

    app_pw     = os.environ.get("APP_PASSWORD", "") or get_setting("app_password", "")
    multi_user = os.environ.get("MULTI_USER", "true").lower() not in ("false", "0", "no")

    if app_pw and not multi_user:
        _legacy_password_check()
        return

    if st.session_state.get("authenticated") and st.session_state.get("user"):
        user = st.session_state["user"]
        # Route this session to the user's isolated data DB
        set_active_db(user.get("email"))
        # Ensure the user's per-user DB has all tables created
        init_db()
        # Refresh from shared auth DB to pick up subscription changes
        if user.get("id", 0) != 0:
            fresh = get_user_by_id(user["id"])
            if fresh:
                fresh.pop("password_hash", None)
                fresh.pop("salt", None)
                st.session_state["user"] = fresh
        return

    _show_auth_page()


def require_password():
    """Alias for require_login() — keeps old page imports working."""
    require_login()


def get_current_user() -> dict | None:
    """Return the currently logged-in user dict, or None."""
    return st.session_state.get("user")


def current_user_is_pro() -> bool:
    """Return True if the current session user has an active Pro plan."""
    return is_pro_user(get_current_user())


def is_sovereign_user(user: dict | None) -> bool:
    """Return True if user is on the invite-only Sovereign plan."""
    if not user:
        return False
    plan   = user.get("plan", "free")
    status = user.get("subscription_status", "")
    # sovereign users always have full access regardless of stripe status
    return plan == "sovereign"


def current_user_is_sovereign() -> bool:
    """Return True if current session is on the Sovereign plan."""
    return is_sovereign_user(get_current_user())


# Sovereign emails — Darrian grants these manually
SOVEREIGN_OWNER_EMAIL = "darrianbelcher@gmail.com"


def require_pro(feature_name: str = "this feature"):
    """
    Gate: show a paywall if the user is not on Pro.
    Call after require_login(). Stops page execution if not Pro.
    """
    if current_user_is_pro():
        return

    inject_css()
    user  = get_current_user()
    email = user.get("email", "") if user else ""

    st.markdown(f"""
    <div class="paywall-card">
        <h2>🔒 Pro Feature</h2>
        <p>
            <strong>{feature_name}</strong> is available on the
            <strong>{APP_NAME} Pro</strong> plan.<br>
            Upgrade for $4.99/month to unlock AI insights, trends analysis,
            and net worth tracking.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        from utils.stripe_utils import create_checkout_session, is_sandbox_mode, stripe_enabled_for
        sandbox = is_sandbox_mode(email)
        if sandbox:
            st.markdown(
                "<div style='background:#1a2a1a; border:1px solid #3a6b3a; border-radius:8px; "
                "padding:8px 12px; margin-bottom:10px; font-size:0.78rem; color:#7ec87e;'>"
                "🧪 <strong>Sandbox mode</strong> — Stripe test keys active. "
                "Use card <code>4242 4242 4242 4242</code>, any future date &amp; CVC.</div>",
                unsafe_allow_html=True
            )
        btn_label = "🧪 Test Checkout — $4.99/month" if sandbox else "🚀 Upgrade to Pro — $4.99/month"
        if st.button(btn_label, type="primary",
                     use_container_width=True, key="paywall_upgrade_btn"):
            if stripe_enabled_for(email) and user and user.get("id", 0) != 0:
                url = create_checkout_session(email, user["id"])
                if url:
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url={url}">',
                        unsafe_allow_html=True
                    )
                    st.markdown(f"[Click here if not redirected]({url})")
                else:
                    st.error("Could not create checkout session. Please try again.")
            else:
                st.switch_page("pages/0_pricing.py")

        footer = "🧪 Test mode — no real charge" if sandbox else "Cancel anytime · Secure payment via Stripe"
        st.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.8rem; margin-top:8px;'>"
            f"{footer}</div>",
            unsafe_allow_html=True
        )

    st.stop()


def render_sidebar_brand():
    """Render the Peach State Savings brand header in the sidebar."""
    inject_css()
    st.sidebar.markdown(f"""
    <div class="brand-header">
        <div>
            <div class="brand-name">{APP_EMOJI} {APP_NAME}</div>
            <div class="brand-tagline">AI-powered budgeting</div>
            <div style="margin-top:5px;">
                <span style="
                    font-size:0.62rem;
                    font-weight:700;
                    color:#FFB300;
                    letter-spacing:0.06em;
                    text-transform:uppercase;
                    opacity:0.85;
                ">🐾 Aggie Built · NC A&T</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_nav():
    """
    Render navigation links based on user plan.
    Free users see only free-tier pages.
    Pro users see free pages + all Pro pages.
    Call this after render_sidebar_brand() and before render_sidebar_user_widget().
    """
    pro = current_user_is_pro()
    st.sidebar.markdown("---")

    # ── Free-tier pages (visible to everyone) ─────────────────────────────────
    st.sidebar.page_link("app.py",                 label="📊 Overview")
    st.sidebar.page_link("pages/1_expenses.py",    label="📋 Expenses")
    st.sidebar.page_link("pages/2_income.py",      label="💵 Income")
    st.sidebar.page_link("pages/5_bank_import.py", label="🏦 Bank Import")
    st.sidebar.page_link("pages/8_goals.py",       label="🎯 Financial Goals")
    st.sidebar.page_link("pages/15_bills.py",      label="📅 Bill Calendar")
    st.sidebar.page_link("pages/16_paycheck.py",   label="💸 Paycheck")

    if pro:
        # ── Pro-only pages ─────────────────────────────────────────────────────
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            f"<div style='font-size:0.72rem; color:{TEXT_MUTED}; text-transform:uppercase; "
            f"letter-spacing:0.06em; padding:4px 0 2px 4px;'>⭐ Pro</div>",
            unsafe_allow_html=True
        )
        st.sidebar.page_link("pages/3_business_tracker.py", label="💼 Business Tracker")
        st.sidebar.page_link("pages/4_trends.py",            label="📈 Monthly Trends")
        st.sidebar.page_link("pages/6_receipts.py",          label="🧾 Receipts & HSA")
        st.sidebar.page_link("pages/7_ai_insights.py",       label="🤖 AI Insights")
        st.sidebar.page_link("pages/9_net_worth.py",         label="💎 Net Worth")
        st.sidebar.page_link("pages/10_rsu_espp.py",         label="📊 RSU/ESPP")
        st.sidebar.page_link("pages/11_portfolio.py",        label="🗂️ Portfolio")
        st.sidebar.page_link("pages/12_market_news.py",      label="📰 Market News")
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            f"<div style='font-size:0.72rem; color:{TEXT_MUTED}; text-transform:uppercase; "
            f"letter-spacing:0.06em; padding:4px 0 2px 4px;'>🎓 Learning</div>",
            unsafe_allow_html=True
        )
        st.sidebar.page_link("pages/89_learning_system.py", label="🧠 Learning System")
        st.sidebar.page_link("pages/90_ai_workflow_hub.py", label="⚡ AI Workflow Hub")
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            f"<div style='font-size:0.72rem; color:{TEXT_MUTED}; text-transform:uppercase; "
            f"letter-spacing:0.06em; padding:4px 0 2px 4px;'>🛠️ Tools</div>",
            unsafe_allow_html=True
        )
        st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo")
        st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes")
        st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator Companion")
        st.sidebar.page_link("pages/17_personal_assistant.py",  label="🤖 AI Assistant")
        st.sidebar.page_link("pages/144_holistic_health_dashboard.py", label="🌿 Health Dashboard")
        st.sidebar.page_link("pages/145_family_health_portal.py",      label="💚 Family Health Portal")
    else:
        # ── Upgrade prompt for free users ─────────────────────────────────────
        st.sidebar.markdown("---")
        st.sidebar.page_link("pages/0_pricing.py", label="⭐ Upgrade to Pro")


def render_sidebar_user_widget():
    """
    Render the user account widget at the bottom of the sidebar.
    Shows profile photo (if static/photos/darrian_profile.jpg exists),
    email, plan badge, upgrade button, and logout.
    """
    import os as _os
    user = get_current_user()
    if not user:
        return

    email = user.get("email", "")
    pro   = is_pro_user(user)
    badge = (f'<span class="pro-badge">PRO</span>'
             if pro else f'<span class="free-badge">FREE</span>')

    st.sidebar.markdown("---")

    # ── Profile photo ─────────────────────────────────────────────────────────
    _profile_path = _os.path.join(
        _os.path.dirname(_os.path.dirname(__file__)),
        "static", "photos", "darrian_profile.jpg"
    )
    if _os.path.exists(_profile_path):
        st.sidebar.image(
            _profile_path,
            width=72,
            caption=None,
            use_container_width=False,
        )
        st.sidebar.markdown(
            "<style>[data-testid='stSidebar'] img { border-radius: 50%; border: 2px solid #FFB300; }</style>",
            unsafe_allow_html=True,
        )

    st.sidebar.markdown(
        f"<div style='font-size:0.78rem; color:{TEXT_MUTED};'>Signed in as</div>"
        f"<div style='font-size:0.82rem; color:{TEXT_MAIN}; font-weight:600; "
        f"word-break:break-all;'>{email} {badge}</div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if not pro:
            if st.button("⬆️ Upgrade", use_container_width=True,
                         key="sidebar_upgrade"):
                st.switch_page("pages/0_pricing.py")
    with col2:
        if st.button("Sign Out", use_container_width=True, key="sidebar_logout"):
            set_active_db(None)
            for key in ["user", "authenticated", "api_key",
                        "inv_loaded_from_db", "_css_injected"]:
                st.session_state.pop(key, None)
            st.rerun()
